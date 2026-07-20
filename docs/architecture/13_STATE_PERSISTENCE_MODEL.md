# 13. State Persistence Model

## Current persisted state

The inspected `NXS_State` implementation primarily persists daily protection state and saves periodically.

## Important state currently at risk

Not fully and reliably persisted/reconstructed:

- virtual-stop records;
- Strategy Chain state;
- institutional/recovery groups;
- recovery depth;
- original ATR and entry context;
- SplitTrade phase and residual targets;
- Grid/Pyramid relationships;
- last processed deal/event;
- command cursor.

## Confirmed shutdown risk

`OnDeinit` invokes save, but the ordinary 30-second throttle can prevent a final immediate write.

## Target state categories

### Reconstructable from broker history

- active broker positions;
- deals and orders;
- current volume and prices.

### Must be persisted by Nexus

- logical trade ID mapping;
- strategy identity where broker comment is insufficient;
- group membership;
- original decision inputs;
- management phase;
- original ATR/structural stop;
- virtual-stop state;
- last processed event cursor;
- settings/profile version applied.

### Derived and disposable

- dashboard snapshots;
- cached indicators;
- temporary analytics;
- UI filters.

## Snapshot format

```json
{
  "schema_version": 2,
  "instance_id": "...",
  "run_id": "...",
  "saved_at": "...",
  "last_event_id": "...",
  "profile_version": 4,
  "positions": [],
  "groups": [],
  "protections": {},
  "checksum": "..."
}
```

## Durability rules

1. Write to temporary file.
2. Flush and close.
3. Verify checksum/readability.
4. Atomically replace previous snapshot.
5. Keep previous known-good snapshot.
6. Final shutdown save bypasses throttle.
7. Restore validates schema and broker reconciliation before enabling new entries.

## Restore policy

If state cannot be reconciled with broker positions:

- block new exposure;
- retain emergency management capability;
- emit `STATE_RESTORE_FAILED`;
- require deterministic recovery or operator acknowledgement.
