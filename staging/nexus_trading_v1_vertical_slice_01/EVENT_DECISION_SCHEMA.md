# EVENT_DECISION_SCHEMA — Vertical Slice 01 (H1_A)

Schema dei tre tipi di record prodotti da questa slice. Ogni record è
scritto nei journal hash-chained (`logs/decisions.jsonl`,
`logs/paper_attempts.jsonl`, vedi `REPLAY_AND_JOURNAL.md`) prima di
qualunque lettura a valle (cockpit demo, test, report) — nessuno di
questi documenti o della demo ricalcola i numeri, li leggono soltanto.

## 1. Journal line envelope (comune a entrambi i log)

```json
{"prev_hash": "<hex o GENESIS_HASH>", "payload": {...}, "record_hash": "<hex>"}
```

- `prev_hash` = `record_hash` della riga precedente nello stesso file
  (o `GENESIS_HASH` per la prima riga) — vedi `journal/journal.py`,
  che riusa `phase5d_shadow_engine_v1.shadow_mode` verbatim.
- `record_hash` = `canonical_hash({"prev_hash": ..., "payload": ...})`
  — qualunque riscrittura di una riga precedente rompe la catena
  (verificato da `journal.verify_chain`, testato in
  `tests/test_h1a_vertical_slice.py::TestJournalIntegrity`).
- `payload` = uno dei due schemi sotto.

## 2. Decision record (`logs/decisions.jsonl`, un record per bar H4)

Prodotto da `decision_engine/engine.py::evaluate_bar`. **Un record per
ogni bar**, anche quando la decisione è `WAIT` — mai un'assenza
silenziosa (requisito esplicito del mandato).

| Campo | Tipo | Significato |
|---|---|---|
| `event_id` | string | Hash deterministico — stesso bar rivalutato produce lo stesso id (vedi `STRATEGY_CONTRACT_H1_A.md` §9-10) |
| `strategy_id` | string | Sempre `"H1_A"` |
| `strategy_version` | string | Sempre `"H1_A_V1"` |
| `detector_version` | string | Uguale a `strategy_version` in questa slice |
| `bar_epoch` | int | Epoch UTC del bar valutato |
| `causal_timestamp` | string (ISO) | `bar.available_at_utc` — quando il record sarebbe stato conoscibile in tempo reale |
| `symbol` | string | `"XAUUSD"` |
| `timeframe` | string | `"H4"` |
| `level_high_observed` / `level_low_observed` | float \| null | `PREEXISTING_LEVEL` Donchian N=20 usato per questo bar; `null` durante il warmup |
| `sweep_buffer_used` | float | Buffer realmente applicato (= `bar.avg_spread`, mai 0 hardcoded — parametro, non costante) |
| `bar_high` / `bar_low` / `bar_close` | float | Copia dei valori OHLC del bar, per leggibilità del log senza un secondo join contro `BarStore` |
| `h1a_decision` | `"BUY"` \| `"SELL"` \| `"WAIT"` | **Decisione finale**, dopo l'eventuale veto di deduplicazione — questo è il campo che guida il Paper Engine |
| `h1a_reason_code` | string | Uno dei 7 codici definiti in `STRATEGY_CONTRACT_H1_A.md` §6 |
| `h1a_decision_pre_veto` / `h1a_reason_code_pre_veto` | string | Decisione/motivo **prima** di un eventuale veto — permette di distinguere "nessun candidato" da "candidato soppresso per deduplicazione" |
| `is_veto` | bool | `true` se il candidato originale è stato soppresso perché un tentativo di carta era già aperto |
| `veto_reason` | string \| null | `"DUPLICATE_SUPPRESSED_OPEN_ATTEMPT_EXISTS"` se `is_veto`, altrimenti `null` |
| `missing_rules_declared` | list[string] | Le 3 regole esplicitamente fuori scope (HTF, sessione, soglia sweep > 0) — ripetute su ogni record per trasparenza, non solo nel contratto |
| `candidate_detail` | object \| null | `{"direction","entry_reference_price","level","sweep_extreme"}` quando `h1a_decision_pre_veto` è BUY/SELL con candidato valido (non vetoed); `null` altrimenti |
| `shadow_audit_event` | object | **Record di audit separato e riusato** (`phase5d_shadow_engine_v1.contract.DecisionEvent.to_dict()`) — vedi §4 |

