//+------------------------------------------------------------------+
//|  NXS_InstitutionalCore.mqh - Modello istituzionale (v2.1.0)      |
//|  Una lettura unica del mercato guida tutto:                      |
//|   1) raccoglie i segnali gia' prodotti dalle 37 strategie        |
//|   2) li RAGGRUPPA per direzione (confluenza = 1 posizione forte)  |
//|   3) classifica CONTINUAZIONE vs REVERSAL                         |
//|   4) calcola il TIER dinamico = quanto in alto e' confermato ->  |
//|      determina ampiezza SL/TP e durata (trend largo vs scalp)     |
//|  Le strategie CONFERMANO, non decidono da sole.                  |
//|  Dietro InpUseInstitutionalCore (OFF di default).                |
//+------------------------------------------------------------------+
#ifndef __NXS_INSTITUTIONAL_CORE_MQH__
#define __NXS_INSTITUTIONAL_CORE_MQH__

#define NXS_SETUP_CONTINUATION  0
#define NXS_SETUP_REVERSAL      1

struct SNXSDecision {
   ENUM_NXS_DIR    dir;          // direzione dominante
   double          confidence;   // conviction netta aggregata (dir dominante - opposta)
   int             tier;         // 0=local .. 3=D1: quanto in alto e' confermato
   ENUM_TIMEFRAMES tierTF;       // TF associato al tier (per SL/TP e durata)
   int             setupType;    // NXS_SETUP_CONTINUATION | NXS_SETUP_REVERSAL
   int             contributors; // quante strategie concordano
   double          entryRef;
   double          slPrice;
   double          tpPrice;
   string          topStrat;     // strategia col punteggio piu' alto nel gruppo
   string          group;        // firma della collaborazione: "TSI+ADX_RSI+..."
   string          reason;
   bool            valid;
};

// Conta le posizioni core aperte nella direzione data (per il modello
// "1 posizione per direzione": gli add di grid/recovery arrivano in Fase 3).
int NXS_Inst_OpenPositionsInDir(ENUM_NXS_DIR dir){
   int cnt = 0;
   long want = (dir == DIR_BUY) ? POSITION_TYPE_BUY : POSITION_TYPE_SELL;
   for(int i = PositionsTotal() - 1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      if(PositionGetInteger(POSITION_TYPE) == want) cnt++;
   }
   return cnt;
}

// Tag di contesto per il comment: "TF-C/R" (es. "H4-R" = timeframe H4,
// Reversal / "M15-C" = M15, Continuazione). Cosi' in MT5 si vede a colpo
// d'occhio su che timeframe e con che tipo di setup e' aperta la posizione.
string NXS_Inst_CtxTag(SNXSDecision &d){
   string tf = StringSubstr(EnumToString(d.tierTF), 7);   // "M15","H1","H4","D1"
   string cr = (d.setupType == NXS_SETUP_REVERSAL) ? "R" : "C";
   return tf + "-" + cr;
}

// TF associato a ciascun tier (0=local usa il TF di esecuzione).
ENUM_TIMEFRAMES _nxs_inst_tierTF(int tier){
   if(tier >= 3) return PERIOD_D1;
   if(tier == 2) return PERIOD_H4;
   if(tier == 1) return PERIOD_H1;
   return InpTFEntry;
}

// Quanti concetti del contesto sono allineati con la direzione -> tier.
int _nxs_inst_tier(int dir){
   if(!g_ctx.valid) return 0;
   int a = 0;
   if(g_ctx.structTrend == dir) a++;
   if(g_ctx.bosDir      == dir) a++;
   if(g_ctx.htfBias     == dir) a++;
   if(g_ctx.sweepDir    == dir) a++;
   if(g_ctx.zoneDir     == dir) a++;
   if(g_ctx.reactionDir == dir) a++;
   if(a >= 5) return 3;
   if(a >= 3) return 2;
   if(a >= 1) return 1;
   return 0;
}

