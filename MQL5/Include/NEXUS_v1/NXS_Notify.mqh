//+------------------------------------------------------------------+
//|  NXS_Notify.mqh - Multi-channel notifications                     |
//|  - MT5 push to mobile (free)                                       |
//|  - Email (via MT5 SMTP settings)                                  |
//|  - Telegram (via backend /api/notify/telegram)                    |
//+------------------------------------------------------------------+
#ifndef __NXS_NOTIFY_MQH__
#define __NXS_NOTIFY_MQH__

void _NXS_NotifyTelegram(string msg){
   if(!InpNotifyTelegram) return;
   if(!InpEnableWebSync) return;
   string body = "{\"message\":\"" + msg + "\",\"chat\":\"" + InpTelegramChatId + "\"}";
   string url = InpWebURL + "/api/notify/telegram";
   char post[]; StringToCharArray(body, post, 0, -1, CP_UTF8);
   ArrayResize(post, ArraySize(post) - 1);
   char result[]; string headersOut;
   string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";
   WebRequest("POST", url, headers, 3000, post, result, headersOut);
}

void NXS_Notify(string title, string body){
   string full = StringFormat("[NEXUS %s] %s", title, body);
   if(InpNotifyPush)     SendNotification(full);
   if(InpNotifyEmail)    SendMail(full, body);
   if(InpNotifyTelegram) _NXS_NotifyTelegram(full);
   PrintFormat("[NEXUS NOTIFY] %s", full);
}

void NXS_Notify_TradeOpen(string strat, string side, double lots, double price, double score){
   if(!InpNotifyOnOpen) return;
   string m = StringFormat("OPEN %s %s lots=%.2f @%.5f score=%.1f", side, strat, lots, price, score);
   NXS_Notify("TRADE", m);
}

void NXS_Notify_TradeClose(string strat, double pnl, string reason){
   if(!InpNotifyOnClose) return;
   string m = StringFormat("CLOSE %s pnl=%.2f reason=%s", strat, pnl, reason);
   NXS_Notify("TRADE", m);
}

void NXS_Notify_Protection(string protName, string detail){
   if(!InpNotifyOnProtection) return;
   string m = StringFormat("%s: %s", protName, detail);
   NXS_Notify("PROT", m);
}

void NXS_Notify_DailySummary(){
   if(!InpNotifyDailySummary) return;
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double dailyPnL = (g_balanceDayStart > 0) ? (bal - g_balanceDayStart) : 0;
   string m = StringFormat("Daily summary | bal=%.2f pnl=%.2f trades=%d consec_loss=%d",
                           bal, dailyPnL, g_tradesToday, g_consecLosses);
   NXS_Notify("DAILY", m);
}

#endif
