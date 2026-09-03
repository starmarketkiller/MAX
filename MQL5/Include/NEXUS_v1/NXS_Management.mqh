//+------------------------------------------------------------------+
//|  NXS_Management.mqh - BE + ATR trailing                           |
//+------------------------------------------------------------------+
#ifndef __NXS_MANAGEMENT_MQH__
#define __NXS_MANAGEMENT_MQH__

// 30/08 - breakeven fisso in pip, indipendente dal percorso per-strategia/
// globale di NXS_ManageBreakevenAndTrail() sotto (che per SAR e' inerte,
// beR=0/trailATR=0 nel profilo - vedi commento li'). Girata su OGNI
// posizione Nexus, non collegata a nessun profilo: sposta lo stop
// all'apertura appena il prezzo si muove a favore di InpFixedBEPips pip,
// senza toccare TP ne' altre logiche di trailing.
void NXS_ManageFixedBE(){
   if(!InpUseFixedBE) return;
   double beDist = InpFixedBEPips * g_profile.pipSize;
   if(beDist <= 0) return;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      long type = PositionGetInteger(POSITION_TYPE);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   = PositionGetDouble(POSITION_SL);
      double tp   = PositionGetDouble(POSITION_TP);
      double now  = (type == POSITION_TYPE_BUY)
                  ? SymbolInfoDouble(g_sym, SYMBOL_BID)
                  : SymbolInfoDouble(g_sym, SYMBOL_ASK);
      double prof = (type == POSITION_TYPE_BUY) ? (now - open) : (open - now);
      if(prof < beDist) continue;
      bool alreadyBE = (type == POSITION_TYPE_BUY) ? (sl >= open - g_point * 2)
                                                    : (sl <= open + g_point * 2 && sl > 0);
      if(alreadyBE) continue;
      NXS_PM_ProposeModify(t, NormPrice(open), tp, 55, "FIXED_BE",
                           StringFormat("breakeven fisso dopo %.0f pip", InpFixedBEPips));
   }
}

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

      // P1 — Time-based forced exit.
      // v2.3.1 FIX: con i profili, il max-hold SCALA sul TF della strategia
      // (~40 barre di quel TF, come il motore del sito). Il vecchio cap fisso
      // di InpMaxHoldHours (4h) ammazzava le strategie D1/H4 prima del TP ->
      // 0 TP colpiti. Fallback su InpMaxHoldHours per chi non ha profilo.
      // NXS-PROT-006: il limite viene ora da NXS_MaxHold_LimitSec(), unica
      // autorita'. Se la strategia NON e' risolvibile dal commento, questo
      // modulo NON agisce: la competenza passa interamente a
      // NXS_Prot_CheckMaxHold(), che applica il limite conservativo. Prima
      // entrambi agivano con fallback diversi (4h qui, 12h x factor la').
      bool holdResolved = false;
      long maxHoldSec = NXS_MaxHold_LimitSec(PositionGetString(POSITION_COMMENT),
                                             holdResolved);
      if(holdResolved && maxHoldSec > 0){
         datetime openT = (datetime)PositionGetInteger(POSITION_TIME);
         if(openT > 0 && (TimeCurrent() - openT) > maxHoldSec){
            NXS_PM_ProposeClose(t, 80, "CLASSIC_TIME_STOP", "maximum hold time exceeded");
            PrintFormat("[NEXUS] Time-exit (%.1fh) ticket %I64u", maxHoldSec/3600.0, t);
            continue;
         }
      }

      bool beReached = (type == POSITION_TYPE_BUY) ? (sl >= open - g_point * 2)
                                                    : (sl <= open + g_point * 2 && sl > 0);

      // v2.2.8 — BE/trail PER-STRATEGIA (come nel backtest). Se la posizione ha un
      // profilo: BE a beR x RISCHIO (0=off), trailing a trailATR x ATR (0=off).
      double pBeR = -1, pTrail = -1;
      if(InpUseStrategyProfiles){
         // NXS-MGMT-002: la gestione dipendeva dal parsing del COMMENTO. Un
         // commento troncato dal broker faceva perdere il profilo, quindi la
         // posizione finiva sul percorso globale con soglie diverse da quelle
         // della sua strategia. Il registro degli intenti e' l'autorita'.
         string stratName = "";
         SNxsIntent pIntent;
         if(NXS_Intent_ByPosition((ulong)PositionGetInteger(POSITION_IDENTIFIER), pIntent))
            stratName = pIntent.strategy;
         if(stratName == ""){
            string cmt = PositionGetString(POSITION_COMMENT);
            string pp[]; int npp = StringSplit(cmt, '|', pp);
            if(npp >= 2) stratName = pp[1];
         }
         if(StringLen(stratName) > 0){
            double a, b; bool h; double be, tr;
            if(NXS_Profile_Get(stratName, a, b, h, be, tr)){ pBeR = be; pTrail = tr; }
         }
      }
      if(pBeR >= 0 || pTrail >= 0){
         // NXS-MGMT-001 — IL RISCHIO INIZIALE E' IMMUTABILE.
         //
         // `|apertura - SL corrente|` non e' il rischio del trade: e' la
         // distanza dallo stop DI ADESSO. Dopo il primo spostamento (breakeven
         // o trailing) quel numero si restringe, quindi la soglia "profitto >=
         // N x rischio" diventa via via piu' facile da superare: le azioni di
         // gestione scattano prima di quanto la regola prevedesse, e in modo
         // diverso a ogni posizione a seconda di quanto lo stop si e' mosso.
         //
         // Il rischio iniziale e' registrato all'esecuzione: si usa quello.
         double risk = MathAbs(open - sl);
         SNxsIntent mIntent;
         double posVol = PositionGetDouble(POSITION_VOLUME);
         if(NXS_Intent_ByPosition((ulong)PositionGetInteger(POSITION_IDENTIFIER), mIntent) &&
            mIntent.risk_money > 0 && posVol > 0){
            // risk_money e' in valuta: si riconverte in distanza di prezzo.
            double tickV  = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_VALUE);
            double tickSz = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_SIZE);
            if(tickV > 0 && tickSz > 0){
               double origDist = (mIntent.risk_money / (tickV * posVol)) * tickSz;
               if(origDist > 0) risk = origDist;
            }
         }
         if(pBeR > 0 && !beReached && risk > 0 && prof >= pBeR * risk){
            NXS_PM_ProposeModify(t, NormPrice(open), tp, 60, "PROFILE_BREAKEVEN", "profile R threshold");
            beReached = true;
         }
         if(pTrail > 0){
            double td = g_atr * pTrail;
            double nSL = (type == POSITION_TYPE_BUY) ? now - td : now + td;
            if(type == POSITION_TYPE_BUY  && nSL > sl + g_point * 2)
               NXS_PM_ProposeModify(t, NormPrice(nSL), tp, 40, "PROFILE_TRAIL", "profile ATR trail");
            if(type == POSITION_TYPE_SELL && (sl == 0 || nSL < sl - g_point * 2))
               NXS_PM_ProposeModify(t, NormPrice(nSL), tp, 40, "PROFILE_TRAIL", "profile ATR trail");
         }
         continue;   // gestita per-strategia, salta il globale
      }

      // --- Fallback GLOBALE (strategie senza profilo) ---
      double beTrigger = g_atr * g_run_BE_TriggerATR;   // tunabile dal sito
      if(!beReached && prof >= beTrigger){
         double newSL = (type == POSITION_TYPE_BUY) ? MathMax(sl, open) : MathMin(sl == 0 ? open : sl, open);
         if(MathAbs(newSL - sl) > g_point * 2){
             NXS_PM_ProposeModify(t, NormPrice(newSL), tp, 60, "GLOBAL_BREAKEVEN", "global BE threshold");
            beReached = true;
         }
      }
      double trailAct = g_atr * g_run_TrailActivateATR;   // tunabile dal sito
      double trailDist= g_atr * (beReached ? InpTrailDistancePostBE : g_run_TrailDistanceATR);
      if(prof >= trailAct){
         double newSL = (type == POSITION_TYPE_BUY) ? now - trailDist : now + trailDist;
         if(type == POSITION_TYPE_BUY  && newSL > sl + g_point * 2)
            NXS_PM_ProposeModify(t, NormPrice(newSL), tp, 40, "CLASSIC_TRAIL", "classic ATR trail");
         if(type == POSITION_TYPE_SELL && (sl == 0 || newSL < sl - g_point * 2))
            NXS_PM_ProposeModify(t, NormPrice(newSL), tp, 40, "CLASSIC_TRAIL", "classic ATR trail");
      }
   }
}

#endif
