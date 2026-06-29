//+------------------------------------------------------------------+
//|                                       NEXUS_VisualSuite_v2.mq5    |
//|                                  Italian Traders Club - NEXUS     |
//|                                                                   |
//|  Companion INDICATOR for NEXUS EA v2.0.x                          |
//|  Reads EA state via Global Variables (set by NXS_ExportStateToGV) |
//|  + draws on chart: OB, FVG, IFVG, OTE, Sweep levels, SNR,         |
//|                    Trendline, Bjorgum Zones, Quasimodo, Killzone, |
//|                    Velocity/Pressure HUD panel.                   |
//|                                                                   |
//|  THREE LAYERS:                                                    |
//|   - L1 EA-LINKED   : reads GV exported by EA                      |
//|   - L2 VISUAL-ONLY : computed locally (Bjorgum, Quasimodo, KZ)    |
//|   - L3 FUTURE      : placeholder slots (heatmap, multi-TF)        |
//|                                                                   |
//|  NO trading - no orders - safe to run alongside the EA.           |
//+------------------------------------------------------------------+
#property copyright "Italian Traders Club"
#property link      "https://nexus.local"
#property version   "2.04"
#property strict
#property indicator_chart_window
#property indicator_plots 0
#property description "NEXUS Visual Suite v2.0.4 - Companion to NEXUS EA"
#property description "Reads EA state (GV) + draws SMC/ICT context + HUD"

#include <NEXUS_v1\NXS_VisualObjects.mqh>
#include <NEXUS_v1\NXS_BjorgumZones.mqh>

//+------------------------------------------------------------------+
//| Inputs                                                            |
//+------------------------------------------------------------------+
input group "=== LAYER 1 - EA Linked (reads GV) ==="
input bool InpShowHUD          = true;   // HUD panel (velocity/pressure/strat/blocker)
input bool InpShowOTE          = true;   // OTE band 0.62-0.79 from EA
input bool InpShowAsiaPDH      = true;   // Asia H/L + PDH/PDL from EA
input bool InpShowReaction     = true;   // Reaction marker

input group "=== LAYER 1 - Computed Locally (chart price action) ==="
input bool InpShowOB           = true;   // Order Blocks
input bool InpShowFVG          = true;   // Fair Value Gaps
input bool InpShowIFVG         = true;   // Inverted FVG
input bool InpShowTrendline    = true;   // Auto trendline
input bool InpShowSNR          = true;   // Malaysian SNR levels
input bool InpShowMultiLayer   = true;   // Trend LTF/MTF/HTF mini-panel
input bool InpShowStatsPanel   = true;   // v2.0.5 strategy stats mini-panel
input int  InpStatsPanelTopN   = 6;      // top N strategies by called

input group "=== LAYER 2 - Visual Only (not used by EA) ==="
input bool InpShowBjorgum      = true;   // Bjorgum key zones
input bool InpShowQuasimodo    = true;   // Quasimodo pattern
input bool InpShowKillzone     = true;   // London/NY Silver Bullet windows

input group "=== LAYER 3 - Future / Experimental ==="
input bool InpShowHeatmap      = false;  // (reserved) multi-TF heatmap
input bool InpShowFlowProfile  = false;  // (reserved) volume profile

input group "=== Detection Parameters ==="
input ENUM_TIMEFRAMES InpTFEntry  = PERIOD_M15;
input ENUM_TIMEFRAMES InpTFMedium = PERIOD_H1;
input ENUM_TIMEFRAMES InpTFHigh   = PERIOD_H4;
input int    InpLookback          = 80;    // bars to scan
input double InpOBDisplacement    = 1.2;   // ATR multiplier for OB displacement
input double InpFVGMinBody        = 0.3;   // ATR multiplier for FVG body
input int    InpSwingWing         = 3;     // swing wing for fractals
input int    InpMaxObjects        = 60;    // hard cap for chart objects

input group "=== HUD Style ==="
input int    InpHUD_X             = 10;
input int    InpHUD_Y             = 20;
input int    InpHUD_Corner        = CORNER_RIGHT_UPPER;
input int    InpHUD_Font          = 9;
input color  InpHUD_Bg            = clrBlack;
input color  InpHUD_FgPos         = clrLime;
input color  InpHUD_FgNeg         = clrTomato;
input color  InpHUD_FgNeu         = clrSilver;

