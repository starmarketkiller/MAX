//+------------------------------------------------------------------+
//|  NXS_MTFSpreadVol.mqh - Audit PDF gaps: MTF validation,           |
//|  dynamic spread filter, volatility regime detection.              |
//+------------------------------------------------------------------+
#ifndef __NXS_MTF_SPREAD_VOL_MQH__
#define __NXS_MTF_SPREAD_VOL_MQH__

// ----- Volatility regimes -----
#define NXS_VOL_LOW    0
#define NXS_VOL_NORMAL 1
#define NXS_VOL_HIGH   2

// Indicator handles for MTF (created in OnInit hook)
int g_hEMA_MTF_1 = INVALID_HANDLE;
int g_hEMA_MTF_2 = INVALID_HANDLE;

bool NXS_MTF_CreateHandles(){
   if(!InpUseMTFValidation) return true;
   g_hEMA_MTF_1 = iMA(g_sym, InpMTF_TF1, 50, 0, MODE_EMA, PRICE_CLOSE);
   g_hEMA_MTF_2 = iMA(g_sym, InpMTF_TF2, 50, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hEMA_MTF_1 == INVALID_HANDLE || g_hEMA_MTF_2 == INVALID_HANDLE){
      Print("[NEXUS MTF] WARNING: failed to create MTF EMA handles");
      return false;
   }
   return true;
}

void NXS_MTF_ReleaseHandles(){
   if(g_hEMA_MTF_1 != INVALID_HANDLE) IndicatorRelease(g_hEMA_MTF_1);
   if(g_hEMA_MTF_2 != INVALID_HANDLE) IndicatorRelease(g_hEMA_MTF_2);
}

// Returns +1 if both TFs are bullish (close > EMA50), -1 if both bearish, 0 mixed.
int NXS_MTF_Bias(){
   if(!InpUseMTFValidation) return 0;
   double e1[], e2[];
   if(CopyBuffer(g_hEMA_MTF_1, 0, 1, 1, e1) <= 0) return 0;
   if(CopyBuffer(g_hEMA_MTF_2, 0, 1, 1, e2) <= 0) return 0;
   double c1 = iClose(g_sym, InpMTF_TF1, 1);
   double c2 = iClose(g_sym, InpMTF_TF2, 1);
   bool bull = (c1 > e1[0]) && (c2 > e2[0]);
   bool bear = (c1 < e1[0]) && (c2 < e2[0]);
   if(bull) return +1;
   if(bear) return -1;
   return 0;
}

// Returns true if `direction` (+1 BUY, -1 SELL) is aligned with MTF (or no MTF filter).
// Phase 1: respects InpMTFMixedMode (0=block, 1=penalty in router, 2=allow).
bool NXS_MTF_Aligned(int direction){
   if(!InpUseMTFValidation) return true;
   int b = NXS_MTF_Bias();
   if(b == direction) return true;
   if(b == 0){
      // mixed: only hard-block if mode == 0; modes 1/2 let signal through and
      // the router applies a score penalty (handled in NXS_MTF_FamilyFactor).
      return (InpMTFMixedMode != 0);
   }
   return false;  // counter-trend on a clear bias → still blocks
}

// ===================================================================
//   Dynamic spread filter (gold-aware)
// ===================================================================
double NXS_CurrentSpreadPoints(){
   double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double pt  = g_point > 0 ? g_point : SymbolInfoDouble(g_sym, SYMBOL_POINT);
   if(pt <= 0) return 0;
   return (ask - bid) / pt;
}

bool NXS_SpreadOK(){
   if(!InpUseDynamicSpread) return true;
   double sp = NXS_CurrentSpreadPoints();

   // AUDITPATCH: 0 means use the symbol profile (FX/metal/index/crypto), rather
   // than silently applying the same 50-point ceiling to every asset class.
   int pointCap = InpMaxSpreadPoints;
   if(pointCap <= 0) pointCap = g_profile.maxSpreadPts;
   if(pointCap > 0 && sp > pointCap) return false;

   // Dynamic vs ATR. NXS_SpreadCapATRPct() already implements the crypto
   // override; previously it existed but was never called by this gate.
   if(g_atr > 0){
      double spreadPrice = sp * g_point;
      double pctOfAtr    = (spreadPrice / g_atr) * 100.0;
      double atrPctCap   = NXS_SpreadCapATRPct();
      if(atrPctCap > 0 && pctOfAtr > atrPctCap) return false;
   }
   return true;
}

// ===================================================================
//   Volatility regime
// ===================================================================
int NXS_VolatilityRegime(){
   if(!InpUseVolRegime) return NXS_VOL_NORMAL;
   double price = SymbolInfoDouble(g_sym, SYMBOL_BID);
   if(g_atr <= 0 || price <= 0) return NXS_VOL_NORMAL;
   double atrPct = (g_atr / price) * 100.0;
   if(atrPct < InpLowVolAtrPct)  return NXS_VOL_LOW;
   if(atrPct > InpHighVolAtrPct) return NXS_VOL_HIGH;
   return NXS_VOL_NORMAL;
}

string NXS_VolRegimeStr(){
   switch(NXS_VolatilityRegime()){
      case NXS_VOL_LOW:    return "LOW";
      case NXS_VOL_HIGH:   return "HIGH";
      default:             return "NORMAL";
   }
}

#endif
