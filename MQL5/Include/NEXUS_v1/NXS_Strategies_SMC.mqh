//+------------------------------------------------------------------+
//|  NXS_Strategies_SMC.mqh                                           |
//|  Phase 4 - 10 SMC/ICT strategies                                  |
//|                                                                   |
//|  Outputs: SNXSSignal {dir, score, stratName, reason, slPrice,     |
//|                       tpPrice, entryRef, strat=STRAT_STRUCT_REACT}|
//+------------------------------------------------------------------+
#ifndef __NXS_STRATEGIES_SMC_MQH__
#define __NXS_STRATEGIES_SMC_MQH__

// ----- helpers --------------------------------------------------------
double _smc_atr(){ return g_atr > 0 ? g_atr : 1.0 * g_point; }
double _smc_sl(double entry, ENUM_NXS_DIR dir, double atrMult){
   double atr = _smc_atr();
   return (dir == DIR_BUY) ? entry - atrMult * atr : entry + atrMult * atr;
}
double _smc_tp(double entry, ENUM_NXS_DIR dir, double atrMult){
   double atr = _smc_atr();
   return (dir == DIR_BUY) ? entry + atrMult * atr : entry - atrMult * atr;
}

// === 1. TURTLE SOUP (v2.0.6 — richiede body[1] >= 0.4 ATR per evitare noise) ==
// Sweep previous H/L + close back inside + reversal candle con body forte
SNXSSignal NXS_Strat_TurtleSoup(SNXSSweepExt &sw){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "TURTLE_SOUP";
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double o1 = iOpen (g_sym, NXS_EffTF(), 1);
   double atr = _smc_atr();
   double bodyAbs = MathAbs(c1 - o1);
   if(bodyAbs < atr * 0.4) return s;        // v2.0.6: rejection candle must have strong body
   if(sw.sweptPDH || sw.sweptEQH){
      if(c1 < o1 && c1 < sw.refHigh){
         s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
         s.slPrice = sw.refHigh + 0.5 * atr;
         s.tpPrice = s.entryRef - 2.0 * (s.slPrice - s.entryRef);
         s.score   = 72.0;
         s.reason  = "TS:sweptHi+closeBack+body";
         return s;
      }
   }
   if(sw.sweptPDL || sw.sweptEQL){
      if(c1 > o1 && c1 > sw.refLow){
         s.dir = DIR_BUY;  s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
         s.slPrice = sw.refLow - 0.5 * atr;
         s.tpPrice = s.entryRef + 2.0 * (s.entryRef - s.slPrice);
         s.score   = 72.0;
         s.reason  = "TS:sweptLo+closeBack+body";
         return s;
      }
   }
   return s;
}

// === 1b. SWING FALSE-BREAK (24/08 — pivot di swing maggiore) ================
// Spunto da script TradingView "Bjorgum Key Levels" condiviso dall'utente
// (vedi vault "NEXUS EA - Idee da Script TradingView Esterni (17-08)").
// Stesso concetto sweep+rientro di TURTLE_SOUP sopra, ma con un ancoraggio
// MAI provato prima: pivot di swing MAGGIORE (left=20/right=15 barre,
// confermato solo 15 barre dopo essersi formato - nessun lookahead, stesso
// principio del choch_int interno ma finestra piu' larga) invece dei
// livelli intraday/sessione (PDH/PDL/Asia) usati da TURTLE_SOUP/LIQ_SWEEP.
// Zona larga min(prezzo*2%, 0.5xATR) intorno al pivot.
//
// Validato in Python su 1h con verifica due-meta'-storia (nessuna meta'
// negativa): retail PF 1.14->1.46, ECN PF 1.42->1.74 (234 trade grezzi
// nel campione di validazione). SL/TP: profilo ATR standard via
// NXS_DefaultSLTP (vedi NXS_Profile_Get "SWING_FALSEBREAK": 1.5/4.0xATR,
// gli stessi usati nel backtest Python) - non un anchoring strutturale
// come TURTLE_SOUP, qui lo stop e' un multiplo ATR fisso.
//
// GAP NOTO: il filtro di regime (Efficiency Ratio, lookback lungo) usato
// nella validazione Python NON e' ancora portato in MQL5 come gate live -
// stesso gap dell'intero portafoglio SAR/MACD/LONDON_BO/FVG_CONT (vedi
// vault "NEXUS EA - Filtro di Regime e Portafoglio 5 Strategie 16-08").
// Senza quel filtro il comportamento live puo' differire da quello
// validato, in particolare nei mercati laterali dove la ricerca prevede
// che la strategia perda edge.
#define NXS_SFB_LEFT        20
#define NXS_SFB_RIGHT       15
#define NXS_SFB_MAXLOOKBACK 300

bool _sfb_isPivotHigh(int m){
   double h = iHigh(g_sym, NXS_EffTF(), m);
   if(h <= 0) return false;
   for(int j = m - NXS_SFB_RIGHT; j <= m + NXS_SFB_LEFT; j++){
      if(j == m) continue;
      double hj = iHigh(g_sym, NXS_EffTF(), j);
      if(hj <= 0) return false;
      if(hj > h) return false;
   }
   return true;
}
bool _sfb_isPivotLow(int m){
   double l = iLow(g_sym, NXS_EffTF(), m);
   if(l <= 0) return false;
   for(int j = m - NXS_SFB_RIGHT; j <= m + NXS_SFB_LEFT; j++){
      if(j == m) continue;
      double lj = iLow(g_sym, NXS_EffTF(), j);
      if(lj <= 0) return false;
      if(lj < l) return false;
   }
   return true;
}
// Pivot CONFERMATO piu' recente (il primo trovato scendendo da RIGHT+1 -
// stesso "last_ph/last_pl" del find_pivots Python, ma calcolato al volo
// invece che precomputato su tutto l'array, senza cache tra i tick).
double _sfb_lastPivotHigh(){
   for(int m = NXS_SFB_RIGHT + 1; m <= NXS_SFB_MAXLOOKBACK; m++)
      if(_sfb_isPivotHigh(m)) return iHigh(g_sym, NXS_EffTF(), m);
   return 0.0;
}
double _sfb_lastPivotLow(){
   for(int m = NXS_SFB_RIGHT + 1; m <= NXS_SFB_MAXLOOKBACK; m++)
      if(_sfb_isPivotLow(m)) return iLow(g_sym, NXS_EffTF(), m);
   return 0.0;
}

