//+------------------------------------------------------------------+
//|                                                NEXUS_EA_v2.mq5   |
//|                          Italian Traders Club - NEXUS EA v2.0    |
//|                  Commercial-grade Multi-Symbol EA for MT5         |
//+------------------------------------------------------------------+
#property copyright "Italian Traders Club"
#property link      "https://nexus.local"
#property version   "2.10"
#property strict
#property description "NEXUS EA v2.0 - Commercial-grade adaptive multi-strategy EA"
#property description "Multi-symbol | License-gated | Confluence scoring | Risk Protections"

//+------------------------------------------------------------------+
//| NO dependency on <Trade\Trade.mqh> / <Object.mqh> / <Arrays\*>.   |
//| The EA uses only native MQL5 functions. All trade ops live in    |
//| NXS_Globals.mqh as raw helpers (NXS_DoBuy / NXS_DoSell / ...).   |
//| Compiles on every MT5 build, even when standard library missing. |
//+------------------------------------------------------------------+

#include <NEXUS_v1\NXS_Defines.mqh>
#include <NEXUS_v1\NXS_Inputs.mqh>
#include <NEXUS_v1\NXS_Globals.mqh>
#include <NEXUS_v1\NXS_RuntimeSettings.mqh>
#include <NEXUS_v1\NXS_Presets.mqh>
#include <NEXUS_v1\NXS_SymbolProfile.mqh>
#include <NEXUS_v1\NXS_Risk.mqh>
#include <NEXUS_v1\NXS_Slippage.mqh>
#include <NEXUS_v1\NXS_SafeOrder.mqh>
#include <NEXUS_v1\NXS_State.mqh>
#include <NEXUS_v1\NXS_License.mqh>
#include <NEXUS_v1\NXS_Sessions.mqh>
#include <NEXUS_v1\NXS_NewsFilter.mqh>
#include <NEXUS_v1\NXS_HTFBias.mqh>
#include <NEXUS_v1\NXS_Velocity.mqh>
#include <NEXUS_v1\NXS_AMDModel.mqh>
#include <NEXUS_v1\NXS_Pressure.mqh>
#include <NEXUS_v1\NXS_MarketAnalysis.mqh>
#include <NEXUS_v1\NXS_Structure.mqh>
#include <NEXUS_v1\NXS_StructureMultiLayer.mqh>
#include <NEXUS_v1\NXS_Reaction.mqh>
#include <NEXUS_v1\NXS_FibonacciContext.mqh>
#include <NEXUS_v1\NXS_Strategies.mqh>
#include <NEXUS_v1\NXS_BlockerDiagnostics.mqh>
#include <NEXUS_v1\NXS_Strategies_SMC.mqh>
#include <NEXUS_v1\NXS_Strategies_Institutional.mqh>
#include <NEXUS_v1\NXS_ShadowTrading.mqh>
#include <NEXUS_v1\NXS_EntryScore.mqh>
#include <NEXUS_v1\NXS_Execution.mqh>
#include <NEXUS_v1\NXS_SignalRouter.mqh>
// v2.0.9 — Performance roadmap (Sprint 1+2+3): all auto-active.
#include <NEXUS_v1\NXS_Performance.mqh>
#include <NEXUS_v1\NXS_RiskShield.mqh>
#include <NEXUS_v1\NXS_EdgeAdaptive.mqh>
#include <NEXUS_v1\NXS_Management.mqh>
#include <NEXUS_v1\NXS_GridRecovery.mqh>
#include <NEXUS_v1\NXS_Pyramiding.mqh>
#include <NEXUS_v1\NXS_SplitTrade.mqh>
#include <NEXUS_v1\NXS_Confluence.mqh>
#include <NEXUS_v1\NXS_MTFSpreadVol.mqh>
#include <NEXUS_v1\NXS_Protections.mqh>
#include <NEXUS_v1\NXS_TrailingATR.mqh>
#include <NEXUS_v1\NXS_Notify.mqh>
#include <NEXUS_v1\NXS_Dashboard.mqh>
#include <NEXUS_v1\NXS_HistorySync.mqh>
#include <NEXUS_v1\NXS_Diagnostics.mqh>
#include <NEXUS_v1\NXS_StratStats.mqh>
#include <NEXUS_v1\NXS_WebBridge.mqh>
#include <NEXUS_v1\NXS_VisualBridge.mqh>
#include <NEXUS_v1\NXS_VisualBridgeHTTP.mqh>
#include <NEXUS_v1\NXS_LockedProfile.mqh>
#include <NEXUS_v1\NXS_StrategyChain.mqh>
#include <NEXUS_v1\NXS_Logging.mqh>

