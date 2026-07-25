//+------------------------------------------------------------------+
//| NXS_State.mqh - versioned atomic operational snapshot            |
//+------------------------------------------------------------------+
#ifndef __NXS_STATE_MQH__
#define __NXS_STATE_MQH__

#define NXS_STATE_MAGIC   0x4E585335
#define NXS_STATE_SCHEMA  4
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
   // AUD0-STATE-008: nel tester lo snapshot vive in un file separato, cosi'
   // una verifica di riavvio non puo' in nessun caso sovrascrivere lo stato
   // operativo di un conto reale.
   string scope = MQLInfoInteger(MQL_TESTER) ? "tester" : "live";
   return StringFormat("NEXUS_state_%s_%I64d_%s_%I64d_%s.bin",
                       scope, (long)AccountInfoInteger(ACCOUNT_LOGIN), server,
                       InpMagic, g_sym);
}
string _NXS_StateTmp(){ return _NXS_StateFile() + ".tmp"; }
string _NXS_StatePrev(){ return _NXS_StateFile() + ".prev"; }

// AUD0-STATE-006 / NXS-STATE-004 — INTEGRITA' DEL CONTENUTO.
//
// La validazione era solo strutturale: magic iniziale, versione, magic finale.
// Una corruzione interna che lasciasse intatti quei tre campi passava
// inosservata, e lo snapshot veniva applicato come valido — riportando in vita
// numeri sbagliati proprio sui contatori di rischio.
//
// Ogni campo scritto e letto alimenta ora una somma di controllo, confrontata
// prima di applicare qualunque valore.
long g_nxsStateSum = 0;
bool g_nxsStateParseOk = true;

void _NXS_SumFeed(long v){ g_nxsStateSum = (g_nxsStateSum * 1000003) ^ v; }
void _NXS_SumFeedD(double v){ _NXS_SumFeed((long)MathRound(v * 1e6)); }
void _NXS_SumFeedS(string v){
   _NXS_SumFeed((long)StringLen(v));
   for(int i = 0; i < StringLen(v); i++) _NXS_SumFeed((long)StringGetCharacter(v, i));
}

void _NXS_WInt(int h, int v){ FileWriteInteger(h, v, INT_VALUE); _NXS_SumFeed((long)v); }
void _NXS_WLong(int h, long v){ FileWriteLong(h, v); _NXS_SumFeed(v); }
void _NXS_WDbl(int h, double v){ FileWriteDouble(h, v); _NXS_SumFeedD(v); }

int  _NXS_RInt(int h){ int v = FileReadInteger(h, INT_VALUE); _NXS_SumFeed((long)v); return v; }
long _NXS_RLong(int h){ long v = FileReadLong(h); _NXS_SumFeed(v); return v; }
double _NXS_RDbl(int h){ double v = FileReadDouble(h); _NXS_SumFeedD(v); return v; }

void _NXS_WriteString(int h, string value){
   int n = StringLen(value);
   FileWriteInteger(h, n, INT_VALUE);
   if(n > 0) FileWriteString(h, value, n);
   _NXS_SumFeedS(value);
}

// AUD0-STATE-007 / NXS-STATE-003 — una lunghezza non plausibile non e' una
// stringa vuota: e' uno snapshot rotto. Prima si restituiva "" e la lettura
// proseguiva, applicando uno stato in parte inventato. Ora l'errore invalida
// l'INTERO snapshot.
string _NXS_ReadString(int h){
   int n = FileReadInteger(h, INT_VALUE);
   if(n < 0 || n > 4096){
      g_nxsStateParseOk = false;
      _NXS_SumFeedS("");
      return "";
   }
   string v = (n > 0) ? FileReadString(h, n) : "";
   if(StringLen(v) != n) g_nxsStateParseOk = false;   // lettura troncata
   _NXS_SumFeedS(v);
   return v;
}

