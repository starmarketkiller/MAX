//+------------------------------------------------------------------+
//|  NXS_Protections.mqh - Risk Protections (NEXUS v2.0 spec)         |
//|  ESL · DPT · MaxHoldTime · MaxLossPerPosition · AutoClose         |
//|  + Trade Reason Codes pushed to backend on close.                 |
//+------------------------------------------------------------------+
#ifndef __NXS_PROTECTIONS_MQH__
#define __NXS_PROTECTIONS_MQH__

// ----- State -----
bool     g_eslHit              = false;
bool     g_dptHit              = false;
bool     g_pausedUntilNextOpen = false;
bool     g_autoClosePending    = false;
datetime g_dptResetDay         = 0;

// ----- Reason codes -----
#define NXS_R_TREND   "NXS:TREND"
#define NXS_R_PROFIT  "NXS:PROFIT"
#define NXS_R_DD      "NXS:DD"
#define NXS_R_TIME    "NXS:TIME"
#define NXS_R_NEWS    "NXS:NEWS"
#define NXS_R_BE      "NXS:BE"
#define NXS_R_RISK    "NXS:RISK"

// ----- Push Trade Reason to backend -----
void NXS_Prot_PushTradeReason(ulong ticket, long magic, string strategy,
                              string side, double lots, double openPrice,
                              double closePrice, double pnl, string reason){
   if(!InpEnableWebSync) return;
   string body = "{";
   body += "\"ticket\":"     + IntegerToString((long)ticket) + ",";
   body += "\"magic\":"      + IntegerToString(magic) + ",";
   body += "\"strategy\":\""  + strategy + "\",";
   body += "\"side\":\""     + side + "\",";
   body += "\"lots\":"       + DoubleToString(lots, 2) + ",";
   body += "\"openPrice\":"  + DoubleToString(openPrice, g_digits) + ",";
   body += "\"closePrice\":" + DoubleToString(closePrice, g_digits) + ",";
   body += "\"pnl\":"        + DoubleToString(pnl, 2) + ",";
   body += "\"reason\":\""   + reason + "\"";
   body += "}";

   string url = InpWebURL + "/api/ea/trade_reason";
   char post[]; StringToCharArray(body, post, 0, -1, CP_UTF8);
   ArrayResize(post, ArraySize(post) - 1);
   char result[]; string headersOut;
   string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";
   int code = WebRequest("POST", url, headers, 3000, post, result, headersOut);
   if(code != 200 && InpDebugLog){
      PrintFormat("[NEXUS PROT] PushTradeReason FAILED code=%d ticket=%d reason=%s", code, ticket, reason);
   }
}

// ----- Close one position w/ reason in comment + push to backend -----
bool NXS_Prot_ClosePositionWithReason(ulong ticket, string reason){
   if(!PositionSelectByTicket(ticket)) return false;
   long mg = (long)PositionGetInteger(POSITION_MAGIC);
   if(!IsNexusMagic(mg)) return false;
   string sym = PositionGetString(POSITION_SYMBOL);
   double openP = PositionGetDouble(POSITION_PRICE_OPEN);
   double lots  = PositionGetDouble(POSITION_VOLUME);
   long   ptype = PositionGetInteger(POSITION_TYPE);
   double pnl   = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   string side  = (ptype == POSITION_TYPE_BUY) ? "BUY" : "SELL";
   string strat = PositionGetString(POSITION_COMMENT);

   // Build close request w/ reason in comment so audit is readable in MT5 History
   MqlTradeRequest req;  ZeroMemory(req);
   MqlTradeResult  res;  ZeroMemory(res);
   req.action      = TRADE_ACTION_DEAL;
   req.position    = ticket;
   req.symbol      = sym;
   req.volume      = lots;
   req.deviation   = 30;
   req.magic       = mg;
   req.type_filling= g_tradeFilling;
   req.comment     = reason;
   if(ptype == POSITION_TYPE_BUY){
      req.type  = ORDER_TYPE_SELL;
      req.price = SymbolInfoDouble(sym, SYMBOL_BID);
   } else {
      req.type  = ORDER_TYPE_BUY;
      req.price = SymbolInfoDouble(sym, SYMBOL_ASK);
   }
   bool ok = OrderSend(req, res);
   g_tradeRetcode = res.retcode;
   bool success = ok && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED);
   if(success){
      double closeP = req.price;
      NXS_Prot_PushTradeReason(ticket, mg, strat, side, lots, openP, closeP, pnl, reason);
   }
   return success;
}

// ----- Close ALL positions w/ reason -----
int NXS_Prot_CloseAllWithReason(string reason){
   int closed = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      if(NXS_Prot_ClosePositionWithReason(t, reason)) closed++;
   }
   return closed;
}

