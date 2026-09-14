//+------------------------------------------------------------------+
//| NXS_ReactionEngine.mqh                                            |
//| 13/09 - Unified Level/Reaction Engine, Phase A (telemetry-only).  |
//| Vedi vault "NEXUS - Unified Structure Level Reaction Engine       |
//| Migration Plan v1" e "NEXUS - Unified Level Engine Phase A WICK   |
//| Telemetry Shadow".                                                |
//|                                                                    |
//| Riceve gli stessi eventi gia' calcolati dal vecchio WICK (mai      |
//| ricalcolati qui), li registra come SNXSReactionEvent e aggiorna il |
//| livello corrispondente in NXS_LevelRegistry.mqh. Non genera        |
//| SNXSSignal, non apre trade, non e' letto da nessuna strategia.     |
//|                                                                    |
//| Include anche il parity report old-vs-new (estende, non sostituisce|
//| NXS_WickShadow_PrintSummary): confronta i contatori qui accumulati |
//| con g_wickFunnel/g_wickReclaimFunnel (contatori indipendenti gia'  |
//| esistenti, calcolati dal vecchio codice PRIMA di questo modulo).   |
//+------------------------------------------------------------------+
#ifndef __NXS_REACTION_ENGINE_MQH__
#define __NXS_REACTION_ENGINE_MQH__

enum ENUM_NXS_REACTION_TYPE_A {
   NXS_REACT_CREATE_A = 0,   // Phase B - aggiunto per completare il log evento-per-evento su levels_created
   NXS_REACT_TOUCH_A,
   NXS_REACT_SWEEP_A,
   NXS_REACT_RECLAIM_A,
   NXS_REACT_INVALIDATE_A,
   NXS_REACT_CONSUME_A
};

// Campi minimi richiesti dal task + source_strategy (necessario per
// separare, nel parity report, i due path canonici indipendenti che
// possono osservare lo stesso livello: WICK_SWEEP_REV e
// WICK_SWEEP_RECLAIM - senza questo campo i due sweep count non sarebbero
// distinguibili nell'evento).
struct SNXSReactionEvent {
   long                     event_id;
   long                     level_id;
   datetime                 timestamp;
   ENUM_NXS_REACTION_TYPE_A type;
   ENUM_NXS_DIR             direction;
   double                   penetration;   // pip, 0 se non applicabile (touch/reclaim/invalidate/consume)
   bool                     reclaim;
   ENUM_TIMEFRAMES          source_tf;
   string                   source_strategy;
   string                   reason;        // libero, solo per invalidate ("price_returned"/"level_replaced") - diagnostico, non usato da alcuna decisione
};

SNXSReactionEvent g_nxsReactionLog[];
int               g_nxsReactionLogCount = 0;
long              g_nxsReactionEventIdSeq = 0;

// Contatori paralleli, accumulati SOLO da questo modulo, mai letti dal
// vecchio codice - servono esclusivamente al parity report sotto.
struct SNXSWickParityCounters {
   long levelsCreated;
   long levelsReplaced;
   long touches;
   long sweepsRev;
   long sweepsReclaim;
   long reclaims;
   long invalidatedByPrice;
   long invalidatedByReplacement;
   long consumedRev;
   long consumedReclaim;
};
SNXSWickParityCounters g_nxsWickParity;

void _NXS_LevelReg_EnsureReactionCapacity(){
   int cap = ArraySize(g_nxsReactionLog);
   if(g_nxsReactionLogCount >= cap){
      int newCap = (cap == 0) ? 256 : cap * 2;
      ArrayResize(g_nxsReactionLog, newCap);
   }
}

string _NXS_ReactionTypeStr(ENUM_NXS_REACTION_TYPE_A t){
   switch(t){
      case NXS_REACT_CREATE_A:     return "CREATE";
      case NXS_REACT_TOUCH_A:      return "TOUCH";
      case NXS_REACT_SWEEP_A:      return "SWEEP";
      case NXS_REACT_RECLAIM_A:    return "RECLAIM";
      case NXS_REACT_INVALIDATE_A: return "INVALIDATE";
      case NXS_REACT_CONSUME_A:    return "CONSUME";
   }
   return "UNKNOWN";
}

