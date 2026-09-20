# NEXUS - Phase 7.4A Structural Closure + Baseline Matching Integrity Patch

**Baseline:** `0103ea0` (Phase 7.4A Baseline Matching Topology Audit). Chiude tre obiettivi: (1) corregge un errore metodologico nel controfattuale dell'audit precedente; (2) formalizza SEQ-0015 come esito strutturale distinto, non un edge refutato; (3) corregge l'infrastruttura generale di matching (autorizzata questa volta). **Nessuna edge discovery, nessun outcome letto, nessuna modifica a threshold/horizon di SEQ-0015 per "salvarla".**

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

---

## Verdetti finali

| | |
|---|---|
| **SEQ0015_STATUS** | `STRUCTURALLY_NON_VIABLE_UNDER_FROZEN_SPEC` |
| **BASELINE_ENGINE_STATUS** | `FIXED` |
| **PRIMARY_INFERENCE_METHOD** | `NOT_YET_VALIDATED` (invariato) |

## 1. Errore corretto nel controfattuale precedente

Confermato l'errore segnalato: il vecchio `compare_topology_and_selection_audit.py` ricostruiva il candidate pool a mano (`rv==vv and rt==tv`, **senza** la dimensione `direction`) — non garantito identico al pool del motore reale. **Corretto radicalmente**, non solo aggiungendo `direction`: `BaselineEngineV4.match()` ora **espone direttamente** `eligible_candidate_pool` (il pool esatto, post-filtro, usato realmente) nel proprio return value. Il nuovo confronto opera **sugli stessi pool esatti catturati dal motore reale** — mai ricostruiti a mano. `candidate_pools_changed = 0`, verificato programmaticamente (non solo dichiarato).

**Risultato validato**: motore reale patchato (`max_control_reuse_per_run=5`, tie-break deterministico) → **max_reuse=1**; controfattuale least-used-first sugli stessi pool esatti pre-patch → **max_reuse=1**. I due numeri **convergono esattamente**, confermando rigorosamente (non più solo plausibilmente) che l'assenza di tie-break era causa diretta e sufficiente.

## 4. Verdetto strutturale formale per SEQ-0015

```
EVENT_VIEW = 249 → EPISODE_VIEW = 210 → INDEPENDENT_VIEW = 1
episode_gap=3, natural_horizon=40, embargo=39
```

**`STRUCTURALLY_NON_VIABLE_UNDER_FROZEN_SPEC`** — categoria distinta e non sovrapponibile a:
- **NOT_REFUTED_EDGE**: nessun outcome è mai stato letto o calcolato.
- **NOT_INSUFFICIENT_SAMPLE**: non è "questa run ha pochi dati" (risolvibile con più storia) — è il **design** (detector+episode_gap+embargo) a essere incompatibile con l'orizzonte scelto.
- **NOT_NO_EDGE**: l'inferenza non ha mai potuto *iniziare*.

Formalizzato riusando `candidate_lifecycle.py` (nessun lifecycle parallelo): aggiunto un nuovo stato terminale **`STRUCTURALLY_NON_VIABLE`**, raggiungibile **solo da `GENERATED`** (mai da `REFUTED` — verificato negativamente che quella transizione sia vietata). Artifact: `phase7_4_seq0015_structural_failure_v1.json`.

## 5. NO RESCUE rispettato

**Nessuna modifica** a P90/252/`natural_horizon`=40/embargo=39 per rendere SEQ-0015 testabile. Una futura variante con parametri diversi dovrà essere una **nuova sequence spec/hypothesis** con nuova identità e nuova preregistrazione — mai una modifica silenziosa di SEQ-0015.

## 6-7. BaselineEngineV4 — bug confermato e corretto (autorizzato questa volta)

Confermato meccanicamente: `ControlReuseLedger` non era **mai** invocato dal motore reale → classificato **`BASELINE_MATCHING_INTEGRITY_BUG`** (ora `failure_memory_registry_v1.json:FAIL-010`, status `FIXED_IN_PHASE_7_4A`).

**Correzione generale** (non hardcoded su SEQ-0015):
- `BaselineEngineV4.__init__` accetta `max_control_reuse_per_run` (opzionale — `None` preserva il comportamento storico per candidati già conclusi come Phase 7.1 RECLAIM, retrocompatibilità verificata byte-per-byte via `canonical_sha256` invariato sugli artifact rigenerati).
- `SequenceBaselineAdapter` lo rende **obbligatorio** per ogni nuova sequence family (stesso principio di `match_dimensions`).

