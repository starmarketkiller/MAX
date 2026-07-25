//+------------------------------------------------------------------+
//|  NXS_Intent.mqh — registro durevole dell'INTENTO di esecuzione    |
//|                                                                   |
//|  AUD0-LEDGER-004 / AUD0-LEDGER-006 / AUD0-LEDGER-010 / NXS-TX-002 |
//|                                                                   |
//|  Il problema: identita' e rischio di un trade venivano RICOSTRUITI |
//|  a posteriori dal commento della posizione e dallo stop del primo  |
//|  deal. Il commento non e' un identificatore: MT5 lo tronca, alcuni |
//|  broker lo riscrivono, le gambe di grid/piramide ne portano uno    |
//|  diverso e i parziali lo perdono del tutto. Il rischio dedotto da  |
//|  un solo deal ignora scale-in e gambe successive.                  |
//|                                                                   |
//|  Qui l'intento viene REGISTRATO al momento dell'invio, quando e'   |
//|  ancora un fatto e non una deduzione: strategia, score, budget di  |
//|  rischio deciso dal sizer, rotta e sequenza di appartenenza. La    |
//|  chiave e' il ticket dell'ordine, che il ledger ritrova su ogni    |
//|  deal via DEAL_ORDER.                                              |
//|                                                                   |
//|  Il registro e' persistito (sopravvive ai riavvii), limitato e     |
//|  potato per eta'. Se un intento non si trova, i consumatori        |
//|  ricadono sul vecchio parsing del commento: nessuna regressione,   |
//|  ma con provenienza dichiarata.                                    |
//+------------------------------------------------------------------+
#ifndef __NXS_INTENT_MQH__
#define __NXS_INTENT_MQH__

#define NXS_INTENT_MAX        512
#define NXS_INTENT_KEEP_DAYS   30
#define NXS_INTENT_FILE_MAGIC  0x4E584931   // "NXI1"
#define NXS_INTENT_FILE_VER    1

struct SNxsIntent {
   ulong    order_ticket;   // chiave primaria: ordine inviato
   ulong    position_id;    // risolto al primo deal IN (0 finche' ignoto)
   ulong    group_id;       // sequenza logica: core + sue gambe
   string   strategy;       // identificativo di strategia, non il commento
   double   score;
   double   risk_money;     // budget di rischio DECISO, non dedotto
   double   entry_atr;      // AUD0-STATE-003: ATR AL MOMENTO dell'ingresso
   string   route;          // primary | grid | pyramid | institutional | split
   datetime created;
};

SNxsIntent g_nxsIntents[];
bool       g_nxsIntentLoaded = false;
bool       g_nxsIntentDirty  = false;

string _nxs_intent_file(){
   return StringFormat("NEXUS_v1_intent_%I64d_%I64d.bin",
                       (long)AccountInfoInteger(ACCOUNT_LOGIN), (long)InpMagic);
}

int _nxs_intent_idxByOrder(ulong orderTicket){
   for(int i = ArraySize(g_nxsIntents) - 1; i >= 0; i--)
      if(g_nxsIntents[i].order_ticket == orderTicket) return i;
   return -1;
}

int _nxs_intent_idxByPosition(ulong posId){
   for(int i = ArraySize(g_nxsIntents) - 1; i >= 0; i--)
      if(g_nxsIntents[i].position_id == posId && posId != 0) return i;
   return -1;
}

void _nxs_intent_removeAt(int idx){
   int n = ArraySize(g_nxsIntents);
   if(idx < 0 || idx >= n) return;
   for(int i = idx; i < n - 1; i++) g_nxsIntents[i] = g_nxsIntents[i + 1];
   ArrayResize(g_nxsIntents, n - 1);
   g_nxsIntentDirty = true;
}

