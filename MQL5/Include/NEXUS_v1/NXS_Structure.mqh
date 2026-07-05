//+------------------------------------------------------------------+
//|  NXS_Structure.mqh - Autonomous Structure Engine                  |
//|  BOS / CHOCH / Swings / Order Blocks / FVG / Trendlines           |
//+------------------------------------------------------------------+
#ifndef __NXS_STRUCTURE_MQH__
#define __NXS_STRUCTURE_MQH__

enum ENUM_NXS_LEVEL_TYPE {
   NXS_LVL_SWING_HIGH,
   NXS_LVL_SWING_LOW,
   NXS_LVL_OB_BULL,
   NXS_LVL_OB_BEAR,
   NXS_LVL_FVG_BULL,
   NXS_LVL_FVG_BEAR
};

struct SNXSLevel {
   ENUM_NXS_LEVEL_TYPE type;
   double   priceTop;
   double   priceBot;
   double   priceRef;
   datetime time;
   bool     mitigated;
   int      mitigations;
   bool     active;
};

struct SNXSStructure {
   int      trend;          // +1 HH/HL, -1 LH/LL, 0 range
   bool     bosUp, bosDown;
   bool     chochUp, chochDown;
   double   lastSwingHigh;
   double   lastSwingLow;
   double   prevSwingHigh;
   double   prevSwingLow;
   double   trendlineValue;
   int      trendlineDir;   // +1 ascending, -1 descending
   string   summary;
};

SNXSStructure g_struct;     // entry TF (e.g. M15) - read by ~30 call sites across strategies
SNXSStructure g_structH1;   // v2.0.34: independent H1 structure context, computed separately so
                            // strategies wanting higher-TF confirmation don't read entry-TF state
                            // mislabeled as H1 (audit point 2 - "one global mixes contexts").
SNXSLevel     g_levels[];
int           g_levelCount = 0;

void NXS_AddLevel(ENUM_NXS_LEVEL_TYPE type, double top, double bot, double ref, datetime t){
   const int maxLevels = 40;
   if(g_levelCount >= maxLevels){
      // compact: drop the oldest inactive, else drop index 0
      int dropIdx = -1;
      for(int i = 0; i < g_levelCount; i++){
         if(!g_levels[i].active || (g_levels[i].mitigated && g_levels[i].mitigations >= 2)){ dropIdx = i; break; }
      }
      if(dropIdx < 0) dropIdx = 0;
      for(int i = dropIdx; i < g_levelCount - 1; i++) g_levels[i] = g_levels[i+1];
      g_levelCount--;
   }
   if(ArraySize(g_levels) < g_levelCount + 1) ArrayResize(g_levels, g_levelCount + 8);

   // dedupe near-identical recent level
   for(int i = 0; i < g_levelCount; i++){
      if(g_levels[i].type != type) continue;
      if(MathAbs(g_levels[i].priceRef - ref) < g_point * 5 && g_levels[i].time == t) return;
   }

   SNXSLevel lv;
   lv.type        = type;
   lv.priceTop    = top;
   lv.priceBot    = bot;
   lv.priceRef    = ref;
   lv.time        = t;
   lv.mitigated   = false;
   lv.mitigations = 0;
   lv.active      = true;
   g_levels[g_levelCount++] = lv;
}

bool NXS_IsSwingHigh(string sym, ENUM_TIMEFRAMES tf, int shift, int wing){
   double h = iHigh(sym, tf, shift);
   if(h <= 0) return false;
   for(int k = 1; k <= wing; k++){
      if(iHigh(sym, tf, shift + k) >= h) return false;
      if(iHigh(sym, tf, shift - k) >= h) return false;
   }
   return true;
}

bool NXS_IsSwingLow(string sym, ENUM_TIMEFRAMES tf, int shift, int wing){
   double l = iLow(sym, tf, shift);
   if(l <= 0) return false;
   for(int k = 1; k <= wing; k++){
      if(iLow(sym, tf, shift + k) <= l) return false;
      if(iLow(sym, tf, shift - k) <= l) return false;
   }
   return true;
}

void NXS_DetectOrderBlocks(string sym, ENUM_TIMEFRAMES tf){
   if(g_atr <= 0) return;
   int lookback = 30;
   for(int i = 3; i < lookback; i++){
      double o = iOpen (sym, tf, i);
      double c = iClose(sym, tf, i);
      double h = iHigh (sym, tf, i);
      double l = iLow  (sym, tf, i);
      // strong bull move on next candle
      double moveUp = iClose(sym, tf, i-1) - iOpen(sym, tf, i-1);
      double moveDn = iOpen (sym, tf, i-1) - iClose(sym, tf, i-1);
      // Bullish OB = bearish candle followed by strong bullish displacement
      if(c < o && moveUp > g_atr * InpOBDisplacement){
         NXS_AddLevel(NXS_LVL_OB_BULL, MathMax(o,c), MathMin(o,c), (o+c)/2.0, iTime(sym, tf, i));
      }
      // Bearish OB = bullish candle followed by strong bearish displacement
      if(c > o && moveDn > g_atr * InpOBDisplacement){
         NXS_AddLevel(NXS_LVL_OB_BEAR, MathMax(o,c), MathMin(o,c), (o+c)/2.0, iTime(sym, tf, i));
      }
   }
}

