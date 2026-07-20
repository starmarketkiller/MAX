# 2. Runtime Tick Pipeline

## Current lifecycle entry points

**Observed in `NEXUS_EA_v2.mq5`:**

- `OnInit`
- `OnDeinit`
- `OnTimer`
- `OnTick`
- `OnTradeTransaction`

## Reconstructed `OnTick` order

```text
1. Fresh tick received
2. Spread sample update
3. Virtual-SL hit detection
4. Daily rollover/state checks
5. Indicator and market-state update
6. Classic position management
7. ATR trailing
8. Split-trade management
9. Institutional management OR Grid/Pyramid additions
10. Risk-of-Ruin update
11. Protection refresh
12. Dashboard/runtime settings pull
13. Telemetry push
14. New-bar gate
15. Structure and context calculations
16. Entry gates
17. Strategy signal collection
18. Confluence / scoring / routing
19. Data, institutional or classic execution path
```

## Confirmed ordering risks

### Portfolio changes before full protection refresh

Institutional/Grid/Pyramid actions occur before risk protections and dashboard settings are refreshed for the current tick.

**Impact:** an add-on order can be evaluated using stale protection or configuration state.

### Multiple managers before new-entry evaluation

Management modules run sequentially and can each modify the same position. No explicit ownership arbitration was observed.

### Virtual-SL detection is early but closure is not guaranteed

The check runs near the beginning of `OnTick`, but the inspected implementation records/deactivates the virtual stop state without being a complete close-confirmation workflow.

### Settings synchronization after management

Runtime settings from the dashboard are pulled after position-management actions. A newly changed risk or management setting may therefore take effect one tick later than expected.

## `OnTimer`

**Observed:** periodic web telemetry is pushed from `OnTimer`, while another push occurs from `OnTick`.

**Risk:** duplicated snapshots, increased load and ambiguous freshness unless backend ingestion is idempotent and timestamps are explicit.

## `OnTradeTransaction`

### Current interpretation risk

Every `DEAL_ENTRY_OUT` is treated as a closing event by several modules.

Potential downstream actions include:

- trade-close statistics;
- Strategy Chain state update;
- loss-protection update;
- notifications;
- logging and history synchronization.

**Confirmed defect:** `DEAL_ENTRY_OUT` does not necessarily mean the logical position is fully closed. It can be a partial exit.

## Required target ordering

**Proposed:**

```text
Tick snapshot
→ refresh settings and protection state
→ reconcile broker positions and persisted state
→ emergency exits / confirmed virtual-stop actions
→ compute management proposals
→ resolve one final management action per position
→ apply portfolio-level exposure gates
→ process add-on orders
→ process new-entry signals
→ record decisions and execution outcomes
→ publish telemetry
```

## Acceptance criteria for future refactor

1. Configuration and protection state are refreshed before any new exposure is added.
2. Each position has one management decision per tick.
3. Partial exits never trigger final-close hooks.
4. Telemetry events have stable IDs and are idempotent.
5. An emergency close remains active until broker confirmation is observed.
