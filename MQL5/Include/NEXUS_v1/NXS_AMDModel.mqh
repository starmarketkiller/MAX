//+------------------------------------------------------------------+
//|  NXS_AMDModel.mqh - Asian range / Manipulation / Distribution     |
//+------------------------------------------------------------------+
#ifndef __NXS_AMD_MQH__
#define __NXS_AMD_MQH__

struct SNXSAMD {
   ENUM_NXS_AMD phase;
   double       asianHigh;
   double       asianLow;
   ENUM_NXS_DIR expectedDir;
   double       modifier;
};

SNXSAMD NXS_GetAMD(){
   SNXSAMD r; r.phase = AMD_NONE; r.asianHigh = 0; r.asianLow = 0;
   r.expectedDir = DIR_NONE; r.modifier = 0;
   if(!InpUseAMD) return r;

   // v2.0.5b: compute asianStart in server-time, but use GMT-anchored hour window
   MqlDateTime mt; TimeToStruct(TimeCurrent(), mt);
   datetime midnightServer = StructToTime(mt);
   midnightServer -= mt.hour * 3600 + mt.min * 60 + mt.sec;
   // Asian hours are defined in GMT in Inputs → convert to server time
   datetime asianStart = midnightServer + (InpAsianStartHour + InpServerGMTOffset) * 3600;
   datetime asianEnd   = midnightServer + (InpAsianEndHour   + InpServerGMTOffset) * 3600;
   if(asianEnd > TimeCurrent()) return r;

   int barsBack = (int)((TimeCurrent() - asianStart) / PeriodSeconds(InpTFEntry)) + 4;
   if(barsBack < 8) barsBack = 8;
   double hi = -DBL_MAX, lo = DBL_MAX;
   for(int i = 1; i < barsBack; i++){
      datetime t = iTime(g_sym, InpTFEntry, i);
      if(t < asianStart || t > asianEnd) continue;
      hi = MathMax(hi, iHigh(g_sym, InpTFEntry, i));
      lo = MathMin(lo, iLow (g_sym, InpTFEntry, i));
   }
   if(hi == -DBL_MAX || lo == DBL_MAX) return r;
   r.asianHigh = hi; r.asianLow = lo;

   double now = SymbolInfoDouble(g_sym, SYMBOL_BID);
   if(now > hi){
      r.phase = AMD_DISTRIBUTION;
      r.expectedDir = DIR_BUY;
      r.modifier = 8.0;
   } else if(now < lo){
      r.phase = AMD_DISTRIBUTION;
      r.expectedDir = DIR_SELL;
      r.modifier = 8.0;
   } else {
      r.phase = AMD_ACCUMULATION;
      r.modifier = 0;
   }
   return r;
}

string NXS_AMDName(ENUM_NXS_AMD a){
   switch(a){
      case AMD_ACCUMULATION: return "ACCUMULATION";
      case AMD_MANIPULATION: return "MANIPULATION";
      case AMD_DISTRIBUTION: return "DISTRIBUTION";
   }
   return "NONE";
}

#endif
