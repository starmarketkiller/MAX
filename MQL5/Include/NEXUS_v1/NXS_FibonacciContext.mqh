//+------------------------------------------------------------------+
//|  NXS_FibonacciContext.mqh                                         |
//|  Phase 3 - OTE / premium-discount / extensions for SMC scoring    |
//+------------------------------------------------------------------+
#ifndef __NXS_FIB_CONTEXT_MQH__
#define __NXS_FIB_CONTEXT_MQH__

struct SNXSFib {
   double swingHigh;
   double swingLow;
   double mid;            // 50%
   double premium705;     // 0.705 from low
   double ote62;
   double ote705;
   double ote79;
   double ext1272;
   double ext1618;
   double ext200;
   bool   inDiscount;     // current price <= mid
   bool   inPremium;      // current price >= mid
   bool   inOTE;          // 0.62-0.79 of move
};

// Build Fib context using last NXS swing high/low from `lookback` bars on TF
SNXSFib NXS_Fib_Build(ENUM_TIMEFRAMES tf, int lookback){
   SNXSFib f; ZeroMemory(f);
   int hiIdx = iHighest(g_sym, tf, MODE_HIGH, lookback, 1);
   int loIdx = iLowest (g_sym, tf, MODE_LOW,  lookback, 1);
   f.swingHigh = iHigh(g_sym, tf, hiIdx);
   f.swingLow  = iLow (g_sym, tf, loIdx);
   if(f.swingHigh <= f.swingLow) return f;
   double range = f.swingHigh - f.swingLow;
   // Direction-aware: if last high is more recent than last low, last leg is up → OTE in discount
   bool legUp = (hiIdx < loIdx);
   if(legUp){
      f.ote62  = f.swingHigh - range * 0.62;
      f.ote705 = f.swingHigh - range * 0.705;
      f.ote79  = f.swingHigh - range * 0.79;
      f.ext1272 = f.swingHigh + range * 0.272;
      f.ext1618 = f.swingHigh + range * 0.618;
      f.ext200  = f.swingHigh + range * 1.0;
   } else {
      f.ote62  = f.swingLow + range * 0.62;
      f.ote705 = f.swingLow + range * 0.705;
      f.ote79  = f.swingLow + range * 0.79;
      f.ext1272 = f.swingLow - range * 0.272;
      f.ext1618 = f.swingLow - range * 0.618;
      f.ext200  = f.swingLow - range * 1.0;
   }
   f.mid       = (f.swingHigh + f.swingLow) * 0.5;
   f.premium705= legUp ? (f.swingLow + range * 0.705) : (f.swingHigh - range * 0.705);
   double bid  = SymbolInfoDouble(g_sym, SYMBOL_BID);
   f.inDiscount= bid <= f.mid;
   f.inPremium = bid >= f.mid;
   double oteHi = MathMax(f.ote62, f.ote79);
   double oteLo = MathMin(f.ote62, f.ote79);
   f.inOTE     = (bid >= oteLo && bid <= oteHi);
   return f;
}

#endif
