# FINAL DECISION CARD — NEXUS Trading V1 Vertical Slice 01

**Strategia**: H1_A (Sweep/Reclaim), `strategy_version=H1_A_V1` ·
**Simbolo**: XAUUSD · **Timeframe operativo**: H4 ·
**Modalità**: PAPER-ONLY, nessun broker, nessuna modifica a MQL5/EA canonico.

## VERDETTO: **FUNCTIONAL_PAPER_SLICE_READY**

L'intera catena mandata — **osserva → riconosce → decide → simula →
gestisce → registra → spiega** — funziona end-to-end su dati reali
reused, in modo causale (anti-lookahead dimostrato, non solo
assunto), deterministico (stesso input → stesso output, verificato) e
verificabile (journal hash-chained, 27/27 test passano, cockpit demo
funzionante confermata via driver browser headless). Non è
`PARTIALLY_FUNCTIONAL` perché nessun componente richiesto dal mandato
manca o è stub; non è `BLOCKED` perché nessun blocco tecnico o di
sicurezza impedisce l'esecuzione end-to-end in modalità carta.

## 1. Cosa è stato costruito (mappa deliverable → file)

| Deliverable richiesto | File |
|---|---|
| Strategy Contract | `STRATEGY_CONTRACT_H1_A.md` |
| Event/Decision Schema | `EVENT_DECISION_SCHEMA.md` |
| Data Provenance | `DATA_PROVENANCE.md` |
| Paper Engine (codice + descrizione) | `paper_engine/simulator.py`, `PAPER_ENGINE.md` |
| Replay e Journal (codice + descrizione) | `replay/replay.py`, `journal/journal.py`, `REPLAY_AND_JOURNAL.md` |
| Cockpit Demo | `cockpit_demo/index.html` (autocontenuto), `cockpit_demo/template/`, `cockpit_demo/data/` |
| Test Results | `TEST_RESULTS.md` (+ `tests/test_h1a_vertical_slice.py`, 27 test) |
| Limitations | `LIMITATIONS.md` |
| Decision Card | questo documento |
| Manifest SHA-256 | `MANIFEST_SHA256.txt` |

Più il codice di supporto non esplicitamente nella lista deliverable
ma necessario per l'esecuzione: `data_layer/bar_store.py`,
`decision_engine/h1a_detector.py`, `decision_engine/engine.py`,
`scripts/run_full_replay.py`, `scripts/export_cockpit_data.py`,
`scripts/build_cockpit_html.py`.

## 2. Evidenza a sostegno del verdetto

- **Causalità**: `replay.verify_no_future_leakage` eseguito su dati
  reali (7 cutoff, 4.808 bar) — **0 mismatch**. Non un'asserzione
  statica ("nessun bar futuro nella lista") ma una prova
  comportamentale (run troncato vs run completo, confronto
  campo-per-campo).
- **Determinismo**: `test_replay_is_deterministic_same_input_same_output`
  passa — stesso input produce output byte-identico.
- **Integrità del journal**: `decisions_log_chain_verified=true` e
  `attempts_log_chain_verified=true` sull'intero run da 4.808 bar;
  tampering sintetico rilevato correttamente nei test
  (`TestJournalIntegrity::test_hash_chain_detects_tampering`).
- **Nessuna dipendenza broker/rete**: verificato staticamente sul
  testo sorgente di `simulator.py` e `engine.py`
  (`TestBrokerSeparation`, 2/2 test).
- **WAIT sempre osservabile**: ogni bar produce un record, mai
  un'assenza silenziosa (`TestWaitIsObservable`).
- **Nessun fill inventato**: `FILL_UNCERTAIN` esplicito quando il fill
  non può essere determinato in modo affidabile
  (`TestMissingData::test_no_next_bar_registers_fill_uncertain_not_invented_fill`).
- **Un solo tentativo alla volta**: enforced sia dal veto del Decision
  Engine sia da un controllo difensivo nel Paper Engine
  (`TestMandatoryStopAndCosts::test_no_grid_pyramid_recovery_martingale_single_attempt_enforced`).
- **Cockpit Demo**: verificata con un driver CDP headless (Chrome,
  fuori dalla suite pytest) su 5 scenari — stato iniziale, bar
  intermedio con livelli popolati, fine corsa con 19 trade nel
  journal (8 TP, 11 SL), vista D1 aggregata con nota esplicita di
  "solo display", navigazione "prossimo segnale" — **0 errori
  console in tutti gli scenari**.
- **Suite di test**: 27/27 passed, 0 failed, 0 errors (vedi
  `TEST_RESULTS.md` per il dettaglio completo).

## 3. Cosa questo verdetto NON afferma

Per evitare qualunque ambiguità con il punto §0 di `LIMITATIONS.md`:
**`FUNCTIONAL_PAPER_SLICE_READY` è un giudizio sulla correttezza
ingegneristica e sulla verificabilità della catena, non sulla qualità
economica della strategia H1_A.** Il +134.6% di equity sull'intero
run non è stato validato statisticamente, non è stato testato fuori
dal periodo su cui il codice è stato scritto, e non deve essere letto
come raccomandazione di trading. Questo verdetto non autorizza alcun
passo verso l'esecuzione live, né modifica in alcun modo
`contracts/strategy-registry.json` o il codice MQL5/EA canonico.

## 4. Prossimi passi possibili (fuori scope per questa missione, non eseguiti)

- Validazione statistica fuori-campione su una finestra non usata
  durante lo sviluppo (holdout proprio della slice, non il
  FINAL_HOLDOUT sigillato, che resta riservato).
- Test di sensibilità ai parametri DESIGN_ASSUMPTION_V1 (N del
  lookback, buffer, R-multiple) per capire quanto il risultato dipenda
  da scelte arbitrarie.
- Estensione del Decision Engine con un filtro HTF o di sessione,
  esplicitamente fuori scope qui (§11 del contratto).
- Una Mission di validazione statistica dedicata, se il
  responsabile del progetto decide che questa linea d'ipotesi merita
  ulteriore investimento — decisione esplicitamente non presa da
  questa missione.
