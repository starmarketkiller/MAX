//+------------------------------------------------------------------+
//|  NXS_OpenTelemetry.mqh - conferma delle aperture verso NEXUS      |
//|                                                                    |
//|  NEXUS-OTEL-001. Prima il backend riceveva solo le CHIUSURE: non  |
//|  poteva sapere che un ordine DEMO era stato accettato, eseguito e |
//|  che la posizione esisteva davvero.                               |
//|                                                                    |
//|  Tre eventi, ciascuno con una chiave di idempotenza propria:      |
//|    order_result  ogni OrderSend di apertura (o blocco locale)     |
//|                  chiave ord:<order> | req:<sent_at>:<us>          |
//|    deal_in       ogni deal IN visto dal ledger (OPEN/SCALE_IN)    |
//|                  chiave deal:<deal>                               |
//|    position_snapshot  posizioni vive al boot (riconciliazione     |
//|                  dopo crash o disconnessione)                     |
//|                  chiave snap:<position>:<volume in centesimi>     |
//|                                                                    |
//|  Nessun evento dichiara una posizione aperta prima di MT5: la     |
//|  posizione e' "aperta" solo se esiste un deal IN e il terminale   |
//|  la seleziona con PositionSelectByTicket.                         |
//|                                                                    |
//|  Consegna: solo accodamento nell'outbox durevole (file), drenato  |
//|  dal timer con backoff. Mai WebRequest nel percorso d'ordine, mai |
//|  in Strategy Tester. Questo modulo non invia ordini.              |
//+------------------------------------------------------------------+
#ifndef __NXS_OPEN_TELEMETRY_MQH__
#define __NXS_OPEN_TELEMETRY_MQH__

#define NXS_OTEL_PATH "/api/ea/execution_event"

bool _nxs_otel_enabled(){
   return InpEnableWebSync && !MQLInfoInteger(MQL_TESTER)
          && !MQLInfoInteger(MQL_OPTIMIZATION);
}

string _nxs_otel_num(double v, int digits){ return DoubleToString(v, digits); }

int _nxs_otel_digits(string sym){
   int d = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   return (d > 0) ? d : g_digits;
}

// Campi comuni: chi parla (conto, magic, build) e quando.
string _nxs_otel_head(string kind, string key){
   string b = "{";
   b += "\"schema\":\"nexus-otel-1\",";
   b += "\"kind\":\"" + kind + "\",";
   b += "\"event_key\":\"" + _JsonEsc(key) + "\",";
   b += "\"account_login\":" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + ",";
   b += "\"account_mode\":\"" + NXS_AccountModeName() + "\",";
   b += "\"ea_magic\":" + IntegerToString(InpMagic) + ",";
   b += "\"ea_version\":\"" + (string)NEXUS_VERSION + "\",";
   b += "\"emitted_at\":\"" + NXS_IsoTime(TimeCurrent()) + "\",";
   return b;
}

// Strategia dal commento "prefisso|STRAT|score|..." (fallback dichiarato).
string _nxs_otel_strategyFromComment(string cm){
   int p1 = StringFind(cm, "|");
   if(p1 < 0) return "";
   int p2 = StringFind(cm, "|", p1 + 1);
   return (p2 > p1) ? StringSubstr(cm, p1 + 1, p2 - p1 - 1) : StringSubstr(cm, p1 + 1);
}

void _nxs_otel_enqueue(string body){
   NXS_Outbox_Push(InpWebURL + NXS_OTEL_PATH, body);
}