SNXSSignal NXS_Strat_SwingFalseBreak(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "SWING_FALSEBREAK";
   if(!InpStrat_SwingFalseBreak || !NXS_SelectorAllows(41)) return s;
   double atr = _smc_atr();
   double c1  = iClose(g_sym, NXS_EffTF(), 1);
   double o1  = iOpen (g_sym, NXS_EffTF(), 1);
   double band = MathMin(c1 * 0.02, 0.5 * atr);

   // Sweep ribassista risolto: il pivot low e' stato rotto nelle ultime 3
   // barre chiuse ma la barra corrente chiude sopra la zona (rientro).
   double pl = _sfb_lastPivotLow();
   if(pl > 0){
      double zoneBottom = pl - band;
      bool swept = false;
      for(int k = 1; k <= 3; k++){
         if(iLow(g_sym, NXS_EffTF(), k) < zoneBottom){ swept = true; break; }
      }
      if(swept && c1 > zoneBottom && c1 > o1){
         s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
         s.score = 70.0; s.reason = "SFB:sweptPivotLow+closeBack";
         NXS_DefaultSLTP(s);
         return s;
      }
   }
   // Speculare: sweep rialzista del pivot high, rientro sotto zona.
   double ph = _sfb_lastPivotHigh();
   if(ph > 0){
      double zoneTop = ph + band;
      bool swept = false;
      for(int k = 1; k <= 3; k++){
         if(iHigh(g_sym, NXS_EffTF(), k) > zoneTop){ swept = true; break; }
      }
      if(swept && c1 < zoneTop && c1 < o1){
         s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
         s.score = 70.0; s.reason = "SFB:sweptPivotHigh+closeBack";
         NXS_DefaultSLTP(s);
         return s;
      }
   }
   return s;
}

// === 2. IFVG REVERSAL (v2.0.3 — richiede MSS opposto + reaction candle) =====
SNXSSignal NXS_Strat_IFVG_Reversal(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_FVG_CONT; s.stratName = "IFVG";
   // AUDITPATCH: an FVG is a 3-candle imbalance. Use candle 4 and candle 2
   // around candle 3; candle 1 is then free to invalidate/reject the zone.
   double h2 = iHigh(g_sym, NXS_EffTF(), 2), l2 = iLow(g_sym, NXS_EffTF(), 2);
   double h4 = iHigh(g_sym, NXS_EffTF(), 4), l4 = iLow(g_sym, NXS_EffTF(), 4);
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double o1 = iOpen (g_sym, NXS_EffTF(), 1);
   double atr = _smc_atr();
   bool reactionBear = (c1 < o1) && (MathAbs(c1-o1) > atr * 0.3);
   bool reactionBull = (c1 > o1) && (MathAbs(c1-o1) > atr * 0.3);
   // Bullish FVG [h4..l2] invalidated DOWN.
   if(l2 > h4 + atr * 0.2 && c1 < h4 && reactionBear && g_struct.chochDown){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = l2 + 0.5 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_SELL, 2.4);
      s.score = 73.0; s.reason = "IFVG bull→bear +MSS";
      return s;
   }
   // Bearish FVG [h2..l4] invalidated UP.
   if(h2 < l4 - atr * 0.2 && c1 > l4 && reactionBull && g_struct.chochUp){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = h2 - 0.5 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_BUY, 2.4);
      s.score = 73.0; s.reason = "IFVG bear→bull +MSS";
      return s;
   }
   return s;
}

// === 3. FVG MITIGATION (v2.0.3 — solo retest mature + rejection) ===========
// Distingue FVG appena formato (zona "fresh") da FVG già mitigato (zona "tested").
// Entry SOLO quando il prezzo torna in zona FVG vecchia (bars 5-7) e produce
// una candela di rejection (body forte + close in direzione attesa).
SNXSSignal NXS_Strat_FVG_Mitigation(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_FVG_CONT; s.stratName = "FVG_MIT";
   double h2 = iHigh(g_sym, NXS_EffTF(), 5), l2 = iLow(g_sym, NXS_EffTF(), 5);
   double h0 = iHigh(g_sym, NXS_EffTF(), 7), l0 = iLow(g_sym, NXS_EffTF(), 7);
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double atr = _smc_atr();
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double o1 = iOpen (g_sym, NXS_EffTF(), 1);
   double bodyAbs = MathAbs(c1 - o1);
   bool rejectionBull = (c1 > o1) && bodyAbs > atr * 0.35;
   bool rejectionBear = (c1 < o1) && bodyAbs > atr * 0.35;
   // Bullish FVG mature: price returned + bullish rejection
   if(l0 > h2 + atr * 0.15){
      double fvgLo = h2, fvgHi = l0;
      if(bid >= fvgLo && bid <= fvgHi && rejectionBull){
         s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
         s.slPrice = fvgLo - 0.4 * atr;          // invalidation = below FVG low
         s.tpPrice = _smc_tp(s.entryRef, DIR_BUY, 2.5);
         s.score = 70.0; s.reason = "FVG_MIT bull retest+reject";
         return s;
      }
   }
   if(h0 < l2 - atr * 0.15){
      double fvgLo = h0, fvgHi = l2;
      if(bid >= fvgLo && bid <= fvgHi && rejectionBear){
         s.dir = DIR_SELL; s.entryRef = bid;
         s.slPrice = fvgHi + 0.4 * atr;
         s.tpPrice = _smc_tp(s.entryRef, DIR_SELL, 2.5);
         s.score = 70.0; s.reason = "FVG_MIT bear retest+reject";
         return s;
      }
   }
   return s;
}

// === 3b. FVG MITIGATION — WINDOW (11-08/13-08) ==============================
// La #3 sopra valuta ogni gap SOLO all'istante fisso shift5-7 vs il prezzo di
// ORA: se il ritorno sulla zona non avviene esattamente in quel momento, il
// segnale e' perso per sempre (nessun registro). Qui il gap resta "attivo"
// fino a NXS_FVGMITW_MAX_WAIT barre: ogni barra nuova puo' ancora mitigarlo.
// Confermato due volte indipendentemente su 4h (walk-forward 11/08 + batch
// grid 12/08, n=129 robusto) - vedi vault "NEXUS EA - Incidente Sicurezza e
// Setup Desktop (13-08)". Porting fedele di _fvg_mit_window_series/
// sig_fvg_mit_window/_fvg_mit_window_sl_tp in server/backtest.py: stessa
// coppia di candele per la formazione del gap (shift5/shift7), stesso
// registro di zone con eta' massima, stesso SL (bordo zona ∓0.4×ATR) e
// stesso TP a multiplo-R (2.5R sulla distanza SL, NON 2.5×ATR fisso come la
// #3 - e' l'unica differenza di formula tra le due). HTF=true e trailing
// 3.0×ATR vengono dal miglior candidato del batch grezzo del 12/08 (non da
// una ricerca dedicata a griglia piena come CRT/FVG_CONT/TSI - trattarli con
// meno certezza di quei tre). Tier di rischio invariato (0.5%, Tier C) finche'
// non c'e' storia reale su MT5.
#define NXS_FVGMITW_MAX_ZONES 24
#define NXS_FVGMITW_MAX_WAIT  15

struct SNXSFvgMitWZone {
   double   lo;
   double   hi;
   datetime tBorn;
};

SNXSFvgMitWZone g_fvgMitWBull[NXS_FVGMITW_MAX_ZONES];
int             g_fvgMitWBullCount = 0;
SNXSFvgMitWZone g_fvgMitWBear[NXS_FVGMITW_MAX_ZONES];
int             g_fvgMitWBearCount = 0;
datetime        g_fvgMitWLastBar   = 0;

