# 1. Architecture Overview

## Purpose

Describe the current NEXUS system boundaries, sources of truth, integration paths, and the principal architectural risks.

## Current system map

```text
MT5 Expert Advisor
  MQL5/Experts/NEXUS_EA_v2.mq5
  MQL5/Include/NEXUS_v1/*.mqh
        |
        | HTTP telemetry, configuration and commands
        v
FastAPI backend
  server/app.py
        |
        +--> SQLite operational snapshots and analytics tables
        +--> Research backtest / sweep engine
        +--> Static legacy dashboard
        |
        v
React dashboard
  frontend/src/*

LocalBridge
  LocalBridge/nexus_local_worker.py
  server/nexus_local_worker.py
        |
        v
Local MT5 host / deployment actions

Separate research plane
  server/backtest.py
  server/sweep.py
  server/bt_verdict.py
  results/*
```

## Current responsibilities

| Component | Current responsibility | Architectural classification |
|---|---|---|
| MT5 EA | Market data, signals, risk checks, execution, position management | Operational authority |
| FastAPI | Settings, snapshots, commands, trade history, analytics, licenses | Configuration and snapshot server |
| React | Operator control panel and analytics presentation | Polling client |
| LocalBridge | Remote-to-local command transport | Worker bridge |
| Python backtest | Fast strategy research using approximations | Research simulator |
| SQLite | Mixed snapshots, configuration and derived analytics | Non-event-sourced store |

## Primary source-of-truth problem

**Observed:** different concepts are independently defined in multiple layers:

- strategy names and counts;
- settings defaults;
- command status values;
- trade identifiers;
- lifecycle states;
- analytics metrics;
- backtest behavior.

**Confirmed defect:** no single canonical contract currently governs these copies. This creates drift such as 35/36/37 strategy counts, mismatched LocalBridge statuses, and settings defaults that differ between EA, backend and frontend.

## Operational data flow

```text
Tick
→ indicator/state update
→ position management
→ portfolio additions
→ protections/config refresh
→ signal generation
→ gates and sizing
→ order execution
→ transaction callback
→ telemetry/history synchronization
→ backend snapshots
→ frontend polling/analytics
```

The exact ordering is documented in `02_RUNTIME_TICK_PIPELINE.md`.

## Highest-risk architectural defects

1. A partial exit can be treated as a complete trade close.
2. Position, deal, order and logical trade identities are conflated.
3. Virtual stop-loss detection does not itself guarantee closure.
4. RiskShield master gating appears disconnected from the main entry path.
5. Multiple position-management modules can overwrite the same stop.
6. Grid/Pyramid additions can take a different path than primary entries.
7. State required to reconstruct live management is not fully persisted.
8. Analytics and strategy verdicts depend on a trade ledger that may be overwritten.
9. The research backtest is presented more strongly than its parity supports.
10. Frontend and backend contracts are partly implicit and inconsistent.

## Target architectural direction

**Proposed:** retain MT5 as broker/execution authority initially, but introduce shared contracts and an immutable event ledger. Separate the system into four explicit planes:

1. **Execution plane** — MT5 broker interaction.
2. **Decision plane** — strategy, risk and portfolio decisions.
3. **Control plane** — settings, commands, profiles and deployment.
4. **Research plane** — backtesting, sweeps and strategy experiments.

Research results must never silently become live truth. Promotion from research to live should be versioned and auditable.

## Non-goals for the first repair cycle

- redesigning all strategies;
- tuning profitability;
- replacing the EA with the backend;
- turning the Python simulator into a digital twin immediately;
- redesigning the full UI before correcting data integrity.
