//+------------------------------------------------------------------+
//| NXS_ExportH4.mq5                                                   |
//| 29/08 - esporta le barre H4 GOLD (CopyRates, dati ufficiali del    |
//| terminale) su CSV, per validare il motore Python contro la STESSA  |
//| fonte prezzi che usa il motore MQL5 reale (non Dukascopy/Yahoo).   |
//+------------------------------------------------------------------+
#property strict

input string   InpSymbol = "GOLD";
input datetime InpFrom   = D'2015.01.01 00:00:00';
input datetime InpTo     = D'2026.08.26 23:59:59';
input string   InpOutFile= "nxs_h4_gold.csv";

int OnInit(){
   SymbolSelect(InpSymbol, true);
   MqlRates rates[];
   int copied = CopyRates(InpSymbol, PERIOD_H4, InpFrom, InpTo, rates);
   if(copied <= 0){
      PrintFormat("[NXS EXPORT H4] CopyRates fallita (err=%d)", GetLastError());
      return INIT_SUCCEEDED;
   }
   int fh = FileOpen(InpOutFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE){
      PrintFormat("[NXS EXPORT H4] impossibile aprire il file (err=%d)", GetLastError());
      return INIT_SUCCEEDED;
   }
   FileWrite(fh, "time", "open", "high", "low", "close", "tick_volume");
   for(int i = 0; i < copied; i++){
      FileWrite(fh, TimeToString(rates[i].time, TIME_DATE|TIME_MINUTES),
                rates[i].open, rates[i].high, rates[i].low, rates[i].close,
                (long)rates[i].tick_volume);
   }
   FileClose(fh);
   PrintFormat("[NXS EXPORT H4] COMPLETATO: %d barre scritte su %s", copied, InpOutFile);
   return INIT_SUCCEEDED;
}
void OnTick(){}
