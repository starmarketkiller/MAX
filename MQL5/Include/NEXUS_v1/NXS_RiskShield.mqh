//+------------------------------------------------------------------+
//|  NXS_RiskShield.mqh — Sprint 2 (drawdown protection)             |
//|  #6 Spread Burst · #10 Equity Breaker · #11 Correlation Cluster  |
//|  #14 News Tier-3 Position Management                             |
//|  v2.0.9 — institutional-grade capital defense layer              |
//+------------------------------------------------------------------+
#ifndef __NXS_RISKSHIELD_MQH__
#define __NXS_RISKSHIELD_MQH__

// =====================================================================
// #6 — SPREAD BURST PROTECTION
// Tracks a rolling window of spreads and freezes entries when current
// spread exceeds the P95 of the window. Eliminates fill-in-news-spike.
// =====================================================================
bool   InpSpreadBurst_Enable    = true;
int    InpSpreadBurst_Samples   = 1000;   // rolling window size
double InpSpreadBurst_P95Cap    = 1.30;   // multiplier of P95 (e.g. 1.3× P95)
int    InpSpreadBurst_FreezeSec = 30;     // freeze duration on burst

double g_NXSrsSpreadBuf[];          // ring buffer
int    g_NXSrsSpreadIdx  = 0;
int    g_NXSrsSpreadN    = 0;
datetime g_NXSrsFrozenUntil = 0;

void NXS_RS_SpreadSample(){
   double sp = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(sp <= 0) return;
   if(ArraySize(g_NXSrsSpreadBuf) < InpSpreadBurst_Samples)
      ArrayResize(g_NXSrsSpreadBuf, InpSpreadBurst_Samples);
   g_NXSrsSpreadBuf[g_NXSrsSpreadIdx] = sp;
   g_NXSrsSpreadIdx = (g_NXSrsSpreadIdx + 1) % InpSpreadBurst_Samples;
   if(g_NXSrsSpreadN < InpSpreadBurst_Samples) g_NXSrsSpreadN++;
}

// AUD0-RS-005: questa funzione copiava e ORDINAVA fino a 1000 campioni a OGNI
// preflight d'ingresso (O(n log n) per ogni segnale valutato, su ogni tick).
// Il P95 di una finestra rolling di 1000 osservazioni non cambia in modo
// significativo fra due tick: ora si ricalcola con cadenza limitata e si
// riusa il valore in cache nel frattempo.
//
// La cache viene invalidata anche quando la finestra e' cambiata di almeno
// il 5% dei campioni, cosi' un burst di spread non resta mascherato da un
// P95 vecchio piu' a lungo del dovuto.
#define NXS_RS_P95_MAX_AGE_SEC 5

double g_NXSrsP95Cache     = 0.0;
datetime g_NXSrsP95At      = 0;
int      g_NXSrsP95SamplesAt = -1;

double _NXS_RS_SpreadP95Compute(){
   double tmp[];
   ArrayResize(tmp, g_NXSrsSpreadN);
   for(int i = 0; i < g_NXSrsSpreadN; ++i) tmp[i] = g_NXSrsSpreadBuf[i];
   ArraySort(tmp);
   int p95Idx = (int)MathFloor(g_NXSrsSpreadN * 0.95);
   if(p95Idx >= g_NXSrsSpreadN) p95Idx = g_NXSrsSpreadN - 1;
   return tmp[p95Idx];
}

