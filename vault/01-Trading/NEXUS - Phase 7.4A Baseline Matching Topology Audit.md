# NEXUS - Phase 7.4A Baseline Matching Topology Audit

**Baseline:** `f684813` (Phase 7.4A On-Policy Matched-Control Audit). Verifica se il rischio *sintetico* (control reuse × sovrapposizione temporale) esiste realmente nella topologia prodotta da `BaselineEngineV4` sul detector/soglia congelati (v1, invariati) applicati alla sola partition `development_discovery`. **Audit-only**: nessuna modifica al motore, nessun outcome letto/calcolato, nessuna Phase 7.4B, nessuna frozen_spec_v5.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.** Solo informazioni strutturali (event/control id/index/time, direction, split, stato categorico, match distance, reuse) — enforcement via `structural_audit_outcome_guard.py`, applicato su ogni struttura caricata/costruita.

---

## Provenance verificata

Detector `seq0015_momentum_burst_detector.py@v1` invariato, `frozen_parameters_hash` identico a quello registrato in v4 (`6c7c15c8...`), P90/252 invariati, `f684813` ancestor dell'HEAD corrente.

## 1. Algoritmo reale di matching — differenza sostanziale dalla simulazione

Ispezionati `BaselineEngineV4`, `SequenceBaselineAdapter`, `ControlReuseLedger`:

- **`ControlReuseLedger` non è mai invocato** né da `BaselineEngineV4.match()` né da `SequenceBaselineAdapter.match_sequence_event()`. Il tetto `max_control_reuse_per_run=5` esiste come modulo autonomo, testato in isolamento, ma **non è collegato alla catena di chiamata reale**.
- Per SEQ-0015, `match_dimensions=["direction","volatility_state_pre_burst","trend_state_pre_burst"]` sono **tutte categoriche** — nessuna dimensione numerica esiste per calcolare una distanza standardizzata (`_standardized_distance` ritorna sempre `None`). Di conseguenza `distances.sort(...)` non discrimina alcunché: **la selezione dei k=5 controlli preserva semplicemente l'ordine della lista `control_pool` fornita dal chiamante** (qui: indice di riga crescente) — nessun tie-break, nessun meccanismo anti-concentrazione.
- Questo **non equivale** a `_select_least_used()` della simulazione sintetica (che sceglie deliberatamente i candidati meno usati). Il motore reale, oggi, non ha alcun equivalente.

## 3. Scoperta strutturale maggiore — indipendente dal problema di reuse

Eseguito il detector frozen su `development_discovery` (righe 396–2788, 2393 barre H4):

| Vista | n |
|---|---|
| EVENT_VIEW (eventi grezzi) | 249 |
| EPISODE_VIEW (gap=3) | 210 |
| **INDEPENDENT_VIEW (embargo=39)** | **1** |

**Il tasso di innesco reale del detector (P90/252) è troppo alto rispetto a `natural_horizon=40`/`embargo=39`**: gap mediano fra episodi ≈7 barre, **100% dei gap ≤39** → l'intero periodo discovery collassa transitivamente in **una sola osservazione indipendente**. Questo è un **blocker strutturale puro** (conteggio eventi, mai un outcome) e **indipendente** dal problema di dipendenza seriale (φ=0.7) o di control-reuse: sotto i parametri congelati attuali, **nessun metodo statistico potrebbe produrre un'inferenza per SEQ-0015** — n=1 non è analizzabile da nessun test. La topologia di matching sotto è quindi calcolata su **EPISODE_VIEW (n=210)** come analisi esplorativa del comportamento del matcher, non come l'insieme che verrebbe realmente usato per un'inferenza.

## 5. Control reuse topology — molto oltre il caso sintetico peggiore

| Metrica | Valore |
|---|---|
| Eventi matchati | 210 (0 respinti per pool insufficiente) |
| Assegnazioni controllo totali | 1050 (=210×5) |
| Controlli unici usati | 83 |
| **Reuse massimo** | **37** |
| Reuse medio | 12.65 |
| Reuse mediano | 3.0 |
| Controlli che raggiungono/superano il tetto congelato (5) | 40/83 (48%) |

Istogramma bimodale: 43 controlli usati 1-3 volte, poi un salto diretto a 17-37 usi — nessuna gradualità, coerente con celle categoriche con pochi candidati disponibili che vengono "martellate".

## 6-7. Geometria temporale e overlap delle outcome window

Percentili di `|control_index_i - control_index_j|` fra controlli di eventi diversi: p10=4, **p25=25, p50=50**, p75=93 barre. Con `horizon=40`: **52.4% di tutte le coppie di eventi condivide almeno un controllo con outcome window sovrapposta** (39.9% delle singole coppie controllo-controllo).

## 8-9. Interazione reuse×geometria e grafo bipartito

