//+------------------------------------------------------------------+
//|  NXS_WebBridge.mqh - Push status + Poll commands                  |
//+------------------------------------------------------------------+
#ifndef __NXS_WEB_MQH__
#define __NXS_WEB_MQH__

// _JsonEsc now lives in NXS_Globals.mqh (shared with NXS_Protections.mqh).

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
   int code = WebRequest("POST", url, headers, 20000, post, result, headersOut);
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

// --- helper di parsing --------------------------------------------------- #
string _NXS_JsonStr(string resp, string key){
   string needle = "\"" + key + "\":\"";
   int p = StringFind(resp, needle);
   if(p < 0) return "";
   int s = p + StringLen(needle);
   int e = StringFind(resp, "\"", s);
   return (e > s) ? StringSubstr(resp, s, e - s) : "";
}

double _NXS_JsonNum(string resp, string key, bool &found){
   found = false;
   string needle = "\"" + key + "\":";
   int p = StringFind(resp, needle);
   if(p < 0) return 0;
   int s = p + StringLen(needle);
   while(s < StringLen(resp) && StringGetCharacter(resp, s) == ' ') s++;
   int e = s;
   while(e < StringLen(resp)){
      ushort c = StringGetCharacter(resp, e);
      if((c >= '0' && c <= '9') || c == '.' || c == '-') e++; else break;
   }
   if(e <= s) return 0;
   found = true;
   return StringToDouble(StringSubstr(resp, s, e - s));
}

// AUD0-WEB-006: le chiusure remote non verificavano che il ticket
// appartenesse davvero a questa istanza prima di inviare l'ordine.
bool _NXS_OwnsPosition(ulong ticket){
   if(!PositionSelectByTicket(ticket)) return false;
   if(PositionGetString(POSITION_SYMBOL) != g_sym) return false;
   return IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC));
}

// AUD0-WEB-004: l'EA non comunicava mai l'esito reale al backend, quindi
// "DELIVERED" era l'unica informazione disponibile. Ora ogni comando termina
// con un ACK esplicito che riporta lo stato broker.
void _NXS_CommandAck(string commandId, string leaseId, string status,
                     string detail, int closedCount, int remainingCount){
   if(StringLen(commandId) == 0 || StringLen(leaseId) == 0) return;
   string body = "{";
   body += "\"command_id\":\"" + _JsonEsc(commandId) + "\",";
   body += "\"lease_id\":\""   + _JsonEsc(leaseId)   + "\",";
   body += "\"status\":\""     + status              + "\",";
   body += "\"retcode\":"      + (string)NXS_TradeRetcode() + ",";
   body += "\"closed_count\":" + (string)closedCount + ",";
   body += "\"remaining_count\":" + (string)remainingCount + ",";
   body += "\"detail\":\""     + _JsonEsc(detail)    + "\"}";

   char data[]; StringToCharArray(body, data, 0, StringLen(body), CP_UTF8);
   char result[]; string headersOut;
   string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";
   int code = WebRequest("POST", InpWebURL + "/api/ea/command/ack", headers, 5000,
                         data, result, headersOut);
   if(code != 200)
      PrintFormat("[NEXUS] ACK comando %s non confermato (http=%d)", commandId, code);
}

