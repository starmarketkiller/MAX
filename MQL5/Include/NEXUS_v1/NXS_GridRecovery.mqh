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
      double existingExposure = NXS_DirExposureLots(gridDir);
      double effCap = NXS_EffectiveMaxDirExposureLots();
      if(existingExposure + lots > effCap + 1e-9){
         PrintFormat("[NEXUS RISK] GRID BLOCCATO: esposizione %s existing=%.2f + new=%.2f supererebbe cap=%.2f",
                     NXS_DirName(gridDir), existingExposure, lots, effCap);
         break;
      }

      NXS_TradeSetMagic(InpMagic + MAGIC_GRID + NXS_CountGrid() + 1);
      if(type == POSITION_TYPE_BUY)
         NXS_DoBuy(lots, g_sym, 0, 0, "NEXUS_GRID");
      else
         NXS_DoSell(lots, g_sym, 0, 0, "NEXUS_GRID");
      break;
   }
}

#endif
