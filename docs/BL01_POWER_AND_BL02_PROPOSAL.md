# BL-01 power verification and BL-02 proposal

Date: 2026-10-11. No tick data was read, BL-01 was not run, and nothing in the BL-01 preregistration was changed.

- Reproducible computation: `server/research_scripts/bl_power_study_v1/run_study.py` produces `bl01_power_report_v1.json`.
- Model: `server/research_scripts/research_intelligence_v1/power.py`.
- Draft: `server/research_scripts/bl_power_study_v1/BL-02_proposal_draft_v0.json`.
- Tests: `server/tests/test_bl_power_study_v1.py`.

**Human decision recorded (max, 2026-10-11):**

- BL-01 keeps its preregistration unchanged.
- The period is not extended, and the minimum effect is not raised.
- The discovery run gives descriptive results, a preliminary reading of the hypothesis, and feasibility information. It makes no confirmatory claim of an edge.
- Discovery outcomes are never used to change parameters or to choose an effect size afterwards.

## 1. The 24% / 372 figure, verified

It came from the RI-02 loop's `SYNTHETIC_DRY_RUN`. Recomputed exactly (`power.replicate_loop_v1`):

| Item | Value used by the loop |
|---|---|
| Test | one-sample, one-sided z-test on `p_target_first` against p0 |
| Baseline p0 | 1/3 (driftless barrier probability for +2R / −1R) |
| Effect | +0.08 absolute (p1 = 0.4133), a default of the loop, not a BL-01 quantity |
| Alpha | 0.05 / 6 = 0.00833 (z = 2.394): Bonferroni over BL-01 plus 5 **untested** AI alternatives |
| Target power | 0.80 (z = 0.842) |
| Sample | 80 "events", taken from the catalog estimate of H4 setups |
| Groups | one sample, no control group |
| Dependence | none |
| Costs | none |

n = ((2.394·√(⅓·⅔) + 0.842·√(0.4133·0.5867)) / 0.08)² = (1.543 / 0.08)² = **372**.

Power at n = 80: critical p = ⅓ + 2.394·√(0.2222/80) = 0.4595, z = (0.4595 − 0.4133)/√(0.2425/80) = 0.839, so the **analytic power is 0.20**. The simulation gave 0.21–0.25 (binomial discreteness).

**The arithmetic is correct. The test does not match BL-01, for four reasons:**

1. BL-01 does not test `p_target_first` against 1/3. Its decision rule (`BL01_DECISION_RULES_V1`) is GO only if all of these hold:
   - n ≥ 60 closed trades;
   - net expectancy > 0;
   - month-block bootstrap CI95 low > 0;
   - still > 0 after an extra +0.10 R cost;
   - at least 60% of quarters (with n ≥ 5) positive;
   - better than the no-context control (adjusted delta and ≥ 60% of strata);
   - no direction below −0.10 R;
   - no UTC hour above 35% of entries.

   The rule says STOP below 30 trades or when the CI is entirely below 0, and INVESTIGATE otherwise.
2. BL-01 declares one primary hypothesis. The five ALT/NULL hypotheses were generated afterwards, are untested proposals, and are not part of its multiple-testing family. Its effective two-sided alpha is 0.05.
3. 80 was a count of H4 setups, not of trades (see §2).
4. Costs and within-month dependence change the variance and the mean (see §3).

## 2. H4 frequency (2019–2022) versus BL-01 trades

