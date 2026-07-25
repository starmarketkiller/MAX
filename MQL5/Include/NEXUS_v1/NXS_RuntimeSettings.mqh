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

//: AUD0-SET-001 — variante che distingue "assente" da "false".
//: Serve alla pubblicazione atomica: un booleano non presente nel payload non
//: deve sovrascrivere il valore corrente con un default.
bool _NXS_JsonBoolOpt(const string &json, const string key, bool &out){
   string needle = "\"" + key + "\":";
   int p = StringFind(json, needle);
   if(p < 0) return false;
   int s = p + StringLen(needle);
   while(s < StringLen(json) && (StringGetCharacter(json, s) == ' '
         || StringGetCharacter(json, s) == '\t')) s++;
   string rest = StringSubstr(json, s, 5);
   if(StringFind(rest, "true") == 0){ out = true;  return true; }
   if(StringFind(rest, "false") == 0){ out = false; return true; }
   return false;
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

// AUD0-EXEC-008 — SEMANTICA DEL MOLTIPLICATORE DI RISCHIO REMOTO.
//
// Qualunque valore assente, malformato o non positivo ricadeva su 1.0, cioe'
// "rischio pieno". Per un valore accidentalmente a zero e' innocuo; per una
// richiesta del piano di controllo che voleva DISATTIVARE o ridurre
// drasticamente una strategia e' l'esatto contrario di cio' che era stato
// chiesto: il comando "azzera il rischio" diventava "rischio normale".
//
// I tre casi sono ora distinti:
//   chiave assente  -> 1.0 (nessuna istruzione: comportamento predefinito)
//   valore 0 o < 0  -> 0.0 (istruzione esplicita di NON operare)
//   valore malformato -> 0.0 + allarme (non si indovina cosa volesse dire)
//
// Un moltiplicatore 0.0 blocca l'apertura a valle, dove il lotto risultante
// non supera il minimo.
double NXS_Runtime_StrategyLotMult(const string name){
   if(StringLen(g_run_StrategyRiskJson) == 0) return 1.0;
   double v = _NXS_JsonNum(g_run_StrategyRiskJson, name);
   if(v == EMPTY_VALUE) return 1.0;              // nessuna istruzione per questa strategia
   if(v <= 0.0){
      PrintFormat("[NEXUS RUNTIME] moltiplicatore di rischio %.4f per '%s': "
                  "interpretato come DISATTIVAZIONE (nessuna nuova esposizione)",
                  v, name);
      return 0.0;
   }
   if(!MathIsValidNumber(v)){
      PrintFormat("[NEXUS RUNTIME][ALERT] moltiplicatore di rischio non valido per "
                  "'%s': la strategia viene DISATTIVATA invece di operare a "
                  "rischio pieno", name);
      return 0.0;
   }
   return v;
}

// AUD0-SET-001: le macro _RT_APPLY_NUM/_RT_APPLY_BOOL sono state rimosse.
// Scrivevano DIRETTAMENTE nelle globali mentre il resto del payload era
// ancora da interpretare, cioe' esattamente il percorso non atomico che
// l'audit segnala. La lettura ora passa da copie locali validate.

// AUD0-SET-002 — INTERVALLI LOCALI PER I VALORI REMOTI.
//
// Le macro applicavano qualunque numero arrivasse dal backend. Il piano di
// controllo ha i suoi limiti, ma l'EA e' l'ultimo anello prima del broker: un
// backend compromesso, un bug di serializzazione o un semplice errore di
// digitazione potevano portare RiskPercent a 400 o MaxDailyDDPct a 0.
//
// Ogni valore ha ora un intervallo locale. Fuori intervallo NON viene
// applicato — non viene "corretto" al limite piu' vicino: applicare un valore
// diverso da quello richiesto sarebbe altrettanto sbagliato, ma silenzioso.
bool _NXS_RangeOK(string key, double v, double lo, double hi){
   if(v >= lo && v <= hi) return true;
   PrintFormat("[NEXUS RUNTIME][ALERT] '%s'=%g fuori intervallo consentito "
               "[%g, %g]: valore RIFIUTATO, resta quello precedente", key, v, lo, hi);
   return false;
}

// AUD0-SET-004 — salute del canale impostazioni, prima invisibile.
datetime g_setLastOkPull   = 0;
int      g_setFailStreak   = 0;
int      g_setLastCode     = 0;
int      g_setRejectedVals = 0;

bool     NXS_Settings_Healthy(){ return g_setFailStreak < 5; }
datetime NXS_Settings_LastOk(){ return g_setLastOkPull; }
int      NXS_Settings_FailStreak(){ return g_setFailStreak; }
int      NXS_Settings_LastCode(){ return g_setLastCode; }

//: Eta' della configurazione in secondi (-1 se non e' mai stata scaricata).
long NXS_Settings_StaleSec(){
   if(g_setLastOkPull == 0) return -1;
   return (long)(TimeCurrent() - g_setLastOkPull);
}

void NXS_PullSettings(){
   if(!InpEnableWebSync) return;
   if(TimeCurrent() - g_lastSettingsPull < g_settingsPullSec) return;
   g_lastSettingsPull = TimeCurrent();

   string url = InpWebURL + "/api/ea/settings";
   char empty[]; char result[]; string headersOut;
   string headers = "X-Nexus-Token: " + InpWebToken + "\r\n";
   int code = WebRequest("GET", url, headers, 3000, empty, result, headersOut);
   g_setLastCode = code;
   if(code != 200){
      // AUD0-SET-004: qui si usciva in silenzio. L'EA poteva girare per giorni
      // con una configurazione vecchia — e nessuno, ne' in locale ne' sulla
      // dashboard, aveva modo di saperlo.
      g_setFailStreak++;
      if(g_setFailStreak == 1 || g_setFailStreak % 20 == 0){
         long age = NXS_Settings_StaleSec();
         PrintFormat("[NEXUS RUNTIME][ALERT] pull impostazioni fallito %d volte "
                     "(http=%d). Configurazione in uso vecchia di %s.",
                     g_setFailStreak, code,
                     (age < 0 ? "sempre (mai scaricata)" : IntegerToString(age) + "s"));
      }
      return;
   }
   string json = CharArrayToString(result, 0, -1, CP_UTF8);

   // AUD0-SET-003 — il parser e' a scansione di stringa: non gestisce
   // stringhe con escape, oggetti annidati profondi ne' chiavi duplicate.
   // Riscriverlo come parser JSON completo e' fuori portata qui, ma il caso
   // che produce un'interpretazione SILENZIOSAMENTE diversa — la stessa chiave
   // presente due volte, dove due lettori scelgono valori diversi — viene ora
   // rilevato e il payload rifiutato per intero.
   string dupCheck[] = {"RiskPercent","MaxLot","MaxDailyDDPct","MaxConcurrent",
                        "MaxTradesPerDay","strategy_risk","strategies_disabled"};
   for(int dk = 0; dk < ArraySize(dupCheck); dk++){
      string needle = "\"" + dupCheck[dk] + "\":";
      int first = StringFind(json, needle);
      if(first < 0) continue;
      if(StringFind(json, needle, first + StringLen(needle)) >= 0){
         g_setFailStreak++;
         PrintFormat("[NEXUS RUNTIME][ALERT] chiave '%s' duplicata nel payload "
                     "impostazioni: payload RIFIUTATO per intero (interpretazione "
                     "ambigua)", dupCheck[dk]);
         return;
      }
   }

   // AUD0-SET-001 — APPLICAZIONE ATOMICA.
   //
   // I valori venivano scritti direttamente nelle globali, uno a uno, mentre
   // il resto del payload era ancora da interpretare. Un tick che fosse
   // arrivato a meta' funzione avrebbe visto una configurazione IBRIDA — per
   // esempio il nuovo MaxLot con il vecchio RiskPercent — che non e' mai stata
   // approvata da nessuno.
   //
   // Ora si interpreta e si valida TUTTO su copie locali; le globali vengono
   // aggiornate solo alla fine, in blocco.
   double n_RiskPercent      = g_run_RiskPercent;
   double n_MaxLot           = g_run_MaxLot;
   int    n_MaxTradesPerDay  = g_run_MaxTradesPerDay;
   int    n_MaxConcurrent    = g_run_MaxConcurrent;
   double n_MaxDailyDDPct    = g_run_MaxDailyDDPct;
   int    n_MinEntryScore    = g_run_MinEntryScore;
   double n_AsianScoreMin    = g_run_AsianScoreMin;
   double n_LondonScoreMin   = g_run_LondonScoreMin;
   double n_OverlapScoreMin  = g_run_OverlapScoreMin;
   double n_NYScoreMin       = g_run_NYScoreMin;
   double n_AfterNYScoreMin  = g_run_AfterNYScoreMin;
   double n_AtrSLMult        = g_run_AtrSLMult;
   double n_AtrTPMult        = g_run_AtrTPMult;
   double n_BE_TriggerATR    = g_run_BE_TriggerATR;
   double n_TrailActivateATR = g_run_TrailActivateATR;
   double n_TrailDistanceATR = g_run_TrailDistanceATR;
   double n_TF_SLTP_H1       = g_run_TF_SLTP_H1;
   double n_TF_SLTP_H4       = g_run_TF_SLTP_H4;
   double n_TF_SLTP_D1       = g_run_TF_SLTP_D1;
   bool   n_UseNewsFilter    = g_run_UseNewsFilter;
   bool   n_UseHTFBias       = g_run_UseHTFBias;
   bool   n_UseVelocityGate  = g_run_UseVelocityGate;

   int rejected = 0;
   double _v;

   #define _RT_STAGE(TARGET, key, lo, hi, type) \
      { _v = _NXS_JsonNum(json, key); \
        if(_v != EMPTY_VALUE){ \
           if(_NXS_RangeOK(key, _v, lo, hi)) TARGET = (type)_v; else rejected++; } }

   _RT_STAGE(n_RiskPercent,      "RiskPercent",       0.01,   10.0, double);
   _RT_STAGE(n_MaxLot,           "MaxLot",            0.01,  100.0, double);
   _RT_STAGE(n_MaxTradesPerDay,  "MaxTradesPerDay",   1,      500,  int);
   _RT_STAGE(n_MaxConcurrent,    "MaxConcurrent",     1,       40,  int);
   _RT_STAGE(n_MaxDailyDDPct,    "MaxDailyDDPct",     0.1,    50.0, double);
   _RT_STAGE(n_MinEntryScore,    "MinEntryScore",     0,      100,  int);
   _RT_STAGE(n_AsianScoreMin,    "AsianScoreMin",     0,      100,  double);
   _RT_STAGE(n_LondonScoreMin,   "LondonScoreMin",    0,      100,  double);
   _RT_STAGE(n_OverlapScoreMin,  "OverlapScoreMin",   0,      100,  double);
   _RT_STAGE(n_NYScoreMin,       "NYScoreMin",        0,      100,  double);
   _RT_STAGE(n_AfterNYScoreMin,  "AfterNYScoreMin",   0,      100,  double);
   _RT_STAGE(n_AtrSLMult,        "ATR_SL_Mult",       0.1,     20.0, double);
   _RT_STAGE(n_AtrTPMult,        "ATR_TP_Mult",       0.1,     50.0, double);
   _RT_STAGE(n_BE_TriggerATR,    "BE_TriggerATR",     0.0,     20.0, double);
   _RT_STAGE(n_TrailActivateATR, "TrailActivateATR",  0.0,     20.0, double);
   _RT_STAGE(n_TrailDistanceATR, "TrailDistanceATR",  0.1,     20.0, double);
   _RT_STAGE(n_TF_SLTP_H1,       "TF_SLTP_H1",        0.1,     20.0, double);
   _RT_STAGE(n_TF_SLTP_H4,       "TF_SLTP_H4",        0.1,     20.0, double);
   _RT_STAGE(n_TF_SLTP_D1,       "TF_SLTP_D1",        0.1,     20.0, double);
   #undef _RT_STAGE

   bool bv;
   if(_NXS_JsonBoolOpt(json, "UseNewsFilter", bv))   n_UseNewsFilter   = bv;
   if(_NXS_JsonBoolOpt(json, "UseHTFBias", bv))      n_UseHTFBias      = bv;
   if(_NXS_JsonBoolOpt(json, "UseVelocityGate", bv)) n_UseVelocityGate = bv;

   // Strategie disattivate e moltiplicatori per-strategia: si interpretano
   // PRIMA di toccare qualunque globale, cosi' un payload rotto non lascia
   // meta' configurazione applicata.
   string disabled[];
   int dn = _NXS_JsonStrArray(json, "strategies_disabled", disabled);
   string riskJson = _NXS_JsonObject(json, "strategy_risk");

   // ---- da qui in poi: pubblicazione ATOMICA ----
   if(n_RiskPercent != g_run_RiskPercent)
      PrintFormat("[NEXUS RUNTIME] RiskPercent: %g -> %g", g_run_RiskPercent, n_RiskPercent);
   if(n_MaxDailyDDPct != g_run_MaxDailyDDPct)
      PrintFormat("[NEXUS RUNTIME] MaxDailyDDPct: %g -> %g", g_run_MaxDailyDDPct, n_MaxDailyDDPct);
   if(dn != g_run_StratDisabledCount)
      PrintFormat("[NEXUS RUNTIME] strategie disattivate dalla dashboard: %d -> %d",
                  g_run_StratDisabledCount, dn);

   g_run_RiskPercent      = n_RiskPercent;
   g_run_MaxLot           = n_MaxLot;
   g_run_MaxTradesPerDay  = n_MaxTradesPerDay;
   g_run_MaxConcurrent    = n_MaxConcurrent;
   g_run_MaxDailyDDPct    = n_MaxDailyDDPct;
   g_run_MinEntryScore    = n_MinEntryScore;
   g_run_AsianScoreMin    = n_AsianScoreMin;
   g_run_LondonScoreMin   = n_LondonScoreMin;
   g_run_OverlapScoreMin  = n_OverlapScoreMin;
   g_run_NYScoreMin       = n_NYScoreMin;
   g_run_AfterNYScoreMin  = n_AfterNYScoreMin;
   g_run_AtrSLMult        = n_AtrSLMult;
   g_run_AtrTPMult        = n_AtrTPMult;
   g_run_BE_TriggerATR    = n_BE_TriggerATR;
   g_run_TrailActivateATR = n_TrailActivateATR;
   g_run_TrailDistanceATR = n_TrailDistanceATR;
   g_run_TF_SLTP_H1       = n_TF_SLTP_H1;
   g_run_TF_SLTP_H4       = n_TF_SLTP_H4;
   g_run_TF_SLTP_D1       = n_TF_SLTP_D1;
   g_run_UseNewsFilter    = n_UseNewsFilter;
   g_run_UseHTFBias       = n_UseHTFBias;
   g_run_UseVelocityGate  = n_UseVelocityGate;

   ArrayResize(g_run_StratDisabled, dn);
   for(int i = 0; i < dn; ++i) g_run_StratDisabled[i] = disabled[i];
   g_run_StratDisabledCount = dn;
   g_run_StrategyRiskJson   = riskJson;

   g_setFailStreak   = 0;
   g_setLastOkPull   = TimeCurrent();
   g_setRejectedVals = rejected;
   if(rejected > 0)
      PrintFormat("[NEXUS RUNTIME] %d valori rifiutati perche' fuori intervallo: "
                  "restano quelli precedenti", rejected);
}

#endif
