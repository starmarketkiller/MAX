//+------------------------------------------------------------------+
//|                                     XAUUSD Killer XM (MT5)       |
//|   Trend-follow + SMC light - production-safe single file EA      |
//|                                                                  |
//| FIXES                                                           |
//| - Normalize pip/point/tick handling across FX/JPY/indices.       |
//| - Harden symbol profile detection for XM index variants.         |
//| - Convert GOLD-tuned distances to profile-aware points.          |
//| - Fix index key-step units and volume step rounding.             |
//| - Add tickSize/pipSize to logs and sanity warnings.              |
//| - Add optional SD/candle/momentum bonus scoring + CSV fields.    |
//|                                                                  |
//| CHANGELOG                                                       |
//| - Added ICT/SMC modules: NY killzones, PD arrays, liquidity      |
//|   sweeps, displacement, MSS/BOS, order blocks + RTO/MT, and OTE  |
//|   premium/discount filters with HTF swings.                      |
//| - Expanded CSV logging to include ICT context (killzone, PDH/PDL,|
//|   sweep/displacement/OB/OTE metadata).                           |
//+------------------------------------------------------------------+
#property strict
#include <Trade/Trade.mqh>
#include <GROK/PatternScores.mqh>
#include "Strategy_RSIEngulfTouch.mqh"
#include <GROK/LicenseClient.mqh>
#include <GROK/PatternEngine.mqh>
#include <GROK/Core/Config.mqh>
#include <GROK/Core/Utils.mqh>
#include <GROK/Stats/ProbabilityEngine.mqh>

CTrade trade;

enum RegimeState
{
   REGIME_RANGE = 0,
   REGIME_TRANSITION = 1,
   REGIME_TREND = 2,
   REGIME_EXPANSION = 3
};

enum TradeDir
{
   DIR_NONE = 0,
   DIR_LONG = 1,
   DIR_SHORT = -1
};

#include <GROK/OrderGate.mqh>

enum PresetMode
{
   PRESET_CUSTOM = 0,
   PRESET_BALANCED = 1,
   PRESET_CONSERVATIVE = 2
};

enum SymbolProfile
{
   PROFILE_FX_MAJORS_5DIG = 0,
   PROFILE_FX_JPY_3DIG = 1,
   PROFILE_INDICES = 2
};

input PresetMode InpPresetMode = PRESET_CUSTOM;

input string InpSymbolOverride = "";
input long   InpMagic = 3011;
input double InpPipPrice = 0.10; // DEPRECATED name: acts as pip size override (if 0 -> auto)
input int    InpMaxSpreadPoints = 35;
input int    InpMaxSlippagePoints = 35;
input int    InpMaxRetries = 2;
input int    InpRetryDelayMs = 350;

// RSI Engulf Touch strategy (modulo separato, attivabile)
input bool   Enable_RSIEngulfTouch = true;
input int    RSI_Length = 7;
input double RSI_OB = 70;
input double RSI_OS = 30;
input double Lots = 0.01;
input double PipSize = 0.01;
input double SL_Pips = 70;
input double TP1_Pips = 50;
input double TP2_Pips = 100;
input double MaxSpreadPips = 25;
input bool   OneSetPerBar = true;
input int    CooldownSeconds = 90;
input long   MagicBase = 91001;
input ENUM_TIMEFRAMES SignalTF = PERIOD_CURRENT;
input double TrendThresholdMultiplier = 1.0;
input RSITrendMode TrendMode = TRENDMODE_DISABLED;
input bool   InpUseSMCZ3C = false;
input bool   InpDrawZones = true;
input string InpSMCTFs = "PERIOD_M5,PERIOD_M15,PERIOD_M30,PERIOD_H1,PERIOD_H4";
input int    InpScanBars = 300;
input double InpBodyEngulfEpsPoints = 2.0;
input double InpDispATRMult = 0.8;
input int    InpSwingLookbackBars = 80;
input int    InpPivotLR = 2;
input double InpMitigatePct = 50.0;
input int    InpMaxTouches = 3;
input double InpInvalidationBufferPoints = 5.0;
input double InpMergeTolPoints = 5.0;
input double InpMinScoreToKeep = 50.0;
input double InpTimeFactor = 1.0;

input bool   InpUseReactionProbabilityModel = true;
input int    InpMaxTradesPerDay = 3;
input int    InpCooldownMinutes = 30;
input int    InpMaxLossStreak = 3;
input bool   InpOneTradePerZone = true;
input bool   InpNoTradeAgainstHTF = true;
input int    InpZoneOldAgeBars = 120;
input double InpReactionNearATRMult = 0.25;
input double InpReactionDispATRMult = 1.2;
input int    InpSweepReclaimBars = 3;
input double InpSweepPoints = 15.0;
input double InpRiskATRBufferMult = 0.5;

input int    InpEntryThreshold = 70;
input double InpRiskBasePct = 0.005;
input double InpRiskMinPct = 0.001;
input double InpRiskMaxPct = 0.0125;
input double InpMaxRiskMultiplier = 1.25;
input double InpAtrSpikeRatio = 1.8;
input int    InpAtrMaPeriod = 20;
input bool   InpUseSessionRiskMultiplier = true;
input double InpSessionRiskMultiplier = 0.75;
input double InpDailyDDSoft = 2.0;
input double InpDailyDDHard = 4.0;
input int    InpCatastrophicSL_Points = 150;

input int MaxSpreadPoints = 30; // DEPRECATED: use InpMaxSpreadPoints
input bool UseInstitutionalScore = true;
input int InstitutionalMinScore = 60;
input bool LogInstitutional = true;

input bool   UsePatternEngine = true;
input bool   UsePatternPriors = true;
input bool   UseBustedLogic = true;
input string PatternCSVFileName = "pattern_stats.csv";
input ENUM_TIMEFRAMES InpPatternTF = PERIOD_M15;
input int    InpPatternLookback = 120;
input int    InpPatternPivotLR = 2;
input double InpPatternWeight = 1.20;
input double InpPatternQualityWeight = 8.0;
input double InpPattern_kRank = 0.20;
input double InpPattern_kFail = 18.0;
input double InpPattern_kTarget = 18.0;
input double InpPattern_kMove = 14.0;
input double InpPatternSL_ATR_Buffer = 0.15;
input int    InpBustedBars = 6;
input double InpBustedMinATR = 0.30;

input bool   InpRunSelfTestOnInit = true;

input string InpLicenseKey="";
input string InpLicenseApiBase="https://api.example.com";
input string InpEaId="Grok3xAI";
input string InpEaVersion="3.13";
input int    InpVerifyHours=6;
input int    InpGraceHours=48;
input bool   InpAllowManageOpenPositionsWhenInvalid=true;
input bool   InpBypassLicensingInStrategyTester=true;
input bool   InpHardFailIfNoValidEver=true;
input bool   InpShowLicensePanel=true;
input bool   InpLogLicenseToFile=true;

input bool   InpUseSpreadMultiple = true;
input double InpSpreadMultiple = 3.0;
input int    InpSpreadMultipleBlockMin = 45; // minutes

input bool   InpUseRolloverBlock = true;
input string InpRolloverStart = "23:55";
input string InpRolloverEnd = "00:15";

input bool InpUseSessionFilter = true;
input int  InpStartHour = 6;
input int  InpEndHour = 23;

input bool InpUseICTTime = true;
input bool InpUseManualNYOffset = true;
input int  InpNYOffsetHours = -5;
input bool InpAutoNYDST = false;
input int  InpNYOffsetSummerHours = -4;
input bool InpUseKillzoneAsia = true;
input bool InpUseKillzoneLondon = true;
input bool InpUseKillzoneNY = true;

input int    InpATRPeriod = 14;
input int    InpADXPeriod = 14;
input int    InpRSIPeriod = 14;
input int    InpEMA_Fast = 50;
input int    InpEMA_Slow = 200;

input int    InpRegimeConfirmBarsH1 = 2;
input int    InpRegimeLockBarsH1 = 4;

input int    InpPivotLen = 3;
input int    InpPivotConfirmBars = 2;
input int    InpMaxBarsAfterBOS = 6;

input double InpEqToleranceATR = 0.25;
input double InpEqToleranceMinPoints = 8;
input int    InpEqClusterMin = 2;
input int    InpEqScanBars = 40;
input double InpDisplacementATR = 1.1;
input double InpDisplacementBodyRatio = 0.55;
input int    InpDisplacementSearchBars = 4;
input int    InpOBLookback = 10;
input int    InpOBMaxAgeBars = 12;

input ENUM_TIMEFRAMES InpOTE_HTF = PERIOD_H1;
input int    InpOTE_SwingLookback = 48;
input double InpOTE_Min = 0.62;
input double InpOTE_Max = 0.79;
input double InpMinPDArrayDistance = 0.80;
input double InpMinPDArrayATR = 1.0;
input int    InpMinPDArrayMinPoints = 80;

input bool   InpUseBreakRetest = true;
input double InpRetestTolATR = 0.15;

input double InpKeyLevelStepPrice = 3.0;
input double InpKeyNearPrice = 0.35;
input double InpKeyChaseMaxDistPrice = 0.90;

input bool   InpUseFVGFeature = true;
input int    InpFVGScanBars = 30;
input double InpFVGMaxDistATR = 1.2;

input bool   InpUseFibFilter = true;
input double InpFibBaseMin = 0.50;
input double InpFibBaseMax = 0.618;
input double InpFibTolPrice = 0.20;
input bool   InpUseOTEBonus = true;
input double InpOTEMin = 0.62;
input double InpOTEMax = 0.79;
input int    InpOTEBonusPoints = 6;

input bool   InpUseFootprintProxy = true;
input int    InpFP_VolMAPeriod = 48;
input double InpFP_VolSpikeRatio = 1.35;
input double InpFP_BodyMinRatio = 0.55;
input double InpFP_CloseSideMin = 0.65;
input double InpFP_AbsorpVolRatio = 1.50;
input double InpFP_AbsorpRangeATR = 0.45;
input bool   InpFP_RequireAcceptance = true;
input int    InpFP_ScoreBonus = 10;

input bool   InpUseSupplyDemandBonus = true;
input ENUM_TIMEFRAMES InpSD_TF = PERIOD_H1;
input int    InpSD_LookbackBars = 200;
input double InpSD_MinImpulseATR = 1.2;
input int    InpSD_MaxBaseBars = 3;
input double InpSD_ZonePadATR = 0.15;
input double InpSD_MaxDistATR = 0.8;
input int    InpSD_BonusPoints = 6;
input int    InpSD_FreshnessBonus = 3;

input bool   InpUseCandleBonus = true;
input int    InpCandleBonusPoints = 4;

input bool   InpUseMomentumBonus = true;
input int    InpMomentumBonusPoints = 4;
input bool   InpRequireBiasAlignWithSweep = true;

input bool   InpUseSpikeGuard = true;
input double InpSpikeMultATR = 2.5;

input double InpSL_ATR_Mult = 0.25;
input double InpSL_MinBufferPrice = 0.15;

input bool   InpUseMMSL = true;
input int    InpMMSL_Pips = 35;
input double InpMMSL_ExtraBufferPrice = 0.00;

input double InpTP_RR_Main = 2.0;
input double InpMinRRAllowed = 1.5;

input bool   InpUseTP1Partial = true;
input double InpTP1_CloseFrac = 0.50;
input bool   InpTP1_UseKeyLevelFirst = true;

input bool   InpUseSmartBE = true;
input double InpBE_MinProfitR = 1.0;
input double InpBE_OffsetPrice = 0.05;

input bool   InpUseATRTrailAfterTP1 = true;
input double InpTrailATR_Mult = 1.20;
input double InpTrailMinImprovePrice = 0.10;
input bool   InpTrailOnNewBarOnly = true;

input double InpBaseRiskPct = 3.0;
input double InpMaxLotCap = 2.0;

input bool   InpUseLowVolFilter = true;
input ENUM_TIMEFRAMES InpVolTF = PERIOD_H1;
input int    InpVolMAPeriod = 48;
input double InpLowVolFactor = 0.75;

input bool   InpUseSpreadInstability = true;
input int    InpSpreadAvgBarsH1 = 24;
input double InpSpreadSpikeFactor = 1.6;
input int    InpSpreadSpikeBlockMin = 60;

input bool   InpUseDailyTradeControl = true;
input int    InpHardMaxTradesPerDay = 4;

input bool   InpUseMaxDailyLossLock = true;
input double InpMaxDailyLossPct = 4.0;

input bool   InpUseSoftEquityLock = true;
input double InpSoftEqTrigger1 = 2.0;
input double InpSoftEqFloor1 = 0.8;
input double InpSoftEqTrigger2 = 4.0;
input double InpSoftEqFloor2 = 2.0;

input int    InpCooldownBarsAfterEntry = 2;

input bool   InpUseAntiChop = true;
input int    InpLossBlock2_Hours = 4;
input int    InpLossBlock3_Hours = 12;
input double InpRiskMultAfter3Loss = 0.70;
input int    InpRiskCutAfter3Loss_H = 24;

input bool   InpUseRSIAfterLoss = true;
input int    InpLossStreakForRSI = 1;

input bool   InpUsePyramiding = true;
input int    InpMaxAdds = 2;
input double InpPyramidMinProfitR = 0.8;
input bool   InpPyramidRequireMainBE = true;
input double InpPyramidSpacingATR = 0.7;
input bool   InpPyramidOnlyInTrend = true;
input bool   InpPyramidRequireAdxRising = true;
input bool   InpPyramidUsePeakDDCap = true;
input double InpPyramidMaxPeakDDPct = 2.0;
input double InpAddRiskMult1 = 0.50;
input double InpAddRiskMult2 = 0.35;

input bool   InpEnableCSV = true;
input string InpCSVName = "xauusd_killer_v314_xm_gold.csv";

const int SETUP_MIN = 50;
const int TIMING_MIN = 15;
const int TOTAL_MIN = 68;

// XM suggested starting inputs (not optimized; adjust per broker/spread):
// Profile   | MaxSpreadPts | MaxSlippagePts | SpreadMultiple | SpreadSpikeFactor | Rollover  | Session
// FX majors | 25-35        | 30-40          | 2.5-3.0        | 1.5-1.8           | 23:55-00:15 | 06-23
// FX JPY    | 25-40        | 30-50          | 2.5-3.0        | 1.5-1.8           | 23:55-00:15 | 06-23
// Indices   | 80-150       | 80-150         | 2.0-2.5        | 1.4-1.7           | 23:55-00:15 | 06-23

string g_symbol = "";
int g_digits = 2;
double g_point = 0.01;
double g_pip = 0.10;
SymbolProfile g_profile = PROFILE_FX_MAJORS_5DIG;
bool g_isGoldSymbol = false;
RSIEngulfTouchStrategy g_rsiEngulfTouch;
bool g_rsiEngulfTouchReady = false;
datetime g_lastM15Bar = 0;
datetime g_lastH1Bar = 0;
double g_spreadEma = 0.0;
bool g_csvOpenWarned = false;

int g_irEntryScore = 0;
string g_irTier = "NA";
double g_irRiskBasePct = 0.0;
double g_irScoreMult = 0.0;
double g_irRegimeMult = 0.0;
double g_irFearMult = 0.0;
double g_irFinalRiskPct = 0.0;
double g_irRiskMoney = 0.0;
double g_irStopDistancePoints = 0.0;
double g_irLots = 0.0;
double g_irSpreadPoints = 0.0;
double g_irAtrRatio = 0.0;
int g_irLossStreak = 0;
double g_irDailyDD = 0.0;

int g_instTotalScore = 0;
double g_instRiskMult = 1.0;
int g_instPatternScore = 0;
EPattern50 g_instPattern = PAT_DOJI;

PatternStats g_patternStats[];
bool g_patternStatsLoaded = false;
datetime g_patternCacheBar = 0;
PatternSignal g_patternSignal;
double g_patternPriorScore = 50.0;
double g_patternFinalScore = 0.0;
double g_patternScoreDelta = 0.0;
double g_patternOutcomePips = 0.0;
double g_patternMaxFavorPips = 0.0;
double g_patternMaxAdversePips = 0.0;

PatternContextFeatures g_patternCtx;
string g_patternBreakdown = "";

bool SelfTest();

void PatternEngine_Init();
void PatternEngine_Update();
double PatternEngine_ComputePrior(const PatternSignal &sig);
void PatternEngine_UpdateMfeMae();


void SMCZ3C_Update();
bool RP_ModelGate(TradeDir dir, double entry, double &sl, double &tp, int &scoreOut, string &reasonOut, string &zoneKeyOut);
void RP_RegisterTrade(const string zoneKey);

double IR_GetScoreMultiplier(int entryScore, string &tierOut);
double IR_GetAtrRatio();
double IR_GetRegimeMultiplier(double spreadPoints, double atrRatio, bool &blockOut);
double IR_GetDailyDDPct();
double IR_GetFearMultiplier(int lossStreak, double dailyDrawdownPct, bool &blockOut);
double IR_ClampRiskPct(double riskPct);
double RiskInputToPercent(double v);
double IR_CalcLotsFromRiskPct(double entryPrice, double stopPrice, double riskPct, double &riskMoneyOut, double &stopDistancePointsOut);
bool IR_ComputeLots(TradeDir dir, double entryPrice, double &stopPrice, int entryScore, double &lotsOut, string &tierOut, string &reasonOut);
void IR_ResetTelemetry();

EPattern50 MapDetectorToEPattern50(int detectorIdOrEnum, bool isBullish);
void ComputeInstitutionalAdapter(int detectorIdOrEnum, bool isBullish, int entryMask, int killzoneActive, int &outTotalScore, double &outRiskMult, int &outPatternScore, EPattern50 &outPattern);
string ExplainSkipMask(int mask);
string ExplainEntryMask(int mask);
datetime GetTradingDayStart(datetime t);
int GetTradingDayId(datetime t);

struct IndicatorEntry
{
   int type;
   string sym;
   ENUM_TIMEFRAMES tf;
   int p1;
   int p2;
   int p3;
   int handle;
};

struct IndicatorsCache
{
   IndicatorEntry entries[];
};

IndicatorsCache g_indicators;
int g_hodlodDayId = 0;
datetime g_hodlodBarTime = 0;
double g_cachedHod = 0.0;
double g_cachedLod = 0.0;

// Runtime config (preset-applied)
PresetMode cfg_InpPresetMode;
string cfg_InpSymbolOverride;
long cfg_InpMagic;
double cfg_InpPipPrice;
bool cfg_InpUseSessionFilter;
int cfg_InpStartHour;
int cfg_InpEndHour;
int cfg_InpMaxSpreadPoints;
int cfg_InpMaxSlippagePoints;
int cfg_InpMaxRetries;
int cfg_InpRetryDelayMs;
bool cfg_InpUseICTTime;
bool cfg_InpUseManualNYOffset;
int cfg_InpNYOffsetHours;
bool cfg_InpAutoNYDST;
int cfg_InpNYOffsetSummerHours;
bool cfg_InpUseKillzoneAsia;
bool cfg_InpUseKillzoneLondon;
bool cfg_InpUseKillzoneNY;
int cfg_InpATRPeriod;
int cfg_InpADXPeriod;
int cfg_InpRSIPeriod;
int cfg_InpEMA_Fast;
int cfg_InpEMA_Slow;
int cfg_InpRegimeConfirmBarsH1;
int cfg_InpRegimeLockBarsH1;
int cfg_InpPivotLen;
int cfg_InpPivotConfirmBars;
int cfg_InpMaxBarsAfterBOS;
double cfg_InpEqToleranceATR;
double cfg_InpEqToleranceMinPoints;
int cfg_InpEqClusterMin;
int cfg_InpEqScanBars;
double cfg_InpDisplacementATR;
double cfg_InpDisplacementBodyRatio;
int cfg_InpDisplacementSearchBars;
int cfg_InpOBLookback;
int cfg_InpOBMaxAgeBars;
ENUM_TIMEFRAMES cfg_InpOTE_HTF;
int cfg_InpOTE_SwingLookback;
double cfg_InpOTE_Min;
double cfg_InpOTE_Max;
double cfg_InpMinPDArrayDistance;
double cfg_InpMinPDArrayATR;
int cfg_InpMinPDArrayMinPoints;
bool cfg_InpUseBreakRetest;
double cfg_InpRetestTolATR;
double cfg_InpKeyLevelStepPrice;
double cfg_InpKeyNearPrice;
double cfg_InpKeyChaseMaxDistPrice;
bool cfg_InpUseFVGFeature;
int cfg_InpFVGScanBars;
double cfg_InpFVGMaxDistATR;
bool cfg_InpUseFibFilter;
double cfg_InpFibBaseMin;
double cfg_InpFibBaseMax;
double cfg_InpFibTolPrice;
bool cfg_InpUseOTEBonus;
double cfg_InpOTEMin;
double cfg_InpOTEMax;
int cfg_InpOTEBonusPoints;
bool cfg_InpUseFootprintProxy;
int cfg_InpFP_VolMAPeriod;
double cfg_InpFP_VolSpikeRatio;
double cfg_InpFP_BodyMinRatio;
double cfg_InpFP_CloseSideMin;
double cfg_InpFP_AbsorpVolRatio;
double cfg_InpFP_AbsorpRangeATR;
bool cfg_InpFP_RequireAcceptance;
int cfg_InpFP_ScoreBonus;
bool cfg_InpUseSupplyDemandBonus;
ENUM_TIMEFRAMES cfg_InpSD_TF;
int cfg_InpSD_LookbackBars;
double cfg_InpSD_MinImpulseATR;
int cfg_InpSD_MaxBaseBars;
double cfg_InpSD_ZonePadATR;
double cfg_InpSD_MaxDistATR;
int cfg_InpSD_BonusPoints;
int cfg_InpSD_FreshnessBonus;
bool cfg_InpUseCandleBonus;
int cfg_InpCandleBonusPoints;
bool cfg_InpUseMomentumBonus;
int cfg_InpMomentumBonusPoints;
bool cfg_InpRequireBiasAlignWithSweep;
bool cfg_InpUseSpikeGuard;
double cfg_InpSpikeMultATR;
double cfg_InpSL_ATR_Mult;
double cfg_InpSL_MinBufferPrice;
bool cfg_InpUseMMSL;
int cfg_InpMMSL_Pips;
double cfg_InpMMSL_ExtraBufferPrice;
double cfg_InpTP_RR_Main;
double cfg_InpMinRRAllowed;
bool cfg_InpUseTP1Partial;
double cfg_InpTP1_CloseFrac;
bool cfg_InpTP1_UseKeyLevelFirst;
bool cfg_InpUseSmartBE;
double cfg_InpBE_MinProfitR;
double cfg_InpBE_OffsetPrice;
bool cfg_InpUseATRTrailAfterTP1;
double cfg_InpTrailATR_Mult;
double cfg_InpTrailMinImprovePrice;
bool cfg_InpTrailOnNewBarOnly;
double cfg_InpBaseRiskPct;
double cfg_InpMaxLotCap;
bool cfg_InpUseLowVolFilter;
ENUM_TIMEFRAMES cfg_InpVolTF;
int cfg_InpVolMAPeriod;
double cfg_InpLowVolFactor;
bool cfg_InpUseSpreadMultiple;
double cfg_InpSpreadMultiple;
int cfg_InpSpreadMultipleBlockMin;
bool cfg_InpUseSpreadInstability;
int cfg_InpSpreadAvgBarsH1;
double cfg_InpSpreadSpikeFactor;
int cfg_InpSpreadSpikeBlockMin;
bool cfg_InpUseRolloverBlock;
string cfg_InpRolloverStart;
string cfg_InpRolloverEnd;
bool cfg_InpUseDailyTradeControl;
int cfg_InpHardMaxTradesPerDay;
bool cfg_InpUseMaxDailyLossLock;
double cfg_InpMaxDailyLossPct;
bool cfg_InpUseSoftEquityLock;
double cfg_InpSoftEqTrigger1;
double cfg_InpSoftEqFloor1;
double cfg_InpSoftEqTrigger2;
double cfg_InpSoftEqFloor2;
int cfg_InpCooldownBarsAfterEntry;
bool cfg_InpUseAntiChop;
int cfg_InpLossBlock2_Hours;
int cfg_InpLossBlock3_Hours;
double cfg_InpRiskMultAfter3Loss;
int cfg_InpRiskCutAfter3Loss_H;
bool cfg_InpUseRSIAfterLoss;
int cfg_InpLossStreakForRSI;
bool cfg_InpUsePyramiding;
int cfg_InpMaxAdds;
double cfg_InpPyramidMinProfitR;
bool cfg_InpPyramidRequireMainBE;
double cfg_InpPyramidSpacingATR;
bool cfg_InpPyramidOnlyInTrend;
bool cfg_InpPyramidRequireAdxRising;
bool cfg_InpPyramidUsePeakDDCap;
double cfg_InpPyramidMaxPeakDDPct;
double cfg_InpAddRiskMult1;
double cfg_InpAddRiskMult2;
bool cfg_InpEnableCSV;
string cfg_InpCSVName;

double cfg_KeyLevelStepPoints;
double cfg_KeyNearPoints;
double cfg_KeyChaseMaxDistPoints;
double cfg_EqToleranceMinPoints;
double cfg_SL_MinBufferPoints;
double cfg_MMSL_ExtraBufferPoints;
double cfg_BE_OffsetPoints;
double cfg_TrailMinImprovePoints;
double cfg_FibTolPoints;
double cfg_MinPDArrayDistancePoints;
int cfg_MinPDArrayMinPoints;

enum SkipMask
{
   SKIP_NONE = 0,
   SKIP_SESSION = 1 << 0,
   SKIP_ROLLOVER = 1 << 1,
   SKIP_SPREAD = 1 << 2,
   SKIP_SPREAD_MULT = 1 << 3,
   SKIP_SPREAD_INSTAB = 1 << 4,
   SKIP_LOWVOL = 1 << 5,
   SKIP_DAILY_LOCK = 1 << 6,
   SKIP_COOLDOWN = 1 << 7,
   SKIP_LOSS_BLOCK = 1 << 8,
   SKIP_DAILY_MAX = 1 << 9,
   SKIP_DAILY_SCORE = 1 << 10,
   SKIP_STOPS = 1 << 11,
   SKIP_KILLZONE = 1 << 12,
   SKIP_PDARRAY = 1 << 13
};

enum EntryMask
{
   ENTRY_NONE = 0,
   ENTRY_BIAS = 1 << 0,
   ENTRY_PIVOT = 1 << 1,
   ENTRY_HL_LH = 1 << 2,
   ENTRY_BOS_CLOSE = 1 << 3,
   ENTRY_BOS_RETEST = 1 << 4,
   ENTRY_KEYLEVEL = 1 << 5,
   ENTRY_ANTICHASE = 1 << 6,
   ENTRY_FVG = 1 << 7,
   ENTRY_FIB = 1 << 8,
   ENTRY_FOOTPRINT = 1 << 9,
   ENTRY_SPIKE = 1 << 10,
   ENTRY_RSI_LOSS = 1 << 11,
   ENTRY_MMSL = 1 << 12,
   ENTRY_RR = 1 << 13,
   ENTRY_KILLZONE = 1 << 14,
   ENTRY_SWEEP = 1 << 15,
   ENTRY_DISPLACEMENT = 1 << 16,
   ENTRY_MSS = 1 << 17,
   ENTRY_OB_RTO = 1 << 18,
   ENTRY_OTE = 1 << 19,
   ENTRY_PDARRAY = 1 << 20,
   ENTRY_SR = 1 << 21,
   ENTRY_SD = 1 << 22,
   ENTRY_CANDLE = 1 << 23,
   ENTRY_MOM = 1 << 24
};

// --- forward declarations (needed for MQL5 compiler order)
double NormalizeVolumeByStep(double volume);

