//+------------------------------------------------------------------+
//|  NXS_RuntimeSettings.mqh - pull settings from dashboard backend   |
//|  and override a curated set of shadow globals at runtime.         |
//+------------------------------------------------------------------+
#ifndef __NXS_RUNTIME_SETTINGS_MQH__
#define __NXS_RUNTIME_SETTINGS_MQH__

// ----- Runtime-tunable shadow globals (initialised from Inp* in OnInit) -----
double  g_run_RiskPercent     = 0;
double  g_run_MaxLot          = 0;
int     g_run_MaxTradesPerDay = 0;
int     g_run_MaxConcurrent   = 0;
double  g_run_MaxDailyDDPct   = 0;
int     g_run_MinEntryScore   = 0;
double  g_run_AsianScoreMin   = 0;
double  g_run_LondonScoreMin  = 0;
double  g_run_OverlapScoreMin = 0;
double  g_run_NYScoreMin      = 0;
double  g_run_AfterNYScoreMin = 0;
bool    g_run_UseNewsFilter   = true;
bool    g_run_UseHTFBias      = true;
bool    g_run_UseVelocityGate = true;
datetime g_lastSettingsPull   = 0;
int     g_settingsPullSec     = 15;   // poll cadence

void NXS_Runtime_Init(){
   g_run_RiskPercent     = InpRiskPercent;
   g_run_MaxLot          = InpMaxLot;
   g_run_MaxTradesPerDay = InpMaxTradesPerDay;
   g_run_MaxConcurrent   = InpMaxConcurrent;
   g_run_MaxDailyDDPct   = InpMaxDailyDDPct;
   g_run_MinEntryScore   = (int)InpMinEntryScore;
   g_run_AsianScoreMin   = InpAsianScoreMin;
   g_run_LondonScoreMin  = InpLondonScoreMin;
   g_run_OverlapScoreMin = InpOverlapScoreMin;
   g_run_NYScoreMin      = InpNYScoreMin;
   g_run_AfterNYScoreMin = InpAfterNYScoreMin;
   g_run_UseNewsFilter   = InpUseNews;
   g_run_UseHTFBias      = InpUseHTFBias;
   g_run_UseVelocityGate = InpUseVelocity;
   Print("[NEXUS RUNTIME] Initialised shadow globals from inputs");
}

// Extract numeric value for "\"key\":" from JSON-ish string. Returns NaN if not found.
double _NXS_JsonNum(const string &json, const string key){
   string needle = "\"" + key + "\":";
   int p = StringFind(json, needle);
   if(p < 0) return EMPTY_VALUE;
   int s = p + StringLen(needle);
   // skip whitespace
   while(s < StringLen(json) && (StringGetCharacter(json, s) == ' '
         || StringGetCharacter(json, s) == '\t')) s++;
   int e = s;
   // allow digits, dot, minus, e/E for scientific
   while(e < StringLen(json)){
      ushort c = StringGetCharacter(json, e);
      if((c >= '0' && c <= '9') || c == '.' || c == '-' || c == 'e' || c == 'E' || c == '+') e++;
      else break;
   }
   if(e == s) return EMPTY_VALUE;
   return (double)StringToDouble(StringSubstr(json, s, e - s));
}

bool _NXS_JsonBool(const string &json, const string key, bool fallback){
   string needle = "\"" + key + "\":";
   int p = StringFind(json, needle);
   if(p < 0) return fallback;
   int s = p + StringLen(needle);
   while(s < StringLen(json) && (StringGetCharacter(json, s) == ' '
         || StringGetCharacter(json, s) == '\t')) s++;
   string rest = StringSubstr(json, s, 5);
   if(StringFind(rest, "true") == 0)  return true;
   if(StringFind(rest, "false") == 0) return false;
   return fallback;
}

#define _RT_APPLY_NUM(NAME, key, type) \
   { double _v = _NXS_JsonNum(json, key); \
     if(_v != EMPTY_VALUE && (type)_v != NAME){ \
       PrintFormat("[NEXUS RUNTIME] %s: %g -> %g (from dashboard)", key, (double)NAME, _v); \
       NAME = (type)_v; } }

#define _RT_APPLY_BOOL(NAME, key) \
   { bool _v = _NXS_JsonBool(json, key, NAME); \
     if(_v != NAME){ \
       PrintFormat("[NEXUS RUNTIME] %s: %s -> %s (from dashboard)", key, \
                   (NAME?"true":"false"), (_v?"true":"false")); \
       NAME = _v; } }

void NXS_PullSettings(){
   if(!InpEnableWebSync) return;
   if(TimeCurrent() - g_lastSettingsPull < g_settingsPullSec) return;
   g_lastSettingsPull = TimeCurrent();

   string url = InpWebURL + "/api/ea/settings";
   char empty[]; char result[]; string headersOut;
   string headers = "X-Nexus-Token: " + InpWebToken + "\r\n";
   int code = WebRequest("GET", url, headers, 3000, empty, result, headersOut);
   if(code != 200) return;
   string json = CharArrayToString(result, 0, -1, CP_UTF8);

   // Numerics
   _RT_APPLY_NUM(g_run_RiskPercent,     "RiskPercent",     double);
   _RT_APPLY_NUM(g_run_MaxLot,          "MaxLot",          double);
   _RT_APPLY_NUM(g_run_MaxTradesPerDay, "MaxTradesPerDay", int);
   _RT_APPLY_NUM(g_run_MaxConcurrent,   "MaxConcurrent",   int);
   _RT_APPLY_NUM(g_run_MaxDailyDDPct,   "MaxDailyDDPct",   double);
   _RT_APPLY_NUM(g_run_MinEntryScore,   "MinEntryScore",   int);
   _RT_APPLY_NUM(g_run_AsianScoreMin,   "AsianScoreMin",   double);
   _RT_APPLY_NUM(g_run_LondonScoreMin,  "LondonScoreMin",  double);
   _RT_APPLY_NUM(g_run_OverlapScoreMin, "OverlapScoreMin", double);
   _RT_APPLY_NUM(g_run_NYScoreMin,      "NYScoreMin",      double);
   _RT_APPLY_NUM(g_run_AfterNYScoreMin, "AfterNYScoreMin", double);

   // Booleans
   _RT_APPLY_BOOL(g_run_UseNewsFilter,   "UseNewsFilter");
   _RT_APPLY_BOOL(g_run_UseHTFBias,      "UseHTFBias");
   _RT_APPLY_BOOL(g_run_UseVelocityGate, "UseVelocityGate");
}

#endif