## 8-9. Tie-break deterministico — distanza prima, reuse poi, id infine

```
1. distanza standardizzata minima (MAI degradata dal reuse)
2. minimo utilizzo residuo corrente (ControlReuseLedger.usage_count)
3. control_id crescente (stabile, mai casuale)
```

Verificato esplicitamente: un candidato più vicino ma già riusato 5 volte batte uno mai usato ma più lontano (distanza resta primaria); a parità di distanza vince il meno riusato; a ulteriore parità vince l'id più basso, indipendentemente dall'ordine del pool in input (**stabilità verificata con 4 seed di shuffle diversi, stesso risultato**).

## Prima/dopo — topologia reale (EPISODE_VIEW, esplorativa, diagnostica)

| Metrica | PRIMA | DOPO |
|---|---|---|
| Reuse massimo | **37** | **1** |
| Reuse medio | 12.65 | 1.00 |
| Controlli unici usati | 83 | 1050 |
| Coppie di eventi con overlap geometrico | 52.4% | 10.2% |
| Componenti connesse | 14 (concentrate) | 210 (quasi 1 per evento) |
| Eventi respinti per pool insufficiente | 0 | 0 |

## 12. Il blocker di sample size resta indipendente

**Anche con il matching engine perfettamente corretto, `INDEPENDENT_VIEW=1` non cambia** (la correzione del matcher non tocca detector/episode/embargo) — **resta un blocker per SEQ-0015**, indipendente e non superato da questa patch. **Nessuna Phase 7.4B autorizzata.**

## Regression tests

- `test_phase7_4a_baseline_matching_integrity_patch.py`: **60/60 PASS** (direction inclusa, nessun controllo supera il tetto, stabilità con input shuffled, distanza numerica batte il reuse, parità distanza→reuse→id stabile, pool esaurito dopo il tetto → rifiuto esplicito, usage report corretto, cross-split safety preservata, nessun accesso a outcome).
- `phase7_4_baseline_matching_topology_audit_tests.py`: **32/32 PASS** (aggiornato per riflettere prima/dopo, convergenza reale↔controfattuale verificata).
- **Nessuna regressione** su tutte le suite precedenti (Phase 7.3, tutte le patch Phase 7.4A precedenti, Phase 7.0B preflight/red-team) — 9 suite, tutte ancora verdi.

## File prodotti/modificati

Nuovi: `build_seq0015_structural_failure.py` + `phase7_4_seq0015_structural_failure_v1.json`, `build_baseline_matching_integrity_patch_summary.py` + `phase7_4_baseline_matching_integrity_patch_v1.json`, `test_phase7_4a_baseline_matching_integrity_patch.py`.

Modificati: `engine/baseline_engine_v4.py` (reuse enforcement + tie-break deterministico + `eligible_candidate_pool` esposto), `engine/control_reuse_ledger.py` (+`usage_count()`, additivo), `engine/candidate_lifecycle.py` (+stato `STRUCTURALLY_NON_VIABLE`, additivo), `phase7_3/sequence_baseline_adapter_v1.py` (`max_control_reuse_per_run` obbligatorio), `failure_memory_registry_v1.json` (+FAIL-009, +FAIL-010), `baseline_matching_topology_audit.py` (before/after + pool esatto), `compare_topology_and_selection_audit.py` (corretto), 3 call-site aggiornati (`phase7_3_red_team.py`, `test_phase7_3_synthetic_suite.py` ×2).

Nessuna modifica a: detector SEQ-0015, frozen spec v1-v4, P90/252/episode/embargo/control-reuse-cap/outcome definitions.

---

**NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

**Commit/push eseguiti. SEQ0015_STATUS=STRUCTURALLY_NON_VIABLE_UNDER_FROZEN_SPEC. BASELINE_ENGINE_STATUS=FIXED. PRIMARY_INFERENCE_METHOD=NOT_YET_VALIDATED. Nessuna Phase 7.4B. La prossima famiglia sequence potrà usare un matching engine corretto, senza portarsi dietro questo bug.**
