//+------------------------------------------------------------------+
//|  NXS_HTFBias.mqh - Higher TF bias with reversal exception         |
//+------------------------------------------------------------------+
#ifndef __NXS_HTFBIAS_MQH__
#define __NXS_HTFBIAS_MQH__

struct SNXSHTF { ENUM_NXS_HTF bias; double conf; bool reversalAllowed; };

double _bufVal(int h, int buf, int shift){
   double a[];
   if(CopyBuffer(h, buf, shift, 1, a) <= 0) return 0;
   return a[0];
}

SNXSHTF NXS_GetHTFBias(){
   SNXSHTF r; r.bias = HTF_NEUTRAL; r.conf = 0.0; r.reversalAllowed = false;
   if(!g_run_UseHTFBias){ r.bias = HTF_NEUTRAL; r.conf = 1.0; return r; }

   double emaH = _bufVal(g_hEMA_HTF, 0, 1);
   double emaM = _bufVal(g_hEMA_MTF, 0, 1);
   double close= iClose(g_sym, InpTFHigh, 1);
   if(emaH <= 0 || emaM <= 0 || close <= 0) return r;

   bool bull = (close > emaH && emaM > emaH);
   bool bear = (close < emaH && emaM < emaH);
   if(bull){ r.bias = HTF_BULL; r.conf = 0.7; }
   else if(bear){ r.bias = HTF_BEAR; r.conf = 0.7; }
   else { r.bias = HTF_NEUTRAL; r.conf = 0.4; }

   // Reversal-at-structure exception
   if(InpHTF_AllowReversal){
      double pdH = iHigh(g_sym, PERIOD_D1, 1);
      double pdL = iLow(g_sym,  PERIOD_D1, 1);
      double now = SymbolInfoDouble(g_sym, SYMBOL_BID);
      double dist = MathMax(g_atr * 0.5, 1.0 * g_point);
      if(MathAbs(now - pdH) <= dist || MathAbs(now - pdL) <= dist){
         r.reversalAllowed = true;
      }
   }
   return r;
}

bool NXS_HTFBlocks(ENUM_NXS_DIR dir, SNXSHTF &h){
   if(!g_run_UseHTFBias) return false;
   if(h.bias == HTF_NEUTRAL) return false;
   if(h.conf < InpHTF_MinConf) return false;
   // AUDITPATCH: Discovery/Debug and Counter-HTF Soft are decided by the
   // family-aware router/execution layer; do not veto them a second time here.
   if(InpGateMode >= 2 || InpEnableCounterHTFSoft) return false;
   if(dir == DIR_BUY  && h.bias == HTF_BEAR && !h.reversalAllowed) return true;
   if(dir == DIR_SELL && h.bias == HTF_BULL && !h.reversalAllowed) return true;
   return false;
}

string NXS_HTFName(ENUM_NXS_HTF h){
   if(h == HTF_BULL) return "BULL";
   if(h == HTF_BEAR) return "BEAR";
   return "NEUTRAL";
}

#endif
