# NEXUS - Phase 7.3: Sequence Discovery Engine v1

**Baseline:** `5b9c928` (Phase 7.2B, chiusa, READY_FOR_PHASE_7_3=true). Questa fase costruisce la MACCHINA di discovery per sequence (STATE→EVENT_A→TRANSITION→EVENT_B opzionale→OUTCOME_FAMILY) - **non esegue nessuna discovery reale**.

**Conferma esplicita: NO REAL NEXUS EDGE DISCOVERY PERFORMED IN PHASE 7.3.** Verificato strutturalmente dal gate `no_real_outcome_edge_discovery_performed` in `phase7_3_engine_readiness_gate_v1.json`: scansione automatica di ogni file di questa fase per riferimenti a dataset/path NEXUS reali (market_state, outcomes, validation, holdout, frozen spec di Phase 7.1) - **0 offender trovati** - più verifica positiva che l'artefatto red-team non contenga alcun `delta_p` calcolato.

**READY_FOR_FIRST_SEQUENCE_DISCOVERY = TRUE.**

---

## 1. Sequence tecnicamente eleggibili: 6/20

Selezione **non basata su punteggio di priorità** - applicati 6 criteri deterministici (READY_FOR_FORMALIZATION, causal-safe, implementabile con dati H4 esistenti, nessun gap VWAP/sessione/calendario/multi-asset, nessun DIRECT_REPEAT_OF_FAILED_IDEA, semantic leakage PASS). Output: `phase7_3_eligible_sequence_families_v1.json`.

| Sequence | Mechanism | Event A | Failure memory |
|---|---|---|---|
| SEQ-0001 | MECH-01 | Movimento direzionale sostenuto (finestra lunga, mesi) | NOVEL |
| SEQ-0009 | MECH-18 | Prezzo eccede brevemente un livello (wick) senza chiudere oltre | RELATED_TO_PREVIOUS_FAILURE (non DIRECT_REPEAT) |
| SEQ-0014 | MECH-23 | Stato classificato come choppy/laterale a bassa efficienza direzionale | NOVEL |
| SEQ-0015 | MECH-25 | Chiusura di una barra con true range anomalamente ampio | NOVEL |
| SEQ-0016 | MECH-26 | Tocco/superamento della banda esterna | NOVEL |
| SEQ-0020 | MECH-33 | Incrocio/divergenza fra medie mobili corta e lunga | NOVEL |

**14/20 restano bloccate** (`NEEDS_ADDITIONAL_SPECIFICATION` o `NOT_IMPLEMENTABLE_AS_DESCRIBED`) per gap già dichiarati in Phase 7.2/7.2B: multi-timeframe non disponibile, VWAP non implementato, calendario macro/culturale assente, secondo strumento cointegrato assente. Nessuna di queste 14 è stata forzata nell'inventario eleggibile.

## 2-9. Componenti dell'engine - tutti verificati per esecuzione reale (non solo presenza file)

| Componente | File | Stato |
|---|---|---|
| Detector contract | `sequence_detector_contract_v1.json` | PASS (5 hard_requirements, sequence_event_id deterministico via SHA256) |
| Temporal causality guard | `engine/sequence_causality_guard.py` | PASS (6 casi dimostrati: 4 su causalità temporale, 2 su coerenza detector_version) |
| Sequence state snapshot | `engine/sequence_state_snapshot.py` | PASS (2 casi: feature sicure accettate, feature non-causal-safe rifiutata) |
| Episode-first engine | `engine/sequence_episode_engine.py` | PASS (3 casi: regole mancanti→errore, COLLAPSE_TO_FIRST, NO_COLLAPSE_INDEPENDENT_HORIZON) - riusa `assign_clusters` di Phase 6.5 |
| Baseline Engine v4 adapter | `sequence_baseline_adapter_v1.py` | PASS - thin wrapper su `BaselineEngineV4` (Phase 7.0B), nessuna duplicazione |
| Outcome Surface v3 | `outcome_surface_v3.py` | PASS (3 casi: family_size corretto, outcome pre-registrato ammesso, outcome shopping bloccato) |
| Frozen spec schema | `schemas/sequence_family_frozen_spec_v1.schema.json` | Creato, incl. `direct_repeat_override` condizionale |
| Evidence record v3 schema | `schemas/sequence_evidence_record_v3.schema.json` + esempio sintetico | Creato e validato (0 campi mancanti, 0 campi extra) |
| Governance (provenance + lifecycle + failure memory) | `engine/sequence_engine_governance.py` | PASS (4 casi) - riusa direttamente `preregistration_provenance_guard.py` e `candidate_lifecycle.py` di Phase 7.0/7.1, nessun lifecycle parallelo |

## 10. Synthetic Test Suite + Dry Run E2E

