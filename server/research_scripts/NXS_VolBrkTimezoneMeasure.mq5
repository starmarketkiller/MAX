//+------------------------------------------------------------------+
//| NXS_VolBrkTimezoneMeasure.mq5                                     |
//| Phase 7.8E - misura DIRETTA (non da costante) dell'offset UTC del |
//| broker/server attualmente connesso, nello stesso istante:         |
//| TimeCurrent(), TimeTradeServer(), TimeGMT(), TimeLocal().         |
//| Nessun trade, nessuna modifica di stato, nessuna EA toccata.       |
//| Va lanciato LIVE-attached (non Tester).                           |
//+------------------------------------------------------------------+
#property strict

input string InpOutFile = "nxs_volbrk_timezone_measure.txt";
input string InpDoneMarker = "nxs_volbrk_timezone_done.txt";

int OnInit(){
   datetime tCurrent = TimeCurrent();
   datetime tTradeServer = TimeTradeServer();
   datetime tGMT = TimeGMT();
   datetime tLocal = TimeLocal();

   long offsetTradeServerMinusGMT = (long)tTradeServer - (long)tGMT;
   long offsetCurrentMinusGMT = (long)tCurrent - (long)tGMT;
   long offsetLocalMinusGMT = (long)tLocal - (long)tGMT;

   string server = AccountInfoString(ACCOUNT_SERVER);
   long login = AccountInfoInteger(ACCOUNT_LOGIN);

   int fh = FileOpen(InpOutFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(fh == INVALID_HANDLE){
      PrintFormat("[NXS TZ MEASURE] impossibile aprire %s (err=%d)", InpOutFile, GetLastError());
      return INIT_SUCCEEDED;
   }
   FileWrite(fh, "server=" + server);
   FileWrite(fh, "login=" + (string)login);
   FileWrite(fh, "measured_at_TimeCurrent=" + TimeToString(tCurrent, TIME_DATE|TIME_SECONDS));
   FileWrite(fh, "measured_at_TimeTradeServer=" + TimeToString(tTradeServer, TIME_DATE|TIME_SECONDS));
   FileWrite(fh, "measured_at_TimeGMT=" + TimeToString(tGMT, TIME_DATE|TIME_SECONDS));
   FileWrite(fh, "measured_at_TimeLocal=" + TimeToString(tLocal, TIME_DATE|TIME_SECONDS));
   FileWrite(fh, "TimeCurrent_raw=" + (string)(long)tCurrent);
   FileWrite(fh, "TimeTradeServer_raw=" + (string)(long)tTradeServer);
   FileWrite(fh, "TimeGMT_raw=" + (string)(long)tGMT);
   FileWrite(fh, "TimeLocal_raw=" + (string)(long)tLocal);
   FileWrite(fh, "broker_utc_offset_seconds_TradeServer_minus_GMT=" + (string)offsetTradeServerMinusGMT);
   FileWrite(fh, "offset_seconds_Current_minus_GMT=" + (string)offsetCurrentMinusGMT);
   FileWrite(fh, "offset_seconds_Local_minus_GMT=" + (string)offsetLocalMinusGMT);
   FileWrite(fh, "note=misura singola istante - riflette lo stato DST corrente al momento della misura, "
             + "va ri-misurato se il RUN avviene in una stagione con DST diverso");
   FileClose(fh);

   PrintFormat("[NXS TZ MEASURE] TradeServer-GMT=%d s Current-GMT=%d s Local-GMT=%d s",
               offsetTradeServerMinusGMT, offsetCurrentMinusGMT, offsetLocalMinusGMT);

   int mfh = FileOpen(InpDoneMarker, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(mfh != INVALID_HANDLE){
      FileWrite(mfh, "done=1");
      FileWrite(mfh, "broker_utc_offset_seconds=" + (string)offsetTradeServerMinusGMT);
      FileClose(mfh);
   }
   PrintFormat("[NXS TZ MEASURE] COMPLETATO -> %s", InpOutFile);
   return INIT_SUCCEEDED;
}
void OnTick(){}