double NXS_RS_SpreadP95(){
   if(g_NXSrsSpreadN < 50) return 0;  // warm-up

   datetime now = TimeCurrent();
   // Contatore monotono di campioni visti: g_NXSrsSpreadN si satura al tetto
   // della finestra, quindi da solo non segnala piu' il ricambio.
   int churn = (int)MathMax(1, g_NXSrsSpreadN / 20);   // 5% della finestra
   int win   = (int)MathMax(1, ArraySize(g_NXSrsSpreadBuf));
   // L'indice e' un ring buffer: la differenza va presa modulo la finestra,
   // altrimenti il wrap-around produce un delta enorme (o negativo).
   int delta = (g_NXSrsSpreadIdx - g_NXSrsP95SamplesAt + win) % win;
   bool stale = (g_NXSrsP95SamplesAt < 0) ||
                ((now - g_NXSrsP95At) >= NXS_RS_P95_MAX_AGE_SEC) ||
                (delta >= churn);

   if(stale){
      g_NXSrsP95Cache      = _NXS_RS_SpreadP95Compute();
      g_NXSrsP95At         = now;
      g_NXSrsP95SamplesAt  = g_NXSrsSpreadIdx;
   }
   return g_NXSrsP95Cache;
}

// Call before each new entry attempt. Returns true if entries are blocked.
bool NXS_RS_SpreadBurst_Block(string &reason){
   if(!InpSpreadBurst_Enable) return false;
   NXS_RS_SpreadSample();
   if(TimeCurrent() < g_NXSrsFrozenUntil){
      reason = StringFormat("SPREAD_BURST_FROZEN until %s",
                            TimeToString(g_NXSrsFrozenUntil, TIME_SECONDS));
      return true;
   }
   double p95 = NXS_RS_SpreadP95();
   if(p95 <= 0) return false;          // warm-up, allow
   double cur = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(cur > p95 * InpSpreadBurst_P95Cap){
      g_NXSrsFrozenUntil = TimeCurrent() + InpSpreadBurst_FreezeSec;
      reason = StringFormat("SPREAD_BURST cur=%.0f p95=%.0f cap=%.0f freeze=%ds",
                            cur, p95, p95 * InpSpreadBurst_P95Cap, InpSpreadBurst_FreezeSec);
      return true;
   }
   // AUD0-RS-006: durante il warm-up (meno di 50 campioni) il P95 vale zero e
   // il gate lasciava passare TUTTO, proprio nei primi minuti dopo l'avvio,
   // quando lo spread è tipicamente più largo. Si applica il tetto duro del
   // profilo simbolo finché non ci sono abbastanza campioni.
   if(p95 <= 0){
      double hardCap = (InpHardMaxSpreadPts > 0) ? (double)InpHardMaxSpreadPts
                                                 : (double)g_profile.maxSpreadPts;
      if(hardCap > 0 && cur > hardCap){
         reason = StringFormat("SPREAD_WARMUP cur=%.0f > cap_profilo=%.0f "
                               "(campioni insufficienti per il P95)", cur, hardCap);
         return true;
      }
   }
   return false;
}

// =====================================================================
// #10 — EQUITY CURVE BREAKER (rolling Sharpe auto-pause)
// Computes Sharpe over the last N closed trades. If Sharpe < threshold,
// the EA self-pauses for `InpBreaker_PauseHours` and pushes a Coach alert.
// =====================================================================
// 30/08 - resi input veri (erano plain, invisibili al Tester/.set -
// stessa classe di bug gia' trovata e corretta piu' volte oggi).
// Scoperto durante l'esperimento pip-sequence: questo breaker (Sharpe
// rolling su 50 trade < 0.30 -> pausa 24h) restava sempre attivo
// nonostante non fosse nella lista dei toggle disponibili da .set -
// visibile nei log come "[NEXUS RS] EQUITY_BREAKER ... nuove entrate
// sospese".
input bool   InpBreaker_Enable      = true;
input int    InpBreaker_LookbackN   = 50;
input double InpBreaker_SharpeMin   = 0.30;
input int    InpBreaker_PauseHours  = 24;

// g_NXSrsBreakerUntil / g_NXSrsLastSharpe: dichiarati in NXS_Globals.mqh
// perché NXS_State.mqh li persiste ed è incluso prima di questo file.

