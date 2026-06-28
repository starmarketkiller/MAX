//| NXS_ReusePerformancePack.mqh                                     |
//| Reuse/adaptation pack v1.2 for NEXUS v2.0.8c AUDITPATCH         |
//|                                                                  |
//| PURPOSE                                                          |
//| - Reuse only the sound, isolated logic found in KODEXAI v26,     |
//|   GoldKiller and GROK; NEXUS remains the principal EA.            |
//| - Remove the main causes of low trade frequency without using    |
//|   martingale, grid escalation or unsafe probability constants.   |
//| - Keep one observable route: setup -> score -> gate -> preflight. |
//|                                                                  |
//| EXACT INSTALLATION                                                |
//| 1) Use NEXUS_v2.0.8c_AUDITPATCH_UNCOMPILED as the baseline.       |
//| 2) Copy this file to MQL5\Include\NEXUS_v1\.                     |
//| 3) In Experts\NEXUS_EA_v2.mq5, insert the following ONE line      |
//|    immediately AFTER the closing brace of NXS_UpdateIndicators()  |
//|    and BEFORE NXS_PickBestSignal():                               |
//|                                                                  |
//|       #include <NEXUS_v1\NXS_ReusePerformancePack.mqh>            |
//|                                                                  |
//| No other source edit is required. The hooks at the end of this    |
//| file affect only code appearing after the include point.          |
//|                                                                  |
//| REUSED DESIGN, ADAPTED (not copied wholesale)                     |
//| - KDX_FuzzyFilter: additive penalties + emergency-only hard gate. |
//| - KDX_EntryScore: transparent, bounded component scoring.         |
//| - KDX_MarketFilter/GROK Regime: family routing by regime.         |
//| - GoldKiller POI: fresh/touched/mitigated/broken lifecycle.       |
//| - GoldKiller/GROK patterns: closed-bar M5 rejection trigger.      |
//| - GROK AdaptiveSpread: rolling-relative spread assessment.        |
//|                                                                  |
//| IMPORTANT                                                        |
//| - All pattern decisions use CLOSED bars.                          |
//| - M15/H1 build context; M5 only triggers an already valid POI.    |
//| - IFVG is created only after a real three-candle FVG is closed    |
//|   through and later retested from the opposite side.              |
//| - Malaysian SNR uses open/close zones + independent HTF storyline;|
//|   it never requires "near H4 low" and "above H4 midpoint" at     |
//|   the same time.                                                   |
//| ROOT-CAUSE COVERAGE                                               |
//| - AUDITPATCH baseline: tester license/Web/state isolation,         |
//|   GateMode/Counter-HTF wiring, corrected FVG/IFVG/SH indexing,     |
//|   asset spread profile, broker tick-size stops and diagnostics.    |
//| - This include: one additive MTF/velocity route, adaptive spread,  |
//|   POI lifecycle, M15/H1 context + closed-M5 trigger, family score, |
//|   monetary-risk volume sizing and explicit preflight reasons.      |
//| - This source still requires compilation and Strategy Tester QA.  |
//+------------------------------------------------------------------+
#ifndef __NXS_REUSE_PERFORMANCE_PACK_MQH__
#define __NXS_REUSE_PERFORMANCE_PACK_MQH__

// -------------------------------------------------------------------
// User controls kept inside this single include
// -------------------------------------------------------------------
input group "=== NXR REUSE / PERFORMANCE PACK ==="
input bool             InpNXR_Enable                 = true;
input bool             InpNXR_DirectM5Execution      = true;
input bool             InpNXR_RespectNexusSwitches  = true;
input ENUM_TIMEFRAMES  InpNXR_TriggerTF              = PERIOD_M5;
input int              InpNXR_ContextLookbackM15     = 96;
input int              InpNXR_ContextLookbackH1      = 48;
input int              InpNXR_MaxActiveZones         = 48;
input int              InpNXR_MaxZoneTouches         = 2;
input int              InpNXR_TriggerExpiryMinutes   = 12;
input int              InpNXR_MinSecondsBetweenTrade = 120;
input double           InpNXR_MinFVGSizeATR          = 0.05;
input double           InpNXR_DisplacementATR        = 0.75;
input double           InpNXR_MinReactionQuality     = 62.0;
input double           InpNXR_MinM5Score             = 58.0;
input double           InpNXR_MinRR                   = 1.60;
input double           InpNXR_MaxEntryDriftR          = 0.35;
input bool             InpNXR_EnableCounterHTFSoft = true;
input double           InpNXR_CounterMinReactionQ   = 72.0;
input double           InpNXR_CounterLotMultiplier   = 0.40;
input bool             InpNXR_AdaptiveSpread         = true;
input double           InpNXR_SpreadSpikeRatio       = 2.40;
input double           InpNXR_HardSpreadMultiplier   = 1.60;
input double           InpNXR_HardSpreadATRMultiplier= 1.50;
input bool             InpNXR_Debug                  = false;

#define NXR_PACK_VERSION  "1.2.0"
#define NXR_ZONE_CAPACITY 64
#define NXR_REASON_MAX    240

// -------------------------------------------------------------------
// Internal models
// -------------------------------------------------------------------
enum ENUM_NXR_ZONE_TYPE
{
   NXR_ZONE_NONE = 0,
   NXR_ZONE_OB_BULL,
   NXR_ZONE_OB_BEAR,
   NXR_ZONE_FVG_BULL,
   NXR_ZONE_FVG_BEAR,
   NXR_ZONE_IFVG_BULL,
   NXR_ZONE_IFVG_BEAR,
   NXR_ZONE_BREAKER_BULL,
   NXR_ZONE_BREAKER_BEAR,
   NXR_ZONE_SNR_SUPPORT,
   NXR_ZONE_SNR_RESISTANCE
};

enum ENUM_NXR_ZONE_STATE
{
   NXR_STATE_FRESH = 0,
   NXR_STATE_TOUCHED,
   NXR_STATE_MITIGATED,
   NXR_STATE_BROKEN
};

struct SNXRZone
{
   bool                 active;
   int                  id;
   ENUM_NXR_ZONE_TYPE   type;
   ENUM_NXR_ZONE_STATE  state;
   ENUM_TIMEFRAMES      tf;
   int                  direction;       // +1 demand/bull, -1 supply/bear
   double               lower;
   double               upper;
   double               midpoint;
   double               baseStrength;
   datetime             createdAt;
   datetime             lastTouchBar;
   datetime             lastSignalBar;
   datetime             brokenAt;
   int                  touches;
   string               source;
};

struct SNXRSpreadState
{
   int       currentPts;
   double    fastAvgPts;
   double    slowAvgPts;
   double    ratioToNormal;
   double    pctOfATR;
   double    scorePenalty;
   int       samples;
   datetime lastSampleBar;
   bool      emergency;
   string    reason;
};

struct SNXRTrigger
{
   bool                 valid;
   bool                 consumed;
   datetime             formedAt;
   datetime             expiresAt;
   datetime             lastAttemptAt;
   int                  zoneId;
   ENUM_NXR_ZONE_TYPE   zoneType;
   double               reactionQuality;
   SNXSSignal           signal;
};

struct SNXRRouteResult
{
   bool                 allowed;
   ENUM_NXS_EXEC_RC     blockRc;
   double               score;
   double               threshold;
   double               lotMultiplier;
   bool                 counterHTF;
   string               trace;
};

SNXRZone        g_nxrZones[NXR_ZONE_CAPACITY];
int             g_nxrZoneCount          = 0;
int             g_nxrNextZoneId         = 1;
SNXRSpreadState g_nxrSpread;
SNXRTrigger     g_nxrTrigger;
datetime        g_nxrLastTriggerBar     = 0;
datetime        g_nxrLastContextM15Bar  = 0;
datetime        g_nxrLastContextH1Bar   = 0;
bool            g_nxrContextReady       = false;
datetime        g_nxrLastContextRetry   = 0;
string          g_nxrLastRouteTrace     = "";
string          g_nxrLastPreflight      = "";
datetime        g_nxrEntryBufferBar     = 0;
datetime        g_nxrMediumBufferBar    = 0;
double          g_nxrEntryBuffer        = 0.0;
double          g_nxrMediumBuffer       = 0.0;

// Forward declaration for the bounded startup lifecycle replay.
void NXR_ReplayHistoricalLifecycle();

// -------------------------------------------------------------------
// Generic helpers
// -------------------------------------------------------------------
double NXR_Clamp(double v, double lo, double hi)
{
   if(v < lo) return lo;
   if(v > hi) return hi;
   return v;
}

int NXR_IntClamp(int v, int lo, int hi)
{
   if(v < lo) return lo;
   if(v > hi) return hi;
   return v;
}

double NXR_TickSize()
{
   double tick = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_SIZE);
   if(tick <= 0.0) tick = g_point;
   if(tick <= 0.0) tick = _Point;
   return tick;
}

double NXR_NormalizePrice(double price)
{
   if(price <= 0.0) return price;
   double tick = NXR_TickSize();
   return NormalizeDouble(MathRound(price / tick) * tick, g_digits);
}

string NXR_AppendReason(string base, string extra)
{
   if(StringLen(extra) == 0) return base;
   string out = (StringLen(base) == 0) ? extra : base + "|" + extra;
   if(StringLen(out) > NXR_REASON_MAX)
      out = StringSubstr(out, 0, NXR_REASON_MAX);
   return out;
}

bool NXR_IsBullZone(ENUM_NXR_ZONE_TYPE t)
{
   return (t == NXR_ZONE_OB_BULL || t == NXR_ZONE_FVG_BULL ||
           t == NXR_ZONE_IFVG_BULL || t == NXR_ZONE_BREAKER_BULL ||
           t == NXR_ZONE_SNR_SUPPORT);
}

bool NXR_IsBearZone(ENUM_NXR_ZONE_TYPE t)
{
   return (t == NXR_ZONE_OB_BEAR || t == NXR_ZONE_FVG_BEAR ||
           t == NXR_ZONE_IFVG_BEAR || t == NXR_ZONE_BREAKER_BEAR ||
           t == NXR_ZONE_SNR_RESISTANCE);
}

string NXR_ZoneName(ENUM_NXR_ZONE_TYPE t)
{
   switch(t)
   {
      case NXR_ZONE_OB_BULL:         return "OB_BULL";
      case NXR_ZONE_OB_BEAR:         return "OB_BEAR";
      case NXR_ZONE_FVG_BULL:        return "FVG_BULL";
      case NXR_ZONE_FVG_BEAR:        return "FVG_BEAR";
      case NXR_ZONE_IFVG_BULL:       return "IFVG_BULL";
      case NXR_ZONE_IFVG_BEAR:       return "IFVG_BEAR";
      case NXR_ZONE_BREAKER_BULL:    return "BREAKER_BULL";
      case NXR_ZONE_BREAKER_BEAR:    return "BREAKER_BEAR";
      case NXR_ZONE_SNR_SUPPORT:     return "MSNR_SUPPORT";
      case NXR_ZONE_SNR_RESISTANCE:  return "MSNR_RESIST";
      default:                       return "NONE";
   }
}

SNXSSignal NXR_EmptySignal(string name, ENUM_NXS_STRAT strat)
{
   SNXSSignal s;
   ZeroMemory(s);
   s.dir       = DIR_NONE;
   s.strat     = strat;
   s.stratName = name;
   s.reason    = "NXR:no_closed_bar_trigger";
   return s;
}

double NXR_AverageRange(ENUM_TIMEFRAMES tf, int startShift, int count)
{
   int bars = Bars(g_sym, tf);
   if(bars <= startShift + 2) return MathMax(g_atr, g_point * 20.0);
   int n = MathMin(count, bars - startShift - 1);
   if(n <= 0) return MathMax(g_atr, g_point * 20.0);
   double sum = 0.0;
   int valid = 0;
   for(int i = startShift; i < startShift + n; i++)
   {
      double h = iHigh(g_sym, tf, i);
      double l = iLow(g_sym, tf, i);
      if(h <= 0.0 || l <= 0.0 || h <= l) continue;
      sum += h - l;
      valid++;
   }
   if(valid <= 0) return MathMax(g_atr, g_point * 20.0);
   return sum / valid;
}

