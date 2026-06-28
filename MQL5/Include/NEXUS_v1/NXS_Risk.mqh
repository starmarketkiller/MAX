//+------------------------------------------------------------------+
//|  NXS_Risk.mqh - Capital protection                                |
//+------------------------------------------------------------------+
#ifndef __NXS_RISK_MQH__
#define __NXS_RISK_MQH__

double NXS_AntiBleedMultiplier(){
   if(!InpUseAntiBleed) return 1.0;
   double m = 1.0;
   // 1) consecutive-loss scaling
   if(g_consecLosses == 1)      m *= InpAB_RiskMult_1L;
   else if(g_consecLosses == 2) m *= InpAB_RiskMult_2L;
   else if(g_consecLosses >= 3) m *= InpAB_RiskMult_3L;
   // 2) drawdown-based scaling
   if(g_balanceDayStart > 0){
      double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      double ddPct = (g_balanceDayStart - eq) / g_balanceDayStart * 100.0;
      if(ddPct >= InpAB_DD_Hard)      m *= InpAB_RiskMult_DDHard;
      else if(ddPct >= InpAB_DD_Soft) m *= InpAB_RiskMult_DDSoft;
   }
   return m;
}

double NXS_DynamicScoreThreshold(double base){
   if(!InpUseAntiBleed) return base;
   if(g_balanceDayStart > 0){
      double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      double ddPct = (g_balanceDayStart - eq) / g_balanceDayStart * 100.0;
      if(ddPct >= InpAB_DD_Hard) return base + InpAB_ScoreBonus_DDHard;
   }
   return base;
}

double NXS_CalcLot(double slPriceDist){
   double risk = AccountInfoDouble(ACCOUNT_BALANCE) * g_run_RiskPercent / 100.0;
   risk *= NXS_AntiBleedMultiplier();   // P2 anti-bleed scaling
   double tickVal  = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_SIZE);
   if(tickVal <= 0 || tickSize <= 0 || slPriceDist <= 0) return 0.01;
   // v2.0.2b — explicit robust formula (audit-friendly):
   //   lots = risk_money / (ticks_in_SL * value_per_tick)
   double ticksInSL = slPriceDist / tickSize;
   if(ticksInSL <= 0) return 0.01;
   double lots = risk / (ticksInSL * tickVal);
   double minLot = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
   double maxLot = MathMin(g_run_MaxLot, SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MAX));
   double step   = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
   if(step <= 0) step = 0.01;
   lots = MathMax(minLot, MathMin(maxLot, lots));
   lots = MathFloor(lots / step) * step;
   return NormalizeDouble(lots, 2);
}

bool NXS_CheckProtections(string &reason){
   // P2: skip queue from anti-bleed
   if(g_skipNextSignals > 0){
      g_skipNextSignals--;
      reason = "anti_bleed_skip"; return false;
   }
   // Anti-revenge cooldown
   if(InpAntiRevenge && g_antiRevengeUntil > 0 && TimeCurrent() < g_antiRevengeUntil){
      reason = "anti_revenge"; return false;
   }
   // Margin level
   double ml = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   if(ml > 0 && ml < (double)InpMinMarginLevel){
      reason = "margin_low"; return false;
   }
   // Daily DD
   if(g_balanceDayStart > 0){
      double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      double ddPct = (g_balanceDayStart - eq) / g_balanceDayStart * 100.0;
      if(ddPct >= g_run_MaxDailyDDPct){ reason = "daily_dd"; return false; }
   }
   if(g_tradesToday >= g_run_MaxTradesPerDay){ reason = "max_trades"; return false; }
   if(NXS_CountPositions() >= g_run_MaxConcurrent){ reason = "max_concurrent"; return false; }
   if(g_eaPaused){ reason = "ea_paused"; return false; }
   return true;
}

void NXS_OnTradeClosed(double pnl){
   if(pnl < 0){
      g_consecLosses++;
      if(InpAntiRevenge && g_consecLosses >= InpAntiRevengeLosses){
         g_antiRevengeUntil = TimeCurrent() + InpAntiRevengeMin * 60;
         g_consecLosses = 0;
         PrintFormat("[NEXUS] Anti-revenge engaged until %s",
                     TimeToString(g_antiRevengeUntil, TIME_DATE|TIME_MINUTES));
      }
      // P2: after 3rd consecutive loss, skip next N signals
      if(InpUseAntiBleed && g_consecLosses == 3 && InpAB_SkipAfter3L > 0){
         g_skipNextSignals = InpAB_SkipAfter3L;
         PrintFormat("[NEXUS] Anti-bleed: skipping next %d signals", g_skipNextSignals);
      }
   } else {
      // Reset losses streak only after 2 consecutive wins (anti-bleed wisdom)
      if(g_consecLosses > 0) g_consecLosses = MathMax(0, g_consecLosses - 1);
   }
}

void NXS_DailyRollover(){
   MqlDateTime mt; TimeToStruct(TimeCurrent(), mt);
   mt.hour = 0; mt.min = 0; mt.sec = 0;
   datetime today = StructToTime(mt);
   if(today != g_dayStart){
      g_dayStart = today;
      g_tradesToday = 0;
      g_balanceDayStart = AccountInfoDouble(ACCOUNT_BALANCE);
   }
}

#endif
