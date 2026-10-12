# BL-01 discovery on real XAUUSD ticks: results

Date: 2026-10-12. Hypothesis `BL-H4M15-IPC-001`, preregistration unchanged (params_sha256 `7c66d51c…35c9`). The run was exploratory, on the discovery split only. **Nothing here confirms an edge, and nothing here authorizes trading.**

- Run on the research PC: `DESKTOP-JNFS6CC`, run_id `BL-H4M15-IPC-001_discovery_20261012T083523Z`.
- Code: commit `87f7f10` (branch `claude/xau-behavior-lab-h4m15`; its two fixes are on main through PR #44).
- Outputs stay on the PC: `C:\Users\User\ClaudeWork\MAX-bl01\server\research_scripts\behavior_lab_v1\data\bl01\20261012T083336Z\`.
- In the repo: `server/research_scripts/behavior_lab_v1/results/BL-01_discovery_20261012T083523Z/`.
  - `summary.transcribed.json` is a declared transcription (see §7).
  - `report.transcribed.md` is the runner's report, unchanged.
- Research Memory: `EXP-BL-H4M15-IPC-001_DISCOVERY_20261012T083523Z` (run) and `.A1` (analysis), plus the records in §8.

## 1. Environment (verified with commands on the PC, not assumed)

| Item | Value |
|---|---|
| Machine | Windows 11 Pro 10.0.26100, 4 logical CPUs, 19.85 GB RAM (9.78 GB free), 230.9 GB free on C: |
| Python | 3.12.10; numpy 2.5.3, pandas 3.0.5, scipy 1.18.1, tzdata 2025.2 |
| Repo | separate git worktree `MAX-bl01` at `87f7f10`, clean. The other session's EA work in `MAX` (`fix/trading-ea-telemetry-wiring`) was not touched. |
| Data | `phase7/data_cache_new_period/decoded` (1.7 GB) and `phase6/data_cache_holdout` (614 MB, warmup lookback only), reached through junctions. Nothing was downloaded. |
| MT5 | installed (`C:\Program Files\MetaTrader 5`, `C:\MT5-Terminal3`, `C:\MT5-Tester`). Not started, no account touched. |

## 2. Data checks (all gates passed)

| Check | Smoke (10 days) | Discovery |
|---|---|---|
| Tick manifest (content hash) | MATCH `605249c6…` | MATCH |
| Days present | – | 547/547; warmup 92/92; 0 missing day files |
| Tick audit | PASS_WITH_NOTES, 11,728,159 ticks | PASS_WITH_NOTES, 72,159,303 ticks |
| Crossed / non-positive / non-monotonic / duplicate ticks | 0 | 0 |
| Ticks above the spread cap | 55 | 325 (mean spread 0.356) |
| H4/M15 alignment mismatches | 0 | 0 |
| H4 bars vs Phase 7.1 reference | 0 differences | 0 differences |
| M15 gaps (weekend / pause / other) | 15 / 53 / 2 | 89 / 345 / 16 |
| Detector firing (IMPULSE / PULLBACK) | NORMAL | 4.47% / 3.97% NORMAL (107 / 95 of 2394 bars) |

The runner first stopped on two defects, both fixed before the valid run:

1. The tick-manifest check compared the raw file sha (`7c4a0ff6…`) with the registry's canonical content hash (`605249c6…`). Fixed in `bdb6e74`.
2. The firing rate counted warmup detections against split bars only. Fixed in `87f7f10`.

Both fixes have regression tests, are in PR #44, and changed no parameter.

Timing: smoke 106 s; discovery 713 s, of which 712 s read ticks and built bars. Peak memory was not recorded on Windows (`PROP-WINDOWS_PEAK_RSS`).

## 3. From H4 setups to trades

| Stage | Count |
|---|---|
| H4 bars in the split | 2394 |
| Impulses | 107 |
| Pullbacks (setups) | 95 |
| M15 confirmed, closed trades | 49 |
| Unconfirmed / anchor broken / risk out of bounds | 36 / 4 / 6 |

Setup-to-trade conversion was **0.516**. The power study (`OBS-BL01-POWER-ANALYSIS-V1`) predicted:

- 83 pullbacks, with a 90% range of 68–98. The run saw 95.
- At conversion 0.6, P(n ≥ 60) = 0.093.
- A minimum detectable net effect of 0.568 R at 50 trades.

INVESTIGATE was the expected outcome: the sample was always going to be too small for the CI criterion unless the effect was very large.

## 4. Results (net of Dukascopy spread)

| | Events H4→M15 | Control (same M15 rule, no H4 context) |
|---|---|---|
| Closed trades | 49 | 1803 |
| P(+2R before −1R), Wilson 95% | 34.7% [22.9, 48.7] | 23.6% [21.7, 25.6] |
| Net expectancy | **+0.262 R** | −0.045 R |
| Month-block bootstrap CI95 | **[−0.061, +0.528] R** (16 blocks) | [−0.134, +0.037] R (19 blocks) |
| Expectancy before spread | +0.316 R | +0.017 R |
| Profit factor | 1.555 | 0.924 |
| Median MFE / MAE | 0.876 / 0.812 R | 0.758 / 1.024 R |

- **Gross breakeven win rate:** 33.3% (+2R / −1R).
- **Stratified comparison** (direction × session × ATR tercile, 25 usable cells, every event covered):
  - P(+2R) delta +0.092; expectancy delta +0.269 R.
  - Events beat controls in **13/25 cells**. 13 of the 25 cells hold a single event and 21 hold at most two.
- **Cost stress:** still +0.162 R with 0.10 R extra cost per trade.

Stability (n, P(+2R), net R):

| Quarter | n | P | R |
|---|---|---|---|
| 2023Q1 | 4 | 25.0% | −0.046 |
| 2023Q2 | 6 | 33.3% | +0.498 |
| 2023Q3 | 7 | 28.6% | −0.143 |
| 2023Q4 | 11 | 45.5% | +0.543 |
| 2024Q1 | 7 | 14.3% | −0.325 |
| 2024Q2 | 9 | 44.4% | +0.578 |
| 2024Q3 | 5 | 40.0% | +0.426 |

- **Quarters:** positive in 4/6 quarters with n ≥ 5 (control: 2/7).
- **Direction:** BUY n=29, 41.4%, +0.448 R; SELL n=20, 25.0%, −0.008 R.
- **Session:**
  - TOKYO 18, +0.524
  - NEW_YORK 8, +0.427
  - LONDON 7, +0.286
  - OFF 9, −0.040
  - LONDON_NY_OVERLAP 7, −0.236
- **Hour concentration:** largest UTC hour share 14.3% (limit 35%).

## 5. Decision (BL01_DECISION_RULES_V1): **INVESTIGATE**

| Check | Outcome |
|---|---|
| n_closed ≥ 60 | ✗ (49) |
| net expectancy > 0 | ✓ |
| month-block CI95 low > 0 | ✗ (−0.061) |
| adjusted delta vs control > 0 | ✓ (+0.269 R) |
| event better than control in ≥ 60% of usable cells | ✗ (52%) |
| positive in ≥ 60% of quarters with n ≥ 5 | ✓ (4/6) |
| still > 0 with +0.10 R extra cost | ✓ |
| no direction below −0.1 R with n ≥ 20 | ✓ |
| no UTC hour above 35% of entries | ✓ |

Alternative explanations still open (recorded in `.A1`):

- Sampling noise.
- Gold's 2023–2024 uptrend: BUY carries the result.
- Thin strata.
- TOKYO concentration.
- Different filter survival: 51.6% of event setups close as trades against 39.2% of controls.
- Spread-only costs.

## 6. MT5 and Strategy Tester

MT5 is installed on the PC. It was **not started**: no tester run, no account, no orders.

- **What it could do later:** run an EA port of the detector on broker data in an isolated tester profile, as a parity check (do the same setups appear on the XM feed, and how do spread and slippage change R?).
- **What it cannot do:** replace this preregistered experiment, read any protected split, or turn INVESTIGATE into GO.
- **What is missing:** such a check needs its own written question first. No EA port of the detector exists.

## 7. Provenance of the numbers in the repo

The PC session's safety policy refused to encode and send whole files, so the original `summary.json` stays on the PC. What the repo holds:

- **Original file hashes.** `summary.json` sha256 `61a5cd9b…78bb` (47,935 bytes), confirmed on the PC against `outputs.sha256.json`. Also `events.csv` `8cea3a1d…`, `controls.csv` `c03e1d30…`, `run.log` `521a858a…`.
- **Exact values.** Named fields printed on the PC with `json.dumps` (run_id, splits, timings, detector health, the full stratified comparison, events/controls estimates and CIs, manifest check, decision and checks). They are listed in `transcription.exact_fields`.
- **Rounded values.** Quarters, direction, session, MFE/MAE and cost stress come from the run's `report.md`, rounded as printed (`report_md.*`).

In memory, the run record cites the original hash as `RUN` provenance and the transcription as a separate `FILE`. Its limits say it is a transcription. `PROP-RUN_ARTIFACT_TRANSFER` asks the person to choose a channel for byte-identical artifacts in future runs.

## 8. Research Intelligence update

Two RI-02 cycles ran in AUTO_SAFE mode, with `--no-approval-channel`, no schedule and no data access.

| Cycle | What happened |
|---|---|
| C0001 | OBSERVE ingested the transcription (`INGEST_AVAILABLE_REPORT`); the run supersedes `EXP-BL-01-DISCOVERY.R1` (kept unchanged). REVIEW raised `CI_CROSSES_ZERO` (INSUFFICIENT_EVIDENCE) and `NO_ALTERNATIVE_EXPLANATIONS` (NEW_HYPOTHESIS). HYPOTHESIZE registered nothing: the BL-H4M15 family has used its 6-hypothesis budget, so ablations went to `over_budget` and alternatives were deduplicated. PRIORITIZE and PLAN produced nothing; EXECUTE ran no action. |
| analysis | `bl01_results_v1.record_results` wrote:<br>• `.A1`: alternative explanations, conclusions, limits.<br>• `OBS-BL01-FEASIBILITY-OBSERVED-V1`.<br>• Three PROPOSED improvements (below). |
| C0002 | REVIEW of `.A1`: no new proposals; `CI_CROSSES_ZERO` linked again. Nothing planned or executed. |

New proposals, all `PROPOSED`, none approved:

- `PROP-H4_CONTEXT_VS_MATCHED_CONTROL`: a new preregistered question with its own hypothesis_id. It needs a family-budget decision first.
- `PROP-RUN_ARTIFACT_TRANSFER`: a reviewed channel for byte-identical run outputs.
- `PROP-WINDOWS_PEAK_RSS`: record peak memory on Windows.
- Existing and still open: `PROP-BL02_POWERED_REPLICATION`, `PROP-POWER_MODEL_MISMATCH`, `PROP-PLANNING_ALPHA_FAMILY`.

Integrity:

- Memory has 124 records; `verify()` reports no problems.
- External checkpoints were written after each cycle and after the analysis.
- Hashes are tested in `server/tests/test_bl01_results_v1.py`.

RI-03 (`server/research_intelligence_read_model.py`) shows:

- Loop `CYCLE_CLOSED`, last cycle C0002.
- Queue `AVAILABLE` with 0 items: every candidate was excluded by budget, and nothing is invented.
- BL-01 as COMPLETED / INCONCLUSIVE / INVESTIGATE.
- The new proposals in the approval centre, with actions disabled.

The adapter fix in this change: `ingest.import_behavior_lab_summary` now reads the runner's month-block CI dict as `[low, high]`. Before, the review's CI check silently skipped real runs. It also accepts a declared transcription and a dataset id.

## 9. Decision Card: BL-01

| | |
|---|---|
| Question | Does an H4 impulse → pullback context change the M15 +2R/−1R outcome of the same entry rule? |
| Data | Dukascopy XAUUSD ticks, discovery split 2023-02-04 → 2024-08-04, manifest MATCH; no protected split read |
| Result | +0.262 R net per trade (CI95 −0.061 to +0.528), n = 49; control −0.045 R, n = 1803 |
| Decision | **INVESTIGATE**: neither GO nor STOP |
| What it means | The sign is favourable and robust to +0.10 R cost, but the sample cannot exclude zero, and the advantage is not consistent across strata. This matches what the power study predicted for ~50 trades. |
| What it does not mean | It is not an edge. It is not a reason to trade, size or change the EA. It is not permission to read internal_validation. |
| Next (needs a person) | (a) Decide the BL-H4M15 budget. (b) Choose between a new preregistered H4-context question and BL-02 on unseen 2008–2018 data, sized on data it has not seen. (c) Pick a channel for byte-identical run outputs. |
| Not done | MT5 / Strategy Tester (not started); internal_validation, locked_validation, final_holdout (not read); any order, deploy or merge |
