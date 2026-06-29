//+------------------------------------------------------------------+
//|  NXS_Inputs.mqh - All input parameters                            |
//+------------------------------------------------------------------+
#ifndef __NXS_INPUTS_MQH__
#define __NXS_INPUTS_MQH__

input group "=== GENERAL ==="
input long     InpMagic            = 991000;
input string   InpComment          = "NEXUS_v2";
input ENUM_TIMEFRAMES InpTFEntry   = PERIOD_M15;
input ENUM_TIMEFRAMES InpTFMedium  = PERIOD_H1;
input ENUM_TIMEFRAMES InpTFHigh    = PERIOD_H4;

input group "=== PRESET / SCALING ==="
// 0=Custom, 1=Conservative, 2=Balanced, 3=Aggressive, 4=MVP_v206 (5 SMC MVP)
input int      InpRiskProfile      = 2;
input bool     InpAutoScaleByAccount = true;

input group "=== SYMBOL WHITELIST ==="
input bool     InpUseSymbolWhitelist = true;
input string   InpAllowedSymbols   = "GOLD,XAUUSD,EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,US30,NAS100,SPX500,GER40,BTCUSD,ETHUSD";

input group "=== LICENSE ==="
input bool     InpEnableLicense    = true;
input string   InpLicenseKey       = "";

input group "=== ROBUSTNESS (Phase 1) ==="
input int      InpHardMaxSpreadPts = 0;     // 0 = use profile default
input int      InpOrderRetries     = 3;     // retries on requote/off-quotes
input bool     InpUseStatePersist  = true;  // resume state after MT5 restart
input bool     InpUseAtrTrail      = true;  // ATR-based trailing stop
input double   InpAtrTrailMult     = 1.5;

input group "=== ON-CHART DASHBOARD ==="
input bool     InpShowDashboard    = true;
input int      InpDashX            = 10;
input int      InpDashY            = 25;

input group "=== NOTIFICATIONS ==="
input bool     InpNotifyPush       = false;   // MT5 mobile push
input bool     InpNotifyEmail      = false;
input bool     InpNotifyTelegram   = false;
input string   InpTelegramChatId   = "";
input bool     InpNotifyOnOpen     = true;
input bool     InpNotifyOnClose    = true;
input bool     InpNotifyOnProtection = true;
input bool     InpNotifyDailySummary = false;

input group "=== RISK MANAGEMENT ==="
input double   InpRiskPercent      = 1.0;
input double   InpMaxLot           = 5.0;
input int      InpMaxTradesPerDay  = 12;
input int      InpMaxConcurrent    = 4;
input double   InpMaxDailyDDPct    = 5.0;
input double   InpMinEntryScore    = 70.0;
input double   InpMalaysianMinScore = 80.0;  // v2.0.14: MALAYSIAN_SNR richiede score >= 80
input int      InpMinMarginLevel   = 200;

input group "=== ANTI-REVENGE ==="
input bool     InpAntiRevenge      = true;
input int      InpAntiRevengeLosses= 3;
input int      InpAntiRevengeMin   = 60;

input group "=== HTF BIAS ==="
input bool     InpUseHTFBias       = false;   // OFF by default — gate must IMPROVE not BLOCK
input int      InpHTF_EMAPeriod    = 50;
input double   InpHTF_MinConf      = 0.55;
input bool     InpHTF_AllowReversal= true;

input group "=== VELOCITY GATE ==="
input bool     InpUseVelocity      = false;   // OFF by default — was blocking too many trades
input int      InpVel_ZLEMA        = 35;
input double   InpVel_ATRMult      = 0.5;

input group "=== NEWS FILTER ==="
input bool     InpUseNews          = true;
input int      InpNewsMinBefore    = 5;     // was 30 — user wants tight buffer 5/5
input int      InpNewsMinAfter     = 5;     // was 30 — user wants tight buffer 5/5
input string   InpNewsCurrencies   = "USD,EUR,XAU";

input group "=== AMD MODEL ==="
input bool     InpUseAMD           = true;
input int      InpAsianStartHour   = 0;
input int      InpAsianEndHour     = 7;

input group "=== BSP (Buyer/Seller Pressure) ==="
input bool     InpUseBSP           = true;
input double   InpBSPWeight        = 0.20;

