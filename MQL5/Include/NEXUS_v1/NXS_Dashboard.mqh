//+------------------------------------------------------------------+
//|  NXS_Dashboard.mqh - On-chart visual dashboard                    |
//|  Renders a branded info panel + status badges using OBJ_LABEL.    |
//+------------------------------------------------------------------+
#ifndef __NXS_DASHBOARD_MQH__
#define __NXS_DASHBOARD_MQH__

#define DASH_PFX  "NXS_DASH_"

void _DashLabel(string name, string text, int x, int y, int size, color clr, string font="Consolas"){
   string n = DASH_PFX + name;
   if(ObjectFind(0, n) < 0){
      ObjectCreate(0, n, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, n, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, n, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
      ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, n, OBJPROP_BACK, false);
   }
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
   ObjectSetString (0, n, OBJPROP_FONT, font);
   ObjectSetString (0, n, OBJPROP_TEXT, text);
}

void _DashRect(string name, int x, int y, int w, int h, color bg){
   string n = DASH_PFX + name;
   if(ObjectFind(0, n) < 0){
      ObjectCreate(0, n, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, n, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, n, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, n, OBJPROP_BACK, true);
      ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
   }
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, n, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, n, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, n, OBJPROP_COLOR, bg);
}

color _NXS_StatusColor(){
   if(!g_licOK)                              return clrCrimson;
   if(g_eslHit || g_dptHit)                  return clrDarkOrange;
   if(g_pausedUntilNextOpen || g_eaPaused)   return clrGold;
   return clrLimeGreen;
}

string _NXS_StatusText(){
   if(!g_licOK)                  return "LICENSE INVALID";
   if(g_eslHit)                  return "ESL HIT";
   if(g_dptHit)                  return "DPT HIT";
   if(g_pausedUntilNextOpen)     return "DAY PAUSED";
   if(g_autoClosePending)        return "AUTO-CLOSE";
   if(g_eaPaused)                return "PAUSED";
   return "LIVE";
}

void NXS_Dashboard_Render(){
   if(!InpShowDashboard) return;

   double bal  = AccountInfoDouble(ACCOUNT_BALANCE);
   double eq   = AccountInfoDouble(ACCOUNT_EQUITY);
   double flt  = NXS_FloatingPnL();
   double dly  = (g_balanceDayStart > 0) ? (eq - g_balanceDayStart) : 0;
   double dd   = (g_balanceDayStart > 0)
                 ? ((g_balanceDayStart - eq) / g_balanceDayStart * 100.0) : 0;
   if(dd < 0) dd = 0;

   int X = InpDashX, Y = InpDashY, W = 280;
   color bg     = (color)0x141A22;
   color border = (color)0x2A3340;
   color cText  = clrWhite;
   color cMuted = (color)0x9CA3AF;
   color cPos   = clrLimeGreen;
   color cNeg   = clrTomato;

   _DashRect("bg",      X,      Y,      W, 220, bg);
   _DashRect("border",  X,      Y,      W,   2, border);
   _DashRect("hdr",     X,      Y,      W,  28, (color)0x1F2937);
   _DashRect("statusBar", X,    Y + 28, W,   4, _NXS_StatusColor());

   _DashLabel("title",   "NEXUS  v" + NEXUS_VERSION + "  -  " + g_profile.className,
              X + 10, Y + 6, 10, clrWhite, "Verdana");
   _DashLabel("status",  "[" + _NXS_StatusText() + "]", X + W - 110, Y + 6, 9, _NXS_StatusColor(), "Verdana");

   int row = Y + 40, lh = 16;
   _DashLabel("l_sym",  "Symbol:",   X + 10, row, 8, cMuted); _DashLabel("v_sym", _Symbol,  X + 110, row, 8, cText); row += lh;
   _DashLabel("l_bal",  "Balance:",  X + 10, row, 8, cMuted); _DashLabel("v_bal", DoubleToString(bal, 2), X + 110, row, 8, cText); row += lh;
   _DashLabel("l_eq",   "Equity:",   X + 10, row, 8, cMuted); _DashLabel("v_eq",  DoubleToString(eq, 2),  X + 110, row, 8, cText); row += lh;
   _DashLabel("l_flt",  "Float PnL:",X + 10, row, 8, cMuted); _DashLabel("v_flt", DoubleToString(flt, 2), X + 110, row, 8, (flt >= 0 ? cPos : cNeg)); row += lh;
   _DashLabel("l_dly",  "Daily PnL:",X + 10, row, 8, cMuted); _DashLabel("v_dly", DoubleToString(dly, 2), X + 110, row, 8, (dly >= 0 ? cPos : cNeg)); row += lh;
   _DashLabel("l_dd",   "Daily DD:", X + 10, row, 8, cMuted); _DashLabel("v_dd",  DoubleToString(dd, 2) + " %", X + 110, row, 8, (dd >= 3.0 ? cNeg : cText)); row += lh;
   _DashLabel("l_trd",  "Trades:",   X + 10, row, 8, cMuted); _DashLabel("v_trd", IntegerToString(g_tradesToday) + " / " + IntegerToString(g_run_MaxTradesPerDay), X + 110, row, 8, cText); row += lh;
   _DashLabel("l_pos",  "Positions:",X + 10, row, 8, cMuted); _DashLabel("v_pos", IntegerToString(NXS_CountPositions()) + " / " + IntegerToString(g_run_MaxConcurrent), X + 110, row, 8, cText); row += lh;
   _DashLabel("l_loss", "ConsecLoss:",X + 10, row, 8, cMuted); _DashLabel("v_loss", IntegerToString(g_consecLosses), X + 110, row, 8, (g_consecLosses >= 2 ? cNeg : cText)); row += lh;
   _DashLabel("l_lic",  "License:",  X + 10, row, 8, cMuted); _DashLabel("v_lic", NXS_License_Status(), X + 110, row, 8, (g_licOK ? cPos : cNeg)); row += lh;

   ChartRedraw(0);
}

void NXS_Dashboard_Cleanup(){
   ObjectsDeleteAll(0, DASH_PFX);
}

#endif
