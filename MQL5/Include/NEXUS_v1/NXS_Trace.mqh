//+------------------------------------------------------------------+
//| NXS_Trace.mqh                                                     |
//| 12/09 - Decision/Gate/Execution Trace v1 (roadmap NEXUS 95/99).    |
//|                                                                    |
//| Obiettivo dichiarato dall'utente: ogni segnale deve poter essere   |
//| seguito causalmente da generazione ad apertura o blocco. Requisito |
//| esplicito, per non ripetere l'errore gia' documentato in vault     |
//| (CAUSAL_HOOK_MISMATCH, Failure Memory 12/09): "il trace deve       |
//| essere inserito nello stesso punto causale della decisione reale". |
//|                                                                    |
//| Per questo NON e' un modulo nuovo isolato: estende                 |
//| NXS_GateTelemetry (gia' esistente in NXS_Execution.mqh, gia'       |
//| agganciato al punto causale corretto dentro                        |
//| NXS_CommonExposurePreflight) invece di duplicarlo, e aggiunge gli  |
//| stessi call site su ogni altro gate reale nei 4 execution path     |
//| mappati (DataCollection/Institutional/StrategyProfiles/Legacy).    |
//| Vedi il report della sessione per la mappa completa.               |
//+------------------------------------------------------------------+
#ifndef __NXS_TRACE_MQH__
#define __NXS_TRACE_MQH__

// Stati minimi richiesti:
//   GENERATED -> BLOCKED(reason)
//   GENERATED -> OPEN_ATTEMPT -> OPENED(position_id)
//   GENERATED -> OPEN_ATTEMPT -> BROKER_REJECT(reason)
enum ENUM_NXS_TRACE_STAGE {
   TRACE_GENERATED = 0,
   TRACE_BLOCKED,
   TRACE_OPEN_ATTEMPT,
   TRACE_OPENED,
   TRACE_BROKER_REJECT
};

// Canonical gate enum (minimo richiesto + 2 estensioni dichiarate: LICENSE e
// STATE_UNCERTAIN, entrambe gia' gate reali esistenti in
// NXS_CommonExposurePreflight senza un bucket canonico corrispondente -
// piuttosto che forzarle dentro PROTECTIONS in modo fuorviante, sono
// enumerate a parte e documentate qui).
enum ENUM_NXS_GATE_REASON {
   GATE_NONE = 0,
   GATE_PROFILE_DISABLED,
   GATE_TF_GATE,
   GATE_OPEN_POSITION,
   GATE_COOLDOWN,
   GATE_PROTECTIONS,
   GATE_RISKSHIELD,
   GATE_SPREAD,
   GATE_NEWS,
   GATE_HTF,
   GATE_VELOCITY,
   GATE_SCORE,
   GATE_EXPOSURE,
   GATE_MARGIN,
   GATE_INVALID_STOPS,
   GATE_BROKER_REJECT,
   GATE_UNKNOWN_STRATEGY,
   GATE_OPENED,
   // estensioni dichiarate (gate reali senza bucket canonico corrispondente):
   GATE_LICENSE,
   GATE_STATE_UNCERTAIN
};

string NXS_GateReasonName(ENUM_NXS_GATE_REASON g){
   switch(g){
      case GATE_NONE:              return "NONE";
      case GATE_PROFILE_DISABLED:  return "PROFILE_DISABLED";
      case GATE_TF_GATE:           return "TF_GATE";
      case GATE_OPEN_POSITION:     return "OPEN_POSITION";
      case GATE_COOLDOWN:          return "COOLDOWN";
      case GATE_PROTECTIONS:       return "PROTECTIONS";
      case GATE_RISKSHIELD:        return "RISKSHIELD";
      case GATE_SPREAD:            return "SPREAD";
      case GATE_NEWS:              return "NEWS";
      case GATE_HTF:               return "HTF";
      case GATE_VELOCITY:          return "VELOCITY";
      case GATE_SCORE:             return "SCORE";
      case GATE_EXPOSURE:          return "EXPOSURE";
      case GATE_MARGIN:            return "MARGIN";
      case GATE_INVALID_STOPS:     return "INVALID_STOPS";
      case GATE_BROKER_REJECT:     return "BROKER_REJECT";
      case GATE_UNKNOWN_STRATEGY:  return "UNKNOWN_STRATEGY";
      case GATE_OPENED:            return "OPENED";
      case GATE_LICENSE:           return "LICENSE";
      case GATE_STATE_UNCERTAIN:   return "STATE_UNCERTAIN";
      default:                     return "UNKNOWN";
   }
}

