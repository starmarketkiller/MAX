//+------------------------------------------------------------------+
//|  NXS_Diagnostics.mqh - verbose diagnostic logging for debugging   |
//|  Tells you EXACTLY what's wrong / missing / blocked.              |
//+------------------------------------------------------------------+
#ifndef __NXS_DIAGNOSTICS_MQH__
#define __NXS_DIAGNOSTICS_MQH__

datetime g_lastDiagPrint   = 0;
int      g_diagIntervalSec = 60;   // print summary every 60s

// One-shot at OnInit — prints config + tests the backend bridge
void NXS_Diag_OnInit(){
   Print("================================================================");
   Print("[NEXUS DIAG] NEXUS EA v", NEXUS_VERSION, " booting on ", _Symbol,
         " | TF entry=", EnumToString(InpTFEntry),
         " | magic=", InpMagic);
   Print("[NEXUS DIAG] Account: #", AccountInfoInteger(ACCOUNT_LOGIN),
         " | Balance=", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
         " | Currency=", AccountInfoString(ACCOUNT_CURRENCY),
         " | Leverage=1:", AccountInfoInteger(ACCOUNT_LEVERAGE),
         " | Demo=", (AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_DEMO ? "YES" : "NO"));
   Print("[NEXUS DIAG] Symbol: digits=", _Digits, " point=", _Point,
         " min_lot=", SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN),
         " max_lot=", SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX),
         " step=", SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP),
         " spread=", (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD));

   // === Trading permissions ===
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
      Print("[NEXUS ERROR] Auto-trading DISABLED in MQL -> click the 'AlgoTrading' button in MT5 toolbar");
   if(!AccountInfoInteger(ACCOUNT_TRADE_EXPERT))
      Print("[NEXUS ERROR] EA trading DISABLED on this account (server-side)");
   if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))
      Print("[NEXUS ERROR] Trading DISABLED on this account (broker)");
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
      Print("[NEXUS ERROR] Trading DISABLED in Terminal Options -> Tools -> Options -> Expert Advisors");

   // === WebRequest config ===
   if(InpEnableWebSync){
      Print("[NEXUS DIAG] WebSync target: ", InpWebURL);
      Print("[NEXUS DIAG] WebRequest test pending - first push will reveal allow-list status.");
      Print("[NEXUS DIAG] If you see error 4060/4014 below: go to Tools -> Options -> Expert Advisors -> 'Allow WebRequest for'");
      Print("[NEXUS DIAG] and ADD this URL: ", InpWebURL);
   } else {
      Print("[NEXUS DIAG] WebSync DISABLED (InpEnableWebSync=false) - running standalone.");
   }

   // === Runtime config snapshot ===
   Print("[NEXUS DIAG] Risk: ", DoubleToString(InpRiskPercent, 2), "% | MaxLot=", DoubleToString(InpMaxLot, 2),
         " | MaxTradesPerDay=", InpMaxTradesPerDay, " | MaxConcurrent=", InpMaxConcurrent,
         " | MaxDailyDDPct=", DoubleToString(InpMaxDailyDDPct, 2), "%");
   Print("[NEXUS DIAG] Gates: HTF=", InpUseHTFBias, " Velocity=", InpUseVelocity,
         " News=", InpUseNews, " AMD=", InpUseAMD, " BSP=", InpUseBSP,
         " Sessions=", InpUseSessions, " Structure=", InpUseStructure, " Reaction=", InpUseReaction);
   Print("[NEXUS DIAG] Protections: ESL=", InpUseESL, "(", DoubleToString(InpESL_Value, 1), "%)",
         " DPT=", InpUseDPT, "(", DoubleToString(InpDPT_Value, 1), "%)",
         " MaxHold=", InpUseMaxHold, "(", InpProt_MaxHoldHours, "h)",
         " AutoClose=", InpUseAutoClose);
   Print("[NEXUS DIAG] Confluence=", InpUseConfluence, " ADXRsiCap=", InpADXRsiScoreCap,
         " StrategyCD=", InpUseStrategyCD, "(", InpMaxConsecPerStrat, "->", InpStratCooldownMin, "m)");
   Print("[NEXUS DIAG] Audit: MTF=", InpUseMTFValidation, "(", EnumToString(InpMTF_TF1), "+", EnumToString(InpMTF_TF2), ")",
         " DynSpread=", InpUseDynamicSpread, "(", DoubleToString(InpMaxSpreadAtrPct, 1), "% ATR)",
         " VolRegime=", InpUseVolRegime);
   Print("================================================================");
}