input group "=== Colors ==="
input color  InpClr_OB_Bull       = C'40,140,90';
input color  InpClr_OB_Bear       = C'170,60,70';
input color  InpClr_FVG_Bull      = C'60,180,120';
input color  InpClr_FVG_Bear      = C'200,80,90';
input color  InpClr_IFVG          = C'180,120,40';
input color  InpClr_OTE           = C'120,150,220';
input color  InpClr_Sweep         = C'255,200,60';
input color  InpClr_PDH_PDL       = C'180,180,200';
input color  InpClr_Trendline     = C'90,170,220';
input color  InpClr_SNR           = C'200,100,200';
input color  InpClr_Bjorgum_Res   = C'220,90,90';
input color  InpClr_Bjorgum_Sup   = C'90,200,90';
input color  InpClr_Quasimodo     = C'255,140,40';
input color  InpClr_Killzone      = C'70,70,160';

//+------------------------------------------------------------------+
//| State                                                             |
//+------------------------------------------------------------------+
string   g_sym;
double   g_atr_local = 0;
datetime g_lastBar   = 0;
int      g_hATR_local = INVALID_HANDLE;

//+------------------------------------------------------------------+
//| GV Helpers (Layer 1)                                              |
//+------------------------------------------------------------------+
string _gv(string key){ return "NXS_" + g_sym + "_" + key; }

double NXS_VS_GV(string key, double def){
   string n = _gv(key);
   if(GlobalVariableCheck(n)) return GlobalVariableGet(n);
   return def;
}

string NXS_VS_StrategyName(int code){
   switch(code){
      case 0:  return "ADX_RSI";
      case 1:  return "BOLLINGER";
      case 2:  return "MACD";
      case 3:  return "SAR";
      case 4:  return "TSI";
      case 5:  return "BJORGUM";
      case 6:  return "LIQ_SWEEP";
      case 7:  return "FVG_CONT";
      case 8:  return "BREAKOUT_ACC";
      case 9:  return "LONDON_BO";
      case 10: return "EMA_PULLBACK";
      case 11: return "BB_SQUEEZE";
      case 12: return "ICHIMOKU";
      case 13: return "RSI_DIV";
      case 14: return "ORDER_BLOCK";
      case 15: return "STRUCT_REACT";
   }
   return "NONE";
}

string NXS_VS_VelName(int v){
   switch(v){
      case 1: return "BULL";
      case 2: return "BEAR";
      case 3: return "BULL_PB";
      case 4: return "BEAR_PB";
   }
   return "NEUTRAL";
}

string NXS_VS_BlockerName(int b){
   switch(b){
      case 0:  return "NONE";
      case 1:  return "NO_SIGNAL";
      case 2:  return "COOLDOWN";
      case 3:  return "MTF";
      case 4:  return "HTF";
      case 5:  return "VELOCITY";
      case 6:  return "NEWS";
      case 7:  return "SPREAD";
      case 8:  return "PROTECTIONS";
      case 9:  return "SCORE_BELOW";
      case 10: return "PREFLIGHT";
      case 11: return "LICENSE";
      case 12: return "PAUSED";
      case 13: return "SEND_FAILED";
   }
   return "?";
}

string NXS_VS_TrendName(int t){ return t==1 ? "UP" : (t==-1 ? "DN" : "RANGE"); }

//+------------------------------------------------------------------+
//| Local detectors (Layer 1 visual + Layer 2)                        |
//+------------------------------------------------------------------+
bool _vs_isSwingHigh(int s, int wing){
   double h = iHigh(g_sym, InpTFEntry, s);
   for(int k = 1; k <= wing; k++){
      if(iHigh(g_sym, InpTFEntry, s+k) >= h) return false;
      if(iHigh(g_sym, InpTFEntry, s-k) >= h) return false;
   }
   return true;
}

bool _vs_isSwingLow(int s, int wing){
   double l = iLow(g_sym, InpTFEntry, s);
   for(int k = 1; k <= wing; k++){
      if(iLow(g_sym, InpTFEntry, s+k) <= l) return false;
      if(iLow(g_sym, InpTFEntry, s-k) <= l) return false;
   }
   return true;
}

