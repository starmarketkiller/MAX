//+------------------------------------------------------------------+
//| NXS_PositionCoordinator.mqh - one action per position/tick       |
//+------------------------------------------------------------------+
#ifndef __NXS_POSITION_COORDINATOR_MQH__
#define __NXS_POSITION_COORDINATOR_MQH__

#define NXS_PM_MAX_PROPOSALS 512
#define NXS_PM_MAX_APPLIED   512

enum ENUM_NXS_PM_ACTION { NXS_PM_NONE=0, NXS_PM_MODIFY, NXS_PM_PARTIAL, NXS_PM_CLOSE };

struct SNXSPMProposal {
   ulong ticket;
   ENUM_NXS_PM_ACTION action;
   int priority;
   double sl;
   double tp;
   double volume;
   string source;
   string reason;
};

SNXSPMProposal g_nxsPmBest[NXS_PM_MAX_PROPOSALS];
int g_nxsPmBestCount = 0;
ulong g_nxsPmAppliedTicket[NXS_PM_MAX_APPLIED];
string g_nxsPmAppliedSource[NXS_PM_MAX_APPLIED];
int g_nxsPmAppliedCount = 0;

void NXS_PM_BeginCycle(){ g_nxsPmBestCount = 0; }

bool NXS_PM_HasApplied(ulong ticket, string source){
   if(NXS_State_HasApplied(ticket, source)) return true;
   for(int i=0; i<g_nxsPmAppliedCount; i++)
      if(g_nxsPmAppliedTicket[i] == ticket && g_nxsPmAppliedSource[i] == source) return true;
   return false;
}

void NXS_PM_RecordApplied(ulong ticket, string source){
   if(NXS_PM_HasApplied(ticket, source)) return;
   // AUD0-PM-003 — questa lista in memoria non e' l'autorita'.
   //
   // Oltre 512 voci scarta la piu' vecchia, quindi da sola non puo' garantire
   // che un'azione one-shot non venga rifatta. L'autorita' e' lo stato
   // PERSISTITO (NXS_State_RecordManagement, salvato subito sotto): la lista
   // resta una cache di lettura veloce. Quando e' piena si scarta la voce piu'
   // vecchia, ma NXS_State_HasApplied continua a rispondere correttamente
   // perche' legge dallo snapshot per-posizione, non da qui.
   if(g_nxsPmAppliedCount >= NXS_PM_MAX_APPLIED){
      for(int i=1; i<NXS_PM_MAX_APPLIED; i++){
         g_nxsPmAppliedTicket[i-1] = g_nxsPmAppliedTicket[i];
         g_nxsPmAppliedSource[i-1] = g_nxsPmAppliedSource[i];
      }
      g_nxsPmAppliedCount = NXS_PM_MAX_APPLIED - 1;
   }
   g_nxsPmAppliedTicket[g_nxsPmAppliedCount] = ticket;
   g_nxsPmAppliedSource[g_nxsPmAppliedCount] = source;
   g_nxsPmAppliedCount++;
   NXS_State_RecordManagement(ticket, source);
   NXS_State_Save();
}

// AUD0-PM-002 / AUD0-PM-006 — IDENTITA' E RIPETIBILITA' DELLE AZIONI.
//
// Il coordinatore usava stringhe arbitrarie fornite dal chiamante sia per la
// deduplica sia per la persistenza. Due conseguenze:
//   - rinominare una sorgente riabilitava un'azione "una tantum" gia' applicata;
//   - un'azione legittimamente RIPETIBILE (un trailing che si aggiorna a ogni
//     barra) veniva trattata come one-shot se qualcuno la registrava.
//
// Le sorgenti sono ora un contratto esplicito: quelle one-shot si applicano una
// volta sola per posizione, le altre possono ripetersi. Una sorgente ignota
// viene segnalata e trattata come RIPETIBILE (il caso conservativo per la
// gestione: meglio riapplicare un trailing che saltarlo).
// Sorgenti ONE-SHOT: hanno senso una volta sola per posizione.
bool NXS_PM_SourceIsOneShot(string source){
   return (source == "SPLIT_P1"          || source == "SPLIT_P2" ||
           source == "GLOBAL_BREAKEVEN"  || source == "PROFILE_BREAKEVEN" ||
           source == "CLASSIC_TIME_STOP" || source == "INST_TIME_STOP" ||
           source == "CLOSE_REVERSE"     || source == "FIXEDPIP_PARTIAL");
}

// Sorgenti RIPETIBILI: un trailing si aggiorna a ogni barra ed e' corretto che
// lo faccia. L'elenco completo e' il contratto delle azioni di gestione.
bool NXS_PM_SourceKnown(string source){
   if(NXS_PM_SourceIsOneShot(source)) return true;
   return (source == "ATR_TRAILING" || source == "CLASSIC_TRAIL" ||
           source == "PROFILE_TRAIL");
}

