//+------------------------------------------------------------------+
//|                                     XAUUSD Killer XM (MT5)       |
//|   Trend-follow + SMC light - production-safe single file EA      |
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

input int    InpATRPeriod = 14;
input int    InpADXPeriod = 14;
input int    InpRSIPeriod = 14;
input int    InpEMA_Fast = 50;
input int    InpEMA_Slow = 200;

input int    InpRegimeConfirmBarsH1 = 2;
input int    InpRegimeLockBarsH1 = 4;

input int    InpPivotLen = 3;
input int    InpPivotConfirmBars = 2;

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
datetime g_lastM15Bar = 0;
datetime g_lastH1Bar = 0;
double g_spreadEma = 0.0;

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
   return _Point * 10.0;
}

double SpreadPoints()
{
   double ask = SymbolInfoDouble(g_symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(g_symbol, SYMBOL_BID);
   return (ask - bid) / _Point;
}

bool TimeInRange(const string start, const string end)
{
   datetime now = TimeCurrent();
   int sh = StringToInteger(StringSubstr(start, 0, 2));
   int sm = StringToInteger(StringSubstr(start, 3, 2));
   int eh = StringToInteger(StringSubstr(end, 0, 2));
   int em = StringToInteger(StringSubstr(end, 3, 2));

   datetime s = StructToTime(BuildTimeStruct(now, sh, sm));
   datetime e = StructToTime(BuildTimeStruct(now, eh, em));

   if(e < s)
      return (now >= s || now <= e);
   return (now >= s && now <= e);
}

MqlDateTime BuildTimeStruct(datetime t, int hour, int min)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   dt.hour = hour;
   dt.min = min;
   dt.sec = 0;
   return dt;
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

bool FindRecentPivots(double &lastHigh, double &prevHigh, double &lastLow, double &prevLow)
{
   int foundHigh = 0;
   int foundLow = 0;
   lastHigh = prevHigh = 0.0;
   lastLow = prevLow = 0.0;

   int start = InpPivotConfirmBars;
   int end = 100;
   for(int i = start; i < end; i++)
   {
      bool isHigh = true;
      bool isLow = true;
      double high = iHigh(g_symbol, PERIOD_M15, i);
      double low = iLow(g_symbol, PERIOD_M15, i);
      for(int j = 1; j <= InpPivotLen; j++)
      {
         if(high <= iHigh(g_symbol, PERIOD_M15, i - j) || high <= iHigh(g_symbol, PERIOD_M15, i + j))
            isHigh = false;
         if(low >= iLow(g_symbol, PERIOD_M15, i - j) || low >= iLow(g_symbol, PERIOD_M15, i + j))
            isLow = false;
      }
      if(isHigh)
      {
         if(foundHigh == 0)
            lastHigh = high;
         else if(foundHigh == 1)
            prevHigh = high;
         foundHigh++;
      }
      if(isLow)
      {
         if(foundLow == 0)
            lastLow = low;
         else if(foundLow == 1)
            prevLow = low;
         foundLow++;
      }
      if(foundHigh >= 2 && foundLow >= 2)
         return true;
   }
   return false;
}

bool BreakRetestOk(TradeDir dir, double bosLevel, double atrM15)
{
   if(!InpUseBreakRetest)
      return true;

   double tol = MathMax(atrM15 * InpRetestTolATR, 5 * _Point);
   double close1 = iClose(g_symbol, PERIOD_M15, 1);
   double low1 = iLow(g_symbol, PERIOD_M15, 1);
   double high1 = iHigh(g_symbol, PERIOD_M15, 1);

   if(dir == DIR_LONG)
      return (low1 <= bosLevel + tol && close1 > bosLevel);
   if(dir == DIR_SHORT)
      return (high1 >= bosLevel - tol && close1 < bosLevel);
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

bool KeyLevelOk(TradeDir dir, double mid)
{
   double nearest = NearestKeyLevel(mid);
   if(MathAbs(mid - nearest) > InpKeyNearPrice)
      return false;

   if(dir == DIR_LONG)
      return (mid - KeyBelow(mid) <= InpKeyChaseMaxDistPrice);
   if(dir == DIR_SHORT)
      return (KeyAbove(mid) - mid <= InpKeyChaseMaxDistPrice);
   return false;
}

int FVGDirection(double &zoneMid, double atrM15)
{
   if(!InpUseFVGFeature)
      return 0;

   for(int i = 1; i <= InpFVGScanBars; i++)
   {
      double low = iLow(g_symbol, PERIOD_M15, i);
      double high = iHigh(g_symbol, PERIOD_M15, i);
      double low2 = iLow(g_symbol, PERIOD_M15, i + 2);
      double high2 = iHigh(g_symbol, PERIOD_M15, i + 2);

      if(low > high2)
      {
         zoneMid = (low + high2) / 2.0;
         return DIR_LONG;
      }
      if(high < low2)
      {
         zoneMid = (high + low2) / 2.0;
         return DIR_SHORT;
      }
   }
   return 0;
}

bool FVGOk(TradeDir dir, double mid, double atrM15)
{
   if(!InpUseFVGFeature)
      return true;

   double zoneMid = 0.0;
   int fvgDir = FVGDirection(zoneMid, atrM15);
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

bool HasPosition()
{
   return PositionSelect(g_symbol);
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
   int lastEntryBar = GVGetInt("lastEntryBar", 0);
   int currentBar = (int)iBars(g_symbol, PERIOD_M15);
   return (currentBar - lastEntryBar) <= InpCooldownBarsAfterEntry;
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

bool HardGuardsOk()
{
   if(!SessionAllowed())
      return false;
   if(RolloverBlocked())
      return false;
   if(SpreadPoints() > InpMaxSpreadPoints)
      return false;
   if(SpreadMultipleBlocked())
      return false;
   if(SpreadInstabilityBlocked())
      return false;
   if(LowVolumeBlocked())
      return false;
   if(DailyLossLocked() || SoftEquityLocked())
      return false;
   if(GVGetInt("dayLocked", 0) == 1)
      return false;
   if(CooldownActive())
      return false;
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

double CalcLots(double slDist, double riskPct)
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * (riskPct / 100.0);
   double tickSize = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(g_symbol, SYMBOL_TRADE_TICK_VALUE);
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
   lot = MathFloor(lot / step) * step;
   return NormalizeDouble(lot, 2);
}

void LogCSV(const string event, TradeDir dir, double entry, double sl, double tp, double tp1, double lot,
            int dailyScore, int setup, int timing, int total, int skipMask, int entryMask)
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
                "setup", "timing", "total");
   }

   int lossStreak = GVGetInt("lossStreak", 0);
   RegimeState reg = (RegimeState)GVGetInt("regime", REGIME_RANGE);
   TradeDir bias = BiasH1();
   double adx = ADX(PERIOD_H1, 1);
   double atrM15 = ATR(PERIOD_M15, 1);
   double atrH1 = ATR(PERIOD_H1, 1);

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
             DoubleToString(SpreadPoints(), 1),
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
             total);

   FileClose(handle);
}

