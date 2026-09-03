# NEXUS Architecture Pack

This folder documents the architecture reconstructed from the repository snapshot and from the prior audit sessions.

## Evidence labels

- **Observed** — directly present in repository code or configuration.
- **Confirmed defect** — behavior follows directly from the inspected call graph or data model.
- **Needs runtime verification** — static inspection is insufficient; verify in MT5, logs, or deployment.
- **Proposed** — target architecture or remediation, not current behavior.

## Documents

1. [Architecture overview](01_ARCHITECTURE_OVERVIEW.md)
2. [Runtime tick pipeline](02_RUNTIME_TICK_PIPELINE.md)
3. [Trade identity model](03_TRADE_IDENTITY_MODEL.md)
4. [Event ledger specification](04_EVENT_LEDGER_SPEC.md)
5. [Strategy registry specification](05_STRATEGY_REGISTRY_SPEC.md)
6. [Settings schema](06_SETTINGS_SCHEMA.md)
7. [Risk and protection pipeline](07_RISK_AND_PROTECTION_PIPELINE.md)
8. [Position-management ownership](08_POSITION_MANAGEMENT_OWNERSHIP.md)
9. [Command lifecycle](09_COMMAND_LIFECYCLE.md)
10. [LocalBridge protocol](10_LOCALBRIDGE_PROTOCOL.md)
11. [Backtest capability matrix](11_BACKTEST_CAPABILITY_MATRIX.md)
12. [Frontend/backend contract](12_FRONTEND_BACKEND_CONTRACT.md)
13. [State persistence model](13_STATE_PERSISTENCE_MODEL.md)
14. [Observability and audit](14_OBSERVABILITY_AND_AUDIT.md)
15. [Deployment and security](15_DEPLOYMENT_AND_SECURITY.md)
16. [Migration roadmap and Claude execution plan](16_MIGRATION_ROADMAP.md)
17. [TREND_GATE + Nucleo 9 — MQL5 implementation spec](17_TREND_GATE_NUCLEO9_SPEC.md)

## Governing rule

No implementation agent should make broad cross-system changes without first reading this pack, declaring the exact files it intends to modify, and demonstrating tests for the behavior being changed.
