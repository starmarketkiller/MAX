//+------------------------------------------------------------------+
//|  NXS_TradeLedger.mqh — PR1: trade lifecycle ledger                |
//|                                                                   |
//|  Distingue i 4 livelli del ciclo di vita:                         |
//|    deal (fill atomico) -> order -> position -> TRADE LOGICO.      |
//|  Un trade logico = una position (DEAL_POSITION_ID) su conto       |
//|  hedging: tutti i deal IN/OUT della stessa position sono lo       |
//|  stesso trade.                                                    |
//|                                                                   |
//|  Garanzie:                                                        |
//|   - esattamente UN evento FINAL (TRADE_CLOSED) per trade logico,  |
//|     con PnL/volumi/prezzi AGGREGATI sui parziali;                 |
//|   - replay di deal duplicati = nessun doppio evento (lo stato     |
//|     deriva dall'aggregato di history, non dal singolo evento);    |
//|   - restart/resync: l'emitted-set persistito evita di ri-emettere |
//|     chiusure gia' notificate prima dello shutdown;                |
//|   - due position sullo stesso simbolo = due trade logici          |
//|     indipendenti (chiave position_id, mai symbol).                |
//|                                                                   |
//|  Design: "aggregate-diff". Ogni deal event fa ri-aggregare la     |
//|  position da history e confronta con lo stato precedente: la      |
//|  differenza determina l'evento (OPEN/SCALE_IN/PARTIAL/FINAL).     |
//|  Ordine di consegna, duplicati e riavvii diventano irrilevanti.   |
//|                                                                   |
//|  Limiti documentati:                                              |
//|   - conti NETTING: position_id sopravvive ai flip di direzione,   |
//|     quindi "position == trade logico" non regge; il ledger logga  |
//|     un warning sul primo deal INOUT e tratta il flip come FINAL   |
//|     del trade precedente. Il progetto gira su hedging (XM).       |
//|   - DEAL_ENTRY_OUT_BY (close-by): volume e PnL sono contati sul   |
//|     deal della position corrente; la position opposta genera il   |
//|     proprio evento.                                               |
//+------------------------------------------------------------------+
#ifndef __NXS_TRADE_LEDGER_MQH__
#define __NXS_TRADE_LEDGER_MQH__

#define NXS_LEDGER_EV_NONE     0   // duplicato / non nostro / nessun cambiamento
#define NXS_LEDGER_EV_OPEN     1   // primo deal IN della position
#define NXS_LEDGER_EV_SCALE_IN 2   // volume IN aggiuntivo sulla stessa position
#define NXS_LEDGER_EV_PARTIAL  3   // uscita parziale (position ancora viva)
#define NXS_LEDGER_EV_FINAL    4   // chiusura del trade logico (exactly-once)

#define NXS_LEDGER_MAX_EMITTED 8192   // cap FIFO dell'emitted-set persistito

// ----- snapshot aggregato di un trade logico (da history) -----
struct SNxsLedgerTrade {
   ulong    position_id;
   string   symbol;
   long     magic;
   string   strategy;       // dal commento del primo deal IN ("x|STRAT|score")
   double   score;          // score stampato nel commento IN (0 se assente)
   string   side;           // direzione logica: "BUY"/"SELL"
   double   vol_in;         // volume totale entrato
   double   vol_out;        // volume totale uscito
   double   vwap_in;        // prezzo medio pesato di ingresso
   double   vwap_out;       // prezzo medio pesato di uscita
   double   pnl;            // profit+swap+commission REALIZZATI (tutti gli OUT)
   double   risk_money;     // |open-SL| del primo IN in valuta (0 se SL assente)
   datetime open_time;      // primo IN
   datetime close_time;     // ultimo OUT
   string   close_reason;   // trigger dell'ultimo OUT (sl/tp/stop_out/expert/…)
   int      partial_count;  // deal OUT prima di quello finale
   int      deal_count;     // deal totali visti per la position
   bool     from_boot;      // true = chiusura rilevata dal resync di boot
};

// ----- stato interno per-position (per il diff) -----
struct SNxsLedgerState {
   ulong  position_id;
   int    deal_count;
   double vol_in;
   double vol_out;
   double pnl;
   bool   emitted;          // FINAL gia' emesso per questa position
};

