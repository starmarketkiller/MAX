# Design: Mix Structure + Workflow (A + B + C)

Data: 2026-10-19. Branch: `cursor/structure-workflow-mix-8f05`. Base: `main`.

## Intent

Eseguire in un solo PR tre binari indipendenti già mappati:

| Track | Nome | Obiettivo |
|---|---|---|
| A | Workflow #2 | L'EA emette `event=open` su `/api/ea/trade_reason` al primo deal IN |
| B | Structure OB Phase A | Telemetry-only Order Block → Unified Level Registry (`source=ORDER_BLOCK`) |
| C | Research WICK | Hardening del dataset causale già prodotto (schema + CLI portabile) |

## Vincoli non negoziabili

- Python non invia ordini. Solo telemetria / ledger / ricerca.
- Track B: zero cambiamenti a segnali, SL/TP, execution, `NXS_Structure.mqh`, `NXS_Reaction.mqh`.
- Track C: nessuna nuova ottimizzazione di WICK; baseline negativa resta congelata.
- `trading_v1` / TradingSupervisor non è su `main`: fuori scope (resta documentato come passo successivo).

## Track A — Open event

### Problema

`NXS_Ledger_OnDeal` già classifica `NXS_LEDGER_EV_OPEN`, ma `OnTradeTransaction` lo ignora per il backend. Il backend accetta già `"open"` in `EA_TRADE_EVENTS` (non autoritativo → solo `trade_events`).

### Design

1. In `OnTradeTransaction`, dopo `NXS_Ledger_OnDeal`, se `ev == NXS_LEDGER_EV_OPEN`:
   - aggregare la position con `NXS_Ledger_AggregatePosition`;
   - chiamare `NXS_Prot_PushTradeReason(..., eventKind="open")` con PnL=0, closePrice=openPrice, closeTime=openTime;
   - log CSV `OPEN` opzionale (stesso stile di PARTIAL).
2. Backend: test che `open` entra in `trade_events`, non upserta PnL in `trades`, è idempotente su replay `(trade_uid, event)`.
3. Nessun collegamento al supervisore (assente su main).

### Fail-safe

Se `AggregatePosition` fallisce: nessun push, solo log. Nessun blocco del tick.

## Track B — Order Block Phase A

### Problema

WICK è migrato A→E. Prossima famiglia del migration plan: `SNXSOBState` (lifecycle maturo, isolato da `g_struct`).

### Design

1. Spostare `#include` di `NXS_LevelRegistry.mqh` / `NXS_ReactionEngine.mqh` **prima** di `NXS_Strategies.mqh` così gli hook OB possono chiamare `NXS_Reaction_*`.
2. Generalizzare `NXS_LevelReg_Create` con parametro `source` (WICK passa `"WICK"`, OB passa `"ORDER_BLOCK"`).
3. Estendere `SNXSOBState` con `long id` (identità stabile, come WICK).
4. Hook causali in `NXS_OB_UpdateSide` (dietro `InpLevelRegistry_ObTelemetry`, default `true`):
   - create zona → `NXS_Reaction_OnLevelCreated` (side HIGH/LOW da dir);
   - invalidate (max wait / price through) → `NXS_Reaction_OnInvalidated`;
   - consume (signal one-shot) → `NXS_Reaction_OnConsumed` con `source_strategy=ORDER_BLOCK`.
5. Contatori `g_nxsObParity` + `NXS_LevelEngine_PrintObParity` (create/invalidate/consume vs funnel locale OB).
6. Nessun read-path, nessun cambio gate HTF/reaction.

### Fuori scope B

Fase B/C/D OB, FVG, `Structure.mqh`, default `WickReadPath=true`.

## Track C — Causal dataset hardening

### Stato

Experiment 1–3 già eseguiti; `results/causal_experiment_1/` contiene dataset congelati. Script hardcodato su path Windows locali.

### Design

1. Test Python CI-safe: valida schema CSV, cardinalità ≥ 150, outcome ∈ {PLUS_1R_FIRST, MINUS_1R_FIRST, CENSORED}, `created_time ≤ timestamp`, split id univoci.
2. CLI portabile su `causal_experiment_1_wick_sweep_1r.py`: `--events-dir`, `--bars`, `--out` (default: path relativi al repo se presenti).
3. Nessuna riesecuzione MT5 in questo ambiente.

## Ordine di implementazione

1. A (test backend → hook EA)
2. B (include order → schema → hooks → parity print)
3. C (test schema → CLI)
4. Aggiornare `docs/TRADING_WORKFLOW_COVERAGE_V1.md` (blocco #2: EA emette open; supervisore ancora aperto)

## Verifica

- `pytest server/tests/test_trade_lifecycle.py server/tests/test_causal_experiment_1_dataset.py` (+ eventuale test statico OB/open sorgente)
- Verifier MQL5 skill se disponibile
- Compile MT5: NOT_COMPILED in questo ambiente
