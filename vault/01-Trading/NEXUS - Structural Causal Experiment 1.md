# NEXUS Causal Research Thread 2 — Structural Causal Experiment 1: Discovery

Segue [[NEXUS - Structural Dataset v1 Causal Linkage Integrity Audit]]. Prima analisi predittiva sul dataset strutturale: alcune feature note AL MOMENTO dello SWEEP predicono `TRUE_BREAK_OBSERVED` vs `INVALIDATED_NO_BREAK`? Discovery, non ottimizzazione — nessuna strategia implementata.

## Bug critico trovato ed eliminato prima dell'analisi

Durante la costruzione della population di questo esperimento è emerso che `event_id` **non è univoco fra le 4 finestre** — ogni finestra è una run separata del Tester e `g_nxsStructEventIdSeq` riparte da 1 ad ogni run. Verificato: **2108 dei 2382 valori di `event_id` (88.5%) sono condivisi da tutte e 4 le finestre**. `build_episode_lifecycle_index()` (introdotta nell'audit di linkage precedente) indicizzava gli eventi lifecycle SOLO per `event_id`, senza qualificare per finestra — le finestre successive sovrascrivevano silenziosamente le assegnazioni delle finestre precedenti nello stesso dict. Sintomo che ha reso il bug visibile: la finestra `w1` risultava con **zero** episodi in popolazione valida, un risultato implausibile dato che w1 aveva 87 TRUE_BREAK grezzi.

**Fix**: tutte le strutture indicizzate per evento lifecycle (`lifecycle_link`, `ev_by_id` dentro `build_episode_lifecycle_index()`) ora usano la chiave composita `(window_id, event_id)`. La regola di linkage per episodio descritta nell'audit precedente restava corretta nella sua logica — solo l'implementazione del secondo livello di indicizzazione era compromessa. **Dataset ricostruito** (`structural_events.csv`, `at_sweep.csv`, `at_true_break.csv`, `metadata.json`) prima di procedere con l'analisi. I conteggi di episodio (2411 totali, 1968 chiusi esplicitamente, 410 implicitamente, 33 aperti a fine finestra, 0 orphan, 0 ordine impossibile) **non cambiano** — provenivano dalla replay per-gruppo, mai dal dict compromesso — ma i LABEL in `at_sweep.csv`/`at_true_break.csv` sì, in modo sostanziale (vedi §1).

## 1. Population

| | n |
|---|---|
| Episodi SH_BMS_RTO totali | 2411 |
| Esclusi: `NO_LIFECYCLE_OBSERVED` (nessun TRUE_BREAK né INVALIDATE-da-SWEPT agganciato) | 427 |
| Esclusi: esito determinato da un evento `redundant_after_close`/`true_break_after_close` (arrivato quando l'episodio era già chiuso — sintomo del desync multi-TF-pass, esito non affidabile) | 1052 |
| **Population valida (TRUE_BREAK_OBSERVED vs INVALIDATED_NO_BREAK, esito affidabile)** | **932** |

Per confronto: la stessa estrazione, PRIMA del fix del bug cross-finestra, dava population=303 (con `w1` completamente assente) — la cifra 932 è quella corretta e usata in questo esperimento.

## 2. Target

Binario: `TRUE_BREAK_OBSERVED` (1) vs `INVALIDATED_NO_BREAK` (0). Nessun trade result, nessun +1R/-1R usato come target principale (i due label forward-looking restano nel dataset ma non sono l'oggetto di questo esperimento).

## 3. Causal safety check esplicito (obbligatorio, punto 3/7 del task)

Verificato nel codice sorgente (`NXS_StructuralResearchLog.mqh`, righe 241-246): `observation_count` e `observed_by` vengono **mutati** (incrementato/esteso) ogni volta che un consumer/pass successivo osserva la stessa riga SWEEP, fino a `OnDeinit` (fine dell'intera run) — l'export CSV cattura lo stato **finale**, non quello al momento della creazione (commento già presente nel codice della Fase B: "riflettono quindi lo stato FINALE, non quello al momento [della creazione]"). **Esclusi da ogni feature causale** in questo esperimento.

`consumer` (chi ha creato per primo la riga SWEEP) è invece impostato **una sola volta** alla creazione e mai più toccato — ammesso come feature categorica. Nella pratica risulta però **costante** (sempre `"DETECTOR"`, dato che il punto di osservazione centrale in `NXS_CollectAllSignals` vince sempre la corsa alla creazione prima di qualunque strategia) — zero varianza, quindi non informativo, correttamente classificato `NO_SIGNAL`/`WEAK_HINT` a uplift esattamente nullo.

Feature ammesse usate: `side` (levelTag), `source_tf`, `direction`, `regime_at_event`, `structure_trend_at_event`, `consumer`, `penetration_pips`, `penetration_pips` normalizzata per `atr_at_event`, `age_seconds` (quando causalmente valido, cioè non Equal-High/Low).

## 4. Split temporale (dichiarato prima di guardare i risultati)

| | Periodo | n |
|---|---|---|
| TRAIN | w1 + w2 + w3 fino al 2026-06-01 | 642 |
| OOS | w3 dal 2026-06-01 + w4 | 290 |

Nessuno split casuale. OOS mai osservato durante la fase di scelta dei bucket — gli stessi 9 raggruppamenti di feature sono stati applicati identicamente a entrambi i set.

## 5. Base rate

| | n | TRUE_BREAK_OBSERVED | rate | CI95 |
|---|---|---|---|---|
| Totale | 932 | 76 | **8.2%** | [6.6%, 10.1%] |
| TRAIN | 642 | 48 | 7.5% | — |
| OOS | 290 | 28 | 9.7% | — |

## 6. Analisi univariata

**39 bucket/ipotesi testate in totale** su 9 feature (side, source_tf, direction, regime_at_event, structure_trend_at_event, consumer, penetration_pips a quartili, penetration/ATR a quartili, age_seconds a bucket) — multiple comparison dichiarato esplicitamente, nessun bucket promosso solo perché appariva interessante isolatamente.

### Top pattern (per magnitudo di uplift, **esclusi** i bucket con n<30 non interpretabili)

| Feature | Bucket | TRAIN n / rate / uplift | OOS n / rate / uplift | Stessa direzione | Classificazione |
|---|---|---|---|---|---|
| `penetration_per_atr_quartile` | Q4 (top 25%) | 160 / 14.4% / **+0.069** | 78 / 19.2% / **+0.096** | SÌ | **WEAK_HINT** |
| `age_seconds_bucket` | `<1h` | 54 / 16.7% / **+0.092** | 29 / 20.7% / **+0.110** | SÌ | **WEAK_HINT** |
| `source_tf` | `PERIOD_D1` | 57 / 15.8% / **+0.083** | 31 / 19.4% / **+0.097** | SÌ | **WEAK_HINT** |

(Esclusi dalla tabella per n insufficiente e non interpretabili: `side=Monthly-High` n_train=2 uplift=+0.425, `regime_at_event=CHOPPY` n_train=2 uplift=+0.425 — artefatti di campione minuscolo, correttamente `NO_SIGNAL`.)

Tutti e tre i pattern sopra mostrano **direzione coerente** TRAIN→OOS con **effetto che cresce, non si dissolve, in OOS** — un segnale qualitativamente incoraggiante ma quantitativamente sotto la soglia di promozione dichiarata (vedi §7): l'uplift in TRAIN resta sotto 0.10 in tutti e tre i casi (0.069, 0.092, 0.083).

### Classificazione completa

| | n |
|---|---|
| NO_SIGNAL | 13 |
| WEAK_HINT | 26 |
| **PROMISING_HYPOTHESIS** | **0** |

## 7. Criteri di promozione (dichiarati prima dell'analisi)

`PROMISING_HYPOTHESIS` richiede **tutti**: `n_train≥30`, `n_oos≥20`, stessa direzione TRAIN/OOS, **e** `|uplift|≥0.10` in **entrambi** i set. Nessun bucket soddisfa l'ultimo criterio — i tre migliori pattern (§6) restano `WEAK_HINT` per un margine di 1-3 punti percentuali sul lato TRAIN.

## 8. Modello logistico (discovery, non produzione)

Feature: `penetration_per_atr`, `age_hours`, `atr_at_event`, `structure_trend` (standardizzate). Gradient descent, 2000 epoche, L2=0.01.

| | Accuracy |
|---|---|
| TRAIN | 92.7% |
| OOS | 90.7% |
| Baseline maggioranza (predici sempre "no true break") su OOS | 90.3% |

**Il modello supera la baseline di maggioranza solo dello 0.4% su OOS** — nessun segnale predittivo utile catturato dalla combinazione lineare di queste 4 feature.

## 9. Albero decisionale shallow (max depth 3, Gini)

```
IF penetration_per_atr <= 0.133 (n=642, rate=0.075):
  IF atr_at_event <= 9.633 (n=622, rate=0.063):
    IF structure_trend <= 0.000 (n=171, rate=0.111): LEAF n=80 rate=0.150
    ELSE:                                             LEAF n=91 rate=0.077
  ELSE:
    IF atr_at_event <= 60.493 (n=451, rate=0.044):     LEAF n=380 rate=0.032
    ELSE:                                              LEAF n=71 rate=0.113
ELSE:
  IF penetration_per_atr <= 0.160 (n=20, rate=0.450):  LEAF n=10 rate=0.500
  ELSE:                                                LEAF n=10 rate=0.400
```

Le due foglie finali del ramo `penetration_per_atr > 0.133` mostrano i tassi più alti (0.400-0.500) ma su **n=10 ciascuna** — validazione OOS per queste stesse foglie: n=7/rate=0.571 e n=5/rate=0.200, **fortemente instabile** (nessuna delle due replica il proprio tasso TRAIN). Trattato come artefatto di overfitting su un ramo a campione minuscolo, non promosso. Le foglie con campione adeguato (n=380, n=451 area) mostrano invece un tasso OOS ragionevolmente vicino a quello TRAIN (0.032→0.039), confermando che il grosso della popolazione non porta segnale utile.

## 10. Stabilità TRAIN/OOS complessiva

Nessun pattern con effetto grande (≥0.10) è stato trovato in nessuno dei due set contemporaneamente. I tre `WEAK_HINT` migliori mostrano tutti direzione coerente e **nessun collasso** in OOS (anzi, un lieve rafforzamento) — non abbastanza per una promozione secondo i criteri dichiarati, ma abbastanza per meritare di essere ri-testati con più dati in un futuro esperimento confermativo dedicato, senza cercare nuove feature.

## 11. Limitations

- Population valida (932) è solo il 38.7% degli episodi SH_BMS_RTO totali (2411) — l'esclusione di `NO_LIFECYCLE_OBSERVED` (427) e soprattutto degli esiti "redundant_after_close" (1052, quasi la metà!) riflette un limite reale dell'instrumentazione attuale (desync multi-TF-pass pre-esistente, fuori scope), non un artefatto di questo esperimento — ma riduce la potenza statistica disponibile.
- Split TRAIN/OOS temporale non bilanciato per finestra (w1+w2+parte w3 in TRAIN, resto in OOS) per costruzione — non uno split 50/50, ma un vero split cronologico come richiesto.
- Nessun controllo per confluenza/correlazione fra feature (es. `source_tf` e `age_seconds` sono probabilmente correlate) — questo esperimento è univariato + un modello lineare/albero shallow, non un'analisi multivariata completa.
- R=25 pip e soglie ATR non toccati qui (non è il target di questo esperimento).

## Verdict

### **NO_PROMISING_HYPOTHESIS**

Nessun pattern supera la soglia di effetto dichiarata (0.10 assoluto) in entrambi i set con campione adeguato. Tre `WEAK_HINT` degni di nota per una futura conferma mirata (`penetration_per_atr` alto, `age_seconds<1h`, `source_tf=D1`), ma **non implementati né promossi** in questa fase, come richiesto.
