//+------------------------------------------------------------------+
//|  NXS_LockedProfile.mqh                                            |
//|  NEXUS v2.0.10 — pulls the active locked profile at OnInit() and  |
//|  overrides the EA inputs with the auto-optimizer winning values.  |
//|                                                                    |
//|  Endpoint:  GET {InpWebURL}/api/ea/locked_profile?symbol=...      |
//|  Header:    X-Nexus-Token: <InpWebToken>                          |
//|  Response JSON example:                                            |
//|    { "locked":true, "label":"...", "saved_at":"...",              |
//|      "metrics":{...},                                             |
//|      "params":{                                                    |
//|        "RiskPct":1.0,"AtrSLMult":1.2,"AtrTPMult":4.5,             |
//|        "MinScore":70,"AdxMin":18,"HtfBiasRequired":false,         |
//|        "SessionLondon":true,"SessionNY":true,"SessionAsian":true, |
//|        "CooldownBars":3,"DailyDDCap":5,"BreakevenR":0,            |
//|        "TrailingAtrMult":0,"MaxConcurrent":3                      |
//|      }                                                             |
//|    }                                                               |
//|                                                                    |
//|  This module mutates a small set of GLOBAL knob variables that the |
//|  rest of the EA reads. We do NOT alter the original `input ...`    |
//|  declarations — that would require recompile. Instead we expose    |
//|  effective getters that strategies consult.                        |
//+------------------------------------------------------------------+
#ifndef __NXS_LOCKED_PROFILE_MQH__
#define __NXS_LOCKED_PROFILE_MQH__

input bool   InpLockedProfile_Enable = true;   // pull locked profile on OnInit
input string InpLockedProfile_TF     = "D1";   // timeframe key used by backend

// Effective values, populated after _NXS_LockedProfile_Fetch().
// They default to whatever the user already configured in EA Properties.
bool   g_NXSlp_locked        = false;
string g_NXSlp_label         = "";
string g_NXSlp_savedAt       = "";
double g_NXSlp_metricsSharpe = 0.0;
double g_NXSlp_metricsPF     = 0.0;

// Effective overridden knobs (mirrored to the rest of the EA)
double g_NXSlp_RiskPct         = -1;   // -1 = use input value
double g_NXSlp_AtrSLMult        = -1;
double g_NXSlp_AtrTPMult        = -1;
int    g_NXSlp_MinScore         = -1;
double g_NXSlp_AdxMin           = -1;
int    g_NXSlp_HtfBiasRequired  = -1;  // -1=unset, 0=false, 1=true
int    g_NXSlp_SessionLondon    = -1;
int    g_NXSlp_SessionNY        = -1;
int    g_NXSlp_SessionAsian     = -1;
int    g_NXSlp_CooldownBars     = -1;
double g_NXSlp_DailyDDCap       = -1;
double g_NXSlp_BreakevenR       = -1;
double g_NXSlp_TrailingAtrMult  = -1;
int    g_NXSlp_MaxConcurrent    = -1;
// Strategy allowlist (when non-empty, only these strategies fire)
string g_NXSlp_StrategiesEnabled[];   // upper-case ids
int    g_NXSlp_StrategiesCount  = 0;
// Grid / Pyramiding flags (informational — applied by NXS_Management.mqh)
int    g_NXSlp_GridEnabled      = -1;
double g_NXSlp_GridStepAtr       = -1;
int    g_NXSlp_GridMaxLevels     = -1;
double g_NXSlp_GridSizeMult      = -1;
int    g_NXSlp_PyramidEnabled    = -1;
double g_NXSlp_PyramidStepR      = -1;
int    g_NXSlp_PyramidMaxAdds    = -1;
double g_NXSlp_PyramidSizePct    = -1;

