//+------------------------------------------------------------------+
//| NXS_SLReclaim.mqh                                                  |
//| 30/08 - meccanismo richiesto dall'utente, esplicitamente PIU'      |
//| sicuro di un grid (nessuna media in perdita, mai piu' esposizione  |
//| nella direzione che sta perdendo):                                 |
//|   1. Un trade salta per stop nativo (es. buy, stop sotto)          |
//|   2. Si segna quel livello di prezzo (la linea dello stop)         |
//|   3. Si aspetta che una candela M15 CHIUDA oltre quella linea       |
//|      nella direzione ORIGINALE del trade (per un buy: close >      |
//|      livello) - non basta toccarla, serve la chiusura              |
//|   4. Se conferma, si riapre nella STESSA direzione del trade        |
//|      originale (non nella direzione della rottura che aveva        |
//|      stoppato) - la logica: il crollo/rally che ha stoppato era     |
//|      probabilmente un falso allarme se il prezzo torna a           |
//|      riconquistare quel livello, non una vera inversione di trend. |
//|                                                                     |
//| 10/09 - FIX IDENTITA' E ATTRIBUZIONE (commit separato dal Research  |
//| Mode, audit richiesto dall'utente):                                 |
//|                                                                     |
//| BUG TROVATO: la riapertura era hardcoded come se fosse SEMPRE un    |
//| trade SAR ("|SAR|SLRECLAIM|", ATR H4, ricetta 1.0/6.0), qualunque   |
//| fosse la strategia REALMENTE stoppata (chiamata da                  |
//| NXS_EA_OnLogicalClose per OGNI chiusura "sl", non solo SAR). Nessuna|
//| chiamata a NXS_Intent_Record: il trade riaperto non esisteva nel    |
//| registro degli intenti, quindi ogni consumer (RiskShield breaker,   |
//| ledger, stats) ricadeva sul parsing del commento e leggeva "SAR" -  |
//| un trade FVG_CONT/TURTLE_SOUP/qualunque stoppato e poi riconquistato|
//| finiva silenziosamente nelle statistiche di SAR, alterandole in modo|
//| non distinguibile a posteriori. In piu' lo stato (g_slrPending/     |
//| g_slrLevel/g_slrDir) era un singleton globale: due stop di strategie|
//| diverse quasi simultanei si sovrascrivevano a vicenda senza log.    |
//|                                                                     |
//| FIX: lo stato pending diventa una coda (piu' stop in attesa insieme,|
//| uno per strategia/livello), la catena di perdite consecutive e'     |
//| tracciata PER STRATEGIA (prima era implicitamente "per SAR"), la    |
//| riapertura porta il commento "InpComment|<STRATEGIA_ORIGINALE>|     |
//| SL_RECLAIM|<TF_ORIGINE>" (es. "NEXUS_v2.50|FVG_CONT|SL_RECLAIM|     |
//| PERIOD_H4") ed e' registrata in NXS_Intent_Record con la strategia  |
//| originale come identita' e route="sl_reclaim" a marcarla come       |
//| follow-up senza perdere il genitore. L'ATR usato per SL/TP del      |
//| reclaim e' quello del TF DI ORIGINE della strategia stoppata (prima |
//| sempre H4, sbagliato per TURTLE_SOUP=H1/MALAYSIAN_SNR=M30/ecc), ma  |
//| il moltiplicatore resta una ricetta esplicita e dedicata al reclaim |
//| (InpSLReclaimSLAtr/InpSLReclaimTPAtr, stessi default 1.0/6.0 di     |
//| prima - NESSUN cambio di comportamento numerico per chi lo usava    |
//| gia' solo su SAR), non la ricetta nativa della strategia originale. |
//| Non toccata la logica di QUANDO il reclaim scatta (arm/conferma/    |
//| scadenza/gate identici a prima).                                    |
//+------------------------------------------------------------------+
#ifndef __NXS_SLRECLAIM_MQH__
#define __NXS_SLRECLAIM_MQH__

#define NXS_SLR_MAX 8   // riconquiste in attesa contemporaneamente (una per stop armato)

struct SNxsSLRSlot {
   double          level;         // linea dello stop originale
   int             dir;           // direzione ORIGINALE del trade stoppato (+1 buy, -1 sell)
   datetime        armedAt;
   datetime        lastM15Seen;   // evita di ricontrollare la stessa barra M15 piu' volte
   string          strategy;      // strategia REALMENTE stoppata (non piu' sempre "SAR")
   ENUM_TIMEFRAMES sourceTF;      // TF di origine di quella strategia (NXS_StrategySourceTF)
};
SNxsSLRSlot g_slrSlots[];         // coda dinamica - vedi nota 10/09 sopra

// Catena di perdite consecutive nella riconquista, PER STRATEGIA (prima era
// un contatore globale unico, implicitamente "per SAR" - vedi nota 10/09).
string g_slrChainStrat[];
int    g_slrChainCount[];