void NXS_WebPoll(){
   if(!InpEnableWebSync) return;
   if(TimeCurrent() - g_lastPollTime < InpPollIntervalSec) return;
   g_lastPollTime = TimeCurrent();

   // AUD0-CMD-002 / AUD0-WEB-002: il polling non dichiarava a quale istanza
   // appartenesse, quindi il backend consegnava il comando globale più
   // vecchio — potenzialmente destinato a un altro account o simbolo.
   long   account = (long)AccountInfoInteger(ACCOUNT_LOGIN);
   string url = InpWebURL + "/api/ea/command"
              + "?account_id=" + (string)account
              + "&symbol=" + g_sym
              + "&magic=" + (string)InpMagic;

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

   string action    = _NXS_JsonStr(resp, "action");
   string commandId = _NXS_JsonStr(resp, "command_id");
   string leaseId   = _NXS_JsonStr(resp, "lease_id");
   if(action == "") return;

   // AUD0-WEB-002: il target dichiarato dal backend deve corrispondere
   // ESATTAMENTE a questa istanza. Un comando indirizzato altrove viene
   // rifiutato in modo definitivo, non eseguito.
   string tgtAccount = _NXS_JsonStr(resp, "account_id");
   string tgtSymbol  = _NXS_JsonStr(resp, "symbol");
   if((StringLen(tgtAccount) > 0 && tgtAccount != (string)account) ||
      (StringLen(tgtSymbol)  > 0 && tgtSymbol  != g_sym)){
      PrintFormat("[NEXUS] comando %s RIFIUTATO: target %s/%s != istanza %I64d/%s",
                  action, tgtAccount, tgtSymbol, account, g_sym);
      _NXS_CommandAck(commandId, leaseId, "FAILED_FINAL",
                      "target mismatch", 0, 0);
      return;
   }

   PrintFormat("[NEXUS] Command received: %s (id=%s)", action, commandId);
   string status = "SUCCEEDED";
   string detail = "";
   int    closed = 0, remaining = 0;

   if(action == "pause"){
      g_eaPaused = true;
      detail = "trading in pausa";
   }
   else if(action == "resume"){
      g_eaPaused = false;
      detail = "trading ripreso";
   }
   else if(action == "close_all"){
      // AUD0-WEB-005: il loop ignorava ogni esito e stampava comunque
      // "close_all executed", anche con posizioni ancora aperte.
      for(int i = PositionsTotal()-1; i >= 0; i--){
         ulong t = PositionGetTicket(i);
         if(t == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
         long mg = (long)PositionGetInteger(POSITION_MAGIC);
         if(!IsNexusMagic(mg)) continue;
         if(NXS_DoClose(t)) closed++; else remaining++;
      }
      if(remaining > 0){
         // Restano posizioni: il comando NON è riuscito. Retryable, così il
         // backend lo riprova finché ci sono tentativi disponibili.
         status = "FAILED_RETRYABLE";
         detail = StringFormat("chiuse %d, ancora aperte %d", closed, remaining);
      } else {
         detail = StringFormat("chiuse %d posizioni", closed);
      }
      PrintFormat("[NEXUS] close_all: chiuse=%d rimaste=%d", closed, remaining);
   }
   else if(action == "close_position"){
      bool found = false;
      double tRaw = _NXS_JsonNum(resp, "ticket", found);
      if(!found){
         status = "FAILED_FINAL"; detail = "ticket mancante";
      } else {
         ulong ticket = (ulong)tRaw;
         if(!_NXS_OwnsPosition(ticket)){
            status = "FAILED_FINAL";
            detail = StringFormat("ticket %I64u non appartiene a questa istanza", ticket);
            PrintFormat("[NEXUS] close_position RIFIUTATO: %s", detail);
         } else if(NXS_DoClose(ticket)){
            closed = 1;
            detail = StringFormat("ticket %I64u chiuso", ticket);
         } else {
            status = "FAILED_RETRYABLE";
            detail = StringFormat("close fallito retcode=%d", NXS_TradeRetcode());
         }
      }
   }
   else if(action == "partial_close"){
      bool fT = false, fV = false;
      double tRaw = _NXS_JsonNum(resp, "ticket", fT);
      double vol  = _NXS_JsonNum(resp, "volume", fV);
      if(!fT || !fV){
         status = "FAILED_FINAL"; detail = "ticket o volume mancante";
      } else {
         ulong ticket = (ulong)tRaw;
         // AUD0-WEB-007: ticket e volume finivano direttamente nell'helper
         // raw, senza verifica di ownership né di volume valido.
         if(!_NXS_OwnsPosition(ticket)){
            status = "FAILED_FINAL";
            detail = StringFormat("ticket %I64u non appartiene a questa istanza", ticket);
         } else if(NXS_DoClosePartial(ticket, vol)){
            detail = StringFormat("chiusi %.4f lotti su %I64u", vol, ticket);
         } else {
            status = "FAILED_FINAL";
            detail = StringFormat("volume non valido o rifiutato retcode=%d", NXS_TradeRetcode());
         }
      }
   }
   else if(action == "reset_anti_revenge"){
      g_antiRevengeUntil = 0;
      g_consecLosses = 0;
      detail = "anti-revenge azzerato";
      Print("[NEXUS] anti-revenge reset");
   }
   else if(action == "reset_daily"){
      // AUD0-WEB-009: il comando riscrive la baseline di drawdown giornaliero.
      // L'effetto viene ora dichiarato esplicitamente nell'ACK, così resta
      // tracciato nell'audit del backend e non solo nel log locale.
      g_tradesToday = 0;
      g_balanceDayStart = AccountInfoDouble(ACCOUNT_BALANCE);
      detail = StringFormat("contatori azzerati; baseline DD riportata a %.2f",
                            g_balanceDayStart);
      Print("[NEXUS] daily counters reset — baseline drawdown riscritta");
   }
   // v2.0.24 — remote unlock for ESL/DPT/AutoClose pause. Previously only a
   // state-file delete + EA restart could clear g_pausedUntilNextOpen; this
   // lets the dashboard do it without touching files or restarting.
   else if(action == "reset_protections"){
      g_eslHit = false;
      g_dptHit = false;
      g_pausedUntilNextOpen = false;
      g_autoClosePending = false;
      detail = "ESL/DPT/AutoClose pause azzerati";
      Print("[NEXUS] protections reset (ESL/DPT/AutoClose pause cleared) via dashboard");
   }
   else if(action == "resync_trades"){
      // AUD0-BE-CMD-009: il backend accettava questa azione ma il parser MQL
      // non la gestiva, quindi non accadeva nulla e nessuno se ne accorgeva.
      g_lastHistSyncTime = 0;   // forza la risincronizzazione al prossimo ciclo
      detail = "risincronizzazione storico richiesta";
   }
   else {
      status = "FAILED_FINAL";
      detail = "azione non supportata da questa build dell'EA";
      PrintFormat("[NEXUS] comando sconosciuto: %s", action);
   }

   _NXS_CommandAck(commandId, leaseId, status, detail, closed, remaining);
}

#endif
