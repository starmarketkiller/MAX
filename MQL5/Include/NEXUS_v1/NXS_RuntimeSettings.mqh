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
// Stop/target/trailing tunabili dal sito (default = valori Inp in OnInit).
double  g_run_AtrSLMult       = 0;
double  g_run_AtrTPMult       = 0;
double  g_run_BE_TriggerATR   = 0;
double  g_run_TrailActivateATR= 0;
double  g_run_TrailDistanceATR= 0;
// Moltiplicatori SL/TP per timeframe di origine del segnale (tunabili dal sito).
double  g_run_TF_SLTP_H1      = 0;
double  g_run_TF_SLTP_H4      = 0;
double  g_run_TF_SLTP_D1      = 0;
datetime g_lastSettingsPull   = 0;
int     g_settingsPullSec     = 15;   // poll cadence

// Strategie disattivate da remoto (pagina "Strategie" della dashboard).
// Aggiornate ad ogni poll; se una strategia è qui, l'EA non apre nuovi trade
// per essa finché non viene riattivata dal sito. Nessun riavvio richiesto.
string  g_run_StratDisabled[];
int     g_run_StratDisabledCount = 0;

// Moltiplicatori di rischio per-strategia dal loop di ottimizzazione live.
// Cache del sotto-oggetto JSON "strategy_risk":{...}; il lotto viene scalato
// per strategia in apertura. Default 1.0 (nessuna variazione).
string  g_run_StrategyRiskJson = "";

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
   g_run_AtrSLMult        = InpATR_SL_Mult;
   g_run_AtrTPMult        = InpATR_TP_Mult;
   g_run_BE_TriggerATR    = InpBE_TriggerATR;
   g_run_TrailActivateATR = InpTrailActivateATR;
   g_run_TrailDistanceATR = InpTrailDistanceATR;
   g_run_TF_SLTP_H1       = InpTF_SLTP_H1;
   g_run_TF_SLTP_H4       = InpTF_SLTP_H4;
   g_run_TF_SLTP_D1       = InpTF_SLTP_D1;
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

// Parsa un array JSON di stringhe quotate, es. "strategies_disabled":["MACD","CISD"].
// Riempie out[] e ritorna il numero di elementi (0 se assente/vuoto).
int _NXS_JsonStrArray(const string &json, const string key, string &out[]){
   string needle = "\"" + key + "\":";
   int pos = StringFind(json, needle);
   if(pos < 0){ ArrayResize(out, 0); return 0; }
   pos += StringLen(needle);
   int len = StringLen(json);
   while(pos < len && (StringGetCharacter(json, pos) == ' '
                       || StringGetCharacter(json, pos) == '\t')) pos++;
   if(pos >= len || StringGetCharacter(json, pos) != '['){ ArrayResize(out, 0); return 0; }
   pos++;
   int n = 0;
   ArrayResize(out, 64);
   while(pos < len){
      while(pos < len && (StringGetCharacter(json, pos) == ' '
                          || StringGetCharacter(json, pos) == ','
                          || StringGetCharacter(json, pos) == '\n'
                          || StringGetCharacter(json, pos) == '\r')) pos++;
      if(pos >= len) break;
      if(StringGetCharacter(json, pos) == ']') break;
      if(StringGetCharacter(json, pos) != '\"') break;
      int end = StringFind(json, "\"", pos + 1);
      if(end < 0) break;
      if(n >= ArraySize(out)) ArrayResize(out, n + 32);
      out[n++] = StringSubstr(json, pos + 1, end - pos - 1);
      pos = end + 1;
   }
   ArrayResize(out, n);
   return n;
}

// True se la strategia è stata disattivata da remoto dalla dashboard.
bool NXS_Runtime_StrategyBlocked(const string name){
   for(int i = 0; i < g_run_StratDisabledCount; ++i)
      if(g_run_StratDisabled[i] == name) return true;
   return false;
}

// Estrae il sotto-oggetto JSON "key":{ ... } (valori flat, niente nesting).
// Ritorna il contenuto tra graffe (escluse) o "" se assente.
string _NXS_JsonObject(const string &json, const string key){
   string needle = "\"" + key + "\":";
   int p = StringFind(json, needle);
   if(p < 0) return "";
   p += StringLen(needle);
   int len = StringLen(json);
   while(p < len && (StringGetCharacter(json, p) == ' '
                     || StringGetCharacter(json, p) == '\t')) p++;
   if(p >= len || StringGetCharacter(json, p) != '{') return "";
   int start = p + 1;
   int e = start;
   while(e < len && StringGetCharacter(json, e) != '}') e++;
   if(e >= len) return "";
   return StringSubstr(json, start, e - start);
}

// Moltiplicatore di rischio per la strategia (1.0 se non specificato).
double NXS_Runtime_StrategyLotMult(const string name){
   if(StringLen(g_run_StrategyRiskJson) == 0) return 1.0;
   double v = _NXS_JsonNum(g_run_StrategyRiskJson, name);
   if(v == EMPTY_VALUE || v <= 0.0) return 1.0;
   return v;
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
   // Stop/target/trailing (tunabili dal sito)
   _RT_APPLY_NUM(g_run_AtrSLMult,        "ATR_SL_Mult",      double);
   _RT_APPLY_NUM(g_run_AtrTPMult,        "ATR_TP_Mult",      double);
   _RT_APPLY_NUM(g_run_BE_TriggerATR,    "BE_TriggerATR",    double);
   _RT_APPLY_NUM(g_run_TrailActivateATR, "TrailActivateATR", double);
   _RT_APPLY_NUM(g_run_TrailDistanceATR, "TrailDistanceATR", double);
   _RT_APPLY_NUM(g_run_TF_SLTP_H1,       "TF_SLTP_H1",       double);
   _RT_APPLY_NUM(g_run_TF_SLTP_H4,       "TF_SLTP_H4",       double);
   _RT_APPLY_NUM(g_run_TF_SLTP_D1,       "TF_SLTP_D1",       double);

   // Booleans
   _RT_APPLY_BOOL(g_run_UseNewsFilter,   "UseNewsFilter");
   _RT_APPLY_BOOL(g_run_UseHTFBias,      "UseHTFBias");
   _RT_APPLY_BOOL(g_run_UseVelocityGate, "UseVelocityGate");

   // Strategie disattivate da remoto — applicazione live.
   string disabled[];
   int dn = _NXS_JsonStrArray(json, "strategies_disabled", disabled);
   if(dn != g_run_StratDisabledCount){
      PrintFormat("[NEXUS RUNTIME] strategie disattivate dalla dashboard: %d -> %d",
                  g_run_StratDisabledCount, dn);
   }
   ArrayResize(g_run_StratDisabled, dn);
   for(int i = 0; i < dn; ++i) g_run_StratDisabled[i] = disabled[i];
   g_run_StratDisabledCount = dn;

   // Moltiplicatori di rischio per-strategia — cache del sotto-oggetto JSON.
   g_run_StrategyRiskJson = _NXS_JsonObject(json, "strategy_risk");
}

#endif
