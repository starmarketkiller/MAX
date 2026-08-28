//+------------------------------------------------------------------+
//|  NXS_Strategies_Institutional.mqh                                 |
//|  NEXUS v2.0.7 — 9 Institutional/ICT models (READY_FOR_BACKTEST)   |
//|                                                                   |
//|  Tutte le strategie ritornano SNXSSignal completo: dir, score,    |
//|  stratName, reason, slPrice, tpPrice, entryRef, strat.            |
//|  Score base 70-75; SL/TP da struttura quando possibile.           |
//|                                                                   |
//|  Tutte le funzioni rispettano il pattern del router NEXUS:        |
//|    - early return su input toggle disabilitato                    |
//|    - assegnano stratName per stat lifecycle tracking              |
//|    - reason string compatibile con log [NEXUS DECISION]           |
//+------------------------------------------------------------------+
#ifndef __NXS_STRATEGIES_INST_MQH__
#define __NXS_STRATEGIES_INST_MQH__

// ----- shared helpers -----------------------------------------------------
double _inst_atr(){ return g_atr > 0 ? g_atr : 1.0 * g_point; }

// Find last bullish/bearish "delivery candle" (body) in lookback window
// dir=+1 = last bullish delivery (used as resistance to reclaim for CISD buy)
// dir=-1 = last bearish delivery
bool _inst_lastDelivery(int dir, int lookback, double &outHigh, double &outLow){
   for(int i = 1; i <= lookback; i++){
      double o = iOpen (g_sym, NXS_EffTF(), i);
      double c = iClose(g_sym, NXS_EffTF(), i);
      double h = iHigh (g_sym, NXS_EffTF(), i);
      double l = iLow  (g_sym, NXS_EffTF(), i);
      double body = MathAbs(c - o);
      if(body < _inst_atr() * 0.5) continue;
      if(dir > 0 && c > o){ outHigh = h; outLow = l; return true; }
      if(dir < 0 && c < o){ outHigh = h; outLow = l; return true; }
   }
   return false;
}

// Detect bullish/bearish displacement bar within `lookback`
// Returns the bar index (>=1) or -1 if not found
int _inst_displacementBar(int dir, int lookback, double bodyMult){
   double atr = _inst_atr();
   for(int i = 1; i <= lookback; i++){
      double o = iOpen (g_sym, NXS_EffTF(), i);
      double c = iClose(g_sym, NXS_EffTF(), i);
      double body = MathAbs(c - o);
      if(body < atr * bodyMult) continue;
      if(dir > 0 && c > o) return i;
      if(dir < 0 && c < o) return i;
   }
   return -1;
}

// GMT hour (server time - offset)
int _inst_gmtHour(){
   datetime g = (datetime)((long)TimeCurrent() - (long)InpServerGMTOffset * 3600);
   MqlDateTime mt; TimeToStruct(g, mt);
   return mt.hour;
}

bool _inst_inLondonOpen(){
   int h = _inst_gmtHour();
   return (h >= 7 && h < 10);   // London open / pre-killzone window
}
bool _inst_inNYOpen(){
   int h = _inst_gmtHour();
   return (h >= 12 && h < 15);  // NY open / killzone
}

// =================================================================
// 1. CISD — Change In State of Delivery
// =================================================================
// 17/07 notte - rinominata da "CISD" a "THREE_BAR_DELIVERY_BREAK", da audit
// esterno canonico: il vero Change in State of Delivery e' normalmente
// identificato dalla rottura del LIVELLO/OPEN che sosteneva la sequenza di
// candele opposte, non da "tre candele dello stesso colore + rottura del
// loro massimo/minimo" - questo e' un pattern di rottura reale e
// funzionante, ma non e' un CISD canonico. Rinominata invece di riscritta:
// un tentativo precedente di versione "vera" (displacement+delivery+sweep+
// reclaim, v2.3.3, vedi commento sotto) non scattava MAI (0 setup su
// 1067) - rischio concreto di silenziare di nuovo la strategia. La logica
// resta invariata, cambia solo l'identita' dichiarata (nome, non concetto
// preteso). Il toggle InpUseStrat_CISD resta invariato per non rompere i
// .set esistenti.
SNXSSignal NXS_Strat_CISD(SNXSSweepExt &sw){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "THREE_BAR_DELIVERY_BREAK";
   if(!InpUseStrat_CISD) return s;
   // v2.3.3 — riportata la logica SEMPLICE del sito (change in state of delivery):
   // 3 barre chiuse dello stesso segno, poi rottura del loro estremo. La vecchia
   // versione (displacement+delivery+sweep+reclaim) non scattava MAI (0 setup su
   // 1067) e hardcodava SL/TP ignorando il profilo. Ora usa NXS_DefaultSLTP.
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   double c1 = iClose(g_sym, tf, 1);
   double o2=iOpen(g_sym,tf,2), c2=iClose(g_sym,tf,2), h2=iHigh(g_sym,tf,2), l2=iLow(g_sym,tf,2);
   double o3=iOpen(g_sym,tf,3), c3=iClose(g_sym,tf,3), h3=iHigh(g_sym,tf,3), l3=iLow(g_sym,tf,3);
   double o4=iOpen(g_sym,tf,4), c4=iClose(g_sym,tf,4), h4=iHigh(g_sym,tf,4), l4=iLow(g_sym,tf,4);
   bool bear3 = (c2<o2) && (c3<o3) && (c4<o4);
   bool bull3 = (c2>o2) && (c3>o3) && (c4>o4);
   double hh = MathMax(h2, MathMax(h3, h4));
   double ll = MathMin(l2, MathMin(l3, l4));
   if(bear3 && c1 > hh){ s.dir = DIR_BUY;  s.score = 74.0; s.reason = "CISD bull (3bear+break)"; }
   else if(bull3 && c1 < ll){ s.dir = DIR_SELL; s.score = 74.0; s.reason = "CISD bear (3bull+break)"; }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);   // SL/TP dal profilo (come il sito)
   return s;
}