SNxsLedgerState g_ledgerState[];
ulong           g_ledgerEmitted[];      // position_id gia' notificate (persistito)
SNxsLedgerTrade g_ledgerClosedQ[];      // coda FIFO delle chiusure logiche
bool            g_ledgerNettingWarned = false;

// ---------------------------------------------------------------- utils ----
double _nxs_ledger_volEps(string sym){
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   return (step > 0.0) ? step * 0.5 : 0.005;
}

string _nxs_ledger_emittedFile(){
   return StringFormat("NEXUS_v1_ledger_emitted_%I64d_%I64d.bin",
                       (long)AccountInfoInteger(ACCOUNT_LOGIN), (long)InpMagic);
}

bool NXS_Ledger_Emitted(ulong posId){
   for(int i = ArraySize(g_ledgerEmitted) - 1; i >= 0; i--)
      if(g_ledgerEmitted[i] == posId) return true;
   return false;
}

void _nxs_ledger_markEmitted(ulong posId){
   if(NXS_Ledger_Emitted(posId)) return;
   int n = ArraySize(g_ledgerEmitted);
   if(n >= NXS_LEDGER_MAX_EMITTED){       // FIFO trim: scarta il piu' vecchio
      ArrayCopy(g_ledgerEmitted, g_ledgerEmitted, 0, 1, n - 1);
      ArrayResize(g_ledgerEmitted, n - 1);
      n--;
   }
   ArrayResize(g_ledgerEmitted, n + 1);
   g_ledgerEmitted[n] = posId;
}

// Persistenza SOLO live: nel tester ogni run parte pulita e non esistono
// restart a meta' run; un file condiviso inquinerebbe i backtest.
void NXS_Ledger_Persist(){
   if(MQLInfoInteger(MQL_TESTER)) return;
   int h = FileOpen(_nxs_ledger_emittedFile(), FILE_WRITE|FILE_BIN);
   if(h == INVALID_HANDLE) return;
   int n = ArraySize(g_ledgerEmitted);
   FileWriteInteger(h, n, INT_VALUE);
   for(int i = 0; i < n; i++) FileWriteLong(h, (long)g_ledgerEmitted[i]);
   FileClose(h);
}

void _nxs_ledger_loadEmitted(){
   if(MQLInfoInteger(MQL_TESTER)) return;
   int h = FileOpen(_nxs_ledger_emittedFile(), FILE_READ|FILE_BIN);
   if(h == INVALID_HANDLE) return;
   int n = FileReadInteger(h, INT_VALUE);
   if(n < 0 || n > NXS_LEDGER_MAX_EMITTED){ FileClose(h); return; }
   ArrayResize(g_ledgerEmitted, n);
   for(int i = 0; i < n; i++) g_ledgerEmitted[i] = (ulong)FileReadLong(h);
   FileClose(h);
}

int _nxs_ledger_stateIdx(ulong posId){
   for(int i = ArraySize(g_ledgerState) - 1; i >= 0; i--)
      if(g_ledgerState[i].position_id == posId) return i;
   return -1;
}