double NXR_ZoneBuffer(ENUM_TIMEFRAMES tf)
{
   datetime currentBar = iTime(g_sym, tf, 0);
   if(tf == InpTFEntry && g_nxrEntryBuffer > 0.0 &&
      currentBar == g_nxrEntryBufferBar)
      return g_nxrEntryBuffer;
   if(tf == InpTFMedium && g_nxrMediumBuffer > 0.0 &&
      currentBar == g_nxrMediumBufferBar)
      return g_nxrMediumBuffer;

   double avg = NXR_AverageRange(tf, 1, 20);
   double buffer = MathMax(NXR_TickSize() * 2.0, avg * 0.04);
   if(tf == InpTFEntry)
   {
      g_nxrEntryBufferBar = currentBar;
      g_nxrEntryBuffer = buffer;
   }
   if(tf == InpTFMedium)
   {
      g_nxrMediumBufferBar = currentBar;
      g_nxrMediumBuffer = buffer;
   }
   return buffer;
}

int NXR_MaxZonesRuntime()
{
   return NXR_IntClamp(InpNXR_MaxActiveZones, 8, NXR_ZONE_CAPACITY);
}

int NXR_FindZoneById(int id)
{
   for(int i = 0; i < g_nxrZoneCount; i++)
      if(g_nxrZones[i].id == id) return i;
   return -1;
}

int NXR_FindDuplicateZone(ENUM_NXR_ZONE_TYPE type, ENUM_TIMEFRAMES tf,
                          double lower, double upper)
{
   double mid = (lower + upper) * 0.5;
   double tol = MathMax(NXR_TickSize() * 4.0, NXR_ZoneBuffer(tf));
   for(int i = 0; i < g_nxrZoneCount; i++)
   {
      // A historically broken/retired level must never absorb a genuinely
      // new zone formed at approximately the same price.
      if(!g_nxrZones[i].active || g_nxrZones[i].state == NXR_STATE_BROKEN) continue;
      if(g_nxrZones[i].type != type || g_nxrZones[i].tf != tf) continue;
      if(MathAbs(g_nxrZones[i].midpoint - mid) <= tol) return i;
   }
   return -1;
}

int NXR_WeakestReplaceIndex()
{
   int idx = -1;
   double weakest = DBL_MAX;
   for(int i = 0; i < g_nxrZoneCount; i++)
   {
      if(!g_nxrZones[i].active || g_nxrZones[i].state == NXR_STATE_BROKEN)
         return i;
      double value = g_nxrZones[i].baseStrength - g_nxrZones[i].touches * 12.0;
      if(value < weakest)
      {
         weakest = value;
         idx = i;
      }
   }
   return idx;
}

int NXR_AddZone(ENUM_NXR_ZONE_TYPE type, ENUM_TIMEFRAMES tf,
                double lower, double upper, datetime createdAt,
                double strength, string source)
{
   if(lower <= 0.0 || upper <= 0.0) return -1;
   if(lower > upper)
   {
      double tmp = lower;
      lower = upper;
      upper = tmp;
   }

   double minWidth = MathMax(NXR_TickSize() * 2.0, NXR_ZoneBuffer(tf) * 0.50);
   if((upper - lower) < minWidth)
   {
      double mid = (upper + lower) * 0.5;
      lower = mid - minWidth * 0.5;
      upper = mid + minWidth * 0.5;
   }

   lower = NXR_NormalizePrice(lower);
   upper = NXR_NormalizePrice(upper);

   int dup = NXR_FindDuplicateZone(type, tf, lower, upper);
   if(dup >= 0)
   {
      // Preserve lifecycle; refresh only structural evidence.
      g_nxrZones[dup].baseStrength = MathMax(g_nxrZones[dup].baseStrength, strength);
      // Keep the original creation time and touch history. Moving createdAt
      // forward would make an already-tested POI look fresh again.
      g_nxrZones[dup].source = source;
      return dup;
   }

   int limit = NXR_MaxZonesRuntime();
   int idx = -1;
   if(g_nxrZoneCount < limit)
   {
      idx = g_nxrZoneCount;
      g_nxrZoneCount++;
   }
   else
   {
      idx = NXR_WeakestReplaceIndex();
      if(idx < 0) return -1;
   }

   ZeroMemory(g_nxrZones[idx]);
   g_nxrZones[idx].active        = true;
   g_nxrZones[idx].id            = g_nxrNextZoneId++;
   g_nxrZones[idx].type          = type;
   g_nxrZones[idx].state         = NXR_STATE_FRESH;
   g_nxrZones[idx].tf            = tf;
   g_nxrZones[idx].direction     = NXR_IsBullZone(type) ? +1 : -1;
   g_nxrZones[idx].lower         = lower;
   g_nxrZones[idx].upper         = upper;
   g_nxrZones[idx].midpoint      = (lower + upper) * 0.5;
   g_nxrZones[idx].baseStrength  = NXR_Clamp(strength, 0.0, 100.0);
   g_nxrZones[idx].createdAt     = createdAt;
   g_nxrZones[idx].source        = source;

   if(InpNXR_Debug)
      PrintFormat("[NXR ZONE] add id=%d %s tf=%s [%.5f..%.5f] str=%.0f src=%s",
                  g_nxrZones[idx].id, NXR_ZoneName(type), EnumToString(tf),
                  lower, upper, strength, source);
   return idx;
}

// -------------------------------------------------------------------
// Adaptive spread: relative condition + asset profile + ATR
// -------------------------------------------------------------------
void NXR_UpdateSpreadState()
{
   int sp = (int)SymbolInfoInteger(g_sym, SYMBOL_SPREAD);
   if(sp <= 0)
   {
      MqlTick tick;
      if(SymbolInfoTick(g_sym, tick) && g_point > 0.0)
         sp = (int)MathRound((tick.ask - tick.bid) / g_point);
   }
   if(sp <= 0) return;

   g_nxrSpread.currentPts = sp;
   datetime minuteBar = iTime(g_sym, PERIOD_M1, 0);
   if(minuteBar <= 0) minuteBar = TimeCurrent() - (TimeCurrent() % 60);

   if(g_nxrSpread.samples == 0)
   {
      g_nxrSpread.fastAvgPts = sp;
      g_nxrSpread.slowAvgPts = sp;
      g_nxrSpread.samples = 1;
      g_nxrSpread.lastSampleBar = minuteBar;
   }
   else if(minuteBar != g_nxrSpread.lastSampleBar)
   {
      g_nxrSpread.fastAvgPts = g_nxrSpread.fastAvgPts * 0.80 + sp * 0.20;
      g_nxrSpread.slowAvgPts = g_nxrSpread.slowAvgPts * 0.96 + sp * 0.04;
      g_nxrSpread.samples++;
      g_nxrSpread.lastSampleBar = minuteBar;
   }

   double normal = MathMax(1.0, g_nxrSpread.slowAvgPts);
   g_nxrSpread.ratioToNormal = sp / normal;
   g_nxrSpread.pctOfATR = (g_atr > 0.0)
                          ? ((sp * g_point) / g_atr) * 100.0
                          : 0.0;

   double p = 0.0;
   if(g_nxrSpread.ratioToNormal > 1.15)
      p += NXR_Clamp((g_nxrSpread.ratioToNormal - 1.15) * 8.0, 0.0, 10.0);

   double atrCap = NXS_SpreadCapATRPct();
   if(atrCap > 0.0 && g_nxrSpread.pctOfATR > atrCap * 0.75)
      p += NXR_Clamp((g_nxrSpread.pctOfATR / atrCap - 0.75) * 8.0, 0.0, 8.0);

   int profileCap = InpMaxSpreadPoints;
   if(profileCap <= 0) profileCap = g_profile.maxSpreadPts;
   if(profileCap > 0 && sp > profileCap)
      p += NXR_Clamp(((double)sp / profileCap - 1.0) * 10.0, 0.0, 8.0);

   g_nxrSpread.scorePenalty = NXR_Clamp(p, 0.0, 14.0);
   g_nxrSpread.emergency = false;
   g_nxrSpread.reason = "OK";

   int explicitHard = InpHardMaxSpreadPts;
   double hardAbs = 0.0;
   if(explicitHard > 0)
      hardAbs = explicitHard;
   else if(profileCap > 0)
      hardAbs = profileCap * MathMax(1.05, InpNXR_HardSpreadMultiplier);

   if(hardAbs > 0.0 && sp > hardAbs)
   {
      g_nxrSpread.emergency = true;
      g_nxrSpread.reason = StringFormat("ABS_EMERGENCY %d>%.0f", sp, hardAbs);
   }
   else if(g_nxrSpread.samples >= 5 &&
           g_nxrSpread.ratioToNormal > MathMax(1.20, InpNXR_SpreadSpikeRatio))
   {
      g_nxrSpread.emergency = true;
      g_nxrSpread.reason = StringFormat("REL_SPIKE %.2fx", g_nxrSpread.ratioToNormal);
   }
   else if(atrCap > 0.0 && g_nxrSpread.pctOfATR >
           atrCap * MathMax(1.05, InpNXR_HardSpreadATRMultiplier))
   {
      g_nxrSpread.emergency = true;
      g_nxrSpread.reason = StringFormat("ATR_EMERGENCY %.1f%%", g_nxrSpread.pctOfATR);
   }
}

bool NXR_SpreadOK()
{
   if(!InpNXR_Enable) return NXS_SpreadOK();
   if(!InpUseDynamicSpread) return true;
   if(!InpNXR_AdaptiveSpread) return NXS_SpreadOK();
   NXR_UpdateSpreadState();
   if(InpNXR_Debug && g_nxrSpread.emergency)
      PrintFormat("[NXR SPREAD] blocked %s sp=%d normal=%.1f ratio=%.2f atr=%.1f%%",
                  g_nxrSpread.reason, g_nxrSpread.currentPts,
                  g_nxrSpread.slowAvgPts, g_nxrSpread.ratioToNormal,
                  g_nxrSpread.pctOfATR);
   return !g_nxrSpread.emergency;
}

// -------------------------------------------------------------------
// Context detection: real 3-candle FVG, displacement OB, MSNR body zone
// -------------------------------------------------------------------
double NXR_LocalHigh(ENUM_TIMEFRAMES tf, int firstShift, int count)
{
   double v = -DBL_MAX;
   for(int i = firstShift; i < firstShift + count; i++)
      v = MathMax(v, iHigh(g_sym, tf, i));
   return v;
}

double NXR_LocalLow(ENUM_TIMEFRAMES tf, int firstShift, int count)
{
   double v = DBL_MAX;
   for(int i = firstShift; i < firstShift + count; i++)
      v = MathMin(v, iLow(g_sym, tf, i));
   return v;
}

