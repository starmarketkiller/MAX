# NEXUS - Phase 7.26 — Research Safety Net V1

**Baseline:** `38e0e22` (Phase 7.25, LIQ_SWEEP EDGE_VALIDATION_V1). Nessuna modifica a MQL5/strategie. Nessuna optimization. Nessun nuovo backtest lungo (tutto backfillato da artifact già esistenti). Nessun deploy.

**Obiettivo**: integrare l'evidenza accumulata in Phase 7 (BREAKOUT_ACC, ORDER_BLOCK, TSI, LIQ_SWEEP) in un sistema permanente che impedisca pseudo-OOS/leakage, raccolga cosa impariamo da ogni strategia, permetta cross-strategy analysis, e generi hypothesis testabili — prima di continuare a testare strategie una per una in isolamento.

---

## A. Global Data Exposure Registry

**11 record** su 4 strategie, backfillati dalle rispettive data_exposure_map/decision card già esistenti (nessuna nuova analisi). Ogni record: dataset_id, symbol, timeframe, date_range, strategy/implementation identity, experiment_run_ids, 7 flag di esposizione (development/integrity_audit/mechanism_discovery/visual_review/optimization/validation/oos/forward), holdout_status. Query `is_genuinely_untouched(dataset_id)` — True solo per `NOT_USED`/`UNVERIFIED`. Distinzione esplicita "seen per una domanda" vs "seen per un'altra": es. ORDER_BLOCK 2023.10.02-2026.08.24 è `SEEN_FOR_SIGNALS_NOT_FOR_ECONOMICS`, LIQ_SWEEP stessa finestra è `SEEN_FOR_NET_PNL_TOTALE_NOT_FOR_GRANULAR_STATS`.

## B. Experiment Registry

**8 esperimenti** backfillati (2 per BREAKOUT_ACC, 2 ORDER_BLOCK, 1 TSI, 3 LIQ_SWEEP), ognuno con hypothesis_id/run_id/dataset_id/code_sha/config_hash (None quando non esiste — BREAKOUT_ACC/ORDER_BLOCK precedono l'harness di isolamento, quindi niente config_hash inventato)/metrics/verdict/confidence/limitations. Verificato: nessun esperimento orfano (hypothesis_id e dataset_id sempre risolvibili nell'altro registro).

## C. Hypothesis Registry

**8 hypothesis**, lifecycle OBSERVATION→...→SUPPORTED/REJECTED/INCONCLUSIVE. **Regola obbligatoria enforced dal verificatore**: una hypothesis non può essere SUPPORTED/REJECTED usando il proprio discovery_dataset_id come unica validation, salvo `mechanical_verification_exception=True` (riservata a verifiche deterministiche di codice, non statistiche — usata per H_TSI_TF_GUARD_FIX_EFFECTIVE e i 2 mismatch LIQ_SWEEP di Phase 7.23). H2 (BUY più robusto di SELL, BREAKOUT_ACC) resta correttamente `HYPOTHESIS` — mai salita a SUPPORTED perché scoperta guardando l'intero campione e mai testata su un dataset indipendente.

## D+K. Cross-Strategy Learning Packet — generatore + backfill

