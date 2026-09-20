# NEXUS - Phase 7.4A Structural Verdict Semantics Patch

**Baseline:** `f883c17` (Phase 7.4A Structural Closure + Baseline Matching Integrity Patch, fix del matching engine **accettato e invariato**). Corregge due formulazioni scientifiche troppo forti/ambigue nel record - **nessuna modifica al matcher, nessun outcome letto, nessuna Phase 7.4B**.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

---

## Verdetti finali

| | |
|---|---|
| **BASELINE_ENGINE_STATUS** | `FIXED` (invariato, accettato) |
| **SEQ0015_STATUS** | `FROZEN_EXPERIMENT_NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY_PARTITION` |
| **PRIMARY_INFERENCE_METHOD** | `NOT_YET_VALIDATED` (invariato) |

## 1-2. L'errore concettuale corretto

L'evidenza disponibile dimostra con forza:

```
development_discovery congelata: n_bars=2393
EVENT_VIEW=249 → EPISODE_VIEW=210 → INDEPENDENT_VIEW=1
minimum required=30
```

→ **il test preregistrato di SEQ-0015 non è eseguibile sulla partition discovery congelata.**

Il record precedente affermava invece che "il design non può **MAI** produrre un numero sufficiente di osservazioni indipendenti, **indipendentemente dalla quantità di dati disponibili**" - un claim **non dimostrato**. Basta immaginare una serie più lunga con un gap fra cluster di eventi >39 barre: il clustering transitivo si interromperebbe e si avrebbero ≥2 unità indipendenti, potenzialmente molte di più con abbastanza storia. `INDEPENDENT_VIEW=1` sulla discovery partition **non implica matematicamente** che resterà ~1 con arbitrariamente più dati.

**Corretto ovunque**: rimossi tutti i claim "MAI"/"indipendentemente dalla quantità di dati" da `candidate_lifecycle.py`, `failure_memory_registry_v1.json` (FAIL-009), `phase7_4_seq0015_structural_failure_v1.json`.

## 2-3. Categoria corretta e distinzione da INSUFFICIENT_SAMPLE

Il concetto di fallimento strutturale è **mantenuto** (non è un ordinario "n=25 invece di 30"), ma **ridefinito con precisione**:

- **`STRUCTURALLY_NON_VIABLE`** (nome dello stato lifecycle, **non rinominato** - vedi sec.6): ridefinito come *"il design congelato non soddisfa il gate di campione minimo indipendente **sulla partition preregistrata attuale**"* - nessun claim oltre quella partition.
- **`SEQ0015_STATUS`** (campo di report, libero da vincoli del lifecycle enum): rinominato in **`FROZEN_EXPERIMENT_NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY_PARTITION`**, la formulazione precisa suggerita.
- **Distinzione da INSUFFICIENT_SAMPLE ordinario**: quest'ultimo presume che il processo sperimentale sia valido e che più dati risolverebbero il problema *senza toccare il design*; qui il **meccanismo di clustering** del design comprime 210 episodi in 1 unità **sulla partition già fissata** - il test pre-registrato non è eseguibile senza **ridefinire l'esperimento** (nuova partition, nuova provenance, nuova preregistrazione - mai un'estensione silenziosa della stessa run).

## 4. Direction semantics - verificata coerente, solo terminologia

Confermato in `baseline_contract_v4.json:direction_aware.rule`: *"Un evento BUY riceve SOLO controlli **valutati come ipotetico** BUY"* - la parola "ipotetico" è nel contratto stesso. Il codice (`control_direction_by_id = {cid: direction for cid in control_pool_same_split}`) è **esattamente coerente** con questo design dichiarato - **nessuna modifica al codice**. Corretta solo la documentazione: la direzione del controllo è una **direction-conditioned counterfactual baseline** ("cosa sarebbe successo se quella barra fosse stata negoziata nella stessa direzione dell'evento?"), non una proprietà osservata indipendentemente della barra di controllo. Commento esplicativo aggiunto in `sequence_baseline_adapter_v1.py`.

## 6. Lifecycle - nome mantenuto, semantica corretta

Lo stato `STRUCTURALLY_NON_VIABLE` in `candidate_lifecycle.py` **non è stato rinominato** (introdotto solo nella patch precedente, nessun risultato storico da migrare) - la sua docstring è stata riscritta per rimuovere il claim universale, sostituendolo con la definizione scoped-to-partition, più un paragrafo di correzione esplicito che documenta l'errore e la sua correzione per trasparenza. Il campo `SEQ0015_STATUS` (libero, non vincolato all'enum del lifecycle) porta invece il nome preciso suggerito.

## 7. Regression tests - 20/20 PASS

`test_phase7_4a_structural_verdict_semantics.py`: nessun claim di impossibilità universale in nessun artifact (scansione con allowlist esplicito per i campi/paragrafi di correzione, per evitare il classico falso positivo autoreferenziale - stesso pattern già usato per `structural_audit_outcome_guard.py`), status precisato, FAIL-009 corretto, docstring del lifecycle corretta, direction correttamente etichettata come counterfactual, evidenza esplicitamente scoped alla partition, nessuna v5, nessuna modifica ai file frozen, verdetti generali (`BASELINE_ENGINE_STATUS=FIXED`, `PRIMARY_INFERENCE_METHOD=NOT_YET_VALIDATED`) invariati. Nessuna regressione su tutte e 9 le suite precedenti.

## File modificati (nessuna nuova logica di matching/inferenza)

`engine/candidate_lifecycle.py` (docstring `STRUCTURALLY_NON_VIABLE` corretta), `failure_memory_registry_v1.json` (FAIL-009 riformulato, signature aggiornata), `phase7_3/sequence_baseline_adapter_v1.py` (commento esplicativo, nessun cambio di comportamento), `build_seq0015_structural_failure.py` + `phase7_4_seq0015_structural_failure_v1.json` (status e claim corretti), nuovo `test_phase7_4a_structural_verdict_semantics.py`.

Nessuna modifica a: `BaselineEngineV4`, `ControlReuseLedger`, `SequenceBaselineAdapter` (comportamento), detector SEQ-0015, frozen spec v1-v4.

---

**NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

**Commit/push eseguiti. BASELINE_ENGINE_STATUS=FIXED. SEQ0015_STATUS=FROZEN_EXPERIMENT_NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY_PARTITION. PRIMARY_INFERENCE_METHOD=NOT_YET_VALIDATED. Nessuna Phase 7.4B. Con questa correzione, Phase 7.4A è considerata chiusa - nessun ulteriore lavoro su SEQ-0015. Il prossimo passo naturale è una nuova sequence family, usando fin dall'inizio il matcher corretto e un firing-rate/independent-unit feasibility check prima di investire nel contratto inferenziale.**
