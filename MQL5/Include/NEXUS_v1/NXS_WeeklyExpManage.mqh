//+------------------------------------------------------------------+
//|  NXS_WeeklyExpManage.mqh                                          |
//|  26/08 - breakeven + trailing STRUTTURALE per WEEKLY_EXP           |
//|  (candela M15 precedente, non ATR dal prezzo corrente come         |
//|  NXS_TrailingATR.mqh) - la stessa uscita adattiva verificata in    |
//|  Python (weekly_exp_ltf_entry_structural_trail_26-08.py):          |
//|  breakeven a 1.0R, trailing attivato a 1.5R e ancorato al minimo/  |
//|  massimo della candela M15 precedente +-0.3xATR(M15). Il rischio   |
//|  iniziale (R) e' quello REALE della posizione (open-SL al momento  |
//|  dell'apertura), tracciato per ticket - dopo che il breakeven o il |
//|  trailing spostano lo stop, POSITION_SL non lo dice piu'.          |
//+------------------------------------------------------------------+
#ifndef __NXS_WEEKLYEXP_MANAGE_MQH__
#define __NXS_WEEKLYEXP_MANAGE_MQH__

#define NXS_WEXP_MAX_TRACKED 20
ulong  g_wexpTicket[NXS_WEXP_MAX_TRACKED];
double g_wexpRiskDist[NXS_WEXP_MAX_TRACKED];
bool   g_wexpBE[NXS_WEXP_MAX_TRACKED];
bool   g_wexpTrailOn[NXS_WEXP_MAX_TRACKED];
int    g_wexpTrackCount = 0;

int _NXS_WExpMgr_Find(ulong ticket){
   for(int i = 0; i < g_wexpTrackCount; i++)
      if(g_wexpTicket[i] == ticket) return i;
   return -1;
}
int _NXS_WExpMgr_Register(ulong ticket, double riskDist){
   if(g_wexpTrackCount >= NXS_WEXP_MAX_TRACKED) return -1;
   int idx = g_wexpTrackCount;
   g_wexpTicket[idx] = ticket; g_wexpRiskDist[idx] = riskDist;
   g_wexpBE[idx] = false; g_wexpTrailOn[idx] = false;
   g_wexpTrackCount++;
   return idx;
}
void _NXS_WExpMgr_Remove(int idx){
   for(int k = idx; k < g_wexpTrackCount - 1; k++){
      g_wexpTicket[k]   = g_wexpTicket[k+1];
      g_wexpRiskDist[k] = g_wexpRiskDist[k+1];
      g_wexpBE[k]       = g_wexpBE[k+1];
      g_wexpTrailOn[k]  = g_wexpTrailOn[k+1];
   }
   g_wexpTrackCount--;
}

void NXS_WeeklyExpManage(){
   double a15 = NXS_ATRv(PERIOD_M15, 1);
   double prevLow  = iLow (g_sym, PERIOD_M15, 1);
   double prevHigh = iHigh(g_sym, PERIOD_M15, 1);

   for(int i = PositionsTotal() - 1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsNexusMagic(mg)) continue;
      string cm = PositionGetString(POSITION_COMMENT);
      if(StringFind(cm, "WEEKLY_EXP") < 0) continue;

      long   ptype = PositionGetInteger(POSITION_TYPE);
      double open  = PositionGetDouble(POSITION_PRICE_OPEN);
      double curSL = PositionGetDouble(POSITION_SL);
      double curTP = PositionGetDouble(POSITION_TP);

      int idx = _NXS_WExpMgr_Find(t);
      if(idx < 0){
         double rd = MathAbs(open - curSL);
         if(rd <= 0) continue;   // stop non ancora impostato, salta questo giro
         idx = _NXS_WExpMgr_Register(t, rd);
         if(idx < 0) continue;
      }
      double rd = g_wexpRiskDist[idx];
      if(rd <= 0) continue;

      if(ptype == POSITION_TYPE_BUY){
         double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
         if(!g_wexpBE[idx] && bid >= open + 1.0 * rd){
            double newSL = MathMax(curSL, open);
            if(newSL > curSL + 0.1 * g_point)
               NXS_PM_ProposeModify(t, newSL, curTP, 40, "WEXP_BE", "weekly_exp breakeven 1.0R");
            g_wexpBE[idx] = true;
         }
         if(!g_wexpTrailOn[idx] && bid >= open + 1.5 * rd) g_wexpTrailOn[idx] = true;
         if(g_wexpTrailOn[idx] && a15 > 0 && prevLow > 0){
            double newSL = NormPrice(prevLow - 0.3 * a15);
            if(newSL > curSL + 0.1 * g_point && newSL < bid)
               NXS_PM_ProposeModify(t, newSL, curTP, 40, "WEXP_TRAIL", "weekly_exp structural trail (prev M15 low)");
         }
      } else if(ptype == POSITION_TYPE_SELL){
         double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);
         if(!g_wexpBE[idx] && ask <= open - 1.0 * rd){
            double newSL = (curSL == 0) ? open : MathMin(curSL, open);
            if(curSL == 0 || newSL < curSL - 0.1 * g_point)
               NXS_PM_ProposeModify(t, newSL, curTP, 40, "WEXP_BE", "weekly_exp breakeven 1.0R");
            g_wexpBE[idx] = true;
         }
         if(!g_wexpTrailOn[idx] && ask <= open - 1.5 * rd) g_wexpTrailOn[idx] = true;
         if(g_wexpTrailOn[idx] && a15 > 0 && prevHigh > 0){
            double newSL = NormPrice(prevHigh + 0.3 * a15);
            if((curSL == 0 || newSL < curSL - 0.1 * g_point) && newSL > ask)
               NXS_PM_ProposeModify(t, newSL, curTP, 40, "WEXP_TRAIL", "weekly_exp structural trail (prev M15 high)");
         }
      }
   }

   // pulizia: rimuovi dal tracking i ticket non piu' aperti
   for(int i = g_wexpTrackCount - 1; i >= 0; i--){
      if(!PositionSelectByTicket(g_wexpTicket[i])) _NXS_WExpMgr_Remove(i);
   }
}

#endif