void _NXS_Reaction_Emit(long level_id, ENUM_NXS_REACTION_TYPE_A rtype, ENUM_NXS_DIR direction,
                         double penetration, bool reclaim, datetime t,
                         ENUM_TIMEFRAMES source_tf, string source_strategy, string reason){
   _NXS_LevelReg_EnsureReactionCapacity();
   SNXSReactionEvent ev;
   ev.event_id = ++g_nxsReactionEventIdSeq;
   ev.level_id = level_id;
   ev.timestamp = t;
   ev.type = rtype;
   ev.direction = direction;
   ev.penetration = penetration;
   ev.reclaim = reclaim;
   ev.source_tf = source_tf;
   ev.source_strategy = source_strategy;
   ev.reason = reason;
   // Phase B - log per-evento per il confronto old-vs-new evento-per-evento
   // (mai letto da nessuna strategia, solo diagnostica). Gate dedicato,
   // default OFF: non e' pensato per girare sempre (volume di log), solo
   // durante le run di validazione.
   if(InpLevelRegistry_WickEventLog){
      int idx = _NXS_LevelReg_Find(level_id);
      string sideLbl = (idx >= 0) ? g_nxsLevelReg[idx].side : "?";
      // Causal Experiment 1 (14/09) - aggiunto "price" (prezzo del livello,
      // gia' presente nel registro, mai stato stampato) e "touch_count"
      // (gia' presente nel registro): servono a ricostruire entry_ref e
      // touch_count_before_sweep nel dataset di ricerca senza ricalcolare
      // nulla ex-post - sono valori GIA' scritti da hook causali esistenti,
      // qui solo esposti in stampa. Nessuna nuova decisione, nessun nuovo
      // hook di scrittura.
      double lvlPrice = (idx >= 0) ? g_nxsLevelReg[idx].price : 0.0;
      int touchCount = (idx >= 0) ? g_nxsLevelReg[idx].touch_count : 0;
      PrintFormat("[LEVELENGINE][EVENT] event_id=%d level_id=%d type=%s side=%s dir=%d price=%.2f pen=%.2f "
                  "touch_count=%d reclaim=%s tf=%s strat=%s time=%s reason=%s",
                  ev.event_id, ev.level_id, _NXS_ReactionTypeStr(ev.type), sideLbl, (int)ev.direction,
                  lvlPrice, ev.penetration, touchCount, (ev.reclaim ? "true" : "false"), EnumToString(ev.source_tf),
                  ev.source_strategy, TimeToString(ev.timestamp, TIME_DATE|TIME_SECONDS), ev.reason);
   }
   g_nxsReactionLog[g_nxsReactionLogCount] = ev;
   g_nxsReactionLogCount++;
}

// --- Hook chiamati da NXS_Strategies_Experimental.mqh, uno per famiglia di evento causale ---
// Ogni funzione e' chiamata SOLO dal punto esatto in cui il vecchio stato
// (SNxsWickSide / SNxsWickReclaimState) e' GIA' stato mutato dal codice
// esistente - vedi "Causal hook requirement" nel report Phase A per
// l'elenco file:riga di ogni call site.

void NXS_Reaction_OnLevelCreated(long level_id, string side, ENUM_NXS_DIR direction,
                                  double price, datetime created_time, ENUM_TIMEFRAMES source_tf){
   NXS_LevelReg_Create(level_id, side, direction, price, created_time, source_tf);
   g_nxsWickParity.levelsCreated++;
   _NXS_Reaction_Emit(level_id, NXS_REACT_CREATE_A, direction, 0, false, created_time, source_tf, "", "");
}