int EnsureIndicatorHandle(const int type, const string sym, ENUM_TIMEFRAMES tf, int p1, int p2, int p3);
double ReadIndicatorValue(const int handle, const int bufferIndex, const int shift);
void ReleaseIndicatorsCache();

struct MarketContext
{
   double bid;
   double ask;
   double mid;
   double spreadPts;
   double atrM15;
   double atrH1;
   double adxH1;
   double rsi1;
   double rsi2;
   double emaFast;
   double emaSlow;
   int killzoneActive;
   double pdh;
   double pdl;
   double hod;
   double lod;
   int lossStreak;
   int dayTrades;
   double spreadEma;
};

void BuildContext(MarketContext &ctx);

bool CalculateEntryCore(TradeDir &dir, double &entry, double &sl, double &tp, double &tp1, double &riskR,
                        int &setupScore, int &timingScore, int &totalScore, int &skipMask, int &entryMask,
                        double &nearestKey, double &bosLevel, int &bosAgeBars, int &killzoneActive,
                        double &pdh, double &pdl, double &psh, double &psl, double &hod, double &lod,
                        int &sweepDir, double &sweepLevel, double &displacementScore,
                        double &obHigh, double &obLow, double &obMT, int &oteOk,
                        int &sdHit, int &sdType, double &sdDistATR, int &sdFresh,
                        int &candleHit, int &candleType,
                        int &momHit, double &rsi1, double &rsi2);

void LogCSVEx(const string event, TradeDir dir, double entry, double sl, double tp, double tp1, double lot,
              int dailyScore, int setup, int timing, int total, int skipMask, int entryMask,
              int retcode, int lasterr, double bosLevel, int bosAgeBars, double nearestKey,
              int killzoneActive, double pdh, double pdl, double psh, double psl, double hod, double lod,
              int sweepDir, double sweepLevel, double displacementScore, double obHigh, double obLow, double obMT,
              int oteOk, int sdHit, int sdType, double sdDistATR, int sdFresh,
              int candleHit, int candleType, int momHit, double rsi1, double rsi2);

string GVName(const string key)
{
   return "XK_" + key + "_" + g_symbol + "_" + (string)cfg_InpMagic;
}

double GVGetDouble(const string key, double defval)
{
   string name = GVName(key);
   if(!GlobalVariableCheck(name))
   {
      GlobalVariableSet(name, defval);
      return defval;
   }
   return GlobalVariableGet(name);
}

void GVSetDouble(const string key, double val)
{
   GlobalVariableSet(GVName(key), val);
}

int GVGetInt(const string key, int defval)
{
   return (int)GVGetDouble(key, defval);
}

void GVSetInt(const string key, int val)
{
   GVSetDouble(key, (double)val);
}

bool IsNewBar(ENUM_TIMEFRAMES tf, datetime &lastBarTime)
{
   datetime t = iTime(g_symbol, tf, 0);
   if(t != lastBarTime)
   {
      lastBarTime = t;
      return true;
   }
   return false;
}

string ResolveSymbol()
{
   if(StringLen(cfg_InpSymbolOverride) > 0)
      return cfg_InpSymbolOverride;
   return _Symbol;
}

bool ContainsAny(const string text, const string &tokens[])
{
   for(int i = 0; i < ArraySize(tokens); i++)
   {
      if(StringFind(text, tokens[i]) >= 0)
         return true;
   }
   return false;
}

SymbolProfile DetectSymbolProfile(const string symbol)
{
   string symUpper = symbol;
   StringToUpper(symUpper);
   if(StringFind(symUpper, "XAU") >= 0 || StringFind(symUpper, "GOLD") >= 0)
      return PROFILE_FX_MAJORS_5DIG;
   string indexTokens[] = {"US30", "DJ30", "WS30", "US30CASH",
                           "NAS100", "USTEC", "US100", "NAS",
                           "SPX500", "SPX", "US500", "US_500", "SP500",
                           "GER40", "DE40", "DAX", "DAX40",
                           "FTSEMIB", "FTSE_MIB", "ITA40",
                           "UK100", "FTSE"};
   if(ContainsAny(symUpper, indexTokens))
      return PROFILE_INDICES;
   if(StringFind(symUpper, "JPY") >= 0)
      return PROFILE_FX_JPY_3DIG;
   return PROFILE_FX_MAJORS_5DIG;
}

bool IsGoldSymbol(const string symbol)
{
   string symUpper = symbol;
   StringToUpper(symUpper);
   return (StringFind(symUpper, "XAU") >= 0 || StringFind(symUpper, "GOLD") >= 0);
}

string ProfileName(SymbolProfile profile)
{
   switch(profile)
   {
      case PROFILE_FX_MAJORS_5DIG:
         return "FX_MAJORS_5DIG";
      case PROFILE_FX_JPY_3DIG:
         return "FX_JPY_3DIG";
      case PROFILE_INDICES:
         return "INDICES";
   }
   return "UNKNOWN";
}

double PriceFromPoints(double points)
{
   return points * g_point;
}

double PointsFromPrice(double price)
{
   return (g_point > 0.0) ? price / g_point : 0.0;
}

double PriceFromPips(double pips)
{
   return pips * g_pip;
}

double PipsFromPrice(double price)
{
   return (g_pip > 0.0) ? price / g_pip : 0.0;
}

double PointsFromPips(double pips)
{
   double price = PriceFromPips(pips);
   return PointsFromPrice(price);
}

double PipsFromPoints(double points)
{
   double price = PriceFromPoints(points);
   return PipsFromPrice(price);
}

// Canonical helpers to avoid pip/point ambiguity in risk and stops.
double GetPipSize() { return g_pip; }
double GetPointSize() { return g_point; }
double PriceToPoints(double priceDistance) { return PointsFromPrice(priceDistance); }
double PointsToPrice(double points) { return PriceFromPoints(points); }
double PipsToPoints(double pips) { return PointsFromPips(pips); }
double PointsToPips(double points) { return PipsFromPoints(points); }

double NormalizePrice(double p)
{
   return NormalizeDouble(p, g_digits);
}

double PipPrice()
{
   if(cfg_InpPipPrice > 0.0)
      return cfg_InpPipPrice;
   return g_pip;
}

double AutoPipSize(bool useOverride)
{
   if(useOverride && cfg_InpPipPrice > 0.0)
      return cfg_InpPipPrice;

   if(g_profile == PROFILE_INDICES)
      return 1.0;

   if(g_digits == 3 || g_digits == 5)
      return g_point * 10.0;

   return g_point;
}