// AUD0-PM-005: stato di sovraccarico esposto, non solo un false silenzioso.
int g_nxsPmOverflow = 0;
int NXS_PM_OverflowCount(){ return g_nxsPmOverflow; }

bool NXS_PM_StopDoesNotLoosen(ulong ticket, double proposedSL){
   if(proposedSL <= 0 || !PositionSelectByTicket(ticket)) return proposedSL <= 0;
   long type = PositionGetInteger(POSITION_TYPE);
   double currentSL = PositionGetDouble(POSITION_SL);
   if(currentSL <= 0) return true;
   // NXS-PM-004: la tolleranza usava g_point, cioe' il point del simbolo del
   // GRAFICO, applicato a una posizione selezionata per ticket che puo'
   // appartenere a un altro strumento. Fra EURUSD (0.00001) e BTCUSD (0.01) la
   // differenza e' di tre ordini di grandezza: la stessa modifica veniva
   // accettata o rifiutata a caso.
   double point = SymbolInfoDouble(PositionGetString(POSITION_SYMBOL), SYMBOL_POINT);
   if(point <= 0) point = g_point;
   if(type == POSITION_TYPE_BUY) return proposedSL >= currentSL - point;
   if(type == POSITION_TYPE_SELL) return proposedSL <= currentSL + point;
   return false;
}

bool NXS_PM_Stricter(const SNXSPMProposal &candidate, const SNXSPMProposal &current){
   if(candidate.priority != current.priority) return candidate.priority > current.priority;
   if(candidate.action != current.action) return candidate.action > current.action;
   if(candidate.action == NXS_PM_MODIFY && PositionSelectByTicket(candidate.ticket)){
      long type = PositionGetInteger(POSITION_TYPE);
      if(type == POSITION_TYPE_BUY && candidate.sl != current.sl) return candidate.sl > current.sl;
      if(type == POSITION_TYPE_SELL && candidate.sl != current.sl) return candidate.sl < current.sl;
   }
   return StringCompare(candidate.source, current.source) < 0;
}

bool NXS_PM_Submit(SNXSPMProposal &proposal){
   if(proposal.ticket == 0 || proposal.action == NXS_PM_NONE) return false;
   if(proposal.action == NXS_PM_MODIFY && !NXS_PM_StopDoesNotLoosen(proposal.ticket, proposal.sl)){
      PrintFormat("[NEXUS MANAGEMENT] rejected stop regression ticket=%I64u source=%s sl=%.8f",
                  proposal.ticket, proposal.source, proposal.sl);
      return false;
   }
   for(int i=0; i<g_nxsPmBestCount; i++){
      if(g_nxsPmBest[i].ticket != proposal.ticket) continue;
      if(NXS_PM_Stricter(proposal, g_nxsPmBest[i])) g_nxsPmBest[i] = proposal;
      return true;
   }
   if(g_nxsPmBestCount >= NXS_PM_MAX_PROPOSALS){
      // AUD0-PM-005: qui si tornava false in silenzio. Una proposta di
      // CHIUSURA scartata senza traccia e' una protezione che non scatta e di
      // cui nessuno sa nulla. L'overflow e' ora contato e segnalato; per le
      // chiusure si tenta l'esecuzione IMMEDIATA invece di perderla.
      g_nxsPmOverflow++;
      PrintFormat("[NEXUS MANAGEMENT][ALERT] coda proposte piena (%d): "
                  "azione=%d ticket=%I64u source=%s scartata (overflow totale=%d)",
                  NXS_PM_MAX_PROPOSALS, (int)proposal.action, proposal.ticket,
                  proposal.source, g_nxsPmOverflow);
      if(proposal.action == NXS_PM_CLOSE){
         PrintFormat("[NEXUS MANAGEMENT] chiusura critica eseguita fuori coda: %I64u",
                     proposal.ticket);
         return NXS_DoClose(proposal.ticket);
      }
      return false;
   }
   g_nxsPmBest[g_nxsPmBestCount++] = proposal;
   return true;
}

bool NXS_PM_ProposeModify(ulong ticket, double sl, double tp, int priority,
                          string source, string reason){
   SNXSPMProposal p; p.ticket=ticket; p.action=NXS_PM_MODIFY; p.priority=priority;
   p.sl=sl; p.tp=tp; p.volume=0; p.source=source; p.reason=reason;
   return NXS_PM_Submit(p);
}

