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
      double o = iOpen (g_sym, InpTFEntry, i);
      double c = iClose(g_sym, InpTFEntry, i);
      double h = iHigh (g_sym, InpTFEntry, i);
      double l = iLow  (g_sym, InpTFEntry, i);
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
      double o = iOpen (g_sym, InpTFEntry, i);
      double c = iClose(g_sym, InpTFEntry, i);
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
SNXSSignal NXS_Strat_CISD(SNXSSweepExt &sw){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "CISD";
   if(!InpUseStrat_CISD) return s;
   double atr = _inst_atr();
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double o1 = iOpen (g_sym, InpTFEntry, 1);
   double bodyAbs = MathAbs(c1 - o1);
   if(bodyAbs < atr * 0.7) return s;     // require displacement candle

   // BUY: previously bearish delivery + sweep low + reclaim last bearish delivery high
   double bearHi=0, bearLo=0;
   if(c1 > o1 && _inst_lastDelivery(-1, 15, bearHi, bearLo)){
      bool sweptLow  = (sw.sweptPDL || sw.sweptEQL || sw.sweptAsiaLow || sw.dir == DIR_BUY);
      if(sweptLow && c1 > bearHi){
         s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
         s.slPrice = (sw.confirmed ? sw.level : bearLo) - 0.4 * atr;
         s.tpPrice = s.entryRef + 2.5 * (s.entryRef - s.slPrice);
         s.score   = 74.0;
         s.reason  = "CISD bull:sweep+reclaim";
         return s;
      }
   }
   // SELL: previously bullish delivery + sweep high + reclaim last bullish delivery low
   double bullHi=0, bullLo=0;
   if(c1 < o1 && _inst_lastDelivery(+1, 15, bullHi, bullLo)){
      bool sweptHigh = (sw.sweptPDH || sw.sweptEQH || sw.sweptAsiaHigh || sw.dir == DIR_SELL);
      if(sweptHigh && c1 < bullLo){
         s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
         s.slPrice = (sw.confirmed ? sw.level : bullHi) + 0.4 * atr;
         s.tpPrice = s.entryRef - 2.5 * (s.slPrice - s.entryRef);
         s.score   = 74.0;
         s.reason  = "CISD bear:sweep+reclaim";
         return s;
      }
   }
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
   if(amd.phase != AMD_DISTRIBUTION) return s;
   if(!(g_session == SESS_LONDON || g_session == SESS_OVERLAP || g_session == SESS_NY)) return s;

   double atr = _inst_atr();
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double mid = (amd.asianHigh + amd.asianLow) * 0.5;

   // BUY: distribution above Asian range + retest near asianHigh + htf bull/neutral
   if(c1 > amd.asianHigh && bid <= amd.asianHigh + atr * 0.6
      && (htf.bias == HTF_BULL || htf.bias == HTF_NEUTRAL)){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = MathMin(amd.asianHigh - 0.3 * atr, mid);
      s.tpPrice = s.entryRef + 2.4 * (s.entryRef - s.slPrice);
      s.score   = 72.0;
      s.reason  = "AMD_CONT bull:asiaHi retest";
      return s;
   }
   // SELL mirror
   if(c1 < amd.asianLow && bid >= amd.asianLow - atr * 0.6
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
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double l1 = iLow  (g_sym, InpTFEntry, 1);
   double h1 = iHigh (g_sym, InpTFEntry, 1);

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
   double c1 = iClose(g_sym, InpTFEntry, 1);

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

// =================================================================
// 5. NY REVERSAL  (mirror of LdnReversal, NY hours only, considers London HoD/LoD)
// =================================================================
SNXSSignal NXS_Strat_NYReversal(SNXSSweepExt &sw){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "NY_REVERSAL";
   if(!InpUseStrat_NYReversal) return s;
   if(g_session != SESS_NY && g_session != SESS_OVERLAP) return s;
   double atr = _inst_atr();
   double c1 = iClose(g_sym, InpTFEntry, 1);

   // London HoD/LoD proxy: highest/lowest of last 24 entry-TF bars during London (06-12 GMT)
   double londonHi = -DBL_MAX, londonLo = DBL_MAX;
   for(int i = 1; i <= 48; i++){
      datetime t = iTime(g_sym, InpTFEntry, i);
      datetime tGmt = (datetime)((long)t - (long)InpServerGMTOffset * 3600);
      MqlDateTime mt; TimeToStruct(tGmt, mt);
      if(mt.hour >= 6 && mt.hour < 12){
         londonHi = MathMax(londonHi, iHigh(g_sym, InpTFEntry, i));
         londonLo = MathMin(londonLo, iLow (g_sym, InpTFEntry, i));
      }
   }
   if(londonHi == -DBL_MAX || londonLo == DBL_MAX) return s;

   // SELL: NY sweep > londonHi + close back + chochDown
   double h1 = iHigh(g_sym, InpTFEntry, 1);
   double l1 = iLow (g_sym, InpTFEntry, 1);
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
SNXSSignal NXS_Strat_WeeklyRangeExp(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "WEEKLY_EXP";
   if(!InpUseStrat_WeeklyExp) return s;
   double atr = _inst_atr();
   // PWH/PWL = previous week (W1, shift 1)
   double pwh = iHigh(g_sym, PERIOD_W1, 1);
   double pwl = iLow (g_sym, PERIOD_W1, 1);
   double wOpen = iOpen(g_sym, PERIOD_W1, 0);   // current week open
   if(pwh <= 0 || pwl <= 0 || wOpen <= 0) return s;
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);

   // displacement candle on H4 (medium TF) — use g_atr as proxy
   // (avoid iATR(...) which returns a handle, not a value)
   double atrM = atr;
   double cH4 = iClose(g_sym, InpTFHigh, 1);
   double oH4 = iOpen (g_sym, InpTFHigh, 1);
   double bH4 = MathAbs(cH4 - oH4);
   if(bH4 < atrM * 0.8) return s;

   // BUY: weekly discount (below midpoint), bullish 4H displacement, weekly open reclaim
   double wMid = (pwh + pwl) * 0.5;
   if(bid < wMid && cH4 > oH4 && bid > wOpen && g_struct.chochUp){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = MathMin(pwl, bid - 1.5 * atr);
      // v2.0.9 P3 #25: Fibonacci 1.272 extension target if strong leg
      double leg = pwh - pwl;
      double fib1272 = pwh + 0.272 * leg;
      s.tpPrice = MathMax(MathMax(pwh, fib1272), s.entryRef + 2.6 * (s.entryRef - s.slPrice));
      s.score   = 70.0;
      s.reason  = "WK-EXP bull:disc+disp+fib1.272";
      return s;
   }
   // SELL mirror
   if(bid > wMid && cH4 < oH4 && bid < wOpen && g_struct.chochDown){
      s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      s.slPrice = MathMax(pwh, bid + 1.5 * atr);
      double leg = pwh - pwl;
      double fib1272 = pwl - 0.272 * leg;
      s.tpPrice = MathMin(MathMin(pwl, fib1272), s.entryRef - 2.6 * (s.slPrice - s.entryRef));
      s.score   = 70.0;
      s.reason  = "WK-EXP bear:prem+disp+fib1.272";
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
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double o1 = iOpen (g_sym, InpTFEntry, 1);
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

   // Bullish void = recent strong displacement bar that left an FVG above (l[i+1] > h[i+3])
   int dispIdx = _inst_displacementBar(+1, 12, 1.2);
   if(dispIdx > 0 && htf.bias == HTF_BULL){
      // FVG from (dispIdx) range
      double h_disp = iHigh(g_sym, InpTFEntry, dispIdx);
      double l_disp = iLow (g_sym, InpTFEntry, dispIdx);
      double voidHi = h_disp;
      double voidLo = iHigh(g_sym, InpTFEntry, dispIdx + 2);
      if(voidHi > voidLo + atr * 0.3){
         double ce = (voidHi + voidLo) * 0.5;     // consequent encroachment 50%
         double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
         double c1 = iClose(g_sym, InpTFEntry, 1);
         double o1 = iOpen (g_sym, InpTFEntry, 1);
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
   int dispIdxB = _inst_displacementBar(-1, 12, 1.2);
   if(dispIdxB > 0 && htf.bias == HTF_BEAR){
      double l_disp = iLow (g_sym, InpTFEntry, dispIdxB);
      double voidLo = l_disp;
      double voidHi = iLow(g_sym, InpTFEntry, dispIdxB + 2);
      if(voidHi > voidLo + atr * 0.3){
         double ce = (voidHi + voidLo) * 0.5;
         double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
         double c1 = iClose(g_sym, InpTFEntry, 1);
         double o1 = iOpen (g_sym, InpTFEntry, 1);
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
SNXSSignal NXS_Strat_DisplacementRebalance(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "DISP_REBAL";
   if(!InpUseStrat_DispRebal) return s;
   double atr = _inst_atr();
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double o1 = iOpen (g_sym, InpTFEntry, 1);

   // BUY: strong bullish displacement (body > 1.3 ATR) + retracement to 50% + reaction
   int dispIdx = _inst_displacementBar(+1, 8, 1.3);
   if(dispIdx > 0){
      double dh = iHigh(g_sym, InpTFEntry, dispIdx);
      double dl = iLow (g_sym, InpTFEntry, dispIdx);
      double mid = (dh + dl) * 0.5;
      if(bid >= dl && bid <= mid + atr * 0.2 && c1 > o1){
         s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
         s.slPrice = dl - 0.3 * atr;
         s.tpPrice = MathMax(dh + 0.8 * (dh - dl), s.entryRef + 2.4 * (s.entryRef - s.slPrice));
         s.score   = 72.0;
         s.reason  = "DISP-REBAL bull:50% CE";
         return s;
      }
   }
   int dispIdxB = _inst_displacementBar(-1, 8, 1.3);
   if(dispIdxB > 0){
      double dh = iHigh(g_sym, InpTFEntry, dispIdxB);
      double dl = iLow (g_sym, InpTFEntry, dispIdxB);
      double mid = (dh + dl) * 0.5;
      if(bid <= dh && bid >= mid - atr * 0.2 && c1 < o1){
         s.dir = DIR_SELL; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
         s.slPrice = dh + 0.3 * atr;
         s.tpPrice = MathMin(dl - 0.8 * (dh - dl), s.entryRef - 2.4 * (s.slPrice - s.entryRef));
         s.score   = 72.0;
         s.reason  = "DISP-REBAL bear:50% CE";
         return s;
      }
   }
   return s;
}

// =================================================================
// 10. RANGE FADE (v2.0.8) — mean revert sui range stretti
// =================================================================
SNXSSignal NXS_Strat_RangeFade(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "RANGE_FADE";
   if(!InpUseStrat_RangeFade) return s;
   double atr = _inst_atr();
   // require compressed market: ADX<20 + velocity neutral
   if(g_adx >= 20.0) return s;
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double o1 = iOpen (g_sym, InpTFEntry, 1);
   double h1 = iHigh (g_sym, InpTFEntry, 1);
   double l1 = iLow  (g_sym, InpTFEntry, 1);
   double body = MathAbs(c1 - o1);
   if(body < atr * 0.25) return s;          // require some rejection candle

   // Range extremes — use last 40 bars
   int hiIdx = iHighest(g_sym, InpTFEntry, MODE_HIGH, 40, 2);
   int loIdx = iLowest (g_sym, InpTFEntry, MODE_LOW,  40, 2);
   if(hiIdx < 0 || loIdx < 0) return s;
   double rngHi = iHigh(g_sym, InpTFEntry, hiIdx);
   double rngLo = iLow (g_sym, InpTFEntry, loIdx);
   double rngMid = (rngHi + rngLo) * 0.5;
   double rngSize = rngHi - rngLo;
   if(rngSize < atr * 1.5) return s;        // range too tight (no edge)

   // BUY: bid near low + bullish rejection
   if(bid <= rngLo + 0.4 * atr && c1 > o1 && c1 > rngLo){
      s.dir = DIR_BUY; s.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      s.slPrice = MathMin(l1, rngLo) - 0.4 * atr;
      s.tpPrice = MathMin(rngMid, s.entryRef + 2.0 * (s.entryRef - s.slPrice));
      s.score   = 68.0;
      s.reason  = "RANGE_FADE bull:lowReject";
      return s;
   }
   // SELL: bid near high + bearish rejection
   if(bid >= rngHi - 0.4 * atr && c1 < o1 && c1 < rngHi){
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