//+------------------------------------------------------------------+
//| NXS_ExportMACDIndicators.mq5                                      |
//| 16/09 - Phase E: export OHLC H4 GOLD + EMA200/MACD-line/MACD-      |
//| signal nativi MT5 (stessi parametri di NXS_Strat_MACD: EMA200,     |
//| MACD 12/26/9 su PRICE_CLOSE), per confrontare bar-per-bar contro    |
//| i valori Python sulle date contese del parity test MACD (Phase D). |
//| Standalone, zero rischio per NEXUS_EA_v2.mq5 - stesso pattern di   |
//| NXS_ExportH4Indicators.mq5 (SAR).                                  |
//+------------------------------------------------------------------+
#property strict

input string   InpSymbol = "GOLD";
input datetime InpFrom   = D'2026.05.15 00:00:00';
input datetime InpTo     = D'2026.08.28 23:59:59';
input string   InpOutFile= "nxs_h4_gold_macd_indicators.csv";
input int      InpEMA200_Period = 200;
input int      InpMACD_Fast     = 12;
input int      InpMACD_Slow     = 26;
input int      InpMACD_Signal   = 9;

int OnInit(){
   SymbolSelect(InpSymbol, true);
   MqlRates rates[];
   int copied = 0, copyTries = 0;
   while(copyTries < 100){
      copied = CopyRates(InpSymbol, PERIOD_H4, InpFrom, InpTo, rates);
      if(copied > 0) break;
      Sleep(200);
      copyTries++;
   }
   if(copied <= 0){
      PrintFormat("[NXS EXPORT MACD IND] CopyRates fallita dopo %d tentativi (err=%d)", copyTries, GetLastError());
      return INIT_SUCCEEDED;
   }

   int hEMA200 = iMA(InpSymbol, PERIOD_H4, InpEMA200_Period, 0, MODE_EMA, PRICE_CLOSE);
   int hMACD   = iMACD(InpSymbol, PERIOD_H4, InpMACD_Fast, InpMACD_Slow, InpMACD_Signal, PRICE_CLOSE);
   if(hEMA200 == INVALID_HANDLE || hMACD == INVALID_HANDLE){
      PrintFormat("[NXS EXPORT MACD IND] handle indicatore invalido (err=%d)", GetLastError());
      return INIT_SUCCEEDED;
   }

   int tries = 0;
   while(BarsCalculated(hMACD) < copied && tries < 200){ Sleep(50); tries++; }

   double ema200Buf[], macdBuf[], sigBuf[];
   int nEma = CopyBuffer(hEMA200, 0, InpFrom, InpTo, ema200Buf);
   int nMacd= CopyBuffer(hMACD,   0, InpFrom, InpTo, macdBuf);   // MAIN line
   int nSig = CopyBuffer(hMACD,   1, InpFrom, InpTo, sigBuf);    // SIGNAL line
   PrintFormat("[NXS EXPORT MACD IND] copied=%d nEma=%d nMacd=%d nSig=%d",
               copied, nEma, nMacd, nSig);

   int fh = FileOpen(InpOutFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE){
      PrintFormat("[NXS EXPORT MACD IND] impossibile aprire il file (err=%d)", GetLastError());
      return INIT_SUCCEEDED;
   }
   FileWrite(fh, "time", "open", "high", "low", "close", "ema200", "macd_main", "macd_signal");
   int n = MathMin(copied, MathMin(nEma, MathMin(nMacd, nSig)));
   int offRates = copied - n, offEma = nEma - n, offMacd = nMacd - n, offSig = nSig - n;
   for(int k = 0; k < n; k++){
      FileWrite(fh, TimeToString(rates[k+offRates].time, TIME_DATE|TIME_MINUTES),
                rates[k+offRates].open, rates[k+offRates].high, rates[k+offRates].low, rates[k+offRates].close,
                ema200Buf[k+offEma], macdBuf[k+offMacd], sigBuf[k+offSig]);
   }
   FileClose(fh);
   PrintFormat("[NXS EXPORT MACD IND] COMPLETATO: %d righe scritte su %s (rates=%d ema=%d macd=%d sig=%d)",
               n, InpOutFile, copied, nEma, nMacd, nSig);
   return INIT_SUCCEEDED;
}
void OnTick(){}
