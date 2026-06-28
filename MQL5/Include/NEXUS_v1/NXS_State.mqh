//+------------------------------------------------------------------+
//|  NXS_State.mqh - Persist critical EA state across restarts        |
//|  Stores: g_tradesToday, g_balanceDayStart, g_consecLosses,        |
//|          g_eslHit, g_dptHit, g_antiRevengeUntil, g_dayStart       |
//|  File: Files/NEXUS_state_<magic>.bin                              |
//+------------------------------------------------------------------+
#ifndef __NXS_STATE_MQH__
#define __NXS_STATE_MQH__

datetime g_lastStateSave = 0;
int      g_stateSaveSec  = 30;   // persist every 30 seconds

string _NXS_StateFile(){
   return StringFormat("NEXUS_state_%I64d_%s.bin", InpMagic, g_sym);
}

void NXS_State_Save(){
   // AUDITPATCH: do not share daily counters/protection state across tester runs.
   if(MQLInfoInteger(MQL_TESTER)) return;
   if(!InpUseStatePersist) return;
   if(TimeCurrent() - g_lastStateSave < g_stateSaveSec) return;
   g_lastStateSave = TimeCurrent();

   int h = FileOpen(_NXS_StateFile(), FILE_BIN|FILE_WRITE|FILE_COMMON);
   if(h == INVALID_HANDLE){
      if(InpDebugLog) PrintFormat("[NEXUS STATE] save FAILED err=%d", GetLastError());
      return;
   }
   FileWriteInteger(h, 1, INT_VALUE);            // schema version
   FileWriteLong(h, (long)g_dayStart);
   FileWriteDouble(h, g_balanceDayStart);
   FileWriteInteger(h, g_tradesToday);
   FileWriteInteger(h, g_consecLosses);
   FileWriteLong(h, (long)g_antiRevengeUntil);
   FileWriteInteger(h, g_eslHit ? 1 : 0);
   FileWriteInteger(h, g_dptHit ? 1 : 0);
   FileWriteInteger(h, g_pausedUntilNextOpen ? 1 : 0);
   FileWriteInteger(h, g_skipNextSignals);
   FileWriteLong(h, (long)TimeCurrent());
   FileClose(h);
}

void NXS_State_Load(){
   // AUDITPATCH: each tester run starts from a clean deterministic state.
   if(MQLInfoInteger(MQL_TESTER)) return;
   if(!InpUseStatePersist) return;
   if(!FileIsExist(_NXS_StateFile(), FILE_COMMON)){
      Print("[NEXUS STATE] no prior state - fresh start");
      return;
   }
   int h = FileOpen(_NXS_StateFile(), FILE_BIN|FILE_READ|FILE_COMMON);
   if(h == INVALID_HANDLE){
      PrintFormat("[NEXUS STATE] load FAILED err=%d", GetLastError());
      return;
   }
   int  ver         = FileReadInteger(h, INT_VALUE);
   if(ver != 1){ FileClose(h); Print("[NEXUS STATE] schema mismatch, ignoring"); return; }
   long dayStart    = FileReadLong(h);
   double bal0      = FileReadDouble(h);
   int  tradesToday = FileReadInteger(h);
   int  consecLoss  = FileReadInteger(h);
   long antiRev     = FileReadLong(h);
   int  esl         = FileReadInteger(h);
   int  dpt         = FileReadInteger(h);
   int  paused      = FileReadInteger(h);
   int  skip        = FileReadInteger(h);
   long savedAt     = FileReadLong(h);
   FileClose(h);

   // Only restore if same trading day
   MqlDateTime nowDt; TimeToStruct(TimeCurrent(), nowDt);
   nowDt.hour = 0; nowDt.min = 0; nowDt.sec = 0;
   datetime today = StructToTime(nowDt);
   if((datetime)dayStart != today){
      PrintFormat("[NEXUS STATE] saved state is from a different day (saved=%s today=%s) - ignored",
                  TimeToString((datetime)dayStart), TimeToString(today));
      return;
   }

   g_dayStart            = (datetime)dayStart;
   g_balanceDayStart     = bal0;
   g_tradesToday         = tradesToday;
   g_consecLosses        = consecLoss;
   g_antiRevengeUntil    = (datetime)antiRev;
   g_eslHit              = (esl != 0);
   g_dptHit              = (dpt != 0);
   g_pausedUntilNextOpen = (paused != 0);
   g_skipNextSignals     = skip;

   PrintFormat("[NEXUS STATE] restored | trades_today=%d consec_loss=%d ESL=%s DPT=%s paused=%s (saved %s)",
               g_tradesToday, g_consecLosses,
               (g_eslHit?"YES":"NO"), (g_dptHit?"YES":"NO"),
               (g_pausedUntilNextOpen?"YES":"NO"),
               TimeToString((datetime)savedAt, TIME_DATE|TIME_MINUTES));
}

#endif
