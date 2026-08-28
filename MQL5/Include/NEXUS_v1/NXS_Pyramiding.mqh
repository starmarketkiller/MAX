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
      // 28/08 - il velocity gate e' spento di default a livello globale
      // (InpUseVelocity=false, NXS_Inputs.mqh - disattivato in passato perche'
      // troppo restrittivo sull'ingresso primario). Con il gate spento
      // NXS_GetVelocity() ritorna SEMPRE VEL_NEUTRAL (NXS_Velocity.mqh, prima
      // riga della funzione): il controllo di direzione si applica solo
      // quando il gate e' davvero attivo, stesso trattamento gia' riservato
      // al gate primario (NXS_VelocityBlocks: "if(!gate) return false").
      // Accetta anche le varianti _PB (pullback dentro un trend in corso),
      // coerenti col resto del codice (NXS_SignalRouter.mqh).
      if(g_run_UseVelocityGate){
         bool velBlocks = (type == POSITION_TYPE_BUY  && vel.state != VEL_BULL && vel.state != VEL_BULL_PB) ||
                          (type == POSITION_TYPE_SELL && vel.state != VEL_BEAR && vel.state != VEL_BEAR_PB);
         if(velBlocks) continue;
      }
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
      //
      // 28/08 - causa REALE trovata con diagnostica dedicata sul Tester MT5 a
      // tick reali (939.234 volte "profitto raggiunto", 0 gambe aperte mai):
      // su un conto piccolo ($500-1000) le posizioni normali aprono quasi
      // sempre al lotto minimo (0.01, per il gate RISK_SIZE gia' noto) -
      // "meta' del genitore" e' allora 0.005, che arrotondato per difetto
      // allo step del broker (0.01) diventa ESATTAMENTE ZERO. NXS_CalcLot()
      // calcolava correttamente un budget valido (verificato nei log: a volte
      // 0.01 "a rischio maggiorato"), ma MathMin(half, budgetLots) faceva
      // sempre vincere lo zero. Ora "meta' del genitore" non scende mai sotto
      // il lotto minimo tradabile - il budget di rischio resta comunque il
      // tetto vero tramite MathMin con budgetLots subito sotto.
      double vstep = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
      double vmin  = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
      double vmax  = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MAX);
      double half = MathMax(PositionGetDouble(POSITION_VOLUME) * 0.5, vmin);
      double budgetLots = NXS_CalcLot(slDist);
      if(budgetLots <= 0){
         Print("[NEXUS RISK] PYRAMID BLOCCATO: rischio non calcolabile per la leg");
         break;
      }
      double lots  = MathMin(half, budgetLots);
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