//+------------------------------------------------------------------+
//| Indicator handle helpers                                          |
//+------------------------------------------------------------------+
bool NXS_CreateHandles(){
   g_hADX   = iADX(g_sym, InpTFEntry, InpADX_Period);
   g_hRSI   = iRSI(g_sym, InpTFEntry, InpRSI_Period, PRICE_CLOSE);
   g_hBB    = iBands(g_sym, InpTFEntry, InpBB_Period, 0, InpBB_Dev, PRICE_CLOSE);
   g_hMACD  = iMACD(g_sym, InpTFEntry, InpMACD_Fast, InpMACD_Slow, InpMACD_Signal, PRICE_CLOSE);
   g_hSAR   = iSAR(g_sym, InpTFEntry, InpSAR_Step, InpSAR_Max);
   g_hATR   = iATR(g_sym, InpTFEntry, InpATR_Period);
   g_hEMA200= iMA(g_sym, InpTFEntry, InpEMA200_Period, 0, MODE_EMA, PRICE_CLOSE);
   g_hEMA9  = iMA(g_sym, InpTFEntry, InpEMA9_Period,   0, MODE_EMA, PRICE_CLOSE);
   g_hEMA21 = iMA(g_sym, InpTFEntry, InpEMA21_Period,  0, MODE_EMA, PRICE_CLOSE);
   g_hEMA_HTF = iMA(g_sym, InpTFHigh,   InpHTF_EMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_hEMA_MTF = iMA(g_sym, InpTFMedium, InpHTF_EMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_hICHI    = iIchimoku(g_sym, InpTFEntry, 9, 26, 52);

   if(g_hADX == INVALID_HANDLE || g_hRSI == INVALID_HANDLE || g_hBB == INVALID_HANDLE
      || g_hMACD == INVALID_HANDLE || g_hSAR == INVALID_HANDLE || g_hATR == INVALID_HANDLE
      || g_hEMA200 == INVALID_HANDLE || g_hEMA9 == INVALID_HANDLE || g_hEMA21 == INVALID_HANDLE
      || g_hEMA_HTF == INVALID_HANDLE || g_hEMA_MTF == INVALID_HANDLE || g_hICHI == INVALID_HANDLE){
      Print("[NEXUS] Indicator handle creation failed.");
      return false;
   }
   return true;
}

void NXS_ReleaseHandles(){
   int hs[] = { g_hADX,g_hRSI,g_hBB,g_hMACD,g_hSAR,g_hATR,
                g_hEMA200,g_hEMA9,g_hEMA21,g_hEMA_HTF,g_hEMA_MTF,g_hICHI };
   for(int i = 0; i < ArraySize(hs); i++)
      if(hs[i] != INVALID_HANDLE) IndicatorRelease(hs[i]);
}

bool NXS_UpdateIndicators(){
   double a[]; ArraySetAsSeries(a, true);
   if(CopyBuffer(g_hADX, 0, 1, 1, a) <= 0) return false; g_adx = a[0];
   if(CopyBuffer(g_hADX, 1, 1, 1, a) <= 0) return false; g_adxPlus = a[0];
   if(CopyBuffer(g_hADX, 2, 1, 1, a) <= 0) return false; g_adxMinus= a[0];
   if(CopyBuffer(g_hRSI, 0, 1, 1, a) <= 0) return false; g_rsi = a[0];
   if(CopyBuffer(g_hBB, 1, 1, 1, a) <= 0) return false; g_bbUpper = a[0];
   if(CopyBuffer(g_hBB, 2, 1, 1, a) <= 0) return false; g_bbLower = a[0];
   if(CopyBuffer(g_hBB, 0, 1, 1, a) <= 0) return false; g_bbMid   = a[0];
   if(CopyBuffer(g_hMACD, 0, 1, 1, a) <= 0) return false; g_macd    = a[0];
   if(CopyBuffer(g_hMACD, 1, 1, 1, a) <= 0) return false; g_macdSig = a[0];
   if(CopyBuffer(g_hSAR, 0, 1, 1, a) <= 0) return false; g_sar = a[0];
   if(CopyBuffer(g_hATR, 0, 1, 1, a) <= 0) return false; g_atr = a[0];
   double atrArr[];
   if(CopyBuffer(g_hATR, 0, 1, InpATR_AvgPeriod, atrArr) > 0){
      double s = 0; int n = ArraySize(atrArr); for(int k=0;k<n;k++) s += atrArr[k];
      g_atrAvg = (n>0) ? s/n : g_atr;
   } else g_atrAvg = g_atr;
   if(CopyBuffer(g_hEMA200, 0, 1, 1, a) <= 0) return false; g_ema200 = a[0];
   if(CopyBuffer(g_hEMA9,   0, 1, 1, a) <= 0) return false; g_ema9   = a[0];
   if(CopyBuffer(g_hEMA21,  0, 1, 1, a) <= 0) return false; g_ema21  = a[0];
   if(CopyBuffer(g_hICHI, 0, 1, 1, a) <= 0) return false; g_ichiTenkan = a[0];
   if(CopyBuffer(g_hICHI, 1, 1, 1, a) <= 0) return false; g_ichiKijun  = a[0];
   if(CopyBuffer(g_hICHI, 2, 1, 1, a) <= 0) return false; g_ichiSpanA  = a[0];
   if(CopyBuffer(g_hICHI, 3, 1, 1, a) <= 0) return false; g_ichiSpanB  = a[0];
   return true;
}

// NXR reuse/performance pack: include at file scope, after the original
// NXS_UpdateIndicators() definition and before signal/router functions.
#include <NEXUS_v1\NXS_ReusePerformancePack.mqh>

SNXSSignal NXS_PickBestSignal(SNXSSweep &sw){
   SNXSSignal best; ZeroMemory(best);
   SNXSSignal arr[16];
   arr[0]  = NXS_Strat_ADXRSI();
   arr[1]  = NXS_Strat_Bollinger();
   arr[2]  = NXS_Strat_MACD();
   arr[3]  = NXS_Strat_SAR();
   arr[4]  = NXS_Strat_TSI();
   arr[5]  = NXS_Strat_Bjorgum();
   arr[6]  = NXS_Strat_LiqSweep(sw);
   arr[7]  = NXS_Strat_FVG();
   arr[8]  = NXS_Strat_BreakoutAcc();
   arr[9]  = NXS_Strat_LondonBO();
   arr[10] = NXS_Strat_EMAPullback();
   arr[11] = NXS_Strat_BBSqueeze();
   arr[12] = NXS_Strat_Ichimoku();
   arr[13] = NXS_Strat_RSIDiv();
   arr[14] = NXS_Strat_OrderBlock();
   arr[15] = NXS_Strat_StructureReaction();

   NXS_ConfluenceReset();
   for(int i = 0; i < 16; i++){
      if(arr[i].dir == DIR_NONE) continue;
      int d = (arr[i].dir == DIR_BUY) ? +1 : -1;
      NXS_ConfluenceRegister(d);
      arr[i].score = NXS_ApplyScoreCap(arr[i].stratName, arr[i].score);
   }
   for(int i = 0; i < 16; i++){
      if(arr[i].dir == DIR_NONE) continue;
      if(arr[i].score > best.score){ best = arr[i]; }
   }
   if(best.dir != DIR_NONE){
      int wd = (best.dir == DIR_BUY) ? +1 : -1;
      double bonus = (double)NXS_ConfluenceBonus(wd);
      best.score = MathMin(100.0, best.score + bonus);
   }
   return best;
}

// ============================================================
// PHASE 2 — Signal Router with fallback.
// Collects every signal (classic + SMC), applies score cap +
// confluence + MTF/Velocity family factor, then tries the best
// signal first; if a non-critical gate blocks it, falls back to
// the next-best until one passes or the list is exhausted.
// ============================================================
int NXS_CollectAllSignals(SNXSSweep &sw, SNXSSweepExt &swExt, SNXSAMD &amd,
                          SNXSSignal &out[]){
   int n = 0;
   // Classic 16
   out[n++] = NXS_Strat_ADXRSI();
   out[n++] = NXS_Strat_Bollinger();
   out[n++] = NXS_Strat_MACD();
   out[n++] = NXS_Strat_SAR();
   out[n++] = NXS_Strat_TSI();
   out[n++] = NXS_Strat_Bjorgum();
   out[n++] = NXS_Strat_LiqSweep(sw);
   out[n++] = NXS_Strat_FVG();
   out[n++] = NXS_Strat_BreakoutAcc();
   out[n++] = NXS_Strat_LondonBO();
   out[n++] = NXS_Strat_EMAPullback();
   out[n++] = NXS_Strat_BBSqueeze();
   out[n++] = NXS_Strat_Ichimoku();
   out[n++] = NXS_Strat_RSIDiv();
   out[n++] = NXS_Strat_OrderBlock();
   out[n++] = NXS_Strat_StructureReaction();
   // SMC/ICT 10
   if(InpStrat_TurtleSoup)    out[n++] = NXS_Strat_TurtleSoup(swExt);
   if(InpStrat_IFVG)          out[n++] = NXS_Strat_IFVG_Reversal();
   if(InpStrat_FVG_Mit)       out[n++] = NXS_Strat_FVG_Mitigation();
   if(InpStrat_OB_Mit)        out[n++] = NXS_Strat_OB_Mitigation_Structural();
   if(InpStrat_SH_BMS_RTO)    out[n++] = NXS_Strat_SH_BMS_RTO(swExt);
   if(InpStrat_SMS_BMS_RTO)   out[n++] = NXS_Strat_SMS_BMS_RTO();
   if(InpStrat_SilverBullet)  out[n++] = NXS_Strat_SilverBullet(swExt);
   if(InpStrat_AMD_Reversal)  out[n++] = NXS_Strat_AMD_Reversal(swExt, amd);
   if(InpStrat_OTE_Cont)      out[n++] = NXS_Strat_OTE_Continuation();
   if(InpStrat_MalaysianSNR)  out[n++] = NXS_Strat_MalaysianSNR_Rejection();

   // v2.0.7 INSTITUTIONAL MODELS (9)
   SNXSHTF htfInst = NXS_GetHTFBias();
   if(InpUseStrat_CISD)        out[n++] = NXS_Strat_CISD(swExt);
   if(InpUseStrat_AMD_Cont)    out[n++] = NXS_Strat_AMD_Continuation(amd, htfInst);
   if(InpUseStrat_Judas)       out[n++] = NXS_Strat_JudasSwing(swExt, amd);
   if(InpUseStrat_LdnReversal) out[n++] = NXS_Strat_LondonReversal(swExt, amd);
   if(InpUseStrat_NYReversal)  out[n++] = NXS_Strat_NYReversal(swExt);
   if(InpUseStrat_WeeklyExp)   out[n++] = NXS_Strat_WeeklyRangeExp();
   if(InpUseStrat_PO3)         out[n++] = NXS_Strat_PO3(swExt, amd);
   if(InpUseStrat_LiqVoid)     out[n++] = NXS_Strat_LiquidityVoid(htfInst);
   if(InpUseStrat_DispRebal)   out[n++] = NXS_Strat_DisplacementRebalance();

   // v2.0.8 — Range Fade
   if(InpUseStrat_RangeFade)   out[n++] = NXS_Strat_RangeFade();

   // v2.0.5 stats: record called/setup for every invoked strategy
   for(int k = 0; k < n; k++){
      if(StringLen(out[k].stratName) > 0) NXS_Stats_RecordCalled(out[k].stratName);
      if(out[k].dir != DIR_NONE)          NXS_Stats_RecordSetup(out[k].stratName);
   }
   return n;
}

//+------------------------------------------------------------------+
//| OnInit                                                            |
//+------------------------------------------------------------------+
int OnInit(){
   g_sym    = _Symbol;
   g_point  = SymbolInfoDouble(g_sym, SYMBOL_POINT);
   g_digits = (int)SymbolInfoInteger(g_sym, SYMBOL_DIGITS);
   // v2.0.10 — pull active locked profile from backend (auto-optimizer winner)
   NXS_LockedProfile_Fetch();
   // v2.0.9 — load Sprint 3 learner CSV + reset handle pool
   NXS_HandlePool_Release();
   NXS_EA_Learner_Load();
   NXS_TradeSetMagic(InpMagic);
   NXS_TradeSetFillingBySymbol(g_sym);
   g_balanceDayStart = AccountInfoDouble(ACCOUNT_BALANCE);
   NXS_DailyRollover();

   // === Phase 2: symbol profile + presets ===
   NXS_BuildSymbolProfile();
   if(!g_profile.allowed){
      PrintFormat("[NEXUS ERROR] Symbol %s NOT in whitelist (InpAllowedSymbols). EA will not trade.",
                  _Symbol);
      return INIT_FAILED;
   }

   if(!NXS_CreateHandles()) return INIT_FAILED;
   NXS_MTF_CreateHandles();

   NXS_Runtime_Init();
   NXS_ApplyPreset();

   // Apply profile defaults for spread cap if user kept 0
   if(InpHardMaxSpreadPts == 0){
      Print("[NEXUS] Using profile default hard spread cap: ", g_profile.maxSpreadPts, " points");
   }

   // === Phase 3: license verification ===
   if(!NXS_License_Verify()){
      Print("[NEXUS ERROR] License verification FAILED - EA in IDLE mode (no trading)");
      // Continue init but trading disabled
   }

   // === Phase 1: state persistence resume ===
   NXS_Blk_Reset();
   NXS_State_Load();

   // Diagnostics
   NXS_Diag_OnInit();
   NXS_Stats_Init();   // v2.0.5 strategy stats tracker

   PrintFormat("[NEXUS v%s] Initialized on %s | Profile=%s | Magic=%I64d | WebSync=%s URL=%s",
               NEXUS_VERSION, g_sym, g_profile.className, InpMagic,
               (InpEnableWebSync ? "ON":"OFF"), InpWebURL);
   // v2.0.9 — explicit MTF independence declaration
   PrintFormat("[NEXUS MTF] Chart TF=%s · Entry=%s · Medium=%s · High=%s · System is CHART-INDEPENDENT (uses configured TFs only)",
               EnumToString((ENUM_TIMEFRAMES)Period()),
               EnumToString((ENUM_TIMEFRAMES)InpTFEntry),
               EnumToString((ENUM_TIMEFRAMES)InpTFMedium),
               EnumToString((ENUM_TIMEFRAMES)InpTFHigh));
   if((int)Period() != (int)InpTFEntry){
      PrintFormat("[NEXUS MTF] WARNING: chart TF (%s) differs from Entry TF (%s) — EA will still trade %s correctly.",
                  EnumToString((ENUM_TIMEFRAMES)Period()),
                  EnumToString((ENUM_TIMEFRAMES)InpTFEntry),
                  EnumToString((ENUM_TIMEFRAMES)InpTFEntry));
   }
   EventSetTimer(1);

   if(InpEnableWebSync && !MQLInfoInteger(MQL_TESTER)){
      g_lastPushTime = 0;
      NXS_WebPushSafe();
   }

   // Initial dashboard render
   if(InpShowDashboard) NXS_Dashboard_Render();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason){
   EventKillTimer();
   NXS_Stats_Deinit();   // v2.0.5 final export
   NXS_State_Save();
   NXS_ReleaseHandles();
   NXS_MTF_ReleaseHandles();
   NXS_HandlePool_Release();   // v2.0.9 Sprint 1
   if(InpShowDashboard) NXS_Dashboard_Cleanup();
   PrintFormat("[NEXUS] Deinit reason=%d", reason);
}

void OnTimer(){
   // AUDITPATCH: no WebRequest side effects during deterministic backtests.
   if(!MQLInfoInteger(MQL_TESTER)){
      NXS_WebPushSafe();
      NXS_WebPoll();
      NXS_VisualBridge_PushHTTP();   // v2.0.9 — push OB/FVG/SNR to web Live Chart
   }
   NXS_License_Verify();     // tester-safe; live hourly re-validation
   NXS_State_Save();
   if(InpShowDashboard) NXS_Dashboard_Render();
   if(InpStatsEnable)   NXS_Stats_OnTick(InpStatsExportEverySec);
}

void OnTick(){
   // v2.0.9 Sprint 1 — skid protection: drop stale ticks (>InpMaxTickAgeMs)
   if(!NXS_IsFreshTick()) return;
   // v2.0.9 Sprint 2 — keep spread rolling window fresh + virt SL check
   NXS_RS_SpreadSample();
   NXS_EA_VirtSL_Check();
   datetime prevDay = g_dayStart;
   NXS_DailyRollover();
   if(g_dayStart != prevDay){
      NXS_Prot_OnNewDay();
      if(InpNotifyDailySummary) NXS_Notify_DailySummary();
   }
   if(!NXS_UpdateIndicators()) return;

   g_regime  = NXS_DetectRegime();
   g_session = NXS_GetSession();

   SNXSHTF   htf   = NXS_GetHTFBias();
   SNXSVel   vel   = NXS_GetVelocity();
   SNXSAMD   amd   = NXS_GetAMD();
   SNXSSweep sweep = NXS_DetectSweep();

   // Management on every tick
   NXS_ManageBreakevenAndTrail();
   NXS_TrailATR();                // NEW: ATR-based trailing overlay
   NXS_ManageSplit();
   NXS_ManageGrid();
   NXS_ManagePyramid(vel);

   // Risk Protections (NEXUS v2.0)
   NXS_Prot_OnTick();

   // Settings sync from dashboard
   NXS_PullSettings();

   // Web push (disabled in Strategy Tester)
   if(!MQLInfoInteger(MQL_TESTER)) NXS_WebPush(htf, vel, amd, sweep);

   // Diagnostic summary
   NXS_Diag_OnTick(NXS_HTFName(htf.bias), NXS_VelName(vel.state),
                   NXS_AMDName(amd.phase), NXS_GetBSP());

   // === v2.0.4: Visual Bridge export (lightweight ~20 GV sets) ===
   // Uses static cache of last "best" so HUD shows last decision strategy.
   static SNXSSignal s_visualBest; static bool s_visualInit = false;
   if(!s_visualInit){ ZeroMemory(s_visualBest); s_visualInit = true; }
   NXS_ExportStateToGV(htf, vel, amd, s_visualBest);

   // v2.0.13 — track extremum prezzo durante posizione aperta (per chain re-entry)
   NXS_Chain_TrackExtremum();

   // New bar gate
   datetime bt = iTime(g_sym, InpTFEntry, 0);
   if(bt == g_lastBarTime) return;
   g_lastBarTime = bt;

   NXS_UpdateStructure(g_sym, InpTFEntry);
   g_reaction = NXS_DetectReaction(g_sym, InpTFEntry);

   // AUDITPATCH: count/report every closed-bar decision, including upstream vetoes.
   NXS_Blk_DecisionTick();
   if(g_eaPaused){ NXS_Blk_Bump(BLK_PAUSED); NXS_Blk_MaybeReport(); return; }
   if(!NXS_License_Enforce()){ NXS_Blk_Bump(BLK_LICENSE); NXS_Blk_MaybeReport(); return; }
   if(NXS_Prot_EntryBlocked()){ NXS_Blk_Bump(BLK_PROTECTIONS); NXS_Blk_MaybeReport(); return; }
   if(!NXS_SpreadOK()){ NXS_Blk_Bump(BLK_SPREAD); NXS_Blk_MaybeReport(); return; }
   if(NXS_NewsBlocking()){ NXS_Blk_Bump(BLK_NEWS); NXS_Blk_MaybeReport(); return; }

   NXS_ML_RefreshAll();

   // ---- Phase 2 router with fallback ----
   SNXSSweepExt swExt = NXS_DetectSweepExt();
   SNXSSignal all[48];
   int n = NXS_CollectAllSignals(sweep, swExt, amd, all);
   int directionalSignals = 0;
   for(int ds = 0; ds < n; ds++) if(all[ds].dir != DIR_NONE) directionalSignals++;

   // Confluence + score cap (only consider valid signals)
   NXS_ConfluenceReset();
   for(int i = 0; i < n; i++){
      if(all[i].dir == DIR_NONE) continue;
      int d = (all[i].dir == DIR_BUY) ? +1 : -1;
      NXS_ConfluenceRegister(d);
      all[i].score = NXS_ApplyScoreCap(all[i].stratName, all[i].score);
   }
   for(int i = 0; i < n; i++){
      if(all[i].dir == DIR_NONE) continue;
      int wd = (all[i].dir == DIR_BUY) ? +1 : -1;
      all[i].score = MathMin(100.0, all[i].score + (double)NXS_ConfluenceBonus(wd));
   }
   NXS_SignalSort(all, n);

   // v2.0.4: cache best signal for Visual Bridge HUD
   if(n > 0 && all[0].dir != DIR_NONE){ s_visualBest = all[0]; }

      bool opened = false;
      ENUM_NXS_EXEC_RC lastRc = EXEC_FAIL_NO_DIR;
      for(int i = 0; i < n; i++){
         SNXSSignal sig = all[i];
         if(sig.dir == DIR_NONE) continue;
         if(NXS_StrategyOnCooldown(sig.stratName)){
            NXS_Blk_Bump(BLK_COOLDOWN);
            NXS_Stats_RecordBlock(sig.stratName, (int)BLK_COOLDOWN);
            continue;
         }

         string mtfReason, velReason;
         double baseScore = sig.score;
         double mtfFactor = NXS_MTF_FamilyFactor((sig.dir == DIR_BUY ? +1 : -1),
                                                 sig.stratName, mtfReason);
         if(mtfFactor <= 0.0){
            NXS_Blk_Bump(BLK_MTF);
            NXS_Stats_RecordBlock(sig.stratName, (int)BLK_MTF);
            NXS_Blk_LogDecision(sig.stratName, NXS_DirName(sig.dir),
                                baseScore, 0, 0, 0,
                                mtfReason, "MTF blocked");
            NXS_Shadow_Record(sig, 0.0, 0.0, "MTF", "", mtfReason,
                              NXS_HTFName(htf.bias), NXS_VelName(vel.state),
                              (sweep.confirmed ? "CONFIRMED" : "NONE"),
                              NXS_SessionName(g_session),
                              EnumToString(NXS_DetectRegime()));
            if(!InpTryNextSignalIfBlocked) return;
            continue;
         }
         double penalizedScore = baseScore * mtfFactor;

         double velFactor = NXS_Vel_FamilyFactor(sig.dir, vel, sig.stratName, velReason);
         if(velFactor <= 0.0){
            NXS_Blk_Bump(BLK_VELOCITY);
            NXS_Stats_RecordBlock(sig.stratName, (int)BLK_VELOCITY);
            NXS_Blk_LogDecision(sig.stratName, NXS_DirName(sig.dir),
                                baseScore, penalizedScore, 0, 0,
                                mtfReason + "|" + velReason, "VEL blocked");
            NXS_Shadow_Record(sig, penalizedScore, 0.0, "VELOCITY", "MTF",
                              mtfReason + "|" + velReason,
                              NXS_HTFName(htf.bias), NXS_VelName(vel.state),
                              (sweep.confirmed ? "CONFIRMED" : "NONE"),
                              NXS_SessionName(g_session),
                              EnumToString(NXS_DetectRegime()));
            if(!InpTryNextSignalIfBlocked) return;
            continue;
         }
         penalizedScore *= velFactor;
         sig.score = penalizedScore;

         // v2.0.13 — Chain continuation: se è continuazione di trade vincente, applica bonus score + lot mult
         double chainLotMult = 1.0;
         string chainReason  = "";
         bool isContinuation = NXS_Chain_IsContinuation(sig.stratName,
                                                        (sig.dir == DIR_BUY ? +1 : -1),
                                                        chainLotMult, chainReason);
         g_chainPendingLotMult = isContinuation ? chainLotMult : 1.0;
         if(isContinuation){
            sig.score = MathMin(100.0, sig.score + 8.0); // bonus continuazione
            sig.reason = sig.reason + "|" + chainReason;
            PrintFormat("[NEXUS CHAIN] %s lotMult=%.2f score+8 → %.1f",
                        chainReason, chainLotMult, sig.score);
         }

         double finalScore = 0, thresh = 0;
         ENUM_NXS_EXEC_RC rc = NXS_TryExecuteRC(sig, amd, sweep, htf, vel, finalScore, thresh);
         lastRc = rc;
         string gates = mtfReason + "|" + velReason;

         if(rc == EXEC_OK){
            if(isContinuation) NXS_Chain_OnContinuationOpen();
            NXS_StrategyRegisterTrade(sig.stratName);
            double curSpread = (double)SymbolInfoInteger(g_sym, SYMBOL_SPREAD);
            NXS_Stats_RecordScoreSample(sig.stratName, baseScore, finalScore, thresh);
            NXS_Stats_RecordExec(sig.stratName, finalScore, curSpread);
            NXS_LogTradeCSV("OPEN", 0, sig.stratName, sig.entryRef,
                            0, sig.slPrice, sig.tpPrice, sig.score, sig.reason);
            NXS_Blk_LogDecision(sig.stratName, NXS_DirName(sig.dir),
                                baseScore, penalizedScore, finalScore, thresh,
                                gates, "EXEC_OK");
            opened = true;
            break;
         }
         // map rc → counter
         ENUM_NXS_BLOCK blkCode = BLK_PREFLIGHT;
         if(rc == EXEC_FAIL_PROTECTIONS){ blkCode = BLK_PROTECTIONS; gates += "|PROT"; }
         else if(rc == EXEC_FAIL_NEWS)  { blkCode = BLK_NEWS;        gates += "|NEWS"; }
         else if(rc == EXEC_FAIL_HTF)   { blkCode = BLK_HTF;         gates += "|HTF";  }
         else if(rc == EXEC_FAIL_VELOCITY){ blkCode = BLK_VELOCITY;  gates += "|VEL2"; }
         else if(rc == EXEC_FAIL_SCORE_BELOW){ blkCode = BLK_SCORE_BELOW; gates += "|SCORE"; }
         else if(rc == EXEC_FAIL_INVALID_STOPS){ blkCode = BLK_PREFLIGHT; gates += "|BAD_STOPS"; }
         else if(rc == EXEC_FAIL_INVALID_VOLUME){ blkCode = BLK_PREFLIGHT; gates += "|BAD_VOLUME"; }
         else if(rc == EXEC_FAIL_PREFLIGHT){ blkCode = BLK_PREFLIGHT; gates += "|PRE:" + g_nxsLastOpenFailure; }
         else if(rc == EXEC_FAIL_ORDER_SEND ){ blkCode = BLK_SEND_FAILED; gates += "|SEND:" + g_nxsLastOpenFailure; }
         else                              { blkCode = BLK_PREFLIGHT;    gates += "|PRE";  }
         NXS_Blk_Bump(blkCode);
         NXS_Stats_RecordBlock(sig.stratName, (int)blkCode);
         NXS_Stats_RecordScoreSample(sig.stratName, baseScore, finalScore, thresh);
         if(rc == EXEC_FAIL_INVALID_STOPS){
            NXS_Stats_RecordSLTPInvalid(sig.stratName);
         }

         NXS_Blk_LogDecision(sig.stratName, NXS_DirName(sig.dir),
                             baseScore, penalizedScore, finalScore, thresh,
                             gates, "exec_rc=" + IntegerToString((int)rc));
         // v2.0.8 shadow record for any non-EXEC_OK outcome
         NXS_Shadow_Record(sig, finalScore, thresh,
                           EnumToString(blkCode), "",
                           "exec_rc=" + IntegerToString((int)rc),
                           NXS_HTFName(htf.bias), NXS_VelName(vel.state),
                           (sweep.confirmed ? "CONFIRMED" : "NONE"),
                           NXS_SessionName(g_session),
                           EnumToString(NXS_DetectRegime()));
         if(!InpTryNextSignalIfBlocked) return;
      }
      // AUDITPATCH: NO_SIGNAL means exactly that. Signals rejected by score/MTF/etc.
      // already have their own counters and must not be double-counted as absent.
      if(!opened && directionalSignals == 0) NXS_Blk_Bump(BLK_NO_SIGNAL);
      // v2.0.8c — diagnose HTF blockage: reaction detected but no strategy emitted
      // a same-direction signal → strong indicator that internal HTF gates inside
      // strategies are vetoing all 36 trigger sources at once.
      if(directionalSignals == 0 && g_reaction.detected){
         int reactDir = g_reaction.direction;
         int htfBias  = htf.bias;   // +1 bull, -1 bear, 0 neutral
         bool counter = (reactDir == +1 && htfBias == -1) || (reactDir == -1 && htfBias == +1);
         if(counter){
            NXS_Blk_Bump(BLK_HTF);
            PrintFormat("[NEXUS BLOCK] reaction=%s qual=%.0f vs HTF=%s → all 36 strategies "
                        "self-vetoed (counter-trend). Enable Counter-HTF Soft or lower "
                        "%s ScoreMin to allow.",
                        (reactDir == +1 ? "BULL" : "BEAR"),
                        g_reaction.quality,
                        NXS_HTFName(htf.bias),
                        NXS_SessionName(g_session));
         }
      }
      NXS_Blk_MaybeReport();
      // v2.0.8 — Shadow logger tick (evaluate + export + push)
      NXS_Shadow_Tick();
}

void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& tradeReq,
                        const MqlTradeResult& tradeRes){
   // v2.0.9 Sprint 3 — event-driven fill capture (replaces polling)
   NXS_EA_OnTradeTx(trans);
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(trans.deal)) return;
   long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if(entry != DEAL_ENTRY_OUT) return;
   long mg = HistoryDealGetInteger(trans.deal, DEAL_MAGIC);
   if(!IsNexusMagic(mg)) return;
   double pnl = HistoryDealGetDouble(trans.deal, DEAL_PROFIT)
              + HistoryDealGetDouble(trans.deal, DEAL_SWAP)
              + HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
   NXS_OnTradeClosed(pnl);
   NXS_LogTradeCSV("CLOSE", trans.deal, "", 0, 0, 0, 0, pnl, "");

   string reason = HistoryDealGetString(trans.deal, DEAL_COMMENT);
   if(StringLen(reason) == 0) reason = (pnl >= 0) ? NXS_R_PROFIT : NXS_R_DD;
   ulong  ticket = (ulong)HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);
   double lots   = HistoryDealGetDouble(trans.deal, DEAL_VOLUME);
   double price  = HistoryDealGetDouble(trans.deal, DEAL_PRICE);
   ENUM_DEAL_TYPE dtype = (ENUM_DEAL_TYPE)HistoryDealGetInteger(trans.deal, DEAL_TYPE);
   string side = (dtype == DEAL_TYPE_SELL) ? "BUY" : "SELL";
   // Estrai strategia dal comment originale del deal (format "NEXUS_v2|STRAT|score")
   string dcomment = HistoryDealGetString(trans.deal, DEAL_COMMENT);
   string strat = "";
   int p1 = StringFind(dcomment, "|");
   if(p1 >= 0){
      int p2 = StringFind(dcomment, "|", p1+1);
      if(p2 > p1) strat = StringSubstr(dcomment, p1+1, p2-p1-1);
   }
   NXS_Prot_PushTradeReason(ticket, mg, strat, side, lots, 0.0, price, pnl, reason);

   // v2.0.13 — hook chain
   int closeDir = (side == "BUY") ? +1 : -1;
   NXS_Chain_OnTradeClose(strat, closeDir, price, pnl);

   NXS_Notify_TradeClose(strat, pnl, reason);
}
//+------------------------------------------------------------------+
