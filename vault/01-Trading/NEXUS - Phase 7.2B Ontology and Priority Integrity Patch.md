# NEXUS - Phase 7.2B: Ontology & Priority Integrity Patch

**Baseline:** `327af16` (Phase 7.2, chiusa). Nessuna discovery, nessun outcome NEXUS letto, nessun accesso a development/validation/holdout, nessun backtest - solo correzione metodologica del corpus/ontologia/scoring gia' prodotti.

**Conferma esplicita: NO NEXUS OUTCOME DATA USED IN PHASE 7.2B.** Verificato strutturalmente da `phase7_3_readiness_gate_v1.json` (gate `no_nexus_outcome_data_accessed`): scan automatico di ogni script di questa fase per riferimenti a market_state/outcomes/validation/holdout NEXUS - **0 offender trovati**.

**READY_FOR_PHASE_7_3 = TRUE.**

---

## 1. Contradiction vs Conditional Branch

**0 vere contraddizioni restano verificate** nel corpus. I 2 gruppi originariamente registrati come CONTRADICTION in Phase 7.2 (CG-0001: sweep+reclaim→reversal vs sweep-senza-reclaim→continuazione; CG-0002: breakout→accettazione vs breakout→fallimento) **non soddisfano la definizione rigorosa** (stesso information set ex-ante, stesso observation time, stessa definizione di setup, esiti opposti): in entrambi i casi le due posizioni divergono perche' osservano una TRANSITION diversa DOPO lo stesso evento comune, non perche' fanno affermazioni opposte sullo stesso stato al medesimo istante.

**Entrambi riclassificati come CONDITIONAL_BRANCH** (`conditional_branch_registry_v1.json`, CBG-0001/CBG-0002) - `contradiction_registry_v1.json` aggiornato (schema_version 2) con i gruppi originali marcati SUPERSEDED, non cancellati, per trasparenza del processo.

## 2. Semantic Leakage Guard

Applicato a tutte e **20 le sequence** (`sequence_semantic_leakage_guard_v1.json`):

| Verdetto (as-described) | N | Dopo correzione |
|---|---|---|
| PASS | 11 | 11 PASS |
| NEEDS_REFORMULATION | 9 | 9 PASS (corrette) |
| FAIL (circolarita' non risolvibile) | 0 | - |

**Nessuna sequence e' risultata strutturalmente circolare** (outcome==trigger) - tutte le 9 formulazioni problematiche erano risolvibili allineando `prediction_start` al reale completamento della transition. Le 9 corrette: SEQ-0003, SEQ-0004, SEQ-0005, SEQ-0010, SEQ-0011, SEQ-0012, SEQ-0013, SEQ-0017, SEQ-0018 - tutte ora hanno campi espliciti `observation_cutoff`/`transition_completion_time`/`prediction_start`/`outcome_window` in `market_sequence_registry_v1.json`, e `implementation_status` degradato a `NEEDS_ADDITIONAL_SPECIFICATION` dove prima era `READY_FOR_FORMALIZATION` (nessuna sequence corretta e' stata silenziosamente ri-approvata).

**Caso piu' rilevante**: SEQ-0012 (sweep senza reclaim → continuazione) - il ramo era definito dall'ASSENZA di reclaim entro l'intero orizzonte dichiarato, informazione disponibile solo a fine finestra; se implementata con un ingresso immediato ("scommessa" sulla continuazione subito dopo lo sweep), sarebbe stato un vero lookahead. Corretta esplicitando che `prediction_start` deve coincidere con la scadenza confermata della finestra di non-reclaim.

## 3-4. Independent Evidence Clustering & Hindsight Awareness

**2 independent_evidence_cluster** identificati e fusi (`evidence_cluster_registry_v1.json`):
- **ECLU-0001**: Radovan Vojtko & Cyril Dujava - stesso studio pubblicato su SSRN (SRC-0014) E Quantpedia (SRC-0015), titolo identico.
- **ECLU-0002**: Mathias Mesfin - stesso paper arXiv (2605.04004) citato via URL `/abs/` (SRC-0016) e `/pdf/` (SRC-0066) da due agenti di ricerca diversi senza rendersene conto.

**Non fusi** (stesso autore, studi/articoli genuinamente diversi): Allan Munene Mutiiria (4 articoli MQL5 distinti), tiptoptrade (2 articoli distinti), tflab (2 articoli distinti).

`research_priority_scoring_rule_v2.json`: `external_evidence_transparency` ora conta CLUSTER indipendenti a Q3/Q4 (non fonti/claim grezzi); nuovo decimo componente `hindsight_awareness` penalizza le sequence supportate prevalentemente da claim con `hindsight_risk=HIGH`.