// ------------------------------------------------------------ order_result --
void _nxs_otel_emitOrderResult(const SNxsOpenRequest &r){
   string key;
   if(r.order > 0) key = "ord:" + IntegerToString((long)r.order);
   else key = StringFormat("req:%I64d:%I64u", (long)r.sent_at, r.sent_us);
   int dg = _nxs_otel_digits(r.symbol);
   string b = _nxs_otel_head("order_result", key);
   b += "\"request_id\":" + IntegerToString((long)r.request_id) + ",";
   b += "\"sent\":" + (r.sent ? "true" : "false") + ",";
   b += "\"blocked_reason\":\"" + _JsonEsc(r.blocked_reason) + "\",";
   b += "\"symbol\":\"" + _JsonEsc(r.symbol) + "\",";
   b += "\"side\":\"" + r.side + "\",";
   b += "\"magic\":" + IntegerToString(r.magic) + ",";
   b += "\"strategy\":\"" + _JsonEsc(_nxs_otel_strategyFromComment(r.comment)) + "\",";
   b += "\"requested_volume\":" + _nxs_otel_num(r.req_volume, 2) + ",";
   b += "\"requested_price\":" + _nxs_otel_num(r.req_price, dg) + ",";
   b += "\"sl\":" + _nxs_otel_num(r.sl, dg) + ",";
   b += "\"tp\":" + _nxs_otel_num(r.tp, dg) + ",";
   b += "\"retcode\":" + IntegerToString((long)r.retcode) + ",";
   b += "\"order\":" + IntegerToString((long)r.order) + ",";
   b += "\"deal\":" + IntegerToString((long)r.deal) + ",";
   b += "\"filled_volume\":" + _nxs_otel_num(r.fill_volume, 2) + ",";
   b += "\"fill_price\":" + _nxs_otel_num(r.fill_price, dg) + ",";
   b += "\"broker_comment\":\"" + _JsonEsc(r.broker_comment) + "\",";
   b += "\"sent_at\":\"" + NXS_IsoTime(r.sent_at) + "\"";
   b += "}";
   _nxs_otel_enqueue(b);
}

//: Svuota le richieste di apertura registrate da NXS_DoBuy/NXS_DoSell.
//: Chiamata dal timer e da OnTradeTransaction (prima del deal).
void NXS_OTel_Flush(){
   SNxsOpenRequest r;
   while(NXS_PopOpenRequest(r)){
      if(_nxs_otel_enabled()) _nxs_otel_emitOrderResult(r);
   }
}

// ----------------------------------------------------------------- deal_in --
// ledgerEv: NXS_LEDGER_EV_OPEN o NXS_LEDGER_EV_SCALE_IN.
void NXS_OTel_OnDealIn(ulong dealTicket, int ledgerEv){
   if(!_nxs_otel_enabled()) return;
   if(ledgerEv != NXS_LEDGER_EV_OPEN && ledgerEv != NXS_LEDGER_EV_SCALE_IN) return;
   if(!HistoryDealSelect(dealTicket)) return;
   long entry = HistoryDealGetInteger(dealTicket, DEAL_ENTRY);
   if(entry != DEAL_ENTRY_IN) return;   // INOUT non esiste su hedging (OnInit lo impone)
   long   magic  = HistoryDealGetInteger(dealTicket, DEAL_MAGIC);
   if(!IsNexusMagic(magic)) return;
   ulong  order  = (ulong)HistoryDealGetInteger(dealTicket, DEAL_ORDER);
   ulong  posId  = (ulong)HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID);
   string sym    = HistoryDealGetString(dealTicket, DEAL_SYMBOL);
   long   dtype  = HistoryDealGetInteger(dealTicket, DEAL_TYPE);
   double vol    = HistoryDealGetDouble(dealTicket, DEAL_VOLUME);
   double px     = HistoryDealGetDouble(dealTicket, DEAL_PRICE);
   long   tmsc   = HistoryDealGetInteger(dealTicket, DEAL_TIME_MSC);
   string cm     = HistoryDealGetString(dealTicket, DEAL_COMMENT);

   string strat = ""; string identity = "comment";
   SNxsIntent it;
   if(NXS_Intent_ByOrder(order, it) || NXS_Intent_ByPosition(posId, it)){
      strat = it.strategy; identity = "intent";
   }
   if(strat == "") strat = _nxs_otel_strategyFromComment(cm);

   // La posizione e' "aperta" solo se il terminale la vede adesso.
   bool   alive  = PositionSelectByTicket(posId);
   double posVol = alive ? PositionGetDouble(POSITION_VOLUME) : 0.0;
   double posSL  = alive ? PositionGetDouble(POSITION_SL) : 0.0;
   double posTP  = alive ? PositionGetDouble(POSITION_TP) : 0.0;
   double posPx  = alive ? PositionGetDouble(POSITION_PRICE_OPEN) : 0.0;

   int dg = _nxs_otel_digits(sym);
   string b = _nxs_otel_head("deal_in", "deal:" + IntegerToString((long)dealTicket));
   b += "\"ledger_event\":\"" + (ledgerEv == NXS_LEDGER_EV_OPEN ? "open" : "scale_in") + "\",";
   b += "\"deal\":" + IntegerToString((long)dealTicket) + ",";
   b += "\"order\":" + IntegerToString((long)order) + ",";
   b += "\"position_id\":" + IntegerToString((long)posId) + ",";
   b += "\"symbol\":\"" + _JsonEsc(sym) + "\",";
   b += "\"side\":\"" + (dtype == DEAL_TYPE_BUY ? "BUY" : "SELL") + "\",";
   b += "\"magic\":" + IntegerToString(magic) + ",";
   b += "\"strategy\":\"" + _JsonEsc(strat) + "\",";
   b += "\"identity_source\":\"" + identity + "\",";
   b += "\"deal_volume\":" + _nxs_otel_num(vol, 2) + ",";
   b += "\"deal_price\":" + _nxs_otel_num(px, dg) + ",";
   b += "\"deal_time_msc\":" + IntegerToString(tmsc) + ",";
   b += "\"position_alive\":" + (alive ? "true" : "false") + ",";
   b += "\"position_volume\":" + _nxs_otel_num(posVol, 2) + ",";
   b += "\"position_price\":" + _nxs_otel_num(posPx, dg) + ",";
   b += "\"sl\":" + _nxs_otel_num(posSL, dg) + ",";
   b += "\"tp\":" + _nxs_otel_num(posTP, dg);
   b += "}";
   _nxs_otel_enqueue(b);
}

