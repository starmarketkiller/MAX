# NEXUS Semantic Strategy Audit — All 53 Live Strategies

Read directly from MQL5 source (`NXS_Strategies.mqh`, `NXS_Strategies_Institutional.mqh`,
`NXS_Strategies_SMC.mqh`, `NXS_Strategies_Elliott.mqh`, `NXS_Strategies_Experimental.mqh`,
`NXS_StrategyProfiles.mqh`, `NXS_Inputs.mqh`, `NXS_Globals.mqh`, `NXS_Defines.mqh`,
`NEXUS_EA_v2.mq5`). No code was modified. Scope = the 53 `strategy_id`s in
`contracts/strategy-registry.json` with `live_implementation: true`.

## Universal facts (apply to every strategy unless noted)

- **ORDER/FILL PRICE is always live ASK (buy) / BID (sell)** at `OrderSend` time
  (`NXS_DoBuy`/`NXS_DoSell`, `NXS_Globals.mqh:348-384`). No strategy controls the real fill
  price. `entryRef` is bookkeeping only, used to compute SL/TP distance upstream.
- **`NXS_DefaultSLTP()`** (`NXS_Strategies.mqh:126-158`) is the generic SL/TP engine used by
  most strategies with no frozen external spec: `entryRef = live ASK/BID`, SL/TP = `g_atr *
  mult`, where `mult` comes from a per-strategy profile (`NXS_Profile_SLTP`/`NXS_Profile_Get`,
  see `NXS_StrategyProfiles.mqh`) if `InpUseStrategyProfiles=true` (default true) and the
  strategy has a profile row, else global `InpATR_SL_Mult`/`InpATR_TP_Mult`. Strategies that
  compute their own structural stop (order-block edge, sweep level, range extreme, wick, Fib
  leg, weekly range) bypass `NXS_DefaultSLTP` entirely and set `slPrice`/`tpPrice` inline —
  flagged per strategy below as "custom SL/TP".
- **Observation point**: every "classic"/SMC/Institutional strategy in `NXS_Strategies*.mqh`
  evaluates on **closed-bar data** (reads shift ≥1), gated by a `lastBarTime`/`lastEvalBar`
  static so the decision is made once per closed bar of its execution TF — even though
  `OnTick()` calls the router every tick. The two exceptions are **WICK_SWEEP_REV** (true
  tick-level evaluation of live bid/ask against a wick level) and **WICK_SWEEP_RECLAIM**
  (tick-level state machine, though its H4 level source is bar-gated).
- **Timeframe**: `NXS_Profile_TF(name)` (`NXS_StrategyProfiles.mqh:222-326`) is the single
  source of truth for a strategy's execution TF when `InpUseStrategyProfiles=true`; falls back
  to `InpTFEntry` (or a small hardcoded map for session/Elliott strategies) otherwise. This
  matches the registry's `supported_timeframes` for all strategies checked.
- **Risk/lot sizing**: `NXS_Profile_Risk(name)` (`NXS_StrategyProfiles.mqh:348+`) returns a
  per-strategy risk % tier (0.3%–5.0%), derived from a mix of real-MT5 PF history and
  Python OOS/walk-forward evidence (see per-strategy notes for tier rationale); falls back to
  global `InpRiskPercent`. Feeds `NXS_CalcLotRisk`/`NXS_CalcLot` (`NXS_Risk.mqh`).
- **Selector isolation**: `NXS_SelectorAllows(idx)` (`NXS_Globals.mqh:11-13`) — a debug-only
  single-strategy isolation switch (`InpStrategySelector`, default 0 = no restriction). Not a
  behavioral gate under normal operation.

### ⚠ Critical finding: registry `default_enabled` does not match compiled behavior

For six strategies the registry says `status: ACTIVE, default_enabled: true`, but the actual
`input bool InpStrat_*`/`InpUseStrat_*` flag in `NXS_Inputs.mqh` defaults to **false**, and in
three of the six the strategy is additionally **dead by construction** (cannot fire even if the
flag is flipped true) because of a macro redirect. See the per-strategy entries and the
"Registry vs. reality" table in the summary.

---

## MOMENTUM family

### ADX_RSI (selector 1)
- `NXS_Strat_ADXRSI`, `NXS_Strategies.mqh:261`. Family matches registry.
- market_idea: EMA50-slope trend filter + RSI mid-band re-entry (not a real ADX-based system
  originally, but `g_adx<20` gate was added 2025-07 as a trend-strength floor after A/B testing).
- market_context: `g_adx >= 20` (trend strength floor). event: EMA50(shift1) vs EMA50(shift2)
  slope defines trend direction. setup: RSI(14) in 45–65 (bull) / 35–55 (bear) band + close
  beyond/below EMA50. trigger: all conditions true on the same evaluated (closed) bar — no
  separate confirmation step, fires on the evaluation tick of the bar close.
- observation_point: per-tick evaluation of already-closed bar 1 values (no bar-gate static,
  so re-evaluated every tick until the underlying values change bar).
- SIGNAL_PRICE: `iClose(shift1)` vs EMA50. REFERENCE_PRICE: `NXS_DefaultSLTP` → live ASK/BID.
  ORDER/FILL_PRICE: live ASK/BID.
- invalidation: none explicit (no state machine); simply stops firing once RSI/EMA condition breaks.
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.0/tpMult=10.0, `htf=true`, `beR=1.5` (breakeven at
  1.5R) — profile derived from MFE/MAE study showing 85.6% of signals reach ≥1R.
- exit: breakeven move at 1.5R (via profile beR, generic mechanism, not per-strategy code).
  timeout: `NXS_MaxHold_LimitSec` via profile TF (D1) × `InpProfileMaxHoldBars`.
  filters: HTF gate (profile htf=true) — EMA200 alignment on `NXS_EffTF()` required in addition.
- indicator deps: EMA50 (custom cache `NXS_EMAv`), `g_rsi` (RSI14 global), `g_adx` (ADX14 global).
- state deps: `g_adx`, `g_rsi` globals (updated every tick from `iADX`/`iRSI`). execution deps:
  `NXS_DefaultSLTP`, strategy profile. risk: Tier A 2.5% ("real PF1.14 positive but thin D1 sample").
- default-enabled: `InpStrat_ADX_RSI = true` (matches registry).

### MACD (selector 3)
- `NXS_Strat_MACD`, `NXS_Strategies.mqh:358`. Family matches registry.
- market_idea: classic EMA-based MACD/signal cross filtered by EMA200 trend (native `iMACD`,
  not the SMA-based clone — see MACD_SMA200 below, a genuinely separate implementation).
- event/trigger: `g_macd>g_macdSig && g_macd>0 && close>EMA200` (bull, mirror for bear) — all
  read from cached globals, no separate confirmation.
- SIGNAL_PRICE: close(shift1) vs EMA200. REFERENCE/ORDER: `NXS_DefaultSLTP` → live ASK/BID.
- SL/TP: profile slMult=2.0/tpMult=8.0, `htf=true`, `beR=1.0` — from MFE/MAE study (70.5% reach
  ≥1R, MFE avg 2.40R vs old TP3.0). Code comment flags this strategy as "CRITICA on real MT5"
  (PF~1.10) despite strong Python backtest — a known live-execution mismatch, not a trigger bug.
- risk tier: 0.5% (Tier C, "red-flag real-MT5 execution known"). filters: HTF gate (EMA200 on EffTF).
- indicator deps: `g_macd`, `g_macdSig`, `g_ema200` globals (native MACD indicator + EMA200).
- default-enabled: `InpStrat_MACD = true` (matches registry).

### SAR (selector 4)
- `NXS_Strat_SAR`, `NXS_Strategies.mqh:406`. Family matches registry.
- market_idea: Parabolic SAR flip direction confirmed by EMA9/EMA21 cross, with two OPTIONAL
  filters found via post-hoc trade analysis: candle-alignment (bar 1 color must agree with
  signal direction) and pressure-CONTRARY (last 8 M15 bars' net direction must be the OPPOSITE
  of the signal — the code explicitly notes this is counter-intuitive but validated: catches a
  real reversal rather than chasing an extended move). Both filters default **off**
  (`InpSAR_RequireCandleAlign=false`, `InpSAR_RequirePressureContrary=false`) — live-tested
  25-08/31-08 and found to change timing cascades rather than help net when actually enabled on
  the Tester (see MACD-style live/offline divergence note).
- event/trigger: `g_sar` crosses to the opposite side of price + EMA9/EMA21 agree with the same
  direction.
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.0(or override)/tpMult=6.0, `htf=false`.
- risk: 1.0% (down from 5.0% after a Sep-2025 Monte-Carlo ruin study found SAR alone drove 39%
  of portfolio trade volume at max tier, producing 78% ruin probability via volatility drag —
  code comment is explicit that this is a position-sizing fix, not a trigger fix).
- indicator/state deps: `g_sar`, `g_ema9`, `g_ema21` globals; M15 OHLC for the pressure filter.
- default-enabled: `InpStrat_SAR = true` (matches registry).

### TSI (selector 5)
- `NXS_Strat_TSI`, `NXS_Strategies.mqh:1366`. Family matches registry.
- market_idea: genuine Blau True Strength Index (double-EMA of price change / double-EMA of
  abs price change) vs its own EMA signal line — code comment notes a *prior* version was
  mislabeled (was actually RSI+EMA20 despite the "TSI" name; fixed 17/07).