// ===================================================================
//   PROTECTION 1: Equity Stop Loss (ESL)
// ===================================================================
void NXS_Prot_CheckESL(){
   if(!InpUseESL || g_eslHit) return;
   double bal   = AccountInfoDouble(ACCOUNT_BALANCE);
   double floatL = NXS_FloatingPnL();
   double limit = InpESL_IsPercent ? -(bal * InpESL_Value / 100.0) : -InpESL_Value;
   if(floatL <= limit){
      int n = NXS_Prot_CloseAllWithReason(NXS_R_DD);
      g_eslHit = true;
      g_pausedUntilNextOpen = true;
      PrintFormat("[NEXUS PROT] ESL HIT: floatPnL=%.2f <= limit=%.2f. Closed %d positions. Paused.",
                  floatL, limit, n);
   }
}

// ===================================================================
//   PROTECTION 2: Daily Profit Target (DPT)
// ===================================================================
void NXS_Prot_CheckDPT(){
   if(!InpUseDPT || g_dptHit) return;
   double bal0 = g_balanceDayStart > 0 ? g_balanceDayStart : AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double profit = equity - bal0;
   double target = InpDPT_IsPercent ? (bal0 * InpDPT_Value / 100.0) : InpDPT_Value;
   if(profit >= target){
      int n = NXS_Prot_CloseAllWithReason(NXS_R_PROFIT);
      g_dptHit = true;
      g_pausedUntilNextOpen = true;
      PrintFormat("[NEXUS PROT] DPT HIT: profit=%.2f >= target=%.2f. Closed %d positions. Paused for day.",
                  profit, target, n);
   }
}

// ===================================================================
//   PROTECTION 3: Max Hold Time per position
// ===================================================================
void NXS_Prot_CheckMaxHold(){
   if(!InpUseMaxHold) return;
   datetime now = TimeCurrent();
   long limit = (long)InpProt_MaxHoldHours * 3600;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
      if(now - opened >= limit){
         NXS_Prot_ClosePositionWithReason(t, NXS_R_TIME);
         PrintFormat("[NEXUS PROT] MaxHold: closed ticket=%d (held %d s)", t, (int)(now - opened));
      }
   }
}

// ===================================================================
//   PROTECTION 4: Max Loss Per Position
// ===================================================================
void NXS_Prot_CheckMaxLossPerPos(){
   if(!InpUseMaxLossPos) return;
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double lim = -(bal * InpMaxLossPosPct / 100.0);
   datetime now = TimeCurrent();
   long minLife = (long)InpProt_MinLifeMin * 60;   // v2.0.14
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      // v2.0.14 — non chiudere prima del tempo minimo di vita (anti stop-out su rumore M5).
      // Nei primi minuti la posizione resta protetta dallo SL hard (>=1.5 ATR).
      datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
      if(now - opened < minLife) continue;
      double pl = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      if(pl <= lim){
         NXS_Prot_ClosePositionWithReason(t, NXS_R_RISK);
         PrintFormat("[NEXUS PROT] MaxLossPos: closed ticket=%d pl=%.2f <= lim=%.2f age=%ds",
                     t, pl, lim, (int)(now - opened));
      }
   }
}

// ===================================================================
//   PROTECTION 5: AutoClose before market close (Friday-aware)
// ===================================================================
void NXS_Prot_CheckAutoClose(){
   if(!InpUseAutoClose) return;
   MqlDateTime dt;  TimeToStruct(TimeGMT(), dt);
   int nowMin   = dt.hour * 60 + dt.min;
   int closeMin = InpMarketCloseGMT * 60;
   if(nowMin >= closeMin - InpAutoCloseMin && nowMin < closeMin){
      if(!g_autoClosePending){
         int n = NXS_Prot_CloseAllWithReason(NXS_R_TIME);
         g_autoClosePending = true;
         g_pausedUntilNextOpen = true;
         PrintFormat("[NEXUS PROT] AutoClose: closed %d positions at GMT %02d:%02d", n, dt.hour, dt.min);
      }
   } else {
      g_autoClosePending = false;
   }
}

// ===================================================================
//   Daily resume hook
// ===================================================================
void NXS_Prot_OnNewDay(){
   g_eslHit = false;
   g_dptHit = false;
   g_pausedUntilNextOpen = false;
   g_autoClosePending = false;
   g_dptResetDay = TimeCurrent();
}

// ===================================================================
//   Master gate
// ===================================================================
bool NXS_Prot_EntryBlocked(){
   return g_pausedUntilNextOpen || g_eslHit || g_dptHit || g_autoClosePending;
}

// ===================================================================
//   Master tick
// ===================================================================
void NXS_Prot_OnTick(){
   if(g_pausedUntilNextOpen) return;
   NXS_Prot_CheckMaxHold();
   NXS_Prot_CheckMaxLossPerPos();
   NXS_Prot_CheckESL();
   NXS_Prot_CheckDPT();
   NXS_Prot_CheckAutoClose();
}

#endif
