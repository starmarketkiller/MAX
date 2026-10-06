# Forbidden Patterns — NEXUS MQL5

Every pattern below cites real file:line evidence from this repository (as of HEAD `f150988`, 2026-10-06). None of these are stylistic preferences — each corresponds to a defect that was actually found, or a safety invariant that was deliberately built after one was found.

## 1. New exposure bypassing `NXS_CommonExposurePreflight()`

**Why forbidden:** `NXS_Execution.mqh:44-56` documents the exact failure mode this prevents — three separate pipelines (primary entry, grid/pyramid, institutional) with different gate subsets, found and fixed under `AUD0-ADD-001/002/003`/`AUD0-INST-001/002`. Re-verified wired correctly 2026-10-06 (`docs/RISKSHIELD_ENTRY_PATH_FORENSIC_VERIFICATION_V1.md`).

**The only two primitives that create new exposure:** `NXS_DoBuy`/`NXS_DoSell` (`NXS_Globals.mqh:348,367`). Every verified caller path reaches them only via `NXS_OpenTrade()` (`NXS_Execution.mqh:306`), which itself calls `NXS_CommonExposurePreflight` at line 548. Direct callers of `NXS_CommonExposurePreflight`: `NXS_Execution.mqh:548` (primary), `NXS_GridRecovery.mqh:86`, `NXS_InstManage.mqh:195`, `NXS_ProfitReclaim.mqh:107`, `NXS_Pyramiding.mqh:166`, `NXS_SLReclaim.mqh:214`.

**If you add a new exposure-creating mechanism**, it must call `NXS_CommonExposurePreflight` (directly, or via `NXS_OpenTrade`) — adding a 7th parallel path that skips it recreates the exact defect this invariant was built to close.

## 2. Persistent state without a timeframe-scoped guard

**Why forbidden:** the EA's collector calls every strategy once per timeframe pass (`NXS_CollectAllSignals`), not only during the pass matching the strategy's declared timeframe. Confirmed defect classes (`server/research_scripts/phase7/phase7_10/cross_timeframe_state_contamination_failure_memory_v1.json`, baseline `651d3a2`):

- `COOLDOWN_STATE_CONTAMINATION` — e.g. `BREAKOUT_ACC` pre-fix: shared `lastFireTime` across TF passes suppressed 95/95 real D1 signals.
- `RECURSIVE_VALUE_STATE_CONTAMINATION` — e.g. `TSI` (double EMA smoothing), `PMAX` (`longStop`/`shortStop`/`dir`), `BB_SQUEEZE` (`squeezeBars`) — the *value* itself corrupts, not just timing.
- `STATE_MACHINE_CONTAMINATION` — e.g. `ORDER_BLOCK` pre-fix (`g_obBuy`/`g_obSell`): 18,485 non-canonical state mutations measured on a real EA trace, 123→8 D1 signals on the same ticks after the fix (`17da794`).

**Fixed pattern (apply verbatim to new strategies with persistent state):**
```mql5
if(tf != NXS_Profile_TF("YOUR_STRATEGY_NAME")) return s;
```
placed before any read/write of a `static`/global variable. See `NXS_Strategies.mqh:1549` (`BREAKOUT_ACC`) and `NXS_Strategies.mqh:2156` (`ORDER_BLOCK`) for the applied fix.

**Still affected, not yet fixed** (do not assume these are safe to pattern-match from): `BAR_UPDN`, `PIVOT_WICK`, `PMAX`, `TSI`, `BB_SQUEEZE`, `SH_BMS_RTO`, `SH_BMS_RTO_V2`, `SILVER_BULLET`, `RANGE_FADE` — `docs/STRATEGY_IDENTITY_ATTRIBUTION_PREAUDIT_V1.md` §Cluster 1.

## 3. Hardcoded "scientific truth" thresholds

**Why forbidden:** a numeric performance threshold (PF > 1.5, Sharpe > 1, risk ≤ 1%) is a policy choice, not a fact about the market. External reference packages (e.g. `nawfdev/mq5_skills`) bake such numbers in as if universal — `docs/NEXUS_EXTERNAL_TRADING_AUDIT_WAVE3.md` explicitly flags this as "What NOT to copy as truth." Any such number in NEXUS code must be an `input` with a comment stating it's a configurable default, and any claim that a strategy "has edge" must come from the edge-validation pipeline (`contracts/edge-validation-registry.json`, `docs/TRADING_EDGE_STATUS_RECONCILIATION_V1.md`), never from a hardcoded gate value alone.

## 4. Silent live-strategy behavior change

**Why forbidden:** standing project rule — Python/research findings don't auto-apply to live MQL5; the engine's mechanics often differ from the backtest, and live-code changes require explicit user authorization in-conversation before being applied, every time.

## 5. Ad hoc logging instead of `NXS_GateTelemetry`

**Why forbidden:** the Decision/Gate/Execution Trace (`NXS_Execution.mqh:37-42`, commit `c9a8ebc`) deliberately classifies *which* gate blocked from the code path itself (`gateOut` enum), specifically because `RiskShield`'s formatted `reason` string wording can change and string-matching on it would be fragile exactly where precision matters most. A second log format for a new gate breaks this.

## 6. Attribution via `s.strat` (enum) instead of `s.stratName`

**Why forbidden:** repo-wide census, 2026-10-06 (`docs/STRATEGY_IDENTITY_ATTRIBUTION_PREAUDIT_V1.md`): 34 distinct `stratName` values share `STRAT_STRUCT_REACT` as a fallback bucket — the enum was never extended per-strategy. `NXS_StratStats.mqh` (the real per-strategy performance tracker) is confirmed name-keyed, not enum-keyed — this is why historical stats are *not* contaminated by the enum sharing, and why any new attribution-sensitive code must follow the same convention.
