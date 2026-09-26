//+------------------------------------------------------------------+
//| NXS_ExportD1_Phase79H.mq5                                          |
//| Phase 7.9H - esporta le barre D1 GOLD (CopyRates, stessa fonte     |
//| prezzi ufficiale del terminale usata dal backtest BREAKOUT_ACC)    |
//| su CSV, per il post-event path anatomy (MFE/MAE/forward returns). |
//| Sola lettura, nessuna logica di trading, nessun ordine.           |
//+------------------------------------------------------------------+
#property strict

input string   InpSymbol = "GOLD";
input datetime InpFrom   = D'2019.01.01 00:00:00';
input datetime InpTo     = D'2026.08.20 23:59:59';
input string   InpOutFile= "nxs_d1_gold_phase79h.csv";

int OnInit(){
   SymbolSelect(InpSymbol, true);
   return INIT_SUCCEEDED;
}

void OnTick(){}

// 26/09 - CopyRates in OnInit falliva con err=4401 (ERR_HISTORY_NOT_FOUND);
// farlo a ogni OnTick esportava dopo la primissima barra (copied>0 gia' con
// 1 sola barra disponibile). Fix: esportare in OnDeinit, quando il Tester ha
// gia' processato l'intero intervallo [InpFrom, InpTo] e la history D1 e'
// completa. Sola lettura, nessuna logica di trading.
void OnDeinit(const int reason){
   MqlRates rates[];
   int copied = CopyRates(InpSymbol, PERIOD_D1, InpFrom, InpTo, rates);
   if(copied <= 0){
      PrintFormat("[NXS EXPORT D1 79H] CopyRates fallita (err=%d)", GetLastError());
      return;
   }
   int fh = FileOpen(InpOutFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE){
      PrintFormat("[NXS EXPORT D1 79H] impossibile aprire il file (err=%d)", GetLastError());
      return;
   }
   FileWrite(fh, "time", "open", "high", "low", "close", "tick_volume");
   for(int i = 0; i < copied; i++){
      FileWrite(fh, TimeToString(rates[i].time, TIME_DATE|TIME_MINUTES),
                rates[i].open, rates[i].high, rates[i].low, rates[i].close,
                (long)rates[i].tick_volume);
   }
   FileFlush(fh);
   FileClose(fh);
   PrintFormat("[NXS EXPORT D1 79H] COMPLETATO: %d barre scritte su %s", copied, InpOutFile);
}