string NXS_TraceStageName(ENUM_NXS_TRACE_STAGE s){
   switch(s){
      case TRACE_GENERATED:     return "GENERATED";
      case TRACE_BLOCKED:       return "BLOCKED";
      case TRACE_OPEN_ATTEMPT:  return "OPEN_ATTEMPT";
      case TRACE_OPENED:        return "OPENED";
      case TRACE_BROKER_REJECT: return "BROKER_REJECT";
      default:                  return "UNKNOWN";
   }
}

// --- identita' del run (assegnata una volta in OnInit) ---------------------
string   g_nxsTraceRunId   = "";
string   g_nxsTraceBuild   = "";   // versione EA / commit, se disponibile
long     g_nxsTraceSeq     = 0;    // contatore signal_id/decision_id, monotono per il run
// "Live Mode invariato" + "overhead minimo": il trace emette SOLO quando
// attivo. NXS_IsResearchMode() non e' chiamabile da qui (definita molto piu'
// tardi nella catena di include, NXS_ResearchMode.mqh) - il flag viene
// impostato dal chiamante (OnInit) dopo che tutti gli include sono risolti,
// non richiamato da dentro questo file.
bool     g_nxsTraceActive  = false;

void NXS_Trace_ResetCert();   // forward decl - definita sotto, chiamata da Init prima della propria definizione testuale

void NXS_Trace_Init(string runId, string buildInfo, bool active){
   g_nxsTraceRunId = runId;
   g_nxsTraceBuild = buildInfo;
   g_nxsTraceSeq = 0;
   g_nxsTraceActive = active;
   NXS_Trace_ResetCert();
}

long NXS_Trace_NextId(){
   if(!g_nxsTraceActive) return 0;
   return ++g_nxsTraceSeq;
}

// --- Aggregazione in memoria per il Test Validity Certificate v2 -----------
// Il certificato usa il trace come FONTE PRIMARIA: invece di rileggere il
// Journal (MQL5 non può farlo in modo affidabile durante l'esecuzione), ogni
// NXS_Trace_Emit aggiorna QUESTI contatori nello stesso momento in cui
// stampa la riga - stesso punto causale, nessuna doppia fonte di verità.
long g_certGenerated = 0, g_certBlocked = 0, g_certOpenAttempt = 0,
     g_certOpened = 0, g_certBrokerReject = 0;
long g_certGateCount[20];   // indicizzato da ENUM_NXS_GATE_REASON
long g_certOpenedMissingPositionId = 0;   // invariante: ogni OPENED deve avere position_id
long g_certBrokerRejectMissingReason = 0; // invariante: ogni broker reject deve avere reason
// per il controllo "source TF mismatch": prima strategia/TF visti in GENERATED,
// e se una successiva GENERATED della STESSA strategia dichiara un TF diverso.
string   g_certFirstStrategy = "";
ENUM_TIMEFRAMES g_certFirstSourceTF = PERIOD_CURRENT;
bool     g_certSourceTFSeen = false;
bool     g_certSourceTFMismatch = false;
// Incrementato da NXS_ResearchMode.mqh (NXS_ResearchLogExit) ogni volta che
// stampa [RESEARCH][INVARIANT_FAIL] - EXPERT_UNKNOWN o un'autorita' di uscita
// non prevista dal contratto RAW/opt-in corrente. Dichiarato qui (incluso
// prima di NXS_ResearchMode.mqh) perche' il certificato lo usa come fonte
// primaria invece di ri-analizzare il Journal.
long     g_certInvariantFailCount = 0;
// period_start/period_end richiesti dal certificato: non e' l'orario di
// lancio del run (quello e' g_testerPassStart, identita' del run) ma il
// range dati EFFETTIVAMENTE attraversato dai tick - primo e ultimo
// TimeCurrent() osservato in OnTick. Aggiornato da NXS_Trace_TouchPeriod(),
// chiamata in testa a OnTick() SOLO quando il trace e' attivo.
datetime g_certPeriodStart = 0;
datetime g_certPeriodEnd   = 0;

void NXS_Trace_ResetCert(){
   g_certGenerated = 0; g_certBlocked = 0; g_certOpenAttempt = 0;
   g_certOpened = 0; g_certBrokerReject = 0;
   for(int i = 0; i < 20; i++) g_certGateCount[i] = 0;
   g_certOpenedMissingPositionId = 0;
   g_certBrokerRejectMissingReason = 0;
   g_certFirstStrategy = ""; g_certSourceTFSeen = false; g_certSourceTFMismatch = false;
   g_certInvariantFailCount = 0;
   g_certPeriodStart = 0; g_certPeriodEnd = 0;
}

