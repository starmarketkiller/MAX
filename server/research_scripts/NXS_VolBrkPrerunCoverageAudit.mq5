//+------------------------------------------------------------------+
//| NXS_VolBrkPrerunCoverageAudit.mq5                                 |
//| Phase 7.8D (redo) - audit READ-ONLY di copertura storica reale    |
//| per GOLD/XAU* sull'account/server attualmente connesso, per il    |
//| PRE-RUN MANIFEST di VOLATILITY_BREAKOUT_CONFIRMED Serious 3Y.     |
//| Nessun trade, nessuna modifica di stato, nessuna EA/strategia     |
//| toccata. Va lanciato LIVE-attached (non Tester).                  |
//| Sonde mensili (7 giorni per punto) sugli ultimi ~37 mesi + query  |
//| wide-range per first/last tick assoluto disponibile.              |
//+------------------------------------------------------------------+
#property strict

input string InpOutFile = "nxs_volbrk_prerun_coverage.csv";
input string InpSummaryFile = "nxs_volbrk_prerun_summary.txt";
input string InpDoneMarker = "nxs_volbrk_prerun_done.txt";

int OnInit(){
   string server = AccountInfoString(ACCOUNT_SERVER);
   long   login  = AccountInfoInteger(ACCOUNT_LOGIN);
   long   mode   = AccountInfoInteger(ACCOUNT_TRADE_MODE);
   string modeStr = (mode==0? "DEMO" : (mode==2? "REAL" : "CONTEST"));
   datetime nowServer = TimeCurrent();
   datetime nowTradeServer = TimeTradeServer();

   int total = SymbolsTotal(false);
   string candidates[]; int nCand = 0; ArrayResize(candidates, 20);
   for(int i = 0; i < total; i++){
      string nm = SymbolName(i, false);
      string up = nm; StringToUpper(up);
      if(up == "GOLD" || up == "GOLD24-7" || StringFind(up, "XAU") == 0){
         if(nCand < 20) candidates[nCand++] = nm;
      }
   }

   int fh = FileOpen(InpOutFile, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(fh == INVALID_HANDLE){
      PrintFormat("[NXS VOLBRK PRERUN] impossibile aprire %s (err=%d)", InpOutFile, GetLastError());
      return INIT_SUCCEEDED;
   }
   FileWrite(fh, "server", "login", "trade_mode", "symbol", "probe_month_start", "probe_to_plus7d",
              "ticks_found", "first_tick_in_probe", "last_tick_in_probe", "err");

   int shFile = FileOpen(InpSummaryFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(shFile != INVALID_HANDLE){
      FileWrite(shFile, "server=" + server);
      FileWrite(shFile, "login=" + (string)login);
      FileWrite(shFile, "trade_mode=" + modeStr);
      FileWrite(shFile, "server_time_now=" + TimeToString(nowServer, TIME_DATE|TIME_SECONDS));
      FileWrite(shFile, "trade_server_time_now=" + TimeToString(nowTradeServer, TIME_DATE|TIME_SECONDS));
      FileWrite(shFile, "n_candidate_symbols=" + (string)nCand);
      for(int c = 0; c < nCand; c++) FileWrite(shFile, "candidate_symbol=" + candidates[c]);
   }

   // Sonde mensili sugli ultimi 37 mesi (~3 anni + 1 mese di margine), finestra 7gg per punto
   for(int c = 0; c < nCand; c++){
      string sym = candidates[c];
      if(!SymbolSelect(sym, true)){
         PrintFormat("[NXS VOLBRK PRERUN] %s: SymbolSelect fallita (err=%d)", sym, GetLastError());
         continue;
      }

      // Query wide-range per first/last tick assoluto disponibile negli ultimi ~37 mesi
      // (forza il terminal a richiedere/sincronizzare dal server se non gia' in cache).
      datetime wideFrom = nowServer - (long)37*30*24*3600;
      MqlTick wideTicks[];
      ResetLastError();
      int wideCopied = CopyTicksRange(sym, wideTicks, COPY_TICKS_ALL, (long)wideFrom * 1000, (long)nowServer * 1000);
      int wideErr = GetLastError();
      string wideFirst = "-", wideLast = "-";
      if(wideCopied > 0){
         wideFirst = TimeToString(wideTicks[0].time, TIME_DATE|TIME_SECONDS);
         wideLast  = TimeToString(wideTicks[wideCopied-1].time, TIME_DATE|TIME_SECONDS);
      }
      PrintFormat("[NXS VOLBRK PRERUN] %s WIDE probe: ticks=%d first=%s last=%s err=%d",
                  sym, wideCopied, wideFirst, wideLast, wideErr);
      if(shFile != INVALID_HANDLE){
         FileWrite(shFile, "symbol=" + sym + " wide_ticks=" + (string)wideCopied +
                   " wide_first=" + wideFirst + " wide_last=" + wideLast + " wide_err=" + (string)wideErr);
      }

      for(int m = 0; m < 37; m++){
         datetime from = nowServer - (long)(37 - m) * 30 * 24 * 3600;
         datetime to = from + 7*24*3600;
         MqlTick ticks[];
         ResetLastError();
         int copied = CopyTicksRange(sym, ticks, COPY_TICKS_ALL, (long)from * 1000, (long)to * 1000);
         int err = GetLastError();
         string firstT = "-", lastT = "-";
         if(copied > 0){
            firstT = TimeToString(ticks[0].time, TIME_DATE|TIME_SECONDS);
            lastT  = TimeToString(ticks[copied-1].time, TIME_DATE|TIME_SECONDS);
         }
         FileWrite(fh, server, (string)login, modeStr, sym, TimeToString(from, TIME_DATE), TimeToString(to, TIME_DATE),
                   (string)MathMax(copied,0), firstT, lastT, (string)err);
         FileFlush(fh);
      }
      // Copertura H4 bar reale (per il conteggio bar atteso nella finestra)
      MqlRates rates[];
      ResetLastError();
      int nBars = CopyRates(sym, PERIOD_H4, wideFrom, nowServer, rates);
      int barsErr = GetLastError();
      if(shFile != INVALID_HANDLE){
         string firstBar = (nBars > 0) ? TimeToString(rates[0].time, TIME_DATE|TIME_SECONDS) : "-";
         string lastBar  = (nBars > 0) ? TimeToString(rates[nBars-1].time, TIME_DATE|TIME_SECONDS) : "-";
         FileWrite(shFile, "symbol=" + sym + " h4_bars=" + (string)MathMax(nBars,0) +
                   " h4_first_bar=" + firstBar + " h4_last_bar=" + lastBar + " h4_err=" + (string)barsErr);
      }
      PrintFormat("[NXS VOLBRK PRERUN] %s H4: bars=%d err=%d", sym, MathMax(nBars,0), barsErr);
   }

   if(shFile != INVALID_HANDLE) FileClose(shFile);
   FileClose(fh);

   int mfh = FileOpen(InpDoneMarker, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(mfh != INVALID_HANDLE){
      FileWrite(mfh, "done=1");
      FileWrite(mfh, "server=" + server);
      FileWrite(mfh, "login=" + (string)login);
      FileWrite(mfh, "n_candidates=" + (string)nCand);
      FileClose(mfh);
   }
   PrintFormat("[NXS VOLBRK PRERUN] COMPLETATO -> %s / %s / %s", InpOutFile, InpSummaryFile, InpDoneMarker);
   return INIT_SUCCEEDED;
}
void OnTick(){}