void NXR_ScanContextTF(ENUM_TIMEFRAMES tf, int lookback, bool fullScan)
{
   int bars = Bars(g_sym, tf);
   if(bars < 10) return;

   int requested = NXR_IntClamp(lookback, 8, 300);
   int maxShift = fullScan ? MathMin(requested, bars - 5) : MathMin(7, bars - 5);
   if(maxShift < 2) return;

   double avg = NXR_AverageRange(tf, 1, 20);
   double minGap = MathMax(NXR_TickSize() * 2.0,
                           avg * MathMax(0.01, InpNXR_MinFVGSizeATR));
   double minDisp = avg * MathMax(0.30, InpNXR_DisplacementATR);
   double tfBonus = (tf == PERIOD_H1 || tf == InpTFMedium) ? 5.0 : 0.0;

   for(int s = maxShift; s >= 2; s--)
   {
      int older  = s + 1;
      int middle = s;
      int newer  = s - 1;

      double oldH = iHigh(g_sym, tf, older);
      double oldL = iLow (g_sym, tf, older);
      double midH = iHigh(g_sym, tf, middle);
      double midL = iLow (g_sym, tf, middle);
      double newH = iHigh(g_sym, tf, newer);
      double newL = iLow (g_sym, tf, newer);
      double midRange = midH - midL;
      // A zone becomes tradable only after the newest confirmation candle has
      // closed. Store activation time, not the middle/base candle time.
      datetime activationTime = iTime(g_sym, tf, newer) + PeriodSeconds(tf);

      // Three-candle FVG: compare candle 1 and candle 3 around the middle.
      if(newL > oldH + minGap && (midRange >= avg * 0.55 || (newL - oldH) >= avg * 0.10))
      {
         double strength = 61.0 + tfBonus +
                           NXR_Clamp(((newL - oldH) / MathMax(avg, g_point)) * 40.0, 0.0, 12.0);
         NXR_AddZone(NXR_ZONE_FVG_BULL, tf, oldH, newL, activationTime,
                     strength, "3C_FVG+DISP");
      }
      if(newH < oldL - minGap && (midRange >= avg * 0.55 || (oldL - newH) >= avg * 0.10))
      {
         double strength = 61.0 + tfBonus +
                           NXR_Clamp(((oldL - newH) / MathMax(avg, g_point)) * 40.0, 0.0, 12.0);
         NXR_AddZone(NXR_ZONE_FVG_BEAR, tf, newH, oldL, activationTime,
                     strength, "3C_FVG+DISP");
      }

      // Order block: opposite candle immediately before displacement and
      // preferably a close through a local structural level.
      double o0 = iOpen (g_sym, tf, s);
      double c0 = iClose(g_sym, tf, s);
      double h0 = iHigh (g_sym, tf, s);
      double l0 = iLow  (g_sym, tf, s);
      double o1 = iOpen (g_sym, tf, s - 1);
      double c1 = iClose(g_sym, tf, s - 1);
      double h1 = iHigh (g_sym, tf, s - 1);
      double l1 = iLow  (g_sym, tf, s - 1);
      double moveRange = h1 - l1;
      double moveBody  = MathAbs(c1 - o1);
      bool displacement = (moveRange >= minDisp && moveBody >= moveRange * 0.50);
      double priorHigh = NXR_LocalHigh(tf, s + 1, 3);
      double priorLow  = NXR_LocalLow (tf, s + 1, 3);

      if(c0 < o0 && c1 > o1 && displacement && c1 > h0)
      {
         bool bos = (c1 > priorHigh);
         double strength = 66.0 + tfBonus + (bos ? 8.0 : 0.0);
         NXR_AddZone(NXR_ZONE_OB_BULL, tf, MathMin(o0, c0), MathMax(o0, c0),
                     iTime(g_sym, tf, s - 1) + PeriodSeconds(tf), strength,
                     bos ? "LAST_DOWN+DISP+BOS" : "LAST_DOWN+DISP");
      }
      if(c0 > o0 && c1 < o1 && displacement && c1 < l0)
      {
         bool bos = (c1 < priorLow);
         double strength = 66.0 + tfBonus + (bos ? 8.0 : 0.0);
         NXR_AddZone(NXR_ZONE_OB_BEAR, tf, MathMin(o0, c0), MathMax(o0, c0),
                     iTime(g_sym, tf, s - 1) + PeriodSeconds(tf), strength,
                     bos ? "LAST_UP+DISP+BOS" : "LAST_UP+DISP");
      }

      // Malaysian SNR: open/close transition zone, not wick level.
      // A local V/A close-shape is required to avoid creating a zone at every
      // colour change. Storyline is evaluated later and remains independent.
      if(s >= 3)
      {
         double prevClose = iClose(g_sym, tf, s + 1);
         double nextClose = iClose(g_sym, tf, s - 1);
         double levelA = c0;
         double levelB = o1;
         double bodyLevel = (levelA + levelB) * 0.5;
         double halfWidth = MathMax(NXR_TickSize() * 2.0, avg * 0.035);

         bool supportTurn = (c0 < o0 && c1 > o1 &&
                             bodyLevel <= prevClose && bodyLevel <= nextClose);
         bool resistTurn  = (c0 > o0 && c1 < o1 &&
                             bodyLevel >= prevClose && bodyLevel >= nextClose);
         if(supportTurn)
            NXR_AddZone(NXR_ZONE_SNR_SUPPORT, tf,
                        bodyLevel - halfWidth, bodyLevel + halfWidth,
                        iTime(g_sym, tf, s - 1) + PeriodSeconds(tf), 58.0 + tfBonus,
                        "MSNR_OPEN_CLOSE_V");
         if(resistTurn)
            NXR_AddZone(NXR_ZONE_SNR_RESISTANCE, tf,
                        bodyLevel - halfWidth, bodyLevel + halfWidth,
                        iTime(g_sym, tf, s - 1) + PeriodSeconds(tf), 58.0 + tfBonus,
                        "MSNR_OPEN_CLOSE_A");
      }
   }
}

void NXR_RebuildContextIfNeeded()
{
   if(!InpNXR_Enable) return;
   if(g_nxrContextReady) return;

   datetime now = TimeCurrent();
   if(g_nxrLastContextRetry > 0 && now - g_nxrLastContextRetry < 5) return;
   g_nxrLastContextRetry = now;

   int needEntry = MathMax(10, MathMin(300, MathMax(8, InpNXR_ContextLookbackM15) + 5));
   int needMedium= MathMax(10, MathMin(300, MathMax(8, InpNXR_ContextLookbackH1)  + 5));

   g_nxrZoneCount = 0;
   g_nxrNextZoneId = 1;
   NXR_ScanContextTF(InpTFEntry, InpNXR_ContextLookbackM15, true);
   NXR_ScanContextTF(InpTFMedium, InpNXR_ContextLookbackH1, true);
   NXR_ReplayHistoricalLifecycle();
   g_nxrLastContextM15Bar = iTime(g_sym, InpTFEntry, 0);
   g_nxrLastContextH1Bar  = iTime(g_sym, InpTFMedium, 0);

   // Do not freeze a partial 10-bar initialization when the terminal is still
   // synchronizing history. The retry is throttled, so no per-tick full scan.
   int entryBars  = Bars(g_sym, InpTFEntry);
   int mediumBars = Bars(g_sym, InpTFMedium);
   bool entrySync  = (bool)SeriesInfoInteger(g_sym, InpTFEntry,  SERIES_SYNCHRONIZED);
   bool mediumSync = (bool)SeriesInfoInteger(g_sym, InpTFMedium, SERIES_SYNCHRONIZED);
   bool requestedHistory = (entryBars >= needEntry && mediumBars >= needMedium);
   bool terminalComplete = (entrySync && mediumSync && entryBars >= 10 && mediumBars >= 10);
   g_nxrContextReady = (requestedHistory || terminalComplete);

   if(InpNXR_Debug)
      PrintFormat("[NXR] context scan zones=%d ready=%s bars=%d/%d need=%d/%d sync=%d/%d",
                  g_nxrZoneCount, g_nxrContextReady ? "YES" : "NO",
                  entryBars, mediumBars, needEntry, needMedium,
                  (int)entrySync, (int)mediumSync);
}

void NXR_RefreshContext()
{
   if(!InpNXR_Enable) return;
   NXR_RebuildContextIfNeeded();

   datetime m15 = iTime(g_sym, InpTFEntry, 0);
   if(m15 > 0 && m15 != g_nxrLastContextM15Bar)
   {
      g_nxrLastContextM15Bar = m15;
      NXR_ScanContextTF(InpTFEntry, 8, false);
   }

   datetime h1 = iTime(g_sym, InpTFMedium, 0);
   if(h1 > 0 && h1 != g_nxrLastContextH1Bar)
   {
      g_nxrLastContextH1Bar = h1;
      NXR_ScanContextTF(InpTFMedium, 8, false);
   }
}

// -------------------------------------------------------------------
// Zone lifecycle: FVG->IFVG, OB->breaker, SNR flip
// -------------------------------------------------------------------
void NXR_SpawnInverseFromBroken(SNXRZone &z, datetime breakBar)
{
   ENUM_NXR_ZONE_TYPE inverse = NXR_ZONE_NONE;
   string src = "";

   if(z.type == NXR_ZONE_FVG_BULL)
   {
      inverse = NXR_ZONE_IFVG_BEAR;
      src = "BULL_FVG_INVALIDATED";
   }
   else if(z.type == NXR_ZONE_FVG_BEAR)
   {
      inverse = NXR_ZONE_IFVG_BULL;
      src = "BEAR_FVG_INVALIDATED";
   }
   else if(z.type == NXR_ZONE_OB_BULL)
   {
      inverse = NXR_ZONE_BREAKER_BEAR;
      src = "BULL_OB_BROKEN";
   }
   else if(z.type == NXR_ZONE_OB_BEAR)
   {
      inverse = NXR_ZONE_BREAKER_BULL;
      src = "BEAR_OB_BROKEN";
   }
   else if(z.type == NXR_ZONE_SNR_SUPPORT)
   {
      inverse = NXR_ZONE_SNR_RESISTANCE;
      src = "SBR_FLIP";
   }
   else if(z.type == NXR_ZONE_SNR_RESISTANCE)
   {
      inverse = NXR_ZONE_SNR_SUPPORT;
      src = "RBS_FLIP";
   }

   if(inverse != NXR_ZONE_NONE)
      NXR_AddZone(inverse, z.tf, z.lower, z.upper, breakBar,
                  MathMax(54.0, z.baseStrength - 4.0), src);
}

void NXR_ProcessZoneBreaksOnClosedBar(ENUM_TIMEFRAMES tf)
{
   datetime barTime = iTime(g_sym, tf, 1);
   int tfSeconds = PeriodSeconds(tf);
   if(tfSeconds <= 0) tfSeconds = 60;
   datetime barClose = barTime + tfSeconds;
   double close1 = iClose(g_sym, tf, 1);
   if(barTime <= 0 || close1 <= 0.0) return;

   int snapshotCount = g_nxrZoneCount;
   for(int i = 0; i < snapshotCount; i++)
   {
      if(!g_nxrZones[i].active) continue;
      // The closed bar is valid when its close occurs after zone activation.
      // This permits the first M5 retest after an M15/H1 close without using
      // information that was unavailable at the start of that M5 bar.
      if(barClose <= g_nxrZones[i].createdAt) continue;

      double buffer = MathMax(NXR_TickSize() * 2.0,
                              NXR_ZoneBuffer(g_nxrZones[i].tf) * 0.50);
      bool broken = false;
      if(g_nxrZones[i].direction > 0 && close1 < g_nxrZones[i].lower - buffer)
         broken = true;
      if(g_nxrZones[i].direction < 0 && close1 > g_nxrZones[i].upper + buffer)
         broken = true;

      if(!broken) continue;
      SNXRZone oldZone = g_nxrZones[i];
      g_nxrZones[i].state = NXR_STATE_BROKEN;
      g_nxrZones[i].active = false;
      g_nxrZones[i].brokenAt = barClose;
      // The inverse/breaker becomes active only after the invalidating bar
      // closes, so that bar cannot double as its own retest.
      NXR_SpawnInverseFromBroken(oldZone, barClose);

      if(InpNXR_Debug)
         PrintFormat("[NXR ZONE] broken id=%d %s close=%.5f",
                     oldZone.id, NXR_ZoneName(oldZone.type), close1);
   }
}

bool NXR_BarIntersectsZone(ENUM_TIMEFRAMES tf, int shift, SNXRZone &z)
{
   double h = iHigh(g_sym, tf, shift);
   double l = iLow (g_sym, tf, shift);
   double tol = MathMax(NXR_TickSize(), NXR_ZoneBuffer(z.tf) * 0.20);
   return (h >= z.lower - tol && l <= z.upper + tol);
}

void NXR_RegisterZoneTouches(ENUM_TIMEFRAMES tf)
{
   datetime barTime = iTime(g_sym, tf, 1);
   int tfSeconds = PeriodSeconds(tf);
   if(tfSeconds <= 0) tfSeconds = 60;
   datetime barClose = barTime + tfSeconds;
   if(barTime <= 0) return;

   for(int i = 0; i < g_nxrZoneCount; i++)
   {
      if(!g_nxrZones[i].active) continue;
      if(barClose <= g_nxrZones[i].createdAt) continue;
      if(g_nxrZones[i].lastTouchBar == barTime) continue;
      if(!NXR_BarIntersectsZone(tf, 1, g_nxrZones[i])) continue;

      g_nxrZones[i].lastTouchBar = barTime;
      g_nxrZones[i].touches++;
      if(g_nxrZones[i].touches == 1)
         g_nxrZones[i].state = NXR_STATE_TOUCHED;
      else
         g_nxrZones[i].state = NXR_STATE_MITIGATED;

      if(g_nxrZones[i].touches > MathMax(1, InpNXR_MaxZoneTouches) + 1)
         g_nxrZones[i].active = false;
   }
}

