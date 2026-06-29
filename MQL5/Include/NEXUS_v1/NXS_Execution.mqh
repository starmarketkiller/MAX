//+------------------------------------------------------------------+
//|  NXS_Execution.mqh - Open trades with gates + Close & Reverse     |
//|  AUDITPATCH: precise preflight RC, GateMode, Counter-HTF sizing    |
//+------------------------------------------------------------------+
#ifndef __NXS_EXECUTION_MQH__
#define __NXS_EXECUTION_MQH__

enum ENUM_NXS_OPEN_RC {
   OPEN_OK = 0,
   OPEN_FAIL_INVALID_STOPS,
   OPEN_FAIL_INVALID_VOLUME,
   OPEN_FAIL_PREFLIGHT,
   OPEN_FAIL_SEND
};

string g_nxsLastOpenFailure = "";
int g_nxsCounterSessionKey = -1;
datetime g_nxsCounterDay = 0;
int g_nxsCounterCount = 0;

void NXS_CounterSessionRollover(){
   MqlDateTime mt; TimeToStruct(TimeCurrent(), mt);
   mt.hour = 0; mt.min = 0; mt.sec = 0;
   datetime day = StructToTime(mt);
   int sess = (int)g_session;
   if(day != g_nxsCounterDay || sess != g_nxsCounterSessionKey){
      g_nxsCounterDay = day;
      g_nxsCounterSessionKey = sess;
      g_nxsCounterCount = 0;
   }
}

bool NXS_IsCounterHTFDirection(ENUM_NXS_DIR dir, SNXSHTF &htf){
   return (dir == DIR_BUY  && htf.bias == HTF_BEAR) ||
          (dir == DIR_SELL && htf.bias == HTF_BULL);
}

bool NXS_IsCounterHTFPriceActionStrategy(string name){
   return (name == "BOLLINGER" || name == "RSI_DIV" || name == "BJORGUM" ||
           name == "BB_SQUEEZE" || name == "LIQ_SWEEP" || name == "FVG_MIT" ||
           name == "IFVG" || name == "OB_MIT" || name == "ORDER_BLOCK" ||
           name == "STRUCT_REACT" || name == "TURTLE_SOUP" ||
           name == "SH_BMS_RTO" || name == "SMS_BMS_RTO" ||
           name == "SILVER_BULLET" || name == "AMD_REVERSAL" ||
           name == "MALAYSIAN_SNR" || name == "CISD" || name == "JUDAS_SWING" ||
           name == "LDN_REVERSAL" || name == "NY_REVERSAL" || name == "PO3" ||
           name == "DISP_REBAL" || name == "RANGE_FADE");
}

bool NXS_CounterHTFSoftEligible(SNXSSignal &sig, SNXSHTF &htf){
   if(!InpEnableCounterHTFSoft) return false;
   if(!NXS_IsCounterHTFDirection(sig.dir, htf)) return false;
   if(!NXS_IsCounterHTFPriceActionStrategy(sig.stratName)) return false;
   int d = (sig.dir == DIR_BUY) ? +1 : -1;
   if(!g_reaction.detected || g_reaction.direction != d) return false;
   if(g_reaction.quality < InpCounterHTF_MinReactQ) return false;
   NXS_CounterSessionRollover();
   if(InpCounterHTF_MaxPerSession > 0 && g_nxsCounterCount >= InpCounterHTF_MaxPerSession)
      return false;
   return true;
}

void NXS_ApplyCounterHTFProfile(SNXSSignal &sig){
   double atr = (g_atr > 0 ? g_atr : g_point * 100.0);
   double entry = (sig.dir == DIR_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_ASK)
                                       : SymbolInfoDouble(g_sym, SYMBOL_BID);
   sig.entryRef = entry;
   double slMult = MathMax(0.1, InpCounterHTF_SLATR);
   double minRR  = MathMax(0.1, InpCounterHTF_MinRR);
   if(sig.dir == DIR_BUY){
      sig.slPrice = entry - slMult * atr;
      double target = entry + minRR * (entry - sig.slPrice);
      if(sig.tpPrice <= entry || sig.tpPrice < target) sig.tpPrice = target;
   } else {
      sig.slPrice = entry + slMult * atr;
      double target = entry - minRR * (sig.slPrice - entry);
      if(sig.tpPrice >= entry || sig.tpPrice > target) sig.tpPrice = target;
   }
}