// AUD0-RS-008 — unita' di misura e normalizzazione del Sharpe.
//
// La versione precedente accettava valori descritti come "in R o in dollari":
// due unita' diverse nella stessa finestra rendono la soglia incomparabile, e
// la deviazione standard era di POPOLAZIONE (divisa per n) invece che
// campionaria (n-1), sottostimando sistematicamente sigma e gonfiando lo
// Sharpe proprio quando i campioni sono pochi.
//
// Ora il contratto e' esplicito e verificato:
//   - l'ingresso e' SEMPRE in multipli di R (perdita = -1.0), prodotti da
//     NXS_RS_Breaker_Update(): il chiamante non sceglie piu' l'unita';
//   - sigma e' campionaria (n-1);
//   - lo Sharpe e' PER TRADE, non annualizzato: la soglia InpBreaker_SharpeMin
//     va letta come "Sharpe medio per operazione", ed e' documentato qui
//     invece di essere lasciato ambiguo. Annualizzare richiederebbe una
//     frequenza di trading stabile che questo EA non garantisce (le
//     protezioni possono sospendere il trading per ore).
//   - un guardiano di plausibilita' rifiuta finestre che chiaramente non
//     sono in R (|R| oltre il tetto), invece di calcolare in silenzio uno
//     Sharpe privo di significato.
#define NXS_RS_MAX_PLAUSIBLE_R 50.0

// 02/09 - REFATTORIZZATA: prima calcolava lo Sharpe e scriveva DIRETTAMENTE
// nei globali g_NXSrsBreakerUntil/g_NXSrsLastSharpe come effetto collaterale.
// Bloccava TUTTO il conto (ogni strategia, anche quelle che stavano andando
// bene) quando una sola strategia aveva una serie negativa - richiesto
// dall'utente: bloccare solo la strategia responsabile. Ora e' una funzione
// pura (nessun globale toccato): calcola e ritorna lo sharpe, il chiamante
// decide dove salvare l'esito (vedi NXS_RS_Breaker_Update sotto, che la
// chiama una volta per ogni strategia con la SUA finestra di rendimenti).
bool NXS_RS_Breaker_Check(double &rets[], int n, double &sharpeOut, string &reason){
   reason = ""; sharpeOut = 0.0;
   if(!InpBreaker_Enable || n < InpBreaker_LookbackN) return false;
   if(InpBreaker_LookbackN < 2) return false;   // sigma campionaria indefinita

   int from = n - InpBreaker_LookbackN;
   int cnt  = InpBreaker_LookbackN;

   // Guardiano di unita': se i valori non sono R, la soglia non ha senso.
   for(int i = from; i < n; ++i){
      if(MathAbs(rets[i]) > NXS_RS_MAX_PLAUSIBLE_R){
         PrintFormat("[NEXUS RS] Equity breaker SALTATO: valore %.2f fuori scala per un "
                     "multiplo di R (tetto %.1f). La finestra non e' in R: soglia non "
                     "comparabile, nessuna decisione presa.", rets[i], NXS_RS_MAX_PLAUSIBLE_R);
         return false;
      }
   }

   double sum = 0.0;
   for(int i = from; i < n; ++i) sum += rets[i];
   double mean = sum / cnt;

   double sqsum = 0.0;
   for(int i = from; i < n; ++i){
      double d = rets[i] - mean;
      sqsum += d * d;
   }
   double sigma = MathSqrt(sqsum / (cnt - 1));   // campionaria, non di popolazione

   // sigma ~ 0 con media positiva non e' "Sharpe zero": e' una serie senza
   // dispersione. Trattarla come 0.0 faceva scattare il breaker su una serie
   // di vincite identiche. Si esce senza decidere.
   if(sigma <= 1e-9){
      sharpeOut = (mean >= 0 ? 99.0 : -99.0);
      if(mean >= 0) return false;
   }
   double sharpe = (sigma > 1e-9 ? mean / sigma : (mean >= 0 ? 99.0 : -99.0));
   sharpeOut = sharpe;

   if(sharpe < InpBreaker_SharpeMin){
      reason = StringFormat("EQUITY_BREAKER sharpe/trade=%.2f<%.2f n=%d pause=%dh",
                            sharpe, InpBreaker_SharpeMin, InpBreaker_LookbackN,
                            InpBreaker_PauseHours);
      return true;
   }
   return false;
}

