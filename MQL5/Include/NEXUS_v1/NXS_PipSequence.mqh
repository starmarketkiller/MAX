//+------------------------------------------------------------------+
//| NXS_PipSequence.mqh                                                |
//| 30/08 - schema di gestione richiesto dall'utente per l'esperimento |
//| "auto-close off" su SAR: lotto fisso, dimezza lo stop e prendi un  |
//| parziale a +50 pip, sposta in pareggio e prendi un altro parziale  |
//| a +100 pip, e se poi il prezzo torna a toccare il pareggio riapre  |
//| un lotto pieno con lo stop gia' dimezzato. "Pip" qui e'            |
//| InpPipSeqPipValue in prezzo (confermato dall'utente: $0.10 su      |
//| GOLD - NON il pipSize=0.01 del profilo simbolo, che a quella scala |
//| resta dentro il rumore, vedi il test fallito di InpUseFixedBE).    |
//|                                                                    |
//| BUG TROVATO E CORRETTO (primo giro): il coordinatore              |
//| (NXS_PositionCoordinator.mqh) accetta UNA SOLA proposta per        |
//| ticket per ciclo - due Propose (modify + partial) sullo stesso     |
//| ticket nello stesso tick si scartano a vicenda, vince quella       |
//| "piu' stretta" per NXS_PM_Stricter(). Verificato nei log: solo i   |
//| parziali applicavano, mai la modifica dello stop. Ora ogni stage   |
//| e' spezzato in due sotto-passi (modifica poi parziale) su tick     |
//| separati, tracciati con marcatori one-shot indipendenti.           |
//|                                                                    |
//| SEMPLIFICAZIONE DICHIARATA: la "riapertura a pareggio" e' rilevata |
//| controllando se una posizione che aveva gia' raggiunto lo stage 2  |
//| sparisce da PositionsTotal() - non distingue un'uscita esattamente |
//| al pareggio da un'altra chiusura (es. spread gate, max-loss) nel   |
//| raro caso in cui intervenga prima. Accettabile per un build        |
//| sperimentale, da rivedere se il pattern risulta utile.             |
//+------------------------------------------------------------------+
#ifndef __NXS_PIPSEQUENCE_MQH__
#define __NXS_PIPSEQUENCE_MQH__

#define NXS_PIPSEQ_MAX 64
ulong  g_pipSeqS1Mod[NXS_PIPSEQ_MAX];  int g_pipSeqS1ModCnt = 0;
ulong  g_pipSeqS1Part[NXS_PIPSEQ_MAX]; int g_pipSeqS1PartCnt = 0;
ulong  g_pipSeqS2Mod[NXS_PIPSEQ_MAX];  int g_pipSeqS2ModCnt = 0;
ulong  g_pipSeqS2Part[NXS_PIPSEQ_MAX]; int g_pipSeqS2PartCnt = 0;
ulong  g_pipSeqTicket[NXS_PIPSEQ_MAX]; double g_pipSeqHalfDist[NXS_PIPSEQ_MAX]; int g_pipSeqHalfCnt = 0;
ulong  g_pipSeqPrevS2Mod[NXS_PIPSEQ_MAX]; int g_pipSeqPrevS2ModCnt = 0;

bool   g_pipSeqAwaitingReentry = false;
int    g_pipSeqReentryDir = 0;
double g_pipSeqReentrySLDist = 0;

// 30/08 - stesso problema segnalato dall'utente per SLReclaim: senza un
// limite, il loop di riapertura ricombatte la stessa direzione stantia
// all'infinito se SAR ha semplicemente chiamato il verso sbagliato per un
// tratto lungo (non rumore) - visto stanotte: PF0.94, netto -809.60 su
// 1421 trade con l'equity breaker disattivato. Stesso schema di
// InpSLReclaimMaxChain: conta le perdite REALIZZATE (non presunte) della
// catena di riaperture, si ferma dopo InpPipSeqMaxChain, resta fermo
// finche' non arriva una posizione SAR genuinamente fresca (comment senza
// "PIPSEQ_REENTRY").
int    g_pipSeqChainLosses = 0;
ulong  g_pipSeqSeenTicket[NXS_PIPSEQ_MAX]; int g_pipSeqSeenCnt = 0;

