#pragma once
#property strict

input string InpLicenseKey = "";
input string InpLicenseApiBase = "https://YOUR_DOMAIN_HERE";
input int    InpVerifyHours = 6;
input bool   InpAllowManageOpenPositionsWhenInvalid = true;
input bool   InpLicenseLog = true;

static bool   g_license_ok = false;
static datetime g_last_ok = 0;
static datetime g_last_check = 0;
static int    g_grace_seconds = 172800;
static string g_last_code = "";
static string g_last_message = "";
static string g_last_expires = "";

static void LicLog(const string s)
{
  if(InpLicenseLog) Print("[LICENSE] ", s);
}

static string JsonEscape(const string s)
{
  string out = s;
  StringReplace(out, "\\", "\\\\");
  StringReplace(out, "\"", "\\\"");
  return out;
}

static string JsonGetString(const string json, const string key)
{
  string pattern = "\"" + key + "\":\"";
  int p = StringFind(json, pattern);
  if(p < 0) return "";
  p += StringLen(pattern);
  int e = StringFind(json, "\"", p);
  if(e < 0) return "";
  return StringSubstr(json, p, e - p);
}

static long JsonGetInt(const string json, const string key, const long defVal)
{
  string pattern = "\"" + key + "\":";
  int p = StringFind(json, pattern);
  if(p < 0) return defVal;
  p += StringLen(pattern);

  while(p < StringLen(json) && (StringGetCharacter(json, p) == ' ')) p++;

  int e = p;
  while(e < StringLen(json))
  {
    ushort c = (ushort)StringGetCharacter(json, e);
    if((c >= '0' && c <= '9') || c == '-') { e++; continue; }
    break;
  }
  if(e <= p) return defVal;

  string num = StringSubstr(json, p, e - p);
  return (long)StringToInteger(num);
}

static bool JsonHasStatusValid(const string json)
{
  return (StringFind(json, "\"status\":\"VALID\"") >= 0);
}

bool License_VerifyOnline()
{
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

  string body =
    "{"
    "\"license_key\":\"" + JsonEscape(InpLicenseKey) + "\"," 
    "\"account_login\":" + (string)login + ","
    "\"account_server\":\"" + JsonEscape(server) + "\"," 
    "\"ea_id\":\"MarketKiller\"," 
    "\"ea_version\":\"3.13\""
    "}";

  char post[];
  StringToCharArray(body, post, 0, WHOLE_ARRAY, CP_UTF8);

  int postSize = ArraySize(post);
  if(postSize > 0 && post[postSize - 1] == 0) postSize--;

  char result[];
  string headers;
  ResetLastError();

  int timeoutMs = 8000;
  string reqHeaders = "Content-Type: application/json\r\n";

  int res = WebRequest("POST", url, reqHeaders, timeoutMs, post, postSize, result, headers);

  if(res == -1)
  {
    int err = GetLastError();
    LicLog("WebRequest failed. err=" + (string)err + " (using grace if available)");
    return false;
  }

  string resp = CharArrayToString(result, 0, -1, CP_UTF8);

  bool ok = JsonHasStatusValid(resp);

  g_grace_seconds = (int)JsonGetInt(resp, "grace_seconds", 172800);
  g_last_code = JsonGetString(resp, "code");
  g_last_message = JsonGetString(resp, "message");
  g_last_expires = JsonGetString(resp, "expires_at");

  if(ok)
  {
    g_license_ok = true;
    g_last_ok = TimeCurrent();
    LicLog("VALID. code=" + g_last_code + " expires_at=" + g_last_expires);
    return true;
  }
  else
  {
    g_license_ok = false;
    LicLog("INVALID. code=" + g_last_code + " msg=" + g_last_message);
    return false;
  }
}

void License_Refresh()
{
  datetime now = TimeCurrent();

  int interval = MathMax(1, InpVerifyHours) * 3600;
  if(g_last_check != 0 && (now - g_last_check) < interval) return;

  g_last_check = now;

  bool onlineOk = License_VerifyOnline();
  if(onlineOk) return;

  if(g_last_ok > 0 && (now - g_last_ok) <= g_grace_seconds)
  {
    g_license_ok = true;
    LicLog("API unreachable but within grace. seconds_left=" + (string)(g_grace_seconds - (now - g_last_ok)));
  }
  else
  {
    g_license_ok = false;
    LicLog("Grace exceeded. Blocking new trades.");
  }
}

bool License_CanOpenNewTrades()
{
  return g_license_ok;
}

bool License_CanManageOpenTrades()
{
  return (g_license_ok || InpAllowManageOpenPositionsWhenInvalid);
}

string License_LastCode() { return g_last_code; }
string License_LastMessage() { return g_last_message; }
string License_LastExpiresAt() { return g_last_expires; }