//+------------------------------------------------------------------+
//| Draw: Order Blocks (Layer 1 visual)                               |
//+------------------------------------------------------------------+
void NXS_VS_DrawOrderBlocks(){
   NXS_VS_CleanupCategory("OB_");
   if(g_atr_local <= 0) return;
   int drawn = 0;
   for(int i = 3; i < InpLookback && drawn < 8; i++){
      double o = iOpen (g_sym, InpTFEntry, i);
      double c = iClose(g_sym, InpTFEntry, i);
      double moveUp = iClose(g_sym, InpTFEntry, i-1) - iOpen(g_sym, InpTFEntry, i-1);
      double moveDn = iOpen (g_sym, InpTFEntry, i-1) - iClose(g_sym, InpTFEntry, i-1);
      datetime t1 = iTime(g_sym, InpTFEntry, i);
      datetime t2 = iTime(g_sym, InpTFEntry, 0) + PeriodSeconds(InpTFEntry) * 5;
      if(c < o && moveUp > g_atr_local * InpOBDisplacement){
         NXS_VS_DrawRectangle("OB_BULL_" + IntegerToString(i), t1, MathMax(o,c), t2, MathMin(o,c),
                              InpClr_OB_Bull, true, STYLE_SOLID, 1);
         NXS_VS_DrawText("OB_BULL_TAG_" + IntegerToString(i), t1, MathMin(o,c), "OB+", InpClr_OB_Bull, 7);
         drawn++;
      }
      if(c > o && moveDn > g_atr_local * InpOBDisplacement){
         NXS_VS_DrawRectangle("OB_BEAR_" + IntegerToString(i), t1, MathMax(o,c), t2, MathMin(o,c),
                              InpClr_OB_Bear, true, STYLE_SOLID, 1);
         NXS_VS_DrawText("OB_BEAR_TAG_" + IntegerToString(i), t1, MathMax(o,c), "OB-", InpClr_OB_Bear, 7);
         drawn++;
      }
   }
}

//+------------------------------------------------------------------+
//| Draw: FVG (Layer 1 visual)                                        |
//+------------------------------------------------------------------+
void NXS_VS_DrawFVG(){
   NXS_VS_CleanupCategory("FVG_");
   if(g_atr_local <= 0) return;
   int drawn = 0;
   for(int i = 3; i < InpLookback && drawn < 8; i++){
      double hPrev = iHigh(g_sym, InpTFEntry, i+1);
      double lPrev = iLow (g_sym, InpTFEntry, i+1);
      double oMid  = iOpen (g_sym, InpTFEntry, i);
      double cMid  = iClose(g_sym, InpTFEntry, i);
      double hNext = iHigh(g_sym, InpTFEntry, i-1);
      double lNext = iLow (g_sym, InpTFEntry, i-1);
      double body  = MathAbs(cMid - oMid);
      if(body < g_atr_local * InpFVGMinBody) continue;
      datetime t1 = iTime(g_sym, InpTFEntry, i+1);
      datetime t2 = iTime(g_sym, InpTFEntry, 0) + PeriodSeconds(InpTFEntry) * 5;
      if(lNext > hPrev){
         NXS_VS_DrawRectangle("FVG_BULL_" + IntegerToString(i), t1, lNext, t2, hPrev,
                              InpClr_FVG_Bull, true, STYLE_DOT, 1);
         drawn++;
      }
      if(hNext < lPrev){
         NXS_VS_DrawRectangle("FVG_BEAR_" + IntegerToString(i), t1, lPrev, t2, hNext,
                              InpClr_FVG_Bear, true, STYLE_DOT, 1);
         drawn++;
      }
   }
}

//+------------------------------------------------------------------+
//| Draw: IFVG ghost (last 4 detected, no persistence in EA)          |
//+------------------------------------------------------------------+
void NXS_VS_DrawIFVG(){
   NXS_VS_CleanupCategory("IFVG_");
   if(g_atr_local <= 0) return;
   int drawn = 0;
   for(int i = 4; i < InpLookback && drawn < 4; i++){
      double h2 = iHigh(g_sym, InpTFEntry, i+1), l2 = iLow(g_sym, InpTFEntry, i+1);
      double h3 = iHigh(g_sym, InpTFEntry, i+2), l3 = iLow(g_sym, InpTFEntry, i+2);
      double c1 = iClose(g_sym, InpTFEntry, i);
      double atr = g_atr_local;
      datetime t1 = iTime(g_sym, InpTFEntry, i+2);
      datetime t2 = iTime(g_sym, InpTFEntry, 0);
      // Bullish FVG inverted DOWN
      if(l3 > h2 + atr * 0.2 && c1 < h2){
         NXS_VS_DrawRectangle("IFVG_DN_" + IntegerToString(i), t1, l3, t2, h2,
                              InpClr_IFVG, false, STYLE_DASHDOT, 1);
         NXS_VS_DrawText("IFVG_DN_TAG_" + IntegerToString(i), t1, l3, "IFVG↓", InpClr_IFVG, 7);
         drawn++;
      }
      // Bearish FVG inverted UP
      if(h3 < l2 - atr * 0.2 && c1 > l2){
         NXS_VS_DrawRectangle("IFVG_UP_" + IntegerToString(i), t1, l2, t2, h3,
                              InpClr_IFVG, false, STYLE_DASHDOT, 1);
         NXS_VS_DrawText("IFVG_UP_TAG_" + IntegerToString(i), t1, h3, "IFVG↑", InpClr_IFVG, 7);
         drawn++;
      }
   }
}

