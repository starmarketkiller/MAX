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
// F-05 (fidelity report 01, Q-01 in NEXUS_CORPUS_CONCEPT_FORMALIZATION.md):
// "A zone can only be used a maximum of 2 times." Contatore per livello,
// con reset quando il livello H4 si sposta oltre la stessa tolleranza gia'
// usata altrove in questa funzione per il touch/fresh check (atrH4*0.3).
// L'eccezione della fonte per i livelli nati da un daily gap con "reazione
// forte" NON e' implementata: "strong" non e' mai quantificato da nessuna
// fonte del corpus (stesso limite gia' segnalato in M-06, S-07, T-03), e il
// codice non ha alcun rilevatore di daily gap su cui appoggiarla.
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
   // F-05: contatore utilizzi per livello (Q-01), stessa persistenza per-call di hAtrH4.
   static double s_snrLoLevel = 0; static int s_snrLoUses = 0;
   static double s_snrHiLevel = 0; static int s_snrHiUses = 0;
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
      // F-05 / Q-01: "A zone can only be used a maximum of 2 times." Livello
      // nuovo (fuori tolleranza) resetta il contatore; esaurito -> niente segnale.
      if(MathAbs(h4Lo - s_snrLoLevel) > atrH4 * 0.3){ s_snrLoLevel = h4Lo; s_snrLoUses = 0; }
      if(s_snrLoUses >= 2) return s;
      s_snrLoUses++;
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = h4Lo - 0.5 * atrH4;
      s.tpPrice = _smc_tp(s.entryRef, DIR_BUY, 2.3);
      s.score = 68.0 + (freshLo ? 5.0 : 0.0);
      if(MathAbs(h4Lo - w1Lo) <= atrH4 * 0.5){ s.score += 4.0; s.reason = freshLo ? "SNR bull fresh+story+W1" : "SNR bull tested+story+W1"; }
      else s.reason = freshLo ? "SNR bull fresh+story" : "SNR bull tested+story";
      return s;
   }
   if(h1 >= h4Hi - atrH4 * 0.4 && h1 <= h4Hi + atrH4 * 0.4 && c1 < o1 && storyBear){
      // F-05 / Q-01: stessa regola del ramo BUY, sul livello di resistenza.
      if(MathAbs(h4Hi - s_snrHiLevel) > atrH4 * 0.3){ s_snrHiLevel = h4Hi; s_snrHiUses = 0; }
      if(s_snrHiUses >= 2) return s;
      s_snrHiUses++;
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

#endif
