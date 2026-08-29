//+------------------------------------------------------------------+
//| NXS_ExportM15.mq5                                                  |
//| 29/08 - esporta le barre M15 GOLD (CopyRates, dati ufficiali del   |
//| terminale) per simulare la gestione intraday (trailing/timeout/   |
//| max-loss) con la stessa granularita' del motore vero.              |
//+------------------------------------------------------------------+
#property strict
input string   InpSymbol = "GOLD";
input datetime InpFrom   = D'2025.10.15 00:00:00';
input datetime InpTo     = D'2026.08.26 23:59:59';
input string   InpOutFile= "nxs_m15_gold.csv";

int OnInit(){
   SymbolSelect(InpSymbol, true);
   MqlRates rates[];
   int copied = CopyRates(InpSymbol, PERIOD_M15, InpFrom, InpTo, rates);
   if(copied <= 0){
      PrintFormat("[NXS EXPORT M15] CopyRates fallita (err=%d)", GetLastError());
      return INIT_SUCCEEDED;
   }
   int fh = FileOpen(InpOutFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE){
      PrintFormat("[NXS EXPORT M15] impossibile aprire il file (err=%d)", GetLastError());
      return INIT_SUCCEEDED;
   }
   FileWrite(fh, "time", "open", "high", "low", "close");
   for(int i = 0; i < copied; i++){
      FileWrite(fh, TimeToString(rates[i].time, TIME_DATE|TIME_MINUTES),
                rates[i].open, rates[i].high, rates[i].low, rates[i].close);
   }
   FileClose(fh);
   PrintFormat("[NXS EXPORT M15] COMPLETATO: %d barre scritte su %s", copied, InpOutFile);
   return INIT_SUCCEEDED;
}
void OnTick(){}
