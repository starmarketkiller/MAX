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

SNXSStructure g_struct;
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

void NXS_UpdateStructure(string sym, ENUM_TIMEFRAMES tf){
   if(!InpUseStructure) return;
   int wing = InpSwingWing;
   int scan = 60;

   // 1. find last 2 swing highs and lows
   double sH[2] = {0,0}; double sL[2] = {0,0};
   datetime sHt[2] = {0,0}; datetime sLt[2] = {0,0};
   int hCount = 0, lCount = 0;
   for(int i = wing + 1; i < scan; i++){
      if(hCount < 2 && NXS_IsSwingHigh(sym, tf, i, wing)){
         sH[hCount]  = iHigh(sym, tf, i);
         sHt[hCount] = iTime(sym, tf, i);
         hCount++;
         // also add as level
         NXS_AddLevel(NXS_LVL_SWING_HIGH, sH[hCount-1], sH[hCount-1], sH[hCount-1], sHt[hCount-1]);
      }
      if(lCount < 2 && NXS_IsSwingLow(sym, tf, i, wing)){
         sL[lCount]  = iLow(sym, tf, i);
         sLt[lCount] = iTime(sym, tf, i);
         lCount++;
         NXS_AddLevel(NXS_LVL_SWING_LOW, sL[lCount-1], sL[lCount-1], sL[lCount-1], sLt[lCount-1]);
      }
      if(hCount >= 2 && lCount >= 2) break;
   }
   if(hCount >= 2){ g_struct.lastSwingHigh = sH[0]; g_struct.prevSwingHigh = sH[1]; }
   if(lCount >= 2){ g_struct.lastSwingLow  = sL[0]; g_struct.prevSwingLow  = sL[1]; }

   // 2. determine trend
   int trend = 0;
   if(hCount >= 2 && lCount >= 2){
      bool hh = (sH[0] > sH[1]);
      bool hl = (sL[0] > sL[1]);
      bool lh = (sH[0] < sH[1]);
      bool ll = (sL[0] < sL[1]);
      if(hh && hl)      trend = 1;
      else if(lh && ll) trend = -1;
      else              trend = 0;
   }

   // 3. BOS detection (close beyond last swing)
   double c1 = iClose(sym, tf, 1);
   g_struct.bosUp = false; g_struct.bosDown = false;
   if(g_struct.lastSwingHigh > 0 && c1 > g_struct.lastSwingHigh) g_struct.bosUp   = true;
   if(g_struct.lastSwingLow  > 0 && c1 < g_struct.lastSwingLow)  g_struct.bosDown = true;

   // 4. CHOCH detection (opposite direction break)
   g_struct.chochUp = false; g_struct.chochDown = false;
   if(g_struct.trend == -1 && g_struct.bosUp)   g_struct.chochUp   = true;
   if(g_struct.trend ==  1 && g_struct.bosDown) g_struct.chochDown = true;

   g_struct.trend = trend;

   // 5. order blocks, FVG, trendlines, mitigation
   NXS_DetectOrderBlocks(sym, tf);
   NXS_DetectFVG(sym, tf);
   NXS_UpdateTrendline(sym, tf);
   NXS_MitigateLevels(sym);

   // 6. summary
   string trendStr = (g_struct.trend == 1 ? "UP" : (g_struct.trend == -1 ? "DN" : "RANGE"));
   g_struct.summary = StringFormat("trend=%s BOSup=%d CHOCHup=%d sHi=%.2f sLo=%.2f lvls=%d",
                                    trendStr, (int)g_struct.bosUp, (int)g_struct.chochUp,
                                    g_struct.lastSwingHigh, g_struct.lastSwingLow, g_levelCount);
   if(InpDebugLog) Print("[STRUCT] ", g_struct.summary);
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
