//+------------------------------------------------------------------+
//|  NXS_Strategies.mqh - 15 trading strategies (KODEXAI + HYDRA+SMC) |
//+------------------------------------------------------------------+
#ifndef __NXS_STRATEGIES_MQH__
#define __NXS_STRATEGIES_MQH__

void NXS_DefaultSLTP(SNXSSignal &sig){
   double slMult = InpATR_SL_Mult;
   if(InpUseAdaptiveSL && g_atrAvg > 0){
      slMult = (g_atr > g_atrAvg) ? InpSL_HighVol_Mult : InpSL_LowVol_Mult;
   }
   slMult = MathMax(slMult, InpMinSLMult);   // v2.0.14 — floor SL (rumore M5 gold)
   double sl = g_atr * slMult;
   double tp = g_atr * InpATR_TP_Mult;
   if(sig.dir == DIR_BUY){
      sig.entryRef = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      sig.slPrice  = NormPrice(sig.entryRef - sl);
      sig.tpPrice  = NormPrice(sig.entryRef + tp);
   } else if(sig.dir == DIR_SELL){
      sig.entryRef = SymbolInfoDouble(g_sym, SYMBOL_BID);
      sig.slPrice  = NormPrice(sig.entryRef + sl);
      sig.tpPrice  = NormPrice(sig.entryRef - tp);
   }
}