## 3. Paper Attempt record (`logs/paper_attempts.jsonl`)

Prodotto da `paper_engine/simulator.py::PaperEngine`. Un record per
ogni tentativo di carta aperto (anche se mai riempito —
`outcome="FILL_UNCERTAIN"` — vedi `PAPER_ENGINE.md`).

| Campo | Tipo | Significato |
|---|---|---|
| `attempt_id` | string | `"H1A-PAPER-NNNNNN"`, sequenziale, mai riusato |
| `strategy_id` / `strategy_version` / `symbol` | string | Copiati dal Decision record che ha generato il candidato |
| `direction` | `"LONG"` \| `"SHORT"` | |
| `signal_bar_epoch` / `signal_event_id` | int / string | Riferimento al Decision record di origine (join esplicito, non implicito) |
| `stop_price` / `target_price` | float | Calcolati come in `STRATEGY_CONTRACT_H1_A.md` §7-8 |
| `risk_amount` | float | `equity_al_momento * risk_pct` (default 1%) |
| `volume` | float | `risk_amount / risk_distance` — **DESIGN_ASSUMPTION_V1**: 1 unità = 1 oncia, nessun modello di margine/contratto |
| `fill_bar_epoch` / `fill_price` | int \| null / float \| null | `null` se mai riempito |
| `fill_uncertain_reason` | string \| null | `"NO_NEXT_BAR_AVAILABLE_FOR_FILL"` \| `"NON_POSITIVE_RISK_DISTANCE"` \| `null` |
| `exit_bar_epoch` / `exit_price` | int \| null / float \| null | |
| `outcome` | `"TP_HIT"` \| `"SL_HIT"` \| `"DATASET_ENDED_STILL_OPEN"` \| `"FILL_UNCERTAIN"` \| `null` | `null` solo mentre il tentativo è ancora aperto nel record scritto a fine corsa (vedi `run_full_replay.py`, che chiude sempre l'ultimo tentativo pendente con `close_still_open_at_dataset_end`) |
| `mfe_price_units` / `mae_price_units` | float | Massima escursione favorevole/avversa osservata, in unità di prezzo |
| `cost_breakdown` | object | `{"slippage_price_units","spread_price_units_at_signal_bar","realized_pnl"?,"exit_slippage_price_units"?}` |
| `bars_held` | int | Numero di bar durante cui il tentativo è rimasto aperto |
| `is_open` | bool | `false` per ogni record scritto nel journal a fine corsa (i tentativi ancora aperti vengono chiusi esplicitamente prima della scrittura) |

## 4. `shadow_audit_event` — perché è un campo e non un secondo segnale

Riusa **verbatim** `phase5d_shadow_engine_v1.contract.build_event()` —
lo stesso generatore di `DecisionEvent` usato da ogni altra candidata
NEXUS già censita in `vault/`. Passandogli
`registry_status={"H1_A":"RESEARCH_ONLY"}` (mai scritto nel file
canonico `contracts/strategy-registry.json`), l'arbiter del motore
riusato garantisce per costruzione che
`hypothetical_decision` sia sempre `"NO_TRADE"` e
`authorization_status` sia sempre `"OBSERVATION_ONLY"` o
`"NO_CANDIDATES_CONFIRMED_EMPTY"` — **mai** `AUTHORIZED_EXECUTABLE`.
Questo è un secondo livello di sicurezza, indipendente dal Paper
Engine: anche se questo journal venisse letto in futuro da un
percorso realmente registry-gated, il campo stesso proverebbe che
H1_A non può essere scambiato per una decisione autorizzata live. Non
è mai usato per guidare il Paper Engine (quel ruolo appartiene
esclusivamente a `h1a_decision`).

## 5. Campi esplicitamente NON presenti (per trasparenza)

- Nessun campo di PnL cumulativo nel Decision record (solo nel
  `run_summary.json` aggregato, vedi `TEST_RESULTS.md`).
- Nessun campo "confidence"/"probabilità" — nessuna fonte NEXUS
  fornisce una calibrazione per H1_A (`calibration_status: "UNKNOWN"`
  dentro `shadow_audit_event`, dichiarato, non omesso).
