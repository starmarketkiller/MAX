# 8. Position-Management Ownership

## Current managers

A single position may be touched by:

- classic breakeven/trailing logic;
- `NXS_TrailingATR`;
- `NXS_SplitTrade`;
- `NXS_InstManage`;
- virtual-stop logic;
- Grid/Pyramid/Recovery logic.

## Confirmed defect

No central arbitration layer was observed. Multiple modules can modify SL/TP during the same tick. The effective result is dependent on execution order: the last successful modification wins.

## Additional current risks

- Split targets use current ATR rather than a guaranteed entry ATR snapshot.
- Partial close volume normalization may not consistently use `SYMBOL_VOLUME_STEP`.
- institutional management groups positions by symbol/direction without an explicit persisted group identifier.
- Grid/Pyramid comments may not preserve original strategy identity reliably.
- current management state is mainly in RAM.

## Target model: proposal and arbitration

Each module should return a proposal without directly modifying the broker position.

```json
{
  "position_id": "123",
  "proposal_type": "MOVE_STOP",
  "source": "ATR_TRAILING",
  "priority": 50,
  "new_sl": 2350.10,
  "new_tp": null,
  "reason": "2 ATR trail",
  "valid_until_tick": 456
}
```

A `PositionManagementCoordinator` selects one final action per position.

## Priority model

Suggested priority, highest first:

1. emergency account/virtual-stop close;
2. hard catastrophic protection;
3. final time stop;
4. split/partial-exit action;
5. break-even protection;
6. institutional/structural stop;
7. ATR/classic trailing;
8. optional target extension.

A lower-priority proposal may never loosen a stronger protective stop unless the policy explicitly allows it.

## Ownership state

Every managed position should store:

- logical trade ID;
- group ID;
- original entry ATR;
- strategy ID;
- management profile ID/version;
- current phase (`INITIAL`, `BREAKEVEN`, `RUNNER`, `RECOVERY`, etc.);
- last applied proposal/event ID;
- residual volume.

## Acceptance criteria

- at most one broker modification per position per management cycle;
- deterministic winner selection;
- no stop regression without explicit audited policy;
- restart reconstructs management phase;
- partial close and final close are distinguished;
- all changes are confirmed against broker state.
