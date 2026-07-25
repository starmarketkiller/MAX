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
      // v2.0.30 SAFETY FIX: same bypass as grid - pyramid adds went straight
      // to NXS_DoBuy/DoSell, skipping the total-exposure cap entirely.
      ENUM_NXS_DIR pyrDir = (type == POSITION_TYPE_BUY) ? DIR_BUY : DIR_SELL;
      ENUM_ORDER_TYPE otype = (type == POSITION_TYPE_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      double refPrice = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_ASK)
                                                     : SymbolInfoDouble(g_sym, SYMBOL_BID);

      // AUD0-ADD-005 / NXS-EXP-002: la leg partiva con sl=0, senza protezione
      // lato broker. Stop a un ATR dal prezzo di ingresso della piramide.
      double slDist = g_atr;
      if(slDist <= 0){
         Print("[NEXUS RISK] PYRAMID BLOCCATO: ATR non valido, stop non calcolabile");
         break;
      }
      double sl = (type == POSITION_TYPE_BUY) ? (refPrice - slDist) : (refPrice + slDist);
      sl = NormalizeDouble(sl, (int)SymbolInfoInteger(g_sym, SYMBOL_DIGITS));
      double tp = 0;

      // AUD0-ADD-006 / NXS-EXP-004: il volume era "metà del genitore" con il
      // solo clamp al minimo broker — nessuna normalizzazione allo step e
      // nessun legame con il rischio effettivo. Ora si prende il minore tra
      // metà del genitore e il lotto consentito dal budget di rischio.
      double half = PositionGetDouble(POSITION_VOLUME) * 0.5;
      double budgetLots = NXS_CalcLot(slDist);
      if(budgetLots <= 0){
         Print("[NEXUS RISK] PYRAMID BLOCCATO: rischio non calcolabile per la leg");
         break;
      }
      double lots  = MathMin(half, budgetLots);
      double vstep = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
      double vmin  = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
      double vmax  = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MAX);
      if(vstep > 0) lots = MathFloor(lots / vstep) * vstep;
      if(vmax  > 0) lots = MathMin(lots, vmax);
      if(lots < vmin){
         // Non si arrotonda MAI verso l'alto fino al minimo broker: sarebbe
         // rischiare più del budget approvato (stesso difetto di
         // AUD0-RISK-002 sul percorso primario).
         PrintFormat("[NEXUS RISK] PYRAMID BLOCCATO: lotto derivato dal budget "
                     "(%.4f) sotto il minimo broker (%.4f)", lots, vmin);
         break;
      }

      string gateReason = "";
      if(!NXS_CommonExposurePreflight("PYRAMID", pyrDir, lots, otype, refPrice,
                                      sl, tp, gateReason)){
         PrintFormat("[NEXUS RISK] PYRAMID BLOCCATO: %s", gateReason);
         break;
      }

      NXS_TradeSetMagic(InpMagic + MAGIC_PYRAMID + NXS_CountPyr() + 1);
      // AUD0-ADD-007: l'esito dell'invio veniva ignorato.
      bool sent = (type == POSITION_TYPE_BUY)
                  ? NXS_SafeBuy(lots, g_sym, sl, tp, "NEXUS_PYR")
                  : NXS_SafeSell(lots, g_sym, sl, tp, "NEXUS_PYR");
      if(sent){
         NXS_Intent_Record(NXS_TradeOrderTicket(), "PYRAMID", 0.0,
                           NXS_Intent_RiskMoney(g_sym, refPrice, sl, lots),
                           "pyramid", NXS_Intent_GroupOfTicket(t), g_atr, lots);
         // NXS-VSL-007 / NXS-EXP-001: la correlazione del Virtual SL escludeva
         // le gambe secondarie, creando DUE classi di protezione — ingressi
         // con stop logico ed esposizione aggiuntiva senza. Ora la copertura
         // e' la stessa su ogni percorso che crea esposizione.
         NXS_VSL_OnRequested(NXS_TradeOrderTicket(), g_sym, (long)InpMagic,
                             (type == POSITION_TYPE_BUY ? +1 : -1),
                             "PYRAMID", sl, sl);
      }
      PrintFormat("[NEXUS PYRAMID] add %s lots=%.4f sl=%.5f result=%s",
                  (type == POSITION_TYPE_BUY ? "BUY" : "SELL"), lots, sl,
                  (sent ? "SENT" : "FAILED"));
      break;
   }
}

#endif
