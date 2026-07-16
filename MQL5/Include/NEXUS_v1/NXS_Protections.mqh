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

// v2.0.33 — post-stop-loss directional cooldown. Found via live trade
// review: a position gets stopped out, and within seconds a NEW position
// opens in the OPPOSITE direction at nearly the same price (chasing the
// reversal), which itself then gets stopped out too - a whipsaw pattern
// most visible on MALAYSIAN_SNR_NXR in choppy/ranging BTC conditions.
// Recording the close time per direction here; NXS_PostSLCooldownBlocks()
// below is the check called from NXS_OpenTrade/NXR_OpenTrade.
datetime g_lastSLCloseTime_BUY  = 0;   // last time a BUY position was stopped out
datetime g_lastSLCloseTime_SELL = 0;   // last time a SELL position was stopped out

void NXS_RegisterSLClose(ENUM_NXS_DIR closedDir){
   if(closedDir == DIR_BUY)  g_lastSLCloseTime_BUY  = TimeCurrent();
   if(closedDir == DIR_SELL) g_lastSLCloseTime_SELL = TimeCurrent();
}

// Blocks a NEW entry in `dir` if a position in the OPPOSITE direction was
// stopped out less than InpPostSLCooldownMin minutes ago.
bool NXS_PostSLCooldownBlocks(ENUM_NXS_DIR dir){
   if(!InpUsePostSLCooldown) return false;
   datetime oppositeCloseTime = (dir == DIR_BUY) ? g_lastSLCloseTime_SELL : g_lastSLCloseTime_BUY;
   if(oppositeCloseTime <= 0) return false;
   return (TimeCurrent() - oppositeCloseTime) < InpPostSLCooldownMin * 60;
}

// ----- Reason codes -----
#define NXS_R_TREND   "NXS:TREND"
#define NXS_R_PROFIT  "NXS:PROFIT"
#define NXS_R_DD      "NXS:DD"
#define NXS_R_TIME    "NXS:TIME"
#define NXS_R_NEWS    "NXS:NEWS"
#define NXS_R_BE      "NXS:BE"
#define NXS_R_RISK    "NXS:RISK"

// ----- Push Trade Reason to backend (retries w/ backoff — cold-start safe) --
void NXS_Prot_PushTradeReason(ulong ticket, long magic, string strategy,
                              string side, double lots, double openPrice,
                              double closePrice, double pnl, string reason,
                              datetime openTime, datetime closeTime){
   if(!InpEnableWebSync) return;
   string body = "{";
   body += "\"ticket\":"     + IntegerToString((long)ticket) + ",";
   body += "\"magic\":"      + IntegerToString(magic) + ",";
   body += "\"symbol\":\""   + g_sym + "\",";
   body += "\"strategy\":\""  + _JsonEsc(strategy) + "\",";
   body += "\"side\":\""     + side + "\",";
   body += "\"lots\":"       + DoubleToString(lots, 2) + ",";
   body += "\"openPrice\":"  + DoubleToString(openPrice, g_digits) + ",";
   body += "\"closePrice\":" + DoubleToString(closePrice, g_digits) + ",";
   body += "\"pnl\":"        + DoubleToString(pnl, 2) + ",";
   body += "\"openTime\":\"" + NXS_IsoTime(openTime) + "\",";
   body += "\"closeTime\":\""+ NXS_IsoTime(closeTime) + "\",";
   body += "\"reason\":\""   + _JsonEsc(reason) + "\"";
   body += "}";

   string url = InpWebURL + "/api/ea/trade_reason";
   char post[]; StringToCharArray(body, post, 0, -1, CP_UTF8);
   ArrayResize(post, ArraySize(post) - 1);
   string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";

   int maxAttempts = 3;
   int backoffMs    = 1000;
   for(int attempt = 1; attempt <= maxAttempts; attempt++){
      char result[]; string headersOut;
      int code = WebRequest("POST", url, headers, 20000, post, result, headersOut);
      if(code == 200) return;
      bool lastAttempt = (attempt == maxAttempts);
      if(InpDebugLog || lastAttempt){
         PrintFormat("[NEXUS PROT] PushTradeReason FAILED attempt=%d/%d code=%d ticket=%d reason=%s",
                     attempt, maxAttempts, code, ticket, reason);
      }
      if(!lastAttempt){
         Sleep(backoffMs);
         backoffMs *= 2;
      }
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
   datetime openTm = (datetime)PositionGetInteger(POSITION_TIME);

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
      NXS_Prot_PushTradeReason(ticket, mg, strat, side, lots, openP, closeP, pnl, reason,
                               openTm, TimeCurrent());
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
   long baseLimit = (long)InpProt_MaxHoldHours * 3600;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      // 17/07 fix - "due sistemi di chiusura per durata massima indipendenti
      // e non coordinati" (segnalato dall'utente il 24/06, ancora presente):
      // questo gate (base InpProt_MaxHoldHours=12h, scala x NXS_TF_LifeFactor)
      // e NXS_ManageBreakevenAndTrail() P1 (base InpMaxHoldHours=4h, scala
      // x40 barre del TF) potevano chiudere la STESSA posizione con limiti
      // diversi (es. D1: qui 30 giorni, li' 40 giorni) - vince chi scatta
      // prima, in modo imprevedibile. Per le strategie con profilo reale,
      // NXS_Management.mqh e' gia' l'autorita' (integrato con BE/trailing
      // nello stesso loop) - questo gate ora si limita alle strategie SENZA
      // profilo (session/Elliott), la sua vera rete di sicurezza originale.
      string posComment = PositionGetString(POSITION_COMMENT);
      string cpp[]; int ncpp = StringSplit(posComment, '|', cpp);
      string posStrat = (ncpp >= 2) ? cpp[1] : "";
      if(InpUseStrategyProfiles && StringLen(posStrat) > 0 &&
         NXS_Profile_TF(posStrat) != PERIOD_CURRENT)
         continue;   // ha un profilo reale -> gestita solo da NXS_Management.mqh
      datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
      // v2.0.21 — MaxHold proporzionato al TF di origine del segnale.
      long limit = (long)(baseLimit * NXS_TF_LifeFactor(NXS_PosSourceTF(posComment)));
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
   long baseMinLife = (long)InpProt_MinLifeMin * 60;   // v2.0.14
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      // v2.0.14 — non chiudere prima del tempo minimo di vita (anti stop-out su rumore M5).
      // v2.0.21 — il minimo scala col TF di origine: un trade H4/D1 vive di più
      // prima che NXS:RISK possa chiuderlo.
      datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
      long minLife = (long)(baseMinLife * NXS_TF_LifeFactor(NXS_PosSourceTF(PositionGetString(POSITION_COMMENT))));
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
   // v2.0.31: in Strategy Tester, don't let daily-pause/ESL/DPT/AutoClose
   // gates silence most of the 37 strategies for a big chunk of every test
   // window (this is what the Phase 2c per-strategy diagnostic found as the
   // dominant blocker for nearly all of them). Live behavior is completely
   // untouched - MQL_TESTER is only true while backtesting/optimizing.
   if(MQLInfoInteger(MQL_TESTER)) return false;
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
