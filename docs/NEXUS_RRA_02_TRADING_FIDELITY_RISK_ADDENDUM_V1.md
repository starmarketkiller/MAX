# NEXUS RRA-02 — Trading Fidelity & Risk Addendum V1

Status: **READY_FOR_REVIEW — no risk-policy mutation**  
Repository baseline: `c568cff68e6c6926af31df2e543fdf1014e9c476`  
Scope: repository evidence and deterministic synthetic fixtures only.

The named Grok inputs `NEXUS_followup_review.md` and
`NEXUS_followup_matrix.csv` were not present in the repository, known local
worktrees, attachments, Downloads, Documents, or Desktop during this work.
Their claims are therefore not promoted to evidence here. This report can be
reconciled additively if the original files become available.

## 1. Risk Configuration Gap Report

### Effective sizing path

`NXS_OpenTrade` selects a profile risk percentage when profiles are enabled,
otherwise `InpRiskPercent` (1%). `NXS_CalcLotRisk` converts money-at-risk to
lots, applies anti-bleed, account/streak multipliers, floors to broker volume
step, and rejects an untradeable minimum lot unless the separate
`InpMaxRiskAtMinLotPct` ceiling permits it. After calculation, Pip Sequence,
EMA Pullback fixed-lot, and Research fixed-lot modes can replace that result.
Outside Research, remaining runtime multipliers are capped by
`InpMaxTotalLotMult` (1.8). The lot then enters
`NXS_CommonExposurePreflight`, which enforces account guard, permanent DD
protection, general protections including aggregate risk, RiskShield cluster
controls, directional exposure, projected margin, and broker preflight.

Grid, pyramid, institutional add, SL reclaim, and profit reclaim reuse the
common preflight. PipSequence re-entry now composes both protection families
through PR #49; this addendum does not duplicate or modify that Safety fix.
Final safe Buy/Sell helpers retain account-guard defense in
depth. The Data Collection branch is different: fixed `0.01` by default and
only `NXS_PreFlight` plus its open-position ceiling. Its own source comment
explicitly says it bypasses concurrency, projected-margin, directional
exposure, and total multiplier controls. Account Guard still exists at the
final safe helper, but the full common risk contract is not applied. This is
an intentional research/demo path today, not a live-safe equivalent.

### Effective matrix (observed, not approved policy)

| Dimension | DEFAULT | RESEARCH | DEMO | PROPOSED LIVE |
|---|---|---|---|---|
| Base sizing | profile 0.3–5% or global 1% | fixed `InpResearchFixedLot` | same code path as default unless a mode/preset changes it | candidate hard cap ≤0.5% per trade |
| Fixed overrides | PipSeq 0.05; EMA override if non-zero | research fixed lot wins | Data Collection fixed 0.01 when enabled | fixed overrides must also prove cap compliance |
| Minimum-lot exception | may allow effective risk up to 8% balance | fixed-lot semantics | applies unless isolated mode changes path | candidate: reject if hard cap exceeded |
| Multipliers | account, anti-bleed, optional loss-streak, runtime; residual cap 1.8 | disabled by research branch | configurable; not intrinsically ≤1% | cap must apply to final effective risk, after every override/multiplier |
| Aggregate risk | 25% based on current open risk | may be disabled by research settings | current configured behavior | explicit lower approved cap required |
| Grid/pyramid/add-ons | common preflight, budget-derived sizing | mode-dependent | common path except Data Collection | every new exposure charged to same final-risk budget |
| Margin | projected margin 500% plus broker preflight | parity setting matters | enforced on common path | mandatory, not a substitute for risk cap |
| Correlation | RiskShield cluster cap | parity/config dependent | common path | mandatory fail-closed for unknown profile where applicable |
| Total DD | PR #47 permanent persisted latch | research can explicitly disable for scientific isolation | enabled by default | mandatory; runtime restart/broker replay remains a live-readiness blocker |

The suggested Demo ≤1% and Live ≤0.5% are **proposals**, not approved policy.
Current profiles reach 5%, the minimum-lot exception reaches 8%, aggregate
risk is 25%, and fixed-lot paths are not expressed as percentages. Therefore
the current code cannot truthfully claim either proposed cap.

### Versioned hard-cap contract (design only)

`NXS_EFFECTIVE_RISK_CAP_V1` should evaluate immediately before every order
request, including primary, fixed-lot, grid, pyramid, reclaim, institutional,
and Data Collection routes. Inputs: account mode, balance/equity, final lots,
broker tick metadata, effective stop, existing open risk, route, strategy,
profile/preset provenance, and cap-policy version. Outputs: computed
per-order risk %, projected aggregate risk %, decision, reason, and audit ID.

