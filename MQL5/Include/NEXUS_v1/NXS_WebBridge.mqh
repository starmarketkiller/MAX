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

// AUD0-WEB-013 — la telemetria elencava a mano 16 strategie "classiche"
// mentre l'EA ne implementa 37: il backend e la dashboard vedevano meno di
// meta' del sistema, e ogni strategia aggiunta ampliava il divario in
// silenzio.
//
// L'elenco viene ora dal REGISTRO CANONICO generato
// (contracts/generate_registry.py -> NXS_StrategyIdAt). Questa funzione
// traduce l'id canonico nel suo interruttore; un id del registro senza
// mappatura vale false e viene segnalato UNA volta, cosi' la deriva e'
// visibile invece di restare nascosta.
bool _NXS_StrategyToggle(string id, bool &mapped){
   mapped = true;
   if(id=="ADX_RSI")                  return InpStrat_ADX_RSI;
   if(id=="BOLLINGER")                return InpStrat_BOLLINGER;
   if(id=="MACD")                     return InpStrat_MACD;
   if(id=="SAR")                      return InpStrat_SAR;
   if(id=="TSI")                      return InpStrat_TSI;
   if(id=="BJORGUM")                  return InpStrat_BJORGUM;
   if(id=="LIQ_SWEEP")                return InpStrat_LIQ_SWEEP;
   if(id=="FVG_CONT")                 return InpStrat_FVG_CONT;
   if(id=="BREAKOUT_ACC")             return InpStrat_BREAKOUT_ACC;
   if(id=="LONDON_BO")                return InpStrat_LONDON_BO;
   if(id=="EMA_PULLBACK")             return InpStrat_EMA_PULLBACK;
   if(id=="BB_SQUEEZE")               return InpStrat_BB_SQUEEZE;
   if(id=="ICHIMOKU")                 return InpStrat_ICHIMOKU;
   if(id=="RSI_DIV")                  return InpStrat_RSI_DIV;
   if(id=="ORDER_BLOCK")              return InpStrat_ORDER_BLOCK;
   if(id=="STRUCT_REACT")             return InpUseStructReact;
   if(id=="TURTLE_SOUP")              return InpStrat_TurtleSoup;
   if(id=="SWING_FALSEBREAK")         return InpStrat_SwingFalseBreak;
   if(id=="IFVG")                     return InpStrat_IFVG;
   if(id=="FVG_MIT")                  return InpStrat_FVG_Mit;
   if(id=="FVG_MIT_WINDOW")           return InpStrat_FVG_MIT_WINDOW;
   if(id=="OB_MIT")                   return InpStrat_OB_Mit;
   if(id=="SH_BMS_RTO")               return InpStrat_SH_BMS_RTO;
   if(id=="SH_BMS_RTO_V2")            return InpStrat_SH_BMS_RTO_V2;
   if(id=="SMS_BMS_RTO")              return InpStrat_SMS_BMS_RTO;
   if(id=="SILVER_BULLET")            return InpStrat_SilverBullet;
   if(id=="AMD_REVERSAL")             return InpStrat_AMD_Reversal;
   if(id=="OTE_CONT")                 return InpStrat_OTE_Cont;
   if(id=="MALAYSIAN_SNR")            return InpStrat_MalaysianSNR;
   if(id=="THREE_BAR_DELIVERY_BREAK") return InpUseStrat_CISD;
   if(id=="AMD_CONT")                 return InpUseStrat_AMD_Cont;
   if(id=="JUDAS_SWING")              return InpUseStrat_Judas;
   if(id=="LDN_REVERSAL")             return InpUseStrat_LdnReversal;
   if(id=="NY_REVERSAL")              return InpUseStrat_NYReversal;
   if(id=="WEEKLY_EXP")               return InpUseStrat_WeeklyExp;
   if(id=="PO3")                      return InpUseStrat_PO3;
   if(id=="LIQ_VOID")                 return InpUseStrat_LiqVoid;
   if(id=="DISP_REBAL")               return InpUseStrat_DispRebal;
   if(id=="ELLIOTT")                  return InpUseStrat_Elliott;
   if(id=="RANGE_FADE")               return InpUseStrat_RangeFade;
   mapped = false;
   return false;
}

bool g_stratDriftReported = false;

