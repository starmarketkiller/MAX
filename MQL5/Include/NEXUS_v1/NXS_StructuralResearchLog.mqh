//+------------------------------------------------------------------+
//| NXS_StructuralResearchLog.mqh                                     |
//| 14/09 - Causal Research Thread 2, Phase A (instrumentation only). |
//| Vedi vault "NEXUS - Causal Research Thread 2 Phase A Structural   |
//| Instrumentation" e "...Reclaim False Break Feasibility".          |
//|                                                                    |
//| Modulo SOLO diagnostico (Print/log strutturato), completamente     |
//| separato dalla logica di trading: NON genera SNXSSignal, NON apre  |
//| trade, NON modifica execution/risk/SL/TP, NON e' letto da nessuna  |
//| strategia o gate. Osserva (read-only) eventi gia' calcolati da     |
//| NXS_DetectSweepExt() (NXS_MarketAnalysis.mqh, invariato) e dalla   |
//| state machine SH_BMS_RTO (NXS_Strategies_SMC.mqh, invariata nelle  |
//| sue condizioni - solo Print aggiunti nei punti in cui lo stato e'  |
//| GIA' mutato).                                                      |
//+------------------------------------------------------------------+
#ifndef __NXS_STRUCTURAL_RESEARCH_LOG_MQH__
#define __NXS_STRUCTURAL_RESEARCH_LOG_MQH__

// Campi minimi richiesti dal task. "source" resta sempre "SNXSSweepExt" in
// questa fase: e' l'unico detector strutturale strumentato (SH_BMS_RTO ne
// e' un CONSUMER, non una fonte di livello indipendente).
struct SNXSStructuralEvent {
   long            event_id;
   string          structural_level_id;
   datetime        timestamp;
   string          event_type;          // "SWEEP" | "TRUE_BREAK" | "RETEST" | "INVALIDATE"
   string          source;              // "SNXSSweepExt"
   ENUM_TIMEFRAMES source_tf;
   string          side;                // sw.levelTag: "Daily-High","Asia-Low",...
   ENUM_NXS_DIR    direction;
   double          level_price;
   double          price_at_event;
   double          penetration_pips;
   datetime        created_time;        // 0 = NOT_CAUSALLY_RECOVERABLE (vedi Equal-High/Low)
   double          age_seconds;         // -1 = non definibile
   string          state_before;
   string          state_after;
   string          regime_at_event;     // NXS_DetectRegime(), read-only
   string          structure_trend_at_event;   // g_struct.trend, read-only
   string          consumer;            // "SH_BMS_RTO" in questa fase
};

SNXSStructuralEvent g_nxsStructEvents[];
int                 g_nxsStructEventCount = 0;
long                g_nxsStructEventIdSeq = 0;
long                g_nxsStructDuplicatesSuppressed = 0;

void _NXS_Struct_EnsureCapacity(){
   int cap = ArraySize(g_nxsStructEvents);
   if(g_nxsStructEventCount >= cap){
      int newCap = (cap == 0) ? 128 : cap * 2;
      ArrayResize(g_nxsStructEvents, newCap);
   }
}

// Deriva un id persistente e deterministico dal riferimento sweepato.
// Daily/Weekly/Monthly: ancorato all'apertura del periodo PRECEDENTE (stesso
// shift=1 gia' usato internamente da NXS_DetectSweepExt per calcolare
// pdh/pwh/pmh), quindi identico per costruzione a cio' che il detector ha
// davvero usato. Asia: ancorato alla data del giorno corrente (il detector
// scansiona "le ultime 24h", non un vero range di calendario fisso - stesso
// limite gia' presente nel detector, non introdotto qui). Equal-High/Low:
// NESSUN periodo di calendario pulito esiste per un cluster di 2+ swing -
// usato il timestamp del bar sweepato stesso (data+minuti) come discriminante,
// dichiarato esplicitamente come convenzione diversa dagli altri tag.
string _NXS_Structural_ComputeLevelId(SNXSSweepExt &sw, ENUM_TIMEFRAMES tf){
   datetime anchor;
   bool fullTimestamp = false;
   string tag = (sw.levelTag != "") ? sw.levelTag : "Unknown";
   if(tag == "Daily-High" || tag == "Daily-Low")           anchor = iTime(g_sym, PERIOD_D1, 1);
   else if(tag == "Weekly-High" || tag == "Weekly-Low")    anchor = iTime(g_sym, PERIOD_W1, 1);
   else if(tag == "Monthly-High" || tag == "Monthly-Low")  anchor = iTime(g_sym, PERIOD_MN1, 1);
   else if(tag == "Asia-High" || tag == "Asia-Low")        anchor = iTime(g_sym, PERIOD_D1, 0);
   else { anchor = iTime(g_sym, tf, 1); fullTimestamp = true; }
   string dateStr = fullTimestamp ? TimeToString(anchor, TIME_DATE|TIME_MINUTES) : TimeToString(anchor, TIME_DATE);
   return tag + "_" + dateStr;
}