void _nxs_intent_prune(){
   datetime cutoff = TimeCurrent() - (long)NXS_INTENT_KEEP_DAYS * 86400;
   for(int i = ArraySize(g_nxsIntents) - 1; i >= 0; i--)
      if(g_nxsIntents[i].created > 0 && g_nxsIntents[i].created < cutoff)
         _nxs_intent_removeAt(i);
   while(ArraySize(g_nxsIntents) > NXS_INTENT_MAX) _nxs_intent_removeAt(0);
}

void NXS_Intent_Save(){
   if(MQLInfoInteger(MQL_TESTER)) return;
   if(!g_nxsIntentDirty) return;
   string finalName = _nxs_intent_file();
   string tmpName   = finalName + ".tmp";
   int h = FileOpen(tmpName, FILE_WRITE|FILE_BIN);
   if(h == INVALID_HANDLE) return;
   int n = ArraySize(g_nxsIntents);
   FileWriteInteger(h, NXS_INTENT_FILE_MAGIC, INT_VALUE);
   FileWriteInteger(h, NXS_INTENT_FILE_VER,   INT_VALUE);
   FileWriteInteger(h, n, INT_VALUE);
   for(int i = 0; i < n; i++){
      FileWriteLong(h,   (long)g_nxsIntents[i].order_ticket);
      FileWriteLong(h,   (long)g_nxsIntents[i].position_id);
      FileWriteLong(h,   (long)g_nxsIntents[i].group_id);
      FileWriteDouble(h, g_nxsIntents[i].score);
      FileWriteDouble(h, g_nxsIntents[i].risk_money);
      FileWriteDouble(h, g_nxsIntents[i].entry_atr);
      FileWriteLong(h,   (long)g_nxsIntents[i].created);
      FileWriteString(h, g_nxsIntents[i].strategy, 32);
      FileWriteString(h, g_nxsIntents[i].route,    16);
   }
   FileFlush(h);
   FileClose(h);
   FileDelete(finalName);
   FileMove(tmpName, 0, finalName, FILE_REWRITE);
   g_nxsIntentDirty = false;
}

void NXS_Intent_Load(){
   if(g_nxsIntentLoaded) return;
   g_nxsIntentLoaded = true;
   if(MQLInfoInteger(MQL_TESTER)) return;
   string name = _nxs_intent_file();
   if(!FileIsExist(name)) return;
   int h = FileOpen(name, FILE_READ|FILE_BIN);
   if(h == INVALID_HANDLE) return;
   int magic = FileReadInteger(h, INT_VALUE);
   int ver   = FileReadInteger(h, INT_VALUE);
   int n     = FileReadInteger(h, INT_VALUE);
   if(magic != NXS_INTENT_FILE_MAGIC || ver != NXS_INTENT_FILE_VER ||
      n < 0 || n > NXS_INTENT_MAX){
      FileClose(h);
      PrintFormat("[NEXUS INTENT] registro non riconosciuto: si riparte vuoto "
                  "(identita' e rischio ricadranno sul commento)");
      return;
   }
   ArrayResize(g_nxsIntents, n);
   for(int i = 0; i < n; i++){
      g_nxsIntents[i].order_ticket = (ulong)FileReadLong(h);
      g_nxsIntents[i].position_id  = (ulong)FileReadLong(h);
      g_nxsIntents[i].group_id     = (ulong)FileReadLong(h);
      g_nxsIntents[i].score        = FileReadDouble(h);
      g_nxsIntents[i].risk_money   = FileReadDouble(h);
      g_nxsIntents[i].entry_atr    = FileReadDouble(h);
      g_nxsIntents[i].created      = (datetime)FileReadLong(h);
      g_nxsIntents[i].strategy     = FileReadString(h, 32);
      g_nxsIntents[i].route        = FileReadString(h, 16);
   }
   FileClose(h);
   _nxs_intent_prune();
}

//: Rischio in valuta di conto per una gamba: |entry-SL| convertito in denaro.
//: E' il budget DECISO all'esecuzione, non una ricostruzione da history.
double NXS_Intent_RiskMoney(string sym, double entry, double sl, double lots){
   if(entry <= 0 || sl <= 0 || lots <= 0) return 0.0;
   double tickV  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double tickSz = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   if(tickSz <= 0 || tickV <= 0) return 0.0;
   return (MathAbs(entry - sl) / tickSz) * tickV * lots;
}

