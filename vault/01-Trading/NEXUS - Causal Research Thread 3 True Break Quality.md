# NEXUS Causal Research Thread 3 — True Break Quality: Continuation vs Failure

Segue la chiusura del Thread 2 ([[NEXUS - Structural Causal Experiment 3 Economic Bridge]], verdict `STRUCTURAL_HYPOTHESIS_REFUTED_FINAL`). Nuovo filone: dato un TRUE_BREAK già avvenuto, esistono feature causali note in quel momento che predicono CONTINUATION vs FAILURE? **Non riaperte** le ipotesi del Thread 2 (`penetration_per_atr > 0.058713928652578955`, `age_seconds<1h`, `source_tf=D1`) — usate eventualmente solo come feature candidate fra molte altre su un target diverso, mai come ipotesi da salvare.

## 1. Dataset e periodi

Riusati **tutti** i dati grezzi già raccolti in questo thread (nessuna nuova run del Tester necessaria, tranne l'export M1 mancante per `w0`, generato ora con lo stesso script `NXS_ResearchExportBars.mq5` già usato per le altre finestre):

| Finestra | Periodo | Ruolo |
|---|---|---|
| wA | 2025-05-01 → 2025-09-01 | DISCOVERY |
| w0 | 2025-09-01 → 2026-01-01 | DISCOVERY |
| w1 | 2026-01-01 → 2026-03-01 | VALIDATION |
| w2 | 2026-03-01 → 2026-05-01 | VALIDATION |
| w3 | 2026-05-01 → 2026-07-01 | VALIDATION |
| w4 | 2026-07-01 → 2026-08-25 | VALIDATION |

Split cronologico puro (DISCOVERY = 2025-05-01→2026-01-01, VALIDATION = 2026-01-01→2026-08-25), nessun overlap, nessun random split.

## 2. Population e ricostruzione

Stesso `assign_episodes()`/`build_episode_lifecycle_index()` (chiavi `(window_id, event_id)`) applicato a **tutti e 6** i gruppi di eventi combinati in una sola chiamata (il raggruppamento interno è già per `(structural_level_id, window_id)`, quindi corretto anche con finestre multiple insieme).

| Check | Esito |
|---|---|
| Orphan TRUE_BREAK | **0** |
| Malformed rows | **0** |
| Episodi con almeno un TRUE_BREAK | 349 |
| Esclusi (esito da evento `lifecycle_redundant_after_close`/`true_break_after_close`) | **242 (69.3%)** |
| **TRUE_BREAK validi in population** | **107** |

L'esclusione è molto alta (quasi 7 su 10) — riflette la stessa causa già documentata nell'audit di linkage e negli esperimenti precedenti: il desync multi-TF-pass di `NXS_CollectAllSignals` produce frequentemente eventi lifecycle "ridondanti dopo chiusura" o TRUE_BREAK non affidabili. Non è un artefatto di questa analisi — è la stessa policy di esclusione già validata nel Thread 2, applicata qui senza modifiche.

## 3. Sample sufficiency (verifica obbligatoria PRIMA di ogni analisi di feature)

| | n |
|---|---|
| TRUE_BREAK totali validi | 107 |
| PLUS_1R_FIRST | 29 |
| MINUS_1R_FIRST | 31 |
| AMBIGUOUS_SAME_BAR (esclusi dall'analisi primaria) | 47 (**43.9%**) |
| CENSORED | 0 (0.0%) |
| **RISOLTI totali (PLUS_1R_FIRST + MINUS_1R_FIRST)** | **60** |
| BUY | 54 |
| SELL | 53 |

L'ambiguity rate (43.9%) è coerente con quanto già osservato in tutti gli esperimenti precedenti di questo thread (R=25 pip fisso è stretto rispetto alla volatilità H4 di GOLD) — non è la causa principale dell'insufficienza campionaria, che deriva soprattutto dall'alto tasso di esclusione per esito post-close (§2).

**60 < 150 (soglia minima dichiarata).**

## 4. Stop condition applicata

Per istruzione esplicita: *"Se dopo l'esclusione ambiguous restano meno di 150 outcome risolti totali, NON fare discovery multivariata. In quel caso: verdict HOLD_INSUFFICIENT_TRUE_BREAK_SAMPLE e fermati."*

Nessuna analisi univariata, nessuna regressione logistica, nessun albero decisionale è stata eseguita. Nessuna feature è stata testata. Nessun pattern è stato osservato o può essere riportato.

## 5. Retest — solo conteggio, come richiesto per completezza

Non essendo stata eseguita l'analisi principale, il conteggio retest viene comunque riportato per trasparenza (il dataset raw è disponibile in `results/causal_thread3_true_break_quality/thread3_at_true_break.csv` per un'eventuale fase futura con più dati), ma **non è stato usato per alcuna decisione**.

## 6. Limitations

- La causa principale dell'insufficienza campionaria (69.3% di esclusione per esito post-close) è un limite architetturale pre-esistente e documentato (desync multi-TF-pass), non un difetto di questa analisi — ma **impatta pesantemente la potenza disponibile** per qualunque analisi futura su `AT_TRUE_BREAK` con questa instrumentazione.
- Per raggiungere una popolazione sufficiente servirebbe uno dei seguenti, nessuno eseguito qui (fuori scope per questo task, che usa solo dati già disponibili): (a) più storico raccolto, (b) una correzione del desync multi-TF-pass alla fonte (fuori scope, tocca la logica di SH_BMS_RTO), (c) un secondo consumer strumentato con lifecycle proprio oltre a SH_BMS_RTO (fuori scope dichiarato nelle fasi precedenti).
- Il dataset grezzo (107 righe, incluse le 47 ambiguous) resta disponibile e riutilizzabile senza dover rieseguire il Tester, se in futuro si decide di espandere il periodo storico.

## Verdict

### **HOLD_INSUFFICIENT_TRUE_BREAK_SAMPLE**

n_risolti = 60, sotto la soglia dichiarata di 150. Nessuna discovery multivariata eseguita. Nessun pattern trovato o riportato, perché nessuna analisi di feature è stata condotta.