void NXR_ReplayHistoricalLifecycle()
{
   if(g_nxrZoneCount <= 0) return;

   int bars = Bars(g_sym, InpNXR_TriggerTF);
   if(bars < 4) return;
   int tfSeconds = PeriodSeconds(InpNXR_TriggerTF);
   if(tfSeconds <= 0) tfSeconds = 60;

   datetime earliest = 0;
   for(int i = 0; i < g_nxrZoneCount; i++)
   {
      if(g_nxrZones[i].createdAt <= 0) continue;
      if(earliest == 0 || g_nxrZones[i].createdAt < earliest)
         earliest = g_nxrZones[i].createdAt;
   }
   if(earliest <= 0) return;

   int oldestShift = iBarShift(g_sym, InpNXR_TriggerTF, earliest, false);
   if(oldestShift < 2) return;
   // Bounded startup work: 5,000 M5 bars are roughly 17 days and still only
   // ~320k zone checks at the hard 64-zone capacity. Normal defaults replay
   // about 48 hours.
   oldestShift = MathMin(oldestShift, MathMin(bars - 2, 5000));

   int replayed = 0;
   for(int shift = oldestShift; shift >= 2; shift--)
   {
      datetime barTime = iTime(g_sym, InpNXR_TriggerTF, shift);
      if(barTime <= 0) continue;
      datetime barClose = barTime + tfSeconds;
      double h = iHigh (g_sym, InpNXR_TriggerTF, shift);
      double l = iLow  (g_sym, InpNXR_TriggerTF, shift);
      double c = iClose(g_sym, InpNXR_TriggerTF, shift);
      if(h <= 0.0 || l <= 0.0 || c <= 0.0 || h < l) continue;

      // Snapshot prevents an IFVG/breaker spawned at this close from being
      // touched or broken by its own invalidation candle.
      int snapshotCount = g_nxrZoneCount;
      for(int i = 0; i < snapshotCount; i++)
      {
         if(!g_nxrZones[i].active) continue;
         if(barClose <= g_nxrZones[i].createdAt) continue;

         double buffer = MathMax(NXR_TickSize() * 2.0,
                                 NXR_ZoneBuffer(g_nxrZones[i].tf) * 0.50);
         bool broken = (g_nxrZones[i].direction > 0 &&
                        c < g_nxrZones[i].lower - buffer) ||
                       (g_nxrZones[i].direction < 0 &&
                        c > g_nxrZones[i].upper + buffer);
         if(broken)
         {
            SNXRZone oldZone = g_nxrZones[i];
            g_nxrZones[i].state = NXR_STATE_BROKEN;
            g_nxrZones[i].active = false;
            g_nxrZones[i].brokenAt = barClose;
            NXR_SpawnInverseFromBroken(oldZone, barClose);
            continue;
         }

         double tol = MathMax(NXR_TickSize(),
                              NXR_ZoneBuffer(g_nxrZones[i].tf) * 0.20);
         bool intersects = (h >= g_nxrZones[i].lower - tol &&
                            l <= g_nxrZones[i].upper + tol);
         if(!intersects || g_nxrZones[i].lastTouchBar == barTime) continue;

         g_nxrZones[i].lastTouchBar = barTime;
         g_nxrZones[i].touches++;
         g_nxrZones[i].state = (g_nxrZones[i].touches == 1)
                               ? NXR_STATE_TOUCHED
                               : NXR_STATE_MITIGATED;
         if(g_nxrZones[i].touches > MathMax(1, InpNXR_MaxZoneTouches) + 1)
            g_nxrZones[i].active = false;
      }
      replayed++;
   }

   if(InpNXR_Debug)
      PrintFormat("[NXR] lifecycle replay bars=%d zones=%d oldestShift=%d",
                  replayed, g_nxrZoneCount, oldestShift);
}

double NXR_ZoneStrength(SNXRZone &z)
{
   double s = z.baseStrength;
   s -= z.touches * 8.0;

   int age = iBarShift(g_sym, z.tf, z.createdAt, false);
   if(age > 80)  s -= 5.0;
   if(age > 160) s -= 7.0;
   if(z.state == NXR_STATE_MITIGATED) s -= 7.0;
   if(z.state == NXR_STATE_BROKEN || !z.active) s = 0.0;
   return NXR_Clamp(s, 0.0, 100.0);
}

bool NXR_InCorrectPDHalf(int direction, double price)
{
   int bars = Bars(g_sym, InpTFMedium);
   if(bars < 30) return false;
   int hiShift = iHighest(g_sym, InpTFMedium, MODE_HIGH, 24, 1);
   int loShift = iLowest (g_sym, InpTFMedium, MODE_LOW,  24, 1);
   if(hiShift < 0 || loShift < 0) return false;
   double hi = iHigh(g_sym, InpTFMedium, hiShift);
   double lo = iLow (g_sym, InpTFMedium, loShift);
   if(hi <= lo) return false;
   double eq = (hi + lo) * 0.5;
   if(direction > 0) return price <= eq;  // buy in discount
   return price >= eq;                    // sell in premium
}

// -------------------------------------------------------------------
// Closed M5 reaction detector (rejection / engulf / sweep-reclaim)
// -------------------------------------------------------------------
double NXR_ReactionQuality(ENUM_TIMEFRAMES tf, int shift, int direction,
                           SNXRZone &z, bool &sweepReclaim,
                           bool &engulfing, bool &rejection)
{
   sweepReclaim = false;
   engulfing = false;
   rejection = false;

   double o = iOpen (g_sym, tf, shift);
   double h = iHigh (g_sym, tf, shift);
   double l = iLow  (g_sym, tf, shift);
   double c = iClose(g_sym, tf, shift);
   double po = iOpen (g_sym, tf, shift + 1);
   double pc = iClose(g_sym, tf, shift + 1);
   double range = h - l;
   if(range <= 0.0) return 0.0;

   double body = MathAbs(c - o);
   double upperWick = h - MathMax(o, c);
   double lowerWick = MathMin(o, c) - l;
   double closeLocation = (c - l) / range;
   double buffer = MathMax(NXR_TickSize(), NXR_ZoneBuffer(z.tf) * 0.20);
   double q = 30.0;

   if(direction > 0)
   {
      engulfing = (c > o && pc < po && c >= po && o <= pc);
      sweepReclaim = (l < z.lower - buffer && c > z.lower);
      rejection = (c > o && closeLocation >= 0.60 &&
                   lowerWick >= MathMax(body * 0.65, range * 0.18));
      if(c <= o && !sweepReclaim) return 0.0;
      if(closeLocation >= 0.72) q += 12.0;
      else if(closeLocation >= 0.60) q += 7.0;
      if(lowerWick >= body * 1.20) q += 15.0;
      else if(lowerWick >= body * 0.65) q += 9.0;
   }
   else
   {
      engulfing = (c < o && pc > po && c <= po && o >= pc);
      sweepReclaim = (h > z.upper + buffer && c < z.upper);
      rejection = (c < o && closeLocation <= 0.40 &&
                   upperWick >= MathMax(body * 0.65, range * 0.18));
      if(c >= o && !sweepReclaim) return 0.0;
      if(closeLocation <= 0.28) q += 12.0;
      else if(closeLocation <= 0.40) q += 7.0;
      if(upperWick >= body * 1.20) q += 15.0;
      else if(upperWick >= body * 0.65) q += 9.0;
   }

   if(body / range >= 0.55) q += 8.0;
   if(engulfing) q += 14.0;
   if(sweepReclaim) q += 16.0;
   if(rejection) q += 6.0;
   if(!(engulfing || sweepReclaim || rejection)) return 0.0;
   return NXR_Clamp(q, 0.0, 100.0);
}

string NXR_StrategyNameForZone(ENUM_NXR_ZONE_TYPE type)
{
   if(type == NXR_ZONE_IFVG_BULL || type == NXR_ZONE_IFVG_BEAR)
      return "IFVG";
   if(type == NXR_ZONE_FVG_BULL || type == NXR_ZONE_FVG_BEAR)
      return "FVG_MIT";
   if(type == NXR_ZONE_OB_BULL || type == NXR_ZONE_OB_BEAR ||
      type == NXR_ZONE_BREAKER_BULL || type == NXR_ZONE_BREAKER_BEAR)
      return "OB_MIT";
   if(type == NXR_ZONE_SNR_SUPPORT || type == NXR_ZONE_SNR_RESISTANCE)
      return "MALAYSIAN_SNR";
   return "STRUCT_REACT";
}

ENUM_NXS_STRAT NXR_StratEnumForZone(ENUM_NXR_ZONE_TYPE type)
{
   if(type == NXR_ZONE_OB_BULL || type == NXR_ZONE_OB_BEAR ||
      type == NXR_ZONE_BREAKER_BULL || type == NXR_ZONE_BREAKER_BEAR)
      return STRAT_ORDER_BLOCK;
   if(type == NXR_ZONE_FVG_BULL || type == NXR_ZONE_FVG_BEAR ||
      type == NXR_ZONE_IFVG_BULL || type == NXR_ZONE_IFVG_BEAR)
      return STRAT_FVG_CONT;
   return STRAT_STRUCT_REACT;
}

bool NXR_ZoneStrategyEnabled(ENUM_NXR_ZONE_TYPE type)
{
   if(!InpNXR_RespectNexusSwitches) return true;
   if(type == NXR_ZONE_IFVG_BULL || type == NXR_ZONE_IFVG_BEAR)
      return InpStrat_IFVG;
   if(type == NXR_ZONE_FVG_BULL || type == NXR_ZONE_FVG_BEAR)
      return InpStrat_FVG_Mit;
   if(type == NXR_ZONE_OB_BULL || type == NXR_ZONE_OB_BEAR ||
      type == NXR_ZONE_BREAKER_BULL || type == NXR_ZONE_BREAKER_BEAR)
      return InpStrat_OB_Mit;
   if(type == NXR_ZONE_SNR_SUPPORT || type == NXR_ZONE_SNR_RESISTANCE)
      return InpStrat_MalaysianSNR;
   return true;
}

double NXR_FindTargetLiquidity(int direction, double entry, double risk)
{
   if(risk <= 0.0) return entry;
   double rrTarget = (direction > 0)
                     ? entry + risk * MathMax(1.10, InpNXR_MinRR)
                     : entry - risk * MathMax(1.10, InpNXR_MinRR);

   double candidates[4];
   candidates[0] = (direction > 0) ? iHigh(g_sym, PERIOD_D1, 1)
                                    : iLow (g_sym, PERIOD_D1, 1);
   candidates[1] = (direction > 0) ? g_struct.lastSwingHigh
                                    : g_struct.lastSwingLow;
   int extShift = (direction > 0)
                  ? iHighest(g_sym, InpTFMedium, MODE_HIGH, 24, 1)
                  : iLowest (g_sym, InpTFMedium, MODE_LOW,  24, 1);
   candidates[2] = (extShift >= 0)
                   ? ((direction > 0) ? iHigh(g_sym, InpTFMedium, extShift)
                                      : iLow (g_sym, InpTFMedium, extShift))
                   : 0.0;
   candidates[3] = (direction > 0) ? iHigh(g_sym, PERIOD_W1, 1)
                                    : iLow (g_sym, PERIOD_W1, 1);

   double chosen = rrTarget;
   double maxDistance = risk * 4.0;
   if(direction > 0)
   {
      double nearest = DBL_MAX;
      for(int i = 0; i < 4; i++)
      {
         if(candidates[i] < rrTarget || candidates[i] > entry + maxDistance) continue;
         if(candidates[i] < nearest) nearest = candidates[i];
      }
      if(nearest != DBL_MAX) chosen = nearest;
   }
   else
   {
      double nearest = -DBL_MAX;
      for(int i = 0; i < 4; i++)
      {
         if(candidates[i] > rrTarget || candidates[i] < entry - maxDistance) continue;
         if(candidates[i] > nearest) nearest = candidates[i];
      }
      if(nearest != -DBL_MAX) chosen = nearest;
   }
   return chosen;
}