// =================================================================
// 2. AMD CONTINUATION (not reversal)
// =================================================================
SNXSSignal NXS_Strat_AMD_Continuation(SNXSAMD &amd, SNXSHTF &htf){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "AMD_CONT";
   if(!InpUseStrat_AMD_Cont) return s;
   if(amd.asianHigh <= 0 || amd.asianLow <= 0) return s;
   // v2.0.34 (audit point 4): only the confirmed continuation/acceptance
   // phase now - was AMD_DISTRIBUTION, the same condition AMD_REVERSAL
   // gated on, so both were eligible on the same bars.
   if(amd.phase != AMD_CONTINUATION_DISTRIBUTION) return s;
   if(!(g_session == SESS_LONDON || g_session == SESS_OVERLAP || g_session == SESS_NY)) return s;

   double atr = _inst_atr();
   double mid = (amd.asianHigh + amd.asianLow) * 0.5;
   // 17/07 notte - da audit esterno canonico: mescolava close della barra 1
   // (breakout) con bid live (retest) - due punti temporali diversi sulla
   // stessa condizione. Ora tutto sulla barra chiusa 1: il breakout e il
   // retest devono appartenere alla STESSA barra (low tocca la fascia,
   // close conferma oltre il bordo) - niente prezzo live.
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double l1 = iLow  (g_sym, NXS_EffTF(), 1);
   double h1 = iHigh (g_sym, NXS_EffTF(), 1);

   // BUY: distribution above Asian range + retest near asianHigh + htf bull/neutral
   if(c1 > amd.asianHigh && l1 <= amd.asianHigh + atr * 0.6
      && (htf.bias == HTF_BULL || htf.bias == HTF_NEUTRAL)){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = MathMin(amd.asianHigh - 0.3 * atr, mid);
      s.tpPrice = s.entryRef + 2.4 * (s.entryRef - s.slPrice);
      s.score   = 72.0;
      s.reason  = "AMD_CONT bull:asiaHi retest";
      return s;
   }
   // SELL mirror
   if(c1 < amd.asianLow && h1 >= amd.asianLow - atr * 0.6
      && (htf.bias == HTF_BEAR || htf.bias == HTF_NEUTRAL)){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = MathMax(amd.asianLow + 0.3 * atr, mid);
      s.tpPrice = s.entryRef - 2.4 * (s.slPrice - s.entryRef);
      s.score   = 72.0;
      s.reason  = "AMD_CONT bear:asiaLo retest";
      return s;
   }
   return s;
}

// =================================================================
// 3. JUDAS SWING (false move at London/NY open, reverse into range)
// =================================================================
SNXSSignal NXS_Strat_JudasSwing(SNXSSweepExt &sw, SNXSAMD &amd){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "JUDAS_SWING";
   if(!InpUseStrat_Judas) return s;
   if(!(_inst_inLondonOpen() || _inst_inNYOpen())) return s;
   if(amd.asianHigh <= 0 || amd.asianLow <= 0) return s;

   double atr = _inst_atr();
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double l1 = iLow  (g_sym, NXS_EffTF(), 1);
   double h1 = iHigh (g_sym, NXS_EffTF(), 1);

   // BUY: wick below asianLow / PDL / EQL then close back inside + chochUp
   bool wickedDown = (sw.sweptAsiaLow || sw.sweptPDL || sw.sweptEQL || l1 < amd.asianLow);
   if(wickedDown && c1 > amd.asianLow && g_struct.chochUp){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = MathMin(l1, amd.asianLow) - 0.4 * atr;
      s.tpPrice = MathMax(amd.asianHigh, s.entryRef + 2.5 * (s.entryRef - s.slPrice));
      s.score   = 75.0;
      s.reason  = "JUDAS bull:fake low+MSS";
      return s;
   }
   // SELL mirror
   bool wickedUp = (sw.sweptAsiaHigh || sw.sweptPDH || sw.sweptEQH || h1 > amd.asianHigh);
   if(wickedUp && c1 < amd.asianHigh && g_struct.chochDown){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = MathMax(h1, amd.asianHigh) + 0.4 * atr;
      s.tpPrice = MathMin(amd.asianLow, s.entryRef - 2.5 * (s.slPrice - s.entryRef));
      s.score   = 75.0;
      s.reason  = "JUDAS bear:fake high+MSS";
      return s;
   }
   return s;
}

