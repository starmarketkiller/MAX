//+------------------------------------------------------------------+
//|  NXS_BjorgumZones.mqh                                             |
//|  NEXUS Visual Suite v2.0.4                                        |
//|                                                                   |
//|  Computes true Bjorgum-style key zones:                           |
//|  - Pivot-based untouched fractals (3-bar fractals)                |
//|  - "Hot" zones: clusters of 2+ fractals within atrTol             |
//|  - Direction-aware (resistance vs support)                        |
//|                                                                   |
//|  Pure visual indicator helper - NO trading logic.                 |
//+------------------------------------------------------------------+
#ifndef __NXS_BJORGUM_ZONES_MQH__
#define __NXS_BJORGUM_ZONES_MQH__

#define NXS_BJ_MAX_ZONES 12

struct SNXSBjZone {
   double   priceTop;
   double   priceBot;
   datetime tAnchor;
   int      hits;            // number of fractals clustering
   bool     isResistance;    // true = supply, false = demand
   bool     active;
};

SNXSBjZone g_bjZones[NXS_BJ_MAX_ZONES];
int        g_bjZoneCount = 0;

bool _bj_isFractalHigh(string sym, ENUM_TIMEFRAMES tf, int shift){
   double h0 = iHigh(sym, tf, shift);
   if(h0 <= 0) return false;
   double hL1 = iHigh(sym, tf, shift+1);
   double hL2 = iHigh(sym, tf, shift+2);
   double hR1 = iHigh(sym, tf, shift-1);
   double hR2 = iHigh(sym, tf, shift-2);
   return (h0 > hL1 && h0 > hL2 && h0 > hR1 && h0 > hR2);
}

bool _bj_isFractalLow(string sym, ENUM_TIMEFRAMES tf, int shift){
   double l0 = iLow(sym, tf, shift);
   if(l0 <= 0) return false;
   double lL1 = iLow(sym, tf, shift+1);
   double lL2 = iLow(sym, tf, shift+2);
   double lR1 = iLow(sym, tf, shift-1);
   double lR2 = iLow(sym, tf, shift-2);
   return (l0 < lL1 && l0 < lL2 && l0 < lR1 && l0 < lR2);
}

// Try to add a fractal to an existing cluster, otherwise create new zone
void _bj_addOrMerge(double price, datetime t, bool isResistance, double atrTol){
   for(int i = 0; i < g_bjZoneCount; i++){
      if(!g_bjZones[i].active) continue;
      if(g_bjZones[i].isResistance != isResistance) continue;
      double mid = (g_bjZones[i].priceTop + g_bjZones[i].priceBot) * 0.5;
      if(MathAbs(price - mid) < atrTol){
         g_bjZones[i].priceTop = MathMax(g_bjZones[i].priceTop, price);
         g_bjZones[i].priceBot = MathMin(g_bjZones[i].priceBot, price);
         g_bjZones[i].hits++;
         if(t > g_bjZones[i].tAnchor) g_bjZones[i].tAnchor = t;
         return;
      }
   }
   if(g_bjZoneCount >= NXS_BJ_MAX_ZONES){
      // replace the weakest (least hits)
      int idx = 0; int minHits = g_bjZones[0].hits;
      for(int i = 1; i < NXS_BJ_MAX_ZONES; i++){
         if(g_bjZones[i].hits < minHits){ minHits = g_bjZones[i].hits; idx = i; }
      }
      g_bjZones[idx].priceTop     = price + atrTol * 0.3;
      g_bjZones[idx].priceBot     = price - atrTol * 0.3;
      g_bjZones[idx].tAnchor      = t;
      g_bjZones[idx].hits         = 1;
      g_bjZones[idx].isResistance = isResistance;
      g_bjZones[idx].active       = true;
      return;
   }
   g_bjZones[g_bjZoneCount].priceTop     = price + atrTol * 0.3;
   g_bjZones[g_bjZoneCount].priceBot     = price - atrTol * 0.3;
   g_bjZones[g_bjZoneCount].tAnchor      = t;
   g_bjZones[g_bjZoneCount].hits         = 1;
   g_bjZones[g_bjZoneCount].isResistance = isResistance;
   g_bjZones[g_bjZoneCount].active       = true;
   g_bjZoneCount++;
}

void NXS_BJ_Compute(string sym, ENUM_TIMEFRAMES tf, int lookback, double atr){
   // reset
   for(int i = 0; i < NXS_BJ_MAX_ZONES; i++){
      g_bjZones[i].active = false;
      g_bjZones[i].hits   = 0;
   }
   g_bjZoneCount = 0;
   if(atr <= 0) return;
   double atrTol = atr * 0.6;
   for(int s = 3; s < lookback - 2; s++){
      if(_bj_isFractalHigh(sym, tf, s)){
         _bj_addOrMerge(iHigh(sym, tf, s), iTime(sym, tf, s), true,  atrTol);
      }
      if(_bj_isFractalLow(sym, tf, s)){
         _bj_addOrMerge(iLow(sym, tf, s),  iTime(sym, tf, s), false, atrTol);
      }
   }
}

// Quasimodo detector (HH then deeper LL then HL above prior LH) - pure visual
struct SNXSQuasimodo {
   bool   detected;
   int    direction;     // +1 bullish QM, -1 bearish QM
   double anchorPrice;
   datetime anchorTime;
};

SNXSQuasimodo NXS_Quasimodo_Detect(string sym, ENUM_TIMEFRAMES tf, int lookback){
   SNXSQuasimodo q; q.detected = false; q.direction = 0;
   q.anchorPrice = 0; q.anchorTime = 0;
   if(lookback < 20) lookback = 20;
   // Find last 3 swing highs and 3 swing lows in 4-bar fractal grid
   double hs[3]; datetime ths[3]; int hc = 0;
   double ls[3]; datetime tls[3]; int lc = 0;
   for(int s = 3; s < lookback - 2 && (hc < 3 || lc < 3); s++){
      if(hc < 3 && _bj_isFractalHigh(sym, tf, s)){
         hs[hc]  = iHigh(sym, tf, s);
         ths[hc] = iTime(sym, tf, s);
         hc++;
      }
      if(lc < 3 && _bj_isFractalLow(sym, tf, s)){
         ls[lc]  = iLow(sym, tf, s);
         tls[lc] = iTime(sym, tf, s);
         lc++;
      }
   }
   if(hc < 3 || lc < 3) return q;
   // Bearish Quasimodo: HH(2) → LH(1) → LL(0) with LL > prev_low(2)
   // Pattern detection (simplified): h2 > h1 < h0  AND  l1 < l2 < l0
   if(hs[0] < hs[1] && hs[1] > hs[2] && ls[0] > ls[1] && ls[1] < ls[2]){
      q.detected     = true;
      q.direction    = -1;
      q.anchorPrice  = hs[1];   // the LH (neckline area)
      q.anchorTime   = ths[1];
   } else if(hs[0] > hs[1] && hs[1] < hs[2] && ls[0] < ls[1] && ls[1] > ls[2]){
      q.detected     = true;
      q.direction    = +1;
      q.anchorPrice  = ls[1];   // the HL
      q.anchorTime   = tls[1];
   }
   return q;
}

#endif
