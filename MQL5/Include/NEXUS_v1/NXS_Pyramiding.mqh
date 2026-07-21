//+------------------------------------------------------------------+
//|  NXS_Pyramiding.mqh - Add when winning > 1 ATR + velocity ok       |
//+------------------------------------------------------------------+
#ifndef __NXS_PYRAMID_MQH__
#define __NXS_PYRAMID_MQH__

int NXS_CountPyr(){
   int n = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(IsPyrMagic(mg)) n++;
   }
   return n;
}

void NXS_ManagePyramid(SNXSVel &vel){
   if(!InpEnablePyramid) return;
   if(g_atr <= 0) return;
   if(NXS_CountPyr() >= MAX_PYRAMID) return;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsCoreMagic(mg)) continue;
      long type = PositionGetInteger(POSITION_TYPE);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double now  = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_BID)
                                                 : SymbolInfoDouble(g_sym, SYMBOL_ASK);
      double prof = (type == POSITION_TYPE_BUY) ? (now - open) : (open - now);
      if(prof < g_atr) continue;
      if(type == POSITION_TYPE_BUY  && vel.state != VEL_BULL) continue;
      if(type == POSITION_TYPE_SELL && vel.state != VEL_BEAR) continue;
      double lots = PositionGetDouble(POSITION_VOLUME) * 0.5;
      double minLot = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
      lots = MathMax(minLot, lots);

      // v2.0.30 SAFETY FIX: same bypass as grid - pyramid adds went straight
      // to NXS_DoBuy/DoSell, skipping the total-exposure cap entirely.
      ENUM_NXS_DIR pyrDir = (type == POSITION_TYPE_BUY) ? DIR_BUY : DIR_SELL;
      ENUM_ORDER_TYPE otype = (type == POSITION_TYPE_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      double refPrice = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_ASK)
                                                     : SymbolInfoDouble(g_sym, SYMBOL_BID);
      double sl = 0, tp = 0;
      string gateReason = "";
      if(!NXS_CommonExposurePreflight("PYRAMID", pyrDir, lots, otype, refPrice,
                                      sl, tp, gateReason)){
         PrintFormat("[NEXUS RISK] PYRAMID BLOCCATO: %s", gateReason);
         break;
      }

      NXS_TradeSetMagic(InpMagic + MAGIC_PYRAMID + NXS_CountPyr() + 1);
      if(type == POSITION_TYPE_BUY)
         NXS_SafeBuy(lots, g_sym, sl, tp, "NEXUS_PYR");
      else
         NXS_SafeSell(lots, g_sym, sl, tp, "NEXUS_PYR");
      break;
   }
}

#endif