// NXS-STATE-002 — l'intestazione non legava lo snapshot a NULLA: bastava
// copiare un file di un altro conto (o di un'altra build dell'EA) nella
// cartella comune perche' venisse applicato. Questa firma lega conto, server,
// simbolo, magic e build; una discordanza rifiuta il file invece di fidarsi.
string _NXS_StateBinding(){
   return StringFormat("%I64d|%s|%s|%I64d|%d|%d",
                       (long)AccountInfoInteger(ACCOUNT_LOGIN),
                       AccountInfoString(ACCOUNT_SERVER),
                       g_sym, InpMagic,
                       (int)TerminalInfoInteger(TERMINAL_BUILD),
                       NXS_STATE_SCHEMA);
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

         // AUD0-STATE-002 — strategia e gruppo venivano ricostruiti ENTRAMBI
         // dal secondo campo del commento: identita' di strategia, sequenza,
         // gruppo istituzionale e provenienza del setup collassavano in una
         // sola stringa, per giunta modificabile dal broker. Il registro degli
         // intenti le tiene distinte e durevoli.
         SNxsIntent it;
         bool haveIntent = NXS_Intent_ByPosition(pid, it);
         if(haveIntent){
            reconciled[count].strategyId = it.strategy;
            reconciled[count].groupId    = StringFormat("SEQ-%I64u", it.group_id);
         } else {
            _NXS_StateParseComment(PositionGetString(POSITION_COMMENT),
                                   reconciled[count].strategyId, reconciled[count].groupId);
         }

         // AUD0-STATE-003 / NXS-STATE-005 — l'ATR d'ingresso e' immutabile.
         // Sostituirlo con l'ATR CORRENTE (o con la distanza dello stop) dopo
         // un riavvio cambia le soglie di breakeven, trailing e split di una
         // posizione gia' aperta: la stessa posizione veniva gestita con
         // regole diverse prima e dopo il restart.
         if(haveIntent && it.entry_atr > 0){
            reconciled[count].entryAtr = it.entry_atr;
         } else {
            double open = PositionGetDouble(POSITION_PRICE_OPEN);
            double sl = PositionGetDouble(POSITION_SL);
            reconciled[count].entryAtr = (g_atr > 0) ? g_atr : MathAbs(open - sl);
            PrintFormat("[NEXUS STATE] pos %I64d senza ATR d'ingresso registrato: "
                        "si usa un valore APPROSSIMATO (%.5f) — le soglie di "
                        "gestione possono differire da prima del riavvio",
                        pid, reconciled[count].entryAtr);
         }
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
   g_nxsStateSum = 0;
   FileWriteInteger(h, NXS_STATE_MAGIC, INT_VALUE);
   FileWriteInteger(h, NXS_STATE_SCHEMA, INT_VALUE);
   _NXS_WriteString(h, _NXS_StateBinding());        // NXS-STATE-002
   _NXS_WLong(h, (long)TimeCurrent());
   _NXS_WLong(h, (long)g_dayStart);
   // AUD0-STATE-005: il giorno di trading era implicito nell'ora del terminale.
   // Si persiste ora il GIORNO DEL SERVER e lo scarto GMT con cui e' stato
   // calcolato: senza, un cambio di fuso (o l'ora legale del broker) faceva
   // "ereditare" o "perdere" un giorno di limiti di rischio.
   _NXS_WriteString(h, TimeToString(g_dayStart, TIME_DATE));
   _NXS_WLong(h, (long)(TimeCurrent() - TimeGMT()));
   _NXS_WDbl(h, g_balanceDayStart);
   _NXS_WInt(h, g_tradesToday);
   _NXS_WInt(h, g_consecLosses);
   _NXS_WLong(h, (long)g_antiRevengeUntil);
   _NXS_WInt(h, g_eslHit ? 1 : 0);
   _NXS_WInt(h, g_dptHit ? 1 : 0);
   _NXS_WInt(h, g_pausedUntilNextOpen ? 1 : 0);
   _NXS_WInt(h, g_skipNextSignals);
   // AUD0-STATE-004 / AUD0-RS-007 / AUD0-PROT-004: questi campi erano solo in
   // memoria. Un riavvio azzerava freeze di ruin, breaker di equity, flatten
   // incompiuto e streak: il conto ripartiva come se nulla fosse successo,
   // proprio dopo l'evento che aveva richiesto la protezione.
   _NXS_WLong(h, (long)g_ruinFrozenDay);
   _NXS_WLong(h, (long)g_NXSrsBreakerUntil);
   _NXS_WDbl(h, g_NXSrsLastSharpe);
   _NXS_WInt(h, g_autoClosePending ? 1 : 0);
   _NXS_WInt(h, g_flattenPending ? 1 : 0);
   _NXS_WriteString(h, g_flattenReason);
   _NXS_WInt(h, g_streakWins);
   _NXS_WInt(h, g_streakLosses);
   _NXS_WDbl(h, g_streakLotMult);
   _NXS_WInt(h, g_managedStateCount);
   for(int i=0; i<g_managedStateCount; i++){
      _NXS_WLong(h, (long)g_managedState[i].ticket);
      _NXS_WLong(h, g_managedState[i].positionId);
      _NXS_WriteString(h, g_managedState[i].logicalId);
      _NXS_WriteString(h, g_managedState[i].groupId);
      _NXS_WriteString(h, g_managedState[i].strategyId);
      _NXS_WDbl(h, g_managedState[i].entryAtr);
      _NXS_WInt(h, g_managedState[i].profileVersion);
      _NXS_WriteString(h, g_managedState[i].phase);
      _NXS_WriteString(h, g_managedState[i].lastEvent);
      _NXS_WDbl(h, g_managedState[i].residualVolume);
      _NXS_WInt(h, g_managedState[i].splitP1 ? 1 : 0);
      _NXS_WInt(h, g_managedState[i].splitP2 ? 1 : 0);
   }
   FileWriteLong(h, g_nxsStateSum);                 // AUD0-STATE-006
   FileWriteInteger(h, NXS_STATE_MAGIC, INT_VALUE);
   FileFlush(h); FileClose(h);
   return true;
}

