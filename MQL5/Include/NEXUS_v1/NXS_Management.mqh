//+------------------------------------------------------------------+
//|  NXS_Management.mqh - BE + ATR trailing                           |
//+------------------------------------------------------------------+
#ifndef __NXS_MANAGEMENT_MQH__
#define __NXS_MANAGEMENT_MQH__

void NXS_ManageBreakevenAndTrail(){
   if(g_atr <= 0) return;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsNexusMagic(mg)) continue;
      long type = PositionGetInteger(POSITION_TYPE);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   = PositionGetDouble(POSITION_SL);
      double tp   = PositionGetDouble(POSITION_TP);
      double now  = (type == POSITION_TYPE_BUY)
                  ? SymbolInfoDouble(g_sym, SYMBOL_BID)
                  : SymbolInfoDouble(g_sym, SYMBOL_ASK);
      double prof = (type == POSITION_TYPE_BUY) ? (now - open) : (open - now);

      // P1 — Time-based forced exit
      if(InpMaxHoldHours > 0){
         datetime openT = (datetime)PositionGetInteger(POSITION_TIME);
         if(openT > 0 && (TimeCurrent() - openT) > InpMaxHoldHours * 3600){
            NXS_DoClose(t);
            PrintFormat("[NEXUS] Time-exit (%dh) ticket %I64u", InpMaxHoldHours, t);
            continue;
         }
      }

      // Break-even check
      bool beReached = (type == POSITION_TYPE_BUY) ? (sl >= open - g_point * 2)
                                                    : (sl <= open + g_point * 2 && sl > 0);
      double beTrigger = g_atr * g_run_BE_TriggerATR;   // tunabile dal sito
      if(!beReached && prof >= beTrigger){
         double newSL = (type == POSITION_TYPE_BUY) ? MathMax(sl, open) : MathMin(sl == 0 ? open : sl, open);
         if(MathAbs(newSL - sl) > g_point * 2){
            NXS_DoModify(t, NormPrice(newSL), tp);
            beReached = true;
         }
      }
      // Trailing — tighter once BE has been reached
      double trailAct = g_atr * g_run_TrailActivateATR;   // tunabile dal sito
      double trailDist= g_atr * (beReached ? InpTrailDistancePostBE : g_run_TrailDistanceATR);
      if(prof >= trailAct){
         double newSL = (type == POSITION_TYPE_BUY) ? now - trailDist : now + trailDist;
         if(type == POSITION_TYPE_BUY  && newSL > sl + g_point * 2)
            NXS_DoModify(t, NormPrice(newSL), tp);
         if(type == POSITION_TYPE_SELL && (sl == 0 || newSL < sl - g_point * 2))
            NXS_DoModify(t, NormPrice(newSL), tp);
      }
   }
}

#endif