SNXSSignal NXR_BuildSignalFromZone(SNXRZone &z, double reactionQ,
                                    bool sweepReclaim, bool engulfing,
                                    bool rejection)
{
   string name = NXR_StrategyNameForZone(z.type);
   SNXSSignal sig = NXR_EmptySignal(name, NXR_StratEnumForZone(z.type));
   int direction = z.direction;

   MqlTick tick;
   if(!SymbolInfoTick(g_sym, tick)) return sig;
   double entry = (direction > 0) ? tick.ask : tick.bid;
   if(entry <= 0.0) return sig;

   double zoneStrength = NXR_ZoneStrength(z);
   double sourceBonus = 0.0;
   if(z.type == NXR_ZONE_IFVG_BULL || z.type == NXR_ZONE_IFVG_BEAR) sourceBonus = 5.0;
   if(z.type == NXR_ZONE_BREAKER_BULL || z.type == NXR_ZONE_BREAKER_BEAR) sourceBonus = 4.0;
   if(z.tf == InpTFMedium) sourceBonus += 4.0;
   if(z.state == NXR_STATE_FRESH) sourceBonus += 5.0;
   if(NXR_InCorrectPDHalf(direction, z.midpoint)) sourceBonus += 4.0;
   if(sweepReclaim) sourceBonus += 4.0;

   // Weighted and bounded: setup validity exists before this score is used.
   double score = 30.0 + zoneStrength * 0.28 + reactionQ * 0.28 + sourceBonus;
   score = NXR_Clamp(score, 0.0, 92.0);

   double spreadPrice = MathMax(0, g_nxrSpread.currentPts) * g_point;
   double buffer = MathMax(NXR_ZoneBuffer(z.tf) * 0.65,
                           MathMax(spreadPrice * 1.40, NXR_TickSize() * 3.0));
   double barLow  = iLow (g_sym, InpNXR_TriggerTF, 1);
   double barHigh = iHigh(g_sym, InpNXR_TriggerTF, 1);
   double sl = 0.0;
   if(direction > 0)
      sl = MathMin(z.lower, barLow) - buffer;
   else
      sl = MathMax(z.upper, barHigh) + buffer;

   double risk = MathAbs(entry - sl);
   double fallbackRisk = MathMax(g_atr * 0.80, NXR_ZoneBuffer(z.tf) * 3.0);
   if(risk <= NXR_TickSize() * 2.0 ||
      (direction > 0 && sl >= entry) ||
      (direction < 0 && sl <= entry))
   {
      sl = (direction > 0) ? entry - fallbackRisk : entry + fallbackRisk;
      risk = MathAbs(entry - sl);
   }

   double tp = NXR_FindTargetLiquidity(direction, entry, risk);
   sig.dir       = (direction > 0) ? DIR_BUY : DIR_SELL;
   sig.score     = score;
   sig.entryRef  = entry;
   sig.slPrice   = NXR_NormalizePrice(sl);
   sig.tpPrice   = NXR_NormalizePrice(tp);
   sig.reason    = StringFormat("NXR_M5:%s:id=%d:state=%d:touch=%d:Z=%.0f:R=%.0f:%s%s%s",
                                NXR_ZoneName(z.type), z.id, (int)z.state, z.touches,
                                zoneStrength, reactionQ,
                                sweepReclaim ? "SWEEP," : "",
                                engulfing ? "ENGULF," : "",
                                rejection ? "REJECT" : "");
   return sig;
}

void NXR_InvalidateExpiredTrigger()
{
   if(!g_nxrTrigger.valid) return;
   if(g_nxrTrigger.consumed || TimeCurrent() > g_nxrTrigger.expiresAt)
   {
      g_nxrTrigger.valid = false;
      g_nxrTrigger.consumed = true;
   }
}

void NXR_DetectClosedBarTrigger()
{
   NXR_InvalidateExpiredTrigger();
   datetime barTime = iTime(g_sym, InpNXR_TriggerTF, 1);
   int tfSeconds = PeriodSeconds(InpNXR_TriggerTF);
   if(tfSeconds <= 0) tfSeconds = 60;
   datetime barClose = barTime + tfSeconds;
   if(barTime <= 0) return;

   int bestIdx = -1;
   double bestScore = -DBL_MAX;
   double bestQ = 0.0;
   bool bestSweep = false, bestEngulf = false, bestReject = false;

   for(int i = 0; i < g_nxrZoneCount; i++)
   {
      if(!g_nxrZones[i].active || g_nxrZones[i].state == NXR_STATE_BROKEN) continue;
      if(!NXR_ZoneStrategyEnabled(g_nxrZones[i].type)) continue;
      if(g_nxrZones[i].touches > MathMax(1, InpNXR_MaxZoneTouches)) continue;
      if(g_nxrZones[i].createdAt >= barClose) continue;
      if(g_nxrZones[i].lastSignalBar == barTime) continue;
      if(!NXR_BarIntersectsZone(InpNXR_TriggerTF, 1, g_nxrZones[i])) continue;

      bool sweep = false, engulf = false, reject = false;
      double q = NXR_ReactionQuality(InpNXR_TriggerTF, 1,
                                     g_nxrZones[i].direction,
                                     g_nxrZones[i], sweep, engulf, reject);
      if(q < InpNXR_MinReactionQuality) continue;

      double rank = NXR_ZoneStrength(g_nxrZones[i]) * 0.55 + q * 0.45;
      if(g_nxrZones[i].state == NXR_STATE_FRESH) rank += 5.0;
      if(g_nxrZones[i].tf == InpTFMedium) rank += 3.0;
      if(sweep) rank += 4.0;

      if(rank > bestScore)
      {
         bestScore = rank;
         bestIdx = i;
         bestQ = q;
         bestSweep = sweep;
         bestEngulf = engulf;
         bestReject = reject;
      }
   }

   if(bestIdx < 0) return;

   SNXSSignal sig = NXR_BuildSignalFromZone(g_nxrZones[bestIdx], bestQ,
                                             bestSweep, bestEngulf, bestReject);
   if(sig.dir == DIR_NONE) return;

   g_nxrZones[bestIdx].lastSignalBar = barTime;
   ZeroMemory(g_nxrTrigger);
   g_nxrTrigger.valid           = true;
   g_nxrTrigger.consumed        = false;
   g_nxrTrigger.formedAt        = TimeCurrent();
   int expiryMin = MathMax(1, InpNXR_TriggerExpiryMinutes);
   if(!InpNXR_DirectM5Execution)
   {
      int entryMinutes = (int)MathCeil((double)PeriodSeconds(InpTFEntry) / 60.0);
      expiryMin = MathMax(expiryMin, entryMinutes);
   }
   g_nxrTrigger.expiresAt       = TimeCurrent() + expiryMin * 60;
   g_nxrTrigger.zoneId          = g_nxrZones[bestIdx].id;
   g_nxrTrigger.zoneType        = g_nxrZones[bestIdx].type;
   g_nxrTrigger.reactionQuality = bestQ;
   g_nxrTrigger.signal          = sig;

   NXS_Stats_RecordCalled(sig.stratName);
   NXS_Stats_RecordSetup(sig.stratName);

   if(InpNXR_Debug)
      PrintFormat("[NXR TRIGGER] %s %s score=%.1f exp=%s reason=%s",
                  sig.stratName, NXS_DirName(sig.dir), sig.score,
                  TimeToString(g_nxrTrigger.expiresAt, TIME_MINUTES), sig.reason);
}

SNXSReaction NXR_ReactionFromTrigger()
{
   SNXSReaction r;
   ZeroMemory(r);
   NXR_InvalidateExpiredTrigger();
   if(!g_nxrTrigger.valid || g_nxrTrigger.consumed) return r;

   int idx = NXR_FindZoneById(g_nxrTrigger.zoneId);
   r.detected   = true;
   r.direction  = (g_nxrTrigger.signal.dir == DIR_BUY) ? +1 : -1;
   r.levelPrice = (idx >= 0) ? g_nxrZones[idx].midpoint
                             : g_nxrTrigger.signal.entryRef;
   r.levelType  = NXR_ZoneName(g_nxrTrigger.zoneType);
   r.quality    = g_nxrTrigger.reactionQuality;
   r.summary    = StringFormat("NXR M5 reaction %s Q=%.0f",
                               r.levelType, r.quality);
   return r;
}

// -------------------------------------------------------------------
// Family-aware, additive router (one MTF/velocity decision only)
// -------------------------------------------------------------------
bool NXR_IsCounterHTF(ENUM_NXS_DIR dir, SNXSHTF &htf)
{
   return (dir == DIR_BUY  && htf.bias == HTF_BEAR) ||
          (dir == DIR_SELL && htf.bias == HTF_BULL);
}

bool NXR_IsVelocityOpposite(ENUM_NXS_DIR dir, SNXSVel &vel)
{
   return (dir == DIR_BUY  && (vel.state == VEL_BEAR || vel.state == VEL_BEAR_PB)) ||
          (dir == DIR_SELL && (vel.state == VEL_BULL || vel.state == VEL_BULL_PB));
}

bool NXR_IsVelocityAligned(ENUM_NXS_DIR dir, SNXSVel &vel)
{
   return (dir == DIR_BUY  && (vel.state == VEL_BULL || vel.state == VEL_BULL_PB)) ||
          (dir == DIR_SELL && (vel.state == VEL_BEAR || vel.state == VEL_BEAR_PB));
}

bool NXR_HasPriceActionEvidence(SNXSSignal &sig, SNXSSweep &sw)
{
   int d = (sig.dir == DIR_BUY) ? +1 : -1;
   bool reaction = g_reaction.detected && g_reaction.direction == d &&
                   g_reaction.quality >= InpNXR_MinReactionQuality;
   bool sweep = sw.confirmed && sw.dir == sig.dir;
   bool nxrTrigger = (StringFind(sig.reason, "NXR_M5:") >= 0);
   return (reaction || sweep || nxrTrigger);
}

bool NXR_HasStrongCounterEvidence(SNXSSignal &sig, SNXSSweep &sw)
{
   int d = (sig.dir == DIR_BUY) ? +1 : -1;
   double minQ = MathMax(InpNXR_MinReactionQuality,
                         InpNXR_CounterMinReactionQ);
   bool reaction = g_reaction.detected && g_reaction.direction == d &&
                   g_reaction.quality >= minQ;
   bool trigger = (StringFind(sig.reason, "NXR_M5:") >= 0 &&
                   g_nxrTrigger.reactionQuality >= minQ);
   bool sweepPlusReaction = sw.confirmed && sw.dir == sig.dir &&
                            (reaction || trigger);
   return (reaction || trigger || sweepPlusReaction);
}

double NXR_ContextScoreDelta(SNXSSignal &sig, SNXSAMD &amd,
                             SNXSSweep &sw, bool isM5)
{
   if(!isM5)
   {
      SNXSSignal tmp = sig;
      double legacyScore = NXS_FinalScore(tmp, amd, sw);
      return NXR_Clamp(legacyScore - sig.score, -10.0, 12.0);
   }

   // NXR M5 signals already contain POI strength and reaction quality. Reuse
   // only independent context components; do not count reaction/regime twice.
   double d = 0.0;
   if(InpUseAMD && amd.expectedDir != DIR_NONE)
   {
      if(amd.expectedDir == sig.dir) d += amd.modifier;
      else                           d -= amd.modifier * 0.5;
   }
   d += NXS_BSPModifier(sig.dir);
   if(sw.confirmed && sw.dir == sig.dir) d += 6.0;

   double pdH = iHigh(g_sym, PERIOD_D1, 1);
   double pdL = iLow (g_sym, PERIOD_D1, 1);
   double now = (sig.dir == DIR_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_ASK)
                                      : SymbolInfoDouble(g_sym, SYMBOL_BID);
   double prox = MathMax(g_atr * 0.60, g_point * 10.0);
   if(sig.dir == DIR_BUY  && pdL > 0.0 && MathAbs(now - pdL) <= prox) d += 4.0;
   if(sig.dir == DIR_SELL && pdH > 0.0 && MathAbs(now - pdH) <= prox) d += 4.0;
   return NXR_Clamp(d, -6.0, 8.0);
}

double NXR_FamilyThreshold(ENUM_NXS_FAMILY fam, bool isM5)
{
   double familyBase = 65.0;
   if(fam == FAM_TREND)         familyBase = 64.0;
   if(fam == FAM_REVERSAL)      familyBase = 61.0;
   if(fam == FAM_SMC)           familyBase = 60.0;
   if(fam == FAM_INSTITUTIONAL) familyBase = 62.0;
   if(isM5) familyBase = MathMin(familyBase, InpNXR_MinM5Score);

   double configured = NXS_ResolvedEntryThreshold();
   double th = configured;
   if(InpGateMode <= 0)
      th = MathMax(configured, familyBase);
   else if(InpGateMode == 1)
      th = MathMin(configured, familyBase + 2.0);
   else if(InpGateMode == 2)
      th = MathMin(configured, familyBase - 3.0);
   else
      th = MathMin(configured, familyBase - 8.0);

   if(g_session == SESS_OVERLAP) th -= 2.0;
   else if(g_session == SESS_LONDON || g_session == SESS_NY) th -= 1.0;
   else if(g_session == SESS_AFTERNY) th += 3.0;

   if(g_regime == REGIME_CHOPPY) th += 2.0;
   if(g_regime == REGIME_VOLATILE) th += 1.0;

   th = MathMax((InpGateMode >= 3) ? 45.0 : 52.0, th);
   return NXS_DynamicScoreThreshold(th);
}

