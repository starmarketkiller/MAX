//+------------------------------------------------------------------+
//|  NXS_HistorySync.mqh - riconciliazione dei trade chiusi           |
//|                                                                   |
//|  Recupera le chiusure avvenute mentre MT5/EA era offline e le     |
//|  consegna al backend come TRADE LOGICI (non deal).                |
//|                                                                   |
//|  Correzioni dell'audit implementate qui:                          |
//|   AUD0-HSYNC-002  paginazione deterministica con cursore, invece  |
//|                   di 50 trade e poi silenzio;                     |
//|   AUD0-HSYNC-004  nessuna chiamata bloccante da 20s: timeout      |
//|                   breve, un lotto per chiamata, fallimenti in     |
//|                   outbox;                                         |
//|   AUD0-HSYNC-005  i trade con IN non ricostruibile non sono piu'  |
//|                   scartati in silenzio;                           |
//|   AUD0-HSYNC-006  il payload porta la sequenza logica e la        |
//|                   provenienza dell'identita';                     |
//|   AUD0-HSYNC-007  l'esito e' validato semanticamente: il cursore  |
//|                   avanza solo su conferma esplicita del backend.  |
//+------------------------------------------------------------------+
#ifndef __NXS_HISTORY_SYNC_MQH__
#define __NXS_HISTORY_SYNC_MQH__

#define NXS_HSYNC_BATCH        50     // trade per lotto
#define NXS_HSYNC_TIMEOUT_MS 5000     // AUD0-HSYNC-004: mai 20s sul thread EA
#define NXS_HSYNC_LOOKBACK_D   30     // finestra di recupero iniziale (giorni)
#define NXS_HSYNC_MAX_SCAN   2000     // tetto di deal esaminati per chiamata

string _NXS_HistTrigger(long reason){
   // DEAL_REASON_*: 0=client 1=mobile 2=web 3=expert 4=sl 5=tp 6=so 7=rollover ...
   switch((int)reason){
      case 4: return "sl";
      case 5: return "tp";
      case 6: return "stop_out";
      case 3: return "expert";
      default: return "unknown";
   }
}

// AUD0-HSYNC-002 / AUD0-HSYNC-005 — CURSORE PERSISTENTE.
//
// Prima la funzione guardava sempre gli ultimi 7 giorni e si fermava a 50
// trade, senza continuazione: dal 51esimo in poi i trade non venivano mai
// consegnati e nessuno se ne accorgeva. Il cursore rende la ripresa
// deterministica: si riparte da dove il backend ha confermato, non da una
// finestra fissa.
datetime g_hsyncCursor       = 0;     // ultima chiusura CONFERMATA dal backend
bool     g_hsyncCursorLoaded = false;
bool     g_hsyncMore         = false; // true = restano trade da consegnare

string _nxs_hsync_cursorFile(){
   return StringFormat("NEXUS_v1_hsync_cursor_%I64d_%I64d.bin",
                       (long)AccountInfoInteger(ACCOUNT_LOGIN), (long)InpMagic);
}

void _nxs_hsync_loadCursor(){
   if(g_hsyncCursorLoaded) return;
   g_hsyncCursorLoaded = true;
   if(MQLInfoInteger(MQL_TESTER)) return;
   if(!FileIsExist(_nxs_hsync_cursorFile())) return;
   int h = FileOpen(_nxs_hsync_cursorFile(), FILE_READ|FILE_BIN);
   if(h == INVALID_HANDLE) return;
   g_hsyncCursor = (datetime)FileReadLong(h);
   FileClose(h);
}

void _nxs_hsync_saveCursor(datetime v){
   g_hsyncCursor = v;
   if(MQLInfoInteger(MQL_TESTER)) return;
   int h = FileOpen(_nxs_hsync_cursorFile(), FILE_WRITE|FILE_BIN);
   if(h == INVALID_HANDLE) return;
   FileWriteLong(h, (long)v);
   FileFlush(h);
   FileClose(h);
}

bool NXS_HSync_HasMore(){ return g_hsyncMore; }

