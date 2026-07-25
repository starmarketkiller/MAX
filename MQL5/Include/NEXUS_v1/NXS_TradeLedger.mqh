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

// AUD0-LEDGER-001: il cap FIFO da solo lega la garanzia exactly-once al
// NUMERO di chiusure, non al tempo. Con 8192 finali una position vecchia usciva
// dall'insieme e poteva essere ri-emessa se rientrava nella finestra di
// resync. La ritenzione e' ora anche TEMPORALE: si scartano per prime le
// entry piu' vecchie della finestra di ricostruzione, non le piu' vecchie in
// senso assoluto.
#define NXS_LEDGER_EMITTED_KEEP_DAYS 400
#define NXS_LEDGER_FILE_MAGIC  0x4E584C31   // "NXL1"
#define NXS_LEDGER_FILE_VER    2

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
   double   risk_money;     // rischio iniziale in valuta, sommato su TUTTI gli IN con SL
   bool     risk_known;     // AUD0-LEDGER-005: false => R non calcolabile, MAI inventata
   bool     risk_partial;   // almeno un ingresso senza stop noto => rischio incompleto
   bool     risk_from_intent;      // rischio deciso all'esecuzione, non dedotto
   bool     identity_from_comment; // strategia ricavata dal commento (meno affidabile)
   ulong    group_id;       // AUD0-LEDGER-010: sequenza logica (core+grid+pyramid)
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
datetime        g_ledgerEmittedAt[];    // istante di emissione, parallelo al precedente
SNxsLedgerTrade g_ledgerClosedQ[];      // coda FIFO delle chiusure logiche
bool            g_ledgerNettingWarned = false;

// AUD0-LEDGER-003: il caricamento corrotto usciva in silenzio, lasciando il
// ledger convinto di non aver mai emesso nulla — cioe' pronto a ri-emettere
// ogni chiusura come nuova. Ora lo stato degradato e' esplicito, viene
// segnalato e accompagna gli eventi verso il backend, che puo' trattarli come
// sospetti invece di fidarsi.
bool   g_ledgerDegraded = false;
string g_ledgerDegradedReason = "";

void NXS_Ledger_MarkDegraded(string why){
   if(g_ledgerDegraded) return;
   g_ledgerDegraded = true;
   g_ledgerDegradedReason = why;
   PrintFormat("[NEXUS LEDGER][ALERT] stato anti-doppione DEGRADATO: %s. "
               "Le chiusure gia' notificate potrebbero essere rinviate: la "
               "deduplica resta garantita dal backend sul trade_uid.", why);
}

bool   NXS_Ledger_IsDegraded()      { return g_ledgerDegraded; }
string NXS_Ledger_DegradedReason()  { return g_ledgerDegradedReason; }

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

void _nxs_ledger_dropEmittedAt(int idx){
   int n = ArraySize(g_ledgerEmitted);
   if(idx < 0 || idx >= n) return;
   for(int i = idx; i < n - 1; i++){
      g_ledgerEmitted[i]   = g_ledgerEmitted[i + 1];
      g_ledgerEmittedAt[i] = g_ledgerEmittedAt[i + 1];
   }
   ArrayResize(g_ledgerEmitted,   n - 1);
   ArrayResize(g_ledgerEmittedAt, n - 1);
}

//: AUD0-LEDGER-001 — potatura per ETA' prima che per numero.
int _nxs_ledger_pruneEmittedByAge(){
   datetime cutoff = TimeCurrent() - (long)NXS_LEDGER_EMITTED_KEEP_DAYS * 86400;
   int dropped = 0;
   for(int i = ArraySize(g_ledgerEmitted) - 1; i >= 0; i--){
      if(g_ledgerEmittedAt[i] > 0 && g_ledgerEmittedAt[i] < cutoff){
         _nxs_ledger_dropEmittedAt(i);
         dropped++;
      }
   }
   return dropped;
}

