//+------------------------------------------------------------------+
//| NXS_VolBrkTesterWindowProbe.mq5                                   |
//| Phase 7.8F - probe di sola misura per la semantica esatta di      |
//| FromDate/ToDate nello Strategy Tester. NESSUN trading, NESSUN     |
//| include NEXUS_v1, NESSUN OrderSend. Registra il primo e l'ultimo  |
//| timestamp effettivamente visto da OnTick() e da OnTimer/bar H4,   |
//| e il numero totale di barre H4 processate.                        |
//+------------------------------------------------------------------+
#property strict

datetime g_firstTickTime = 0;
datetime g_lastTickTime  = 0;
long     g_tickCount     = 0;
datetime g_firstBarTime  = 0;
datetime g_lastBarTime   = 0;
long     g_barCount      = 0;
datetime g_lastSeenBar   = 0;

int OnInit(){
   g_firstTickTime = 0;
   g_lastTickTime  = 0;
   g_tickCount     = 0;
   g_firstBarTime  = 0;
   g_lastBarTime   = 0;
   g_barCount      = 0;
   g_lastSeenBar   = 0;
   return(INIT_SUCCEEDED);
}

void OnTick(){
   datetime now = TimeCurrent();
   if(g_firstTickTime == 0) g_firstTickTime = now;
   g_lastTickTime = now;
   g_tickCount++;

   datetime barTime = iTime(_Symbol, PERIOD_H4, 0);
   if(barTime > 0 && barTime != g_lastSeenBar){
      g_lastSeenBar = barTime;
      if(g_firstBarTime == 0) g_firstBarTime = barTime;
      g_lastBarTime = barTime;
      g_barCount++;
   }
}

void OnDeinit(const int reason){
   int h = FileOpen("nxs_volbrk_tester_window_probe.txt", FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(h != INVALID_HANDLE){
      FileWrite(h, "probe_symbol=" + _Symbol);
      FileWrite(h, "probe_period=H4");
      FileWrite(h, "ini_FromDate_ToDate_as_configured_by_launcher");
      FileWrite(h, "first_tick_time=" + TimeToString(g_firstTickTime, TIME_DATE|TIME_MINUTES|TIME_SECONDS));
      FileWrite(h, "last_tick_time=" + TimeToString(g_lastTickTime, TIME_DATE|TIME_MINUTES|TIME_SECONDS));
      FileWrite(h, "first_tick_time_raw=" + IntegerToString((long)g_firstTickTime));
      FileWrite(h, "last_tick_time_raw=" + IntegerToString((long)g_lastTickTime));
      FileWrite(h, "tick_count=" + IntegerToString(g_tickCount));
      FileWrite(h, "first_bar_time=" + TimeToString(g_firstBarTime, TIME_DATE|TIME_MINUTES|TIME_SECONDS));
      FileWrite(h, "last_bar_time=" + TimeToString(g_lastBarTime, TIME_DATE|TIME_MINUTES|TIME_SECONDS));
      FileWrite(h, "first_bar_time_raw=" + IntegerToString((long)g_firstBarTime));
      FileWrite(h, "last_bar_time_raw=" + IntegerToString((long)g_lastBarTime));
      FileWrite(h, "bar_count=" + IntegerToString(g_barCount));
      FileWrite(h, "deinit_reason=" + IntegerToString(reason));
      FileClose(h);
   }
   int hd = FileOpen("nxs_volbrk_tester_window_probe_done.txt", FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(hd != INVALID_HANDLE){
      FileWrite(hd, "done=1");
      FileClose(hd);
   }
}

double OnTester(){
   return 0.0;
}
