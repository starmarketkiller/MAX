//+------------------------------------------------------------------+
//|  NXS_VisualBridgeHTTP.mqh                                         |
//|  NEXUS v2.0.9 — push OB/FVG/SNR zones to the web Live Chart        |
//|                                                                    |
//|  One-way EA → backend via WebRequest. Re-uses the existing         |
//|  NEXUS_API_TOKEN header for authentication. Throttled to ~1 push   |
//|  every InpVisualPushSec seconds (default 30s) so we don't flood    |
//|  the backend during quiet markets.                                 |
//|                                                                    |
//|  Endpoint: POST {InpWebURL}/api/ea/visual_objects                  |
//|  Header:   X-Nexus-Token: <InpWebToken>                            |
//|  Body JSON:                                                        |
//|    { symbol, timeframe, version, generated_at, objects: [...] }    |
//+------------------------------------------------------------------+
#ifndef __NXS_VISUAL_BRIDGE_HTTP_MQH__
#define __NXS_VISUAL_BRIDGE_HTTP_MQH__

input bool   InpVisualPush_Enable = true;   // push OB/FVG/SNR to web chart
input int    InpVisualPushSec     = 30;     // min seconds between pushes
input int    InpVisualMaxObjects  = 30;     // max objects per push

datetime g_NXSvbLastPush = 0;

// ----------------------------------------------------------------------
// Build a single JSON object from EA-side primitives.
// type can be: "OB_BULL", "OB_BEAR", "FVG_BULL", "FVG_BEAR", "IFVG",
//              "SNR_SUPPLY", "SNR_DEMAND".
// ----------------------------------------------------------------------
string _nxs_vobj_json(string type_, double price, double top, double bottom,
                      datetime tFrom, datetime tTo, double score, string tag){
   return StringFormat(
      "{\"type\":\"%s\",\"price\":%.5f,\"top\":%.5f,\"bottom\":%.5f,"
      "\"time_from\":%I64d,\"time_to\":%I64d,\"score\":%.1f,\"tf\":\"%s\",\"tag\":\"%s\"}",
      type_, price, top, bottom,
      (long)tFrom, (long)tTo,
      score, EnumToString((ENUM_TIMEFRAMES)InpTFEntry), tag);
}