ENUM_NXS_OPEN_RC NXS_OpenTrade(SNXSSignal &sig, long magic, double lotMult){
   g_nxsLastOpenFailure = "";
   double sl = sig.slPrice, tp = sig.tpPrice;
   double slDist = MathAbs(sig.entryRef - sl);
   if(slDist <= 0){ g_nxsLastOpenFailure = "invalid_sl_distance"; return OPEN_FAIL_INVALID_STOPS; }

   double lots = NXS_CalcLot(slDist);
   if(lots <= 0){ g_nxsLastOpenFailure = "lot_calc_zero"; return OPEN_FAIL_INVALID_VOLUME; }
   lots *= MathMax(0.01, lotMult);

   // Re-align volume after a Counter-HTF risk multiplier.
   double step = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
   if(step <= 0) step = 0.01;
   lots = MathFloor(lots / step) * step;
   lots = NormalizeDouble(lots, 8);
   lots = NXS_License_CapLot(lots);

   ENUM_ORDER_TYPE otype = (sig.dir == DIR_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double refPrice = (sig.dir == DIR_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_ASK)
                                          : SymbolInfoDouble(g_sym, SYMBOL_BID);
   string pfReason = "";
   if(!NXS_PreFlight(otype, lots, refPrice, sl, tp, pfReason)){
      g_nxsLastOpenFailure = pfReason;
      PrintFormat("[NEXUS] OPEN BLOCKED preflight: %s strat=%s", pfReason, sig.stratName);
      return OPEN_FAIL_PREFLIGHT;
   }

   // Persist broker-adjusted/tick-normalized values for logging and management.
   sig.slPrice = sl;
   sig.tpPrice = tp;

   NXS_TradeSetMagic(magic);
   string cm = StringFormat("%s|%s|%.1f", InpComment, sig.stratName, sig.score);
   bool ok = false;
   if(sig.dir == DIR_BUY)       ok = NXS_SafeBuy(lots, g_sym, sl, tp, cm);
   else if(sig.dir == DIR_SELL) ok = NXS_SafeSell(lots, g_sym, sl, tp, cm);

   if(ok){
      g_tradesToday++;
      g_lastTradeTime = TimeCurrent();
      PrintFormat("[NEXUS] OPEN %s %s lots=%.4f sl=%.5f tp=%.5f score=%.1f reason=%s",
                  NXS_DirName(sig.dir), sig.stratName, lots, sl, tp, sig.score, sig.reason);
      NXS_Notify_TradeOpen(sig.stratName, NXS_DirName(sig.dir), lots, refPrice, sig.score);
      return OPEN_OK;
   }

   g_nxsLastOpenFailure = StringFormat("order_send_retcode=%u", NXS_TradeRetcode());
   NXS_Diag_TradeFail(sig.stratName, (int)sig.dir, lots, refPrice, (int)NXS_TradeRetcode());
   return OPEN_FAIL_SEND;
}

void NXS_CloseOppositeIfBetter(ENUM_NXS_DIR newDir, double newScore){
   if(!InpEnableCloseReverse) return;
   if(newScore < InpMinScoreReverse) return;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsCoreMagic(mg)) continue;
      long ptype = PositionGetInteger(POSITION_TYPE);
      bool oppToBuy  = (newDir == DIR_BUY  && ptype == POSITION_TYPE_SELL);
      bool oppToSell = (newDir == DIR_SELL && ptype == POSITION_TYPE_BUY);
      if(!(oppToBuy || oppToSell)) continue;
      double profit = PositionGetDouble(POSITION_PROFIT);
      if(profit > 0) continue;
      NXS_DoClose(t);
      PrintFormat("[NEXUS] Close&Reverse closing %I64u", t);
   }
}

// v2.0.13 — Smart Close & Reverse: dynamic threshold based on reaction + HTF
void NXS_SmartCloseOppositeIfBetter(ENUM_NXS_DIR newDir, double newScore, SNXSHTF &htf){
   if(!InpEnableCloseReverse) return;
   double thresholdUsed = InpMinScoreReverse;
   bool ok = false;
   if(InpChainEnableSmartReverse){
      int dirInt = (newDir == DIR_BUY) ? +1 : -1;
      double reactQ = g_reaction.detected ? g_reaction.quality : 0.0;
      ok = NXS_Chain_ShouldSmartReverse(dirInt, newScore, reactQ, htf.bias, thresholdUsed);
   } else {
      ok = (newScore >= thresholdUsed);
   }
   if(!ok) return;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsCoreMagic(mg)) continue;
      long ptype = PositionGetInteger(POSITION_TYPE);
      bool oppToBuy  = (newDir == DIR_BUY  && ptype == POSITION_TYPE_SELL);
      bool oppToSell = (newDir == DIR_SELL && ptype == POSITION_TYPE_BUY);
      if(!(oppToBuy || oppToSell)) continue;
      double profit = PositionGetDouble(POSITION_PROFIT);
      bool allowLossClose = (newScore >= thresholdUsed + 10.0);
      if(profit > 0 || allowLossClose){
         NXS_DoClose(t);
         PrintFormat("[NEXUS] Smart Close&Reverse closing %I64u (score=%.1f thr=%.1f profit=%.2f)",
                     t, newScore, thresholdUsed, profit);
      }
   }
}