// =================================================================
// 4. LONDON REVERSAL
// =================================================================
SNXSSignal NXS_Strat_LondonReversal(SNXSSweepExt &sw, SNXSAMD &amd){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "LDN_REVERSAL";
   if(!InpUseStrat_LdnReversal) return s;
   if(g_session != SESS_LONDON && g_session != SESS_OVERLAP) return s;
   double atr = _inst_atr();
   double c1 = iClose(g_sym, NXS_EffTF(), 1);

   // SELL: London sweep above AsiaHigh/PDH/EQH + close below + chochDown
   if((sw.sweptAsiaHigh || sw.sweptPDH || sw.sweptEQH) && c1 < sw.refHigh && g_struct.chochDown){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = sw.refHigh + 0.5 * atr;
      double tgt = (amd.asianLow > 0) ? amd.asianLow : (s.entryRef - 2.5 * (s.slPrice - s.entryRef));
      s.tpPrice = MathMin(tgt, s.entryRef - 2.0 * (s.slPrice - s.entryRef));
      s.score   = 76.0;
      s.reason  = "LDN-REV bear:sweepHi+MSS";
      return s;
   }
   // BUY mirror
   if((sw.sweptAsiaLow || sw.sweptPDL || sw.sweptEQL) && c1 > sw.refLow && g_struct.chochUp){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = sw.refLow - 0.5 * atr;
      double tgt = (amd.asianHigh > 0) ? amd.asianHigh : (s.entryRef + 2.5 * (s.entryRef - s.slPrice));
      s.tpPrice = MathMax(tgt, s.entryRef + 2.0 * (s.entryRef - s.slPrice));
      s.score   = 76.0;
      s.reason  = "LDN-REV bull:sweepLo+MSS";
      return s;
   }
   return s;
}

// 17/07 notte - da audit esterno canonico: la sessione di Londra usava un
// offset GMT fisso (6-12) tutto l'anno, che in estate (BST, UTC+1) sbaglia
// la finestra di un'ora, e veniva aggregata dalle barre del TF strategia
// (su H4/D1 una singola barra non rappresenta la finestra precisa). Ora:
// (1) calcolo reale del BST (Europe/London: dall'01:00 UTC dell'ultima
// domenica di marzo all'01:00 UTC dell'ultima domenica di ottobre - la
// stessa regola che UK e USA NON condividono, motivo per cui un offset
// fisso annuale e' strutturalmente sbagliato in certe settimane); (2)
// aggregazione da M5, indipendente dal timeframe della strategia.
datetime NXS_LastSundayUTC(int year, int month){
   // Chiamata solo con month=3 o month=10, entrambi hanno 31 giorni - day=31 sempre valido.
   MqlDateTime mt; mt.year = year; mt.mon = month; mt.day = 31; mt.hour = 1; mt.min = 0; mt.sec = 0;
   datetime t = StructToTime(mt);
   MqlDateTime norm; TimeToStruct(t, norm);
   return t - norm.day_of_week * 86400;   // day_of_week: 0=domenica
}
bool NXS_IsLondonBST(datetime utcTime){
   MqlDateTime mt; TimeToStruct(utcTime, mt);
   datetime bstStart = NXS_LastSundayUTC(mt.year, 3);
   datetime bstEnd   = NXS_LastSundayUTC(mt.year, 10);
   return (utcTime >= bstStart && utcTime < bstEnd);
}

// =================================================================
// 5. NY REVERSAL  (mirror of LdnReversal, NY hours only, considers London HoD/LoD)
// =================================================================
SNXSSignal NXS_Strat_NYReversal(SNXSSweepExt &sw){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "NY_REVERSAL";
   if(!InpUseStrat_NYReversal) return s;
   if(g_session != SESS_NY && g_session != SESS_OVERLAP) return s;
   double atr = _inst_atr();
   double c1 = iClose(g_sym, NXS_EffTF(), 1);

   // Finestra Londra 08:00-12:00 Europe/London, tradotta in ore UTC reali
   // (07-11 UTC durante BST, 08-12 UTC durante GMT). Aggregata da M5 sulla
   // giornata corrente, non dalle barre del TF strategia.
   datetime nowUtc = (datetime)((long)TimeCurrent() - (long)InpServerGMTOffset * 3600);
   MqlDateTime nowMt; TimeToStruct(nowUtc, nowMt);
   bool bst = NXS_IsLondonBST(nowUtc);
   int londonStartH = bst ? 7 : 8, londonEndH = bst ? 11 : 12;

   double londonHi = -DBL_MAX, londonLo = DBL_MAX;
   for(int i = 1; i <= 300; i++){   // M5, ~25h di lookback: copre l'intera giornata corrente
      datetime t = iTime(g_sym, PERIOD_M5, i);
      if(t == 0) break;
      datetime tUtc = (datetime)((long)t - (long)InpServerGMTOffset * 3600);
      MqlDateTime mt; TimeToStruct(tUtc, mt);
      if(mt.year != nowMt.year || mt.mon != nowMt.mon || mt.day != nowMt.day) continue;   // solo la sessione londinese di OGGI
      if(mt.hour >= londonStartH && mt.hour < londonEndH){
         londonHi = MathMax(londonHi, iHigh(g_sym, PERIOD_M5, i));
         londonLo = MathMin(londonLo, iLow (g_sym, PERIOD_M5, i));
      }
   }
   if(londonHi == -DBL_MAX || londonLo == DBL_MAX) return s;

   // SELL: NY sweep > londonHi + close back + chochDown
   double h1 = iHigh(g_sym, NXS_EffTF(), 1);
   double l1 = iLow (g_sym, NXS_EffTF(), 1);
   if(h1 > londonHi && c1 < londonHi && g_struct.chochDown){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = h1 + 0.5 * atr;
      s.tpPrice = MathMin(londonLo, s.entryRef - 2.5 * (s.slPrice - s.entryRef));
      s.score   = 75.0;
      s.reason  = "NY-REV bear:sweep LDN-Hi";
      return s;
   }
   // BUY mirror
   if(l1 < londonLo && c1 > londonLo && g_struct.chochUp){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = l1 - 0.5 * atr;
      s.tpPrice = MathMax(londonHi, s.entryRef + 2.5 * (s.entryRef - s.slPrice));
      s.score   = 75.0;
      s.reason  = "NY-REV bull:sweep LDN-Lo";
      return s;
   }
   return s;
}

