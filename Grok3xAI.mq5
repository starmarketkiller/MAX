//+------------------------------------------------------------------+
//|                                     XAUUSD Killer XM (MT5)       |
//|   Trend-follow + SMC light - production-safe single file EA      |
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

input string InpSymbolOverride = "";
input long   InpMagic = 3011;
input double InpPipPrice = 0.10; // if 0 -> auto Point*10
input int    InpMaxSpreadPoints = 35;
input int    InpMaxSlippagePoints = 35;
input int    InpMaxRetries = 2;
input int    InpRetryDelayMs = 350;

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
input int    InpOBLookback = 10;
input int    InpOBMaxAgeBars = 12;

input ENUM_TIMEFRAMES InpOTE_HTF = PERIOD_H1;
input int    InpOTE_SwingLookback = 48;
input double InpOTE_Min = 0.62;
input double InpOTE_Max = 0.79;
input double InpMinPDArrayDistance = 0.80;

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

string g_symbol = "";
int g_digits = 2;
double g_point = 0.01;
double g_pip = 0.10;
datetime g_lastM15Bar = 0;
datetime g_lastH1Bar = 0;
double g_spreadEma = 0.0;

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
   ENTRY_SR = 1 << 21
};

string GVName(const string key)
{
   return "XK_" + key + "_" + g_symbol + "_" + (string)InpMagic;
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
   if(StringLen(InpSymbolOverride) > 0)
      return InpSymbolOverride;
   return _Symbol;
}