void _fvgMitW_removeBull(int idx){
   for(int k = idx; k < g_fvgMitWBullCount - 1; k++) g_fvgMitWBull[k] = g_fvgMitWBull[k+1];
   g_fvgMitWBullCount--;
}
void _fvgMitW_removeBear(int idx){
   for(int k = idx; k < g_fvgMitWBearCount - 1; k++) g_fvgMitWBear[k] = g_fvgMitWBear[k+1];
   g_fvgMitWBearCount--;
}

// Aggiorna il registro UNA VOLTA per barra nuova (stato persistente fra
// chiamate - deve girare sempre, anche se il toggle e' spento in questo giro,
// altrimenti il registro perde barre e la finestra si sfasa rispetto al
// Python, che itera ogni candela senza saltarne mai una).
void NXS_FvgMitWindow_Update(){
   datetime tBar1 = iTime(g_sym, NXS_EffTF(), 1);
   if(tBar1 == g_fvgMitWLastBar) return;
   g_fvgMitWLastBar = tBar1;

   double atr = _smc_atr();
   if(atr <= 0) return;

   double h2 = iHigh(g_sym, NXS_EffTF(), 5), l2 = iLow(g_sym, NXS_EffTF(), 5);
   double h0 = iHigh(g_sym, NXS_EffTF(), 7), l0 = iLow(g_sym, NXS_EffTF(), 7);
   if(l0 > h2 + atr * 0.15 && g_fvgMitWBullCount < NXS_FVGMITW_MAX_ZONES){
      g_fvgMitWBull[g_fvgMitWBullCount].lo    = h2;
      g_fvgMitWBull[g_fvgMitWBullCount].hi    = l0;
      g_fvgMitWBull[g_fvgMitWBullCount].tBorn = tBar1;
      g_fvgMitWBullCount++;
   }
   if(h0 < l2 - atr * 0.15 && g_fvgMitWBearCount < NXS_FVGMITW_MAX_ZONES){
      g_fvgMitWBear[g_fvgMitWBearCount].lo    = h0;
      g_fvgMitWBear[g_fvgMitWBearCount].hi    = l2;
      g_fvgMitWBear[g_fvgMitWBearCount].tBorn = tBar1;
      g_fvgMitWBearCount++;
   }

   for(int i = g_fvgMitWBullCount - 1; i >= 0; i--){
      int age = iBarShift(g_sym, NXS_EffTF(), g_fvgMitWBull[i].tBorn) - 1;
      if(age > NXS_FVGMITW_MAX_WAIT) _fvgMitW_removeBull(i);
   }
   for(int i = g_fvgMitWBearCount - 1; i >= 0; i--){
      int age = iBarShift(g_sym, NXS_EffTF(), g_fvgMitWBear[i].tBorn) - 1;
      if(age > NXS_FVGMITW_MAX_WAIT) _fvgMitW_removeBear(i);
   }
}

SNXSSignal NXS_Strat_FVG_Mitigation_Window(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_FVG_CONT; s.stratName = "FVG_MIT_WINDOW";
   NXS_FvgMitWindow_Update();
   double atr = _smc_atr();
   if(atr <= 0) return s;
   double c1    = iClose(g_sym, NXS_EffTF(), 1);
   double o1    = iOpen (g_sym, NXS_EffTF(), 1);
   double curLo = iLow  (g_sym, NXS_EffTF(), 1);
   double curHi = iHigh (g_sym, NXS_EffTF(), 1);
   double bodyAbs = MathAbs(c1 - o1);
   bool rejectionBull = (c1 > o1) && bodyAbs > atr * 0.35;
   bool rejectionBear = (c1 < o1) && bodyAbs > atr * 0.35;

   if(rejectionBull){
      for(int i = 0; i < g_fvgMitWBullCount; i++){
         if(curHi >= g_fvgMitWBull[i].lo && curLo <= g_fvgMitWBull[i].hi){
            s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
            s.slPrice = g_fvgMitWBull[i].lo - 0.4 * atr;
            s.tpPrice = s.entryRef + (s.entryRef - s.slPrice) * 2.5;
            s.score = 70.0; s.reason = "FVG_MIT_WINDOW bull retest+reject";
            _fvgMitW_removeBull(i);
            return s;
         }
      }
   }
   if(rejectionBear){
      for(int i = 0; i < g_fvgMitWBearCount; i++){
         if(curHi >= g_fvgMitWBear[i].lo && curLo <= g_fvgMitWBear[i].hi){
            s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
            s.slPrice = g_fvgMitWBear[i].hi + 0.4 * atr;
            s.tpPrice = s.entryRef - (s.slPrice - s.entryRef) * 2.5;
            s.score = 70.0; s.reason = "FVG_MIT_WINDOW bear retest+reject";
            _fvgMitW_removeBear(i);
            return s;
         }
      }
   }
   return s;
}

// === 4. OB MITIGATION STRUCTURAL ======================================
// Uses NXS_Structure last OB (after displacement+BOS) → wrapper
SNXSSignal NXS_Strat_OB_Mitigation_Structural(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_ORDER_BLOCK; s.stratName = "OB_MIT";
   // Reuse existing structure-aware OB detector
   SNXSSignal raw = NXS_Strat_OrderBlock();
   if(raw.dir == DIR_NONE) return s;
   s = raw;
   s.stratName = "OB_MIT";
   s.reason    = "OB:structuralMit";
   if(s.score < 68) s.score = 68;          // floor
   return s;
}

// === 5. SH + BMS + RTO ===============================================
// Stop hunt (sweep) → Break market structure → Return to OB/FVG
// 17/07 notte - riscritta come macchina a stati, da audit esterno canonico
// (fonti ICT/SMC). La versione precedente richiedeva sweep + CHOCH + FVG +
// prezzo gia' dentro la zona TUTTO sullo stesso tick - "collassava" una
// sequenza che nella realta' e' causale e temporale (sweep, POI displacement/
// MSS entro qualche barra, POI un ritorno SUCCESSIVO alla zona d'origine),
// senza dimostrare che gli eventi fossero davvero collegati fra loro.
// Sequenza reale: IDLE -> SWEPT -> (entro InpSHBMS_MaxMSSBars barre, MSS
// confermato + origine registrata) -> WAITING_RETURN -> primo ritorno nella
// zona = entry. Vincolo causale: sweepTime < mssTime < retestTime, garantito
// per costruzione (si avanza di stato solo su una barra chiusa successiva).
int    InpSHBMS_SwingLookback = 15;   // barre per il riferimento swing pre-sweep
int    InpSHBMS_MaxMSSBars    = 20;   // barre max fra sweep e MSS prima di scadere
int    InpSHBMS_MaxWaitBars   = 15;   // barre max di attesa del ritorno dopo l'MSS
double InpSHBMS_DispBodyATR   = 0.8;  // corpo minimo del displacement (x ATR) per contare come MSS

enum ENUM_NXS_SHBMS_STATE { SHBMS_IDLE = 0, SHBMS_SWEPT, SHBMS_WAITING_RETURN };

