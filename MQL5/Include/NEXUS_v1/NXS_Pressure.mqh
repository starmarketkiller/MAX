//+------------------------------------------------------------------+
//|  NXS_Pressure.mqh - Buyer / Seller pressure (v2.0.5)              |
//|                                                                   |
//|  Computes %buy on the last N M5 bars using a 3-component blend:   |
//|    1. Close-vs-Range position (where did price close in the bar?) |
//|    2. Body direction × tick volume (weight)                       |
//|    3. Wick imbalance (upper wick vs lower wick)                   |
//|                                                                   |
//|  Falls back to GlobalVariable HYDRA_BSP_pct_buy_<sym> if external |
//|  feeder is providing it.                                          |
//+------------------------------------------------------------------+
#ifndef __NXS_PRESSURE_MQH__
#define __NXS_PRESSURE_MQH__

double _nxs_bsp_compute_local(){
   const int    N  = 18;          // 18 × M5 = ~90 min of microstructure
   const ENUM_TIMEFRAMES TF = PERIOD_M5;
   double sumBuy = 0.0, sumTot = 0.0;
   for(int i = 1; i <= N; i++){
      double o = iOpen (g_sym, TF, i);
      double c = iClose(g_sym, TF, i);
      double h = iHigh (g_sym, TF, i);
      double l = iLow  (g_sym, TF, i);
      long   v = iVolume(g_sym, TF, i);
      if(o <= 0 || c <= 0 || h <= 0 || l <= 0 || v <= 0) continue;
      double range = h - l; if(range < _Point) range = _Point;
      // (1) close position in bar [0..1]
      double clPos   = (c - l) / range;
      // (2) body direction
      double bodyDir = (c > o ? 1.0 : (c < o ? 0.0 : 0.5));
      // (3) wick imbalance: lower wick = buy rejection
      double upWick  = (h - MathMax(o, c)) / range;
      double dnWick  = (MathMin(o, c) - l) / range;
      double wickBuy = (dnWick + 0.0001) / (dnWick + upWick + 0.0002);
      // weighted blend
      double buyScore = (0.45 * clPos + 0.35 * bodyDir + 0.20 * wickBuy);
      sumBuy += buyScore * (double)v;
      sumTot += (double)v;
   }
   if(sumTot <= 0.0) return 50.0;
   double pct = 100.0 * sumBuy / sumTot;
   if(pct < 0.0)   pct = 0.0;
   if(pct > 100.0) pct = 100.0;
   return pct;
}

double NXS_GetBSP(){
   if(!InpUseBSP) return 50.0;
   // External feeder takes priority if present
   string var = "HYDRA_BSP_pct_buy_" + g_sym;
   if(GlobalVariableCheck(var)){
      double v = GlobalVariableGet(var);
      if(v >= 0 && v <= 100) return v;
   }
   // Local computation fallback (v2.0.5)
   return _nxs_bsp_compute_local();
}

double NXS_BSPModifier(ENUM_NXS_DIR dir){
   if(!InpUseBSP) return 0;
   double pct = NXS_GetBSP();
   double m   = 0;
   if(dir == DIR_BUY)  m = (pct - 50.0);
   else if(dir == DIR_SELL) m = (50.0 - pct);
   return m * InpBSPWeight; // up to ±10 if weight = 0.2
}

#endif