// AUD0-RS-008 (secondo difetto, non presente nell'audit): il breaker non era
// MAI alimentato. NXS_RS_Breaker_Check() non veniva chiamato da nessuna parte
// del progetto, quindi g_NXSrsBreakerUntil restava a 0 e il gate in
// NXS_RS_BlockEntry() non poteva scattare: una protezione documentata e
// completamente inerte.
//
// Questa funzione costruisce la finestra dei rendimenti dallo storico dei deal
// e la passa al check. Gira a cadenza limitata: e' una scansione della
// history, non deve stare sul percorso del tick.
datetime g_NXSrsBreakerLastCalc = 0;
#define NXS_RS_BREAKER_CALC_SEC 300

// 02/09 - stato PER STRATEGIA (era un'unica coppia globale che bloccava
// tutto il conto). Array paralleli, stesso pattern gia' usato altrove nel
// progetto (es. NXS_ProfitReclaim.mqh) invece di una struct con array
// dentro, per compatibilita' con le versioni piu' vecchie di MQL5 usate qui.
#define NXS_RS_BREAKER_MAX 64
string   g_NXSrsBreakerStrat[NXS_RS_BREAKER_MAX];
datetime g_NXSrsBreakerStratUntil[NXS_RS_BREAKER_MAX];
double   g_NXSrsBreakerStratSharpe[NXS_RS_BREAKER_MAX];
int      g_NXSrsBreakerStratCount = 0;

int _NXS_RS_BreakerStratFind(string name){
   for(int i = 0; i < g_NXSrsBreakerStratCount; ++i)
      if(g_NXSrsBreakerStrat[i] == name) return i;
   return -1;
}
int _NXS_RS_BreakerStratEnsure(string name){
   int i = _NXS_RS_BreakerStratFind(name);
   if(i >= 0) return i;
   if(g_NXSrsBreakerStratCount >= NXS_RS_BREAKER_MAX) return -1;   // limite di sicurezza, mai atteso in pratica
   int idx = g_NXSrsBreakerStratCount++;
   g_NXSrsBreakerStrat[idx] = name;
   g_NXSrsBreakerStratUntil[idx] = 0;
   g_NXSrsBreakerStratSharpe[idx] = 0.0;
   return idx;
}