void NXS_Trace_TouchPeriod(){
   if(!g_nxsTraceActive) return;
   datetime t = TimeCurrent();
   if(g_certPeriodStart == 0) g_certPeriodStart = t;
   g_certPeriodEnd = t;
}

// Emissione centralizzata - UNA riga strutturata per ogni transizione di
// stato. decisionId e signalId coincidono in v1 per i path 1:1 segnale-
// decisione (DataCollection/StrategyProfiles/Legacy); il path Institutional
// aggrega piu' segnali in una decisione sola - vedi nota al call site.
void NXS_Trace_Emit(long decisionId, long signalId, string strategy,
                    ENUM_TIMEFRAMES sourceTF, ENUM_TIMEFRAMES entryTF,
                    string levelId, ulong positionId,
                    ENUM_NXS_TRACE_STAGE stage, ENUM_NXS_GATE_REASON gate,
                    string detail){
   if(!g_nxsTraceActive) return;
   PrintFormat("[NXS_TRACE] run_id=%s decision_id=%d signal_id=%d strategy=%s "
               "source_tf=%s entry_tf=%s level_id=%s position_id=%I64u "
               "timestamp=%s pipeline_stage=%s gate_reason=%s detail=%s build=%s",
               g_nxsTraceRunId, decisionId, signalId, strategy,
               EnumToString(sourceTF), EnumToString(entryTF),
               (StringLen(levelId) > 0 ? levelId : "-"), positionId,
               TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS),
               NXS_TraceStageName(stage), NXS_GateReasonName(gate),
               detail, g_nxsTraceBuild);

   // --- aggiornamento contatori certificato (stesso punto causale) ---------
   switch(stage){
      case TRACE_GENERATED:
         g_certGenerated++;
         if(!g_certSourceTFSeen){
            g_certFirstStrategy = strategy; g_certFirstSourceTF = sourceTF;
            g_certSourceTFSeen = true;
         } else if(strategy == g_certFirstStrategy && sourceTF != g_certFirstSourceTF){
            g_certSourceTFMismatch = true;
         }
         break;
      case TRACE_BLOCKED:
         g_certBlocked++;
         if((int)gate >= 0 && (int)gate < 20) g_certGateCount[(int)gate]++;
         break;
      case TRACE_OPEN_ATTEMPT:
         g_certOpenAttempt++;
         break;
      case TRACE_OPENED:
         g_certOpened++;
         if(positionId == 0) g_certOpenedMissingPositionId++;
         break;
      case TRACE_BROKER_REJECT:
         g_certBrokerReject++;
         if((int)gate >= 0 && (int)gate < 20) g_certGateCount[(int)gate]++;
         if(StringLen(detail) == 0) g_certBrokerRejectMissingReason++;
         break;
   }
}

// Helper per il caso comune (segnale 1:1, entry_tf = InpTFEntry corrente).
void NXS_Trace_Generated(SNXSSignal &sig, ENUM_TIMEFRAMES entryTF){
   NXS_Trace_Emit(sig.trace_id, sig.trace_id, sig.stratName, sig.sourceTF, entryTF,
                  "", 0, TRACE_GENERATED, GATE_NONE, sig.reason);
}
void NXS_Trace_Blocked(SNXSSignal &sig, ENUM_TIMEFRAMES entryTF,
                       ENUM_NXS_GATE_REASON gate, string detail){
   NXS_Trace_Emit(sig.trace_id, sig.trace_id, sig.stratName, sig.sourceTF, entryTF,
                  "", 0, TRACE_BLOCKED, gate, detail);
}
void NXS_Trace_OpenAttempt(SNXSSignal &sig, ENUM_TIMEFRAMES entryTF){
   NXS_Trace_Emit(sig.trace_id, sig.trace_id, sig.stratName, sig.sourceTF, entryTF,
                  "", 0, TRACE_OPEN_ATTEMPT, GATE_NONE, "");
}
void NXS_Trace_Opened(SNXSSignal &sig, ENUM_TIMEFRAMES entryTF, ulong positionId){
   NXS_Trace_Emit(sig.trace_id, sig.trace_id, sig.stratName, sig.sourceTF, entryTF,
                  "", positionId, TRACE_OPENED, GATE_OPENED, "");
}
void NXS_Trace_BrokerReject(SNXSSignal &sig, ENUM_TIMEFRAMES entryTF, string detail){
   NXS_Trace_Emit(sig.trace_id, sig.trace_id, sig.stratName, sig.sourceTF, entryTF,
                  "", 0, TRACE_BROKER_REJECT, GATE_BROKER_REJECT, detail);
}