// created_time coerente con l'anchor sopra - 0 solo per Equal-High/Low, dove
// non esiste un istante di creazione causalmente pulito (un cluster di 2+
// swing non "nasce" in un momento unico).
datetime _NXS_Structural_CreatedTime(SNXSSweepExt &sw, ENUM_TIMEFRAMES tf){
   string tag = (sw.levelTag != "") ? sw.levelTag : "Unknown";
   if(tag == "Daily-High" || tag == "Daily-Low")           return iTime(g_sym, PERIOD_D1, 1);
   if(tag == "Weekly-High" || tag == "Weekly-Low")         return iTime(g_sym, PERIOD_W1, 1);
   if(tag == "Monthly-High" || tag == "Monthly-Low")       return iTime(g_sym, PERIOD_MN1, 1);
   if(tag == "Asia-High" || tag == "Asia-Low")             return iTime(g_sym, PERIOD_D1, 0);
   return 0;   // Equal-High/Equal-Low: NOT_CAUSALLY_RECOVERABLE
}

string _NXS_Structural_RegimeSnapshot(){
   return NXS_RegimeName(NXS_DetectRegime());
}

string _NXS_Structural_TrendSnapshot(){
   if(g_struct.trend > 0) return "UP";
   if(g_struct.trend < 0) return "DOWN";
   return "RANGE";
}

// Deduplicazione: un evento (structural_level_id, event_type, timestamp di
// barra) gia' presente nel log NON viene riscritto. Questo copre sia il
// caso "stesso detector richiamato piu' volte nello stesso bar/tick" sia il
// caso "piu' passaggi multi-TF rivalutano la stessa barra chiusa" - nessuna
// assunzione su QUALE meccanismo produce la ripetizione, solo sul fatto che
// (id, tipo, timestamp) identico = stesso evento reale, mai un secondo
// evento genuino. Occorrenze successive dello STESSO id in un momento
// diverso (es. lo stesso Daily-High swept di nuovo su una barra successiva)
// restano invece eventi distinti e vengono loggate normalmente.
bool _NXS_Struct_IsDuplicate(string level_id, string event_type, datetime ts){
   for(int i = g_nxsStructEventCount - 1; i >= 0; i--){
      if(g_nxsStructEvents[i].timestamp != ts) continue;
      if(g_nxsStructEvents[i].event_type != event_type) continue;
      if(g_nxsStructEvents[i].structural_level_id != level_id) continue;
      return true;
   }
   return false;
}

void _NXS_Struct_LogEvent(string level_id, datetime ts, string event_type, ENUM_TIMEFRAMES tf,
                           string side, ENUM_NXS_DIR dir, double levelPrice, double priceAtEvent,
                           datetime createdTime, string stateBefore, string stateAfter, string consumer){
   if(!InpStructuralResearchEventLog) return;
   if(_NXS_Struct_IsDuplicate(level_id, event_type, ts)){
      g_nxsStructDuplicatesSuppressed++;
      return;
   }
   _NXS_Struct_EnsureCapacity();
   double pip = 10.0 * g_profile.pipSize;
   SNXSStructuralEvent ev;
   ev.event_id = ++g_nxsStructEventIdSeq;
   ev.structural_level_id = level_id;
   ev.timestamp = ts;
   ev.event_type = event_type;
   ev.source = "SNXSSweepExt";
   ev.source_tf = tf;
   ev.side = side;
   ev.direction = dir;
   ev.level_price = levelPrice;
   ev.price_at_event = priceAtEvent;
   ev.penetration_pips = (pip > 0) ? MathAbs(priceAtEvent - levelPrice) / pip : 0;
   ev.created_time = createdTime;
   ev.age_seconds = (createdTime > 0 && createdTime <= ts) ? (double)(ts - createdTime) : -1;
   ev.state_before = stateBefore;
   ev.state_after = stateAfter;
   ev.regime_at_event = _NXS_Structural_RegimeSnapshot();
   ev.structure_trend_at_event = _NXS_Structural_TrendSnapshot();
   ev.consumer = consumer;
   g_nxsStructEvents[g_nxsStructEventCount] = ev;
   g_nxsStructEventCount++;
   PrintFormat("[STRUCTLOG][EVENT] event_id=%d level_id=%s type=%s side=%s dir=%d level=%.2f price=%.2f "
               "pen_pips=%.2f age_s=%.0f state=%s->%s regime=%s trend=%s consumer=%s time=%s",
               ev.event_id, ev.structural_level_id, ev.event_type, ev.side, (int)ev.direction,
               ev.level_price, ev.price_at_event, ev.penetration_pips, ev.age_seconds,
               ev.state_before, ev.state_after, ev.regime_at_event, ev.structure_trend_at_event,
               ev.consumer, TimeToString(ev.timestamp, TIME_DATE|TIME_SECONDS));
}