void NXS_DetectFVG(string sym, ENUM_TIMEFRAMES tf){
   if(g_atr <= 0) return;
   int lookback = 30;
   for(int i = 3; i < lookback; i++){
      double hPrev = iHigh(sym, tf, i+1);   // candle before
      double lPrev = iLow (sym, tf, i+1);
      double oMid  = iOpen (sym, tf, i);
      double cMid  = iClose(sym, tf, i);
      double hNext = iHigh(sym, tf, i-1);   // candle after
      double lNext = iLow (sym, tf, i-1);
      double body  = MathAbs(cMid - oMid);
      if(body < g_atr * InpFVGMinBody) continue;
      // Bullish FVG: gap between i+1.high and i-1.low (low_next > high_prev)
      if(lNext > hPrev){
         NXS_AddLevel(NXS_LVL_FVG_BULL, lNext, hPrev, (lNext + hPrev) / 2.0, iTime(sym, tf, i));
      }
      // Bearish FVG: high_next < low_prev
      if(hNext < lPrev){
         NXS_AddLevel(NXS_LVL_FVG_BEAR, lPrev, hNext, (lPrev + hNext) / 2.0, iTime(sym, tf, i));
      }
   }
}

void NXS_UpdateTrendline(string sym, ENUM_TIMEFRAMES tf){
   g_struct.trendlineValue = 0;
   g_struct.trendlineDir   = 0;
   if(g_struct.trend == 1 && g_struct.lastSwingLow > 0 && g_struct.prevSwingLow > 0){
      // slope from prev → last swing low extended to current bar
      double slope = (g_struct.lastSwingLow - g_struct.prevSwingLow);
      g_struct.trendlineValue = g_struct.lastSwingLow + slope * 0.5;
      g_struct.trendlineDir   = (slope > 0) ? 1 : -1;
   } else if(g_struct.trend == -1 && g_struct.lastSwingHigh > 0 && g_struct.prevSwingHigh > 0){
      double slope = (g_struct.lastSwingHigh - g_struct.prevSwingHigh);
      g_struct.trendlineValue = g_struct.lastSwingHigh + slope * 0.5;
      g_struct.trendlineDir   = (slope < 0) ? -1 : 1;
   }
}

void NXS_MitigateLevels(string sym){
   double price = SymbolInfoDouble(sym, SYMBOL_BID);
   if(price <= 0) return;
   for(int i = 0; i < g_levelCount; i++){
      if(!g_levels[i].active) continue;
      bool touched = false;
      // zones: OB / FVG use top/bot
      ENUM_NXS_LEVEL_TYPE t = g_levels[i].type;
      if(t == NXS_LVL_OB_BULL || t == NXS_LVL_OB_BEAR || t == NXS_LVL_FVG_BULL || t == NXS_LVL_FVG_BEAR){
         if(price <= g_levels[i].priceTop && price >= g_levels[i].priceBot) touched = true;
      } else {
         // swings: single price
         if(MathAbs(price - g_levels[i].priceRef) <= g_point * 5) touched = true;
      }
      if(touched){
         if(!g_levels[i].mitigated) g_levels[i].mitigations = 1;
         else                       g_levels[i].mitigations++;
         g_levels[i].mitigated = true;
         if(g_levels[i].mitigations >= 2) g_levels[i].active = false;
      }
   }
}