`test_phase7_3_synthetic_suite.py`: **12/12 PASS** (10 casi nominati dall'utente + `outcome_overlap_rejected` + `structural_dry_run_e2e_completes`), interamente su dati sintetici (toy detector generico, nessun dato NEXUS). Durante lo sviluppo sono stati trovati e corretti 2 bug di TEST (non del motore): un'aspettativa sbagliata sul meccanismo di enforcement cross-split (`BaselineEngineV4.match()` filtra silenziosamente il pool prima del calcolo distanze, non solleva eccezione in condizioni normali - l'eccezione `CrossSplitViolation` è un controllo difensivo verificato separatamente nel red-team) e un `KeyError` nel dry-run E2E per un adapter configurato con dimensioni di match incompatibili con lo state snapshot reale. Dettagli in `phase7_3_research_journal_v1.jsonl` (J-009).

## 11. Red-Team: 10/10 attacchi bloccati

`phase7_3_red_team.py` esegue i 10 attacchi nominati (sec.17) contro i moduli **reali** (non simulazioni):

| # | Attacco | Esito | Guard/eccezione |
|---|---|---|---|
| 1 | Sequence usa barra futura | BLOCKED | `SequenceCausalityViolation` |
| 2 | Outcome usato come trigger | BLOCKED | `check_sequence_leakage` → FAIL (riuso Phase 7.2B) |
| 3 | Eventi duplicati dello stesso episodio | BLOCKED | EPISODE_VIEW collassa correttamente in 1 episodio |
| 4 | Baseline pesca dallo split successivo | BLOCKED | `CrossSplitViolation` |
| 5 | Direction mismatch | BLOCKED | Filtro direction-aware, nessun match con direzione sbagliata |
| 6 | Detector cambia dopo outcome | BLOCKED | `DetectorVersionMismatchError` (**gap nuovo, colmato in questa fase** - nessun modulo precedente lo verificava) |
| 7 | Outcome shopping | BLOCKED | `OutcomeShoppingBlocked` |
| 8 | Repeated validation access | BLOCKED | `ValidationAccessViolation` (riuso `ValidationAccessLedger` di Phase 7.0B) |
| 9 | Post-hoc parameter change (spec non committata) | BLOCKED | `PreRegistrationProvenanceError` |
| 10 | Failed idea renamed | BLOCKED | `DirectRepeatBlockedError` |

**0 blocker residui.** Durante la scrittura del red-team è stato trovato e corretto un bug di logica nel case 2 (messaggio di stampa incoerente col risultato salvato, per riuso improprio dell'helper generico `attack()`), riscritto con un try/except esplicito coerente col resto dello script.

## 12. Readiness Gate - 12/12 gate PASS

`phase7_3_engine_readiness_gate_v1.json`, gate binari (nessuna media pesata), ciascuno verificato **eseguendo realmente** lo script corrispondente (non solo controllando l'esistenza del file):

```
eligible_sequence_inventory_built:          true
detector_contract_pass:                     true
temporal_causality_guard_pass:              true
episode_first_architecture_pass:            true
baseline_v4_adapter_pass:                   true
outcome_surface_v3_contract_pass:           true
preregistration_guard_integrated:           true
lifecycle_integrated:                       true
failure_memory_integrated:                  true
synthetic_e2e_pass:                         true
red_team_pass:                              true
no_real_outcome_edge_discovery_performed:   true

READY_FOR_FIRST_SEQUENCE_DISCOVERY = TRUE
```

## Note metodologica

Come nella fase precedente: essere pronti per la prima discovery reale con il Sequence Engine **non significa** che tutte le 20 sequence siano implementabili oggi. Significa che l'infrastruttura (detector contract, causality guard, episode engine, baseline adapter, outcome surface, governance, red-team) è verificata end-to-end su dati sintetici e pronta a ricevere **una singola family frozen spec** per la prima esecuzione reale - decisione che richiede una nuova, separata autorizzazione.

## File prodotti

`server/research_scripts/phase7/phase7_3/`:
- `phase7_3_eligible_sequence_families_v1.json`, `build_eligible_sequence_families.py`
- `sequence_detector_contract_v1.json`
- `engine/sequence_causality_guard.py`, `engine/sequence_state_snapshot.py`, `engine/sequence_episode_engine.py`, `engine/sequence_engine_governance.py`
- `sequence_baseline_adapter_v1.py`, `outcome_surface_v3.py`
- `schemas/sequence_family_frozen_spec_v1.schema.json`, `schemas/sequence_evidence_record_v3.schema.json` + esempio sintetico
- `test_phase7_3_synthetic_suite.py`
- `phase7_3_red_team.py`, `phase7_3_red_team_v1.json`
- `phase7_3_research_journal_v1.jsonl`
- `build_phase7_3_engine_readiness_gate.py`, `phase7_3_engine_readiness_gate_v1.json`

---

**Commit/push eseguiti. Nessuna discovery reale senza nuova autorizzazione.**