double PipPrice()
{
   if(InpPipPrice > 0.0)
      return InpPipPrice;
   return g_pip;
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

int GetServerUtcOffsetSeconds()
{
   return (int)(TimeTradeServer() - TimeGMT());
}

datetime ToNYTime(datetime serverTime)
{
   int serverOffset = GetServerUtcOffsetSeconds();
   int nyOffset = InpUseManualNYOffset ? (InpNYOffsetHours * 3600) : (-5 * 3600);
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
   if(!InpUseICTTime)
      return false;
   int minNY = MinutesOfDayNY(TimeCurrent());
   if(InpUseKillzoneAsia && minNY >= 20 * 60 && minNY < 22 * 60)
      isAsia = true;
   if(InpUseKillzoneLondon && minNY >= 2 * 60 && minNY < 5 * 60)
      isLondon = true;
   if(InpUseKillzoneNY && minNY >= 7 * 60 && minNY < 9 * 60)
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
   double alpha = 2.0 / (InpSpreadAvgBarsH1 + 1.0);
   if(g_spreadEma <= 0.0)
      g_spreadEma = spread;
   else
      g_spreadEma = alpha * spread + (1.0 - alpha) * g_spreadEma;
}

bool SpreadMultipleBlocked()
{
   if(!InpUseSpreadMultiple)
      return false;

   double spread = SpreadPoints();
   if(g_spreadEma <= 0.0)
      return false;

   if(spread > g_spreadEma * InpSpreadMultiple)
   {
      datetime until = TimeCurrent() + InpSpreadMultipleBlockMin * 60;
      GVSetDouble("spreadBlockUntil", (double)until);
   }

   datetime blockUntil = (datetime)GVGetDouble("spreadBlockUntil", 0.0);
   return (blockUntil > TimeCurrent());
}

bool SpreadInstabilityBlocked()
{
   if(!InpUseSpreadInstability || g_spreadEma <= 0.0)
      return false;

   double spread = SpreadPoints();
   if(spread > g_spreadEma * InpSpreadSpikeFactor)
   {
      datetime until = TimeCurrent() + InpSpreadSpikeBlockMin * 60;
      GVSetDouble("spreadSpikeUntil", (double)until);
   }

   datetime blockUntil = (datetime)GVGetDouble("spreadSpikeUntil", 0.0);
   return (blockUntil > TimeCurrent());
}

bool SessionAllowed()
{
   if(!InpUseSessionFilter)
      return true;
   int hour = TimeHour(TimeCurrent());
   if(InpStartHour <= InpEndHour)
      return (hour >= InpStartHour && hour <= InpEndHour);
   return (hour >= InpStartHour || hour <= InpEndHour);
}

bool RolloverBlocked()
{
   if(!InpUseRolloverBlock)
      return false;
   return TimeInRange(InpRolloverStart, InpRolloverEnd);
}

double ATR(ENUM_TIMEFRAMES tf, int shift)
{
   return iATR(g_symbol, tf, InpATRPeriod, shift);
}

double ADX(ENUM_TIMEFRAMES tf, int shift)
{
   return iADX(g_symbol, tf, InpADXPeriod, PRICE_CLOSE, MODE_MAIN, shift);
}

double RSI(ENUM_TIMEFRAMES tf, int shift)
{
   return iRSI(g_symbol, tf, InpRSIPeriod, PRICE_CLOSE, shift);
}

double EMA(ENUM_TIMEFRAMES tf, int period, int shift)
{
   return iMA(g_symbol, tf, period, 0, MODE_EMA, PRICE_CLOSE, shift);
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
   if(!InpUseLowVolFilter)
      return false;

   double vol = (double)iVolume(g_symbol, InpVolTF, 0);
   double avg = VolumeMA(InpVolTF, InpVolMAPeriod, 1);
   if(avg <= 0.0)
      return false;
   return vol < avg * InpLowVolFactor;
}

TradeDir BiasH1()
{
   double emaFast = EMA(PERIOD_H1, InpEMA_Fast, 1);
   double emaSlow = EMA(PERIOD_H1, InpEMA_Slow, 1);
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
      if(confirmBars >= InpRegimeConfirmBarsH1)
      {
         current = next;
         GVSetInt("regime", (int)current);
         GVSetInt("regimeConfirm", 0);
         GVSetInt("regimeLock", InpRegimeLockBarsH1);
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
   double high = iHigh(g_symbol, PERIOD_M15, index);
   for(int j = 1; j <= InpPivotLen; j++)
   {
      if(high <= iHigh(g_symbol, PERIOD_M15, index - j) || high <= iHigh(g_symbol, PERIOD_M15, index + j))
         return false;
   }
   return true;
}

bool IsPivotLow(int index)
{
   double low = iLow(g_symbol, PERIOD_M15, index);
   for(int j = 1; j <= InpPivotLen; j++)
   {
      if(low >= iLow(g_symbol, PERIOD_M15, index - j) || low >= iLow(g_symbol, PERIOD_M15, index + j))
         return false;
   }
   return true;
}

bool IsConfirmedPivotHigh(int index)
{
   if(!IsPivotHigh(index))
      return false;
   for(int j = 1; j <= InpPivotConfirmBars; j++)
   {
      if(iHigh(g_symbol, PERIOD_M15, index - j) >= iHigh(g_symbol, PERIOD_M15, index))
         return false;
   }
   return true;
}

bool IsConfirmedPivotLow(int index)
{
   if(!IsPivotLow(index))
      return false;
   for(int j = 1; j <= InpPivotConfirmBars; j++)
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

int NYDayId(datetime serverTime)
{
   MqlDateTime dt;
   TimeToStruct(ToNYTime(serverTime), dt);
   return dt.year * 10000 + dt.mon * 100 + dt.day;
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

bool GetSessionHighLowNY(int startMin, int endMin, int dayOffset, double &high, double &low)
{
   high = -DBL_MAX;
   low = DBL_MAX;
   int bars = iBars(g_symbol, PERIOD_M15);
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
   double tol = MathMax(atr * InpEqToleranceATR, InpEqToleranceMinPoints * g_point);
   int count = 0;
   level = 0.0;
   for(int i = 2; i < InpEqScanBars; i++)
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
      if(count >= InpEqClusterMin)
         return true;
   }
   return false;
}

bool FindEqualLowCluster(double &level)
{
   double atr = ATR(PERIOD_M15, 1);
   double tol = MathMax(atr * InpEqToleranceATR, InpEqToleranceMinPoints * g_point);
   int count = 0;
   level = 0.0;
   for(int i = 2; i < InpEqScanBars; i++)
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
      if(count >= InpEqClusterMin)
         return true;
   }
   return false;
}

bool DetectLiquiditySweep(TradeDir &sweepDir, double &sweepLevel)
{
   sweepDir = DIR_NONE;
   sweepLevel = 0.0;
   double eqHigh = 0.0;
   double eqLow = 0.0;
   bool hasHigh = FindEqualHighCluster(eqHigh);
   bool hasLow = FindEqualLowCluster(eqLow);
   double high1 = iHigh(g_symbol, PERIOD_M15, 1);
   double low1 = iLow(g_symbol, PERIOD_M15, 1);
   double close1 = iClose(g_symbol, PERIOD_M15, 1);
   double atr = ATR(PERIOD_M15, 1);
   double tol = MathMax(atr * InpEqToleranceATR, InpEqToleranceMinPoints * g_point);
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
   double high1 = iHigh(g_symbol, PERIOD_M15, 1);
   double low1 = iLow(g_symbol, PERIOD_M15, 1);
   double open1 = iOpen(g_symbol, PERIOD_M15, 1);
   double close1 = iClose(g_symbol, PERIOD_M15, 1);
   double range = high1 - low1;
   double body = MathAbs(close1 - open1);
   double atr = ATR(PERIOD_M15, 1);
   double bodyRatio = (range > 0.0) ? body / range : 0.0;
   bool dirOk = (dir == DIR_LONG) ? (close1 > open1) : (close1 < open1);
   bool sizeOk = range >= atr * InpDisplacementATR && bodyRatio >= InpDisplacementBodyRatio;
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
   for(int i = 2; i <= InpOBLookback; i++)
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
   int bars = iBars(g_symbol, InpOTE_HTF);
   int lookback = MathMin(InpOTE_SwingLookback, bars - 1);
   for(int i = 1; i <= lookback; i++)
   {
      swingHigh = MathMax(swingHigh, iHigh(g_symbol, InpOTE_HTF, i));
      swingLow = MathMin(swingLow, iLow(g_symbol, InpOTE_HTF, i));
   }
   if(swingHigh <= swingLow)
      return false;
   double range = swingHigh - swingLow;
   if(dir == DIR_LONG)
   {
      oteMin = swingHigh - range * InpOTE_Max;
      oteMax = swingHigh - range * InpOTE_Min;
      return (price >= oteMin && price <= oteMax && price <= (swingHigh - range * 0.5));
   }
   oteMin = swingLow + range * InpOTE_Min;
   oteMax = swingLow + range * InpOTE_Max;
   return (price >= oteMin && price <= oteMax && price >= (swingLow + range * 0.5));
}

bool FindRecentPivots(double &lastHigh, double &prevHigh, double &lastLow, double &prevLow)
{
   int foundHigh = 0;
   int foundLow = 0;
   lastHigh = prevHigh = 0.0;
   lastLow = prevLow = 0.0;

   int bars = iBars(g_symbol, PERIOD_M15);
   int start = InpPivotLen + InpPivotConfirmBars;
   int end = MathMin(bars - InpPivotLen - 1, 200);
   for(int i = start; i < end; i++)
   {
      if(i - InpPivotConfirmBars < 0)
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
   return shift <= InpMaxBarsAfterBOS;
}

bool BreakRetestOk(TradeDir dir, double atrM15)
{
   if(!InpUseBreakRetest)
      return true;

   double storedBosLevel = 0.0;
   if(!BOSStateValid(dir, storedBosLevel))
      return false;

   double tol = MathMax(atrM15 * InpRetestTolATR, 5 * g_point);
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
   double step = InpKeyLevelStepPrice;
   if(step <= 0.0)
      return price;
   return MathRound(price / step) * step;
}

double KeyBelow(double price)
{
   double step = InpKeyLevelStepPrice;
   return MathFloor(price / step) * step;
}

double KeyAbove(double price)
{
   double step = InpKeyLevelStepPrice;
   return MathCeil(price / step) * step;
}

bool KeyLevelNearOk(double mid, double &nearest)
{
   nearest = NearestKeyLevel(mid);
   return MathAbs(mid - nearest) <= InpKeyNearPrice;
}

bool AntiChaseOk(TradeDir dir, double mid, double nearest)
{
   double step = InpKeyLevelStepPrice;
   if(step <= 0.0)
      return true;
   double chaseKey = nearest;
   if(dir == DIR_LONG && nearest > mid)
      chaseKey = nearest - step;
   else if(dir == DIR_SHORT && nearest < mid)
      chaseKey = nearest + step;

   if(dir == DIR_LONG)
      return (mid - chaseKey <= InpKeyChaseMaxDistPrice);
   if(dir == DIR_SHORT)
      return (chaseKey - mid <= InpKeyChaseMaxDistPrice);
   return false;
}

int FVGDirection(double &zoneMid, double priceMid)
{
   if(!InpUseFVGFeature)
      return 0;

   int bars = iBars(g_symbol, PERIOD_M15);
   double bestDist = DBL_MAX;
   int bestDir = 0;
   double bestMid = 0.0;

   for(int i = 1; i <= InpFVGScanBars; i++)
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
   if(!InpUseFVGFeature)
      return true;

   double zoneMid = 0.0;
   int fvgDir = FVGDirection(zoneMid, mid);
   if(fvgDir == 0 || fvgDir != dir)
      return false;

   return MathAbs(mid - zoneMid) <= atrM15 * InpFVGMaxDistATR;
}

bool FibFilterOk(TradeDir dir, double mid, double lastLow, double lastHigh, bool &oteBonus)
{
   oteBonus = false;
   if(!InpUseFibFilter)
      return true;

   double range = MathAbs(lastHigh - lastLow);
   if(range <= 0.0)
      return false;

   double lvl50 = 0.0;
   double lvl618 = 0.0;
   if(dir == DIR_LONG)
   {
      lvl50 = lastHigh - range * InpFibBaseMin;
      lvl618 = lastHigh - range * InpFibBaseMax;
   }
   else
   {
      lvl50 = lastLow + range * InpFibBaseMin;
      lvl618 = lastLow + range * InpFibBaseMax;
   }

   double minLvl = MathMin(lvl50, lvl618) - InpFibTolPrice;
   double maxLvl = MathMax(lvl50, lvl618) + InpFibTolPrice;
   bool inBase = (mid >= minLvl && mid <= maxLvl);

   if(InpUseOTEBonus)
   {
      double otemin = 0.0;
      double otemax = 0.0;
      if(dir == DIR_LONG)
      {
         otemin = lastHigh - range * InpOTEMax;
         otemax = lastHigh - range * InpOTEMin;
      }
      else
      {
         otemin = lastLow + range * InpOTEMin;
         otemax = lastLow + range * InpOTEMax;
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
   if(!InpUseFootprintProxy)
      return true;

   double vol = (double)iVolume(g_symbol, PERIOD_M15, 1);
   double volMA = VolumeMA(PERIOD_M15, InpFP_VolMAPeriod, 2);
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

   accepted = (volRatio >= InpFP_VolSpikeRatio && bodyRatio >= InpFP_BodyMinRatio && closeSide >= InpFP_CloseSideMin);

   if(volRatio >= InpFP_AbsorpVolRatio && range <= atrM15 * InpFP_AbsorpRangeATR && closeSide < 0.55)
      absorption = true;

   if(InpFP_RequireAcceptance)
      return accepted && !absorption;
   return !absorption;
}

bool SpikeGuardOk(double atrM15)
{
   if(!InpUseSpikeGuard)
      return true;

   double high = iHigh(g_symbol, PERIOD_M15, 1);
   double low = iLow(g_symbol, PERIOD_M15, 1);
   return (high - low) <= atrM15 * InpSpikeMultATR;
}

bool RSIAfterLossOk(TradeDir dir)
{
   if(!InpUseRSIAfterLoss)
      return true;

   int lossStreak = GVGetInt("lossStreak", 0);
   if(lossStreak < InpLossStreakForRSI)
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
         if(symbol == g_symbol && magic == InpMagic)
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
   if(!InpUseMaxDailyLossLock)
      return false;

   double startEquity = GVGetDouble("dayEquityStart", AccountInfoDouble(ACCOUNT_EQUITY));
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double pct = (startEquity > 0.0) ? (equity - startEquity) / startEquity * 100.0 : 0.0;
   if(pct <= -InpMaxDailyLossPct)
   {
      GVSetInt("dayLocked", 1);
      return true;
   }
   return false;
}

bool SoftEquityLocked()
{
   if(!InpUseSoftEquityLock)
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
   if((gainPct >= InpSoftEqTrigger2 && curPct <= InpSoftEqFloor2) ||
      (gainPct >= InpSoftEqTrigger1 && curPct <= InpSoftEqFloor1))
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
   double volAvg = VolumeMA(PERIOD_H1, InpVolMAPeriod, 2);
   double volScore = (volAvg > 0.0) ? MathMin(30.0, (vol / volAvg) * 15.0) : 0.0;
   double adxScore = MathMin(30.0, adx);

   double spreadScore = 20.0;
   if(g_spreadEma > 0.0)
   {
      double spread = SpreadPoints();
      spreadScore = 20.0 * MathMax(0.0, 1.0 - (spread / (g_spreadEma * InpSpreadSpikeFactor)));
   }

   double regimeScore = 0.0;
   if(regime == REGIME_TREND)
      regimeScore = 20.0;
   else if(regime == REGIME_TRANSITION)
      regimeScore = 10.0;

   int lossStreak = GVGetInt("lossStreak", 0);
   double lossPenalty = lossStreak * 5.0;
   if(SpreadMultipleBlocked() || SpreadInstabilityBlocked() || RolloverBlocked())
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
   return shift <= InpCooldownBarsAfterEntry;
}

void UpdateDailyReset()
{
   datetime dayStart = (datetime)GVGetDouble("dayStart", 0.0);
   datetime now = TimeCurrent();
   if(TimeDay(dayStart) != TimeDay(now) || dayStart == 0)
   {
      GVSetDouble("dayStart", (double)now);
      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      GVSetDouble("dayEquityStart", equity);
      GVSetDouble("dayEquityPeak", equity);
      GVSetInt("dayLocked", 0);
      GVSetInt("dayTrades", 0);
   }
}

bool HardGuardsOk(int &skipMask)
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
   if(SpreadPoints() > InpMaxSpreadPoints)
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

bool LossBlocksActive()
{
   if(!InpUseAntiChop)
      return false;

   datetime blockUntil = (datetime)GVGetDouble("blockUntil", 0.0);
   return (blockUntil > TimeCurrent());
}

void UpdateLossBlock(int lossStreak)
{
   if(!InpUseAntiChop)
      return;

   if(lossStreak >= 3)
   {
      GVSetDouble("blockUntil", TimeCurrent() + InpLossBlock3_Hours * 3600.0);
      GVSetDouble("riskCutUntil", TimeCurrent() + InpRiskCutAfter3Loss_H * 3600.0);
   }
   else if(lossStreak == 2)
   {
      GVSetDouble("blockUntil", TimeCurrent() + InpLossBlock2_Hours * 3600.0);
   }
}

double CurrentRiskMultiplier(double dailyRiskMult)
{
   double mult = dailyRiskMult;
   datetime riskCutUntil = (datetime)GVGetDouble("riskCutUntil", 0.0);
   if(riskCutUntil > TimeCurrent())
      mult *= InpRiskMultAfter3Loss;
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

double CalcLots(double slDist, double riskPct)
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * (riskPct / 100.0);
   double tickSize = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
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
   if(InpMaxLotCap > 0.0)
      maxLot = MathMin(maxLot, InpMaxLotCap);
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
   return NormalizeDouble(vol, 2);
}

bool StopsOk(TradeDir dir, double entry, double sl, double tp)
{
   int stopsLevel = (int)SymbolInfoInteger(g_symbol, SYMBOL_TRADE_STOPS_LEVEL);
   if(stopsLevel <= 0)
      return true;

   double minDist = stopsLevel * g_point;
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

bool SendOrderWithRetry(TradeDir dir, double lots, double sl, double tp, const string comment, int &retcode, int &lasterr)
{
   retcode = 0;
   lasterr = 0;
   for(int attempt = 0; attempt <= InpMaxRetries; attempt++)
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
         Sleep(InpRetryDelayMs);
         continue;
      }
      break;
   }
   return false;
}

void LogCSV(const string event, TradeDir dir, double entry, double sl, double tp, double tp1, double lot,
            int dailyScore, int setup, int timing, int total, int skipMask, int entryMask,
            int retcode, int lasterr, double bosLevel, int bosAgeBars, double nearestKey,
            int killzoneActive, double pdh, double pdl, double psh, double psl, double hod, double lod,
            int sweepDir, double sweepLevel, double displacementScore, double obHigh, double obLow, double obMT,
            int oteOk)
{
   if(!InpEnableCSV)
      return;

   int handle = FileOpen(InpCSVName, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      handle = FileOpen(InpCSVName, FILE_WRITE | FILE_CSV | FILE_ANSI);

   if(handle == INVALID_HANDLE)
      return;

   if(FileSize(handle) == 0)
   {
      FileWrite(handle, "time", "sym", "magic", "event", "dir", "entry", "sl", "tp", "tp1", "lot", "spreadPts",
                "reg", "bias", "adx", "atrM15", "atrH1", "dailyScore", "lossStreak", "skipMask", "entryMask",
                "setup", "timing", "total", "retcode", "lasterr", "spreadEma", "spreadNow",
                "stopsLevelPts", "freezeLevelPts", "bosLevel", "bosAgeBars", "nearestKey", "tp1Price",
                "killzoneActive", "pdh", "pdl", "psh", "psl", "hod", "lod",
                "sweepDir", "sweepLevel", "displacementScore", "obHigh", "obLow", "obMT", "oteOk");
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
             (string)InpMagic,
             event,
             (int)dir,
             DoubleToString(entry, g_digits),
             DoubleToString(sl, g_digits),
             DoubleToString(tp, g_digits),
             DoubleToString(tp1, g_digits),
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
             oteOk);

   FileClose(handle);
}

bool CalculateEntry(TradeDir &dir, double &entry, double &sl, double &tp, double &tp1, double &riskR,
                    int &setupScore, int &timingScore, int &totalScore, int &skipMask, int &entryMask,
                    double &nearestKey, double &bosLevel, int &bosAgeBars, int &killzoneActive,
                    double &pdh, double &pdl, double &psh, double &psl, double &hod, double &lod,
                    int &sweepDir, double &sweepLevel, double &displacementScore,
                    double &obHigh, double &obLow, double &obMT, int &oteOk)
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

   TradeDir bias = BiasH1();
   if(bias == DIR_NONE)
      return false;
   dir = bias;
   setupScore += 20;
   entryMask |= ENTRY_BIAS;

   bool kzAsia = false;
   bool kzLondon = false;
   bool kzNY = false;
   if(InpUseICTTime)
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
   GetHODLOD(hod, lod);

   TradeDir sweepDirFound = DIR_NONE;
   double sweepLevelFound = 0.0;
   if(!DetectLiquiditySweep(sweepDirFound, sweepLevelFound))
      return false;
   if(sweepDirFound != dir)
      return false;
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

   if(InpUseFVGFeature)
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
      setupScore += InpOTEBonusPoints;

   double oteMin = 0.0;
   double oteMax = 0.0;
   double swingHigh = 0.0;
   double swingLow = 0.0;
   if(!OTEOk(dir, mid, oteMin, oteMax, swingHigh, swingLow))
      return false;
   oteOk = 1;
   entryMask |= ENTRY_OTE;
   setupScore += 10;
   if(MathAbs(mid - swingHigh) <= InpKeyNearPrice || MathAbs(mid - swingLow) <= InpKeyNearPrice)
      entryMask |= ENTRY_SR;

   bool absorption = false;
   bool acceptance = true;
   if(!FootprintOk(dir, atrM15, absorption, acceptance))
      return false;
   entryMask |= ENTRY_FOOTPRINT;
   if(acceptance)
      timingScore += InpFP_ScoreBonus;

   if(!SpikeGuardOk(atrM15))
      return false;
   entryMask |= ENTRY_SPIKE;

   if(!RSIAfterLossOk(dir))
      return false;
   entryMask |= ENTRY_RSI_LOSS;

   int obAgeBars = -1;
   if(!FindOrderBlock(dir, obHigh, obLow, obMT, obAgeBars))
      return false;
   if(obAgeBars > InpOBMaxAgeBars)
      return false;
   if(!(mid >= obLow && mid <= obHigh))
      return false;
   entryMask |= ENTRY_OB_RTO;
   setupScore += 10;

   entry = (dir == DIR_LONG) ? SymbolInfoDouble(g_symbol, SYMBOL_ASK) : SymbolInfoDouble(g_symbol, SYMBOL_BID);
   double atrBuf = atrM15 * InpSL_ATR_Mult;
   double spreadBuf = SpreadPoints() * g_point * 0.5;
   double buffer = MathMax(InpSL_MinBufferPrice, MathMax(atrBuf, spreadBuf));

   sl = (dir == DIR_LONG) ? (lastLow - buffer) : (lastHigh + buffer);
   riskR = MathAbs(entry - sl);
   if(riskR <= 0.0)
      return false;

   if(InpUseMMSL)
   {
      double mmsl = InpMMSL_Pips * PipPrice() + InpMMSL_ExtraBufferPrice;
      if(riskR < mmsl)
         return false;
      entryMask |= ENTRY_MMSL;
   }

   tp = (dir == DIR_LONG) ? (entry + riskR * InpTP_RR_Main) : (entry - riskR * InpTP_RR_Main);
   double rr = MathAbs(tp - entry) / riskR;
   if(rr < InpMinRRAllowed)
      return false;
   entryMask |= ENTRY_RR;

   tp1 = (dir == DIR_LONG) ? (entry + riskR) : (entry - riskR);
   if(InpUseTP1Partial && InpTP1_UseKeyLevelFirst)
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
   if(space < InpMinPDArrayDistance)
   {
      skipMask |= SKIP_PDARRAY;
      return false;
   }
   entryMask |= ENTRY_PDARRAY;

   bosAgeBars = BOSAgeBars(bosLevel);
   totalScore = setupScore + timingScore;
   return true;
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

   bool tp1done = GVGetInt("tp1done", 0) == 1;
   double tp1price = GVGetDouble("tp1price", 0.0);

   bool tp1Hit = false;
   if(type == POSITION_TYPE_BUY)
      tp1Hit = (tp1price > 0.0 && SymbolInfoDouble(g_symbol, SYMBOL_BID) >= tp1price);
   else
      tp1Hit = (tp1price > 0.0 && SymbolInfoDouble(g_symbol, SYMBOL_ASK) <= tp1price);

   if(InpUseTP1Partial && !tp1done && tp1Hit)
   {
      double step = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_STEP);
      double minLot = SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN);
      double closeVol = MathFloor((volume * InpTP1_CloseFrac) / step) * step;
      closeVol = NormalizeVolumeByStep(closeVol);
      if(closeVol >= minLot && (volume - closeVol) >= minLot && FreezeOkForClose())
      {
         trade.PositionClosePartial(ticket, closeVol);
         GVSetInt("tp1done", 1);
         GVSetDouble("tp1price", price);
         double bosLevel = 0.0;
         int bosAgeBars = BOSAgeBars(bosLevel);
         LogCSV("TP1", (type == POSITION_TYPE_BUY ? DIR_LONG : DIR_SHORT), entry, sl, tp, tp1price, volume, 0, 0, 0, 0, 0, 0,
                0, 0, bosLevel, bosAgeBars, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0, 0.0, 0.0, 0.0, 0.0, 0.0, 0);
      }
   }

   if(InpUseSmartBE && profitR >= InpBE_MinProfitR)
   {
      double newSL = (type == POSITION_TYPE_BUY) ? (entry + InpBE_OffsetPrice) : (entry - InpBE_OffsetPrice);
      TradeDir dir = (type == POSITION_TYPE_BUY) ? DIR_LONG : DIR_SHORT;
      if(CanModifyStops(newSL) && StopsOk(dir, entry, newSL, tp) &&
         ((type == POSITION_TYPE_BUY && newSL > sl) || (type == POSITION_TYPE_SELL && newSL < sl)))
         trade.PositionModify(ticket, newSL, tp);
   }

   if(InpUseATRTrailAfterTP1 && tp1done)
   {
      if(!InpTrailOnNewBarOnly || IsNewBar(PERIOD_M15, g_lastM15Bar))
      {
         double atr = ATR(PERIOD_M15, 1);
         double newSL = (type == POSITION_TYPE_BUY) ? (price - atr * InpTrailATR_Mult) : (price + atr * InpTrailATR_Mult);
         TradeDir dir = (type == POSITION_TYPE_BUY) ? DIR_LONG : DIR_SHORT;
         if(type == POSITION_TYPE_BUY && newSL > sl + InpTrailMinImprovePrice && CanModifyStops(newSL) && StopsOk(dir, entry, newSL, tp))
            trade.PositionModify(ticket, newSL, tp);
         else if(type == POSITION_TYPE_SELL && newSL < sl - InpTrailMinImprovePrice && CanModifyStops(newSL) && StopsOk(dir, entry, newSL, tp))
            trade.PositionModify(ticket, newSL, tp);
      }
   }
}

void TryPyramiding(double riskR, bool pyramidAllowed, RegimeState regime)
{
   if(!InpUsePyramiding || !pyramidAllowed)
      return;
   if(!SelectOurPosition())
      return;

   int addCount = GVGetInt("addCount", 0);
   if(addCount >= InpMaxAdds)
      return;

   int type = (int)PositionGetInteger(POSITION_TYPE);
   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl = PositionGetDouble(POSITION_SL);
   double price = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_symbol, SYMBOL_BID) : SymbolInfoDouble(g_symbol, SYMBOL_ASK);
   double profitR = (type == POSITION_TYPE_BUY) ? (price - entry) / riskR : (entry - price) / riskR;

   if(profitR < InpPyramidMinProfitR)
      return;

   double lastAddPrice = GVGetDouble("lastAddPrice", entry);
   double atr = ATR(PERIOD_M15, 1);
   if(MathAbs(price - lastAddPrice) < atr * InpPyramidSpacingATR)
      return;

   if(InpPyramidRequireMainBE)
   {
      if(type == POSITION_TYPE_BUY && sl < entry + g_point)
         return;
      if(type == POSITION_TYPE_SELL && sl > entry - g_point)
         return;
   }

   if(InpPyramidOnlyInTrend && regime != REGIME_TREND)
      return;

   if(InpPyramidRequireAdxRising)
   {
      double adx1 = ADX(PERIOD_H1, 1);
      double adx2 = ADX(PERIOD_H1, 2);
      if(adx1 <= adx2)
         return;
   }

   if(InpPyramidUsePeakDDCap)
   {
      double peak = GVGetDouble("dayEquityPeak", AccountInfoDouble(ACCOUNT_EQUITY));
      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      double dd = (peak - equity) / peak * 100.0;
      if(dd > InpPyramidMaxPeakDDPct)
         return;
   }

   double riskMult = (addCount == 0) ? InpAddRiskMult1 : InpAddRiskMult2;
   double addLots = CalcLots(riskR, InpBaseRiskPct * riskMult);
   if(addLots <= 0.0)
      return;

   double addTp = (type == POSITION_TYPE_BUY) ? (price + riskR * InpTP_RR_Main) : (price - riskR * InpTP_RR_Main);
   TradeDir dir = (type == POSITION_TYPE_BUY) ? DIR_LONG : DIR_SHORT;
   if(!StopsOk(dir, price, sl, addTp))
      return;

   bool result = false;
   int retcode = 0;
   int lasterr = 0;
   result = SendOrderWithRetry(dir, addLots, sl, addTp, "PYR", retcode, lasterr);

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

int OnInit()
{
   g_symbol = ResolveSymbol();
   g_digits = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);
   g_point = SymbolInfoDouble(g_symbol, SYMBOL_POINT);
   g_pip = g_point * 10.0;

   trade.SetExpertMagicNumber((uint)InpMagic);
   trade.SetDeviationInPoints(InpMaxSlippagePoints);

   UpdateDailyReset();

   return INIT_SUCCEEDED;
}

void OnTick()
{
   if(g_symbol == "")
      return;

   UpdateDailyReset();

   if(IsNewBar(PERIOD_H1, g_lastH1Bar))
      UpdateSpreadEMA();

   RegimeState regime = UpdateRegime();

   if(HasPosition())
   {
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
      LogCSV("SKIP", DIR_NONE, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0, skipMask, 0,
             0, 0, bosLevel, bosAgeBars, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
             0, 0.0, 0.0, 0.0, 0.0, 0.0, 0);
      return;
   }
   if(!HardGuardsOk(skipMask))
   {
      double bosLevel = 0.0;
      int bosAgeBars = BOSAgeBars(bosLevel);
      LogCSV("SKIP", DIR_NONE, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0, skipMask, 0,
             0, 0, bosLevel, bosAgeBars, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
             0, 0.0, 0.0, 0.0, 0.0, 0.0, 0);
      return;
   }

   int dayTrades = GVGetInt("dayTrades", 0);
   int dailyScore = DailyScore(regime);
   int maxTrades = 0;
   double dailyRiskMult = 0.0;
   bool pyramidAllowed = false;
   if(InpUseDailyTradeControl && !DailyTradeAllowed(dailyScore, maxTrades, dailyRiskMult, pyramidAllowed))
   {
      skipMask |= SKIP_DAILY_SCORE;
      double bosLevel = 0.0;
      int bosAgeBars = BOSAgeBars(bosLevel);
      LogCSV("SKIP", DIR_NONE, 0.0, 0.0, 0.0, 0.0, 0.0, dailyScore, 0, 0, 0, skipMask, 0,
             0, 0, bosLevel, bosAgeBars, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
             0, 0.0, 0.0, 0.0, 0.0, 0.0, 0);
      return;
   }

   int allowedTrades = InpHardMaxTradesPerDay;
   if(InpUseDailyTradeControl)
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

   if(!CalculateEntry(dir, entry, sl, tp, tp1, riskR, setupScore, timingScore, totalScore, skipMask, entryMask,
                      nearestKey, bosLevel, bosAgeBars, killzoneActive, pdh, pdl, psh, psl, hod, lod,
                      sweepDir, sweepLevel, displacementScore, obHigh, obLow, obMT, oteOk))
   {
      LogCSV("NOENTRY", DIR_NONE, 0.0, 0.0, 0.0, tp1, 0.0, dailyScore, setupScore, timingScore, totalScore, skipMask, entryMask,
             0, 0, bosLevel, bosAgeBars, nearestKey, killzoneActive, pdh, pdl, psh, psl, hod, lod,
             sweepDir, sweepLevel, displacementScore, obHigh, obLow, obMT, oteOk);
      return;
   }

   if(!ShouldEnterTrade(setupScore, timingScore, totalScore, regime))
      return;

   double riskMult = CurrentRiskMultiplier(dailyRiskMult);
   double lots = CalcLots(riskR, InpBaseRiskPct * riskMult);
   if(lots <= 0.0)
      return;

   if(!StopsOk(dir, entry, sl, tp))
   {
      skipMask |= SKIP_STOPS;
      LogCSV("SKIP", DIR_NONE, entry, sl, tp, tp1, 0.0, dailyScore, setupScore, timingScore, totalScore, skipMask, entryMask,
             0, 0, bosLevel, bosAgeBars, nearestKey, killzoneActive, pdh, pdl, psh, psl, hod, lod,
             sweepDir, sweepLevel, displacementScore, obHigh, obLow, obMT, oteOk);
      return;
   }

   int retcode = 0;
   int lasterr = 0;
   bool sent = SendOrderWithRetry(dir, lots, sl, tp, "ENTRY", retcode, lasterr);

   if(sent)
   {
      GVSetInt("dayTrades", dayTrades + 1);
      GVSetDouble("lastEntryTime", (double)iTime(g_symbol, PERIOD_M15, 0));
      GVSetDouble("origRisk", riskR);
      GVSetInt("tp1done", 0);
      GVSetDouble("tp1price", tp1);
      GVSetInt("addCount", 0);
      GVSetDouble("lastAddPrice", entry);

      LogCSV("ENTRY", dir, entry, sl, tp, tp1, lots, dailyScore, setupScore, timingScore, totalScore, skipMask, entryMask,
             retcode, lasterr, bosLevel, bosAgeBars, nearestKey, killzoneActive, pdh, pdl, psh, psl, hod, lod,
             sweepDir, sweepLevel, displacementScore, obHigh, obLow, obMT, oteOk);
   }
   else
   {
      LogCSV("ENTRY_FAIL", dir, entry, sl, tp, tp1, lots, dailyScore, setupScore, timingScore, totalScore, skipMask, entryMask,
             retcode, lasterr, bosLevel, bosAgeBars, nearestKey, killzoneActive, pdh, pdl, psh, psl, hod, lod,
             sweepDir, sweepLevel, displacementScore, obHigh, obLow, obMT, oteOk);
   }
}

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD)
      return;
   if(trans.symbol != g_symbol)
      return;
   if(trans.magic != InpMagic)
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

      double bosLevel = 0.0;
      int bosAgeBars = BOSAgeBars(bosLevel);
      LogCSV("EXIT", DIR_NONE, trans.price, 0.0, 0.0, 0.0, trans.volume,
             DailyScore((RegimeState)GVGetInt("regime", REGIME_RANGE)), 0, 0, 0, 0, 0,
             0, 0, bosLevel, bosAgeBars, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
             0, 0.0, 0.0, 0.0, 0.0, 0.0, 0);
   }
}