// v2.0.34 (audit point 2): core swing/trend/BOS/CHOCH computation, factored
// out so it can be run independently per timeframe (into any SNXSStructure
// instance) instead of one global that different callers/timeframes clobber.
//
// Trend hysteresis: previously `trend` was fully recomputed from scratch
// every call and reset to 0 (RANGE) whenever the last-2-swings read was
// ambiguous, causing it to flip UP/DOWN/RANGE on nearly every bar even in a
// clean trend (audit finding). Now an ambiguous read simply KEEPS the prior
// trend instead of collapsing it - trend only changes on a clear opposite
// HH+HL / LH+LL confirmation.
//
// BOS vs CHOCH: previously a single close-beyond-swing break set `bosUp`
// unconditionally, AND ALSO set `chochUp` as an add-on if trend was already
// down - so the exact same break was reported as both a "continuation" and
// a "reversal" simultaneously. Now they're mutually exclusive: a break is
// BOS only when it agrees with (or extends) the trend in place BEFORE the
// break, and CHOCH only when it contradicts it.
void NXS_ComputeStructureCore(string sym, ENUM_TIMEFRAMES tf, int wing, int scan, SNXSStructure &st, bool addLevels){
   // 1. find last 2 swing highs and lows
   double sH[2] = {0,0}; double sL[2] = {0,0};
   datetime sHt[2] = {0,0}; datetime sLt[2] = {0,0};
   int hCount = 0, lCount = 0;
   for(int i = wing + 1; i < scan; i++){
      if(hCount < 2 && NXS_IsSwingHigh(sym, tf, i, wing)){
         sH[hCount]  = iHigh(sym, tf, i);
         sHt[hCount] = iTime(sym, tf, i);
         hCount++;
         if(addLevels) NXS_AddLevel(NXS_LVL_SWING_HIGH, sH[hCount-1], sH[hCount-1], sH[hCount-1], sHt[hCount-1]);
      }
      if(lCount < 2 && NXS_IsSwingLow(sym, tf, i, wing)){
         sL[lCount]  = iLow(sym, tf, i);
         sLt[lCount] = iTime(sym, tf, i);
         lCount++;
         if(addLevels) NXS_AddLevel(NXS_LVL_SWING_LOW, sL[lCount-1], sL[lCount-1], sL[lCount-1], sLt[lCount-1]);
      }
      if(hCount >= 2 && lCount >= 2) break;
   }
   if(hCount >= 2){ st.lastSwingHigh = sH[0]; st.prevSwingHigh = sH[1]; }
   if(lCount >= 2){ st.lastSwingLow  = sL[0]; st.prevSwingLow  = sL[1]; }

   // 2. determine trend candidate from the confirmed swing sequence
   int trendCandidate = 0;
   bool clearSignal = false;
   if(hCount >= 2 && lCount >= 2){
      bool hh = (sH[0] > sH[1]);
      bool hl = (sL[0] > sL[1]);
      bool lh = (sH[0] < sH[1]);
      bool ll = (sL[0] < sL[1]);
      if(hh && hl)      { trendCandidate = 1;  clearSignal = true; }
      else if(lh && ll) { trendCandidate = -1; clearSignal = true; }
   }
   // Hysteresis: only adopt the candidate when it's an unambiguous HH+HL or
   // LH+LL read; otherwise keep whatever trend was already stored.
   int trendBefore = st.trend;
   if(clearSignal) st.trend = trendCandidate;

   // 3/4. BOS (continuation, agrees with trendBefore) vs CHOCH (reversal,
   // contradicts trendBefore) - mutually exclusive per break direction.
   double c1 = iClose(sym, tf, 1);
   st.bosUp = false; st.bosDown = false; st.chochUp = false; st.chochDown = false;
   if(st.lastSwingHigh > 0 && c1 > st.lastSwingHigh){
      if(trendBefore == -1) st.chochUp = true;
      else                  st.bosUp   = true;
   }
   if(st.lastSwingLow > 0 && c1 < st.lastSwingLow){
      if(trendBefore == 1) st.chochDown = true;
      else                 st.bosDown   = true;
   }
}

void NXS_UpdateStructure(string sym, ENUM_TIMEFRAMES tf){
   if(!InpUseStructure) return;
   NXS_ComputeStructureCore(sym, tf, InpSwingWing, 60, g_struct, true);

   // order blocks, FVG, trendlines, mitigation (entry-TF only, unchanged)
   NXS_DetectOrderBlocks(sym, tf);
   NXS_DetectFVG(sym, tf);
   NXS_UpdateTrendline(sym, tf);
   NXS_MitigateLevels(sym);

   string trendStr = (g_struct.trend == 1 ? "UP" : (g_struct.trend == -1 ? "DN" : "RANGE"));
   g_struct.summary = StringFormat("trend=%s BOSup=%d CHOCHup=%d sHi=%.2f sLo=%.2f lvls=%d",
                                    trendStr, (int)g_struct.bosUp, (int)g_struct.chochUp,
                                    g_struct.lastSwingHigh, g_struct.lastSwingLow, g_levelCount);
   if(InpDebugLog) Print("[STRUCT] ", g_struct.summary);
}

// v2.0.34: independent H1 structure context (audit point 2) - no level/OB/
// FVG side effects (those stay entry-TF-only), just its own trend/BOS/CHOCH
// so strategies wanting higher-TF confirmation read genuine H1 state
// instead of the entry-TF struct mislabeled as H1.
void NXS_UpdateStructureH1(string sym){
   if(!InpUseStructure) return;
   NXS_ComputeStructureCore(sym, PERIOD_H1, InpSwingWing, 60, g_structH1, false);
   if(InpDebugLog){
      string trendStr = (g_structH1.trend == 1 ? "UP" : (g_structH1.trend == -1 ? "DN" : "RANGE"));
      PrintFormat("[STRUCT H1] trend=%s CHOCHup=%d CHOCHdn=%d sHi=%.2f sLo=%.2f",
                  trendStr, (int)g_structH1.chochUp, (int)g_structH1.chochDown,
                  g_structH1.lastSwingHigh, g_structH1.lastSwingLow);
   }
}

int NXS_ActiveLevelCount(){
   int n = 0;
   for(int i = 0; i < g_levelCount; i++) if(g_levels[i].active) n++;
   return n;
}

string NXS_StructTrendName(int t){
   if(t == 1) return "UP";
   if(t == -1) return "DN";
   return "RANGE";
}

#endif