//: Registra l'intento subito dopo un invio riuscito.
//: groupId == 0 => la posizione APRE una nuova sequenza (il gruppo diventa
//: il ticket dell'ordine stesso, stabile e unico).
void NXS_Intent_Record(ulong orderTicket, string strategy, double score,
                       double riskMoney, string route, ulong groupId = 0,
                       double entryAtr = 0.0){
   if(orderTicket == 0) return;
   NXS_Intent_Load();
   int idx = _nxs_intent_idxByOrder(orderTicket);
   if(idx < 0){
      idx = ArraySize(g_nxsIntents);
      ArrayResize(g_nxsIntents, idx + 1);
      g_nxsIntents[idx].position_id = 0;
   }
   g_nxsIntents[idx].order_ticket = orderTicket;
   g_nxsIntents[idx].group_id     = (groupId != 0) ? groupId : orderTicket;
   g_nxsIntents[idx].strategy     = strategy;
   g_nxsIntents[idx].score        = score;
   g_nxsIntents[idx].risk_money   = riskMoney;
   // AUD0-STATE-003 / NXS-STATE-005: l'ATR d'ingresso e' un valore IMMUTABILE
   // del trade. Dopo un riavvio veniva sostituito con l'ATR corrente (o con la
   // distanza dello stop), cambiando le soglie di gestione di una posizione
   // gia' aperta. Qui viene registrato quando e' ancora quello vero.
   g_nxsIntents[idx].entry_atr    = (entryAtr > 0.0 ? entryAtr : g_atr);
   g_nxsIntents[idx].route        = route;
   g_nxsIntents[idx].created      = TimeCurrent();
   g_nxsIntentDirty = true;
   _nxs_intent_prune();
   NXS_Intent_Save();
}

//: Lega l'intento alla position, nota solo quando arriva il primo deal.
void NXS_Intent_BindPosition(ulong orderTicket, ulong posId){
   if(orderTicket == 0 || posId == 0) return;
   NXS_Intent_Load();
   int idx = _nxs_intent_idxByOrder(orderTicket);
   if(idx < 0) return;
   if(g_nxsIntents[idx].position_id == posId) return;
   g_nxsIntents[idx].position_id = posId;
   g_nxsIntentDirty = true;
   NXS_Intent_Save();
}

bool NXS_Intent_ByOrder(ulong orderTicket, SNxsIntent &out){
   NXS_Intent_Load();
   int idx = _nxs_intent_idxByOrder(orderTicket);
   if(idx < 0) return false;
   out = g_nxsIntents[idx];
   return true;
}

bool NXS_Intent_ByPosition(ulong posId, SNxsIntent &out){
   NXS_Intent_Load();
   int idx = _nxs_intent_idxByPosition(posId);
   if(idx < 0) return false;
   out = g_nxsIntents[idx];
   return true;
}

//: Sequenza a partire dal TICKET di una posizione aperta. Ticket e
//: POSITION_IDENTIFIER non sono sempre lo stesso valore: la chiave del ledger
//: e' l'identifier, quindi va risolto esplicitamente (cfr. AUD0-LEDGER-008).
ulong NXS_Intent_GroupOfTicket(ulong ticket);

//: Sequenza di appartenenza di una position gia' nota (0 se sconosciuta).
ulong NXS_Intent_GroupOf(ulong posId){
   SNxsIntent it;
   if(NXS_Intent_ByPosition(posId, it)) return it.group_id;
   return 0;
}

ulong NXS_Intent_GroupOfTicket(ulong ticket){
   if(ticket == 0) return 0;
   if(!PositionSelectByTicket(ticket)) return 0;
   return NXS_Intent_GroupOf((ulong)PositionGetInteger(POSITION_IDENTIFIER));
}

#endif
