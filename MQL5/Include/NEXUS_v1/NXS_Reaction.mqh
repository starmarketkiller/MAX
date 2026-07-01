//+------------------------------------------------------------------+
//|  NXS_Reaction.mqh - Price Reaction Engine on structure levels     |
//+------------------------------------------------------------------+
#ifndef __NXS_REACTION_MQH__
#define __NXS_REACTION_MQH__

struct SNXSReaction {
   bool   detected;
   int    direction;      // +1 bullish, -1 bearish
   double levelPrice;
   string levelType;      // "OB_BULL" | "OB_BEAR" | "FVG_BULL" | "FVG_BEAR" | "SWING_HIGH" | "SWING_LOW"
   double quality;        // 0-100
   string summary;
};

SNXSReaction g_reaction;

bool NXS_HasPriceReaction(string sym, ENUM_TIMEFRAMES tf, int dir){
   double o = iOpen (sym, tf, 1);
   double c = iClose(sym, tf, 1);
   double h = iHigh (sym, tf, 1);
   double l = iLow  (sym, tf, 1);
   double body  = MathAbs(c - o);
   double range = MathMax(h - l, _Point);
   double upWick= h - MathMax(o, c);
   double dnWick= MathMin(o, c) - l;

   if(dir > 0){
      bool pin   = (dnWick > body * 1.5) && (dnWick > range * 0.5);
      bool close = (c > o);
      return (pin || close);
   } else if(dir < 0){
      bool pin   = (upWick > body * 1.5) && (upWick > range * 0.5);
      bool close = (c < o);
      return (pin || close);
   }
   return false;
}

SNXSReaction NXS_DetectReaction(string sym, ENUM_TIMEFRAMES tf){
   SNXSReaction r;
   r.detected = false; r.direction = 0; r.levelPrice = 0;
   r.levelType = ""; r.quality = 0; r.summary = "";
   if(!InpUseReaction) return r;

   double price = SymbolInfoDouble(sym, SYMBOL_BID);
   if(price <= 0 || g_atr <= 0) return r;
   double tol = g_atr * InpReactionTol;
   double bestQuality = 0;

   // 1. Scan OB / FVG zones
   for(int i = 0; i < g_levelCount; i++){
      if(!g_levels[i].active) continue;
      SNXSLevel lv = g_levels[i];
      ENUM_NXS_LEVEL_TYPE t = lv.type;
      bool isZone = (t == NXS_LVL_OB_BULL || t == NXS_LVL_OB_BEAR ||
                     t == NXS_LVL_FVG_BULL || t == NXS_LVL_FVG_BEAR);
      if(!isZone) continue;
      bool inZone = (price <= lv.priceTop + tol && price >= lv.priceBot - tol);
      if(!inZone) continue;

      int expectedDir = 0; string typeName = "";
      switch(t){
         case NXS_LVL_OB_BULL:  expectedDir =  1; typeName = "OB_BULL";  break;
         case NXS_LVL_OB_BEAR:  expectedDir = -1; typeName = "OB_BEAR";  break;
         case NXS_LVL_FVG_BULL: expectedDir =  1; typeName = "FVG_BULL"; break;
         case NXS_LVL_FVG_BEAR: expectedDir = -1; typeName = "FVG_BEAR"; break;
         default: continue;
      }

      if(!NXS_HasPriceReaction(sym, tf, expectedDir)) continue;
      double q = 60;
      if(expectedDir == g_struct.trend) q += 20;
      if(!lv.mitigated)                 q += 15;
      if(q > bestQuality){
         bestQuality   = q;
         r.detected    = true;
         r.direction   = expectedDir;
         r.levelPrice  = lv.priceRef;
         r.levelType   = typeName;
         r.quality     = q;
      }
   }

   // 2. Scan Swing levels
   double tolSwing = g_atr * InpReactionTol;
   if(g_struct.lastSwingLow > 0 && MathAbs(price - g_struct.lastSwingLow) < tolSwing){
      if(NXS_HasPriceReaction(sym, tf, 1)){
         double q = 55 + (g_struct.trend == 1 ? 20 : 0);
         if(q > bestQuality){
            bestQuality   = q;
            r.detected    = true;
            r.direction   = 1;
            r.levelPrice  = g_struct.lastSwingLow;
            r.levelType   = "SWING_LOW";
            r.quality     = q;
         }
      }
   }
   if(g_struct.lastSwingHigh > 0 && MathAbs(price - g_struct.lastSwingHigh) < tolSwing){
      if(NXS_HasPriceReaction(sym, tf, -1)){
         double q = 55 + (g_struct.trend == -1 ? 20 : 0);
         if(q > bestQuality){
            bestQuality   = q;
            r.detected    = true;
            r.direction   = -1;
            r.levelPrice  = g_struct.lastSwingHigh;
            r.levelType   = "SWING_HIGH";
            r.quality     = q;
         }
      }
   }

   // 3. Livello dinamico: EMA200 (mean-reversion sulle medie lente).
   // Confluenza NON sostitutiva: se una reazione esiste già ed è vicina alla
   // EMA200 nella stessa direzione, ne alza la qualità; altrimenti può
   // generarla da sola (qualità base più bassa delle zone OB/FVG).
   if(InpUseReactionEMA && g_ema200 > 0){
      double emaTol = g_atr * InpReactEMATolATR;
      bool nearEMA = (MathAbs(price - g_ema200) <= emaTol);
      if(nearEMA){
         if(r.detected && MathAbs(r.levelPrice - g_ema200) <= emaTol * 2.0){
            // confluenza col livello già rilevato
            r.quality = MathMin(100.0, r.quality + InpReactEMABonus);
            r.levelType = r.levelType + "+EMA";
         } else if(!r.detected){
            // reazione dinamica autonoma sulla EMA200
            int emaDir = 0;
            if(NXS_HasPriceReaction(sym, tf, 1))      emaDir = 1;   // rimbalzo rialzista (supporto)
            else if(NXS_HasPriceReaction(sym, tf, -1)) emaDir = -1;  // rigetto ribassista (resistenza)
            if(emaDir != 0){
               double q = 58.0 + (emaDir == g_struct.trend ? 15.0 : 0.0);
               r.detected   = true;
               r.direction  = emaDir;
               r.levelPrice = g_ema200;
               r.levelType  = "EMA200";
               r.quality    = q;
            }
         }
      }
   }

   if(r.detected){
      r.summary = StringFormat("Reaction %s @ %.2f type=%s Q=%.0f",
                               (r.direction == 1 ? "BULL" : "BEAR"),
                               r.levelPrice, r.levelType, r.quality);
      if(InpDebugLog) Print("[REACTION] ", r.summary);
   }
   return r;
}

double NXS_ReactionScoreMod(int dir){
   if(!InpUseReaction || !g_reaction.detected) return 0;
   if(g_reaction.direction == dir)             return g_reaction.quality * 0.4;
   if(g_reaction.direction != 0)               return -20;
   return 0;
}

#endif