input group "=== SESSIONS ==="
input bool     InpUseSessions      = true;
input double   InpAsianScoreMin    = 65.0;
input double   InpLondonScoreMin   = 60.0;
input double   InpOverlapScoreMin  = 58.0;
input double   InpNYScoreMin       = 60.0;
input double   InpAfterNYScoreMin  = 70.0;

input group "=== STRATEGIES TOGGLE ==="
input bool     InpStrat_ADX_RSI      = true;
input bool     InpStrat_BOLLINGER    = true;
input bool     InpStrat_MACD         = true;
input bool     InpStrat_SAR          = true;
input bool     InpStrat_TSI          = true;
input bool     InpStrat_BJORGUM      = true;
input bool     InpStrat_LIQ_SWEEP    = true;
input bool     InpStrat_FVG_CONT     = true;
input bool     InpStrat_BREAKOUT_ACC = true;
input bool     InpStrat_LONDON_BO    = true;
input bool     InpStrat_EMA_PULLBACK = true;
input bool     InpStrat_BB_SQUEEZE   = true;
input bool     InpStrat_ICHIMOKU     = true;
input bool     InpStrat_RSI_DIV      = true;
input bool     InpStrat_ORDER_BLOCK  = true;
input bool     InpUseStructReact     = true;

input group "=== STRUCTURE ENGINE ==="
input bool     InpUseStructure       = true;
input int      InpSwingWing          = 3;
input double   InpOBDisplacement     = 1.5;
input double   InpFVGMinBody         = 0.5;

input group "=== REACTION ENGINE ==="
input bool     InpUseReaction        = true;
input double   InpReactionTol        = 0.3;

input group "=== INDICATORS ==="
input int      InpADX_Period       = 14;
input int      InpRSI_Period       = 14;
input int      InpBB_Period        = 20;
input double   InpBB_Dev           = 2.0;
input int      InpMACD_Fast        = 12;
input int      InpMACD_Slow        = 26;
input int      InpMACD_Signal      = 9;
input double   InpSAR_Step         = 0.02;
input double   InpSAR_Max          = 0.2;
input int      InpATR_Period       = 14;
input int      InpEMA200_Period    = 200;
input int      InpEMA9_Period      = 9;
input int      InpEMA21_Period     = 21;

input group "=== SL / TP ==="
input double   InpATR_SL_Mult      = 2.0;    // v2.0.14: 1.8→2.0 (SL piu' largo su M5 gold)
input double   InpATR_TP_Mult      = 2.6;
input double   InpMinSLMult        = 1.5;    // v2.0.14: pavimento minimo moltiplicatore SL

input group "=== CLOSE & REVERSE ==="
input bool     InpEnableCloseReverse = true;
input double   InpMinScoreReverse    = 70.0;       // v2.0.13: lowered 75→70 (chain smart-reverse can lower further)

input group "=== STRATEGY CHAIN / CONTINUATION (v2.0.13) ==="
input bool     InpChainEnableContinuation     = true;   // dopo profit, riapri in continuazione se setup compatibile
input bool     InpChainEnableSmartReverse     = true;   // abbassa soglia reverse se reaction>=75 AND HTF concorde
input int      InpChainContinuationWindowSec  = 1800;   // 30 min: finestra valida per continuazione
input double   InpChainContinuationLotMult    = 0.6;    // lotto continuazione (60% del base)
input int      InpChainMaxContinuations       = 3;      // n. max continuazioni dopo un trade vincente

input group "=== BREAK EVEN & TRAIL ==="
input double   InpBE_TriggerATR    = 1.0;
input double   InpTrailActivateATR = 1.5;
input double   InpTrailDistanceATR = 1.0;
input double   InpTrailDistancePostBE = 0.7;   // tighter trail once BE reached
input int      InpMaxHoldHours     = 4;        // force-close trade older than this
input bool     InpUseAdaptiveSL    = true;     // dynamic SL by ATR regime
input double   InpSL_HighVol_Mult  = 2.0;      // SL multiplier when ATR > avg
input double   InpSL_LowVol_Mult   = 1.8;      // v2.0.14: 1.5→1.8 (SL piu' largo bassa vol)
input int      InpATR_AvgPeriod    = 20;       // ATR moving-avg window
input double   InpTP1_ATR          = 1.5;      // P1 partial-close at +1.5 ATR (was 1.0)
input double   InpTP2_ATR          = 3.0;      // P2 partial-close at +3.0 ATR (was 2.0)
input double   InpTP1_Pct          = 0.30;     // partial close 30% at TP1 (was 33%)
input double   InpTP2_Pct          = 0.50;     // partial close 50% of remainder at TP2