Measured again with the Behavior Lab detectors (PR #39, commit 613a9a8, frozen parameters) on MARKET_STATE_V1 H4 bars, 2019-02-03..2022-02-03 (sha 4f4a248d…):

| Quantity | Value |
|---|---|
| H4 bars | 4809 (3.0 years) |
| Impulses | 183 (3.81% of bars) |
| Pullbacks ≥ 38.2% | 167, impulse→pullback conversion 0.913 |
| Pullbacks per year | 55.65 (2019: 60, 2020: 58, 2021: 45) |
| Monthly dispersion (variance/mean) | 0.98, close to Poisson |
| Spread / ATR at the pullback | median 0.046, p90 0.076 |

Expected pullbacks in the BL-01 discovery window (1.498 years): **83 (90%: 68–98)**.

A pullback is a setup, not a trade. A closed BL-01 trade additionally needs:

- an M15 micro-break within 16 bars, after at least 2 bars;
- an entry gap of at most 1 h;
- risk between 0.25 and 3 ATR;
- no censoring at the split end.

That pullback→trade conversion has never been measured: it needs M15 data, which is only on the research PC. It is a structural quantity, and BL-01 itself will measure it. Scenarios:

| Conversion | Median trades | P(n ≥ 30): needed to avoid STOP_SAMPLE | P(n ≥ 60): needed for GO |
|---|---|---|---|
| 0.4 | 33 | 0.74 | ≈ 0.00 |
| 0.6 | 50 | 1.00 | 0.09 |
| 0.7 | 58 | 1.00 | 0.43 |
| 0.8 | 67 | 1.00 | 0.81 |

## 3. Power of the BL-01 decision rule

**Outcome model, per closed trade:**

- 15% of trades time out, with R ~ N(0, 0.7) clipped to [−1, 2].
- Otherwise the trade ends at +2R with probability p, or at −1R.
- The round-trip cost is 0.05 R: spread/ATR ≈ 0.046 at a risk of about 1 ATR.
- No edge means p = 1/3, gross mean 0, net mean −0.05 R.

**Dependence:** p shifts by month with SD 0.05 (also tested at 0.10). The month-clustered standard error used in the simulation matches BL-01's month-block bootstrap: width ratio 0.98, CI-low on average 0.017 R lower (slightly conservative).

**Not modelled:** the direction, hour and stratified-cell checks. The GO rates below are therefore upper bounds.

| True lift Δp | Net mean (R) | n for 80% on the CI criterion alone | GO / INVESTIGATE / any STOP at conversion 0.6 | GO / INVESTIGATE / any STOP at conversion 0.8 |
|---|---|---|---|---|
| 0 (no edge) | −0.05 | – | 0.00 / 0.50 / 0.49 | 0.01 / 0.49 / 0.49 |
| +0.04 | +0.05 | 5685 | 0.00 / 0.69 / 0.31 | 0.05 / 0.68 / 0.27 |
| +0.08 | +0.15 | 673 | 0.01 / 0.83 / 0.15 | 0.14 / 0.75 / 0.11 |
| +0.12 | +0.26 | 250 | 0.03 / 0.91 / 0.07 | 0.29 / 0.68 / 0.03 |
| +0.16 | +0.36 | 130 | 0.05 / 0.93 / 0.03 | 0.47 / 0.52 / 0.01 |

(Month SD 0.05; the 0.10 rows are in the report.) The minimum detectable net effect of the CI criterion at 80% power is **0.70 R at 33 trades, 0.57 R at 50, 0.49 R at 67 and 0.44 R at 83**.

**What BL-01 can and cannot say:**

- The false-GO rate is very low (≤ 1–2%): the rule is conservative, and a GO would be meaningful.
- The probability of GO is low for any realistic effect. It is limited first by the n ≥ 60 requirement, then by the CI. INVESTIGATE is the most likely outcome whether or not an edge exists, so INVESTIGATE carries little evidence either way.
- A STOP_NO_ADVANTAGE is about 2.8 times more likely under no edge (0.42) than under Δp = +0.08 (0.15, conversion 0.6). That is a moderate likelihood ratio, not proof of absence.
- **BL-01 does measure useful facts:** the conversion and trade count, timeouts, the cost in R, MFE/MAE, the control comparison, and quarter and direction profiles. These are exactly the inputs BL-02 needs.

## 4. Independent periods and exposure

| Period | Status for this family | Usable for BL-02 |
|---|---|---|
| 2008-01..2018-12 (lookback 2007-10..12) | Not in any exposure record (BREAKOUT_ACC pre-2019 UNVERIFIED; ORDER_BLOCK and LIQ_SWEEP pre-2023 NOT_USED); outside MARKET_STATE_V1 and the Phase 6/7 data | **Yes**, after download and integrity audit on the PC |
| 2004-01..2007-12 | Same, data quality unknown | Only if the audit passes, decided on audit metrics alone |
| 2019-02..2022-02 | MARKET_STATE_V1: Phase 5 reuse, BREAKOUT_ACC economics, BL H4 counts | No (exploratory only) |
| 2022-02..2023-02 | Phase 6 holdout consumed by H006, BL-01 lookback | No |
| 2023-02..2026-09 | BL-01 partitions; locked/final one-shot; neighbour exposures | No (BL-01 only) |
| After 2026-09-17 | Unseen, but about 30–45 trades per year | Forward collection, not a historical window |

## 5. BL-02 (separate experiment, draft not frozen)

- **Same hypothesis, same frozen parameters** (params sha 7c66d51c…). Only the data are new. No generated alternative is included.
- **Endpoint:** net expectancy (R), month-block CI95.
  - SUPPORTED_AT_REPLICATION_LEVEL: CI low > 0 and still > 0 at +0.10 R.
  - EFFECT_BELOW_MINIMUM: CI high < the minimum effect. This is an informative negative.
  - INCONCLUSIVE otherwise.
- **Alpha:** 0.05 two-sided, with a family of 1.
- **Minimum effect proposed now, before any BL-01 run: 0.20 R net.** A person must confirm it. Rationale: below that, a single-instrument setup at about 30–45 trades per year is not worth its unmodelled execution uncertainty.

Sample size (SD 1.40 R, design effect 1.10, 80% power):

| Minimum effect (net R) | Trades | XAUUSD years at conversion 0.4 / 0.6 / 0.8 |
|---|---|---|
| 0.10 | 1693 | 76 / 51 / 38 |
| 0.15 | 753 | 34 / 23 / 17 |
| **0.20** | **424** | **19 / 12.7 / 9.5** |
| 0.25 | 271 | 12 / 8 / 6 |
| 0.30 | 189 | 8.5 / 5.7 / 4.2 |

The 11-year window (2008–2018) reaches a minimum effect of **0.26 / 0.22 / 0.19 R** at conversion 0.4 / 0.6 / 0.8.

**Rule declared now:** the conversion measured by BL-01 (closed trades over pullbacks, no outcome used) sets the expected BL-02 trade count. If that count is below 424, BL-02 is labelled UNDERPOWERED_FOR_0.20R before it runs, and it reports the minimum effect it can reach. The window may extend to 2004 only if the audit passes. The minimum effect is never changed afterwards.

**Gating, also declared now:**

- BL-01 STOP_NEGATIVE closes the hypothesis.
- STOP_DATA_OR_DETECTOR waits for the fix.
- Any other BL-01 decision lets BL-02 proceed, without using BL-01 outcomes.

Effects under about 0.15 R cannot be resolved on XAUUSD H4 alone with any available history. That would need pooling across instruments, which is a different, generalisation hypothesis with its own preregistration, or years of forward data.

## 6. Recorded in Research Memory

| Record | Content |
|---|---|
| `OBS-BL-H4-PULLBACK-FREQUENCY-2019-2022` | Structural rates. Explicitly not evidence for trade counts or outcomes |
| `OBS-BL01-POWER-ANALYSIS-V1` | Loop-v1 replication, P(n ≥ 30/60), MDE, decision-rule distributions, all assumptions. Not evidence of edge, not usable to pick an effect |
| `EXP-BL-01-DISCOVERY.R1` | Supersedes the placeholder: still NOT_RUN, same params sha, adds the power limits and the human decision |
| `PROP-POWER_MODEL_MISMATCH-*` | Method: dry runs must simulate the preregistered decision rule |
| `PROP-PLANNING_ALPHA_FAMILY-*` | Method: planning alpha counts preregistered, planned or run tests, not untested proposals |
| `PROP-BL02_POWERED_REPLICATION-*` | INSUFFICIENT_EVIDENCE → more data and better design (this BL-02 draft) |

New store invariant: a record can be superseded only once (linear history). `cli ingest-bl01` now supersedes the current BL-01 record.

## 7. Decision Card: BL-01 / BL-02

| | |
|---|---|
| **Feasibility of BL-01 (as preregistered)** | Runs as designed. Expected 33–67 trades (83 setups × an unknown conversion). About 26% chance of STOP_SAMPLE if the conversion is 0.4 |
| **Estimated power (GO)** | ≤ 0.14 for a +0.08 lift (net +0.15 R), ≤ 0.47 even for +0.16. False GO ≤ 0.02. CI MDE 0.44–0.70 R net |
| **What BL-01 will reliably give** | Descriptive profile, pullback→trade conversion, cost in R, timeouts, control comparison, preliminary reading, feasibility for BL-02. No confirmatory claim |
| **Limits** | Conversion unknown until it runs; outcome model simplified (direction/hour/cell checks not simulated: GO is an upper bound); Dukascopy, not the broker feed; costs exclude commission and slippage |
| **Alternatives** | (A) BL-02 on unseen 2008–2018, recommended. (B) Extend back to 2004 if audit passes. (C) Forward collection after 2026-09 (slow). (D) Cross-instrument generalisation, a new hypothesis. (E) Stop the family after BL-01 if it STOPs NEGATIVE |
| **Not allowed** | Changing BL-01 parameters or effect; reading locked_validation or final_holdout; promoting on discovery; touching the EA |
| **Recommended next action** | 1) Run BL-01 smoke and discovery as preregistered on the research PC, when access is authorised. 2) Confirm (or change, now) the 0.20 R BL-02 minimum effect. 3) Approve the 2008–2018 download and integrity audit, and register the window as UNSEEN before reading it |