// Continuazione (con il trend) o reversal (la direzione cambia a una flip zone).
int _nxs_inst_setupType(int dir){
   if(!g_ctx.valid) return NXS_SETUP_CONTINUATION;
   // Reversal: si va CONTRO il trend di struttura, ma con CHoCH o reazione a
   // favore (tipico ribaltamento ex-zona buy->sell / sell->buy).
   if(g_ctx.structTrend == -dir &&
      (g_ctx.chochDir == dir || g_ctx.reactionDir == dir))
      return NXS_SETUP_REVERSAL;
   return NXS_SETUP_CONTINUATION;
}

// Costruisce la decisione dominante raggruppando i segnali per direzione.
//: AUD0-INST-010 — famiglia di appartenenza usata per pesare i contributi
//: correlati SOLO quando InpInstCorrelationWeighting e' true (default: false).
//
// ⚠️ QUESTA CLASSIFICAZIONE NON E' AFFIDABILE, ed e' documentato che non lo sia.
// Il commento originale diceva "raggruppa per CONCETTO letto, non per nome":
// era falso. L'implementazione raggruppa per SOTTOSTRINGA DEL NOME, cioe'
// esattamente per nome. Conseguenze verificate (MM-12):
//
//   - 12 strategie live su 37 cadono in "OTHER" — AMD_CONT, BB_SQUEEZE, BJORGUM,
//     ELLIOTT, ICHIMOKU, MALAYSIAN_SNR, OTE_CONT, PO3, SILVER_BULLET,
//     THREE_BAR_DELIVERY_BREAK, TSI, WEEKLY_EXP — e "OTHER" e' trattato come una
//     famiglia vera: 66 coppie non imparentate si penalizzano a vicenda;
//   - ADX_RSI finisce in MEAN_REVERSION perche' il nome contiene "RSI";
//     LDN_REVERSAL e NY_REVERSAL perche' contengono "REVERSAL", pur essendo
//     strategie di sessione;
//   - la partizione e' in disaccordo con la famiglia del registro canonico su
//     154 coppie di strategie su 666;
//   - l'ordine delle regole conta: BOLLINGER evita MOMENTUM (che cerca "BO")
//     solo perche' la regola MEAN_REVERSION viene prima. Fragile al primo
//     rename o alla prima regola inserita in mezzo.
//
// Non la sostituisco con un'altra formula: servirebbe una tassonomia canonica
// definita e una misura reale della correlazione fra strategie. Finche' non
// esistono, questa funzione ha effetto solo se qualcuno accende esplicitamente
// l'input sperimentale.
string _nxs_inst_family(string name){
   if(StringFind(name, "FVG") >= 0 || StringFind(name, "IFVG") >= 0 ||
      StringFind(name, "DISP") >= 0 || StringFind(name, "VOID") >= 0)
      return "IMBALANCE";
   if(StringFind(name, "OB") >= 0 || StringFind(name, "ORDER_BLOCK") >= 0 ||
      StringFind(name, "BMS") >= 0 || StringFind(name, "STRUCT") >= 0)
      return "STRUCTURE";
   if(StringFind(name, "LIQ") >= 0 || StringFind(name, "SWEEP") >= 0 ||
      StringFind(name, "TURTLE") >= 0 || StringFind(name, "JUDAS") >= 0)
      return "LIQUIDITY";
   if(StringFind(name, "REVERSAL") >= 0 || StringFind(name, "RSI") >= 0 ||
      StringFind(name, "BOLLINGER") >= 0 || StringFind(name, "RANGE") >= 0)
      return "MEAN_REVERSION";
   if(StringFind(name, "BREAKOUT") >= 0 || StringFind(name, "BO") >= 0 ||
      StringFind(name, "MACD") >= 0 || StringFind(name, "ADX") >= 0 ||
      StringFind(name, "EMA") >= 0 || StringFind(name, "SAR") >= 0)
      return "MOMENTUM";
   return "OTHER";
}