double SpreadPoints()
{
   double ask = SymbolInfoDouble(g_symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(g_symbol, SYMBOL_BID);
   return (ask - bid) / g_point;
}

int MinutesOfDay(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return dt.hour * 60 + dt.min;
}

datetime MakeDateTime(int year, int mon, int day, int hour, int min, int sec)
{
   MqlDateTime dt;
   dt.year = year;
   dt.mon = mon;
   dt.day = day;
   dt.hour = hour;
   dt.min = min;
   dt.sec = sec;
   return StructToTime(dt);
}

datetime FirstSundayUTC(int year, int mon, int hour, int min)
{
   MqlDateTime dt;
   TimeToStruct(MakeDateTime(year, mon, 1, 0, 0, 0), dt);
   int firstSunday = 1 + ((7 - dt.day_of_week) % 7);
   return MakeDateTime(year, mon, firstSunday, hour, min, 0);
}

datetime SecondSundayUTC(int year, int mon, int hour, int min)
{
   datetime firstSunday = FirstSundayUTC(year, mon, 0, 0);
   MqlDateTime dt;
   TimeToStruct(firstSunday, dt);
   int secondSunday = dt.day + 7;
   return MakeDateTime(year, mon, secondSunday, hour, min, 0);
}

bool IsUSDST(datetime utcTime)
{
   MqlDateTime dt;
   TimeToStruct(utcTime, dt);
   datetime dstStart = SecondSundayUTC(dt.year, 3, 7, 0);
   datetime dstEnd = FirstSundayUTC(dt.year, 11, 6, 0);
   return (utcTime >= dstStart && utcTime < dstEnd);
}

int EffectiveNYOffsetHours()
{
   if(!cfg_InpAutoNYDST)
      return cfg_InpNYOffsetHours;
   datetime nowUtc = TimeGMT();
   return IsUSDST(nowUtc) ? cfg_InpNYOffsetSummerHours : cfg_InpNYOffsetHours;
}

int GetServerUtcOffsetSeconds()
{
   return (int)(TimeTradeServer() - TimeGMT());
}

datetime ToNYTime(datetime serverTime)
{
   int serverOffset = GetServerUtcOffsetSeconds();
   int nyOffset = cfg_InpUseManualNYOffset ? (EffectiveNYOffsetHours() * 3600) : (-5 * 3600);
   return serverTime - serverOffset + nyOffset;
}

int MinutesOfDayNY(datetime serverTime)
{
   datetime ny = ToNYTime(serverTime);
   return MinutesOfDay(ny);
}

bool KillzoneActive(bool &isAsia, bool &isLondon, bool &isNY)
{
   isAsia = false;
   isLondon = false;
   isNY = false;
   if(!cfg_InpUseICTTime)
      return false;
   int minNY = MinutesOfDayNY(TimeCurrent());
   if(cfg_InpUseKillzoneAsia && minNY >= 20 * 60 && minNY < 22 * 60)
      isAsia = true;
   if(cfg_InpUseKillzoneLondon && minNY >= 2 * 60 && minNY < 5 * 60)
      isLondon = true;
   if(cfg_InpUseKillzoneNY && minNY >= 7 * 60 && minNY < 9 * 60)
      isNY = true;
   return (isAsia || isLondon || isNY);
}

bool TimeInRange(const string start, const string end)
{
   int sh = StringToInteger(StringSubstr(start, 0, 2));
   int sm = StringToInteger(StringSubstr(start, 3, 2));
   int eh = StringToInteger(StringSubstr(end, 0, 2));
   int em = StringToInteger(StringSubstr(end, 3, 2));

   int startMin = sh * 60 + sm;
   int endMin = eh * 60 + em;
   int nowMin = MinutesOfDay(TimeCurrent());

   if(startMin <= endMin)
      return (nowMin >= startMin && nowMin < endMin);
   return (nowMin >= startMin || nowMin < endMin);
}

void UpdateSpreadEMA()
{
   double spread = SpreadPoints();
   double alpha = 2.0 / (cfg_InpSpreadAvgBarsH1 + 1.0);
   if(g_spreadEma <= 0.0)
      g_spreadEma = spread;
   else
      g_spreadEma = alpha * spread + (1.0 - alpha) * g_spreadEma;
}

bool SpreadMultipleWouldBlock(double spread, double spreadEma)
{
   if(!cfg_InpUseSpreadMultiple || spreadEma <= 0.0)
      return false;
   return (spread > spreadEma * cfg_InpSpreadMultiple);
}

bool SpreadInstabilityWouldBlock(double spread, double spreadEma)
{
   if(!cfg_InpUseSpreadInstability || spreadEma <= 0.0)
      return false;
   return (spread > spreadEma * cfg_InpSpreadSpikeFactor);
}

bool SpreadMultipleBlocked()
{
   if(!cfg_InpUseSpreadMultiple)
      return false;

   double spread = SpreadPoints();
   if(g_spreadEma <= 0.0)
      return false;

   if(spread > g_spreadEma * cfg_InpSpreadMultiple)
   {
      datetime until = TimeCurrent() + cfg_InpSpreadMultipleBlockMin * 60;
      GVSetDouble("spreadBlockUntil", (double)until);
   }

   datetime blockUntil = (datetime)GVGetDouble("spreadBlockUntil", 0.0);
   return (blockUntil > TimeCurrent());
}

bool SpreadInstabilityBlocked()
{
   if(!cfg_InpUseSpreadInstability || g_spreadEma <= 0.0)
      return false;

   double spread = SpreadPoints();
   if(spread > g_spreadEma * cfg_InpSpreadSpikeFactor)
   {
      datetime until = TimeCurrent() + cfg_InpSpreadSpikeBlockMin * 60;
      GVSetDouble("spreadSpikeUntil", (double)until);
   }

   datetime blockUntil = (datetime)GVGetDouble("spreadSpikeUntil", 0.0);
   return (blockUntil > TimeCurrent());
}

bool SessionAllowed()
{
   if(!cfg_InpUseSessionFilter)
      return true;
   int hour = TimeHour(TimeCurrent());
   if(cfg_InpStartHour <= cfg_InpEndHour)
      return (hour >= cfg_InpStartHour && hour <= cfg_InpEndHour);
   return (hour >= cfg_InpStartHour || hour <= cfg_InpEndHour);
}

bool RolloverBlocked()
{
   if(!cfg_InpUseRolloverBlock)
      return false;
   return TimeInRange(cfg_InpRolloverStart, cfg_InpRolloverEnd);
}

int EnsureIndicatorHandle(const int type, const string sym, ENUM_TIMEFRAMES tf, int p1, int p2, int p3)
{
   for(int i = 0; i < ArraySize(g_indicators.entries); i++)
   {
      IndicatorEntry e = g_indicators.entries[i];
      if(e.type == type && e.sym == sym && e.tf == tf && e.p1 == p1 && e.p2 == p2 && e.p3 == p3)
         return e.handle;
   }

   int handle = INVALID_HANDLE;
   if(type == 1)
      handle = iATR(sym, tf, p1);
   else if(type == 2)
      handle = iADX(sym, tf, p1);
   else if(type == 3)
      handle = iRSI(sym, tf, p1, p2);
   else if(type == 4)
      handle = iMA(sym, tf, p1, p2, (ENUM_MA_METHOD)p3, PRICE_CLOSE);

   if(handle == INVALID_HANDLE)
      return INVALID_HANDLE;

   IndicatorEntry ne;
   ne.type = type;
   ne.sym = sym;
   ne.tf = tf;
   ne.p1 = p1;
   ne.p2 = p2;
   ne.p3 = p3;
   ne.handle = handle;
   int n = ArraySize(g_indicators.entries);
   ArrayResize(g_indicators.entries, n + 1);
   g_indicators.entries[n] = ne;
   return handle;
}

double ReadIndicatorValue(const int handle, const int bufferIndex, const int shift)
{
   if(handle == INVALID_HANDLE)
      return EMPTY_VALUE;
   double buf[];
   ArraySetAsSeries(buf, true);
   if(CopyBuffer(handle, bufferIndex, shift, 1, buf) <= 0)
      return EMPTY_VALUE;
   return buf[0];
}

void ReleaseIndicatorsCache()
{
   for(int i = 0; i < ArraySize(g_indicators.entries); i++)
   {
      if(g_indicators.entries[i].handle != INVALID_HANDLE)
      {
         IndicatorRelease(g_indicators.entries[i].handle);
         g_indicators.entries[i].handle = INVALID_HANDLE;
      }
   }
   ArrayResize(g_indicators.entries, 0);
}

double GetRSI(const string sym, ENUM_TIMEFRAMES tf, int period, int applied_price, int shift = 0)
{
   int handle = EnsureIndicatorHandle(3, sym, tf, period, applied_price, 0);
   return ReadIndicatorValue(handle, 0, shift);
}

double GetMA(const string sym, ENUM_TIMEFRAMES tf, int period, int ma_shift, ENUM_MA_METHOD method, int applied_price, int shift = 0)
{
   int handle = EnsureIndicatorHandle(4, sym, tf, period, ma_shift, (int)method);
   return ReadIndicatorValue(handle, 0, shift);
}

double GetATR(const string sym, ENUM_TIMEFRAMES tf, int period, int shift = 0)
{
   int handle = EnsureIndicatorHandle(1, sym, tf, period, 0, 0);
   return ReadIndicatorValue(handle, 0, shift);
}

double GetADX(const string sym, ENUM_TIMEFRAMES tf, int period, int shift = 0)
{
   int handle = EnsureIndicatorHandle(2, sym, tf, period, 0, 0);
   return ReadIndicatorValue(handle, 0, shift);
}

double ATR(ENUM_TIMEFRAMES tf, int shift)
{
   return GetATR(g_symbol, tf, cfg_InpATRPeriod, shift);
}

double ADX(ENUM_TIMEFRAMES tf, int shift)
{
   return GetADX(g_symbol, tf, cfg_InpADXPeriod, shift);
}

double RSI(ENUM_TIMEFRAMES tf, int shift)
{
   return GetRSI(g_symbol, tf, cfg_InpRSIPeriod, PRICE_CLOSE, shift);
}

double EMA(ENUM_TIMEFRAMES tf, int period, int shift)
{
   return GetMA(g_symbol, tf, period, 0, MODE_EMA, PRICE_CLOSE, shift);
}

double VolumeMA(ENUM_TIMEFRAMES tf, int period, int shift)
{
   double sum = 0.0;
   for(int i = shift; i < shift + period; i++)
      sum += (double)iVolume(g_symbol, tf, i);
   return sum / MathMax(1, period);
}

bool LowVolumeBlocked()
{
   if(!cfg_InpUseLowVolFilter)
      return false;

   double vol = (double)iVolume(g_symbol, cfg_InpVolTF, 0);
   double avg = VolumeMA(cfg_InpVolTF, cfg_InpVolMAPeriod, 1);
   if(avg <= 0.0)
      return false;
   return vol < avg * cfg_InpLowVolFactor;
}

TradeDir BiasH1()
{
   double emaFast = EMA(PERIOD_H1, cfg_InpEMA_Fast, 1);
   double emaSlow = EMA(PERIOD_H1, cfg_InpEMA_Slow, 1);
   double close = iClose(g_symbol, PERIOD_H1, 1);
   if(emaFast > emaSlow && close > emaFast)
      return DIR_LONG;
   if(emaFast < emaSlow && close < emaFast)
      return DIR_SHORT;
   return DIR_NONE;
}

RegimeState ClassifyRegime()
{
   double atr = ATR(PERIOD_H1, 1);
   double close = iClose(g_symbol, PERIOD_H1, 1);
   double atrRel = (close > 0.0) ? (atr / close) * 100.0 : 0.0;
   bool isExpansion = atrRel > 0.18;
   double adx = ADX(PERIOD_H1, 1);
   TradeDir bias = BiasH1();

   if(isExpansion && adx < 18.0)
      return REGIME_EXPANSION;
   if(adx >= 25.0 && bias != DIR_NONE)
      return REGIME_TREND;
   if(adx >= 18.0)
      return REGIME_TRANSITION;
   return REGIME_RANGE;
}

RegimeState UpdateRegime()
{
   RegimeState current = (RegimeState)GVGetInt("regime", REGIME_RANGE);
   int lockBars = GVGetInt("regimeLock", 0);
   int confirmBars = GVGetInt("regimeConfirm", 0);

   RegimeState next = ClassifyRegime();

   if(lockBars > 0)
   {
      GVSetInt("regimeLock", lockBars - 1);
      return current;
   }

   if(next != current)
   {
      confirmBars++;
      if(confirmBars >= cfg_InpRegimeConfirmBarsH1)
      {
         current = next;
         GVSetInt("regime", (int)current);
         GVSetInt("regimeConfirm", 0);
         GVSetInt("regimeLock", cfg_InpRegimeLockBarsH1);
         return current;
      }
      GVSetInt("regimeConfirm", confirmBars);
      return current;
   }

   GVSetInt("regimeConfirm", 0);
   return current;
}

bool IsPivotHigh(int index)
{
   int bars = iBars(g_symbol, PERIOD_M15);
   if(bars <= 0 || index <= 0 || index >= bars)
      return false;
   if(index - cfg_InpPivotLen < 0 || index + cfg_InpPivotLen >= bars)
      return false;
   double high = iHigh(g_symbol, PERIOD_M15, index);
   for(int j = 1; j <= cfg_InpPivotLen; j++)
   {
      if(high <= iHigh(g_symbol, PERIOD_M15, index - j) || high <= iHigh(g_symbol, PERIOD_M15, index + j))
         return false;
   }
   return true;
}

bool IsPivotLow(int index)
{
   int bars = iBars(g_symbol, PERIOD_M15);
   if(bars <= 0 || index <= 0 || index >= bars)
      return false;
   if(index - cfg_InpPivotLen < 0 || index + cfg_InpPivotLen >= bars)
      return false;
   double low = iLow(g_symbol, PERIOD_M15, index);
   for(int j = 1; j <= cfg_InpPivotLen; j++)
   {
      if(low >= iLow(g_symbol, PERIOD_M15, index - j) || low >= iLow(g_symbol, PERIOD_M15, index + j))
         return false;
   }
   return true;
}

bool IsConfirmedPivotHigh(int index)
{
   int bars = iBars(g_symbol, PERIOD_M15);
   if(bars <= 0 || index <= 0 || index >= bars)
      return false;
   if(index - cfg_InpPivotConfirmBars < 0)
      return false;
   if(!IsPivotHigh(index))
      return false;
   for(int j = 1; j <= cfg_InpPivotConfirmBars; j++)
   {
      if(iHigh(g_symbol, PERIOD_M15, index - j) >= iHigh(g_symbol, PERIOD_M15, index))
         return false;
   }
   return true;
}

bool IsConfirmedPivotLow(int index)
{
   int bars = iBars(g_symbol, PERIOD_M15);
   if(bars <= 0 || index <= 0 || index >= bars)
      return false;
   if(index - cfg_InpPivotConfirmBars < 0)
      return false;
   if(!IsPivotLow(index))
      return false;
   for(int j = 1; j <= cfg_InpPivotConfirmBars; j++)
   {
      if(iLow(g_symbol, PERIOD_M15, index - j) <= iLow(g_symbol, PERIOD_M15, index))
         return false;
   }
   return true;
}

int BOSAgeBars(double &bosLevel)
{
   bosLevel = GVGetDouble("bosLevel", 0.0);
   datetime bosTime = (datetime)GVGetDouble("bosTime", 0.0);
   if(bosTime == 0)
      return -1;
   return iBarShift(g_symbol, PERIOD_M15, bosTime, true);
}


datetime GetTradingDayStart(datetime t)
{
   datetime ny = ToNYTime(t);
   MqlDateTime dt;
   TimeToStruct(ny, dt);
   dt.hour = 0;
   dt.min = 0;
   dt.sec = 0;
   datetime nyStart = StructToTime(dt);
   int nyOffset = cfg_InpUseManualNYOffset ? (EffectiveNYOffsetHours() * 3600) : (-5 * 3600);
   return nyStart - nyOffset;
}

int GetTradingDayId(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(ToNYTime(t), dt);
   return dt.year * 10000 + dt.mon * 100 + dt.day;
}

int NYDayId(datetime serverTime)
{
   return GetTradingDayId(serverTime);
}

void GetPDLevels(double &pdh, double &pdl)
{
   pdh = iHigh(g_symbol, PERIOD_D1, 1);
   pdl = iLow(g_symbol, PERIOD_D1, 1);
}

void GetHODLOD(double &hod, double &lod)
{
   hod = -DBL_MAX;
   lod = DBL_MAX;
   int bars = iBars(g_symbol, PERIOD_M15);
   if(bars <= 0)
   {
      hod = iHigh(g_symbol, PERIOD_D1, 0);
      lod = iLow(g_symbol, PERIOD_D1, 0);
      return;
   }
   int todayId = NYDayId(TimeCurrent());
   for(int i = 0; i < bars; i++)
   {
      datetime t = iTime(g_symbol, PERIOD_M15, i);
      if(NYDayId(t) != todayId)
         break;
      double high = iHigh(g_symbol, PERIOD_M15, i);
      double low = iLow(g_symbol, PERIOD_M15, i);
      hod = MathMax(hod, high);
      lod = MathMin(lod, low);
   }
   if(hod == -DBL_MAX)
      hod = iHigh(g_symbol, PERIOD_D1, 0);
   if(lod == DBL_MAX)
      lod = iLow(g_symbol, PERIOD_D1, 0);
}


void GetHODLOD_Cached(double &hod, double &lod)
{
   int dayId = NYDayId(TimeCurrent());
   datetime barT = iTime(g_symbol, PERIOD_M15, 0);
   if(g_hodlodDayId != dayId || g_hodlodBarTime != barT)
   {
      GetHODLOD(g_cachedHod, g_cachedLod);
      g_hodlodDayId = dayId;
      g_hodlodBarTime = barT;
   }
   hod = g_cachedHod;
   lod = g_cachedLod;
}

bool GetSessionHighLowNY(int startMin, int endMin, int dayOffset, double &high, double &low)
{
   high = -DBL_MAX;
   low = DBL_MAX;
   int bars = iBars(g_symbol, PERIOD_M15);
   if(bars <= 0)
      return false;
   int targetDay = NYDayId(TimeCurrent() + dayOffset * 86400);
   for(int i = 0; i < bars; i++)
   {
      datetime t = iTime(g_symbol, PERIOD_M15, i);
      if(NYDayId(t) != targetDay)
         continue;
      int minNY = MinutesOfDayNY(t);
      if(minNY >= startMin && minNY < endMin)
      {
         high = MathMax(high, iHigh(g_symbol, PERIOD_M15, i));
         low = MathMin(low, iLow(g_symbol, PERIOD_M15, i));
      }
   }
   return (high > -DBL_MAX && low < DBL_MAX);
}

void GetPSHPSL(double &psh, double &psl)
{
   psh = 0.0;
   psl = 0.0;
   int minNY = MinutesOfDayNY(TimeCurrent());
   double high = 0.0;
   double low = 0.0;
   if(minNY >= 9 * 60)
   {
      if(GetSessionHighLowNY(7 * 60, 9 * 60, 0, high, low))
      {
         psh = high;
         psl = low;
         return;
      }
   }
   if(minNY >= 5 * 60)
   {
      if(GetSessionHighLowNY(2 * 60, 5 * 60, 0, high, low))
      {
         psh = high;
         psl = low;
         return;
      }
   }
   if(GetSessionHighLowNY(20 * 60, 22 * 60, -1, high, low))
   {
      psh = high;
      psl = low;
   }
}

bool FindEqualHighCluster(double &level)
{
   double atr = ATR(PERIOD_M15, 1);
   double tol = MathMax(atr * cfg_InpEqToleranceATR, cfg_EqToleranceMinPoints * g_point);
   int count = 0;
   level = 0.0;
   int bars = iBars(g_symbol, PERIOD_M15);
   int scanBars = MathMin(cfg_InpEqScanBars, bars - 1);
   if(scanBars <= 2)
      return false;
   for(int i = 2; i < scanBars; i++)
   {
      if(!IsConfirmedPivotHigh(i))
         continue;
      double high = iHigh(g_symbol, PERIOD_M15, i);
      if(count == 0)
      {
         level = high;
         count = 1;
      }
      else if(MathAbs(high - level) <= tol)
      {
         count++;
      }
      if(count >= cfg_InpEqClusterMin)
         return true;
   }
   return false;
}

bool FindEqualLowCluster(double &level)
{
   double atr = ATR(PERIOD_M15, 1);
   double tol = MathMax(atr * cfg_InpEqToleranceATR, cfg_EqToleranceMinPoints * g_point);
   int count = 0;
   level = 0.0;
   int bars = iBars(g_symbol, PERIOD_M15);
   int scanBars = MathMin(cfg_InpEqScanBars, bars - 1);
   if(scanBars <= 2)
      return false;
   for(int i = 2; i < scanBars; i++)
   {
      if(!IsConfirmedPivotLow(i))
         continue;
      double low = iLow(g_symbol, PERIOD_M15, i);
      if(count == 0)
      {
         level = low;
         count = 1;
      }
      else if(MathAbs(low - level) <= tol)
      {
         count++;
      }
      if(count >= cfg_InpEqClusterMin)
         return true;
   }
   return false;
}

bool DetectLiquiditySweep(TradeDir &sweepDir, double &sweepLevel)
{
   sweepDir = DIR_NONE;
   sweepLevel = 0.0;
   if(iBars(g_symbol, PERIOD_M15) <= 1)
      return false;
   double eqHigh = 0.0;
   double eqLow = 0.0;
   bool hasHigh = FindEqualHighCluster(eqHigh);
   bool hasLow = FindEqualLowCluster(eqLow);
   double high1 = iHigh(g_symbol, PERIOD_M15, 1);
   double low1 = iLow(g_symbol, PERIOD_M15, 1);
   double close1 = iClose(g_symbol, PERIOD_M15, 1);
   double atr = ATR(PERIOD_M15, 1);
   double tol = MathMax(atr * cfg_InpEqToleranceATR, cfg_EqToleranceMinPoints * g_point);
   if(hasHigh && high1 > eqHigh + tol && close1 < eqHigh)
   {
      sweepDir = DIR_SHORT;
      sweepLevel = eqHigh;
      return true;
   }
   if(hasLow && low1 < eqLow - tol && close1 > eqLow)
   {
      sweepDir = DIR_LONG;
      sweepLevel = eqLow;
      return true;
   }
   return false;
}

bool DisplacementOk(TradeDir dir, double &score)
{
   score = 0.0;
   if(iBars(g_symbol, PERIOD_M15) <= 1)
      return false;
   double high1 = iHigh(g_symbol, PERIOD_M15, 1);
   double low1 = iLow(g_symbol, PERIOD_M15, 1);
   double open1 = iOpen(g_symbol, PERIOD_M15, 1);
   double close1 = iClose(g_symbol, PERIOD_M15, 1);
   double range = high1 - low1;
   double body = MathAbs(close1 - open1);
   double atr = ATR(PERIOD_M15, 1);
   double bodyRatio = (range > 0.0) ? body / range : 0.0;
   bool dirOk = (dir == DIR_LONG) ? (close1 > open1) : (close1 < open1);
   bool sizeOk = range >= atr * cfg_InpDisplacementATR && bodyRatio >= cfg_InpDisplacementBodyRatio;
   if(dirOk && sizeOk)
      score = range / (atr > 0.0 ? atr : 1.0);
   return dirOk && sizeOk;
}

bool FindOrderBlock(TradeDir dir, double &obHigh, double &obLow, double &obMT, int &obAgeBars)
{
   obHigh = 0.0;
   obLow = 0.0;
   obMT = 0.0;
   obAgeBars = -1;
   int bars = iBars(g_symbol, PERIOD_M15);
   int lookback = MathMin(cfg_InpOBLookback, bars - 1);
   if(lookback < 2)
      return false;
   for(int i = 2; i <= lookback; i++)
   {
      double open = iOpen(g_symbol, PERIOD_M15, i);
      double close = iClose(g_symbol, PERIOD_M15, i);
      bool opposite = (dir == DIR_LONG) ? (close < open) : (close > open);
      if(opposite)
      {
         obHigh = iHigh(g_symbol, PERIOD_M15, i);
         obLow = iLow(g_symbol, PERIOD_M15, i);
         obMT = (obHigh + obLow) / 2.0;
         obAgeBars = i;
         return true;
      }
   }
   return false;
}

bool OTEOk(TradeDir dir, double price, double &oteMin, double &oteMax, double &swingHigh, double &swingLow)
{
   swingHigh = -DBL_MAX;
   swingLow = DBL_MAX;
   int bars = iBars(g_symbol, cfg_InpOTE_HTF);
   if(bars <= 1)
      return false;
   int lookback = MathMin(cfg_InpOTE_SwingLookback, bars - 1);
   if(lookback < 1)
      return false;
   for(int i = 1; i <= lookback; i++)
   {
      swingHigh = MathMax(swingHigh, iHigh(g_symbol, cfg_InpOTE_HTF, i));
      swingLow = MathMin(swingLow, iLow(g_symbol, cfg_InpOTE_HTF, i));
   }
   if(swingHigh <= swingLow)
      return false;
   double range = swingHigh - swingLow;
   if(dir == DIR_LONG)
   {
      oteMin = swingHigh - range * cfg_InpOTE_Max;
      oteMax = swingHigh - range * cfg_InpOTE_Min;
      return (price >= oteMin && price <= oteMax && price <= (swingHigh - range * 0.5));
   }
   oteMin = swingLow + range * cfg_InpOTE_Min;
   oteMax = swingLow + range * cfg_InpOTE_Max;
   return (price >= oteMin && price <= oteMax && price >= (swingLow + range * 0.5));
}

bool FindRecentPivots(double &lastHigh, double &prevHigh, double &lastLow, double &prevLow)
{
   int foundHigh = 0;
   int foundLow = 0;
   lastHigh = prevHigh = 0.0;
   lastLow = prevLow = 0.0;

   int bars = iBars(g_symbol, PERIOD_M15);
   if(bars <= 0)
      return false;
   int start = cfg_InpPivotLen + cfg_InpPivotConfirmBars;
   int end = MathMin(bars - cfg_InpPivotLen - 1, 200);
   if(end <= start)
      return false;
   for(int i = start; i < end; i++)
   {
      if(i - cfg_InpPivotConfirmBars < 0)
         continue;

      if(IsConfirmedPivotHigh(i))
      {
         if(foundHigh == 0)
            lastHigh = iHigh(g_symbol, PERIOD_M15, i);
         else if(foundHigh == 1)
            prevHigh = iHigh(g_symbol, PERIOD_M15, i);
         foundHigh++;
      }
      if(IsConfirmedPivotLow(i))
      {
         if(foundLow == 0)
            lastLow = iLow(g_symbol, PERIOD_M15, i);
         else if(foundLow == 1)
            prevLow = iLow(g_symbol, PERIOD_M15, i);
         foundLow++;
      }
      if(foundHigh >= 2 && foundLow >= 2)
         return true;
   }
   return false;
}

void StoreBOS(TradeDir dir, double bosLevel, datetime bosTime)
{
   GVSetDouble("bosLevel", bosLevel);
   GVSetDouble("bosTime", (double)bosTime);
   GVSetInt("bosDir", (int)dir);
}

bool BOSStateValid(TradeDir dir, double &bosLevel)
{
   int bosDir = GVGetInt("bosDir", 0);
   if(bosDir != (int)dir)
      return false;

   bosLevel = GVGetDouble("bosLevel", 0.0);
   datetime bosTime = (datetime)GVGetDouble("bosTime", 0.0);
   if(bosTime == 0 || bosLevel <= 0.0)
      return false;

   int shift = iBarShift(g_symbol, PERIOD_M15, bosTime, true);
   if(shift < 0)
      return false;
   return shift <= cfg_InpMaxBarsAfterBOS;
}

bool BreakRetestOk(TradeDir dir, double atrM15)
{
   if(!cfg_InpUseBreakRetest)
      return true;

   double storedBosLevel = 0.0;
   if(!BOSStateValid(dir, storedBosLevel))
      return false;

   double tol = MathMax(atrM15 * cfg_InpRetestTolATR, 5 * g_point);
   double close1 = iClose(g_symbol, PERIOD_M15, 1);
   double low1 = iLow(g_symbol, PERIOD_M15, 1);
   double high1 = iHigh(g_symbol, PERIOD_M15, 1);

   if(dir == DIR_LONG)
      return (low1 <= storedBosLevel + tol && close1 > storedBosLevel);
   if(dir == DIR_SHORT)
      return (high1 >= storedBosLevel - tol && close1 < storedBosLevel);
   return false;
}

double NearestKeyLevel(double price)
{
   double step = PriceFromPoints(cfg_KeyLevelStepPoints);
   if(step <= 0.0)
      return price;
   return MathRound(price / step) * step;
}

double KeyBelow(double price)
{
   double step = PriceFromPoints(cfg_KeyLevelStepPoints);
   return MathFloor(price / step) * step;
}

double KeyAbove(double price)
{
   double step = PriceFromPoints(cfg_KeyLevelStepPoints);
   return MathCeil(price / step) * step;
}

bool KeyLevelNearOk(double mid, double &nearest)
{
   nearest = NearestKeyLevel(mid);
   return MathAbs(mid - nearest) <= PriceFromPoints(cfg_KeyNearPoints);
}

bool AntiChaseOk(TradeDir dir, double mid, double nearest)
{
   double step = PriceFromPoints(cfg_KeyLevelStepPoints);
   if(step <= 0.0)
      return true;
   double chaseKey = nearest;
   if(dir == DIR_LONG && nearest > mid)
      chaseKey = nearest - step;
   else if(dir == DIR_SHORT && nearest < mid)
      chaseKey = nearest + step;

   double chaseMax = PriceFromPoints(cfg_KeyChaseMaxDistPoints);
   if(dir == DIR_LONG)
      return (mid - chaseKey <= chaseMax);
   if(dir == DIR_SHORT)
      return (chaseKey - mid <= chaseMax);
   return false;
}

int FVGDirection(double &zoneMid, double priceMid)
{
   if(!cfg_InpUseFVGFeature)
      return 0;

   int bars = iBars(g_symbol, PERIOD_M15);
   if(bars <= 3)
      return 0;
   double bestDist = DBL_MAX;
   int bestDir = 0;
   double bestMid = 0.0;

   int scanBars = MathMin(cfg_InpFVGScanBars, bars - 3);
   for(int i = 1; i <= scanBars; i++)
   {
      if(i + 2 >= bars)
         break;
      double low = iLow(g_symbol, PERIOD_M15, i);
      double high = iHigh(g_symbol, PERIOD_M15, i);
      double low2 = iLow(g_symbol, PERIOD_M15, i + 2);
      double high2 = iHigh(g_symbol, PERIOD_M15, i + 2);

      if(low > high2)
      {
         double mid = (low + high2) / 2.0;
         double dist = MathAbs(priceMid - mid);
         if(dist < bestDist)
         {
            bestDist = dist;
            bestDir = DIR_LONG;
            bestMid = mid;
         }
      }
      if(high < low2)
      {
         double mid = (high + low2) / 2.0;
         double dist = MathAbs(priceMid - mid);
         if(dist < bestDist)
         {
            bestDist = dist;
            bestDir = DIR_SHORT;
            bestMid = mid;
         }
      }
   }
   zoneMid = bestMid;
   return bestDir;
}

bool FVGOk(TradeDir dir, double mid, double atrM15)
{
   if(!cfg_InpUseFVGFeature)
      return true;

   double zoneMid = 0.0;
   int fvgDir = FVGDirection(zoneMid, mid);
   if(fvgDir == 0 || fvgDir != dir)
      return false;

   return MathAbs(mid - zoneMid) <= atrM15 * cfg_InpFVGMaxDistATR;
}

bool FibFilterOk(TradeDir dir, double mid, double lastLow, double lastHigh, bool &oteBonus)
{
   oteBonus = false;
   if(!cfg_InpUseFibFilter)
      return true;

   double range = MathAbs(lastHigh - lastLow);
   if(range <= 0.0)
      return false;

   double lvl50 = 0.0;
   double lvl618 = 0.0;
   if(dir == DIR_LONG)
   {
      lvl50 = lastHigh - range * cfg_InpFibBaseMin;
      lvl618 = lastHigh - range * cfg_InpFibBaseMax;
   }
   else
   {
      lvl50 = lastLow + range * cfg_InpFibBaseMin;
      lvl618 = lastLow + range * cfg_InpFibBaseMax;
   }

   double tol = PriceFromPoints(cfg_FibTolPoints);
   double minLvl = MathMin(lvl50, lvl618) - tol;
   double maxLvl = MathMax(lvl50, lvl618) + tol;
   bool inBase = (mid >= minLvl && mid <= maxLvl);

   if(cfg_InpUseOTEBonus)
   {
      double otemin = 0.0;
      double otemax = 0.0;
      if(dir == DIR_LONG)
      {
         otemin = lastHigh - range * cfg_InpOTEMax;
         otemax = lastHigh - range * cfg_InpOTEMin;
      }
      else
      {
         otemin = lastLow + range * cfg_InpOTEMin;
         otemax = lastLow + range * cfg_InpOTEMax;
      }
      double omin = MathMin(otemin, otemax);
      double omax = MathMax(otemin, otemax);
      if(mid >= omin && mid <= omax)
         oteBonus = true;
   }

   return inBase;
}

bool FootprintOk(TradeDir dir, double atrM15, bool &absorption, bool &accepted)
{
   absorption = false;
   accepted = true;
   if(!cfg_InpUseFootprintProxy)
      return true;

   double vol = (double)iVolume(g_symbol, PERIOD_M15, 1);
   double volMA = VolumeMA(PERIOD_M15, cfg_InpFP_VolMAPeriod, 2);
   double volRatio = (volMA > 0.0) ? vol / volMA : 0.0;
   double high = iHigh(g_symbol, PERIOD_M15, 1);
   double low = iLow(g_symbol, PERIOD_M15, 1);
   double open = iOpen(g_symbol, PERIOD_M15, 1);
   double close = iClose(g_symbol, PERIOD_M15, 1);
   double range = high - low;
   double body = MathAbs(close - open);
   double bodyRatio = (range > 0.0) ? body / range : 0.0;
   double closeSide = 0.5;
   if(range > 0.0)
   {
      if(dir == DIR_LONG)
         closeSide = (close - low) / range;
      else
         closeSide = 1.0 - (close - low) / range;
   }

   accepted = (volRatio >= cfg_InpFP_VolSpikeRatio && bodyRatio >= cfg_InpFP_BodyMinRatio && closeSide >= cfg_InpFP_CloseSideMin);

   if(volRatio >= cfg_InpFP_AbsorpVolRatio && range <= atrM15 * cfg_InpFP_AbsorpRangeATR && closeSide < 0.55)
      absorption = true;

   if(cfg_InpFP_RequireAcceptance)
      return accepted && !absorption;
   return !absorption;
}

bool DetectSupplyDemandBonus(TradeDir dir, int &sdType, double &sdDistATR, int &sdFresh)
{
   sdType = 0;
   sdDistATR = 0.0;
   sdFresh = 0;
   if(!cfg_InpUseSupplyDemandBonus)
      return false;

   int bars = iBars(g_symbol, cfg_InpSD_TF);
   if(bars <= cfg_InpSD_MaxBaseBars + 2)
      return false;

   int lookback = MathMin(cfg_InpSD_LookbackBars, bars - cfg_InpSD_MaxBaseBars - 2);
   if(lookback < cfg_InpSD_MaxBaseBars + 2)
      return false;

   double atrM15 = ATR(PERIOD_M15, 1);
   if(atrM15 <= 0.0)
      return false;

   double bestDist = DBL_MAX;
   bool zoneFresh = false;
   int zoneType = 0;

   for(int i = 1; i <= lookback; i++)
   {
      double atr = GetATR(g_symbol, cfg_InpSD_TF, cfg_InpATRPeriod, i);
      if(atr <= 0.0)
         continue;
      double impOpen = iOpen(g_symbol, cfg_InpSD_TF, i);
      double impClose = iClose(g_symbol, cfg_InpSD_TF, i);
      double impHigh = iHigh(g_symbol, cfg_InpSD_TF, i);
      double impLow = iLow(g_symbol, cfg_InpSD_TF, i);
      double impRange = impHigh - impLow;
      double impBody = MathAbs(impClose - impOpen);
      double bodyRatio = (impRange > 0.0) ? (impBody / impRange) : 0.0;
      if(impRange < atr * cfg_InpSD_MinImpulseATR || bodyRatio < 0.55)
         continue;

      int baseBars = 0;
      double baseMinLow = DBL_MAX;
      double baseMaxHigh = -DBL_MAX;
      double baseMinBody = DBL_MAX;
      double baseMaxBody = -DBL_MAX;
      for(int b = 1; b <= cfg_InpSD_MaxBaseBars; b++)
      {
         int shift = i + b;
         if(shift >= bars)
            break;
         double bHigh = iHigh(g_symbol, cfg_InpSD_TF, shift);
         double bLow = iLow(g_symbol, cfg_InpSD_TF, shift);
         double bOpen = iOpen(g_symbol, cfg_InpSD_TF, shift);
         double bClose = iClose(g_symbol, cfg_InpSD_TF, shift);
         double bRange = bHigh - bLow;
         if(bRange >= atr * 0.8)
            break;
         baseBars++;
         baseMinLow = MathMin(baseMinLow, bLow);
         baseMaxHigh = MathMax(baseMaxHigh, bHigh);
         baseMinBody = MathMin(baseMinBody, MathMin(bOpen, bClose));
         baseMaxBody = MathMax(baseMaxBody, MathMax(bOpen, bClose));
      }
      if(baseBars <= 0)
         continue;

      bool impulseUp = impClose > impOpen;
      int candidateType = impulseUp ? 1 : -1;
      if(dir == DIR_LONG && candidateType != 1)
         continue;
      if(dir == DIR_SHORT && candidateType != -1)
         continue;

      double pad = atr * cfg_InpSD_ZonePadATR;
      double candLow = (candidateType == 1) ? baseMinLow : baseMinBody;
      double candHigh = (candidateType == 1) ? baseMaxBody : baseMaxHigh;
      candLow -= pad;
      candHigh += pad;

      bool mitigated = false;
      for(int j = i - 1; j >= 1; j--)
      {
         double jHigh = iHigh(g_symbol, cfg_InpSD_TF, j);
         double jLow = iLow(g_symbol, cfg_InpSD_TF, j);
         if(jLow <= candHigh && jHigh >= candLow)
         {
            mitigated = true;
            break;
         }
      }

      double price = iClose(g_symbol, PERIOD_M15, 1);
      double dist = 0.0;
      if(price < candLow)
         dist = candLow - price;
      else if(price > candHigh)
         dist = price - candHigh;
      else
         dist = 0.0;

      double distAtr = dist / atrM15;
      if(distAtr > cfg_InpSD_MaxDistATR)
         continue;

      if(distAtr < bestDist)
      {
         bestDist = distAtr;
         zoneFresh = !mitigated;
         zoneType = candidateType;
      }
   }

   if(bestDist == DBL_MAX)
      return false;

   sdType = zoneType;
   sdDistATR = bestDist;
   sdFresh = zoneFresh ? 1 : 0;
   return true;
}

bool CandleBonus(TradeDir dir, int &candleType)
{
   candleType = 0;
   if(!cfg_InpUseCandleBonus)
      return false;

   double o1 = iOpen(g_symbol, PERIOD_M15, 1);
   double c1 = iClose(g_symbol, PERIOD_M15, 1);
   double h1 = iHigh(g_symbol, PERIOD_M15, 1);
   double l1 = iLow(g_symbol, PERIOD_M15, 1);
   double o2 = iOpen(g_symbol, PERIOD_M15, 2);
   double c2 = iClose(g_symbol, PERIOD_M15, 2);
   double range = h1 - l1;
   if(range <= 0.0)
      return false;

   double body = MathAbs(c1 - o1);
   double upperWick = h1 - MathMax(o1, c1);
   double lowerWick = MathMin(o1, c1) - l1;

   bool bullish = c1 > o1;
   bool bearish = c1 < o1;

   bool bullEngulf = bullish && c1 >= o2 && o1 <= c2;
   bool bearEngulf = bearish && c1 <= o2 && o1 >= c2;

   bool bullPin = lowerWick > body * 2.0 && lowerWick > upperWick;
   bool bearPin = upperWick > body * 2.0 && upperWick > lowerWick;

   bool doji = body <= range * 0.25;
   bool dojiBull = doji && lowerWick > upperWick * 1.5;
   bool dojiBear = doji && upperWick > lowerWick * 1.5;

   if(dir == DIR_LONG)
   {
      if(bullEngulf)
      {
         candleType = 1;
         return true;
      }
      if(bullPin)
      {
         candleType = 3;
         return true;
      }
      if(dojiBull)
      {
         candleType = 5;
         return true;
      }
   }
   else if(dir == DIR_SHORT)
   {
      if(bearEngulf)
      {
         candleType = 2;
         return true;
      }
      if(bearPin)
      {
         candleType = 4;
         return true;
      }
      if(dojiBear)
      {
         candleType = 6;
         return true;
      }
   }

   return false;
}

bool MomentumBonus(TradeDir dir, double &rsi1, double &rsi2)
{
   rsi1 = RSI(PERIOD_M15, 1);
   rsi2 = RSI(PERIOD_M15, 2);
   if(!cfg_InpUseMomentumBonus)
      return false;
   if(dir == DIR_LONG)
      return (rsi1 > rsi2 && rsi1 > 50.0);
   if(dir == DIR_SHORT)
      return (rsi1 < rsi2 && rsi1 < 50.0);
   return false;
}

bool SpikeGuardOk(double atrM15)
{
   if(!cfg_InpUseSpikeGuard)
      return true;

   double high = iHigh(g_symbol, PERIOD_M15, 1);
   double low = iLow(g_symbol, PERIOD_M15, 1);
   return (high - low) <= atrM15 * cfg_InpSpikeMultATR;
}

bool RSIAfterLossOk(TradeDir dir)
{
   if(!cfg_InpUseRSIAfterLoss)
      return true;

   int lossStreak = GVGetInt("lossStreak", 0);
   if(lossStreak < cfg_InpLossStreakForRSI)
      return true;

   double rsi1 = RSI(PERIOD_M15, 1);
   double rsi2 = RSI(PERIOD_M15, 2);
   if(dir == DIR_LONG)
      return (rsi1 >= 52.0 && rsi1 > rsi2);
   if(dir == DIR_SHORT)
      return (rsi1 <= 48.0 && rsi1 < rsi2);
   return false;
}

bool SelectOurPosition()
{
   int total = PositionsTotal();
   for(int i = 0; i < total; i++)
   {
      if(PositionSelectByIndex(i))
      {
         string symbol = PositionGetString(POSITION_SYMBOL);
         long magic = PositionGetInteger(POSITION_MAGIC);
         if(symbol == g_symbol && magic == cfg_InpMagic)
            return true;
      }
   }
   return false;
}

bool HasPosition()
{
   return SelectOurPosition();
}

bool DailyLossLocked()
{
   if(!cfg_InpUseMaxDailyLossLock)
      return false;

   double startEquity = GVGetDouble("dayEquityStart", AccountInfoDouble(ACCOUNT_EQUITY));
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double pct = (startEquity > 0.0) ? (equity - startEquity) / startEquity * 100.0 : 0.0;
   if(pct <= -cfg_InpMaxDailyLossPct)
   {
      GVSetInt("dayLocked", 1);
      return true;
   }
   return false;
}

bool SoftEquityLocked()
{
   if(!cfg_InpUseSoftEquityLock)
      return false;

   double peak = GVGetDouble("dayEquityPeak", AccountInfoDouble(ACCOUNT_EQUITY));
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity > peak)
   {
      peak = equity;
      GVSetDouble("dayEquityPeak", peak);
   }

   double start = GVGetDouble("dayEquityStart", equity);
   double gainPct = (peak - start) / start * 100.0;
   double curPct = (equity - start) / start * 100.0;
   if((gainPct >= cfg_InpSoftEqTrigger2 && curPct <= cfg_InpSoftEqFloor2) ||
      (gainPct >= cfg_InpSoftEqTrigger1 && curPct <= cfg_InpSoftEqFloor1))
   {
      GVSetInt("dayLocked", 1);
      return true;
   }
   return false;
}

int DailyScore(RegimeState regime)
{
   double adx = ADX(PERIOD_H1, 1);
   double vol = (double)iVolume(g_symbol, PERIOD_H1, 1);
   double volAvg = VolumeMA(PERIOD_H1, cfg_InpVolMAPeriod, 2);
   double volScore = (volAvg > 0.0) ? MathMin(30.0, (vol / volAvg) * 15.0) : 0.0;
   double adxScore = MathMin(30.0, adx);

   double spreadScore = 20.0;
   if(g_spreadEma > 0.0)
   {
      double spread = SpreadPoints();
      spreadScore = 20.0 * MathMax(0.0, 1.0 - (spread / (g_spreadEma * cfg_InpSpreadSpikeFactor)));
   }

   double regimeScore = 0.0;
   if(regime == REGIME_TREND)
      regimeScore = 20.0;
   else if(regime == REGIME_TRANSITION)
      regimeScore = 10.0;

   int lossStreak = GVGetInt("lossStreak", 0);
   double lossPenalty = lossStreak * 5.0;
   double spreadNow = SpreadPoints();
   if(SpreadMultipleWouldBlock(spreadNow, g_spreadEma) || SpreadInstabilityWouldBlock(spreadNow, g_spreadEma) || RolloverBlocked())
      lossPenalty += 10.0;

   double score = volScore + adxScore + spreadScore + regimeScore - lossPenalty;
   if(score < 0.0)
      score = 0.0;
   if(score > 100.0)
      score = 100.0;
   return (int)score;
}

bool DailyTradeAllowed(int dailyScore, int &maxTrades, double &riskMult, bool &pyramidOk)
{
   maxTrades = 0;
   riskMult = 0.0;
   pyramidOk = false;
   if(dailyScore >= 70)
   {
      maxTrades = 3;
      riskMult = 1.0;
      pyramidOk = true;
   }
   else if(dailyScore >= 50)
   {
      maxTrades = 2;
      riskMult = 0.8;
      pyramidOk = true;
   }
   else if(dailyScore >= 30)
   {
      maxTrades = 1;
      riskMult = 0.6;
      pyramidOk = false;
   }
   return maxTrades > 0;
}

bool CooldownActive()
{
   datetime lastEntryTime = (datetime)GVGetDouble("lastEntryTime", 0.0);
   if(lastEntryTime == 0)
      return false;
   int shift = iBarShift(g_symbol, PERIOD_M15, lastEntryTime, true);
   if(shift < 0)
      return false;
   return shift <= cfg_InpCooldownBarsAfterEntry;
}

void UpdateDailyReset()
{
   datetime now = TimeCurrent();
   datetime todayStart = GetTradingDayStart(now);

   datetime storedStart = (datetime)GVGetDouble("dayStart", 0.0);

   if(storedStart == 0 || storedStart != todayStart)
   {
      GVSetDouble("dayStart", (double)todayStart);

      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      GVSetDouble("dayEquityStart", equity);
      GVSetDouble("dayEquityPeak", equity);
      GVSetInt("dayLocked", 0);
      GVSetInt("dayTrades", 0);
      GVSetInt("tp1done", 0);
      GVSetInt("addCount", 0);
   }
}


string AppendReason(string base, string add)
{
   if(StringLen(add) == 0)
      return base;
   if(StringLen(base) == 0)
      return add;
   return base + "|" + add;
}

string ExplainSkipMask(int mask)
{
   if(mask == SKIP_NONE)
      return "NONE";
   string out = "";
   if((mask & SKIP_SESSION) != 0) out = AppendReason(out, "SESSION");
   if((mask & SKIP_ROLLOVER) != 0) out = AppendReason(out, "ROLLOVER");
   if((mask & SKIP_SPREAD) != 0) out = AppendReason(out, "SPREAD");
   if((mask & SKIP_SPREAD_MULT) != 0) out = AppendReason(out, "SPREAD_MULT");
   if((mask & SKIP_SPREAD_INSTAB) != 0) out = AppendReason(out, "SPREAD_INSTAB");
   if((mask & SKIP_LOWVOL) != 0) out = AppendReason(out, "LOWVOL");
   if((mask & SKIP_DAILY_LOCK) != 0) out = AppendReason(out, "DAILY_LOCK");
   if((mask & SKIP_COOLDOWN) != 0) out = AppendReason(out, "COOLDOWN");
   if((mask & SKIP_LOSS_BLOCK) != 0) out = AppendReason(out, "LOSS_BLOCK");
   if((mask & SKIP_DAILY_MAX) != 0) out = AppendReason(out, "DAILY_MAX");
   if((mask & SKIP_DAILY_SCORE) != 0) out = AppendReason(out, "DAILY_SCORE");
   if((mask & SKIP_STOPS) != 0) out = AppendReason(out, "STOPS");
   if((mask & SKIP_KILLZONE) != 0) out = AppendReason(out, "KILLZONE");
   if((mask & SKIP_PDARRAY) != 0) out = AppendReason(out, "PDARRAY");
   return out;
}

