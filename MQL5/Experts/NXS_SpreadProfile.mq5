//+------------------------------------------------------------------+
//| NXS_SpreadProfile.mq5                                              |
//| 29/08 - EA minimo lanciato via Tester (Model=4, tick reali) per     |
//| registrare la distribuzione REALE dello spread GOLD per ora del    |
//| giorno (server time). Serve a dare al motore Python un modello di  |
//| spread realistico senza dover rigiocare milioni di tick grezzi -   |
//| un istogramma per ora, non lo storico completo.                    |
//+------------------------------------------------------------------+
#property strict

#define NXS_SP_BINS 200   // 1 punto per bin, 0..199 punti (GOLD spread tipico 40-80pt)

long g_hist[24][NXS_SP_BINS];
long g_count[24];
long g_sum[24];
long g_overflow[24];   // spread >= NXS_SP_BINS punti

int OnInit(){
   ArrayInitialize(g_count, 0);
   ArrayInitialize(g_sum, 0);
   ArrayInitialize(g_overflow, 0);
   for(int h = 0; h < 24; h++)
      for(int b = 0; b < NXS_SP_BINS; b++)
         g_hist[h][b] = 0;
   return INIT_SUCCEEDED;
}

void OnTick(){
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int h = dt.hour;
   long spreadPts = (long)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spreadPts < 0) return;
   g_count[h]++;
   g_sum[h] += spreadPts;
   int bin = (int)MathMin(spreadPts, NXS_SP_BINS - 1);
   if(spreadPts >= NXS_SP_BINS) g_overflow[h]++;
   g_hist[h][bin]++;
}

long PercentileFromHist(int h, double pct){
   long target = (long)MathCeil(g_count[h] * pct);
   long cum = 0;
   for(int b = 0; b < NXS_SP_BINS; b++){
      cum += g_hist[h][b];
      if(cum >= target) return b;
   }
   return NXS_SP_BINS - 1;
}

void OnDeinit(const int reason){
   int fh = FileOpen("nxs_spread_profile_gold.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE){
      PrintFormat("[NXS SPREAD] impossibile aprire il file di output (err=%d)", GetLastError());
      return;
   }
   FileWrite(fh, "hour", "count", "mean_pts", "p10", "p25", "p50", "p75", "p90", "p95", "p99", "overflow_ge200");
   for(int h = 0; h < 24; h++){
      double mean = (g_count[h] > 0) ? (double)g_sum[h] / g_count[h] : 0.0;
      FileWrite(fh, h, g_count[h], mean,
                PercentileFromHist(h, 0.10), PercentileFromHist(h, 0.25),
                PercentileFromHist(h, 0.50), PercentileFromHist(h, 0.75),
                PercentileFromHist(h, 0.90), PercentileFromHist(h, 0.95),
                PercentileFromHist(h, 0.99), g_overflow[h]);
   }
   FileClose(fh);
   PrintFormat("[NXS SPREAD] profilo scritto: nxs_spread_profile_gold.csv");
}
