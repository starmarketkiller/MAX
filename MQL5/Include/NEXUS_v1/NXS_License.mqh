//+------------------------------------------------------------------+
//|  NXS_License.mqh - License binding & expiration                   |
//|  Validates licenseKey against backend at OnInit + every hour.     |
//|  Trial mode: 14 days, max 0.01 lots, watermark on chart.          |
//+------------------------------------------------------------------+
#ifndef __NXS_LICENSE_MQH__
#define __NXS_LICENSE_MQH__

bool     g_licOK         = false;
bool     g_licTrial      = false;
datetime g_licExpiresAt  = 0;
datetime g_licLastCheck  = 0;
string   g_licClientName = "";
string   g_licPlan       = "";
int      g_licCheckSec   = 3600;        // re-validate every hour
int      g_licGracePeriod= 86400 * 3;   // 3 days offline grace if backend unreachable
datetime g_licLastOK     = 0;

// Extract string value for "\"key\":\"value\"" from json
string _NXS_LicJsonStr(const string &json, const string key){
   string needle = "\"" + key + "\":\"";
   int p = StringFind(json, needle);
   if(p < 0) return "";
   int s = p + StringLen(needle);
   int e = StringFind(json, "\"", s);
   if(e <= s) return "";
   return StringSubstr(json, s, e - s);
}

bool _NXS_LicJsonBool(const string &json, const string key){
   string needle = "\"" + key + "\":";
   int p = StringFind(json, needle);
   if(p < 0) return false;
   int s = p + StringLen(needle);
   while(s < StringLen(json) && StringGetCharacter(json, s) == ' ') s++;
   return (StringFind(StringSubstr(json, s, 4), "true") == 0);
}

long _NXS_LicJsonLong(const string &json, const string key){
   string needle = "\"" + key + "\":";
   int p = StringFind(json, needle);
   if(p < 0) return 0;
   int s = p + StringLen(needle), e = s;
   while(e < StringLen(json)){
      ushort c = StringGetCharacter(json, e);
      if((c >= '0' && c <= '9') || c == '-') e++; else break;
   }
   if(e == s) return 0;
   return StringToInteger(StringSubstr(json, s, e - s));
}

bool NXS_License_Verify(){
   // AUDITPATCH: Strategy Tester is an offline deterministic environment.
   // Never convert a backtest into TRIAL mode (0.01 lot cap) because WebRequest
   // is unavailable or the local backend is not running.
   if(MQLInfoInteger(MQL_TESTER)){
      g_licOK = true;
      g_licTrial = false;
      g_licPlan = "TESTER";
      return true;
   }
   if(!InpEnableLicense){
      g_licOK = true;
      return true;
   }
   if(TimeCurrent() - g_licLastCheck < g_licCheckSec && g_licOK) return true;
   g_licLastCheck = TimeCurrent();

   long acc = AccountInfoInteger(ACCOUNT_LOGIN);
   string body = StringFormat("{\"key\":\"%s\",\"account\":%I64d,\"symbol\":\"%s\",\"version\":\"%s\"}",
                              InpLicenseKey, acc, _Symbol, NEXUS_VERSION);
   string url = InpWebURL + "/api/license/verify";
   char post[]; StringToCharArray(body, post, 0, -1, CP_UTF8);
   ArrayResize(post, ArraySize(post) - 1);
   char result[]; string headersOut;
   string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";
   int code = WebRequest("POST", url, headers, 5000, post, result, headersOut);

   if(code != 200){
      // grace period: if we had a valid license recently, allow offline
      if(g_licLastOK > 0 && TimeCurrent() - g_licLastOK < g_licGracePeriod){
         PrintFormat("[NEXUS LIC] verify offline code=%d - using grace period", code);
         return g_licOK;
      }
      // No license + no backend: TRIAL fallback for new installs
      g_licTrial = true;
      g_licExpiresAt = TimeCurrent() + 14 * 86400;
      g_licClientName = "TRIAL";
      g_licPlan = "TRIAL";
      g_licOK = true;
      PrintFormat("[NEXUS LIC] backend unreachable - TRIAL mode (14 days, max 0.01 lots)");
      return true;
   }
   string resp = CharArrayToString(result, 0, -1, CP_UTF8);
   bool valid = _NXS_LicJsonBool(resp, "valid");
   if(!valid){
      string reason = _NXS_LicJsonStr(resp, "reason");
      PrintFormat("[NEXUS LIC] REJECTED reason=%s", reason);
      g_licOK = false;
      return false;
   }
   g_licOK         = true;
   g_licTrial      = _NXS_LicJsonBool(resp, "trial");
   long expTs      = _NXS_LicJsonLong(resp, "expires_at");
   g_licExpiresAt  = (expTs > 0) ? (datetime)expTs : 0;
   g_licClientName = _NXS_LicJsonStr(resp, "client");
   g_licPlan       = _NXS_LicJsonStr(resp, "plan");
   g_licLastOK     = TimeCurrent();
   PrintFormat("[NEXUS LIC] OK client=%s plan=%s trial=%s expires=%s",
               g_licClientName, g_licPlan, (g_licTrial?"YES":"NO"),
               (g_licExpiresAt > 0 ? TimeToString(g_licExpiresAt) : "never"));
   return true;
}

bool NXS_License_Enforce(){
   if(MQLInfoInteger(MQL_TESTER)) return true;
   if(!InpEnableLicense) return true;
   if(g_licExpiresAt > 0 && TimeCurrent() > g_licExpiresAt){
      Print("[NEXUS LIC] License EXPIRED - trading disabled");
      g_licOK = false;
      return false;
   }
   return g_licOK;
}

// Trial enforcement: caps lot size to 0.01
double NXS_License_CapLot(double requested){
   if(MQLInfoInteger(MQL_TESTER)) return requested;
   if(g_licTrial) return MathMin(requested, 0.01);
   return requested;
}

string NXS_License_Status(){
   if(!InpEnableLicense) return "DISABLED";
   if(!g_licOK)          return "INVALID";
   if(g_licTrial)        return "TRIAL";
   if(g_licExpiresAt > 0 && TimeCurrent() > g_licExpiresAt) return "EXPIRED";
   return "VALID";
}

#endif
