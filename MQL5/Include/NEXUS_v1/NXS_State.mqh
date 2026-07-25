//+------------------------------------------------------------------+
//| NXS_State.mqh - versioned atomic operational snapshot            |
//+------------------------------------------------------------------+
#ifndef __NXS_STATE_MQH__
#define __NXS_STATE_MQH__

#define NXS_STATE_MAGIC   0x4E585335
#define NXS_STATE_SCHEMA  3
#define NXS_STATE_MAX_POS 512

struct SNXSManagedState {
   ulong ticket;
   long positionId;
   string logicalId;
   string groupId;
   string strategyId;
   double entryAtr;
   int profileVersion;
   string phase;
   string lastEvent;
   double residualVolume;
   bool splitP1;
   bool splitP2;
};

datetime g_lastStateSave = 0;
int g_stateSaveSec = 30;
bool g_stateRestoreHealthy = true;
SNXSManagedState g_managedState[NXS_STATE_MAX_POS];
int g_managedStateCount = 0;

// AUD0-STATE-001 / NXS-STATE-001: il nome conteneva solo magic e simbolo, ma
// i file vivono in FILE_COMMON — cartella CONDIVISA tra tutti i terminali
// della macchina. Due account (o due terminali) con lo stesso magic sullo
// stesso simbolo scrivevano nello stesso snapshot, contaminandosi a vicenda.
// La chiave include ora login del conto e server del broker.
string _NXS_StateFile(){
   string server = AccountInfoString(ACCOUNT_SERVER);
   StringReplace(server, "\\", "_");
   StringReplace(server, "/", "_");
   StringReplace(server, " ", "_");
   StringReplace(server, ":", "_");
   return StringFormat("NEXUS_state_%I64d_%s_%I64d_%s.bin",
                       (long)AccountInfoInteger(ACCOUNT_LOGIN), server,
                       InpMagic, g_sym);
}
string _NXS_StateTmp(){ return _NXS_StateFile() + ".tmp"; }
string _NXS_StatePrev(){ return _NXS_StateFile() + ".prev"; }

void _NXS_WriteString(int h, string value){
   int n = StringLen(value);
   FileWriteInteger(h, n, INT_VALUE);
   if(n > 0) FileWriteString(h, value, n);
}

string _NXS_ReadString(int h){
   int n = FileReadInteger(h, INT_VALUE);
   if(n < 0 || n > 4096) return "";
   return (n > 0) ? FileReadString(h, n) : "";
}

int NXS_State_FindByPositionId(long positionId){
   for(int i=0; i<g_managedStateCount; i++)
      if(g_managedState[i].positionId == positionId) return i;
   return -1;
}

int NXS_State_FindTicket(ulong ticket){
   for(int i=0; i<g_managedStateCount; i++)
      if(g_managedState[i].ticket == ticket) return i;
   return -1;
}

void _NXS_StateParseComment(string comment, string &strategy, string &group){
   strategy = "UNKNOWN"; group = "UNGROUPED";
   string parts[]; int n = StringSplit(comment, '|', parts);
   if(n >= 2 && StringLen(parts[1]) > 0){ strategy = parts[1]; group = parts[1]; }
}

void NXS_State_ReconcileBroker(){
   SNXSManagedState reconciled[NXS_STATE_MAX_POS]; int count = 0;
   for(int i=PositionsTotal()-1; i>=0 && count<NXS_STATE_MAX_POS; i--){
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      long pid = (long)PositionGetInteger(POSITION_IDENTIFIER);
      int old = NXS_State_FindByPositionId(pid);
      if(old >= 0) reconciled[count] = g_managedState[old];
      else {
         ZeroMemory(reconciled[count]);
         reconciled[count].positionId = pid;
         reconciled[count].logicalId = StringFormat("POS-%I64d", pid);
         _NXS_StateParseComment(PositionGetString(POSITION_COMMENT),
                                reconciled[count].strategyId, reconciled[count].groupId);
         double open = PositionGetDouble(POSITION_PRICE_OPEN);
         double sl = PositionGetDouble(POSITION_SL);
         reconciled[count].entryAtr = (g_atr > 0) ? g_atr : MathAbs(open - sl);
         reconciled[count].profileVersion = 1;
         reconciled[count].phase = "INITIAL";
         reconciled[count].lastEvent = "BROKER_RECONCILED";
      }
      reconciled[count].ticket = ticket;
      reconciled[count].residualVolume = PositionGetDouble(POSITION_VOLUME);
      count++;
   }
   g_managedStateCount = count;
   for(int i=0; i<count; i++) g_managedState[i] = reconciled[i];
}