// =================================================================
// 6. WEEKLY RANGE EXPANSION
// =================================================================
// 17/07 notte - da audit esterno canonico: la versione attuale e' gia' piu'
// vicina al "Modello B" (weekly continuation expansion) proposto dall'audit,
// completata invece di ricostruita da zero. Due correzioni: (1) il corpo H4
// veniva confrontato con l'ATR D1 (g_atr = ATR del TF di profilo di questa
// strategia = D1) - unita' diverse, soglia quasi irraggiungibile, era IL
// bug dominante dietro gli zero-trade. Ora usa un ATR H4 dedicato. (2)
// mancava del tutto la verifica che il displacement rompa uno swing H4
// (BOS) - senza quella non e' "displacement che produce continuation", e'
// solo "una candela H4 abbastanza grande".
// 26/08 - macchina a stati a due tappe (proposta esplicita dell'utente
// dopo la scoperta RISK_SIZE: lo stop nativo 1.5xATR(D1) dal livello
// settimanale e' spesso $30-45, che al lotto minimo su un conto piccolo
// supera l'8% e l'ordine viene rifiutato prima ancora dello spread).
// Verificato in Python (weekly_exp_ltf_entry_structural_trail_26-08.py,
// ricetta CON filtro CHOCH): nativo PF1.18 n=16 rischio mediano $38 ->
// ingresso raffinato + BE/trailing PF1.64 n=15 rischio mediano $3.51,
// rifiuti RISK_SIZE a conto $500 dal 37.5% al 6.7%. Campione ancora
// piccolo (n=15-16), prima conferma live ancora da avere.
//
// STAGE 1 (IDLE): il trigger H4/settimanale resta IDENTICO a prima -
// non e' il segnale a cambiare, e' cosa succede DOPO che scatta.
// STAGE 2 (WAITING_LTF): invece di entrare subito con lo stop nativo
// largo, aspetta fino a NXS_WEXP_MAX_WAIT_M15 barre M15 una vera
// candela di reazione (stessa logica di NXS_HasPriceReaction: pin bar
// o chiusura direzionale) DENTRO la finestra aperta dal trigger H4, e
// usa il suo estremo (+-0.2xATR M15) come stop - molto piu' stretto.
// Target: lasciato come "tetto di sicurezza" lontano (stesso calcolo
// Fibonacci di prima) - la gestione vera del profitto e' delegata a
// NXS_WeeklyExpManage() (breakeven 1.0R + trailing strutturale 1.5R,
// vedi NXS_WeeklyExpManage.mqh), che di solito chiude prima del tetto.
enum ENUM_NXS_WEXP_STATE { WEXP_IDLE = 0, WEXP_WAITING_LTF };
#define NXS_WEXP_MAX_WAIT_M15 8
struct SNXSWExpState {
   int      state;
   int      dir;             // +1 buy, -1 sell
   double   pwh, pwl;        // per il calcolo del target
   datetime armedAtH4Bar;    // barra H4 gia' valutata (evita ri-armare sullo stesso H4)
   int      barsWaited;
   datetime lastM15Bar;
};
SNXSWExpState g_wexpState;

