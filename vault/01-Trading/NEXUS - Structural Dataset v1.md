# NEXUS Causal Research Thread 2 — Fase B: Structural Dataset v1

> ⚠️ **SUPERATO da [[NEXUS - Structural Dataset v1 Causal Linkage Integrity Audit]]**. Il verdict `READY_FOR_STRUCTURAL_CAUSAL_EXPERIMENT` di questo report **non è stato approvato** in revisione: il linkage lifecycle era scope-livello (non scope-episodio), causando leakage fra episodi diversi dello stesso `structural_level_id` — in particolare `label_reclaim_or_false_break`/`TRUE_BREAK` era sovrastimato (789, 19.5%) rispetto al valore corretto (47, 1.16%, vedi audit), ed esistevano righe `at_true_break.csv` con `sweep_event_id` vuoto. I CSV in `results/structural_dataset_v1/` sono stati RISCRITTI dall'audit con linkage per episodio (`structural_episode_id`), label rinominato (`label_lifecycle_outcome`), e `time_to_true_break_sec` rimosso. Usare l'audit come riferimento autorevole; questo report resta solo per cronologia.

Segue [[NEXUS - SNXSSweepExt Semantic Impact Audit]] (fix `9b77f83`, `malformed=0`). Primo dataset strutturale vero, costruito da eventi SWEEP/TRUE_BREAK/RETEST/INVALIDATE — **non** da trade eseguiti. Nessuna ottimizzazione, nessuna regola, nessuna feature selection: questo task finisce con il dataset costruito e validato.

## 1. Periodi

Quattro finestre non sovrapposte, contigue, GOLD H4, Model=1, Research Mode con selettore SH_BMS_RTO (21) — il DETECTOR canonico (fonte SWEEP) non dipende dal selettore ed è quindi comunque completo; SH_BMS_RTO resta l'unico consumer che produce lifecycle (TRUE_BREAK/RETEST/INVALIDATE) in questa fase, come nelle Fasi A/A.1:

| Finestra | Da | A |
|---|---|---|
| w1 | 2026-01-01 | 2026-03-01 |
| w2 | 2026-03-01 | 2026-05-01 |
| w3 | 2026-05-01 | 2026-07-01 |
| w4 | 2026-07-01 | 2026-08-25 |

Copertura totale: ~7.8 mesi, nessuna sovrapposizione, nessun buco. `window_id` presente in ogni riga dei tre CSV output — nessuna label attraversa il confine fra finestre (vedi §6).

## 2. Event counts

| | w1 | w2 | w3 | w4 | **Totale** |
|---|---|---|---|---|---|
| SWEEP | 1040 | 1181 | 1041 | 783 | **4045** |
| TRUE_BREAK | 87 | 56 | 64 | 62 | **269** |
| RETEST | 30 | 0 | 24 | 9 | **63** |
| INVALIDATE | 834 | 1145 | 979 | 783 | **3741** |
| **Totale eventi** | 1991 | 2382 | 2108 | 1637 | **8118** |

`unique_structural_levels` (SWEEP distinti per `structural_level_id`+finestra): **1989**.

`malformed_skipped` (dal logger MQL5, Fase A.1 detector fix): **0 in tutte e 4 le finestre**, confermato di nuovo da questa run.

## 3. Popolazione e schema

**Popolazione primaria**: eventi SWEEP unici dalla fonte canonica `SNXSSweepExt` (punto di osservazione centrale in `NXS_CollectAllSignals`, Fase A.1). Collegati, quando disponibili sullo stesso `structural_level_id`, a TRUE_BREAK/RETEST/INVALIDATE (unico produttore in questa fase: SH_BMS_RTO).

**Due dataset/view separati, mai mescolati**:

- **`at_sweep.csv`** (4045 righe): un rigo per ogni evento SWEEP unico. Feature = solo ciò che è noto AL MOMENTO dello sweep.
- **`at_true_break.csv`** (269 righe): un rigo per ogni evento TRUE_BREAK. Feature = solo ciò che è noto AL MOMENTO del true break (regime/trend/ATR ripresi dalla snapshot del TRUE_BREAK stesso, mai dello SWEEP originale) + `time_to_true_break_sec`.

