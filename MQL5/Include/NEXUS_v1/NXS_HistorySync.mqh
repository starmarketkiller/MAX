//+------------------------------------------------------------------+
//|  NXS_HistorySync.mqh - sync closed trades to backend on boot      |
//|  Catches trades that closed while MT5/EA was offline.             |
//+------------------------------------------------------------------+
#ifndef __NXS_HISTORY_SYNC_MQH__
#define __NXS_HISTORY_SYNC_MQH__

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

void NXS_SyncRecentClosedTrades(){
   if(!InpEnableWebSync) return;
   if(!HistorySelect(TimeCurrent() - 7 * 86400, TimeCurrent())) return;

   int total = HistoryDealsTotal();
   if(total <= 0){ Print("[NEXUS SYNC] no recent deals to sync"); return; }

   // Aggregate deals by position_id  (each closed trade has IN + OUT deal)
   string body = "{\"trades\":[";
   bool first = true;
   int count = 0, scanned = 0;

   for(int i = total - 1; i >= 0 && scanned < 200; i--){
      ulong dealTicket = HistoryDealGetTicket(i);
      if(dealTicket == 0) continue;
      scanned++;
      long magic = HistoryDealGetInteger(dealTicket, DEAL_MAGIC);
      if(!IsNexusMagic(magic)) continue;
      ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(dealTicket, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT) continue;

      ulong posId       = HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID);
      string sym        = HistoryDealGetString (dealTicket, DEAL_SYMBOL);
      ENUM_DEAL_TYPE dt = (ENUM_DEAL_TYPE)HistoryDealGetInteger(dealTicket, DEAL_TYPE);
      string side       = (dt == DEAL_TYPE_SELL) ? "BUY" : "SELL"; // OUT deal is opposite
      double lots       = HistoryDealGetDouble (dealTicket, DEAL_VOLUME);
      double closePrice = HistoryDealGetDouble (dealTicket, DEAL_PRICE);
      double pnl        = HistoryDealGetDouble (dealTicket, DEAL_PROFIT)
                        + HistoryDealGetDouble (dealTicket, DEAL_SWAP)
                        + HistoryDealGetDouble (dealTicket, DEAL_COMMISSION);
      datetime closeTm  = (datetime)HistoryDealGetInteger(dealTicket, DEAL_TIME);
      long reasonCode   = HistoryDealGetInteger(dealTicket, DEAL_REASON);
      string reason     = _NXS_HistTrigger(reasonCode);
      string comment    = HistoryDealGetString(dealTicket, DEAL_COMMENT);

      // Find the OPEN deal for this position
      double openPrice = 0; datetime openTm = 0; string strat = "UNKNOWN";
      for(int j = 0; j < total; j++){
         ulong dt2 = HistoryDealGetTicket(j);
         if(dt2 == 0) continue;
         if((ulong)HistoryDealGetInteger(dt2, DEAL_POSITION_ID) != posId) continue;
         if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(dt2, DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
         openPrice = HistoryDealGetDouble(dt2, DEAL_PRICE);
         openTm    = (datetime)HistoryDealGetInteger(dt2, DEAL_TIME);
         string oc = HistoryDealGetString(dt2, DEAL_COMMENT);
         // Comment format from execution: "<comment>|<strat>|<score>"
         int p1 = StringFind(oc, "|");
         if(p1 >= 0){
            int p2 = StringFind(oc, "|", p1 + 1);
            if(p2 > p1) strat = StringSubstr(oc, p1 + 1, p2 - p1 - 1);
         }
         break;
      }
      if(openPrice == 0) continue;

      if(!first) body += ",";
      first = false;
      body += StringFormat(
         "{\"ticket\":%I64u,\"symbol\":\"%s\",\"side\":\"%s\",\"lots\":%.2f,"
         "\"openPrice\":%.5f,\"closePrice\":%.5f,\"pnl\":%.2f,\"magic\":%I64d,"
         "\"strategy\":\"%s\",\"openTime\":\"%s\",\"closeTime\":\"%s\",\"reason\":\"%s\"}",
         posId, sym, side, lots, openPrice, closePrice, pnl, magic, strat,
         TimeToString(openTm, TIME_DATE|TIME_SECONDS),
         TimeToString(closeTm, TIME_DATE|TIME_SECONDS),
         reason);
      count++;
      if(count >= 50) break;   // cap batch size
   }
   body += "]}";

   if(count == 0){ Print("[NEXUS SYNC] no NEXUS closed deals in last 7d"); return; }

   string url = InpWebURL + "/api/ea/trade_history_sync";
   char post[]; StringToCharArray(body, post, 0, -1, CP_UTF8);
   ArrayResize(post, ArraySize(post) - 1);
   char result[]; string headersOut;
   string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";
   int code = WebRequest("POST", url, headers, 8000, post, result, headersOut);
   if(code == 200){
      string resp = CharArrayToString(result, 0, -1, CP_UTF8);
      PrintFormat("[NEXUS SYNC] pushed %d trade(s) | resp=%s", count, StringSubstr(resp, 0, 120));
   } else {
      PrintFormat("[NEXUS SYNC] FAILED code=%d", code);
   }
}

#endif