//+------------------------------------------------------------------+
//| Draw: OTE band 0.62 / 0.705 / 0.79 (Layer 1 - EA linked)          |
//+------------------------------------------------------------------+
void NXS_VS_DrawOTE(){
   NXS_VS_CleanupCategory("OTE_");
   double ote62  = NXS_VS_GV("ote62",  0);
   double ote705 = NXS_VS_GV("ote705", 0);
   double ote79  = NXS_VS_GV("ote79",  0);
   double sH     = NXS_VS_GV("fib_swingHi", 0);
   double sL     = NXS_VS_GV("fib_swingLo", 0);
   if(ote62 <= 0 || ote79 <= 0) return;
   datetime t1 = iTime(g_sym, InpTFEntry, InpLookback);
   datetime t2 = iTime(g_sym, InpTFEntry, 0) + PeriodSeconds(InpTFEntry) * 6;
   NXS_VS_DrawRectangle("OTE_BAND", t1, MathMax(ote62, ote79), t2, MathMin(ote62, ote79),
                        InpClr_OTE, true, STYLE_SOLID, 1);
   NXS_VS_DrawHLine("OTE_705", ote705, InpClr_OTE, STYLE_DOT, 1, "OTE 0.705");
   if(sH > 0) NXS_VS_DrawHLine("OTE_SH", sH, InpClr_OTE, STYLE_DASH, 1, "Swing Hi");
   if(sL > 0) NXS_VS_DrawHLine("OTE_SL", sL, InpClr_OTE, STYLE_DASH, 1, "Swing Lo");
}

//+------------------------------------------------------------------+
//| Draw: PDH/PDL/Asia (Layer 1 - EA linked)                          |
//+------------------------------------------------------------------+
void NXS_VS_DrawAsiaPDH(){
   NXS_VS_CleanupCategory("LIQ_");
   double pdh = NXS_VS_GV("pdh", 0);
   double pdl = NXS_VS_GV("pdl", 0);
   double aH  = NXS_VS_GV("asian_hi", 0);
   double aL  = NXS_VS_GV("asian_lo", 0);
   if(pdh > 0) NXS_VS_DrawHLine("LIQ_PDH", pdh, InpClr_PDH_PDL, STYLE_SOLID, 1, "PDH");
   if(pdl > 0) NXS_VS_DrawHLine("LIQ_PDL", pdl, InpClr_PDH_PDL, STYLE_SOLID, 1, "PDL");
   if(aH  > 0) NXS_VS_DrawHLine("LIQ_AsiaH", aH, InpClr_Sweep, STYLE_DASH, 1, "Asia H");
   if(aL  > 0) NXS_VS_DrawHLine("LIQ_AsiaL", aL, InpClr_Sweep, STYLE_DASH, 1, "Asia L");
}

//+------------------------------------------------------------------+
//| Draw: Trendline (Layer 1 visual - auto detected)                  |
//+------------------------------------------------------------------+
void NXS_VS_DrawTrendline(){
   NXS_VS_CleanupCategory("TL_");
   if(g_atr_local <= 0) return;
   // last 2 swing highs + 2 swing lows
   int hi[2] = {-1,-1}, lo[2] = {-1,-1}; int hc = 0, lc = 0;
   for(int s = InpSwingWing+1; s < InpLookback && (hc<2 || lc<2); s++){
      if(hc<2 && _vs_isSwingHigh(s, InpSwingWing)){ hi[hc++] = s; }
      if(lc<2 && _vs_isSwingLow (s, InpSwingWing)){ lo[lc++] = s; }
   }
   if(hc == 2){
      double p1 = iHigh(g_sym, InpTFEntry, hi[1]); datetime t1 = iTime(g_sym, InpTFEntry, hi[1]);
      double p2 = iHigh(g_sym, InpTFEntry, hi[0]); datetime t2 = iTime(g_sym, InpTFEntry, hi[0]);
      NXS_VS_DrawTrendline("TL_RES", t1, p1, t2, p2, InpClr_Trendline, STYLE_SOLID, 1, true);
   }
   if(lc == 2){
      double p1 = iLow(g_sym, InpTFEntry, lo[1]); datetime t1 = iTime(g_sym, InpTFEntry, lo[1]);
      double p2 = iLow(g_sym, InpTFEntry, lo[0]); datetime t2 = iTime(g_sym, InpTFEntry, lo[0]);
      NXS_VS_DrawTrendline("TL_SUP", t1, p1, t2, p2, InpClr_Trendline, STYLE_SOLID, 1, true);
   }
}

