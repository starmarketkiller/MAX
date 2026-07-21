# PR9 — Ledger-derived analytics

## Authoritative source

Realised performance metrics are derived from the append-only `trade_events`
ledger. Mutable `trades` rows remain a temporary journal/read model and are not
used as analytical truth.

For each `trade_uid`, the read model selects exactly one terminal event:

1. `close` (`OBSERVED_LIVE`) when present;
2. otherwise `resync` (`RECONSTRUCTED_HISTORY`).

A later resync or overwrite of `trades.pnl` cannot change a metric already
supported by a close event. Every aggregate is labelled `DERIVED_ANALYTICS`.

## Legacy quarantine

Rows without a non-legacy terminal event, plus synthetic `legacy:*` event IDs,
are labelled `LEGACY_UNVERIFIED`, counted in the provenance response and
excluded from all authoritative metrics. They can only enter analytics after a
broker-deal reconstruction produces verifiable ledger evidence.

## Consumers migrated

- analytics trades, summary, reason, what-if, calendar and heatmap;
- strategy leaderboard, risk autoscaling and live diagnostics;
- EA health profit factor, journal aggregate and chart markers.

The dashboard displays both the metric provenance and the number of quarantined
legacy rows.

## Acceptance checks

- mutable trade overwrite does not alter ledger P&L;
- close plus resync is counted once, with close preferred;
- resync-only history is explicitly reconstructed;
- legacy history is quarantined and excluded.