SNXSSignal NXS_Strat_WeeklyRangeExp(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "WEEKLY_EXP";
   if(!InpUseStrat_WeeklyExp) return s;

   // ---- STAGE 2: in attesa della conferma M15 ----
   if(g_wexpState.state == WEXP_WAITING_LTF){
      datetime m15Bar1 = iTime(g_sym, PERIOD_M15, 1);
      if(m15Bar1 == g_wexpState.lastM15Bar) return s;   // nessuna nuova barra M15
      g_wexpState.lastM15Bar = m15Bar1;
      g_wexpState.barsWaited++;
      if(g_wexpState.barsWaited > NXS_WEXP_MAX_WAIT_M15){
         g_wexpState.state = WEXP_IDLE;
         return s;
      }
      double a15 = NXS_ATRv(PERIOD_M15, 1);
      if(a15 <= 0) return s;
      double o1 = iOpen (g_sym, PERIOD_M15, 1), c1 = iClose(g_sym, PERIOD_M15, 1);
      double h1 = iHigh (g_sym, PERIOD_M15, 1), l1 = iLow  (g_sym, PERIOD_M15, 1);
      double body = MathAbs(c1 - o1);
      if(body < a15 * 0.3) return s;
      int dir = g_wexpState.dir;
      double upWick = h1 - MathMax(o1, c1), dnWick = MathMin(o1, c1) - l1;
      double rng = MathMax(h1 - l1, _Point);
      bool reacted = false; double sl0 = 0;
      if(dir == 1){
         bool pin = (dnWick > body * 1.5 && dnWick > rng * 0.5);
         if(pin || c1 > o1){ reacted = true; sl0 = l1 - 0.2 * a15; }
      } else {
         bool pin = (upWick > body * 1.5 && upWick > rng * 0.5);
         if(pin || c1 < o1){ reacted = true; sl0 = h1 + 0.2 * a15; }
      }
      if(!reacted) return s;

      s.dir = (dir == 1) ? DIR_BUY : DIR_SELL;
      s.entryRef = (dir == 1) ? SymbolInfoDouble(g_sym, SYMBOL_ASK) : SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = sl0;
      double leg = g_wexpState.pwh - g_wexpState.pwl;
      if(dir == 1){
         double fib1272 = g_wexpState.pwh + 0.272 * leg;
         s.tpPrice = MathMax(MathMax(g_wexpState.pwh, fib1272), s.entryRef + 2.6 * (s.entryRef - s.slPrice));
         s.reason  = "WK-EXP bull:LTF-refined entry";
      } else {
         double fib1272 = g_wexpState.pwl - 0.272 * leg;
         s.tpPrice = MathMin(MathMin(g_wexpState.pwl, fib1272), s.entryRef - 2.6 * (s.slPrice - s.entryRef));
         s.reason  = "WK-EXP bear:LTF-refined entry";
      }
      s.score = 70.0;
      g_wexpState.state = WEXP_IDLE;   // one-shot
      return s;
   }

   // ---- STAGE 1: trigger H4/settimanale (logica invariata) ----
   double atr = _inst_atr();
   double pwh = iHigh(g_sym, PERIOD_W1, 1);
   double pwl = iLow (g_sym, PERIOD_W1, 1);
   double wOpen = iOpen(g_sym, PERIOD_W1, 0);
   if(pwh <= 0 || pwl <= 0 || wOpen <= 0) return s;
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);

   static int hAtrH4 = INVALID_HANDLE;
   if(hAtrH4 == INVALID_HANDLE) hAtrH4 = iATR(g_sym, InpTFHigh, 14);
   double atrH4Arr[]; double atrH4 = 0;
   if(hAtrH4 != INVALID_HANDLE) CopyBuffer(hAtrH4, 0, 1, 1, atrH4Arr);
   if(ArraySize(atrH4Arr) > 0) atrH4 = atrH4Arr[0];
   if(atrH4 <= 0) return s;

   double cH4 = iClose(g_sym, InpTFHigh, 1);
   double oH4 = iOpen (g_sym, InpTFHigh, 1);
   double bH4 = MathAbs(cH4 - oH4);
   if(bH4 < atrH4 * 0.8) return s;

   datetime h4Bar1 = iTime(g_sym, InpTFHigh, 1);
   if(h4Bar1 == g_wexpState.armedAtH4Bar) return s;   // questa barra H4 gia' valutata

   int hiIdxH4 = iHighest(g_sym, InpTFHigh, MODE_HIGH, 15, 2);
   int loIdxH4 = iLowest (g_sym, InpTFHigh, MODE_LOW,  15, 2);
   double swingHiH4 = hiIdxH4 >= 0 ? iHigh(g_sym, InpTFHigh, hiIdxH4) : 0;
   double swingLoH4 = loIdxH4 >= 0 ? iLow (g_sym, InpTFHigh, loIdxH4) : 0;
   bool bosUpH4   = (swingHiH4 > 0 && cH4 > swingHiH4);
   bool bosDownH4 = (swingLoH4 > 0 && cH4 < swingLoH4);

   double wMid = (pwh + pwl) * 0.5;
   // 27/08 - FIX: NON marcare la barra H4 come "valutata" qui. chochUp/
   // chochDown sono flag a cadenza M15 (NXS_ComputeStructureCore, resettati
   // ogni barra M15) - veri solo per la durata di UNA barra M15 dentro le
   // ~16 che compongono la barra H4. Segnare armedAtH4Bar incondizionatamente
   // al primo tick della barra H4 blocca tutti i tick successivi PRIMA che
   // il choch possa mai diventare vero durante quella barra H4 - risultato
   // (verificato su Tester MT5 a tick reali, 10 mesi): 0 trade. Va marcata
   // SOLO quando ci si arma davvero, cosi' si continua a ricontrollare a
   // ogni tick per tutta la durata della barra H4 (comportamento originale
   // pre-refactor), fino a intercettare il momento in cui il choch e' vero.

   if(bid < wMid && cH4 > oH4 && bosUpH4 && bid > wOpen && g_struct.chochUp){
      g_wexpState.state = WEXP_WAITING_LTF;
      g_wexpState.dir = 1;
      g_wexpState.pwh = pwh; g_wexpState.pwl = pwl;
      g_wexpState.barsWaited = 0;
      g_wexpState.lastM15Bar = iTime(g_sym, PERIOD_M15, 1);
      g_wexpState.armedAtH4Bar = h4Bar1;
      return s;
   }
   if(bid > wMid && cH4 < oH4 && bosDownH4 && bid < wOpen && g_struct.chochDown){
      g_wexpState.state = WEXP_WAITING_LTF;
      g_wexpState.dir = -1;
      g_wexpState.pwh = pwh; g_wexpState.pwl = pwl;
      g_wexpState.barsWaited = 0;
      g_wexpState.lastM15Bar = iTime(g_sym, PERIOD_M15, 1);
      g_wexpState.armedAtH4Bar = h4Bar1;
      return s;
   }
   return s;
}

// =================================================================
// 7. POWER OF THREE (PO3) — full ACC + MAN + DIST classifier entry
// =================================================================
SNXSSignal NXS_Strat_PO3(SNXSSweepExt &sw, SNXSAMD &amd){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "PO3";
   if(!InpUseStrat_PO3) return s;
   if(amd.asianHigh <= 0 || amd.asianLow <= 0) return s;
   // ACC = Asia range, MAN = sweep beyond range, DIST = displacement + continuation
   double atr = _inst_atr();
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double o1 = iOpen (g_sym, NXS_EffTF(), 1);
   double body = MathAbs(c1 - o1);
   if(body < atr * 0.6) return s;        // require distribution candle

   // BUY: accumulation defined + manipulation under (sweep asianLow) + reclaim + bullish dist
   if(sw.sweptAsiaLow && c1 > amd.asianLow && c1 > o1 && g_struct.chochUp){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = sw.refLow - 0.4 * atr;
      s.tpPrice = MathMax(amd.asianHigh, s.entryRef + 2.6 * (s.entryRef - s.slPrice));
      s.score   = 76.0;
      s.reason  = "PO3 bull:ACC-MAN-DIST";
      return s;
   }
   if(sw.sweptAsiaHigh && c1 < amd.asianHigh && c1 < o1 && g_struct.chochDown){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = sw.refHigh + 0.4 * atr;
      s.tpPrice = MathMin(amd.asianLow, s.entryRef - 2.6 * (s.slPrice - s.entryRef));
      s.score   = 76.0;
      s.reason  = "PO3 bear:ACC-MAN-DIST";
      return s;
   }
   return s;
}

