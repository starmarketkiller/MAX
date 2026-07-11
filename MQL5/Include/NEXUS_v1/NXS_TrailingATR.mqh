//+------------------------------------------------------------------+
//|  NXS_TrailingATR.mqh - Dynamic ATR-based trailing stop            |
//|  Replaces simple step trailing with: SL = price - k*ATR(now)      |
//+------------------------------------------------------------------+
#ifndef __NXS_TRAILING_ATR_MQH__
#define __NXS_TRAILING_ATR_MQH__

void NXS_TrailATR(){
   if(!InpUseAtrTrail) return;
   if(g_atr <= 0) return;
   double kGlobal = InpAtrTrailMult;
   if(kGlobal <= 0) kGlobal = 1.5;
   double act = (InpAtrTrailActivateATR > 0) ? InpAtrTrailActivateATR : 0.5; // v2.4.4: soglia d'attivazione tunabile

   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsNexusMagic(mg)) continue;
      long ptype = PositionGetInteger(POSITION_TYPE);
      double open  = PositionGetDouble(POSITION_PRICE_OPEN);
      double curSL = PositionGetDouble(POSITION_SL);
      double curTP = PositionGetDouble(POSITION_TP);

      // v2.4.5 — larghezza trail PER-STRATEGIA (dal commento: prefix|strat|score).
      // Le trend/continuazione corrono (2.5), le mean-reversion prendono profitto
      // presto (1.5). Fallback al globale se la strategia non ha un valore.
      double k    = kGlobal;
      double actK = act;   // soglia d'attivazione globale (v2.4.7: attivazione
                           // per-strategia rimossa - in v2.4.6 dava netto piu' basso)
      if(InpUseStrategyProfiles){
         string cm = PositionGetString(POSITION_COMMENT);
         string pp[]; int npp = StringSplit(cm, '|', pp);
         if(npp >= 2 && StringLen(pp[1]) > 0){
            double pk = NXS_Profile_TrailK(pp[1]);
            if(pk > 0) k = pk;   // solo la LARGHEZZA e' per-strategia (v2.4.5, vincente)
         }
      }

      if(ptype == POSITION_TYPE_BUY){
         double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
         // only trail once in profit by at least `act` ATR (v2.4.4: era 0.5 fisso)
         if(bid - open < actK * g_atr) continue;
         double newSL = NormPrice(bid - k * g_atr);
         if(newSL > curSL + 0.1 * g_point && newSL < bid){
            NXS_DoModify(t, newSL, curTP);
         }
      } else if(ptype == POSITION_TYPE_SELL){
         double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);
         if(open - ask < actK * g_atr) continue;
         double newSL = NormPrice(ask + k * g_atr);
         if((curSL == 0 || newSL < curSL - 0.1 * g_point) && newSL > ask){
            NXS_DoModify(t, newSL, curTP);
         }
      }
   }
}

#endif
