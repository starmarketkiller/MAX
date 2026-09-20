# NEXUS - Phase 7.5A Structural Gate Integration and Geometry Semantics Patch

**Baseline:** `fbfab21` (Phase 7.5A Sequence Structural Feasibility Gate). Corregge due problemi architetturali trovati in review nel gate appena introdotto - **nessuna nuova sequence family formalizzata, nessun outcome letto, nessuna edge discovery**.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

---

## Verdetti finali

| | |
|---|---|
| **GATE_STATUS** | `run_matching_preflight() ORA INTEGRATO nel verdetto composito` |
| **FIRING_RATE_GUARD_SEMANTICS** | `CORRETTA - median_gap e' un flag diagnostico, mai un'autorita'` |
| **FAIL-004** | `MECHANICALLY_BLOCKABLE_NOW` (invariato, detection_mechanism corretto) |
| **SEQ0015_STATUS** | `CLOSED_NOT_REEXAMINED_AS_CANDIDATE` (invariato) |
| **5 remaining eligible families** | tutte `NEEDS_DETECTOR_FORMALIZATION` (invariato - nessuna formalizzata) |
| **Regression suite** | 81/81 PASS (era 53/53 prima della patch) |

## 1. I due problemi trovati in review

1. **Matching preflight non integrato**: `run_matching_preflight()` esisteva ma non veniva mai chiamato da `evaluate_family_structural_feasibility()`, e gli input di matching non facevano parte del contratto richiesto - una family poteva ricevere `FEASIBLE` basandosi solo su `EVENT_VIEW -> EPISODE_VIEW -> INDEPENDENT_VIEW`, anche se il matching reale (`BaselineEngineV4`) avrebbe respinto meta' degli eventi per pool insufficiente.
2. **Firing-rate guard troppo forte**: `median_gap_bars <= embargo => PATHOLOGICAL_FOR_HORIZON` non e' un'implicazione matematicamente sufficiente - un detector con gap mediano sotto l'embargo puo' comunque produrre abbastanza unita' indipendenti se un numero sufficiente di gap grandi spezza la catena transitiva del clustering (`assign_clusters`). Controesempio: 100 gap totali, 60 piccoli (10 barre) + 40 grandi (100 barre) - la mediana e' sotto l'embargo=39 ma i 40 gap grandi generano 41 cluster indipendenti.

## 2. Architettura corretta: due livelli, verdetto composito

`server/research_scripts/phase7/engine/sequence_structural_feasibility_gate.py` (v2) distingue ora esplicitamente:

```
DETECTOR_GEOMETRY_READY   -> geometry_verdict (FEASIBLE / BORDERLINE_FEASIBILITY / NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY)
        +
MATCHING_PREFLIGHT_READY  -> matching.status (NOT_DECLARED / DECLARED_AWAITING_DATA / EXECUTED_FEASIBLE / EXECUTED_INFEASIBLE)
        =
verdict finale composito (_compose_final_verdict)
```

**Geometry verdict** (`_classify_geometry_verdict`, logica invariata dalla v1): `FEASIBLE`/`BORDERLINE_FEASIBILITY`/`NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY`, basato su `independent_units` (dai cluster REALI, `assign_clusters`) confrontato con `minimum_required_n`.

**Matching verdict** (`evaluate_matching_feasibility`, nuovo): richiede `spec["matching_spec"]` completo (`match_dimensions`, `k`, `minimum_control_count`, `max_control_reuse_per_run`, `state_feature_definitions`, `control_pool_construction_policy`, `split_boundaries` - nomi canonici allineati a `BaselineEngineV4`/`baseline_contract_v4.json`, non reinventati) **e** `spec["matching_runtime_data"]` (feature di stato reali) prima di poter eseguire il preflight per davvero. Se manca anche solo una feature per una delle osservazioni INDEPENDENT_VIEW, solleva `MatchingRuntimeDataIncompleteError` - mai una feature inventata. Il gate di campione minimo e' **ricalcolato** su `independent_units_with_valid_match` (le sole osservazioni indipendenti che hanno REALMENTE ottenuto un match, non `REJECTED_INSUFFICIENT_POOL`) - un evento strutturalmente indipendente ma senza baseline valida non entra nell'esperimento.

**Composizione** (`_compose_final_verdict`):

```
geometry_verdict == NOT_TESTABLE                         -> NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY (matching non valutato)
matching.status in (NOT_DECLARED, DECLARED_AWAITING_DATA) -> NEEDS_MATCHING_FORMALIZATION
matching.status == EXECUTED_INFEASIBLE                    -> MATCHING_STRUCTURALLY_INFEASIBLE
matching.status == EXECUTED_FEASIBLE                       -> eredita geometry_verdict (FEASIBLE/BORDERLINE_FEASIBILITY)
```

Una geometria `FEASIBLE` da sola **non produce piu' `FEASIBLE`** - produce `NEEDS_MATCHING_FORMALIZATION` finche' il matching non e' stato dichiarato ed eseguito con successo. Regression test dedicato: `test_geometry_feasible_without_matching_spec_is_not_feasible`.

## 3. Correzione di semantica del firing-rate guard

`classify_firing_geometry_risk_flag()` (rinominata da `classify_geometry_firing_rate_guard`) produce ora un `risk_flag` **booleano diagnostico** (`median_gap_bars <= embargo`), mai un verdetto pseudo-autorevole - rimossi interamente `PATHOLOGICAL_FOR_HORIZON`/`COMPATIBLE_WITH_HORIZON` dal codice (verificato meccanicamente da `test_no_pathological_verdict_word_survives_in_risk_flag`). L'**unica autorita'** che classifica l'incompatibilita' strutturale resta `independent_units` (cluster reali) vs `minimum_required_n` - il gap mediano e' riportato accanto come segnale di rischio, mai come causa sufficiente.