// =================================================================
// 8. LIQUIDITY VOID CONTINUATION
// =================================================================
SNXSSignal NXS_Strat_LiquidityVoid(SNXSHTF &htf){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "LIQ_VOID";
   if(!InpUseStrat_LiqVoid) return s;
   double atr = _inst_atr();

   // 17/07 notte - geometria FVG corretta, da audit esterno canonico
   // (fonti ICT/SMC: bullish FVG = Low(candela3) > High(candela1), zona fra
   // High[candela1]-Low[candela3]). La versione precedente confrontava
   // high(displacement) con high(displacement+2) - due high, non un vero
   // gap - poteva classificare come void un normale nuovo massimo.
   // Candela 1 (piu' vecchia) = dispIdx+1, candela 2 (displacement) =
   // dispIdx, candela 3 (piu' recente, gia' chiusa) = dispIdx-1.
   int dispIdx = _inst_displacementBar(+1, 12, 1.2);
   if(dispIdx > 1 && htf.bias == HTF_BULL){
      double c1High = iHigh(g_sym, NXS_EffTF(), dispIdx + 1);
      double c3Low  = iLow (g_sym, NXS_EffTF(), dispIdx - 1);
      double voidLo = c1High;
      double voidHi = c3Low;
      if(voidHi > voidLo + atr * 0.3){
         double ce = (voidHi + voidLo) * 0.5;     // consequent encroachment 50%
         double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
         double c1 = iClose(g_sym, NXS_EffTF(), 1);
         double o1 = iOpen (g_sym, NXS_EffTF(), 1);
         if(bid <= ce && bid >= voidLo && c1 > o1){
            s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
            s.slPrice = voidLo - 0.4 * atr;
            s.tpPrice = s.entryRef + 2.5 * (s.entryRef - s.slPrice);
            s.score   = 73.0;
            s.reason  = "LIQ-VOID bull:CE retest";
            return s;
         }
      }
   }
   // Bearish: High(candela3) < Low(candela1), zona fra High[candela3]-Low[candela1].
   int dispIdxB = _inst_displacementBar(-1, 12, 1.2);
   if(dispIdxB > 1 && htf.bias == HTF_BEAR){
      double c1Low  = iLow (g_sym, NXS_EffTF(), dispIdxB + 1);
      double c3High = iHigh(g_sym, NXS_EffTF(), dispIdxB - 1);
      double voidLo = c3High;
      double voidHi = c1Low;
      if(voidHi > voidLo + atr * 0.3){
         double ce = (voidHi + voidLo) * 0.5;
         double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
         double c1 = iClose(g_sym, NXS_EffTF(), 1);
         double o1 = iOpen (g_sym, NXS_EffTF(), 1);
         if(bid >= ce && bid <= voidHi && c1 < o1){
            s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
            s.slPrice = voidHi + 0.4 * atr;
            s.tpPrice = s.entryRef - 2.5 * (s.slPrice - s.entryRef);
            s.score   = 73.0;
            s.reason  = "LIQ-VOID bear:CE retest";
            return s;
         }
      }
   }
   return s;
}

// =================================================================
// 9. DISPLACEMENT REBALANCE
// =================================================================
// 17/07 notte - CE (Consequent Encroachment) corretto, da audit esterno
// canonico: la versione precedente usava il 50% dell'INTERA candela di
// displacement come "CE" - non e' il rebalance di un'inefficienza, e' un
// retracement al 50% della candela impulso. Un vero rebalance ICT/SMC
// torna al 50% del FVG lasciato dal displacement, non della candela
// stessa. Ora usa la stessa geometria FVG a 3 candele gia' corretta per
// LIQ_VOID stanotte (bullish: Low(candela3) > High(candela1)).
SNXSSignal NXS_Strat_DisplacementRebalance(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "DISP_REBAL";
   if(!InpUseStrat_DispRebal) return s;
   double atr = _inst_atr();
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double o1 = iOpen (g_sym, NXS_EffTF(), 1);

   // BUY: displacement bullish (body > 1.3 ATR) + FVG a 3 candele + retest del CE + reazione.
   int dispIdx = _inst_displacementBar(+1, 8, 1.3);
   if(dispIdx > 1){
      double c1High = iHigh(g_sym, NXS_EffTF(), dispIdx + 1);
      double c3Low  = iLow (g_sym, NXS_EffTF(), dispIdx - 1);
      if(c3Low > c1High + atr * 0.1){
         double fvgLo = c1High, fvgHi = c3Low, ce = (fvgLo + fvgHi) * 0.5;
         if(bid >= fvgLo && bid <= ce + atr * 0.15 && c1 > o1){
            s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
            s.slPrice = fvgLo - 0.3 * atr;
            s.tpPrice = MathMax(fvgHi + 0.8 * (fvgHi - fvgLo), s.entryRef + 2.4 * (s.entryRef - s.slPrice));
            s.score   = 72.0;
            s.reason  = "DISP-REBAL bull:fvg_CE";
            return s;
         }
      }
   }
   int dispIdxB = _inst_displacementBar(-1, 8, 1.3);
   if(dispIdxB > 1){
      double c1Low  = iLow (g_sym, NXS_EffTF(), dispIdxB + 1);
      double c3High = iHigh(g_sym, NXS_EffTF(), dispIdxB - 1);
      if(c1Low > c3High + atr * 0.1){
         double fvgLo = c3High, fvgHi = c1Low, ce = (fvgLo + fvgHi) * 0.5;
         if(bid <= fvgHi && bid >= ce - atr * 0.15 && c1 < o1){
            s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
            s.slPrice = fvgHi + 0.3 * atr;
            s.tpPrice = MathMin(fvgLo - 0.8 * (fvgHi - fvgLo), s.entryRef - 2.4 * (s.slPrice - s.entryRef));
            s.score   = 72.0;
            s.reason  = "DISP-REBAL bear:fvg_CE";
            return s;
         }
      }
   }
   return s;
}