double NXS_State_EntryAtr(ulong ticket, double fallback){
   int i = NXS_State_FindTicket(ticket);
   if(i >= 0 && g_managedState[i].entryAtr > 0) return g_managedState[i].entryAtr;
   return fallback;
}

bool NXS_State_HasApplied(ulong ticket, string source){
   int i = NXS_State_FindTicket(ticket);
   if(i < 0) return false;
   if(source == "SPLIT_P1") return g_managedState[i].splitP1;
   if(source == "SPLIT_P2") return g_managedState[i].splitP2;
   return g_managedState[i].lastEvent == source;
}

void NXS_State_RecordManagement(ulong ticket, string source){
   NXS_State_ReconcileBroker();
   int i = NXS_State_FindTicket(ticket);
   if(i < 0) return;
   g_managedState[i].lastEvent = source;
   if(source == "SPLIT_P1") g_managedState[i].splitP1 = true;
   if(source == "SPLIT_P2") g_managedState[i].splitP2 = true;
   if(StringFind(source, "BREAKEVEN") >= 0) g_managedState[i].phase = "BREAKEVEN";
   else if(source == "SPLIT_P1" || source == "SPLIT_P2") g_managedState[i].phase = "PARTIAL";
   else if(StringFind(source, "TRAIL") >= 0 || source == "INSTITUTIONAL") g_managedState[i].phase = "RUNNER";
}

bool _NXS_StateWrite(string fileName){
   int h = FileOpen(fileName, FILE_BIN|FILE_WRITE|FILE_COMMON);
   if(h == INVALID_HANDLE) return false;
   FileWriteInteger(h, NXS_STATE_MAGIC, INT_VALUE);
   FileWriteInteger(h, NXS_STATE_SCHEMA, INT_VALUE);
   FileWriteLong(h, (long)TimeCurrent());
   FileWriteLong(h, (long)g_dayStart);
   FileWriteDouble(h, g_balanceDayStart);
   FileWriteInteger(h, g_tradesToday);
   FileWriteInteger(h, g_consecLosses);
   FileWriteLong(h, (long)g_antiRevengeUntil);
   FileWriteInteger(h, g_eslHit ? 1 : 0);
   FileWriteInteger(h, g_dptHit ? 1 : 0);
   FileWriteInteger(h, g_pausedUntilNextOpen ? 1 : 0);
   FileWriteInteger(h, g_skipNextSignals);
   // AUD0-STATE-004 / AUD0-RS-007 / AUD0-PROT-004: questi campi erano solo in
   // memoria. Un riavvio azzerava freeze di ruin, breaker di equity, flatten
   // incompiuto e streak: il conto ripartiva come se nulla fosse successo,
   // proprio dopo l'evento che aveva richiesto la protezione.
   FileWriteLong(h, (long)g_ruinFrozenDay);
   FileWriteLong(h, (long)g_NXSrsBreakerUntil);
   FileWriteDouble(h, g_NXSrsLastSharpe);
   FileWriteInteger(h, g_autoClosePending ? 1 : 0);
   FileWriteInteger(h, g_flattenPending ? 1 : 0);
   _NXS_WriteString(h, g_flattenReason);
   FileWriteInteger(h, g_streakWins);
   FileWriteInteger(h, g_streakLosses);
   FileWriteDouble(h, g_streakLotMult);
   FileWriteInteger(h, g_managedStateCount);
   for(int i=0; i<g_managedStateCount; i++){
      FileWriteLong(h, (long)g_managedState[i].ticket);
      FileWriteLong(h, g_managedState[i].positionId);
      _NXS_WriteString(h, g_managedState[i].logicalId);
      _NXS_WriteString(h, g_managedState[i].groupId);
      _NXS_WriteString(h, g_managedState[i].strategyId);
      FileWriteDouble(h, g_managedState[i].entryAtr);
      FileWriteInteger(h, g_managedState[i].profileVersion);
      _NXS_WriteString(h, g_managedState[i].phase);
      _NXS_WriteString(h, g_managedState[i].lastEvent);
      FileWriteDouble(h, g_managedState[i].residualVolume);
      FileWriteInteger(h, g_managedState[i].splitP1 ? 1 : 0);
      FileWriteInteger(h, g_managedState[i].splitP2 ? 1 : 0);
   }
   FileWriteInteger(h, NXS_STATE_MAGIC, INT_VALUE);
   FileFlush(h); FileClose(h);
   return true;
}

