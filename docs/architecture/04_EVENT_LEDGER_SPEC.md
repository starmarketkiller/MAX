# 4. Event Ledger Specification

## Objective

Introduce an immutable, replayable record of what NEXUS observed, decided, requested and confirmed.

## Event envelope

Every event should contain:

```json
{
  "event_id": "uuid-or-deterministic-id",
  "event_type": "POSITION_VOLUME_REDUCED",
  "schema_version": 1,
  "occurred_at": "broker/event timestamp",
  "recorded_at": "backend ingestion timestamp",
  "instance_id": "stable EA instance",
  "run_id": "current EA session",
  "account_id": "broker account scope",
  "symbol": "XAUUSD",
  "strategy_id": "canonical strategy ID or null",
  "signal_id": "...",
  "decision_id": "...",
  "logical_trade_id": "...",
  "position_id": "...",
  "order_id": "...",
  "deal_id": "...",
  "group_id": "...",
  "payload": {},
  "source": "EA|BACKEND|BRIDGE|OPERATOR"
}
```

## Core event types

### Runtime and configuration

- `INSTANCE_STARTED`
- `INSTANCE_STOPPED`
- `SETTINGS_RECEIVED`
- `SETTINGS_APPLIED`
- `PROFILE_LOCKED`
- `PROFILE_REJECTED`
- `STATE_RESTORED`
- `STATE_RESTORE_FAILED`

### Signal and decision

- `SIGNAL_GENERATED`
- `SIGNAL_REJECTED`
- `DECISION_CREATED`
- `GATE_EVALUATED`
- `ENTRY_APPROVED`
- `ENTRY_BLOCKED`

### Execution

- `ORDER_REQUESTED`
- `ORDER_ACCEPTED`
- `ORDER_REJECTED`
- `DEAL_RECORDED`
- `POSITION_OPENED`
- `POSITION_VOLUME_INCREASED`
- `POSITION_VOLUME_REDUCED`
- `POSITION_CLOSED`
- `TRADE_CLOSED`

### Management and protection

- `MANAGEMENT_PROPOSAL_CREATED`
- `MANAGEMENT_DECISION_APPLIED`
- `STOP_MODIFICATION_REQUESTED`
- `STOP_MODIFICATION_CONFIRMED`
- `VIRTUAL_STOP_TRIGGERED`
- `EMERGENCY_CLOSE_REQUESTED`
- `EMERGENCY_CLOSE_CONFIRMED`
- `PROTECTION_STATE_CHANGED`

### Commands and deployment

- `COMMAND_CREATED`
- `COMMAND_LEASED`
- `COMMAND_ACKNOWLEDGED`
- `COMMAND_COMPLETED`
- `COMMAND_FAILED`
- `COMMAND_EXPIRED`

## Event vs read model

The ledger is append-only. User-facing tables remain read models derived from the ledger:

- open positions;
- completed trades;
- strategy statistics;
- protection state;
- command status;
- journal view.

A read model may be rebuilt from the event stream. Direct mutation of historical events is prohibited.

## Provenance

Every displayed metric should state one of:

- `OBSERVED_LIVE`
- `RECONSTRUCTED_HISTORY`
- `DERIVED_ANALYTICS`
- `SIMULATED_RESEARCH`
- `SYNTHETIC_DATA`

This prevents the frontend from presenting inferred timelines as directly observed facts.

## Retention and migration

- Existing `trades` and snapshot tables remain temporarily.
- New writes go to both ledger and legacy tables during transition.
- After reconciliation, analytics switch to ledger-derived read models.
- Historical data affected by the partial-close defect must be marked `LEGACY_UNVERIFIED` unless reconstructed from broker deals.