struct SNXSSHBmsState {
   int      state;
   datetime lastBarTime;   // barra 0 (in formazione) all'ultimo avanzamento di stato - gating
   double   sweepLevel;    // livello sweepato (sw.level al momento dello SWEPT)
   double   swingRef;      // swing di riferimento che l'MSS deve rompere
   int      barsWaited;    // barre trascorse nello stato corrente
   double   originLo, originHi;   // zona d'origine (ultima candela opposta prima del displacement)
};
SNXSSHBmsState g_shbmsBuy, g_shbmsSell;

void NXS_SHBMS_Reset(SNXSSHBmsState &st){
   st.state = SHBMS_IDLE; st.barsWaited = 0;
   st.sweepLevel = 0; st.swingRef = 0; st.originLo = 0; st.originHi = 0;
}

SNXSSignal NXS_SHBMS_UpdateSide(int dir, SNXSSHBmsState &st, SNXSSweepExt &sw,
                                ENUM_TIMEFRAMES tf, double atr, datetime curBar0){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "SH_BMS_RTO";
   bool newBar = (st.lastBarTime != curBar0);
   ENUM_NXS_DIR wantSweep = (dir == +1) ? DIR_BUY : DIR_SELL;

   if(st.state == SHBMS_IDLE){
      if(newBar && sw.confirmed && sw.dir == wantSweep){
         // SWEPT: registra il livello e lo swing di riferimento che l'MSS dovra' rompere.
         st.state = SHBMS_SWEPT; st.barsWaited = 0; st.sweepLevel = sw.level; st.lastBarTime = curBar0;
         int hiIdx = iHighest(g_sym, tf, MODE_HIGH, InpSHBMS_SwingLookback, 2);
         int loIdx = iLowest (g_sym, tf, MODE_LOW,  InpSHBMS_SwingLookback, 2);
         st.swingRef = (dir == +1) ? (hiIdx >= 0 ? iHigh(g_sym, tf, hiIdx) : 0)
                                    : (loIdx >= 0 ? iLow (g_sym, tf, loIdx) : 0);
      }
      return s;
   }

   if(st.state == SHBMS_SWEPT){
      // Invalidation: chiusura oltre il livello sweepato nel verso sbagliato.
      double c1 = iClose(g_sym, tf, 1);
      if(newBar && ((dir == +1 && c1 < st.sweepLevel) || (dir == -1 && c1 > st.sweepLevel))){
         NXS_SHBMS_Reset(st); st.lastBarTime = curBar0; return s;
      }
      if(!newBar) return s;
      st.barsWaited++;
      if(st.barsWaited > InpSHBMS_MaxMSSBars){ NXS_SHBMS_Reset(st); st.lastBarTime = curBar0; return s; }
      double o1 = iOpen(g_sym, tf, 1);
      double body1 = MathAbs(c1 - o1);
      bool mss = (dir == +1) ? (st.swingRef > 0 && c1 > st.swingRef && body1 >= atr * InpSHBMS_DispBodyATR)
                              : (st.swingRef > 0 && c1 < st.swingRef && body1 >= atr * InpSHBMS_DispBodyATR);
      st.lastBarTime = curBar0;
      if(!mss) return s;
      // MSS confermato: origine = ultima candela di colore opposto prima del displacement (barra 1).
      double originA = o1, originB = c1;
      for(int k = 2; k <= 6; k++){
         double ok = iOpen(g_sym, tf, k), ck = iClose(g_sym, tf, k);
         bool oppositeColor = (dir == +1) ? (ck < ok) : (ck > ok);
         if(oppositeColor){ originA = ok; originB = ck; break; }
      }
      st.originLo = MathMin(originA, originB);
      st.originHi = MathMax(originA, originB);
      st.state = SHBMS_WAITING_RETURN; st.barsWaited = 0;
      return s;
   }

   // SHBMS_WAITING_RETURN
   if(newBar){
      st.barsWaited++;
      st.lastBarTime = curBar0;
      if(st.barsWaited > InpSHBMS_MaxWaitBars){ NXS_SHBMS_Reset(st); return s; }
      double c1 = iClose(g_sym, tf, 1);
      if((dir == +1 && c1 < st.sweepLevel) || (dir == -1 && c1 > st.sweepLevel)){
         NXS_SHBMS_Reset(st); return s;   // invalidazione profonda
      }
   }
   if(st.originHi <= st.originLo) return s;
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   bool touched = (bid >= st.originLo && bid <= st.originHi);
   if(!touched) return s;
   // Primo ritorno nella zona d'origine = entry. One-shot: reset subito dopo.
   if(dir == +1){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = MathMin(st.sweepLevel, st.originLo) - 0.5 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_BUY, 2.6);
   } else {
      s.dir = DIR_SELL; s.entryRef = bid;
      s.slPrice = MathMax(st.sweepLevel, st.originHi) + 0.5 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_SELL, 2.6);
   }
   s.score = 74.0; s.reason = "SH+BMS+RTO " + (string)((dir == +1) ? "bull" : "bear") + ":origin_return";
   NXS_SHBMS_Reset(st);
   return s;
}

SNXSSignal NXS_Strat_SH_BMS_RTO(SNXSSweepExt &sw){
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   double atr = _smc_atr();
   datetime curBar0 = iTime(g_sym, tf, 0);
   SNXSSignal s = NXS_SHBMS_UpdateSide(+1, g_shbmsBuy, sw, tf, atr, curBar0);
   if(s.dir != DIR_NONE) return s;
   return NXS_SHBMS_UpdateSide(-1, g_shbmsSell, sw, tf, atr, curBar0);
}

// === 5b. SH+BMS+RTO V2 (14/08) — state machine piu' semplice, MSS "morbido" =
// Porting fedele di _shbms_v2_series/sig_sh_bms_rto_v2 in server/backtest.py.
// Regole DIVERSE dalla v1 sopra (non un refactor, una variante indipendente
// gia' esistente lato Python dall'08/08): nessuna soglia body-ATR sull'MSS,
// zona di ritorno [sweepLevel..mssLevel] invece della "candela opposta
// pre-displacement", rejection a 0.3xATR sul punto medio della zona, timeout
// 12 barre condiviso da entrambe le fasi, gate ADX>=20 + trend di struttura
// != 0 che blocca l'avanzamento di stato (non solo l'ingresso) - un bar
// gated-out non fa avanzare barsWaited, fedele al "continue" Python che
// salta l'intera barra per entrambe le direzioni insieme.
// Risultato 14/08: walk-forward 5/5 su 1h, il piu' robusto della sessione -
// vedi vault "50 Maestri del Trading, Sintesi e Confronto col Nucleo (14-08)".
#define NXS_SHBMSV2_MAX_WAIT 12
enum ENUM_NXS_SHBMSV2_STATE { SHBMSV2_IDLE = 0, SHBMSV2_SWEPT, SHBMSV2_WAITING };

struct SNXSSHBmsV2State {
   int    state;
   int    barsWaited;
   double sweepLevel;
   double mssLevel;
};
SNXSSHBmsV2State g_shbmsV2Buy, g_shbmsV2Sell;
datetime         g_shbmsV2LastBar = 0;