// Chiamata dal punto causale esatto in cui SH_BMS_RTO osserva `sw.confirmed`
// per la prima volta (transizione IDLE->SWEPT, NXS_Strategies_SMC.mqh) - MAI
// una decisione nuova, solo l'osservazione di un dato gia' calcolato da
// NXS_DetectSweepExt() (chiamata dal chiamante, non qui).
void NXS_Structural_OnSweepObserved(SNXSSweepExt &sw, ENUM_TIMEFRAMES tf, datetime barTs,
                                     string consumer, string &outLevelId){
   outLevelId = _NXS_Structural_ComputeLevelId(sw, tf);
   if(!InpStructuralResearchEventLog) return;
   double c1 = iClose(g_sym, tf, 1);
   datetime created = _NXS_Structural_CreatedTime(sw, tf);
   _NXS_Struct_LogEvent(outLevelId, barTs, "SWEEP", tf, sw.levelTag, sw.dir, sw.level, c1,
                        created, "IDLE", "SWEPT", consumer);
}

void NXS_Structural_OnTrueBreak(string level_id, ENUM_TIMEFRAMES tf, datetime barTs, string side,
                                 ENUM_NXS_DIR dir, double levelPrice, string consumer){
   double c1 = iClose(g_sym, tf, 1);
   _NXS_Struct_LogEvent(level_id, barTs, "TRUE_BREAK", tf, side, dir, levelPrice, c1,
                        0, "SWEPT", "WAITING_RETURN", consumer);
}

void NXS_Structural_OnRetest(string level_id, ENUM_TIMEFRAMES tf, datetime barTs, string side,
                              ENUM_NXS_DIR dir, double levelPrice, double priceAtEvent, string consumer){
   _NXS_Struct_LogEvent(level_id, barTs, "RETEST", tf, side, dir, levelPrice, priceAtEvent,
                        0, "WAITING_RETURN", "CONSUMED", consumer);
}

void NXS_Structural_OnInvalidate(string level_id, ENUM_TIMEFRAMES tf, datetime barTs, string side,
                                  ENUM_NXS_DIR dir, double levelPrice, string stateBefore, string consumer){
   double c1 = iClose(g_sym, tf, 1);
   _NXS_Struct_LogEvent(level_id, barTs, "INVALIDATE", tf, side, dir, levelPrice, c1,
                        0, stateBefore, "IDLE", consumer);
}

void NXS_Structural_PrintSummary(){
   if(!InpStructuralResearchEventLog) return;
   int sweeps = 0, breaks = 0, retests = 0, invalidations = 0;
   for(int i = 0; i < g_nxsStructEventCount; i++){
      if(g_nxsStructEvents[i].event_type == "SWEEP") sweeps++;
      else if(g_nxsStructEvents[i].event_type == "TRUE_BREAK") breaks++;
      else if(g_nxsStructEvents[i].event_type == "RETEST") retests++;
      else if(g_nxsStructEvents[i].event_type == "INVALIDATE") invalidations++;
   }
   // livelli unici = structural_level_id distinti fra gli eventi SWEEP
   string seen[]; int seenCount = 0;
   ArrayResize(seen, g_nxsStructEventCount);
   for(int i = 0; i < g_nxsStructEventCount; i++){
      if(g_nxsStructEvents[i].event_type != "SWEEP") continue;
      bool dup = false;
      for(int k = 0; k < seenCount; k++) if(seen[k] == g_nxsStructEvents[i].structural_level_id){ dup = true; break; }
      if(!dup){ seen[seenCount++] = g_nxsStructEvents[i].structural_level_id; }
   }
   PrintFormat("[STRUCTLOG][SUMMARY] total_events=%d sweeps=%d true_breaks=%d retests=%d invalidations=%d "
               "unique_structural_levels=%d duplicates_suppressed=%d",
               g_nxsStructEventCount, sweeps, breaks, retests, invalidations, seenCount,
               g_nxsStructDuplicatesSuppressed);
}

#endif