bool _NXS_StateRead(string fileName, bool apply){
   int h = FileOpen(fileName, FILE_BIN|FILE_READ|FILE_COMMON);
   if(h == INVALID_HANDLE) return false;
   int magic = FileReadInteger(h, INT_VALUE);
   int ver = FileReadInteger(h, INT_VALUE);
   if(magic != NXS_STATE_MAGIC || ver != NXS_STATE_SCHEMA){ FileClose(h); return false; }
   long savedAt = FileReadLong(h);
   long dayStart = FileReadLong(h);
   double bal0 = FileReadDouble(h);
   int tradesToday = FileReadInteger(h);
   int consecLoss = FileReadInteger(h);
   long antiRev = FileReadLong(h);
   int esl = FileReadInteger(h), dpt = FileReadInteger(h);
   int paused = FileReadInteger(h), skip = FileReadInteger(h);
   long ruinDay      = FileReadLong(h);
   long breakerUntil = FileReadLong(h);
   double lastSharpe = FileReadDouble(h);
   int autoClose     = FileReadInteger(h);
   int flattenPend   = FileReadInteger(h);
   string flattenRsn = _NXS_ReadString(h);
   int streakW       = FileReadInteger(h);
   int streakL       = FileReadInteger(h);
   double streakMult = FileReadDouble(h);
   int count = FileReadInteger(h);
   if(count < 0 || count > NXS_STATE_MAX_POS){ FileClose(h); return false; }
   SNXSManagedState loaded[NXS_STATE_MAX_POS];
   for(int i=0; i<count; i++){
      ZeroMemory(loaded[i]);
      loaded[i].ticket = (ulong)FileReadLong(h);
      loaded[i].positionId = FileReadLong(h);
      loaded[i].logicalId = _NXS_ReadString(h);
      loaded[i].groupId = _NXS_ReadString(h);
      loaded[i].strategyId = _NXS_ReadString(h);
      loaded[i].entryAtr = FileReadDouble(h);
      loaded[i].profileVersion = FileReadInteger(h);
      loaded[i].phase = _NXS_ReadString(h);
      loaded[i].lastEvent = _NXS_ReadString(h);
      loaded[i].residualVolume = FileReadDouble(h);
      loaded[i].splitP1 = FileReadInteger(h) != 0;
      loaded[i].splitP2 = FileReadInteger(h) != 0;
   }
   int trailer = FileReadInteger(h, INT_VALUE); FileClose(h);
   if(trailer != NXS_STATE_MAGIC) return false;
   if(!apply) return true;
   g_managedStateCount = count;
   for(int i=0; i<count; i++) g_managedState[i] = loaded[i];

   // La safety state va ripristinata SEMPRE, non solo nello stesso giorno:
   // un breaker di equity con scadenza a 24h o un flatten incompiuto non
   // smettono di valere perché è cambiata la data.
   g_ruinFrozenDay      = (datetime)ruinDay;
   g_NXSrsBreakerUntil  = (datetime)breakerUntil;
   g_NXSrsLastSharpe    = lastSharpe;
   g_autoClosePending   = (autoClose != 0);
   g_flattenPending     = (flattenPend != 0);
   g_flattenReason      = flattenRsn;
   g_streakWins         = streakW;
   g_streakLosses       = streakL;
   g_streakLotMult      = (streakMult > 0 ? streakMult : 1.0);
   if(g_flattenPending)
      PrintFormat("[NEXUS STATE][ALERT] ripreso con FLATTEN INCOMPIUTO (%s): "
                  "nuove entrate bloccate finche' l'esposizione non e' chiusa",
                  g_flattenReason);

   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt); dt.hour=0; dt.min=0; dt.sec=0;
   if((datetime)dayStart == StructToTime(dt)){
      g_dayStart=(datetime)dayStart; g_balanceDayStart=bal0; g_tradesToday=tradesToday;
      g_consecLosses=consecLoss; g_antiRevengeUntil=(datetime)antiRev;
      g_eslHit=(esl!=0); g_dptHit=(dpt!=0); g_pausedUntilNextOpen=(paused!=0);
      g_skipNextSignals=skip;
   }
   PrintFormat("[NEXUS STATE] schema=%d restored positions=%d saved=%s",
               ver, count, TimeToString((datetime)savedAt, TIME_DATE|TIME_SECONDS));
   return true;
}