void NXS_RS_Breaker_Update(){
   if(!InpBreaker_Enable) return;
   datetime now = TimeCurrent();
   if(now - g_NXSrsBreakerLastCalc < NXS_RS_BREAKER_CALC_SEC) return;
   g_NXSrsBreakerLastCalc = now;

   // Denominatore R costante sulla finestra: il budget di rischio nominale per
   // operazione. Costante ⇒ non altera lo Sharpe (che e' invariante di scala),
   // ma rende i valori leggibili come R e attivabile il guardiano di unita'.
   double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0;
   if(riskMoney <= 0.0) return;

   // Finestra temporale generosa: servono InpBreaker_LookbackN chiusure, non
   // un intervallo fisso. 90 giorni coprono qualunque cadenza realistica.
   if(!HistorySelect(now - 90 * 86400, now)) return;
   int total = HistoryDealsTotal();
   if(total <= 0) return;

   // Un solo giro sullo storico: raccoglie (strategia, rendimento in R) per
   // ogni deal di chiusura, poi valuta lo Sharpe SEPARATAMENTE per ogni
   // strategia incontrata - non piu' un'unica serie mescolata.
   string allName[]; double allRet[];
   ArrayResize(allName, 0); ArrayResize(allRet, 0);
   for(int i = 0; i < total; ++i){
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket, DEAL_ENTRY) == DEAL_ENTRY_IN) continue;
      if(!IsNexusMagic((long)HistoryDealGetInteger(ticket, DEAL_MAGIC))) continue;
      if(HistoryDealGetString(ticket, DEAL_SYMBOL) != g_sym) continue;
      double net = HistoryDealGetDouble(ticket, DEAL_PROFIT) +
                   HistoryDealGetDouble(ticket, DEAL_SWAP) +
                   HistoryDealGetDouble(ticket, DEAL_COMMISSION);
      string strat, group;
      _NXS_StateParseComment(HistoryDealGetString(ticket, DEAL_COMMENT), strat, group);
      int k = ArraySize(allName);
      ArrayResize(allName, k + 1); ArrayResize(allRet, k + 1);
      allName[k] = strat; allRet[k] = net / riskMoney;
   }
   int n = ArraySize(allName);
   if(n < InpBreaker_LookbackN) return;   // nemmeno il totale basta per una sola strategia

   string doneNames[]; ArrayResize(doneNames, 0);
   for(int i = 0; i < n; ++i){
      string sname = allName[i];
      bool already = false;
      for(int k = 0; k < ArraySize(doneNames); ++k) if(doneNames[k] == sname){ already = true; break; }
      if(already) continue;
      int dk = ArraySize(doneNames); ArrayResize(doneNames, dk + 1); doneNames[dk] = sname;

      double stratRets[]; ArrayResize(stratRets, 0);
      for(int j = 0; j < n; ++j){
         if(allName[j] != sname) continue;
         int rk = ArraySize(stratRets); ArrayResize(stratRets, rk + 1); stratRets[rk] = allRet[j];
      }
      int rn = ArraySize(stratRets);
      if(rn < InpBreaker_LookbackN) continue;

      double sharpe = 0.0; string reason = "";
      bool trip = NXS_RS_Breaker_Check(stratRets, rn, sharpe, reason);
      int idx = _NXS_RS_BreakerStratEnsure(sname);
      if(idx < 0) continue;
      g_NXSrsBreakerStratSharpe[idx] = sharpe;
      if(trip){
         g_NXSrsBreakerStratUntil[idx] = now + InpBreaker_PauseHours * 3600;
         PrintFormat("[NEXUS RS] %s strat=%s — nuove entrate di QUESTA STRATEGIA sospese fino a %s "
                     "(le altre continuano)", reason, sname,
                     TimeToString(g_NXSrsBreakerStratUntil[idx], TIME_DATE | TIME_MINUTES));
      }
   }

   // Compat: i vecchi globali (usati solo per persistenza/telemetria, non
   // piu' per bloccare) riportano il caso peggiore tra tutte le strategie.
   double worstSharpe = 999.0; datetime maxUntil = 0;
   for(int i = 0; i < g_NXSrsBreakerStratCount; ++i){
      if(g_NXSrsBreakerStratSharpe[i] < worstSharpe) worstSharpe = g_NXSrsBreakerStratSharpe[i];
      if(g_NXSrsBreakerStratUntil[i] > maxUntil) maxUntil = g_NXSrsBreakerStratUntil[i];
   }
   if(g_NXSrsBreakerStratCount > 0) g_NXSrsLastSharpe = worstSharpe;
   g_NXSrsBreakerUntil = maxUntil;
}

bool NXS_RS_Breaker_Active(string stratName){
   if(!InpBreaker_Enable) return false;
   int idx = _NXS_RS_BreakerStratFind(stratName);
   if(idx < 0) return false;   // non ancora abbastanza trade per questa strategia: mai scattato
   return TimeCurrent() < g_NXSrsBreakerStratUntil[idx];
}

double NXS_RS_Breaker_LastSharpe(string stratName){
   int idx = _NXS_RS_BreakerStratFind(stratName);
   return (idx >= 0) ? g_NXSrsBreakerStratSharpe[idx] : 0.0;
}

// =====================================================================
// #11 — CORRELATION-CLUSTER RISK CAP
// Two perfectly correlated trades = 2× the intended risk. Group symbols
// into clusters and cap concurrent exposure per cluster, not per ticket.
// =====================================================================
int InpCluster_MaxPerCluster = 2;   // max concurrent positions per cluster

