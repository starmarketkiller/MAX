//+------------------------------------------------------------------+
//| NXS_DukaRangeCheck.mq5 - TEMP diagnostic: map which months of the  |
//| imported XAUUSD_DSC tick history actually survived a graceful      |
//| terminal restart. Delete after use.                                 |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs
input string InpSymbol = "XAUUSD_DSC";

void OnStart(){
   int h = FileOpen("nxs_duka_rangecheck.txt", FILE_WRITE|FILE_TXT);
   if(h==INVALID_HANDLE){ Print("open fail ", GetLastError()); return; }

   bool exists = (bool)SymbolInfoInteger(InpSymbol, SYMBOL_CUSTOM);
   FileWrite(h, StringFormat("symbol_custom_exists=%s select=%s", (exists?"true":"false"), (SymbolSelect(InpSymbol,true)?"true":"false")));

   datetime months[]; // first day of each test month
   string labels[];
   ArrayResize(months, 14); ArrayResize(labels, 14);
   months[0]=D'2019.02.03'; labels[0]="2019-02";
   months[1]=D'2019.06.01'; labels[1]="2019-06";
   months[2]=D'2019.12.01'; labels[2]="2019-12";
   months[3]=D'2020.03.01'; labels[3]="2020-03";
   months[4]=D'2020.06.01'; labels[4]="2020-06";
   months[5]=D'2020.09.01'; labels[5]="2020-09";
   months[6]=D'2020.12.01'; labels[6]="2020-12";
   months[7]=D'2021.02.01'; labels[7]="2021-02";
   months[8]=D'2021.04.01'; labels[8]="2021-04";
   months[9]=D'2021.05.01'; labels[9]="2021-05";
   months[10]=D'2021.08.01'; labels[10]="2021-08";
   months[11]=D'2021.11.01'; labels[11]="2021-11";
   months[12]=D'2022.01.01'; labels[12]="2022-01";
   months[13]=D'2022.02.02'; labels[13]="2022-02";

   for(int i=0;i<14;i++){
      MqlTick a[];
      ulong from = (ulong)((long)months[i]*1000);
      ulong to   = (ulong)((long)(months[i]+3*86400)*1000); // 3-day window sample
      int got = CopyTicksRange(InpSymbol, a, COPY_TICKS_ALL, from, to);
      MqlRates r[];
      int gotBars = CopyRates(InpSymbol, PERIOD_H4, months[i], 3, r);
      FileWrite(h, StringFormat("%s: ticks_3day_window=%d  h4_bars_from_that_date=%d", labels[i], got, gotBars));
   }

   long firstAvail=0, lastAvail=0;
   FileClose(h);
   Print("[RANGECHECK] done");
}