void NXS_Reaction_OnLevelReplaced(long old_level_id, ENUM_NXS_DIR direction, ENUM_TIMEFRAMES source_tf, datetime t){
   NXS_LevelReg_SetInvalidated(old_level_id, true);
   g_nxsWickParity.levelsReplaced++;
   _NXS_Reaction_Emit(old_level_id, NXS_REACT_INVALIDATE_A, direction, 0, false, t, source_tf, "", "level_replaced_by_new_wick");
}

void NXS_Reaction_OnTouch(long level_id, ENUM_NXS_DIR direction, ENUM_TIMEFRAMES source_tf, datetime t){
   NXS_LevelReg_SetTouched(level_id, t);
   g_nxsWickParity.touches++;
   _NXS_Reaction_Emit(level_id, NXS_REACT_TOUCH_A, direction, 0, false, t, source_tf, "", "");
}

void NXS_Reaction_OnSweep(long level_id, ENUM_NXS_DIR direction, double penetration_pips,
                           ENUM_TIMEFRAMES source_tf, datetime t, string source_strategy){
   NXS_LevelReg_SetSwept(level_id, source_strategy, penetration_pips);
   if(source_strategy == "WICK_SWEEP_REV") g_nxsWickParity.sweepsRev++;
   else if(source_strategy == "WICK_SWEEP_RECLAIM") g_nxsWickParity.sweepsReclaim++;
   _NXS_Reaction_Emit(level_id, NXS_REACT_SWEEP_A, direction, penetration_pips, false, t, source_tf, source_strategy, "");
}

void NXS_Reaction_OnReclaim(long level_id, ENUM_NXS_DIR direction, ENUM_TIMEFRAMES source_tf,
                             datetime t, string source_strategy){
   NXS_LevelReg_SetReclaimed(level_id, t);
   g_nxsWickParity.reclaims++;
   _NXS_Reaction_Emit(level_id, NXS_REACT_RECLAIM_A, direction, 0, true, t, source_tf, source_strategy, "");
}

void NXS_Reaction_OnInvalidated(long level_id, ENUM_NXS_DIR direction, ENUM_TIMEFRAMES source_tf,
                                 datetime t, string source_strategy, string reason){
   NXS_LevelReg_SetInvalidated(level_id, false);
   if(reason == "price_returned_before_consumption") g_nxsWickParity.invalidatedByPrice++;
   else                                               g_nxsWickParity.invalidatedByReplacement++;
   _NXS_Reaction_Emit(level_id, NXS_REACT_INVALIDATE_A, direction, 0, false, t, source_tf, source_strategy, reason);
}

void NXS_Reaction_OnConsumed(long level_id, ENUM_NXS_DIR direction, ENUM_TIMEFRAMES source_tf,
                              datetime t, string source_strategy){
   NXS_LevelReg_SetConsumed(level_id, source_strategy);
   if(source_strategy == "WICK_SWEEP_REV") g_nxsWickParity.consumedRev++;
   else if(source_strategy == "WICK_SWEEP_RECLAIM") g_nxsWickParity.consumedReclaim++;
   _NXS_Reaction_Emit(level_id, NXS_REACT_CONSUME_A, direction, 0, false, t, source_tf, source_strategy, "");
}

// --- Parity report old-vs-new ------------------------------------------------
// Ogni riga confronta un contatore del vecchio motore (gia' esistente,
// calcolato indipendentemente da questo modulo) con l'equivalente
// accumulato qui, e classifica esplicitamente il mismatch (non solo lo
// conta). Chiamata da OnDeinit, stesso punto di NXS_WickShadow_PrintSummary/
// NXS_WickReclaim_PrintFunnel.
void _NXS_Parity_Line(string label, long oldVal, long newVal, string mismatchHint){
   if(oldVal == newVal){
      PrintFormat("[LEVELENGINE][PARITY] %-28s old=%-6d new=%-6d PASS", label, oldVal, newVal);
   } else {
      PrintFormat("[LEVELENGINE][PARITY] %-28s old=%-6d new=%-6d MISMATCH delta=%d possible_cause=%s",
                  label, oldVal, newVal, (int)(newVal - oldVal), mismatchHint);
   }
}