string ExplainEntryMask(int mask)
{
   if(mask == ENTRY_NONE)
      return "NONE";
   string out = "";
   if((mask & ENTRY_BIAS) != 0) out = AppendReason(out, "BIAS");
   if((mask & ENTRY_PIVOT) != 0) out = AppendReason(out, "PIVOT");
   if((mask & ENTRY_HL_LH) != 0) out = AppendReason(out, "HL_LH");
   if((mask & ENTRY_BOS_CLOSE) != 0) out = AppendReason(out, "BOS_CLOSE");
   if((mask & ENTRY_BOS_RETEST) != 0) out = AppendReason(out, "BOS_RETEST");
   if((mask & ENTRY_KILLZONE) != 0) out = AppendReason(out, "KILLZONE");
   if((mask & ENTRY_SWEEP) != 0) out = AppendReason(out, "SWEEP");
   if((mask & ENTRY_DISPLACEMENT) != 0) out = AppendReason(out, "DISPLACEMENT");
   if((mask & ENTRY_MSS) != 0) out = AppendReason(out, "MSS");
   if((mask & ENTRY_PDARRAY) != 0) out = AppendReason(out, "PDARRAY");
   if((mask & ENTRY_RR) != 0) out = AppendReason(out, "RR");
   return out;
}

void BuildContext(MarketContext &ctx)
{
   ctx.bid = SymbolInfoDouble(g_symbol, SYMBOL_BID);
   ctx.ask = SymbolInfoDouble(g_symbol, SYMBOL_ASK);
   ctx.mid = (ctx.bid + ctx.ask) * 0.5;
   ctx.spreadPts = (g_point > 0.0) ? ((ctx.ask - ctx.bid) / g_point) : 0.0;
   ctx.atrM15 = ATR(PERIOD_M15, 1);
   ctx.atrH1 = ATR(PERIOD_H1, 1);
   ctx.adxH1 = ADX(PERIOD_H1, 1);
   ctx.rsi1 = RSI(PERIOD_M15, 1);
   ctx.rsi2 = RSI(PERIOD_M15, 2);
   ctx.emaFast = EMA(PERIOD_H1, cfg_InpEMA_Fast, 1);
   ctx.emaSlow = EMA(PERIOD_H1, cfg_InpEMA_Slow, 1);
   bool kzA = false, kzL = false, kzN = false;
   ctx.killzoneActive = KillzoneActive(kzA, kzL, kzN) ? 1 : 0;
   GetPDLevels(ctx.pdh, ctx.pdl);
   GetHODLOD_Cached(ctx.hod, ctx.lod);
   ctx.lossStreak = GVGetInt("lossStreak", 0);
   ctx.dayTrades = GVGetInt("dayTrades", 0);
   ctx.spreadEma = g_spreadEma;
}

bool HardGuardsOk(int &skipMask, const MarketContext &ctx)
{
   skipMask = SKIP_NONE;
   if(!SessionAllowed())
   {
      skipMask |= SKIP_SESSION;
      return false;
   }
   if(RolloverBlocked())
   {
      skipMask |= SKIP_ROLLOVER;
      return false;
   }
   if(ctx.spreadPts > cfg_InpMaxSpreadPoints)
   {
      skipMask |= SKIP_SPREAD;
      return false;
   }
   if(SpreadMultipleBlocked())
   {
      skipMask |= SKIP_SPREAD_MULT;
      return false;
   }
   if(SpreadInstabilityBlocked())
   {
      skipMask |= SKIP_SPREAD_INSTAB;
      return false;
   }
   if(LowVolumeBlocked())
   {
      skipMask |= SKIP_LOWVOL;
      return false;
   }
   if(DailyLossLocked() || SoftEquityLocked())
   {
      skipMask |= SKIP_DAILY_LOCK;
      return false;
   }
   if(GVGetInt("dayLocked", 0) == 1)
   {
      skipMask |= SKIP_DAILY_LOCK;
      return false;
   }
   if(CooldownActive())
   {
      skipMask |= SKIP_COOLDOWN;
      return false;
   }
   return true;
}

bool HardGuardsOk(int &skipMask)
{
   MarketContext ctx;
   BuildContext(ctx);
   return HardGuardsOk(skipMask, ctx);
}

bool LossBlocksActive()
{
   if(!cfg_InpUseAntiChop)
      return false;

   datetime blockUntil = (datetime)GVGetDouble("blockUntil", 0.0);
   return (blockUntil > TimeCurrent());
}

void UpdateLossBlock(int lossStreak)
{
   if(!cfg_InpUseAntiChop)
      return;

   if(lossStreak >= 3)
   {
      GVSetDouble("blockUntil", TimeCurrent() + cfg_InpLossBlock3_Hours * 3600.0);
      GVSetDouble("riskCutUntil", TimeCurrent() + cfg_InpRiskCutAfter3Loss_H * 3600.0);
   }
   else if(lossStreak == 2)
   {
      GVSetDouble("blockUntil", TimeCurrent() + cfg_InpLossBlock2_Hours * 3600.0);
   }
}

double CurrentRiskMultiplier(double dailyRiskMult)
{
   double mult = dailyRiskMult;
   datetime riskCutUntil = (datetime)GVGetDouble("riskCutUntil", 0.0);
   if(riskCutUntil > TimeCurrent())
      mult *= cfg_InpRiskMultAfter3Loss;
   return mult;
}

double TickValue()
{
   double tickValue = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE_PROFIT);
   if(tickValue <= 0.0)
      tickValue = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tickValue <= 0.0)
      tickValue = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE);
   return tickValue;
}

double TickSize()
{
   double tickSize = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize <= 0.0)
      tickSize = g_point;
   return tickSize;
}

double CalcLots(double slDist, double riskPct)
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * (riskPct / 100.0);
   double tickSize = TickSize();
   double tickValue = TickValue();
   if(tickSize <= 0.0 || tickValue <= 0.0 || slDist <= 0.0)
      return 0.0;

   double moneyPerLot = (slDist / tickSize) * tickValue;
   if(moneyPerLot <= 0.0)
      return 0.0;

   double lot = riskMoney / moneyPerLot;
   double minLot = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP);

   lot = MathMax(minLot, lot);
   if(cfg_InpMaxLotCap > 0.0)
      maxLot = MathMin(maxLot, cfg_InpMaxLotCap);
   lot = MathMin(lot, maxLot);
   return NormalizeVolumeByStep(lot);
}

double NormalizeVolumeByStep(double volume)
{
   double minLot = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP);
   double vol = MathMin(maxLot, MathMax(minLot, volume));
   vol = MathFloor(vol / step) * step;
   int decimals = 0;
   double scaled = step;
   while(decimals < 8 && MathAbs(scaled - MathRound(scaled)) > 1e-8)
   {
      scaled *= 10.0;
      decimals++;
   }
   return NormalizeDouble(vol, decimals);
}

