//+------------------------------------------------------------------+
//| NXS_StructuralResearchLog.mqh                                     |
//| 14/09 - Causal Research Thread 2, Phase A (instrumentation only). |
//| 14/09 - Fase A.1: SWEEP canonicalizzato come sorgente condivisa    |
//| indipendente dal consumer (vedi vault "...Phase A1 Shared Sweep   |
//| Instrumentation"). TRUE_BREAK/RETEST/INVALIDATE restano invariati  |
//| e legati a SH_BMS_RTO (lifecycle-specific, non un source event).   |
//| Vedi anche vault "...Phase A Structural Instrumentation" e         |
//| "...Reclaim False Break Feasibility".                              |
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
// questa fase: e' l'unico detector strutturale strumentato. "consumer" per
// un evento SWEEP e' ora il PRIMO osservatore che lo ha reso canonico
// (spesso il punto centrale in NXS_CollectAllSignals); "observed_by" elenca
// TUTTI i consumer che lo hanno successivamente osservato senza duplicarlo.
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
   double          atr_at_event;        // 14/09 - Fase B: g_atr read-only, snapshot per label ATR-based
   string          consumer;            // primo osservatore (solo SWEEP: sorgente canonica)
   string          observed_by;         // SOLO SWEEP: lista "|Nome1|Nome2|" dei consumer osservanti -
                                         // delimitatore "|" (non ",") perche' FileWrite(FILE_CSV) non
                                         // quota i campi contenenti il delimitatore CSV stesso (14/09,
                                         // Fase B - bug scoperto nel parsing del primo export)
   int             observation_count;   // SOLO SWEEP: quante volte e' stato osservato in totale
   int             sh_bms_episode_seq;  // [Phase C - Sample Recovery] SNXSSHBmsState.episodeSeq quando
                                         // il chiamante e' SH_BMS_RTO - 0 = non applicabile/non ancora
                                         // osservato da SH_BMS_RTO. Identita' REALE dell'episodio dal
                                         // punto di vista della macchina a stati (mai ricostruita a
                                         // posteriori da event_id/observed_by). Vedi vault "NEXUS -
                                         // Structural Lifecycle Sample Recovery".
};

SNXSStructuralEvent g_nxsStructEvents[];
int                 g_nxsStructEventCount = 0;
long                g_nxsStructEventIdSeq = 0;
// Lifecycle (TRUE_BREAK/RETEST/INVALIDATE): un solo scrittore (SH_BMS_RTO),
// dedup identico alla Fase A, nessun concetto di cross-consumer necessario qui.
long                g_nxsLifecycleDuplicatesSuppressed = 0;
// SWEEP (fonte condivisa): tre contatori distinti richiesti dalla Fase A.1.
long                g_nxsSweepRawObservations   = 0;   // ogni chiamata con sw.confirmed, ON
long                g_nxsSweepUniqueEvents      = 0;   // nuovi eventi canonici scritti
long                g_nxsSweepMultipassDup      = 0;   // stesso consumer, stesso (level,bar) gia' visto
long                g_nxsSweepCrossConsumerDup  = 0;   // consumer DIVERSO sullo stesso (level,bar) gia' visto
long                g_nxsSweepMalformedSkipped  = 0;   // confirmed=true ma dir/level/levelTag incoerenti - scartato

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

