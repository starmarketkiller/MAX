---
name: mql5-engineering
description: "NEXUS MQL5 engineering conventions for the NEXUS_v1 EA (MQL5/Include/NEXUS_v1/, MQL5/Experts/NEXUS_EA_v2.mq5). Use when writing, reviewing, or modifying MQL5 code in this repository: new strategy/component logic, indicator handles, CopyBuffer, closed-bar/new-bar state, timeframe-ownership, risk/execution gates, order sending, compile or Strategy Tester workflows, or diagnosing an MQL5 bug. Covers known pitfalls already found and fixed in this codebase (CROSS_TIMEFRAME_STATE_CONTAMINATION classes, strategy identity/attribution via s.stratName not the s.strat enum, the single exposure-creation invariant NXS_CommonExposurePreflight) and the output contract/verifier checklist any MQL5 change in this repo must satisfy. Reusable by Claude, Codex, Ministral, or any other model/worker producing MQL5 for this project."
---

# NEXUS MQL5 Engineering

**Scope:** `MQL5/Include/NEXUS_v1/`, `MQL5/Experts/NEXUS_EA_v2.mq5`, and any new file in the same tree. Not a trading-strategy design guide — a correctness/safety convention guide for code that already decides *what* to trade; this skill is about not corrupting *how* that decision reaches the market.

**Non-negotiable framing:** every rule below that cites a heuristic number (risk %, PF, Sharpe, cooldown bars, ATR multiples) is a **policy/example from this codebase**, not a universal scientific fact. Treat them as configurable defaults to point to with `Inp*` parameters, never as hardcoded truths a new strategy must match to be "correct." Where this skill says "forbidden," it means a structural/safety rule, not a performance opinion.

## When to apply

**Must use:** writing a new `NXS_Strat_*` function or component; modifying signal generation, state persistence, or order-sending code; touching anything in `NXS_Execution.mqh`, `NXS_RiskShield.mqh`, `NXS_Protections.mqh`, `NXS_MarketContext.mqh`, `NXS_InstitutionalCore.mqh`; diagnosing why a strategy behaves differently on different timeframes or after a restart; preparing a compile/Strategy Tester run.

**Skip:** pure Python research scripts (`server/research_scripts/`), backend/web code, documentation-only changes, anything outside `MQL5/`.

## 1. Indicator handle lifecycle

Create each handle **once per (indicator, timeframe) pair**, cache it, never recreate per tick/per call. Canonical pattern (`NXS_SignalQuality.mqh`, `NXS_ADXv`):

```mql5
int g_adxCacheTF[8]; int g_adxCacheH[8]; int g_adxCacheN = 0;
double NXS_ADXv(ENUM_TIMEFRAMES tf, int shift, int period = 14){
   int h = INVALID_HANDLE;
   for(int i = 0; i < g_adxCacheN; i++) if(g_adxCacheTF[i] == (int)tf){ h = g_adxCacheH[i]; break; }
   if(h == INVALID_HANDLE){
      h = iADX(g_sym, tf, period);
      if(h == INVALID_HANDLE) return 0.0;
      if(g_adxCacheN < 8){ g_adxCacheTF[g_adxCacheN] = (int)tf; g_adxCacheH[g_adxCacheN] = h; g_adxCacheN++; }
   }
   double a[]; ArraySetAsSeries(a, true);
   if(CopyBuffer(h, 0, shift, 1, a) <= 0) return 0.0;
   return a[0];
}
```

**Forbidden:** calling `iADX`/`iRSI`/`iMACD`/etc. inside a per-tick loop without caching the handle. **Forbidden:** sharing a single global indicator handle across different timeframes without the per-TF cache above (the global `g_adx`/`g_rsi`/`g_atr` pattern in `NXS_Globals.mqh` is correct *only* because it is deliberately single-TF, computed once in `OnTick` for the active TF — do not repurpose those globals for a different TF without going through a cache like the one above).

## 2. CopyBuffer

Always `ArraySetAsSeries(arr, true)` before `CopyBuffer`, so index `0` is the most recent completed value relative to `shift`. Always check the return value (`< count` means failure — treat as "no data," never as zero/default).

```mql5
double bbUp[]; ArraySetAsSeries(bbUp, true);
if(CopyBuffer(g_hBB, 1, 1, 2, bbUp) < 2) return s;   // bbUp[0]=shift1, bbUp[1]=shift2
```

## 3. Closed-bar / new-bar semantics — the single most expensive lesson in this codebase

