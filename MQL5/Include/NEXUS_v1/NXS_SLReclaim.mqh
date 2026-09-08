//+------------------------------------------------------------------+
//| NXS_SLReclaim.mqh                                                  |
//| 30/08 - meccanismo richiesto dall'utente, esplicitamente PIU'      |
//| sicuro di un grid (nessuna media in perdita, mai piu' esposizione  |
//| nella direzione che sta perdendo):                                 |
//|   1. Un trade SAR salta per stop nativo (es. buy, stop sotto)      |
//|   2. Si segna quel livello di prezzo (la linea dello stop)         |
//|   3. Si aspetta che una candela M15 CHIUDA oltre quella linea       |
//|      nella direzione ORIGINALE del trade (per un buy: close >      |
//|      livello) - non basta toccarla, serve la chiusura              |
//|   4. Se conferma, si riapre nella STESSA direzione del trade        |
//|      originale (non nella direzione della rottura che aveva        |
//|      stoppato) - la logica: il crollo/rally che ha stoppato era     |
//|      probabilmente un falso allarme se il prezzo torna a           |
//|      riconquistare quel livello, non una vera inversione di trend. |
//+------------------------------------------------------------------+
#ifndef __NXS_SLRECLAIM_MQH__
#define __NXS_SLRECLAIM_MQH__

bool     g_slrPending = false;
double   g_slrLevel = 0;
int      g_slrDir = 0;          // direzione ORIGINALE del trade stoppato (+1 buy, -1 sell)
datetime g_slrArmedAt = 0;
datetime g_slrLastM15Seen = 0;  // evita di ricontrollare la stessa barra M15 piu' volte
int      g_slrChainLosses = 0;  // 30/08 - perdite CONSECUTIVE nella catena di riconquiste

// 30/08 - SICUREZZA aggiunta su segnalazione dell'utente: "e se l'EA
// rientra e la direzione e' ancora sbagliata, o rompe e gira di nuovo?"
// - senza un limite, una vera inversione di trend (non un falso allarme)
// puo' far incatenare piu' stop pieni sulla stessa chiamata di direzione
// sbagliata, ognuno riaperto dalla riconquista precedente. Dopo
// InpSLReclaimMaxChain perdite consecutive nella catena, ci si arrende:
// niente altra riconquista finche' non arriva un segnale SAR FRESCO
// (che ricalcola la direzione da zero, non riusa quella vecchia) o un
// trade della catena chiude in guadagno (resetta il contatore).
//
// Chiamata da NXS_EA_OnLogicalClose per OGNI chiusura di trade SAR (non
// solo quelle che riarmano) - pnl>=0 rompe la catena di perdite anche se
// il motivo di chiusura e' "sl" (uno stop trailing puo' chiudere in
// guadagno, visto stanotte sui trade grezzi).
void NXS_SLReclaim_OnTradeClosed(double pnl){
   if(pnl >= 0) g_slrChainLosses = 0;
}

// Chiamata quando una posizione SAR chiude per STOP nativo (non pareggio/
// trailing/max-loss/altre protezioni) - arma l'attesa della riconquista,
// a meno che la catena di perdite consecutive abbia gia' raggiunto il
// limite.
void NXS_SLReclaim_Arm(double slPrice, int dir, double pnl){
   if(!InpUseSLReclaim) return;
   if(slPrice <= 0 || dir == 0) return;
   if(pnl >= 0){
      g_slrChainLosses = 0;   // uno stop trailing in guadagno non e' una sconfitta - nessuna riconquista necessaria
      return;
   }
   g_slrChainLosses++;
   if(InpSLReclaimMaxChain > 0 && g_slrChainLosses > InpSLReclaimMaxChain){
      PrintFormat("[NEXUS SLRECLAIM] catena di %d perdite consecutive raggiunta (limite=%d) - "
                  "NESSUNA riconquista, ci si arrende fino al prossimo segnale SAR fresco",
                  g_slrChainLosses, InpSLReclaimMaxChain);
      g_slrPending = false;
      return;
   }
   g_slrPending = true;
   g_slrLevel = slPrice;
   g_slrDir = dir;
   g_slrArmedAt = TimeCurrent();
   g_slrLastM15Seen = 0;
   PrintFormat("[NEXUS SLRECLAIM] armato (catena=%d/%d): livello=%.2f dir=%d (in attesa di una chiusura M15 oltre la linea)",
               g_slrChainLosses, InpSLReclaimMaxChain, slPrice, dir);
}

