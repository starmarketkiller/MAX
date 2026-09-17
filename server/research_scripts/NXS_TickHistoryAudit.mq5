//+------------------------------------------------------------------+
//| NXS_TickHistoryAudit.mq5                                          |
//| 17/09 - Phase G follow-up: audit READ-ONLY della profondita' reale |
//| dello storico tick per GOLD/XAU* sull'account/server attualmente   |
//| connesso. Nessun trade, nessuna modifica di stato. Sonde LEGGERE   |
//| (7 giorni per punto, non interi anni) per non scaricare milioni di |
//| tick inutilmente - lo scopo e' localizzare il confine, non         |
//| scaricare l'archivio. Va lanciato LIVE-attached (non Tester): il   |
//| Tester limita CopyTicksRange alla finestra del test stesso.        |
//+------------------------------------------------------------------+
#property strict

input string InpOutFile = "nxs_tick_history_audit.csv";

datetime ProbePoints[] = {
   D'2005.01.01', D'2008.01.01', D'2010.01.01', D'2012.01.01', D'2014.01.01',
   D'2016.01.01', D'2018.01.01', D'2019.01.01', D'2020.01.01', D'2021.01.01',
   D'2022.01.01', D'2022.07.01', D'2023.01.01', D'2023.06.01', D'2023.08.01',
   D'2023.09.01', D'2023.09.08', D'2023.09.10', D'2023.09.11', D'2023.09.12',
   D'2023.09.15', D'2023.10.01', D'2024.01.01'
};

int OnInit(){
   int fh = FileOpen(InpOutFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE){
      PrintFormat("[NXS TICK AUDIT] impossibile aprire il file (err=%d)", GetLastError());
      return INIT_SUCCEEDED;
   }
   FileWrite(fh, "server", "login", "trade_mode", "symbol", "probe_from", "probe_to_plus7d", "ticks_found", "first_tick", "last_tick");

   string server = AccountInfoString(ACCOUNT_SERVER);
   long   login  = AccountInfoInteger(ACCOUNT_LOGIN);
   long   mode   = AccountInfoInteger(ACCOUNT_TRADE_MODE);
   string modeStr = (mode==0? "DEMO" : (mode==2? "REAL" : "CONTEST"));
   PrintFormat("[NXS TICK AUDIT] server=%s login=%d mode=%s", server, login, modeStr);

   int total = SymbolsTotal(false);
   string candidates[]; int nCand = 0; ArrayResize(candidates, 20);
   for(int i = 0; i < total; i++){
      string nm = SymbolName(i, false);
      string up = nm; StringToUpper(up);
      // Solo simboli di prezzo metallo/coppia valutaria oro, non azioni miniere
      if(up == "GOLD" || up == "GOLD24-7" || StringFind(up, "XAU") == 0){
         if(nCand < 20) candidates[nCand++] = nm;
      }
   }
   PrintFormat("[NXS TICK AUDIT] candidati filtrati=%d", nCand);
   for(int c = 0; c < nCand; c++) PrintFormat("[NXS TICK AUDIT] candidato: %s", candidates[c]);

   for(int c = 0; c < nCand; c++){
      string sym = candidates[c];
      if(!SymbolSelect(sym, true)){
         PrintFormat("[NXS TICK AUDIT] %s: SymbolSelect fallita (err=%d)", sym, GetLastError());
         continue;
      }
      for(int p = 0; p < ArraySize(ProbePoints); p++){
         datetime from = ProbePoints[p];
         datetime to = from + 7*24*3600;
         MqlTick ticks[];
         ResetLastError();
         int copied = CopyTicksRange(sym, ticks, COPY_TICKS_ALL, (long)from * 1000, (long)to * 1000);
         string firstT = "-", lastT = "-";
         if(copied > 0){
            firstT = TimeToString(ticks[0].time, TIME_DATE|TIME_SECONDS);
            lastT  = TimeToString(ticks[copied-1].time, TIME_DATE|TIME_SECONDS);
         }
         int err = GetLastError();
         PrintFormat("[NXS TICK AUDIT] %s probe=%s ticks=%d first=%s last=%s err=%d",
                     sym, TimeToString(from, TIME_DATE), MathMax(copied,0), firstT, lastT, err);
         FileWrite(fh, server, (string)login, modeStr, sym, TimeToString(from, TIME_DATE),
                   TimeToString(to, TIME_DATE), (string)MathMax(copied,0), firstT, lastT);
         FileFlush(fh);
      }
   }
   FileClose(fh);
   PrintFormat("[NXS TICK AUDIT] COMPLETATO -> %s", InpOutFile);
   return INIT_SUCCEEDED;
}
void OnTick(){}