void NXS_State_Save(bool force=false){
   if(MQLInfoInteger(MQL_TESTER) || !InpUseStatePersist) return;
   if(!force && TimeCurrent()-g_lastStateSave < g_stateSaveSec) return;
   NXS_State_ReconcileBroker();
   string tmp=_NXS_StateTmp(), main=_NXS_StateFile(), prev=_NXS_StatePrev();
   FileDelete(tmp, FILE_COMMON);
   if(!_NXS_StateWrite(tmp) || !_NXS_StateRead(tmp, false)){
      g_stateRestoreHealthy=false; FileDelete(tmp, FILE_COMMON);
      PrintFormat("[NEXUS STATE] STATE_SAVE_FAILED err=%d", GetLastError()); return;
   }
   if(FileIsExist(main, FILE_COMMON)) FileCopy(main, FILE_COMMON, prev, FILE_COMMON|FILE_REWRITE);
   if(!FileMove(tmp, FILE_COMMON, main, FILE_COMMON|FILE_REWRITE)){
      g_stateRestoreHealthy=false;
      PrintFormat("[NEXUS STATE] atomic replace FAILED err=%d", GetLastError()); return;
   }
   g_lastStateSave=TimeCurrent(); g_stateRestoreHealthy=true;
}

void NXS_State_Load(){
   if(MQLInfoInteger(MQL_TESTER) || !InpUseStatePersist) return;
   string main=_NXS_StateFile(), prev=_NXS_StatePrev();
   if(!FileIsExist(main, FILE_COMMON)){ Print("[NEXUS STATE] no prior state - fresh start"); return; }
   bool ok=_NXS_StateRead(main, true);
   if(!ok && FileIsExist(prev, FILE_COMMON)){
      Print("[NEXUS STATE] primary invalid, restoring previous snapshot");
      ok=_NXS_StateRead(prev, true);
   }
   g_stateRestoreHealthy=ok;
   if(!ok){ Print("[NEXUS STATE] STATE_RESTORE_FAILED - new exposure blocked"); return; }
   NXS_State_ReconcileBroker();
}

bool NXS_State_EntryAllowed(){ return g_stateRestoreHealthy; }

#endif
