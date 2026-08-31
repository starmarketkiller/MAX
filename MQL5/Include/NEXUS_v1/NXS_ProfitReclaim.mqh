//+------------------------------------------------------------------+
//| NXS_ProfitReclaim.mqh                                              |
//| 31/08 - idea dell'utente dopo aver visto che ~50% del picco di     |
//| profitto flottante viene "ridato indietro" (analisi sui 112 trade  |
//| nudi: MFE totale $9754, incassato solo $4919). Un pareggio o       |
//| parziale puro PEGGIORA sempre il risultato (testato in 8 varianti  |
//| diverse stanotte, tutte negative) perche' taglia via l'esposizione |
//| dei pochi vincenti enormi da cui dipende l'intero edge.            |
//|                                                                    |
//| Questa versione e' diversa: incassa il profitto quando il          |
//| flottante e' alto (non lo stop), e se il prezzo poi RITORNA vicino |
//| al livello di entrata originale, riapre li' - recuperando          |
//| l'esposizione persa mantenendo il profitto gia' incassato.         |
//|                                                                    |
//| 31/08 - CORREZIONE dopo il primo test dal vivo: a lotto 0.01 (il   |
//| minimo del broker, quello di TUTTI i trade nudi) un parziale e'    |
//| matematicamente impossibile - 50% di 0.01 sarebbe 0.005, sotto il  |
//| minimo. Il guardiano di sicurezza nel codice bloccava tutto in     |
//| silenzio (nessun log, nessun errore) - stesso limite gia' visto in |
//| NXS_PipSequence.mqh ma dimenticato qui in fase di progetto. Ora    |
//| CHIUDE l'intera posizione al livello di armamento (incassa il      |
//| profitto vero, non pareggio) invece di tentare un parziale         |
//| impossibile - aggira il limite del lotto minimo completamente.     |
//| Simulazione offline aggiornata (arm=1.5xATR, tolleranza=0.35xATR): |
//| +$712.17 rispetto a non fare nulla, coerente su tutta la vicinanza |
//| di parametri testati. Da confermare sul vero Tester.               |
//+------------------------------------------------------------------+
#ifndef __NXS_PROFITRECLAIM_MQH__
#define __NXS_PROFITRECLAIM_MQH__

#define NXS_PRC_MAX 32
ulong    g_prcArmedTicket[NXS_PRC_MAX]; int g_prcArmedCnt = 0;   // posizioni gia' armate (in attesa di chiusura)
ulong    g_prcClosedTicket[NXS_PRC_MAX]; int g_prcClosedCnt = 0; // posizioni gia' chiuse da questo meccanismo

bool     g_prcAwaitingReentry = false;
int      g_prcReentryDir = 0;
double   g_prcReentryEntryPx = 0;   // livello di entrata originale, per la tolleranza
double   g_prcReentryTol = 0;       // tolleranza in prezzo
double   g_prcReentryLot = 0;
datetime g_prcReentryArmedAt = 0;

bool _prcHas(ulong t, ulong &arr[], int cnt){
   for(int i = 0; i < cnt; i++) if(arr[i] == t) return true;
   return false;
}
void _prcAdd(ulong t, ulong &arr[], int &cnt){
   if(cnt >= NXS_PRC_MAX){
      for(int i = 0; i < NXS_PRC_MAX-1; i++) arr[i] = arr[i+1];
      cnt = NXS_PRC_MAX - 1;
   }
   arr[cnt++] = t;
}

void NXS_ManageProfitReclaim(){
   if(!InpUseProfitReclaim) return;
   double atr = NXS_ATRv(PERIOD_H4, 1, InpATR_Period);
   if(atr <= 0) atr = g_atr;
   double armThresh = InpProfitReclaimArmATR * atr;
   double tol = InpProfitReclaimTolATR * atr;

   // --- riapertura, se in attesa e il prezzo e' tornato vicino all'entrata originale ---
   if(g_prcAwaitingReentry){
      if(InpSLReclaimExpireHours > 0 &&
         TimeCurrent() - g_prcReentryArmedAt > InpSLReclaimExpireHours * 3600){
         g_prcAwaitingReentry = false;
      } else {
         double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK), bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
         double px  = (g_prcReentryDir == 1) ? bid : ask;   // prezzo di mercato dal lato rilevante
         if(MathAbs(px - g_prcReentryEntryPx) <= tol){
            string cmt = InpComment + "|SAR|PROFITRECLAIM|" + EnumToString(PERIOD_H4);
            double atrH4 = atr;
            bool ok;
            if(g_prcReentryDir == 1){
               double sl = NormPrice(ask - atrH4 * 1.0);
               ok = NXS_SafeBuy(g_prcReentryLot, g_sym, sl, 0, cmt);
            } else {
               double sl = NormPrice(bid + atrH4 * 1.0);
               ok = NXS_SafeSell(g_prcReentryLot, g_sym, sl, 0, cmt);
            }
            PrintFormat("[NEXUS PROFITRECLAIM] rientro vicino a %.2f (tol=%.2f) dir=%d lot=%.2f esito=%s",
                        g_prcReentryEntryPx, tol, g_prcReentryDir, g_prcReentryLot, (ok?"OK":"FALLITA"));
            g_prcAwaitingReentry = false;
         }
      }
   }

   // --- armamento + chiusura completa sulle posizioni SAR aperte ---
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      if(_prcHas(t, g_prcClosedTicket, g_prcClosedCnt)) continue;   // gia' fatto per questo ticket

      long type = PositionGetInteger(POSITION_TYPE);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double vol  = PositionGetDouble(POSITION_VOLUME);
      double now  = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_BID)
                                                 : SymbolInfoDouble(g_sym, SYMBOL_ASK);
      double fav  = (type == POSITION_TYPE_BUY) ? (now - open) : (open - now);

      if(!_prcHas(t, g_prcArmedTicket, g_prcArmedCnt)){
         if(fav < armThresh) continue;
         _prcAdd(t, g_prcArmedTicket, g_prcArmedCnt);
         continue;   // la chiusura segue su un tick successivo (evita conflitto col coordinatore)
      }

      // armato: chiude l'intera posizione, incassando il profitto vero (non pareggio)
      NXS_PM_ProposeClose(t, 65, "PROFITRECLAIM",
                          StringFormat("chiusura completa a +%.2fxATR", InpProfitReclaimArmATR));
      g_prcAwaitingReentry = true;
      g_prcReentryDir = (type == POSITION_TYPE_BUY) ? 1 : -1;
      g_prcReentryEntryPx = open;
      g_prcReentryLot = vol;
      g_prcReentryArmedAt = TimeCurrent();
      _prcAdd(t, g_prcClosedTicket, g_prcClosedCnt);
   }
}

#endif
