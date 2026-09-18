# NEXUS Terminal — UI Phase 3 Execution

## Scope

Phase UI-3 replaces the `/execution` landing page with an operational workspace. It consolidates existing EA, position, runtime-engine, risk, LocalBridge, allocation and ledger data without changing commands, trading logic, research logic, authentication or MQL5.

## Execution domain model

`GET /api/execution/snapshot` is an authenticated, read-only materialized view with schema `execution-read-model-v1`.

| Entity | Current representation | Availability |
| --- | --- | --- |
| Engine | Saved engine configuration plus ledger-derived allocation stats | Configuration cached; actual runtime state unavailable |
| Signal | Stable join and timestamp | Unavailable |
| Order | Order-sent timestamp, requested price | Unavailable |
| Fill | Dedicated fill timestamp and fill price | Unavailable |
| Position | EA-reported open positions | Live or stale according to EA freshness |
| Exit | Authoritative ledger terminal trade | Derived; partial lifecycle |
| RiskState | EA risk telemetry plus saved limits | Live/stale with nullable fields |
| BridgeState | LocalBridge heartbeat and recent command queue | Live, cached/stale or unavailable |

The API never constructs Signal, Order or Fill objects from a position. `execution_quality.state` is `PARTIAL` only when at least position timing exists, otherwise `UNAVAILABLE`. It lists the missing join fields explicitly.

## Current data sources

- EA state, positions, account values and risk telemetry: latest `ea_status` payload, also exposed by `/api/ea/status`.
- Runtime engine enablement and risk limits: current saved settings.
- Allocation multipliers and execution statistics: authoritative ledger-derived strategy leaderboard.
- Recent actual performance: authoritative terminal events through the reconciled ledger read model.
- Bridge worker and queue: LocalBridge hosts and command records.
- Health: the existing telemetry-health calculation; it is not an independent risk guarantee.

Every domain includes provenance. Old EA data is `STALE`, never `LIVE`; missing fields remain `null` and render as `—`.

## Runtime engine versus canonical strategy

An Execution Engine is an executable configuration: saved enabled state, engine identifier, family, allocation multiplier and any actual trade statistics. Saved enablement is marked `CACHED`; it does not prove that a specific engine is currently running inside the EA, so `runtime_status` remains `UNAVAILABLE`. This also does not establish that the corresponding idea is a validated canonical Strategy or Edge Component. The read model therefore returns `canonical_strategy_status: UNAVAILABLE` until explicit stable relations exist.

## Workspace structure

Desktop presents:

1. compact EA/Bridge/account/risk/freshness strip;
2. a single execution-specific `Needs attention` queue;
3. live positions with existing close and partial-close confirmation flow;
4. risk budget/protection summary;
5. runtime engines and Allocation summary;
6. MT5/Bridge status;
7. honest Execution Quality coverage and recent actual trades.

The Trade Lifecycle inspector now marks Signal, Gate and Order phases unavailable unless their fields are actually present. A position open time proves only the position/fill-adjacent stage, not the upstream signal or broker latency.

Mobile uses `Live`, `Engines`, `Risk` and `Systems` tabs. Execution Quality is available under Systems. Wide position data remains inside its controlled horizontal table container.

## Allocation terminology

The legacy `/optimizer` route remains unchanged, but the workspace and navigation call this operational function **Allocation**. It adjusts runtime risk multipliers from actual execution performance and must not be confused with research parameter optimization.

## Strategy Analytics split

Execution links to runtime diagnostics and uses only actual ledger performance, blockers and runtime configuration. Canonical research evidence stays in Research. The legacy `/strategy-analytics` page remains available and is not removed or reclassified in this phase.

## Legacy mapping

- `/strategies` → detailed engine configuration
- `/optimizer` → Allocation detail
- `/risk` → full risk controls
- `/local-bridge` → advanced bridge and worker operations
- `/chain` → strategy runtime chain
- `/analytics` → full execution analytics
- `/strategy-analytics` → retained mixed diagnostic page pending later internal split

All existing routes and mutation paths remain intact.

## Signal-to-fill gaps

Reliable latency, slippage and rejection analysis still requires stable identifiers and timestamps for `signal_id`, `decision_id`, signal observation, order submission, broker acknowledgement/fill, requested price, fill price and reject reason. These fields must share a stable join to the resulting position/trade. Until then the UI shows `Signal-to-fill telemetry incomplete` and no fabricated latency or slippage.

## Known limitations

- Current-price, exposure, SL, TP, duration and engine attribution depend on optional EA payload fields.
- LocalBridge state describes the local worker, not necessarily terminal login or broker connectivity.
- Allocation statistics are derived from terminal ledger events; they are not research validation.
- Command queue failures are shown as exceptions, but no new command behavior was added.
- There is no SSE/WebSocket execution stream; the read-only snapshot uses visibility-aware 10-second polling.