input group "=== ANTI-BLEED (P2) ==="
input bool     InpUseAntiBleed     = true;
input double   InpAB_RiskMult_1L   = 0.7;      // lot mult after 1 consecutive loss
input double   InpAB_RiskMult_2L   = 0.7;      // after 2
input double   InpAB_RiskMult_3L   = 0.4;      // after 3
input int      InpAB_SkipAfter3L   = 2;        // skip next N signals after 3rd loss
input double   InpAB_DD_Soft       = 2.0;      // DD% threshold for soft risk reduction
input double   InpAB_DD_Hard       = 4.0;      // DD% for hard reduction + stricter score
input double   InpAB_RiskMult_DDSoft= 0.7;
input double   InpAB_RiskMult_DDHard= 0.4;
input double   InpAB_ScoreBonus_DDHard = 10.0; // require MinEntryScore+10 when DD hard

input group "=== GRID / PYRAMID / SPLIT ==="
input bool     InpEnableGrid       = false;
input double   InpGridStepATR      = 1.2;
input bool     InpEnablePyramid    = false;
input bool     InpEnableSplit      = true;

input group "=== WEB BRIDGE ==="
input bool     InpEnableWebSync    = true;
input string   InpWebURL           = "http://127.0.0.1:8001";
input string   InpWebToken         = "NEXUS_BRIDGE_TOKEN_2026";
input int      InpPushIntervalSec  = 5;
input int      InpPollIntervalSec  = 3;

input group "=== LOGGING ==="
input bool     InpLogTrades        = true;
input bool     InpDebugLog         = false;

//================================================================
//  NEXUS v2.0 / Phase 3-5 additions (additive — defaults preserve v1 behaviour)
//================================================================
input group "=== RISK PROTECTIONS (v2.0) ==="
input bool     InpUseESL           = true;   // Equity Stop Loss
input bool     InpESL_IsPercent    = true;
input double   InpESL_Value        = 5.0;    // 5% of balance
input bool     InpUseDPT           = false;  // OFF by default — user wants to decide WHEN to stop
input bool     InpDPT_IsPercent    = true;
input double   InpDPT_Value        = 3.0;    // 3% of dayStart balance (only if InpUseDPT=true)
input bool     InpUseMaxHold       = true;   // Max hold time per position
input int      InpProt_MaxHoldHours= 12;
input bool     InpUseMaxLossPos    = true;   // Max loss per position
input double   InpMaxLossPosPct    = 2.0;    // % of balance
input int      InpProt_MinLifeMin  = 15;     // v2.0.14: min minuti vita prima che NXS:RISK chiuda
input bool     InpUseAutoClose     = true;   // Flatten before market close
input int      InpAutoCloseMin     = 15;
input int      InpMarketCloseGMT   = 21;

input group "=== CONFLUENCE + COOLDOWN (Phase 3) ==="
input bool     InpUseConfluence    = true;
input int      InpConfluenceBonus2 = 10;
input int      InpConfluenceBonus3 = 20;
input int      InpConfluenceBonus4 = 30;
input int      InpADXRsiScoreCap   = 70;   // cap anti-dominance
input bool     InpUseStrategyCD    = true;
input int      InpMaxConsecPerStrat= 3;
input int      InpStratCooldownMin = 30;

input group "=== MTF / SPREAD / VOL REGIME (Audit PDF) ==="
input bool     InpUseMTFValidation = true;
input ENUM_TIMEFRAMES InpMTF_TF1   = PERIOD_H1;
input ENUM_TIMEFRAMES InpMTF_TF2   = PERIOD_H4;
input bool     InpUseDynamicSpread = true;
input double   InpMaxSpreadAtrPct  = 8.0;    // spread > 8% of ATR → block
input int      InpMaxSpreadPoints  = 0;     // 0 = use asset-class profile cap
input bool     InpUseVolRegime     = true;
input double   InpLowVolAtrPct     = 0.15;
input double   InpHighVolAtrPct    = 0.6;