// ------------------------------------------------------- position_snapshot --
// Riconciliazione dopo un (ri)avvio: ogni posizione Nexus viva viene
// dichiarata con lo stato che il terminale vede ORA. Un deal_in perso durante
// un crash o una disconnessione viene cosi' coperto dal fatto osservato.
int NXS_OTel_ResyncOpenPositions(string source){
   if(!_nxs_otel_enabled()) return 0;
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!IsNexusMagic(magic)) continue;
      ulong  posId = (ulong)PositionGetInteger(POSITION_IDENTIFIER);
      string sym   = PositionGetString(POSITION_SYMBOL);
      double vol   = PositionGetDouble(POSITION_VOLUME);
      int    dg    = _nxs_otel_digits(sym);
      string strat = "";
      SNxsIntent it;
      if(NXS_Intent_ByPosition(posId, it)) strat = it.strategy;
      if(strat == "") strat = _nxs_otel_strategyFromComment(PositionGetString(POSITION_COMMENT));
      string key = StringFormat("snap:%I64u:%I64d", posId, (long)MathRound(vol * 100.0));
      string b = _nxs_otel_head("position_snapshot", key);
      b += "\"source\":\"" + _JsonEsc(source) + "\",";
      b += "\"position_id\":" + IntegerToString((long)posId) + ",";
      b += "\"symbol\":\"" + _JsonEsc(sym) + "\",";
      b += "\"side\":\"" + (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? "BUY" : "SELL") + "\",";
      b += "\"magic\":" + IntegerToString(magic) + ",";
      b += "\"strategy\":\"" + _JsonEsc(strat) + "\",";
      b += "\"position_alive\":true,";
      b += "\"position_volume\":" + _nxs_otel_num(vol, 2) + ",";
      b += "\"position_price\":" + _nxs_otel_num(PositionGetDouble(POSITION_PRICE_OPEN), dg) + ",";
      b += "\"sl\":" + _nxs_otel_num(PositionGetDouble(POSITION_SL), dg) + ",";
      b += "\"tp\":" + _nxs_otel_num(PositionGetDouble(POSITION_TP), dg) + ",";
      b += "\"position_time_msc\":" + IntegerToString(PositionGetInteger(POSITION_TIME_MSC));
      b += "}";
      _nxs_otel_enqueue(b);
      n++;
   }
   return n;
}

#endif
