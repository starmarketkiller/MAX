# NEXUS - Phase 7.24 — LIQ_SWEEP Canonical Dataset Adjudication

**Baseline:** `ae94901` (Phase 7.23, Run Isolation + LIQ_SWEEP Integrity Audit). Nessuna edge validation, nessun tuning in questa fase — solo adjudication del residuo 42 vs 43 e costruzione del dataset canonico MT5. MT5 trattato come ground truth per costruzione, mai forzata la parità con Python.

**Obiettivo**: stabilire un dataset canonico MT5 di LIQ_SWEEP utilizzabile per una futura edge validation, chiudendo definitivamente il residuo di riconciliazione 42 vs 43 lasciato aperto da Phase 7.23, senza inseguire parity completa Python↔MQL5.

---

## 1. Scoperta: il residuo era in realtà DUE problemi distinti, non uno

Il "42 vs 43" di Phase 7.23 nascondeva un bug reale nell'harness, scoperto ricostruendo l'appaiamento OPEN↔CLOSE in modo indipendente dal builder di Phase 7.23.

### 1a. Il vero bug: BOM non rimosso dal codec

`_detect_text_encoding()` (introdotta in Phase 7.23 per correggere il primo bug di encoding) restituiva il codec esplicito `"utf-16-le"`/`"utf-16-be"` invece del codec generico `"utf-16"`. Il primo **non rimuove il BOM** dal testo decodificato — lascia un carattere `U+FEFF` incollato al campo `time` della primissima riga del file (il primo OPEN cronologico, `2023.10.03 17:30:00` → `'﻿2023.10.03 17:30:00'`). Poiché `U+FEFF` (65279) ordina **dopo** qualunque cifra ASCII in un confronto di stringhe, quell'OPEN finiva in fondo alla lista ordinata invece che in testa, disallineando l'appaiamento FIFO cronologico e facendo fallire esattamente un confronto — non quello sul primo evento (che sarebbe stato l'ipotesi naturale), ma quello sull'**ultimo**, per effetto domino dello shift.

**Verifica diretta**: decodificando con `"utf-16-le"` si ottengono 41 eventi appaiati; decodificando con `"utf-16"` (che rimuove il BOM) se ne ottengono 42, e l'unico OPEN che resta senza CLOSE è quello genuinamente più recente del campione (2026.06.25), non uno arbitrario. Questo conferma che il bug era nel parsing, non nei dati.

**Fix applicato** (harness, non strategia): `_detect_text_encoding()` ora ritorna `"utf-16"` per qualunque BOM UTF-16 rilevato. `liq_sweep_diagnostic_run_v1.json` (Phase 7.23) ricostruito con il fix: **42 eventi**, non più 41; net P&L **+$1.076,30** (non più +$1.101,90 — il numero precedente rifletteva un appaiamento cronologicamente scorretto). Decision card di Phase 7.23 rigenerata: decisione invariata (`INTEGRITY_PARTIALLY_VALIDATED`), verificatore e 38/38 test di Phase 7.23 rieseguiti con esito invariato.

### 1b. Il residuo reale, dopo il fix: 43 OPEN vs 42 CLOSE

Il funnel, verificato aritmeticamente in modo indipendente (non fidandosi del solo certificato):

| Stage | Count | Check |
|---|---|---|
| 1. Raw event generated | 3672 | — |
| 2. Blocked by gate | 3623 | 3623+49=3672 ✓ |
| 3. Open attempt | 49 | — |
| 4. Broker reject | 6 | — |
| 5. Opened | 43 | 49-6=43 ✓, = righe OPEN nel CSV ✓ |
| 6. Closed within window | 42 | = righe CLOSE nel CSV |
| 7. Still open at period end | 1 | 43-42=1 ✓ |
| 8. Events used economically | 42 | = closed_within_window ✓ |

Tutti i controlli aritmetici tornano (`all_arithmetic_checks_hold=True`). L'unico OPEN senza CLOSE è il segnale cronologicamente più recente del campione (2026.06.25 01:15:00, SELL, `Sweep_high_reversal:Asia-High`, entry 4001.49), aperto solo ~4,9 giorni prima della fine della finestra testata (`period_end=2026.06.29 23:58:58`). Gli `hold_sec` osservati sui 42 eventi chiusi vanno da poche ore a >80 giorni — una posizione ancora aperta dopo 4,9 giorni è pienamente compatibile con la distribuzione osservata.

**Classificazione**: `EXPECTED_FUNNEL_DIFFERENCE` — non un difetto, l'esito atteso di qualunque backtest con finestra finita e una posizione ancora in corso alla chiusura. Nessun residuo classificato `UNKNOWN` o `DATA_LOSS`. Nessuna riconciliazione forzata.

## 2. Dataset canonico MT5

`liq_sweep_canonical_dataset_v1.json`: 43 eventi totali, **42 CLOSED** (dataset economico primario) + **1 OPEN_AT_PERIOD_END** (conservato per completezza del ciclo di vita, escluso dal calcolo economico — nessun P&L realizzato). Ogni evento porta: `event_id` univoco, `run_id`, identità strategia/selettore, entry (timestamp, prezzo segnale, SL/TP pianificati, reason tag), exit (timestamp, prezzo, motivo, hold_sec, r_multiple, TF risolta), `actual_pnl`, lotto, ticket, provenance. Costruito **esclusivamente da MT5** (`python_used_to_build_this_dataset: false`), tramite il Run Isolation Harness di Phase 7.23, senza passare dal builder di Phase 7.23 (ricostruzione indipendente per l'adjudication). Split direzionale sui 42 chiusi: 39 BUY / 3 SELL (nota descrittiva, nessuna analisi economica in questa fase). Net P&L (solo chiusi): **+$1.076,30** — numero diagnostico, non una conclusione di edge.

## 3. Separazione trigger/exit semantics — classificazione formale

`liq_sweep_python_fidelity_classification_v1.json` formalizza (senza ri-derivare) i findings di Phase 7.23:

- **MQL5 canonico** — uscita FISSA: SL=1.5×ATR, TP=3.0×ATR (R:R=2.0), da `NXS_DefaultSLTP()`/`NXS_Profile_SLTP`. Unica logica realmente eseguita dal vivo/nel Tester — fonte di ogni P&L nel dataset canonico.
- **Python proxy storico** — uscita DINAMICA su pool di liquidità opposti (`_liq_sweep_target()`), dichiarata nel codice stesso come sostituzione di "un multiplo fisso di ATR" — esplicitamente una variante di ricerca indipendente, non un tentativo di replica.
- **Conseguenza**: Python non può validare PF/expectancy/P&L della strategia canonica. Può essere usato solo per confronti compatibili col livello di fedeltà dimostrato (identità dell'ingresso: sweep detection, delivery-candle filter, direction gate — tutti event-level-faithful o partial-structural-model per lettura diretta del codice), mai per l'uscita.
- Nessuna modifica al codice Python per forzare la coincidenza di P&L/lifecycle.

## 4. Decision Card di readiness

**`READY_WITH_DOCUMENTED_LIMITATION`**

Check superati: funnel riconciliato aritmeticamente, residuo interamente adjudicato (zero `UNKNOWN`/`DATA_LOSS`), dataset canonico costruito solo da MT5, non vuoto, harness di isolamento usato, mismatch Python documentato (non nascosto), fedeltà Python classificata esplicitamente. La "limitazione documentata": Python non può essere usato per validare P&L/PF di questa strategia — qualunque edge validation futura deve usare solo il dataset MT5 canonico di questa fase.

## 5. Nessun nuovo run lungo

I 42 eventi già raccolti in Phase 7.23 restano il dataset primario — nessun rilancio del Tester in questa fase (gli artifact esistenti erano sufficienti per chiudere l'adjudication).

## Deliverables

`nxs_liq_sweep_dataset_loader.py` (loader condiviso, ricostruzione indipendente dai file grezzi), `build_funnel_accounting.py` + `funnel_accounting_v1.json`, `build_canonical_dataset.py` + `liq_sweep_canonical_dataset_v1.json`, `build_python_fidelity_classification.py` + `liq_sweep_python_fidelity_classification_v1.json`, `build_readiness_decision_card.py` + `liq_sweep_readiness_decision_card_v1.json`, `verify_phase_7_24.py` (VERIFY OK), `test_phase_7_24.py` (22/22), fix al harness condiviso di Phase 7.23 (`nxs_research_run_harness.py::_detect_text_encoding`) + rebuild dei suoi artifact impattati (`liq_sweep_diagnostic_run_v1.json`, `liq_sweep_decision_card_v1.json` — decisione invariata, 38/38 test invariati), questo vault report.

## Vincoli preservati

Nessuna modifica a `MQL5/`, `Product-Platform/`, `contracts/` (diff zero verificato dal verificatore stesso). Nessuna modifica al codice Python (`server/backtest.py` e affini) per forzare parity. Nessuna optimization, nessuna analisi economica ulteriore (concentrazione/costi/CI/OOS/MVC deferiti a `EDGE_VALIDATION_V1`). Nessun nuovo run MT5 lanciato.

## Regressione

Suite Phase 7.23+7.24 combinata: 60/60 pass. Suite Phase 7 completa: 750 passed, 7 failed (stessi 7 self-check di staleness pre-esistenti già noti da Phase 7.23 — phase7_12, phase7_13, phase7_15 ×2, phase7_17, phase7_9h ×2 — nessun nuovo fallimento introdotto da questa fase, `git diff` zero su tutti i file coinvolti in quei fallimenti). Effetto collaterale noto reintegrato: `phase7_9c/breakout_acc_{mt5,python}_event_stream_v1.json` (solo timestamp) revertito con `git checkout --` prima del commit.

---

```
7.23: RUN ISOLATION HARNESS + LIQ_SWEEP INTEGRITY AUDIT - COMPLETATO
7.24: LIQ_SWEEP CANONICAL DATASET ADJUDICATION - COMPLETATO

BUG TROVATO E CORRETTO (harness, non strategia): _detect_text_encoding
  ritornava 'utf-16-le'/'utf-16-be' (non rimuove il BOM) invece di
  'utf-16' (lo rimuove) - il BOM incollato al primo timestamp
  corrompeva l'ordinamento FIFO, perdendo 1 appaiamento su 42 (41
  invece di 42). Rebuild di liq_sweep_diagnostic_run_v1.json
  (Phase 7.23): 42 eventi, net +$1.076,30 (non piu' 41/+$1.101,90).

FUNNEL (verificato aritmeticamente, indipendente dal certificato):
  GENERATED 3672 -> BLOCKED 3623 + OPEN_ATTEMPT 49 (3623+49=3672 OK)
  OPEN_ATTEMPT 49 -> OPENED 43 + BROKER_REJECT 6 (43+6=49 OK)
  OPENED 43 -> CLOSED 42 + STILL_OPEN_AT_END 1 (42+1=43 OK)
  tutti i check aritmetici: HOLD

RESIDUO ADJUDICATO (2 voci, entrambe chiuse):
  #1 "41 vs 42 appaiati" -> LOGGING_ACCOUNTING_GAP, ROOT CAUSE
    TROVATA E CORRETTA (bug BOM harness) - RISOLTO
  #2 "43 open vs 42 close" -> EXPECTED_FUNNEL_DIFFERENCE (1 posizione
    ancora aperta a fine finestra, 4.9gg prima di period_end,
    compatibile con la distribuzione hold_sec osservata) - non un
    difetto, escluso dal dataset economico

DATASET CANONICO MT5: 43 eventi (42 CLOSED economici + 1
  OPEN_AT_PERIOD_END) - costruito SOLO da MT5, zero dipendenza Python
  - ogni evento con event_id/entry/exit/P&L/provenance/hash

PYTHON FIDELITY: entry event-level-faithful (sweep+delivery-candle+
  direzione), exit STRUCTURALLY_DIFFERENT_NOT_COMPARABLE (ATR fisso
  MQL5 vs liquidita' dinamica Python) - Python NON validabile per
  P&L/PF di questa strategia, nessuna modifica forzata al codice
  Python

DECISIONE: READY_WITH_DOCUMENTED_LIMITATION
  (dataset MT5 riconciliato e riproducibile - limitazione: Python
   non usabile per P&L, solo MT5 come input per edge validation)
PROSSIMO: autorizzata LIQ_SWEEP EDGE_VALIDATION_V1 (stesso protocollo
  di BREAKOUT_ACC/ORDER_BLOCK: expectancy -> concentrazione -> costi
  -> CI -> OOS -> minimum viable capital -> visual audit), usando il
  dataset canonico di questa fase come input primario, nessun nuovo
  run MT5 salvo necessita' dimostrata (es. OOS forward)
```
