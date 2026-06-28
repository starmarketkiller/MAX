//+------------------------------------------------------------------+
//|  NXS_SymbolProfile.mqh - Multi-symbol auto-config                 |
//|  Detects asset class (Metal/Forex/Index/Crypto) and adapts:       |
//|   - ATR SL/TP multipliers                                         |
//|   - Spread caps                                                   |
//|   - Pip value calculation                                         |
//|  Also resolves broker symbol suffix variants (XAUUSD.m, GOLD).    |
//+------------------------------------------------------------------+
#ifndef __NXS_SYMBOL_PROFILE_MQH__
#define __NXS_SYMBOL_PROFILE_MQH__

enum ENUM_NXS_ASSET_CLASS {
   ASSET_UNKNOWN = 0,
   ASSET_METAL,
   ASSET_FOREX_MAJOR,
   ASSET_FOREX_CROSS,
   ASSET_INDEX,
   ASSET_CRYPTO,
   ASSET_OIL
};

struct SNXSSymbolProfile {
   ENUM_NXS_ASSET_CLASS klass;
   string  baseSymbol;     // canonical (XAUUSD, EURUSD, US30, BTCUSD)
   string  brokerSymbol;   // resolved (XAUUSD.m, GOLD, etc.)
   double  pipSize;        // 0.01 for XAUUSD, 0.0001 for EURUSD, 0.01 for JPY pairs
   int     pipDigits;      // 2 for XAUUSD, 4 for EURUSD, 2 for JPY pairs
   double  atrSLMult;
   double  atrTPMult;
   int     maxSpreadPts;
   bool    allowed;
   string  className;
};

SNXSSymbolProfile g_profile;

// Try multiple broker suffix variants
string NXS_ResolveBrokerSymbol(string baseSym){
   string variants[] = { "", ".m", ".raw", "_m", "#", ".pro", "+", "i" };
   string suffixes[] = { "", "MICRO" };
   // also try uppercase/replace XAUUSD -> GOLD
   string aliases[] = { baseSym, baseSym };
   if(baseSym == "XAUUSD"){ aliases[0] = "XAUUSD"; aliases[1] = "GOLD"; }
   else if(baseSym == "XAGUSD"){ aliases[0] = "XAGUSD"; aliases[1] = "SILVER"; }
   else if(baseSym == "US30"){ aliases[0] = "US30"; aliases[1] = "DJ30"; }
   else if(baseSym == "NAS100"){ aliases[0] = "NAS100"; aliases[1] = "USTEC"; }
   else if(baseSym == "BTCUSD"){ aliases[0] = "BTCUSD"; aliases[1] = "BTCUSDT"; }

   for(int a = 0; a < ArraySize(aliases); a++){
      for(int v = 0; v < ArraySize(variants); v++){
         string candidate = aliases[a] + variants[v];
         if(SymbolSelect(candidate, true)){
            return candidate;
         }
      }
   }
   return baseSym;   // fallback
}

ENUM_NXS_ASSET_CLASS NXS_ClassifySymbol(string sym){
   string s = sym;
   StringToUpper(s);
   if(StringFind(s, "XAU") >= 0 || StringFind(s, "GOLD") >= 0)   return ASSET_METAL;
   if(StringFind(s, "XAG") >= 0 || StringFind(s, "SILVER") >= 0) return ASSET_METAL;
   if(StringFind(s, "BTC") >= 0 || StringFind(s, "ETH") >= 0
      || StringFind(s, "LTC") >= 0 || StringFind(s, "XRP") >= 0) return ASSET_CRYPTO;
   if(StringFind(s, "US30") >= 0 || StringFind(s, "DJ") >= 0
      || StringFind(s, "NAS") >= 0 || StringFind(s, "SPX") >= 0
      || StringFind(s, "GER") >= 0 || StringFind(s, "DAX") >= 0
      || StringFind(s, "UK100") >= 0 || StringFind(s, "FTSE") >= 0) return ASSET_INDEX;
   if(StringFind(s, "WTI") >= 0 || StringFind(s, "OIL") >= 0
      || StringFind(s, "BRENT") >= 0) return ASSET_OIL;
   // Forex
   string majors[] = {"EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","USDCAD","NZDUSD"};
   for(int i = 0; i < ArraySize(majors); i++)
      if(StringFind(s, majors[i]) >= 0) return ASSET_FOREX_MAJOR;
   if(StringLen(s) >= 6) return ASSET_FOREX_CROSS;
   return ASSET_UNKNOWN;
}