bool CalculateEntry(TradeDir &dir, double &entry, double &sl, double &tp, double &tp1, double &riskR,
                    int &setupScore, int &timingScore, int &totalScore, int &skipMask, int &entryMask)
{
   setupScore = 0;
   timingScore = 0;
   totalScore = 0;
   skipMask = 0;
   entryMask = 0;
   dir = DIR_NONE;

   TradeDir bias = BiasH1();
   if(bias == DIR_NONE)
      return false;
   dir = bias;
   setupScore += 20;

   double lastHigh = 0.0, prevHigh = 0.0, lastLow = 0.0, prevLow = 0.0;
   if(!FindRecentPivots(lastHigh, prevHigh, lastLow, prevLow))
      return false;

   if(dir == DIR_LONG && !(lastLow > prevLow))
      return false;
   if(dir == DIR_SHORT && !(lastHigh < prevHigh))
      return false;
   setupScore += 10;

   double bosLevel = (dir == DIR_LONG) ? lastHigh : lastLow;
   double close1 = iClose(g_symbol, PERIOD_M15, 1);
   bool closeConfirm = (dir == DIR_LONG) ? (close1 > bosLevel) : (close1 < bosLevel);
   double atrM15 = ATR(PERIOD_M15, 1);

   bool brOk = BreakRetestOk(dir, bosLevel, atrM15);
   if(!closeConfirm && !brOk)
      return false;
   timingScore += 10;

   double mid = (SymbolInfoDouble(g_symbol, SYMBOL_ASK) + SymbolInfoDouble(g_symbol, SYMBOL_BID)) / 2.0;
   if(!KeyLevelOk(dir, mid))
      return false;
   setupScore += 10;

   if(!FVGOk(dir, mid, atrM15))
      return false;
   setupScore += 5;

   bool oteBonus = false;
   if(!FibFilterOk(dir, mid, lastLow, lastHigh, oteBonus))
      return false;
   setupScore += 15;
   if(oteBonus)
      setupScore += InpOTEBonusPoints;

   bool absorption = false;
   bool acceptance = true;
   if(!FootprintOk(dir, atrM15, absorption, acceptance))
      return false;
   if(acceptance)
      timingScore += InpFP_ScoreBonus;

   if(!SpikeGuardOk(atrM15))
      return false;

   if(!RSIAfterLossOk(dir))
      return false;

   entry = (dir == DIR_LONG) ? SymbolInfoDouble(g_symbol, SYMBOL_ASK) : SymbolInfoDouble(g_symbol, SYMBOL_BID);
   double atrBuf = atrM15 * InpSL_ATR_Mult;
   double spreadBuf = SpreadPoints() * _Point * 0.5;
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
   }

   tp = (dir == DIR_LONG) ? (entry + riskR * InpTP_RR_Main) : (entry - riskR * InpTP_RR_Main);
   double rr = MathAbs(tp - entry) / riskR;
   if(rr < InpMinRRAllowed)
      return false;

   tp1 = (dir == DIR_LONG) ? (entry + riskR) : (entry - riskR);
   if(InpUseTP1Partial && InpTP1_UseKeyLevelFirst)
   {
      double key = NearestKeyLevel(entry);
      double dist = MathAbs(key - entry);
      if(dist > PipPrice() && dist < MathAbs(tp1 - entry))
         tp1 = (dir == DIR_LONG) ? MathMax(entry + dist, tp1) : MathMin(entry - dist, tp1);
   }

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
   if(!PositionSelect(g_symbol))
      return;

   ulong ticket = PositionGetInteger(POSITION_TICKET);
   int type = (int)PositionGetInteger(POSITION_TYPE);
   double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl = PositionGetDouble(POSITION_SL);
   double tp = PositionGetDouble(POSITION_TP);
   double volume = PositionGetDouble(POSITION_VOLUME);
   double price = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_symbol, SYMBOL_BID) : SymbolInfoDouble(g_symbol, SYMBOL_ASK);

   double profitR = (type == POSITION_TYPE_BUY) ? (price - entry) / riskR : (entry - price) / riskR;

   bool tp1done = GVGetInt("tp1done", 0) == 1;
   double tp1price = GVGetDouble("tp1price", 0.0);

   if(InpUseTP1Partial && !tp1done && profitR >= 1.0)
   {
      double closeVol = volume * InpTP1_CloseFrac;
      closeVol = NormalizeDouble(closeVol, 2);
      if(closeVol >= SymbolInfoDouble(g_symbol, SYMBOL_VOLUME_MIN))
      {
         trade.PositionClosePartial(ticket, closeVol);
         GVSetInt("tp1done", 1);
         GVSetDouble("tp1price", price);
         LogCSV("TP1", (type == POSITION_TYPE_BUY ? DIR_LONG : DIR_SHORT), entry, sl, tp, tp1price, volume, 0, 0, 0, 0, 0, 0);
      }
   }

   if(InpUseSmartBE && profitR >= InpBE_MinProfitR)
   {
      double newSL = (type == POSITION_TYPE_BUY) ? (entry + InpBE_OffsetPrice) : (entry - InpBE_OffsetPrice);
      if((type == POSITION_TYPE_BUY && newSL > sl) || (type == POSITION_TYPE_SELL && newSL < sl))
         trade.PositionModify(ticket, newSL, tp);
   }

   if(InpUseATRTrailAfterTP1 && tp1done)
   {
      if(!InpTrailOnNewBarOnly || IsNewBar(PERIOD_M15, g_lastM15Bar))
      {
         double atr = ATR(PERIOD_M15, 1);
         double newSL = (type == POSITION_TYPE_BUY) ? (price - atr * InpTrailATR_Mult) : (price + atr * InpTrailATR_Mult);
         if(type == POSITION_TYPE_BUY && newSL > sl + InpTrailMinImprovePrice)
            trade.PositionModify(ticket, newSL, tp);
         else if(type == POSITION_TYPE_SELL && newSL < sl - InpTrailMinImprovePrice)
            trade.PositionModify(ticket, newSL, tp);
      }
   }
}