// =================================================================
// 10. RANGE FADE (v2.0.8) — mean revert sui range stretti
// =================================================================
// 17/07 notte - qualificazione del range resa persistente, da audit esterno
// canonico: prima bastava l'ultima lettura di ADX (ritardato, puo' essere
// basso anche subito dopo un trend) su una finestra di 40 barre presa per
// buona senza verificare che fosse DAVVERO stata laterale. Ora un range
// "CONFIRMED" richiede, su tutta la finestra: persistenza ADX (>=70% delle
// barre sotto soglia), ampiezza stabile fra prima e seconda meta' della
// finestra, almeno 2 contatti per lato separati da un numero minimo di
// barre, occupazione bilanciata del prezzo (30-70% sopra il midpoint),
// nessun breakout accettato nelle ultime M barre. Calcolo bar-gated (una
// volta per barra chiusa). Entry solo su barra chiusa 1, niente piu' bid
// live per decidere la vicinanza al bordo.
int    InpRangeFade_Lookback       = 40;
double InpRangeFade_ADXPersistPct  = 70.0;
double InpRangeFade_MaxWidthDrift  = 0.35;   // tolleranza fra meta' prima e seconda del range (%)
int    InpRangeFade_MinTouches     = 2;
int    InpRangeFade_MinBarsBetweenTouches = 3;
int    InpRangeFade_NoBreakoutBars = 5;

struct SNXSRangeFadeState {
   datetime lastBarTime;
   bool     confirmed;
   double   rngHi, rngLo, rngMid;
};
SNXSRangeFadeState g_rangeFadeState;