bool _NXS_StateRead(string fileName, bool apply){
   int h = FileOpen(fileName, FILE_BIN|FILE_READ|FILE_COMMON);
   if(h == INVALID_HANDLE) return false;
   g_nxsStateSum = 0;
   g_nxsStateParseOk = true;
   int magic = FileReadInteger(h, INT_VALUE);
   int ver = FileReadInteger(h, INT_VALUE);
   if(magic != NXS_STATE_MAGIC || ver != NXS_STATE_SCHEMA){ FileClose(h); return false; }

   // NXS-STATE-002: lo snapshot deve appartenere a QUESTO conto/server/simbolo.
   string binding = _NXS_ReadString(h);
   if(binding != _NXS_StateBinding()){
      FileClose(h);
      PrintFormat("[NEXUS STATE] snapshot RIFIUTATO: appartiene a un'altra "
                  "configurazione (%s, atteso %s)", binding, _NXS_StateBinding());
      return false;
   }

   long savedAt = _NXS_RLong(h);
   long dayStart = _NXS_RLong(h);
   string dayLabel = _NXS_ReadString(h);
   long gmtOffset = _NXS_RLong(h);
   double bal0 = _NXS_RDbl(h);
   int tradesToday = _NXS_RInt(h);
   int consecLoss = _NXS_RInt(h);
   long antiRev = _NXS_RLong(h);
   int esl = _NXS_RInt(h), dpt = _NXS_RInt(h);
   int paused = _NXS_RInt(h), skip = _NXS_RInt(h);
   long ruinDay      = _NXS_RLong(h);
   long breakerUntil = _NXS_RLong(h);
   double lastSharpe = _NXS_RDbl(h);
   int autoClose     = _NXS_RInt(h);
   int flattenPend   = _NXS_RInt(h);
   string flattenRsn = _NXS_ReadString(h);
   int streakW       = _NXS_RInt(h);
   int streakL       = _NXS_RInt(h);
   double streakMult = _NXS_RDbl(h);
   int count = _NXS_RInt(h);
   if(count < 0 || count > NXS_STATE_MAX_POS){ FileClose(h); return false; }
   SNXSManagedState loaded[NXS_STATE_MAX_POS];
   for(int i=0; i<count; i++){
      ZeroMemory(loaded[i]);
      loaded[i].ticket = (ulong)_NXS_RLong(h);
      loaded[i].positionId = _NXS_RLong(h);
      loaded[i].logicalId = _NXS_ReadString(h);
      loaded[i].groupId = _NXS_ReadString(h);
      loaded[i].strategyId = _NXS_ReadString(h);
      loaded[i].entryAtr = _NXS_RDbl(h);
      loaded[i].profileVersion = _NXS_RInt(h);
      loaded[i].phase = _NXS_ReadString(h);
      loaded[i].lastEvent = _NXS_ReadString(h);
      loaded[i].residualVolume = _NXS_RDbl(h);
      loaded[i].splitP1 = _NXS_RInt(h) != 0;
      loaded[i].splitP2 = _NXS_RInt(h) != 0;
   }
   long storedSum = FileReadLong(h);
   long computed  = g_nxsStateSum;
   int trailer = FileReadInteger(h, INT_VALUE); FileClose(h);
   if(trailer != NXS_STATE_MAGIC) return false;

   // AUD0-STATE-007: qualunque campo malformato invalida TUTTO lo snapshot.
   if(!g_nxsStateParseOk){
      Print("[NEXUS STATE] snapshot RIFIUTATO: campo malformato (lettura parziale)");
      return false;
   }
   // AUD0-STATE-006: integrita' del contenuto, non solo della struttura.
   if(storedSum != computed){
      PrintFormat("[NEXUS STATE] snapshot RIFIUTATO: checksum non corrispondente "
                  "(atteso %I64d, calcolato %I64d)", storedSum, computed);
      return false;
   }
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

   // AUD0-STATE-005 — il "giorno" e' quello del SERVER del broker, dichiarato
   // nello snapshot, non una mezzanotte ricalcolata sull'ora locale. Si
   // confronta l'etichetta di giornata; se lo scarto GMT e' cambiato (fuso o
   // ora legale del broker) lo si segnala invece di ereditare limiti che
   // appartengono a un'altra giornata di trading.
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt); dt.hour=0; dt.min=0; dt.sec=0;
   datetime todayStart = StructToTime(dt);
   long nowOffset = (long)(TimeCurrent() - TimeGMT());
   bool sameDay = (dayLabel == TimeToString(todayStart, TIME_DATE));
   if(sameDay && nowOffset != gmtOffset)
      PrintFormat("[NEXUS STATE] scarto GMT del server cambiato (%I64d -> %I64d): "
                  "i limiti giornalieri ripristinati potrebbero riferirsi a una "
                  "sessione diversa", gmtOffset, nowOffset);
   if(sameDay){
      g_dayStart=(datetime)dayStart; g_balanceDayStart=bal0; g_tradesToday=tradesToday;
      g_consecLosses=consecLoss; g_antiRevengeUntil=(datetime)antiRev;
      g_eslHit=(esl!=0); g_dptHit=(dpt!=0); g_pausedUntilNextOpen=(paused!=0);
      g_skipNextSignals=skip;
   }
   PrintFormat("[NEXUS STATE] schema=%d restored positions=%d saved=%s giorno=%s",
               ver, count, TimeToString((datetime)savedAt, TIME_DATE|TIME_SECONDS),
               (sameDay ? "stesso" : "nuovo"));
   return true;
}

bool _NXS_StatePersistEnabled(){
   if(!InpUseStatePersist) return false;
   if(MQLInfoInteger(MQL_TESTER)) return InpStatePersistInTester;
   return true;
}

void NXS_State_Save(bool force=false){
   if(!_NXS_StatePersistEnabled()) return;
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
   if(!_NXS_StatePersistEnabled()) return;
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
