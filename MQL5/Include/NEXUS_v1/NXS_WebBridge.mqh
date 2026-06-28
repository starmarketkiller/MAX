//+------------------------------------------------------------------+
//|  NXS_WebBridge.mqh - Push status + Poll commands                  |
//+------------------------------------------------------------------+
#ifndef __NXS_WEB_MQH__
#define __NXS_WEB_MQH__

string _JsonEsc(string s){
   string r = s;
   StringReplace(r, "\\", "\\\\");
   StringReplace(r, "\"", "\\\"");
   return r;
}

string _PositionsJSON(){
   string out = "[";
   bool first = true;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsNexusMagic(mg)) continue;
      long type = PositionGetInteger(POSITION_TYPE);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   = PositionGetDouble(POSITION_SL);
      double tp   = PositionGetDouble(POSITION_TP);
      double vol  = PositionGetDouble(POSITION_VOLUME);
      double pr   = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      double cur  = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_BID)
                                                 : SymbolInfoDouble(g_sym, SYMBOL_ASK);
      string side = (type == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      string com  = PositionGetString(POSITION_COMMENT);
      string strat = com;
      int p = StringFind(com, "|");
      if(p >= 0){
         strat = StringSubstr(com, p + 1);
         int q = StringFind(strat, "|");
         if(q >= 0) strat = StringSubstr(strat, 0, q);
      }
      if(!first) out += ",";
      out += "{";
      out += "\"ticket\":"      + (string)t + ",";
      out += "\"symbol\":\""    + g_sym + "\",";
      out += "\"side\":\""      + side + "\",";
      out += "\"lots\":"        + DoubleToString(vol, 2) + ",";
      out += "\"openPrice\":"   + DoubleToString(open, 2) + ",";
      out += "\"currentPrice\":"+ DoubleToString(cur,  2) + ",";
      out += "\"sl\":"          + DoubleToString(sl,   2) + ",";
      out += "\"tp\":"          + DoubleToString(tp,   2) + ",";
      out += "\"pnl\":"         + DoubleToString(pr,   2) + ",";
      out += "\"magic\":"       + (string)mg + ",";
      out += "\"strategy\":\""  + _JsonEsc(strat) + "\"";
      out += "}";
      first = false;
   }
   out += "]";
   return out;
}

string _StrategiesJSON(){
   string s = "{";
   s += StringFormat("\"ADX_RSI\":%s,",      (InpStrat_ADX_RSI ? "true":"false"));
   s += StringFormat("\"BOLLINGER\":%s,",    (InpStrat_BOLLINGER ? "true":"false"));
   s += StringFormat("\"MACD\":%s,",         (InpStrat_MACD ? "true":"false"));
   s += StringFormat("\"SAR\":%s,",          (InpStrat_SAR ? "true":"false"));
   s += StringFormat("\"TSI\":%s,",          (InpStrat_TSI ? "true":"false"));
   s += StringFormat("\"BJORGUM\":%s,",      (InpStrat_BJORGUM ? "true":"false"));
   s += StringFormat("\"LIQ_SWEEP\":%s,",    (InpStrat_LIQ_SWEEP ? "true":"false"));
   s += StringFormat("\"FVG_CONT\":%s,",     (InpStrat_FVG_CONT ? "true":"false"));
   s += StringFormat("\"BREAKOUT_ACC\":%s,", (InpStrat_BREAKOUT_ACC ? "true":"false"));
   s += StringFormat("\"LONDON_BO\":%s,",    (InpStrat_LONDON_BO ? "true":"false"));
   s += StringFormat("\"EMA_PULLBACK\":%s,", (InpStrat_EMA_PULLBACK ? "true":"false"));
   s += StringFormat("\"BB_SQUEEZE\":%s,",   (InpStrat_BB_SQUEEZE ? "true":"false"));
   s += StringFormat("\"ICHIMOKU\":%s,",     (InpStrat_ICHIMOKU ? "true":"false"));
   s += StringFormat("\"RSI_DIV\":%s,",      (InpStrat_RSI_DIV ? "true":"false"));
   s += StringFormat("\"ORDER_BLOCK\":%s,",   (InpStrat_ORDER_BLOCK ? "true":"false"));
   s += StringFormat("\"STRUCT_REACT\":%s",   (InpUseStructReact ? "true":"false"));
   s += "}";
   return s;
}