// Static cluster table. Each symbol belongs to ONE cluster.
//   USD_STRONG: positions that benefit from a strong USD
//   USD_WEAK:   positions that benefit from a weak USD
//   GOLD_BLOCK: gold-correlated cluster
//   CRYPTO:     crypto risk-on cluster
//   INDEX_RISKON: equity indices risk-on cluster
string NXS_RS_ClusterOf(string sym){
   string s = sym; StringToUpper(s);
   if(StringFind(s, "XAU") >= 0 || StringFind(s, "GOLD") >= 0 ||
      StringFind(s, "XAG") >= 0 || StringFind(s, "SILVER") >= 0)
      return "GOLD_BLOCK";
   if(StringFind(s, "BTC") >= 0 || StringFind(s, "ETH") >= 0 ||
      StringFind(s, "SOL") >= 0 || StringFind(s, "DOGE") >= 0)
      return "CRYPTO";
   if(StringFind(s, "US30") >= 0 || StringFind(s, "NAS") >= 0 ||
      StringFind(s, "SPX") >= 0 || StringFind(s, "DAX") >= 0)
      return "INDEX_RISKON";
   if(StringFind(s, "EURUSD") >= 0 || StringFind(s, "GBPUSD") >= 0 ||
      StringFind(s, "AUDUSD") >= 0 || StringFind(s, "NZDUSD") >= 0)
      return "USD_STRONG";   // long these = short USD
   if(StringFind(s, "USDJPY") >= 0 || StringFind(s, "USDCAD") >= 0 ||
      StringFind(s, "USDCHF") >= 0)
      return "USD_WEAK";     // long these = long USD
   return "OTHER";
}

// Returns true if opening a position on `symbol` would exceed cluster cap.
// Caller passes the function that returns count of open positions per symbol.
//: Esposizione FIRMATA di un cluster, in lotti.
//:
//: AUD0-RS-002: il conteggio ignorava la direzione, quindi una posizione long
//: e una short sullo stesso fattore risultavano "due unità di rischio" mentre
//: in realtà si compensano. AUD0-RS-003: contava i ticket, quindi un trade da
//: 0.01 lotti e uno da 5 occupavano lo stesso slot.
//: AUD0-RS-001: contava OGNI posizione del conto, incluse quelle manuali o di
//: altri EA; ora si distingue esplicitamente il perimetro NEXUS.
struct SNXSClusterExposure {
   int    positions;      // conteggio (compatibilità con il cap storico)
   double netLots;        // lotti firmati: long positivi, short negativi
   double grossLots;      // lotti in valore assoluto
   int    foreignSkipped; // posizioni fuori dal perimetro NEXUS
};

void NXS_RS_ClusterExposure(string targetCluster, SNXSClusterExposure &out){
   out.positions = 0; out.netLots = 0; out.grossLots = 0; out.foreignSkipped = 0;
   int total = PositionsTotal();
   for(int i = 0; i < total; ++i){
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      string s = PositionGetString(POSITION_SYMBOL);
      if(s == "") continue;
      if(NXS_RS_ClusterOf(s) != targetCluster) continue;

      // Perimetro esplicito: il RiskShield governa l'esposizione NEXUS.
      // Le posizioni estranee vengono contate a parte, non ignorate in
      // silenzio, così l'operatore sa che esistono.
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))){
         out.foreignSkipped++;
         continue;
      }

      double vol = PositionGetDouble(POSITION_VOLUME);
      long   ptype = PositionGetInteger(POSITION_TYPE);
      out.positions++;
      out.grossLots += vol;
      out.netLots   += (ptype == POSITION_TYPE_BUY) ? vol : -vol;
   }
}

//: Compatibilità: il vecchio conteggio per ticket.
int NXS_RS_ClusterCount(string targetCluster){
   SNXSClusterExposure e;
   NXS_RS_ClusterExposure(targetCluster, e);
   return e.positions;
}

