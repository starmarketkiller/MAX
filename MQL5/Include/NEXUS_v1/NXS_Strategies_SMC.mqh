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
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double o1 = iOpen (g_sym, InpTFEntry, 1);
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
   double h2 = iHigh(g_sym, InpTFEntry, 2), l2 = iLow(g_sym, InpTFEntry, 2);
   double h4 = iHigh(g_sym, InpTFEntry, 4), l4 = iLow(g_sym, InpTFEntry, 4);
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double o1 = iOpen (g_sym, InpTFEntry, 1);
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
   double h2 = iHigh(g_sym, InpTFEntry, 5), l2 = iLow(g_sym, InpTFEntry, 5);
   double h0 = iHigh(g_sym, InpTFEntry, 7), l0 = iLow(g_sym, InpTFEntry, 7);
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double atr = _smc_atr();
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double o1 = iOpen (g_sym, InpTFEntry, 1);
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
SNXSSignal NXS_Strat_SH_BMS_RTO(SNXSSweepExt &sw){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "SH_BMS_RTO";
   if(!sw.confirmed) return s;
   // AUDITPATCH: 3-candle FVG (bars 4 and 2), plus the BMS that the
   // strategy name promises. The prior adjacent-candle gap was exceptionally rare.
   double h2 = iHigh(g_sym, InpTFEntry, 2), l2 = iLow(g_sym, InpTFEntry, 2);
   double h4 = iHigh(g_sym, InpTFEntry, 4), l4 = iLow(g_sym, InpTFEntry, 4);
   double atr = _smc_atr();
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   bool bullFVG = (l2 > h4 + atr * 0.1);
   bool bearFVG = (h2 < l4 - atr * 0.1);
   if(sw.dir == DIR_BUY && g_struct.chochUp && bullFVG && bid >= h4 && bid <= l2){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = MathMin(sw.level, h4) - 0.5 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_BUY, 2.6);
      s.score = 74.0; s.reason = "SH+BMS+RTO bull";
      return s;
   }
   if(sw.dir == DIR_SELL && g_struct.chochDown && bearFVG && bid >= h2 && bid <= l4){
      s.dir = DIR_SELL; s.entryRef = bid;
      s.slPrice = MathMax(sw.level, l4) + 0.5 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_SELL, 2.6);
      s.score = 74.0; s.reason = "SH+BMS+RTO bear";
      return s;
   }
   return s;
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
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double o1 = iOpen (g_sym, InpTFEntry, 1);
   double bodyAbs = MathAbs(c1 - o1);
   bool rejectionBull = (c1 > o1) && bodyAbs > atr * 0.3;
   bool rejectionBear = (c1 < o1) && bodyAbs > atr * 0.3;
   // Quick HH/LH/LL/HL via iHighest/iLowest in two windows
   int    hiIdxA = iHighest(g_sym, InpTFEntry, MODE_HIGH, 10, 1);
   int    hiIdxB = iHighest(g_sym, InpTFEntry, MODE_HIGH, 20, 11);
   int    loIdxA = iLowest (g_sym, InpTFEntry, MODE_LOW,  10, 1);
   int    loIdxB = iLowest (g_sym, InpTFEntry, MODE_LOW,  20, 11);
   double hi_recent = iHigh(g_sym, InpTFEntry, hiIdxA);
   double hi_older  = iHigh(g_sym, InpTFEntry, hiIdxB);
   double lo_recent = iLow (g_sym, InpTFEntry, loIdxA);
   double lo_older  = iLow (g_sym, InpTFEntry, loIdxB);
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
SNXSSignal NXS_Strat_SilverBullet(SNXSSweepExt &sw){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "SILVER_BULLET";
   // v2.0.5b: GMT-corrected killzones (server time → GMT)
   datetime gmtNow = (datetime)((long)TimeCurrent() - (long)InpServerGMTOffset * 3600);
   MqlDateTime mt; TimeToStruct(gmtNow, mt);
   int h = mt.hour;
   bool killzoneLO = (h >= 10 && h < 11);   // London KZ 10-11 GMT
   bool killzoneNY = (h >= 14 && h < 15);   // NY KZ 14-15 GMT
   if(!(killzoneLO || killzoneNY)) return s;
   if(!sw.confirmed) return s;
   double atr = _smc_atr();
   if(sw.dir == DIR_BUY){
      s.dir = DIR_BUY;  s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = sw.level - 0.6 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_BUY, 2.8);
      s.score = 76.0; s.reason = killzoneLO ? "SB:LO-KZ bull" : "SB:NY-KZ bull";
   } else if(sw.dir == DIR_SELL){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = sw.level + 0.6 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_SELL, 2.8);
      s.score = 76.0; s.reason = killzoneLO ? "SB:LO-KZ bear" : "SB:NY-KZ bear";
   }
   return s;
}

