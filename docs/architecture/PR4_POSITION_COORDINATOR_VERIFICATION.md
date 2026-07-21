# PR4 Position Coordinator Verification

## Scope

- Classic, profile, ATR, split and institutional management submit proposals.
- A coordinator selects one action per ticket and management cycle.
- Priority is deterministic: close, partial exit, break-even, institutional, trailing.
- A proposed stop that loosens the broker stop is rejected before arbitration and rechecked before apply.
- Partial-close volumes are aligned to the broker volume step.
- Every winner emits a structured `[NEXUS MANAGEMENT]` record.

## Static acceptance scenarios

1. Multiple stop proposals for one ticket produce one broker modification.
2. A close proposal outranks partial and modify proposals.
3. A partial exit outranks stop modifications.
4. Break-even outranks institutional and trailing proposals.
5. Equal-priority stop proposals choose the tighter stop, then source name for a stable tie-break.
6. BUY stops cannot move down and SELL stops cannot move up.
7. A successful split source is not applied twice to the same ticket.

MT5 runtime/Strategy Tester tests are intentionally excluded at the user's request.