// Deduplicazione LIFECYCLE (TRUE_BREAK/RETEST/INVALIDATE): un evento
// (structural_level_id, event_type, timestamp di barra) gia' presente nel
// log NON viene riscritto. Un solo scrittore (SH_BMS_RTO) in questa fase,
// quindi nessuna distinzione cross-consumer necessaria qui - vedi invece
// _NXS_Struct_FindSweepEvent per la fonte SWEEP condivisa. Copre sia il
// caso "stesso detector richiamato piu' volte nello stesso bar/tick" sia il
// caso "piu' passaggi multi-TF rivalutano la stessa barra chiusa".
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
                           datetime createdTime, string stateBefore, string stateAfter, string consumer,
                           int episodeSeq){
   if(!InpStructuralResearchEventLog) return;
   if(_NXS_Struct_IsDuplicate(level_id, event_type, ts)){
      g_nxsLifecycleDuplicatesSuppressed++;
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
   ev.atr_at_event = g_atr;
   ev.consumer = consumer;
   ev.observed_by = "|" + consumer + "|";
   ev.observation_count = 1;
   ev.sh_bms_episode_seq = episodeSeq;
   g_nxsStructEvents[g_nxsStructEventCount] = ev;
   g_nxsStructEventCount++;
   PrintFormat("[STRUCTLOG][EVENT] event_id=%d level_id=%s type=%s side=%s dir=%d level=%.2f price=%.2f "
               "pen_pips=%.2f age_s=%.0f state=%s->%s regime=%s trend=%s consumer=%s time=%s",
               ev.event_id, ev.structural_level_id, ev.event_type, ev.side, (int)ev.direction,
               ev.level_price, ev.price_at_event, ev.penetration_pips, ev.age_seconds,
               ev.state_before, ev.state_after, ev.regime_at_event, ev.structure_trend_at_event,
               ev.consumer, TimeToString(ev.timestamp, TIME_DATE|TIME_SECONDS));
}

// ============================================================
// Fase A.1 — SWEEP come fonte strutturale condivisa (canonicalizzata).
// ============================================================
// Trova un evento SWEEP gia' registrato per (level_id, timestamp di barra).
// Ritorna l'indice in g_nxsStructEvents[], o -1 se non esiste ancora.
int _NXS_Struct_FindSweepEvent(string level_id, datetime ts){
   for(int i = g_nxsStructEventCount - 1; i >= 0; i--){
      if(g_nxsStructEvents[i].event_type != "SWEEP") continue;
      if(g_nxsStructEvents[i].timestamp != ts) continue;
      if(g_nxsStructEvents[i].structural_level_id != level_id) continue;
      return i;
   }
   return -1;
}

// Punto di osservazione condiviso per un risultato VALIDO di
// NXS_DetectSweepExt() (sw.confirmed=true), indipendente da quale consumer
// lo chiama. Non ridefinisce cosa sia uno sweep (riusa sw.confirmed/dir/
// level/levelTag cosi' come li ha calcolati il detector) e non decide nulla
// per il trading: registra al piu' UN evento SWEEP per (structural_level_id,
// bar del tf attivo), qualunque sia il numero di consumer/pass che lo
// osservano nello stesso bar.
//
// Classificazione della duplicazione quando l'evento esiste gia':
//   - MULTIPASS_DUPLICATE: il consumer che chiama ora e' GIA' nell'elenco
//     observed_by di questo evento (stesso consumer, ri-osservato per via
//     di piu' tick/pass sullo stesso bar - es. SH_BMS_RTO richiamato piu'
//     volte per via del loop multi-TF-pass di NXS_CollectAllSignals).
//   - CROSS_CONSUMER_DUPLICATE: il consumer che chiama ora NON e' ancora
//     nell'elenco (es. LIQ_SWEEP osserva un evento gia' scritto dal punto
//     centrale o da SH_BMS_RTO sullo stesso identico livello+barra) - viene
//     AGGIUNTO a observed_by (metadata) ma NON crea una seconda riga.
//
// outLevelId e' sempre calcolato e restituito anche con il flag OFF, cosi'
// i chiamanti (es. lo stato SH_BMS_RTO) possono continuare a portare un id
// stabile per i propri hook di lifecycle (TRUE_BREAK/RETEST/INVALIDATE),
// invariati rispetto alla Fase A.
void NXS_Structural_ObserveSweep(SNXSSweepExt &sw, ENUM_TIMEFRAMES tf, string consumer,
                                  string &outLevelId, int episodeSeq = 0){
   outLevelId = _NXS_Structural_ComputeLevelId(sw, tf);
   if(!InpStructuralResearchEventLog) return;
   if(!sw.confirmed) return;   // nessuna decisione nuova: solo se il detector ha gia' confermato
   // Controllo di coerenza difensivo: per costruzione NXS_DetectSweepExt() imposta
   // sempre confirmed insieme a dir/level/levelTag nello stesso ramo (mai confirmed
   // da solo). Osservato pero' un caso isolato, solo dal punto di osservazione
   // centrale multi-TF-pass e solo nei primissimi tick di un run fresco, in cui
   // sw arriva con confirmed=true ma dir/level/levelTag ancora ai valori di
   // default - probabile artefatto di dati non ancora sincronizzati per il TF di
   // quel pass specifico a freddo (vedi vault Fase A.1, sezione "anomalia
   // osservata"). Per non registrare mai un evento strutturale internamente
   // incoerente, uno scarto silenzioso (solo contato) e' piu' sicuro di un fix
   // speculativo sul detector, che e' esplicitamente fuori scope qui.
   if(sw.dir == DIR_NONE || sw.levelTag == "" || sw.level <= 0){
      g_nxsSweepMalformedSkipped++;
      return;
   }
   g_nxsSweepRawObservations++;
   datetime obsTime = iTime(g_sym, tf, 0);   // bar in formazione del tf attivo al momento dell'osservazione
   int idx = _NXS_Struct_FindSweepEvent(outLevelId, obsTime);
   if(idx >= 0){
      string tok = "|" + consumer + "|";
      bool alreadySeen = (StringFind(g_nxsStructEvents[idx].observed_by, tok) >= 0);
      g_nxsStructEvents[idx].observation_count++;
      // Se questa chiamata porta un episodeSeq reale (SH_BMS_RTO) e la riga non ne aveva ancora
      // uno (es. creata prima da DETECTOR, sh_bms_episode_seq=0), lo attacca ora - stesso evento
      // canonico, nessuna riga aggiuntiva, solo metadata arricchito.
      if(episodeSeq != 0 && g_nxsStructEvents[idx].sh_bms_episode_seq == 0)
         g_nxsStructEvents[idx].sh_bms_episode_seq = episodeSeq;
      if(alreadySeen){
         g_nxsSweepMultipassDup++;
      } else {
         g_nxsStructEvents[idx].observed_by += consumer + "|";
         g_nxsSweepCrossConsumerDup++;
      }
      return;
   }
   // Nuovo evento canonico: nessun writer precedente per questo (level_id, bar).
   _NXS_Struct_EnsureCapacity();
   double pip = 10.0 * g_profile.pipSize;
   double c1 = iClose(g_sym, tf, 1);
   datetime created = _NXS_Structural_CreatedTime(sw, tf);
   SNXSStructuralEvent ev;
   ev.event_id = ++g_nxsStructEventIdSeq;
   ev.structural_level_id = outLevelId;
   ev.timestamp = obsTime;
   ev.event_type = "SWEEP";
   ev.source = "SNXSSweepExt";
   ev.source_tf = tf;
   ev.side = sw.levelTag;
   ev.direction = sw.dir;
   ev.level_price = sw.level;
   ev.price_at_event = c1;
   ev.penetration_pips = (pip > 0) ? MathAbs(c1 - sw.level) / pip : 0;
   ev.created_time = created;
   ev.age_seconds = (created > 0 && created <= obsTime) ? (double)(obsTime - created) : -1;
   ev.state_before = "IDLE";
   ev.state_after = "SWEPT";
   ev.regime_at_event = _NXS_Structural_RegimeSnapshot();
   ev.structure_trend_at_event = _NXS_Structural_TrendSnapshot();
   ev.atr_at_event = g_atr;
   ev.consumer = consumer;         // primo osservatore = sorgente canonica di questo evento
   ev.observed_by = "|" + consumer + "|";
   ev.observation_count = 1;
   ev.sh_bms_episode_seq = episodeSeq;
   g_nxsStructEvents[g_nxsStructEventCount] = ev;
   g_nxsStructEventCount++;
   g_nxsSweepUniqueEvents++;
   PrintFormat("[STRUCTLOG][EVENT] event_id=%d level_id=%s type=SWEEP side=%s dir=%d level=%.2f price=%.2f "
               "pen_pips=%.2f age_s=%.0f state=IDLE->SWEPT regime=%s trend=%s consumer=%s time=%s",
               ev.event_id, ev.structural_level_id, ev.side, (int)ev.direction,
               ev.level_price, ev.price_at_event, ev.penetration_pips, ev.age_seconds,
               ev.regime_at_event, ev.structure_trend_at_event, ev.consumer,
               TimeToString(ev.timestamp, TIME_DATE|TIME_SECONDS));
}

void NXS_Structural_OnTrueBreak(string level_id, ENUM_TIMEFRAMES tf, datetime barTs, string side,
                                 ENUM_NXS_DIR dir, double levelPrice, string consumer, int episodeSeq){
   double c1 = iClose(g_sym, tf, 1);
   _NXS_Struct_LogEvent(level_id, barTs, "TRUE_BREAK", tf, side, dir, levelPrice, c1,
                        0, "SWEPT", "WAITING_RETURN", consumer, episodeSeq);
}

void NXS_Structural_OnRetest(string level_id, ENUM_TIMEFRAMES tf, datetime barTs, string side,
                              ENUM_NXS_DIR dir, double levelPrice, double priceAtEvent, string consumer, int episodeSeq){
   _NXS_Struct_LogEvent(level_id, barTs, "RETEST", tf, side, dir, levelPrice, priceAtEvent,
                        0, "WAITING_RETURN", "CONSUMED", consumer, episodeSeq);
}

void NXS_Structural_OnInvalidate(string level_id, ENUM_TIMEFRAMES tf, datetime barTs, string side,
                                  ENUM_NXS_DIR dir, double levelPrice, string stateBefore, string consumer, int episodeSeq){
   double c1 = iClose(g_sym, tf, 1);
   _NXS_Struct_LogEvent(level_id, barTs, "INVALIDATE", tf, side, dir, levelPrice, c1,
                        0, stateBefore, "IDLE", consumer, episodeSeq);
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
               "unique_structural_levels=%d lifecycle_duplicates_suppressed=%d",
               g_nxsStructEventCount, sweeps, breaks, retests, invalidations, seenCount,
               g_nxsLifecycleDuplicatesSuppressed);
   PrintFormat("[STRUCTLOG][SWEEP_SUMMARY] raw_observations=%d unique_events=%d "
               "multipass_duplicate=%d cross_consumer_duplicate=%d malformed_skipped=%d",
               g_nxsSweepRawObservations, g_nxsSweepUniqueEvents,
               g_nxsSweepMultipassDup, g_nxsSweepCrossConsumerDup, g_nxsSweepMalformedSkipped);
}