void NXS_LevelEngine_PrintWickParity(){
   if(!InpLevelRegistry_WickTelemetry) return;
   if(!InpStrat_WickSweep && !InpStrat_WickSweepReclaim){
      Print("[LEVELENGINE][PARITY] skipped: ne' WICK_SWEEP_REV ne' WICK_SWEEP_RECLAIM erano attivi in questo run");
      return;
   }
   Print("[LEVELENGINE][PARITY] === WICK old-vs-new (Fase A, telemetry-only) ===");
   _NXS_Parity_Line("levels_created", g_wickFunnel.levelsCreated, g_nxsWickParity.levelsCreated,
                     "hook mancante in _NXS_WickSweep_UpdateLevel o ArrayResize fallito");
   _NXS_Parity_Line("levels_replaced", g_wickFunnel.levelsReplacedUnused, g_nxsWickParity.levelsReplaced,
                     "hook di replacement non allineato alla condizione level>0&&!consumed");
   _NXS_Parity_Line("sweeps_REV", g_wickFunnel.sweepsDetected, g_nxsWickParity.sweepsRev,
                     "hook sweep in NXS_Strat_WickSweepReversal non allineato a firstTrigger");
   _NXS_Parity_Line("sweeps_RECLAIM(armed)", g_wickReclaimFunnel.armed, g_nxsWickParity.sweepsReclaim,
                     "hook ARMED in _NXS_WickReclaim_ProcessSide non allineato al blocco WR_IDLE->WR_ARMED");
   _NXS_Parity_Line("reclaims", g_wickReclaimFunnel.reclaimAvailable, g_nxsWickParity.reclaims,
                     "hook RECLAIM_AVAILABLE non allineato al blocco WR_ARMED->WR_RECLAIMED");
   _NXS_Parity_Line("invalidated_by_price", g_wickFunnel.levelsInvalidatedByPrice, g_nxsWickParity.invalidatedByPrice,
                     "hook invalidazione REV non allineato al branch 'triggered && prezzo rientrato'");
   _NXS_Parity_Line("invalidated_by_replacement(abandoned)", g_wickReclaimFunnel.abandoned, g_nxsWickParity.invalidatedByReplacement,
                     "hook ABANDONED non allineato alla guardia state!=WR_OPENED");
   _NXS_Parity_Line("consumed_REV", g_wickFunnel.entryOpened, g_nxsWickParity.consumedRev,
                     "hook consumed in _NXS_WickSweep_FinalizeSide non allineato a opened==true");
   _NXS_Parity_Line("consumed_RECLAIM", g_wickReclaimFunnel.entryOpened, g_nxsWickParity.consumedReclaim,
                     "hook consumed in NXS_WickReclaim_OnExecuteResult non allineato a opened==true");
   PrintFormat("[LEVELENGINE][PARITY] levels_in_registry=%d reaction_events_logged=%d",
               g_nxsLevelRegCount, g_nxsReactionLogCount);
   Print("[LEVELENGINE][PARITY] nota: timestamp/prezzo/lato di ogni singolo evento sono identici per "
         "costruzione (l'hook legge gli STESSI valori appena calcolati dal vecchio codice, nello stesso "
         "punto causale - il confronto sopra verifica che NESSUN hook sia mancante o duplicato, non una "
         "seconda implementazione indipendente che potrebbe divergere per prezzo/tempo).");
}

// === Fase C - Dual-decision comparator (WICK_SWEEP_REV read-path) ==========
// Confronta la decisione legacy (SEMPRE calcolata, write path sempre ON)
// con quella derivata leggendo il nuovo registro. Non decide nulla da
// solo: il chiamante (NXS_Strategies_Experimental.mqh) decide quale
// decisione restituire in base a InpLevelRegistry_WickReadPath e
// all'esito di questo confronto (fail-safe: mismatch -> legacy sempre).
long g_nxsWickReadPathChecks = 0;
long g_nxsWickReadPathMismatches = 0;