//+------------------------------------------------------------------+
//| Draw: Malaysian SNR (Layer 1 visual)                              |
//+------------------------------------------------------------------+
void NXS_VS_DrawSNR(){
   NXS_VS_CleanupCategory("SNR_");
   int idxH4Hi = iHighest(g_sym, InpTFHigh, MODE_CLOSE, 12, 1);
   int idxH4Lo = iLowest (g_sym, InpTFHigh, MODE_CLOSE, 12, 1);
   double h4Hi = iClose(g_sym, InpTFHigh, idxH4Hi);
   double h4Lo = iClose(g_sym, InpTFHigh, idxH4Lo);
   if(h4Hi > 0) NXS_VS_DrawHLine("SNR_H4Hi", h4Hi, InpClr_SNR, STYLE_DASH, 2, "SNR H4 R");
   if(h4Lo > 0) NXS_VS_DrawHLine("SNR_H4Lo", h4Lo, InpClr_SNR, STYLE_DASH, 2, "SNR H4 S");
   int idxW1Hi = iHighest(g_sym, PERIOD_W1, MODE_CLOSE, 8, 1);
   int idxW1Lo = iLowest (g_sym, PERIOD_W1, MODE_CLOSE, 8, 1);
   double w1Hi = iClose(g_sym, PERIOD_W1, idxW1Hi);
   double w1Lo = iClose(g_sym, PERIOD_W1, idxW1Lo);
   if(w1Hi > 0) NXS_VS_DrawHLine("SNR_W1Hi", w1Hi, InpClr_SNR, STYLE_DASHDOTDOT, 2, "SNR W1 R");
   if(w1Lo > 0) NXS_VS_DrawHLine("SNR_W1Lo", w1Lo, InpClr_SNR, STYLE_DASHDOTDOT, 2, "SNR W1 S");
}

//+------------------------------------------------------------------+
//| Draw: Bjorgum Zones (Layer 2)                                     |
//+------------------------------------------------------------------+
void NXS_VS_DrawBjorgum(){
   NXS_VS_CleanupCategory("BJ_");
   NXS_BJ_Compute(g_sym, InpTFEntry, InpLookback, g_atr_local);
   for(int i = 0; i < g_bjZoneCount; i++){
      if(!g_bjZones[i].active) continue;
      if(g_bjZones[i].hits < 2) continue;     // require cluster of 2+
      color c = g_bjZones[i].isResistance ? InpClr_Bjorgum_Res : InpClr_Bjorgum_Sup;
      datetime t1 = g_bjZones[i].tAnchor;
      datetime t2 = iTime(g_sym, InpTFEntry, 0) + PeriodSeconds(InpTFEntry) * 6;
      NXS_VS_DrawRectangle("BJ_Z" + IntegerToString(i),
                           t1, g_bjZones[i].priceTop, t2, g_bjZones[i].priceBot,
                           c, false, STYLE_SOLID, 2);
      NXS_VS_DrawText("BJ_T" + IntegerToString(i), t1,
                      g_bjZones[i].isResistance ? g_bjZones[i].priceTop : g_bjZones[i].priceBot,
                      "BJ x" + IntegerToString(g_bjZones[i].hits), c, 7);
   }
}

//+------------------------------------------------------------------+
//| Draw: Quasimodo (Layer 2)                                         |
//+------------------------------------------------------------------+
void NXS_VS_DrawQuasimodo(){
   NXS_VS_CleanupCategory("QM_");
   SNXSQuasimodo q = NXS_Quasimodo_Detect(g_sym, InpTFEntry, InpLookback);
   if(!q.detected) return;
   datetime t2 = iTime(g_sym, InpTFEntry, 0) + PeriodSeconds(InpTFEntry) * 4;
   NXS_VS_DrawTrendline("QM_LINE", q.anchorTime, q.anchorPrice, t2, q.anchorPrice,
                        InpClr_Quasimodo, STYLE_DOT, 2, true);
   NXS_VS_DrawText("QM_TAG", q.anchorTime, q.anchorPrice,
                   q.direction > 0 ? "QM↑ neckline" : "QM↓ neckline",
                   InpClr_Quasimodo, 8);
}