void _nxs_ledger_markEmitted(ulong posId){
   if(NXS_Ledger_Emitted(posId)) return;
   int n = ArraySize(g_ledgerEmitted);
   if(n >= NXS_LEDGER_MAX_EMITTED){
      // Prima si liberano le entry OLTRE la finestra di ricostruzione: quelle
      // non possono piu' rientrare in un resync, quindi scartarle non crea
      // doppioni. Solo se non ne esistono si ricade sul trim FIFO cieco.
      if(_nxs_ledger_pruneEmittedByAge() == 0){
         PrintFormat("[NEXUS LEDGER] emitted-set pieno (%d) con tutte le entry "
                     "recenti: si scarta la piu' vecchia (pos %I64u). La "
                     "deduplica di quella chiusura resta al backend.",
                     n, g_ledgerEmitted[0]);
         _nxs_ledger_dropEmittedAt(0);
      }
      n = ArraySize(g_ledgerEmitted);
   }
   ArrayResize(g_ledgerEmitted,   n + 1);
   ArrayResize(g_ledgerEmittedAt, n + 1);
   g_ledgerEmitted[n]   = posId;
   g_ledgerEmittedAt[n] = TimeCurrent();
}

// Persistenza SOLO live: nel tester ogni run parte pulita e non esistono
// restart a meta' run; un file condiviso inquinerebbe i backtest.
//: Checksum semplice ma sufficiente a rilevare troncamenti e byte corrotti.
long _nxs_ledger_checksum(int n){
   long sum = (long)NXS_LEDGER_FILE_MAGIC ^ (long)NXS_LEDGER_FILE_VER ^ (long)n;
   for(int i = 0; i < n; i++){
      sum = (sum * 1000003) ^ (long)g_ledgerEmitted[i];
      sum = (sum * 1000003) ^ (long)g_ledgerEmittedAt[i];
   }
   return sum;
}

// AUD0-LEDGER-002: il ledger scriveva DIRETTAMENTE sul file definitivo. Un
// crash a meta' scrittura lasciava un file troncato — e con esso uno stato
// anti-doppione parziale, senza alcun modo di accorgersene.
//
// Si adotta lo stesso schema gia' usato da NXS_State: scrittura su file
// temporaneo, copia precedente conservata, sostituzione atomica, header con
// magic/versione/conteggio e checksum a chiusura.
void NXS_Ledger_Persist(){
   if(MQLInfoInteger(MQL_TESTER)) return;
   string finalName = _nxs_ledger_emittedFile();
   string tmpName   = finalName + ".tmp";
   string prevName  = finalName + ".prev";

   int n = ArraySize(g_ledgerEmitted);
   if(ArraySize(g_ledgerEmittedAt) != n) ArrayResize(g_ledgerEmittedAt, n);

   int h = FileOpen(tmpName, FILE_WRITE|FILE_BIN);
   if(h == INVALID_HANDLE){
      NXS_Ledger_MarkDegraded(StringFormat("scrittura di %s fallita (err=%d)",
                                           tmpName, GetLastError()));
      return;
   }
   FileWriteInteger(h, NXS_LEDGER_FILE_MAGIC, INT_VALUE);
   FileWriteInteger(h, NXS_LEDGER_FILE_VER,   INT_VALUE);
   FileWriteInteger(h, n, INT_VALUE);
   for(int i = 0; i < n; i++){
      FileWriteLong(h, (long)g_ledgerEmitted[i]);
      FileWriteLong(h, (long)g_ledgerEmittedAt[i]);
   }
   FileWriteLong(h, _nxs_ledger_checksum(n));
   FileFlush(h);
   FileClose(h);

   // La copia precedente resta disponibile finche' la nuova non e' al suo posto.
   if(FileIsExist(finalName)){
      FileDelete(prevName);
      FileMove(finalName, 0, prevName, FILE_REWRITE);
   }
   if(!FileMove(tmpName, 0, finalName, FILE_REWRITE)){
      NXS_Ledger_MarkDegraded(StringFormat("sostituzione atomica fallita (err=%d)",
                                           GetLastError()));
      // Ripristina la copia precedente: meglio lo stato vecchio che nessuno.
      if(FileIsExist(prevName)) FileMove(prevName, 0, finalName, FILE_REWRITE);
   }
}