// Called every tick - prints a compact summary every g_diagIntervalSec
void NXS_Diag_OnTick(string htfBiasStr, string velStr, string amdPhase, double bsp_v){
   if(!InpDebugLog) return;
   if(TimeCurrent() - g_lastDiagPrint < g_diagIntervalSec) return;
   g_lastDiagPrint = TimeCurrent();

   double dd = (g_balanceDayStart > 0)
               ? ((AccountInfoDouble(ACCOUNT_BALANCE) - AccountInfoDouble(ACCOUNT_EQUITY)) / g_balanceDayStart * 100.0)
               : 0;

   PrintFormat("[NEXUS DIAG %s] HTF=%s VEL=%s AMD=%s BSP=%.0f%% ATR=%.5f Spread=%d trades_today=%d float=%.2f DD=%.2f%% positions=%d",
               TimeToString(TimeCurrent(), TIME_MINUTES),
               htfBiasStr, velStr, amdPhase, bsp_v,
               g_atr,
               (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD),
               g_tradesToday,
               NXS_FloatingPnL(),
               dd,
               PositionsTotal());

   // Active blockers report
   string blockers = "";
   if(g_eaPaused)                              blockers += "PAUSED ";
   if(g_eslHit)                                blockers += "ESL_HIT ";
   if(g_dptHit)                                blockers += "DPT_HIT ";
   if(g_pausedUntilNextOpen)                   blockers += "DAY_PAUSED ";
   if(g_autoClosePending)                      blockers += "AUTOCLOSE_WINDOW ";
   if(g_tradesToday >= g_run_MaxTradesPerDay)  blockers += "MAX_TRADES_REACHED ";
   if(PositionsTotal() >= g_run_MaxConcurrent) blockers += "MAX_CONCURRENT ";
   if(StringLen(blockers) > 0)
      PrintFormat("[NEXUS DIAG] BLOCKERS active: %s", blockers);
}

// Called on trade execution failure
void NXS_Diag_TradeFail(string strategy, int dir, double lots, double price, int retcode){
   string reason = "OTHER";
   if(retcode == 10004) reason = "REQUOTE";
   else if(retcode == 10006) reason = "REJECTED";
   else if(retcode == 10013) reason = "INVALID_REQUEST";
   else if(retcode == 10014) reason = "INVALID_VOLUME";
   else if(retcode == 10015) reason = "INVALID_PRICE";
   else if(retcode == 10016) reason = "INVALID_STOPS";
   else if(retcode == 10018) reason = "MARKET_CLOSED";
   else if(retcode == 10019) reason = "NO_MONEY";
   else if(retcode == 10027) reason = "AUTOTRADING_DISABLED";
   PrintFormat("[NEXUS ERROR] Trade FAILED | strategy=%s dir=%d lots=%.2f price=%.5f retcode=%d (%s)",
               strategy, dir, lots, price, retcode, reason);
}

// Called when web push fails
void NXS_Diag_WebFail(string endpoint, int httpCode){
   string hint = "";
   if(httpCode == -1 || httpCode == 4060) hint = " | URL not in MT5 WebRequest allow-list";
   else if(httpCode == 0)   hint = " | network down or server unreachable";
   else if(httpCode == 401) hint = " | X-Nexus-Token mismatch - check NEXUS_API_TOKEN in backend .env vs InpWebToken";
   else if(httpCode == 404) hint = " | backend route not deployed";
   else if(httpCode == 500) hint = " | backend exception - check server logs";
   PrintFormat("[NEXUS ERROR] WebRequest %s FAILED | http=%d%s", endpoint, httpCode, hint);
}

#endif
