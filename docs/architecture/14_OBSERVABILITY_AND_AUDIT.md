# 14. Observability and Audit

## Current observability

The repository contains extensive CSV logging, strategy statistics, telemetry pushes, history synchronization, diagnostics and frontend analytics.

## Current limitations

- shared CSV files lack complete account/instance/group identity;
- file-open failure can silently lose telemetry;
- trade-close logs may be deal-level rather than logical-trade-level;
- history sync repeatedly scans a bounded window without a durable cursor;
- backend snapshots are overwritten and lack immutable history;
- analytics mix observed, reconstructed and simulated data;
- opening logs in institutional paths may contain zero ticket/lot placeholders;
- telemetry may be pushed from both timer and tick paths.

## Canonical correlation fields

Every log/event should include:

- `instance_id`;
- `run_id`;
- `account_id`;
- `symbol`;
- `strategy_id`;
- `signal_id`;
- `decision_id`;
- `logical_trade_id`;
- `position_id`;
- `deal_id`;
- `group_id`;
- `event_id`;
- UTC timestamp and broker timestamp.

## Log levels and categories

- `AUDIT` — settings, commands, profile and operator changes;
- `RISK` — gates, breakers, exposure and emergency actions;
- `EXECUTION` — order/deal/broker outcomes;
- `STRATEGY` — signals and score contributions;
- `MANAGEMENT` — stop/partial-close proposals and decisions;
- `SYSTEM` — startup, restore, connectivity and failures;
- `RESEARCH` — simulation provenance and experiment metadata.

## Metrics

Minimum operational metrics:

- event-ingestion lag;
- duplicate events rejected;
- command age and retry count;
- last EA heartbeat;
- broker-request error rate;
- unprotected-position count;
- positions with state mismatch;
- settings-version drift;
- history-sync cursor lag;
- telemetry-drop count.

## Audit requirements

- who changed what, when and from which prior value;
- every locked profile version and checksum;
- command creator and target;
- deployment release manifest;
- strategy enable/disable provenance;
- no silent automated strategy disable without auditable rule/version.

## Historical-result validity

Backtest and live result artifacts should carry a manifest:

```text
CANONICAL
EXPERIMENTAL
SYNTHETIC
PRE_FIX
INVALIDATED_BY_BUG
LEGACY_UNVERIFIED
```

Results produced before the partial-close/trade-identity repairs should not automatically train or drive automated risk decisions.