- event/trigger: TSI crosses its signal line, computed incrementally once per closed bar
  (iterative double-EMA state, `barsSeen` warmup = `LongPeriod*3` bars before trusting the value).
- SL/TP: profile slMult=2.0/tpMult=6.0, `htf=true`, `beR=1.0` — code explicitly calls this "an
  open problem never solved," a fragile 22-24 trade OOS sample, "not an established fact like
  CRT/FVG_CONT."
- risk: 0.3% (Tier D — lowest tier, "confirmed open problem, no solution found after multiple
  attempts, only OOS-negative strategy in the core").
- indicator deps: `g_tsiState` persistent struct (double-EMA of price-change), no native indicator handle.
- default-enabled: `InpStrat_TSI = true` (matches registry).

---

## VOLATILITY family

### BOLLINGER (selector 2)
- `NXS_Strat_Bollinger`, `NXS_Strategies.mqh:286`. Family matches registry.
- market_idea: **mean reversion** — price touches/exceeds a Bollinger band and closes back
  inside; optional RSI non-confirmation filter (divergence-style: band touch must NOT be
  confirmed by an RSI extreme) and optional candle-reversal filter (hammer/engulf/shooting-star).
- event: `close(shift2) <= lowerBand(shift1)` then `lowerBand(shift0) < close(shift0)` (mirror
  upper). Note explicit historical fix: band and close shifts were misaligned before 17/07.
- trigger: bar-gated (`lastEvalBar`) — evaluated once at bar close, not re-evaluated per tick.
- filters (all optional, tunable): `InpBollingerUseRSIFilter` (default false),
  `InpBollingerUseCandleFilter` (default false), `InpBollingerBuyOnly` (default false — but
  H4-nude test found BUY PF1.33 vs SELL PF0.61, i.e. a documented but *not enforced* directional
  edge).
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.0/tpMult=2.0, `htf=false`.
- indicator deps: `g_hBB` (Bollinger Bands handle), `g_hRSI`. default-enabled:
  `InpStrat_BOLLINGER = true` (matches registry).
- **Relationship**: shares the same 2-SD statistical band construct as Z_SCORE_BREAKOUT but
  the OPPOSITE market thesis (mean-reversion vs breakout-continuation) — code comment makes
  this explicit. GENUINELY_DISTINCT despite the shared indicator.

### BB_SQUEEZE (selector 12)
- `NXS_Strat_BBSqueeze`, `NXS_Strategies.mqh:1859`. Family matches registry.
- market_idea: volatility-contraction breakout. Bandwidth percentile (vs its own 150-bar
  history) must be ≤20th percentile for ≥5 consecutive bars (a real historical-relative squeeze,
  not an absolute threshold — code notes the old absolute-ATR threshold was too weak), then
  price closes outside the bands while bandwidth is re-expanding.
- trigger: one-shot per squeeze episode (`consumed` flag) — no repeat signals within the same squeeze.
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.0/tpMult=4.5, `htf=false`.
- indicator deps: `g_hBB`. default-enabled: `InpStrat_BB_SQUEEZE = true` (matches registry).

### RANGE_FADE (selector 37)
- `NXS_Strat_RangeFade`, `NXS_Strategies_Institutional.mqh:645`. Family matches registry.
- market_idea: mean reversion inside a CONFIRMED range — a 5-part persistence test (ADX
  persistence ≥70% of a 40-bar window, stable width between window-halves, ≥2 touches per side
  ≥3 bars apart, 30-70% balanced close occupation, no accepted breakout in last 5 bars) must all
  hold before fading the edges.
- **default-enabled: `InpUseStrat_RangeFade = false`** (registry says default_enabled=true).
  Disabled 25/08: the confirmation gate is so strict it fires only 6 times in ~10y of D1
  XAUUSD, all losses (PF0.00) — "not a solid profitability verdict given the tiny sample, but a
  signal that in practice never contributes to the live system."
- SL/TP: custom (edge ± 0.4×ATR to range mid, capped at 2.0R). risk/exec: no `NXS_DefaultSLTP`.

---

## TREND family

### BREAKOUT_ACC (selector 9)
- `NXS_Strat_BreakoutAcc`, `NXS_Strategies.mqh:1534`. Family matches registry.
- market_idea: "acceptance" breakout — two consecutive closes beyond a 20-bar range extreme
  (not a single-bar breakout). Per-direction cooldown (`InpBreakoutAccCooldownBars=8`) added
  2025-09-02 after finding 106/201 raw M15 trades were chase-entries into the same continuing
  move (only the first of a cluster profited).
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.0/tpMult=4.5, `htf=true`. risk: 0.5% (Tier C — "Python
  DEBOLE, OOS2.71 contradicted by real walk-forward 1/5, D1 noise").
- default-enabled: `InpStrat_BREAKOUT_ACC = true` (matches registry).
- **Relationship**: shares enum `STRAT_BREAKOUT_ACC` with Z_SCORE_BREAKOUT and
  VOLATILITY_BREAKOUT_CONFIRMED but all three are logically distinct (range-acceptance vs
  z-score-regime vs frozen-spec range-break) — consistent with the pre-verified
  Z_SCORE_BREAKOUT/selector-42 calibration case that a shared internal enum ≠ duplicate.

### LONDON_BO (selector 10)
- `NXS_Strat_LondonBO`, `NXS_Strategies.mqh:1720`. Family matches registry.
- market_idea: London-session breakout of the Asian range, validated (body ≥0.5×ATR, buffer
  beyond the level, close-location-value ≥0.6 — a real "conviction" filter added 17/07; before
  that any marginal close beyond Asia counted).
- market_context: `g_session == SESS_LONDON` only.
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.0/tpMult=4.5, `htf=true`. risk: 2.5% (Tier A, "Python
  OOS1.38/99 WF4/5, no real history yet").
- default-enabled: `InpStrat_LONDON_BO = true` (matches registry).

### EMA_PULLBACK (selector 11)
- `NXS_Strat_EMAPullback`, `NXS_Strategies.mqh:1791`. Family matches registry.
- market_idea: continuation pullback — EMA20/EMA50 trend must persist for
  `InpEMAPB_TrendPersistBars=5` bars, a prior impulse must have moved ≥1.0×ATR from EMA20, then
  a rejection candle at EMA20 (touch + reclaim + no break of EMA50). Optional pressure-ALIGNED
  filter (opposite convention from SAR's pressure-CONTRARY — this is a continuation strategy,
  SAR is a reversal-catch strategy) exists but is proven NOT to help on the real Tester
  (offline PF1.51→1.74 but live PF1.42→1.35) and is left off by default with the note
  "confirmed the gate works correctly in code — it's a cascading-timing effect offline analysis
  can't see, not a bug."
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.5/tpMult=4.0, `htf=true`.
- risk: 2.5% (cut from 5.0% in the same SAR ruin study — EMA_PULLBACK was the other high-volume/thin-edge strategy).
- default-enabled: `InpStrat_EMA_PULLBACK = true` (matches registry).

### ICHIMOKU (selector 13)
- `NXS_Strat_Ichimoku`, `NXS_Strategies.mqh:1918`. Family matches registry.
- market_idea: Kumo (cloud) breakout with Tenkan/Kijun confirmation — price crosses from inside/below
  the cloud to above it (mirror below), confirmed by Tenkan>Kijun.
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.0/tpMult=4.5, `htf=true`. risk: 1.8% (off-tier legacy value, "PF1.91 real, small sample").
- default-enabled: `InpStrat_ICHIMOKU = true` (matches registry).

### Z_SCORE_BREAKOUT (selector 42)
- `NXS_Strat_ZScoreBreakout`, `NXS_Strategies.mqh:1675`. Registry family TREND — code is a
  "quant" breakout thesis (statistical continuation), arguably closer to VOLATILITY family by
  mechanism but registry classification is defensible given its trend-continuation intent.
- market_idea: SMA200 regime filter (bull if close>SMA200) + 20-bar z-score >2.0 (bull) — a
  BREAKOUT interpretation of 2-SD bands, explicitly the "opposite hypothesis" of BOLLINGER's
  mean-reversion on the same statistical construct.
- SL/TP: custom — SL from a structural M5 12-bar extreme (floor 0.3×ATR(H1)), NOT
  `NXS_DefaultSLTP` (slMult/tpMult profile row is "inert," only tpMult=4.0×ATR is real; SL
  distance is native). ENTRY: live ASK/BID (no frozen entryRef spec here, unlike its neighbor
  VOLATILITY_BREAKOUT_CONFIRMED).
- gap noted in code: the Efficiency-Ratio regime filter used in Python validation is NOT a live
  gate here (shared gap with SWING_FALSEBREAK).
- default-enabled: `InpStrat_ZScoreBreakout = true` (matches registry).

### VOLATILITY_BREAKOUT_CONFIRMED (selector 56, EXPERIMENTAL)
- `NXS_Strat_VolatilityBreakoutConfirmed`, `NXS_Strategies.mqh:1579`. Family matches registry.
- market_idea: exact port of a frozen Python spec (`FROZEN_SIGNAL_SPEC_V1`,
  `sig_volatility_breakout_confirmed`), bit-verified against 927/927 Phase-2 events. 20-bar
  range breakout on `close(shift1)`, confirmed by `trueRange(shift1) > 1.0×ATR(14)`. TP is
  exactly 1R (symmetric — the level whose first touch defined "won" in the offline screen).
- **SIGNAL_PRICE = REFERENCE_PRICE = `close(shift1)`** — the code contains an explicit
  17/09-dated correction: an earlier version used live ASK/BID as `entryRef` (the generic
  `NXS_DefaultSLTP` convention inherited by mistake), which contradicted the frozen spec's
  "entry = signal-bar close." This is the exact precedent the task brief cites. ORDER/FILL_PRICE
  is still live ASK/BID (unavoidable, same as every other strategy) — the gap between
  `close(shift1)` and the real fill is ordinary execution slippage, not a spec violation.
- filters: explicitly NONE — no HTF, no session, no trailing/BE ("do not add filters: the
  signal is frozen as submitted to causal screening").
- default-enabled: `InpStrat_VolBreakoutConfirmed = false` ("never verified on MT5," matches
  registry's EXPERIMENTAL/`default_enabled:false`).

### SWING_FALSEBREAK (selector 41)
- `NXS_Strat_SwingFalseBreak`, `NXS_Strategies_SMC.mqh:119`. Registry family LIQUIDITY — code
  is a sweep-and-reclaim of a MAJOR fractal swing pivot (left=20/right=15 bars), same
  sweep+close-back mechanic as TURTLE_SOUP but anchored to structural swing pivots instead of
  session/PDH-PDL levels — family assignment (LIQUIDITY) is defensible.
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.5/tpMult=4.0, `htf=false` (ATR-multiple stop, NOT
  structural like TURTLE_SOUP — an explicit code note flags this difference).
- gap noted: Efficiency-Ratio regime filter used in Python validation not ported as a live gate
  (shared with Z_SCORE_BREAKOUT and the wider SAR/MACD/LONDON_BO/FVG_CONT portfolio).
- default-enabled: `InpStrat_SwingFalseBreak = true` (matches registry).

---

## LIQUIDITY family

### BJORGUM (selector 6)
- `NXS_Strat_Bjorgum`, `NXS_Strategies.mqh:1417`. Registry family LIQUIDITY (30-bar pivot
  high/low bounce/reject within 0.5×ATR) — a simple support/resistance bounce, same family as
  MALAYSIAN_SNR/PIVOT_WICK/STRUCT_REACT cluster but with its own (simplest) level construction.
- **default-enabled: `InpStrat_BJORGUM = false`** (registry says default_enabled=true, status
  ACTIVE). Disabled 25/08 after the true (non-EMA-ribbon-proxy) backtest on 6 years of real MT5
  data showed **-8.6R, 5 of 6 years negative**. Risk tier if ever re-enabled: 0.4% (explicitly
  the lowest legacy tier, "no unjustified high tier if reactivated").
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.5/tpMult=3.0, `htf=false`.

### LIQ_SWEEP (selector 7)
- `NXS_Strat_LiqSweep`, `NXS_Strategies.mqh:1454`. Family matches registry.
- market_idea: reversal off a confirmed multi-level liquidity sweep (`SNXSSweepExt`, covers
  PDH/PDL/Asia-High-Low/equal-highs-lows/daily/weekly/monthly), requiring a strong "delivery
  candle" body (≥0.7×ATR) in the reversal direction. `sw.levelTag` records exactly which level
  triggered it for diagnostics — deliberately a single detection engine reused by many other
  strategies (TURTLE_SOUP, SH_BMS_RTO, JUDAS_SWING, LDN/NY_REVERSAL, PO3, AMD_REVERSAL,
  SILVER_BULLET, SWING_FALSEBREAK), each with its own confirmation/state-machine layered on top
  — a deliberate "one sweep-detector, many distinct strategies" design, directly analogous to
  the pre-verified Z_SCORE_BREAKOUT/BREAKOUT_ACC shared-enum calibration case.
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.5/tpMult=3.0, `htf=true`. risk: 0.5% (Tier C, "Python
  DEBOLE, IS 0.91 below breakeven").
- default-enabled: `InpStrat_LIQ_SWEEP = true` (matches registry).

### TURTLE_SOUP (selector 17)
- `NXS_Strat_TurtleSoup`, `NXS_Strategies_SMC.mqh:24`. Family matches registry.
- market_idea: sweep of prior-day high/low or equal-high/low + close back inside + a
  strong-body (≥0.4×ATR) reversal candle — the classic "turtle soup" fakeout reversal.
- **No self-guard inside the function** — unlike the "classic 16," this strategy's
  `InpStrat_TurtleSoup`/`NXS_SelectorAllows(17)` gate lives at the CALL SITE
  (`NEXUS_EA_v2.mq5:538`), not inside `NXS_Strat_TurtleSoup()` itself. Functionally identical
  outcome, just a different code-organization pattern (shared by all SMC/Institutional
  strategies below selector 17).
- **default-enabled: `InpStrat_TurtleSoup = false`** (registry says default_enabled=true,
  status ACTIVE). Disabled 25/08 after a from-scratch (not the old Python-proxy) backtest of the
  TRUE live signal on H1/4h/30m, symmetric and BUY/SELL-only variants, found **never robustly
  profitable** (max PF0.94). Risk tier if ever re-enabled: 5.0% ("PF2.04 'the star' is WITH the
  official recipe active" — i.e. only profitable in a config not what actually runs).
- SL/TP: custom, structural (`refHigh`/`refLow` ± 0.5×ATR, 2.0R target) — profile row exists
  (slMult=1.0/tpMult=4.5/htf=true) but is superseded by the inline structural calc.

### STRUCT_REACT (selector 16)
- `NXS_Strat_StructureReaction`, `NXS_Strategies.mqh:2153`. Family matches registry.
- market_idea: reacts to whatever the shared structure/reaction engine (`g_reaction`,
  `g_struct`) has already detected as a live SMC reaction zone (OB/FVG) — this strategy is a
  thin scoring wrapper (`score = 55 + quality*0.35`, + trend-alignment/BOS-CHOCH bonuses) around
  externally-computed structure state, not its own event detector.
- SL/TP: `NXS_DefaultSLTP`, profile slMult=2.0/tpMult=6.0, `htf=true`, BUY-only per code comment
  ("4h BUY-only, see 25/08 note" — SELL side found broken in re-verification). Note: no
  explicit BUY-only code gate was found in `NXS_Strat_StructureReaction` itself; the BUY-only
  constraint is applied via `NXS_Profile_DirectionLock`, external to this function (not
  independently re-verified in this audit — flagged for follow-up).
- default-enabled: `InpUseStructReact = true` (matches registry).
- **Relationship**: explicitly named by the code itself (see PIVOT_WICK/LEVEL_CONFLUENCE/
  LEVEL_REACTION comments) as one of 3-4 independent implementations of "react to a key level" —
  see Classification section.

### SH_BMS_RTO (selector 21)
- `NXS_Strat_SH_BMS_RTO`, `NXS_Strategies_SMC.mqh:511`. Family matches registry.
- market_idea: canonical 3-stage ICT state machine — Stop-Hunt (confirmed sweep) → Break of
  Market Structure (displacement body ≥0.8×ATR breaking the pre-sweep swing, within
  `InpSHBMS_MaxMSSBars=20`) → Return-To-Origin (first touch of the last opposite-color candle
  before the displacement, within `InpSHBMS_MaxWaitBars=15`). Rewritten 17/07 from a
  same-tick-collapsed version specifically because sweep→MSS→retest is a genuinely causal,
  temporal sequence (`sweepTime < mssTime < retestTime` enforced by construction).
- SL/TP: `NXS_DefaultSLTP`-independent — custom structural (origin zone ± 0.5×ATR, 2.6R target).
  Note: profile row exists (slMult=1.0/tpMult=4.5) as a fallback only.
- SIGNAL_PRICE: the sweep bar's extreme + the MSS displacement close. REFERENCE_PRICE: origin
  zone edges. ORDER/FILL: live ASK/BID.
- default-enabled: `InpStrat_SH_BMS_RTO = true` (matches registry). Registry's
  `proxy_for: "OB_MIT"` field is misleading — this strategy is fully independent of OB_MIT in
  the live code path (no shared function); likely a research/proxy-mapping artifact for offline
  parity testing, not a live code relationship.

### SMS_BMS_RTO (selector 22, no selector_index in registry)
- `NXS_Strat_SMS_BMS_RTO`, `NXS_Strategies_SMC.mqh:623`. Family matches registry.
- market_idea: failure-swing labelling (HH/LH/LL/HL via two rolling `iHighest`/`iLowest`
  windows) → requires CHOCH in the recovery direction → return to within 60% of the swing body
  (proxy for "return to OB/FVG," not an actual zone read) → rejection candle. Same overarching
  "sweep→structure-break→return" idea as SH_BMS_RTO but a DIFFERENT detection method
  (failure-swing HH/LL labelling vs `SNXSSweepExt` sweep detection + explicit state machine) and
  no multi-bar state machine — evaluated fresh every call, not staged.
- SL/TP: custom structural (swing extreme ± 0.5×ATR, 2.6R). Profile row: slMult=1.0/tpMult=4.5 (fallback).
- default-enabled: `InpStrat_SMS_BMS_RTO = true` (matches registry).
- **Relationship to SH_BMS_RTO**: SEMANTIC_DUPLICATE of the same overarching concept
  ("liquidity failure → structure break → return"), implemented via genuinely different
  detection primitives — closer to MINOR_VARIANT than TRUE_DUPLICATE since the trigger geometry
  differs materially (failure-swing HH/LL vs sweep-of-external-level).

### SH_BMS_RTO_V2 — NOT LIVE (research_implementation only, excluded from the 53; noted for context: an independent, simpler state machine with no body-ATR MSS threshold, shared timeout, ADX+structure-trend gate. Kept for cross-reference since it explains why `NXS_Strat_SH_BMS_RTO_V2` exists in the same file as the live SH_BMS_RTO.)

### MALAYSIAN_SNR (no selector_index in registry; live per `InpStrat_MalaysianSNR`, code selector 26)
- `NXS_Strat_MalaysianSNR_Rejection`, `NXS_Strategies_SMC.mqh:875`. Family matches registry.
- market_idea: body-based (CLOSE, not wick) H4 support/resistance from the last 12 closed bars,
  with a "storyline" directional filter (H4 4-bar trend + D1 2-bar trend must agree), a
  "fresh" bonus (level untouched in the last 20 H4 bars) and a W1-confluence bonus. Explicitly
  distinguished by the code from PIVOT_WICK (wick-based fractal pivots) and LEVEL_REACTION
  (which deliberately merges this SNR source with the pivot source).
- market_context: skips Asian session explicitly (low-vol false-signal risk on H4 body levels).
- SL/TP: `NXS_DefaultSLTP`-independent — custom (level ± 0.5×ATR(H4), 2.3R). Profile row:
  slMult=2.0/tpMult=4.5/htf=true (fallback only — TF fixed to M30 via `NXS_Profile_TF`, moved
  from D1 25/08 after D1 checked the level too infrequently: PF0.76→PF1.75 on M30, n=1289).
- default-enabled: `InpStrat_MalaysianSNR = true` (matches registry).

### SH_BMS_RTO / SMS_BMS_RTO / MALAYSIAN_SNR / TURTLE_SOUP / SWING_FALSEBREAK / BJORGUM /
PIVOT_WICK / STRUCT_REACT / LEVEL_CONFLUENCE(+M5) / LEVEL_REACTION(+M5) all sit in a broad
"react to a level" super-family — see Classification section for the precise duplicate/variant
graph; they are not all collapsed into one bucket because their level sources and confirmation
logic differ meaningfully in several cases.

---

## SMC / ICT family

### FVG_CONT (selector 8)
- `NXS_Strat_FVG`, `NXS_Strategies.mqh:1487`. Family matches registry.
- market_idea: 3-candle Fair Value Gap CONTINUATION — `low(shift1) > high(shift3)` (bullish
  gap) filtered by EXTERNAL H1 structure trend (`g_structH1.trend`), not just a local EMA50
  proxy (explicit 16/07 upgrade). Optional SMC reaction-gate filter
  (`InpUseSMCReactionGate`) to avoid gaps price passes through without reacting.
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.5/tpMult=6.0, `htf=true`, `beR=InpFvgContBeR`
  (default 1.5, tunable). risk: 0.5% (Tier C — "CRITICA on real MT5, PF0.79, despite strong
  Python backtest" — same live/offline mismatch pattern as MACD).
- default-enabled: `InpStrat_FVG_CONT = true` (matches registry).

### FVG_MIT (selector 19)
- Textually `NXS_Strat_FVG_Mitigation`, `NXS_Strategies_SMC.mqh:198` — retest of a MATURE
  (bars 5-7 old) FVG with a strong (≥0.35×ATR) rejection candle in the mitigation direction —
  a distinct idea from FVG_CONT (mitigation/reversion-into-gap vs gap-continuation) and from
  IFVG (gap invalidation reversal, below).
- **DEAD BY CONSTRUCTION**: `#define NXS_Strat_FVG_Mitigation NXR_Strat_FVG_Mitigation`
  (`NXS_ReusePerformancePack.mqh:2365`) — the compiled function is actually
  `NXR_Strat_FVG_Mitigation`, a zone-registry lookup gated by `InpNXR_Enable`, which is
  **hardcoded `false`** (`NXS_ReusePerformancePack.mqh:55` — not exposed as an `input`, cannot
  be flipped without recompiling). No fallback to the legacy logic exists by design ("converge
  on NXR as sole source of truth"). So this strategy structurally cannot fire regardless of its
  toggle.
- **default-enabled: `InpStrat_FVG_Mit = false`** (registry says default_enabled=true, status
  ACTIVE) — consistent with it being dead either way.
- Its sibling `FVG_MIT_WINDOW` (a registry-tracked zone with `InpFVGMITWindow` bookkeeping,
  `NXS_Strat_FVG_Mitigation_Window`, `NXS_Strategies_SMC.mqh:312`) is NOT redirected and IS live
  (`InpStrat_FVG_MIT_WINDOW = true`), but **`FVG_MIT_WINDOW` is not itself a registered
  `strategy_id`** in `contracts/strategy-registry.json` (checked: it's `RESEARCH_ONLY`,
  `live_implementation:false`) — i.e., the version of "FVG mitigation" that is actually alive
  and firing in the compiled EA is entirely absent from the canonical registry, while the
  registry-listed `FVG_MIT` is dead code.

### OB_MIT (selector 20)
- Textually `NXS_Strat_OB_Mitigation_Structural`, `NXS_Strategies_SMC.mqh:355` — as WRITTEN,
  this is a pure wrapper: it calls `NXS_Strat_OrderBlock()` verbatim, renames `stratName` to
  "OB_MIT", and floors the score at 68. As coded this is a **TRUE_DUPLICATE of ORDER_BLOCK**
  (selector 15) wearing a different name.
- **Also DEAD BY CONSTRUCTION**: `#define NXS_Strat_OB_Mitigation_Structural
  NXR_Strat_OB_Mitigation` (`NXS_ReusePerformancePack.mqh:2366`), same `InpNXR_Enable`-hardcoded-false
  redirect as IFVG/FVG_MIT — the ORDER_BLOCK-wrapper body never actually executes in the
  compiled EA.
- **default-enabled: `InpStrat_OB_Mit = false`** (registry says default_enabled=true, status
  ACTIVE) — consistent with dead-either-way.
- risk tier if ever alive: 0.5% ("PF0.38, collapsed from interaction").

### IFVG (selector 18)
- Textually `NXS_Strat_IFVG_Reversal`, `NXS_Strategies_SMC.mqh:163` — Inversion-FVG reversal:
  a 3-candle FVG gets violated (`close < h4` for a bullish gap) with a strong reaction candle
  AND a confirming CHOCH — genuinely distinct idea from FVG_CONT/FVG_MIT (this is a REVERSAL off
  a failed gap, not a continuation or a mitigation-retest).
- **Also DEAD BY CONSTRUCTION**: `#define NXS_Strat_IFVG_Reversal NXR_Strat_IFVG_Reversal`
  (`NXS_ReusePerformancePack.mqh:2364`), same hardcoded `InpNXR_Enable=false` redirect. The
  disabling code comment (25/08) explicitly documents that an EARLIER "PF0.66, disable it" note
  was reasoning about the WRONG (already-dead) code path — the real reason to keep it off is
  that it can never fire, independent of profitability.
- **default-enabled: `InpStrat_IFVG = false`** (registry says default_enabled=true, status ACTIVE).

### OTE_CONT (no selector_index in registry; live per `InpStrat_OTE_Cont`, code selector 25)
- `NXS_Strat_OTE_Continuation`, `NXS_Strategies_SMC.mqh:817`. Family matches registry.
- market_idea: Optimal Trade Entry — retracement into the 0.62-0.79 Fibonacci zone of the
  dominant leg on `InpTFMedium`, gated by a genuine BOS requirement (the leg must have produced
  a real displacement breaking a PRIOR swing — 17/07 fix; before, the leg was just a rolling
  30-bar high/low with no proof it was a real impulse) and strict structural-trend alignment
  (`g_struct.trend` must agree; ranging market = no trade, ambiguous discount/premium fallback removed).
- SL/TP: `NXS_DefaultSLTP`-independent — custom (swing extreme ± 0.3×ATR, target = opposite
  swing or 2.2R, whichever further). Profile row slMult=2.0/tpMult=4.5/htf=true is a fallback.
- default-enabled: `InpStrat_OTE_Cont = true` (matches registry).

### CRT — NOT LIVE (registry: `live_implementation:false`, `RESEARCH_ONLY`) — `NXS_Strat_CRT`
exists in `NXS_Strategies_SMC.mqh:959` and is fully implemented (3-candle Candle-Range-Theory
sweep-and-reverse, wick-anchored SL with a floor, no `NXS_DefaultSLTP`), and even has a live
toggle (`InpUseStrat_CRT`, default false) — but it has **no entry in the canonical registry**
(`contracts/generate_registry.py` excludes it after a cost-sensitivity re-verification found it
"definitively broken" despite an initially very strong walk-forward). Confirmed genuinely
excluded, not a registry omission bug — included here only for completeness since it lives in
the same file as several live SMC strategies.

---

## AMD / Session / Institutional family

### AMD_CONT (no selector_index in registry; live per `InpUseStrat_AMD_Cont`, code selector 28)
- `NXS_Strat_AMD_Continuation`, `NXS_Strategies_Institutional.mqh:109`. Family matches registry.
- market_idea: continuation breakout of the Asian range with a retest of the broken edge,
  gated on the AMD phase classifier being specifically `AMD_CONTINUATION_DISTRIBUTION` (a
  2025 split of a single ambiguous `AMD_DISTRIBUTION` phase that used to let AMD_CONT and
  AMD_REVERSAL both fire on the same bars — now mutually exclusive by phase).
- **default-enabled: `InpUseStrat_AMD_Cont = false`** (registry says default_enabled=true,
  status ACTIVE). Disabled 25/08: from-scratch backtest of the true live signal (M15/M30/H1,
  BUY/SELL-only variants) "never profitable" (PF 0.53-0.71, max 1/5 windows positive).
- SL/TP: custom (Asian-range mid or edge ± 0.3×ATR, 2.4R). Session/context: London, Overlap, or NY only.

### JUDAS_SWING (no selector_index; live per `InpUseStrat_Judas`, code selector 29)
- `NXS_Strat_JudasSwing`, `NXS_Strategies_Institutional.mqh:157`. Family matches registry.
- market_idea: false-move-then-reverse at London/NY open — wick below/above Asian
  range/PDL/PDH/equal-lows/highs, closing back inside, with a CHOCH confirming the reversal.
- market_context: London-open (07-10 GMT) or NY-open (12-15 GMT) window only.
- SL/TP: custom (extreme ± 0.4×ATR, target = opposite Asian edge or 2.5R). risk not in the
  tiered table (legacy/global default). default-enabled: `InpUseStrat_Judas = true` (matches registry).

### LDN_REVERSAL (no selector_index; live per `InpUseStrat_LdnReversal`, code selector 30)
- `NXS_Strat_LondonReversal`, `NXS_Strategies_Institutional.mqh:195`. Family matches registry.
- market_idea: London/Overlap-session reversal off a sweep of Asia-high/PDH/equal-high (or
  low mirror) confirmed by CHOCH, targeting the Asian opposite edge or 2.0-2.5R.
- **default-enabled: `InpUseStrat_LdnReversal = false`** (registry says default_enabled=true,
  status ACTIVE). Disabled 25/08: the true native signal "never profitable" on M15/M30/H1 or
  BUY/SELL-only splits (PF 0.36-0.78, max 1/5 windows positive).

### NY_REVERSAL (no selector_index; live per `InpUseStrat_NYReversal`, code selector 31)
- `NXS_Strat_NYReversal`, `NXS_Strategies_Institutional.mqh:252`. Family matches registry.
- market_idea: mirror of LDN_REVERSAL for the NY session, but anchored to the CURRENT day's
  actual London session high/low (computed by aggregating M5 bars in a real BST-aware GMT
  window, not the broader Asian range) — a genuinely different anchor from LDN_REVERSAL despite
  the shared "session sweep + CHOCH" mechanic.
- Notable engineering correctness detail: implements real UK daylight-saving (BST) date math
  (last-Sunday-of-March/October) rather than a fixed GMT offset, specifically because UK/US DST
  transition dates don't coincide.
- default-enabled: `InpUseStrat_NYReversal = true` (matches registry).

### WEEKLY_EXP (no selector_index; live per `InpUseStrat_WeeklyExp`, code selector 32)
- `NXS_Strat_WeeklyRangeExp`, `NXS_Strategies_Institutional.mqh:350`. Family matches registry
  (SESSION, weekly variant).
- market_idea: two-stage state machine. Stage 1 (H4/weekly trigger, unchanged since original):
  H4 displacement (body ≥0.8×ATR-H4) breaking an H4 swing (BOS) beyond the weekly open, with a
  confirming CHOCH. Stage 2 (added 26/08, a genuine redesign): instead of entering immediately
  with a wide native stop (median $38, causing 37.5% `RISK_SIZE` rejections on a $500 account),
  it ARMS and waits up to 8 M15 bars for a real reaction candle (pin bar or directional close),
  using that candle's extreme ±0.2×ATR-M15 as a much tighter stop (median $3.51 in Python
  validation, rejections 37.5%→6.7%).
- SL/TP: fully custom two-stage (not `NXS_DefaultSLTP`); target = weekly high/low or a 27.2%
  Fibonacci extension or 2.6R, whichever further; managed post-entry by a dedicated
  `NXS_WeeklyExpManage.mqh` (BE at 1.0R + structural trailing at 1.5R — separate from the
  generic profile beR/trailATR mechanism).
- default-enabled: `InpUseStrat_WeeklyExp = true` (matches registry).

### PO3 (no selector_index; live per `InpUseStrat_PO3`, code selector 33)
- `NXS_Strat_PO3`, `NXS_Strategies_Institutional.mqh:468`. Family matches registry (AMD).
- market_idea: full Power-of-Three classifier — Accumulation (Asian range) → Manipulation
  (confirmed sweep of Asian low/high) → Distribution (reclaim + strong body ≥0.6×ATR + CHOCH in
  the reclaim direction). This is a STRICTER superset of AMD_CONT's simpler
  "breakout+retest+HTF-bias" logic — PO3 requires an explicit sweep AND a CHOCH, AMD_CONT
  requires neither (just a close beyond the range and a retest near the edge).
- SL/TP: custom (sweep extreme ± 0.4×ATR, target = opposite Asian edge or 2.6R).
- default-enabled: `InpUseStrat_PO3 = true` (matches registry). **AMD_CONT is disabled and
  research-proven unprofitable while PO3 (its stricter superset) is enabled** — see
  Classification (MINOR_VARIANT: PO3 is AMD_CONT + mandatory sweep + mandatory CHOCH).

### LIQ_VOID (no selector_index; registry family SMC, live per `InpUseStrat_LiqVoid`, code
selector 34 — physically implemented in `NXS_Strategies_Institutional.mqh:503`, NOT in the SMC
file, despite the registry classifying it as family SMC)
- `NXS_Strat_LiquidityVoid`. market_idea: FVG "consequent encroachment" (50% retrace into the
  gap) continuation, requiring `htf.bias` to be strictly BULL or BEAR (never NEUTRAL).
- **default-enabled: `InpUseStrat_LiqVoid = false`** (registry says default_enabled=true, status
  ACTIVE). **Structurally unreachable, not just unprofitable**: `InpUseHTFBias` defaults to
  `false` (`NXS_Inputs.mqh:448`), which makes `NXS_GetHTFBias()` always return `HTF_NEUTRAL` in
  live operation — and this strategy's gate strictly excludes `HTF_NEUTRAL`. The code explicitly
  says "no backtest necessary: unreachable by construction, not a case of poor profitability" —
  same class of finding as IFVG/FVG_MIT/OB_MIT (dead by construction) but via a different
  mechanism (an input default, not a hardcoded macro).

### DISP_REBAL (no selector_index; live per `InpUseStrat_DispRebal`, code selector 35)
- `NXS_Strat_DisplacementRebalance`, `NXS_Strategies_Institutional.mqh:572`. Family matches
  registry (SMC — correctly placed, unlike LIQ_VOID above, despite living in the same
  Institutional file).
- market_idea: genuine FVG "50% rebalance" retracement-continuation — corrected 17/07 from an
  earlier bug that used 50% of the displacement CANDLE itself (not the FVG the candle left
  behind) as the "CE" level.
- SL/TP: custom (FVG edge ± 0.3×ATR, target = 0.8×gap extension or 2.4R).
- default-enabled: `InpUseStrat_DispRebal = true` (matches registry).

### THREE_BAR_DELIVERY_BREAK (no selector_index; live per `InpUseStrat_CISD`, code selector 27
— internal function name is still `NXS_Strat_CISD`)
- `NXS_Strat_CISD`, `NXS_Strategies_Institutional.mqh:83`. Family matches registry (LIQUIDITY —
  though it's really a simple structure-break pattern, not sweep-specific).
- **MISNAMED / renamed, not rewritten**: originally called "CISD" (Change-In-State-of-Delivery),
  but a 17/07 audit found the actual logic (3 same-color closed bars, then a close beyond their
  combined high/low) is NOT a canonical CISD (which should be identified by a break of the
  level/open that supported the opposite-candle sequence, not just "3 bars + break of their
  extreme"). The strategy was renamed to `THREE_BAR_DELIVERY_BREAK` rather than rewritten,
  because an earlier attempt at a "true" CISD (displacement+delivery+sweep+reclaim, v2.3.3) fired
  **zero times in 1067 bars** — too risky to silence the strategy again. The `InpUseStrat_CISD`
  input name was kept unchanged for `.set`-file compatibility even though the strategy's real
  identity (`stratName`) is `THREE_BAR_DELIVERY_BREAK`.
- **default-enabled: `InpUseStrat_CISD = false`** (registry says default_enabled=true, status
  ACTIVE). Disabled 25/08: PF 0.51-0.65 on the exact live recipe across all trailing widths tested.
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.5/tpMult=3.0, `htf=true`. risk: 0.5% (Tier C, "WF
  2/5 inconsistent between windows").

### AMD_REVERSAL (no selector_index; live per `InpStrat_AMD_Reversal`, code selector 24)
- `NXS_Strat_AMD_Reversal`, `NXS_Strategies_SMC.mqh:778`. Family matches registry (AMD).
- market_idea: reversal off manipulation beyond the Asian range, gated on the AMD phase being
  specifically `AMD_REVERSAL_DISTRIBUTION` (post-2025 split, mutually exclusive with AMD_CONT's
  phase — see AMD_CONT above). Requires sweep + CHOCH in the reversal direction.
- SL/TP: `NXS_DefaultSLTP`-independent — custom (swept level ± 0.5×ATR, 2.5R). Profile row
  slMult=1.5/tpMult=3.0 exists as fallback (TF=M15 per `NXS_Profile_TF`).
- risk: 1.2% (Tier B, "Python OOS1.59/117 but WF only 3/5").
- default-enabled: `InpStrat_AMD_Reversal = true` (matches registry). Notably this is AMD_CONT's
  direct phase-mirror sibling and it is ENABLED while AMD_CONT is disabled — the reversal
  interpretation of the same Asian-range framework tested better than the continuation one.

### SILVER_BULLET (no selector_index; live per `InpStrat_SilverBullet`, code selector 23)
- `NXS_Strat_SilverBullet`, `NXS_Strategies_SMC.mqh:759`. Family matches registry (SESSION).
- market_idea: full ICT Silver Bullet state machine restricted to London (10-11 GMT) or NY
  (14-15 GMT) killzones — sweep confirmed in-window → displacement with BOS (body ≥0.8×ATR)
  within 15 bars → FVG registered from that displacement → return into the FVG within 15 more
  bars. Rewritten 17/07 from a much weaker "sweep inside a time window" check (missing
  displacement/FVG/return entirely).
- SL/TP: custom (sweep level ± 0.6×ATR, 2.8R). default-enabled: `InpStrat_SilverBullet = true`
  (matches registry).

---

## PATTERN family

### ELLIOTT (no selector_index; live per `InpUseStrat_Elliott`, standalone `#endif`-guarded file)
- `NXS_Strat_Elliott`, `NXS_Strategies_Elliott.mqh:37`. Family matches registry.
- market_idea: alternating-swing pivot extraction (up to 8, fractal wing=3) mapped onto 3
  distinct wave patterns: Wave2→3 continuation (Fib retrace 0.382-0.786, 1.618 extension
  target), Wave4→5 continuation (retrace 0.236-0.618, ~1.0×leg target), and Wave5-complete
  REVERSAL (fade the completed impulse, 50% retrace target, lower score = "sc-4.0" reflecting
  lower conviction). Three genuinely different entry conditions inside one strategy_id, unified
  only by the shared pivot-extraction helper.
- **direction lock**: found in `NXS_Profile_DirectionLock`-style history — reactivated 25/08
  BUY-only on 4h after the untouched-default M15 config was net-loss (PF0.49, SELL side broken
  on every TF tried); the code's own retrace/reversal logic is symmetric (buy and sell branches
  both present), the asymmetry is empirical/config-level, not a hardcoded direction bias in
  `NXS_Strat_Elliott` itself.
- SL/TP: fully custom per pattern (structural swing ± 0.4-0.5×ATR, Fibonacci-multiple targets)
  — `NXS_DefaultSLTP` not used; profile row is inert (slMult=tpMult=0).
- default-enabled: `InpUseStrat_Elliott = true` (matches registry).

### ORDER_BLOCK (selector 15)
- `NXS_Strat_OrderBlock`, `NXS_Strategies.mqh:2130`. Registry family SMC (not PATTERN) — correct classification.
- market_idea: canonical ICT order block — a displacement (body ≥1.2×ATR) that breaks a prior
  swing (BOS), whose origin zone is the LAST opposite-color candle before the impulse (not the
  impulse candle itself — a 17/07 fix; the old version used the impulse body as if it were the
  OB). Zone persists until first retest (with rejection-candle confirmation) or
  `InpOB_MaxWaitBars=20` bars pass (expiry) or price closes fully through it (invalidation).
  Also gated by external H1 structure trend agreement and the optional SMC reaction-gate.
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.0/tpMult=3.0, `htf=true`. risk: 0.5% (legacy tier,
  "PF0.67"). default-enabled: `InpStrat_ORDER_BLOCK = true` (matches registry).
- **Relationship**: OB_MIT is, AS WRITTEN, a direct wrapper/TRUE_DUPLICATE of this function
  (see OB_MIT above) — though dead by construction either way.

### RSI_DIV (selector 14)
- `NXS_Strat_RSIDiv`, `NXS_Strategies.mqh:2014`. Registry family MOMENTUM (fixed-window
  8-bar RSI/price divergence: lower price low + higher RSI low while RSI<40, mirror for highs>60).
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.0/tpMult=4.5, `htf=false`. risk: 1.5% (legacy, "PF1.21, 98 trades").
- default-enabled: `InpStrat_RSI_DIV = true` (matches registry).
- **Relationship to RSI_DIV_PINE (below)**: explicitly documented in the code as "a second
  mechanism to compare, not a replacement" — a genuine MINOR_VARIANT (same market idea: RSI/price
  divergence; different pivot-detection method: fixed 8-bar window vs true confirmed local pivots
  with a 5-60 bar distance filter, ported from a public Pine Script).

---

## Currently-disabled/experimental TradingView-port cluster (all `default-enabled: false`,
all annotated "never verified on MT5" in `NXS_Inputs.mqh`, selectors 43-48)

### BAR_UPDN (selector 43)
- `NXS_Strat_BarUpDn`, `NXS_Strategies.mqh:450`. Registry family UNCLASSIFIED (status DISABLED — matches).
- market_idea: pure price-action, no indicator — current bar green AND opens above prior close
  = buy (mirror sell). Per-direction cooldown (`InpBarUpDnCooldownBars=8`) added after finding
  134/210 raw M15 trades were chase-entries into the same trend (first entry of a cluster
  usually won, chases usually lost) — a "reset on pattern-break" fix was tried first and failed
  (trend patterns aren't perfectly consecutive), replaced by a bar-count cooldown.
- SL/TP: `NXS_DefaultSLTP`, profile slMult=1.0/tpMult=2.5 (R:R 2.5, per explicit user request
  for tighter-stop/wider-target scalp behavior vs the swing-oriented global defaults).

### PMAX (selector 44)
- `NXS_Strat_PMax`, `NXS_Strategies.mqh:497`. market_idea: ATR-adaptive SuperTrend
  (`PMax_Func` port) — stop-and-reverse using ratcheting long/short stops around an EMA, more
  adaptive than the native Parabolic SAR; explicitly proposed as a SAR successor/complement
  after SAR alone showed negative PF (0.92) on the real engine.
- **Relationship to SAR**: MINOR_VARIANT/candidate-replacement of the same "stop-and-reverse
  trend flip" idea, different construction (ATR-ratcheted MA channel vs native Parabolic SAR).

### MACD_SMA200 (selector 45)
- `NXS_Strat_MacdSma200`, `NXS_Strategies.mqh:567`. market_idea: MACD built on SIMPLE (not
  exponential) moving averages + an SMA200 trend filter — a distinct construction from the
  native MACD strategy (selector 3), ported faithfully from a public Pine script including its
  exact histogram-zero-cross and `close[slowLength]>SMA200` conditions.
- **Relationship to MACD**: MINOR_VARIANT — same "MACD + long trend filter" idea, SMA vs EMA
  construction is a real (not cosmetic) difference in signal timing.

### RSI_DIV_PINE (selector 46) — see RSI_DIV above (MINOR_VARIANT pair).

### ICHIMOKU_HULL_MACD (selector 47)
- `NXS_Strat_IchimokuHullMacd`, `NXS_Strategies.mqh:623`. market_idea: 5-condition AND-gate
  (Hull MA rising, daily-candle trend, price vs Hull MA, Ichimoku cloud direction, Hull-based
  MACD vs its own signal) ported from a public Pine script — genuinely multi-indicator, distinct
  from both ICHIMOKU (selector 13, pure Kumo break) and MACD (native EMA MACD). One declared
  simplification: the original's Hull-based MACD signal line is itself a Hull MA of the MACD;
  here approximated by a simple average over `round(sqrt(9))=3` bars for computational cost.
- **Relationship**: GENUINELY_DISTINCT from ICHIMOKU and MACD despite reusing both names/concepts
  — the AND-of-5-filters construction is a materially different strategy, not a variant of either parent.

### 3COMMAS_BOT (selector 48)
- `NXS_Strat_3CommasBot`, `NXS_Strategies.mqh:676`. market_idea: EMA21/EMA50 cross with a
  swing-low/high (5-bar lookback) ±1×ATR(14) stop and a fixed 1:1 R:R target — ported from a
  public "3Commas Bot"/"Bj Bot" Pine script, deliberately NOT using `NXS_DefaultSLTP` (structured
  stop/target instead of a generic ATR multiple).
- **Relationship to SAR**: code explicitly calls this "conceptually similar to our SAR (EMA9/21
  cross) but with a different period and structured stop/target instead of generic ATR" —
  MINOR_VARIANT of the same "fast/slow EMA cross trend flip" idea.

---

## User-idea experimental cluster (selectors 49-55, all originated as explicit user requests, not ports)

### PIVOT_WICK (selector 49)
- `NXS_Strat_PivotWick`, `NXS_Strategies.mqh:801`. market_idea: multi-timeframe (M15/M30/H1/H4/D1)
  fractal swing-pivot pool; a touch (optionally requiring a true rejection wick) of ANY pooled
  level, evaluated only on the M15 execution bar, with optional one-shot level consumption,
  close-confirmation, and anti-buildup (Rayner Teo) filters — all default OFF except the base
  touch trigger.
- default-enabled: `InpStrat_PivotWick = false` ("original user idea, never verified on MT5" —
  matches registry `status: ACTIVE`/`default_enabled: true` MISMATCH — registry again overstates
  live-enabled status).
- **Relationship**: explicitly named by the code as one of 3 (later 4, with STRUCT_REACT and
  MALAYSIAN_SNR) independent "react to a key level" implementations later formally merged into
  LEVEL_CONFLUENCE and then LEVEL_REACTION — see Classification.

### LEVEL_CONFLUENCE / LEVEL_CONFLUENCE_M5 (selectors 50/51)
- `NXS_Strat_LevelConfluence(_M5)`, `NXS_Strategies.mqh:1069/1086`, sharing core
  `_nxs_levelconf_core`. **Explicitly documented in the code header as a merge of
  PIVOT_WICK/STRUCT_REACT/MALAYSIAN_SNR** ("the same idea implemented three times with
  different sources, never cross-checked"). Reuses PIVOT_WICK's H1/H4/D1 pivot pool only (not
  MALAYSIAN_SNR's body-based levels or STRUCT_REACT's SMC zones — despite the stated intent,
  V1 only actually incorporates the pivot source), adds: (a) a multi-TF confluence score bonus,
  (b) touch OR sweep-then-reclaim trigger modes, (c) an N-bar-confirmation delay (default 2 —
  added after finding first-touch entries had only 34% win rate / 58% stopped out).
- The M5 twin is a **TRUE_DUPLICATE** of the M15 version — identical core function, only the
  execution TF and state struct differ (explicit user request: "mark levels D1/H4/H1, enter on
  both M15 and M5").
- default-enabled: both `false` (never verified; superseded by LEVEL_REACTION per the code's own
  admission below).

### LEVEL_REACTION / LEVEL_REACTION_M5 (selectors 52/53)
- `NXS_Strat_LevelReaction(_M5)`, `NXS_Strategies.mqh:1325/1335`, sharing core
  `_nxs_levelreact_core`. **Explicitly documented as the TRUE merge** of
  PIVOT_WICK+STRUCT_REACT+MALAYSIAN_SNR (+LEVEL_CONFLUENCE's skeleton) — LEVEL_CONFLUENCE
  "closed negative" and used only the pivot source; LEVEL_REACTION adds a genuine second
  independent level source (H4 12-bar CLOSE-based S/R, the actual MALAYSIAN_SNR construction)
  plus a confluence bonus with live SMC OB/FVG zones (`g_reaction`, the STRUCT_REACT
  infrastructure) — this is the first of the cluster to actually combine ≥2 real level sources
  in one trigger. New ingredient not in any of the three originals: a max-breach-depth gate
  (100 pips) derived from a fresh 7402-pivot GOLD-M15 study (reversal rate 99.5% under 50 pips,
  78.9% at 50-100, only 69.1% beyond 100 — beyond the threshold the candidate is discarded
  outright, not merely penalized), plus extra confirmation bars for "deep" breaches (≥50 pips).
- M5 twin is again a **TRUE_DUPLICATE** (same core, different execution TF).
- default-enabled: both `false` (never verified).
- **Overall cluster verdict**: PIVOT_WICK, STRUCT_REACT (as a level-reaction sub-behavior),
  MALAYSIAN_SNR, LEVEL_CONFLUENCE(+M5), and LEVEL_REACTION(+M5) are SEMANTIC_DUPLICATEs of one
  market idea ("price reacts at a pre-identified key level") — LEVEL_REACTION is the most
  evolved/complete implementation; LEVEL_CONFLUENCE is a strict subset of LEVEL_REACTION;
  PIVOT_WICK is the subset that only LEVEL_CONFLUENCE/LEVEL_REACTION's pivot-source path
  reimplements; MALAYSIAN_SNR is the subset that only LEVEL_REACTION's SNR-source path
  reimplements; STRUCT_REACT is architecturally different (reacts to the SMC OB/FVG engine
  directly rather than to pivot/SNR levels) but is folded into LEVEL_REACTION only as a
  confluence BONUS, not a trigger source — so STRUCT_REACT remains the most independent member
  of this family and is graded GENUINELY_DISTINCT-but-related rather than a pure duplicate.

### WICK_SWEEP_REV (selector 54, EXPERIMENTAL)
- `NXS_Strat_WickSweepReversal` (compiled as a Fase-C wrapper comparing legacy vs a read-path
  engine, functionally identical output — `NXS_Strategies_Experimental.mqh:861`, core logic
  `_NXS_WickSweepReversal_Legacy`, line 675). market_idea: an H4 candle's wick (≥15 pips) marks
  a level; when a later price sweeps ≥35 pips beyond it, enter IMMEDIATELY (tick-level, not
  bar-close) in the FADE direction, fixed 25-pip SL / 100-pip TP. Hardcoded to H4 regardless of
  `InpUseStrategyProfiles`/`InpProfileMultiTF`. One active level per side; a new qualifying wick
  REPLACES an unconsumed level (documented as an unoptimized simplification, candidate for a
  multi-zone registry later).
- **observation_point exception**: this is the one core strategy that genuinely evaluates on
  live bid/ask per tick, not once per closed bar — confirmed by extensive shadow-research
  instrumentation in the same file built specifically to verify this claim empirically (found
  the *global* new-bar gate in `OnTick()` still throttles it to once per `InpTFEntry` (M15) bar
  in practice, despite the per-tick H4-level check).
- default-enabled: `InpStrat_WickSweep = false` (matches registry EXPERIMENTAL/false).

### WICK_SWEEP_RECLAIM (selector 55, EXPERIMENTAL)
- Implemented OUTSIDE the normal `SNXSSignal`-returning dispatcher: `NXS_WickReclaim_Detect`/
  `NXS_WickReclaim_HasPendingEntry`/`NXS_WickReclaim_OnExecuteResult`
  (`NXS_Strategies_Experimental.mqh:581-652`), called directly from `NEXUS_EA_v2.mq5:320`
  (`NXS_WickReclaim_TryEntries`) rather than through `NXS_CollectRaw`. **MINOR_VARIANT of
  WICK_SWEEP_REV**: identical level source and sweep threshold (same
  `InpWickSweep_MinWickPips`/`SweepPips`/`SLPips`/`TPPips`, no new parameters), but instead of
  entering immediately on the sweep, it ARMS and waits for price to reclaim back to the original
  trigger price before entering — promoted from a pure research/shadow mode after tick-level
  study showed waiting for reclaim improves win-rate/PF on the same real sample.
- SIGNAL_PRICE/REFERENCE_PRICE: `entryRef = trigger_price` (the price observed at the moment of
  the original sweep, frozen) — NOT the live price at the moment of reclaim. ORDER/FILL_PRICE:
  still live ASK/BID via `NXS_OpenTrade`→`NXS_DoBuy/DoSell`, unchanged from every other strategy.
- default-enabled: `InpStrat_WickSweepReclaim = false` (matches registry EXPERIMENTAL/false).

---

# Summary

## Registry vs. compiled-default mismatches (registry says `status: ACTIVE, default_enabled:
true`; actual `NXS_Inputs.mqh` flag defaults to `false`)

**Correction (Phase 4 sec.0 direct verification, post-audit):** the PIVOT_WICK row below was in
this agent's original output but does NOT hold up under direct verification — `contracts/strategy-registry.json`
actually lists PIVOT_WICK as `status: DISABLED, default_enabled: false` (its `stato` in
`knowledge/strategy_database.json` is `"disabilitata in produzione"`, which the generator maps
correctly). PIVOT_WICK is REMOVED from the confirmed-mismatch count; the confirmed total is
**10**, not 11. Kept below (struck through in spirit, not deleted) for traceability of the
correction.

| strategy_id | Actual default | Why disabled (from code comments) |
|---|---|---|
| BJORGUM | false | Real-MT5 backtest -8.6R, 5/6 years negative (proxy bug fixed, re-tested, confirmed negative) |
| TURTLE_SOUP | false | True live signal never robustly profitable (max PF0.94) across TF/direction splits |
| IFVG | false | Dead by construction: macro-redirected to `NXR_Strat_IFVG_Reversal`, gated by hardcoded `InpNXR_Enable=false` |
| FVG_MIT | false | Same NXR dead-by-construction redirect as IFVG |
| OB_MIT | false | Same NXR dead-by-construction redirect (and, as literally written, a duplicate of ORDER_BLOCK) |
| LIQ_VOID | false | Structurally unreachable: requires `htf.bias != NEUTRAL`, but `InpUseHTFBias=false` makes it always NEUTRAL |
| ~~PIVOT_WICK~~ | ~~false~~ | **NOT a real mismatch** — registry already correctly shows `DISABLED`/`default_enabled:false`; see correction note above |
| InpUseStrat_AMD_Cont (AMD_CONT) | false | True live signal never profitable (PF 0.53-0.71) |
| InpUseStrat_LdnReversal (LDN_REVERSAL) | false | True live signal never profitable (PF 0.36-0.78) |
| InpUseStrat_CISD (THREE_BAR_DELIVERY_BREAK) | false | PF 0.51-0.65 on exact live recipe |
| InpUseStrat_RangeFade (RANGE_FADE) | false | Confirmation gate fires only 6x/10y, all losses |

Registry also lists `LEVEL_CONFLUENCE`, `LEVEL_CONFLUENCE_M5`, `LEVEL_REACTION`,
`LEVEL_REACTION_M5`, `BAR_UPDN`, `PMAX`, `MACD_SMA200`, `RSI_DIV_PINE`, `ICHIMOKU_HULL_MACD`,
`3COMMAS_BOT`, `WICK_SWEEP_REV`, `WICK_SWEEP_RECLAIM`, and (per the correction above) `PIVOT_WICK`
correctly as `DISABLED`/`EXPERIMENTAL`/`default_enabled:false` — consistent with code. The
mismatch is concentrated in the "ACTIVE" bucket: **10 of the registry's "ACTIVE, default-enabled"
strategies are actually off by default in the compiled EA** (confirmed by direct line-by-line
verification against `NXS_Inputs.mqh` and `contracts/strategy-registry.json` in Phase 4 sec.0),
three of them (IFVG/FVG_MIT/OB_MIT) unconditionally dead regardless of the toggle.

## Classification groups (by real market idea, not name)

**TRUE_DUPLICATE** (functionally identical logic, cosmetic difference only):
- OB_MIT = ORDER_BLOCK, as literally coded (direct wrapper call + score floor) — moot in
  practice since OB_MIT is also dead-by-construction via the NXR redirect.
- LEVEL_CONFLUENCE_M5 = LEVEL_CONFLUENCE (identical core function, execution TF only differs).
- LEVEL_REACTION_M5 = LEVEL_REACTION (identical core function, execution TF only differs).

**SEMANTIC_DUPLICATE** (same market idea, different indicator/detection primitive):
- PIVOT_WICK / MALAYSIAN_SNR / LEVEL_CONFLUENCE / LEVEL_REACTION — all "price reacts at a
  pre-identified key level," different level sources (fractal wick pivots vs H4 close-based S/R
  vs a merge of both); LEVEL_REACTION is the superset, LEVEL_CONFLUENCE a partial subset,
  PIVOT_WICK and MALAYSIAN_SNR the two original single-source ancestors.
- SH_BMS_RTO / SMS_BMS_RTO — both "sweep → break of structure → return to origin," different
  detection method (external-level sweep + state machine vs HH/LL failure-swing labelling).
- IFVG / FVG_MIT / FVG_CONT — all FVG-based but genuinely different theses (inversion-reversal
  / mitigation-retest / continuation) — NOT duplicates of each other, listed together only
  because they share the "FVG" building block; kept GENUINELY_DISTINCT (see below), noted here
  only to make clear the non-duplication was actively checked.

**MINOR_VARIANT** (same core idea, deliberately different parameters/construction, kept as a
separate candidate to compare):
- RSI_DIV_PINE is a variant of RSI_DIV (true confirmed pivots vs fixed 8-bar window).
- MACD_SMA200 is a variant of MACD (SMA vs EMA construction).
- PMAX is a variant/candidate-successor of SAR (ATR-ratcheted MA channel vs native Parabolic SAR).
- 3COMMAS_BOT is a variant of SAR (EMA21/50 cross + structured stop/target vs EMA9/21 + generic ATR).
- WICK_SWEEP_RECLAIM is a variant of WICK_SWEEP_REV (same event source, wait-for-reclaim vs
  immediate entry).
- AMD_CONT is a simpler subset of PO3 (PO3 = AMD_CONT + mandatory sweep + mandatory CHOCH); one
  is disabled (unprofitable) and its superset is enabled.
- SWING_FALSEBREAK is a variant of TURTLE_SOUP (same sweep+close-back mechanic, anchored to
  major fractal swing pivots instead of session/PDH-PDL levels; ATR-multiple stop instead of
  structural).

**MISNAMED** (name implies X, code/behavior is actually Y):
- **THREE_BAR_DELIVERY_BREAK** (`InpUseStrat_CISD` toggle, internal function `NXS_Strat_CISD`):
  the input/function names still say "CISD" (Change-In-State-of-Delivery) but the code was
  explicitly renamed away from that concept in 2025-07 because the actual logic (3 same-color
  bars + break of their extreme) is not a canonical CISD — a real CISD would key off a break of
  the level/open that supported the opposite-candle sequence. The `stratName` field correctly
  says `THREE_BAR_DELIVERY_BREAK`; only the legacy input/function identifiers still say CISD.
- **OB_MIT**: name implies "order block mitigation" (a distinct SMC concept — a broken/retested
  OB) but, as literally written, its body performs exactly `NXS_Strat_OrderBlock()` (a retest of
  a still-valid OB, not a mitigation/breaker) — moot in the compiled EA since it's redirected to
  a dead NXR path regardless.
- **IFVG / FVG_MIT / OB_MIT (as a trio)**: all three names imply active, tunable SMC strategies;
  in the compiled EA they are dead code paths (macro-redirected to an `InpNXR_Enable`-gated
  engine that is hardcoded off) — the registry's `status: ACTIVE` is misleading for all three.
- **LIQ_VOID**: name/registry family imply a working SMC continuation strategy; it is
  structurally unreachable given the engine's own default HTF-bias setting (always NEUTRAL),
  independent of profitability.

**GENUINELY_DISTINCT** (real, separate market ideas — the large majority):
ADX_RSI, MACD, SAR, TSI, BOLLINGER, BB_SQUEEZE, BREAKOUT_ACC, Z_SCORE_BREAKOUT,
VOLATILITY_BREAKOUT_CONFIRMED, LONDON_BO, EMA_PULLBACK, ICHIMOKU, ICHIMOKU_HULL_MACD, RSI_DIV,
ORDER_BLOCK, LIQ_SWEEP, FVG_CONT, FVG_MIT (idea, though dead), IFVG (idea, though dead), OTE_CONT,
SH_BMS_RTO, STRUCT_REACT, WEEKLY_EXP, PO3, DISP_REBAL, ELLIOTT, JUDAS_SWING, LDN_REVERSAL,
NY_REVERSAL, AMD_REVERSAL, SILVER_BULLET, SWING_FALSEBREAK (variant-flavored but a distinct
anchor), WICK_SWEEP_REV, RANGE_FADE, BJORGUM (idea, though disabled).

## Genuinely distinct market ideas across the 53 registered strategies

Counting one idea per SEMANTIC_DUPLICATE/TRUE_DUPLICATE cluster (taking the most complete/live
member as the idea's representative) and one idea per GENUINELY_DISTINCT and MINOR_VARIANT entry
(variants are counted as their own idea since the task's own MACD/PMax/3Commas comments treat
them as "a second mechanism to compare," not interchangeable):

- 53 registered live strategy_ids
- minus 3 TRUE_DUPLICATE collapses (OB_MIT→ORDER_BLOCK, LEVEL_CONFLUENCE_M5→LEVEL_CONFLUENCE,
  LEVEL_REACTION_M5→LEVEL_REACTION)
- minus 2 more collapses inside the level-reaction SEMANTIC_DUPLICATE cluster (PIVOT_WICK and
  LEVEL_CONFLUENCE folded into LEVEL_REACTION as their superset; MALAYSIAN_SNR kept distinct as
  the second true level-source that LEVEL_REACTION actually incorporates, so it is folded too) —
  net: {PIVOT_WICK, LEVEL_CONFLUENCE, LEVEL_REACTION, MALAYSIAN_SNR} → counted as **1** idea
  (LEVEL_REACTION), a reduction of 3.
- minus 1 collapse for SH_BMS_RTO/SMS_BMS_RTO (kept as 1 idea, "sweep→structure-break→return,"
  despite different detection primitives, per the task's instruction to be rigorous about
  same-idea-different-wrapper cases)

**≈ 53 − 3 − 3 − 1 = 46 genuinely distinct market ideas** implemented across the 53 registered
"strategies." (STRUCT_REACT is counted separately from the LEVEL_REACTION cluster since it reacts
to a live SMC zone engine, not a pivot/SNR level pool — a materially different mechanism even
though the code itself treats it as a spiritual cousin.)

## Duplicates/variants found: 7 clusters, 10 strategy_ids involved
(OB_MIT+ORDER_BLOCK; LEVEL_CONFLUENCE+LEVEL_CONFLUENCE_M5+LEVEL_REACTION+LEVEL_REACTION_M5+
PIVOT_WICK+MALAYSIAN_SNR as one 6-member cluster; SH_BMS_RTO+SMS_BMS_RTO;
RSI_DIV+RSI_DIV_PINE; MACD+MACD_SMA200; SAR+PMAX+3COMMAS_BOT; AMD_CONT+PO3;
WICK_SWEEP_REV+WICK_SWEEP_RECLAIM; TURTLE_SOUP+SWING_FALSEBREAK) — 22 strategy_ids total
touched by some duplicate/variant relationship, the remaining 31 are GENUINELY_DISTINCT.

## Misnamed strategies (4)
1. **THREE_BAR_DELIVERY_BREAK** (toggle/function still say "CISD") — actually a simple 3-bar
   same-color-run + extreme-break pattern, not a canonical Change-In-State-of-Delivery.
2. **OB_MIT** — as coded, a verbatim wrapper around `NXS_Strat_OrderBlock()` (a valid-OB retest),
   not an order-block "mitigation"/breaker pattern; also dead code via the NXR redirect.
3. **IFVG / FVG_MIT** (as a pair) — both are dead-by-construction (redirected to an
   `InpNXR_Enable`-gated engine hardcoded off); the registry's `status: ACTIVE` for both is
   incorrect for the compiled EA.
4. **LIQ_VOID** — registry marks it `ACTIVE`/`default_enabled:true`; it cannot fire given the
   engine's own default HTF-bias setting, independent of the `InpUseStrat_LiqVoid` toggle (which
   is itself also `false`).

---

*Audit method: read every `NXS_Strat_*`/`NXR_Strat_*` function body, its `NXS_DefaultSLTP`/custom
SL-TP path, its `NXS_Profile_TF`/`NXS_Profile_Risk`/`NXS_Profile_Get` profile row, its
`InpStrat_*`/`InpUseStrat_*` default and any adjacent code comment, and its call site in
`NEXUS_EA_v2.mq5:NXS_CollectRaw`. `knowledge/strategy_database.json` was not required to
corroborate any finding above — all findings trace directly to MQL5 source line references
cited inline. No code, config, or any file other than this one was modified.*