int _NXS_SLR_ChainIdx(const string strategy, bool createIfMissing){
   for(int i = ArraySize(g_slrChainStrat) - 1; i >= 0; i--)
      if(g_slrChainStrat[i] == strategy) return i;
   if(!createIfMissing) return -1;
   int n = ArraySize(g_slrChainStrat);
   ArrayResize(g_slrChainStrat, n + 1);
   ArrayResize(g_slrChainCount, n + 1);
   g_slrChainStrat[n] = strategy;
   g_slrChainCount[n] = 0;
   return n;
}

void _NXS_SLR_RemoveSlot(int idx){
   int n = ArraySize(g_slrSlots);
   if(idx < 0 || idx >= n) return;
   for(int i = idx; i < n - 1; i++) g_slrSlots[i] = g_slrSlots[i + 1];
   ArrayResize(g_slrSlots, n - 1);
}

// Chiamata da NXS_EA_OnLogicalClose per OGNI chiusura di trade (non solo
// quelle che riarmano) - pnl>=0 rompe la catena di perdite di QUELLA
// strategia anche se il motivo di chiusura non e' "sl" (uno stop trailing
// puo' chiudere in guadagno).
void NXS_SLReclaim_OnTradeClosed(double pnl, const string strategy){
   if(pnl < 0) return;
   int ci = _NXS_SLR_ChainIdx(strategy, false);
   if(ci >= 0) g_slrChainCount[ci] = 0;
}

// Chiamata quando una posizione chiude per STOP nativo (non pareggio/
// trailing/max-loss/altre protezioni) - arma l'attesa della riconquista per
// QUELLA strategia, a meno che la sua catena di perdite consecutive abbia
// gia' raggiunto il limite.
void NXS_SLReclaim_Arm(double slPrice, int dir, double pnl,
                       string strategy, ENUM_TIMEFRAMES sourceTF){
   if(!InpUseSLReclaim) return;
   if(slPrice <= 0 || dir == 0) return;
   if(StringLen(strategy) == 0) strategy = "UNKNOWN";

   int ci = _NXS_SLR_ChainIdx(strategy, true);
   if(pnl >= 0){
      g_slrChainCount[ci] = 0;   // uno stop trailing in guadagno non e' una sconfitta - nessuna riconquista necessaria
      return;
   }
   g_slrChainCount[ci]++;
   if(InpSLReclaimMaxChain > 0 && g_slrChainCount[ci] > InpSLReclaimMaxChain){
      PrintFormat("[NEXUS SLRECLAIM] %s: catena di %d perdite consecutive raggiunta (limite=%d) - "
                  "NESSUNA riconquista, ci si arrende fino al prossimo stop fresco di %s",
                  strategy, g_slrChainCount[ci], InpSLReclaimMaxChain, strategy);
      return;
   }
   if(ArraySize(g_slrSlots) >= NXS_SLR_MAX){
      PrintFormat("[NEXUS SLRECLAIM] coda piena (%d/%d) - riconquista per %s scartata",
                  ArraySize(g_slrSlots), (int)NXS_SLR_MAX, strategy);
      return;
   }

   int n = ArraySize(g_slrSlots);
   ArrayResize(g_slrSlots, n + 1);
   g_slrSlots[n].level       = slPrice;
   g_slrSlots[n].dir         = dir;
   g_slrSlots[n].armedAt     = TimeCurrent();
   g_slrSlots[n].lastM15Seen = 0;
   g_slrSlots[n].strategy    = strategy;
   g_slrSlots[n].sourceTF    = sourceTF;
   PrintFormat("[NEXUS SLRECLAIM] armato per %s (catena=%d/%d, TF origine=%s): livello=%.2f dir=%d "
               "(in attesa di una chiusura M15 oltre la linea)",
               strategy, g_slrChainCount[ci], InpSLReclaimMaxChain, EnumToString(sourceTF), slPrice, dir);
}