`generate_packet()` con firma esplicita (28 campi, nessun `**kwargs` — un campo dimenticato è un errore immediato, non un'omissione silenziosa). Backfillati i 4 pacchetti: TSI ha quasi tutti i campi economici `NOT_AVAILABLE` (mai esistito un dataset P&L — dichiarato, non nascosto). LIQ_SWEEP porta il pacchetto più ricco (MFE/MAE reali, concentrazione, OOS). BREAKOUT_ACC recupera MFE/MAE/outcome-flip da Phase 7.9K.

## E. Failure Map

Tassonomia a 18 tag. BREAKOUT_ACC: `OUTLIER_DEPENDENT`, `DIRECTION_DEPENDENT`, `OOS_DEGRADATION`. ORDER_BLOCK: `OUTLIER_DEPENDENT`, `LOW_SAMPLE`, `OOS_DEGRADATION`. TSI: solo `IMPLEMENTATION_DEFECT` (nessun tag economico — non applicabile per costruzione). LIQ_SWEEP: `OUTLIER_DEPENDENT`, `TEMPORALLY_CONCENTRATED`, `REGIME_DEPENDENT`, `OOS_DEGRADATION`. Ogni tag porta un `evidence_ref` verificabile.

## F. Path Anatomy Engine

Standardizzato (`PathAnatomyEvent`, `compute_path_metrics`, `excursion_before_outcome`, `fixed_horizon_outcome`, `build_event_report`) — separa **sempre** signal-relative da fill-relative, gestisce censoring (posizione ancora aperta). Generalizza la logica ad hoc di Phase 7.25.

## G. Pre-Entry Feature Store

`make_feature()` **fail-closed**: solleva `FeatureLeakageError` immediatamente se `availability_time > decision_timestamp`, invece di salvare un record silenziosamente contaminato. Auto-test nel verificatore di leakage: una feature valida deve passare, una futura deve essere rifiutata (entrambi verificati).

## H. Matched Non-Events e Near Miss

`select_matched_non_event()` — usa **esclusivamente** timestamp entry/exit (mai P&L/MFE/MAE/esito). Verificato **staticamente** (`verify_no_outcome_fields_used()`, ispeziona il sorgente della funzione stessa) che nessuna delle `FORBIDDEN_OUTCOME_KEYS` sia referenziata. `select_near_miss()` dichiara `GAP_DICHIARATO_NON_FABBRICATO` quando non esiste telemetria per-evento (caso reale: tutti i segnali bloccati del corpus).

## I. Visual Audit Engine riusabile

Riutilizza (non riscrive) il rendering SVG puro-Python di Phase 7.25 (bloccato da matplotlib in questo ambiente) — generalizzato in `render_event_stages()`, strategy-agnostic, Stage A/B/C, fidelity grade sempre dichiarato. Testato con un evento sintetico (rendering reale confermato) e un evento senza prezzo (`data_available=False`, zero file scritti — mai un chart fuorviante).

## J. Cross-Strategy Synthesis

Legge **solo** artifact già costruiti in questa fase (mai ricalcola dai dati grezzi). Output ristretto a OBSERVATION/CROSS_STRATEGY_PATTERN/CANDIDATE_HYPOTHESIS — **mai** EDGE_FOUND (verificato: nessuna occorrenza della stringa nell'output). **7 finding**, i più rilevanti:

- **CROSS_STRATEGY_PATTERN**: le 3 strategie economiche condividono `OUTLIER_DEPENDENT` **E** `OOS_DEGRADATION` — non un caso isolato di una singola strategia.
- **CANDIDATE_HYPOTHESIS**: tutte e 3 mostrano dominanza BUY — potrebbe riflettere il trend secolare di GOLD 2019-2026 più che un edge specifico. Non verificato in questa fase (richiede benchmark buy-and-hold).
- **OBSERVATION**: solo LIQ_SWEEP ha temporal_concentration ed exit_efficiency calcolati — gap di ricerca dichiarato per BREAKOUT_ACC/ORDER_BLOCK, non un'assenza del fenomeno.

## L. Research Priority Queue

8 criteri dichiarati **prima** di assegnare i punteggi (PF esplicitamente escluso, verificato). Ranking: **1) benchmark buy-and-hold** per testare la CANDIDATE_HYPOTHESIS della dominanza BUY (punteggio 32 — se confermata invaliderebbe l'apparente edge di tutte e 3 le strategie insieme); 2) backfill temporal/exit-efficiency per BREAKOUT_ACC/ORDER_BLOCK (29, costo quasi zero); 3) accumulo forward passivo LIQ_SWEEP (26); 4) audit integrità FVG_CONT (23, prossimo candidato di Phase 7.20 ma penalizzato da bassa mechanism_distinctiveness — condivide codice con IFVG/FVG_MIT/FVG_MIT_WINDOW); 5) resto dell'universo strategie (17).

## M. Multiple Testing Registry

8 hypothesis testate su 4 strategie/8 esperimenti/11 dataset registrati, **3 finestre OOS consumate** (BREAKOUT_ACC/ORDER_BLOCK/LIQ_SWEEP forward). Nessuna correzione multiple-comparison applicata (dichiarato) — il rapporto hypothesis/OOS-indipendenti (8/3) è registrato come segnale d'allarme precoce, non ancora una correzione formale.

## N. Verifica e provenance

`verify_leakage.py` (5 controlli strutturali trasversali: separazione discovery/validation, no-outcome-fields nel matched non-event, causal self-test del feature store, coerenza interna del data exposure registry, no-EDGE_FOUND nella sintesi) + `verify_phase_7_26.py` (ricostruzione indipendente di tutti gli 8 registry/artifact, no-modifica a Phase 7.9x-7.25/MQL5/Product-Platform/contracts, no-riferimenti orfani). **35/35 test**.

## Bug trovati e corretti durante la fase

Diversi errori di battitura reali in stringhe `dataset_id`/`hypothesis_id` (troncate a metà parola, es. `"ORDER_BLOCK_1_2023.10.02 - 2026.08.24 (13 tr"`, e un mismatch `H1_NET_EXPECTANCY_POSITIVE` vs il vero id `H1_BREAKOUT_ACC_NET_EXPECTANCY_POSITIVE`) — introdotti durante lo sviluppo iterativo di questa stessa fase, trovati dal verificatore stesso (controllo di riferimenti orfani) prima del commit, corretti e riverificati.

## Deliverables

`nxs_schemas.py`, `nxs_backfill_sources.py`, `build_data_exposure_registry.py`, `build_experiment_registry.py`, `build_hypothesis_registry.py`, `build_failure_map.py`, `nxs_path_anatomy_engine.py`, `nxs_pre_entry_feature_store.py`, `nxs_matched_non_event_builder.py`, `nxs_visual_audit_engine.py`, `build_cross_strategy_learning_packet.py`, `build_cross_strategy_synthesis.py`, `build_research_priority_queue.py`, `build_multiple_testing_registry.py`, `verify_leakage.py`, `verify_phase_7_26.py`, `test_phase_7_26.py` + gli 8 JSON risultanti, questo vault report.

## Vincoli preservati

Nessuna modifica a `MQL5/`, `Product-Platform/`, `contracts/`, né a Phase 7.9c-7.25 (diff zero verificato su tutte). Nessuna optimization. Nessun nuovo backtest MT5 (tutto backfillato). Nessun deploy.

## Regressione

(compilata dopo l'esecuzione della suite completa)

---

```
7.25: LIQ_SWEEP EDGE_VALIDATION_V1 - EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION
7.26: NEXUS RESEARCH SAFETY NET V1 - COMPLETATO

BACKFILL: 4 strategie (BREAKOUT_ACC/ORDER_BLOCK/TSI/LIQ_SWEEP) in
  11 dataset_id, 8 esperimenti, 8 hypothesis, 4 learning packet,
  4 failure-mode profile - tutto da artifact GIA' esistenti

REGOLA CHIAVE ENFORCED: hypothesis discovery!=validation (verificata
  dal codice, non solo dichiarata) - eccezione solo per verifiche
  meccaniche di codice (TSI fix, 2 mismatch LIQ_SWEEP)

SINTESI TRASVERSALE (7 finding, mai EDGE_FOUND):
  PATTERN CONDIVISO: le 3 strategie economiche mostrano TUTTE
    OUTLIER_DEPENDENT e OOS_DEGRADATION - non un caso isolato
  CANDIDATE HYPOTHESIS: dominanza BUY condivisa - forse solo il
    trend secolare di GOLD, non un edge - da testare vs benchmark
  GAP DICHIARATI: solo LIQ_SWEEP ha temporal_concentration ed
    exit_efficiency - BREAKOUT_ACC/ORDER_BLOCK da colmare (costo
    quasi zero, dati gia' esistenti)

PRIORITY QUEUE (PF esplicitamente NON un criterio):
  1) benchmark buy-and-hold (info gain piu' alto - potrebbe
     invalidare 3 apparenti edge insieme)
  2) backfill BREAKOUT_ACC/ORDER_BLOCK (costo zero)
  3) accumulo forward passivo LIQ_SWEEP
  4) audit FVG_CONT (penalizzato: condivide codice con 3 varianti)
  5) resto universo strategie

BUG TROVATI E CORRETTI (durante questa stessa fase, dal verificatore
  di riferimenti orfani): dataset_id/hypothesis_id troncati o
  mismatch fra registry - corretti prima del commit

VISUAL AUDIT ENGINE: prototipo Phase 7.25 reso riusabile
  strategy-agnostic, testato con evento sintetico + caso senza dati
  (NOT_AVAILABLE, zero file fuorvianti)

PROSSIMO: 1) benchmark BUY vs buy-and-hold (Research Priority Queue,
  priorita' 1), poi tornare a testare strategie una per una - ogni
  test futuro alimenta questi registry automaticamente
```
