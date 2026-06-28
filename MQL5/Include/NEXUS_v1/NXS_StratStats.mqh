//+------------------------------------------------------------------+
//|  NXS_StratStats.mqh                                               |
//|  NEXUS v2.0.5 - Per-strategy full-lifecycle diagnostics tracker   |
//|                                                                   |
//|  12-step lifecycle tracked per strategy NAME:                     |
//|     1. enabled       (input flag check)                           |
//|     2. called        (invoked by collector)                       |
//|     3. setup         (returned dir != NONE → setup detected)      |
//|     4. signal        (alias of setup in this version)             |
//|     5. score_base    (pre-MTF/Vel)                                |
//|     6. score_final   (post-router gates)                          |
//|     7. threshold     (required min score)                         |
//|     8. blocked_at    (per-gate counters)                          |
//|     9. sltp_invalid  (SL/TP precheck failure count)               |
//|    10. executed      (EXEC_OK)                                    |
//|    11. closed        (deal_out)                                   |
//|    12. outcome_R / pnl / hold_sec                                 |
//|                                                                   |
//|  Exports to MQL5/Files/NEXUS/nexus_stats_{sym}_{tf}.csv           |
//|  + .json companion every InpStatsExportEverySec.                  |
//+------------------------------------------------------------------+
#ifndef __NXS_STRAT_STATS_MQH__
#define __NXS_STRAT_STATS_MQH__

#define NXS_STATS_MAX_NAMES   48
#define NXS_STATS_BLOCKERS    16
#define NXS_STATS_FOLDER      "NEXUS"

struct SNXSStratRow {
   string name;
   bool   enabled;
   long   called;
   long   setupDetected;
   long   signalsProduced;     // alias of setupDetected in v2.0.5 baseline
   long   executed;
   long   sltp_invalid;
   long   wins;
   long   losses;
   long   breakeven;
   double sumScoreBase;        // sum across all signals
   double sumScoreFinal;       // sum at execution time
   double sumThreshold;
   long   countScoreSamples;   // for averages
   double sumR_wins;
   double sumR_losses;         // negative
   double sumScore_wins;
   double sumScore_losses;
   double sumSpread;
   long   countSpread;
   double sumHoldingSec;
   long   countHolding;
   long   blockedAt[NXS_STATS_BLOCKERS];
};

SNXSStratRow g_stratStats[NXS_STATS_MAX_NAMES];
int          g_stratStatsCount = 0;

datetime g_stats_lastDealTime   = 0;
ulong    g_stats_lastDealTicket = 0;
datetime g_stats_lastExportTime = 0;
datetime g_stats_sessionStart   = 0;

//+------------------------------------------------------------------+
//| Lookup / create row                                               |
//+------------------------------------------------------------------+
int _nxs_stats_idx(string name){
   for(int i = 0; i < g_stratStatsCount; i++)
      if(g_stratStats[i].name == name) return i;
   if(g_stratStatsCount >= NXS_STATS_MAX_NAMES) return -1;
   int idx = g_stratStatsCount;
   ZeroMemory(g_stratStats[idx]);
   g_stratStats[idx].name    = name;
   g_stratStats[idx].enabled = true;
   g_stratStatsCount++;
   return idx;
}

//+------------------------------------------------------------------+
//| Public recorders                                                  |
//+------------------------------------------------------------------+
void NXS_Stats_SetEnabled(string name, bool en){
   int i = _nxs_stats_idx(name); if(i < 0) return;
   g_stratStats[i].enabled = en;
}

void NXS_Stats_RecordCalled(string name){
   int i = _nxs_stats_idx(name); if(i < 0) return;
   g_stratStats[i].called++;
}

void NXS_Stats_RecordSetup(string name){
   int i = _nxs_stats_idx(name); if(i < 0) return;
   g_stratStats[i].setupDetected++;
   g_stratStats[i].signalsProduced++;
}