// ----------------------------------------------------------------------
// Collect current OB/FVG zones from the strategy state.
// We re-use the same helpers strategies use, so we never duplicate logic.
// If a particular detector isn't available, we silently skip it.
// ----------------------------------------------------------------------
int _nxs_vobj_collect(string &items[], int maxItems){
   int n = 0;
   if(maxItems <= 0) return 0;

   // 1) FIB / OTE zone (always available)
   SNXSFib fib = NXS_Fib_Build(InpTFMedium, 30);
   if(fib.swingHigh > 0 && fib.swingLow > 0 && n < maxItems){
      string j = _nxs_vobj_json("FIB_OTE", fib.ote705, fib.ote79, fib.ote62,
                                iTime(g_sym, InpTFMedium, 30),
                                iTime(g_sym, InpTFMedium, 0),
                                70.0, "OTE_62_79");
      items[n++] = j;
   }

   // 2) Recent reaction zone (if detected)
   if(g_reaction.detected && n < maxItems){
      string side = (g_reaction.direction > 0) ? "OB_BULL" : "OB_BEAR";
      double lp   = g_reaction.levelPrice;
      double atr5 = (g_atr > 0 ? g_atr * 0.5 : g_point * 50);
      string j = _nxs_vobj_json(side, lp, lp + atr5, lp - atr5,
                                iTime(g_sym, InpTFEntry, 5),
                                iTime(g_sym, InpTFEntry, 0),
                                g_reaction.quality, "REACTION");
      items[n++] = j;
   }

   // 3) AMD Asian Range as SNR
   SNXSAMD amd = NXS_GetAMD();
   if(amd.asianHigh > 0 && amd.asianLow > 0 && n < maxItems){
      double mid = (amd.asianHigh + amd.asianLow) * 0.5;
      string j = _nxs_vobj_json("SNR_SUPPLY", amd.asianHigh, amd.asianHigh, amd.asianLow,
                                iTime(g_sym, PERIOD_H1, 24),
                                iTime(g_sym, InpTFEntry, 0),
                                60.0, "ASIAN_RANGE");
      items[n++] = j;
   }

   // 4) PDH / PDL as horizontal S/R
   double pdh = iHigh(g_sym, PERIOD_D1, 1);
   double pdl = iLow (g_sym, PERIOD_D1, 1);
   if(pdh > 0 && n < maxItems){
      items[n++] = _nxs_vobj_json("SNR_SUPPLY", pdh, pdh, pdh,
                                  iTime(g_sym, PERIOD_D1, 1),
                                  iTime(g_sym, InpTFEntry, 0),
                                  55.0, "PDH");
   }
   if(pdl > 0 && n < maxItems){
      items[n++] = _nxs_vobj_json("SNR_DEMAND", pdl, pdl, pdl,
                                  iTime(g_sym, PERIOD_D1, 1),
                                  iTime(g_sym, InpTFEntry, 0),
                                  55.0, "PDL");
   }

   // 5) Structure swing levels (entry TF) as horizontal SR lines
   if(g_structEntry.lastSwingHigh > 0 && n < maxItems){
      double v = g_structEntry.lastSwingHigh;
      items[n++] = _nxs_vobj_json("SNR_SUPPLY", v, v, v,
                                  iTime(g_sym, InpTFEntry, 10),
                                  iTime(g_sym, InpTFEntry, 0),
                                  50.0, "STRUCT_HIGH");
   }
   if(g_structEntry.lastSwingLow > 0 && n < maxItems){
      double v = g_structEntry.lastSwingLow;
      items[n++] = _nxs_vobj_json("SNR_DEMAND", v, v, v,
                                  iTime(g_sym, InpTFEntry, 10),
                                  iTime(g_sym, InpTFEntry, 0),
                                  50.0, "STRUCT_LOW");
   }

   return n;
}

// ----------------------------------------------------------------------
// Push the current zones to the backend. Returns HTTP code or -1.
// Tester-safe: never fires inside Strategy Tester.
// ----------------------------------------------------------------------
int NXS_VisualBridge_PushHTTP(){
   if(!InpVisualPush_Enable)               return 0;
   if(!InpEnableWebSync)                   return 0;
   if(MQLInfoInteger(MQL_TESTER))          return 0;
   if(StringLen(InpWebURL) == 0)           return 0;
   datetime nowT = TimeCurrent();
   if(nowT - g_NXSvbLastPush < InpVisualPushSec) return 0;
   g_NXSvbLastPush = nowT;

   string items[];
   ArrayResize(items, InpVisualMaxObjects);
   int n = _nxs_vobj_collect(items, InpVisualMaxObjects);
   if(n <= 0) return 0;

   string arr = "[";
   for(int i = 0; i < n; ++i){
      if(i > 0) arr += ",";
      arr += items[i];
   }
   arr += "]";

   string body = StringFormat(
      "{\"symbol\":\"%s\",\"timeframe\":\"%s\",\"version\":\"%s\","
      "\"generated_at\":\"%s\",\"objects\":%s}",
      g_sym,
      EnumToString((ENUM_TIMEFRAMES)InpTFEntry),
      NEXUS_VERSION,
      TimeToString(nowT, TIME_DATE | TIME_SECONDS),
      arr);

   string headers = "Content-Type: application/json\r\n"
                    "X-Nexus-Token: " + InpWebToken + "\r\n";
   char post[]; char result[]; string resultHeaders = "";
   StringToCharArray(body, post, 0, StringLen(body));
   ResetLastError();
   string url = InpWebURL + "/api/ea/visual_objects";
   int code = WebRequest("POST", url, headers, 5000, post, result, resultHeaders);
   if(code <= 0){
      PrintFormat("[NXS VisualBridge] HTTP push failed code=%d err=%d", code, GetLastError());
   } else {
      PrintFormat("[NXS VisualBridge] pushed %d objects → HTTP %d", n, code);
   }
   return code;
}

#endif // __NXS_VISUAL_BRIDGE_HTTP_MQH__
