//+------------------------------------------------------------------+
//|  NXS_GridRecovery.mqh - Limited 3-layer grid in trend             |
//+------------------------------------------------------------------+
#ifndef __NXS_GRID_MQH__
#define __NXS_GRID_MQH__

int NXS_CountGrid(){
   int n = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(IsGridMagic(mg)) n++;
   }
   return n;
}

void NXS_ManageGrid(){
   if(!InpEnableGrid) return;
   if(g_atr <= 0) return;
   if(g_regime != REGIME_STRONG_TREND && g_regime != REGIME_WEAK_TREND) return;
   if(NXS_CountGrid() >= MAX_GRID_LAYERS) return;

   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsCoreMagic(mg)) continue;
      double profit = PositionGetDouble(POSITION_PROFIT);
      if(profit >= 0) continue;
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      long type = PositionGetInteger(POSITION_TYPE);
      double step = g_atr * InpGridStepATR;
      double now  = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_BID)
                                                 : SymbolInfoDouble(g_sym, SYMBOL_ASK);
      double dist = (type == POSITION_TYPE_BUY) ? (open - now) : (now - open);
      if(dist < step) continue;
      double lots = PositionGetDouble(POSITION_VOLUME);

      // v2.0.30 SAFETY FIX: grid adds used to call NXS_DoBuy/DoSell directly,
      // completely bypassing the v2.0.26 total-exposure cap (which only the
      // signal-driven NXS_OpenTrade/NXR_OpenTrade paths checked). This let a
      // losing core position balloon to 4x its size (core + 3 grid layers)
      // with no cap - the exact pattern that caused the 2026-07 BTC incident.
      ENUM_NXS_DIR gridDir = (type == POSITION_TYPE_BUY) ? DIR_BUY : DIR_SELL;
      ENUM_ORDER_TYPE otype = (type == POSITION_TYPE_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      double refPrice = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_ASK)
                                                     : SymbolInfoDouble(g_sym, SYMBOL_BID);
      double sl = 0, tp = 0;
      string gateReason = "";
      if(!NXS_CommonExposurePreflight("GRID", gridDir, lots, otype, refPrice,
                                      sl, tp, gateReason)){
         PrintFormat("[NEXUS RISK] GRID BLOCCATO: %s", gateReason);
         break;
      }

      NXS_TradeSetMagic(InpMagic + MAGIC_GRID + NXS_CountGrid() + 1);
      if(type == POSITION_TYPE_BUY)
         NXS_SafeBuy(lots, g_sym, sl, tp, "NEXUS_GRID");
      else
         NXS_SafeSell(lots, g_sym, sl, tp, "NEXUS_GRID");
      break;
   }
}

#endif
