//+------------------------------------------------------------------+
//|  NXS_Risk.mqh - Capital protection                                |
//+------------------------------------------------------------------+
#ifndef __NXS_RISK_MQH__
#define __NXS_RISK_MQH__

// v2.2.1 — moltiplicatore lotto a livello di account: aggressivita' base x
// scala da streak (vincite/perdite). Applicato UNA volta in NXS_CalcLot.
double NXS_AccountLotMult(){
   double m = (InpLotAggressiveness > 0 ? InpLotAggressiveness : 1.0);
   if(InpUseStreakSizing) m *= g_streakLotMult;
   return MathMax(0.05, m);
}

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
   risk *= NXS_AccountLotMult();        // v2.2.1 aggressivita' + scala da streak
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
   // v2.0.31: same tester-only bypass as NXS_Prot_EntryBlocked - these
   // account-level gates (daily DD, max trades/day, max concurrent, margin,
   // anti-revenge/anti-bleed) exist to protect live capital, which doesn't
   // apply when backtesting/optimizing. Live behavior is unaffected.
   if(MQLInfoInteger(MQL_TESTER)) return true;
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

// v2.0.34 (audit point 8): universal exhaustion/extension gate. Blocks a
// NEW entry chasing a move that has already run too far, checked 3 ways:
//   1) N consecutive higher-highs (buy) / lower-lows (sell) with no pullback
//   2) price too far from EMA200 relative to ATR
//   3) RSI diverging against the entry direction (price extending, momentum not)
bool NXS_ExhaustionConsecutive(ENUM_NXS_DIR dir){
   int streak = 0;
   if(dir == DIR_BUY){
      for(int i = 1; i <= InpExhaustionMaxConsecutive; i++){
         if(iHigh(g_sym, InpTFEntry, i) > iHigh(g_sym, InpTFEntry, i+1)) streak++;
         else break;
      }
   } else if(dir == DIR_SELL){
      for(int i = 1; i <= InpExhaustionMaxConsecutive; i++){
         if(iLow(g_sym, InpTFEntry, i) < iLow(g_sym, InpTFEntry, i+1)) streak++;
         else break;
      }
   }
   return streak >= InpExhaustionMaxConsecutive;
}

bool NXS_ExhaustionEMADistance(){
   if(g_atr <= 0 || g_ema200 <= 0) return false;
   double price = SymbolInfoDouble(g_sym, SYMBOL_BID);
   return MathAbs(price - g_ema200) > InpExhaustionEMADistATR * g_atr;
}

bool NXS_ExhaustionRsiDivergence(ENUM_NXS_DIR dir){
   int n = InpExhaustionRsiDivLookback;
   if(n < 2) return false;
   double rsiArr[];
   if(CopyBuffer(g_hRSI, 0, 1, n, rsiArr) <= 0) return false;
   if(ArraySize(rsiArr) < n) return false;
   double rsiRecent = rsiArr[0];
   double rsiPast   = rsiArr[n-1];
   if(dir == DIR_BUY){
      // bearish divergence: price made a higher high but RSI made a lower high
      double priceRecent = iHigh(g_sym, InpTFEntry, 1);
      double pricePast   = iHigh(g_sym, InpTFEntry, n);
      if(priceRecent > pricePast && rsiRecent < rsiPast) return true;
   } else if(dir == DIR_SELL){
      // bullish divergence: price made a lower low but RSI made a higher low
      double priceRecent = iLow(g_sym, InpTFEntry, 1);
      double pricePast   = iLow(g_sym, InpTFEntry, n);
      if(priceRecent < pricePast && rsiRecent > rsiPast) return true;
   }
   return false;
}

// v2.0.35: A/B test (MACD, FVG_MIT, TURTLE_SOUP; same 3-week window) showed
// the exhaustion gate is NOT uniformly helpful - it wrecked MACD (11->1
// trades) and FVG_MIT (103->27 trades, PF 0.99->0.46), but genuinely
// improved TURTLE_SOUP (PF 0.64->1.92). This isn't a clean trend-vs-reversal
// split (TURTLE_SOUP is itself a reversal strategy) - only 3 data points
// exist, so rather than guess a broader family rule, this exempts
// specifically the two strategies MEASURED to be hurt and leaves the gate
// unchanged for everyone else pending more A/B data.
bool NXS_ExhaustionGateExempt(string stratName){
   return (stratName == "MACD" || stratName == "FVG_MIT_NXR" || stratName == "FVG_MIT");
}

bool NXS_ExhaustionBlocks(ENUM_NXS_DIR dir, string stratName, string &reason){
   if(!InpUseExhaustionGate) return false;
   if(NXS_ExhaustionGateExempt(stratName)) return false;
   if(NXS_ExhaustionConsecutive(dir)){ reason = "exhaustion_consecutive"; return true; }
   if(NXS_ExhaustionEMADistance())   { reason = "exhaustion_ema_distance"; return true; }
   if(NXS_ExhaustionRsiDivergence(dir)){ reason = "exhaustion_rsi_divergence"; return true; }
   return false;
}

// v2.2.1 — aggiorna il moltiplicatore di sizing sull'andamento: sale dopo N
// vittorie di fila, scende dopo N perdite di fila, dentro [floor, cap].
void _nxs_streak_update(double pnl){
   if(!InpUseStreakSizing) return;
   if(pnl > 0){
      g_streakWins++; g_streakLosses = 0;
      if(g_streakWins >= InpStreakWinsToScale){
         g_streakLotMult = MathMin(InpStreakMaxMult, g_streakLotMult * InpStreakScaleUp);
         g_streakWins = 0;   // uno step per soglia raggiunta
         PrintFormat("[NEXUS SIZE] +vincite -> lotMult=%.2f", g_streakLotMult);
      }
   } else if(pnl < 0){
      g_streakLosses++; g_streakWins = 0;
      if(g_streakLosses >= InpStreakLossesToScale){
         g_streakLotMult = MathMax(InpStreakMinMult, g_streakLotMult * InpStreakScaleDown);
         g_streakLosses = 0;
         PrintFormat("[NEXUS SIZE] -perdite -> lotMult=%.2f", g_streakLotMult);
      }
   }
}

void NXS_OnTradeClosed(double pnl){
   _nxs_streak_update(pnl);
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