I controlli più riusati (17-37 volte) sono anche i più vicini temporalmente agli eventi che li usano — esattamente l'interazione identificata nella simulazione sintetica. Il grafo bipartito (210 eventi, 83 controlli) ha **14 componenti connesse**, la più grande di 48 nodi (16.4% del totale) — non un unico blocco monolitico, ma diversi cluster densi di riuso concentrato.

## 10. Confronto con gli scenari sintetici — classificazione

**Criteri dichiarati**: `MATERIAL_MATCH` se `real_max_reuse≥5` **e** `fraction_event_pairs_overlap≥0.20`; `PARTIAL_MATCH` se una sola condizione; `LOW_MATCH` altrimenti.

- `real_max_reuse=37 ≥ 5` ✓
- `fraction_event_pairs_sharing_overlapping_control=0.524 ≥ 0.20` ✓

## **Verdetto topologico: `MATERIAL_MATCH_TO_HIGH_RISK_SYNTHETIC_GEOMETRY`**

E la severità reale (37×) **supera** nettamente lo scenario sintetico più severo testato in precedenza (reuse=5) — la classificazione è conservativa, il rischio reale è probabilmente maggiore di quanto ipotizzato.

## 11. Root cause confermata — controfattuale sugli stessi dati reali

Ricostruita la stessa topologia usando la selezione `_select_least_used()` (anziché l'ordine grezzo del motore reale) **sugli stessi identici eventi/pool**:

| | Motore reale | Controfattuale least-used-first |
|---|---|---|
| Reuse massimo | **37** | **1** |
| Controlli unici usati | 83 | 1050 |

**Il pool di candidati non è scarso** (1050 controlli unici disponibili, sufficienti per zero riuso) — la concentrazione estrema è **interamente un artefatto della mancanza di un criterio di selezione anti-concentrazione** nel motore reale, non della disponibilità di dati. La distanza numerica non è applicabile a SEQ-0015 (nessuna dimensione numerica dichiarata) quindi il confronto di "deterioramento della distanza" non si applica qui.

## Verdetto complessivo — invariato

## **PRIMARY INFERENCE METHOD NOT YET VALIDATED**

Confermato indipendente e ancora bloccante: φ=0.7 resta un blocker statistico a sé stante, indipendente da qualunque risultato di questo audit topologico.

## Implicazioni

Questo audit ha rivelato **tre fatti reali distinti**, non ipotesi sintetiche:
1. **Blocker di sample size** (INDEPENDENT_VIEW=1): il più severo, indipendente da tutto il resto — SEQ-0015, sotto i parametri attuali, non è analizzabile.
2. **Reuse/overlap combinato confermato e amplificato** (37× vs 5× ipotizzato): la simulazione sintetica era, se mai, ottimistica.
3. **Root cause meccanica identificata**: assenza di tie-breaking/anti-concentrazione in `BaselineEngineV4` per famiglie con match_dimensions puramente categoriche, e `ControlReuseLedger` mai collegato alla catena di chiamata reale.

Nessuna di queste scoperte richiede una nuova architettura statistica per essere risolta — sono problemi di **matching engine**, non di test inferenziale. Un futuro intervento (fuori scope per questo audit, che resta audit-only) dovrebbe prioritizzare: (a) rivedere `natural_horizon`/soglia per SEQ-0015 o accettare che questa family non è viabile con i parametri attuali; (b) collegare `ControlReuseLedger` alla catena di chiamata reale; (c) introdurre un tie-break esplicito (es. distanza temporale o least-used) quando le dimensioni di match sono tutte categoriche.

## Regression tests — 26/26 PASS

Copre: guard anti-leakage (nessun falso positivo su `return_direction`/`roc`), struttura e coerenza interna dell'artefatto di topologia, collasso INDEPENDENT_VIEW documentato, reuse reale supera il tetto congelato, nessun leakage nei record grezzi di match, controfattuale conferma la non-scarsità del pool, classificazione ricalcolabile deterministicamente, tutti i file congelati intatti, nessuna v5 creata, verdetto generale invariato. Nessuna regressione sulle suite precedenti.

## File prodotti

`server/research_scripts/phase7/phase7_4/`: `structural_audit_outcome_guard.py`, `baseline_matching_topology_audit.py`, `compare_topology_and_selection_audit.py`, `phase7_4_baseline_matching_topology_audit_v1.json`, `phase7_4_topology_vs_synthetic_comparison_v1.json`, `phase7_4_baseline_matching_topology_audit_tests.py`.

Nessun file del motore congelato (BaselineEngineV4, SequenceBaselineAdapter, ControlReuseLedger, detector, frozen spec v1-v4) è stato modificato — solo ispezionati/importati.

---

**NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

**Commit/push eseguiti. Verdetto topologico: MATERIAL_MATCH_TO_HIGH_RISK_SYNTHETIC_GEOMETRY (confermato e amplificato). Verdetto generale: PRIMARY INFERENCE METHOD NOT YET VALIDATED (φ=0.7 resta il blocker statistico primario indipendente). Nessuna Phase 7.4B. Nessuna frozen_spec_v5.**
