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
- `NXS_Execution.mqh` (added 2026-10-06 reconciliation — hosts the single exposure-creation invariant, see below)

## Confirmed current behavior

### Entry path gates observed

The normal execution path includes several checks such as pause, license, daily protections, dynamic spread, news, ruin, profiles, timeframe, dashboard enable/disable, caps, cooldown, sizing, exposure, margin, preflight and SafeOrder.

### RiskShield master gate — RESOLVED (2026-10-06 reconciliation)

**This section previously read "not observed in the reconstructed normal entry call graph" (2026-07-20 audit). That finding was accurate for the code as it existed on 2026-07-20, but is stale for the current repository.**

`docs/RISKSHIELD_ENTRY_PATH_FORENSIC_VERIFICATION_V1.md` (2026-10-06) independently re-verified the entry call graph from scratch and found the gate **wired correctly**, closed by commit `c9a8ebc` ("Decision/Gate/Execution Trace v1", 2026-09-12) — roughly two months after this document's original audit, not as a consequence of it.

**Current state:** `NXS_CommonExposurePreflight()` (`NXS_Execution.mqh:63-213`) is the single exposure-creation invariant — explicitly documented in its own code comments as the fix for a prior finding (`AUD0-ADD-001/002/003`, `AUD0-INST-001/002`) that three separate pipelines (primary entry, grid/pyramid, institutional) carried different gate subsets. It now runs 8 ordered gates for every exposure-creating call, including step (5), `NXS_RS_BlockEntry()` — i.e. RiskShield (Equity Breaker, Spread Burst, Correlation Cluster) is enforced there, not bypassable by construction.

**Verified call paths, all converging on this invariant** (see the forensic doc for exact file:line citations): legacy strategies (`NXS_TryExecuteRC` → `NXS_OpenTrade`), NXR-redirected strategies (same `NXS_TryExecuteRC`, not a separate route), the Institutional Core's group entry (`NXS_OpenTrade` directly), Grid/Recovery, Pyramiding, Institutional add-on management, Profit Reclaim, and SL Reclaim — each calls `NXS_CommonExposurePreflight` directly or via `NXS_OpenTrade`. No order-sending call (`NXS_DoBuy`/`NXS_DoSell`) was found reachable outside this invariant.

**Pending-order entry path:** does not exist in the current codebase. A repo-wide search for `TRADE_ACTION_PENDING`/`ORDER_TYPE_*_LIMIT`/`ORDER_TYPE_*_STOP` returns zero matches — NEXUS only ever sends market orders (`TRADE_ACTION_DEAL`). Not a gap; the path is simply absent by construction.

**Distinct, still-open item (not resolved by this reconciliation):** `FVG_CONT` carries a known defect `SLRECLAIM_ACCOUNT_PROTECTION_BYPASS`, `remediation_state=UNKNOWN_REMEDIATION` (`contracts/edge-validation-registry.json`, via `docs/TRADING_EDGE_STATUS_RECONCILIATION_V1.md`). This is unrelated to the RiskShield wiring question — it concerns whether a specific SLReclaim account-protection interaction was ever fixed, not whether the entry path reaches the master gate. Keep tracking separately.

### Dynamic Spread vs Spread Burst

- Dynamic Spread: absolute/current-spread cap and ATR-relative logic.
- Spread Burst: anomaly detection against historical percentile baseline.

Enforcement of the burst detector is confirmed active as part of the resolved `NXS_RS_BlockEntry()` path above (superseding the earlier "was not observed" note for this detector specifically).

### Correlation cluster scope

The inspected logic counts account positions by broad asset/USD clusters and may include positions not owned by Nexus or not directionally aligned.

### Grid/Pyramid path — RESOLVED (2026-10-06 reconciliation)

**Previously:** "Add-on exposure can follow a different execution route from primary entries." **Current state:** both `NXS_GridRecovery.mqh` and `NXS_Pyramiding.mqh` call `NXS_CommonExposurePreflight()` directly (same invariant as primary entries, see above) — confirmed by `docs/RISKSHIELD_ENTRY_PATH_FORENSIC_VERIFICATION_V1.md`. The "losing recovery legs without an immediate broker-side stop" observation about later management timing was not re-verified by that forensic pass (it addressed gate wiring, not stop-placement timing) and should be treated as a separate, still-open question if it matters operationally.

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

1. ~~Wire and test the master protection gate.~~ **DONE** — closed by commit `c9a8ebc` (2026-09-12), re-verified 2026-10-06 (`docs/RISKSHIELD_ENTRY_PATH_FORENSIC_VERIFICATION_V1.md`).
2. Move protection refresh before add-on exposure. — **not re-verified** by the 2026-10-06 reconciliation (that pass confirmed gate *wiring*, not refresh *ordering*); still open until checked explicitly.
3. ~~Route Grid/Pyramid through common preflight/exposure controls.~~ **DONE** — same commit/verification as item 1; both modules call `NXS_CommonExposurePreflight()` directly.
4. Provide broker-side catastrophic stop or explicit bounded emergency mechanism. — not addressed by this reconciliation.
5. Record every gate outcome in the event ledger. — not addressed by this reconciliation; note `NXS_GateTelemetry()` (`NXS_Execution.mqh:37`) already emits a structured per-gate log line on every call to the invariant, which may already satisfy this item or be close to it — not independently verified against the event ledger schema here.