enum ENUM_NXS_EXEC_RC {
   EXEC_OK = 0,
   EXEC_FAIL_NO_DIR,
   EXEC_FAIL_PROTECTIONS,
   EXEC_FAIL_NEWS,
   EXEC_FAIL_HTF,
   EXEC_FAIL_VELOCITY,
   EXEC_FAIL_SCORE_BELOW,
   EXEC_FAIL_INVALID_STOPS,
   EXEC_FAIL_INVALID_VOLUME,
   EXEC_FAIL_PREFLIGHT,
   EXEC_FAIL_ORDER_SEND
};

// GateMode semantics advertised in Inputs are now functional:
// 0 Conservative = never lower global threshold
// 1 Balanced     = session may lower it by at most 5 points
// 2 Discovery    = use the lower of global/session threshold
// 3 DebugTrade   = Discovery threshold minus 10, floor 40
// This does not bypass risk, margin, spread or protection gates.
double NXS_ResolvedEntryThreshold(){
   double globalTh = (double)g_run_MinEntryScore;
   double sessionTh = InpUseSessions ? NXS_SessionMinScore(g_session) : globalTh;
   if(InpGateMode <= 0) return MathMax(globalTh, sessionTh);
   if(InpGateMode == 1) return MathMax(sessionTh, globalTh - 5.0);
   if(InpGateMode == 2) return MathMin(globalTh, sessionTh);
   return MathMax(40.0, MathMin(globalTh, sessionTh) - 10.0);
}

ENUM_NXS_EXEC_RC NXS_TryExecuteRC(SNXSSignal &sig, SNXSAMD &amd, SNXSSweep &sw,
                                  SNXSHTF &htf, SNXSVel &vel, double &finalScoreOut,
                                  double &threshOut){
   finalScoreOut = sig.score; threshOut = 0;
   if(sig.dir == DIR_NONE) return EXEC_FAIL_NO_DIR;

   string r;
   if(!NXS_CheckProtections(r)) return EXEC_FAIL_PROTECTIONS;
   if(NXS_NewsBlocking())       return EXEC_FAIL_NEWS;

   bool rawCounter  = NXS_IsCounterHTFDirection(sig.dir, htf);
   bool counterSoft = NXS_CounterHTFSoftEligible(sig, htf);
   // In Balanced/Conservative, enabling Counter-HTF Soft must not become a
   // blanket bypass: an ineligible counter signal is still rejected here.
   if(rawCounter && InpEnableCounterHTFSoft && !counterSoft && InpGateMode < 2)
      return EXEC_FAIL_HTF;
   if(NXS_HTFBlocks(sig.dir, htf) && !counterSoft) return EXEC_FAIL_HTF;
   if(NXS_VelocityBlocks(sig.dir, vel))            return EXEC_FAIL_VELOCITY;

   if(counterSoft) NXS_ApplyCounterHTFProfile(sig);

   double finalScore = NXS_FinalScore(sig, amd, sw);
   sig.score = finalScore; finalScoreOut = finalScore;
   double thresh = NXS_DynamicScoreThreshold(NXS_ResolvedEntryThreshold());
   thresh = MathMax(thresh, NXS_StrategyMinScoreFloor(sig.stratName));  // v2.0.14
   threshOut = thresh;
   if(finalScore < thresh) return EXEC_FAIL_SCORE_BELOW;

   NXS_SmartCloseOppositeIfBetter(sig.dir, finalScore, htf);
   double lotMult = counterSoft ? MathMax(0.01, InpCounterHTF_LotMult) : 1.0;
   // v2.0.13 — apply chain continuation lot multiplier
   if(g_chainPendingLotMult > 0.0 && g_chainPendingLotMult < 1.0)
      lotMult *= g_chainPendingLotMult;
   g_chainPendingLotMult = 1.0;  // reset
   ENUM_NXS_OPEN_RC openRc = NXS_OpenTrade(sig, InpMagic + MAGIC_CORE, lotMult);
   if(openRc == OPEN_OK){
      if(counterSoft){ NXS_CounterSessionRollover(); g_nxsCounterCount++; }
      return EXEC_OK;
   }
   if(openRc == OPEN_FAIL_INVALID_STOPS)  return EXEC_FAIL_INVALID_STOPS;
   if(openRc == OPEN_FAIL_INVALID_VOLUME) return EXEC_FAIL_INVALID_VOLUME;
   if(openRc == OPEN_FAIL_PREFLIGHT)      return EXEC_FAIL_PREFLIGHT;
   return EXEC_FAIL_ORDER_SEND;
}

bool NXS_TryExecute(SNXSSignal &sig, SNXSAMD &amd, SNXSSweep &sw, SNXSHTF &htf, SNXSVel &vel){
   double f, t;
   return (NXS_TryExecuteRC(sig, amd, sw, htf, vel, f, t) == EXEC_OK);
}

#endif