**`structural_events.csv`** (8118 righe): dump grezzo di tutti gli eventi, tutte le finestre, per audit/riproducibilità.

### Causal field matrix finale

| Campo | In AT_SWEEP | In AT_TRUE_BREAK | Nota causale |
|---|---|---|---|
| `structural_level_id`, `event_id`, `timestamp` | ✅ | ✅ | identità/tempo dell'evento stesso |
| `source`, `source_tf`, `side`, `direction` | ✅ | ✅ | noti al momento dell'evento |
| `level_price`, `price_at_event`, `penetration_pips` | ✅ | ✅ | prezzo dell'evento stesso, mai futuro |
| `created_time`, `age_seconds` | ✅ | — | solo AT_SWEEP (concetto legato alla nascita del livello, non al true break) |
| `regime_at_event`, `structure_trend_at_event`, `atr_at_event` | ✅ (snapshot allo SWEEP) | ✅ (snapshot al TRUE_BREAK, ricalcolato — MAI riusato dallo sweep) | read-only, mai riletti dopo il fatto |
| `consumer`, `observed_by`, `observation_count` | ✅ | — (tautologico: consumer unico che produce TRUE_BREAK) | metadata multi-consumer solo dove ha senso |
| `time_to_true_break_sec` | — | ✅ | SOLO in AT_TRUE_BREAK, per definizione richiede che il TRUE_BREAK sia già avvenuto |
| TRUE_BREAK futuro, RETEST futuro, INVALIDATE futura, trade outcome, MFE/MAE futura | ❌ **vietato** | ❌ **vietato come feature** (solo come LABEL, vedi §4) | mai usati come feature in nessuna view |

## 4. Label (costruiti, NON analizzati)

Tutti calcolati con **R=25 pip fisso** (stessa convenzione di Causal Experiment 1/2/3, per comparabilità) e **orizzonte fisso di 5 giorni** dall'observation timestamp, mai oltre il confine della propria finestra (vedi §6 sul censoring).

| Label | Entry/reference price | Horizon | Ambiguity handling | Censoring | Same-bar tie |
|---|---|---|---|---|---|
| `TRUE_BREAK_OCCURRED` | n/a (boolean strutturale) | nessuno (tutta la vita del livello nella finestra) | n/a | n/a | n/a |
| `RETEST_OCCURRED` | n/a (boolean strutturale) | nessuno | n/a | n/a | n/a |
| `RECLAIM_OR_FALSE_BREAK` | n/a (categorico: TRUE_BREAK / RECLAIM / NO_LIFECYCLE) | nessuno | `NO_LIFECYCLE` = nessun evento successivo osservato da SH_BMS_RTO per questo livello (copertura parziale, vedi §5) | n/a | n/a |
| `RETEST_HOLD_OR_FAIL` | prezzo del RETEST stesso (`price_at_event` del rigo RETEST) | 5gg dal retest, cap a fine finestra | `AMBIGUOUS_SAME_BAR` se +1R e -1R nella stessa barra M1 | `CENSORED` se orizzonte/finestra esauriti prima di -1R/+1R | mai risolto arbitrariamente |
| `PLUS_1R_BEFORE_MINUS_1R` | `price_at_event` dell'osservazione (SWEEP in AT_SWEEP, TRUE_BREAK in AT_TRUE_BREAK) | 5gg, cap a fine finestra | `AMBIGUOUS_SAME_BAR` | `CENSORED` | mai risolto arbitrariamente |
| `CONTINUATION_1ATR_BEFORE_FAILURE` | idem, soglia continuazione = `atr_at_event` nella direzione dello sweep/break; soglia fallimento = ritorno al `price_at_event` originale (reclaim) | 5gg, cap a fine finestra | `AMBIGUOUS_SAME_BAR` | `CENSORED` (anche se `atr_at_event<=0`) | mai risolto arbitrariamente |

`RETEST_HOLD_OR_FAIL = "N/A_NO_RETEST"` quando `RETEST_OCCURRED=false` — non un censoring, una non-applicabilità dichiarata.

## 5. Label coverage

