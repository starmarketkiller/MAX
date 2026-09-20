# NEXUS - Phase 7.5A Directional Matching Fidelity Final Patch

**Baseline:** `21dba60` (Phase 7.5A Structural Gate Integration & Geometry Semantics Patch). Patch finale e strettamente circoscritta - corregge una fedelta' direzionale mancante fra il matching preflight e la pipeline reale, piu' un bug minore di stato. **Nessuna nuova sequence family formalizzata, nessun outcome letto, nessuna edge discovery.**

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

---

## Verdetti finali

| | |
|---|---|
| **DIRECTION_DERIVATION** | fail-closed, enum canonico a 4 valori, nessun fallback a BOTH |
| **MATCHING_DIRECTION_SEMANTICS** | replica esatta di `SequenceBaselineAdapter` (verificata per parita' diretta) |
| **FORMALIZATION_LEVEL_BUG** | corretto - nuovo stato intermedio `MATCHING_SPEC_READY_AWAITING_RUNTIME_DATA` |
| **MATCHED_K_SHORTFALL** | auditato, semantica CONGELATA (inclusa in `independent_units_with_valid_match`, invariata) |
| **SEQ0015_STATUS** | `CLOSED_NOT_REEXAMINED_AS_CANDIDATE` (invariato) |
| **5 remaining eligible families** | tutte `NEEDS_DETECTOR_FORMALIZATION` (invariato) |
| **Regression suite** | 114/114 PASS (era 81/81 prima di questa patch) |

## 1. I due problemi trovati in review

1. **Fallback silenzioso a BOTH.** `compute_detection_funnel` accettava `direction_by_row` come parametro OPZIONALE con `direction_by_row = direction_by_row or {r: "BOTH" ...}` - una family con `event_direction_policy=BUY` poteva quindi essere testata strutturalmente come non-direzionale senza alcun errore, violando fail-closed.
2. **Mappa di direzione globale invece di per-evento.** `run_matching_preflight()` accettava `control_direction_by_id` una sola volta per l'intero run - ma la pipeline reale (`sequence_baseline_adapter_v1.py:SequenceBaselineAdapter.match_sequence_event`) costruisce `control_direction_by_id = {cid: event_direction for cid in pool}` **fresca ad ogni chiamata**, per OGNI evento. Per una family con eventi sia BUY sia SELL, lo stesso control bar deve poter essere valutato come ipotetico BUY per un evento e ipotetico SELL per un altro - impossibile con una mappa statica.

Più un bug minore: `DECLARED_AWAITING_DATA` (matching_spec completo, nessun dato reale) veniva classificato `MATCHING_PREFLIGHT_READY` come se il preflight fosse gia' stato eseguito.

## 2. Direction derivation contract

`event_direction_policy` e' ora vincolato a 4 valori canonici (`server/research_scripts/phase7/engine/sequence_structural_feasibility_gate.py`):

| Valore | Derivazione riga |
|---|---|
| `FIXED_BUY` | ogni riga -> `BUY` |
| `FIXED_SELL` | ogni riga -> `SELL` |
| `NON_DIRECTIONAL` | ogni riga -> `BOTH`, ma dichiarato **esplicitamente** (non un default) |
| `PER_EVENT_DIRECTION` | richiede `direction_by_row` **completo** per ogni riga grezza - fail-closed su qualunque riga mancante |

I vecchi valori narrativi (`BOTH`/`CONTEXT_DEPENDENT`, ereditati da `market_sequence_registry_v1.json`) **non sono piu' ammessi** per questo gate - `missing_spec_fields()` li rifiuta esplicitamente. `resolve_direction_by_row()` deriva la mappa row->direzione meccanicamente, senza alcun fallback; il parametro `direction_by_row` di `evaluate_family_structural_feasibility()` (la falla originale) e' stato **rimosso** - l'unica via d'ingresso e' ora lo spec dichiarato.

## 3. Come il preflight replica SequenceBaselineAdapter

`run_matching_preflight()` non accetta piu' `control_direction_by_id`. La nuova funzione `_match_one_event()` costruisce `{cid: ev["direction"] for cid in control_pool}` **per ogni singolo evento**, byte-per-byte la stessa regola di `SequenceBaselineAdapter.match_sequence_event()`. Verificato con un **test di parita' diretta**: un'istanza reale di `SequenceBaselineAdapter` e il preflight ricevono lo stesso scenario (E1=BUY, E2=SELL, stesso pool) e producono status/control-picks identici; una seconda dimostrazione (pool ridotto a `k`, forza la condivisione) prova che lo **stesso control bar** riceve `control_direction="BUY"` per E1 e `control_direction="SELL"` per E2.

## 4. Formalization-level bug corretto

Nuovo stato esplicito `MATCHING_SPEC_READY_AWAITING_RUNTIME_DATA` (matching_spec completo, dati reali non ancora disponibili) - `MATCHING_PREFLIGHT_READY` ora significa **esclusivamente** "il preflight e' stato eseguito per davvero" (`EXECUTED_FEASIBLE`/`EXECUTED_INFEASIBLE`).

## 5. MATCHED_K_SHORTFALL - decisione congelata (non cambiata automaticamente)

Auditato come richiesto: `independent_units_with_valid_match` **include** le osservazioni `MATCHED_K_SHORTFALL` insieme a `MATCHED` (stessa definizione di `build_quality_report`, gia' in uso in tutta Phase 7, mai modificata). Rationale: `k` e' un obiettivo di ricchezza/riduzione-varianza del baseline, non un requisito di correttezza stretto - un evento con meno di `k` controlli (ma sopra `minimum_control_count`) ha comunque un baseline statisticamente valido. Trasparenza aggiunta: `n_matched_full_k`/`n_matched_k_shortfall` ora riportati separatamente nel risultato del preflight per audit.

## 6. Provenance estesa

`provenance["direction_derivation"]` (sempre presente: `event_direction_policy`, `direction_map_hash`) e, quando il matching viene eseguito, `provenance["matching"]` include anche `event_direction_policy`, `direction_source`, `direction_map_hash`, `counterfactual_direction_semantics=true`.

## 7. Regression suite - 114/114 PASS (era 81/81)

Nuovi test: `FIXED_BUY` non diventa mai `BOTH`; `FIXED_SELL`; `NON_DIRECTIONAL` esplicito; `PER_EVENT_DIRECTION` con riga mancante fallisce fail-closed; valori legacy (`BOTH`/`CONTEXT_DEPENDENT`) rifiutati; **parita' diretta contro `SequenceBaselineAdapter`** su scenario misto BUY/SELL + dimostrazione forzata dello stesso control bar con direzioni diverse; `DECLARED_AWAITING_DATA != MATCHING_PREFLIGHT_READY`; `EXECUTED_FEASIBLE == MATCHING_PREFLIGHT_READY`; pool di controllo shuffled -> stessi risultati; provenance con i nuovi campi direzionali. Nessuna regressione sui 4 controesempi A/B/C/D della patch precedente, ne' sulle altre 9 suite Phase 7 (tutte 0 FAIL).

## 8. Le 5 family - invariate

Rieseguito `build_phase7_5_structural_feasibility_results.py` senza inventare alcun parametro: tutte e 5 (`SEQ-0001/0009/0014/0016/0020`) restano `NEEDS_DETECTOR_FORMALIZATION`. Aggiunta solo una nota esplicita per family sul fatto che `event_direction_policy` dovra' diventare uno dei 4 valori canonici in fase di formalizzazione (SEQ-0009/SEQ-0001/SEQ-0020 quasi certamente `PER_EVENT_DIRECTION`, SEQ-0014 gia' correttamente `NON_DIRECTIONAL`, SEQ-0016 `CONTEXT_DEPENDENT` da risolvere). Candidate queue invariata nelle categorie (nessuna family raggiunge il livello matching in questa run).

## 9. File modificati

`engine/sequence_structural_feasibility_gate.py` (`ENGINE_VERSION@v3`: `resolve_direction_by_row`, `DirectionDerivationError`, enum canonico, `_match_one_event`, formalization-level a 3 stati, provenance estesa), `phase7_5/build_sequence_structural_feasibility_policy.py` + `sequence_structural_feasibility_policy_v1.json` (nuove sezioni `direction_derivation_contract`, `direction_fidelity_fix`, `matched_k_shortfall_semantics`), `phase7_5/build_phase7_5_structural_feasibility_results.py` + risultati/queue rigenerati, `phase7_5/test_phase7_5_structural_feasibility_gate.py` (+33 check).

**Invariati:** tutto Phase 7.4A/SEQ-0015, `BaselineEngineV4`, `ControlReuseLedger`, `SequenceBaselineAdapter` (solo importato/riusato, mai modificato), `sequence_episode_engine.py`.

---

**Confermato: SEQ-0015 resta CHIUSA e non e' stata riesaminata. NESSUN dato outcome NEXUS e' stato letto. NESSUNA edge discovery e' stata eseguita.** Con questa patch la pipeline di preflight e' completa e fedele alla semantica reale:

```
DETECTOR COMPLETENESS -> EVENT GEOMETRY -> INDEPENDENT SAMPLE YIELD -> BASELINE MATCHING FEASIBILITY (fedele a SequenceBaselineAdapter) -> READY FOR PREREGISTRATION
```

**Punto fermo su Phase 7.5A.** Prossimo passo: formalizzare **SEQ-0009** (detector SWEEP gia' esistente in Phase 5 - la piu' vicina strutturalmente ad avere un detector operativo, non per profittabilita' attesa) - episode_gap_rule/natural_horizon/outcome_overlap_embargo/direction_derivation/matching_spec - poi ri-eseguire questo gate su dati reali. Nessun'altra espansione del framework prevista salvo un bug concreto trovato durante l'uso.