bool NXS_WickReadPath_Compare(bool legacyHasSignal, const SNXSSignal &legacyDecision, long legacyLevelId,
                               bool newHasSignal, const SNXSSignal &newDecision, long newLevelId){
   g_nxsWickReadPathChecks++;
   double tol = 10 * _Point;   // tolleranza difensiva; a parita' di bid/ask/formula il valore atteso e' 0
   bool match = true;
   string field = "";

   if(legacyHasSignal != newHasSignal){ match = false; field = "should_trade"; }
   else if(legacyHasSignal && newHasSignal){
      if(legacyDecision.dir != newDecision.dir){ match = false; field = "direction"; }
      else if(legacyLevelId != newLevelId){ match = false; field = "level_id"; }
      else if(MathAbs(legacyDecision.entryRef - newDecision.entryRef) > tol){ match = false; field = "trigger_price"; }
      else if(MathAbs(legacyDecision.slPrice - newDecision.slPrice) > tol){ match = false; field = "sl"; }
      else if(MathAbs(legacyDecision.tpPrice - newDecision.tpPrice) > tol){ match = false; field = "tp"; }
   }

   if(!match){
      g_nxsWickReadPathMismatches++;
      PrintFormat("[LEVELENGINE][DECISION_MISMATCH] field=%s time=%s | "
                  "legacy(should_trade=%s dir=%d level_id=%d trigger=%.5f sl=%.5f tp=%.5f) | "
                  "new(should_trade=%s dir=%d level_id=%d trigger=%.5f sl=%.5f tp=%.5f)",
                  field, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
                  (legacyHasSignal?"true":"false"), (int)legacyDecision.dir, (int)legacyLevelId,
                  legacyDecision.entryRef, legacyDecision.slPrice, legacyDecision.tpPrice,
                  (newHasSignal?"true":"false"), (int)newDecision.dir, (int)newLevelId,
                  newDecision.entryRef, newDecision.slPrice, newDecision.tpPrice);
   }
   return match;
}

void NXS_LevelEngine_PrintReadPathSummary(){
   if(!InpLevelRegistry_WickTelemetry || !InpStrat_WickSweep) return;
   PrintFormat("[LEVELENGINE][READPATH] enabled=%s checks=%d mismatches=%d",
               (InpLevelRegistry_WickReadPath?"true":"false"),
               g_nxsWickReadPathChecks, g_nxsWickReadPathMismatches);
}