bool _pipSeqHas(ulong t, ulong &arr[], int cnt){
   for(int i = 0; i < cnt; i++) if(arr[i] == t) return true;
   return false;
}
void _pipSeqAdd(ulong t, ulong &arr[], int &cnt){
   if(cnt >= NXS_PIPSEQ_MAX){
      for(int i = 0; i < NXS_PIPSEQ_MAX-1; i++) arr[i] = arr[i+1];
      cnt = NXS_PIPSEQ_MAX - 1;
   }
   arr[cnt++] = t;
}
double _pipSeqClosedPnl(ulong posId){
   double sum = 0;
   if(HistorySelectByPosition(posId)){
      int total = HistoryDealsTotal();
      for(int i = 0; i < total; i++){
         ulong dt = HistoryDealGetTicket(i);
         if(dt == 0) continue;
         sum += HistoryDealGetDouble(dt, DEAL_PROFIT)
              + HistoryDealGetDouble(dt, DEAL_SWAP)
              + HistoryDealGetDouble(dt, DEAL_COMMISSION);
      }
   }
   return sum;
}
double _pipSeqGetHalf(ulong t){
   for(int i = 0; i < g_pipSeqHalfCnt; i++) if(g_pipSeqTicket[i] == t) return g_pipSeqHalfDist[i];
   return 0;
}
void _pipSeqSetHalf(ulong t, double v){
   for(int i = 0; i < g_pipSeqHalfCnt; i++) if(g_pipSeqTicket[i] == t){ g_pipSeqHalfDist[i] = v; return; }
   if(g_pipSeqHalfCnt >= NXS_PIPSEQ_MAX){
      for(int i = 0; i < NXS_PIPSEQ_MAX-1; i++){ g_pipSeqTicket[i]=g_pipSeqTicket[i+1]; g_pipSeqHalfDist[i]=g_pipSeqHalfDist[i+1]; }
      g_pipSeqHalfCnt = NXS_PIPSEQ_MAX - 1;
   }
   g_pipSeqTicket[g_pipSeqHalfCnt] = t; g_pipSeqHalfDist[g_pipSeqHalfCnt] = v; g_pipSeqHalfCnt++;
}

