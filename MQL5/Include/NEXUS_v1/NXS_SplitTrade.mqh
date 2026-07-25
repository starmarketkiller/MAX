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
// AUD0-SPLIT-002 / NXS-SPLIT-001 / NXS-SPLIT-002 — QUESTI ARRAY NON SONO
// L'AUTORITA'.
//
// Erano in memoria, limitati a 256 ticket e potati dal piu' vecchio anche se
// la posizione era ancora aperta: un riavvio, o semplicemente 257 posizioni nel
// tempo, potevano far ripetere un parziale gia' eseguito. Inoltre il marcatore
// veniva scritto DOPO l'azione, lasciando una finestra in cui un crash
// perdeva la traccia.
//
// L'autorita' anti-ripetizione e' lo stato PERSISTITO del coordinatore
// (NXS_PM_HasApplied -> NXS_State_HasApplied, salvato su disco): questi array
// restano solo una cache locale per i casi in cui il parziale NON viene
// proposto (volume sotto il minimo), che il coordinatore non registrerebbe.
// Quando sono pieni si scarta il piu' vecchio, ma la conseguenza e' al piu' una
// proposta in piu' che il coordinatore rifiutera' — non un doppio parziale.
void _splitAdd(ulong t, ulong &arr[], int &cnt){
   if(cnt >= NXS_SPLIT_MAX){
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

// AUD0-SPLIT-001 — il volume parziale era arrotondato a DUE DECIMALI fissi.
//
// Il passo di volume non e' due decimali ovunque: su diverse crypto e CFD e'
// 0.001, su altri strumenti 0.1. Con l'arrotondamento fisso il volume proposto
// poteva non essere un multiplo dello step — quindi rifiutato dal broker — o
// lasciare un residuo non tradabile.
//
// La normalizzazione usa ora lo step reale dello strumento. La stessa
// validazione (residuo minimo, volume non superiore alla posizione) vive nel
// coordinatore, che e' l'unico a inviare l'ordine.
double _nxs_split_normalize(string sym, double raw){
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   if(step <= 0) step = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   if(step <= 0) step = 0.01;
   double v = MathFloor(raw / step) * step;
   return NormalizeDouble(v, 8);
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
      double entryAtr = NXS_State_EntryAtr(t, g_atr);
      double minVol = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);

      // NXS-SPLIT-001 — FINESTRA DI CRASH.
      //
      // Il marcatore "parziale gia' fatto" veniva scritto DOPO l'azione: un
      // crash fra l'esecuzione del broker e il salvataggio lasciava la
      // posizione ridotta ma senza traccia, e al riavvio il parziale veniva
      // rifatto sul volume gia' ridotto.
      //
      // Il volume di APERTURA e' registrato nel registro degli intenti: se il
      // volume corrente e' gia' inferiore, un'uscita parziale e' certamente
      // avvenuta, qualunque cosa dicano i marcatori. E' un fatto osservabile,
      // non uno stato da ricordare.
      SNxsIntent sIntent;
      bool volumeAlreadyReduced = false;
      if(NXS_Intent_ByPosition((ulong)PositionGetInteger(POSITION_IDENTIFIER), sIntent) &&
         sIntent.entry_volume > 0){
         double vstep = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
         if(vstep <= 0) vstep = 0.01;
         volumeAlreadyReduced = (vol < sIntent.entry_volume - vstep * 0.5);
      }

      // P1: partial close at +InpTP1_ATR (only once per ticket)
      if(prof >= entryAtr * InpTP1_ATR && !_splitHas(t, g_splitP1, g_splitP1Cnt) &&
         !NXS_PM_HasApplied(t, "SPLIT_P1") && !volumeAlreadyReduced){
         double part = _nxs_split_normalize(g_sym, vol * InpTP1_Pct);
         if(part >= minVol && (vol - part) >= minVol){
            NXS_PM_ProposePartial(t, part, 70, "SPLIT_P1", "first partial target");
         } else {
            _splitAdd(t, g_splitP1, g_splitP1Cnt);
         }
      }
      // P2: partial close at +InpTP2_ATR (only once per ticket)
      else if(prof >= entryAtr * InpTP2_ATR && !_splitHas(t, g_splitP2, g_splitP2Cnt) &&
              !NXS_PM_HasApplied(t, "SPLIT_P2")){
         double part = _nxs_split_normalize(g_sym, vol * InpTP2_Pct);
         if(part >= minVol && (vol - part) >= minVol){
            NXS_PM_ProposePartial(t, part, 70, "SPLIT_P2", "second partial target");
         } else {
            _splitAdd(t, g_splitP2, g_splitP2Cnt);
         }
      }
   }
}

#endif
