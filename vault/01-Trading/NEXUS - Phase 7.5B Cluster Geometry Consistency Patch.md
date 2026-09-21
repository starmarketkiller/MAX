# NEXUS - Phase 7.5B SEQ-0009 Cluster Geometry Consistency Patch

**Baseline:** `3498606` (SEQ-0009 structural feasibility RESULT - verdetto accettato). Corregge un'incoerenza concreta nel report di geometria trovata in review - **il verdetto di SEQ-0009 non cambia**.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

---

## Verdetto (invariato)

```
EVENT_VIEW=246 -> EPISODE_VIEW=169 -> INDEPENDENT_VIEW=10
minimum_required_n=30
FINAL VERDICT: NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY
```

detector, `episode_gap_rule=2`, `proposed_natural_horizon=40`, `proposed_outcome_overlap_embargo_bars=39`, `matching_spec` - **tutti invariati** (verificato: nessun diff su `seq0009_frozen_structural_spec_v1.json`, 26/26 check di coerienza interna ancora PASS).

## 1. Root cause

`compute_cluster_geometry()` applicava l'embargo **direttamente ai raw event row** (`assign_clusters(raw_rows, embargo)`), producendo `n_independent_clusters=8`. Ma `INDEPENDENT_VIEW` (l'autorita' reale usata dal gate) e' costruito da `build_outcome_independent_view` con **due passate distinte**: raw events → rappresentanti di `EPISODE_VIEW` (via `episode_gap_rule`) → embargo clustering **sui rappresentanti**, dando `INDEPENDENT_VIEW.n=10`. Le due geometrie misurano cose diverse e venivano etichettate con lo stesso nome (`n_independent_clusters`).

## 2. Fix

`compute_cluster_geometry` ora riceve anche `episode_representative_rows` (esposti da `compute_detection_funnel` in `EPISODE_VIEW.representative_rows`, calcolati dalla STESSA chiamata a `build_event_and_episode_views` gia' usata per il funnel - nessuna riimplementazione) e produce due blocchi **esplicitamente separati**:

- **`raw_event_embargo_geometry`** - diagnostica sui raw event, embargo diretto, MAI l'autorita'.
- **`inferential_independent_geometry`** - stessa identica costruzione di `INDEPENDENT_VIEW` (rappresentanti di episodio → embargo), `n_independent_clusters` **deve** coincidere con `detection_funnel.INDEPENDENT_VIEW.n`.

## 3. Invariant meccanico (fail-closed)

Aggiunta `ClusterGeometryInconsistencyError`, sollevata in `evaluate_family_structural_feasibility()` se `inferential_independent_geometry.n_independent_clusters != detection_funnel.INDEPENDENT_VIEW.n` - un'inconsistenza futura non produrrebbe piu' un report silenziosamente errato.

## 4. Controesempio sintetico obbligatorio

`test_cluster_geometry_raw_and_inferential_can_genuinely_differ`: 3 mini-episodi ravvicinati (gap interno=1, gap fra episodi=3), `episode_gap_rule=1`, `embargo=3` → **raw clustering = 1 cluster** (i micro-gap "pontano" transitivamente i gap piu' larghi), **inferential clustering = 3 cluster** (i micro-gap sono gia' rimossi dalla rappresentazione episodica). Riproduce esattamente il meccanismo del bug reale (SEQ-0009: 8 vs 10) su un caso piccolo e verificato per costruzione.

## 5. SEQ-0009 - diagnostiche rigenerate

| | Vecchio (etichettato erroneamente) | Nuovo - `raw_event_embargo_geometry` (diagnostica) | Nuovo - `inferential_independent_geometry` (autorita') |
|---|---|---|---|
| n cluster | 8 | **8** (invariato, ma ora etichettato correttamente come diagnostica raw, mai cancellato) | **10** ✅ = `INDEPENDENT_VIEW.n` |
| max_cluster_size | 145 | 145 | 82 |
| median_cluster_size | 13.0 | 13.0 | 8.0 |
| fraction in largest | 0.589 | 0.589 (su raw events) | 0.485 (su rappresentanti episodio) |

Il vecchio valore **8** non e' stato cancellato silenziosamente - resta visibile in `raw_event_embargo_geometry.n_clusters`, ora esplicitamente etichettato come diagnostica sui raw event, mai la geometria inferenziale.

## 6. Regressione

**132/132 PASS** su `test_phase7_5_structural_feasibility_gate.py` (era 118) - incluso l'invariant su ogni spec valido e il controesempio sintetico obbligatorio. **26/26 PASS** su `test_seq0009_frozen_spec.py` (invariato). **Nessuna regressione** sulle altre 9 suite Phase 7 (11 suite totali, 0 FAIL).

## 7. Conferme

- Detector, direction policy, `episode_gap_rule`, `proposed_natural_horizon`, embargo, `matching_spec`: **invariati**.
- Verdetto finale SEQ-0009: **invariato** (`NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY`).
- **NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**
- SEQ-0015 resta chiusa, non riesaminata.

## File modificati

`engine/sequence_structural_feasibility_gate.py` (`compute_cluster_geometry` riscritta, nuova `ClusterGeometryInconsistencyError`, `EPISODE_VIEW.representative_rows` esposto, invariant fail-closed), `phase7_5/test_phase7_5_structural_feasibility_gate.py` (+14 check, incl. controesempio sintetico), `phase7_5/build_sequence_structural_feasibility_policy.py` + JSON (sezione `cluster_geometry_consistency`), `phase7_5b/seq0009_structural_feasibility_result_v1.json` (rigenerato, solo diagnostiche - stesso verdetto).

---

**SEQ-0009 e' ora davvero archiviabile:** `NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY` su `development_discovery`, con un report di geometria internamente coerente e meccanicamente verificato. Il nuovo processo ha funzionato due volte in questa fase - prima nello scoprire in un solo run che il design non e' testabile su questa partition, poi nel far emergere e correggere un bug di reporting concreto prima di archiviare il risultato. Nessun'altra family avviata, come da istruzione.