bool StopsOk(TradeDir dir, double entry, double sl, double tp)
{
   int stopsLevel = (int)SymbolInfoInteger(g_symbol, SYMBOL_TRADE_STOPS_LEVEL);
   int freezeLevel = (int)SymbolInfoInteger(g_symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   double minDist = stopsLevel * g_point;
   double freezeDist = freezeLevel * g_point;
   double curMid = (SymbolInfoDouble(g_symbol, SYMBOL_ASK) + SymbolInfoDouble(g_symbol, SYMBOL_BID)) * 0.5;
   if(dir == DIR_LONG)
   {
      if(sl > 0.0 && (sl >= entry || MathAbs(entry - sl) < minDist))
         return false;
      if(tp > 0.0 && (tp <= entry || MathAbs(tp - entry) < minDist))
         return false;
   }
   else if(dir == DIR_SHORT)
   {
      if(sl > 0.0 && (sl <= entry || MathAbs(entry - sl) < minDist))
         return false;
      if(tp > 0.0 && (tp >= entry || MathAbs(tp - entry) < minDist))
         return false;
   }
   if(freezeLevel > 0)
   {
      if(sl > 0.0 && MathAbs(curMid - sl) < freezeDist)
         return false;
      if(tp > 0.0 && MathAbs(curMid - tp) < freezeDist)
         return false;
   }
   return true;
}

bool CanModifyStops(double newSl)
{
   int freezeLevel = (int)SymbolInfoInteger(g_symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   if(freezeLevel <= 0)
      return true;

   double price = (SymbolInfoDouble(g_symbol, SYMBOL_ASK) + SymbolInfoDouble(g_symbol, SYMBOL_BID)) / 2.0;
   return MathAbs(price - newSl) > freezeLevel * g_point;
}

bool FreezeOkForClose()
{
   int freezeLevel = (int)SymbolInfoInteger(g_symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   if(freezeLevel <= 0)
      return true;
   double price = (SymbolInfoDouble(g_symbol, SYMBOL_ASK) + SymbolInfoDouble(g_symbol, SYMBOL_BID)) / 2.0;
   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   return MathAbs(price - entry) > freezeLevel * g_point;
}

bool SendOrderCore(TradeDir dir, double lots, double sl, double tp, const string comment, int &retcode, int &lasterr)
{
   retcode = 0;
   lasterr = 0;
   for(int attempt = 0; attempt <= cfg_InpMaxRetries; attempt++)
   {
      bool ok = false;
      ResetLastError();
      if(dir == DIR_LONG)
         ok = trade.Buy(lots, g_symbol, 0.0, sl, tp, comment);
      else if(dir == DIR_SHORT)
         ok = trade.Sell(lots, g_symbol, 0.0, sl, tp, comment);

      retcode = (int)trade.ResultRetcode();
      lasterr = (int)GetLastError();

      if(ok)
         return true;

      if(retcode == TRADE_RETCODE_PRICE_CHANGED ||
         retcode == TRADE_RETCODE_REQUOTE ||
         retcode == TRADE_RETCODE_OFF_QUOTES ||
         retcode == TRADE_RETCODE_TRADE_CONTEXT_BUSY ||
         retcode == TRADE_RETCODE_SERVER_BUSY)
      {
         Sleep(cfg_InpRetryDelayMs);
         continue;
      }
      break;
   }
   return false;
}


string PresetModeLabel(PresetMode mode);
void LogPresetConfig();
void LogSymbolCheck();

double IndexKeyStepPoints()
{
   string symUpper = g_symbol;
   StringToUpper(symUpper);
   if(StringFind(symUpper, "US30") >= 0 || StringFind(symUpper, "DJ30") >= 0 || StringFind(symUpper, "WS30") >= 0)
      return 100.0;
   return 50.0;
}

void ApplyProfileDefaults()
{
   if(g_isGoldSymbol)
   {
      cfg_KeyLevelStepPoints = PointsFromPrice(cfg_InpKeyLevelStepPrice);
      cfg_KeyNearPoints = PointsFromPrice(cfg_InpKeyNearPrice);
      cfg_KeyChaseMaxDistPoints = PointsFromPrice(cfg_InpKeyChaseMaxDistPrice);
      cfg_EqToleranceMinPoints = cfg_InpEqToleranceMinPoints;
      cfg_SL_MinBufferPoints = PointsFromPrice(cfg_InpSL_MinBufferPrice);
      cfg_MMSL_ExtraBufferPoints = PointsFromPrice(cfg_InpMMSL_ExtraBufferPrice);
      cfg_BE_OffsetPoints = PointsFromPrice(cfg_InpBE_OffsetPrice);
      cfg_TrailMinImprovePoints = PointsFromPrice(cfg_InpTrailMinImprovePrice);
      cfg_FibTolPoints = PointsFromPrice(cfg_InpFibTolPrice);
      cfg_MinPDArrayDistancePoints = PointsFromPrice(cfg_InpMinPDArrayDistance);
      cfg_MinPDArrayMinPoints = cfg_InpMinPDArrayMinPoints;
      return;
   }

   if(g_profile == PROFILE_INDICES)
   {
      cfg_KeyLevelStepPoints = IndexKeyStepPoints();
      cfg_KeyNearPoints = PointsFromPrice(5.0);
   }
   else
   {
      cfg_KeyLevelStepPoints = PointsFromPips(50.0);
      cfg_KeyNearPoints = PointsFromPips(5.0);
   }
   cfg_KeyChaseMaxDistPoints = cfg_KeyLevelStepPoints * 0.30;

   double slEquiv = cfg_InpSL_MinBufferPrice / 0.10;
   double beEquiv = cfg_InpBE_OffsetPrice / 0.10;
   double trailEquiv = cfg_InpTrailMinImprovePrice / 0.10;
   double fibEquiv = cfg_InpFibTolPrice / 0.10;
   double pdEquiv = cfg_InpMinPDArrayDistance / 0.10;
   double mmslExtraEquiv = cfg_InpMMSL_ExtraBufferPrice / 0.10;
   double eqTolEquiv = cfg_InpEqToleranceMinPoints / 10.0;
   double pdMinEquiv = cfg_InpMinPDArrayMinPoints / 10.0;

   if(g_profile == PROFILE_INDICES)
   {
      cfg_SL_MinBufferPoints = PointsFromPrice(slEquiv);
      cfg_MMSL_ExtraBufferPoints = PointsFromPrice(mmslExtraEquiv);
      cfg_BE_OffsetPoints = PointsFromPrice(beEquiv);
      cfg_TrailMinImprovePoints = PointsFromPrice(trailEquiv);
      cfg_FibTolPoints = PointsFromPrice(fibEquiv);
      cfg_EqToleranceMinPoints = MathRound(PointsFromPrice(eqTolEquiv));
      cfg_MinPDArrayDistancePoints = PointsFromPrice(pdEquiv);
      cfg_MinPDArrayMinPoints = (int)MathRound(PointsFromPrice(pdMinEquiv));
   }
   else
   {
      cfg_SL_MinBufferPoints = PointsFromPips(slEquiv);
      cfg_MMSL_ExtraBufferPoints = PointsFromPips(mmslExtraEquiv);
      cfg_BE_OffsetPoints = PointsFromPips(beEquiv);
      cfg_TrailMinImprovePoints = PointsFromPips(trailEquiv);
      cfg_FibTolPoints = PointsFromPips(fibEquiv);
      cfg_EqToleranceMinPoints = MathRound(PointsFromPips(eqTolEquiv));
      cfg_MinPDArrayDistancePoints = PointsFromPips(pdEquiv);
      cfg_MinPDArrayMinPoints = (int)MathRound(PointsFromPips(pdMinEquiv));
   }
}

void ApplyPreset()
{
   cfg_InpPresetMode = InpPresetMode;
   cfg_InpSymbolOverride = InpSymbolOverride;
   cfg_InpMagic = InpMagic;
   cfg_InpPipPrice = InpPipPrice;
   cfg_InpUseSessionFilter = InpUseSessionFilter;
   cfg_InpStartHour = InpStartHour;
   cfg_InpEndHour = InpEndHour;
   cfg_InpMaxSpreadPoints = (InpMaxSpreadPoints > 0 ? InpMaxSpreadPoints : MaxSpreadPoints);
   cfg_InpMaxSlippagePoints = InpMaxSlippagePoints;
   cfg_InpMaxRetries = InpMaxRetries;
   cfg_InpRetryDelayMs = InpRetryDelayMs;
   cfg_InpUseICTTime = InpUseICTTime;
   cfg_InpUseManualNYOffset = InpUseManualNYOffset;
   cfg_InpNYOffsetHours = InpNYOffsetHours;
   cfg_InpAutoNYDST = InpAutoNYDST;
   cfg_InpNYOffsetSummerHours = InpNYOffsetSummerHours;
   cfg_InpUseKillzoneAsia = InpUseKillzoneAsia;
   cfg_InpUseKillzoneLondon = InpUseKillzoneLondon;
   cfg_InpUseKillzoneNY = InpUseKillzoneNY;
   cfg_InpATRPeriod = InpATRPeriod;
   cfg_InpADXPeriod = InpADXPeriod;
   cfg_InpRSIPeriod = InpRSIPeriod;
   cfg_InpEMA_Fast = InpEMA_Fast;
   cfg_InpEMA_Slow = InpEMA_Slow;
   cfg_InpRegimeConfirmBarsH1 = InpRegimeConfirmBarsH1;
   cfg_InpRegimeLockBarsH1 = InpRegimeLockBarsH1;
   cfg_InpPivotLen = InpPivotLen;
   cfg_InpPivotConfirmBars = InpPivotConfirmBars;
   cfg_InpMaxBarsAfterBOS = InpMaxBarsAfterBOS;
   cfg_InpEqToleranceATR = InpEqToleranceATR;
   cfg_InpEqToleranceMinPoints = InpEqToleranceMinPoints;
   cfg_InpEqClusterMin = InpEqClusterMin;
   cfg_InpEqScanBars = InpEqScanBars;
   cfg_InpDisplacementATR = InpDisplacementATR;
   cfg_InpDisplacementBodyRatio = InpDisplacementBodyRatio;
   cfg_InpDisplacementSearchBars = InpDisplacementSearchBars;
   cfg_InpOBLookback = InpOBLookback;
   cfg_InpOBMaxAgeBars = InpOBMaxAgeBars;
   cfg_InpOTE_HTF = InpOTE_HTF;
   cfg_InpOTE_SwingLookback = InpOTE_SwingLookback;
   cfg_InpOTE_Min = InpOTE_Min;
   cfg_InpOTE_Max = InpOTE_Max;
   cfg_InpMinPDArrayDistance = InpMinPDArrayDistance;
   cfg_InpMinPDArrayATR = InpMinPDArrayATR;
   cfg_InpMinPDArrayMinPoints = InpMinPDArrayMinPoints;
   cfg_InpUseBreakRetest = InpUseBreakRetest;
   cfg_InpRetestTolATR = InpRetestTolATR;
   cfg_InpKeyLevelStepPrice = InpKeyLevelStepPrice;
   cfg_InpKeyNearPrice = InpKeyNearPrice;
   cfg_InpKeyChaseMaxDistPrice = InpKeyChaseMaxDistPrice;
   cfg_InpUseFVGFeature = InpUseFVGFeature;
   cfg_InpFVGScanBars = InpFVGScanBars;
   cfg_InpFVGMaxDistATR = InpFVGMaxDistATR;
   cfg_InpUseFibFilter = InpUseFibFilter;
   cfg_InpFibBaseMin = InpFibBaseMin;
   cfg_InpFibBaseMax = InpFibBaseMax;
   cfg_InpFibTolPrice = InpFibTolPrice;
   cfg_InpUseOTEBonus = InpUseOTEBonus;
   cfg_InpOTEMin = InpOTEMin;
   cfg_InpOTEMax = InpOTEMax;
   cfg_InpOTEBonusPoints = InpOTEBonusPoints;
   cfg_InpUseFootprintProxy = InpUseFootprintProxy;
   cfg_InpFP_VolMAPeriod = InpFP_VolMAPeriod;
   cfg_InpFP_VolSpikeRatio = InpFP_VolSpikeRatio;
   cfg_InpFP_BodyMinRatio = InpFP_BodyMinRatio;
   cfg_InpFP_CloseSideMin = InpFP_CloseSideMin;
   cfg_InpFP_AbsorpVolRatio = InpFP_AbsorpVolRatio;
   cfg_InpFP_AbsorpRangeATR = InpFP_AbsorpRangeATR;
   cfg_InpFP_RequireAcceptance = InpFP_RequireAcceptance;
   cfg_InpFP_ScoreBonus = InpFP_ScoreBonus;
   cfg_InpUseSupplyDemandBonus = InpUseSupplyDemandBonus;
   cfg_InpSD_TF = InpSD_TF;
   cfg_InpSD_LookbackBars = InpSD_LookbackBars;
   cfg_InpSD_MinImpulseATR = InpSD_MinImpulseATR;
   cfg_InpSD_MaxBaseBars = InpSD_MaxBaseBars;
   cfg_InpSD_ZonePadATR = InpSD_ZonePadATR;
   cfg_InpSD_MaxDistATR = InpSD_MaxDistATR;
   cfg_InpSD_BonusPoints = InpSD_BonusPoints;
   cfg_InpSD_FreshnessBonus = InpSD_FreshnessBonus;
   cfg_InpUseCandleBonus = InpUseCandleBonus;
   cfg_InpCandleBonusPoints = InpCandleBonusPoints;
   cfg_InpUseMomentumBonus = InpUseMomentumBonus;
   cfg_InpMomentumBonusPoints = InpMomentumBonusPoints;
   cfg_InpRequireBiasAlignWithSweep = InpRequireBiasAlignWithSweep;
   cfg_InpUseSpikeGuard = InpUseSpikeGuard;
   cfg_InpSpikeMultATR = InpSpikeMultATR;
   cfg_InpSL_ATR_Mult = InpSL_ATR_Mult;
   cfg_InpSL_MinBufferPrice = InpSL_MinBufferPrice;
   cfg_InpUseMMSL = InpUseMMSL;
   cfg_InpMMSL_Pips = InpMMSL_Pips;
   cfg_InpMMSL_ExtraBufferPrice = InpMMSL_ExtraBufferPrice;
   cfg_InpTP_RR_Main = InpTP_RR_Main;
   cfg_InpMinRRAllowed = InpMinRRAllowed;
   cfg_InpUseTP1Partial = InpUseTP1Partial;
   cfg_InpTP1_CloseFrac = InpTP1_CloseFrac;
   cfg_InpTP1_UseKeyLevelFirst = InpTP1_UseKeyLevelFirst;
   cfg_InpUseSmartBE = InpUseSmartBE;
   cfg_InpBE_MinProfitR = InpBE_MinProfitR;
   cfg_InpBE_OffsetPrice = InpBE_OffsetPrice;
   cfg_InpUseATRTrailAfterTP1 = InpUseATRTrailAfterTP1;
   cfg_InpTrailATR_Mult = InpTrailATR_Mult;
   cfg_InpTrailMinImprovePrice = InpTrailMinImprovePrice;
   cfg_InpTrailOnNewBarOnly = InpTrailOnNewBarOnly;
   cfg_InpBaseRiskPct = InpBaseRiskPct;
   cfg_InpMaxLotCap = InpMaxLotCap;
   cfg_InpUseLowVolFilter = InpUseLowVolFilter;
   cfg_InpVolTF = InpVolTF;
   cfg_InpVolMAPeriod = InpVolMAPeriod;
   cfg_InpLowVolFactor = InpLowVolFactor;
   cfg_InpUseSpreadMultiple = InpUseSpreadMultiple;
   cfg_InpSpreadMultiple = InpSpreadMultiple;
   cfg_InpSpreadMultipleBlockMin = InpSpreadMultipleBlockMin;
   cfg_InpUseSpreadInstability = InpUseSpreadInstability;
   cfg_InpSpreadAvgBarsH1 = InpSpreadAvgBarsH1;
   cfg_InpSpreadSpikeFactor = InpSpreadSpikeFactor;
   cfg_InpSpreadSpikeBlockMin = InpSpreadSpikeBlockMin;
   cfg_InpUseRolloverBlock = InpUseRolloverBlock;
   cfg_InpRolloverStart = InpRolloverStart;
   cfg_InpRolloverEnd = InpRolloverEnd;
   cfg_InpUseDailyTradeControl = InpUseDailyTradeControl;
   cfg_InpHardMaxTradesPerDay = InpHardMaxTradesPerDay;
   cfg_InpUseMaxDailyLossLock = InpUseMaxDailyLossLock;
   cfg_InpMaxDailyLossPct = InpMaxDailyLossPct;
   cfg_InpUseSoftEquityLock = InpUseSoftEquityLock;
   cfg_InpSoftEqTrigger1 = InpSoftEqTrigger1;
   cfg_InpSoftEqFloor1 = InpSoftEqFloor1;
   cfg_InpSoftEqTrigger2 = InpSoftEqTrigger2;
   cfg_InpSoftEqFloor2 = InpSoftEqFloor2;
   cfg_InpCooldownBarsAfterEntry = InpCooldownBarsAfterEntry;
   cfg_InpUseAntiChop = InpUseAntiChop;
   cfg_InpLossBlock2_Hours = InpLossBlock2_Hours;
   cfg_InpLossBlock3_Hours = InpLossBlock3_Hours;
   cfg_InpRiskMultAfter3Loss = InpRiskMultAfter3Loss;
   cfg_InpRiskCutAfter3Loss_H = InpRiskCutAfter3Loss_H;
   cfg_InpUseRSIAfterLoss = InpUseRSIAfterLoss;
   cfg_InpLossStreakForRSI = InpLossStreakForRSI;
   cfg_InpUsePyramiding = InpUsePyramiding;
   cfg_InpMaxAdds = InpMaxAdds;
   cfg_InpPyramidMinProfitR = InpPyramidMinProfitR;
   cfg_InpPyramidRequireMainBE = InpPyramidRequireMainBE;
   cfg_InpPyramidSpacingATR = InpPyramidSpacingATR;
   cfg_InpPyramidOnlyInTrend = InpPyramidOnlyInTrend;
   cfg_InpPyramidRequireAdxRising = InpPyramidRequireAdxRising;
   cfg_InpPyramidUsePeakDDCap = InpPyramidUsePeakDDCap;
   cfg_InpPyramidMaxPeakDDPct = InpPyramidMaxPeakDDPct;
   cfg_InpAddRiskMult1 = InpAddRiskMult1;
   cfg_InpAddRiskMult2 = InpAddRiskMult2;
   cfg_InpEnableCSV = InpEnableCSV;
   cfg_InpCSVName = InpCSVName;

   if(cfg_InpPresetMode == PRESET_BALANCED || cfg_InpPresetMode == PRESET_CONSERVATIVE)
   {
      cfg_InpUseICTTime = true;
      cfg_InpUseManualNYOffset = true;
      cfg_InpNYOffsetHours = -5;
      cfg_InpUseKillzoneAsia = false;
      cfg_InpUseKillzoneLondon = true;
      cfg_InpUseKillzoneNY = true;
      cfg_InpUseSessionFilter = true;
      cfg_InpStartHour = 6;
      cfg_InpEndHour = 23;
      cfg_InpMaxSpreadPoints = 35;
      cfg_InpUseSpreadMultiple = true;
      cfg_InpSpreadMultiple = 2.7;
      cfg_InpSpreadMultipleBlockMin = 45;
      cfg_InpUseSpreadInstability = true;
      cfg_InpSpreadSpikeFactor = 1.6;
      cfg_InpSpreadSpikeBlockMin = 60;
      cfg_InpUseRolloverBlock = true;
      cfg_InpRolloverStart = "23:55";
      cfg_InpRolloverEnd = "00:15";
      cfg_InpEqScanBars = 60;
      cfg_InpEqClusterMin = 2;
      cfg_InpEqToleranceATR = 0.20;
      cfg_InpEqToleranceMinPoints = 12;
      cfg_InpDisplacementATR = 1.25;
      cfg_InpDisplacementBodyRatio = 0.60;
      cfg_InpOBLookback = 14;
      cfg_InpOBMaxAgeBars = 10;
      cfg_InpOTE_HTF = PERIOD_H1;
      cfg_InpOTE_SwingLookback = 72;
      cfg_InpOTE_Min = 0.62;
      cfg_InpOTE_Max = 0.79;
      cfg_InpMinPDArrayDistance = 1.20;
      cfg_InpKeyLevelStepPrice = 5.0;
      cfg_InpKeyNearPrice = 0.45;
      cfg_InpKeyChaseMaxDistPrice = 1.20;
      cfg_InpUseFVGFeature = true;
      cfg_InpFVGScanBars = 24;
      cfg_InpFVGMaxDistATR = 1.0;
      cfg_InpSL_ATR_Mult = 0.30;
      cfg_InpSL_MinBufferPrice = 0.20;
      cfg_InpUseMMSL = true;
      cfg_InpMMSL_Pips = 35;
      cfg_InpTP_RR_Main = 2.0;
      cfg_InpMinRRAllowed = 1.6;
      cfg_InpUseTP1Partial = true;
      cfg_InpTP1_CloseFrac = 0.50;
      cfg_InpUseSmartBE = true;
      cfg_InpBE_MinProfitR = 1.0;
      cfg_InpBE_OffsetPrice = 0.06;
      cfg_InpUseATRTrailAfterTP1 = true;
      cfg_InpTrailATR_Mult = 1.15;
      cfg_InpTrailMinImprovePrice = 0.12;
      cfg_InpTrailOnNewBarOnly = true;
      cfg_InpBaseRiskPct = 1.0;
      cfg_InpHardMaxTradesPerDay = 2;
      cfg_InpUseMaxDailyLossLock = true;
      cfg_InpMaxDailyLossPct = 3.0;
      cfg_InpUseSoftEquityLock = true;
      cfg_InpSoftEqTrigger1 = 2.0;
      cfg_InpSoftEqFloor1 = 0.8;
      cfg_InpSoftEqTrigger2 = 4.0;
      cfg_InpSoftEqFloor2 = 2.0;
      cfg_InpCooldownBarsAfterEntry = 3;
      cfg_InpUseAntiChop = true;
      cfg_InpLossBlock2_Hours = 6;
      cfg_InpLossBlock3_Hours = 18;
      cfg_InpRiskMultAfter3Loss = 0.60;
      cfg_InpRiskCutAfter3Loss_H = 24;
      cfg_InpUsePyramiding = false;

      if(cfg_InpPresetMode == PRESET_CONSERVATIVE)
      {
         cfg_InpUseKillzoneAsia = false;
         cfg_InpUseKillzoneLondon = false;
         cfg_InpUseKillzoneNY = true;
         cfg_InpDisplacementATR = 1.35;
         cfg_InpEqToleranceATR = 0.18;
         cfg_InpHardMaxTradesPerDay = 1;
         cfg_InpBaseRiskPct = 0.7;
      }
   }

   double pipSize = AutoPipSize(true);
   if(cfg_InpPresetMode == PRESET_BALANCED || cfg_InpPresetMode == PRESET_CONSERVATIVE)
   {
      if(g_profile == PROFILE_INDICES)
         cfg_InpMaxSpreadPoints = (int)MathRound(PointsFromPrice(2.5));
      else
         cfg_InpMaxSpreadPoints = (int)MathRound((2.0 * pipSize) / g_point);
   }

   g_pip = pipSize;

   ApplyProfileDefaults();
   LogPresetConfig();
}

string PresetModeLabel(PresetMode mode)
{
   switch(mode)
   {
      case PRESET_CUSTOM:
         return "CUSTOM";
      case PRESET_BALANCED:
         return "BALANCED";
      case PRESET_CONSERVATIVE:
         return "CONSERVATIVE";
   }
   return "UNKNOWN";
}

void LogPresetConfig()
{
   Print("Preset applied: ", PresetModeLabel(cfg_InpPresetMode));
   PrintFormat("Profile: %s Symbol=%s Point=%.5f Pip=%.5f TickSize=%.5f",
               ProfileName(g_profile), g_symbol, g_point, g_pip, TickSize());
   if(cfg_InpUseManualNYOffset)
   {
      string dstNote = cfg_InpAutoNYDST ? "auto DST" : "manual DST";
      Print("NY offset: ", cfg_InpNYOffsetHours, " (", dstNote, ", summer=", cfg_InpNYOffsetSummerHours, ")");
   }

   PrintFormat("Session: use=%s hours=%02d-%02d ICT=%s KZ(Asia/London/NY)=%s/%s/%s",
               (cfg_InpUseSessionFilter ? "true" : "false"), cfg_InpStartHour, cfg_InpEndHour,
               (cfg_InpUseICTTime ? "true" : "false"),
               (cfg_InpUseKillzoneAsia ? "true" : "false"),
               (cfg_InpUseKillzoneLondon ? "true" : "false"),
               (cfg_InpUseKillzoneNY ? "true" : "false"));
   PrintFormat("Execution: spreadMaxPts=%d spreadMult=%s x%.2f blockMin=%d spreadInstab=%s spikeFactor=%.2f spikeBlockMin=%d slippagePts=%d retries=%d retryDelayMs=%d",
               cfg_InpMaxSpreadPoints, (cfg_InpUseSpreadMultiple ? "true" : "false"), cfg_InpSpreadMultiple,
               cfg_InpSpreadMultipleBlockMin, (cfg_InpUseSpreadInstability ? "true" : "false"),
               cfg_InpSpreadSpikeFactor, cfg_InpSpreadSpikeBlockMin, cfg_InpMaxSlippagePoints,
               cfg_InpMaxRetries, cfg_InpRetryDelayMs);
   PrintFormat("Indicators: ATR=%d ADX=%d RSI=%d EMA=%d/%d RegimeConfirmH1=%d RegimeLockH1=%d",
               cfg_InpATRPeriod, cfg_InpADXPeriod, cfg_InpRSIPeriod, cfg_InpEMA_Fast, cfg_InpEMA_Slow,
               cfg_InpRegimeConfirmBarsH1, cfg_InpRegimeLockBarsH1);
   PrintFormat("SMC: PivotLen=%d PivotConfirm=%d MaxBarsAfterBOS=%d EqScanBars=%d EqClusterMin=%d EqTolATR=%.2f EqTolMinPts=%.2f",
               cfg_InpPivotLen, cfg_InpPivotConfirmBars, cfg_InpMaxBarsAfterBOS,
               cfg_InpEqScanBars, cfg_InpEqClusterMin, cfg_InpEqToleranceATR, cfg_EqToleranceMinPoints);
   PrintFormat("SMC: DisplacementATR=%.2f BodyRatio=%.2f SearchBars=%d OBLookback=%d OBMaxAgeBars=%d",
               cfg_InpDisplacementATR, cfg_InpDisplacementBodyRatio, cfg_InpDisplacementSearchBars,
               cfg_InpOBLookback, cfg_InpOBMaxAgeBars);
   PrintFormat("SMC: OTE_HTF=%d SwingLookback=%d OTE_Min=%.2f OTE_Max=%.2f PDArrayDistPts=%.1f PDArrayATR=%.2f PDArrayMinPts=%d",
               cfg_InpOTE_HTF, cfg_InpOTE_SwingLookback, cfg_InpOTE_Min, cfg_InpOTE_Max,
               cfg_MinPDArrayDistancePoints, cfg_InpMinPDArrayATR, cfg_MinPDArrayMinPoints);
   PrintFormat("Filters: BreakRetest=%s RetestTolATR=%.2f KeyStepPts=%.1f KeyNearPts=%.1f KeyChaseMaxPts=%.1f",
               (cfg_InpUseBreakRetest ? "true" : "false"), cfg_InpRetestTolATR,
               cfg_KeyLevelStepPoints, cfg_KeyNearPoints, cfg_KeyChaseMaxDistPoints);
   PrintFormat("FVG/Fib: FVG=%s ScanBars=%d MaxDistATR=%.2f Fib=%s BaseMin=%.2f BaseMax=%.3f FibTolPts=%.1f OTEBonus=%s OTE_Min=%.2f OTE_Max=%.2f BonusPts=%d",
               (cfg_InpUseFVGFeature ? "true" : "false"), cfg_InpFVGScanBars, cfg_InpFVGMaxDistATR,
               (cfg_InpUseFibFilter ? "true" : "false"), cfg_InpFibBaseMin, cfg_InpFibBaseMax,
               cfg_FibTolPoints, (cfg_InpUseOTEBonus ? "true" : "false"),
               cfg_InpOTEMin, cfg_InpOTEMax, cfg_InpOTEBonusPoints);
   PrintFormat("Footprint/Spike: FP=%s VolMAPeriod=%d VolSpike=%.2f BodyMin=%.2f CloseSideMin=%.2f AbsorpVol=%.2f AbsorpRangeATR=%.2f RequireAccept=%s ScoreBonus=%d SpikeGuard=%s SpikeATR=%.2f",
               (cfg_InpUseFootprintProxy ? "true" : "false"), cfg_InpFP_VolMAPeriod, cfg_InpFP_VolSpikeRatio,
               cfg_InpFP_BodyMinRatio, cfg_InpFP_CloseSideMin, cfg_InpFP_AbsorpVolRatio, cfg_InpFP_AbsorpRangeATR,
               (cfg_InpFP_RequireAcceptance ? "true" : "false"), cfg_InpFP_ScoreBonus,
               (cfg_InpUseSpikeGuard ? "true" : "false"), cfg_InpSpikeMultATR);
   PrintFormat("Stops/Targets: SL_ATR=%.2f SL_MinBufferPts=%.1f MMSL=%s MMSL_Pips=%d MMSL_ExtraPts=%.1f RR=%.2f MinRR=%.2f TP1=%s TP1_Close=%.2f KeyFirst=%s",
               cfg_InpSL_ATR_Mult, cfg_SL_MinBufferPoints, (cfg_InpUseMMSL ? "true" : "false"),
               cfg_InpMMSL_Pips, cfg_MMSL_ExtraBufferPoints, cfg_InpTP_RR_Main, cfg_InpMinRRAllowed,
               (cfg_InpUseTP1Partial ? "true" : "false"), cfg_InpTP1_CloseFrac,
               (cfg_InpTP1_UseKeyLevelFirst ? "true" : "false"));
   PrintFormat("BE/Trail: SmartBE=%s MinProfitR=%.2f BE_OffsetPts=%.1f TrailAfterTP1=%s ATR_Mult=%.2f MinImprovePts=%.1f NewBarOnly=%s",
               (cfg_InpUseSmartBE ? "true" : "false"), cfg_InpBE_MinProfitR, cfg_BE_OffsetPoints,
               (cfg_InpUseATRTrailAfterTP1 ? "true" : "false"), cfg_InpTrailATR_Mult,
               cfg_TrailMinImprovePoints, (cfg_InpTrailOnNewBarOnly ? "true" : "false"));
   PrintFormat("Risk/Daily: BaseRiskPct=%.2f MaxLot=%.2f DailyControl=%s MaxTrades=%d MaxDailyLoss=%s %.2f%% SoftEqLock=%s Triggers=%.2f/%.2f Floors=%.2f/%.2f CooldownBars=%d",
               cfg_InpBaseRiskPct, cfg_InpMaxLotCap, (cfg_InpUseDailyTradeControl ? "true" : "false"),
               cfg_InpHardMaxTradesPerDay, (cfg_InpUseMaxDailyLossLock ? "true" : "false"),
               cfg_InpMaxDailyLossPct, (cfg_InpUseSoftEquityLock ? "true" : "false"),
               cfg_InpSoftEqTrigger1, cfg_InpSoftEqTrigger2, cfg_InpSoftEqFloor1, cfg_InpSoftEqFloor2,
               cfg_InpCooldownBarsAfterEntry);
   PrintFormat("AntiChop/RSI: AntiChop=%s LossBlock2H=%d LossBlock3H=%d RiskMultAfter3=%.2f RiskCutAfter3H=%d RSIAfterLoss=%s LossStreakRSI=%d",
               (cfg_InpUseAntiChop ? "true" : "false"), cfg_InpLossBlock2_Hours, cfg_InpLossBlock3_Hours,
               cfg_InpRiskMultAfter3Loss, cfg_InpRiskCutAfter3Loss_H,
               (cfg_InpUseRSIAfterLoss ? "true" : "false"), cfg_InpLossStreakForRSI);
   PrintFormat("Pyramiding: Enable=%s MaxAdds=%d MinProfitR=%.2f RequireMainBE=%s SpacingATR=%.2f OnlyTrend=%s RequireAdxRising=%s PeakDDCap=%s MaxPeakDD=%.2f AddRiskMult=%.2f/%.2f",
               (cfg_InpUsePyramiding ? "true" : "false"), cfg_InpMaxAdds, cfg_InpPyramidMinProfitR,
               (cfg_InpPyramidRequireMainBE ? "true" : "false"), cfg_InpPyramidSpacingATR,
               (cfg_InpPyramidOnlyInTrend ? "true" : "false"), (cfg_InpPyramidRequireAdxRising ? "true" : "false"),
               (cfg_InpPyramidUsePeakDDCap ? "true" : "false"), cfg_InpPyramidMaxPeakDDPct,
               cfg_InpAddRiskMult1, cfg_InpAddRiskMult2);

   double irBasePct = RiskInputToPercent(InpRiskBasePct);
   if(irBasePct > 50.0 || irBasePct < 0.01)
      PrintFormat("Warning: Institutional base risk out of sane range (%.4f%%).", irBasePct);
}

void LogSymbolCheck()
{
   string symUpper = g_symbol;
   StringToUpper(symUpper);
   bool symbolMatch = (StringFind(symUpper, "GOLD") >= 0 || StringFind(symUpper, "XAU") >= 0);
   bool digitsOk = (g_digits == 2 && MathAbs(g_point - 0.01) <= 0.000001);
   double tickSize = TickSize();
   double expectedPip = AutoPipSize(false);

   Print("Symbol check: symbol=", g_symbol, " profile=", ProfileName(g_profile),
         " digits=", g_digits, " point=", DoubleToString(g_point, 5),
         " pip=", DoubleToString(g_pip, 5), " tickSize=", DoubleToString(tickSize, 5));

   if(g_isGoldSymbol)
   {
      if(!symbolMatch)
         Print("Warning: Symbol is not GOLD/XAUUSD. Verify XM GOLD settings.");
      if(!digitsOk)
         Print("Warning: Unexpected digits/point for GOLD. Expected digits=2 and point=0.01. Verify cfg_InpPipPrice/g_pip.");
   }

   if(tickSize > 0.0 && MathAbs(tickSize - g_point) > 1e-7)
      Print("Warning: TickSize differs from Point. Using tickSize for risk math where applicable.");
   if(cfg_InpPipPrice <= 0.0 && MathAbs(g_pip - expectedPip) > 1e-7)
      Print("Warning: Auto pip size differs from expected calculation. Check symbol digits/override.");
}

void LogCSV(const string event, TradeDir dir, double entry, double sl, double tp, double tp1, double lot,
            int dailyScore, int setup, int timing, int total, int skipMask, int entryMask,
            int retcode, int lasterr, double bosLevel, int bosAgeBars, double nearestKey,
            int killzoneActive, double pdh, double pdl, double psh, double psl, double hod, double lod,
            int sweepDir, double sweepLevel, double displacementScore, double obHigh, double obLow, double obMT,
            int oteOk)
{
   LogCSVEx(event, dir, entry, sl, tp, tp1, lot, dailyScore, setup, timing, total, skipMask, entryMask,
            retcode, lasterr, bosLevel, bosAgeBars, nearestKey, killzoneActive, pdh, pdl, psh, psl, hod, lod,
            sweepDir, sweepLevel, displacementScore, obHigh, obLow, obMT, oteOk,
            0, 0, 0.0, 0, 0, 0, 0, 0.0, 0.0);
}

void LogCSVEx(const string event, TradeDir dir, double entry, double sl, double tp, double tp1, double lot,
              int dailyScore, int setup, int timing, int total, int skipMask, int entryMask,
              int retcode, int lasterr, double bosLevel, int bosAgeBars, double nearestKey,
              int killzoneActive, double pdh, double pdl, double psh, double psl, double hod, double lod,
              int sweepDir, double sweepLevel, double displacementScore, double obHigh, double obLow, double obMT,
              int oteOk, int sdHit, int sdType, double sdDistATR, int sdFresh,
              int candleHit, int candleType, int momHit, double rsi1, double rsi2)
{
   if(!cfg_InpEnableCSV)
      return;

   int handle = FileOpen(cfg_InpCSVName, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      handle = FileOpen(cfg_InpCSVName, FILE_WRITE | FILE_CSV | FILE_ANSI);

   if(handle == INVALID_HANDLE)
   {
      if(!g_csvOpenWarned)
      {
         Print("Warning: CSV log file open failed; continuing without CSV logging.");
         g_csvOpenWarned = true;
      }
      return;
   }

   g_csvOpenWarned = false;

   if(FileSize(handle) == 0)
   {
      FileWrite(handle, "time", "sym", "profile", "point", "pipSize", "tickSize", "magic", "event", "dir", "entry", "sl", "tp", "tp1", "lot", "spreadPts",
                "reg", "bias", "adx", "atrM15", "atrH1", "dailyScore", "lossStreak", "skipMask", "entryMask",
                "setup", "timing", "total", "retcode", "lasterr", "spreadEma", "spreadNow",
                "stopsLevelPts", "freezeLevelPts", "bosLevel", "bosAgeBars", "nearestKey", "tp1Target", "tp1FillPrice",
                "killzoneActive", "pdh", "pdl", "psh", "psl", "hod", "lod",
                "sweepDir", "sweepLevel", "displacementScore", "obHigh", "obLow", "obMT", "oteOk",
                "sdHit", "sdType", "sdDistATR", "sdFresh", "candleHit", "candleType",
                "momHit", "rsi1", "rsi2",
                "irEntryScore", "irTier", "irRiskBasePct", "irScoreMult", "irRegimeMult", "irFearMult", "irFinalRiskPct",
                "irRiskMoney", "irStopDistancePoints", "irLots", "irSpreadPoints", "irAtrRatio", "irLossStreak", "irDailyDD",
                "instPattern", "instPatternScore", "instTotalScore", "instRiskMult",
                "pePatternId", "peDir", "peEntry", "peSL", "peTP1", "pePrior", "peFinalScore", "peDelta",
                "peOutcomePips", "peMaxFavor", "peMaxAdverse", "peBreakdown");
   }

   int lossStreak = GVGetInt("lossStreak", 0);
   RegimeState reg = (RegimeState)GVGetInt("regime", REGIME_RANGE);
   TradeDir bias = BiasH1();
   double adx = ADX(PERIOD_H1, 1);
   double atrM15 = ATR(PERIOD_M15, 1);
   double atrH1 = ATR(PERIOD_H1, 1);

   double spreadNow = SpreadPoints();
   int stopsLevel = (int)SymbolInfoInteger(g_symbol, SYMBOL_TRADE_STOPS_LEVEL);
   int freezeLevel = (int)SymbolInfoInteger(g_symbol, SYMBOL_TRADE_FREEZE_LEVEL);

   FileWrite(handle,
             TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES),
             g_symbol,
             ProfileName(g_profile),
             DoubleToString(g_point, 5),
             DoubleToString(g_pip, 5),
             DoubleToString(TickSize(), 5),
             (string)cfg_InpMagic,
             event,
             (int)dir,
             DoubleToString(NormalizePrice(entry), g_digits),
             DoubleToString(NormalizePrice(sl), g_digits),
             DoubleToString(NormalizePrice(tp), g_digits),
             DoubleToString(NormalizePrice(tp1), g_digits),
             DoubleToString(lot, 2),
             DoubleToString(spreadNow, 1),
             (int)reg,
             (int)bias,
             DoubleToString(adx, 2),
             DoubleToString(atrM15, 2),
             DoubleToString(atrH1, 2),
             dailyScore,
             lossStreak,
             skipMask,
             entryMask,
             setup,
             timing,
             total,
             retcode,
             lasterr,
             DoubleToString(g_spreadEma, 2),
             DoubleToString(spreadNow, 1),
             stopsLevel,
             freezeLevel,
             DoubleToString(bosLevel, g_digits),
             bosAgeBars,
             DoubleToString(nearestKey, g_digits),
             DoubleToString(tp1, g_digits),
             DoubleToString(GVGetDouble("tp1FillPrice", 0.0), g_digits),
             killzoneActive,
             DoubleToString(pdh, g_digits),
             DoubleToString(pdl, g_digits),
             DoubleToString(psh, g_digits),
             DoubleToString(psl, g_digits),
             DoubleToString(hod, g_digits),
             DoubleToString(lod, g_digits),
             sweepDir,
             DoubleToString(sweepLevel, g_digits),
             DoubleToString(displacementScore, 2),
             DoubleToString(obHigh, g_digits),
             DoubleToString(obLow, g_digits),
             DoubleToString(obMT, g_digits),
             oteOk,
             sdHit,
             sdType,
             DoubleToString(sdDistATR, 2),
             sdFresh,
             candleHit,
             candleType,
             momHit,
             DoubleToString(rsi1, 2),
             DoubleToString(rsi2, 2),
             g_irEntryScore,
             g_irTier,
             DoubleToString(g_irRiskBasePct, 5),
             DoubleToString(g_irScoreMult, 3),
             DoubleToString(g_irRegimeMult, 3),
             DoubleToString(g_irFearMult, 3),
             DoubleToString(g_irFinalRiskPct, 5),
             DoubleToString(g_irRiskMoney, 2),
             DoubleToString(g_irStopDistancePoints, 1),
             DoubleToString(g_irLots, 2),
             DoubleToString(g_irSpreadPoints, 1),
             DoubleToString(g_irAtrRatio, 2),
             g_irLossStreak,
             DoubleToString(g_irDailyDD, 2),
             GetPatternName(g_instPattern),
             g_instPatternScore,
             g_instTotalScore,
             DoubleToString(g_instRiskMult, 2),
             (g_patternSignal.detected ? g_patternSignal.pattern_id : "NONE"),
             (g_patternSignal.detected ? g_patternSignal.direction : 0),
             DoubleToString(g_patternSignal.entry_level, g_digits),
             DoubleToString(g_patternSignal.invalidation_level, g_digits),
             DoubleToString(g_patternSignal.target_level, g_digits),
             DoubleToString(g_patternPriorScore, 2),
             DoubleToString(g_patternFinalScore, 2),
             DoubleToString(g_patternScoreDelta, 2),
             DoubleToString(g_patternOutcomePips, 2),
             DoubleToString(g_patternMaxFavorPips, 2),
             DoubleToString(g_patternMaxAdversePips, 2),
             g_patternBreakdown);

   FileClose(handle);
}

bool CalculateEntryCore(TradeDir &dir, double &entry, double &sl, double &tp, double &tp1, double &riskR,
                    int &setupScore, int &timingScore, int &totalScore, int &skipMask, int &entryMask,
                    double &nearestKey, double &bosLevel, int &bosAgeBars, int &killzoneActive,
                    double &pdh, double &pdl, double &psh, double &psl, double &hod, double &lod,
                    int &sweepDir, double &sweepLevel, double &displacementScore,
                    double &obHigh, double &obLow, double &obMT, int &oteOk,
                    int &sdHit, int &sdType, double &sdDistATR, int &sdFresh,
                    int &candleHit, int &candleType,
                    int &momHit, double &rsi1, double &rsi2)
{
   setupScore = 0;
   timingScore = 0;
   totalScore = 0;
   skipMask = 0;
   entryMask = 0;
   dir = DIR_NONE;
   nearestKey = 0.0;
   bosLevel = 0.0;
   bosAgeBars = -1;
   killzoneActive = 0;
   pdh = pdl = psh = psl = hod = lod = 0.0;
   sweepDir = 0;
   sweepLevel = 0.0;
   displacementScore = 0.0;
   obHigh = obLow = obMT = 0.0;
   oteOk = 0;
   sdHit = 0;
   sdType = 0;
   sdDistATR = 0.0;
   sdFresh = 0;
   candleHit = 0;
   candleType = 0;
   momHit = 0;
   rsi1 = 0.0;
   rsi2 = 0.0;

   TradeDir bias = BiasH1();
   if(bias == DIR_NONE)
      return false;
   dir = bias;
   setupScore += 20;
   entryMask |= ENTRY_BIAS;

   bool kzAsia = false;
   bool kzLondon = false;
   bool kzNY = false;
   if(cfg_InpUseICTTime)
   {
      bool kzActive = KillzoneActive(kzAsia, kzLondon, kzNY);
      killzoneActive = kzActive ? 1 : 0;
      if(!kzActive)
      {
         skipMask |= SKIP_KILLZONE;
         return false;
      }
      entryMask |= ENTRY_KILLZONE;
      setupScore += 5;
   }

   GetPDLevels(pdh, pdl);
   GetPSHPSL(psh, psl);
   GetHODLOD_Cached(hod, lod);

   TradeDir sweepDirFound = DIR_NONE;
   double sweepLevelFound = 0.0;
   if(!DetectLiquiditySweep(sweepDirFound, sweepLevelFound))
      return false;
   if(sweepDirFound != dir)
   {
      if(cfg_InpRequireBiasAlignWithSweep)
         return false;
      dir = sweepDirFound;
      setupScore -= 5;
   }
   sweepDir = (int)sweepDirFound;
   sweepLevel = sweepLevelFound;
   entryMask |= ENTRY_SWEEP;
   setupScore += 10;

   double atrM15 = ATR(PERIOD_M15, 1);
   if(!DisplacementOk(sweepDirFound, displacementScore))
      return false;
   entryMask |= ENTRY_DISPLACEMENT;
   setupScore += 10;

   double lastHigh = 0.0, prevHigh = 0.0, lastLow = 0.0, prevLow = 0.0;
   if(!FindRecentPivots(lastHigh, prevHigh, lastLow, prevLow))
      return false;
   entryMask |= ENTRY_PIVOT;

   if(dir == DIR_LONG && !(lastLow > prevLow))
      return false;
   if(dir == DIR_SHORT && !(lastHigh < prevHigh))
      return false;
   setupScore += 10;
   entryMask |= ENTRY_HL_LH;

   double close1 = iClose(g_symbol, PERIOD_M15, 1);
   if(dir == DIR_LONG && close1 <= lastHigh)
      return false;
   if(dir == DIR_SHORT && close1 >= lastLow)
      return false;
   entryMask |= ENTRY_MSS;
   timingScore += 10;

   bosLevel = (dir == DIR_LONG) ? lastHigh : lastLow;
   bool closeConfirm = (dir == DIR_LONG) ? (close1 > bosLevel) : (close1 < bosLevel);
   if(closeConfirm)
   {
      entryMask |= ENTRY_BOS_CLOSE;
      StoreBOS(dir, bosLevel, iTime(g_symbol, PERIOD_M15, 1));
   }

   bool brOk = BreakRetestOk(dir, atrM15);
   if(brOk)
      entryMask |= ENTRY_BOS_RETEST;
   if(!closeConfirm && !brOk)
   {
      bosAgeBars = BOSAgeBars(bosLevel);
      return false;
   }

   double mid = (SymbolInfoDouble(g_symbol, SYMBOL_ASK) + SymbolInfoDouble(g_symbol, SYMBOL_BID)) / 2.0;
   if(!KeyLevelNearOk(mid, nearestKey))
      return false;
   entryMask |= ENTRY_KEYLEVEL;

   if(!AntiChaseOk(dir, mid, nearestKey))
      return false;
   entryMask |= ENTRY_ANTICHASE;
   setupScore += 5;

   if(cfg_InpUseFVGFeature)
   {
      if(!FVGOk(dir, mid, atrM15))
         return false;
      entryMask |= ENTRY_FVG;
      setupScore += 5;
   }

   bool oteBonus = false;
   if(!FibFilterOk(dir, mid, lastLow, lastHigh, oteBonus))
      return false;
   entryMask |= ENTRY_FIB;
   setupScore += 10;
   if(oteBonus)
      setupScore += cfg_InpOTEBonusPoints;

   double oteMin = 0.0;
   double oteMax = 0.0;
   double swingHigh = 0.0;
   double swingLow = 0.0;
   if(!OTEOk(dir, mid, oteMin, oteMax, swingHigh, swingLow))
      return false;
   oteOk = 1;
   entryMask |= ENTRY_OTE;
   setupScore += 10;
   if(MathAbs(mid - swingHigh) <= PriceFromPoints(cfg_KeyNearPoints) ||
      MathAbs(mid - swingLow) <= PriceFromPoints(cfg_KeyNearPoints))
      entryMask |= ENTRY_SR;

   bool absorption = false;
   bool acceptance = true;
   if(!FootprintOk(dir, atrM15, absorption, acceptance))
      return false;
   entryMask |= ENTRY_FOOTPRINT;
   if(acceptance)
      timingScore += cfg_InpFP_ScoreBonus;

   if(!SpikeGuardOk(atrM15))
      return false;
   entryMask |= ENTRY_SPIKE;

   if(!RSIAfterLossOk(dir))
      return false;
   entryMask |= ENTRY_RSI_LOSS;

   if(DetectSupplyDemandBonus(dir, sdType, sdDistATR, sdFresh))
   {
      sdHit = 1;
      entryMask |= ENTRY_SD;
      setupScore += cfg_InpSD_BonusPoints;
      if(sdFresh == 1)
         setupScore += cfg_InpSD_FreshnessBonus;
   }

   if(CandleBonus(dir, candleType))
   {
      candleHit = 1;
      entryMask |= ENTRY_CANDLE;
      setupScore += cfg_InpCandleBonusPoints;
   }

   if(MomentumBonus(dir, rsi1, rsi2))
   {
      momHit = 1;
      entryMask |= ENTRY_MOM;
      timingScore += cfg_InpMomentumBonusPoints;
   }

   int obAgeBars = -1;
   if(!FindOrderBlock(dir, obHigh, obLow, obMT, obAgeBars))
      return false;
   if(obAgeBars > cfg_InpOBMaxAgeBars)
      return false;
   if(!(mid >= obLow && mid <= obHigh))
      return false;
   entryMask |= ENTRY_OB_RTO;
   setupScore += 10;

   entry = (dir == DIR_LONG) ? SymbolInfoDouble(g_symbol, SYMBOL_ASK) : SymbolInfoDouble(g_symbol, SYMBOL_BID);
   double atrBuf = atrM15 * cfg_InpSL_ATR_Mult;
   double spreadBuf = SpreadPoints() * g_point * 0.5;
   double buffer = MathMax(PriceFromPoints(cfg_SL_MinBufferPoints), MathMax(atrBuf, spreadBuf));

   sl = (dir == DIR_LONG) ? (lastLow - buffer) : (lastHigh + buffer);
   riskR = MathAbs(entry - sl);
   if(riskR <= 0.0)
      return false;

   if(cfg_InpUseMMSL)
   {
      double mmsl = cfg_InpMMSL_Pips * PipPrice() + PriceFromPoints(cfg_MMSL_ExtraBufferPoints);
      if(riskR < mmsl)
         return false;
      entryMask |= ENTRY_MMSL;
   }

   tp = (dir == DIR_LONG) ? (entry + riskR * cfg_InpTP_RR_Main) : (entry - riskR * cfg_InpTP_RR_Main);
   double rr = MathAbs(tp - entry) / riskR;
   if(rr < cfg_InpMinRRAllowed)
      return false;
   entryMask |= ENTRY_RR;

   tp1 = (dir == DIR_LONG) ? (entry + riskR) : (entry - riskR);
   if(cfg_InpUseTP1Partial && cfg_InpTP1_UseKeyLevelFirst)
   {
      if(dir == DIR_LONG)
      {
         double key = KeyAbove(entry);
         if(key < tp1 && (key - entry) > PipPrice())
            tp1 = key;
      }
      else
      {
         double key = KeyBelow(entry);
         if(key > tp1 && (entry - key) > PipPrice())
            tp1 = key;
      }
   }

   double target = (dir == DIR_LONG) ? MathMin(MathMin(pdh, psh > 0.0 ? psh : pdh), hod)
                                     : MathMax(MathMax(pdl, psl > 0.0 ? psl : pdl), lod);
   double space = (dir == DIR_LONG) ? (target - entry) : (entry - target);
   if(space < PriceFromPoints(cfg_MinPDArrayDistancePoints))
   {
      skipMask |= SKIP_PDARRAY;
      return false;
   }
   entryMask |= ENTRY_PDARRAY;

   entry = NormalizePrice(entry);
   sl = NormalizePrice(sl);
   tp = NormalizePrice(tp);
   tp1 = NormalizePrice(tp1);

   bosAgeBars = BOSAgeBars(bosLevel);
   totalScore = setupScore + timingScore;
   return true;
}

class IStrategy
{
public:
   virtual bool Evaluate(TradeDir &dir, double &entry, double &sl, double &tp, double &tp1, double &riskR,
                         int &setupScore, int &timingScore, int &totalScore, int &skipMask, int &entryMask,
                         double &nearestKey, double &bosLevel, int &bosAgeBars, int &killzoneActive,
                         double &pdh, double &pdl, double &psh, double &psl, double &hod, double &lod,
                         int &sweepDir, double &sweepLevel, double &displacementScore,
                         double &obHigh, double &obLow, double &obMT, int &oteOk,
                         int &sdHit, int &sdType, double &sdDistATR, int &sdFresh,
                         int &candleHit, int &candleType,
                         int &momHit, double &rsi1, double &rsi2) = 0;
};

class TrendSMCStrategy : public IStrategy
{
public:
   virtual bool Evaluate(TradeDir &dir, double &entry, double &sl, double &tp, double &tp1, double &riskR,
                         int &setupScore, int &timingScore, int &totalScore, int &skipMask, int &entryMask,
                         double &nearestKey, double &bosLevel, int &bosAgeBars, int &killzoneActive,
                         double &pdh, double &pdl, double &psh, double &psl, double &hod, double &lod,
                         int &sweepDir, double &sweepLevel, double &displacementScore,
                         double &obHigh, double &obLow, double &obMT, int &oteOk,
                         int &sdHit, int &sdType, double &sdDistATR, int &sdFresh,
                         int &candleHit, int &candleType,
                         int &momHit, double &rsi1, double &rsi2)
   {
      return CalculateEntryCore(dir, entry, sl, tp, tp1, riskR,
                                setupScore, timingScore, totalScore, skipMask, entryMask,
                                nearestKey, bosLevel, bosAgeBars, killzoneActive,
                                pdh, pdl, psh, psl, hod, lod,
                                sweepDir, sweepLevel, displacementScore,
                                obHigh, obLow, obMT, oteOk,
                                sdHit, sdType, sdDistATR, sdFresh,
                                candleHit, candleType,
                                momHit, rsi1, rsi2);
   }
};

class StrategyManager
{
private:
   TrendSMCStrategy m_trend;
public:
   IStrategy* Select()
   {
      return &m_trend;
   }
};

bool CalculateEntry(TradeDir &dir, double &entry, double &sl, double &tp, double &tp1, double &riskR,
                    int &setupScore, int &timingScore, int &totalScore, int &skipMask, int &entryMask,
                    double &nearestKey, double &bosLevel, int &bosAgeBars, int &killzoneActive,
                    double &pdh, double &pdl, double &psh, double &psl, double &hod, double &lod,
                    int &sweepDir, double &sweepLevel, double &displacementScore,
                    double &obHigh, double &obLow, double &obMT, int &oteOk,
                    int &sdHit, int &sdType, double &sdDistATR, int &sdFresh,
                    int &candleHit, int &candleType,
                    int &momHit, double &rsi1, double &rsi2)
{
   static StrategyManager manager;
   IStrategy *strategy = manager.Select();
   return strategy->Evaluate(dir, entry, sl, tp, tp1, riskR,
                            setupScore, timingScore, totalScore, skipMask, entryMask,
                            nearestKey, bosLevel, bosAgeBars, killzoneActive,
                            pdh, pdl, psh, psl, hod, lod,
                            sweepDir, sweepLevel, displacementScore,
                            obHigh, obLow, obMT, oteOk,
                            sdHit, sdType, sdDistATR, sdFresh,
                            candleHit, candleType,
                            momHit, rsi1, rsi2);
}

bool ShouldEnterTrade(int setupScore, int timingScore, int totalScore, RegimeState regime)
{
   int totalMin = TOTAL_MIN;
   int lossStreak = GVGetInt("lossStreak", 0);

   if(regime == REGIME_TRANSITION)
      totalMin += 3;
   else if(regime == REGIME_EXPANSION)
      totalMin += 8;

   if(lossStreak == 1)
      totalMin += 5;
   else if(lossStreak >= 2)
      totalMin += 10;

   return (setupScore >= SETUP_MIN && timingScore >= TIMING_MIN && totalScore >= totalMin);
}

void ManagePosition(double riskR)
{
   if(!SelectOurPosition())
      return;

   ulong ticket = PositionGetInteger(POSITION_TICKET);
   int type = (int)PositionGetInteger(POSITION_TYPE);
   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl = PositionGetDouble(POSITION_SL);
   double tp = PositionGetDouble(POSITION_TP);
   double volume = PositionGetDouble(POSITION_VOLUME);
   double price = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_symbol, SYMBOL_BID) : SymbolInfoDouble(g_symbol, SYMBOL_ASK);

   if(riskR <= 0.0)
      return;
   double profitR = (type == POSITION_TYPE_BUY) ? (price - entry) / riskR : (entry - price) / riskR;

   PatternEngine_UpdateMfeMae();

   if(UseBustedLogic)
   {
      datetime et = (datetime)GVGetDouble("lastEntryTime", 0.0);
      int barsFromEntry = (et > 0 ? iBarShift(g_symbol, PERIOD_M15, et, true) : 9999);
      double breakoutLevel = GVGetDouble("pattern_breakout_level", 0.0);
      double atrNow = ATR(PERIOD_M15, 1);
      bool weakMove = (MathAbs(price - entry) < atrNow * InpBustedMinATR);
      bool busted = false;
      if(type == POSITION_TYPE_BUY && breakoutLevel > 0.0) busted = (price < breakoutLevel);
      if(type == POSITION_TYPE_SELL && breakoutLevel > 0.0) busted = (price > breakoutLevel);
      if(busted && weakMove && barsFromEntry <= InpBustedBars)
      {
         trade.PositionClose(ticket);
         Print("[PatternEngine] BUSTED close executed.");
         return;
      }
   }

   bool tp1done = GVGetInt("tp1done", 0) == 1;
   double tp1price = GVGetDouble("tp1price", 0.0);

   bool tp1Hit = false;
   if(type == POSITION_TYPE_BUY)
      tp1Hit = (tp1price > 0.0 && SymbolInfoDouble(g_symbol, SYMBOL_BID) >= tp1price);
   else
      tp1Hit = (tp1price > 0.0 && SymbolInfoDouble(g_symbol, SYMBOL_ASK) <= tp1price);

   if(cfg_InpUseTP1Partial && !tp1done && tp1Hit)
   {
      double step = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP);
      double minLot = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN);
      double closeVol = MathFloor((volume * cfg_InpTP1_CloseFrac) / step) * step;
      closeVol = NormalizeVolumeByStep(closeVol);
      if(closeVol >= minLot && (volume - closeVol) >= minLot && FreezeOkForClose())
      {
         trade.PositionClosePartial(ticket, closeVol);
         GVSetInt("tp1done", 1);
         GVSetDouble("tp1FillPrice", price);
         double bosLevel = 0.0;
         int bosAgeBars = BOSAgeBars(bosLevel);
         LogCSV("TP1", (type == POSITION_TYPE_BUY ? DIR_LONG : DIR_SHORT), entry, sl, tp, tp1price, volume, 0, 0, 0, 0, 0, 0,
                0, 0, bosLevel, bosAgeBars, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0, 0.0, 0.0, 0.0, 0.0, 0.0, 0);
      }
   }

   if(cfg_InpUseSmartBE && profitR >= cfg_InpBE_MinProfitR)
   {
      double newSL = (type == POSITION_TYPE_BUY) ? (entry + PriceFromPoints(cfg_BE_OffsetPoints))
                                                 : (entry - PriceFromPoints(cfg_BE_OffsetPoints));
      TradeDir dir = (type == POSITION_TYPE_BUY) ? DIR_LONG : DIR_SHORT;
      if(CanModifyStops(newSL) && StopsOk(dir, entry, newSL, tp) &&
         ((type == POSITION_TYPE_BUY && newSL > sl) || (type == POSITION_TYPE_SELL && newSL < sl)))
         trade.PositionModify(ticket, newSL, tp);
   }

   if(cfg_InpUseATRTrailAfterTP1 && tp1done)
   {
      if(!cfg_InpTrailOnNewBarOnly || IsNewBar(PERIOD_M15, g_lastM15Bar))
      {
         double atr = ATR(PERIOD_M15, 1);
         double newSL = (type == POSITION_TYPE_BUY) ? (price - atr * cfg_InpTrailATR_Mult) : (price + atr * cfg_InpTrailATR_Mult);
         TradeDir dir = (type == POSITION_TYPE_BUY) ? DIR_LONG : DIR_SHORT;
         if(type == POSITION_TYPE_BUY && newSL > sl + PriceFromPoints(cfg_TrailMinImprovePoints) && CanModifyStops(newSL) &&
            StopsOk(dir, entry, newSL, tp))
            trade.PositionModify(ticket, newSL, tp);
         else if(type == POSITION_TYPE_SELL && newSL < sl - PriceFromPoints(cfg_TrailMinImprovePoints) && CanModifyStops(newSL) &&
                 StopsOk(dir, entry, newSL, tp))
            trade.PositionModify(ticket, newSL, tp);
      }
   }

}

