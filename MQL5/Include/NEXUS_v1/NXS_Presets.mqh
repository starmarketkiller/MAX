//+------------------------------------------------------------------+
//|  NXS_Presets.mqh - 3 risk profiles overlay on shadow globals      |
//|  Applied AT INIT, after NXS_Runtime_Init, if InpRiskProfile != 0  |
//|  Conservative=1, Balanced=2 (default), Aggressive=3               |
//+------------------------------------------------------------------+
#ifndef __NXS_PRESETS_MQH__
#define __NXS_PRESETS_MQH__

enum ENUM_NXS_PRESET {
   PRESET_CUSTOM      = 0,
   PRESET_CONSERVATIVE= 1,
   PRESET_BALANCED    = 2,
   PRESET_AGGRESSIVE  = 3,
   PRESET_MVP_v206    = 4    // v2.0.6: solo 5 strategie MVP attive
};

// v2.0.6: runtime toggles override (shadow). Applied solo se PRESET_MVP_v206.
// Quando 0 = unchanged, 1 = force ON, -1 = force OFF.
int g_mvp_override_TurtleSoup     = 0;
int g_mvp_override_FVG_Mit        = 0;
int g_mvp_override_SH_BMS_RTO     = 0;
int g_mvp_override_SilverBullet   = 0;
int g_mvp_override_AMD_Reversal   = 0;
// Tutte le altre vengono "soft-disabled" via score floor (lasciamo enable=true ma il router le filtra)
bool g_mvp_profile_active = false;

void NXS_ApplyPreset(){
   if(InpRiskProfile == PRESET_CUSTOM){
      Print("[NEXUS PRESET] CUSTOM (using raw input values)");
      return;
   }

   string name = "";
   switch(InpRiskProfile){
      case PRESET_CONSERVATIVE:
         name = "CONSERVATIVE";
         g_run_RiskPercent     = 0.5;
         g_run_MaxLot          = 2.0;
         g_run_MaxTradesPerDay = 6;
         g_run_MaxConcurrent   = 2;
         g_run_MaxDailyDDPct   = 3.0;
         g_run_MinEntryScore   = 78;
         break;
      case PRESET_BALANCED:
         name = "BALANCED";
         g_run_RiskPercent     = 1.0;
         g_run_MaxLot          = 5.0;
         g_run_MaxTradesPerDay = 12;
         g_run_MaxConcurrent   = 4;
         g_run_MaxDailyDDPct   = 5.0;
         g_run_MinEntryScore   = 70;
         break;
      case PRESET_AGGRESSIVE:
         name = "AGGRESSIVE";
         g_run_RiskPercent     = 1.8;
         g_run_MaxLot          = 10.0;
         g_run_MaxTradesPerDay = 20;
         g_run_MaxConcurrent   = 6;
         g_run_MaxDailyDDPct   = 8.0;
         g_run_MinEntryScore   = 64;
         break;
      case PRESET_MVP_v206:
         // v2.0.6 MVP: 5 strategie MVP attive (Silver Bullet, AMD Reversal,
         // Turtle Soup, SH_BMS_RTO, FVG_MIT). Le altre rimangono enabled per
         // confluence/data collection ma con threshold più alto per evitare exec.
         name = "MVP_v206";
         g_run_RiskPercent     = 0.8;
         g_run_MaxLot          = 4.0;
         g_run_MaxTradesPerDay = 8;
         g_run_MaxConcurrent   = 3;
         g_run_MaxDailyDDPct   = 4.0;
         g_run_MinEntryScore   = 72;     // soft-filter non-MVP via score
         g_run_AsianScoreMin   = 75;     // restrict Asia (no MVP attivi)
         g_run_LondonScoreMin  = 60;     // London = MVP territory
         g_run_OverlapScoreMin = 58;
         g_run_NYScoreMin      = 60;
         g_run_AfterNYScoreMin = 78;
         g_mvp_profile_active  = true;
         break;
   }

   // Account-size auto scaling (defensive for small accounts)
   if(InpAutoScaleByAccount){
      double bal = AccountInfoDouble(ACCOUNT_BALANCE);
      double mult = 1.0;
      if(bal < 1000)        mult = 0.5;
      else if(bal < 5000)   mult = 0.75;
      else if(bal < 25000)  mult = 1.0;
      else if(bal < 100000) mult = 1.1;
      else                  mult = 1.2;
      g_run_RiskPercent   *= mult;
      g_run_MaxLot        *= mult;
      g_run_MaxDailyDDPct *= MathMin(1.0, mult);
      PrintFormat("[NEXUS PRESET] account-scaled by %.2fx (balance=%.2f)", mult, bal);
   }

   PrintFormat("[NEXUS PRESET] %s applied | risk=%.2f%% maxLot=%.2f maxTrades=%d maxConc=%d ddCap=%.1f%% minScore=%d",
               name, g_run_RiskPercent, g_run_MaxLot, g_run_MaxTradesPerDay,
               g_run_MaxConcurrent, g_run_MaxDailyDDPct, g_run_MinEntryScore);
}

#endif