// Effective getters — strategies read these instead of the raw inputs.
double NXS_Eff_RiskPct(double inputVal)     { return (g_NXSlp_RiskPct  >= 0 ? g_NXSlp_RiskPct  : inputVal); }
double NXS_Eff_AtrSLMult(double inputVal)   { return (g_NXSlp_AtrSLMult >= 0 ? g_NXSlp_AtrSLMult : inputVal); }
double NXS_Eff_AtrTPMult(double inputVal)   { return (g_NXSlp_AtrTPMult >= 0 ? g_NXSlp_AtrTPMult : inputVal); }
int    NXS_Eff_MinScore(int inputVal)       { return (g_NXSlp_MinScore  >= 0 ? g_NXSlp_MinScore  : inputVal); }
double NXS_Eff_AdxMin(double inputVal)      { return (g_NXSlp_AdxMin    >= 0 ? g_NXSlp_AdxMin    : inputVal); }
bool   NXS_Eff_HtfBias(bool inputVal)       { return (g_NXSlp_HtfBiasRequired >= 0 ? (g_NXSlp_HtfBiasRequired == 1) : inputVal); }
bool   NXS_Eff_SessionLondon(bool inputVal) { return (g_NXSlp_SessionLondon   >= 0 ? (g_NXSlp_SessionLondon   == 1) : inputVal); }
bool   NXS_Eff_SessionNY(bool inputVal)     { return (g_NXSlp_SessionNY       >= 0 ? (g_NXSlp_SessionNY       == 1) : inputVal); }
bool   NXS_Eff_SessionAsian(bool inputVal)  { return (g_NXSlp_SessionAsian    >= 0 ? (g_NXSlp_SessionAsian    == 1) : inputVal); }
int    NXS_Eff_CooldownBars(int inputVal)   { return (g_NXSlp_CooldownBars  >= 0 ? g_NXSlp_CooldownBars  : inputVal); }
double NXS_Eff_DailyDDCap(double inputVal)  { return (g_NXSlp_DailyDDCap    >= 0 ? g_NXSlp_DailyDDCap    : inputVal); }
double NXS_Eff_BreakevenR(double inputVal)  { return (g_NXSlp_BreakevenR    >= 0 ? g_NXSlp_BreakevenR    : inputVal); }
double NXS_Eff_TrailingAtr(double inputVal) { return (g_NXSlp_TrailingAtrMult >= 0 ? g_NXSlp_TrailingAtrMult : inputVal); }
int    NXS_Eff_MaxConcurrent(int inputVal)  { return (g_NXSlp_MaxConcurrent >= 0 ? g_NXSlp_MaxConcurrent : inputVal); }

// Return true if the strategy id is allowed by the active locked profile.
// When the profile lists no strategies, ALL are allowed.
bool NXS_Eff_StrategyAllowed(const string strategyId){
   if(g_NXSlp_StrategiesCount <= 0) return true;
   for(int i = 0; i < g_NXSlp_StrategiesCount; ++i){
      if(g_NXSlp_StrategiesEnabled[i] == strategyId) return true;
   }
   return false;
}

// Parse a JSON array of quoted strings (e.g. ["MALAYSIAN_SNR","CISD"]).
// Returns the number of items parsed. The "key" should be unquoted.
int _nxs_lp_parse_str_array(const string js, const string key, string &out[]){
   string needle = "\"" + key + "\":";
   int pos = StringFind(js, needle);
   if(pos < 0) return 0;
   pos += StringLen(needle);
   while(pos < StringLen(js) && (StringGetCharacter(js, pos) == ' ' || StringGetCharacter(js, pos) == '\t')) pos++;
   if(pos >= StringLen(js) || StringGetCharacter(js, pos) != '[') return 0;
   pos++;
   int n = 0;
   ArrayResize(out, 64);
   while(pos < StringLen(js)){
      while(pos < StringLen(js) && (StringGetCharacter(js, pos) == ' '
                                    || StringGetCharacter(js, pos) == ','
                                    || StringGetCharacter(js, pos) == '\n'
                                    || StringGetCharacter(js, pos) == '\r')) pos++;
      if(pos >= StringLen(js)) break;
      if(StringGetCharacter(js, pos) == ']') break;
      if(StringGetCharacter(js, pos) != '\"') break;
      int end = StringFind(js, "\"", pos + 1);
      if(end < 0) break;
      if(n >= ArraySize(out)) ArrayResize(out, n + 16);
      out[n++] = StringSubstr(js, pos + 1, end - pos - 1);
      pos = end + 1;
   }
   ArrayResize(out, n);
   return n;
}

// ----------------------------------------------------------------------
// Very small JSON helper — extracts "key": <value> ignoring whitespace.
// Returns the matched string content or "" if not found.
// ----------------------------------------------------------------------
string _nxs_lp_json_str(string js, string key){
   string needle = "\"" + key + "\":";
   int pos = StringFind(js, needle);
   if(pos < 0) return "";
   pos += StringLen(needle);
   while(pos < StringLen(js) && (StringGetCharacter(js, pos) == ' ' || StringGetCharacter(js, pos) == '\t'))
      pos++;
   if(pos >= StringLen(js)) return "";
   ushort c = StringGetCharacter(js, pos);
   if(c == '\"'){
      int end = StringFind(js, "\"", pos + 1);
      if(end < 0) return "";
      return StringSubstr(js, pos + 1, end - pos - 1);
   }
   // number / bool / null
   int end = pos;
   while(end < StringLen(js)){
      ushort ch = StringGetCharacter(js, end);
      if(ch == ',' || ch == '}' || ch == ']' || ch == '\n' || ch == '\r') break;
      end++;
   }
   string raw = StringSubstr(js, pos, end - pos);
   StringTrimLeft(raw); StringTrimRight(raw);
   return raw;
}

double _nxs_lp_num(string js, string key, double dflt){
   string s = _nxs_lp_json_str(js, key);
   if(StringLen(s) == 0) return dflt;
   return StringToDouble(s);
}