SNXRRouteResult NXR_RouteCandidate(SNXSSignal &sig, SNXSAMD &amd,
                                   SNXSSweep &sw, SNXSHTF &htf,
                                   SNXSVel &vel)
{
   SNXRRouteResult r;
   ZeroMemory(r);
   r.allowed       = true;
   r.blockRc       = EXEC_FAIL_NO_DIR;
   r.lotMultiplier= 1.0;
   r.score         = sig.score;
   r.trace         = "NXR";

   ENUM_NXS_FAMILY fam = NXS_StratFamily(sig.stratName);
   bool isM5 = (StringFind(sig.reason, "NXR_M5:") >= 0);
   bool evidence = NXR_HasPriceActionEvidence(sig, sw);

   // Reuse independent NEXUS context, bounded. For NXR M5 setups the POI and
   // reaction components are already inside the base score, so they are not
   // counted a second time.
   double contextDelta = NXR_ContextScoreDelta(sig, amd, sw, isM5);
   r.score += contextDelta;
   r.trace += StringFormat(":CTX%+.1f", contextDelta);

   bool alignedHTF = (sig.dir == DIR_BUY  && htf.bias == HTF_BULL) ||
                     (sig.dir == DIR_SELL && htf.bias == HTF_BEAR);
   r.counterHTF = NXR_IsCounterHTF(sig.dir, htf);

   if(alignedHTF)
   {
      r.score += 4.0;
      r.trace += ":HTF+4";
   }
   else if(r.counterHTF)
   {
      bool counterFamily = (fam == FAM_REVERSAL || fam == FAM_SMC ||
                            fam == FAM_INSTITUTIONAL);
      bool counterFeature = (InpNXR_EnableCounterHTFSoft ||
                             InpEnableCounterHTFSoft);
      bool strongEvidence = NXR_HasStrongCounterEvidence(sig, sw);
      NXS_CounterSessionRollover();
      bool underCounterCap = (InpCounterHTF_MaxPerSession <= 0 ||
                              g_nxsCounterCount < InpCounterHTF_MaxPerSession);
      bool softCounter = counterFeature && counterFamily && underCounterCap &&
                         (strongEvidence || htf.reversalAllowed);

      if(InpGateMode < 2 && !softCounter)
      {
         r.allowed = false;
         r.blockRc = EXEC_FAIL_HTF;
         if(!counterFamily)          r.trace += ":HTF_FAMILY_HARD";
         else if(!counterFeature)   r.trace += ":HTF_SOFT_OFF";
         else if(!underCounterCap) r.trace += ":HTF_COUNTER_CAP";
         else                       r.trace += ":HTF_EVIDENCE_HARD";
      }
      else
      {
         bool qualitySoft = softCounter && (strongEvidence || htf.reversalAllowed);
         r.score -= qualitySoft ? 7.0 : 13.0;
         r.lotMultiplier *= MathMax(0.10, InpNXR_CounterLotMultiplier);
         r.trace += qualitySoft ? ":HTF_SOFT-7" : ":HTF_DISC-13";
      }
   }
   else
   {
      r.trace += ":HTF_NEUTRAL";
   }

   if(r.allowed && g_run_UseVelocityGate)
   {
      if(NXR_IsVelocityAligned(sig.dir, vel))
      {
         r.score += 2.0;
         r.trace += ":VEL+2";
      }
      else if(vel.state == VEL_NEUTRAL)
      {
         if(fam == FAM_TREND) r.score -= 2.0;
         r.trace += (fam == FAM_TREND) ? ":VEL_NEU-2" : ":VEL_NEU";
      }
      else if(NXR_IsVelocityOpposite(sig.dir, vel))
      {
         if(fam == FAM_TREND && InpGateMode < 2 && !evidence)
         {
            r.allowed = false;
            r.blockRc = EXEC_FAIL_VELOCITY;
            r.trace += ":VEL_HARD";
         }
         else
         {
            r.score -= evidence ? 5.0 : 10.0;
            r.lotMultiplier *= evidence ? 0.75 : 0.60;
            r.trace += evidence ? ":VEL_SOFT-5" : ":VEL_DISC-10";
         }
      }
   }

   // Regime routes families instead of allowing all 36 models to compete
   // with the same interpretation.
   if(r.allowed)
   {
      if(g_regime == REGIME_STRONG_TREND)
      {
         if(fam == FAM_TREND) r.score += 4.0;
         else if(fam == FAM_REVERSAL && !evidence) r.score -= 5.0;
      }
      else if(g_regime == REGIME_RANGING)
      {
         if(fam == FAM_REVERSAL || sig.stratName == "RANGE_FADE") r.score += 4.0;
         if(fam == FAM_TREND) r.score -= 5.0;
      }
      else if(g_regime == REGIME_CHOPPY)
      {
         r.score -= (fam == FAM_TREND) ? 7.0 : 3.0;
      }
      else if(g_regime == REGIME_VOLATILE)
      {
         if(fam == FAM_SMC || fam == FAM_INSTITUTIONAL) r.score += 2.0;
         else r.score -= 2.0;
      }
   }

   NXR_UpdateSpreadState();
   r.score -= g_nxrSpread.scorePenalty;
   if(g_nxrSpread.scorePenalty > 0.0)
      r.trace += StringFormat(":SP-%.1f", g_nxrSpread.scorePenalty);

   r.score = NXR_Clamp(r.score, 0.0, 100.0);
   r.threshold = NXR_FamilyThreshold(fam, isM5);
   r.lotMultiplier = NXR_Clamp(r.lotMultiplier, 0.10, 1.00);
   return r;
}

// -------------------------------------------------------------------
// Adaptive preflight and volume: fixes post-cap volume normalization
// -------------------------------------------------------------------
bool NXR_TradeModeAllows(ENUM_ORDER_TYPE otype, string &reason)
{
   ENUM_SYMBOL_TRADE_MODE mode =
      (ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(g_sym, SYMBOL_TRADE_MODE);
   if(mode == SYMBOL_TRADE_MODE_DISABLED || mode == SYMBOL_TRADE_MODE_CLOSEONLY)
   {
      reason = "symbol_trade_mode_block";
      return false;
   }
   if(mode == SYMBOL_TRADE_MODE_LONGONLY && otype == ORDER_TYPE_SELL)
   {
      reason = "symbol_long_only";
      return false;
   }
   if(mode == SYMBOL_TRADE_MODE_SHORTONLY && otype == ORDER_TYPE_BUY)
   {
      reason = "symbol_short_only";
      return false;
   }
   return true;
}

double NXR_RiskBudget(double riskMultiplier)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double pct = MathMax(0.0, g_run_RiskPercent);
   double budget = balance * pct / 100.0;
   budget *= NXS_AntiBleedMultiplier();
   budget *= NXR_Clamp(riskMultiplier, 0.01, 1.00);
   return MathMax(0.0, budget);
}

double NXR_LossForVolume(ENUM_ORDER_TYPE otype, double volume,
                         double entry, double sl)
{
   if(volume <= 0.0 || entry <= 0.0 || sl <= 0.0) return 0.0;
   double pnl = 0.0;
   if(OrderCalcProfit(otype, g_sym, volume, entry, sl, pnl))
      return MathAbs(pnl);

   // Fallback for symbols/brokers where OrderCalcProfit is temporarily
   // unavailable. Prefer loss tick value when the broker exposes it.
   double tickVal = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tickVal <= 0.0)
      tickVal = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_SIZE);
   if(tickVal <= 0.0 || tickSize <= 0.0) return 0.0;
   return (MathAbs(entry - sl) / tickSize) * tickVal * volume;
}

double NXR_CalcRawVolume(ENUM_ORDER_TYPE otype, double entry, double sl,
                         double riskMultiplier, string &reason)
{
   double budget = NXR_RiskBudget(riskMultiplier);
   if(budget <= 0.0)
   {
      reason = "risk_budget_zero";
      return 0.0;
   }
   double lossPerLot = NXR_LossForVolume(otype, 1.0, entry, sl);
   if(lossPerLot <= 0.0)
   {
      reason = StringFormat("loss_per_lot_unavailable err=%d", GetLastError());
      return 0.0;
   }
   return budget / lossPerLot;
}

double NXR_NormalizeVolumeSafe(double requested, ENUM_ORDER_TYPE otype,
                               double entry, double sl,
                               double riskMultiplier, string &reason)
{
   double minLot = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
   double brokerMax = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MAX);
   double maxLot = brokerMax;
   if(g_run_MaxLot > 0.0 && brokerMax > 0.0)
      maxLot = MathMin(g_run_MaxLot, brokerMax);
   else if(g_run_MaxLot > 0.0)
      maxLot = g_run_MaxLot;

   double step = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
   if(step <= 0.0) step = 0.01;
   if(minLot <= 0.0) minLot = step;
   if(maxLot < minLot)
   {
      reason = "invalid_symbol_volume_limits";
      return 0.0;
   }
   if(requested <= 0.0)
   {
      reason = "requested_volume_zero";
      return 0.0;
   }

   double lots = MathMin(maxLot, requested);
   lots = MathFloor((lots + 1e-12) / step) * step;
   lots = NormalizeDouble(lots, 8);

   if(lots < minLot)
   {
      // Raise to broker minimum only if the resulting monetary loss remains
      // within 125% of the risk budget. Otherwise reject explicitly.
      double budget  = NXR_RiskBudget(riskMultiplier);
      double minRisk = NXR_LossForVolume(otype, minLot, entry, sl);
      if(minRisk > 0.0 && minRisk <= budget * 1.25)
      {
         lots = minLot;
         reason = StringFormat("volume_raised_to_min risk=%.2f budget=%.2f",
                               minRisk, budget);
      }
      else
      {
         reason = StringFormat("volume_below_min req=%.4f min=%.4f riskMin=%.2f budget=%.2f",
                               requested, minLot, minRisk, budget);
         return 0.0;
      }
   }

   return NormalizeDouble(lots, 8);
}

double NXR_NormalizeDirectionalPrice(double price, bool roundUp)
{
   if(price <= 0.0) return price;
   double tick = NXR_TickSize();
   double units = price / tick;
   double normalized = roundUp ? MathCeil(units - 1e-12) * tick
                               : MathFloor(units + 1e-12) * tick;
   return NormalizeDouble(normalized, g_digits);
}

bool NXR_PrepareStops(ENUM_ORDER_TYPE otype, double price,
                      double &sl, double &tp, string &reason)
{
   if(!NXS_AdjustStopsForBroker(otype, price, sl, tp, reason)) return false;

   // Add one tradable tick beyond the broker's minimum distance, then round
   // away from market. MathRound can otherwise move a valid CFD/metal stop
   // back inside SYMBOL_TRADE_STOPS_LEVEL.
   int stopsLevel = (int)SymbolInfoInteger(g_sym, SYMBOL_TRADE_STOPS_LEVEL);
   double safeDist = MathMax(0.0, stopsLevel * g_point) + NXR_TickSize();
   if(otype == ORDER_TYPE_BUY)
   {
      if(sl > 0.0 && price - sl < safeDist) sl = price - safeDist;
      if(tp > 0.0 && tp - price < safeDist) tp = price + safeDist;
      sl = NXR_NormalizeDirectionalPrice(sl, false); // farther below
      tp = NXR_NormalizeDirectionalPrice(tp, true);  // farther above
   }
   else if(otype == ORDER_TYPE_SELL)
   {
      if(sl > 0.0 && sl - price < safeDist) sl = price + safeDist;
      if(tp > 0.0 && price - tp < safeDist) tp = price - safeDist;
      sl = NXR_NormalizeDirectionalPrice(sl, true);  // farther above
      tp = NXR_NormalizeDirectionalPrice(tp, false); // farther below
   }
   return NXS_ValidateStopSides(otype, price, sl, tp, reason);
}

bool NXR_RepriceM5Signal(SNXSSignal &sig, double currentEntry, string &reason)
{
   if(StringFind(sig.reason, "NXR_M5:") < 0)
   {
      sig.entryRef = currentEntry;
      return true;
   }

   double initialRisk = MathAbs(sig.entryRef - sig.slPrice);
   if(initialRisk <= NXR_TickSize())
   {
      reason = "m5_initial_risk_invalid";
      return false;
   }

   // Block only adverse chasing: paying higher for a BUY or lower for a SELL.
   double adverseDrift = (sig.dir == DIR_BUY)
                         ? currentEntry - sig.entryRef
                         : sig.entryRef - currentEntry;
   double maxDrift = initialRisk * MathMax(0.0, InpNXR_MaxEntryDriftR);
   if(adverseDrift > maxDrift)
   {
      reason = StringFormat("m5_entry_drift %.2fR>%.2fR",
                            adverseDrift / initialRisk,
                            MathMax(0.0, InpNXR_MaxEntryDriftR));
      return false;
   }

   if((sig.dir == DIR_BUY  && sig.slPrice >= currentEntry) ||
      (sig.dir == DIR_SELL && sig.slPrice <= currentEntry))
   {
      reason = "m5_sl_crossed_before_entry";
      return false;
   }

   double risk = MathAbs(currentEntry - sig.slPrice);
   double target = NXR_FindTargetLiquidity((sig.dir == DIR_BUY) ? +1 : -1,
                                           currentEntry, risk);
   if(sig.dir == DIR_BUY)
      sig.tpPrice = MathMax(sig.tpPrice, target);
   else
      sig.tpPrice = (sig.tpPrice > 0.0) ? MathMin(sig.tpPrice, target) : target;

   sig.entryRef = currentEntry;
   sig.tpPrice = NXR_NormalizePrice(sig.tpPrice);
   return true;
}