//+------------------------------------------------------------------+
//| Draw: Killzone shading (Layer 2)                                  |
//+------------------------------------------------------------------+
void NXS_VS_DrawKillzone(){
   NXS_VS_CleanupCategory("KZ_");
   MqlDateTime mt; TimeToStruct(TimeCurrent(), mt);
   datetime midnight = TimeCurrent() - mt.hour*3600 - mt.min*60 - mt.sec;
   // London KZ 10-11 GMT, NY KZ 14-15 GMT
   datetime lo1 = midnight + 10*3600; datetime lo2 = midnight + 11*3600;
   datetime ny1 = midnight + 14*3600; datetime ny2 = midnight + 15*3600;
   double range_hi = iHigh(g_sym, InpTFEntry, iHighest(g_sym, InpTFEntry, MODE_HIGH, 20, 0));
   double range_lo = iLow (g_sym, InpTFEntry, iLowest (g_sym, InpTFEntry, MODE_LOW,  20, 0));
   if(range_hi <= 0 || range_lo <= 0) return;
   NXS_VS_DrawRectangle("KZ_LO", lo1, range_hi, lo2, range_lo, InpClr_Killzone, false, STYLE_DOT, 1);
   NXS_VS_DrawRectangle("KZ_NY", ny1, range_hi, ny2, range_lo, InpClr_Killzone, false, STYLE_DOT, 1);
   NXS_VS_DrawText("KZ_LO_T", lo1, range_hi, "LO-KZ", InpClr_Killzone, 7);
   NXS_VS_DrawText("KZ_NY_T", ny1, range_hi, "NY-KZ", InpClr_Killzone, 7);
}

//+------------------------------------------------------------------+
//| Draw: Stats Panel (v2.0.5 - reads CSV exported by EA)             |
//+------------------------------------------------------------------+
void NXS_VS_DrawStatsPanel(){
   if(!InpShowStatsPanel){ NXS_VS_CleanupCategory("STATS_"); return; }
   string fn = StringFormat("NEXUS\\nexus_stats_%s_%s.csv", g_sym, EnumToString(InpTFEntry));
   if(!FileIsExist(fn)){
      NXS_VS_DrawLabel("STATS_no", InpHUD_X, InpHUD_Y + 220, InpHUD_Corner,
                       "Stats: no CSV yet", clrGray, InpHUD_Font-1);
      return;
   }
   int fh = FileOpen(fn, FILE_READ|FILE_CSV|FILE_ANSI, ';');
   if(fh == INVALID_HANDLE) return;

   string names[32];  long called[32]; long setup[32];
   long   execs[32];  string health[32];
   int nrows = 0;
   bool headerSkipped = false;
   const int COLS = 40;
   string cells[40];

   while(!FileIsEnding(fh) && nrows < 32){
      for(int c = 0; c < COLS; c++){
         if(FileIsEnding(fh)){ cells[c] = ""; continue; }
         cells[c] = FileReadString(fh);
      }
      if(StringLen(cells[0]) == 0) break;
      if(!headerSkipped && cells[0] == "name"){ headerSkipped = true; continue; }
      names[nrows]  = cells[0];
      called[nrows] = (long)StringToInteger(cells[2]);
      setup[nrows]  = (long)StringToInteger(cells[3]);
      execs[nrows]  = (long)StringToInteger(cells[5]);
      health[nrows] = cells[COLS-1];
      nrows++;
   }
   FileClose(fh);
   if(nrows == 0){
      NXS_VS_DrawLabel("STATS_empty", InpHUD_X, InpHUD_Y + 220, InpHUD_Corner,
                       "Stats: empty CSV", clrGray, InpHUD_Font-1);
      return;
   }

   // Sort by called desc (simple insertion sort)
   for(int i = 1; i < nrows; i++){
      string n = names[i]; long ca = called[i], se = setup[i], ex = execs[i]; string he = health[i];
      int j = i - 1;
      while(j >= 0 && called[j] < ca){
         names[j+1]  = names[j];
         called[j+1] = called[j];
         setup[j+1]  = setup[j];
         execs[j+1]  = execs[j];
         health[j+1] = health[j];
         j--;
      }
      names[j+1]  = n;  called[j+1] = ca;
      setup[j+1]  = se; execs[j+1]  = ex;
      health[j+1] = he;
   }

   int topN = MathMin(InpStatsPanelTopN, nrows);
   int y = InpHUD_Y + 220;
   int lh = InpHUD_Font + 4;

   NXS_VS_DrawLabel("STATS_title", InpHUD_X, y, InpHUD_Corner,
                    "── Strategy Stats (top " + IntegerToString(topN) + ") ──",
                    clrSilver, InpHUD_Font);
   y += lh + 2;
   NXS_VS_DrawLabel("STATS_hdr", InpHUD_X, y, InpHUD_Corner,
                    "Strategy        Cal Setup Exec  Health",
                    clrGray, InpHUD_Font-1);
   y += lh;
   for(int i = 0; i < topN; i++){
      color c = InpHUD_FgNeu;
      if(health[i] == "HEALTHY")           c = InpHUD_FgPos;
      else if(health[i] == "BLOCKED_BY_GATE") c = C'255,180,60';
      else if(health[i] == "EXECUTION_PROBLEM") c = InpHUD_FgNeg;
      else if(health[i] == "LOW_SCORE_ONLY")   c = C'255,140,40';
      else if(health[i] == "NO_SETUP_FOUND")   c = clrSilver;
      else if(health[i] == "NOT_CONNECTED")    c = clrDarkGray;

      // Truncate name to 14 chars
      string nm = names[i];
      if(StringLen(nm) > 14) nm = StringSubstr(nm, 0, 14);
      while(StringLen(nm) < 14) nm += " ";
      string txt = nm + " " +
                   StringFormat("%4d %5d %4d  ", (int)called[i], (int)setup[i], (int)execs[i]) +
                   health[i];
      NXS_VS_DrawLabel("STATS_r" + IntegerToString(i), InpHUD_X, y, InpHUD_Corner,
                       txt, c, InpHUD_Font-1);
      y += lh;
   }
}