void NXS_Stats_RecordScoreSample(string name,
                                  double baseScore, double finalScore, double threshold){
   int i = _nxs_stats_idx(name); if(i < 0) return;
   g_stratStats[i].sumScoreBase    += baseScore;
   g_stratStats[i].sumScoreFinal   += finalScore;
   g_stratStats[i].sumThreshold    += threshold;
   g_stratStats[i].countScoreSamples++;
}

void NXS_Stats_RecordBlock(string name, int blockerCode){
   int i = _nxs_stats_idx(name); if(i < 0) return;
   if(blockerCode < 0 || blockerCode >= NXS_STATS_BLOCKERS) return;
   g_stratStats[i].blockedAt[blockerCode]++;
}

void NXS_Stats_RecordSLTPInvalid(string name){
   int i = _nxs_stats_idx(name); if(i < 0) return;
   g_stratStats[i].sltp_invalid++;
}

void NXS_Stats_RecordExec(string name, double finalScore, double spreadPts){
   int i = _nxs_stats_idx(name); if(i < 0) return;
   g_stratStats[i].executed++;
   if(spreadPts > 0){
      g_stratStats[i].sumSpread += spreadPts;
      g_stratStats[i].countSpread++;
   }
}

void NXS_Stats_RecordOutcome(string name, double pnlR, double scoreUsed, double holdSec){
   int i = _nxs_stats_idx(name); if(i < 0) return;
   if(holdSec > 0){
      g_stratStats[i].sumHoldingSec += holdSec;
      g_stratStats[i].countHolding++;
   }
   if(pnlR > 0.05){
      g_stratStats[i].wins++;
      g_stratStats[i].sumR_wins     += pnlR;
      g_stratStats[i].sumScore_wins += scoreUsed;
   } else if(pnlR < -0.05){
      g_stratStats[i].losses++;
      g_stratStats[i].sumR_losses     += pnlR;
      g_stratStats[i].sumScore_losses += scoreUsed;
   } else {
      g_stratStats[i].breakeven++;
   }
}

//+------------------------------------------------------------------+
//| Trade comment parsing & R calc                                    |
//+------------------------------------------------------------------+
bool _nxs_stats_parseComment(string cm, string &outName, double &outScore){
   int p1 = StringFind(cm, "|", 0);
   if(p1 < 0) return false;
   int p2 = StringFind(cm, "|", p1 + 1);
   if(p2 < 0){
      outName  = StringSubstr(cm, p1 + 1);
      outScore = 0;
      return (StringLen(outName) > 0);
   }
   outName  = StringSubstr(cm, p1 + 1, p2 - p1 - 1);
   outScore = StringToDouble(StringSubstr(cm, p2 + 1));
   return (StringLen(outName) > 0);
}

double _nxs_stats_dealR(ulong dealTicket){
   double profit = HistoryDealGetDouble(dealTicket, DEAL_PROFIT);
   double comm   = HistoryDealGetDouble(dealTicket, DEAL_COMMISSION);
   double swap   = HistoryDealGetDouble(dealTicket, DEAL_SWAP);
   double net    = profit + comm + swap;
   long posId    = HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID);
   double openP=0, slP=0, lots=HistoryDealGetDouble(dealTicket, DEAL_VOLUME);
   int total = HistoryDealsTotal();
   for(int k = 0; k < total; k++){
      ulong dt = HistoryDealGetTicket(k);
      if(HistoryDealGetInteger(dt, DEAL_POSITION_ID) != posId) continue;
      if(HistoryDealGetInteger(dt, DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
      openP = HistoryDealGetDouble(dt, DEAL_PRICE);
      slP   = HistoryDealGetDouble(dt, DEAL_SL);
      lots  = HistoryDealGetDouble(dt, DEAL_VOLUME);
      break;
   }
   double riskMoney = 0;
   if(openP > 0 && slP > 0 && lots > 0){
      double tickV  = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_VALUE);
      double tickSz = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_SIZE);
      if(tickSz > 0){
         double dist = MathAbs(openP - slP);
         riskMoney = (dist / tickSz) * tickV * lots;
      }
   }
   if(riskMoney > 0) return net / riskMoney;
   if(net > 0)  return 1.0;
   if(net < 0)  return -1.0;
   return 0.0;
}

