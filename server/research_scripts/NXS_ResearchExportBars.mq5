//+------------------------------------------------------------------+
//| NXS_ResearchExportBars.mq5                                        |
//| 14/09 - Causal Experiment 1 (WICK Sweep +1R/-1R). Script di sola   |
//| esportazione dati, COMPLETAMENTE SEPARATO da NEXUS_EA_v2.mq5: zero |
//| rischio per l'EA di produzione, nessuna logica di trading, nessun  |
//| ordine, nessuna lettura/scrittura di stato NEXUS. Esporta le barre |
//| M15 dell'intervallo testato in un CSV (FILE_COMMON) per calcolare  |
//| offline il path di prezzo futuro necessario all'etichetta          |
//| PLUS_1R_FIRST/MINUS_1R_FIRST/CENSORED - MAI usato per decisioni di  |
//| trading, solo per costruire il dataset di ricerca dopo il fatto.   |
//+------------------------------------------------------------------+
#property strict

input string InpExportFileName = "nxs_research_bars.csv";
input string InpExportFromDate = "2026.05.25";   // filtro per tenere il file gestibile con M1
input string InpExportToDate   = "2026.09.05";

void OnTick(){}

int OnInit(){
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason){
   ENUM_TIMEFRAMES tf = PERIOD_M1;
   datetime fromT = StringToTime(InpExportFromDate);
   datetime toT   = StringToTime(InpExportToDate);
   int total = Bars(_Symbol, tf);
   int h = FileOpen(InpExportFileName, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
   if(h == INVALID_HANDLE){
      PrintFormat("[NXS_RESEARCH_EXPORT] FileOpen fallito err=%d", GetLastError());
      return;
   }
   FileWrite(h, "time", "open", "high", "low", "close");
   int written = 0;
   for(int i = total - 1; i >= 0; i--){
      datetime t = iTime(_Symbol, tf, i);
      if(t < fromT) continue;
      if(t > toT) continue;
      FileWrite(h, TimeToString(t, TIME_DATE|TIME_SECONDS),
                DoubleToString(iOpen(_Symbol, tf, i), _Digits),
                DoubleToString(iHigh(_Symbol, tf, i), _Digits),
                DoubleToString(iLow(_Symbol, tf, i), _Digits),
                DoubleToString(iClose(_Symbol, tf, i), _Digits));
      written++;
   }
   FileClose(h);
   PrintFormat("[NXS_RESEARCH_EXPORT] esportate %d barre M1 (%s..%s) in %s",
               written, InpExportFromDate, InpExportToDate, InpExportFileName);
}