//: AUD0-HSYNC-007 — validazione SEMANTICA della risposta.
//: Un 200 non e' una conferma: il backend risponde {"ok":true,"stored":N}.
//: Il cursore avanza solo se la risposta dichiara di aver memorizzato tutto
//: il lotto; qualunque altra cosa lo lascia fermo e fa ritentare.
bool _nxs_hsync_ackOk(string resp, int sent, int &storedOut){
   storedOut = -1;
   if(StringFind(resp, "\"ok\":true") < 0 && StringFind(resp, "\"ok\": true") < 0)
      return false;
   int p = StringFind(resp, "\"stored\"");
   if(p < 0) return false;
   int c = StringFind(resp, ":", p);
   if(c < 0) return false;
   storedOut = (int)StringToInteger(StringSubstr(resp, c + 1, 12));
   return (storedOut >= sent);
}

// Consegna UN lotto di trade logici chiusi. Da chiamare ripetutamente: finche'
// NXS_HSync_HasMore() e' true restano trade da consegnare.
void NXS_SyncRecentClosedTrades(){
   if(!InpEnableWebSync) return;
   _nxs_hsync_loadCursor();
   g_hsyncMore = false;

   datetime now  = TimeCurrent();
   datetime from = (g_hsyncCursor > 0)
                   ? (datetime)((long)g_hsyncCursor - 3600)   // sovrapposizione di sicurezza
                   : (datetime)((long)now - (long)NXS_HSYNC_LOOKBACK_D * 86400);
   if(!HistorySelect(from, now)) return;

   int total = HistoryDealsTotal();
   if(total <= 0){ Print("[NEXUS SYNC] nessun deal nella finestra da riconciliare"); return; }

   // Raccolta degli id di position PRIMA di toccare la selezione globale
   // (l'aggregatore usa HistorySelectByPosition — cfr. AUD0-LEDGER-009).
   ulong posIds[];
   int scanned = 0;
   for(int i = 0; i < total && scanned < NXS_HSYNC_MAX_SCAN; i++){
      ulong dealTicket = HistoryDealGetTicket(i);
      if(dealTicket == 0) continue;
      scanned++;
      if(!IsNexusMagic(HistoryDealGetInteger(dealTicket, DEAL_MAGIC))) continue;
      ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(dealTicket, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY) continue;
      datetime dtm = (datetime)HistoryDealGetInteger(dealTicket, DEAL_TIME);
      if(g_hsyncCursor > 0 && dtm <= g_hsyncCursor) continue;   // gia' confermato
      ulong posId = (ulong)HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID);
      bool seen = false;
      for(int k = ArraySize(posIds) - 1; k >= 0; k--)
         if(posIds[k] == posId){ seen = true; break; }
      if(!seen){
         int n = ArraySize(posIds);
         ArrayResize(posIds, n + 1);
         posIds[n] = posId;
      }
   }
   if(ArraySize(posIds) == 0){
      Print("[NEXUS SYNC] nessun trade logico da riconciliare oltre il cursore");
      return;
   }

   long account = (long)AccountInfoInteger(ACCOUNT_LOGIN);
   string body = "{\"trades\":[";
   bool first = true;
   int count = 0;
   int skippedIncomplete = 0;
   datetime batchMaxClose = 0;

   for(int i = 0; i < ArraySize(posIds); i++){
      if(count >= NXS_HSYNC_BATCH){
         // AUD0-HSYNC-002: c'e' altro da consegnare. Non si tronca in
         // silenzio: si segnala e il chiamante richiama.
         g_hsyncMore = true;
         break;
      }
      SNxsLedgerTrade t;
      if(!NXS_Ledger_AggregatePosition(posIds[i], t)) continue;
      if(!NXS_Ledger_IsClosed(t)) continue;        // solo trade logici finiti

      if(t.vol_in <= 0){
         // AUD0-HSYNC-005: qui si faceva `continue` muto. HistorySelectByPosition
         // vede l'intera storia della position, quindi un vol_in a zero non e'
         // "ingresso fuori finestra": e' storia realmente incompleta lato
         // broker. Va detto, non nascosto.
         skippedIncomplete++;
         PrintFormat("[NEXUS SYNC] pos %I64u senza deal di ingresso ricostruibili: "
                     "trade NON riconciliato (storia broker incompleta)", posIds[i]);
         continue;
      }

      string strat = (t.strategy == "") ? "UNKNOWN" : t.strategy;
      if(t.close_time > batchMaxClose) batchMaxClose = t.close_time;

      if(!first) body += ",";
      first = false;
      // AUD0-HSYNC-006: oltre a tradeUid il payload porta ora la SEQUENZA
      // logica (grid/piramide/istituzionale appartengono a una campagna) e la
      // provenienza di identita' e rischio, cosi' il backend sa quanto fidarsi
      // di ogni campo invece di trattarli tutti come certi.
      body += StringFormat(
         "{\"ticket\":%I64u,\"symbol\":\"%s\",\"side\":\"%s\",\"lots\":%.2f,"
         "\"openPrice\":%.5f,\"closePrice\":%.5f,\"pnl\":%.2f,\"magic\":%I64d,"
         "\"strategy\":\"%s\",\"openTime\":\"%s\",\"closeTime\":\"%s\",\"reason\":\"%s\","
         "\"event\":\"resync\",\"positionId\":%I64u,\"tradeUid\":\"%I64d:%I64u\","
         "\"sequenceId\":\"%I64d:%I64u\",\"partialCount\":%d,\"volumeOut\":%.2f,"
         "\"riskMoney\":%.2f,\"riskKnown\":%s,\"riskSource\":\"%s\","
         "\"identitySource\":\"%s\",\"ledgerDegraded\":%s}",
         t.position_id, t.symbol, t.side, t.vol_in, t.vwap_in, t.vwap_out,
         t.pnl, t.magic, strat,
         NXS_IsoTime(t.open_time), NXS_IsoTime(t.close_time), t.close_reason,
         t.position_id, account, t.position_id,
         account, (t.group_id != 0 ? t.group_id : t.position_id),
         t.partial_count, t.vol_out,
         t.risk_money, (t.risk_known ? "true" : "false"),
         (t.risk_from_intent ? "intent" : "deal_sl"),
         (t.identity_from_comment ? "comment" : "intent"),
         (NXS_Ledger_IsDegraded() ? "true" : "false"));
      count++;
   }
   body += "]}";

   if(count == 0){
      if(skippedIncomplete > 0)
         PrintFormat("[NEXUS SYNC] %d trade non riconciliabili, nessun invio",
                     skippedIncomplete);
      return;
   }

   string url = InpWebURL + "/api/ea/trade_history_sync";
   char post[]; StringToCharArray(body, post, 0, -1, CP_UTF8);
   ArrayResize(post, ArraySize(post) - 1);
   char result[]; string headersOut;
   string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";

   // AUD0-HSYNC-004: qui il timeout era di 20 SECONDI, sul thread dell'EA, sia
   // in OnInit sia dal timer. In quella finestra non giravano il Virtual SL, le
   // protezioni ne' OnTradeTransaction. Ora e' breve e i fallimenti finiscono
   // nell'outbox, che li drena senza bloccare nulla.
   int code = WebRequest("POST", url, headers, NXS_HSYNC_TIMEOUT_MS, post, result, headersOut);
   if(code != 200){
      PrintFormat("[NEXUS SYNC] consegna fallita (code=%d, %d trade): accodata nell'outbox",
                  code, count);
      NXS_Outbox_Push(url, body);
      return;
   }

   string resp = CharArrayToString(result, 0, -1, CP_UTF8);
   int stored = -1;
   if(!_nxs_hsync_ackOk(resp, count, stored)){
      // AUD0-HSYNC-007: un 200 senza conferma semantica NON fa avanzare il
      // cursore. Prima qualunque 200 veniva loggato come successo, anche se il
      // backend aveva scartato l'intero lotto.
      PrintFormat("[NEXUS SYNC] risposta 200 NON confermata (inviati=%d memorizzati=%d): "
                  "cursore fermo, si ritenta | resp=%s",
                  count, stored, StringSubstr(resp, 0, 160));
      g_hsyncMore = true;
      return;
   }

   if(batchMaxClose > 0) _nxs_hsync_saveCursor(batchMaxClose);
   PrintFormat("[NEXUS SYNC] confermati %d/%d trade | cursore=%s%s",
               stored, count, TimeToString(g_hsyncCursor, TIME_DATE|TIME_MINUTES),
               (g_hsyncMore ? " | altri lotti in attesa" : ""));
}

#endif