double _nxs_stats_dealHoldSec(ulong outTicket){
   long posId = HistoryDealGetInteger(outTicket, DEAL_POSITION_ID);
   datetime tOut = (datetime)HistoryDealGetInteger(outTicket, DEAL_TIME);
   int total = HistoryDealsTotal();
   for(int k = 0; k < total; k++){
      ulong dt = HistoryDealGetTicket(k);
      if(HistoryDealGetInteger(dt, DEAL_POSITION_ID) != posId) continue;
      if(HistoryDealGetInteger(dt, DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
      datetime tIn = (datetime)HistoryDealGetInteger(dt, DEAL_TIME);
      return (double)((long)tOut - (long)tIn);
   }
   return 0.0;
}

void NXS_Stats_ProcessClosedTrades(){
   if(!HistorySelect(g_stats_sessionStart, TimeCurrent())) return;
   int total = HistoryDealsTotal();
   for(int k = 0; k < total; k++){
      ulong dt = HistoryDealGetTicket(k);
      datetime dtime = (datetime)HistoryDealGetInteger(dt, DEAL_TIME);
      if(dtime < g_stats_lastDealTime) continue;
      if(dtime == g_stats_lastDealTime && dt <= g_stats_lastDealTicket) continue;
      long entry = HistoryDealGetInteger(dt, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY) continue;
      string sym = HistoryDealGetString(dt, DEAL_SYMBOL);
      if(sym != g_sym){ g_stats_lastDealTime = dtime; g_stats_lastDealTicket = dt; continue; }
      long posId = HistoryDealGetInteger(dt, DEAL_POSITION_ID);
      string stratName=""; double scoreUsed=0;
      bool found = false;
      int n2 = HistoryDealsTotal();
      for(int j = 0; j < n2; j++){
         ulong dt2 = HistoryDealGetTicket(j);
         if(HistoryDealGetInteger(dt2, DEAL_POSITION_ID) != posId) continue;
         if(HistoryDealGetInteger(dt2, DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
         string cm2 = HistoryDealGetString(dt2, DEAL_COMMENT);
         if(_nxs_stats_parseComment(cm2, stratName, scoreUsed)) found = true;
         break;
      }
      if(found){
         double R    = _nxs_stats_dealR(dt);
         double hold = _nxs_stats_dealHoldSec(dt);
         NXS_Stats_RecordOutcome(stratName, R, scoreUsed, hold);
      }
      g_stats_lastDealTime   = dtime;
      g_stats_lastDealTicket = dt;
   }
}

//+------------------------------------------------------------------+
//| Health classifier (7 states)                                      |
//+------------------------------------------------------------------+
string NXS_Stats_Health(int idx){
   SNXSStratRow r = g_stratStats[idx];
   if(!r.enabled)        return "NOT_CONNECTED";
   if(r.called == 0)     return "NOT_CONNECTED";
   if(r.setupDetected == 0) return "NO_SETUP_FOUND";
   long blockTotal = 0; long blockScore = 0;
   for(int b = 1; b < NXS_STATS_BLOCKERS; b++) blockTotal += r.blockedAt[b];
   blockScore = r.blockedAt[9]; // SCORE_BELOW
   if(r.executed == 0){
      if(blockScore > blockTotal * 0.6 && blockScore > 0) return "LOW_SCORE_ONLY";
      if(r.sltp_invalid > 0 && r.sltp_invalid >= r.setupDetected/2) return "EXECUTION_PROBLEM";
      if(blockTotal > 0) return "BLOCKED_BY_GATE";
      return "NEEDS_REVIEW";
   }
   long closed = r.wins + r.losses;
   if(closed < 10) return "NEEDS_REVIEW";
   double pf = (r.sumR_losses < 0) ? r.sumR_wins / MathAbs(r.sumR_losses)
                                   : (r.sumR_wins > 0 ? 99.0 : 0.0);
   if(pf < 1.0) return "NEEDS_REVIEW";
   return "HEALTHY";
}

//+------------------------------------------------------------------+
//| CSV Export                                                        |
//+------------------------------------------------------------------+
string _nxs_stats_csvName(){
   return StringFormat("%s\\nexus_stats_%s_%s.csv",
                       NXS_STATS_FOLDER, g_sym, EnumToString(InpTFEntry));
}

string _nxs_stats_jsonName(){
   return StringFormat("%s\\nexus_stats_%s_%s.json",
                       NXS_STATS_FOLDER, g_sym, EnumToString(InpTFEntry));
}

string _nxs_stats_mdName(){
   return StringFormat("%s\\nexus_stats_%s_%s.md",
                       NXS_STATS_FOLDER, g_sym, EnumToString(InpTFEntry));
}

void NXS_Stats_ExportCSV(){
   string fn = _nxs_stats_csvName();
   int fh = FileOpen(fn, FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   if(fh == INVALID_HANDLE){
      PrintFormat("[NXS Stats] cannot open %s err=%d", fn, GetLastError());
      return;
   }
   FileWrite(fh,
      "name","enabled","called","setup","signals","executed","sltp_invalid",
      "wins","losses","breakeven","winrate_pct","expectancy_R","profit_factor",
      "avg_R_win","avg_R_loss","avg_score_win","avg_score_loss",
      "avg_score_base","avg_score_final","avg_threshold",
      "avg_spread_pts","avg_holding_sec",
      "blk_NONE","blk_NO_SIGNAL","blk_COOLDOWN","blk_MTF","blk_HTF","blk_VELOCITY",
      "blk_NEWS","blk_SPREAD","blk_PROTECTIONS","blk_SCORE_BELOW","blk_PREFLIGHT",
      "blk_LICENSE","blk_PAUSED","blk_SEND_FAILED",
      "dominant_blocker","reachability_pct","exec_rate_pct","health"
   );
   for(int i = 0; i < g_stratStatsCount; i++){
      SNXSStratRow r = g_stratStats[i];
      double wr  = (r.wins + r.losses > 0) ? 100.0 * r.wins / (r.wins + r.losses) : 0.0;
      double avgW = (r.wins > 0)   ? r.sumR_wins / r.wins     : 0.0;
      double avgL = (r.losses > 0) ? r.sumR_losses / r.losses : 0.0;
      double exp  = (r.wins + r.losses > 0)
                    ? (r.sumR_wins + r.sumR_losses) / (r.wins + r.losses) : 0.0;
      double pf   = (r.sumR_losses < 0) ? r.sumR_wins / MathAbs(r.sumR_losses)
                                        : (r.sumR_wins > 0 ? 99.0 : 0.0);
      double avgSW = (r.wins > 0)   ? r.sumScore_wins / r.wins     : 0.0;
      double avgSL = (r.losses > 0) ? r.sumScore_losses / r.losses : 0.0;
      double avgSB = (r.countScoreSamples > 0) ? r.sumScoreBase  / r.countScoreSamples : 0.0;
      double avgSF = (r.countScoreSamples > 0) ? r.sumScoreFinal / r.countScoreSamples : 0.0;
      double avgTh = (r.countScoreSamples > 0) ? r.sumThreshold  / r.countScoreSamples : 0.0;
      double avgSp = (r.countSpread  > 0) ? r.sumSpread     / r.countSpread  : 0.0;
      double avgHd = (r.countHolding > 0) ? r.sumHoldingSec / r.countHolding : 0.0;
      int domIdx = 0; long domVal = 0;
      for(int b = 1; b < NXS_STATS_BLOCKERS; b++)
         if(r.blockedAt[b] > domVal){ domVal = r.blockedAt[b]; domIdx = b; }
      double reach = (r.called > 0)        ? 100.0 * r.setupDetected / r.called : 0.0;
      double execR = (r.setupDetected > 0) ? 100.0 * r.executed / r.setupDetected : 0.0;
      string health = NXS_Stats_Health(i);

      FileWrite(fh,
         r.name,
         (r.enabled ? "1" : "0"),
         (string)r.called, (string)r.setupDetected, (string)r.signalsProduced,
         (string)r.executed, (string)r.sltp_invalid,
         (string)r.wins, (string)r.losses, (string)r.breakeven,
         DoubleToString(wr,2), DoubleToString(exp,3), DoubleToString(pf,2),
         DoubleToString(avgW,3), DoubleToString(avgL,3),
         DoubleToString(avgSW,1), DoubleToString(avgSL,1),
         DoubleToString(avgSB,1), DoubleToString(avgSF,1), DoubleToString(avgTh,1),
         DoubleToString(avgSp,1), DoubleToString(avgHd,0),
         (string)r.blockedAt[0], (string)r.blockedAt[1], (string)r.blockedAt[2],
         (string)r.blockedAt[3], (string)r.blockedAt[4], (string)r.blockedAt[5],
         (string)r.blockedAt[6], (string)r.blockedAt[7], (string)r.blockedAt[8],
         (string)r.blockedAt[9], (string)r.blockedAt[10], (string)r.blockedAt[11],
         (string)r.blockedAt[12], (string)r.blockedAt[13],
         IntegerToString(domIdx),
         DoubleToString(reach,2), DoubleToString(execR,2),
         health
      );
   }
   FileClose(fh);
   PrintFormat("[NXS Stats] CSV exported (%d strategies) -> %s", g_stratStatsCount, fn);
}

//+------------------------------------------------------------------+
//| Build JSON payload (string) - used both for export and for push   |
//+------------------------------------------------------------------+
string NXS_Stats_BuildJSON(){
   string j = "{\n  \"symbol\":\"" + g_sym + "\",\n";
   j += "  \"timeframe\":\"" + EnumToString(InpTFEntry) + "\",\n";
   j += "  \"session_start\":\"" + TimeToString(g_stats_sessionStart, TIME_DATE|TIME_SECONDS) + "\",\n";
   j += "  \"generated_at\":\""  + TimeToString(TimeCurrent(),        TIME_DATE|TIME_SECONDS) + "\",\n";
   j += "  \"strategies\":[\n";
   for(int i = 0; i < g_stratStatsCount; i++){
      SNXSStratRow r = g_stratStats[i];
      if(i > 0) j += ",\n";
      j += "    {\"name\":\"" + r.name + "\",";
      j += "\"enabled\":" + (r.enabled?"true":"false") + ",";
      j += "\"called\":"   + IntegerToString(r.called) + ",";
      j += "\"setup\":"    + IntegerToString(r.setupDetected) + ",";
      j += "\"signals\":"  + IntegerToString(r.signalsProduced) + ",";
      j += "\"executed\":" + IntegerToString(r.executed) + ",";
      j += "\"sltp_invalid\":" + IntegerToString(r.sltp_invalid) + ",";
      j += "\"wins\":"     + IntegerToString(r.wins) + ",";
      j += "\"losses\":"   + IntegerToString(r.losses) + ",";
      j += "\"breakeven\":"+ IntegerToString(r.breakeven) + ",";
      j += "\"sumR_wins\":"   + DoubleToString(r.sumR_wins, 4) + ",";
      j += "\"sumR_losses\":" + DoubleToString(r.sumR_losses, 4) + ",";
      j += "\"sumScore_wins\":"   + DoubleToString(r.sumScore_wins, 2) + ",";
      j += "\"sumScore_losses\":" + DoubleToString(r.sumScore_losses, 2) + ",";
      j += "\"sumScoreBase\":"  + DoubleToString(r.sumScoreBase, 2) + ",";
      j += "\"sumScoreFinal\":" + DoubleToString(r.sumScoreFinal, 2) + ",";
      j += "\"sumThreshold\":"  + DoubleToString(r.sumThreshold,  2) + ",";
      j += "\"countScoreSamples\":" + IntegerToString(r.countScoreSamples) + ",";
      j += "\"sumSpread\":"      + DoubleToString(r.sumSpread, 2)     + ",";
      j += "\"countSpread\":"    + IntegerToString(r.countSpread)     + ",";
      j += "\"sumHoldingSec\":"  + DoubleToString(r.sumHoldingSec, 0) + ",";
      j += "\"countHolding\":"   + IntegerToString(r.countHolding)    + ",";
      j += "\"health\":\""       + NXS_Stats_Health(i) + "\",";
      j += "\"blocked\":[";
      for(int b = 0; b < NXS_STATS_BLOCKERS; b++){
         if(b > 0) j += ",";
         j += IntegerToString(r.blockedAt[b]);
      }
      j += "]}";
   }
   j += "\n  ]\n}\n";
   return j;
}

//+------------------------------------------------------------------+
//| JSON Export (file)                                                |
//+------------------------------------------------------------------+
void NXS_Stats_ExportJSON(){
   string fn = _nxs_stats_jsonName();
   int fh = FileOpen(fn, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(fh == INVALID_HANDLE) return;
   string j = NXS_Stats_BuildJSON();
   FileWriteString(fh, j);
   FileClose(fh);
}

//+------------------------------------------------------------------+
//| WebRequest push to backend (LIVE/Demo only, NOT tester)           |
//| Endpoint: POST {InpWebURL}/api/ea/strategy_stats                  |
//| Auth:     X-Nexus-Token: {InpWebToken}                            |
//+------------------------------------------------------------------+
void NXS_Stats_PushToBackend(){
   if(MQLInfoInteger(MQL_TESTER)) return;        // WebRequest disabled in tester
   if(!InpEnableWebSync) return;
   if(StringLen(InpWebURL) == 0) return;
   string body = NXS_Stats_BuildJSON();
   string url  = InpWebURL + "/api/ea/strategy_stats";
   char post[]; StringToCharArray(body, post, 0, -1, CP_UTF8);
   ArrayResize(post, ArraySize(post) - 1);
   char result[]; string headersOut;
   string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";
   int code = WebRequest("POST", url, headers, 5000, post, result, headersOut);
   if(code < 0){
      static int failCount = 0;
      if(failCount < 3){
         PrintFormat("[NXS Stats] PUSH FAILED code=%d err=%d url=%s >>> Check: MT5 Tools→Options→Expert Advisors→Allow WebRequest URL contains '%s'.",
                     code, GetLastError(), url, InpWebURL);
         failCount++;
      }
   } else if(code != 200){
      string resp = CharArrayToString(result, 0, MathMin(ArraySize(result), 300), CP_UTF8);
      PrintFormat("[NXS Stats] PUSH HTTP %d resp=%s", code, resp);
   } else {
      PrintFormat("[NXS Stats] PUSH OK (%d strategies)", g_stratStatsCount);
   }
}

//+------------------------------------------------------------------+
//| Markdown Report                                                   |
//+------------------------------------------------------------------+
void NXS_Stats_ExportMD(){
   string fn = _nxs_stats_mdName();
   int fh = FileOpen(fn, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(fh == INVALID_HANDLE) return;
   string m = "# NEXUS Strategy Analytics Report\n\n";
   m += "**Symbol:** " + g_sym + "  \n";
   m += "**Timeframe:** " + EnumToString(InpTFEntry) + "  \n";
   m += "**Session start:** " + TimeToString(g_stats_sessionStart, TIME_DATE|TIME_SECONDS) + "  \n";
   m += "**Generated:** " + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "  \n\n";
   m += "## Strategy Health Status\n\n";
   m += "| Strategy | Health | Called | Setup | Exec | Win | Loss | PF | Expe(R) |\n";
   m += "|----------|--------|-------:|------:|-----:|----:|-----:|----|--------:|\n";
   for(int i = 0; i < g_stratStatsCount; i++){
      SNXSStratRow r = g_stratStats[i];
      double pf = (r.sumR_losses < 0) ? r.sumR_wins / MathAbs(r.sumR_losses)
                                      : (r.sumR_wins > 0 ? 99.0 : 0.0);
      double exp = (r.wins + r.losses > 0)
                   ? (r.sumR_wins + r.sumR_losses) / (r.wins + r.losses) : 0.0;
      m += "| " + r.name + " | " + NXS_Stats_Health(i) + " | ";
      m += (string)r.called + " | " + (string)r.setupDetected + " | " + (string)r.executed + " | ";
      m += (string)r.wins + " | " + (string)r.losses + " | ";
      m += DoubleToString(pf,2) + " | " + DoubleToString(exp,2) + " |\n";
   }
   FileWriteString(fh, m);
   FileClose(fh);
}

//+------------------------------------------------------------------+
//| Init / Periodic / Deinit                                          |
//+------------------------------------------------------------------+
void NXS_Stats_Init(){
   g_stats_sessionStart   = TimeCurrent();
   g_stats_lastDealTime   = g_stats_sessionStart;
   g_stats_lastDealTicket = 0;
   g_stats_lastExportTime = 0;
   g_stratStatsCount      = 0;
   string known[] = {
      "ADX_RSI","BOLLINGER","MACD","SAR","TSI","BJORGUM","LIQ_SWEEP","FVG_CONT",
      "BREAKOUT_ACC","LONDON_BO","EMA_PULLBACK","BB_SQUEEZE","ICHIMOKU","RSI_DIV",
      "ORDER_BLOCK","STRUCT_REACT",
      "TURTLE_SOUP","IFVG","FVG_MIT","OB_MIT","SH_BMS_RTO","SMS_BMS_RTO",
      "SILVER_BULLET","AMD_REVERSAL","OTE_CONT","MALAYSIAN_SNR",
      // v2.0.7 institutional
      "CISD","AMD_CONT","JUDAS_SWING","LDN_REVERSAL","NY_REVERSAL",
      "WEEKLY_EXP","PO3","LIQ_VOID","DISP_REBAL",
      // v2.0.8
      "RANGE_FADE"
   };
   for(int i = 0; i < ArraySize(known); i++) _nxs_stats_idx(known[i]);
   // v2.0.7b: sync ALL classic strategies (was missing — defaulted to enabled=true regardless of toggle)
   NXS_Stats_SetEnabled("ADX_RSI",        InpStrat_ADX_RSI);
   NXS_Stats_SetEnabled("BOLLINGER",      InpStrat_BOLLINGER);
   NXS_Stats_SetEnabled("MACD",           InpStrat_MACD);
   NXS_Stats_SetEnabled("SAR",            InpStrat_SAR);
   NXS_Stats_SetEnabled("TSI",            InpStrat_TSI);
   NXS_Stats_SetEnabled("BJORGUM",        InpStrat_BJORGUM);
   NXS_Stats_SetEnabled("LIQ_SWEEP",      InpStrat_LIQ_SWEEP);
   NXS_Stats_SetEnabled("FVG_CONT",       InpStrat_FVG_CONT);
   NXS_Stats_SetEnabled("BREAKOUT_ACC",   InpStrat_BREAKOUT_ACC);
   NXS_Stats_SetEnabled("LONDON_BO",      InpStrat_LONDON_BO);
   NXS_Stats_SetEnabled("EMA_PULLBACK",   InpStrat_EMA_PULLBACK);
   NXS_Stats_SetEnabled("BB_SQUEEZE",     InpStrat_BB_SQUEEZE);
   NXS_Stats_SetEnabled("ICHIMOKU",       InpStrat_ICHIMOKU);
   NXS_Stats_SetEnabled("RSI_DIV",        InpStrat_RSI_DIV);
   NXS_Stats_SetEnabled("ORDER_BLOCK",    InpStrat_ORDER_BLOCK);
   // Mark SMC strategies enabled/disabled based on inputs
   NXS_Stats_SetEnabled("TURTLE_SOUP",    InpStrat_TurtleSoup);
   NXS_Stats_SetEnabled("IFVG",           InpStrat_IFVG);
   NXS_Stats_SetEnabled("FVG_MIT",        InpStrat_FVG_Mit);
   NXS_Stats_SetEnabled("OB_MIT",         InpStrat_OB_Mit);
   NXS_Stats_SetEnabled("SH_BMS_RTO",     InpStrat_SH_BMS_RTO);
   NXS_Stats_SetEnabled("SMS_BMS_RTO",    InpStrat_SMS_BMS_RTO);
   NXS_Stats_SetEnabled("SILVER_BULLET",  InpStrat_SilverBullet);
   NXS_Stats_SetEnabled("AMD_REVERSAL",   InpStrat_AMD_Reversal);
   NXS_Stats_SetEnabled("OTE_CONT",       InpStrat_OTE_Cont);
   NXS_Stats_SetEnabled("MALAYSIAN_SNR",  InpStrat_MalaysianSNR);
   // v2.0.6: sync STRUCT_REACT toggle (was missing — used InpUseStructReact path)
   NXS_Stats_SetEnabled("STRUCT_REACT",   InpUseStructReact);
   // v2.0.7: sync institutional toggles
   NXS_Stats_SetEnabled("CISD",          InpUseStrat_CISD);
   NXS_Stats_SetEnabled("AMD_CONT",      InpUseStrat_AMD_Cont);
   NXS_Stats_SetEnabled("JUDAS_SWING",   InpUseStrat_Judas);
   NXS_Stats_SetEnabled("LDN_REVERSAL",  InpUseStrat_LdnReversal);
   NXS_Stats_SetEnabled("NY_REVERSAL",   InpUseStrat_NYReversal);
   NXS_Stats_SetEnabled("WEEKLY_EXP",    InpUseStrat_WeeklyExp);
   NXS_Stats_SetEnabled("PO3",           InpUseStrat_PO3);
   NXS_Stats_SetEnabled("LIQ_VOID",      InpUseStrat_LiqVoid);
   NXS_Stats_SetEnabled("DISP_REBAL",    InpUseStrat_DispRebal);
   // v2.0.8: Range Fade
   NXS_Stats_SetEnabled("RANGE_FADE",    InpUseStrat_RangeFade);
   // Ensure subfolder exists by attempting a write
   string seed = StringFormat("%s\\.keep", NXS_STATS_FOLDER);
   int fh = FileOpen(seed, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(fh != INVALID_HANDLE){ FileWriteString(fh, "NEXUS stats folder"); FileClose(fh); }
}

void NXS_Stats_OnTick(int exportEverySec){
   NXS_Stats_ProcessClosedTrades();
   if(exportEverySec <= 0) return;
   if(TimeCurrent() - g_stats_lastExportTime >= exportEverySec){
      NXS_Stats_ExportCSV();
      NXS_Stats_ExportJSON();
      NXS_Stats_ExportMD();
      if(InpStatsPushToBackend) NXS_Stats_PushToBackend();
      g_stats_lastExportTime = TimeCurrent();
   }
}

void NXS_Stats_Deinit(){
   NXS_Stats_ProcessClosedTrades();
   NXS_Stats_ExportCSV();
   NXS_Stats_ExportJSON();
   NXS_Stats_ExportMD();
   PrintFormat("[NXS Stats] deinit final export complete (n=%d)", g_stratStatsCount);
}

//+------------------------------------------------------------------+
//| Visual Suite mini-panel data (read-only getters)                  |
//+------------------------------------------------------------------+
int NXS_Stats_Count(){ return g_stratStatsCount; }
string NXS_Stats_NameAt(int i){ return (i>=0 && i<g_stratStatsCount) ? g_stratStats[i].name : ""; }
long   NXS_Stats_CalledAt(int i){ return (i>=0 && i<g_stratStatsCount) ? g_stratStats[i].called : 0; }
long   NXS_Stats_SetupAt(int i){  return (i>=0 && i<g_stratStatsCount) ? g_stratStats[i].setupDetected : 0; }
long   NXS_Stats_ExecAt(int i){   return (i>=0 && i<g_stratStatsCount) ? g_stratStats[i].executed : 0; }
string NXS_Stats_HealthAt(int i){ return (i>=0 && i<g_stratStatsCount) ? NXS_Stats_Health(i) : ""; }

#endif
