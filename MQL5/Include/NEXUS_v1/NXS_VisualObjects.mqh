//+------------------------------------------------------------------+
//|  NXS_VisualObjects.mqh                                            |
//|  NEXUS Visual Suite v2.0.4 - Object drawing helpers               |
//|                                                                   |
//|  Used by NEXUS_VisualSuite_v2.mq5 (indicator only).               |
//|  NO trading logic - pure chart object factory.                    |
//+------------------------------------------------------------------+
#ifndef __NXS_VISUAL_OBJECTS_MQH__
#define __NXS_VISUAL_OBJECTS_MQH__

#define NXS_VS_PREFIX  "NXS_VS_"

// ----- create / update rectangle zone (OB / FVG / IFVG / Killzone) ----
void NXS_VS_DrawRectangle(string name, datetime t1, double p1,
                          datetime t2, double p2, color clr,
                          bool filled, int style, int width){
   string id = NXS_VS_PREFIX + name;
   if(ObjectFind(0, id) < 0){
      ObjectCreate(0, id, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
   }
   ObjectSetInteger(0, id, OBJPROP_TIME,  0, t1);
   ObjectSetDouble (0, id, OBJPROP_PRICE, 0, p1);
   ObjectSetInteger(0, id, OBJPROP_TIME,  1, t2);
   ObjectSetDouble (0, id, OBJPROP_PRICE, 1, p2);
   ObjectSetInteger(0, id, OBJPROP_COLOR,   clr);
   ObjectSetInteger(0, id, OBJPROP_FILL,    filled);
   ObjectSetInteger(0, id, OBJPROP_BACK,    true);
   ObjectSetInteger(0, id, OBJPROP_STYLE,   style);
   ObjectSetInteger(0, id, OBJPROP_WIDTH,   width);
   ObjectSetInteger(0, id, OBJPROP_HIDDEN,  true);
   ObjectSetInteger(0, id, OBJPROP_SELECTABLE, false);
}

// ----- horizontal level (PDH/PDL/Asia/EQH/EQL/OTE/SNR) ---------------
void NXS_VS_DrawHLine(string name, double price, color clr, int style, int width, string text){
   string id = NXS_VS_PREFIX + name;
   if(ObjectFind(0, id) < 0){
      ObjectCreate(0, id, OBJ_HLINE, 0, 0, price);
   }
   ObjectSetDouble (0, id, OBJPROP_PRICE, 0, price);
   ObjectSetInteger(0, id, OBJPROP_COLOR,   clr);
   ObjectSetInteger(0, id, OBJPROP_STYLE,   style);
   ObjectSetInteger(0, id, OBJPROP_WIDTH,   width);
   ObjectSetInteger(0, id, OBJPROP_HIDDEN,  true);
   ObjectSetInteger(0, id, OBJPROP_SELECTABLE, false);
   if(StringLen(text) > 0)
      ObjectSetString(0, id, OBJPROP_TEXT, text);
}

// ----- text label (anchored to corner) -------------------------------
void NXS_VS_DrawLabel(string name, int x, int y, int corner,
                      string text, color clr, int fontSize){
   string id = NXS_VS_PREFIX + name;
   if(ObjectFind(0, id) < 0){
      ObjectCreate(0, id, OBJ_LABEL, 0, 0, 0);
   }
   ObjectSetInteger(0, id, OBJPROP_CORNER,    corner);
   ObjectSetInteger(0, id, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, id, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, id, OBJPROP_COLOR,     clr);
   ObjectSetInteger(0, id, OBJPROP_FONTSIZE,  fontSize);
   ObjectSetString (0, id, OBJPROP_TEXT,      text);
   ObjectSetString (0, id, OBJPROP_FONT,      "Consolas");
   ObjectSetInteger(0, id, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, id, OBJPROP_BACK,       false);
}

// ----- price-anchored text (zone tag e.g. "FVG_BULL", "FRESH") --------
void NXS_VS_DrawText(string name, datetime t, double p, string text, color clr, int fontSize){
   string id = NXS_VS_PREFIX + name;
   if(ObjectFind(0, id) < 0){
      ObjectCreate(0, id, OBJ_TEXT, 0, t, p);
   }
   ObjectSetInteger(0, id, OBJPROP_TIME,  0, t);
   ObjectSetDouble (0, id, OBJPROP_PRICE, 0, p);
   ObjectSetInteger(0, id, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, id, OBJPROP_FONTSIZE, fontSize);
   ObjectSetString (0, id, OBJPROP_TEXT, text);
   ObjectSetString (0, id, OBJPROP_FONT, "Consolas");
   ObjectSetInteger(0, id, OBJPROP_SELECTABLE, false);
}

// ----- trendline (BOS line / structure trendline) --------------------
void NXS_VS_DrawTrendline(string name, datetime t1, double p1,
                          datetime t2, double p2, color clr,
                          int style, int width, bool ray){
   string id = NXS_VS_PREFIX + name;
   if(ObjectFind(0, id) < 0){
      ObjectCreate(0, id, OBJ_TREND, 0, t1, p1, t2, p2);
   }
   ObjectSetInteger(0, id, OBJPROP_TIME,  0, t1);
   ObjectSetDouble (0, id, OBJPROP_PRICE, 0, p1);
   ObjectSetInteger(0, id, OBJPROP_TIME,  1, t2);
   ObjectSetDouble (0, id, OBJPROP_PRICE, 1, p2);
   ObjectSetInteger(0, id, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, id, OBJPROP_STYLE, style);
   ObjectSetInteger(0, id, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, id, OBJPROP_RAY_RIGHT, ray);
   ObjectSetInteger(0, id, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, id, OBJPROP_SELECTABLE, false);
}

// ----- arrow up/down for sweep / signal -------------------------------
void NXS_VS_DrawArrow(string name, datetime t, double p, int arrowCode, color clr, int width){
   string id = NXS_VS_PREFIX + name;
   if(ObjectFind(0, id) < 0){
      ObjectCreate(0, id, OBJ_ARROW, 0, t, p);
   }
   ObjectSetInteger(0, id, OBJPROP_TIME,  0, t);
   ObjectSetDouble (0, id, OBJPROP_PRICE, 0, p);
   ObjectSetInteger(0, id, OBJPROP_ARROWCODE, arrowCode);
   ObjectSetInteger(0, id, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, id, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, id, OBJPROP_SELECTABLE, false);
}

// ----- remove all NXS visual objects (cleanup) ------------------------
void NXS_VS_CleanupAll(){
   int total = ObjectsTotal(0, -1, -1);
   for(int i = total - 1; i >= 0; i--){
      string n = ObjectName(0, i, -1, -1);
      if(StringFind(n, NXS_VS_PREFIX) == 0) ObjectDelete(0, n);
   }
}

// ----- remove single category (e.g. "OB_", "FVG_") --------------------
void NXS_VS_CleanupCategory(string category){
   string fullPrefix = NXS_VS_PREFIX + category;
   int total = ObjectsTotal(0, -1, -1);
   for(int i = total - 1; i >= 0; i--){
      string n = ObjectName(0, i, -1, -1);
      if(StringFind(n, fullPrefix) == 0) ObjectDelete(0, n);
   }
}

// ----- color with alpha (helper) --------------------------------------
color NXS_VS_ColorAlpha(color base, uchar alpha){
   // MT5 supports ARGB via OBJPROP_FILL=true + opaque color. We keep flat colors.
   return base;
}

#endif
