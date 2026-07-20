# 7. Risk and Protection Pipeline

## Current protection layers

Inspected modules include:

- `NXS_Risk.mqh`
- `NXS_Protections.mqh`
- `NXS_RiskShield.mqh`
- `NXS_SafeOrder.mqh`
- `NXS_EdgeAdaptive.mqh`
- `NXS_NewsFilter.mqh`
- `NXS_Slippage.mqh`
- `NXS_GridRecovery.mqh`
- `NXS_Pyramiding.mqh`
- `NXS_InstManage.mqh`

## Confirmed current behavior

### Entry path gates observed

The normal execution path includes several checks such as pause, license, daily protections, dynamic spread, news, ruin, profiles, timeframe, dashboard enable/disable, caps, cooldown, sizing, exposure, margin, preflight and SafeOrder.

### RiskShield master gate not observed in main path

`NXS_RS_BlockEntry()` was not observed in the reconstructed normal entry call graph.

**Consequence:** Equity Breaker, Spread Burst enforcement and Correlation Cluster may exist in code without consistently blocking entries.

### Dynamic Spread vs Spread Burst

- Dynamic Spread: absolute/current-spread cap and ATR-relative logic.
- Spread Burst: anomaly detection against historical percentile baseline.

Sampling is active; enforcement of the burst detector was not observed in the main gate path.

### Correlation cluster scope

The inspected logic counts account positions by broad asset/USD clusters and may include positions not owned by Nexus or not directionally aligned.

### Grid/Pyramid path

Add-on exposure can follow a different execution route from primary entries. Losing recovery legs can remain without an immediate broker-side stop while waiting for later management.

## Target pipeline

```text
1. Hard operational gates
   license, pause, instance health
2. Emergency account gates
   equity breaker, margin, daily loss, ruin
3. Market-access gates
   news, spread, spread burst, liquidity/session
4. Portfolio gates
   exposure, correlation, symbol/direction concentration
5. Strategy gates
   enabled, cooldown, quality, chain eligibility
6. Sizing
7. Broker preflight
8. Order request
9. Broker confirmation
```

Every gate must produce a structured result:

```json
{
  "gate_id": "SPREAD_BURST",
  "passed": false,
  "observed": 42.0,
  "threshold": 31.5,
  "reason": "P95 x 1.3 exceeded"
}
```

## Fail-open/fail-closed policy

Safety-critical checks should be explicitly classified:

- license unavailable: policy decision;
- current spread unavailable/zero: fail closed for new entries;
- telemetry backend unavailable: EA continues locally;
- risk state corrupted: no new exposure until reconstructed;
- news service unavailable: configurable and visible, never implicit.

## Repair priority

1. Wire and test the master protection gate.
2. Move protection refresh before add-on exposure.
3. Route Grid/Pyramid through common preflight/exposure controls.
4. Provide broker-side catastrophic stop or explicit bounded emergency mechanism.
5. Record every gate outcome in the event ledger.
