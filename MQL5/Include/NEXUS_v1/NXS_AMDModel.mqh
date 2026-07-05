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

// v2.0.34 (audit point 4): persistent state machine across calls, reset
// once per Asian-range day. Previously ANY close beyond the Asia range was
// immediately labeled AMD_DISTRIBUTION with no MANIPULATION phase at all,
// and AMD_REVERSAL / AMD_CONT strategies both gated on that same single
// phase - meaning they were eligible on the exact same bars, contradicting
// each other's premise. Now:
//   accumulation        -> price still inside the Asia range
//   manipulation        -> first close beyond range (not yet confirmed)
//   continuation_dist.  -> price stays beyond the SAME side for 2+ closes
//                          (accepted, not just a wick)
//   reversal_dist.       -> price closes back INSIDE the range after a
//                          manipulation - the breakout failed
ENUM_NXS_AMD g_amdPhase       = AMD_NONE;
ENUM_NXS_DIR g_amdManipDir    = DIR_NONE;
datetime     g_amdSessionDay  = 0;
int          g_amdBeyondCount = 0;

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

   // Reset the state machine once per new Asia-range day.
   if(g_amdSessionDay != midnightServer){
      g_amdSessionDay  = midnightServer;
      g_amdPhase       = AMD_ACCUMULATION;
      g_amdManipDir    = DIR_NONE;
      g_amdBeyondCount = 0;
   }

   double c1 = iClose(g_sym, InpTFEntry, 1);
   bool beyondHigh = (c1 > hi);
   bool beyondLow  = (c1 < lo);

   if(g_amdPhase == AMD_ACCUMULATION){
      if(beyondHigh)     { g_amdPhase = AMD_MANIPULATION; g_amdManipDir = DIR_BUY;  g_amdBeyondCount = 1; }
      else if(beyondLow) { g_amdPhase = AMD_MANIPULATION; g_amdManipDir = DIR_SELL; g_amdBeyondCount = 1; }
   }
   else if(g_amdPhase == AMD_MANIPULATION || g_amdPhase == AMD_CONTINUATION_DISTRIBUTION){
      bool stillBeyond = (g_amdManipDir == DIR_BUY) ? beyondHigh : beyondLow;
      if(stillBeyond){
         g_amdBeyondCount++;
         g_amdPhase = (g_amdBeyondCount >= 2) ? AMD_CONTINUATION_DISTRIBUTION : AMD_MANIPULATION;
      } else {
         // manipulation wick failed to hold - price closed back inside the range
         g_amdPhase = AMD_REVERSAL_DISTRIBUTION;
      }
   }
   else if(g_amdPhase == AMD_REVERSAL_DISTRIBUTION){
      // a fresh manipulation on the OPPOSITE side re-arms the sequence
      bool oppBeyond = (g_amdManipDir == DIR_BUY) ? beyondLow : beyondHigh;
      if(oppBeyond){
         g_amdManipDir = (g_amdManipDir == DIR_BUY) ? DIR_SELL : DIR_BUY;
         g_amdPhase = AMD_MANIPULATION;
         g_amdBeyondCount = 1;
      }
   }

   r.phase = g_amdPhase;
   switch(g_amdPhase){
      case AMD_MANIPULATION:
         // early/unconfirmed - lean toward a reversal since manipulation
         // wicks fail more often than they get accepted, but with a lower
         // modifier than a confirmed phase.
         r.expectedDir = (g_amdManipDir == DIR_BUY) ? DIR_SELL : DIR_BUY;
         r.modifier = 3.0;
         break;
      case AMD_CONTINUATION_DISTRIBUTION:
         r.expectedDir = g_amdManipDir;
         r.modifier = 8.0;
         break;
      case AMD_REVERSAL_DISTRIBUTION:
         r.expectedDir = (g_amdManipDir == DIR_BUY) ? DIR_SELL : DIR_BUY;
         r.modifier = 8.0;
         break;
      default:
         r.expectedDir = DIR_NONE;
         r.modifier = 0;
   }
   return r;
}

string NXS_AMDName(ENUM_NXS_AMD a){
   switch(a){
      case AMD_ACCUMULATION:             return "ACCUMULATION";
      case AMD_MANIPULATION:             return "MANIPULATION";
      case AMD_DISTRIBUTION:             return "DISTRIBUTION";
      case AMD_REVERSAL_DISTRIBUTION:    return "REVERSAL_DISTRIBUTION";
      case AMD_CONTINUATION_DISTRIBUTION:return "CONTINUATION_DISTRIBUTION";
   }
   return "NONE";
}

#endif
