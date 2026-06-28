//+------------------------------------------------------------------+
//|  NXS_SignalRouter.mqh                                             |
//|  Phase 2 - Collect all signals, sort by score, try fallback       |
//+------------------------------------------------------------------+
#ifndef __NXS_SIGNAL_ROUTER_MQH__
#define __NXS_SIGNAL_ROUTER_MQH__

#define NXS_MAX_SIGNALS 48

// Strategy family classification (gates applied differently per family)
enum ENUM_NXS_FAMILY {
   FAM_TREND = 0,     // ADX_RSI, MACD, EMA_PULLBACK, BREAKOUT_ACC, ICHIMOKU
   FAM_REVERSAL,      // BOLLINGER, RSI_DIV, BJORGUM, BB_SQUEEZE
   FAM_SMC,           // SMC/ICT classics
   FAM_INSTITUTIONAL, // v2.0.7: CISD, PO3, Judas, Reversals, Liquidity Void, etc.
   FAM_OTHER
};

ENUM_NXS_FAMILY NXS_StratFamily(string name){
   if(name == "ADX_RSI" || name == "MACD" || name == "EMA_PULLBACK"
      || name == "BREAKOUT_ACC" || name == "ICHIMOKU" || name == "LONDON_BO"
      || name == "SAR" || name == "TSI")
      return FAM_TREND;
   if(name == "BOLLINGER" || name == "RSI_DIV" || name == "BJORGUM" || name == "BB_SQUEEZE")
      return FAM_REVERSAL;
   if(name == "LIQ_SWEEP" || name == "FVG_CONT" || name == "FVG_MIT" || name == "IFVG"
      || name == "OB_MIT" || name == "ORDER_BLOCK" || name == "STRUCT_REACT"
      || name == "TURTLE_SOUP" || name == "SH_BMS_RTO" || name == "SMS_BMS_RTO"
      || name == "SILVER_BULLET" || name == "AMD_REVERSAL" || name == "OTE_CONT"
      || name == "MALAYSIAN_SNR")
      return FAM_SMC;
   if(name == "CISD" || name == "AMD_CONT" || name == "JUDAS_SWING"
      || name == "LDN_REVERSAL" || name == "NY_REVERSAL" || name == "WEEKLY_EXP"
      || name == "PO3" || name == "LIQ_VOID" || name == "DISP_REBAL"
      || name == "RANGE_FADE")
      return FAM_INSTITUTIONAL;
   return FAM_OTHER;
}

// RANGE_FADE is engineered for low-volatility / NEUTRAL velocity / ranging regimes.
// We exempt it from the Velocity-neutral block so the EA can fade the range
// exactly when Velocity is flat (which is the design intent).
bool NXS_IsVelocityExemptStrategy(string name){
   if(name == "RANGE_FADE") return true;
   return false;
}

// MTF mixed handler: returns score multiplier (1.0 pass, <1 penalty, 0 block)
double NXS_MTF_FamilyFactor(int direction, string stratName, string &reason){
   if(!InpUseMTFValidation){ reason = "MTF:OFF"; return 1.0; }
   int b = NXS_MTF_Bias();
   if(b == direction){ reason = "MTF:PASS"; return 1.0; }

   ENUM_NXS_FAMILY fam = NXS_StratFamily(stratName);
   if(b != 0){
      // AUDITPATCH: Counter-HTF Soft is limited to price-action families and a
      // same-direction high-quality reaction. Before this patch all related
      // inputs were definition-only and could never unlock a trade.
      bool softCounter = InpEnableCounterHTFSoft &&
                         (fam == FAM_REVERSAL || fam == FAM_SMC || fam == FAM_INSTITUTIONAL) &&
                         g_reaction.detected && g_reaction.direction == direction &&
                         g_reaction.quality >= InpCounterHTF_MinReactQ;
      if(softCounter){ reason = "MTF:COUNTER-SOFT"; return 0.85; }

      if(InpGateMode >= 3){ reason = "MTF:COUNTER-DEBUG"; return 0.80; }
      if(InpGateMode == 2 &&
         (fam == FAM_REVERSAL || fam == FAM_SMC || fam == FAM_INSTITUTIONAL)){
         reason = "MTF:COUNTER-DISCOVERY";
         return 0.82;
      }
      reason = "MTF:COUNTER";
      return 0.0;
   }

   // b == 0 → mixed
   if(InpGateMode >= 2 || InpMTFMixedMode == 2){
      reason = "MTF:MIXED-ALLOW";
      return 1.0;
   }
   if(InpMTFMixedMode == 1){
      reason = "MTF:MIXED-PEN";
      return (fam == FAM_TREND) ? 0.75 : 0.90;
   }
   if(InpAllowReversalAgainstMTFOnSweep && (fam == FAM_SMC || fam == FAM_INSTITUTIONAL)){
      reason = "MTF:MIXED-SMC-ALLOW";
      return 0.95;
   }
   reason = "MTF:MIXED-BLOCK";
   return 0.0;
}

// Velocity neutral handler (family-aware)
double NXS_Vel_FamilyFactor(ENUM_NXS_DIR dir, SNXSVel &vel, string stratName, string &reason){
   if(!g_run_UseVelocityGate){ reason = "VEL:OFF"; return 1.0; }
   if(NXS_IsVelocityExemptStrategy(stratName)){ reason = "VEL:EXEMPT"; return 1.0; }

   if(vel.state == VEL_NEUTRAL){
      if(InpGateMode >= 2 || InpVelocityNeutralMode == 2){
         reason = "VEL:NEU-ALLOW";
         return 1.0;
      }
      ENUM_NXS_FAMILY fam = NXS_StratFamily(stratName);
      if(InpVelocityNeutralMode == 1){
         reason = "VEL:NEU-PEN";
         return (fam == FAM_TREND) ? 0.80 : 0.95;
      }
      reason = "VEL:NEU-BLOCK";
      return (fam == FAM_SMC || fam == FAM_INSTITUTIONAL) ? 0.90 : 0.0;
   }

   bool opposite = (dir == DIR_BUY && (vel.state == VEL_BEAR || vel.state == VEL_BEAR_PB)) ||
                   (dir == DIR_SELL && (vel.state == VEL_BULL || vel.state == VEL_BULL_PB));
   if(opposite){
      if(InpGateMode >= 3){ reason = "VEL:COUNTER-DEBUG"; return 0.75; }
      reason = "VEL:COUNTER";
      return 0.0;
   }
   reason = "VEL:ALIGN";
   return 1.0;
}

// In-place insertion sort by score DESC
void NXS_SignalSort(SNXSSignal &arr[], int n){
   for(int i = 1; i < n; i++){
      SNXSSignal cur = arr[i];
      int j = i - 1;
      while(j >= 0 && arr[j].score < cur.score){
         arr[j + 1] = arr[j];
         j--;
      }
      arr[j + 1] = cur;
   }
}

#endif
