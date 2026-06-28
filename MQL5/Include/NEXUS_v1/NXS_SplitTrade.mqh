//+------------------------------------------------------------------+
//|  NXS_SplitTrade.mqh - Partial closes P1 / P2 (FIXED 2026-06-16)   |
//|                                                                    |
//|  Each ticket can only fire P1 once and P2 once.  We track the     |
//|  flags in arrays because PositionClosePartial does NOT update     |
//|  POSITION_COMMENT of the parent ticket, so we cannot rely on the  |
//|  comment to know whether a partial has already been taken.        |
//+------------------------------------------------------------------+
#ifndef __NXS_SPLIT_MQH__
#define __NXS_SPLIT_MQH__

#define NXS_SPLIT_MAX 256

ulong g_splitP1[NXS_SPLIT_MAX];
ulong g_splitP2[NXS_SPLIT_MAX];
int   g_splitP1Cnt = 0;
int   g_splitP2Cnt = 0;

bool _splitHas(ulong t, ulong &arr[], int cnt){
   for(int i = 0; i < cnt; i++) if(arr[i] == t) return true;
   return false;
}
void _splitAdd(ulong t, ulong &arr[], int &cnt){
   if(cnt >= NXS_SPLIT_MAX){
      // shift left to drop oldest
      for(int i = 0; i < NXS_SPLIT_MAX-1; i++) arr[i] = arr[i+1];
      cnt = NXS_SPLIT_MAX - 1;
   }
   arr[cnt++] = t;
}
// Drop tickets that no longer exist (closed positions) — keeps arrays tidy
void _splitCleanup(ulong &arr[], int &cnt){
   int w = 0;
   for(int r = 0; r < cnt; r++){
      if(PositionSelectByTicket(arr[r])){
         arr[w++] = arr[r];
      }
   }
   cnt = w;
}

void NXS_ManageSplit(){
   if(!InpEnableSplit) return;
   if(g_atr <= 0) return;

   static datetime lastClean = 0;
   if(TimeCurrent() - lastClean > 300){   // cleanup every 5 minutes
      _splitCleanup(g_splitP1, g_splitP1Cnt);
      _splitCleanup(g_splitP2, g_splitP2Cnt);
      lastClean = TimeCurrent();
   }

   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsCoreMagic(mg)) continue;

      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double vol  = PositionGetDouble(POSITION_VOLUME);
      long   type = PositionGetInteger(POSITION_TYPE);
      double now  = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_BID)
                                                 : SymbolInfoDouble(g_sym, SYMBOL_ASK);
      double prof = (type == POSITION_TYPE_BUY) ? (now - open) : (open - now);
      double minVol = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);

      // P1: partial close at +InpTP1_ATR (only once per ticket)
      if(prof >= g_atr * InpTP1_ATR && !_splitHas(t, g_splitP1, g_splitP1Cnt)){
         double part = NormalizeDouble(vol * InpTP1_Pct, 2);
         if(part >= minVol && (vol - part) >= minVol){
            if(NXS_DoClosePartial(t, part)){
               _splitAdd(t, g_splitP1, g_splitP1Cnt);
               PrintFormat("[NEXUS] P1 closed %.2f of ticket %I64u @ +%.1fATR",
                           part, t, InpTP1_ATR);
            }
         } else {
            _splitAdd(t, g_splitP1, g_splitP1Cnt);
         }
      }
      // P2: partial close at +InpTP2_ATR (only once per ticket)
      else if(prof >= g_atr * InpTP2_ATR && !_splitHas(t, g_splitP2, g_splitP2Cnt)){
         double part = NormalizeDouble(vol * InpTP2_Pct, 2);
         if(part >= minVol && (vol - part) >= minVol){
            if(NXS_DoClosePartial(t, part)){
               _splitAdd(t, g_splitP2, g_splitP2Cnt);
               PrintFormat("[NEXUS] P2 closed %.2f of ticket %I64u @ +%.1fATR",
                           part, t, InpTP2_ATR);
            }
         } else {
            _splitAdd(t, g_splitP2, g_splitP2Cnt);
         }
      }
   }
}

#endif