void TryPyramiding(double riskR, bool pyramidAllowed, RegimeState regime)
{
   if(!cfg_InpUsePyramiding || !pyramidAllowed)
      return;
   if(!SelectOurPosition())
      return;

   int addCount = GVGetInt("addCount", 0);
   if(addCount >= cfg_InpMaxAdds)
      return;

   int type = (int)PositionGetInteger(POSITION_TYPE);
   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl = PositionGetDouble(POSITION_SL);
   double price = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_symbol, SYMBOL_BID) : SymbolInfoDouble(g_symbol, SYMBOL_ASK);
   double profitR = (type == POSITION_TYPE_BUY) ? (price - entry) / riskR : (entry - price) / riskR;

   if(profitR < cfg_InpPyramidMinProfitR)
      return;

   double lastAddPrice = GVGetDouble("lastAddPrice", entry);
   double atr = ATR(PERIOD_M15, 1);
   if(MathAbs(price - lastAddPrice) < atr * cfg_InpPyramidSpacingATR)
      return;

   if(cfg_InpPyramidRequireMainBE)
   {
      if(type == POSITION_TYPE_BUY && sl < entry + g_point)
         return;
      if(type == POSITION_TYPE_SELL && sl > entry - g_point)
         return;
   }

   if(cfg_InpPyramidOnlyInTrend && regime != REGIME_TREND)
      return;

   if(cfg_InpPyramidRequireAdxRising)
   {
      double adx1 = ADX(PERIOD_H1, 1);
      double adx2 = ADX(PERIOD_H1, 2);
      if(adx1 <= adx2)
         return;
   }

   if(cfg_InpPyramidUsePeakDDCap)
   {
      double peak = GVGetDouble("dayEquityPeak", AccountInfoDouble(ACCOUNT_EQUITY));
      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      double dd = (peak - equity) / peak * 100.0;
      if(dd > cfg_InpPyramidMaxPeakDDPct)
         return;
   }

   double riskMult = (addCount == 0) ? cfg_InpAddRiskMult1 : cfg_InpAddRiskMult2;
   double addLots = CalcLots(riskR, cfg_InpBaseRiskPct * riskMult);
   if(addLots <= 0.0)
      return;

   double addTp = (type == POSITION_TYPE_BUY) ? (price + riskR * cfg_InpTP_RR_Main) : (price - riskR * cfg_InpTP_RR_Main);
   TradeDir dir = (type == POSITION_TYPE_BUY) ? DIR_LONG : DIR_SHORT;
   if(!StopsOk(dir, price, sl, addTp))
      return;

   bool result = false;
   int retcode = 0;
   int lasterr = 0;
   result = TryOpenByDir(dir, addLots, sl, addTp, "PYR", retcode, lasterr);

   if(result)
   {
      GVSetInt("addCount", addCount + 1);
      GVSetDouble("lastAddPrice", price);
      double bosLevel = 0.0;
      int bosAgeBars = BOSAgeBars(bosLevel);
      LogCSV("PYR", dir, price, sl, addTp, 0.0, addLots, 0, 0, 0, 0, 0, 0,
             retcode, lasterr, bosLevel, bosAgeBars, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
             0, 0.0, 0.0, 0.0, 0.0, 0.0, 0);
   }
}


void PatternEngine_Init()
{
   ArrayResize(g_patternStats, 0);
   g_patternStatsLoaded = PE_LoadPatternStatsCSV(PatternCSVFileName, g_patternStats);
   if(!g_patternStatsLoaded)
      Print("[PatternEngine] stats CSV not found, using neutral priors: ", PatternCSVFileName);
   g_patternSignal.detected = false;
   g_patternCacheBar = 0;
   g_patternPriorScore = 50.0;
   g_patternFinalScore = 0.0;
   g_patternScoreDelta = 0.0;
}

double PatternEngine_ComputePrior(const PatternSignal &sig)
{
   if(!sig.detected || !UsePatternPriors)
      return 50.0;
   PatternStats st;
   if(g_patternStatsLoaded)
      st = PE_GetStatsById(g_patternStats, sig.pattern_id, sig.direction);
   else
      PE_DefaultStats(st, sig.pattern_id, sig.family, sig.direction);

   return PE_PatternPriorScore(st, InpPattern_kRank, InpPattern_kFail, InpPattern_kTarget, InpPattern_kMove);
}

void PatternEngine_Update()
{
   if(!UsePatternEngine)
   {
      g_patternSignal.detected = false;
      g_patternPriorScore = 50.0;
      return;
   }
   datetime barTime = iTime(g_symbol, InpPatternTF, 1);
   if(barTime == 0 || barTime == g_patternCacheBar)
      return;

   g_patternCacheBar = barTime;
   double atr = ATR(InpPatternTF, 1);
   if(atr <= 0.0)
      atr = ATR(PERIOD_M15, 1);
   g_patternSignal = PE_DetectBestPattern(g_symbol, InpPatternTF, InpPatternLookback, InpPatternPivotLR, g_point, atr);
   g_patternPriorScore = PatternEngine_ComputePrior(g_patternSignal);

   ZeroMemory(g_patternCtx);
   double dayOpen = iOpen(g_symbol, PERIOD_D1, 0);
   double prevClose = iClose(g_symbol, PERIOD_D1, 1);
   g_patternCtx.breakoutGap = (MathAbs(dayOpen - prevClose) > atr * 0.10);
   long v1 = iVolume(g_symbol, InpPatternTF, 1);
   double vma = 0.0; int vn = 0;
   for(int i=2;i<=31;i++){ long vi=iVolume(g_symbol, InpPatternTF, i); if(vi>0){ vma += (double)vi; vn++; } }
   if(vn>0) vma /= vn;
   g_patternCtx.breakoutVolHigh = (vma > 0.0 && (double)v1 > vma * 1.2);
   double span = (g_patternSignal.detected ? MathAbs(g_patternSignal.entry_level - g_patternSignal.invalidation_level) : 0.0);
   g_patternCtx.patternTall = (span > atr * 1.2);
   g_patternCtx.patternWide = (InpPatternLookback >= 80);
   double c1 = iClose(g_symbol, InpPatternTF, 1);
   g_patternCtx.throwbackRisk = (g_patternSignal.detected && g_patternSignal.direction > 0 && c1 < g_patternSignal.entry_level);
   g_patternCtx.pullbackRisk = (g_patternSignal.detected && g_patternSignal.direction < 0 && c1 > g_patternSignal.entry_level);

   double ctxAdj = PE_ContextAdjustment(g_patternCtx);
   g_patternPriorScore = MathMax(0.0, MathMin(100.0, g_patternPriorScore + ctxAdj));
   g_patternBreakdown = StringFormat("gap=%d vol=%d tall=%d wide=%d throwback=%d pullback=%d adj=%.1f", (int)g_patternCtx.breakoutGap, (int)g_patternCtx.breakoutVolHigh, (int)g_patternCtx.patternTall, (int)g_patternCtx.patternWide, (int)g_patternCtx.throwbackRisk, (int)g_patternCtx.pullbackRisk, ctxAdj);

   if(g_patternSignal.detected)
   {
      PrintFormat("[PatternEngine] id=%s dir=%d prior=%.1f q=%.2f entry=%.3f inv=%.3f tp=%.3f %s",
                  g_patternSignal.pattern_id, g_patternSignal.direction, g_patternPriorScore, g_patternSignal.quality,
                  g_patternSignal.entry_level, g_patternSignal.invalidation_level, g_patternSignal.target_level, g_patternBreakdown);
   }
}

void PatternEngine_UpdateMfeMae()
{
   if(!SelectOurPosition())
      return;
   int type = (int)PositionGetInteger(POSITION_TYPE);
   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   double px = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_symbol, SYMBOL_BID) : SymbolInfoDouble(g_symbol, SYMBOL_ASK);
   double pipsNow = (type == POSITION_TYPE_BUY ? (px - entry) : (entry - px)) / MathMax(g_pip, g_point);
   double mfe = GVGetDouble("pattern_mfe", 0.0);
   double mae = GVGetDouble("pattern_mae", 0.0);
   if(pipsNow > mfe) GVSetDouble("pattern_mfe", pipsNow);
   if(pipsNow < mae) GVSetDouble("pattern_mae", pipsNow);
}

int OnInit()
{
   g_symbol = ResolveSymbol();
   g_digits = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);
   g_point = SymbolInfoDouble(g_symbol, SYMBOL_POINT);
   g_isGoldSymbol = IsGoldSymbol(g_symbol);
   g_profile = DetectSymbolProfile(g_symbol);

   ApplyPreset();
   PatternEngine_Init();
   if(InpRunSelfTestOnInit) SelfTest();

   trade.SetExpertMagicNumber((uint)cfg_InpMagic);
   trade.SetDeviationInPoints(cfg_InpMaxSlippagePoints);

   double tickSize = TickSize();
   double tickValue = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE);
   Print("Symbol=", g_symbol, " Digits=", g_digits, " Point=", DoubleToString(g_point, 5),
         " Pip=", DoubleToString(g_pip, 5), " TickSize=", DoubleToString(tickSize, 5),
         " TickValue=", DoubleToString(tickValue, 2));
   LogSymbolCheck();

   UpdateDailyReset();

   if(Enable_RSIEngulfTouch)
   {
      ENUM_TIMEFRAMES tfUsed = (SignalTF == PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : SignalTF;
      g_rsiEngulfTouchReady = g_rsiEngulfTouch.Init(g_symbol, tfUsed);
      if(!g_rsiEngulfTouchReady)
         Print("[RSIEngulfTouch] disabled: init failed.");
   }
   else
   {
      g_rsiEngulfTouchReady = false;
   }

   License_Init();
   License_Refresh(true);
   EventSetTimer(60);

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   License_Deinit();
   g_rsiEngulfTouch.Deinit();
   g_rsiEngulfTouchReady = false;
   ReleaseIndicatorsCache();
}

void OnTimer()
{
   License_OnTimer();
}

