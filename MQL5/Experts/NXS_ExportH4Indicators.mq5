//+------------------------------------------------------------------+
//| NXS_ExportH4Indicators.mq5                                         |
//| 29/08 - export OHLC H4 GOLD insieme ai valori REALI degli          |
//| indicatori nativi MT5 (iSAR/iMA9/iMA21/iATR14) usati da            |
//| NXS_Strat_SAR, non una reimplementazione Python. Serve a isolare   |
//| se la divergenza segnale-per-segnale vista tra Python e MT5 reale  |
//| viene da una reimplementazione dell'indicatore diversa (PSAR e'    |
//| path-dependent, piccoli scarti si accumulano su centinaia di       |
//| barre) oppure da qualcos'altro a valle.                            |
//+------------------------------------------------------------------+
#property strict

input string   InpSymbol = "GOLD";
input datetime InpFrom   = D'2025.01.01 00:00:00';
input datetime InpTo     = D'2026.08.26 23:59:59';
input string   InpOutFile= "nxs_h4_gold_indicators.csv";
input double   InpSAR_Step = 0.02;
input double   InpSAR_Max  = 0.2;
input int      InpEMA9_Period  = 9;
input int      InpEMA21_Period = 21;
input int      InpATR_Period   = 14;

int OnInit(){
   SymbolSelect(InpSymbol, true);
   MqlRates rates[];
   // 01/09 - su range lontani nel tempo la cronologia H4 non e' ancora
   // sincronizzata al momento esatto di OnInit: CopyRates fallisce con
   // err=4401 anche con InpFrom/InpTo corretti. Ritenta con attesa,
   // stesso pattern gia' usato sotto per BarsCalculated().
   int copied = 0, copyTries = 0;
   while(copyTries < 100){
      copied = CopyRates(InpSymbol, PERIOD_H4, InpFrom, InpTo, rates);
      if(copied > 0) break;
      Sleep(200);
      copyTries++;
   }
   if(copied <= 0){
      PrintFormat("[NXS EXPORT H4 IND] CopyRates fallita dopo %d tentativi (err=%d)", copyTries, GetLastError());
      return INIT_SUCCEEDED;
   }

   int hSAR  = iSAR(InpSymbol, PERIOD_H4, InpSAR_Step, InpSAR_Max);
   int hEMA9 = iMA(InpSymbol, PERIOD_H4, InpEMA9_Period, 0, MODE_EMA, PRICE_CLOSE);
   int hEMA21= iMA(InpSymbol, PERIOD_H4, InpEMA21_Period, 0, MODE_EMA, PRICE_CLOSE);
   int hATR  = iATR(InpSymbol, PERIOD_H4, InpATR_Period);
   if(hSAR == INVALID_HANDLE || hEMA9 == INVALID_HANDLE || hEMA21 == INVALID_HANDLE || hATR == INVALID_HANDLE){
      PrintFormat("[NXS EXPORT H4 IND] handle indicatore invalido (err=%d)", GetLastError());
      return INIT_SUCCEEDED;
   }

   // Forza il calcolo storico completo prima di leggere (gli handle sono
   // lazy, senza questa attesa CopyBuffer puo' tornare dati parziali).
   int tries = 0;
   while(BarsCalculated(hSAR) < copied && tries < 200){ Sleep(50); tries++; }

   double sarBuf[], ema9Buf[], ema21Buf[], atrBuf[];
   int nSar  = CopyBuffer(hSAR,  0, InpFrom, InpTo, sarBuf);
   int nEma9 = CopyBuffer(hEMA9, 0, InpFrom, InpTo, ema9Buf);
   int nEma21= CopyBuffer(hEMA21,0, InpFrom, InpTo, ema21Buf);
   int nAtr  = CopyBuffer(hATR,  0, InpFrom, InpTo, atrBuf);
   PrintFormat("[NXS EXPORT H4 IND] copied=%d nSar=%d nEma9=%d nEma21=%d nAtr=%d",
               copied, nSar, nEma9, nEma21, nAtr);

   int fh = FileOpen(InpOutFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE){
      PrintFormat("[NXS EXPORT H4 IND] impossibile aprire il file (err=%d)", GetLastError());
      return INIT_SUCCEEDED;
   }
   FileWrite(fh, "time", "open", "high", "low", "close", "sar", "ema9", "ema21", "atr14");
   int n = MathMin(copied, MathMin(nSar, MathMin(nEma9, MathMin(nEma21, nAtr))));
   // Gli array indicatore sono allineati per TEMPO (CopyBuffer con from/to),
   // stesso ordine cronologico ascendente di rates[] quando non-timeseries.
   int offRates = copied - n, offSar = nSar - n, offE9 = nEma9 - n, offE21 = nEma21 - n, offAtr = nAtr - n;
   for(int k = 0; k < n; k++){
      FileWrite(fh, TimeToString(rates[k+offRates].time, TIME_DATE|TIME_MINUTES),
                rates[k+offRates].open, rates[k+offRates].high, rates[k+offRates].low, rates[k+offRates].close,
                sarBuf[k+offSar], ema9Buf[k+offE9], ema21Buf[k+offE21], atrBuf[k+offAtr]);
   }
   FileClose(fh);
   PrintFormat("[NXS EXPORT H4 IND] COMPLETATO: %d righe scritte su %s (rates=%d sar=%d ema9=%d ema21=%d atr=%d)",
               n, InpOutFile, copied, nSar, nEma9, nEma21, nAtr);
   return INIT_SUCCEEDED;
}
void OnTick(){}