input group "=== GATE MODE (v2.0.2 - sblocco trade) ==="
// 0=Conservative (block aggressive), 1=Balanced, 2=Discovery (very permissive), 3=DebugTrade
input int      InpGateMode                       = 1;
// 0=block, 1=penalty score, 2=allow
input int      InpMTFMixedMode                   = 1;
input int      InpVelocityNeutralMode            = 1;
input bool     InpAllowReversalAgainstMTFOnSweep = true;
input bool     InpTryNextSignalIfBlocked         = true;
input bool     InpDebugDecisionLog               = true;

input group "=== SMC/ICT STRATEGIES (v2.0.2) ==="
input bool     InpStrat_TurtleSoup     = true;
input bool     InpStrat_IFVG           = true;
input bool     InpStrat_FVG_Mit        = true;
input bool     InpStrat_OB_Mit         = true;
input bool     InpStrat_SH_BMS_RTO     = true;
input bool     InpStrat_SMS_BMS_RTO    = true;
input bool     InpStrat_SilverBullet   = true;
input bool     InpStrat_AMD_Reversal   = true;
input bool     InpStrat_OTE_Cont       = true;
input bool     InpStrat_MalaysianSNR   = true;

input group "=== INSTITUTIONAL MODELS (v2.0.7) ==="
input bool     InpUseStrat_CISD          = true;
input bool     InpUseStrat_AMD_Cont      = true;
input bool     InpUseStrat_Judas         = true;
input bool     InpUseStrat_LdnReversal   = true;
input bool     InpUseStrat_NYReversal    = true;
input bool     InpUseStrat_WeeklyExp     = true;
input bool     InpUseStrat_PO3           = true;
input bool     InpUseStrat_LiqVoid       = true;
input bool     InpUseStrat_DispRebal     = true;

input group "=== RANGE / COUNTER-HTF (v2.0.8) ==="
input bool     InpUseStrat_RangeFade     = true;     // mean-revert sui range stretti
input bool     InpEnableCounterHTFSoft   = false;    // OPTIONAL: counter-trend HTF micro-trade
input double   InpCounterHTF_MinReactQ   = 75.0;     // min reaction quality
input double   InpCounterHTF_LotMult     = 0.40;     // lot reducer (40% of base)
input double   InpCounterHTF_TP1Pct      = 70.0;     // % closed at 1R
input double   InpCounterHTF_SLATR       = 1.5;      // v2.0.14: 1.2→1.5 (no SL sotto 1.5)
input double   InpCounterHTF_MinRR       = 1.2;      // minimum reward/risk
input int      InpCounterHTF_MaxPerSession = 1;      // anti-spam

input group "=== ASSET CLASS / BTC (v2.0.8) ==="
input int      InpAssetClass             = 0;        // 0=AUTO 1=FOREX 2=METAL 3=INDEX 4=CRYPTO
input bool     InpCryptoWeekendMode      = true;     // allow trading weekends if crypto
input double   InpCryptoSpreadCapATRPct  = 15.0;     // spread cap relaxed for crypto

input group "=== SHADOW TRADING (v2.0.8) ==="
input bool     InpEnableShadowTrading    = true;     // log blocked signals
input bool     InpShadowPushToBackend    = true;     // WebRequest push
input int      InpShadowExportEverySec   = 300;      // 5 min

input group "=== VISUAL SUITE LAYERS (v2.0.7) ==="
input bool     InpVis_CISD_Level         = false;
input bool     InpVis_Judas_Marker       = false;
input bool     InpVis_PO3_Phase          = false;
input bool     InpVis_LiquidityVoid      = false;
input bool     InpVis_DispRebalZone      = false;
input bool     InpVis_WeeklyRange        = false;
input bool     InpVis_LdnNyReversal      = false;

input group "=== STATS / ANALYTICS (v2.0.5) ==="
input bool     InpStatsEnable          = true;
input int      InpStatsExportEverySec  = 300;   // CSV export interval (sec)
input bool     InpStatsPushToBackend   = false; // optional WebRequest upload

input group "=== SERVER TIME (v2.0.5b) ==="
input int      InpServerGMTOffset      = 2;     // server-time offset to GMT (h). 2 = CEST broker. Set 0 if your broker is UTC.

#endif