The cap must operate on the **final lot after all overrides and multipliers**.
Unknown tick metadata, missing/invalid stop, unknown account mode, or
unclassifiable risk must reject new exposure. The design does not change
position management. Policy values remain unresolved until human approval.

## 2. Legacy backtest characterization

Repository inspection and synthetic tests establish:

- legacy entry price is the signal bar close;
- next-open is a distinct, currently non-default model;
- SL wins when SL and TP are both touched in one bar;
- BE/trailing updates occur before same-bar exit resolution;
- costs are additive in R and proportionally scaled at a 5R cap;
- unknown timeframes historically fall back to daily semantics;
- unavailable real sources historically fall back to deterministic synthetic data;
- zero costs are the legacy default;
- MACD prefix values are invariant when future bars are truncated.

The last three behaviors are unsuitable as silent defaults for new scientific
runs. `strict_execution_contract=True` now rejects an unknown timeframe and
real-source failure, and emits execution/cost metadata. The flag defaults to
false, preserving legacy reproduction. `NEXT_OPEN_V1` and alternative
intrabar policies are characterized by pure fixture primitives but are not
wired into the economic engine in this milestone.

Python tests do not prove MQL5 parity. No MetaEditor/Strategy Tester run was
performed by this addendum.

## 3. Versioned Execution Model Contract

New experiments must persist the fields in
`contracts/research-execution-model-v1.schema.json`: engine version, dataset
fingerprint/source, timeframe, fill model, intrabar policy, complete cost
model, cap occurrences, fidelity class, and indicator implementation version.
Changing fill or intrabar semantics requires a distinct experiment identity.
Historical records remain immutable and may only receive an append-only
projection stating their known or unknown execution semantics.

## 4. Minimal repairs and compatibility

Implemented, opt-in and backward compatible:

1. strict unknown-timeframe rejection;
2. strict no-synthetic-fallback behavior when real data is unavailable;
3. execution contract metadata;
4. cost-cap occurrence count;
5. zero-cost warning.

Not implemented: a new default fill model, altered intrabar ordering, changed
cost assumptions, or changed risk settings. Those would change trades, PF, or
expectancy and require a separate versioned decision.

## 5. Cross-engine parity integration plan

Reuse the existing Phase 7 parity artifacts and golden-trace work. Add the
execution-contract fields to each trace; do not create another parity engine.

1. **MACD 12/26/9 closed bar:** freeze feed/bar fingerprint and signal-line
   formula; compare indicator values, causal crossover timestamp, direction,
   decision eligibility, then any fill model.
2. **BREAKOUT_ACC bar close:** reuse existing Python/MT5 event streams; compare
   range construction, close-known event, cooldown, and first divergence.
3. **SAR closed bar:** freeze AF/EP rules and reversal-bar semantics; compare
   indicator value and flip event before economics.

Allowed classifications remain `EXACT_ON_FIXTURE`,
`EXPLAINED_FEED_DIFFERENCE`, `EXPLAINED_EXECUTION_DIFFERENCE`,
`LOGIC_MISMATCH`, and `INSUFFICIENT_DATA`.

## 6. Benchmark preregistration draft

Candidates: Z_SCORE_BREAKOUT, EMA_PULLBACK, MACD, SAR, ADX_RSI. This is a
draft only; no benchmark was executed.

- method: Phase 7.27 regime-matched baseline, reused without outcome-driven
  rematching;
- unit: preregistered causal signal/event per candidate;
- matching: direction, regime, session, volatility/exposure opportunity,
  period and holding-duration eligibility within split;
- equality constraints: identical feed/version, period, costs, fill model,
  intrabar policy, direction convention and censoring;
- outcomes: net R/expectancy and uncertainty; PF is secondary;
- controls: temporal exclusion, reuse ledger, dependence diagnostics, fixed
  multiple-testing family;
- stop: insufficient match quality/sample, lineage ambiguity, parity defect,
  or contract incompleteness;
- interpretation: Yahoo/Grok results are not promotion evidence; discovery
  cannot establish live eligibility.

## Review gates

Before any risk-policy change: approve numerical Demo/Live caps, aggregate
cap, treatment of fixed-lot routes, and migration behavior. Before any new
economic default: preregister and version it, prove legacy reproducibility,
and run Python plus MT5 parity evidence where relevant.
