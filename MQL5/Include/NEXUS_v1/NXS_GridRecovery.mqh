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

      // AUD0-ADD-005 / NXS-EXP-002: la leg veniva inviata con sl=0 e tp=0,
      // cioè priva di stop lato broker. Se l'EA o il terminale si fermavano
      // prima di una successiva modifica, la posizione restava scoperta.
      // Lo stop viene calcolato dallo stesso ATR usato per il passo di griglia.
      double slDist = g_atr * InpGridStepATR * (double)MAX_GRID_LAYERS;
      if(slDist <= 0){
         Print("[NEXUS RISK] GRID BLOCCATO: distanza di stop non calcolabile (ATR non valido)");
         break;
      }
      double sl = (type == POSITION_TYPE_BUY) ? (refPrice - slDist) : (refPrice + slDist);
      sl = NormalizeDouble(sl, (int)SymbolInfoInteger(g_sym, SYMBOL_DIGITS));
      double tp = 0;

      // AUD0-ADD-004 / NXS-EXP-003: la leg replicava l'INTERO volume del core
      // in perdita, quindi core + 3 layer arrivavano a 4x l'esposizione
      // iniziale. Il volume viene ora derivato dal budget di rischio residuo
      // e dalla distanza di stop effettiva, non dal volume del genitore.
      double budgetLots = NXS_CalcLot(slDist);
      if(budgetLots <= 0){
         Print("[NEXUS RISK] GRID BLOCCATO: rischio non calcolabile per la leg");
         break;
      }
      double addLots = MathMin(lots, budgetLots);
      double vstep = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
      double vmin  = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
      if(vstep > 0) addLots = MathFloor(addLots / vstep) * vstep;
      if(addLots < vmin){
         PrintFormat("[NEXUS RISK] GRID BLOCCATO: lotto derivato dal budget (%.4f) "
                     "sotto il minimo broker (%.4f)", addLots, vmin);
         break;
      }

      string gateReason = "";
      if(!NXS_CommonExposurePreflight("GRID", gridDir, addLots, otype, refPrice,
                                      sl, tp, gateReason)){
         PrintFormat("[NEXUS RISK] GRID BLOCCATO: %s", gateReason);
         break;
      }

      NXS_TradeSetMagic(InpMagic + MAGIC_GRID + NXS_CountGrid() + 1);
      // AUD0-ADD-007: l'esito dell'invio veniva ignorato, quindi un fallimento
      // restava invisibile e la logica dei layer si basava solo su scansioni
      // successive delle posizioni.
      bool sent = (type == POSITION_TYPE_BUY)
                  ? NXS_SafeBuy(addLots, g_sym, sl, tp, "NEXUS_GRID")
                  : NXS_SafeSell(addLots, g_sym, sl, tp, "NEXUS_GRID");
      if(sent){
         // AUD0-LEDGER-010: la gamba eredita la SEQUENZA del core, cosi' il
         // ledger puo' ricomporre drawdown e P/L della campagna invece di
         // contare ogni position come un trade a se'.
         NXS_Intent_Record(NXS_TradeOrderTicket(), "GRID_RECOVERY", 0.0,
                           NXS_Intent_RiskMoney(g_sym, refPrice, sl, addLots),
                           "grid", NXS_Intent_GroupOfTicket(t), g_atr, addLots);
         // NXS-VSL-007 / NXS-EXP-001: la correlazione del Virtual SL escludeva
         // le gambe secondarie, creando DUE classi di protezione — ingressi
         // con stop logico ed esposizione aggiuntiva senza. Ora la copertura
         // e' la stessa su ogni percorso che crea esposizione.
         NXS_VSL_OnRequested(NXS_TradeOrderTicket(), g_sym, (long)InpMagic,
                             (type == POSITION_TYPE_BUY ? +1 : -1),
                             "GRID_RECOVERY", sl, sl);
      }
      PrintFormat("[NEXUS GRID] add %s lots=%.4f sl=%.5f result=%s",
                  (type == POSITION_TYPE_BUY ? "BUY" : "SELL"), addLots, sl,
                  (sent ? "SENT" : "FAILED"));
      break;
   }
}

#endif