//: Legge un singolo file dell'emitted-set. false = assente o non integro.
bool _nxs_ledger_readEmittedFile(string name, string &why){
   why = "";
   if(!FileIsExist(name)){ why = "assente"; return false; }
   int h = FileOpen(name, FILE_READ|FILE_BIN);
   if(h == INVALID_HANDLE){
      why = StringFormat("apertura fallita (err=%d)", GetLastError());
      return false;
   }
   int magic = FileReadInteger(h, INT_VALUE);
   int ver   = FileReadInteger(h, INT_VALUE);
   int n     = FileReadInteger(h, INT_VALUE);
   if(magic != NXS_LEDGER_FILE_MAGIC || ver != NXS_LEDGER_FILE_VER){
      FileClose(h);
      why = StringFormat("header non riconosciuto (magic=%d ver=%d)", magic, ver);
      return false;
   }
   if(n < 0 || n > NXS_LEDGER_MAX_EMITTED){
      FileClose(h);
      why = StringFormat("conteggio fuori scala (%d)", n);
      return false;
   }
   ArrayResize(g_ledgerEmitted,   n);
   ArrayResize(g_ledgerEmittedAt, n);
   for(int i = 0; i < n; i++){
      g_ledgerEmitted[i]   = (ulong)FileReadLong(h);
      g_ledgerEmittedAt[i] = (datetime)FileReadLong(h);
   }
   long stored = FileReadLong(h);
   FileClose(h);

   long expect = _nxs_ledger_checksum(n);
   if(stored != expect){
      ArrayResize(g_ledgerEmitted, 0);
      ArrayResize(g_ledgerEmittedAt, 0);
      why = "checksum non corrispondente (file troncato o corrotto)";
      return false;
   }
   return true;
}

void _nxs_ledger_loadEmitted(){
   if(MQLInfoInteger(MQL_TESTER)) return;
   string finalName = _nxs_ledger_emittedFile();
   string why = "";

   if(_nxs_ledger_readEmittedFile(finalName, why)){
      _nxs_ledger_pruneEmittedByAge();
      return;
   }

   // AUD0-LEDGER-003: qui si usciva in silenzio. Ora si tenta la copia
   // precedente e, se anche quella non regge, lo stato viene dichiarato
   // degradato invece di fingere un insieme vuoto.
   string prevName = finalName + ".prev";
   string why2 = "";
   if(_nxs_ledger_readEmittedFile(prevName, why2)){
      _nxs_ledger_pruneEmittedByAge();
      NXS_Ledger_MarkDegraded(StringFormat(
         "file corrente non integro (%s): ripristinata la copia precedente, "
         "le chiusure fra le due potrebbero essere rinviate", why));
      return;
   }

   if(why != "assente" || why2 != "assente")
      NXS_Ledger_MarkDegraded(StringFormat("nessuna copia integra (corrente: %s; "
                                           "precedente: %s)", why, why2));
}

// AUD0-LEDGER-008 — la chiave del ledger e' DEAL_POSITION_ID, ma il codice
// chiedeva al terminale PositionSelectByTicket(position_id). Ticket della
// position e POSITION_IDENTIFIER coincidono solo finche' la position non viene
// modificata in modi che le assegnano un nuovo ticket (parziali su alcuni
// broker, migrazioni di server). Quando divergono, la position risulta
// "sparita" mentre e' ancora aperta: il ledger dichiara chiuso un trade vivo.
//
// Qui la ricerca avviene sull'IDENTIFIER, che e' il campo davvero confrontabile
// con DEAL_POSITION_ID; il ticket resta come scorciatoia iniziale.
bool NXS_Ledger_PositionAlive(ulong posId){
   if(posId == 0) return false;
   if(PositionSelectByTicket(posId) &&
      (ulong)PositionGetInteger(POSITION_IDENTIFIER) == posId) return true;
   for(int i = PositionsTotal() - 1; i >= 0; i--){
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if((ulong)PositionGetInteger(POSITION_IDENTIFIER) == posId) return true;
   }
   return false;
}

