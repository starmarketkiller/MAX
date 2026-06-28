//+------------------------------------------------------------------+
//|  NXS_MarketAnalysis.mqh - Regime + liquidity sweep detection      |
//+------------------------------------------------------------------+
#ifndef __NXS_MARKET_MQH__
#define __NXS_MARKET_MQH__

struct SNXSSweep { ENUM_NXS_DIR dir; double level; bool confirmed; };

// Extended sweep info used by the new SMC strategies (Phase 3)
struct SNXSSweepExt {
   ENUM_NXS_DIR dir;
   double       level;        // sweep level (the wicked liquidity)
   double       refHigh;      // dominant reference high (PDH/EQH/AsiaHi/…)
   double       refLow;       // dominant reference low  (PDL/EQL/AsiaLo/…)
   bool         confirmed;
   bool         sweptPDH;
   bool         sweptPDL;
   bool         sweptAsiaHigh;
   bool         sweptAsiaLow;
   bool         sweptEQH;
   bool         sweptEQL;
};

ENUM_NXS_REGIME NXS_DetectRegime(){
   if(g_adx <= 0 || g_atr <= 0) return REGIME_UNKNOWN;
   double atrPrev = 0;
   double a[]; if(CopyBuffer(g_hATR, 0, 2, 20, a) > 0){
      double s = 0; int n = ArraySize(a); for(int i=0;i<n;i++) s += a[i];
      atrPrev = (n>0) ? s/n : 0;
   }
   bool volatile_ = (atrPrev > 0 && g_atr > atrPrev * 1.5);
   if(g_adx >= 30) return volatile_ ? REGIME_VOLATILE : REGIME_STRONG_TREND;
   if(g_adx >= 20) return REGIME_WEAK_TREND;
   if(g_adx <  15 && volatile_) return REGIME_CHOPPY;
   return REGIME_RANGING;
}

SNXSSweep NXS_DetectSweep(){
   SNXSSweep s; s.dir = DIR_NONE; s.level = 0; s.confirmed = false;
   int lookback = 20;
   double hi = iHigh(g_sym, InpTFEntry, iHighest(g_sym, InpTFEntry, MODE_HIGH, lookback, 2));
   double lo = iLow (g_sym, InpTFEntry, iLowest (g_sym, InpTFEntry, MODE_LOW,  lookback, 2));
   double h1 = iHigh(g_sym, InpTFEntry, 1);
   double l1 = iLow (g_sym, InpTFEntry, 1);
   double c1 = iClose(g_sym, InpTFEntry, 1);
   if(h1 > hi && c1 < hi){
      s.dir = DIR_SELL; s.level = hi; s.confirmed = true;
   } else if(l1 < lo && c1 > lo){
      s.dir = DIR_BUY;  s.level = lo; s.confirmed = true;
   }
   return s;
}

string NXS_RegimeName(ENUM_NXS_REGIME r){
   switch(r){
      case REGIME_STRONG_TREND: return "STRONG_TREND";
      case REGIME_WEAK_TREND:   return "WEAK_TREND";
      case REGIME_RANGING:      return "RANGING";
      case REGIME_VOLATILE:     return "VOLATILE";
      case REGIME_CHOPPY:       return "CHOPPY";
   }
   return "UNKNOWN";
}

string NXS_DirName(ENUM_NXS_DIR d){
   if(d == DIR_BUY)  return "BUY";
   if(d == DIR_SELL) return "SELL";
   return "NONE";
}

// ---- Phase 3 extended sweep detector -------------------------------
// Returns liquidity sweeps against PDH/PDL, Asia H/L and equal highs/lows.
SNXSSweepExt NXS_DetectSweepExt(){
   SNXSSweepExt s; ZeroMemory(s); s.dir = DIR_NONE;
   // Yesterday's daily H/L (PDH/PDL)
   double pdh = iHigh(g_sym, PERIOD_D1, 1);
   double pdl = iLow (g_sym, PERIOD_D1, 1);
   // Asia session high/low: scan last 24h of M5 between InpAsianStartHour..InpAsianEndHour
   double asiaHi = 0, asiaLo = DBL_MAX;
   for(int i = 1; i <= 96; i++){
      datetime t = iTime(g_sym, PERIOD_M15, i);
      // AUDITPATCH: Inputs are GMT hours; historical bars are broker/server time.
      datetime tGMT = (datetime)((long)t - (long)InpServerGMTOffset * 3600);
      MqlDateTime mt; TimeToStruct(tGMT, mt);
      if(mt.hour >= InpAsianStartHour && mt.hour <= InpAsianEndHour){
         double hh = iHigh(g_sym, PERIOD_M15, i);
         double ll = iLow (g_sym, PERIOD_M15, i);
         if(hh > asiaHi) asiaHi = hh;
         if(ll < asiaLo) asiaLo = ll;
      }
   }
   if(asiaLo == DBL_MAX) asiaLo = pdl;
   if(asiaHi == 0)       asiaHi = pdh;
   // Equal highs/lows on entry TF (recent cluster within 0.2*ATR)
   double eqH = iHigh(g_sym, InpTFEntry, iHighest(g_sym, InpTFEntry, MODE_HIGH, 30, 2));
   double eqL = iLow (g_sym, InpTFEntry, iLowest (g_sym, InpTFEntry, MODE_LOW,  30, 2));
   double h1 = iHigh(g_sym, InpTFEntry, 1);
   double l1 = iLow (g_sym, InpTFEntry, 1);
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double atr = g_atr > 0 ? g_atr : SymbolInfoDouble(g_sym, SYMBOL_POINT) * 100;
   double tol = atr * 0.2;
   // Sweep evaluation: wick beyond level + close back inside
   if(h1 > pdh    && c1 < pdh    ){ s.sweptPDH = true;       s.dir = DIR_SELL; s.level = pdh;    s.confirmed = true; }
   if(l1 < pdl    && c1 > pdl    ){ s.sweptPDL = true;       s.dir = DIR_BUY;  s.level = pdl;    s.confirmed = true; }
   if(h1 > asiaHi && c1 < asiaHi ){ s.sweptAsiaHigh = true;  s.dir = DIR_SELL; s.level = asiaHi; s.confirmed = true; }
   if(l1 < asiaLo && c1 > asiaLo ){ s.sweptAsiaLow  = true;  s.dir = DIR_BUY;  s.level = asiaLo; s.confirmed = true; }
   if(h1 > eqH - tol && h1 > eqH && c1 < eqH){ s.sweptEQH = true; if(s.dir == DIR_NONE){ s.dir = DIR_SELL; s.level = eqH; s.confirmed = true; } }
   if(l1 < eqL + tol && l1 < eqL && c1 > eqL){ s.sweptEQL = true; if(s.dir == DIR_NONE){ s.dir = DIR_BUY;  s.level = eqL; s.confirmed = true; } }
   s.refHigh = (s.sweptPDH ? pdh : (s.sweptAsiaHigh ? asiaHi : (s.sweptEQH ? eqH : MathMax(pdh, asiaHi))));
   s.refLow  = (s.sweptPDL ? pdl : (s.sweptAsiaLow  ? asiaLo : (s.sweptEQL ? eqL : MathMin(pdl, asiaLo))));
   return s;
}

#endif