**The defect class:** `CROSS_TIMEFRAME_STATE_CONTAMINATION` (Phase 7.10 static audit, confirmed on 11 strategies, 2 fixed as of this writing — `BREAKOUT_ACC` commit `651d3a2`, `ORDER_BLOCK` commit `17da794`). The EA's signal collector calls every strategy function once **per timeframe pass**, not only during the pass matching the strategy's own declared timeframe. Any state read/written without checking which pass is currently active gets corrupted by the other passes. Three distinct sub-classes, all real, all found in this codebase (`cross_timeframe_state_contamination_failure_memory_v1.json`):

- **`COOLDOWN_STATE_CONTAMINATION`** — a cooldown/last-fire timestamp written on every pass suppresses genuine signals on the strategy's real timeframe (false negatives). Case: `BREAKOUT_ACC` pre-fix, 95 real D1 signals → 0 observed.
- **`RECURSIVE_VALUE_STATE_CONTAMINATION`** — a recursively-computed value (smoothed average, trailing stop level, accumulated counter) gets corrupted in *value*, not just timing — can produce false positives too, not only false negatives. More severe than the cooldown class.
- **`STATE_MACHINE_CONTAMINATION`** — a multi-step state machine (e.g. `SWEPT → MSS → RTO`) advances using levels/references computed on the wrong timeframe pass, producing premature or corrupted transitions.

**Required pattern — the fix, verbatim, apply it to any new strategy with persistent state:**

```mql5
if(tf != NXS_Profile_TF("YOUR_STRATEGY_NAME")) return s;   // early guard, BEFORE any state read/write
```

Place this guard **before** touching any global/static state variable, using `NXS_Profile_TF()` (never a hardcoded `PERIOD_*`, so `InpScalpTFOverride` still works if ever enabled). State that is recomputed fresh every call from only the current bar's data (no `static`/global persistence across calls) does not need this guard — only persistent state does.

**Same-bar re-evaluation guard** (a different, smaller problem — a strategy firing multiple times within the same still-open bar): track `lastBarTime`/`lastEvalBar` and return early if the current bar hasn't changed since the last evaluation (see `NXS_Strat_Bollinger`'s `lastEvalBar`, `NXS_Strat_BreakoutAcc`'s `g_breakoutAccState.lastBarTime`).

## 4. Timeframe ownership

- `NXS_EffTF()` — the timeframe of the *current collector pass*, changes as the EA iterates passes within one tick.
- `NXS_Profile_TF(stratName)` — the strategy's own *declared* timeframe, fixed, read from its profile.
- A strategy with persistent state must gate on `NXS_Profile_TF`, not assume `NXS_EffTF()` already equals it (see §3).
- A sub-check that deliberately needs a *different* fixed timeframe than the strategy's own (e.g. SAR's M15 8-bar pressure filter, independent of the strategy's own TF) must say so explicitly in a comment — don't let a hardcoded `PERIOD_M15` look like an accident.

## 5. Timezone / broker time

`TimeCurrent()` is **broker/server time**, not UTC and not the user's local time — never assume otherwise. Session/news-window logic must be explicit about which clock it uses. When comparing to a research dataset built from a different source (Dukascopy, etc.), the timezone offset is a real, previously-found source of divergence — state the assumption, don't leave it implicit.

## 6. Symbol specs

Use `NXS_SymbolProfile.mqh`'s existing auto-config (broker suffix handling, multi-asset profile) rather than hardcoding a symbol string or assuming no broker suffix. `NXS_DeviationForSymbol()`/`NXS_FillingForSymbol()` exist precisely because deviation/filling mode must be derived from the *order's* symbol, not the chart's — a real bug found and fixed once already (`AUD0-RAW-003`/`AUD0-RAW-004`/`NXS-PROT-003`).

## 7. Order / position identity

- `DEAL_POSITION_ID` identifies the position across its lifetime; `DEAL_ORDER` identifies the specific order/deal. Don't conflate them.
- The **close deal's comment is unreliable** — MT5 overwrites it with `"sl ..."`/`"tp ..."`/empty on native stop/target exits regardless of what was set at open. To recover which strategy owned a closed position, map by `DEAL_POSITION_ID` back to the **opening** deal's data (never-rewritten), as done in `NXS_RS_Breaker_Update()` — do not parse the closing deal's comment for attribution.
- `IsNexusMagic()` is the perimeter check for "is this position mine" — always use it before counting/acting on account positions; never assume every open position belongs to this EA (manual trades, other EAs).

## 8. Magic / strategy attribution