void NXS_SHBMSV2_Reset(SNXSSHBmsV2State &st){
   st.state = SHBMSV2_IDLE; st.barsWaited = 0; st.sweepLevel = 0; st.mssLevel = 0;
}

SNXSSignal NXS_SHBMSV2_StepSide(int dir, SNXSSHBmsV2State &st, SNXSSweepExt &sw,
                                double c1, double o1, double curLo, double curHi, double atr){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "SH_BMS_RTO_V2";
   ENUM_NXS_DIR wantSweep = (dir == +1) ? DIR_BUY : DIR_SELL;

   if(st.state == SHBMSV2_IDLE){
      if(sw.confirmed && sw.dir == wantSweep){
         st.sweepLevel = sw.level; st.state = SHBMSV2_SWEPT; st.barsWaited = 0;
      }
      return s;
   }
   if(st.state == SHBMSV2_SWEPT){
      st.barsWaited++;
      if(st.barsWaited > NXS_SHBMSV2_MAX_WAIT){ NXS_SHBMSV2_Reset(st); return s; }
      bool mss = (dir == +1) ? (c1 > o1 && c1 > st.sweepLevel) : (c1 < o1 && c1 < st.sweepLevel);
      if(mss){ st.mssLevel = c1; st.state = SHBMSV2_WAITING; st.barsWaited = 0; }
      return s;
   }
   // SHBMSV2_WAITING
   st.barsWaited++;
   if(st.barsWaited > NXS_SHBMSV2_MAX_WAIT){ NXS_SHBMSV2_Reset(st); return s; }
   double zoneTop = (dir == +1) ? st.mssLevel   : st.sweepLevel;
   double zoneBot = (dir == +1) ? st.sweepLevel : st.mssLevel;
   if(zoneTop <= zoneBot) return s;
   double mid  = (zoneTop + zoneBot) * 0.5;
   double body = MathAbs(c1 - o1);
   bool touch, rej;
   if(dir == +1){ touch = (curLo <= zoneTop); rej = (c1 > o1 && c1 > mid && body >= atr * 0.3); }
   else         { touch = (curHi >= zoneBot); rej = (c1 < o1 && c1 < mid && body >= atr * 0.3); }
   if(!(touch && rej)) return s;
   double sl = (dir == +1) ? st.sweepLevel - 0.3*atr : st.sweepLevel + 0.3*atr;
   double tp = (dir == +1) ? c1 + (c1 - sl) * 2.0     : c1 - (sl - c1) * 2.0;
   s.dir = (dir == +1) ? DIR_BUY : DIR_SELL;
   s.entryRef = (dir == +1) ? SymbolInfoDouble(g_sym, SYMBOL_ASK) : SymbolInfoDouble(g_sym, SYMBOL_BID);
   s.slPrice = sl; s.tpPrice = tp;
   s.score = 70.0; s.reason = "SH_BMS_RTO_V2 sweep+MSS+retest";
   NXS_SHBMSV2_Reset(st);
   return s;
}

SNXSSignal NXS_Strat_SH_BMS_RTO_V2(SNXSSweepExt &sw){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "SH_BMS_RTO_V2";
   datetime tBar1 = iTime(g_sym, NXS_EffTF(), 1);
   if(tBar1 == g_shbmsV2LastBar) return s;   // gia' avanzato per questa barra
   g_shbmsV2LastBar = tBar1;

   double atr = _smc_atr();
   // Gate ADX+trend: fedele al "continue" Python che salta l'INTERA barra
   // (nessun avanzamento di stato per nessuna delle due direzioni), non solo
   // il segnale.
   if(atr <= 0 || g_adx < 20.0 || g_struct.trend == 0) return s;

   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double o1 = iOpen (g_sym, NXS_EffTF(), 1);
   double curLo = iLow (g_sym, NXS_EffTF(), 1);
   double curHi = iHigh(g_sym, NXS_EffTF(), 1);

   SNXSSignal sBuy = NXS_SHBMSV2_StepSide(+1, g_shbmsV2Buy, sw, c1, o1, curLo, curHi, atr);
   SNXSSignal sSell = NXS_SHBMSV2_StepSide(-1, g_shbmsV2Sell, sw, c1, o1, curLo, curHi, atr);
   // Fedele a Python: se entrambe le direzioni segnalano nello stesso giro
   // (raro), vince l'ultima valutata (sell) - stesso ordine del ciclo "for d
   // in (1,-1)" che sovrascrive out_sig[i].
   if(sSell.dir != DIR_NONE) return sSell;
   return sBuy;
}

// === 6. SMS + BMS + RTO (v2.0.3 — failure swing reale con HH/LL labelling) ==
// Logica:
//  - rileva ultimi 2 swing high (h1>h2 = HH, h1<h2 = LH ⇒ failure swing bear)
//  - rileva ultimi 2 swing low  (l1<l2 = LL, l1>l2 = HL ⇒ failure swing bull)
//  - dopo failure swing → BMS opposto (CHOCH già flaggato da NXS_Structure)
//  - return to OB/FVG/IFVG (proxy: ritorno entro 60% del corpo dello swing)
//  - entry con reaction candle
SNXSSignal NXS_Strat_SMS_BMS_RTO(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "SMS_BMS_RTO";
   double atr = _smc_atr();
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double o1 = iOpen (g_sym, NXS_EffTF(), 1);
   double bodyAbs = MathAbs(c1 - o1);
   bool rejectionBull = (c1 > o1) && bodyAbs > atr * 0.3;
   bool rejectionBear = (c1 < o1) && bodyAbs > atr * 0.3;
   // Quick HH/LH/LL/HL via iHighest/iLowest in two windows
   int    hiIdxA = iHighest(g_sym, NXS_EffTF(), MODE_HIGH, 10, 1);
   int    hiIdxB = iHighest(g_sym, NXS_EffTF(), MODE_HIGH, 20, 11);
   int    loIdxA = iLowest (g_sym, NXS_EffTF(), MODE_LOW,  10, 1);
   int    loIdxB = iLowest (g_sym, NXS_EffTF(), MODE_LOW,  20, 11);
   double hi_recent = iHigh(g_sym, NXS_EffTF(), hiIdxA);
   double hi_older  = iHigh(g_sym, NXS_EffTF(), hiIdxB);
   double lo_recent = iLow (g_sym, NXS_EffTF(), loIdxA);
   double lo_older  = iLow (g_sym, NXS_EffTF(), loIdxB);
   bool failureLow  = (lo_recent > lo_older);   // HL = failure to make LL
   bool failureHigh = (hi_recent < hi_older);   // LH = failure to make HH
   double midUp   = (hi_recent + lo_recent) * 0.5;
   double midDown = midUp;

   if(failureLow && g_struct.chochUp && rejectionBull){
      // BUY: failure to break low + BMS up + back to discount + bull rejection
      if(bid <= midUp){
         s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
         s.slPrice = lo_recent - 0.5 * atr;
         s.tpPrice = _smc_tp(s.entryRef, DIR_BUY, 2.6);
         s.score = 72.0; s.reason = "SMS:HL+BMS↑+RTO";
         return s;
      }
   }
   if(failureHigh && g_struct.chochDown && rejectionBear){
      if(bid >= midDown){
         s.dir = DIR_SELL; s.entryRef = bid;
         s.slPrice = hi_recent + 0.5 * atr;
         s.tpPrice = _smc_tp(s.entryRef, DIR_SELL, 2.6);
         s.score = 72.0; s.reason = "SMS:LH+BMS↓+RTO";
         return s;
      }
   }
   return s;
}

