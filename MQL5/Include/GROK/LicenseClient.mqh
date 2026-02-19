#pragma once
#property strict

/*
Expected API examples:
VALID:
{"status":"VALID","expires_at":"2026-03-18T12:00:00.000Z","seats_used":1,"seats_max":2,"grace_seconds":172800,"code":"OK","message":"License valid"}
EXPIRED:
{"status":"INVALID","expires_at":"2026-02-10T12:00:00.000Z","seats_used":0,"seats_max":2,"grace_seconds":172800,"code":"EXPIRED","message":"Subscription expired"}
SEATS_FULL:
{"status":"INVALID","expires_at":"2026-03-18T12:00:00.000Z","seats_used":0,"seats_max":2,"grace_seconds":172800,"code":"SEATS_FULL","message":"Seats full (max 2 MT5 accounts)"}
NOT_FOUND:
{"status":"INVALID","expires_at":null,"seats_used":0,"seats_max":2,"grace_seconds":172800,"code":"NOT_FOUND","message":"License not found"}
SUSPENDED:
{"status":"INVALID","expires_at":"2026-03-18T12:00:00.000Z","seats_used":0,"seats_max":2,"grace_seconds":172800,"code":"SUSPENDED","message":"Subscription suspended (payment issue)"}
*/

extern string InpLicenseKey;
extern string InpLicenseApiBase;
extern string InpEaId;
extern string InpEaVersion;
extern int    InpVerifyHours;
extern int    InpGraceHours;
extern bool   InpAllowManageOpenPositionsWhenInvalid;
extern bool   InpBypassLicensingInStrategyTester;
extern bool   InpHardFailIfNoValidEver;
extern bool   InpShowLicensePanel;
extern bool   InpLogLicenseToFile;

bool   g_license_ok = false;
datetime g_last_ok = 0;
int    g_grace_seconds = 172800;
string g_last_code = "INIT";
string g_last_message = "";
string g_expires_at = "";
int    g_seats_used = 0;
int    g_seats_max = 2;

datetime g_license_last_check = 0;
string g_license_log_file = "Grok3xAI_license.log";
string g_license_gv_key = "Grok3xAI_LicenseLastOK";
string g_license_panel_bg = "Grok3xAI_LIC_BG";
string g_license_panel_text = "Grok3xAI_LIC_TXT";

string JsonEscape(const string s)
{
   string out = s;
   StringReplace(out, "\\", "\\\\");
   StringReplace(out, "\"", "\\\"");
   return out;
}

string JsonGetString(const string json, const string key)
{
   string pattern = "\"" + key + "\":\"";
   int p = StringFind(json, pattern);
   if(p < 0)
      return "";
   p += StringLen(pattern);
   int e = StringFind(json, "\"", p);
   if(e < 0)
      return "";
   return StringSubstr(json, p, e - p);
}

long JsonGetInt(const string json, const string key, const long defVal)
{
   string pattern = "\"" + key + "\":";
   int p = StringFind(json, pattern);
   if(p < 0)
      return defVal;
   p += StringLen(pattern);
   while(p < StringLen(json) && StringGetCharacter(json, p) == ' ')
      p++;
   int e = p;
   while(e < StringLen(json))
   {
      ushort c = (ushort)StringGetCharacter(json, e);
      if((c >= '0' && c <= '9') || c == '-')
      {
         e++;
         continue;
      }
      break;
   }
   if(e <= p)
      return defVal;
   return (long)StringToInteger(StringSubstr(json, p, e - p));
}