void NXS_ManagePipSequence(){
   if(!InpUsePipSeq) return;
   double pip = InpPipSeqPipValue;
   if(pip <= 0) pip = 0.10;
   double stage1Dist = InpPipSeqStage1Pips * pip;
   double stage2Dist  = InpPipSeqStage2Pips * pip;
   double minVol = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);

   // --- rileva chiusure di posizioni che avevano gia' ricevuto il pareggio (stage2 modify) ---
   ulong curS2Mod[NXS_PIPSEQ_MAX]; int curCnt = 0;
   for(int i = 0; i < g_pipSeqS2ModCnt; i++)
      if(PositionSelectByTicket(g_pipSeqS2Mod[i])) curS2Mod[curCnt++] = g_pipSeqS2Mod[i];
   for(int i = 0; i < g_pipSeqPrevS2ModCnt; i++){
      ulong t = g_pipSeqPrevS2Mod[i];
      bool stillOpen = false;
      for(int j = 0; j < curCnt; j++) if(curS2Mod[j] == t){ stillOpen = true; break; }
      if(!stillOpen && !g_pipSeqAwaitingReentry){
         double closedPnl = _pipSeqClosedPnl(t);
         if(closedPnl < 0) g_pipSeqChainLosses++;
         else               g_pipSeqChainLosses = 0;

         if(InpPipSeqMaxChain > 0 && g_pipSeqChainLosses > InpPipSeqMaxChain){
            PrintFormat("[NEXUS PIPSEQ] catena di %d perdite consecutive raggiunta (limite=%d, pnl ultima=%.2f) - "
                        "NESSUNA riapertura, ci si ferma finche' non arriva un segnale SAR fresco",
                        g_pipSeqChainLosses, InpPipSeqMaxChain, closedPnl);
            g_pipSeqReentryDir = 0;
            g_pipSeqReentrySLDist = 0;
         } else {
            g_pipSeqAwaitingReentry = true;
            PrintFormat("[NEXUS PIPSEQ] ticket=%I64u chiuso dopo il pareggio (pnl=%.2f, catena=%d/%d) - riapertura programmata dir=%d dist=%.2f",
                        t, closedPnl, g_pipSeqChainLosses, InpPipSeqMaxChain, g_pipSeqReentryDir, g_pipSeqReentrySLDist);
         }
      }
   }
   ArrayCopy(g_pipSeqPrevS2Mod, curS2Mod, 0, 0, curCnt);
   g_pipSeqPrevS2ModCnt = curCnt;

   // --- riapertura, se in attesa e nessuna posizione Nexus aperta ---
   if(g_pipSeqAwaitingReentry && g_pipSeqReentryDir != 0 && g_pipSeqReentrySLDist > 0){
      bool anyOpen = false;
      for(int i = PositionsTotal()-1; i >= 0; i--){
         ulong t = PositionGetTicket(i);
         if(t == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
         if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
         anyOpen = true; break;
      }
      if(!anyOpen){
         double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);
         double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
         string cmt = InpComment + "|SAR|PIPSEQ_REENTRY|" + EnumToString(PERIOD_H4);
         bool ok;
         if(g_pipSeqReentryDir == 1){
            double sl = NormPrice(ask - g_pipSeqReentrySLDist);
            ok = NXS_SafeBuy(InpPipSeqLot, g_sym, sl, 0, cmt);
         } else {
            double sl = NormPrice(bid + g_pipSeqReentrySLDist);
            ok = NXS_SafeSell(InpPipSeqLot, g_sym, sl, 0, cmt);
         }
         PrintFormat("[NEXUS PIPSEQ] riapertura dir=%d lot=%.2f slDist=%.2f esito=%s",
                     g_pipSeqReentryDir, InpPipSeqLot, g_pipSeqReentrySLDist, (ok?"OK":"FALLITA"));
         g_pipSeqAwaitingReentry = false;
         g_pipSeqReentryDir = 0;
         g_pipSeqReentrySLDist = 0;
      }
   }

   // --- gestione stage 1 / stage 2 sulle posizioni aperte ---
   // Ogni stage e' due sotto-passi su tick SEPARATI (modify poi partial) -
   // il coordinatore scarta la seconda proposta se arriva sullo stesso
   // ticket nello stesso ciclo della prima (vedi commento in testa al file).
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;

      // prima volta che PipSeq vede questo ticket: se non e' una riapertura
      // della catena (comment senza PIPSEQ_REENTRY), e' un segnale SAR
      // genuinamente fresco - la catena di perdite pregresse non conta piu'.
      if(!_pipSeqHas(t, g_pipSeqSeenTicket, g_pipSeqSeenCnt)){
         _pipSeqAdd(t, g_pipSeqSeenTicket, g_pipSeqSeenCnt);
         if(StringFind(PositionGetString(POSITION_COMMENT), "PIPSEQ_REENTRY") < 0 && g_pipSeqChainLosses > 0){
            PrintFormat("[NEXUS PIPSEQ] segnale SAR fresco (ticket=%I64u) - reset catena perdite (era %d)",
                        t, g_pipSeqChainLosses);
            g_pipSeqChainLosses = 0;
         }
      }

      long type = PositionGetInteger(POSITION_TYPE);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   = PositionGetDouble(POSITION_SL);
      double tp   = PositionGetDouble(POSITION_TP);
      double vol  = PositionGetDouble(POSITION_VOLUME);
      double now  = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_BID)
                                                 : SymbolInfoDouble(g_sym, SYMBOL_ASK);
      double prof = (type == POSITION_TYPE_BUY) ? (now - open) : (open - now);

      if(prof < stage1Dist) continue;

      // Stage 1a: dimezza la distanza dello stop (una volta sola)
      if(!_pipSeqHas(t, g_pipSeqS1Mod, g_pipSeqS1ModCnt)){
         if(sl > 0){
            double origDist = MathAbs(open - sl);
            double halfDist = origDist / 2.0;
            _pipSeqSetHalf(t, halfDist);   // memorizzato SUBITO, non ridedotto piu' tardi da un SL che potrebbe non aver ancora applicato
            double newSL = (type == POSITION_TYPE_BUY) ? open - halfDist : open + halfDist;
            bool tighter = (type == POSITION_TYPE_BUY) ? (newSL > sl) : (newSL < sl);
            if(tighter)
               NXS_PM_ProposeModify(t, NormPrice(newSL), tp, 65, "PIPSEQ_STAGE1",
                                    StringFormat("dimezza stop a +%.0f pip", InpPipSeqStage1Pips));
         }
         _pipSeqAdd(t, g_pipSeqS1Mod, g_pipSeqS1ModCnt);
         continue;   // il parziale segue su un tick successivo
      }
      // Stage 1b: parziale 0.01 (una volta sola, dopo che 1a e' gia' passato)
      if(!_pipSeqHas(t, g_pipSeqS1Part, g_pipSeqS1PartCnt)){
         double part = _nxs_split_normalize(g_sym, InpPipSeqPartialLot);
         if(part >= minVol && (vol - part) >= minVol)
            NXS_PM_ProposePartial(t, part, 65, "PIPSEQ_STAGE1",
                                  StringFormat("parziale %.2f a +%.0f pip", InpPipSeqPartialLot, InpPipSeqStage1Pips));
         _pipSeqAdd(t, g_pipSeqS1Part, g_pipSeqS1PartCnt);
         continue;
      }

      if(prof < stage2Dist) continue;

      // Stage 2a: pareggio (una volta sola)
      if(!_pipSeqHas(t, g_pipSeqS2Mod, g_pipSeqS2ModCnt)){
         NXS_PM_ProposeModify(t, NormPrice(open), tp, 65, "PIPSEQ_STAGE2",
                              StringFormat("pareggio a +%.0f pip", InpPipSeqStage2Pips));
         _pipSeqAdd(t, g_pipSeqS2Mod, g_pipSeqS2ModCnt);
         // memorizza direzione/distanza per un eventuale re-ingresso -
         // la distanza e' quella gia' dimezzata allo stage1, non ridedotta
         // dallo stato live del broker (timing-dipendente).
         g_pipSeqReentryDir = (type == POSITION_TYPE_BUY) ? 1 : -1;
         double half = _pipSeqGetHalf(t);
         g_pipSeqReentrySLDist = (half > 0) ? half : stage1Dist;
         continue;   // il parziale segue su un tick successivo
      }
      // Stage 2b: parziale 0.01 (una volta sola, dopo che 2a e' gia' passato)
      if(!_pipSeqHas(t, g_pipSeqS2Part, g_pipSeqS2PartCnt)){
         double part = _nxs_split_normalize(g_sym, InpPipSeqPartialLot);
         if(part >= minVol && (vol - part) >= minVol)
            NXS_PM_ProposePartial(t, part, 65, "PIPSEQ_STAGE2",
                                  StringFormat("parziale %.2f a +%.0f pip", InpPipSeqPartialLot, InpPipSeqStage2Pips));
         _pipSeqAdd(t, g_pipSeqS2Part, g_pipSeqS2PartCnt);
      }
   }
}

#endif