// EXPERIMENTAL — conviction netta con peso decrescente sui contributi della
// stessa famiglia: il primo vale pieno, il secondo 1/2, il terzo 1/3...
//
// Isolata in una funzione propria per tre motivi, tutti richiesti prima di
// poterla anche solo considerare:
//   1. il chiamante puo' non eseguirla affatto (default), e allora il
//      comportamento e' esattamente quello della baseline;
//   2. e' confrontabile: stessa lista di segnali, due numeri, una differenza;
//   3. e' evidente che sia un ramo separato e non la regola del sistema.
//
// NON adottare come canonica senza: confronto contro baseline su dati reali,
// una tassonomia di famiglia che misuri correlazione (non sottostringhe del
// nome), e una motivazione per la forma 1/(n+1) invece di qualunque altra.
double _nxs_inst_correlationAdjustedNet(SNXSSignal &all[], int n){
   double buyAdj = 0, sellAdj = 0;
   string famSeen[]; int famCnt[];
   for(int i = 0; i < n; i++){
      if(all[i].dir == DIR_NONE) continue;
      string fam = _nxs_inst_family(all[i].stratName);
      int idx = -1;
      for(int f = 0; f < ArraySize(famSeen); f++) if(famSeen[f] == fam){ idx = f; break; }
      if(idx < 0){
         idx = ArraySize(famSeen);
         ArrayResize(famSeen, idx + 1); ArrayResize(famCnt, idx + 1);
         famSeen[idx] = fam; famCnt[idx] = 0;
      }
      // 1.0, 0.5, 0.33, 0.25 ... per contributi successivi della stessa famiglia
      double w = 1.0 / (double)(famCnt[idx] + 1);
      famCnt[idx]++;
      if(all[i].dir == DIR_BUY) buyAdj += all[i].score * w;
      else                      sellAdj += all[i].score * w;
   }
   return MathAbs(buyAdj - sellAdj);
}