bool NXR_Preflight(ENUM_ORDER_TYPE otype, double lots, double price,
                   double &sl, double &tp, string &reason)
{
   if(!NXR_TradeModeAllows(otype, reason)) return false;
   if(!NXR_SpreadOK())
   {
      reason = "adaptive_spread:" + g_nxrSpread.reason;
      return false;
   }
   if(!NXR_PrepareStops(otype, price, sl, tp, reason)) return false;

   double minLot = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MAX);
   if(lots < minLot - 1e-12)
   {
      reason = StringFormat("lot_below_min %.4f<%.4f", lots, minLot);
      return false;
   }
   if(lots > maxLot + 1e-12)
   {
      reason = StringFormat("lot_above_max %.4f>%.4f", lots, maxLot);
      return false;
   }
   if(!NXS_MarginCheck(otype, lots, price, reason)) return false;
   return true;
}

ENUM_NXS_OPEN_RC NXR_OpenTrade(SNXSSignal &sig, long magic,
                               double lotMultiplier)
{
   g_nxsLastOpenFailure = "";
   g_nxrLastPreflight = "";

   MqlTick tick;
   if(!SymbolInfoTick(g_sym, tick))
   {
      g_nxsLastOpenFailure = "no_symbol_tick";
      return OPEN_FAIL_PREFLIGHT;
   }

   double refPrice = (sig.dir == DIR_BUY) ? tick.ask : tick.bid;
   if(refPrice <= 0.0)
   {
      g_nxsLastOpenFailure = "invalid_quote";
      return OPEN_FAIL_PREFLIGHT;
   }
   ENUM_ORDER_TYPE otype = (sig.dir == DIR_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;

   string repriceReason = "";
   if(!NXR_RepriceM5Signal(sig, refPrice, repriceReason))
   {
      g_nxsLastOpenFailure = repriceReason;
      return OPEN_FAIL_PREFLIGHT;
   }

   double sl = sig.slPrice;
   double tp = sig.tpPrice;
   string stopReason = "";
   if(!NXR_PrepareStops(otype, refPrice, sl, tp, stopReason))
   {
      g_nxsLastOpenFailure = stopReason;
      return OPEN_FAIL_INVALID_STOPS;
   }

   double slDist = MathAbs(refPrice - sl);
   if(slDist <= NXR_TickSize())
   {
      g_nxsLastOpenFailure = "invalid_sl_distance";
      return OPEN_FAIL_INVALID_STOPS;
   }

   string calcReason = "";
   double calculatedLots = NXR_CalcRawVolume(otype, refPrice, sl,
                                              lotMultiplier, calcReason);
   if(calculatedLots <= 0.0)
   {
      g_nxsLastOpenFailure = calcReason;
      return OPEN_FAIL_INVALID_VOLUME;
   }
   double rawLots = NXS_License_CapLot(calculatedLots);

   // Never raise a license-capped volume back above the cap. In the Strategy
   // Tester the AUDITPATCH bypasses trial caps, while live trial accounts get
   // an explicit diagnostic instead of a silent preflight failure.
   double minLotCheck = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
   bool licenseReduced = (rawLots + 1e-12 < calculatedLots);
   if(licenseReduced && rawLots + 1e-12 < minLotCheck)
   {
      g_nxsLastOpenFailure = StringFormat("license_cap_below_min %.4f<%.4f",
                                          rawLots, minLotCheck);
      return OPEN_FAIL_INVALID_VOLUME;
   }

   string volReason = "";
   double lots = NXR_NormalizeVolumeSafe(rawLots, otype, refPrice, sl,
                                         lotMultiplier, volReason);
   if(lots <= 0.0)
   {
      g_nxsLastOpenFailure = volReason;
      return OPEN_FAIL_INVALID_VOLUME;
   }
   string pfReason = "";
   if(StringLen(volReason) > 0)
      sig.reason = NXR_AppendReason(sig.reason, volReason);

   if(!NXR_Preflight(otype, lots, refPrice, sl, tp, pfReason))
   {
      g_nxsLastOpenFailure = pfReason;
      g_nxrLastPreflight = pfReason;
      PrintFormat("[NXR OPEN BLOCKED] %s strat=%s", pfReason, sig.stratName);
      return OPEN_FAIL_PREFLIGHT;
   }

   sig.slPrice = sl;
   sig.tpPrice = tp;
   NXS_TradeSetMagic(magic);
   string cm = StringFormat("%s|%s|%.0f", InpComment, sig.stratName, sig.score);
   bool ok = (sig.dir == DIR_BUY)
             ? NXS_SafeBuy(lots, g_sym, sl, tp, cm)
             : NXS_SafeSell(lots, g_sym, sl, tp, cm);

   if(ok)
   {
      g_tradesToday++;
      g_lastTradeTime = TimeCurrent();
      PrintFormat("[NXR OPEN] %s %s lots=%.4f sl=%.5f tp=%.5f score=%.1f reason=%s",
                  NXS_DirName(sig.dir), sig.stratName, lots, sl, tp,
                  sig.score, sig.reason);
      NXS_Notify_TradeOpen(sig.stratName, NXS_DirName(sig.dir),
                           lots, refPrice, sig.score);
      return OPEN_OK;
   }

   g_nxsLastOpenFailure = StringFormat("order_send_retcode=%u", NXS_TradeRetcode());
   NXS_Diag_TradeFail(sig.stratName, (int)sig.dir, lots,
                      refPrice, (int)NXS_TradeRetcode());
   return OPEN_FAIL_SEND;
}

ENUM_NXS_EXEC_RC NXR_TryExecuteRC(SNXSSignal &sig, SNXSAMD &amd,
                                  SNXSSweep &sw, SNXSHTF &htf,
                                  SNXSVel &vel, double &finalScoreOut,
                                  double &thresholdOut)
{
   if(!InpNXR_Enable)
      return NXS_TryExecuteRC(sig, amd, sw, htf, vel,
                              finalScoreOut, thresholdOut);

   finalScoreOut = sig.score;
   thresholdOut = 0.0;
   if(sig.dir == DIR_NONE) return EXEC_FAIL_NO_DIR;

   if(InpNXR_MinSecondsBetweenTrade > 0 && g_lastTradeTime > 0 &&
      (TimeCurrent() - g_lastTradeTime) < InpNXR_MinSecondsBetweenTrade)
   {
      g_nxrLastRouteTrace = "NXR:trade_gap";
      return EXEC_FAIL_PROTECTIONS;
   }

   string protectionReason = "";
   if(!NXS_CheckProtections(protectionReason))
   {
      g_nxrLastRouteTrace = "NXR:PROT:" + protectionReason;
      return EXEC_FAIL_PROTECTIONS;
   }
   if(NXS_NewsBlocking())
   {
      g_nxrLastRouteTrace = "NXR:NEWS";
      return EXEC_FAIL_NEWS;
   }
   if(!NXR_SpreadOK())
   {
      g_nxrLastRouteTrace = "NXR:SPREAD:" + g_nxrSpread.reason;
      g_nxsLastOpenFailure = "adaptive_spread:" + g_nxrSpread.reason;
      return EXEC_FAIL_PREFLIGHT;
   }

   SNXRRouteResult route = NXR_RouteCandidate(sig, amd, sw, htf, vel);
   g_nxrLastRouteTrace = route.trace;
   finalScoreOut = route.score;
   thresholdOut = route.threshold;
   sig.reason = NXR_AppendReason(sig.reason, route.trace);

   if(!route.allowed) return route.blockRc;
   sig.score = route.score;
   if(route.score < route.threshold) return EXEC_FAIL_SCORE_BELOW;

   // Keep structural SL/TP for NXR POI entries. Legacy counter-HTF signals
   // receive the AUDITPATCH tighter ATR profile before monetary risk sizing.
   if(route.counterHTF && StringFind(sig.reason, "NXR_M5:") < 0)
      NXS_ApplyCounterHTFProfile(sig);

   NXS_CloseOppositeIfBetter(sig.dir, route.score);
   ENUM_NXS_OPEN_RC openRc = NXR_OpenTrade(sig, InpMagic + MAGIC_CORE,
                                           route.lotMultiplier);
   if(openRc == OPEN_OK)
   {
      if(route.counterHTF)
      {
         NXS_CounterSessionRollover();
         g_nxsCounterCount++;
      }
      return EXEC_OK;
   }
   if(openRc == OPEN_FAIL_INVALID_STOPS)  return EXEC_FAIL_INVALID_STOPS;
   if(openRc == OPEN_FAIL_INVALID_VOLUME) return EXEC_FAIL_INVALID_VOLUME;
   if(openRc == OPEN_FAIL_PREFLIGHT)      return EXEC_FAIL_PREFLIGHT;
   return EXEC_FAIL_ORDER_SEND;
}

// -------------------------------------------------------------------
// Direct M5 executor: runs after NEXUS management/protections on each tick
// -------------------------------------------------------------------
ENUM_NXS_BLOCK NXR_BlockFromExecRC(ENUM_NXS_EXEC_RC rc)
{
   if(rc == EXEC_FAIL_PROTECTIONS)    return BLK_PROTECTIONS;
   if(rc == EXEC_FAIL_NEWS)           return BLK_NEWS;
   if(rc == EXEC_FAIL_HTF)            return BLK_HTF;
   if(rc == EXEC_FAIL_VELOCITY)       return BLK_VELOCITY;
   if(rc == EXEC_FAIL_SCORE_BELOW)    return BLK_SCORE_BELOW;
   if(rc == EXEC_FAIL_ORDER_SEND)     return BLK_SEND_FAILED;
   return BLK_PREFLIGHT;
}

bool NXR_IsTransientExecRC(ENUM_NXS_EXEC_RC rc)
{
   return (rc == EXEC_FAIL_PROTECTIONS || rc == EXEC_FAIL_NEWS ||
           rc == EXEC_FAIL_PREFLIGHT);
}

void NXR_ProcessPendingM5Trigger()
{
   if(!InpNXR_Enable || !InpNXR_DirectM5Execution) return;
   NXR_InvalidateExpiredTrigger();
   if(!g_nxrTrigger.valid || g_nxrTrigger.consumed) return;
   if(TimeCurrent() - g_nxrTrigger.lastAttemptAt < 10) return;
   g_nxrTrigger.lastAttemptAt = TimeCurrent();

   SNXSSignal sig = g_nxrTrigger.signal;
   if(NXS_StrategyOnCooldown(sig.stratName)) return;
   if(g_eaPaused || !NXS_License_Enforce()) return;
   if(NXS_Prot_EntryBlocked()) return;
   if(!NXR_SpreadOK() || NXS_NewsBlocking()) return;

   SNXSHTF htf = NXS_GetHTFBias();
   SNXSVel vel = NXS_GetVelocity();
   SNXSAMD amd = NXS_GetAMD();
   SNXSSweep sw = NXS_DetectSweep();

   double finalScore = 0.0, threshold = 0.0;
   ENUM_NXS_EXEC_RC rc = NXR_TryExecuteRC(sig, amd, sw, htf, vel,
                                          finalScore, threshold);
   NXS_Stats_RecordScoreSample(sig.stratName,
                               g_nxrTrigger.signal.score,
                               finalScore, threshold);

   if(rc == EXEC_OK)
   {
      NXS_StrategyRegisterTrade(sig.stratName);
      NXS_Stats_RecordExec(sig.stratName, finalScore,
                           (double)SymbolInfoInteger(g_sym, SYMBOL_SPREAD));
      NXS_LogTradeCSV("OPEN", 0, sig.stratName, sig.entryRef,
                      0, sig.slPrice, sig.tpPrice, sig.score, sig.reason);
      g_nxrTrigger.consumed = true;
      g_nxrTrigger.valid = false;
      return;
   }

   // Keep only genuinely transient timing conditions until expiry. An
   // anti-bleed skip represents one distinct setup, not a 10-second retry;
   // consume this trigger after the counter is decremented once.
   bool antiBleedConsumed = (rc == EXEC_FAIL_PROTECTIONS &&
                             StringFind(g_nxrLastRouteTrace,
                                        "anti_bleed_skip") >= 0);
   if(antiBleedConsumed || !NXR_IsTransientExecRC(rc) ||
      rc == EXEC_FAIL_SCORE_BELOW)
   {
      ENUM_NXS_BLOCK blk = NXR_BlockFromExecRC(rc);
      NXS_Blk_Bump(blk);
      NXS_Stats_RecordBlock(sig.stratName, (int)blk);
      g_nxrTrigger.consumed = true;
      g_nxrTrigger.valid = false;
   }
}

// -------------------------------------------------------------------
// Hooks called by the main through macros at end of file
// -------------------------------------------------------------------
bool NXR_UpdateIndicatorsHook()
{
   bool ok = NXS_UpdateIndicators();
   if(!ok || !InpNXR_Enable) return ok;

   static bool announced = false;
   if(!announced)
   {
      announced = true;
      PrintFormat("[NXR v%s] ACTIVE directM5=%s triggerTF=%s switches=%s minRR=%.2f",
                  NXR_PACK_VERSION, InpNXR_DirectM5Execution ? "ON" : "OFF",
                  EnumToString(InpNXR_TriggerTF),
                  InpNXR_RespectNexusSwitches ? "NEXUS" : "PACK",
                  InpNXR_MinRR);
   }

   NXR_UpdateSpreadState();
   NXR_RebuildContextIfNeeded();

   datetime triggerBar = iTime(g_sym, InpNXR_TriggerTF, 0);
   if(triggerBar > 0 && triggerBar != g_nxrLastTriggerBar)
   {
      g_nxrLastTriggerBar = triggerBar;
      NXR_RefreshContext();
      NXR_ProcessZoneBreaksOnClosedBar(InpNXR_TriggerTF);
      NXR_DetectClosedBarTrigger();
      NXR_RegisterZoneTouches(InpNXR_TriggerTF);
   }
   return ok;
}

void NXR_UpdateStructureHook(string sym, ENUM_TIMEFRAMES tf)
{
   NXS_UpdateStructure(sym, tf);
   if(!InpNXR_Enable) return;
   NXR_RefreshContext();
}

SNXSReaction NXR_DetectReactionHook(string sym, ENUM_TIMEFRAMES tf)
{
   if(InpNXR_Enable)
   {
      SNXSReaction nxr = NXR_ReactionFromTrigger();
      if(nxr.detected) return nxr;
   }

   SNXSReaction base = NXS_DetectReaction(sym, tf);
   if(!InpNXR_Enable || !base.detected) return base;

   // Sanitize the legacy reaction: a candle with the expected colour alone is
   // not sufficient evidence. Keep it visible for diagnostics, but cap its
   // quality below the counter-HTF eligibility threshold unless a real wick
   // rejection or engulfing pattern is present on the closed entry bar.
   double o1 = iOpen (sym, tf, 1);
   double h1 = iHigh (sym, tf, 1);
   double l1 = iLow  (sym, tf, 1);
   double c1 = iClose(sym, tf, 1);
   double o2 = iOpen (sym, tf, 2);
   double c2 = iClose(sym, tf, 2);
   double range = h1 - l1;
   if(range <= 0.0) return base;

   double body = MathAbs(c1 - o1);
   double upperWick = h1 - MathMax(o1, c1);
   double lowerWick = MathMin(o1, c1) - l1;
   bool strong = false;
   if(base.direction > 0)
   {
      bool pin = (c1 > o1 && lowerWick >= MathMax(body * 0.80, range * 0.20) &&
                  c1 >= l1 + range * 0.60);
      bool engulf = (c2 < o2 && c1 > o1 && c1 >= o2 && o1 <= c2);
      strong = (pin || engulf);
   }
   else if(base.direction < 0)
   {
      bool pin = (c1 < o1 && upperWick >= MathMax(body * 0.80, range * 0.20) &&
                  c1 <= l1 + range * 0.40);
      bool engulf = (c2 > o2 && c1 < o1 && c1 <= o2 && o1 >= c2);
      strong = (pin || engulf);
   }

   if(!strong)
   {
      base.quality = MathMin(base.quality, 55.0);
      base.summary = NXR_AppendReason(base.summary, "NXR_WEAK_CANDLE");
   }
   return base;
}

void NXR_DiagOnTickHook(string htfBiasStr, string velStr,
                        string amdPhase, double bspValue)
{
   NXS_Diag_OnTick(htfBiasStr, velStr, amdPhase, bspValue);
   if(!InpNXR_Enable) return;
   NXR_ProcessPendingM5Trigger();

   static datetime lastPrint = 0;
   if(InpNXR_Debug && TimeCurrent() - lastPrint >= 60)
   {
      lastPrint = TimeCurrent();
      int active = 0, fresh = 0, mitigated = 0;
      for(int i = 0; i < g_nxrZoneCount; i++)
      {
         if(g_nxrZones[i].active) active++;
         if(g_nxrZones[i].state == NXR_STATE_FRESH) fresh++;
         if(g_nxrZones[i].state == NXR_STATE_MITIGATED) mitigated++;
      }
      PrintFormat("[NXR DIAG] zones=%d active=%d fresh=%d mitigated=%d trigger=%s "
                  "spread=%d normal=%.1f ratio=%.2f penalty=%.1f route=%s",
                  g_nxrZoneCount, active, fresh, mitigated,
                  g_nxrTrigger.valid ? "ARMED" : "NONE",
                  g_nxrSpread.currentPts, g_nxrSpread.slowAvgPts,
                  g_nxrSpread.ratioToNormal, g_nxrSpread.scorePenalty,
                  g_nxrLastRouteTrace);
   }
}

// Outer router hooks become observable no-op factors because the unified
// NXR_TryExecuteRC performs MTF and velocity exactly once.
double NXR_OuterMTFFactor(int direction, string stratName, string &reason)
{
   if(!InpNXR_Enable)
      return NXS_MTF_FamilyFactor(direction, stratName, reason);
   reason = "MTF:NXR-UNIFIED";
   return 1.0;
}

double NXR_OuterVelocityFactor(ENUM_NXS_DIR dir, SNXSVel &vel,
                               string stratName, string &reason)
{
   if(!InpNXR_Enable)
      return NXS_Vel_FamilyFactor(dir, vel, stratName, reason);
   reason = "VEL:NXR-UNIFIED";
   return 1.0;
}

// -------------------------------------------------------------------
// Strategy replacements: prefer the cached M5 POI trigger, otherwise keep
// the corrected NEXUS AUDITPATCH implementation as fallback.
// -------------------------------------------------------------------
bool NXR_TriggerMatches(ENUM_NXR_ZONE_TYPE a, ENUM_NXR_ZONE_TYPE b)
{
   return (a == b);
}

SNXSSignal NXR_TriggerSignalFor(ENUM_NXR_ZONE_TYPE t1,
                                ENUM_NXR_ZONE_TYPE t2,
                                string name, ENUM_NXS_STRAT strat)
{
   NXR_InvalidateExpiredTrigger();
   if(!g_nxrTrigger.valid || g_nxrTrigger.consumed)
      return NXR_EmptySignal(name, strat);
   if(!NXR_TriggerMatches(g_nxrTrigger.zoneType, t1) &&
      !NXR_TriggerMatches(g_nxrTrigger.zoneType, t2))
      return NXR_EmptySignal(name, strat);

   SNXSSignal s = g_nxrTrigger.signal;
   s.stratName = name;
   s.strat = strat;
   return s;
}

SNXSSignal NXR_Strat_IFVG_Reversal()
{
   SNXSSignal nxr = NXR_TriggerSignalFor(NXR_ZONE_IFVG_BULL,
                                         NXR_ZONE_IFVG_BEAR,
                                         "IFVG", STRAT_FVG_CONT);
   SNXSSignal base = NXS_Strat_IFVG_Reversal();
   if(nxr.dir != DIR_NONE && (base.dir == DIR_NONE || nxr.score >= base.score))
      return nxr;
   return base;
}

SNXSSignal NXR_Strat_FVG_Mitigation()
{
   SNXSSignal nxr = NXR_TriggerSignalFor(NXR_ZONE_FVG_BULL,
                                         NXR_ZONE_FVG_BEAR,
                                         "FVG_MIT", STRAT_FVG_CONT);
   SNXSSignal base = NXS_Strat_FVG_Mitigation();
   if(nxr.dir != DIR_NONE && (base.dir == DIR_NONE || nxr.score >= base.score))
      return nxr;
   return base;
}

SNXSSignal NXR_Strat_OB_Mitigation()
{
   NXR_InvalidateExpiredTrigger();
   SNXSSignal nxr = NXR_EmptySignal("OB_MIT", STRAT_ORDER_BLOCK);
   if(g_nxrTrigger.valid && !g_nxrTrigger.consumed &&
      (g_nxrTrigger.zoneType == NXR_ZONE_OB_BULL ||
       g_nxrTrigger.zoneType == NXR_ZONE_OB_BEAR ||
       g_nxrTrigger.zoneType == NXR_ZONE_BREAKER_BULL ||
       g_nxrTrigger.zoneType == NXR_ZONE_BREAKER_BEAR))
   {
      nxr = g_nxrTrigger.signal;
      nxr.stratName = "OB_MIT";
      nxr.strat = STRAT_ORDER_BLOCK;
   }
   SNXSSignal base = NXS_Strat_OB_Mitigation_Structural();
   if(nxr.dir != DIR_NONE && (base.dir == DIR_NONE || nxr.score >= base.score))
      return nxr;
   return base;
}

SNXSSignal NXR_Strat_MalaysianSNR()
{
   SNXSSignal nxr = NXR_TriggerSignalFor(NXR_ZONE_SNR_SUPPORT,
                                         NXR_ZONE_SNR_RESISTANCE,
                                         "MALAYSIAN_SNR",
                                         STRAT_STRUCT_REACT);
   SNXSSignal base = NXS_Strat_MalaysianSNR_Rejection();
   if(nxr.dir != DIR_NONE && (base.dir == DIR_NONE || nxr.score >= base.score))
      return nxr;
   return base;
}

SNXSSignal NXR_Strat_StructureReaction()
{
   // Only use a generic trigger if it was not already claimed by one of the
   // four source-specific replacements. This prevents artificial confluence.
   SNXSSignal base = NXS_Strat_StructureReaction();
   NXR_InvalidateExpiredTrigger();
   if(!g_nxrTrigger.valid || g_nxrTrigger.consumed) return base;

   ENUM_NXR_ZONE_TYPE t = g_nxrTrigger.zoneType;
   bool sourceSpecific = (t == NXR_ZONE_IFVG_BULL || t == NXR_ZONE_IFVG_BEAR ||
                          t == NXR_ZONE_FVG_BULL  || t == NXR_ZONE_FVG_BEAR  ||
                          t == NXR_ZONE_OB_BULL   || t == NXR_ZONE_OB_BEAR   ||
                          t == NXR_ZONE_BREAKER_BULL || t == NXR_ZONE_BREAKER_BEAR ||
                          t == NXR_ZONE_SNR_SUPPORT || t == NXR_ZONE_SNR_RESISTANCE);
   if(sourceSpecific) return base;

   SNXSSignal nxr = g_nxrTrigger.signal;
   nxr.stratName = "STRUCT_REACT";
   nxr.strat = STRAT_STRUCT_REACT;
   if(base.dir == DIR_NONE || nxr.score >= base.score) return nxr;
   return base;
}

// -------------------------------------------------------------------
// Compile-time hooks. These names are intentionally defined LAST.
// The include must be placed after the original NXS_UpdateIndicators()
// definition and before NXS_PickBestSignal()/OnInit(), as documented above.
// -------------------------------------------------------------------
#define NXS_UpdateIndicators                 NXR_UpdateIndicatorsHook
#define NXS_UpdateStructure                  NXR_UpdateStructureHook
#define NXS_DetectReaction                   NXR_DetectReactionHook
#define NXS_Diag_OnTick                      NXR_DiagOnTickHook
#define NXS_SpreadOK                         NXR_SpreadOK
#define NXS_MTF_FamilyFactor                 NXR_OuterMTFFactor
#define NXS_Vel_FamilyFactor                 NXR_OuterVelocityFactor
#define NXS_TryExecuteRC                     NXR_TryExecuteRC
#define NXS_Strat_IFVG_Reversal              NXR_Strat_IFVG_Reversal
#define NXS_Strat_FVG_Mitigation              NXR_Strat_FVG_Mitigation
#define NXS_Strat_OB_Mitigation_Structural   NXR_Strat_OB_Mitigation
#define NXS_Strat_MalaysianSNR_Rejection     NXR_Strat_MalaysianSNR
#define NXS_Strat_StructureReaction          NXR_Strat_StructureReaction

#endif // __NXS_REUSE_PERFORMANCE_PACK_MQH__


