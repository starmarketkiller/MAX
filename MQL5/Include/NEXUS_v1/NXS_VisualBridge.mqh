//+------------------------------------------------------------------+
//|  NXS_VisualBridge.mqh                                             |
//|  NEXUS v2.0.4 - One-way EA -> Indicator bridge                    |
//|                                                                   |
//|  Exports lightweight EA state via GlobalVariable so the           |
//|  companion indicator NEXUS_VisualSuite_v2.mq5 can render          |
//|  without inspecting EA internals.                                 |
//|                                                                   |
//|  Cost: ~20 GlobalVariableSet per call. Called once per tick.      |
//|  No trading logic. No file I/O. No allocations.                   |
//+------------------------------------------------------------------+
#ifndef __NXS_VISUAL_BRIDGE_MQH__
#define __NXS_VISUAL_BRIDGE_MQH__

void _nxs_gv_set(string key, double v){
   GlobalVariableSet("NXS_" + g_sym + "_" + key, v);
}

// Convert ENUM_NXS_VEL to int (matches indicator VelName switch)
int _nxs_velCode(ENUM_NXS_VEL v){
   switch(v){
      case VEL_BULL:    return 1;
      case VEL_BEAR:    return 2;
      case VEL_BULL_PB: return 3;
      case VEL_BEAR_PB: return 4;
   }
   return 0;
}

int _nxs_htfCode(ENUM_NXS_HTF h){
   if(h == HTF_BULL) return 1;
   if(h == HTF_BEAR) return 2;
   return 0;
}

int _nxs_amdCode(ENUM_NXS_AMD a){
   if(a == AMD_ACCUMULATION) return 1;
   if(a == AMD_MANIPULATION) return 2;
   if(a == AMD_DISTRIBUTION) return 3;
   return 0;
}

// Find dominant blocker (highest non-NONE counter) for HUD display
int _nxs_dominantBlocker(){
   long maxV = 0;
   int  maxI = 0;
   for(int i = 1; i < BLK_MAX; i++){
      if(g_blockCount[i] > maxV){ maxV = g_blockCount[i]; maxI = i; }
   }
   return maxI;
}

void NXS_ExportStateToGV(SNXSHTF &htf, SNXSVel &vel, SNXSAMD &amd,
                         SNXSSignal &best){
   int lastBlocker = _nxs_dominantBlocker();
   _nxs_gv_set("velocity_state",      (double)_nxs_velCode(vel.state));
   _nxs_gv_set("velocity_slope",      vel.slope);
   _nxs_gv_set("pressure_pct",        NXS_GetBSP());
   _nxs_gv_set("active_strat",        (best.dir == DIR_NONE) ? -1 : (double)best.strat);
   _nxs_gv_set("active_score",        best.score);
   _nxs_gv_set("last_blocker",        (double)lastBlocker);
   _nxs_gv_set("struct_trend_entry",  (double)g_structEntry.trend);
   _nxs_gv_set("struct_trend_medium", (double)g_structMedium.trend);
   _nxs_gv_set("struct_trend_high",   (double)g_structHigh.trend);
   _nxs_gv_set("htf_bias",            (double)_nxs_htfCode(htf.bias));
   _nxs_gv_set("amd_phase",           (double)_nxs_amdCode(amd.phase));
   _nxs_gv_set("asian_hi",            amd.asianHigh);
   _nxs_gv_set("asian_lo",            amd.asianLow);
   _nxs_gv_set("pdh",                 iHigh(g_sym, PERIOD_D1, 1));
   _nxs_gv_set("pdl",                 iLow (g_sym, PERIOD_D1, 1));

   // Fib context (built fresh from medium TF, same as OTE strategy)
   SNXSFib f = NXS_Fib_Build(InpTFMedium, 30);
   _nxs_gv_set("ote62",               f.ote62);
   _nxs_gv_set("ote705",              f.ote705);
   _nxs_gv_set("ote79",               f.ote79);
   _nxs_gv_set("fib_swingHi",         f.swingHigh);
   _nxs_gv_set("fib_swingLo",         f.swingLow);

   _nxs_gv_set("reaction_dir",        (double)g_reaction.direction);
   _nxs_gv_set("reaction_quality",    g_reaction.quality);
   _nxs_gv_set("ea_paused",           g_eaPaused ? 1.0 : 0.0);
}

#endif
