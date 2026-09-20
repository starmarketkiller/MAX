# NEXUS - Phase 7.5A Sequence Structural Feasibility Gate

**Baseline:** `7b9d64b` (Phase 7.4A Structural Verdict Semantics Patch - **SEQ-0015 CHIUSA**, non riesaminata come candidato in questa fase). Introduce un gate strutturale GENERALE, applicabile a qualunque futura sequence family, da eseguire subito dopo la formalizzazione minima del detector e PRIMA di outcome contract/statistical test selection/BH family/validation access.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

---

## Verdetti finali

| | |
|---|---|
| **SEQ0015_STATUS** | `CLOSED_NOT_REEXAMINED_AS_CANDIDATE` (invariato, vedi Phase 7.4A) |
| **GATE_STATUS** | `IMPLEMENTED_AND_REGRESSION_TESTED` |
| **FAIL-004** | `MECHANICALLY_BLOCKABLE_NOW` (chiuso - era `NOT_YET_MECHANICALLY_BLOCKABLE`) |
| **FAIL-009** | `MECHANICALLY_BLOCKABLE_NOW`, generalizzato (era gia' chiuso ma scoped a SEQ-0015) |
| **5 remaining eligible families (SEQ-0001/0009/0014/0016/0020)** | tutte `NEEDS_DETECTOR_FORMALIZATION` |

## 1. Perche' questa fase

Phase 7.4A ha mostrato che un detector formalmente corretto (formula/soglia congelate, direction policy verificata causale) puo' comunque essere **eseguibile solo sulla carta**: la sua geometria di innesco/clustering, applicata alla partition `development_discovery` gia' congelata, ha compresso `EVENT_VIEW=249 -> EPISODE_VIEW=210 -> INDEPENDENT_VIEW=1` (minimo richiesto 30) - scoperto **dopo** aver costruito l'intero contratto di preregistrazione statistico per SEQ-0015. Il miglioramento architetturale di questa fase sposta quel controllo **prima**:

```
PRIMA: formalizzazione -> preregistrazione -> statistica -> (a volte) n_effettivo inutilizzabile
ORA:   formalizzazione minima -> STRUCTURAL FEASIBILITY PREFLIGHT -> solo se passa: preregistrazione statistica
```

## 2. Architettura del gate

`server/research_scripts/phase7/engine/sequence_structural_feasibility_gate.py` - outcome-blind, deterministico, riusa meccanica gia' esistente e testata (`sequence_episode_engine.py` per EVENT/EPISODE/INDEPENDENT_VIEW, `dependence_diagnostics.assign_clusters` per la geometria dei cluster, `BaselineEngineV4`/`ControlReuseLedger` per il matching preflight - nessuna nuova logica di matching o di clustering reimplementata).

**Input richiesti (fail-closed, sec.2):** `sequence_family_id`, `detector_frozen`, `detector_source_ref`, `detector_parameters`, `observation_timing`, `event_direction_policy`, `episode_gap_rule`, `overlap_policy`, `proposed_natural_horizon`, `proposed_outcome_overlap_embargo_bars`, `discovery_partition`, `minimum_evidence_gates`, `event_row_indices`. Se anche un solo campo manca, il gate **non calcola nulla** e restituisce `NEEDS_DETECTOR_FORMALIZATION` con l'elenco esatto dei campi assenti - nessun default inventato per farlo girare comunque.

**Detection funnel** (sec.3): `EVENT_VIEW -> EPISODE_VIEW -> INDEPENDENT_VIEW`, `n_bars`, `firing_rate`, percentili del gap (p10/p25/p50/p75/p90), nessun outcome.

**Cluster geometry** (sec.4): cluster indipendenti (soglia = embargo) e cluster locali (soglia = episode_gap_rule) separati - stessa distinzione concettuale gia' in `sequence_episode_engine.py` (espansione fisica locale vs indipendenza statistica dell'outcome). Riporta size distribution, max/median cluster size, frazione di eventi nel cluster piu' grande, frazione di gap sotto l'embargo, gap piu' lungo senza eventi - esattamente le metriche che avrebbero reso visibile il caso SEQ-0015 immediatamente.