void OnTick()
{
   if(g_symbol == "")
      return;

   if(InpUseSMCZ3C) SMCZ3C_Update();

   if(Enable_RSIEngulfTouch && g_rsiEngulfTouchReady)
      g_rsiEngulfTouch.OnTick();

   UpdateDailyReset();
   PatternEngine_Update();

   if(IsNewBar(PERIOD_H1, g_lastH1Bar))
      UpdateSpreadEMA();

   RegimeState regime = UpdateRegime();

   MarketContext ctx;
   BuildContext(ctx);

   if(HasPosition())
   {
      if(!CanManageOpenTrades())
         return;

      double entryPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double slPrice = PositionGetDouble(POSITION_SL);
      double riskR = MathAbs(entryPrice - slPrice);
      if(riskR <= 0.0)
         riskR = GVGetDouble("origRisk", 0.0);
      ManagePosition(riskR);
      int dailyScore = DailyScore(regime);
      bool pyramidAllowed = false;
      int maxTrades = 0;
      double dailyRiskMult = 0.0;
      DailyTradeAllowed(dailyScore, maxTrades, dailyRiskMult, pyramidAllowed);
      TryPyramiding(riskR, pyramidAllowed, regime);
      return;
   }

   int skipMask = SKIP_NONE;
   if(LossBlocksActive())
   {
      skipMask |= SKIP_LOSS_BLOCK;
      double bosLevel = 0.0;
      int bosAgeBars = BOSAgeBars(bosLevel);
      PrintFormat("[SKIP] %s", ExplainSkipMask(skipMask));
      LogCSV("SKIP", DIR_NONE, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0, skipMask, 0,
             0, 0, bosLevel, bosAgeBars, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
             0, 0.0, 0.0, 0.0, 0.0, 0.0, 0);
      return;
   }
   if(!HardGuardsOk(skipMask, ctx))
   {
      double bosLevel = 0.0;
      int bosAgeBars = BOSAgeBars(bosLevel);
      PrintFormat("[SKIP] %s", ExplainSkipMask(skipMask));
      LogCSV("SKIP", DIR_NONE, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0, skipMask, 0,
             0, 0, bosLevel, bosAgeBars, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
             0, 0.0, 0.0, 0.0, 0.0, 0.0, 0);
      return;
   }

   int dayTrades = ctx.dayTrades;
   int dailyScore = DailyScore(regime);
   int maxTrades = 0;
   double dailyRiskMult = 0.0;
   bool pyramidAllowed = false;
   if(cfg_InpUseDailyTradeControl && !DailyTradeAllowed(dailyScore, maxTrades, dailyRiskMult, pyramidAllowed))
   {
      skipMask |= SKIP_DAILY_SCORE;
      double bosLevel = 0.0;
      int bosAgeBars = BOSAgeBars(bosLevel);
      LogCSV("SKIP", DIR_NONE, 0.0, 0.0, 0.0, 0.0, 0.0, dailyScore, 0, 0, 0, skipMask, 0,
             0, 0, bosLevel, bosAgeBars, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
             0, 0.0, 0.0, 0.0, 0.0, 0.0, 0);
      return;
   }

   int allowedTrades = cfg_InpHardMaxTradesPerDay;
   if(cfg_InpUseDailyTradeControl)
      allowedTrades = MathMin(allowedTrades, maxTrades);
   if(dayTrades >= allowedTrades)
   {
      skipMask |= SKIP_DAILY_MAX;
      double bosLevel = 0.0;
      int bosAgeBars = BOSAgeBars(bosLevel);
      LogCSV("SKIP", DIR_NONE, 0.0, 0.0, 0.0, 0.0, 0.0, dailyScore, 0, 0, 0, skipMask, 0,
             0, 0, bosLevel, bosAgeBars, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
             0, 0.0, 0.0, 0.0, 0.0, 0.0, 0);
      return;
   }

   if(!CanOpenNewTrades())
      return;

   TradeDir dir;
   double entry = 0.0, sl = 0.0, tp = 0.0, tp1 = 0.0, riskR = 0.0;
   int setupScore = 0, timingScore = 0, totalScore = 0, entryMask = 0;
   skipMask = 0;
   double nearestKey = 0.0;
   double bosLevel = 0.0;
   int bosAgeBars = -1;
   int killzoneActive = 0;
   double pdh = 0.0, pdl = 0.0, psh = 0.0, psl = 0.0, hod = 0.0, lod = 0.0;
   int sweepDir = 0;
   double sweepLevel = 0.0;
   double displacementScore = 0.0;
   double obHigh = 0.0, obLow = 0.0, obMT = 0.0;
   int oteOk = 0;
   int sdHit = 0;
   int sdType = 0;
   double sdDistATR = 0.0;
   int sdFresh = 0;
   int candleHit = 0;
   int candleType = 0;
   int momHit = 0;
   double rsi1 = 0.0;
   double rsi2 = 0.0;

   if(!CalculateEntry(dir, entry, sl, tp, tp1, riskR, setupScore, timingScore, totalScore, skipMask, entryMask,
                      nearestKey, bosLevel, bosAgeBars, killzoneActive, pdh, pdl, psh, psl, hod, lod,
                      sweepDir, sweepLevel, displacementScore, obHigh, obLow, obMT, oteOk,
                      sdHit, sdType, sdDistATR, sdFresh, candleHit, candleType, momHit, rsi1, rsi2))
   {
      PrintFormat("[NOENTRY] skip=%s entry=%s", ExplainSkipMask(skipMask), ExplainEntryMask(entryMask));
      LogCSVEx("NOENTRY", DIR_NONE, 0.0, 0.0, 0.0, tp1, 0.0, dailyScore, setupScore, timingScore, totalScore, skipMask, entryMask,
               0, 0, bosLevel, bosAgeBars, nearestKey, killzoneActive, pdh, pdl, psh, psl, hod, lod,
               sweepDir, sweepLevel, displacementScore, obHigh, obLow, obMT, oteOk,
               sdHit, sdType, sdDistATR, sdFresh, candleHit, candleType, momHit, rsi1, rsi2);
      return;
   }

   int entryScore = totalScore;
   g_patternScoreDelta = 0.0;
   g_patternFinalScore = entryScore;
   if(UsePatternEngine && g_patternSignal.detected)
   {
      double prior = (UsePatternPriors ? g_patternPriorScore : 50.0);
      double qualityPts = InpPatternQualityWeight * g_patternSignal.quality;
      g_patternScoreDelta = InpPatternWeight * (prior - 50.0) / 10.0 + qualityPts;
      if(g_patternSignal.direction != 0 && g_patternSignal.direction != (int)dir)
         g_patternScoreDelta -= 6.0;
      g_patternFinalScore = entryScore + g_patternScoreDelta;
      entryScore = (int)MathRound(g_patternFinalScore);
   }

   if(entryScore < InpEntryThreshold)
      return;

   int rpScore = 0;
   string rpReason = "";
   string rpZoneKey = "";
   if(!RP_ModelGate(dir, entry, sl, tp, rpScore, rpReason, rpZoneKey))
   {
      Print("[RPModel] SKIP dir=", (int)dir, " score=", rpScore, " reason=", rpReason);
      return;
   }

   if(UsePatternEngine && g_patternSignal.detected && g_patternSignal.direction == (int)dir)
   {
      double atrPat = ATR(PERIOD_M15, 1);
      double slBuf = atrPat * InpPatternSL_ATR_Buffer + PriceFromPoints(InpInvalidationBufferPoints);
      if(dir == DIR_LONG)
      {
         double patSL = NormalizePrice(g_patternSignal.invalidation_level - slBuf);
         if(patSL > 0.0) sl = (sl > 0.0 ? MathMax(sl, patSL) : patSL);
         if(g_patternSignal.target_level > entry) tp1 = NormalizePrice(g_patternSignal.target_level);
      }
      else if(dir == DIR_SHORT)
      {
         double patSL = NormalizePrice(g_patternSignal.invalidation_level + slBuf);
         if(patSL > 0.0) sl = (sl > 0.0 ? MathMin(sl, patSL) : patSL);
         if(g_patternSignal.target_level < entry) tp1 = NormalizePrice(g_patternSignal.target_level);
      }
   }

   g_instTotalScore = 0;
   g_instRiskMult = 1.0;
   g_instPatternScore = 0;
   g_instPattern = PAT_DOJI;
   if(UseInstitutionalScore)
   {
      ComputeInstitutionalAdapter(candleType, (dir == DIR_LONG), entryMask, killzoneActive,
                                  g_instTotalScore, g_instRiskMult, g_instPatternScore, g_instPattern);
      if(g_instTotalScore < InstitutionalMinScore || g_instRiskMult <= 0.0)
      {
         if(LogInstitutional)
            Print("[INST] SKIP score=", g_instTotalScore, " riskMult=", DoubleToString(g_instRiskMult, 2),
                  " pattern=", GetPatternName(g_instPattern), " pScore=", g_instPatternScore);
         return;
      }
   }

   string irTier = "NA";
   string irReason = "";
   double lots = 0.0;
   double scoreRiskScale = Prob_ToRiskScale(entryScore);
   if(!IR_ComputeLots(dir, entry, sl, entryScore, lots, irTier, irReason))
   {
      Print("[IREngine] SKIP reason=", irReason, " entryScore=", entryScore);
      return;
   }

   lots = NormalizeVolumeByStep(lots * scoreRiskScale);

   if(!StopsOk(dir, entry, sl, tp))
   {
      skipMask |= SKIP_STOPS;
      LogCSVEx("SKIP", DIR_NONE, entry, sl, tp, tp1, 0.0, dailyScore, setupScore, timingScore, totalScore, skipMask, entryMask,
               0, 0, bosLevel, bosAgeBars, nearestKey, killzoneActive, pdh, pdl, psh, psl, hod, lod,
               sweepDir, sweepLevel, displacementScore, obHigh, obLow, obMT, oteOk,
               sdHit, sdType, sdDistATR, sdFresh, candleHit, candleType, momHit, rsi1, rsi2);
      return;
   }

   int retcode = 0;
   int lasterr = 0;
   bool sent = TryOpenByDir(dir, lots, sl, tp, "ENTRY", retcode, lasterr);

   if(sent)
   {
      GVSetInt("dayTrades", dayTrades + 1);
      GVSetDouble("lastEntryTime", (double)iTime(g_symbol, PERIOD_M15, 0));
      GVSetDouble("lastEntryPrice", entry);
      GVSetInt("lastDir", (int)dir);
      GVSetDouble("origRisk", riskR);
      GVSetInt("tp1done", 0);
      GVSetDouble("tp1price", tp1);
      GVSetDouble("tp1FillPrice", 0.0);
      GVSetDouble("pattern_breakout_level", (UsePatternEngine && g_patternSignal.detected ? g_patternSignal.entry_level : entry));
      GVSetDouble("pattern_mfe", 0.0);
      GVSetDouble("pattern_mae", 0.0);
      GVSetInt("addCount", 0);
      GVSetDouble("lastAddPrice", entry);
      if(InpUseReactionProbabilityModel)
         RP_RegisterTrade(rpZoneKey);

      LogCSVEx("ENTRY", dir, entry, sl, tp, tp1, lots, dailyScore, setupScore, timingScore, totalScore, skipMask, entryMask,
               retcode, lasterr, bosLevel, bosAgeBars, nearestKey, killzoneActive, pdh, pdl, psh, psl, hod, lod,
               sweepDir, sweepLevel, displacementScore, obHigh, obLow, obMT, oteOk,
               sdHit, sdType, sdDistATR, sdFresh, candleHit, candleType, momHit, rsi1, rsi2);
   }
   else
   {
      LogCSVEx("ENTRY_FAIL", dir, entry, sl, tp, tp1, lots, dailyScore, setupScore, timingScore, totalScore, skipMask, entryMask,
               retcode, lasterr, bosLevel, bosAgeBars, nearestKey, killzoneActive, pdh, pdl, psh, psl, hod, lod,
               sweepDir, sweepLevel, displacementScore, obHigh, obLow, obMT, oteOk,
               sdHit, sdType, sdDistATR, sdFresh, candleHit, candleType, momHit, rsi1, rsi2);
   }
}

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD)
      return;
   if(trans.symbol != g_symbol)
      return;
   if(trans.magic != cfg_InpMagic)
      return;

   double profit = trans.profit + trans.commission + trans.swap;
   if(trans.entry == DEAL_ENTRY_OUT)
   {
      int lossStreak = GVGetInt("lossStreak", 0);
      if(profit < 0.0)
         lossStreak++;
      else
         lossStreak = 0;
      GVSetInt("lossStreak", lossStreak);
      UpdateLossBlock(lossStreak);

      double entryPx = GVGetDouble("lastEntryPrice", 0.0);
      int lastDir = GVGetInt("lastDir", 0);
      if(entryPx > 0.0 && lastDir != 0)
         g_patternOutcomePips = ((lastDir > 0 ? (trans.price - entryPx) : (entryPx - trans.price)) / MathMax(g_pip, g_point));
      else
         g_patternOutcomePips = 0.0;
      g_patternMaxFavorPips = GVGetDouble("pattern_mfe", 0.0);
      g_patternMaxAdversePips = GVGetDouble("pattern_mae", 0.0);

      double bosLevel = 0.0;
      int bosAgeBars = BOSAgeBars(bosLevel);
      LogCSV("EXIT", DIR_NONE, trans.price, 0.0, 0.0, 0.0, trans.volume,
             DailyScore((RegimeState)GVGetInt("regime", REGIME_RANGE)), 0, 0, 0, 0, 0,
             0, 0, bosLevel, bosAgeBars, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
             0, 0.0, 0.0, 0.0, 0.0, 0.0, 0);
   }
}


/// SMC_Zones_3C BEGIN
struct SMCZone
{
   datetime t0;
   ENUM_TIMEFRAMES tf;
   bool bullish;
   double top;
   double bottom;
   int touches;
   bool mitigated;
   bool active;
   double score;
   double created_at_price;
   double expectedMitigationHours;
};

SMCZone g_smcz3cZones[];
ENUM_TIMEFRAMES g_smcz3cTFs[];
datetime g_smcz3cLastBarTimes[];
bool g_smcz3cInited = false;

string SMCZ3C_TFToString(ENUM_TIMEFRAMES tf)
{
   switch(tf)
   {
      case PERIOD_M1: return "PERIOD_M1";
      case PERIOD_M2: return "PERIOD_M2";
      case PERIOD_M3: return "PERIOD_M3";
      case PERIOD_M4: return "PERIOD_M4";
      case PERIOD_M5: return "PERIOD_M5";
      case PERIOD_M6: return "PERIOD_M6";
      case PERIOD_M10: return "PERIOD_M10";
      case PERIOD_M12: return "PERIOD_M12";
      case PERIOD_M15: return "PERIOD_M15";
      case PERIOD_M20: return "PERIOD_M20";
      case PERIOD_M30: return "PERIOD_M30";
      case PERIOD_H1: return "PERIOD_H1";
      case PERIOD_H2: return "PERIOD_H2";
      case PERIOD_H3: return "PERIOD_H3";
      case PERIOD_H4: return "PERIOD_H4";
      case PERIOD_H6: return "PERIOD_H6";
      case PERIOD_H8: return "PERIOD_H8";
      case PERIOD_H12: return "PERIOD_H12";
      case PERIOD_D1: return "PERIOD_D1";
      case PERIOD_W1: return "PERIOD_W1";
      case PERIOD_MN1: return "PERIOD_MN1";
   }
   return "PERIOD_M15";
}

ENUM_TIMEFRAMES SMCZ3C_ParseTFToken(string token)
{
   StringTrimLeft(token);
   StringTrimRight(token);
   StringToUpper(token);
   if(token == "PERIOD_CURRENT") return (ENUM_TIMEFRAMES)_Period;
   if(token == "PERIOD_M1") return PERIOD_M1;
   if(token == "PERIOD_M2") return PERIOD_M2;
   if(token == "PERIOD_M3") return PERIOD_M3;
   if(token == "PERIOD_M4") return PERIOD_M4;
   if(token == "PERIOD_M5") return PERIOD_M5;
   if(token == "PERIOD_M6") return PERIOD_M6;
   if(token == "PERIOD_M10") return PERIOD_M10;
   if(token == "PERIOD_M12") return PERIOD_M12;
   if(token == "PERIOD_M15") return PERIOD_M15;
   if(token == "PERIOD_M20") return PERIOD_M20;
   if(token == "PERIOD_M30") return PERIOD_M30;
   if(token == "PERIOD_H1") return PERIOD_H1;
   if(token == "PERIOD_H2") return PERIOD_H2;
   if(token == "PERIOD_H3") return PERIOD_H3;
   if(token == "PERIOD_H4") return PERIOD_H4;
   if(token == "PERIOD_H6") return PERIOD_H6;
   if(token == "PERIOD_H8") return PERIOD_H8;
   if(token == "PERIOD_H12") return PERIOD_H12;
   if(token == "PERIOD_D1") return PERIOD_D1;
   if(token == "PERIOD_W1") return PERIOD_W1;
   if(token == "PERIOD_MN1") return PERIOD_MN1;
   return PERIOD_CURRENT;
}

void SMCZ3C_ParseTFs()
{
   ArrayResize(g_smcz3cTFs, 0);
   ArrayResize(g_smcz3cLastBarTimes, 0);

   string parts[];
   int n = StringSplit(InpSMCTFs, ',', parts);
   for(int i = 0; i < n; i++)
   {
      ENUM_TIMEFRAMES tf = SMCZ3C_ParseTFToken(parts[i]);
      if(tf == PERIOD_CURRENT)
         tf = (ENUM_TIMEFRAMES)_Period;
      bool exists = false;
      for(int j = 0; j < ArraySize(g_smcz3cTFs); j++)
      {
         if(g_smcz3cTFs[j] == tf)
         {
            exists = true;
            break;
         }
      }
      if(!exists)
      {
         int k = ArraySize(g_smcz3cTFs);
         ArrayResize(g_smcz3cTFs, k + 1);
         ArrayResize(g_smcz3cLastBarTimes, k + 1);
         g_smcz3cTFs[k] = tf;
         g_smcz3cLastBarTimes[k] = 0;
      }
   }
   if(ArraySize(g_smcz3cTFs) == 0)
   {
      ArrayResize(g_smcz3cTFs, 1);
      ArrayResize(g_smcz3cLastBarTimes, 1);
      g_smcz3cTFs[0] = PERIOD_M15;
      g_smcz3cLastBarTimes[0] = 0;
   }
   g_smcz3cInited = true;
}

double SMCZ3C_BodyHigh(double o, double c) { return MathMax(o, c); }
double SMCZ3C_BodyLow(double o, double c) { return MathMin(o, c); }

double SMCZ3C_ComputeScore(bool bos, double dispBody, double atr, double bodyC2, int touches, bool mitigated)
{
   double score = 0.0;
   if(bos)
      score += 30.0;
   if(atr > 0.0 && dispBody >= 1.0 * atr)
      score += 20.0;
   if(atr > 0.0 && bodyC2 <= 0.5 * atr)
      score += 10.0;
   score -= (10.0 * touches);
   if(mitigated)
      score -= 20.0;
   if(score < 0.0) score = 0.0;
   if(score > 100.0) score = 100.0;
   return score;
}

bool SMCZ3C_IsPivotHigh(ENUM_TIMEFRAMES tf, int shift, int lr)
{
   int bars = iBars(g_symbol, tf);
   if(shift - lr < 1 || shift + lr >= bars)
      return false;
   double h = iHigh(g_symbol, tf, shift);
   for(int j = 1; j <= lr; j++)
   {
      if(h <= iHigh(g_symbol, tf, shift - j) || h <= iHigh(g_symbol, tf, shift + j))
         return false;
   }
   return true;
}

bool SMCZ3C_IsPivotLow(ENUM_TIMEFRAMES tf, int shift, int lr)
{
   int bars = iBars(g_symbol, tf);
   if(shift - lr < 1 || shift + lr >= bars)
      return false;
   double l = iLow(g_symbol, tf, shift);
   for(int j = 1; j <= lr; j++)
   {
      if(l >= iLow(g_symbol, tf, shift - j) || l >= iLow(g_symbol, tf, shift + j))
         return false;
   }
   return true;
}

bool FindSwingHigh(int startShift, int lookback, int leftRight, ENUM_TIMEFRAMES tf, double &outHigh)
{
   int bars = iBars(g_symbol, tf);
   int endShift = MathMin(startShift + lookback, bars - leftRight - 1);
   for(int s = startShift; s <= endShift; s++)
   {
      if(SMCZ3C_IsPivotHigh(tf, s, leftRight))
      {
         outHigh = iHigh(g_symbol, tf, s);
         return true;
      }
   }
   return false;
}

bool FindSwingLow(int startShift, int lookback, int leftRight, ENUM_TIMEFRAMES tf, double &outLow)
{
   int bars = iBars(g_symbol, tf);
   int endShift = MathMin(startShift + lookback, bars - leftRight - 1);
   for(int s = startShift; s <= endShift; s++)
   {
      if(SMCZ3C_IsPivotLow(tf, s, leftRight))
      {
         outLow = iLow(g_symbol, tf, s);
         return true;
      }
   }
   return false;
}

double SMCZ3C_DistanceToNearestEdge(const SMCZone &z, double px)
{
   if(px > z.top)
      return px - z.top;
   if(px < z.bottom)
      return z.bottom - px;
   double d1 = z.top - px;
   double d2 = px - z.bottom;
   return MathMin(d1, d2);
}

void SMCZ3C_UpdateExpectedHours(SMCZone &z)
{
   double atr = ATR(z.tf, 1);
   double tfHours = (double)PeriodSeconds(z.tf) / 3600.0;
   if(atr <= 0.0 || tfHours <= 0.0)
   {
      z.expectedMitigationHours = 0.0;
      return;
   }
   double atrPerHour = atr / tfHours;
   if(atrPerHour <= 0.0)
   {
      z.expectedMitigationHours = 0.0;
      return;
   }
   double px = SymbolInfoDouble(g_symbol, SYMBOL_BID);
   double dist = SMCZ3C_DistanceToNearestEdge(z, px);
   z.expectedMitigationHours = (dist / atrPerHour) * InpTimeFactor;
}

int SMCZ3C_FindExisting(datetime t0, ENUM_TIMEFRAMES tf, bool bullish)
{
   for(int i = 0; i < ArraySize(g_smcz3cZones); i++)
   {
      if(g_smcz3cZones[i].t0 == t0 && g_smcz3cZones[i].tf == tf && g_smcz3cZones[i].bullish == bullish)
         return i;
   }
   return -1;
}

void SMCZ3C_AddOrMergeZone(const SMCZone &zone)
{
   if(zone.score < InpMinScoreToKeep)
      return;

   double tol = InpMergeTolPoints * _Point;
   for(int i = 0; i < ArraySize(g_smcz3cZones); i++)
   {
      SMCZone &z = g_smcz3cZones[i];
      if(z.bullish != zone.bullish)
         continue;
      if(MathAbs(z.top - zone.top) < tol && MathAbs(z.bottom - zone.bottom) < tol)
      {
         bool replace = (zone.score > z.score) || (zone.t0 > z.t0);
         if(replace)
         {
            int touches = z.touches;
            bool mitigated = z.mitigated;
            bool active = z.active;
            z = zone;
            z.touches = MathMax(touches, zone.touches);
            z.mitigated = mitigated || zone.mitigated;
            z.active = active && zone.active;
         }
         return;
      }
   }

   int n = ArraySize(g_smcz3cZones);
   ArrayResize(g_smcz3cZones, n + 1);
   g_smcz3cZones[n] = zone;
}

void SMCZ3C_ScanTF(ENUM_TIMEFRAMES tf)
{
   int bars = iBars(g_symbol, tf);
   if(bars < 20)
      return;

   int maxI = MathMin(InpScanBars, bars - 3);
   double eps = InpBodyEngulfEpsPoints * _Point;

   for(int i = 1; i <= maxI; i++)
   {
      int c3 = i;
      int c2 = i + 1;
      int c1 = i + 2;

      double o1 = iOpen(g_symbol, tf, c1), c1c = iClose(g_symbol, tf, c1);
      double o2 = iOpen(g_symbol, tf, c2), c2c = iClose(g_symbol, tf, c2);
      double o3 = iOpen(g_symbol, tf, c3), c3c = iClose(g_symbol, tf, c3);
      if(o1 == 0.0 || o2 == 0.0 || o3 == 0.0)
         continue;

      double b1h = SMCZ3C_BodyHigh(o1, c1c), b1l = SMCZ3C_BodyLow(o1, c1c);
      double b2h = SMCZ3C_BodyHigh(o2, c2c), b2l = SMCZ3C_BodyLow(o2, c2c);
      double b3h = SMCZ3C_BodyHigh(o3, c3c), b3l = SMCZ3C_BodyLow(o3, c3c);

      bool engulf12 = (b1l <= b2l + eps && b1h >= b2h - eps);
      bool engulf32 = (b3l <= b2l + eps && b3h >= b2h - eps);
      if(!engulf12 || !engulf32)
         continue;

      double atr = ATR(tf, c3);
      double dispBody = MathAbs(c3c - o3);
      if(atr <= 0.0 || dispBody < InpDispATRMult * atr)
         continue;

      bool c3Bull = (c3c > o3);
      bool c3Bear = (c3c < o3);
      if(!c3Bull && !c3Bear)
         continue;

      bool bos = false;
      double swingHigh = 0.0, swingLow = 0.0;
      if(c3Bull)
      {
         if(FindSwingHigh(c3 + 1, InpSwingLookbackBars, InpPivotLR, tf, swingHigh))
            bos = (c3c > swingHigh);
      }
      else
      {
         if(FindSwingLow(c3 + 1, InpSwingLookbackBars, InpPivotLR, tf, swingLow))
            bos = (c3c < swingLow);
      }
      if(!bos)
         continue;

      SMCZone z;
      z.t0 = iTime(g_symbol, tf, c3);
      z.tf = tf;
      z.bullish = c3Bull;
      z.touches = 0;
      z.mitigated = false;
      z.active = true;
      z.created_at_price = c3c;

      if(c3Bull)
      {
         z.bottom = MathMin(iLow(g_symbol, tf, c2), iLow(g_symbol, tf, c1));
         bool c2Bear = (c2c < o2);
         bool c1Bear = (c1c < o1);
         if(c2Bear)
            z.top = SMCZ3C_BodyHigh(o2, c2c);
         else if(c1Bear)
            z.top = SMCZ3C_BodyHigh(o1, c1c);
         else
            z.top = iHigh(g_symbol, tf, c2);
      }
      else
      {
         bool c2Bull = (c2c > o2);
         bool c1Bull = (c1c > o1);
         if(c2Bull)
            z.bottom = SMCZ3C_BodyLow(o2, c2c);
         else if(c1Bull)
            z.bottom = SMCZ3C_BodyLow(o1, c1c);
         else
            z.bottom = iLow(g_symbol, tf, c2);
         z.top = MathMax(iHigh(g_symbol, tf, c2), iHigh(g_symbol, tf, c1));
      }

      if(z.top < z.bottom)
      {
         double tmp = z.top;
         z.top = z.bottom;
         z.bottom = tmp;
      }

      z.score = SMCZ3C_ComputeScore(bos, dispBody, atr, MathAbs(c2c - o2), z.touches, z.mitigated);
      SMCZ3C_UpdateExpectedHours(z);

      if(SMCZ3C_FindExisting(z.t0, z.tf, z.bullish) < 0)
         SMCZ3C_AddOrMergeZone(z);
   }
}

bool SMCZ3C_BoxOverlap(double low, double high, double bottom, double top)
{
   return (high >= bottom && low <= top);
}

void SMCZ3C_UpdateTouchesAndState(SMCZone &z)
{
   if(!z.active)
      return;

   double high1 = iHigh(g_symbol, z.tf, 1);
   double low1 = iLow(g_symbol, z.tf, 1);
   double high2 = iHigh(g_symbol, z.tf, 2);
   double low2 = iLow(g_symbol, z.tf, 2);
   double close1 = iClose(g_symbol, z.tf, 1);

   bool in1 = SMCZ3C_BoxOverlap(low1, high1, z.bottom, z.top);
   bool in2 = SMCZ3C_BoxOverlap(low2, high2, z.bottom, z.top);

   if(in1 && !in2)
      z.touches++;

   double h = z.top - z.bottom;
   if(h > 0.0)
   {
      double overlap = MathMax(0.0, MathMin(high1, z.top) - MathMax(low1, z.bottom));
      double overlapPct = (overlap / h) * 100.0;
      if(overlapPct >= InpMitigatePct)
         z.mitigated = true;
   }

   double invBuf = InpInvalidationBufferPoints * _Point;
   if(z.bullish && close1 < (z.bottom - invBuf))
      z.active = false;
   if(!z.bullish && close1 > (z.top + invBuf))
      z.active = false;
   if(z.touches >= InpMaxTouches)
      z.active = false;

   z.score = SMCZ3C_ComputeScore(true, ATR(z.tf, 1), ATR(z.tf, 1), 0.0, z.touches, z.mitigated);
   SMCZ3C_UpdateExpectedHours(z);
}

void SMCZ3C_DrawZone(const SMCZone &z)
{
   string name = "SMCZ3C_" + SMCZ3C_TFToString(z.tf) + "_" + (z.bullish ? "bull_" : "bear_") + (string)z.t0;
   color clr = z.bullish ? clrLime : clrRed;
   datetime t1 = z.t0;
   datetime t2 = TimeCurrent() + PeriodSeconds(z.tf) * 20;

   if(ObjectFind(0, name) < 0)
      ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, z.top, t2, z.bottom);

   ObjectSetInteger(0, name, OBJPROP_TIME, 0, t1);
   ObjectSetDouble(0, name, OBJPROP_PRICE, 0, z.top);
   ObjectSetInteger(0, name, OBJPROP_TIME, 1, t2);
   ObjectSetDouble(0, name, OBJPROP_PRICE, 1, z.bottom);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_FILL, true);
   ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, name, OBJPROP_BACK, false);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);

   string txt = name + "_TXT";
   if(ObjectFind(0, txt) < 0)
      ObjectCreate(0, txt, OBJ_TEXT, 0, t2, z.top);
   string cap = SMCZ3C_TFToString(z.tf) + " score=" + DoubleToString(z.score, 1) +
                " t=" + (string)z.touches + " eh=" + DoubleToString(z.expectedMitigationHours, 1);
   ObjectSetString(0, txt, OBJPROP_TEXT, cap);
   ObjectSetInteger(0, txt, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, txt, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
   ObjectMove(0, txt, 0, t2, z.top);
}

void SMCZ3C_Update()
{
   if(!g_smcz3cInited)
      SMCZ3C_ParseTFs();

   for(int i = 0; i < ArraySize(g_smcz3cTFs); i++)
   {
      ENUM_TIMEFRAMES tf = g_smcz3cTFs[i];
      datetime barT = iTime(g_symbol, tf, 0);
      if(barT <= 0)
         continue;

      if(g_smcz3cLastBarTimes[i] != barT)
      {
         g_smcz3cLastBarTimes[i] = barT;
         SMCZ3C_ScanTF(tf);
      }
   }

   for(int z = 0; z < ArraySize(g_smcz3cZones); z++)
   {
      SMCZ3C_UpdateTouchesAndState(g_smcz3cZones[z]);
      if(g_smcz3cZones[z].active && InpDrawZones && g_smcz3cZones[z].score >= InpMinScoreToKeep)
         SMCZ3C_DrawZone(g_smcz3cZones[z]);
   }
}

bool SMCZ3C_GetBestZone(bool wantBullish, double &outTop, double &outBottom, ENUM_TIMEFRAMES &outTf, double &outScore, double &outExpHours)
{
   int best = -1;
   double bestScore = -DBL_MAX;
   for(int i = 0; i < ArraySize(g_smcz3cZones); i++)
   {
      SMCZone &z = g_smcz3cZones[i];
      if(!z.active || z.mitigated || z.touches != 0)
         continue;
      if(z.bullish != wantBullish)
         continue;
      if(z.score < InpMinScoreToKeep)
         continue;
      if(z.score > bestScore)
      {
         bestScore = z.score;
         best = i;
      }
   }
   if(best < 0)
      return false;

   outTop = g_smcz3cZones[best].top;
   outBottom = g_smcz3cZones[best].bottom;
   outTf = g_smcz3cZones[best].tf;
   outScore = g_smcz3cZones[best].score;
   outExpHours = g_smcz3cZones[best].expectedMitigationHours;
   return true;
}

