# 16. Migration Roadmap and Claude Execution Plan

## Baseline

The project baseline was already frozen in the previous session. Do not repeat that step unless the repository has materially changed since the recorded baseline.

## Governing implementation rules

Claude must:

1. work on a dedicated branch;
2. read this full architecture pack first;
3. state the exact files to be changed before editing;
4. keep each PR focused on one architectural concern;
5. add tests before or with the implementation;
6. avoid broad refactors of strategies, frontend and backtest in P0 repairs;
7. never merge directly to `main`;
8. stop and request a decision when repository behavior is ambiguous.

## Phase A — Data integrity and safety

### PR 1: Trade lifecycle ledger

**Objective:** distinguish deals, orders, positions and logical trades; fix partial-close semantics.

**Files likely involved:**

- `MQL5/Experts/NEXUS_EA_v2.mq5`
- `MQL5/Include/NEXUS_v1/NXS_HistorySync.mqh`
- `MQL5/Include/NEXUS_v1/NXS_StratStats.mqh`
- `MQL5/Include/NEXUS_v1/NXS_StrategyChain.mqh`
- protection/notification hooks reached from `OnTradeTransaction`
- `server/app.py`
- new backend migration/test files.

**Acceptance tests:**

1. one entry + one full exit;
2. two partial exits + final exit;
3. duplicate deal replay;
4. restart and history resync;
5. two positions on the same symbol;
6. exactly one `TRADE_CLOSED` per logical trade.

### PR 2: Virtual stop execution workflow

- virtual stop remains active until broker close confirmation;
- close retry is bounded and logged;
- state survives restart or the feature fails safely;
- dashboard distinguishes trigger/request/confirmation.

### PR 3: Protection pipeline ordering

- refresh settings/protections before new exposure;
- integrate RiskShield master gate;
- route Grid/Pyramid through common exposure and preflight controls;
- add structured gate telemetry.

### PR 4: Position-management coordinator

- modules create proposals rather than modifying independently;
- deterministic priority resolution;
- no accidental stop loosening;
- one management action per position per cycle.

### PR 5: Durable operational state

- versioned atomic snapshot;
- final save bypasses throttle;
- broker reconciliation on restore;
- persist logical IDs, groups, entry ATR and management phase.

## Phase B — Shared contracts

### PR 6: Canonical strategy registry

- reconcile all 35/36/37 and research-only entries;
- generate/validate backend and frontend adapters;
- remove hardcoded counts;
- unknown strategy becomes validation error.

### PR 7: Settings schema and profiles

- versioned JSON schema;
- backend validation;
- frontend validation and typed inputs;
- profile versions/checksums;
- eliminate divergent defaults.

### PR 8: Command and LocalBridge contract

- target-scoped commands;
- leases, retries and dead-letter state;
- canonical enums/IDs/timestamps;
- remove duplicate worker source;
- versioned deployment manifest.

## Phase C — Presentation and analytics

### PR 9: Ledger-derived analytics

- rebuild trade statistics from immutable events;
- label provenance;
- quarantine legacy-unverified history;
- stop using overwritten `trades` rows as analytical truth.

### PR 10: Frontend data layer

- independent queries rather than one global `Promise.all`;
- command ACK/status;
- suspend hidden-tab polling;
- show observed vs inferred vs simulated information;
- fix missing/mismatched endpoints.

## Phase D — Research system

### PR 11: Research-simulator correctness

- unknown strategy = error;
- forced end-of-data settlement;
- explicit synthetic-data flag;
- correct metric naming;
- engine/config/data hashes.

### PR 12+: Broker-aware validation engine

Add costs, multi-position behavior, broker sizing, floating DD and selected strategy parity incrementally. Keep it separately named until validated.

## First Claude prompt

```text
You are responsible only for NEXUS trade-lifecycle correctness.

Repository: starmarketkiller/MAX
Branch: fix/trade-lifecycle-ledger

Before editing:
1. Read every file in docs/architecture.
2. Read the EA transaction path, HistorySync, StratStats, StrategyChain,
   protections/notifications reached by close hooks, and server/app.py.
3. Produce a call graph for DEAL_ENTRY_OUT.
4. List the exact files you intend to modify.
5. Do not modify frontend, backtest, strategy signal logic, or trading parameters.

Required behavior:
- A partial exit emits a volume-reduction event, not a final trade close.
- Final close is emitted only after residual broker position volume is zero
  or the position no longer exists.
- DealID, OrderID, PositionID and LogicalTradeID are distinct.
- Every deal is immutable and idempotent on replay.
- StrategyChain, consecutive-loss protections, statistics and final
  notifications run exactly once per logical trade.
- Existing APIs remain backward-compatible through a temporary read model.

Tests required:
1. single full close;
2. multiple partial closes then final close;
3. duplicate deal;
4. restart/resync;
5. two same-symbol positions;
6. migration from legacy database;
7. exactly-once final-close hooks.

Deliverables:
- plan before code;
- minimal implementation;
- migration and rollback note;
- automated tests;
- updated architecture document where implementation differs;
- one logical commit per step;
- no merge to main.
```

## Review gate after every PR

Do not start the next PR until:

- tests pass;
- MQL5 compiles where relevant;
- a reproducible scenario demonstrates the fix;
- schema/backward compatibility is reviewed;
- documentation is updated;
- no unrelated files were changed.