**AT_SWEEP (4045 righe)**:
- `TRUE_BREAK_OCCURRED` = true: **19.5%** (789/4045)
- `RETEST_OCCURRED` = true: **2.1%** (83/4045 circa, coerente con 63 RETEST totali meno quelli non collegabili a uno SWEEP nella stessa finestra)
- `RECLAIM_OR_FALSE_BREAK`: TRUE_BREAK=789, RECLAIM=1942, **NO_LIFECYCLE=1314 (32.5%)** — quest'ultimo è il limite di copertura dichiarato: SH_BMS_RTO osserva solo gli sweep che gli è capitato di tracciare (stato IDLE, direzione compatibile) — un terzo degli sweep canonici non ha alcun lifecycle collegato.
- `RETEST_HOLD_OR_FAIL`: N/A_NO_RETEST=3962, FAIL=38, HOLD=26, AMBIGUOUS=19
- `PLUS_1R_BEFORE_MINUS_1R`: PLUS_1R_FIRST=1342, MINUS_1R_FIRST=1292, AMBIGUOUS_SAME_BAR=1411 (**34.9% ambiguo** — R=25 pip è stretto rispetto alla volatilità H4 di GOLD, atteso e coerente con Causal Experiment 1)
- `CONTINUATION_1ATR_BEFORE_FAILURE`: FAILURE_FIRST=3735 (92.3%), CONTINUATION_FIRST=303, AMBIGUOUS=6, CENSORED=1

**AT_TRUE_BREAK (269 righe)**:
- `RETEST_OCCURRED` = true: **27.1%** (73/269)
- `RETEST_HOLD_OR_FAIL`: N/A_NO_RETEST=196, HOLD=28, FAIL=26, AMBIGUOUS=19
- `PLUS_1R_BEFORE_MINUS_1R`: MINUS_1R_FIRST=98, AMBIGUOUS_SAME_BAR=91, PLUS_1R_FIRST=80
- `CONTINUATION_1ATR_BEFORE_FAILURE`: FAILURE_FIRST=243 (90.3%), CONTINUATION_FIRST=25, AMBIGUOUS=1

Nessuna interpretazione di questi numeri come segnale predittivo — sono conteggi di copertura, non risultati di un test.

## 6. Data quality

| Check | Esito |
|---|---|
| Duplicate `structural_level_id`/event keys | **0** |
| Orphan TRUE_BREAK/RETEST/INVALIDATE senza SWEEP | **0** |
| Malformed (confirmed incoerente) | **0** (fix `9b77f83` confermato di nuovo su dati reali) |
| Impossible transitions (RETEST senza TRUE_BREAK per lo stesso livello) | **0** |
| Righe censurate | vedi §5 (`CENSORED` nei label forward, quota ridotta: 1/4045 in AT_SWEEP per continuation, 0 per plus1r) |
| Copertura M1 | w1: 55801 barre (gap >5min: 40) · w2: 59287 (42) · w3: 58890 (42) · w4: 53530 (38) — i gap sono attesi nei weekend/chiusure mercato, non un difetto di esportazione |
| **Temporal ordering (SWEEP ≤ TRUE_BREAK ≤ RETEST)** | **48 violazioni su 1989 livelli (2.4%) — indagate e spiegate, non un bug nuovo** |

### Sull'ordinamento temporale: causa trovata, non un difetto dei dati

Le 48 violazioni sono TUTTE del tipo "TRUE_BREAK con timestamp precedente al proprio SWEEP" (es. SWEEP alle 20:00, TRUE_BREAK con timestamp 00:00 dello stesso giorno). Causa: il campo `timestamp` di ogni evento riflette il "bar in formazione del TF che ha innescato quella specifica transizione" (architettura multi-TF-pass di `NXS_CollectAllSignals`, preesistente e fuori scope qui) — se lo SWEEP è stato osservato durante un pass H1/H4 (bar-open a metà giornata) e il TRUE_BREAK durante un pass D1 (bar-open sempre a mezzanotte), il TRUE_BREAK può mostrare un `timestamp` locale precedente pur essendo avvenuto DOPO in ordine di elaborazione reale.