// === 7. SILVER BULLET (NY/London killzone) ============================
// 17/07 notte - riscritta come macchina a stati, da audit esterno canonico:
// prima era solo "sweep dentro una finestra oraria", mancavano displacement,
// FVG e un ritorno successivo nella zona - gli elementi centrali del
// modello Silver Bullet. Sequenza: finestra aperta -> sweep di liquidita'
// -> displacement con BOS -> FVG registrato dal displacement -> ritorno
// nel FVG (entro un numero massimo di barre, non un calcolo preciso del
// termine sessione in timezone reale - quello resta un lavoro a parte,
// condiviso con NY_REVERSAL, gia' in coda separatamente).
int InpSB_SwingLookback = 12;
int InpSB_MaxBars       = 15;   // barre max dal primo sweep dentro la finestra all'entry
double InpSB_DispBodyATR = 0.8;

enum ENUM_NXS_SB_STATE { SB_IDLE = 0, SB_SWEPT, SB_WAITING_RETURN };

struct SNXSSBState {
   int      state;
   datetime lastBarTime;
   double   sweepLevel;
   double   fvgLo, fvgHi;
   int      barsWaited;
};
SNXSSBState g_sbBuy, g_sbSell;

SNXSSignal NXS_SB_UpdateSide(int dir, SNXSSBState &st, SNXSSweepExt &sw, bool inKillzone,
                             string kzTag, ENUM_TIMEFRAMES tf, double atr, datetime curBar0){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "SILVER_BULLET";
   bool newBar = (st.lastBarTime != curBar0);
   ENUM_NXS_DIR wantSweep = (dir == +1) ? DIR_BUY : DIR_SELL;

   if(st.state == SB_IDLE){
      if(newBar && inKillzone && sw.confirmed && sw.dir == wantSweep){
         st.state = SB_SWEPT; st.barsWaited = 0; st.sweepLevel = sw.level; st.lastBarTime = curBar0;
      }
      return s;
   }

   if(st.state == SB_SWEPT){
      if(!newBar) return s;
      st.lastBarTime = curBar0; st.barsWaited++;
      if(st.barsWaited > InpSB_MaxBars){ st.state = SB_IDLE; return s; }
      // Displacement a shift2 con BOS, FVG fra candela1 (shift3) e candela3 (shift1,
      // appena chiusa) - stessa geometria FVG corretta di LIQ_VOID stanotte.
      double o2 = iOpen(g_sym, tf, 2), c2 = iClose(g_sym, tf, 2);
      double body2 = MathAbs(c2 - o2);
      bool rightColor = (dir == +1) ? (c2 > o2) : (c2 < o2);
      if(body2 < atr * InpSB_DispBodyATR || !rightColor) return s;
      int hiIdx = iHighest(g_sym, tf, MODE_HIGH, InpSB_SwingLookback, 3);
      int loIdx = iLowest (g_sym, tf, MODE_LOW,  InpSB_SwingLookback, 3);
      double swingRef = (dir == +1) ? (hiIdx >= 0 ? iHigh(g_sym, tf, hiIdx) : 0)
                                     : (loIdx >= 0 ? iLow (g_sym, tf, loIdx) : 0);
      bool bos = (dir == +1) ? (swingRef > 0 && c2 > swingRef) : (swingRef > 0 && c2 < swingRef);
      if(!bos) return s;
      double c1High = iHigh(g_sym, tf, 3), c1Low = iLow(g_sym, tf, 3);
      double c3High = iHigh(g_sym, tf, 1), c3Low = iLow(g_sym, tf, 1);
      if(dir == +1){
         if(c3Low > c1High){ st.fvgLo = c1High; st.fvgHi = c3Low; st.state = SB_WAITING_RETURN; st.barsWaited = 0; }
      } else {
         if(c3High < c1Low){ st.fvgLo = c3High; st.fvgHi = c1Low; st.state = SB_WAITING_RETURN; st.barsWaited = 0; }
      }
      return s;
   }

   // SB_WAITING_RETURN
   if(newBar){
      st.lastBarTime = curBar0; st.barsWaited++;
      if(st.barsWaited > InpSB_MaxBars){ st.state = SB_IDLE; return s; }
      double c1 = iClose(g_sym, tf, 1);
      if((dir == +1 && c1 < st.sweepLevel) || (dir == -1 && c1 > st.sweepLevel)){ st.state = SB_IDLE; return s; }
   }
   if(st.fvgHi <= st.fvgLo) return s;
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   if(bid < st.fvgLo || bid > st.fvgHi) return s;
   if(dir == +1){
      s.dir = DIR_BUY;  s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = st.sweepLevel - 0.6 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_BUY, 2.8);
      s.reason = kzTag + " bull:fvg_retest";
   } else {
      s.dir = DIR_SELL; s.entryRef = bid;
      s.slPrice = st.sweepLevel + 0.6 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_SELL, 2.8);
      s.reason = kzTag + " bear:fvg_retest";
   }
   s.score = 76.0;
   st.state = SB_IDLE;   // one-shot
   return s;
}

SNXSSignal NXS_Strat_SilverBullet(SNXSSweepExt &sw){
   // v2.0.5b: GMT-corrected killzones (server time → GMT)
   datetime gmtNow = (datetime)((long)TimeCurrent() - (long)InpServerGMTOffset * 3600);
   MqlDateTime mt; TimeToStruct(gmtNow, mt);
   int h = mt.hour;
   bool killzoneLO = (h >= 10 && h < 11);   // London KZ 10-11 GMT
   bool killzoneNY = (h >= 14 && h < 15);   // NY KZ 14-15 GMT
   bool inKillzone = killzoneLO || killzoneNY;
   string kzTag = killzoneLO ? "SB:LO-KZ" : "SB:NY-KZ";
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   double atr = _smc_atr();
   datetime curBar0 = iTime(g_sym, tf, 0);
   SNXSSignal s = NXS_SB_UpdateSide(+1, g_sbBuy, sw, inKillzone, kzTag, tf, atr, curBar0);
   if(s.dir != DIR_NONE) return s;
   return NXS_SB_UpdateSide(-1, g_sbSell, sw, inKillzone, kzTag, tf, atr, curBar0);
}