// Ritorna d.valid=false se non c'e' conviction sufficiente.
SNXSDecision NXS_Institutional_Decide(SNXSSignal &all[], int n){
   SNXSDecision d; ZeroMemory(d); d.dir = DIR_NONE; d.valid = false;
   if(!InpUseInstitutionalCore) return d;

   double buySum = 0, sellSum = 0;
   int    buyN = 0, sellN = 0;
   double topBuy = -1, topSell = -1;
   string topBuyName = "", topSellName = "";
   double topBuySL = 0, topSellSL = 0;   // SL strutturale del voto dominante
   for(int i = 0; i < n; i++){
      if(all[i].dir == DIR_BUY){
         buySum += all[i].score; buyN++;
         if(all[i].score > topBuy){ topBuy = all[i].score; topBuyName = all[i].stratName; topBuySL = all[i].slPrice; }
      } else if(all[i].dir == DIR_SELL){
         sellSum += all[i].score; sellN++;
         if(all[i].score > topSell){ topSell = all[i].score; topSellName = all[i].stratName; topSellSL = all[i].slPrice; }
      }
   }
   if(buyN == 0 && sellN == 0) return d;

   int dir = (buySum >= sellSum) ? +1 : -1;

   // AUD0-INST-010 / MM-13 — conviction netta.
   //
   // COMPORTAMENTO CANONICO (InpInstCorrelationWeighting = false, default):
   // la conviction e' la somma degli score, identica a prima che la pesatura
   // per famiglia esistesse. Nessun ramo sperimentale viene eseguito, quindi
   // conviction, sizing ed esposizione sono bit-per-bit quelli della baseline.
   double net = MathAbs(buySum - sellSum);   // conviction netta: piu' concordano, piu' e' forte

   // EXPERIMENTAL, disattivato di default. Il problema che affronta e' reale —
   // sommare cinque varianti dello stesso concetto sovrastima la convinzione —
   // ma il peso 1/(n+1) non e' stato validato e la famiglia su cui poggia non
   // misura correlazione (vedi il blocco su _nxs_inst_family). Resta qui,
   // accendibile e confrontabile, invece di essere cancellato: cosi' si potra'
   // misurare contro la baseline quando ci sara' una tassonomia canonica.
   if(InpInstCorrelationWeighting){
      net = _nxs_inst_correlationAdjustedNet(all, n);
   }

   int contributors = (dir > 0) ? buyN : sellN;
   if(net < InpInstMinConviction) return d;
   if(contributors < InpInstMinContributors) return d;

   int tier   = _nxs_inst_tier(dir);
   int setup  = _nxs_inst_setupType(dir);
   ENUM_TIMEFRAMES tf = _nxs_inst_tierTF(tier);

   // Firma della collaborazione: nomi delle strategie concordi (ordine di score,
   // all[] e' gia' ordinato), troncata per stare nel comment MT5.
   ENUM_NXS_DIR wantDir = (dir > 0) ? DIR_BUY : DIR_SELL;
   string group = "";
   int gAdded = 0;
   for(int i = 0; i < n; i++){
      if(all[i].dir != wantDir) continue;
      string nm = all[i].stratName;
      // AUD0-INST-011 — questa firma viene TRONCATA per stare nel commento MT5
      // (31 caratteri). Un commento troncato non e' provenienza: e' una nota
      // diagnostica. L'appartenenza autorevole al gruppo vive nel registro
      // degli intenti (group_id), che l'add istituzionale propaga e che il
      // ledger usa per ricomporre la sequenza. Qui resta solo la leggibilita'.
      if(StringLen(group) + StringLen(nm) + 1 > 20){ group += "+"; break; }
      if(gAdded > 0) group += "+";
      group += nm;
      gAdded++;
   }
   if(StringLen(group) == 0) group = ((dir > 0) ? topBuyName : topSellName);

   // SL/TP larghi, scalati sul tier (usa l'ATR del TF di esecuzione x fattore
   // del tier -> nessun doppio conteggio; piu' alto e' il tier, piu' respiro).
   double atr = (g_atr > 0 ? g_atr : g_point * 100.0);
   double tfMult = NXS_TF_SLTPMult(tf);
   double slDist = atr * InpInstBaseSL * tfMult;
   double tpDist = atr * InpInstBaseTP * tfMult;

   d.dir          = (dir > 0) ? DIR_BUY : DIR_SELL;
   d.confidence   = net;
   d.tier         = tier;
   d.tierTF       = tf;
   d.setupType    = setup;
   d.contributors = contributors;
   d.entryRef     = (dir > 0) ? SymbolInfoDouble(g_sym, SYMBOL_ASK)
                              : SymbolInfoDouble(g_sym, SYMBOL_BID);
   d.slPrice      = (dir > 0) ? d.entryRef - slDist : d.entryRef + slDist;
   d.tpPrice      = (dir > 0) ? d.entryRef + tpDist : d.entryRef - tpDist;

   // A) Allarga lo SL del gruppo oltre l'invalidazione strutturale del voto
   //    dominante (es. sotto l'OB / oltre lo sweep), ma non oltre InpInstMaxSLwiden
   //    volte lo SL di tier -> lo stop sta oltre l'invalidazione senza rovinare l'RR.
   double structSL = (dir > 0) ? topBuySL : topSellSL;
   if(InpInstMaxSLwiden > 0 && structSL > 0){
      double cap = slDist * InpInstMaxSLwiden;
      if(dir > 0 && structSL < d.slPrice){          // struttura piu' in basso
         d.slPrice = MathMax(structSL, d.entryRef - cap);
      } else if(dir < 0 && structSL > d.slPrice){   // struttura piu' in alto
         d.slPrice = MathMin(structSL, d.entryRef + cap);
      }
   }
   d.topStrat     = (dir > 0) ? topBuyName : topSellName;
   d.group        = group;
   d.reason = StringFormat("INST %s tier%d %s conv=%.0f [%s]",
                           (dir > 0 ? "BUY" : "SELL"), tier,
                           (setup == NXS_SETUP_REVERSAL ? "REV" : "CONT"),
                           net, group);
   d.valid = true;
   return d;
}

#endif