void NXS_BuildSymbolProfile(){
   g_profile.brokerSymbol = _Symbol;
   g_profile.baseSymbol   = _Symbol;
   g_profile.klass        = NXS_ClassifySymbol(_Symbol);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   switch(g_profile.klass){
      case ASSET_METAL:
         g_profile.pipSize    = 0.01;
         g_profile.pipDigits  = 2;
         g_profile.atrSLMult  = 1.8;
         g_profile.atrTPMult  = 2.8;
         g_profile.maxSpreadPts = 80;     // XAUUSD can have 40-60 pts normal
         g_profile.className  = "METAL";
         break;
      case ASSET_FOREX_MAJOR:
         g_profile.pipSize    = (digits >= 4) ? 0.0001 : 0.01;
         g_profile.pipDigits  = (digits >= 4) ? 4 : 2;
         g_profile.atrSLMult  = 1.5;
         g_profile.atrTPMult  = 2.3;
         g_profile.maxSpreadPts = 25;
         g_profile.className  = "FX_MAJOR";
         break;
      case ASSET_FOREX_CROSS:
         g_profile.pipSize    = (digits >= 4) ? 0.0001 : 0.01;
         g_profile.pipDigits  = (digits >= 4) ? 4 : 2;
         g_profile.atrSLMult  = 1.8;
         g_profile.atrTPMult  = 2.5;
         g_profile.maxSpreadPts = 40;
         g_profile.className  = "FX_CROSS";
         break;
      case ASSET_INDEX:
         g_profile.pipSize    = 1.0;
         g_profile.pipDigits  = 1;
         g_profile.atrSLMult  = 2.0;
         g_profile.atrTPMult  = 3.0;
         g_profile.maxSpreadPts = 150;
         g_profile.className  = "INDEX";
         break;
      case ASSET_CRYPTO:
         g_profile.pipSize    = 1.0;
         g_profile.pipDigits  = (digits >= 2) ? 2 : 0;
         g_profile.atrSLMult  = 2.2;
         g_profile.atrTPMult  = 3.5;
         g_profile.maxSpreadPts = 500;
         g_profile.className  = "CRYPTO";
         break;
      case ASSET_OIL:
         g_profile.pipSize    = 0.01;
         g_profile.pipDigits  = 2;
         g_profile.atrSLMult  = 1.8;
         g_profile.atrTPMult  = 2.8;
         g_profile.maxSpreadPts = 60;
         g_profile.className  = "OIL";
         break;
      default:
         g_profile.pipSize    = MathPow(10, -digits + 1);
         g_profile.pipDigits  = digits;
         g_profile.atrSLMult  = 1.8;
         g_profile.atrTPMult  = 2.6;
         g_profile.maxSpreadPts = 100;
         g_profile.className  = "UNKNOWN";
   }

   // Whitelist check
   g_profile.allowed = true;
   if(InpUseSymbolWhitelist && StringLen(InpAllowedSymbols) > 0){
      string list = InpAllowedSymbols + ",";
      string up = _Symbol; StringToUpper(up);
      // Strip suffix for the check (XAUUSD.m -> XAUUSD)
      string root = up;
      for(int i = 0; i < StringLen(root); i++){
         ushort c = StringGetCharacter(root, i);
         if(!((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9'))){
            root = StringSubstr(root, 0, i);
            break;
         }
      }
      string listUp = list; StringToUpper(listUp);
      if(StringFind(listUp, root + ",") < 0 && StringFind(listUp, root) < 0){
         g_profile.allowed = false;
      }
   }

   PrintFormat("[NEXUS PROFILE] symbol=%s class=%s pipSize=%.5f digits=%d atrSL=%.2f atrTP=%.2f maxSpread=%d allowed=%s",
               _Symbol, g_profile.className, g_profile.pipSize, g_profile.pipDigits,
               g_profile.atrSLMult, g_profile.atrTPMult, g_profile.maxSpreadPts,
               (g_profile.allowed ? "YES":"NO"));
}

#endif