- **`s.stratName` (string) is the identity that matters** — it is what `NXS_StratStats.mqh` keys its per-strategy lifecycle tracker on, and what the Institutional Core's family/dedup logic reads.
- **`s.strat` (the `STRAT_*` enum) is NOT a reliable per-strategy identity.** A repo-wide census (2026-10-06) found the enum incomplete: ~34 nominally distinct `stratName` values share `STRAT_STRUCT_REACT` as a generic fallback bucket, because the enum was never extended for every strategy added over time. Do not add new code that reads `.strat` expecting it to distinguish strategies — use `.stratName`. If you add a new strategy, you may reuse an existing enum value or request a new one, but never assume the enum alone tells you "which strategy."
- If a new function/variant literally shares state or logic with an existing strategy (e.g. a `_NXR`/mitigation wrapper), say so explicitly in a comment — this has caused real duplicate-counting risk in cross-strategy analysis (`ORDER_BLOCK`/`OB_MIT`, `FVG_CONT`/`FVG_MIT`/`IFVG`).

## 9. Error handling

- `NXS_PreFlight()` return value and `reason` string are authoritative for why an order attempt failed — propagate them, don't re-derive a reason by string-matching elsewhere (the Decision/Gate/Execution Trace deliberately avoids string-matching `RiskShield`'s formatted reason for exactly this fragility reason).
- `OrderSend` success is `ok && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)` — check both, not just the boolean return.
- A plain (non-`input`) module-level variable that should be tunable from a `.set` file is invisible to the Strategy Tester/`.set` UI — this exact bug silenced the Equity Breaker for a period (`AUD0-RS-008`-adjacent note in `NXS_RiskShield.mqh`). Any parameter meant to be configurable per run must be declared `input`.

## 10. Logging / trace

Use `NXS_GateTelemetry(route, gate_id, passed, observed, threshold, reason)` for any new gate inside the exposure-creation path (see §11) — it is the established structured-log convention (`[NEXUS GATE] {"route":...,"gate_id":...}`), already consumed by the Decision/Gate/Execution Trace. Don't invent a second ad hoc log format for a new gate.

## 11. Risk / execution boundary — the rule with zero exceptions

**`NXS_CommonExposurePreflight()` (`NXS_Execution.mqh`) is the single exposure-creation invariant.** Every code path that can create *new* market exposure — primary signals, NXR-redirected signals, the Institutional Core's group entry, Grid/Recovery, Pyramiding, Institutional add-on management, Profit Reclaim, SL Reclaim — calls it, directly or via `NXS_OpenTrade()`. This was deliberately centralized (`AUD0-ADD-001/002/003`, `AUD0-INST-001/002`) after an audit found three pipelines with inconsistent gate coverage; re-verified wired correctly on 2026-10-06 (`docs/RISKSHIELD_ENTRY_PATH_FORENSIC_VERIFICATION_V1.md`).

**Forbidden, no exception:**
- Calling `NXS_DoBuy`/`NXS_DoSell` (or raw `OrderSend` with `TRADE_ACTION_DEAL` and a new volume) from anywhere that has not first passed `NXS_CommonExposurePreflight()` — directly, or via `NXS_OpenTrade()`.
- Any new "fast path" that opens a position bypassing this invariant "just for this one case" — this is exactly the three-pipelines problem that was already found, fixed, and re-verified. If a new exposure-creating mechanism is added, it must call the existing invariant, not a parallel one.
- Closing/modifying an existing position (`NXS_DoClose`, `NXS_DoClosePartial`, `NXS_DoModify`, `TRADE_ACTION_SLTP`) does **not** need this gate — it reduces or adjusts risk, it doesn't create new exposure. Don't add RiskShield checks to a close path "to be safe" — that's a different invariant (risk-reducing actions should not be blockable by a risk-creation gate).
- Pending orders (`TRADE_ACTION_PENDING`) do not exist anywhere in this codebase today — if you are asked to add one, treat it as a new entry-path class that must also be routed through the same invariant from day one, not added as a quick standalone mechanism.

## 12. Compilation workflow

Canonical path: `LocalBridge/nexus_local_worker.py::handle_compile_ea` — `metaeditor.exe /compile:<src> /log:<path> /portable`, with path-containment checks and a timeout. Compile from the **live terminal's** `Include\NEXUS_v1` folder is what MetaEditor actually uses regardless of which terminal you intend to target — if two MT5 terminals exist (live + tester), keep their `Include` trees in sync (a junction, or re-sync before every compile) or you will compile against stale includes. This has already caused a real incident in this project.

## 13. Strategy Tester workflow

Today this is **manual** (`/config` launch in the terminal) — there is no automated job queue, no restart-recovery, and launching `/config` does not queue multiple runs. Do not assume an automated tester control plane exists; if building one, it must not let a tester run share a data folder with a live terminal (same root cause as the compile-folder incident above).

## 14. Regression tests