// --------------------------------------------------- aggregazione pura -----
// Ricostruisce lo snapshot aggregato del trade logico dai deal in history.
// Funzione PURA rispetto allo stato del ledger: usata sia dal diff sia da
// NXS_HistorySync per il resync a livello di trade logico.
// NB: usa HistorySelectByPosition, che cambia la selezione history globale:
// i chiamanti che iterano una propria selezione devono ri-selezionare dopo.
bool NXS_Ledger_AggregatePosition(ulong posId, SNxsLedgerTrade &t){
   t.position_id = posId; t.symbol = ""; t.magic = 0; t.strategy = "";
   t.score = 0; t.side = ""; t.vol_in = 0; t.vol_out = 0; t.vwap_in = 0;
   t.vwap_out = 0; t.pnl = 0; t.risk_money = 0; t.open_time = 0;
   t.close_time = 0; t.close_reason = "unknown"; t.partial_count = 0;
   t.deal_count = 0; t.from_boot = false;

   if(!HistorySelectByPosition(posId)) return false;
   int total = HistoryDealsTotal();
   if(total <= 0) return false;

   int outCount = 0;
   datetime lastOutTime = 0;
   for(int i = 0; i < total; i++){
      ulong d = HistoryDealGetTicket(i);
      if(d == 0) continue;
      ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(d, DEAL_ENTRY);
      double v     = HistoryDealGetDouble(d, DEAL_VOLUME);
      double price = HistoryDealGetDouble(d, DEAL_PRICE);
      datetime tm  = (datetime)HistoryDealGetInteger(d, DEAL_TIME);
      t.deal_count++;
      if(t.magic == 0)       t.magic  = HistoryDealGetInteger(d, DEAL_MAGIC);
      if(t.symbol == "")     t.symbol = HistoryDealGetString(d, DEAL_SYMBOL);

      if(entry == DEAL_ENTRY_INOUT && !g_ledgerNettingWarned){
         g_ledgerNettingWarned = true;
         PrintFormat("[NEXUS LEDGER] WARNING: deal INOUT (netting flip) su pos %I64u — "
                     "'position == trade logico' non regge sui conti netting; "
                     "il flip viene trattato come chiusura del trade precedente.", posId);
      }

      if(entry == DEAL_ENTRY_IN){
         double prev = t.vol_in;
         t.vol_in += v;
         if(t.vol_in > 0) t.vwap_in = (t.vwap_in * prev + price * v) / t.vol_in;
         if(t.open_time == 0 || tm < t.open_time) t.open_time = tm;
         ENUM_DEAL_TYPE dt = (ENUM_DEAL_TYPE)HistoryDealGetInteger(d, DEAL_TYPE);
         if(t.side == "") t.side = (dt == DEAL_TYPE_BUY) ? "BUY" : "SELL";
         if(t.strategy == ""){
            // commento stampato da NXS_OpenTrade: "<comment>|<strat>|<score>"
            string cm = HistoryDealGetString(d, DEAL_COMMENT);
            int p1 = StringFind(cm, "|");
            if(p1 >= 0){
               int p2 = StringFind(cm, "|", p1 + 1);
               if(p2 > p1){
                  t.strategy = StringSubstr(cm, p1 + 1, p2 - p1 - 1);
                  t.score    = StringToDouble(StringSubstr(cm, p2 + 1));
               } else t.strategy = StringSubstr(cm, p1 + 1);
            }
         }
         if(t.risk_money == 0){
            double slP = HistoryDealGetDouble(d, DEAL_SL);
            if(price > 0 && slP > 0){
               double tickV  = SymbolInfoDouble(t.symbol, SYMBOL_TRADE_TICK_VALUE);
               double tickSz = SymbolInfoDouble(t.symbol, SYMBOL_TRADE_TICK_SIZE);
               if(tickSz > 0)
                  t.risk_money = (MathAbs(price - slP) / tickSz) * tickV * v;
            }
         }
      }
      else if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY ||
              entry == DEAL_ENTRY_INOUT){
         double prev = t.vol_out;
         t.vol_out += v;
         if(t.vol_out > 0) t.vwap_out = (t.vwap_out * prev + price * v) / t.vol_out;
         t.pnl += HistoryDealGetDouble(d, DEAL_PROFIT)
                + HistoryDealGetDouble(d, DEAL_SWAP)
                + HistoryDealGetDouble(d, DEAL_COMMISSION);
         outCount++;
         if(tm >= lastOutTime){
            lastOutTime = tm;
            t.close_time = tm;
            t.close_reason = _NXS_HistTrigger(HistoryDealGetInteger(d, DEAL_REASON));
         }
      }
   }
   t.partial_count = (outCount > 0) ? outCount - 1 : 0;
   return (t.vol_in > 0 || t.vol_out > 0);
}

// Il trade logico e' chiuso quando tutto il volume e' uscito E la position
// non esiste piu' (doppio controllo: il solo volume soffre di arrotondamenti,
// la sola sparizione della position soffre di race col terminale).
bool NXS_Ledger_IsClosed(const SNxsLedgerTrade &t){
   if(t.vol_in <= 0) return (t.vol_out > 0 && !PositionSelectByTicket(t.position_id));
   bool volDone = (t.vol_out >= t.vol_in - _nxs_ledger_volEps(t.symbol));
   return volDone && !PositionSelectByTicket(t.position_id);
}