int _nxs_lp_int(string js, string key, int dflt){
   string s = _nxs_lp_json_str(js, key);
   if(StringLen(s) == 0) return dflt;
   return (int)StringToInteger(s);
}

int _nxs_lp_bool(string js, string key){
   // returns 1=true, 0=false, -1=missing
   string s = _nxs_lp_json_str(js, key);
   if(StringLen(s) == 0) return -1;
   if(s == "true" || s == "TRUE" || s == "1") return 1;
   if(s == "false" || s == "FALSE" || s == "0") return 0;
   return -1;
}

// ----------------------------------------------------------------------
// Fetch + apply the locked profile. Called from OnInit().
// Returns true if a locked profile was applied.
// ----------------------------------------------------------------------
bool NXS_LockedProfile_Fetch(){
   if(!InpLockedProfile_Enable)    return false;
   if(!InpEnableWebSync)           return false;
   if(MQLInfoInteger(MQL_TESTER))  return false;  // tester is sandbox-only
   if(StringLen(InpWebURL) == 0)   return false;

   string url = InpWebURL + "/api/ea/locked_profile?symbol=" + g_sym
                + "&timeframe=" + InpLockedProfile_TF;
   string headers = "X-Nexus-Token: " + InpWebToken + "\r\n";
   char post[]; char result[]; string resultHeaders;
   ResetLastError();
   int code = WebRequest("GET", url, headers, 5000, post, result, resultHeaders);
   if(code != 200){
      PrintFormat("[NXS LockedProfile] HTTP %d (err=%d) — using EA Properties values",
                  code, GetLastError());
      return false;
   }
   string body = CharArrayToString(result);
   // Quick guard: is the profile actually locked?
   if(_nxs_lp_bool(body, "locked") != 1){
      Print("[NXS LockedProfile] no active profile for ", g_sym, " ", InpLockedProfile_TF);
      return false;
   }
   g_NXSlp_locked  = true;
   g_NXSlp_label   = _nxs_lp_json_str(body, "label");
   g_NXSlp_savedAt = _nxs_lp_json_str(body, "saved_at");
   g_NXSlp_metricsSharpe = _nxs_lp_num(body, "sharpe", 0);
   g_NXSlp_metricsPF     = _nxs_lp_num(body, "profit_factor", 0);

   // Extract every params.* (we don't have nested-object parser; use full key paths)
   g_NXSlp_RiskPct          = _nxs_lp_num (body, "RiskPct",          -1);
   g_NXSlp_AtrSLMult        = _nxs_lp_num (body, "AtrSLMult",        -1);
   g_NXSlp_AtrTPMult        = _nxs_lp_num (body, "AtrTPMult",        -1);
   g_NXSlp_MinScore         = _nxs_lp_int (body, "MinScore",         -1);
   g_NXSlp_AdxMin           = _nxs_lp_num (body, "AdxMin",           -1);
   g_NXSlp_HtfBiasRequired  = _nxs_lp_bool(body, "HtfBiasRequired");
   g_NXSlp_SessionLondon    = _nxs_lp_bool(body, "SessionLondon");
   g_NXSlp_SessionNY        = _nxs_lp_bool(body, "SessionNY");
   g_NXSlp_SessionAsian     = _nxs_lp_bool(body, "SessionAsian");
   g_NXSlp_CooldownBars     = _nxs_lp_int (body, "CooldownBars",     -1);
   g_NXSlp_DailyDDCap       = _nxs_lp_num (body, "DailyDDCap",       -1);
   g_NXSlp_BreakevenR       = _nxs_lp_num (body, "BreakevenR",       -1);
   g_NXSlp_TrailingAtrMult  = _nxs_lp_num (body, "TrailingAtrMult",  -1);
   g_NXSlp_MaxConcurrent    = _nxs_lp_int (body, "MaxConcurrent",    -1);

   // Strategy allowlist
   g_NXSlp_StrategiesCount = _nxs_lp_parse_str_array(body, "strategies_enabled", g_NXSlp_StrategiesEnabled);

   PrintFormat("[NXS LockedProfile] ✓ APPLIED %s → SL×%.2f TP×%.2f minScore=%d ADX=%.1f BE=%.2fR Trail=%.2fATR | strategies=%d | %s",
               g_sym, g_NXSlp_AtrSLMult, g_NXSlp_AtrTPMult, g_NXSlp_MinScore,
               g_NXSlp_AdxMin, g_NXSlp_BreakevenR, g_NXSlp_TrailingAtrMult,
               g_NXSlp_StrategiesCount, g_NXSlp_label);
   if(g_NXSlp_StrategiesCount > 0){
      string lst = "";
      for(int i = 0; i < g_NXSlp_StrategiesCount; ++i){
         if(i > 0) lst += ", ";
         lst += g_NXSlp_StrategiesEnabled[i];
      }
      Print("[NXS LockedProfile] Allowlist: ", lst);
   }
   return true;
}

#endif // __NXS_LOCKED_PROFILE_MQH__