//+------------------------------------------------------------------+
//| Draw: Reaction marker (Layer 1)                                   |
//+------------------------------------------------------------------+
void NXS_VS_DrawReaction(){
   NXS_VS_CleanupCategory("REACT_");
   int dir = (int)NXS_VS_GV("reaction_dir", 0);
   double q = NXS_VS_GV("reaction_quality", 0);
   if(dir == 0 || q <= 0) return;
   double price = iClose(g_sym, InpTFEntry, 1);
   datetime t   = iTime (g_sym, InpTFEntry, 1);
   int arrow = (dir > 0) ? 233 : 234;
   color c   = (dir > 0) ? InpClr_FVG_Bull : InpClr_FVG_Bear;
   NXS_VS_DrawArrow("REACT_A", t, price, arrow, c, 3);
   NXS_VS_DrawText ("REACT_T", t, price, "R Q=" + DoubleToString(q,0), c, 8);
}

//+------------------------------------------------------------------+
//| Draw: HUD (Layer 1 - EA linked)                                   |
//+------------------------------------------------------------------+
void NXS_VS_DrawHUD(){
   if(!InpShowHUD){ NXS_VS_CleanupCategory("HUD_"); return; }
   int vel    = (int)NXS_VS_GV("velocity_state", 0);
   double bsp = NXS_VS_GV("pressure_pct", 50.0);
   int strat  = (int)NXS_VS_GV("active_strat", -1);
   double sc  = NXS_VS_GV("active_score", 0);
   int blk    = (int)NXS_VS_GV("last_blocker", 0);
   int tEntry = (int)NXS_VS_GV("struct_trend_entry", 0);
   int tMed   = (int)NXS_VS_GV("struct_trend_medium", 0);
   int tHi    = (int)NXS_VS_GV("struct_trend_high", 0);
   int htf    = (int)NXS_VS_GV("htf_bias", 0);
   int amd    = (int)NXS_VS_GV("amd_phase", 0);
   int paused = (int)NXS_VS_GV("ea_paused", 0);

   string amdN = amd==1?"ACCUM":(amd==2?"MANIP":(amd==3?"DISTR":"NONE"));
   string htfN = htf==1?"BULL":(htf==2?"BEAR":"NEU");

   color velClr = (vel==1||vel==3) ? InpHUD_FgPos : ((vel==2||vel==4) ? InpHUD_FgNeg : InpHUD_FgNeu);
   color bspClr = bsp>55 ? InpHUD_FgPos : (bsp<45 ? InpHUD_FgNeg : InpHUD_FgNeu);

   int y = InpHUD_Y;
   int lh = InpHUD_Font + 6;
   NXS_VS_DrawLabel("HUD_title", InpHUD_X, y, InpHUD_Corner,
                    "NEXUS Visual v2.0.4" + (paused?" [PAUSED]":""), clrWhite, InpHUD_Font+1);
   y += lh + 2;
   NXS_VS_DrawLabel("HUD_vel", InpHUD_X, y, InpHUD_Corner,
                    "VEL : " + NXS_VS_VelName(vel), velClr, InpHUD_Font);
   y += lh;
   NXS_VS_DrawLabel("HUD_bsp", InpHUD_X, y, InpHUD_Corner,
                    "BSP : " + DoubleToString(bsp,1) + "% buy", bspClr, InpHUD_Font);
   y += lh;
   if(InpShowMultiLayer){
      NXS_VS_DrawLabel("HUD_ml", InpHUD_X, y, InpHUD_Corner,
                       StringFormat("LTF=%s  MTF=%s  HTF=%s",
                                    NXS_VS_TrendName(tEntry),
                                    NXS_VS_TrendName(tMed),
                                    NXS_VS_TrendName(tHi)), clrLightGray, InpHUD_Font);
      y += lh;
   }
   NXS_VS_DrawLabel("HUD_htf", InpHUD_X, y, InpHUD_Corner,
                    "HTFbias=" + htfN + "  AMD=" + amdN, clrLightGray, InpHUD_Font);
   y += lh;
   if(strat >= 0){
      NXS_VS_DrawLabel("HUD_strat", InpHUD_X, y, InpHUD_Corner,
                       "Best : " + NXS_VS_StrategyName(strat) + "  " + DoubleToString(sc,1),
                       clrAqua, InpHUD_Font);
      y += lh;
   }
   color blkClr = (blk==0) ? InpHUD_FgNeu : InpHUD_FgNeg;
   NXS_VS_DrawLabel("HUD_blk", InpHUD_X, y, InpHUD_Corner,
                    "Blocker: " + NXS_VS_BlockerName(blk), blkClr, InpHUD_Font);
}

