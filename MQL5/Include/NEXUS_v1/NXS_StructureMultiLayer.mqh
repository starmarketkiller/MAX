//+------------------------------------------------------------------+
//|  NXS_StructureMultiLayer.mqh - v2.0.3                              |
//|  Multi-TF structure snapshot: HTF bias, Medium POI, Entry trigger  |
//+------------------------------------------------------------------+
#ifndef __NXS_STRUCTURE_ML_MQH__
#define __NXS_STRUCTURE_ML_MQH__

// Lightweight per-TF snapshot (separate from g_struct which is entry-TF only)
struct SNXSStructLayer {
   int    trend;             // +1 bull / -1 bear / 0 range
   double lastSwingHigh;
   double lastSwingLow;
   bool   bosUp;
   bool   bosDown;
};

SNXSStructLayer g_structEntry;
SNXSStructLayer g_structMedium;
SNXSStructLayer g_structHigh;

void NXS_ML_BuildLayer(SNXSStructLayer &out, ENUM_TIMEFRAMES tf, int wing){
   ZeroMemory(out);
   int hiIdx = iHighest(g_sym, tf, MODE_HIGH, wing*2, 1);
   int loIdx = iLowest (g_sym, tf, MODE_LOW,  wing*2, 1);
   out.lastSwingHigh = iHigh(g_sym, tf, hiIdx);
   out.lastSwingLow  = iLow (g_sym, tf, loIdx);
   double c0 = iClose(g_sym, tf, 0);
   if(c0 > out.lastSwingHigh){ out.bosUp = true;   out.trend = +1; }
   else if(c0 < out.lastSwingLow){ out.bosDown = true; out.trend = -1; }
   else out.trend = 0;
}

void NXS_ML_RefreshAll(){
   NXS_ML_BuildLayer(g_structEntry,  InpTFEntry,  InpSwingWing);
   NXS_ML_BuildLayer(g_structMedium, InpTFMedium, InpSwingWing);
   NXS_ML_BuildLayer(g_structHigh,   InpTFHigh,   InpSwingWing);
}

#endif
