# 18. Portfolio Engineering Roadmap — decisions and known blockers

## Context

On 2026-07-30 the user supplied an external research report ("Next-Generation
Portfolio Engineering for NEXUS EA") proposing a three-layer ML stack on top
of the 37 strategies: meta-labeling (secondary classifier deciding act/size
per trigger), regime detection (HMM/BOCPD) to enable/reweight strategies by
market state, and a correlation-aware allocator (Hierarchical Risk Parity +
online weighting) — gated throughout by an anti-overfitting validation
backbone (Combinatorial Purged CV, Deflated Sharpe Ratio, Probability of
Backtest Overfitting) and a causal-attribution + champion/challenger
deployment loop. The methods cited (López de Prado's AFML, HRP 2016, Bailey
et al. DSR/PBO, Brodersen et al. CausalImpact) are real, correctly described,
and standard in quant research.

## Decision: sequencing

**Proposed.** This architecture is not built now. It is deferred until the
per-strategy validation goal already in progress (10 strategies with a real
tested Profit Factor on an independent engine — see `pinescript/README.md`
Batch 1/2/3) is complete.

Rationale: every layer in the proposed stack (HRP's covariance matrix over
strategy PnL, the meta-labeler's training set, the regime × strategy weight
matrix) is built from historical per-strategy trade series. Today only 4 of
37 strategies have an independently confirmed PF (Batch 1, Pine/TradingView);
2 more are ported but untested (Batch 3); the rest have no real trade
series outside the strategy's own MQL5/Python code. Building portfolio-level
machinery on unvalidated components is the textbook setup PBO exists to
catch — it would very likely produce a plausible-looking but overfit
result, not a plan to be trusted with the 37 strategies as they stand today.

The one piece of the proposed stack that is cheap and useful independent of
that sequencing is the validation backbone itself (CPCV / DSR / PBO) applied
to whatever trade series already exist. That is the natural Stage 0/1 for
whenever the user wants to start on this track — not before.

## Known blockers to strategy performance (as of 2026-07-30)

**Observed**, grounded in `11_BACKTEST_CAPABILITY_MATRIX.md` and this
session's work on `NXS_Strategies_SMC.mqh`:

1. **Spread/commission/slippage are not modeled** in `server/backtest.py`
   (`run_backtest`, confirmed in `11_BACKTEST_CAPABILITY_MATRIX.md`). Every
   PF/WR number produced by that engine is optimistic relative to live
   execution — the gap matters most for tight-SL strategies (e.g. ADX_RSI
   SL=1.0×ATR) where a few dollars of XAUUSD spread is a meaningful fraction
   of the stop distance.
2. **Silent synthetic-data fallback**: `get_ohlc`/`_fetch_real` fall back to
   a deterministic synthetic series if the real feed (Yahoo/Stooq) fails.
   The `data_source` field in every result must be checked — a result with
   `"data_source": "synthetic"` is not a market result.
3. **Single global position, no portfolio simulation**: the Python engine
   cannot show what happens when several correlated SMC/ICT strategies fire
   together during the same regime (e.g. a news-driven whipsaw) — the
   scenario most likely to produce simultaneous drawdown across the
   portfolio is exactly the one it cannot simulate today.
4. **Confirmed fidelity bugs already found and partially fixed**: F-02
   (Silver Bullet killzone used fixed GMT windows, wrong for half the year
   — fixed in `NXS_Strategies_SMC.mqh`, not yet compiled/verified by the
   user) and F-05 (Malaysian SNR had no usage cap per S/R level, allowing
   unlimited re-triggering off a level that had already failed — fixed,
   same caveat). Both are the kind of silent, months-long edge leak that a
   backtest running on the same buggy logic cannot reveal by itself.
5. **Unresolved offset-mapping observation** (flagged, not fixed): comparing
   `NXS_Strat_OrderBlock` (MQL5) against the already-tested
   `NEXUS_ORDER_BLOCK.pine` port suggests the existing port mixes two
   different MQL5-shift→Pine-offset conventions (loop ranges vs single-bar
   touch checks). Left unmodified because fixing it would invalidate the
   already-recorded Batch 1 numbers for that file — worth a dedicated,
   isolated re-test before trusting ORDER_BLOCK's recorded PF as final.
6. **No regime gating**: trend-following strategies (SAR, MACD) and
   mean-reversion/SMC strategies are always live together; there is no
   mechanism to reduce trend-strategy size during chop or vice versa.
7. **31 of 37 strategies have never been independently tested** outside
   their own source code path — the true state of their edge is unknown,
   not confirmed-negative or confirmed-positive.

## Why a multi-agent (multiple parallel Claude) approach does not by itself
## create strategy edge

**Proposed / documented for future reference.** Parallel agents are a good
fit for independent, well-scoped engineering or research tasks with a known
answer to find (the earlier 3-agent git-branch archaeology is an example).
They are a poor fit for "does this strategy have real edge," because:

- The answer can only come from running the strategy against real market
  data through a trustworthy engine — that step is bottlenecked by the
  testing tool itself (TradingView's Strategy Tester runtime, MT5's
  optimizer, or the Python engine's data fetch), not by how much reasoning
  or how many parallel workers are thrown at it.
- Worse, several agents each proposing variants and a human picking the
  best-looking backtest is structurally identical to the "many trials,
  pick the best Sharpe" scenario the Deflated Sharpe Ratio and PBO are
  designed to catch (see the external report's §6). More parallel search
  without an out-of-fold/CPCV discipline manufactures apparent edge from
  noise; it does not find real edge faster.
- Parallel agents remain useful for the mechanical side of this program:
  porting strategies to Pine, writing the validation/backtest code itself,
  and reviewing/auditing fidelity — just not for "trying more parameter
  combinations until one looks good."

## Endorsed testing protocol (user-specified, 2026-07-30)

**Proposed**, to be applied once TradingView access is available, per
strategy, one at a time:

1. Run the strategy's Pine port **unfiltered** ("senza freni" — HTF filter
   off, any optional confluence off) first, to see the raw signal's PF/WR/DD
   on its own.
2. Read the resulting trade list/chart and ask, per strategy: what would
   have improved execution here (early stop-outs before reversal? signals
   during clearly wrong regime? a specific recurring failure pattern
   visible on the chart)?
3. Only then add filters/parameters, one at a time, each justified by what
   was actually observed — not applied speculatively up front.

This is consistent with the MAE/MFE-driven methodology already used for the
17/07 MACD/ADX_RSI fixes recorded in `pinescript/README.md`, and is the
right order of operations: raw signal quality first, filters as a response
to observed failure modes, not as a default.

## Concrete next steps (cheap, before any Stage 1 ML work)

**Proposed**, all inside `server/backtest.py`, no architecture change:

1. Add spread/commission parameters to `run_backtest` so PF/WR figures are
   not systematically optimistic (addresses blocker #1).
2. Export MAE (maximum adverse excursion before exit) per trade in
   `trade_list`, not just the R-multiple outcome — this is the concrete way
   to answer "are we being stopped by noise/spread on a stop that was
   almost right" vs "the trade was genuinely wrong," per strategy, with
   data instead of a guess.
3. Widen `optimize()`'s grid beyond the current fixed 3×3 SL/TP sweep
   (currently `atr_sl ∈ {1.0,1.5,2.0}`, `atr_tp ∈ {2.0,3.0,4.0}` only) to
   cover breakeven_r/trailing_atr/confirm_bars/cooldown_bars, which
   `run_backtest` already accepts as parameters but `optimize()` does not
   sweep.

These three are self-contained, do not touch MQL5, and directly serve the
"reliable tool to try many strategies with many parameters" need — the
engine already exists (`server/backtest.py`, all 37 strategy signals are
already ported to Python per `STRATEGIES`), it just needs these gaps closed
before its numbers can be trusted at parameter-sweep scale.
