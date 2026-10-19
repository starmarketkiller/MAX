# Plan: Structure + Workflow Mix

Spec: `docs/superpowers/specs/2026-10-19-structure-workflow-mix-design.md`

## Files

| File | Track | Change |
|---|---|---|
| `server/tests/test_trade_lifecycle.py` | A | test open → trade_events, non-authoritative |
| `MQL5/Experts/NEXUS_EA_v2.mq5` | A, B | open push; include order LevelRegistry |
| `server/tests/test_ea_open_event_source.py` | A | static: OPEN path exists in EA |
| `MQL5/Include/NEXUS_v1/NXS_LevelRegistry.mqh` | B | source param on Create |
| `MQL5/Include/NEXUS_v1/NXS_ReactionEngine.mqh` | B | OB parity counters + print |
| `MQL5/Include/NEXUS_v1/NXS_Strategies.mqh` | B | OB id + telemetry hooks |
| `MQL5/Include/NEXUS_v1/NXS_Inputs.mqh` | B | `InpLevelRegistry_ObTelemetry` |
| `server/tests/test_causal_experiment_1_dataset.py` | C | schema integrity |
| `server/research_scripts/causal_experiment_1_wick_sweep_1r.py` | C | CLI portabile |
| `docs/TRADING_WORKFLOW_COVERAGE_V1.md` | A | blocco #2 aggiornato |

## Tasks

1. A tests + EA open push
2. B OB Phase A telemetry
3. C dataset test + CLI
4. Docs, commit, push, PR