bool NXS_PM_ProposePartial(ulong ticket, double volume, int priority,
                           string source, string reason){
   // AUD0-PM-002: la deduplica si applica solo alle azioni dichiarate one-shot.
   if(NXS_PM_SourceIsOneShot(source) && NXS_PM_HasApplied(ticket, source)) return false;
   if(!NXS_PM_SourceKnown(source))
      PrintFormat("[NEXUS MANAGEMENT] sorgente '%s' non nel contratto: trattata "
                  "come ripetibile (ticket=%I64u)", source, ticket);
   SNXSPMProposal p; p.ticket=ticket; p.action=NXS_PM_PARTIAL; p.priority=priority;
   p.sl=0; p.tp=0; p.volume=volume; p.source=source; p.reason=reason;
   return NXS_PM_Submit(p);
}

bool NXS_PM_ProposeClose(ulong ticket, int priority, string source, string reason){
   SNXSPMProposal p; p.ticket=ticket; p.action=NXS_PM_CLOSE; p.priority=priority;
   p.sl=0; p.tp=0; p.volume=0; p.source=source; p.reason=reason;
   return NXS_PM_Submit(p);
}

void NXS_PM_ApplyCycle(){
   for(int i=0; i<g_nxsPmBestCount; i++){
      SNXSPMProposal p = g_nxsPmBest[i];
      if(!PositionSelectByTicket(p.ticket)) continue;
      bool ok = false;
      // NXS-PM-001 / NXS-PM-002: passo di volume, minimo e cifre di prezzo
      // vengono dal simbolo della POSIZIONE selezionata, non da quello del
      // grafico. Con una proposta su un altro strumento la normalizzazione
      // precedente produceva volumi e prezzi semplicemente sbagliati.
      string psym   = PositionGetString(POSITION_SYMBOL);
      int    pdig   = (int)SymbolInfoInteger(psym, SYMBOL_DIGITS);
      if(pdig <= 0) pdig = g_digits;

      if(p.action == NXS_PM_CLOSE) ok = NXS_DoClose(p.ticket);
      else if(p.action == NXS_PM_PARTIAL){
         double step = SymbolInfoDouble(psym, SYMBOL_VOLUME_STEP);
         double vmin = SymbolInfoDouble(psym, SYMBOL_VOLUME_MIN);
         double curV = PositionGetDouble(POSITION_VOLUME);
         if(step <= 0) step = (vmin > 0 ? vmin : 0.01);
         double vol = MathFloor(p.volume / step) * step;
         vol = NormalizeDouble(vol, 8);
         // AUD0-PM-004: si verificava solo `vol > 0`. Un volume superiore alla
         // posizione, o un residuo sotto il minimo broker, arrivava comunque al
         // broker — che lo rifiutava, oppure lasciava un residuo non tradabile.
         double residual = curV - vol;
         if(vol <= 0){
            PrintFormat("[NEXUS MANAGEMENT] parziale scartato: volume nullo dopo "
                        "normalizzazione (%s ticket=%I64u)", psym, p.ticket);
         } else if(vol > curV + 1e-9){
            PrintFormat("[NEXUS MANAGEMENT] parziale scartato: %.4f > volume "
                        "posizione %.4f (%s ticket=%I64u)", vol, curV, psym, p.ticket);
         } else if(residual > 1e-9 && vmin > 0 && residual < vmin - 1e-9){
            PrintFormat("[NEXUS MANAGEMENT] parziale scartato: residuo %.4f sotto "
                        "il minimo broker %.4f (%s ticket=%I64u)",
                        residual, vmin, psym, p.ticket);
         } else {
            ok = NXS_DoClosePartial(p.ticket, vol);
            // NXS-PM-003: "inviato" non e' "eseguito". Si verifica che il
            // volume sia davvero diminuito prima di marcare l'azione applicata:
            // altrimenti una one-shot risulterebbe consumata senza effetto.
            if(ok && PositionSelectByTicket(p.ticket)){
               double newV = PositionGetDouble(POSITION_VOLUME);
               if(newV > curV - step * 0.5){
                  PrintFormat("[NEXUS MANAGEMENT] parziale NON confermato: volume "
                              "invariato (%.4f) su %I64u", newV, p.ticket);
                  ok = false;
               }
            }
         }
      } else if(p.action == NXS_PM_MODIFY && NXS_PM_StopDoesNotLoosen(p.ticket, p.sl))
         ok = NXS_DoModify(p.ticket, NormalizeDouble(p.sl, pdig),
                                     NormalizeDouble(p.tp, pdig));
      PrintFormat("[NEXUS MANAGEMENT] {\"ticket\":\"%I64u\",\"action\":%d,\"priority\":%d,\"source\":\"%s\",\"applied\":%s,\"reason\":\"%s\"}",
                  p.ticket, (int)p.action, p.priority, _JsonEsc(p.source),
                  (ok ? "true" : "false"), _JsonEsc(p.reason));
      if(ok) NXS_PM_RecordApplied(p.ticket, p.source);
   }
   g_nxsPmBestCount = 0;
}

#endif