//------------------------------------ K1 ADX + RSI
SNXSSignal NXS_Strat_ADXRSI(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_ADX_RSI; s.stratName = "ADX_RSI";
   if(!InpStrat_ADX_RSI) return s;
   if(g_adx < 22) return s;
   double price = iClose(g_sym, InpTFEntry, 1);
   if(g_adxPlus > g_adxMinus && g_rsi > 50 && price > g_ema200){
      s.dir = DIR_BUY; s.score = 60 + MathMin(g_adx, 50) * 0.4; s.reason = "ADX_bull";
   } else if(g_adxMinus > g_adxPlus && g_rsi < 50 && price < g_ema200){
      s.dir = DIR_SELL; s.score = 60 + MathMin(g_adx, 50) * 0.4; s.reason = "ADX_bear";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K2 Bollinger Mean Reversion
SNXSSignal NXS_Strat_Bollinger(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_BOLLINGER; s.stratName = "BOLLINGER";
   if(!InpStrat_BOLLINGER) return s;
   double close = iClose(g_sym, InpTFEntry, 1);
   double low   = iLow  (g_sym, InpTFEntry, 1);
   double high  = iHigh (g_sym, InpTFEntry, 1);
   if(low <= g_bbLower && close > g_bbLower && g_rsi < 35){
      s.dir = DIR_BUY;  s.score = 62; s.reason = "BB_lower_rejection";
   } else if(high >= g_bbUpper && close < g_bbUpper && g_rsi > 65){
      s.dir = DIR_SELL; s.score = 62; s.reason = "BB_upper_rejection";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K3 MACD Trend
SNXSSignal NXS_Strat_MACD(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_MACD; s.stratName = "MACD";
   if(!InpStrat_MACD) return s;
   double price = iClose(g_sym, InpTFEntry, 1);
   if(g_macd > g_macdSig && g_macd > 0 && price > g_ema200){
      s.dir = DIR_BUY;  s.score = 65; s.reason = "MACD_bull_above_ema200";
   } else if(g_macd < g_macdSig && g_macd < 0 && price < g_ema200){
      s.dir = DIR_SELL; s.score = 65; s.reason = "MACD_bear_below_ema200";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K4 Parabolic SAR
SNXSSignal NXS_Strat_SAR(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_SAR; s.stratName = "SAR";
   if(!InpStrat_SAR) return s;
   double price = iClose(g_sym, InpTFEntry, 1);
   if(g_sar < price && g_ema9 > g_ema21){
      s.dir = DIR_BUY;  s.score = 60; s.reason = "SAR_below_price";
   } else if(g_sar > price && g_ema9 < g_ema21){
      s.dir = DIR_SELL; s.score = 60; s.reason = "SAR_above_price";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K5 TSI Momentum (simplified RSI/EMA proxy)
SNXSSignal NXS_Strat_TSI(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_TSI; s.stratName = "TSI";
   if(!InpStrat_TSI) return s;
   double price = iClose(g_sym, InpTFEntry, 1);
   if(g_rsi > 55 && g_ema9 > g_ema21 && price > g_ema21){
      s.dir = DIR_BUY;  s.score = 66; s.reason = "TSI_bull";   // v2.0.9 +8
   } else if(g_rsi < 45 && g_ema9 < g_ema21 && price < g_ema21){
      s.dir = DIR_SELL; s.score = 66; s.reason = "TSI_bear";   // v2.0.9 +8
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ K6 Bjorgum Key Levels
SNXSSignal NXS_Strat_Bjorgum(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_BJORGUM; s.stratName = "BJORGUM";
   if(!InpStrat_BJORGUM) return s;
   int hh = iHighest(g_sym, InpTFEntry, MODE_HIGH, 30, 2);
   int ll = iLowest (g_sym, InpTFEntry, MODE_LOW,  30, 2);
   double pivHi = iHigh(g_sym, InpTFEntry, hh);
   double pivLo = iLow (g_sym, InpTFEntry, ll);
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double dist = g_atr * 0.5;
   if(MathAbs(c1 - pivLo) <= dist && c1 > pivLo){
      s.dir = DIR_BUY;  s.score = 68; s.reason = "Bjorgum_bounce_low";    // v2.0.9 +4
   } else if(MathAbs(c1 - pivHi) <= dist && c1 < pivHi){
      s.dir = DIR_SELL; s.score = 68; s.reason = "Bjorgum_reject_high";   // v2.0.9 +4
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H1 Liquidity Sweep / Manipulation Reversal
SNXSSignal NXS_Strat_LiqSweep(SNXSSweep &sw){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_LIQ_SWEEP; s.stratName = "LIQ_SWEEP";
   if(!InpStrat_LIQ_SWEEP) return s;
   if(!sw.confirmed) return s;
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double o1 = iOpen (g_sym, InpTFEntry, 1);
   if(sw.dir == DIR_BUY && c1 > o1){
      s.dir = DIR_BUY;  s.score = 72; s.reason = "Sweep_low_reversal";
   } else if(sw.dir == DIR_SELL && c1 < o1){
      s.dir = DIR_SELL; s.score = 72; s.reason = "Sweep_high_reversal";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H2 Displacement FVG Continuation
SNXSSignal NXS_Strat_FVG(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_FVG_CONT; s.stratName = "FVG_CONT";
   if(!InpStrat_FVG_CONT) return s;
   double h3 = iHigh(g_sym, InpTFEntry, 3);
   double l3 = iLow (g_sym, InpTFEntry, 3);
   double h1 = iHigh(g_sym, InpTFEntry, 1);
   double l1 = iLow (g_sym, InpTFEntry, 1);
   double c2 = iClose(g_sym, InpTFEntry, 2);
   double o2 = iOpen (g_sym, InpTFEntry, 2);
   double body2 = MathAbs(c2 - o2);
   if(body2 < g_atr) return s;
   if(l1 > h3 && c2 > o2){
      s.dir = DIR_BUY;  s.score = 70; s.reason = "FVG_bull_continuation";
   } else if(h1 < l3 && c2 < o2){
      s.dir = DIR_SELL; s.score = 70; s.reason = "FVG_bear_continuation";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H3 Breakout Acceptance
SNXSSignal NXS_Strat_BreakoutAcc(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_BREAKOUT_ACC; s.stratName = "BREAKOUT_ACC";
   if(!InpStrat_BREAKOUT_ACC) return s;
   int n = 20;
   double range_hi = iHigh(g_sym, InpTFEntry, iHighest(g_sym, InpTFEntry, MODE_HIGH, n, 3));
   double range_lo = iLow (g_sym, InpTFEntry, iLowest (g_sym, InpTFEntry, MODE_LOW,  n, 3));
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double c2 = iClose(g_sym, InpTFEntry, 2);
   if(c1 > range_hi && c2 > range_hi){
      s.dir = DIR_BUY;  s.score = 68; s.reason = "Acceptance_above_range";
   } else if(c1 < range_lo && c2 < range_lo){
      s.dir = DIR_SELL; s.score = 68; s.reason = "Acceptance_below_range";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H4 London Breakout
SNXSSignal NXS_Strat_LondonBO(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_LONDON_BO; s.stratName = "LONDON_BO";
   if(!InpStrat_LONDON_BO) return s;
   if(g_session != SESS_LONDON) return s;
   // use Asian range
   SNXSAMD amd = NXS_GetAMD();
   if(amd.asianHigh <= 0) return s;
   double c1 = iClose(g_sym, InpTFEntry, 1);
   if(c1 > amd.asianHigh){
      s.dir = DIR_BUY;  s.score = 70; s.reason = "London_BO_above_asia";
   } else if(c1 < amd.asianLow){
      s.dir = DIR_SELL; s.score = 70; s.reason = "London_BO_below_asia";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H5 EMA Pullback
SNXSSignal NXS_Strat_EMAPullback(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_EMA_PULLBACK; s.stratName = "EMA_PULLBACK";
   if(!InpStrat_EMA_PULLBACK) return s;
   double price = iClose(g_sym, InpTFEntry, 1);
   double low   = iLow  (g_sym, InpTFEntry, 1);
   double high  = iHigh (g_sym, InpTFEntry, 1);
   if(g_ema9 > g_ema21 && low <= g_ema21 && price > g_ema21 && g_rsi > 45){
      s.dir = DIR_BUY;  s.score = 66; s.reason = "EMA_PB_bull";
   } else if(g_ema9 < g_ema21 && high >= g_ema21 && price < g_ema21 && g_rsi < 55){
      s.dir = DIR_SELL; s.score = 66; s.reason = "EMA_PB_bear";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H6 BB Squeeze Breakout
SNXSSignal NXS_Strat_BBSqueeze(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_BB_SQUEEZE; s.stratName = "BB_SQUEEZE";
   if(!InpStrat_BB_SQUEEZE) return s;
   double width = g_bbUpper - g_bbLower;
   if(width <= 0 || g_atr <= 0) return s;
   if(width > g_atr * 2.5) return s; // not a squeeze
   double c1 = iClose(g_sym, InpTFEntry, 1);
   if(c1 > g_bbUpper){
      s.dir = DIR_BUY;  s.score = 70; s.reason = "Squeeze_breakout_up";
   } else if(c1 < g_bbLower){
      s.dir = DIR_SELL; s.score = 70; s.reason = "Squeeze_breakout_down";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H7 Ichimoku Kumo Break
SNXSSignal NXS_Strat_Ichimoku(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_ICHIMOKU; s.stratName = "ICHIMOKU";
   if(!InpStrat_ICHIMOKU) return s;
   double price = iClose(g_sym, InpTFEntry, 1);
   double kumoTop = MathMax(g_ichiSpanA, g_ichiSpanB);
   double kumoBot = MathMin(g_ichiSpanA, g_ichiSpanB);
   if(kumoTop <= 0 || kumoBot <= 0) return s;
   double prev = iClose(g_sym, InpTFEntry, 2);
   if(prev <= kumoTop && price > kumoTop && g_ichiTenkan > g_ichiKijun){
      s.dir = DIR_BUY;  s.score = 65; s.reason = "Kumo_break_up";
   } else if(prev >= kumoBot && price < kumoBot && g_ichiTenkan < g_ichiKijun){
      s.dir = DIR_SELL; s.score = 65; s.reason = "Kumo_break_down";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ H8 RSI Divergence
SNXSSignal NXS_Strat_RSIDiv(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_RSI_DIV; s.stratName = "RSI_DIV";
   if(!InpStrat_RSI_DIV) return s;
   double rsiArr[]; ArraySetAsSeries(rsiArr, true);
   if(CopyBuffer(g_hRSI, 0, 1, 15, rsiArr) <= 0) return s;
   double l1 = iLow(g_sym, InpTFEntry, 1);
   double l8 = iLow(g_sym, InpTFEntry, 8);
   double h1 = iHigh(g_sym, InpTFEntry, 1);
   double h8 = iHigh(g_sym, InpTFEntry, 8);
   // bullish divergence: lower low in price, higher low in RSI
   if(l1 < l8 && rsiArr[0] > rsiArr[7] && rsiArr[0] < 40){
      s.dir = DIR_BUY;  s.score = 68; s.reason = "RSI_bull_div";
   } else if(h1 > h8 && rsiArr[0] < rsiArr[7] && rsiArr[0] > 60){
      s.dir = DIR_SELL; s.score = 68; s.reason = "RSI_bear_div";
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ S1 Order Block Retest
SNXSSignal NXS_Strat_OrderBlock(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_ORDER_BLOCK; s.stratName = "ORDER_BLOCK";
   if(!InpStrat_ORDER_BLOCK) return s;
   // Look for last bullish/bearish impulse 5–10 bars ago and a retest
   for(int i = 5; i <= 12; i++){
      double o = iOpen (g_sym, InpTFEntry, i);
      double c = iClose(g_sym, InpTFEntry, i);
      double body = MathAbs(c - o);
      if(body < g_atr) continue;
      double obTop = MathMax(o, c);
      double obBot = MathMin(o, c);
      double c1 = iClose(g_sym, InpTFEntry, 1);
      double l1 = iLow  (g_sym, InpTFEntry, 1);
      double h1 = iHigh (g_sym, InpTFEntry, 1);
      // bullish OB: impulse up, retest down to OB body
      if(c > o && l1 <= obTop && c1 > obBot){
         s.dir = DIR_BUY;  s.score = 70; s.reason = "OB_retest_bull"; break;
      }
      if(c < o && h1 >= obBot && c1 < obTop){
         s.dir = DIR_SELL; s.score = 70; s.reason = "OB_retest_bear"; break;
      }
   }
   if(s.dir != DIR_NONE) NXS_DefaultSLTP(s);
   return s;
}

//------------------------------------ S2 Structure Reaction (addendum)
SNXSSignal NXS_Strat_StructureReaction(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_STRUCT_REACT; s.stratName = "STRUCT_REACT";
   if(!InpUseStructReact) return s;
   if(!g_reaction.detected) return s;

   double base = 55;
   double q = g_reaction.quality;
   double score = base + q * 0.35;  // 55 .. ~90

   // Bonus when reaction aligned with structure trend
   if(g_reaction.direction == g_struct.trend) score += 6;
   // BOS/CHOCH confirmation
   if(g_reaction.direction == 1 && (g_struct.bosUp   || g_struct.chochUp))   score += 5;
   if(g_reaction.direction ==-1 && (g_struct.bosDown || g_struct.chochDown)) score += 5;
   if(score > 95) score = 95;

   s.dir   = (g_reaction.direction == 1) ? DIR_BUY : DIR_SELL;
   s.score = score;
   s.reason= "StructReact_" + g_reaction.levelType;
   NXS_DefaultSLTP(s);
   return s;
}

#endif