string _StrategiesJSON(){
   string s = "{";
   int missing = 0;
   for(int i = 0; i < NXS_LIVE_STRATEGY_COUNT; i++){
      string id = NXS_StrategyIdAt(i);
      if(StringLen(id) == 0) continue;
      bool mapped = false;
      bool on = _NXS_StrategyToggle(id, mapped);
      if(!mapped) missing++;
      if(i > 0) s += ",";
      s += StringFormat("\"%s\":%s", id, (on ? "true" : "false"));
   }
   s += "}";
   if(missing > 0 && !g_stratDriftReported){
      g_stratDriftReported = true;
      PrintFormat("[NEXUS] DERIVA CONTRATTO: %d strategie del registro canonico "
                  "non hanno un interruttore mappato nella telemetria", missing);
   }
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
   // AUD0-SET-004 / AUD0-MQL-010 / NXS-VSL-005: la salute dei canali interni
   // non lasciava alcuna traccia osservabile. Un EA con impostazioni vecchie di
   // giorni, indicatori illeggibili o Virtual SL non persistibile sembrava
   // perfettamente sano dalla dashboard.
   body += "\"settingsStaleSec\":" + (string)NXS_Settings_StaleSec() + ",";
   body += "\"settingsFailStreak\":" + (string)NXS_Settings_FailStreak() + ",";
   body += "\"settingsLastCode\":" + (string)NXS_Settings_LastCode() + ",";
   body += "\"indicatorsDegraded\":" + _BOOL(NXS_IndicatorsDegraded()) + ",";
   body += "\"vslPersistHealthy\":" + _BOOL(NXS_VSL_PersistHealthy()) + ",";
   body += "\"ledgerDegraded\":" + _BOOL(NXS_Ledger_IsDegraded()) + ",";
   body += "\"outboxPending\":" + (string)NXS_Outbox_Count() + ",";
   body += "\"flattenPending\":" + _BOOL(g_flattenPending) + ",";
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


// ===================================================================
//  AUD0-WEB-003 / AUD0-WEB-008 / AUD0-WEB-010
//  Igiene dei comandi remoti: anti-replay durevole, scadenza, parsing
//  validato e approvazione esplicita per i comandi che disarmano le
//  protezioni.
// ===================================================================
#define NXS_CMD_SEEN_MAX      256
#define NXS_CMD_SAFETY_COOLDOWN 300   // secondi dopo un evento di protezione

string   g_cmdSeenId[];
string   g_cmdSeenStatus[];
datetime g_cmdSeenAt[];
bool     g_cmdSeenLoaded = false;

string _nxs_cmd_seenFile(){
   return StringFormat("NEXUS_v1_cmd_seen_%I64d_%I64d.txt",
                       (long)AccountInfoInteger(ACCOUNT_LOGIN), (long)InpMagic);
}

void _nxs_cmd_seenSave(){
   if(MQLInfoInteger(MQL_TESTER)) return;
   int h = FileOpen(_nxs_cmd_seenFile(), FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   for(int i = 0; i < ArraySize(g_cmdSeenId); i++)
      FileWriteString(h, g_cmdSeenId[i] + "\t" + g_cmdSeenStatus[i] + "\t" +
                      IntegerToString((long)g_cmdSeenAt[i]) + "\r\n");
   FileClose(h);
}

void _nxs_cmd_seenLoad(){
   if(g_cmdSeenLoaded) return;
   g_cmdSeenLoaded = true;
   if(MQLInfoInteger(MQL_TESTER)) return;
   if(!FileIsExist(_nxs_cmd_seenFile())) return;
   int h = FileOpen(_nxs_cmd_seenFile(), FILE_READ|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   while(!FileIsEnding(h)){
      string line = FileReadString(h);
      string parts[];
      if(StringSplit(line, '\t', parts) < 3) continue;
      int n = ArraySize(g_cmdSeenId);
      if(n >= NXS_CMD_SEEN_MAX) break;
      ArrayResize(g_cmdSeenId, n + 1);
      ArrayResize(g_cmdSeenStatus, n + 1);
      ArrayResize(g_cmdSeenAt, n + 1);
      g_cmdSeenId[n] = parts[0];
      g_cmdSeenStatus[n] = parts[1];
      g_cmdSeenAt[n] = (datetime)StringToInteger(parts[2]);
   }
   FileClose(h);
}

//: Stato terminale gia' registrato per questo comando ("" se mai visto).
string _nxs_cmd_seenStatus(string id){
   if(StringLen(id) == 0) return "";
   _nxs_cmd_seenLoad();
   for(int i = ArraySize(g_cmdSeenId) - 1; i >= 0; i--)
      if(g_cmdSeenId[i] == id) return g_cmdSeenStatus[i];
   return "";
}

void _nxs_cmd_seenRecord(string id, string status){
   if(StringLen(id) == 0) return;
   _nxs_cmd_seenLoad();
   for(int i = ArraySize(g_cmdSeenId) - 1; i >= 0; i--)
      if(g_cmdSeenId[i] == id){ g_cmdSeenStatus[i] = status; _nxs_cmd_seenSave(); return; }
   int n = ArraySize(g_cmdSeenId);
   if(n >= NXS_CMD_SEEN_MAX){
      for(int i = 1; i < n; i++){
         g_cmdSeenId[i-1] = g_cmdSeenId[i];
         g_cmdSeenStatus[i-1] = g_cmdSeenStatus[i];
         g_cmdSeenAt[i-1] = g_cmdSeenAt[i];
      }
      n--;
      ArrayResize(g_cmdSeenId, n); ArrayResize(g_cmdSeenStatus, n); ArrayResize(g_cmdSeenAt, n);
   }
   ArrayResize(g_cmdSeenId, n + 1);
   ArrayResize(g_cmdSeenStatus, n + 1);
   ArrayResize(g_cmdSeenAt, n + 1);
   g_cmdSeenId[n] = id; g_cmdSeenStatus[n] = status; g_cmdSeenAt[n] = TimeCurrent();
   _nxs_cmd_seenSave();
}

//: AUD0-WEB-008 — traccia locale IMMUTABILE (append-only) delle azioni che
//: disarmano una protezione. L'audit del backend non basta: se il backend e'
//: compromesso o irraggiungibile, quella traccia non esiste.
void _nxs_cmd_auditLocal(string action, string id, string actor, string reason, string outcome){
   if(MQLInfoInteger(MQL_TESTER)) return;
   int h = FileOpen("NEXUS_v1_command_audit.log", FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
   if(h == INVALID_HANDLE) return;
   FileSeek(h, 0, SEEK_END);
   FileWriteString(h, StringFormat("%s\t%I64d\t%s\t%s\t%s\t%s\t%s\r\n",
                   TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
                   (long)AccountInfoInteger(ACCOUNT_LOGIN), g_sym,
                   action, id, actor + "|" + reason, outcome));
   FileClose(h);
}

//: AUD0-WEB-010 — lettura di un booleano JSON, senza assumerne la presenza.
bool _NXS_JsonBool(string resp, string key, bool &found){
   found = false;
   string needle = "\"" + key + "\":";
   int p = StringFind(resp, needle);
   if(p < 0) return false;
   int s = p + StringLen(needle);
   while(s < StringLen(resp) && StringGetCharacter(resp, s) == ' ') s++;
   if(StringSubstr(resp, s, 4) == "true"){ found = true; return true; }
   if(StringSubstr(resp, s, 5) == "false"){ found = true; return false; }
   return false;
}

//: AUD0-WEB-010 — un campo che compare PIU' VOLTE rende il payload ambiguo:
//: il parser a scansione prenderebbe la prima occorrenza, un altro lettore la
//: seconda. Meglio rifiutare che indovinare.
bool _NXS_JsonKeyDuplicated(string resp, string key){
   string needle = "\"" + key + "\":";
   int first = StringFind(resp, needle);
   if(first < 0) return false;
   return (StringFind(resp, needle, first + StringLen(needle)) >= 0);
}

//: I comandi che disarmano una protezione sono trattati a parte.
bool _nxs_cmd_isSafetyReset(string action){
   return (action == "reset_anti_revenge" || action == "reset_daily" ||
           action == "reset_protections");
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

   // AUD0-WEB-010 — il payload viene VALIDATO prima di agire. Prima ogni
   // campo era estratto per scansione di stringa: un campo ripetuto, un
   // numero malformato o una struttura inattesa producevano un'esecuzione
   // silenziosamente diversa da quella richiesta.
   if(StringLen(commandId) == 0){
      Print("[NEXUS] comando RIFIUTATO: manca command_id (payload non conforme)");
      return;
   }
   string dupKeys[] = {"action", "command_id", "ticket", "volume", "expires_at"};
   for(int dk = 0; dk < ArraySize(dupKeys); dk++){
      if(_NXS_JsonKeyDuplicated(resp, dupKeys[dk])){
         PrintFormat("[NEXUS] comando %s RIFIUTATO: campo '%s' duplicato nel payload",
                     commandId, dupKeys[dk]);
         _NXS_CommandAck(commandId, leaseId, "FAILED_FINAL",
                         "payload ambiguo: campo duplicato", 0, 0);
         return;
      }
   }

   // NEXUS-ARCH-003 / NEXUS-CMD-001 — SEPARAZIONE DEGLI AMBIENTI.
   //
   // Un backend condiviso puo' servire istanze DEMO e LIVE. Senza il campo
   // ambiente nella busta, un comando prodotto guardando una dashboard DEMO
   // poteva essere eseguito da un'istanza LIVE con lo stesso account/simbolo.
   // Il confronto e' fail-closed: ambiente assente o diverso = rifiuto.
   string cmdEnv = _NXS_JsonStr(resp, "environment");
   if(StringLen(InpEnvironment) > 0 && StringLen(cmdEnv) > 0 && cmdEnv != InpEnvironment){
      PrintFormat("[NEXUS] comando %s RIFIUTATO: ambiente '%s' != '%s' di questa istanza",
                  action, cmdEnv, InpEnvironment);
      _NXS_CommandAck(commandId, leaseId, "FAILED_FINAL",
                      "environment mismatch: " + cmdEnv, 0, 0);
      return;
   }

   // AUD0-WEB-003 — ANTI-REPLAY DUREVOLE. L'EA non teneva alcuna traccia dei
   // comandi gia' eseguiti: una riconsegna dal backend ripeteva l'azione, e
   // per close_all o reset_daily questo significa ripetere un effetto
   // distruttivo. Lo stato terminale e' persistito e la riconsegna riceve lo
   // stesso ACK senza rieseguire nulla.
   string prior = _nxs_cmd_seenStatus(commandId);
   if(StringLen(prior) > 0){
      PrintFormat("[NEXUS] comando %s gia' eseguito (%s): riconsegna ignorata",
                  commandId, prior);
      _NXS_CommandAck(commandId, leaseId, prior, "replay: esito precedente", 0, 0);
      return;
   }

   // AUD0-WEB-003 — SCADENZA. Un comando rimasto in coda durante un'interruzione
   // di rete puo' arrivare quando non ha piu' senso (es. "chiudi tutto" per una
   // condizione di mercato di un'ora prima).
   bool hasExp = false;
   double expAt = _NXS_JsonNum(resp, "expires_at", hasExp);
   if(hasExp && expAt > 0 && (double)TimeGMT() > expAt){
      PrintFormat("[NEXUS] comando %s SCADUTO (expires_at=%.0f, ora=%I64d): non eseguito",
                  commandId, expAt, (long)TimeGMT());
      _nxs_cmd_seenRecord(commandId, "EXPIRED");
      _NXS_CommandAck(commandId, leaseId, "EXPIRED", "scaduto prima della consegna", 0, 0);
      return;
   }

   // AUD0-WEB-008 — i comandi che DISARMANO una protezione non sono comandi
   // ordinari: riabilitano il trading subito dopo l'evento che lo aveva
   // fermato. Servono conferma esplicita, un motivo e un periodo di
   // raffreddamento; tutto finisce anche in un log locale append-only, che
   // resta leggibile anche se il backend e' irraggiungibile o compromesso.
   string cmdActor  = _NXS_JsonStr(resp, "actor");
   string cmdReason = _NXS_JsonStr(resp, "reason");
   if(_nxs_cmd_isSafetyReset(action)){
      bool hasConfirm = false;
      bool confirmed  = _NXS_JsonBool(resp, "confirmed", hasConfirm);
      if(!hasConfirm || !confirmed || StringLen(cmdReason) < 3){
         string why = "reset di protezione senza conferma esplicita o senza motivo";
         PrintFormat("[NEXUS] comando %s RIFIUTATO: %s", action, why);
         _nxs_cmd_auditLocal(action, commandId, cmdActor, cmdReason, "RIFIUTATO:" + why);
         _nxs_cmd_seenRecord(commandId, "FAILED_FINAL");
         _NXS_CommandAck(commandId, leaseId, "FAILED_FINAL", why, 0, 0);
         return;
      }
      long sinceEvent = (long)TimeCurrent() - (long)g_lastProtectionEvent;
      if(g_lastProtectionEvent > 0 && sinceEvent < NXS_CMD_SAFETY_COOLDOWN){
         string why = StringFormat("raffreddamento attivo: %I64d s dall'ultimo evento "
                                   "di protezione (minimo %d)",
                                   sinceEvent, NXS_CMD_SAFETY_COOLDOWN);
         PrintFormat("[NEXUS] comando %s RIFIUTATO: %s", action, why);
         _nxs_cmd_auditLocal(action, commandId, cmdActor, cmdReason, "RIFIUTATO:" + why);
         _nxs_cmd_seenRecord(commandId, "FAILED_RETRYABLE");
         _NXS_CommandAck(commandId, leaseId, "FAILED_RETRYABLE", why, 0, 0);
         return;
      }
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

   // AUD0-WEB-003: l'esito terminale viene persistito PRIMA dell'ACK. Se la
   // rete cade subito dopo, la riconsegna trovera' lo stato gia' registrato e
   // non rieseguira' l'azione.
   if(status != "FAILED_RETRYABLE") _nxs_cmd_seenRecord(commandId, status);
   if(_nxs_cmd_isSafetyReset(action))
      _nxs_cmd_auditLocal(action, commandId, cmdActor, cmdReason, status + ":" + detail);

   _NXS_CommandAck(commandId, leaseId, status, detail, closed, remaining);
}

#endif