// === 8. AMD REVERSAL ==================================================
// Manipulation above Asia High → SELL on reclaim+MSS (mirror for low)
SNXSSignal NXS_Strat_AMD_Reversal(SNXSSweepExt &sw, SNXSAMD &amd){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "AMD_REVERSAL";
   // v2.0.34 (audit point 4): only the confirmed reversal phase now - was
   // also firing on AMD_MANIPULATION/AMD_DISTRIBUTION, the same condition
   // AMD_CONT gated on, so both were eligible on the same bars.
   if(amd.phase != AMD_REVERSAL_DISTRIBUTION) return s;
   double atr = _smc_atr();
   if(sw.sweptAsiaHigh && g_struct.chochDown){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = sw.refHigh + 0.5 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_SELL, 2.5);
      s.score = 75.0; s.reason = "AMD:manip>Asia+MSS↓";
      return s;
   }
   if(sw.sweptAsiaLow && g_struct.chochUp){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = sw.refLow - 0.5 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_BUY, 2.5);
      s.score = 75.0; s.reason = "AMD:manip<Asia+MSS↑";
      return s;
   }
   return s;
}

// === 9. OTE CONTINUATION (v2.0.6 — strict trend, no OR vago) ==================
// Entry on OTE retrace (0.62-0.79) of the dominant leg. Solo se trend
// strutturale chiaramente bull/bear (rimosso fallback ambiguo discount/premium).
// 17/07 notte - da audit esterno canonico: la zona Fibonacci in se' (62-79%,
// 70.5% centrale) era gia' corretta, il problema era l'ancoraggio - lo swing
// veniva preso da un rolling highest/lowest generico di 30 barre su
// InpTFMedium, MAI verificato che fosse davvero il leg che ha prodotto un
// BOS (poteva essere il punto piu' alto/basso di una fase lenta, non un
// vero impulso). NXS_Fib_Build resta invariata (e' condivisa anche col
// dashboard/visual bridge, fuori scope qui) - aggiunto invece un gate BOS
// dedicato: il leg deve avere prodotto un vero displacement (corpo forte)
// che rompe uno swing PRECEDENTE a quello usato come origine del leg.
double InpOTECont_DispBodyATR = 0.8;

SNXSSignal NXS_Strat_OTE_Continuation(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "OTE_CONT";
   ENUM_TIMEFRAMES structTF = InpTFMedium;
   SNXSFib f = NXS_Fib_Build(structTF, 30);
   if(!f.inOTE) return s;
   double atr = _smc_atr();

   // Gate BOS: nelle ultime 10 barre di structTF deve esserci un vero
   // displacement (corpo >= soglia) che rompe uno swing PRECEDENTE al leg
   // corrente (finestra piu' vecchia, 15 barre prima del displacement) -
   // altrimenti il leg e' solo il max/min di una finestra, non un impulso.
   bool bosConfirmed = false;
   for(int i = 1; i <= 10; i++){
      double oi = iOpen(g_sym, structTF, i), ci = iClose(g_sym, structTF, i);
      double bodyi = MathAbs(ci - oi);
      if(bodyi < atr * InpOTECont_DispBodyATR) continue;
      int hiIdx = iHighest(g_sym, structTF, MODE_HIGH, 15, i + 1);
      int loIdx = iLowest (g_sym, structTF, MODE_LOW,  15, i + 1);
      double swingRefHi = hiIdx >= 0 ? iHigh(g_sym, structTF, hiIdx) : 0;
      double swingRefLo = loIdx >= 0 ? iLow (g_sym, structTF, loIdx) : 0;
      if(ci > oi && swingRefHi > 0 && ci > swingRefHi){ bosConfirmed = true; break; }
      if(ci < oi && swingRefLo > 0 && ci < swingRefLo){ bosConfirmed = true; break; }
   }
   if(!bosConfirmed) return s;

   // Entry su barra chiusa di NXS_EffTF() (entryTF), non piu' bid live.
   double c1 = iClose(g_sym, NXS_EffTF(), 1), o1 = iOpen(g_sym, NXS_EffTF(), 1);
   // v2.0.6: strict alignment con struttura. Range (trend==0) → niente trade.
   if(g_struct.trend == 1 && f.inDiscount && c1 < f.mid && c1 > f.swingLow && c1 > o1){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = f.swingLow - 0.3 * atr;
      s.tpPrice = MathMax(f.swingHigh, _smc_tp(s.entryRef, DIR_BUY, 2.2));
      s.score = 69.0; s.reason = "OTE 0.62-0.79 disc+trend+BOS";
      return s;
   }
   if(g_struct.trend == -1 && f.inPremium && c1 > f.mid && c1 < f.swingHigh && c1 < o1){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = f.swingHigh + 0.3 * atr;
      s.tpPrice = MathMin(f.swingLow, _smc_tp(s.entryRef, DIR_SELL, 2.2));
      s.score = 69.0; s.reason = "OTE 0.62-0.79 prem+trend+BOS";
      return s;
   }
   return s;
}