// === Fase D - State-consistency check =======================================
// Diagnostica pura (solo Print, nessuna mutazione, nessuna decisione): a fine
// run confronta lo stato FINALE legacy (g_wickHigh/g_wickLow) con la voce
// corrispondente nel registro per lo stesso level_id, e scansiona l'intero
// registro per verificare che nessun livello "vecchio" (sostituito) sia
// rimasto in uno stato non-terminale (cioe' apparentemente ancora attivo pur
// non essendo piu' il livello corrente per quel lato).
void NXS_LevelEngine_PrintStateConsistency(){
   if(!InpLevelRegistry_WickTelemetry || !InpStrat_WickSweep) return;

   int fieldMismatches = 0;

   long highId = g_wickHigh.id;
   int idxHigh = _NXS_LevelReg_Find(highId);
   bool legacyHighInvalidated = (g_wickHigh.level <= 0);
   if(highId != 0){
      if(idxHigh < 0){
         fieldMismatches++;
         PrintFormat("[LEVELENGINE][STATE_CHECK] MISMATCH side=HIGH level_id=%d field=existence legacy=present unified=absent", highId);
      } else {
         if(g_nxsLevelReg[idxHigh].consumed != g_wickHigh.consumed){
            fieldMismatches++;
            PrintFormat("[LEVELENGINE][STATE_CHECK] MISMATCH side=HIGH level_id=%d field=consumed legacy=%s unified=%s",
                        highId, (g_wickHigh.consumed?"true":"false"), (g_nxsLevelReg[idxHigh].consumed?"true":"false"));
         }
         if(g_nxsLevelReg[idxHigh].invalidated != legacyHighInvalidated){
            fieldMismatches++;
            PrintFormat("[LEVELENGINE][STATE_CHECK] MISMATCH side=HIGH level_id=%d field=invalidated legacy=%s unified=%s",
                        highId, (legacyHighInvalidated?"true":"false"), (g_nxsLevelReg[idxHigh].invalidated?"true":"false"));
         }
         if(g_nxsLevelReg[idxHigh].last_attempt_bar != g_wickHigh.lastAttemptBar){
            fieldMismatches++;
            PrintFormat("[LEVELENGINE][STATE_CHECK] MISMATCH side=HIGH level_id=%d field=last_attempt_bar legacy=%s unified=%s",
                        highId, TimeToString(g_wickHigh.lastAttemptBar), TimeToString(g_nxsLevelReg[idxHigh].last_attempt_bar));
         }
      }
   }

   long lowId = g_wickLow.id;
   int idxLow = _NXS_LevelReg_Find(lowId);
   bool legacyLowInvalidated = (g_wickLow.level <= 0);
   if(lowId != 0){
      if(idxLow < 0){
         fieldMismatches++;
         PrintFormat("[LEVELENGINE][STATE_CHECK] MISMATCH side=LOW level_id=%d field=existence legacy=present unified=absent", lowId);
      } else {
         if(g_nxsLevelReg[idxLow].consumed != g_wickLow.consumed){
            fieldMismatches++;
            PrintFormat("[LEVELENGINE][STATE_CHECK] MISMATCH side=LOW level_id=%d field=consumed legacy=%s unified=%s",
                        lowId, (g_wickLow.consumed?"true":"false"), (g_nxsLevelReg[idxLow].consumed?"true":"false"));
         }
         if(g_nxsLevelReg[idxLow].invalidated != legacyLowInvalidated){
            fieldMismatches++;
            PrintFormat("[LEVELENGINE][STATE_CHECK] MISMATCH side=LOW level_id=%d field=invalidated legacy=%s unified=%s",
                        lowId, (legacyLowInvalidated?"true":"false"), (g_nxsLevelReg[idxLow].invalidated?"true":"false"));
         }
         if(g_nxsLevelReg[idxLow].last_attempt_bar != g_wickLow.lastAttemptBar){
            fieldMismatches++;
            PrintFormat("[LEVELENGINE][STATE_CHECK] MISMATCH side=LOW level_id=%d field=last_attempt_bar legacy=%s unified=%s",
                        lowId, TimeToString(g_wickLow.lastAttemptBar), TimeToString(g_nxsLevelReg[idxLow].last_attempt_bar));
         }
      }
   }

   // Nessun livello "vecchio" (sostituito) deve restare non-terminale: ogni
   // voce del registro che non e' l'id corrente del proprio lato deve essere
   // invalidated o consumed (il replacement lifecycle lo garantisce via
   // NXS_Reaction_OnLevelReplaced - qui lo si verifica, non lo si impone).
   int staleActive = 0;
   for(int i = 0; i < g_nxsLevelRegCount; i++){
      bool isCurrent = (g_nxsLevelReg[i].level_id == highId) || (g_nxsLevelReg[i].level_id == lowId);
      if(isCurrent) continue;
      if(!g_nxsLevelReg[i].invalidated && !g_nxsLevelReg[i].consumed){
         staleActive++;
         PrintFormat("[LEVELENGINE][STATE_CHECK] STALE level_id=%d side=%s state_non_terminal=true (sostituito ma non invalidato/consumato)",
                     g_nxsLevelReg[i].level_id, g_nxsLevelReg[i].side);
      }
   }

   PrintFormat("[LEVELENGINE][STATE_CHECK] summary field_mismatches=%d stale_active_levels=%d total_levels=%d",
               fieldMismatches, staleActive, g_nxsLevelRegCount);
}

#endif