// === 8. AMD REVERSAL ==================================================
// Manipulation above Asia High → SELL on reclaim+MSS (mirror for low)
SNXSSignal NXS_Strat_AMD_Reversal(SNXSSweepExt &sw, SNXSAMD &amd){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "AMD_REVERSAL";
   if(amd.phase != AMD_MANIPULATION && amd.phase != AMD_DISTRIBUTION) return s;
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
SNXSSignal NXS_Strat_OTE_Continuation(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "OTE_CONT";
   SNXSFib f = NXS_Fib_Build(InpTFMedium, 30);
   if(!f.inOTE) return s;
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double atr = _smc_atr();
   // v2.0.6: strict alignment con struttura. Range (trend==0) → niente trade.
   if(g_struct.trend == 1 && f.inDiscount && bid < f.mid){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = f.swingLow - 0.3 * atr;
      s.tpPrice = MathMax(f.swingHigh, _smc_tp(s.entryRef, DIR_BUY, 2.2));
      s.score = 69.0; s.reason = "OTE 0.62-0.79 disc+trend";
      return s;
   }
   if(g_struct.trend == -1 && f.inPremium && bid > f.mid){
      s.dir = DIR_SELL; s.entryRef = bid;
      s.slPrice = f.swingHigh + 0.3 * atr;
      s.tpPrice = MathMin(f.swingLow, _smc_tp(s.entryRef, DIR_SELL, 2.2));
      s.score = 69.0; s.reason = "OTE 0.62-0.79 prem+trend";
      return s;
   }
   return s;
}

// === 10. MALAYSIAN SNR (v2.0.3 — body-based + fresh/flipped + storyline) ====
// Storyline: Weekly + Daily + H4 supportano? H1 entry su rejection candle body forte.
// Fresh = livello non testato negli ultimi 20 bar H4 → bonus +5
// Flipped = livello che era resistance e ora supporta (close-above) → SBR (Support-Becomes-Resistance) o RBS.
SNXSSignal NXS_Strat_MalaysianSNR_Rejection(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "MALAYSIAN_SNR";
   // v2.0.6: skip Asia (bassa volatilità ⇒ falsi segnali su H4 SR body-based)
   if(g_session == SESS_ASIAN) return s;
   double atr = _smc_atr();
   // Body-based levels (close, not wick) on H4 and W1
   int idxH4Hi = iHighest(g_sym, InpTFHigh, MODE_CLOSE, 12, 1);
   int idxH4Lo = iLowest (g_sym, InpTFHigh, MODE_CLOSE, 12, 1);
   double h4Hi = iClose(g_sym, InpTFHigh, idxH4Hi);
   double h4Lo = iClose(g_sym, InpTFHigh, idxH4Lo);
   int idxW1Hi = iHighest(g_sym, PERIOD_W1, MODE_CLOSE, 8, 1);
   int idxW1Lo = iLowest (g_sym, PERIOD_W1, MODE_CLOSE, 8, 1);
   double w1Hi = iClose(g_sym, PERIOD_W1, idxW1Hi);
   double w1Lo = iClose(g_sym, PERIOD_W1, idxW1Lo);
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double o1 = iOpen (g_sym, InpTFEntry, 1);
   double bodyAbs = MathAbs(c1 - o1);
   if(bodyAbs <= atr * 0.5) return s;          // require strong body
   // Fresh check: did price already touch this level in last 20 H4 bars?
   bool freshHi = true, freshLo = true;
   for(int i = 1; i <= 20; i++){
      double hh = iHigh(g_sym, InpTFHigh, i);
      double ll = iLow (g_sym, InpTFHigh, i);
      if(hh >= h4Hi - atr * 0.3 && hh <= h4Hi + atr * 0.3 && i > 3) freshHi = false;
      if(ll >= h4Lo - atr * 0.3 && ll <= h4Lo + atr * 0.3 && i > 3) freshLo = false;
   }
   // AUDITPATCH: storyline is directional context, not the current location.
   // The previous test required a BUY to be both near the H4 range low and above
   // the H4 midpoint (and the SELL mirror), which is usually contradictory.
   double h4C1 = iClose(g_sym, InpTFHigh, 1);
   double h4C4 = iClose(g_sym, InpTFHigh, 4);
   double d1C1 = iClose(g_sym, PERIOD_D1, 1);
   double d1C2 = iClose(g_sym, PERIOD_D1, 2);
   bool storyBull = (h4C1 > h4C4 && d1C1 >= d1C2);
   bool storyBear = (h4C1 < h4C4 && d1C1 <= d1C2);
   // BUY at support
   if(MathAbs(bid - h4Lo) < atr * 0.4 && c1 > o1 && storyBull){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = h4Lo - 0.5 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_BUY, 2.3);
      s.score = 68.0 + (freshLo ? 5.0 : 0.0);
      s.reason = freshLo ? "SNR bull fresh+story" : "SNR bull tested+story";
      return s;
   }
   if(MathAbs(bid - h4Hi) < atr * 0.4 && c1 < o1 && storyBear){
      s.dir = DIR_SELL; s.entryRef = bid;
      s.slPrice = h4Hi + 0.5 * atr;
      s.tpPrice = _smc_tp(s.entryRef, DIR_SELL, 2.3);
      s.score = 68.0 + (freshHi ? 5.0 : 0.0);
      s.reason = freshHi ? "SNR bear fresh+story" : "SNR bear tested+story";
      return s;
   }
   return s;
}

#endif