bool NXS_RS_Cluster_Block(string sym, string &reason){
   string cl = NXS_RS_ClusterOf(sym);

   // AUD0-RS-004: ogni simbolo non mappato finiva in un unico bucket OTHER
   // con cap 2, quindi strumenti scorrelati si bloccavano a vicenda. Un
   // cluster sconosciuto non è un cluster: si segnala e non si applica il cap
   // condiviso, che sarebbe arbitrario.
   if(cl == "OTHER"){
      PrintFormat("[NEXUS RS] simbolo %s non mappato a nessun cluster: "
                  "cap di correlazione non applicabile (definire un profilo)", sym);
      return false;
   }

   SNXSClusterExposure e;
   NXS_RS_ClusterExposure(cl, e);

   // Il cap resta sul conteggio per non cambiare la calibrazione esistente,
   // ma si usa l'esposizione NETTA: posizioni opposte sullo stesso fattore
   // non consumano slot perché non sommano rischio direzionale.
   double netAbs = MathAbs(e.netLots);
   bool hedged = (e.grossLots > 0 && netAbs < e.grossLots * 0.25);

   if(e.positions >= InpCluster_MaxPerCluster && !hedged){
      reason = StringFormat("CLUSTER_CAP %s pos=%d/%d net=%.2f gross=%.2f",
                            cl, e.positions, InpCluster_MaxPerCluster,
                            e.netLots, e.grossLots);
      return true;
   }
   if(e.foreignSkipped > 0)
      PrintFormat("[NEXUS RS] cluster %s: %d posizioni non-NEXUS non conteggiate",
                  cl, e.foreignSkipped);
   return false;
}

// =====================================================================
// #14 — NEWS TIER-3 POSITION MANAGEMENT
// Tier-1: hard block 30min around red news (existing).
// Tier-2: soft score penalty 60min around news (existing).
// Tier-3 (NEW): 5min before red news, tighten SL on open positions
//               to break-even + 1× ATR. Or 50% partial close.
// =====================================================================
bool   InpNewsTier3_Enable     = true;
int    InpNewsTier3_LeadMin    = 5;      // minutes before red news
int    InpNewsTier3_Mode       = 1;      // 0=close50% 1=tightenSL
double InpNewsTier3_SLBufferATR = 1.0;   // tighten to BE + N*ATR

// Caller provides: minutes until next red news, and the SYMBOL ATR.
// Returns the SL price that should be SET on existing positions (0 if no action).
// Callers loop over their open positions and call this for each.
double NXS_RS_NewsTier3_SuggestedSL(int minutesUntilRedNews, double openPrice,
                                    double atr, int direction){
   if(!InpNewsTier3_Enable) return 0.0;
   if(minutesUntilRedNews < 0 || minutesUntilRedNews > InpNewsTier3_LeadMin) return 0.0;
   if(InpNewsTier3_Mode != 1) return 0.0;
   if(direction == +1)  return openPrice + atr * InpNewsTier3_SLBufferATR;  // BUY: SL above
   if(direction == -1)  return openPrice - atr * InpNewsTier3_SLBufferATR;  // SELL: SL below
   return 0.0;
}

bool NXS_RS_NewsTier3_PartialCloseDue(int minutesUntilRedNews){
   if(!InpNewsTier3_Enable) return false;
   if(InpNewsTier3_Mode != 0) return false;
   return (minutesUntilRedNews >= 0 && minutesUntilRedNews <= InpNewsTier3_LeadMin);
}

// =====================================================================
// MASTER GATE — call this in TryExecute before sending the order.
// One single function that bundles all 4 protections.
// =====================================================================
bool NXS_RS_BlockEntry(string sym, string stratName, string &reason){
   if(NXS_RS_Breaker_Active(stratName)){
      reason = StringFormat("EQUITY_BREAKER strat=%s sharpe=%.2f", stratName,
                            NXS_RS_Breaker_LastSharpe(stratName));
      return true;
   }
   if(NXS_RS_SpreadBurst_Block(reason)) return true;
   if(NXS_RS_Cluster_Block(sym, reason)) return true;
   return false;
}

#endif // __NXS_RISKSHIELD_MQH__