// === 10. MALAYSIAN SNR (v2.0.3 — body-based + fresh/flipped + storyline) ====
// Storyline: Weekly + Daily + H4 supportano? H1 entry su rejection candle body forte.
// Fresh = livello non testato negli ultimi 20 bar H4 → bonus +5
// Flipped = livello che era resistance e ora supporta (close-above) → SBR (Support-Becomes-Resistance) o RBS.
// 17/07 notte - da audit esterno canonico, 3 correzioni:
// (1) i livelli H4 vengono ora confrontati con tolleranze in ATR H4 (non
//     piu' l'ATR del TF strategia attivo - unita' diverse, distanza non
//     dimensionalmente stabile);
// (2) il tocco del livello ora usa low/high della barra CHIUSA 1, non il
//     bid live mescolato con la rejection su barra chiusa;
// (3) W1 non e' piu' calcolato e scartato: e' un vero bonus di confluence
//     (livello W1 vicino = +score), o rimosso dal trigger come suggerito.
SNXSSignal NXS_Strat_MalaysianSNR_Rejection(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "MALAYSIAN_SNR";
   // v2.0.6: skip Asia (bassa volatilità ⇒ falsi segnali su H4 SR body-based)
   if(g_session == SESS_ASIAN) return s;
   double atr = _smc_atr();   // per il corpo della candela sul TF strategia - unita' corretta li'
   // Handle statico locale (non NXS_iATR - questo file e' incluso PRIMA di
   // NXS_Performance.mqh in NEXUS_EA_v2.mq5, quella funzione non sarebbe
   // ancora dichiarata): creato una sola volta, poi riusato ad ogni chiamata.
   static int hAtrH4 = INVALID_HANDLE;
   if(hAtrH4 == INVALID_HANDLE) hAtrH4 = iATR(g_sym, InpTFHigh, 14);
   double atrH4Arr[]; double atrH4 = 0;
   if(hAtrH4 != INVALID_HANDLE) CopyBuffer(hAtrH4, 0, 1, 1, atrH4Arr);
   if(ArraySize(atrH4Arr) > 0) atrH4 = atrH4Arr[0];
   if(atrH4 <= 0) return s;
   // Body-based levels (close, not wick) on H4 e W1
   int idxH4Hi = iHighest(g_sym, InpTFHigh, MODE_CLOSE, 12, 1);
   int idxH4Lo = iLowest (g_sym, InpTFHigh, MODE_CLOSE, 12, 1);
   double h4Hi = iClose(g_sym, InpTFHigh, idxH4Hi);
   double h4Lo = iClose(g_sym, InpTFHigh, idxH4Lo);
   int idxW1Hi = iHighest(g_sym, PERIOD_W1, MODE_CLOSE, 8, 1);
   int idxW1Lo = iLowest (g_sym, PERIOD_W1, MODE_CLOSE, 8, 1);
   double w1Hi = iClose(g_sym, PERIOD_W1, idxW1Hi);
   double w1Lo = iClose(g_sym, PERIOD_W1, idxW1Lo);
   double c1 = iClose(g_sym, NXS_EffTF(), 1);
   double o1 = iOpen (g_sym, NXS_EffTF(), 1);
   double l1 = iLow  (g_sym, NXS_EffTF(), 1);
   double h1 = iHigh (g_sym, NXS_EffTF(), 1);
   double bodyAbs = MathAbs(c1 - o1);
   if(bodyAbs <= atr * 0.5) return s;          // require strong body
   // Fresh check: did price already touch this level in last 20 H4 bars?
   bool freshHi = true, freshLo = true;
   for(int i = 1; i <= 20; i++){
      double hh = iHigh(g_sym, InpTFHigh, i);
      double ll = iLow (g_sym, InpTFHigh, i);
      if(hh >= h4Hi - atrH4 * 0.3 && hh <= h4Hi + atrH4 * 0.3 && i > 3) freshHi = false;
      if(ll >= h4Lo - atrH4 * 0.3 && ll <= h4Lo + atrH4 * 0.3 && i > 3) freshLo = false;
   }
   // AUDITPATCH: storyline is directional context, not the current location.
   double h4C1 = iClose(g_sym, InpTFHigh, 1);
   double h4C4 = iClose(g_sym, InpTFHigh, 4);
   double d1C1 = iClose(g_sym, PERIOD_D1, 1);
   double d1C2 = iClose(g_sym, PERIOD_D1, 2);
   bool storyBull = (h4C1 > h4C4 && d1C1 >= d1C2);
   bool storyBear = (h4C1 < h4C4 && d1C1 <= d1C2);
   // BUY at support - tocco su barra chiusa 1 (low), non bid live.
   if(l1 <= h4Lo + atrH4 * 0.4 && l1 >= h4Lo - atrH4 * 0.4 && c1 > o1 && storyBull){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = h4Lo - 0.5 * atrH4;
      s.tpPrice = _smc_tp(s.entryRef, DIR_BUY, 2.3);
      s.score = 68.0 + (freshLo ? 5.0 : 0.0);
      if(MathAbs(h4Lo - w1Lo) <= atrH4 * 0.5){ s.score += 4.0; s.reason = freshLo ? "SNR bull fresh+story+W1" : "SNR bull tested+story+W1"; }
      else s.reason = freshLo ? "SNR bull fresh+story" : "SNR bull tested+story";
      return s;
   }
   if(h1 >= h4Hi - atrH4 * 0.4 && h1 <= h4Hi + atrH4 * 0.4 && c1 < o1 && storyBear){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = h4Hi + 0.5 * atrH4;
      s.tpPrice = _smc_tp(s.entryRef, DIR_SELL, 2.3);
      s.score = 68.0 + (freshHi ? 5.0 : 0.0);
      if(MathAbs(h4Hi - w1Hi) <= atrH4 * 0.5){ s.score += 4.0; s.reason = freshHi ? "SNR bear fresh+story+W1" : "SNR bear tested+story+W1"; }
      else s.reason = freshHi ? "SNR bear fresh+story" : "SNR bear tested+story";
      return s;
   }
   return s;
}

// === CRT — Candle Range Theory (11/08, fonte: PDF "Candle Range Theory" ===
// di Suven Raj, caricato dall'utente). Pattern a 3 candele CONSECUTIVE sul
// TF della strategia (NXS_EffTF(), M30 di default nel profilo - vedi
// NXS_StrategyProfiles.mqh):
//   barra shift 2 = RANGE -> CRH/CRL (high/low di quella candela)
//   barra shift 1 = SWEEP -> stoppino oltre CRH (o CRL) ma chiude DENTRO
//                   il range (altrimenti il setup e' invalido - il
//                   mercato sta continuando, non invertendo)
//   ora (entrata)  -> direzione OPPOSTA allo sweep, target il lato
//                   opposto del range
// Nessun filtro di sessione/storyline aggiuntivo - fedele esattamente a
// come e' stata validata in Python (server/backtest.py, _crt_series):
// walk-forward 5/5 finestre su 4h/1h/30m dopo la riverifica sullo storico
// ampliato (11/08), quasi 20.000 trade totali - la scoperta piu' solida
// di tutta la sessione di ricerca. slPrice/tpPrice impostati direttamente
// dai livelli reali del pattern, NON da NXS_DefaultSLTP (nessun multiplo
// ATR - stesso stile di NXS_Strat_MalaysianSNR_Rejection sopra).
SNXSSignal NXS_Strat_CRT(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "CRT";
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   double crh = iHigh(g_sym, tf, 2);
   double crl = iLow (g_sym, tf, 2);
   double sweepHi = iHigh (g_sym, tf, 1);
   double sweepLo = iLow  (g_sym, tf, 1);
   double sweepC  = iClose(g_sym, tf, 1);
   bool sweptHigh = (sweepHi > crh && sweepC <= crh);
   bool sweptLow  = (sweepLo < crl && sweepC >= crl);
   if(sweptHigh && !sweptLow){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = sweepHi; s.tpPrice = crl;
      s.score = 68.0; s.reason = "CRT sweep CRH, target CRL";
   } else if(sweptLow && !sweptHigh){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = sweepLo; s.tpPrice = crh;
      s.score = 68.0; s.reason = "CRT sweep CRL, target CRH";
   }
   // 12/08 — floor minimo sulla distanza dello stop (vedi vault "Fase C
   // Recovery Baseline e Rischio Flottante", 11/08): lo stop e' ancorato al
   // wick della candela di sweep, non a un multiplo ATR. Quando il wick e'
   // minimo il rischio flottante durante il trade puo' esplodere (107%
   // osservato in una finestra) prima che il trade chiuda correttamente a
   // -1R — non un rischio attivo con size fissa, ma un vincolo da rispettare
   // ora che il rischio per-strategia sale (NXS_Profile_Risk tier A). Se la
   // distanza wick-based scende sotto InpCRT_MinStopATR x ATR, lo stop viene
   // esteso (mai stretto) fino al floor — allarga solo il rischio nominale
   // per trade, non tocca la logica del target.
   if(s.dir != DIR_NONE && g_atr > 0 && InpCRT_MinStopATR > 0){
      double floorDist = InpCRT_MinStopATR * g_atr;
      double curDist   = MathAbs(s.entryRef - s.slPrice);
      if(curDist > 0 && curDist < floorDist){
         if(s.dir == DIR_SELL) s.slPrice = s.entryRef + floorDist;
         else                  s.slPrice = s.entryRef - floorDist;
      }
   }
   return s;
}

#endif
