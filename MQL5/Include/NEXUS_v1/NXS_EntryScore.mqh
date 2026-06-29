//+------------------------------------------------------------------+
//|  NXS_EntryScore.mqh - Final score with modifiers                  |
//+------------------------------------------------------------------+
#ifndef __NXS_ENTRYSCORE_MQH__
#define __NXS_ENTRYSCORE_MQH__

// v2.0.14 — pavimento score per-strategia (anti over-trading).
// Definita qui (incluso prima di NXS_Execution) per garantire l'ordine di compilazione.
double NXS_StrategyMinScoreFloor(string stratName){
   if(stratName == "MALAYSIAN_SNR") return InpMalaysianMinScore;
   return 0.0;
}

double NXS_FinalScore(SNXSSignal &sig, SNXSAMD &amd, SNXSSweep &sw){
   if(sig.dir == DIR_NONE) return 0;
   double score = sig.score;

   // AMD modifier
   if(InpUseAMD && amd.expectedDir != DIR_NONE){
      if(amd.expectedDir == sig.dir) score += amd.modifier;
      else                           score -= amd.modifier * 0.5;
   }
   // BSP modifier
   score += NXS_BSPModifier(sig.dir);

   // Liquidity sweep alignment bonus
   if(sw.confirmed && sw.dir == sig.dir) score += 6;

   // PDH/PDL proximity (allows reversal with bonus)
   double pdH = iHigh(g_sym, PERIOD_D1, 1);
   double pdL = iLow (g_sym, PERIOD_D1, 1);
   double now = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double prox = MathMax(g_atr * 0.6, 1.0);
   if(sig.dir == DIR_BUY  && MathAbs(now - pdL) <= prox) score += 4;
   if(sig.dir == DIR_SELL && MathAbs(now - pdH) <= prox) score += 4;

   // Regime modifier
   if(g_regime == REGIME_STRONG_TREND) score += 4;
   if(g_regime == REGIME_CHOPPY)       score -= 6;
   if(g_regime == REGIME_VOLATILE)     score -= 3;

   // Reaction Engine modifier (Structure addendum)
   int sigDirInt = (sig.dir == DIR_BUY) ? 1 : (sig.dir == DIR_SELL ? -1 : 0);
   score += NXS_ReactionScoreMod(sigDirInt);

   // v2.0.9 P3 #24 — Candle confirmation booster (+5 score if pin bar or engulfing)
   double o1 = iOpen (g_sym, InpTFEntry, 1);
   double h1 = iHigh (g_sym, InpTFEntry, 1);
   double l1 = iLow  (g_sym, InpTFEntry, 1);
   double c1 = iClose(g_sym, InpTFEntry, 1);
   double range1 = h1 - l1;
   if(range1 > 0 && g_atr > 0){
      double body1 = MathAbs(c1 - o1);
      double upperWick = h1 - MathMax(o1, c1);
      double lowerWick = MathMin(o1, c1) - l1;
      // Pin bar bullish: tail >= 2x body, close in upper third
      bool pinBull = (sig.dir == DIR_BUY) &&
                     (lowerWick >= 2.0 * body1) && (c1 > l1 + 0.66 * range1);
      // Pin bar bearish: head >= 2x body, close in lower third
      bool pinBear = (sig.dir == DIR_SELL) &&
                     (upperWick >= 2.0 * body1) && (c1 < l1 + 0.34 * range1);
      // Engulfing bullish: previous bearish + current bullish body engulfs
      double o2 = iOpen (g_sym, InpTFEntry, 2);
      double c2 = iClose(g_sym, InpTFEntry, 2);
      bool engBull = (sig.dir == DIR_BUY) && (c2 < o2) && (c1 > o1) &&
                     (c1 >= o2) && (o1 <= c2) && (body1 > MathAbs(c2 - o2));
      bool engBear = (sig.dir == DIR_SELL) && (c2 > o2) && (c1 < o1) &&
                     (c1 <= o2) && (o1 >= c2) && (body1 > MathAbs(c2 - o2));
      if(pinBull || pinBear || engBull || engBear) score += 5;
   }

   if(score < 0)   score = 0;
   if(score > 100) score = 100;
   return score;
}

#endif