void TryPyramiding(double riskR, bool pyramidAllowed, RegimeState regime)
{
   if(!InpUsePyramiding || !pyramidAllowed)
      return;
   if(!PositionSelect(g_symbol))
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

   bool result = false;
   if(type == POSITION_TYPE_BUY)
      result = trade.Buy(addLots, g_symbol, price, sl, price + riskR * InpTP_RR_Main, "PYR");
   else
      result = trade.Sell(addLots, g_symbol, price, sl, price - riskR * InpTP_RR_Main, "PYR");

   if(result)
   {
      GVSetInt("addCount", addCount + 1);
      GVSetDouble("lastAddPrice", price);
      LogCSV("PYR", (type == POSITION_TYPE_BUY ? DIR_LONG : DIR_SHORT), price, sl, 0.0, 0.0, addLots, 0, 0, 0, 0, 0, 0);
   }
}

int OnInit()
{
   g_symbol = ResolveSymbol();
   g_digits = (int)SymbolInfoInteger(g_symbol, SYMBOL_DIGITS);

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
      double riskR = GVGetDouble("origRisk", 0.0);
      ManagePosition(riskR);
      int dailyScore = DailyScore(regime);
      bool pyramidAllowed = false;
      int maxTrades = 0;
      double dailyRiskMult = 0.0;
      DailyTradeAllowed(dailyScore, maxTrades, dailyRiskMult, pyramidAllowed);
      TryPyramiding(riskR, pyramidAllowed, regime);
      return;
   }

   if(LossBlocksActive())
      return;
   if(!HardGuardsOk())
      return;

   int dayTrades = GVGetInt("dayTrades", 0);
   if(InpUseDailyTradeControl && dayTrades >= InpHardMaxTradesPerDay)
      return;

   int dailyScore = DailyScore(regime);
   int maxTrades = 0;
   double dailyRiskMult = 0.0;
   bool pyramidAllowed = false;
   if(InpUseDailyTradeControl && !DailyTradeAllowed(dailyScore, maxTrades, dailyRiskMult, pyramidAllowed))
      return;

   TradeDir dir;
   double entry = 0.0, sl = 0.0, tp = 0.0, tp1 = 0.0, riskR = 0.0;
   int setupScore = 0, timingScore = 0, totalScore = 0, skipMask = 0, entryMask = 0;

   if(!CalculateEntry(dir, entry, sl, tp, tp1, riskR, setupScore, timingScore, totalScore, skipMask, entryMask))
      return;

   if(!ShouldEnterTrade(setupScore, timingScore, totalScore, regime))
      return;

   double riskMult = CurrentRiskMultiplier(dailyRiskMult);
   double lots = CalcLots(riskR, InpBaseRiskPct * riskMult);
   if(lots <= 0.0)
      return;

   bool sent = false;
   if(dir == DIR_LONG)
      sent = trade.Buy(lots, g_symbol, entry, sl, tp, "ENTRY");
   else if(dir == DIR_SHORT)
      sent = trade.Sell(lots, g_symbol, entry, sl, tp, "ENTRY");

   if(sent)
   {
      GVSetInt("dayTrades", dayTrades + 1);
      GVSetInt("lastEntryBar", (int)iBars(g_symbol, PERIOD_M15));
      GVSetDouble("origRisk", riskR);
      GVSetInt("tp1done", 0);
      GVSetDouble("tp1price", tp1);
      GVSetInt("addCount", 0);
      GVSetDouble("lastAddPrice", entry);

      LogCSV("ENTRY", dir, entry, sl, tp, tp1, lots, dailyScore, setupScore, timingScore, totalScore, skipMask, entryMask);
   }
}

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD)
      return;
   if(trans.symbol != g_symbol)
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

      LogCSV("EXIT", DIR_NONE, trans.price, 0.0, 0.0, 0.0, trans.volume, DailyScore((RegimeState)GVGetInt("regime", REGIME_RANGE)), 0, 0, 0, 0, 0);
   }
}