// Mappa una stringa g_nxsLastOpenFailure (NXS_OpenTrade/NXS_CommonExposurePreflight)
// sul gate canonico. Stessa idea di NXS_BlkFromFailure (NXS_BlockerDiagnostics.mqh,
// gia' esistente) ma sul set di enum richiesto per il trace - tenute separate
// perche' servono a due sistemi diversi (contatori aggregati vs trace causale
// per-segnale) e unificarle ora rischierebbe di rompere i contatori esistenti
// gia' in uso da telemetria/dashboard.
ENUM_NXS_GATE_REASON NXS_GateReasonFromFailure(const string r){
   if(StringLen(r) == 0)                          return GATE_PROTECTIONS;
   if(StringFind(r, "unknown_strategy")  >= 0)     return GATE_UNKNOWN_STRATEGY;
   if(StringFind(r, "profile_disabled")  >= 0)     return GATE_PROFILE_DISABLED;
   if(StringFind(r, "strategy_disabled_dashboard") >= 0) return GATE_PROFILE_DISABLED;
   if(StringFind(r, "wrong_tf")          >= 0)     return GATE_TF_GATE;
   if(StringFind(r, "bar_dir_cap")       >= 0)     return GATE_EXPOSURE;
   if(StringFind(r, "setup_matrix_cap")  >= 0)     return GATE_EXPOSURE;
   if(StringFind(r, "dir_exposure_cap")  >= 0)     return GATE_EXPOSURE;
   if(StringFind(r, "post_sl_cooldown")  >= 0)     return GATE_COOLDOWN;
   if(StringFind(r, "cooldown")          >= 0)     return GATE_COOLDOWN;
   if(StringFind(r, "exhaustion")        >= 0)     return GATE_PROTECTIONS;
   if(StringFind(r, "elliott")           >= 0)     return GATE_PROTECTIONS;
   if(StringFind(r, "ruin_frozen")       >= 0)     return GATE_PROTECTIONS;
   if(StringFind(r, "protections_block") >= 0)     return GATE_PROTECTIONS;
   if(StringFind(r, "ledger_degraded")   >= 0)     return GATE_STATE_UNCERTAIN;
   if(StringFind(r, "state_restore_failed") >= 0)  return GATE_STATE_UNCERTAIN;
   if(StringFind(r, "indicators_degraded") >= 0)   return GATE_STATE_UNCERTAIN;
   if(StringFind(r, "vsl_persist_unhealthy") >= 0) return GATE_STATE_UNCERTAIN;
   if(StringFind(r, "license")           >= 0)     return GATE_LICENSE;
   if(StringFind(r, "regime_veto")       >= 0)     return GATE_PROTECTIONS;
   if(StringFind(r, "invalid_sl_distance") >= 0)   return GATE_INVALID_STOPS;
   if(StringFind(r, "missing_broker_stop") >= 0)   return GATE_INVALID_STOPS;
   if(StringFind(r, "preflight_cleared_stop") >= 0) return GATE_INVALID_STOPS;
   if(StringFind(r, "virtsl_hardSL_invalid") >= 0) return GATE_INVALID_STOPS;
   if(StringFind(r, "lot_calc_zero")     >= 0)     return GATE_MARGIN;
   if(StringFind(r, "strategy_risk_disabled") >= 0) return GATE_MARGIN;
   if(StringFind(r, "virtsl_offline_risk_over_cap") >= 0) return GATE_MARGIN;
   if(StringFind(r, "margin_gate")       >= 0)     return GATE_MARGIN;
   if(StringFind(r, "lot_below_min")     >= 0)     return GATE_MARGIN;
   if(StringFind(r, "lot_above_max")     >= 0)     return GATE_MARGIN;
   if(StringFind(r, "spread")            >= 0)     return GATE_SPREAD;
   if(StringFind(r, "retcode")           >= 0)     return GATE_BROKER_REJECT;
   if(StringFind(r, "order_send")        >= 0)     return GATE_BROKER_REJECT;
   return GATE_PROTECTIONS;   // fallback dichiarato: nessuna stringa reale osservata finora arriva qui
}

#endif
