# TEST_RESULTS — Vertical Slice 01 (H1_A)

Comando eseguito dalla root di questa slice:

```
PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -v
```

**Risultato finale: 27 passed, 0 failed, 0 errors, 1 warning (benigno, deprecation di pytest non legata al codice sotto test), 17.34s.**

## 1. Classificazione a tre livelli (per mandato)

- **SYNTHETIC** — fixture costruite a mano (`make_bar(...)`), nessun
  dato storico reale coinvolto. Copre la logica pura del detector, del
  Paper Engine e del journal in isolamento.
- **HISTORICAL_ALLOWED** — bar reali del dataset reused
  (`xauusd_h4_bars.csv`, stesso DISCOVERY_REUSE già usato altrove nel
  codebase, mai il holdout sigillato). Copre anti-lookahead,
  determinismo e copertura temporale su dati veri.
- **VISUAL** — **non eseguita**. Nessuno strumento browser era
  disponibile in questa sessione per un controllo visivo automatizzato
  della Cockpit Demo durante la stesura dei test; dichiarato qui come
  limite, non saltato silenziosamente. La demo è stata comunque
  verificata manualmente con un driver CDP headless separato (vedi
  `FINAL_DECISION_CARD.md` §Cockpit) — quella verifica non fa parte
  della suite pytest.

## 2. Elenco test e cosa provano

### TestSyntheticDetector (8 test, SYNTHETIC)
| Test | Prova |
|---|---|
| `test_insufficient_warmup` | Meno di N=20 bar pregressi → `WAIT`/`INSUFFICIENT_WARMUP_HISTORY` |
| `test_no_sweep` | Nessuna penetrazione del livello → `WAIT`/`NO_SWEEP_DETECTED` |
| `test_sweep_without_reclaim_is_wait_not_h1a` | Sweep confermato come breakout (no reclaim) → `WAIT`, non un candidato H1-A |
| `test_long_candidate_sweep_and_reclaim` | Sweep low + reclaim → `BUY`/`CANDIDATE_LONG_SWEEP_RECLAIM` |
| `test_short_candidate_sweep_and_reclaim` | Sweep high + reclaim → `SELL`/`CANDIDATE_SHORT_SWEEP_RECLAIM` |
| `test_ambiguous_both_sides` | Sweep+reclaim su entrambi i lati nello stesso bar → `WAIT`/`AMBIGUOUS_BOTH_SIDES_SWEPT_AND_RECLAIMED` |
| `test_sweep_buffer_is_a_parameter_not_hardcoded` | Lo stesso bar produce esiti diversi con buffer diverso — prova che il buffer è un parametro reale, non una costante nascosta |
| `test_classify_sequence_is_causal_not_centered` | La finestra Donchian usata per il bar `t` non include mai `t` stesso (prova diretta di causalità sulla logica pura, prima ancora del test anti-lookahead sui dati reali) |

### TestWaitIsObservable (1 test, SYNTHETIC)
| Test | Prova |
|---|---|
| `test_wait_record_has_full_schema` | Un `WAIT` produce un record completo con `reason_code` esplicito — mai un'assenza silenziosa |

### TestDeduplication (2 test, SYNTHETIC)
| Test | Prova |
|---|---|
| `test_duplicate_candidate_is_vetoed_while_attempt_open` | Un secondo candidato nella stessa direzione viene vetoed a `WAIT` mentre un tentativo è già aperto |
| `test_same_bar_evaluated_twice_yields_identical_event_id` | Idempotenza: rivalutare lo stesso bar produce lo stesso `event_id`, mai un duplicato |

### TestMissingData (2 test, SYNTHETIC)
| Test | Prova |
|---|---|
| `test_missing_close_marks_data_invalid_in_shadow_event` | Un bar con `close=None` marca `data_quality="INVALID"` nel `shadow_audit_event`, non viene silenziosamente trattato come dato valido |
| `test_no_next_bar_registers_fill_uncertain_not_invented_fill` | Nessun bar successivo disponibile per il fill → `outcome="FILL_UNCERTAIN"`, mai un prezzo inventato |