void NXS_ManageSLReclaim(){
   if(!InpUseSLReclaim || ArraySize(g_slrSlots) == 0) return;

   // se nel frattempo si e' gia' aperta una nuova posizione Nexus, non
   // sovrapporsi - stessa regola di prima (nessun cambiamento sul QUANDO
   // scatta), estesa a valere per l'intera coda invece che per un solo stato
   // globale: resta tutto armato, si ritenta al prossimo tick libero.
   for(int i = PositionsTotal() - 1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) return;
   }

   // valuta solo su una NUOVA barra M15 chiusa (shift=1), non ad ogni tick
   datetime m15Bar = iTime(g_sym, PERIOD_M15, 0);

   for(int i = ArraySize(g_slrSlots) - 1; i >= 0; i--){
      // scadenza: non aspettare all'infinito
      if(InpSLReclaimExpireHours > 0 &&
         TimeCurrent() - g_slrSlots[i].armedAt > InpSLReclaimExpireHours * 3600){
         PrintFormat("[NEXUS SLRECLAIM] %s: scaduto senza conferma (livello=%.2f dir=%d)",
                     g_slrSlots[i].strategy, g_slrSlots[i].level, g_slrSlots[i].dir);
         _NXS_SLR_RemoveSlot(i);
         continue;
      }

      if(m15Bar == g_slrSlots[i].lastM15Seen) continue;
      g_slrSlots[i].lastM15Seen = m15Bar;

      double closeM15 = iClose(g_sym, PERIOD_M15, 1);
      bool confirmed = (g_slrSlots[i].dir == 1) ? (closeM15 > g_slrSlots[i].level)
                                                 : (closeM15 < g_slrSlots[i].level);
      if(!confirmed) continue;

      string          strategy = g_slrSlots[i].strategy;
      ENUM_TIMEFRAMES srcTF    = g_slrSlots[i].sourceTF;

      // stesso gate doppio di sempre (vedi storia in fondo al file) - non
      // toccato dal fix identita'.
      string protReason = "";
      if(!NXS_CheckProtections(protReason)){
         PrintFormat("[NEXUS SLRECLAIM] %s: riapertura bloccata da protezione conto (%s)",
                     strategy, protReason);
         continue;   // resta armato, ritenta alla prossima barra M15 se ancora confermato
      }

      ENUM_NXS_DIR    dir   = (g_slrSlots[i].dir == 1) ? DIR_BUY : DIR_SELL;
      ENUM_ORDER_TYPE otype = (g_slrSlots[i].dir == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      double ask   = SymbolInfoDouble(g_sym, SYMBOL_ASK);
      double bid   = SymbolInfoDouble(g_sym, SYMBOL_BID);
      double price = (g_slrSlots[i].dir == 1) ? ask : bid;

      // SL/TP: ricetta ESPLICITA e dedicata al reclaim (InpSLReclaimSLAtr/
      // InpSLReclaimTPAtr), calcolata pero' sull'ATR del TF DI ORIGINE della
      // strategia stoppata - prima era sempre ATR H4 (la ricetta di SAR),
      // sbagliato per qualunque strategia con un TF diverso.
      double atrSrc = NXS_ATRv(srcTF, 1, InpATR_Period);
      if(atrSrc <= 0) atrSrc = g_atr;
      string cmt = InpComment + "|" + strategy + "|SL_RECLAIM|" + EnumToString(srcTF);
      double sl, tp;
      if(g_slrSlots[i].dir == 1){
         sl = NormPrice(ask - atrSrc * InpSLReclaimSLAtr);
         tp = NormPrice(ask + atrSrc * InpSLReclaimTPAtr);
      } else {
         sl = NormPrice(bid + atrSrc * InpSLReclaimSLAtr);
         tp = NormPrice(bid - atrSrc * InpSLReclaimTPAtr);
      }

      // Gate comune di sempre, ma ora con la VERA strategia al posto di
      // "SAR" hardcoded: eventuali gate per-strategia (es. RiskShield
      // breaker) valutano lo stato della strategia realmente coinvolta.
      string pfReason = "";
      if(!NXS_CommonExposurePreflight("SLRECLAIM", strategy, dir, InpSLReclaimLot,
                                      otype, price, sl, tp, pfReason)){
         PrintFormat("[NEXUS SLRECLAIM] %s: riapertura bloccata dal gate comune (%s)",
                     strategy, pfReason);
         continue;   // resta armato, ritenta alla prossima barra M15 se ancora confermato
      }

      // Rientro "core", non un leg di grid/pyramid.
      NXS_TradeSetMagic(InpMagic + MAGIC_CORE);
      bool ok = (g_slrSlots[i].dir == 1)
                ? NXS_SafeBuy(InpSLReclaimLot, g_sym, sl, tp, cmt)
                : NXS_SafeSell(InpSLReclaimLot, g_sym, sl, tp, cmt);
      if(ok){
         // Registro degli intenti con la strategia ORIGINALE come identita'
         // statistica e route="sl_reclaim" a marcare il follow-up: RiskShield,
         // ledger e stats non ricadono piu' sul parsing del commento e non
         // vedono mai "SAR" per un trade che non lo era.
         NXS_Intent_Record(NXS_TradeOrderTicket(), strategy, 0.0,
                           NXS_Intent_RiskMoney(g_sym, price, sl, InpSLReclaimLot),
                           "sl_reclaim");
      }
      PrintFormat("[NEXUS SLRECLAIM] %s confermato (M15 close=%.2f oltre linea=%.2f) - "
                  "riapertura dir=%d lot=%.2f esito=%s",
                  strategy, closeM15, g_slrSlots[i].level, g_slrSlots[i].dir,
                  InpSLReclaimLot, (ok ? "OK" : "FALLITA"));
      _NXS_SLR_RemoveSlot(i);
   }
}

#endif