**Feasibility ratios** (sec.5): `episode_retention = EPISODE_VIEW/EVENT_VIEW`, `independence_retention = INDEPENDENT_VIEW/EPISODE_VIEW`, `independent_units_per_year` (quando `bars_per_year` e' fornito), `independent_units_over_minimum_required`.

**Verdetto fail-closed** (sec.6): `FEASIBLE` (`independent_units >= 1.5x` il minimo richiesto **e** entrambe le retention sopra il floor 0.30) / `BORDERLINE_FEASIBILITY` (sopra il minimo ma margine fragile) / `NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY` (sotto il minimo **sulla partition proposta** - scoped, mai un claim di impossibilita' universale, stessa correzione gia' applicata a SEQ-0015/FAIL-009). Nessun claim universale in nessuno dei tre stati.

**Firing-rate guard geometrico** (sec.7, **chiude FAIL-004**): sostituisce/affianca il guard a percentuale fissa gia' esistente (`event_firing_rate_guard.py`, mantenuto solo come diagnostica secondaria) con un check basato sulla geometria risultante - `median_gap_bars (EVENT_VIEW) <= outcome_overlap_embargo_bars proposto` ⇒ `PATHOLOGICAL_FOR_HORIZON`. Verificato con un caso di test esplicito: un detector con `firing_rate=0.04%` (fortemente raro) ma eventi concentrati in un blocco ravvicinato e' comunque classificato `PATHOLOGICAL_FOR_HORIZON` - "evento raro" non e' equiparato meccanicamente a "buono".

**Matching preflight** (sec.8): simula il matching strutturale (`n matched`/`rejected`, reuse, qualita', determinismo del tie-break) riusando `BaselineEngineV4`/`ControlReuseLedger` senza modifiche - **richiede feature di stato reali**, quindi non invocato per nessuna delle 5 family rimaste (nessun detector formalizzato produce ancora feature reali per loro).

**Provenance** (sec.12): ogni esecuzione registra `detector_source_ref`, hash canonico dei parametri e dello spec, `discovery_partition`, `engine_version`, `policy_version`, `outcome_blind=true`, `deterministic=true`.

## 3. Policy e thresholds

`server/research_scripts/phase7/phase7_5/sequence_structural_feasibility_policy_v1.json` - stesso stile di `minimum_evidence_gates.json` (ogni soglia classificata `POLICY_THRESHOLD` con rationale esplicito, mai un numero senza motivazione):

| Soglia | Valore | Status |
|---|---|---|
| `feasible_margin_multiplier` | 1.5 | POLICY_THRESHOLD |
| `episode_retention_borderline_floor` | 0.30 | POLICY_THRESHOLD |
| `independence_retention_borderline_floor` | 0.30 | POLICY_THRESHOLD |
| `n_nominal_minimum` (riusato) | 30 | da `minimum_evidence_gates.json`, invariato |

Il ranking del candidate queue e' dichiarato **esclusivamente strutturale** (testabilita', geometria, completezza detector, fattibilita' matching, chiarezza implementativa) - mai probabilita' di edge/expected profitability/likelihood of success. Verificato meccanicamente da `test_ranking_is_structural_only_no_edge_fields`.

## 4. Risultato per le 5 family rimaste

Fonte inventario: `phase7_3_eligible_sequence_families_v1.json` (eligible dopo SEQ-0015, che resta chiusa e non e' stata riesaminata). Ogni family e' stata fatta girare **realmente** attraverso `evaluate_family_structural_feasibility()` con SOLO i campi gia' noti nel repo (`market_sequence_registry_v1.json`, detector Phase 5 esistenti dove applicabile) - nessun parametro inventato.

| Sequence | Detector status | Verdetto | Gradi di liberta' mancanti (principali) |
|---|---|---|---|
| **SEQ-0009** (MECH-18, SWEEP) | detector grezzo **gia' esistente** in `phase5/build_events.py` (`sweep_v1_range20`, `sweep_lookback_n=20`) | `NEEDS_DETECTOR_FORMALIZATION` | episode_gap_rule, natural_horizon, outcome_overlap_embargo, dimensioni di stato pre-evento per il matching - mai dichiarati per SEQ-0009 come sequence standalone (finora solo prerequisito di RECLAIM) |
| **SEQ-0001** (MECH-01, trend sostenuto) | nessun detector in codice | `NEEDS_DETECTOR_FORMALIZATION` | soglia numerica su `directional_efficiency` per "sostenuto", finestra in barre H4 (oggi solo "mesi"), episode_gap_rule/natural_horizon/embargo assenti |
| **SEQ-0014** (MECH-23, low-information/chop) | nessun detector in codice | `NEEDS_DETECTOR_FORMALIZATION` | soglia su `directional_efficiency`/`atr_percentile`/`variance_ratio_proxy`, **definizione stessa di `event_a_index`** (e' uno stato, non un evento puntuale) prima ancora di episode/horizon/embargo |
| **SEQ-0016** (MECH-26, banda di volatilita') | nessun detector in codice | `NEEDS_DETECTOR_FORMALIZATION` | formula della "banda" non congelata, `trend_state` derivato non esiste come feature nominata, direction ancora `CONTEXT_DEPENDENT` (non un policy BUY/SELL/NO_EVENT operativo) |
| **SEQ-0020** (MECH-33, incrocio EMA) | nessun detector in codice | `NEEDS_DETECTOR_FORMALIZATION` | finestre corta/lunga non congelate, soglia di divergenza minima assente (rischio FAIL-004 non ancora verificabile), **possibile ridondanza con `ema_slope_atr_norm` gia' esistente** da risolvere prima di scrivere un nuovo detector |

Tutti i raw feature dipendenti (`directional_efficiency`, `atr_percentile`, `ema_slope_atr_norm`, `ema_slope_raw`, `variance_ratio_proxy`) **esistono gia'** in `feature_registry_v2.json` - il gap non e' nei dati/feature di base, ma nella formalizzazione a livello di sequence (soglie, episode/horizon/embargo, stato di matching).

**Nessuna delle 5 family e' `STRUCTURALLY_BLOCKED_ON_CURRENT_PARTITION`** in questa run - non perche' siano state verificate FEASIBLE, ma perche' nessuna ha ancora un detector abbastanza formalizzato perche' il gate possa calcolare una geometria reale. Questo e' il risultato **atteso e corretto** di eseguire il preflight prima della formalizzazione, non un fallimento del gate.

## 5. Candidate queue

`phase7_5_candidate_queue_v1.json` - ranking esclusivamente strutturale:

- **READY_FOR_PREREGISTRATION:** nessuna.
- **STRUCTURALLY_BLOCKED_ON_CURRENT_PARTITION:** nessuna.
- **NEEDS_DETECTOR_FORMALIZATION** (ordinata per completezza strutturale, non per punteggio di edge):
  1. `SEQ-0009` - detector grezzo gia' esistente in codice (6 gradi di liberta' mancanti, il minimo delle 5).
  2. `SEQ-0001`, `SEQ-0014`, `SEQ-0016`, `SEQ-0020` - nessun detector in codice ancora (8 gradi di liberta' mancanti ciascuna).

## 6. Failure memory aggiornata

- **FAIL-004** (`EVENT_FIRING_RATE_ABOVE_INFORMATIVE_THRESHOLD`): `NOT_YET_MECHANICALLY_BLOCKABLE` → **`MECHANICALLY_BLOCKABLE_NOW`**. Il guard decisivo e' ora geometrico (gap mediano vs embargo), non una percentuale fissa di firing - il vecchio guard a soglie fisse resta attivo solo come diagnostica secondaria.
- **FAIL-009** (`INDEPENDENT_VIEW_COLLAPSE_ON_PREREGISTERED_PARTITION`): gia' `MECHANICALLY_BLOCKABLE_NOW` ma scoped alla scoperta manuale su SEQ-0015 - `detection_mechanism` generalizzato per puntare al gate generale, da eseguire per **qualunque** family futura prima di ogni accesso a outcome.

## 7. Regression suite - 53/53 PASS

`test_phase7_5_structural_feasibility_gate.py`: rifiuto fail-closed di spec incompleti (nessun default inventato), replay sintetico della geometria SEQ-0015 **gia' pubblicata** (249→...→1, verificato che il gate l'avrebbe segnalata come `NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY` con causa esplicita nel firing-rate guard - nessun nuovo dato, nessun outcome, nessuna nuova indagine su SEQ-0015), casi `FEASIBLE`/`BORDERLINE_FEASIBILITY`/`NOT_TESTABLE` sintetici distinti, prova esplicita che il guard di firing-rate non e' una soglia percentuale fissa, geometria dei cluster completa, matching preflight deterministico e rispettoso del tetto di reuse dichiarato, provenance completa e deterministica, assenza meccanica di qualunque campo che assomigli a uno score di edge, coerenza fra policy JSON e default nel codice, e verifica statica che il modulo del gate non importi alcun percorso di outcome/dati reali NEXUS. Nessuna regressione sulla suite Phase 7.4A esistente (20/20 PASS, invariata).

## 8. File creati/modificati

**Nuovi:** `server/research_scripts/phase7/engine/sequence_structural_feasibility_gate.py`, `phase7_5/build_sequence_structural_feasibility_policy.py` + `phase7_5/sequence_structural_feasibility_policy_v1.json`, `phase7_5/build_phase7_5_structural_feasibility_results.py` + `phase7_5/phase7_5_structural_feasibility_results_v1.json` + `phase7_5/phase7_5_candidate_queue_v1.json`, `phase7_5/test_phase7_5_structural_feasibility_gate.py`, questo report.

**Modificati:** `failure_memory_registry_v1.json` (FAIL-004 chiuso, FAIL-009 generalizzato).

**Invariati:** tutto Phase 7.4A/SEQ-0015 (frozen spec v1-v4, detector, matcher, verdetti), `BaselineEngineV4`, `ControlReuseLedger`, `sequence_episode_engine.py` (solo importato, mai modificato).

---

**Confermato: SEQ-0015 resta CHIUSA e non e' stata riesaminata come candidato. NESSUN dato outcome NEXUS e' stato letto. NESSUNA edge discovery e' stata eseguita.** Prossimo passo (non iniziato in questa fase, per istruzione esplicita): scegliere quale delle 5 family formalizzare per prima e avviare una Phase 7.5B di formalizzazione detector + ri-esecuzione del gate su dati reali.