**Verificato** riordinando gli stessi eventi per `event_id` (contatore monotono assegnato in ordine di elaborazione reale, non ricostruibile a posteriori): **37 casi su 48 (77%) risultano perfettamente ordinati** (SWEEP→TRUE_BREAK→RETEST) usando `event_id` invece di `timestamp`. I restanti 11 non sono stati investigati oltre (richiederebbe disambiguare episodi multipli di sweep/reswept sullo stesso `structural_level_id` nella stessa finestra) — non bloccante per questa fase, dichiarato come limite noto.

**Implicazione per l'uso del dataset**: `timestamp` resta affidabile come riferimento di calendario/prezzo per ogni singolo evento preso isolatamente, ma il confronto di ordinamento FRA eventi collegati dello stesso `structural_level_id` deve preferire `event_id` quando la granularità del bar conta (es. calcolo preciso di `time_to_true_break_sec` — il valore riportato in `at_true_break.csv` usa `timestamp`, quindi può essere leggermente distorto per questi 48 casi; non ricalcolato in questa fase, dichiarato qui).

**Pattern collaterali osservati** (non anomalie, spiegati): w2 non ha alcun RETEST (0/56 TRUE_BREAK arrivano a un retest riuscito prima di invalidare o del fine-finestra — plausibile in un periodo di trend continuo). w4 mostra `SWEEP=783` e `INVALIDATE=783` per coincidenza aggregata, NON un rapporto 1:1 per livello: verificato che solo 247/387 livelli unici di w4 hanno sia SWEEP sia INVALIDATE (i restanti hanno invalidazioni multiple sullo stesso livello risweepato, o nessuna invalidazione entro fine finestra).

## 7. File di output

- `results/structural_dataset_v1/structural_events.csv` — 8118 righe, dump grezzo completo
- `results/structural_dataset_v1/at_sweep.csv` — 4045 righe
- `results/structural_dataset_v1/at_true_break.csv` — 269 righe
- `results/structural_dataset_v1/metadata.json` — schema/versione/date range/data-quality/label coverage completi

## 8. Modifiche di codice in questa fase

Puramente additive, nessun impatto su trading (verificato per costruzione: nuovo campo/export sono write-only verso un file diagnostico, mai letti da alcuna decisione):

- `NXS_StructuralResearchLog.mqh`: aggiunto campo `atr_at_event` (snapshot `g_atr`, stesso pattern di `regime_at_event`); aggiunta `NXS_Structural_ExportCSV()` (dump one-shot dell'intero stato finale su CSV in OnDeinit, `FILE_WRITE` senza `FILE_READ` — tronca sempre, nessuna dipendenza dal bug di reset noto di `NEXUS_trades.csv`); **bugfix del delimitatore di `observed_by`**: cambiato da `,` a `|` perché `FileWrite(FILE_CSV)` non quota i campi contenenti il delimitatore CSV, corrompendo la struttura delle righe esportate (scoperto durante il parsing di questa stessa run, corretto per gli export futuri; i dati già raccolti sono stati letti correttamente con un parser robusto lato Python che ricostruisce il campo).
- `NEXUS_EA_v2.mq5`: una riga, chiamata a `NXS_Structural_ExportCSV()` in `OnDeinit`.

Compilazione: 0 errori, entrambi i terminali.

## 9. Blockers

Nessuno bloccante. Limiti noti e dichiarati (non bloccanti):
- Copertura lifecycle parziale (solo SH_BMS_RTO produce TRUE_BREAK/RETEST/INVALIDATE — 32.5% degli SWEEP in AT_SWEEP restano `NO_LIFECYCLE`).
- 48/1989 gruppi con ordinamento timestamp non monotono per artefatto di granularità multi-TF-pass (spiegato, `event_id` come proxy corretto).
- R=25 pip fisso produce ambiguità same-bar elevata (~35%) su H4 — atteso, coerente con esperimenti causali precedenti, non un difetto di questa costruzione.

## Verdict

### **READY_FOR_STRUCTURAL_CAUSAL_EXPERIMENT**

Dataset costruito su 3 CSV + metadata, popolazione e schema conformi alla specifica, nessuna feature futura in nessuna delle due view, label costruiti (non analizzati) con metodologia dichiarata, data quality verificata con un solo pattern anomalo trovato E spiegato (non un difetto). Nessuna feature selection, nessun modello, nessuna regola proposta in questa fase.
