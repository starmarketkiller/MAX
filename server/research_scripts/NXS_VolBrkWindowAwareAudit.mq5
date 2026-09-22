//+------------------------------------------------------------------+
//| NXS_VolBrkWindowAwareAudit.mq5                                    |
//| Phase 7.8G - script di sola lettura. Nessun trading, nessun       |
//| include NEXUS_v1. Tre scopi:                                      |
//|  1. Audit dell'intero anno 2026 (per capire dove cresce il file   |
//|     history/GOLD/2026.hcc: dentro o dopo PRIMARY_FRESH_VERDICT).  |
//|  2. Snapshot deterministico delle barre H4 nel superset esatto    |
//|     che il Tester carica (FromDate=2023.12.20 -> ToDate=2026.03.01|
//|     esclusivo), OHLCV+spread+real_volume, ordinato per tempo.     |
//|  3. Conteggio barre nella sotto-finestra 2026-01-01..2026-03-01   |
//|     (dentro FRESH) vs 2026-03-01..now (fuori FRESH).              |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

void OnStart(){
   string sym = "GOLD";
   ENUM_TIMEFRAMES tf = PERIOD_H4;

   // ---- Parte 1: audit dell'intero anno 2026 ----
   datetime y2026Start = D'2026.01.01 00:00:00';
   datetime nowT = TimeCurrent();
   MqlRates yearRates[];
   int nYear = CopyRates(sym, tf, y2026Start, nowT, yearRates);

   datetime firstBar2026 = (nYear > 0) ? yearRates[0].time : 0;
   datetime lastBar2026  = (nYear > 0) ? yearRates[nYear - 1].time : 0;

   // ---- Parte 3: conteggio dentro vs fuori FRESH per il 2026 ----
   datetime freshEnd = D'2026.03.01 00:00:00';
   int nInsideFresh2026 = 0, nOutsideFresh2026 = 0;
   for(int i = 0; i < nYear; i++){
      if(yearRates[i].time < freshEnd) nInsideFresh2026++;
      else nOutsideFresh2026++;
   }

   // ---- Parte 2: snapshot deterministico del superset esatto Tester ----
   datetime supersetStart = D'2023.12.20 00:00:00';
   datetime supersetEnd   = D'2026.03.01 00:00:00';
   MqlRates freshRates[];
   int nFresh = CopyRates(sym, tf, supersetStart, supersetEnd, freshRates);

   int hSnap = FileOpen("nxs_volbrk_window_snapshot.csv", FILE_WRITE|FILE_TXT|FILE_COMMON|FILE_ANSI);
   if(hSnap != INVALID_HANDLE){
      FileWrite(hSnap, "timestamp,open,high,low,close,tick_volume,spread,real_volume");
      for(int i = 0; i < nFresh; i++){
         FileWrite(hSnap,
            TimeToString(freshRates[i].time, TIME_DATE|TIME_SECONDS) + "," +
            DoubleToString(freshRates[i].open, 2) + "," +
            DoubleToString(freshRates[i].high, 2) + "," +
            DoubleToString(freshRates[i].low, 2) + "," +
            DoubleToString(freshRates[i].close, 2) + "," +
            IntegerToString((long)freshRates[i].tick_volume) + "," +
            IntegerToString((int)freshRates[i].spread) + "," +
            IntegerToString((long)freshRates[i].real_volume));
      }
      FileClose(hSnap);
   }

   int hSum = FileOpen("nxs_volbrk_window_aware_audit.txt", FILE_WRITE|FILE_TXT|FILE_COMMON|FILE_ANSI);
   if(hSum != INVALID_HANDLE){
      FileWrite(hSum, "symbol=" + sym);
      FileWrite(hSum, "measured_at_TimeCurrent=" + TimeToString(nowT, TIME_DATE|TIME_SECONDS));
      FileWrite(hSum, "year2026_bar_count=" + IntegerToString(nYear));
      FileWrite(hSum, "year2026_first_bar_time=" + TimeToString(firstBar2026, TIME_DATE|TIME_SECONDS));
      FileWrite(hSum, "year2026_last_bar_time=" + TimeToString(lastBar2026, TIME_DATE|TIME_SECONDS));
      FileWrite(hSum, "year2026_bars_inside_fresh_before_20260301=" + IntegerToString(nInsideFresh2026));
      FileWrite(hSum, "year2026_bars_outside_fresh_from_20260301=" + IntegerToString(nOutsideFresh2026));
      FileWrite(hSum, "superset_snapshot_bar_count=" + IntegerToString(nFresh));
      FileWrite(hSum, "superset_snapshot_first_bar=" + ((nFresh > 0) ? TimeToString(freshRates[0].time, TIME_DATE|TIME_SECONDS) : "NONE"));
      FileWrite(hSum, "superset_snapshot_last_bar=" + ((nFresh > 0) ? TimeToString(freshRates[nFresh - 1].time, TIME_DATE|TIME_SECONDS) : "NONE"));
      FileClose(hSum);
   }

   int hDone = FileOpen("nxs_volbrk_window_aware_audit_done.txt", FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(hDone != INVALID_HANDLE){
      FileWrite(hDone, "done=1");
      FileClose(hDone);
   }
}