Follow the established `verify_phase_7_X.py` / `test_phase_7_X.py` convention for Python-side research changes. For an MQL5 fix to live code: freeze the pre-fix source hash, demonstrate the specific defect mechanism causally (not just "fewer/more trades," show *why*), and report before/after counts on the same tick data — this is the pattern used for both `BREAKOUT_ACC` and `ORDER_BLOCK` fixes and is the bar any new MQL5 live-code fix should meet.

## 15. Common pitfalls catalogue (all real, all found in this codebase)

| Pitfall | Where found | Lesson |
|---|---|---|
| Cross-TF state contamination (3 sub-classes, §3) | 11 strategies, Phase 7.10 | TF-scoped guard before any persistent state access |
| Regime/indicator computed on the wrong TF | `NXS_SignalQuality.mqh` regime veto, pre-fix | A global computed once per tick on the *active* TF is wrong for a check meant to apply to a *different* strategy's TF — recompute fresh on the right TF, don't reuse the tick-global |
| Close-deal comment used for attribution | `NXS_RS_Breaker_Update`, pre-fix | MT5 overwrites close-deal comments; map by position id to the opening deal instead |
| Plain variable instead of `input` | Equity Breaker silencing | Anything meant to be tunable from `.set` must be declared `input` |
| Enum (`s.strat`) assumed to be strategy identity | repo-wide census, 2026-10-06 | Use `s.stratName`, not the enum, for anything attribution-sensitive |
| Three pipelines, three different gate sets | `AUD0-ADD-*`/`AUD0-INST-*` | One invariant (§11), no parallel "fast path" |
| Deviation/filling mode derived from chart symbol, not order symbol | `AUD0-RAW-003/004` | Always derive from the order's actual symbol |

## 16. Forbidden patterns (summary — see `references/forbidden_patterns.md` for the full list with citations)

1. New exposure without `NXS_CommonExposurePreflight()` in the call path.
2. Persistent state read/written without a TF-scoped guard when the function can be called from multiple collector passes.
3. A hardcoded hard-coded performance threshold (PF, Sharpe, risk %) presented as a universal requirement rather than a configurable, labeled example.
4. Silent behavior change to existing live strategy logic bundled into an unrelated change (every live-code change needs its own explicit scope and, per standing project policy, explicit user authorization before touching live MQL5).
5. A second ad hoc logging format for a gate instead of `NXS_GateTelemetry`.
6. Attribution logic keyed on `s.strat` instead of `s.stratName`.

## 17. Output contract

Any response that writes or modifies MQL5 in this repo must state, explicitly:

- Exact file(s) and function(s) touched.
- Whether the change is in, or calls into, the exposure-creation invariant (§11) — and if so, confirmation that no gate was removed or reordered.
- Whether any persistent state is introduced, and if so, the TF-scoping guard applied (§3).
- Compile verification status (did it actually compile, via the canonical path in §12, or is this unverified).
- A regression/test plan (§14), even if "none needed because X."
- Explicit confirmation that this change to **live** MQL5 was requested/authorized by the user in this conversation — research findings do not auto-apply to live strategy code (standing project rule).

## 18. Verifier checklist

See `verifier.py` in this skill folder for a static, grep-based checker implementing the mechanical parts of this checklist (not a substitute for compiling and reading the diff):

- [ ] No new `OrderSend`/`NXS_DoBuy`/`NXS_DoSell` call site outside a function that itself calls `NXS_CommonExposurePreflight` or `NXS_OpenTrade`.
- [ ] No new persistent (`static`/global) state variable read or written without a `NXS_Profile_TF(...)` guard nearby.
- [ ] No new plain (non-`input`) variable that looks like it should be tunable.
- [ ] No new code path reading `.strat` for attribution instead of `.stratName`.
- [ ] No hardcoded `PERIOD_M15`/etc. without a comment explaining why it's deliberately a different TF than the strategy's own.
- [ ] Any new gate uses `NXS_GateTelemetry`.

## References

- `references/forbidden_patterns.md` — full list with exact file:line citations.
- `references/golden_examples.md` — real, already-applied correct patterns from this codebase to imitate.
- `eval/eval_cases.md` — golden test scenarios (real historical bugs) with expected verdicts.
- `docs/RISKSHIELD_ENTRY_PATH_FORENSIC_VERIFICATION_V1.md` — the full exposure-creation call graph.
- `docs/UNIFIED_COMPONENT_CATALOG_V1.md`, `docs/UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md`, `docs/COMPONENT_COLLAPSE_HIGH_VALUE_VERIFICATION_V1.md`, `docs/STRATEGY_IDENTITY_ATTRIBUTION_PREAUDIT_V1.md` — the full attribution/dependency census behind §8.