void NXS_WebPush(SNXSHTF &htf, SNXSVel &vel, SNXSAMD &amd, SNXSSweep &sw){
   if(!InpEnableWebSync) return;
   if(TimeCurrent() - g_lastPushTime < InpPushIntervalSec) return;
   g_lastPushTime = TimeCurrent();

   // cache for OnTimer fallback push
   g_cached.ready    = true;
   g_cached.htfBias  = htf.bias;
   g_cached.htfConf  = htf.conf;
   g_cached.htfRev   = htf.reversalAllowed;
   g_cached.velState = vel.state;
   g_cached.amdPhase = amd.phase;
   g_cached.amdHi    = amd.asianHigh;
   g_cached.amdLo    = amd.asianLow;
   g_cached.sweepDir = sw.dir;
   g_cached.sweepConf= sw.confirmed;

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   double floatPnL= NXS_FloatingPnL();
   double dailyPnL= (g_balanceDayStart > 0) ? (equity - g_balanceDayStart) : 0;
   double ddPct   = (g_balanceDayStart > 0) ? ((g_balanceDayStart - equity) / g_balanceDayStart * 100.0) : 0;
   if(ddPct < 0) ddPct = 0;
   double marginLvl = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   bool   newsBlock = NXS_NewsBlocking();
   double bspPct    = NXS_GetBSP();

   // Helper macros for compact JSON building
   #define _D2(x)  DoubleToString((x), 2)
   #define _D1(x)  DoubleToString((x), 1)
   #define _BOOL(x) ((x) ? "true" : "false")

   string body = "{";
   body += "\"version\":\""    + (string)NEXUS_VERSION + "\",";
   body += "\"magic\":"        + (string)InpMagic + ",";
   body += "\"symbol\":\""     + g_sym + "\",";
   body += "\"online\":true,";
   body += "\"balance\":"      + _D2(balance)  + ",";
   body += "\"equity\":"       + _D2(equity)   + ",";
   body += "\"floatPnL\":"     + _D2(floatPnL) + ",";
   body += "\"dailyPnL\":"     + _D2(dailyPnL) + ",";
   body += "\"drawdownPct\":"  + _D2(ddPct)    + ",";
   body += "\"eaPaused\":"     + _BOOL(g_eaPaused) + ",";
   body += "\"tradesToday\":"  + (string)g_tradesToday + ",";
   body += "\"consecLosses\":" + (string)g_consecLosses + ",";
   body += "\"marginLevel\":"  + _D2(marginLvl) + ",";
   body += "\"htfBias\":\""    + NXS_HTFName(htf.bias) + "\",";
   body += "\"velocity\":\""   + NXS_VelName(vel.state) + "\",";
   body += "\"newsBlock\":"    + _BOOL(newsBlock) + ",";
   body += "\"amdPhase\":\""   + NXS_AMDName(amd.phase) + "\",";
   body += "\"bspPct\":"       + _D2(bspPct) + ",";
   body += "\"regime\":\""     + NXS_RegimeName(g_regime) + "\",";
   body += "\"session\":\""    + NXS_SessionName(g_session) + "\",";
   body += "\"sweepDir\":\""   + NXS_DirName(sw.dir) + "\",";
   // Structure engine
   body += "\"structTrend\":\""  + NXS_StructTrendName(g_struct.trend) + "\",";
   body += "\"bosUp\":"          + _BOOL(g_struct.bosUp) + ",";
   body += "\"bosDown\":"        + _BOOL(g_struct.bosDown) + ",";
   body += "\"chochUp\":"        + _BOOL(g_struct.chochUp) + ",";
   body += "\"chochDown\":"      + _BOOL(g_struct.chochDown) + ",";
   body += "\"lastSwingHigh\":"  + _D2(g_struct.lastSwingHigh) + ",";
   body += "\"lastSwingLow\":"   + _D2(g_struct.lastSwingLow)  + ",";
   body += "\"activeLevels\":"   + (string)NXS_ActiveLevelCount() + ",";
   // Reaction engine
   body += "\"reactionDetected\":" + _BOOL(g_reaction.detected) + ",";
   body += "\"reactionType\":\""   + g_reaction.levelType + "\",";
   body += "\"reactionDir\":"      + (string)g_reaction.direction + ",";
   body += "\"reactionQuality\":"  + _D1(g_reaction.quality) + ",";
   // Risk Protections state (NEXUS v2.0)
   body += "\"eslHit\":"              + _BOOL(g_eslHit) + ",";
   body += "\"dptHit\":"              + _BOOL(g_dptHit) + ",";
   body += "\"pausedUntilNextOpen\":" + _BOOL(g_pausedUntilNextOpen) + ",";
   body += "\"autoClosePending\":"    + _BOOL(g_autoClosePending) + ",";
   body += "\"floatPnLPct\":"         + _D2((balance > 0) ? (floatPnL / balance * 100.0) : 0) + ",";
   body += "\"dailyPnLPct\":"         + _D2((g_balanceDayStart > 0) ? (dailyPnL / g_balanceDayStart * 100.0) : 0) + ",";
   // Phase 3: per-strategy cooldown snapshot
   body += "\"strategyCooldowns\":"   + NXS_CooldownsJSON() + ",";
   // Volatility regime (audit PDF)
   body += "\"volRegime\":\""         + NXS_VolRegimeStr() + "\",";
   // Filters bitmap
   body += "\"filters\":{";
   body += "\"htf\":"       + _BOOL(InpUseHTFBias) + ",";
   body += "\"velocity\":"  + _BOOL(InpUseVelocity) + ",";
   body += "\"news\":"      + _BOOL(InpUseNews) + ",";
   body += "\"amd\":"       + _BOOL(InpUseAMD) + ",";
   body += "\"bsp\":"       + _BOOL(InpUseBSP) + ",";
   body += "\"structure\":" + _BOOL(InpUseStructure) + ",";
   body += "\"reaction\":"  + _BOOL(InpUseReaction);
   body += "},";
   body += "\"strategies\":" + _StrategiesJSON() + ",";
   body += "\"positions\":"  + _PositionsJSON();
   body += "}";

   #undef _D2
   #undef _D1
   #undef _BOOL

   string url = InpWebURL + "/api/ea/push";
   char post[]; StringToCharArray(body, post, 0, -1, CP_UTF8);
   ArrayResize(post, ArraySize(post) - 1);
   char result[]; string headersOut;
   string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";
   int code = WebRequest("POST", url, headers, 3000, post, result, headersOut);
   if(code < 0){
      // Print first 5 failures always (helps debug WebRequest whitelist), then only with DebugLog
      static int failCount = 0;
      if(failCount < 5 || InpDebugLog){
         PrintFormat("[NEXUS] WebPush FAILED code=%d err=%d url=%s  >>> Check: MT5 Tools→Options→Expert Advisors→Allow WebRequest for listed URL (must contain '%s').",
                     code, GetLastError(), url, InpWebURL);
         failCount++;
      }
   } else if(code != 200){
      string resp = CharArrayToString(result, 0, MathMin(ArraySize(result), 500), CP_UTF8);
      PrintFormat("[NEXUS] WebPush HTTP %d url=%s resp=%s", code, url, resp);
      if(InpDebugLog){
         PrintFormat("[NEXUS] DEBUG body (first 500 chars): %s",
                     StringSubstr(body, 0, MathMin(500, StringLen(body))));
      }
   } else if(InpDebugLog){
      PrintFormat("[NEXUS] WebPush OK %d bytes", ArraySize(result));
   }
}