void License_LogDiag(const string reason)
{
   string msg = StringFormat("[LICENSE] %s | status=%s code=%s message=%s expires=%s seats=%d/%d last_ok=%s grace=%d",
                             reason,
                             (g_license_ok ? "VALID" : "INVALID"),
                             g_last_code,
                             g_last_message,
                             g_expires_at,
                             g_seats_used,
                             g_seats_max,
                             TimeToString(g_last_ok, TIME_DATE | TIME_SECONDS),
                             g_grace_seconds);
   Print(msg);

   if(!InpLogLicenseToFile)
      return;

   int h = FileOpen(g_license_log_file, FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
      h = FileOpen(g_license_log_file, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
      return;
   FileSeek(h, 0, SEEK_END);
   FileWriteString(h, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS) + " " + msg + "\r\n");
   FileClose(h);
}

string License_StatusText()
{
   if(g_license_ok)
      return "LICENSE: VALID " + g_last_code;

   datetime now = TimeCurrent();
   if(g_last_ok > 0 && (now - g_last_ok) <= g_grace_seconds)
   {
      int left = (int)(g_grace_seconds - (now - g_last_ok));
      return "LICENSE: GRACE " + (string)left + "s";
   }
   return "LICENSE: INVALID " + g_last_code;
}

void License_DrawPanel()
{
   if(!InpShowLicensePanel)
      return;

   if(ObjectFind(0, g_license_panel_bg) < 0)
      ObjectCreate(0, g_license_panel_bg, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, g_license_panel_bg, OBJPROP_XDISTANCE, 10);
   ObjectSetInteger(0, g_license_panel_bg, OBJPROP_YDISTANCE, 20);
   ObjectSetInteger(0, g_license_panel_bg, OBJPROP_XSIZE, 340);
   ObjectSetInteger(0, g_license_panel_bg, OBJPROP_YSIZE, 64);
   ObjectSetInteger(0, g_license_panel_bg, OBJPROP_BGCOLOR, clrBlack);
   ObjectSetInteger(0, g_license_panel_bg, OBJPROP_COLOR, g_license_ok ? clrLime : clrTomato);

   if(ObjectFind(0, g_license_panel_text) < 0)
      ObjectCreate(0, g_license_panel_text, OBJ_LABEL, 0, 0, 0);

   string txt = License_StatusText() +
                "\ncode=" + g_last_code + " seats=" + (string)g_seats_used + "/" + (string)g_seats_max +
                " expires=" + g_expires_at;

   ObjectSetInteger(0, g_license_panel_text, OBJPROP_XDISTANCE, 18);
   ObjectSetInteger(0, g_license_panel_text, OBJPROP_YDISTANCE, 28);
   ObjectSetString(0, g_license_panel_text, OBJPROP_TEXT, txt);
   ObjectSetInteger(0, g_license_panel_text, OBJPROP_COLOR, g_license_ok ? clrLime : clrTomato);
}

bool License_VerifyOnline()
{
   if(MQLInfoInteger(MQL_TESTER) && InpBypassLicensingInStrategyTester)
   {
      g_license_ok = true;
      g_last_code = "TESTER_BYPASS";
      g_last_message = "Bypass in strategy tester";
      return true;
   }

   if(StringLen(InpLicenseKey) < 10)
   {
      g_license_ok = false;
      g_last_code = "NO_KEY";
      g_last_message = "License key missing";
      return false;
   }

   string url = InpLicenseApiBase + "/api/v1/license/verify";
   long login = (long)AccountInfoInteger(ACCOUNT_LOGIN);
   string server = AccountInfoString(ACCOUNT_SERVER);

   string body = "{" +
                 "\"license_key\":\"" + JsonEscape(InpLicenseKey) + "\"," +
                 "\"account_login\":" + (string)login + "," +
                 "\"account_server\":\"" + JsonEscape(server) + "\"," +
                 "\"ea_id\":\"" + JsonEscape(InpEaId) + "\"," +
                 "\"ea_version\":\"" + JsonEscape(InpEaVersion) + "\"" +
                 "}";

   char post[];
   StringToCharArray(body, post, 0, WHOLE_ARRAY, CP_UTF8);
   int postSize = ArraySize(post);
   if(postSize > 0 && post[postSize - 1] == 0)
      postSize--;

   char result[];
   string headers;
   string reqHeaders = "Content-Type: application/json\r\n";

   ResetLastError();
   int res = WebRequest("POST", url, reqHeaders, 8000, post, postSize, result, headers);
   if(res == -1)
   {
      g_last_code = "WEBREQUEST_FAIL";
      g_last_message = "err=" + (string)GetLastError();
      return false;
   }

   string resp = CharArrayToString(result, 0, -1, CP_UTF8);
   bool ok = (StringFind(resp, "\"status\":\"VALID\"") >= 0);

   g_last_code = JsonGetString(resp, "code");
   g_last_message = JsonGetString(resp, "message");
   g_expires_at = JsonGetString(resp, "expires_at");
   g_seats_used = (int)JsonGetInt(resp, "seats_used", 0);
   g_seats_max = (int)JsonGetInt(resp, "seats_max", 2);
   g_grace_seconds = (int)JsonGetInt(resp, "grace_seconds", InpGraceHours * 3600);

   if(ok)
   {
      g_license_ok = true;
      g_last_ok = TimeCurrent();
      GlobalVariableSet(g_license_gv_key, (double)g_last_ok);
   }
   else
   {
      g_license_ok = false;
   }
   return ok;
}

void License_Refresh(bool force = false)
{
   if(MQLInfoInteger(MQL_TESTER) && InpBypassLicensingInStrategyTester)
   {
      g_license_ok = true;
      g_last_code = "TESTER_BYPASS";
      return;
   }

   datetime now = TimeCurrent();
   int intervalSec = MathMax(1, InpVerifyHours) * 3600;
   if(!force && g_license_last_check > 0 && (now - g_license_last_check) < intervalSec)
      return;

   g_license_last_check = now;

   bool okOnline = License_VerifyOnline();
   if(okOnline)
   {
      License_LogDiag("verify_ok");
      return;
   }

   if(g_last_ok == 0 && GlobalVariableCheck(g_license_gv_key))
      g_last_ok = (datetime)GlobalVariableGet(g_license_gv_key);

   if(g_last_ok == 0 && InpHardFailIfNoValidEver)
   {
      g_license_ok = false;
      g_last_code = "NO_VALID_EVER";
      License_LogDiag("hard_fail_no_valid_ever");
      return;
   }

   int graceSec = MathMax(1, InpGraceHours) * 3600;
   if(g_grace_seconds <= 0)
      g_grace_seconds = graceSec;

   if(g_last_ok > 0 && (now - g_last_ok) <= g_grace_seconds)
   {
      g_license_ok = true;
      g_last_code = "GRACE";
      License_LogDiag("grace_continue");
   }
   else
   {
      g_license_ok = false;
      if(g_last_code == "")
         g_last_code = "GRACE_EXCEEDED";
      License_LogDiag("grace_expired");
   }
}

void License_Init()
{
   g_grace_seconds = MathMax(1, InpGraceHours) * 3600;
   g_license_last_check = 0;
   if(GlobalVariableCheck(g_license_gv_key))
      g_last_ok = (datetime)GlobalVariableGet(g_license_gv_key);
   else
      g_last_ok = 0;
}

void License_OnTimer()
{
   License_Refresh(false);
   if(InpShowLicensePanel)
      License_DrawPanel();
}

bool License_CanOpenNewTrades()
{
   return g_license_ok;
}

bool License_CanManageOpenTrades()
{
   return (g_license_ok || InpAllowManageOpenPositionsWhenInvalid);
}

void License_Deinit()
{
   ObjectDelete(0, g_license_panel_bg);
   ObjectDelete(0, g_license_panel_text);
}