### TestMandatoryStopAndCosts (3 test, SYNTHETIC)
| Test | Prova |
|---|---|
| `test_every_opened_attempt_has_a_real_stop` | Ogni tentativo aperto ha uno `stop_price` reale (non NaN/None) |
| `test_slippage_and_spread_are_explicit_and_applied` | Slippage e spread sono campi popolati e non-zero in `cost_breakdown`, mai costi impliciti |
| `test_no_grid_pyramid_recovery_martingale_single_attempt_enforced` | Un secondo `open_from_candidate()` mentre uno slot è già occupato solleva `RuntimeError` — un solo tentativo alla volta per costruzione |

### TestBrokerSeparation (2 test, SYNTHETIC — analisi statica del testo sorgente)
| Test | Prova |
|---|---|
| `test_simulator_source_has_no_network_or_mt5_import` | `paper_engine/simulator.py` non contiene nessuno dei token `socket`, `requests`, `MetaTrader5`, `OrderSend`, `urllib`, `http.client` |
| `test_decision_engine_source_has_no_network_or_mt5_import` | Stesso controllo su `decision_engine/engine.py` |

### TestHistoricalAllowedDataLayer (6 test, HISTORICAL_ALLOWED — dati reali)
| Test | Prova |
|---|---|
| `test_coverage_is_outside_final_holdout_window` | Il dataset reused (2019-02-03→2022-02-03) non si sovrappone al FINAL_HOLDOUT sigillato (2026-02-04→2026-09-16) né al vecchio holdout H006 |
| `test_bars_as_of_never_returns_a_future_bar` | `BarStore.bars_as_of(cutoff)` non restituisce mai un bar con `available_at_utc > cutoff` |
| `test_anti_lookahead_replay_passes_on_real_data` | `replay.verify_no_future_leakage` su 7 cutoff campionati sui 4.808 bar reali: **0 mismatch** |
| `test_replay_is_deterministic_same_input_same_output` | Due run identici sullo stesso input producono output byte-identici |
| `test_all_three_decision_kinds_occur_on_real_data` | BUY, SELL e WAIT occorrono tutti realmente nel dataset (non solo nella teoria) |
| `test_causal_timestamp_is_bar_close_never_bar_open` | `causal_timestamp` di ogni decision record corrisponde sempre alla chiusura del bar, mai all'apertura |

### TestJournalIntegrity (3 test, SYNTHETIC — usa uno scratch dir locale, non `tmp_path`)
| Test | Prova |
|---|---|
| `test_hash_chain_detects_tampering` | Una riga alterata a metà file rompe `verify_chain()` |
| `test_journal_is_append_only_never_truncates_existing` | Due scritture separate non si sovrascrivono a vicenda, la catena resta valida sull'intero file |
| `test_strategy_version_present_on_every_record` | Nessun record scritto senza `strategy_id`/`strategy_version` |

## 3. Nota tecnica sull'ambiente di test

`tests/conftest.py::TestJournalIntegrity` usa un fixture locale
(`tests/_scratch/`, ripulito con `shutil.rmtree(ignore_errors=True)`
dopo ogni test) invece del fixture standard `tmp_path` di pytest — in
questo sandbox, `tmp_path` fallisce con
`PermissionError: [WinError 5] Accesso negato` contro
`C:\Users\User\AppData\Local\Temp\pytest-of-User` (limite dell'ambiente
sandbox, non un difetto del codice sotto test).

## 4. Esecuzione end-to-end reale (non un test pytest, ma lo stesso motore)

`scripts/run_full_replay.py` eseguito sull'intero dataset reused
(4.808 bar) con `decisions_log_chain_verified=true` e
`attempts_log_chain_verified=true` — vedi `REPLAY_AND_JOURNAL.md` §3
per l'output completo e `LIMITATIONS.md` per l'interpretazione
corretta (nessuna claim economica) dei numeri aggregati.
