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

      // P1 — Time-based forced exit.
      // v2.3.1 FIX: con i profili, il max-hold SCALA sul TF della strategia
      // (~40 barre di quel TF, come il motore del sito). Il vecchio cap fisso
      // di InpMaxHoldHours (4h) ammazzava le strategie D1/H4 prima del TP ->
      // 0 TP colpiti. Fallback su InpMaxHoldHours per chi non ha profilo.
      long maxHoldSec = (long)InpMaxHoldHours * 3600;
      if(InpUseStrategyProfiles){
         string cm = PositionGetString(POSITION_COMMENT);
         string cp[]; int ncp = StringSplit(cm, '|', cp);
         if(ncp >= 2 && StringLen(cp[1]) > 0){
            ENUM_TIMEFRAMES ptf = NXS_Profile_TF(cp[1]);
            if(ptf != PERIOD_CURRENT)
               maxHoldSec = (long)PeriodSeconds(ptf) * 40;   // ~40 barre del TF
         }
      }
      if(maxHoldSec > 0){
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
         string cmt = PositionGetString(POSITION_COMMENT);
         string pp[]; int npp = StringSplit(cmt, '|', pp);
         if(npp >= 2 && StringLen(pp[1]) > 0){
            double a, b; bool h; double be, tr;
            if(NXS_Profile_Get(pp[1], a, b, h, be, tr)){ pBeR = be; pTrail = tr; }
         }
      }
      if(pBeR >= 0 || pTrail >= 0){
         double risk = MathAbs(open - sl);
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