// 14/09 - Fase B (Structural Dataset v1). Dump dell'intero stato finale di
// g_nxsStructEvents[] su CSV in un colpo solo, chiamato da OnDeinit DOPO che
// tutti gli eventi del run sono gia' stati osservati (osserved_by/
// observation_count riflettono quindi lo stato FINALE, non quello al momento
// della creazione). FILE_WRITE senza FILE_READ tronca sempre il file
// esistente all'apertura - ogni run produce un dump pulito e completo,
// senza dipendere dal meccanismo di reset-per-TimeLocal() gia' noto come
// inaffidabile nel Tester (vedi NEXUS_trades.csv). SOLO lettura/scrittura di
// un file diagnostico: nessun impatto su trading/execution/risk.
void NXS_Structural_ExportCSV(string filename = "nxs_structural_events.csv"){
   if(!InpStructuralResearchEventLog) return;
   int h = FileOpen(filename, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
   if(h == INVALID_HANDLE) return;
   FileWrite(h, "event_id","structural_level_id","timestamp","event_type","source","source_tf",
              "side","direction","level_price","price_at_event","penetration_pips",
              "created_time","age_seconds","state_before","state_after","regime_at_event",
              "structure_trend_at_event","atr_at_event","consumer","observed_by","observation_count",
              "sh_bms_episode_seq");
   for(int i = 0; i < g_nxsStructEventCount; i++){
      SNXSStructuralEvent ev = g_nxsStructEvents[i];
      FileWrite(h, ev.event_id, ev.structural_level_id,
                TimeToString(ev.timestamp, TIME_DATE|TIME_SECONDS),
                ev.event_type, ev.source, EnumToString(ev.source_tf), ev.side,
                NXS_DirName(ev.direction),
                DoubleToString(ev.level_price, g_digits),
                DoubleToString(ev.price_at_event, g_digits),
                DoubleToString(ev.penetration_pips, 2),
                (ev.created_time > 0) ? TimeToString(ev.created_time, TIME_DATE|TIME_SECONDS) : "",
                DoubleToString(ev.age_seconds, 0),
                ev.state_before, ev.state_after, ev.regime_at_event, ev.structure_trend_at_event,
                DoubleToString(ev.atr_at_event, 5),
                ev.consumer, ev.observed_by, ev.observation_count, ev.sh_bms_episode_seq);
   }
   FileClose(h);
   PrintFormat("[STRUCTLOG][EXPORT] %d righe scritte su %s (FILE_COMMON)", g_nxsStructEventCount, filename);
}

#endif
