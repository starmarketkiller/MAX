# NEXUS - Phase 7.5B SEQ-0009 (MECH-18 SWEEP) Structural Feasibility Result

**Formalization commit:** `b1f982b` (frozen spec, congelato PRIMA di eseguire il gate). **Baseline pre-formalizzazione:** `8593f9c` (Phase 7.5A chiusa). **Questo e' il RESULT COMMIT** - eseguito il gate strutturale reale su dati reali (`xauusd_h4_bars_p71.csv`/`market_state_dataset_p71.csv`, partition `development_discovery`), separato dal formalization commit come richiesto.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.** Nessun parametro e' stato aggiustato dopo aver visto questo risultato.

---

## Verdetto finale

| | |
|---|---|
| **FINAL STRUCTURAL VERDICT** | **`NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY`** |
| **geometry_verdict** | `NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY` |
| **matching.status** | `NOT_DECLARED` (mai valutato - la geometria e' gia' insufficiente, nulla da matchare) |
| **formalization_level** | `DETECTOR_GEOMETRY_READY` |

## Detection funnel (reale, su development_discovery)

```
n_bars discovery = 2393
raw SWEEP events (row_index in [396, 2789)) = 248
  - esclusi per regola ambigua (double-sweep stesso bar, dichiarata ex-ante) = 2
  - usati = 246 (129 HIGH-swept/SELL, 117 LOW-swept/BUY)
firing_rate = 246/2393 = 10.3%

EVENT_VIEW      = 246
EPISODE_VIEW     = 169   (episode_gap_rule=2)
INDEPENDENT_VIEW =  10   (outcome_overlap_embargo_bars=39)

minimo richiesto = 30
```

**independent_units = 10 < minimum_required_n = 30** → gate NOT_TESTABLE sulla geometria da sola. Il matching preflight (control pools per-evento realmente costruiti, vedi sotto) non e' stato eseguito perche' la geometria e' gia' insufficiente - **independent_units_with_valid_match non applicabile in questa run**.

## Cluster geometry (diagnostica)

| Metrica | Valore |
|---|---|
| episode_retention | 0.687 (169/246) |
| independence_retention | 0.059 (10/169) |
| fraction_events_in_largest_cluster | 0.589 |
| median_cluster_size (embargo) | 13.0 |
| longest_no_event_gap_bars | 84 |
| firing_geometry_risk_flag | `risk_flag=true` (median_gap_bars=6 ≤ embargo=39) - **diagnostico**, non l'autorita' (l'autorita' e' independent_units, gia' riportato sopra) |

Interpretazione strutturale: il 68.7% degli episodi locali sopravvive (SWEEP non e' un fenomeno estremamente ravvicinato come SEQ-0015), ma la seconda passata di declustering (embargo=39, derivato dall'horizon=40) comprime i 169 episodi in sole 10 unita' indipendenti - un singolo cluster raccoglie il 59% di tutti gli eventi.

## Confronto con SEQ-0015 (solo per contesto architetturale - SEQ-0015 resta chiusa)

| | SEQ-0015 (chiuso) | SEQ-0009 (questo risultato) |
|---|---|---|
| EVENT_VIEW → EPISODE_VIEW → INDEPENDENT_VIEW | 249 → 210 → 1 | 246 → 169 → **10** |
| independence_retention | 0.005 | 0.059 |
| Verdetto | NOT_TESTABLE (post-hoc, scoperto dopo l'intero contratto statistico) | **NOT_TESTABLE (scoperto in un run, prima di qualunque contratto statistico)** |

Questo e' esattamente il cambio di processo cercato: la stessa classe di scoperta (design non testabile su questa partition) ottenuta in **un singolo run outcome-blind**, non dopo una lunga catena metodologica.

## Direction semantics (verificate, non ri-derivate qui)

`PER_EVENT_DIRECTION`, mapping `swept_side`: `HIGH→SELL` (129 eventi), `LOW→BUY` (117 eventi) - derivato dal campo gia' emesso dal detector, coerente con la convenzione di segno del codice.

## Matching spec (dichiarato e costruito, non eseguito)

`match_dimensions=[volatility_state_pre_event]`, `k=5`, `minimum_control_count=20`, `max_control_reuse_per_run=5`. **Bug concreto trovato e corretto durante questa esecuzione** (autorizzato dall'istruzione "salvo bug concreto"): il gate non supportava pool di controllo distinti per evento, necessari perche' l'esclusione per sovrapposizione outcome (`|r-t|<=40`) e' intrinsecamente per-evento, non globale - aggiunto un parametro opzionale e retro-compatibile `control_pool_by_event_row` a `run_matching_preflight`/`evaluate_matching_feasibility` (118/118 test, incl. 4 nuovi, PASS). I control pool per-evento sono stati realmente costruiti per tutti i 246 eventi in questo run, ma il matching non e' stato eseguito perche' la geometria ha gia' fallito.

## Deliverables prodotti

- `seq0009_frozen_structural_spec_v1.json` (formalization commit `b1f982b`)
- `seq0009_structural_feasibility_result_v1.json` (questo commit) - detection funnel, cluster geometry, feasibility ratios, matching runtime construction, verdetto completo
- `test_seq0009_frozen_spec.py` (26/26 PASS, formalization commit)
- `run_seq0009_structural_feasibility.py` (script di esecuzione, questo commit)
- Estensione minima e retro-compatibile del gate (`control_pool_by_event_row`), con test dedicato

## Confermato

- **NO NEXUS OUTCOME DATA ACCESSED** - solo `xauusd_h4_bars_p71.csv`/`market_state_dataset_p71.csv` (OHLC + feature CAUSAL_SAFE), mai `outcomes_v1.csv`/`outcome_surface_v3.py`.
- **NO EDGE DISCOVERY PERFORMED** - nessuna statistica di outcome calcolata.
- **NO STATISTICAL CONTRACT BUILT** - nessun BH/test/outcome surface.
- SEQ-0015 resta `CLOSED_NOT_REEXAMINED_AS_CANDIDATE`.
- Nessun parametro del formalization commit e' stato modificato dopo aver visto questo risultato (no-rescue clause rispettata).

---

**SEQ-0009 e' `NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY`** sulla partition `development_discovery` con il design congelato in `b1f982b` - scoped a quella partition, mai un'affermazione di impossibilita' universale (stessa semantica gia' corretta per SEQ-0015/FAIL-009). Una futura variante (nuova finestra dati, nuovo episode_gap/embargo, nuovo livello di riferimento) richiederebbe una nuova identita' e una nuova preregistrazione - non un secondo tentativo su `SEQFAM-SEQ0009-SWEEP-STRUCTURAL-V1`.

Questo si ferma qui, come da istruzione: nessuna lettura di outcome, nessuna nuova family formalizzata, nessuna ulteriore espansione dell'infrastruttura oltre al bug concreto corretto sopra.