## 4. Controesempi sintetici obbligatori (81/81 PASS totali)

| Caso | Setup | Atteso | Risultato |
|---|---|---|---|
| **A** | 46 cluster (138 eventi, 92 gap piccoli=10 + 45 gap grandi=100) → mediana=10≤39 | `risk_flag=True` MA `geometry_verdict=FEASIBLE` (46≥1.5×30) | ✅ confermato |
| **B** | 20 eventi tutti ravvicinati (gap=5), firing_rate=0.04% | `NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY` nonostante firing_rate bassissimo | ✅ confermato |
| **C** | Geometria ampia (60 unita' indipendenti) ma pool di controllo di 2 (< minimum_control_count=5) | non `READY_FOR_PREREGISTRATION` → `MATCHING_STRUCTURALLY_INFEASIBLE` | ✅ confermato |
| **D** | Stessa geometria + pool di controllo ampio (40, ben sopra il minimo) | `FEASIBLE` (equivalente a READY_FOR_PREREGISTRATION) | ✅ confermato |

## 5. Provenance estesa

Quando il matching preflight viene REALMENTE eseguito, `provenance["matching"]` registra in aggiunta: `baseline_engine_version` (`BaselineEngineV4.CONTRACT_VERSION`), `matching_spec_hash`, `max_control_reuse_per_run`, `matching_result_hash` - tutti sha256 canonici, verificati da `test_counterexample_D_matching_provenance_has_*`.

## 6. FAIL-004 aggiornato

`failure_memory_registry_v1.json`: `detection_mechanism` corretto per riflettere che l'autorita' e' `independent_units` (funnel/geometria reale), **non** `median_gap_bars<=embargo` da solo - quest'ultimo resta un flag diagnostico. Documentato esplicitamente il controesempio 60+40 gap. `status` invariato: `MECHANICALLY_BLOCKABLE_NOW`. FAIL-009 aggiornato per menzionare il ricalcolo del gate su `independent_units_with_valid_match`.

## 7. Le 5 family rimaste - invariate

Rieseguito `build_phase7_5_structural_feasibility_results.py` **senza modificare** `FAMILY_KNOWN_STATE` (nessun parametro inventato, come richiesto): tutte e 5 (`SEQ-0001/0009/0014/0016/0020`) restano `NEEDS_DETECTOR_FORMALIZATION` - nessuna ha ancora superato il livello 1 (geometria), quindi il livello 2 (matching) non viene nemmeno valutato per nessuna di esse in questa run. `phase7_5_candidate_queue_v1.json` ora espone anche le categorie `NEEDS_MATCHING_FORMALIZATION` e `MATCHING_STRUCTURALLY_INFEASIBLE` (entrambe vuote in questa run) accanto a `READY_FOR_PREREGISTRATION`/`STRUCTURALLY_BLOCKED_ON_CURRENT_PARTITION`/`NEEDS_DETECTOR_FORMALIZATION`. Nessun ranking di edge.

## 8. Regression suite

`test_phase7_5_structural_feasibility_gate.py`: **81/81 PASS** (era 53/53 prima di questa patch) - copre i 4 controesempi obbligatori, il rifiuto fail-closed di `matching_spec`/`matching_runtime_data` incompleti (mai inventati), la correzione centrale (`geometry FEASIBLE senza matching_spec != FEASIBLE`), l'errore fail-closed su feature di evento mancanti, la sparizione meccanica del linguaggio `PATHOLOGICAL_FOR_HORIZON`/`COMPATIBLE_WITH_HORIZON`, provenance estesa, determinismo, e coerenza fra policy JSON e default codice (incluso il nuovo `required_matching_spec_inputs`). Nessuna regressione sulle altre 9 suite Phase 7 (verificate invariate).

## 9. File modificati

`engine/sequence_structural_feasibility_gate.py` (riscritto: `ENGINE_VERSION@v2`, nuove funzioni `evaluate_matching_feasibility`/`missing_matching_spec_fields`/`_compose_final_verdict`, rinominata `classify_firing_geometry_risk_flag`), `phase7_5/sequence_structural_feasibility_policy_v1.json` (+ builder, nuove sezioni `required_matching_spec_inputs`/`formalization_levels`/`composite_verdict_composition`/`sample_gate_recalculation_on_matched_units`, sezione firing-rate-guard corretta), `phase7_5/phase7_5_structural_feasibility_results_v1.json` + `phase7_5_candidate_queue_v1.json` (rigenerati, nuove categorie), `phase7_5/test_phase7_5_structural_feasibility_gate.py` (riscritto, +28 check), `failure_memory_registry_v1.json` (FAIL-004/FAIL-009 corretti).

**Invariati:** tutto Phase 7.4A/SEQ-0015, `BaselineEngineV4`, `ControlReuseLedger`, `sequence_episode_engine.py` (solo importati).

---

**Confermato: SEQ-0015 resta CHIUSA e non e' stata riesaminata. NESSUN dato outcome NEXUS e' stato letto. NESSUNA edge discovery e' stata eseguita.** Con questa patch, la pipeline di preflight e' completa:

```
DETECTOR COMPLETENESS -> EVENT GEOMETRY -> INDEPENDENT SAMPLE YIELD -> BASELINE MATCHING FEASIBILITY -> READY FOR PREREGISTRATION
```

Prossimo passo (non iniziato in questa fase): scegliere SEQ-0009 come prima family da formalizzare (piu' vicina strutturalmente ad avere un detector operativo, per completezza, non per profittabilita' attesa) e avviare una Phase 7.5B di formalizzazione detector + episode/horizon/embargo + matching_spec, poi ri-eseguire questo gate su dati reali.
