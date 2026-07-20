# 3. Trade Identity Model

## Problem statement

The current code uses `ticket` to represent multiple different entities. This prevents reliable partial-close handling, idempotent synchronization and trustworthy analytics.

## Required identities

| Identity | Meaning | Cardinality |
|---|---|---|
| `DecisionID` | One evaluated strategy/portfolio decision | many per signal or tick |
| `SignalID` | One generated strategy signal | can create zero or more orders |
| `LogicalTradeID` | One business-level trade lifecycle | can span multiple orders/deals |
| `PositionID` | Broker position identifier | one or more per logical trade depending on account mode |
| `OrderID` | Broker order request/order identifier | many per logical trade |
| `DealID` | Broker execution/fill identifier | many per order/position |
| `ExecutionID` | Internal normalized execution-event identifier | one per ingested broker event |
| `GroupID` | Grid, pyramid, recovery or institutional group | groups multiple positions/trades |
| `RunID` | EA process/session identity | groups runtime events |
| `InstanceID` | Stable EA installation/account/symbol identity | stable across restarts |

## Current defects

**Observed:** backend `trades.ticket` is a primary key and may receive a position ID from history sync.

**Confirmed defect:** multiple exit deals for one position can overwrite the same row.

**Observed:** transaction hooks act on exit deals directly rather than first establishing whether residual position volume is zero.

**Impact:**

- partial closes counted as full trades;
- repeated close hooks;
- corrupted consecutive-loss counters;
- Strategy Chain transitions more than once;
- incorrect win rate and profit factor;
- historical re-sync cannot be made safely idempotent.

## Canonical lifecycle

```text
SignalID
  └── DecisionID
       └── LogicalTradeID
            ├── OrderID 1
            │    ├── DealID 1 (entry fill)
            │    └── DealID 2 (partial exit)
            ├── OrderID 2
            │    └── DealID 3 (final exit)
            └── PositionID / GroupID
```

## Final-close rule

A final-close event is emitted only when both conditions hold:

1. the exit deal was successfully ingested; and
2. the associated broker position no longer exists or its residual volume is zero within symbol-volume tolerance.

A partial exit emits `POSITION_VOLUME_REDUCED`, not `TRADE_CLOSED`.

## Idempotency rules

- `DealID` must be unique per broker account.
- Re-ingesting the same deal produces no duplicate event.
- `TRADE_CLOSED` has a uniqueness constraint on `LogicalTradeID`.
- Derived statistics update from immutable events, not by overwriting a trade row.
- History synchronization uses a cursor and can safely replay.

## Hedging and netting accounts

**Needs runtime verification:** confirm supported MT5 account mode.

- In hedging mode, multiple `PositionID`s may exist for the same symbol/direction.
- In netting mode, multiple orders/deals contribute to one `PositionID`.

The model above supports both by not equating `LogicalTradeID` with `PositionID`.

## Minimum database entities

```text
runtime_instances
signals
decisions
logical_trades
positions
orders
deals
events
trade_groups
```

The first Claude implementation should add the ledger without removing existing read models until migration is complete.