## 5. Priority Ranking v1 vs v2

**6 sequence HIGH_RESEARCH_PRIORITY in v2** (erano 8 in v1):

| Sequence | v1 | v2 | Cambiamento |
|---|---|---|---|
| SEQ-0016 MEAN_REVERSION_BAND_TOUCH | 17 HIGH | 18 HIGH | invariata |
| SEQ-0003 BREAKOUT_ACCEPTANCE | 18 HIGH | 17 HIGH | invariata (transparency 2→1, implementation_status degradato) |
| SEQ-0004 BREAKOUT_FAILURE | 18 HIGH | 17 HIGH | invariata (transparency 2→1, implementation_status degradato) |
| SEQ-0001 TREND_PERSISTENCE | 16 HIGH | 17 HIGH | invariata |
| SEQ-0009 LIQUIDITY_SWEEP | 15 HIGH | 16 HIGH | invariata |
| SEQ-0014 TREND_CHOP_REGIME | 15 HIGH | 16 HIGH | invariata |
| **SEQ-0012 SWEEP_WITHOUT_RECLAIM** | **16 HIGH** | **13 MEDIUM** | **RIMOSSA da HIGH** - leakage guard + evidence transparency + hindsight |
| **SEQ-0005 VOL_COMPRESSION** | **14 HIGH** | **12 MEDIUM** | **RIMOSSA da HIGH** - leakage guard + evidence transparency (0 cluster Q3/Q4 indipendenti) |

**Nessuna sequence aggiunta a HIGH.** Nessun punteggio modificato manualmente - dettaglio completo con `reason_for_change` per ogni sequence in `research_priority_queue_v2.json`.

## Blocker residui / stato di readiness per Phase 7.3

14 sequence su 20 restano `NEEDS_ADDITIONAL_SPECIFICATION` o `NOT_IMPLEMENTABLE_AS_DESCRIBED` (gap di dati/pipeline gia' dichiarati in Phase 7.2 - multi-timeframe, VWAP, calendario macro/culturale, secondo strumento cointegrato - piu' i 9 ora esplicitamente rietichettati per chiarezza di timing). Questo NON blocca `READY_FOR_PHASE_7_3` (il gate valuta la COERENZA dell'infrastruttura di readiness, non richiede che ogni sequence sia gia' pronta all'implementazione).

## Red-team / regression (sec.8)

6/6 casi nominati verificati (`test_phase7_2b_regressions.py`): stesso antecedente+esito opposto→CONTRADICTION; stesso antecedente+transition diversa→CONDITIONAL_BRANCH; trigger osservato prima dell'outcome→causal safe; trigger che userebbe una barra futura→leakage rilevato; 1 fonte Q4+10 Q0 ≠ 10 fonti Q4 indipendenti (verificato: transparency=1 vs transparency=2); paper+blog stesso autore stesso studio→1 solo cluster (verificato su ECLU-0001 reale).

## Readiness Gate

`phase7_3_readiness_gate_v1.json` - **6/6 gate PASS**: `ontology_branching_clean`, `semantic_leakage_guard_pass`, `priority_score_v2_generated`, `hindsight_penalty_active`, `independent_evidence_clustering_active`, `no_nexus_outcome_data_accessed`. **`unresolved_blockers: []`. `ready_for_phase_7_3: true`.**

---

## Deliverables

`server/research_scripts/phase7/phase7_2/`:
- `conditional_branch_registry_v1.json` (nuovo), `contradiction_registry_v1.json` (aggiornato, schema_version 2)
- `sequence_semantic_leakage_guard.py`, `sequence_semantic_leakage_guard_v1.json`, `apply_leakage_guard_and_ontology_update.py`
- `market_sequence_registry_v1.json` (aggiornato: 5 nuovi campi per sequence), `schemas/market_sequence_schema_v1.json` (aggiornato)
- `evidence_cluster_registry_v1.json` (nuovo)
- `research_priority_scoring_rule_v2.json`, `research_priority_queue_v2.json`, `build_priority_queue_v2.py`
- `phase7_3_readiness_gate_v1.json`, `build_phase7_3_readiness_gate.py`
- `test_phase7_2b_regressions.py` (6 casi)
- `phase7_2_research_journal_v1.jsonl` (aggiornato con 5 nuove entry)

## Vincoli rispettati

Nessuna discovery eseguita; nessun outcome NEXUS letto; nessun accesso a development/validation/holdout; nessun backtest su alcuna sequence; nessun punteggio aggiustato manualmente per ottenere un ranking desiderato; commit/push su main; nessuna Phase 7.3 avviata.
