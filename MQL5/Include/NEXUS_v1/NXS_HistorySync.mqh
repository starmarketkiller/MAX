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

   // PR1: si sincronizzano TRADE LOGICI, non deal OUT. Prima ogni deal OUT
   // diventava un record col medesimo ticket(=posId): per un trade chiuso in
   // parziali il backend riceveva N record che si sovrascrivevano a vicenda
   // (e vinceva il piu' VECCHIO, iterando dal fondo). Ora: 1 position chiusa
   // = 1 record aggregato (PnL totale, VWAP, partial_count), idempotente.
   ulong posIds[];
   int scanned = 0;
   for(int i = total - 1; i >= 0 && scanned < 400; i--){
      ulong dealTicket = HistoryDealGetTicket(i);
      if(dealTicket == 0) continue;
      scanned++;
      if(!IsNexusMagic(HistoryDealGetInteger(dealTicket, DEAL_MAGIC))) continue;
      ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(dealTicket, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY) continue;
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

   long account = (long)AccountInfoInteger(ACCOUNT_LOGIN);
   string body = "{\"trades\":[";
   bool first = true;
   int count = 0;
   for(int i = 0; i < ArraySize(posIds) && count < 50; i++){
      SNxsLedgerTrade t;
      // NB: AggregatePosition usa HistorySelectByPosition e cambia la
      // selezione history globale — per questo gli id sono raccolti prima.
      if(!NXS_Ledger_AggregatePosition(posIds[i], t)) continue;
      if(!NXS_Ledger_IsClosed(t)) continue;        // solo trade logici finiti
      if(t.vol_in <= 0) continue;                  // IN fuori finestra: skip
      string strat = (t.strategy == "") ? "UNKNOWN" : t.strategy;

      if(!first) body += ",";
      first = false;
      body += StringFormat(
         "{\"ticket\":%I64u,\"symbol\":\"%s\",\"side\":\"%s\",\"lots\":%.2f,"
         "\"openPrice\":%.5f,\"closePrice\":%.5f,\"pnl\":%.2f,\"magic\":%I64d,"
         "\"strategy\":\"%s\",\"openTime\":\"%s\",\"closeTime\":\"%s\",\"reason\":\"%s\","
         "\"event\":\"resync\",\"positionId\":%I64u,\"tradeUid\":\"%I64d:%I64u\","
         "\"partialCount\":%d,\"volumeOut\":%.2f}",
         t.position_id, t.symbol, t.side, t.vol_in, t.vwap_in, t.vwap_out,
         t.pnl, t.magic, strat,
         NXS_IsoTime(t.open_time), NXS_IsoTime(t.close_time), t.close_reason,
         t.position_id, account, t.position_id, t.partial_count, t.vol_out);
      count++;
   }
   body += "]}";

   if(count == 0){ Print("[NEXUS SYNC] no NEXUS closed deals in last 7d"); return; }

   string url = InpWebURL + "/api/ea/trade_history_sync";
   char post[]; StringToCharArray(body, post, 0, -1, CP_UTF8);
   ArrayResize(post, ArraySize(post) - 1);
   char result[]; string headersOut;
   string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";
   int code = WebRequest("POST", url, headers, 20000, post, result, headersOut);
   if(code == 200){
      string resp = CharArrayToString(result, 0, -1, CP_UTF8);
      PrintFormat("[NEXUS SYNC] pushed %d trade(s) | resp=%s", count, StringSubstr(resp, 0, 120));
   } else {
      PrintFormat("[NEXUS SYNC] FAILED code=%d", code);
   }
}

#endif