int _nxs_ledger_stateIdx(ulong posId){
   for(int i = ArraySize(g_ledgerState) - 1; i >= 0; i--)
      if(g_ledgerState[i].position_id == posId) return i;
   return -1;
}

// AUD0-LEDGER-010 — identificativo della SEQUENZA logica.
//
// Grid, piramidazioni e recovery istituzionali producono position separate che
// il ledger contava come trade indipendenti: drawdown, rischio e P/L della
// campagna risultavano frammentati fra righe scollegate.
//
// La fonte autorevole e' il registro degli intenti, che lega ogni gamba alla
// sequenza decisa all'esecuzione. Se l'intento non c'e' (posizioni aperte
// prima di questa versione, o registro potato) si ripiega sulla position
// stessa: comportamento identico al precedente, ma dichiarato.
ulong NXS_Ledger_GroupId(long magic, string sym, ulong posId){
   ulong g = NXS_Intent_GroupOf(posId);
   return (g != 0) ? g : posId;
}

// --------------------------------------------------- aggregazione pura -----
// Ricostruisce lo snapshot aggregato del trade logico dai deal in history.
// Funzione PURA rispetto allo stato del ledger: usata sia dal diff sia da
// NXS_HistorySync per il resync a livello di trade logico.
//
// AUD0-LEDGER-009 — la selezione history di MT5 e' stato GLOBALE condiviso.
// HistorySelectByPosition la sostituisce, quindi un chiamante che stava
// iterando la propria finestra si ritrovava, dopo questa chiamata, a scorrere
// i deal di UN'ALTRA position senza accorgersene. La convenzione era scritta
// solo in un commento: chi la dimenticava produceva dati sbagliati in silenzio.
//
// Il contratto e' ora esplicito e verificabile: si usa
// NXS_Ledger_AggregateAndRestore() quando esiste una finestra da preservare —
// ripristina la selezione precedente prima di restituire il controllo.
bool NXS_Ledger_AggregatePosition(ulong posId, SNxsLedgerTrade &t){
   t.position_id = posId; t.symbol = ""; t.magic = 0; t.strategy = "";
   t.score = 0; t.side = ""; t.vol_in = 0; t.vol_out = 0; t.vwap_in = 0;
   t.vwap_out = 0; t.pnl = 0; t.risk_money = 0; t.risk_known = false;
   t.risk_partial = false; t.risk_from_intent = false;
   t.identity_from_comment = false; t.group_id = 0; t.open_time = 0;
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
         // AUD0-LEDGER-006 / NXS-TX-002 — identita' dal registro degli
         // INTENTI, non dal commento. Il commento e' testo che il broker puo'
         // troncare o riscrivere: non e' un identificatore. Si consulta prima
         // l'intento registrato all'invio (chiave: DEAL_ORDER) e solo in sua
         // assenza si ricade sul vecchio parsing, dichiarandolo.
         ulong ordTicket = (ulong)HistoryDealGetInteger(d, DEAL_ORDER);
         SNxsIntent intent;
         bool haveIntent = (ordTicket != 0 && NXS_Intent_ByOrder(ordTicket, intent));
         if(haveIntent){
            NXS_Intent_BindPosition(ordTicket, posId);
            if(t.strategy == ""){
               t.strategy = intent.strategy;
               t.score    = intent.score;
            }
            if(intent.risk_money > 0.0){
               // Rischio DECISO dal sizer per questa gamba: preciso per
               // costruzione, mentre quello dedotto dallo stop del deal e'
               // solo una ricostruzione.
               t.risk_money += intent.risk_money;
               t.risk_known  = true;
               t.risk_from_intent = true;
            }
         }
         if(t.strategy == ""){
            // Ripiego storico: commento "<comment>|<strat>|<score>".
            string cm = HistoryDealGetString(d, DEAL_COMMENT);
            int p1 = StringFind(cm, "|");
            if(p1 >= 0){
               int p2 = StringFind(cm, "|", p1 + 1);
               if(p2 > p1){
                  t.strategy = StringSubstr(cm, p1 + 1, p2 - p1 - 1);
                  t.score    = StringToDouble(StringSubstr(cm, p2 + 1));
               } else t.strategy = StringSubstr(cm, p1 + 1);
            }
            t.identity_from_comment = (t.strategy != "");
         }
         // AUD0-LEDGER-004: il rischio veniva preso UNA volta sola, dal primo
         // deal IN con SL visibile. Scale-in, gambe di grid/recovery e
         // piramidazioni aggiungevano volume senza aggiungere rischio al
         // denominatore: la R risultante sottostimava sistematicamente
         // l'esposizione reale del trade logico.
         //
         // Ora il rischio si SOMMA su ogni deal IN che porta un proprio stop.
         // Se anche un solo IN entra senza stop visibile, il rischio del trade
         // non e' piu' ricostruibile e viene marcato come ignoto: meglio
         // "non calcolabile" che un numero plausibile e falso.
         if(!haveIntent || intent.risk_money <= 0.0){
            double slP = HistoryDealGetDouble(d, DEAL_SL);
            if(price > 0 && slP > 0){
               double tickV  = SymbolInfoDouble(t.symbol, SYMBOL_TRADE_TICK_VALUE);
               double tickSz = SymbolInfoDouble(t.symbol, SYMBOL_TRADE_TICK_SIZE);
               if(tickSz > 0){
                  t.risk_money += (MathAbs(price - slP) / tickSz) * tickV * v;
                  t.risk_known  = true;
               } else {
                  t.risk_partial = true;
               }
            } else {
               t.risk_partial = true;   // ingresso senza stop noto in questo deal
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

   // AUD0-LEDGER-004: il rischio e' noto solo se OGNI ingresso ha contribuito.
   // Un solo scale-in senza stop rende l'aggregato non rappresentativo.
   if(t.risk_money <= 0.0) t.risk_known = false;
   else if(t.risk_partial && !t.risk_from_intent) t.risk_known = false;

   // AUD0-LEDGER-010: identificativo di SEQUENZA. Grid, piramidazioni e
   // recovery istituzionali producono position separate che il ledger
   // trattava come trade logici scollegati: drawdown, rischio e P/L della
   // sequenza risultavano frammentati. Il group_id lega le gambe alla stessa
   // campagna, cosi' il backend puo' ricomporle senza indovinare.
   t.group_id = NXS_Ledger_GroupId(t.magic, t.symbol, posId);

   return (t.vol_in > 0 || t.vol_out > 0);
}

//: AUD0-LEDGER-009 — aggrega e RIPRISTINA la finestra history del chiamante.
//: Da usare da ogni scansione che itera una propria HistorySelect(from,to).
bool NXS_Ledger_AggregateAndRestore(ulong posId, SNxsLedgerTrade &t,
                                    datetime from, datetime to){
   bool ok = NXS_Ledger_AggregatePosition(posId, t);
   // Il ripristino avviene SEMPRE, anche quando l'aggregazione fallisce:
   // altrimenti l'errore lascerebbe il chiamante su una selezione altrui.
   if(!HistorySelect(from, to))
      PrintFormat("[NEXUS LEDGER] ripristino della finestra history fallito "
                  "(%s..%s): il chiamante deve ri-selezionare",
                  TimeToString(from), TimeToString(to));
   return ok;
}

// Il trade logico e' chiuso quando tutto il volume e' uscito E la position
// non esiste piu' (doppio controllo: il solo volume soffre di arrotondamenti,
// la sola sparizione della position soffre di race col terminale).
bool NXS_Ledger_IsClosed(const SNxsLedgerTrade &t){
   // AUD0-LEDGER-008: confronto sull'IDENTIFIER, non sul ticket.
   if(t.vol_in <= 0) return (t.vol_out > 0 && !NXS_Ledger_PositionAlive(t.position_id));
   bool volDone = (t.vol_out >= t.vol_in - _nxs_ledger_volEps(t.symbol));
   return volDone && !NXS_Ledger_PositionAlive(t.position_id);
}

// AUD0-LEDGER-005 — la R non si inventa.
//
// Il fallback precedente mappava qualunque esito positivo su +1R e qualunque
// negativo su -1R quando il rischio non era ricostruibile. Una perdita da 5R e
// una da 0.2R finivano entrambe a -1R: ogni statistica costruita sopra (win
// rate in R, expectancy, Sharpe per trade, ranking delle strategie) misurava
// un sistema che non esiste.
//
// Ora l'assenza di rischio noto e' un ESITO: NXS_Ledger_HasR() e' false e il
// trade va escluso dalle analisi in R, non convertito in un numero comodo.
bool NXS_Ledger_HasR(const SNxsLedgerTrade &t){
   return (t.risk_known && t.risk_money > 0.0);
}

double NXS_Ledger_RMultiple(const SNxsLedgerTrade &t){
   if(NXS_Ledger_HasR(t)) return t.pnl / t.risk_money;
   return EMPTY_VALUE;   // R sconosciuta: il chiamante DEVE controllare HasR()
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
   // F1: snapshot dei candidati PRIMA di toccare — Touch puo' innescare
   // _nxs_ledger_pruneStates, che ridimensiona/riordina g_ledgerState:
   // mai iterare l'array mentre Touch puo' potarlo.
   ulong pending[];
   for(int i = ArraySize(g_ledgerState) - 1; i >= 0; i--){
      if(g_ledgerState[i].emitted) continue;
      if(NXS_Ledger_PositionAlive(g_ledgerState[i].position_id)) continue;
      int n = ArraySize(pending);
      ArrayResize(pending, n + 1);
      pending[n] = g_ledgerState[i].position_id;
   }
   int finals = 0;
   for(int i = 0; i < ArraySize(pending); i++){
      double dummy;
      if(NXS_Ledger_Touch(pending[i], dummy) == NXS_LEDGER_EV_FINAL)
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

// ---------------------------------------------------------------- selftest --
// Test deterministico dei percorsi F1/F2 (capacita' emitted, prune, snapshot
// di SweepPending, coda FIFO). DISTRUTTIVO sullo stato in-memory del ledger:
// chiamarlo SOLO prima che il trading inizi (OnInit di un run di verifica o
// uno script dedicato). Non tocca file ne' history reale. true = tutti PASS.
bool NXS_Ledger_SelfTest(){
   bool ok = true;
   ArrayFree(g_ledgerState); ArrayFree(g_ledgerEmitted); ArrayFree(g_ledgerClosedQ);

   // --- F2: emitted FIFO oltre capacita' (9000 > 8192) ---
   int total = NXS_LEDGER_MAX_EMITTED + 808;
   for(int i = 1; i <= total; i++) _nxs_ledger_markEmitted((ulong)i);
   int n = ArraySize(g_ledgerEmitted);
   bool sizeOk = (n == NXS_LEDGER_MAX_EMITTED);
   bool fifoOk = (n > 0 &&
                  g_ledgerEmitted[0]   == (ulong)(total - NXS_LEDGER_MAX_EMITTED + 1) &&
                  g_ledgerEmitted[n-1] == (ulong)total);
   bool monoOk = true;   // strettamente crescente = ordine FIFO + zero duplicati
   for(int i = 1; i < n; i++)
      if(g_ledgerEmitted[i] <= g_ledgerEmitted[i-1]){ monoOk = false; break; }
   if(!sizeOk || !fifoOk || !monoOk){
      ok = false;
      PrintFormat("[LEDGER TEST] FAIL emitted FIFO: size=%d (atteso %d) fifo=%d mono=%d",
                  n, NXS_LEDGER_MAX_EMITTED, fifoOk, monoOk);
   } else Print("[LEDGER TEST] PASS emitted FIFO (capacita', piu' vecchio eliminato, no dup)");

   // --- F1a: prune con 2000 stati misti - nessun non-emesso si perde mai ---
   ArrayFree(g_ledgerState);
   ArrayResize(g_ledgerState, 2000);
   int expectKeep = 0;
   for(int i = 0; i < 2000; i++){
      g_ledgerState[i].position_id = (ulong)(100000 + i);
      g_ledgerState[i].deal_count = 1;  g_ledgerState[i].vol_in = 0.1;
      g_ledgerState[i].vol_out = 0.0;   g_ledgerState[i].pnl = 0.0;
      g_ledgerState[i].emitted = (i % 3 != 0);   // 1/3 non emessi
      if(!g_ledgerState[i].emitted) expectKeep++;
   }
   _nxs_ledger_pruneStates();
   int survivors = 0; bool dupOk = true;
   int m = ArraySize(g_ledgerState);
   for(int i = 0; i < m; i++){
      if(!g_ledgerState[i].emitted) survivors++;
      for(int j = i + 1; j < m; j++)
         if(g_ledgerState[j].position_id == g_ledgerState[i].position_id){ dupOk = false; break; }
      if(!dupOk) break;
   }
   if(survivors != expectKeep || !dupOk){
      ok = false;
      PrintFormat("[LEDGER TEST] FAIL prune: non-emessi %d/%d dup_ok=%d", survivors, expectKeep, dupOk);
   } else Print("[LEDGER TEST] PASS prune (2000 stati: non-emessi tutti conservati, no dup)");

   // --- F1b: SweepPending con 1500 stati non emessi e position inesistenti:
   //     lo snapshot deve reggere anche quando Touch/prune possono mutare ---
   ArrayFree(g_ledgerState);
   ArrayResize(g_ledgerState, 1500);
   for(int i = 0; i < 1500; i++){
      g_ledgerState[i].position_id = (ulong)(900000 + i);
      g_ledgerState[i].deal_count = 0; g_ledgerState[i].vol_in = 0;
      g_ledgerState[i].vol_out = 0;    g_ledgerState[i].pnl = 0;
      g_ledgerState[i].emitted = false;
   }
   int finals = NXS_Ledger_SweepPending();   // history vuota: attesi 0 FINAL
   if(finals != 0 || ArraySize(g_ledgerState) != 1500){
      ok = false;
      PrintFormat("[LEDGER TEST] FAIL sweep snapshot: finals=%d size=%d", finals, ArraySize(g_ledgerState));
   } else Print("[LEDGER TEST] PASS sweep snapshot (1500 stati, iterazione sicura, zero mutazioni spurie)");

   // --- coda chiusure: ordine FIFO e nessuna perdita dell'ultimo FINAL ---
   ArrayFree(g_ledgerClosedQ);
   ArrayResize(g_ledgerClosedQ, 3);
   for(int i = 0; i < 3; i++) g_ledgerClosedQ[i].position_id = (ulong)(i + 1);
   SNxsLedgerTrade tq;
   ulong seen[];
   while(NXS_Ledger_PopClosed(tq)){
      int k = ArraySize(seen);
      ArrayResize(seen, k + 1);
      seen[k] = tq.position_id;
   }
   bool qOk = (ArraySize(seen) == 3 && seen[0] == 1 && seen[1] == 2 && seen[2] == 3);
   if(!qOk){ ok = false; Print("[LEDGER TEST] FAIL coda FIFO chiusure"); }
   else Print("[LEDGER TEST] PASS coda FIFO chiusure (ordine, ultimo FINAL mai perso)");

   ArrayFree(g_ledgerState); ArrayFree(g_ledgerEmitted); ArrayFree(g_ledgerClosedQ);
   Print(ok ? "[LEDGER TEST] TUTTI I TEST PASS" : "[LEDGER TEST] FALLIMENTI PRESENTI");
   return ok;
}

#endif