//+------------------------------------------------------------------+
//| OnInit                                                            |
//+------------------------------------------------------------------+
int OnInit(){
   g_sym = _Symbol;
   g_hATR_local = iATR(g_sym, InpTFEntry, 14);
   if(g_hATR_local == INVALID_HANDLE){
      Print("[NXS VS] ATR handle invalid");
      return INIT_FAILED;
   }
   ChartSetInteger(0, CHART_FOREGROUND, false);
   EventSetMillisecondTimer(1500);
   Print("[NXS VS v2.0.4] init on ", g_sym, " TF=", EnumToString(InpTFEntry));
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason){
   EventKillTimer();
   NXS_VS_CleanupAll();
   if(g_hATR_local != INVALID_HANDLE) IndicatorRelease(g_hATR_local);
   PrintFormat("[NXS VS] deinit reason=%d", reason);
}

//+------------------------------------------------------------------+
//| OnCalculate (light - delegate heavy work to OnTimer)              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[], const double &low[],
                const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[]){
   return rates_total;
}

//+------------------------------------------------------------------+
//| OnTimer: refresh state + redraw (decoupled from EA OnTick)        |
//+------------------------------------------------------------------+
void OnTimer(){
   double atrArr[];
   if(CopyBuffer(g_hATR_local, 0, 1, 1, atrArr) > 0) g_atr_local = atrArr[0];
   datetime bt = iTime(g_sym, InpTFEntry, 0);
   bool newBar = (bt != g_lastBar);
   g_lastBar = bt;

   // HUD updates always (fast)
   NXS_VS_DrawHUD();
   if(InpShowReaction) NXS_VS_DrawReaction();

   // Heavy redraws only on new bar
   if(newBar || ObjectFind(0, NXS_VS_PREFIX + "OB_BULL_3") < 0){
      if(InpShowOB)         NXS_VS_DrawOrderBlocks();
      if(InpShowFVG)        NXS_VS_DrawFVG();
      if(InpShowIFVG)       NXS_VS_DrawIFVG();
      if(InpShowOTE)        NXS_VS_DrawOTE();
      if(InpShowAsiaPDH)    NXS_VS_DrawAsiaPDH();
      if(InpShowTrendline)  NXS_VS_DrawTrendline();
      if(InpShowSNR)        NXS_VS_DrawSNR();
      if(InpShowBjorgum)    NXS_VS_DrawBjorgum();
      if(InpShowQuasimodo)  NXS_VS_DrawQuasimodo();
      if(InpShowKillzone)   NXS_VS_DrawKillzone();
      if(InpShowStatsPanel) NXS_VS_DrawStatsPanel();
   }
   ChartRedraw(0);
}
//+------------------------------------------------------------------+
