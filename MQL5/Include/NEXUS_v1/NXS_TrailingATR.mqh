//+------------------------------------------------------------------+
//|  NXS_TrailingATR.mqh - Dynamic ATR-based trailing stop            |
//|  Replaces simple step trailing with: SL = price - k*ATR(now)      |
//+------------------------------------------------------------------+
#ifndef __NXS_TRAILING_ATR_MQH__
#define __NXS_TRAILING_ATR_MQH__

void NXS_TrailATR(){
   if(!InpUseAtrTrail) return;
   if(g_atr <= 0) return;
   double k = InpAtrTrailMult;
   if(k <= 0) k = 1.5;

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

      if(ptype == POSITION_TYPE_BUY){
         double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
         // only trail once in profit by at least 0.5 ATR
         if(bid - open < 0.5 * g_atr) continue;
         double newSL = NormPrice(bid - k * g_atr);
         if(newSL > curSL + 0.1 * g_point && newSL < bid){
            NXS_DoModify(t, newSL, curTP);
         }
      } else if(ptype == POSITION_TYPE_SELL){
         double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);
         if(open - ask < 0.5 * g_atr) continue;
         double newSL = NormPrice(ask + k * g_atr);
         if((curSL == 0 || newSL < curSL - 0.1 * g_point) && newSL > ask){
            NXS_DoModify(t, newSL, curTP);
         }
      }
   }
}

#endif