// R-multiple aggregata del trade logico: PnL totale / rischio iniziale.
// Stesso fallback del vecchio _nxs_stats_dealR quando l'SL manca.
double NXS_Ledger_RMultiple(const SNxsLedgerTrade &t){
   if(t.risk_money > 0) return t.pnl / t.risk_money;
   if(t.pnl > 0) return 1.0;
   if(t.pnl < 0) return -1.0;
   return 0.0;
}

// Nei run lunghi del tester lo stato per-position crescerebbe senza limite:
// le entry gia' emesse piu' vecchie vengono potate (l'emitted-set persistito
// resta l'autorita' anti-doppione anche dopo la potatura).
void _nxs_ledger_pruneStates(){
   int n = ArraySize(g_ledgerState);
   if(n <= 1024) return;
   SNxsLedgerState keep[];
   for(int i = 0; i < n; i++){
      if(!g_ledgerState[i].emitted || i >= n - 512){
         int k = ArraySize(keep);
         ArrayResize(keep, k + 1);
         keep[k] = g_ledgerState[i];
      }
   }
   ArrayFree(g_ledgerState);
   ArrayCopy(g_ledgerState, keep);
}

// Rete di sicurezza periodica (OnTimer): ri-tocca le position non ancora
// emesse la cui position e' sparita — copre il caso in cui l'ultimo evento
// deal sia andato perso o sia arrivato mentre la position era ancora viva.
int NXS_Ledger_SweepPending(){
   int finals = 0;
   for(int i = ArraySize(g_ledgerState) - 1; i >= 0; i--){
      if(g_ledgerState[i].emitted) continue;
      if(PositionSelectByTicket(g_ledgerState[i].position_id)) continue;
      double dummy;
      if(NXS_Ledger_Touch(g_ledgerState[i].position_id, dummy) == NXS_LEDGER_EV_FINAL)
         finals++;
   }
   return finals;
}

// ------------------------------------------------------------ il diff ------
// Ri-aggrega la position e confronta con lo stato precedente.
// Ritorna l'evento; outRealizedDelta = PnL realizzato NUOVO rispetto
// all'ultimo stato (per le protezioni daily-DD, che vivono di realizzato).
// Le chiusure logiche finiscono in coda (NXS_Ledger_PopClosed) UNA volta sola.
int NXS_Ledger_Touch(ulong posId, double &outRealizedDelta, bool fromBoot = false){
   outRealizedDelta = 0.0;
   if(posId == 0) return NXS_LEDGER_EV_NONE;

   SNxsLedgerTrade t;
   if(!NXS_Ledger_AggregatePosition(posId, t)) return NXS_LEDGER_EV_NONE;
   if(!IsNexusMagic(t.magic)) return NXS_LEDGER_EV_NONE;

   int idx = _nxs_ledger_stateIdx(posId);
   bool isNew = (idx < 0);
   if(isNew){
      idx = ArraySize(g_ledgerState);
      ArrayResize(g_ledgerState, idx + 1);
      g_ledgerState[idx].position_id = posId;
      g_ledgerState[idx].deal_count  = 0;
      g_ledgerState[idx].vol_in      = 0;
      g_ledgerState[idx].vol_out     = 0;
      g_ledgerState[idx].pnl         = 0;
      g_ledgerState[idx].emitted     = NXS_Ledger_Emitted(posId);
   }

   // niente di nuovo (deal duplicato/replay) -> nessun evento. Eccezione:
   // se il trade risulta ORA chiuso e il FINAL non e' mai stato emesso
   // (race: ultimo OUT aggregato mentre la position era ancora visibile),
   // si prosegue per emettere la chiusura.
   bool nothingNew = (t.deal_count <= g_ledgerState[idx].deal_count &&
                      t.vol_out    <= g_ledgerState[idx].vol_out + 1e-12);
   if(nothingNew && (g_ledgerState[idx].emitted || !NXS_Ledger_IsClosed(t)))
      return NXS_LEDGER_EV_NONE;

   outRealizedDelta = t.pnl - g_ledgerState[idx].pnl;
   double eps = _nxs_ledger_volEps(t.symbol);
   bool grewOut = (t.vol_out > g_ledgerState[idx].vol_out + eps * 0.1);
   bool grewIn  = (t.vol_in  > g_ledgerState[idx].vol_in  + eps * 0.1);
   bool wasVirgin = (g_ledgerState[idx].deal_count == 0);

   g_ledgerState[idx].deal_count = t.deal_count;
   g_ledgerState[idx].vol_in     = t.vol_in;
   g_ledgerState[idx].vol_out    = t.vol_out;
   g_ledgerState[idx].pnl        = t.pnl;

   if(NXS_Ledger_IsClosed(t)){
      if(g_ledgerState[idx].emitted) return NXS_LEDGER_EV_NONE;  // exactly-once
      g_ledgerState[idx].emitted = true;
      _nxs_ledger_markEmitted(posId);
      NXS_Ledger_Persist();
      t.from_boot = fromBoot;
      int q = ArraySize(g_ledgerClosedQ);
      ArrayResize(g_ledgerClosedQ, q + 1);
      g_ledgerClosedQ[q] = t;
      _nxs_ledger_pruneStates();
      return NXS_LEDGER_EV_FINAL;
   }
   if(grewOut) return NXS_LEDGER_EV_PARTIAL;
   if(grewIn)  return wasVirgin ? NXS_LEDGER_EV_OPEN : NXS_LEDGER_EV_SCALE_IN;
   return NXS_LEDGER_EV_NONE;
}