// Always-print diagnostic (does not depend on InpDebugLog) - so first push
// failure is visible the first time the EA tries (helps users debug WebRequest).
void NXS_WebPushSafe(){
   if(!InpEnableWebSync) return;
   SNXSHTF   h;  h.bias  = g_cached.ready ? g_cached.htfBias  : HTF_NEUTRAL;
                 h.conf  = g_cached.htfConf;
                 h.reversalAllowed = g_cached.htfRev;
   SNXSVel   v;  v.state = g_cached.ready ? g_cached.velState : VEL_NEUTRAL; v.slope = 0;
   SNXSAMD   a;  a.phase = g_cached.ready ? g_cached.amdPhase : AMD_NONE;
                 a.asianHigh = g_cached.amdHi; a.asianLow = g_cached.amdLo;
                 a.expectedDir = DIR_NONE; a.modifier = 0;
   SNXSSweep s;  s.dir   = g_cached.ready ? g_cached.sweepDir : DIR_NONE;
                 s.confirmed = g_cached.sweepConf; s.level = 0;
   NXS_WebPush(h, v, a, s);
}

void NXS_WebPoll(){
   if(!InpEnableWebSync) return;
   if(TimeCurrent() - g_lastPollTime < InpPollIntervalSec) return;
   g_lastPollTime = TimeCurrent();

   string url = InpWebURL + "/api/ea/command";
   char empty[]; char result[]; string headersOut;
   string headers = "X-Nexus-Token: " + InpWebToken + "\r\n";
   int code = WebRequest("GET", url, headers, 3000, empty, result, headersOut);
   if(code < 0){
      static int pollFailCount = 0;
      if(pollFailCount < 3){
         PrintFormat("[NEXUS] WebPoll FAILED code=%d err=%d url=%s", code, GetLastError(), url);
         pollFailCount++;
      }
      return;
   }
   if(code != 200) return;
   string resp = CharArrayToString(result, 0, -1, CP_UTF8);
   if(StringFind(resp, "\"action\":null") >= 0) return;

   // Extract action
   string action = "";
   int aPos = StringFind(resp, "\"action\":\"");
   if(aPos >= 0){
      int s = aPos + 10;
      int e = StringFind(resp, "\"", s);
      if(e > s) action = StringSubstr(resp, s, e - s);
   }
   if(action == "") return;
   PrintFormat("[NEXUS] Command received: %s", action);

   if(action == "pause"){
      g_eaPaused = true;
   }
   else if(action == "resume"){
      g_eaPaused = false;
   }
   else if(action == "close_all"){
      for(int i = PositionsTotal()-1; i >= 0; i--){
         ulong t = PositionGetTicket(i);
         if(t == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
         long mg = (long)PositionGetInteger(POSITION_MAGIC);
         if(!IsNexusMagic(mg)) continue;
         NXS_DoClose(t);
      }
      Print("[NEXUS] close_all executed");
   }
   else if(action == "close_position"){
      // extract ticket from payload
      int tPos = StringFind(resp, "\"ticket\":");
      if(tPos >= 0){
         int s = tPos + 9;
         // skip spaces
         while(s < StringLen(resp) && (StringGetCharacter(resp, s) == ' ')) s++;
         int e = s;
         while(e < StringLen(resp)){
            ushort c = StringGetCharacter(resp, e);
            if(c >= '0' && c <= '9') e++; else break;
         }
         if(e > s){
            ulong ticket = (ulong)StringToInteger(StringSubstr(resp, s, e - s));
            if(NXS_DoClose(ticket))
               PrintFormat("[NEXUS] close_position OK ticket=%I64u", ticket);
            else
               PrintFormat("[NEXUS] close_position FAIL ticket=%I64u retcode=%d", ticket, NXS_TradeRetcode());
         }
      }
   }
   else if(action == "partial_close"){
      int tPos = StringFind(resp, "\"ticket\":");
      int vPos = StringFind(resp, "\"volume\":");
      if(tPos >= 0 && vPos >= 0){
         int ts = tPos + 9, te = ts;
         while(te < StringLen(resp)){
            ushort c = StringGetCharacter(resp, te);
            if(c >= '0' && c <= '9') te++; else break;
         }
         int vs = vPos + 9, ve = vs;
         while(ve < StringLen(resp)){
            ushort c = StringGetCharacter(resp, ve);
            if((c >= '0' && c <= '9') || c == '.') ve++; else break;
         }
         if(te > ts && ve > vs){
            ulong  ticket = (ulong)StringToInteger(StringSubstr(resp, ts, te - ts));
            double volume = StringToDouble(StringSubstr(resp, vs, ve - vs));
            if(NXS_DoClosePartial(ticket, volume))
               PrintFormat("[NEXUS] partial_close OK ticket=%I64u vol=%.2f", ticket, volume);
            else
               PrintFormat("[NEXUS] partial_close FAIL ticket=%I64u", ticket);
         }
      }
   }
   else if(action == "reset_anti_revenge"){
      g_antiRevengeUntil = 0;
      g_consecLosses = 0;
      Print("[NEXUS] anti-revenge reset");
   }
   else if(action == "reset_daily"){
      g_tradesToday = 0;
      g_balanceDayStart = AccountInfoDouble(ACCOUNT_BALANCE);
      Print("[NEXUS] daily counters reset");
   }
}

#endif