int SMCZ3C_GetZonesCount()
{
   return ArraySize(g_smcz3cZones);
}

bool SMCZ3C_GetZoneByIndex(int idx, SMCZone &outZone)
{
   if(idx < 0 || idx >= ArraySize(g_smcz3cZones))
      return false;
   outZone = g_smcz3cZones[idx];
   return true;
}
/// SMC_Zones_3C END


/// REACTION_PROBABILITY BEGIN
enum RPMarketBias
{
   RP_BIAS_NEUTRAL = 0,
   RP_BIAS_LONG = 1,
   RP_BIAS_SHORT = -1
};

enum ZoneType
{
   ZONE_SUPPORT = 0,
   ZONE_RESISTANCE = 1,
   ZONE_ORDERBLOCK = 2,
   ZONE_SUPPLYDEMAND = 3,
   ZONE_TRENDLINE = 4
};

enum ZoneLifeState
{
   ZONE_FRESH = 0,
   ZONE_SEMI = 1,
   ZONE_OLD = 2
};

struct Zone
{
   int type;
   double upper;
   double lower;
   datetime createdTime;
   int touchCount;
   datetime lastTouchTime;
   bool mitigated;
   bool broken;
   int ageBars;
   int state;
   ENUM_TIMEFRAMES tf;
   bool bullish;
   double score;
   string key;
};

Zone g_rpZones[];
string g_rpTradedZones[];
int g_rpTradesToday = 0;
int g_rpDayId = 0;
datetime g_rpLastTradeTs = 0;
datetime g_rpLastM15Bar = 0;

void RP_RegisterTrade(const string zoneKey)
{
   int dayId = NYDayId(TimeCurrent());
   if(g_rpDayId != dayId)
   {
      g_rpDayId = dayId;
      g_rpTradesToday = 0;
      ArrayResize(g_rpTradedZones, 0);
   }
   g_rpTradesToday++;
   g_rpLastTradeTs = TimeCurrent();
   if(InpOneTradePerZone && StringLen(zoneKey) > 0)
   {
      int n = ArraySize(g_rpTradedZones);
      ArrayResize(g_rpTradedZones, n + 1);
      g_rpTradedZones[n] = zoneKey;
   }
}

bool RP_ZoneAlreadyTraded(const string zoneKey)
{
   if(!InpOneTradePerZone || StringLen(zoneKey) == 0)
      return false;
   for(int i = 0; i < ArraySize(g_rpTradedZones); i++)
      if(g_rpTradedZones[i] == zoneKey)
         return true;
   return false;
}

RPMarketBias RP_GetHTFBias()
{
   double cH4 = iClose(g_symbol, PERIOD_H4, 1);
   double cD1 = iClose(g_symbol, PERIOD_D1, 1);
   double eH4 = EMA(PERIOD_H4, 50, 1);
   double eD1 = EMA(PERIOD_D1, 50, 1);
   if(cH4 > eH4 && cD1 > eD1)
      return RP_BIAS_LONG;
   if(cH4 < eH4 && cD1 < eD1)
      return RP_BIAS_SHORT;
   return RP_BIAS_NEUTRAL;
}

void RP_AddZone(const Zone &z)
{
   int n = ArraySize(g_rpZones);
   ArrayResize(g_rpZones, n + 1);
   g_rpZones[n] = z;
}

void RP_BuildZonesFromSMC()
{
   ArrayResize(g_rpZones, 0);
   int n = SMCZ3C_GetZonesCount();
   for(int i = 0; i < n; i++)
   {
      SMCZone sz;
      if(!SMCZ3C_GetZoneByIndex(i, sz))
         continue;
      Zone z;
      z.type = sz.bullish ? ZONE_SUPPLYDEMAND : ZONE_ORDERBLOCK;
      z.upper = sz.top;
      z.lower = sz.bottom;
      z.createdTime = sz.t0;
      z.touchCount = sz.touches;
      z.lastTouchTime = 0;
      z.mitigated = sz.mitigated;
      z.broken = !sz.active;
      z.tf = sz.tf;
      z.ageBars = (int)(iBarShift(g_symbol, sz.tf, sz.t0, false));
      z.state = (z.touchCount == 0 ? ZONE_FRESH : (z.touchCount == 1 ? ZONE_SEMI : ZONE_OLD));
      if(z.ageBars > InpZoneOldAgeBars)
         z.state = ZONE_OLD;
      z.bullish = sz.bullish;
      z.score = sz.score;
      z.key = "RPZ_" + (string)sz.tf + "_" + (sz.bullish ? "B_" : "S_") + (string)sz.t0;
      RP_AddZone(z);
   }

   ENUM_TIMEFRAMES tfs[2] = {PERIOD_H1, PERIOD_M15};
   for(int t=0;t<2;t++)
   {
      ENUM_TIMEFRAMES tf=tfs[t];
      int hiIdx=iHighest(g_symbol, tf, MODE_HIGH, 80, 1);
      int loIdx=iLowest(g_symbol, tf, MODE_LOW, 80, 1);
      if(hiIdx>0)
      {
         Zone r; r.type=ZONE_RESISTANCE; r.upper=iHigh(g_symbol,tf,hiIdx)+5*g_point; r.lower=iHigh(g_symbol,tf,hiIdx)-5*g_point;
         r.createdTime=iTime(g_symbol,tf,hiIdx); r.touchCount=0; r.lastTouchTime=0; r.mitigated=false; r.broken=false; r.ageBars=hiIdx;
         r.state=(hiIdx>InpZoneOldAgeBars?ZONE_OLD:ZONE_FRESH); r.tf=tf; r.bullish=false; r.score=60.0; r.key="RPZ_SR_H_"+(string)tf+"_"+(string)r.createdTime; RP_AddZone(r);
      }
      if(loIdx>0)
      {
         Zone s; s.type=ZONE_SUPPORT; s.upper=iLow(g_symbol,tf,loIdx)+5*g_point; s.lower=iLow(g_symbol,tf,loIdx)-5*g_point;
         s.createdTime=iTime(g_symbol,tf,loIdx); s.touchCount=0; s.lastTouchTime=0; s.mitigated=false; s.broken=false; s.ageBars=loIdx;
         s.state=(loIdx>InpZoneOldAgeBars?ZONE_OLD:ZONE_FRESH); s.tf=tf; s.bullish=true; s.score=60.0; s.key="RPZ_SR_L_"+(string)tf+"_"+(string)s.createdTime; RP_AddZone(s);
      }
   }
}

bool RP_IsNearZone(const Zone &z, double px, double atrLtf)
{
   double m = MathMax(g_point, atrLtf * InpReactionNearATRMult);
   return (px >= z.lower - m && px <= z.upper + m);
}

bool RP_RejectWick(const Zone &z, bool wantLong)
{
   double o=iOpen(g_symbol, PERIOD_M5, 1), c=iClose(g_symbol, PERIOD_M5,1), h=iHigh(g_symbol,PERIOD_M5,1), l=iLow(g_symbol,PERIOD_M5,1);
   double body=MathAbs(c-o); if(body<=0) return false;
   double upW=h-MathMax(o,c), dnW=MathMin(o,c)-l;
   if(wantLong)
      return (l <= z.upper && c > z.upper && dnW > body*1.2);
   return (h >= z.lower && c < z.lower && upW > body*1.2);
}

bool RP_EngulfOrPin(bool wantLong)
{
   double o1=iOpen(g_symbol,PERIOD_M5,1), c1=iClose(g_symbol,PERIOD_M5,1);
   double o2=iOpen(g_symbol,PERIOD_M5,2), c2=iClose(g_symbol,PERIOD_M5,2);
   double h1=iHigh(g_symbol,PERIOD_M5,1), l1=iLow(g_symbol,PERIOD_M5,1);
   bool engulf = wantLong ? (c1>o1 && c1>=o2 && o1<=c2) : (c1<o1 && c1<=o2 && o1>=c2);
   double body=MathAbs(c1-o1); if(body<=0) body=g_point;
   bool pin = wantLong ? ((MathMin(o1,c1)-l1) > body*1.5) : ((h1-MathMax(o1,c1)) > body*1.5);
   return engulf || pin;
}

bool RP_Displacement(bool wantLong)
{
   double o=iOpen(g_symbol,PERIOD_M5,1), c=iClose(g_symbol,PERIOD_M5,1);
   double atr=ATR(PERIOD_M5,1);
   if(atr<=0) return false;
   double b=MathAbs(c-o);
   if(b < InpReactionDispATRMult*atr) return false;
   return wantLong ? (c>o) : (c<o);
}

bool RP_SweepReclaim(const Zone &z, bool wantLong)
{
   int n=MathMax(1, InpSweepReclaimBars);
   double sw=InpSweepPoints*g_point;
   for(int k=1;k<=n;k++)
   {
      double h=iHigh(g_symbol,PERIOD_M5,k), l=iLow(g_symbol,PERIOD_M5,k), c=iClose(g_symbol,PERIOD_M5,k);
      if(wantLong)
      {
         if(l < z.lower - sw && c > z.lower)
            return true;
      }
      else
      {
         if(h > z.upper + sw && c < z.upper)
            return true;
      }
   }
   return false;
}

bool RP_BreakConfirmed(const Zone &z, bool wantLong)
{
   int n=MathMax(1, InpSweepReclaimBars);
   for(int k=1;k<=n;k++)
   {
      double c=iClose(g_symbol,PERIOD_M5,k);
      if(wantLong && c < z.lower)
      {
         bool reclaimed=false;
         for(int j=1;j<=n;j++) if(iClose(g_symbol,PERIOD_M5,j) > z.lower) reclaimed=true;
         if(!reclaimed) return true;
      }
      if(!wantLong && c > z.upper)
      {
         bool reclaimed=false;
         for(int j=1;j<=n;j++) if(iClose(g_symbol,PERIOD_M5,j) < z.upper) reclaimed=true;
         if(!reclaimed) return true;
      }
   }
   return false;
}

bool RP_PickBestZone(bool wantLong, Zone &outZ)
{
   double px=SymbolInfoDouble(g_symbol, SYMBOL_BID);
   double atr=ATR(PERIOD_M5,1);
   int best=-1; double bestScore=-DBL_MAX;
   for(int i=0;i<ArraySize(g_rpZones);i++)
   {
      Zone &z=g_rpZones[i];
      if(z.broken) continue;
      if(wantLong && !z.bullish) continue;
      if(!wantLong && z.bullish) continue;
      if(!RP_IsNearZone(z, px, atr)) continue;
      double freshness = (z.state==ZONE_FRESH?30:(z.state==ZONE_SEMI?20:10));
      double sc = z.score + freshness - z.touchCount*5.0;
      if(sc>bestScore){bestScore=sc;best=i;}
   }
   if(best<0) return false;
   outZ=g_rpZones[best];
   return true;
}

bool RP_ModelGate(TradeDir dir, double entry, double &sl, double &tp, int &scoreOut, string &reasonOut, string &zoneKeyOut)
{
   scoreOut = 0;
   reasonOut = "";
   zoneKeyOut = "";
   if(!InpUseReactionProbabilityModel)
   {
      scoreOut = 100;
      return true;
   }

   int dayId = NYDayId(TimeCurrent());
   if(g_rpDayId != dayId)
   {
      g_rpDayId = dayId;
      g_rpTradesToday = 0;
      ArrayResize(g_rpTradedZones, 0);
   }

   bool wantLong = (dir == DIR_LONG);
   RPMarketBias bias = RP_GetHTFBias();
   int context = 0;
   if((wantLong && bias==RP_BIAS_LONG) || (!wantLong && bias==RP_BIAS_SHORT)) context = 30;
   else if(bias == RP_BIAS_NEUTRAL) context = 15;
   else context = 0;

   if(InpNoTradeAgainstHTF && context == 0)
   {
      reasonOut = "against_htf";
      return false;
   }

   if(g_rpTradesToday >= InpMaxTradesPerDay)
   {
      reasonOut = "max_trades_day";
      return false;
   }

   if((TimeCurrent() - g_rpLastTradeTs) < InpCooldownMinutes * 60)
   {
      reasonOut = "cooldown";
      return false;
   }

   int lossStreak = GVGetInt("lossStreak", 0);
   if(lossStreak >= InpMaxLossStreak)
   {
      reasonOut = "loss_streak";
      return false;
   }

   if(g_rpLastM15Bar != iTime(g_symbol, PERIOD_M15, 0))
   {
      g_rpLastM15Bar = iTime(g_symbol, PERIOD_M15, 0);
      RP_BuildZonesFromSMC();
   }

   Zone z;
   if(!RP_PickBestZone(wantLong, z))
   {
      reasonOut = "no_zone";
      return false;
   }

   zoneKeyOut = z.key;
   if(RP_ZoneAlreadyTraded(zoneKeyOut))
   {
      reasonOut = "zone_already_traded";
      return false;
   }

   int zoneQuality = (int)MathRound(MathMax(0.0, MathMin(30.0, z.score * 0.3)));

   bool tWick = RP_RejectWick(z, wantLong);
   bool tEngulf = RP_EngulfOrPin(wantLong);
   bool tDisp = RP_Displacement(wantLong);
   bool tSweep = RP_SweepReclaim(z, wantLong);
   bool breakConfirmed = RP_BreakConfirmed(z, wantLong);

   if(breakConfirmed)
   {
      reasonOut = "zone_break_confirmed";
      return false;
   }

   int trigCount = (tWick?1:0) + (tEngulf?1:0) + (tDisp?1:0) + (tSweep?1:0);
   if(trigCount <= 0)
   {
      reasonOut = "no_reaction_trigger";
      return false;
   }

   int trigger = MathMin(30, trigCount * 8 + (tSweep ? 6 : 0));
   int riskFilters = 10;
   if(lossStreak > 0)
      riskFilters = MathMax(0, riskFilters - lossStreak * 2);

   int score = context + zoneQuality + trigger + riskFilters;
   if(score > 100) score = 100;
   if(score < 0) score = 0;
   scoreOut = score;

   bool gate = false;
   if(score >= 70)
      gate = true;
   else if(score >= 60)
      gate = (g_rpTradesToday < InpMaxTradesPerDay && (TimeCurrent() - g_rpLastTradeTs) >= InpCooldownMinutes * 60);

   if(sl <= 0.0)
   {
      double atr = ATR(PERIOD_M15, 1);
      if(atr > 0.0)
      {
         double buf = atr * InpRiskATRBufferMult;
         if(wantLong)
            sl = MathMin(sl <= 0.0 ? DBL_MAX : sl, z.lower - buf);
         else
            sl = MathMax(sl <= 0.0 ? -DBL_MAX : sl, z.upper + buf);
         sl = NormalizePrice(sl);
      }
   }

   if(sl <= 0.0)
   {
      reasonOut = "risk_safety_no_sl";
      return false;
   }

   Print("[RPModel] bias=", (int)bias,
         " zoneState=", z.state,
         " trigW=", (int)tWick,
         " trigE=", (int)tEngulf,
         " trigD=", (int)tDisp,
         " trigS=", (int)tSweep,
         " score=", score,
         " gate=", (gate ? "ALLOW" : "SKIP"),
         " zone=", z.key);

   if(!gate)
   {
      reasonOut = "score_gate";
      return false;
   }

   return true;
}
/// REACTION_PROBABILITY END


/// INSTITUTIONAL_RISK_ENGINE BEGIN
void IR_ResetTelemetry()
{
   g_irEntryScore = 0;
   g_irTier = "NA";
   g_irRiskBasePct = RiskInputToPercent(InpRiskBasePct);
   g_irScoreMult = 0.0;
   g_irRegimeMult = 0.0;
   g_irFearMult = 0.0;
   g_irFinalRiskPct = 0.0;
   g_irRiskMoney = 0.0;
   g_irStopDistancePoints = 0.0;
   g_irLots = 0.0;
   g_irSpreadPoints = 0.0;
   g_irAtrRatio = 0.0;
   g_irLossStreak = GVGetInt("lossStreak", 0);
   g_irDailyDD = 0.0;
}

double IR_GetScoreMultiplier(int entryScore, string &tierOut)
{
   tierOut = "<70";
   if(entryScore >= 90)
   {
      tierOut = ">=90";
      return MathMin(1.25, InpMaxRiskMultiplier);
   }
   if(entryScore >= 85)
   {
      tierOut = "85-89";
      return MathMin(1.00, InpMaxRiskMultiplier);
   }
   if(entryScore >= 80)
   {
      tierOut = "80-84";
      return MathMin(0.75, InpMaxRiskMultiplier);
   }
   if(entryScore >= 75)
   {
      tierOut = "75-79";
      return MathMin(0.50, InpMaxRiskMultiplier);
   }
   if(entryScore >= 70)
   {
      tierOut = "70-74";
      return MathMin(0.25, InpMaxRiskMultiplier);
   }
   return 0.0;
}

double IR_GetAtrRatio()
{
   double atrNow = ATR(PERIOD_M15, 1);
   if(atrNow <= 0.0)
      return 1.0;
   double sum = 0.0;
   int n = MathMax(1, InpAtrMaPeriod);
   int used = 0;
   for(int i = 1; i <= n; i++)
   {
      double a = ATR(PERIOD_M15, i);
      if(a > 0.0)
      {
         sum += a;
         used++;
      }
   }
   if(used <= 0)
      return 1.0;
   double atrMa = sum / used;
   if(atrMa <= 0.0)
      return 1.0;
   return atrNow / atrMa;
}

double IR_GetRegimeMultiplier(double spreadPoints, double atrRatio, bool &blockOut)
{
   blockOut = false;
   if(spreadPoints > cfg_InpMaxSpreadPoints)
   {
      blockOut = true;
      return 0.0;
   }
   double mult = 1.0;
   if(atrRatio > InpAtrSpikeRatio)
      mult *= 0.5;
   if(InpUseSessionRiskMultiplier && !SessionOk())
      mult *= InpSessionRiskMultiplier;
   return mult;
}

double IR_GetDailyDDPct()
{
   double startEquity = GVGetDouble("dayEquityStart", AccountInfoDouble(ACCOUNT_EQUITY));
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(startEquity <= 0.0)
      return 0.0;
   double dd = (startEquity - equity) / startEquity * 100.0;
   if(dd < 0.0)
      dd = 0.0;
   return dd;
}

double IR_GetFearMultiplier(int lossStreak, double dailyDrawdownPct, bool &blockOut)
{
   blockOut = false;
   if(dailyDrawdownPct >= InpDailyDDHard)
   {
      blockOut = true;
      return 0.0;
   }
   double mult = 1.0;
   if(lossStreak >= 3)
      mult *= 0.25;
   else if(lossStreak >= 2)
      mult *= 0.5;
   if(dailyDrawdownPct >= InpDailyDDSoft)
      mult *= 0.5;
   return mult;
}

double RiskInputToPercent(double v)
{
   // Backward compatible: values <= 1.0 are treated as fraction (0.005 => 0.5%).
   if(v <= 0.0)
      return 0.0;
   if(v <= 1.0)
      return v * 100.0;
   return v;
}

double IR_ClampRiskPct(double riskPct)
{
   double minPct = RiskInputToPercent(InpRiskMinPct);
   double maxPct = RiskInputToPercent(InpRiskMaxPct);
   double lo = MathMin(minPct, maxPct);
   double hi = MathMax(minPct, maxPct);
   return MathMax(lo, MathMin(hi, riskPct));
}

double IR_CalcLotsFromRiskPct(double entryPrice, double stopPrice, double riskPct, double &riskMoneyOut, double &stopDistancePointsOut)
{
   riskMoneyOut = 0.0;
   stopDistancePointsOut = 0.0;
   if(entryPrice <= 0.0 || stopPrice <= 0.0 || riskPct <= 0.0)
      return 0.0;

   double stopDistPrice = MathAbs(entryPrice - stopPrice);
   if(stopDistPrice <= 0.0 || g_point <= 0.0)
      return 0.0;

   stopDistancePointsOut = stopDistPrice / g_point;
   double tickValue = TickValue();
   double tickSize = TickSize();
   if(tickValue <= 0.0 || tickSize <= 0.0)
      return 0.0;

   double moneyPerPointPerLot = (tickValue / tickSize) * g_point;
   if(moneyPerPointPerLot <= 0.0)
      return 0.0;

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   riskMoneyOut = equity * (riskPct / 100.0);
   if(riskMoneyOut <= 0.0)
      return 0.0;

   double lots = riskMoneyOut / (stopDistancePointsOut * moneyPerPointPerLot);
   return NormalizeVolumeByStep(lots);
}

bool IR_ComputeLots(TradeDir dir, double entryPrice, double &stopPrice, int entryScore, double &lotsOut, string &tierOut, string &reasonOut)
{
   lotsOut = 0.0;
   reasonOut = "";
   IR_ResetTelemetry();
   g_irEntryScore = entryScore;
   g_irSpreadPoints = SpreadPoints();
   g_irAtrRatio = IR_GetAtrRatio();
   g_irLossStreak = GVGetInt("lossStreak", 0);
   g_irDailyDD = IR_GetDailyDDPct();

   if(stopPrice <= 0.0)
   {
      double cat = InpCatastrophicSL_Points * g_point;
      stopPrice = (dir == DIR_LONG) ? (entryPrice - cat) : (entryPrice + cat);
      stopPrice = NormalizePrice(stopPrice);
   }

   g_irScoreMult = IR_GetScoreMultiplier(entryScore, tierOut);
   g_irTier = tierOut;
   if(g_irScoreMult <= 0.0)
   {
      reasonOut = "score_tier_zero";
      return false;
   }

   bool regimeBlock = false;
   g_irRegimeMult = IR_GetRegimeMultiplier(g_irSpreadPoints, g_irAtrRatio, regimeBlock);
   if(regimeBlock || g_irRegimeMult <= 0.0)
   {
      reasonOut = "regime_block";
      return false;
   }

   bool fearBlock = false;
   g_irFearMult = IR_GetFearMultiplier(g_irLossStreak, g_irDailyDD, fearBlock);
   if(fearBlock || g_irFearMult <= 0.0)
   {
      reasonOut = "fear_block";
      return false;
   }

   double riskPctRaw = RiskInputToPercent(InpRiskBasePct) * g_irScoreMult * g_irRegimeMult * g_irFearMult;
   if(UseInstitutionalScore)
      riskPctRaw *= MathMax(0.0, g_instRiskMult);
   g_irRiskBasePct = RiskInputToPercent(InpRiskBasePct);
   g_irFinalRiskPct = IR_ClampRiskPct(riskPctRaw);

   lotsOut = IR_CalcLotsFromRiskPct(entryPrice, stopPrice, g_irFinalRiskPct, g_irRiskMoney, g_irStopDistancePoints);
   g_irLots = lotsOut;

   Print("[IREngine] EntryScore=", entryScore,
         " tier=", g_irTier,
         " riskBasePct=", DoubleToString(g_irRiskBasePct, 5),
         " scoreMult=", DoubleToString(g_irScoreMult, 3),
         " regimeMult=", DoubleToString(g_irRegimeMult, 3),
         " fearMult=", DoubleToString(g_irFearMult, 3),
         " finalRiskPct=", DoubleToString(g_irFinalRiskPct, 5),
         " riskMoney=", DoubleToString(g_irRiskMoney, 2),
         " stopDistancePoints=", DoubleToString(g_irStopDistancePoints, 1),
         " lots=", DoubleToString(g_irLots, 2),
         " spreadPoints=", DoubleToString(g_irSpreadPoints, 1),
         " atrRatio=", DoubleToString(g_irAtrRatio, 2),
         " lossStreak=", g_irLossStreak,
         " dailyDD=", DoubleToString(g_irDailyDD, 2));

   if(lotsOut <= 0.0)
   {
      reasonOut = "lots_zero";
      return false;
   }

   return true;
}
/// INSTITUTIONAL_RISK_ENGINE END


/// INSTITUTIONAL_PATTERN_ADAPTER BEGIN
EPattern50 MapDetectorToEPattern50(int detectorIdOrEnum, bool isBullish)
{
   // Default adapter for common detector IDs. Keep existing detector untouched.
   switch(detectorIdOrEnum)
   {
      case 1: return isBullish ? PAT_BULLISH_ENGULFING : PAT_BEARISH_ENGULFING; // Engulfing
      case 2: return PAT_HAMMER; // Hammer
      case 3: return PAT_SHOOTING_STAR; // ShootingStar
      case 4: return PAT_DOJI; // Doji
      case 5: return PAT_MORNING_STAR; // MorningStar
      case 6: return PAT_EVENING_STAR; // EveningStar
      case 7: return PAT_THREE_WHITE_SOLDIERS; // ThreeSoldiers
      case 8: return PAT_THREE_BLACK_CROWS; // ThreeCrows
   }
   return PAT_DOJI;
}

void ComputeInstitutionalAdapter(int detectorIdOrEnum, bool isBullish, int entryMask, int killzoneActive,
                                 int &outTotalScore, double &outRiskMult, int &outPatternScore, EPattern50 &outPattern)
{
   outPattern = MapDetectorToEPattern50(detectorIdOrEnum, isBullish);
   outPatternScore = GetPatternScore(outPattern);

   InstFeatures f;
   ZeroMemory(f);

   double spreadPts = SpreadPoints();
   f.spreadOK = (spreadPts <= MaxSpreadPoints) || (spreadPts <= cfg_InpMaxSpreadPoints);
   f.atrOK = !LowVolBlocked();
   f.breakoutRetest = ((entryMask & ENTRY_BOS_RETEST) != 0);

   TradeDir bias = BiasH1();
   f.htfTrendAligned = (isBullish && bias == DIR_LONG) || (!isBullish && bias == DIR_SHORT);
   f.bosOrMss = ((entryMask & ENTRY_MSS) != 0) || ((entryMask & ENTRY_BOS_CLOSE) != 0) || ((entryMask & ENTRY_BOS_RETEST) != 0);
   f.liquiditySweep = ((entryMask & ENTRY_SWEEP) != 0);
   f.displacement = ((entryMask & ENTRY_DISPLACEMENT) != 0);
   f.poiTouched = ((entryMask & ENTRY_OB_RTO) != 0) || ((entryMask & ENTRY_SD) != 0) || ((entryMask & ENTRY_SR) != 0);
   f.sessionNY = (killzoneActive == 1); // TODO: connect NY-specific session module if available.
   f.volumeSpike = false; // TODO: connect volume spike module.
   f.premiumDiscountOK = ((entryMask & ENTRY_PDARRAY) != 0); // TODO: connect explicit PD premium/discount gate.
   f.avoidHighLow = false; // TODO: connect avoid day high/low sweep module.

   InstWeights w = GetXauScalpPresetWeights();
   outTotalScore = ComputeInstitutionalScore(outPatternScore, f, w);
   outRiskMult = ScoreToRiskMultiplier(outTotalScore);

   if(LogInstitutional && outRiskMult > 0.0)
   {
      Print("[INST] pat=", GetPatternName(outPattern),
            " pScore=", outPatternScore,
            " flags=", (int)f.htfTrendAligned, "|", (int)f.bosOrMss, "|", (int)f.liquiditySweep, "|", (int)f.displacement,
            "|", (int)f.poiTouched, "|", (int)f.breakoutRetest, "|", (int)f.sessionNY, "|", (int)f.volumeSpike,
            "|", (int)f.premiumDiscountOK, "|", (int)f.avoidHighLow, "|", (int)f.spreadOK, "|", (int)f.atrOK,
            " total=", outTotalScore,
            " riskMult=", DoubleToString(outRiskMult, 2),
            " spread=", DoubleToString(spreadPts, 1),
            " atrOK=", (int)f.atrOK);
   }
}
/// INSTITUTIONAL_PATTERN_ADAPTER END