// Entry point per OnTradeTransaction: dal deal risale alla position.
int NXS_Ledger_OnDeal(ulong dealTicket, double &outRealizedDelta){
   outRealizedDelta = 0.0;
   if(dealTicket == 0) return NXS_LEDGER_EV_NONE;
   if(!HistoryDealSelect(dealTicket)) return NXS_LEDGER_EV_NONE;
   long magic = HistoryDealGetInteger(dealTicket, DEAL_MAGIC);
   if(!IsNexusMagic(magic)) return NXS_LEDGER_EV_NONE;
   ulong posId = (ulong)HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID);
   return NXS_Ledger_Touch(posId, outRealizedDelta);
}

bool NXS_Ledger_PopClosed(SNxsLedgerTrade &t){
   int n = ArraySize(g_ledgerClosedQ);
   if(n <= 0) return false;
   t = g_ledgerClosedQ[0];
   for(int i = 1; i < n; i++) g_ledgerClosedQ[i - 1] = g_ledgerClosedQ[i];
   ArrayResize(g_ledgerClosedQ, n - 1);
   return true;
}

// --------------------------------------------------------------- boot ------
// Riconcilia lo stato dopo un (ri)avvio: carica l'emitted-set, ricostruisce
// dai deal degli ultimi `days` giorni e mette in coda SOLO le chiusure mai
// notificate (avvenute offline). Le chiusure gia' emesse prima dello
// shutdown restano emesse: zero doppioni dopo il restart.
// Il chiamante decide cosa fare della coda (parita' storica: log soltanto;
// il push al backend resta a NXS_SyncRecentClosedTrades, idempotente).
int NXS_Ledger_Boot(int days = 7){
   _nxs_ledger_loadEmitted();
   if(!HistorySelect(TimeCurrent() - (long)days * 86400, TimeCurrent())) return 0;
   int total = HistoryDealsTotal();

   // raccogli le position nostre PRIMA di toccare la selezione history
   ulong posIds[];
   for(int i = 0; i < total; i++){
      ulong d = HistoryDealGetTicket(i);
      if(d == 0) continue;
      if(!IsNexusMagic(HistoryDealGetInteger(d, DEAL_MAGIC))) continue;
      ulong p = (ulong)HistoryDealGetInteger(d, DEAL_POSITION_ID);
      bool seen = false;
      for(int k = ArraySize(posIds) - 1; k >= 0; k--)
         if(posIds[k] == p){ seen = true; break; }
      if(!seen){
         int n = ArraySize(posIds);
         ArrayResize(posIds, n + 1);
         posIds[n] = p;
      }
   }
   int queued = 0;
   for(int i = 0; i < ArraySize(posIds); i++){
      double dummy;
      if(NXS_Ledger_Touch(posIds[i], dummy, true) == NXS_LEDGER_EV_FINAL) queued++;
   }
   return queued;
}

#endif