void NXS_ManageSLReclaim(){
   if(!InpUseSLReclaim || !g_slrPending) return;

   // scadenza: non aspettare all'infinito
   if(InpSLReclaimExpireHours > 0 &&
      TimeCurrent() - g_slrArmedAt > InpSLReclaimExpireHours * 3600){
      PrintFormat("[NEXUS SLRECLAIM] scaduto senza conferma (livello=%.2f dir=%d)", g_slrLevel, g_slrDir);
      g_slrPending = false;
      return;
   }

   // se nel frattempo si e' gia' aperta una nuova posizione Nexus, non
   // sovrapporsi - resta armato per la prossima occasione libera.
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) return;
   }

   // valuta solo su una NUOVA barra M15 chiusa (shift=1), non ad ogni tick
   datetime m15Bar = iTime(g_sym, PERIOD_M15, 0);
   if(m15Bar == g_slrLastM15Seen) return;
   g_slrLastM15Seen = m15Bar;

   double closeM15 = iClose(g_sym, PERIOD_M15, 1);
   bool confirmed = (g_slrDir == 1) ? (closeM15 > g_slrLevel) : (closeM15 < g_slrLevel);
   if(!confirmed) return;

   // 07/09 - BUG TROVATO: fino a qui la riapertura chiamava NXS_SafeBuy/
   // NXS_SafeSell direttamente, bypassando NXS_CheckProtections() - il gate
   // usato da OGNI altro percorso di apertura (limite giornaliero, congelamento
   // Ruin, margine). In pratica SLReclaim poteva riaprire posizioni anche a
   // conto gia' congelato o oltre il limite di drawdown del giorno (osservato:
   // 37 violazioni della soglia -5%/giorno invece di 1, con le stesse
   // protezioni attive - vedi vault "FVG_CONT Prop-Compliant").
   //
   // 08/09 - AUDIT ESTERNO (A3): NXS_CheckProtections() copre solo DD
   // giornaliero/margine/max-trade/anti-revenge/anti-bleed/pausa EA. Ogni
   // altro percorso di apertura passa invece per
   // NXS_CommonExposurePreflight() (licenza, ruin freeze, protezioni,
   // stop obbligatorio, stato/indicatori degradati, RiskShield per
   // strategia, cap esposizione direzionale, margine proiettato, preflight
   // broker spread/distanza minima stop) - SLReclaim era l'unico percorso
   // senza questi controlli, rischiava un "invalid stops" silenzioso
   // proprio durante lo spike di spread che ha appena generato lo stop-out.
   // Sostituito col gate pieno.
   ENUM_NXS_DIR dir   = (g_slrDir == 1) ? DIR_BUY : DIR_SELL;
   ENUM_ORDER_TYPE otype = (g_slrDir == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double price = (g_slrDir == 1) ? ask : bid;
   // stop/target nativi ricalcolati come un ingresso SAR normale (1xATR/6xATR
   // H4) - nessuna indicazione diversa data dall'utente per questo caso.
   double atrH4 = NXS_ATRv(PERIOD_H4, 1, InpATR_Period);
   if(atrH4 <= 0) atrH4 = g_atr;
   string cmt = InpComment + "|SAR|SLRECLAIM|" + EnumToString(PERIOD_H4);
   double sl, tp;
   if(g_slrDir == 1){
      sl = NormPrice(ask - atrH4 * 1.0);
      tp = NormPrice(ask + atrH4 * 6.0);
   } else {
      sl = NormPrice(bid + atrH4 * 1.0);
      tp = NormPrice(bid - atrH4 * 6.0);
   }

   string pfReason = "";
   if(!NXS_CommonExposurePreflight("SLRECLAIM", "SAR", dir, InpSLReclaimLot,
                                   otype, price, sl, tp, pfReason)){
      PrintFormat("[NEXUS SLRECLAIM] riapertura bloccata dal gate comune (%s)", pfReason);
      return;   // resta armato, ritenta alla prossima barra M15 se ancora confermato
   }

   // 08/09 - AUDIT ESTERNO (A4): nessuno dei due percorsi (SLReclaim/
   // ProfitReclaim) chiamava NXS_TradeSetMagic() prima di riaprire - la
   // posizione ereditava il magic number stantio dell'ultimo modulo che
   // aveva aperto un ordine (grid/pyramid/entry primaria), corrompendo i
   // conteggi di layer e disattivando il partial-close (che filtra su
   // IsCoreMagic). La riapertura è un rientro "core", non un leg di
   // grid/pyramid - tagga come tale.
   NXS_TradeSetMagic(InpMagic + MAGIC_CORE);
   bool ok;
   if(g_slrDir == 1){
      ok = NXS_SafeBuy(InpSLReclaimLot, g_sym, sl, tp, cmt);
   } else {
      ok = NXS_SafeSell(InpSLReclaimLot, g_sym, sl, tp, cmt);
   }
   PrintFormat("[NEXUS SLRECLAIM] confermato (M15 close=%.2f oltre linea=%.2f) - riapertura dir=%d lot=%.2f esito=%s",
               closeM15, g_slrLevel, g_slrDir, InpSLReclaimLot, (ok ? "OK" : "FALLITA"));
   g_slrPending = false;
}

#endif