SNXSSignal NXS_Strat_RangeFade(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "RANGE_FADE";
   if(!InpUseStrat_RangeFade) return s;
   double atr = _inst_atr();
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   datetime curBar0 = iTime(g_sym, tf, 0);

   if(g_rangeFadeState.lastBarTime != curBar0){
      g_rangeFadeState.lastBarTime = curBar0;
      g_rangeFadeState.confirmed = false;
      int N = InpRangeFade_Lookback;

      // (1) Persistenza ADX sulla finestra (non solo l'ultima lettura).
      double adxArr[]; ArraySetAsSeries(adxArr, true);
      if(CopyBuffer(g_hADX, 0, 1, N, adxArr) < N) return s;
      int belowCount = 0; double adxSum = 0;
      for(int i = 0; i < N; i++){ if(adxArr[i] < 20.0) belowCount++; adxSum += adxArr[i]; }
      double adxPersistPct = 100.0 * belowCount / N;
      if(adxPersistPct < InpRangeFade_ADXPersistPct) return s;

      // Range extremes sulla finestra intera.
      int hiIdx = iHighest(g_sym, tf, MODE_HIGH, N, 2);
      int loIdx = iLowest (g_sym, tf, MODE_LOW,  N, 2);
      if(hiIdx < 0 || loIdx < 0) return s;
      double rngHi = iHigh(g_sym, tf, hiIdx);
      double rngLo = iLow (g_sym, tf, loIdx);
      double rngSize = rngHi - rngLo;
      if(rngSize < atr * 1.5) return s;

      // (2) Stabilita' ampiezza: prima meta' vs seconda meta' della finestra.
      int half = N / 2;
      int hiIdxA = iHighest(g_sym, tf, MODE_HIGH, half, 2 + half);
      int loIdxA = iLowest (g_sym, tf, MODE_LOW,  half, 2 + half);
      int hiIdxB = iHighest(g_sym, tf, MODE_HIGH, half, 2);
      int loIdxB = iLowest (g_sym, tf, MODE_LOW,  half, 2);
      if(hiIdxA < 0 || loIdxA < 0 || hiIdxB < 0 || loIdxB < 0) return s;
      double widthA = iHigh(g_sym, tf, hiIdxA) - iLow(g_sym, tf, loIdxA);
      double widthB = iHigh(g_sym, tf, hiIdxB) - iLow(g_sym, tf, loIdxB);
      double maxW = MathMax(widthA, widthB);
      if(maxW <= 0 || MathAbs(widthA - widthB) / maxW > InpRangeFade_MaxWidthDrift) return s;

      // (3) Contatti minimi per lato, separati da un numero minimo di barre.
      double edgeBand = atr * 0.4;
      int upperTouches = 0, lowerTouches = 0, lastUpperTouch = -1000, lastLowerTouch = -1000;
      double sumAboveMid = 0; int countAboveMid = 0;
      double rngMid = (rngHi + rngLo) * 0.5;
      for(int i = 1; i <= N; i++){
         double hh = iHigh(g_sym, tf, i), ll = iLow(g_sym, tf, i), cc = iClose(g_sym, tf, i);
         if(hh >= rngHi - edgeBand && (i - lastUpperTouch) >= InpRangeFade_MinBarsBetweenTouches){
            upperTouches++; lastUpperTouch = i;
         }
         if(ll <= rngLo + edgeBand && (i - lastLowerTouch) >= InpRangeFade_MinBarsBetweenTouches){
            lowerTouches++; lastLowerTouch = i;
         }
         if(cc > rngMid) countAboveMid++;
      }
      if(upperTouches < InpRangeFade_MinTouches || lowerTouches < InpRangeFade_MinTouches) return s;

      // (4) Occupazione bilanciata: chiusure sopra il midpoint fra 30% e 70%.
      double aboveMidPct = 100.0 * countAboveMid / N;
      if(aboveMidPct < 30.0 || aboveMidPct > 70.0) return s;

      // (5) Nessun breakout accettato nelle ultime M barre.
      double breakBuffer = atr * 0.3;
      for(int i = 1; i <= InpRangeFade_NoBreakoutBars; i++){
         double cc = iClose(g_sym, tf, i);
         if(cc > rngHi + breakBuffer || cc < rngLo - breakBuffer) return s;
      }

      g_rangeFadeState.confirmed = true;
      g_rangeFadeState.rngHi = rngHi; g_rangeFadeState.rngLo = rngLo; g_rangeFadeState.rngMid = rngMid;
   }
   if(!g_rangeFadeState.confirmed) return s;

   // Entry solo su barra chiusa 1 - niente bid live per la vicinanza al bordo.
   double rngHi = g_rangeFadeState.rngHi, rngLo = g_rangeFadeState.rngLo, rngMid = g_rangeFadeState.rngMid;
   double c1 = iClose(g_sym, tf, 1), o1 = iOpen(g_sym, tf, 1);
   double h1 = iHigh (g_sym, tf, 1), l1 = iLow (g_sym, tf, 1);
   double body = MathAbs(c1 - o1);
   if(body < atr * 0.25) return s;

   if(l1 <= rngLo + 0.4 * atr && c1 > o1 && c1 > rngLo){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = MathMin(l1, rngLo) - 0.4 * atr;
      s.tpPrice = MathMin(rngMid, s.entryRef + 2.0 * (s.entryRef - s.slPrice));
      s.score   = 68.0;
      s.reason  = "RANGE_FADE bull:lowReject";
      return s;
   }
   if(h1 >= rngHi - 0.4 * atr && c1 < o1 && c1 < rngHi){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = MathMax(h1, rngHi) + 0.4 * atr;
      s.tpPrice = MathMax(rngMid, s.entryRef - 2.0 * (s.slPrice - s.entryRef));
      s.score   = 68.0;
      s.reason  = "RANGE_FADE bear:hiReject";
      return s;
   }
   return s;
}

// =================================================================
// Asset Class detection (v2.0.8) — uses ENUM_NXS_ASSET_CLASS from NXS_SymbolProfile.mqh
// InpAssetClass input legend (see NXS_Inputs.mqh):
//   0 = AUTO (detect by symbol substring)
//   1 = FOREX  (maps to ASSET_FOREX_MAJOR)
//   2 = METAL  (maps to ASSET_METAL)
//   3 = INDEX  (maps to ASSET_INDEX)
//   4 = CRYPTO (maps to ASSET_CRYPTO)
// =================================================================
ENUM_NXS_ASSET_CLASS NXS_DetectAssetClass(){
   if(InpAssetClass > 0){
      switch(InpAssetClass){
         case 1: return ASSET_FOREX_MAJOR;
         case 2: return ASSET_METAL;
         case 3: return ASSET_INDEX;
         case 4: return ASSET_CRYPTO;
         default: break;
      }
   }
   string up = g_sym; StringToUpper(up);
   if(StringFind(up, "BTC") >= 0 || StringFind(up, "ETH") >= 0 ||
      StringFind(up, "XRP") >= 0 || StringFind(up, "SOL") >= 0 ||
      StringFind(up, "DOGE") >= 0) return ASSET_CRYPTO;
   if(StringFind(up, "XAU") >= 0 || StringFind(up, "XAG") >= 0 ||
      StringFind(up, "GOLD") >= 0 || StringFind(up, "SILVER") >= 0) return ASSET_METAL;
   if(StringFind(up, "US30") >= 0 || StringFind(up, "NAS") >= 0 ||
      StringFind(up, "SPX") >= 0 || StringFind(up, "DAX") >= 0 ||
      StringFind(up, "JPN") >= 0) return ASSET_INDEX;
   return ASSET_FOREX_MAJOR;
}

bool NXS_IsCryptoWeekendOK(){
   if(NXS_DetectAssetClass() != ASSET_CRYPTO) return true;   // not crypto, always OK
   if(InpCryptoWeekendMode) return true;                     // explicit crypto weekend ok
   MqlDateTime mt; TimeToStruct(TimeCurrent(), mt);
   return (mt.day_of_week >= 1 && mt.day_of_week <= 5);
}

double NXS_SpreadCapATRPct(){
   // Override spread cap for crypto
   if(NXS_DetectAssetClass() == ASSET_CRYPTO) return InpCryptoSpreadCapATRPct;
   return InpMaxSpreadAtrPct;
}

#endif // __NXS_STRATEGIES_INST_MQH__