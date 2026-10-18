# NEXUS Power Gate V1 (rules V1.1)

Date: 2026-10-18. Pre-experiment power assessment for trading experiments. No backtest, no screening, no holdout, no market data read.

- Module: `server/research_scripts/research_intelligence_v1/power_gate.py` (`assess(plan) -> Power Decision Card`).
- Tests: `server/tests/test_power_gate_v1.py`, with two synthetic fixtures in `server/tests/fixtures/power_gate/`.
- Calibration source: `server/research_scripts/edge_detection_capability_v1/results_v1.json` (PR #59, verdict `PIPELINE_UNDERPOWERED`), read only.
- V1.1 addresses the Codex review of PR #60 (1 P0, 5 P1, confirmatory multiplicity); see the table at the end.

## Principle

**Only a simulated PR #59 cell can certify power.** A plan is `POWER_READY` only when a PR #59 cell dominates it and reached the target power. Dominating means all of the following:
- same estimand, benchmark, number of controls, inference method and dependence model;
- simulated n ≤ the plan's n;
- simulated effect ≤ the plan's effect;
- simulated dispersion ≥ the plan's;
- simulated alpha ≤ the plan's alpha per test.

Analytic numbers from `power.py` are reported as indicative only. In the PR #59 cells they overstate block-method power by up to 0.275.

Anything PR #59 did not simulate is `NOT_ASSESSABLE` (`POWER_NOT_CALIBRATED_FOR_DESIGN`), never extrapolated.

`POWER_READY` means "ready for protocol review". It is not `EDGE_VALIDATED` and authorizes nothing. For screening, the evidence ceiling stays `DISCOVERY_ONLY`.

## What PR #59 calibrates today

| Design | Calibrated? |
|---|---|
| Paired difference in ATR vs **one** regime-matched control, 10-bar outcome, no control reuse, α = 0.05 per test; independent events, or the PR #59 cluster model (4 events, 2 bars apart) | **Yes**: power by dominance, type I by method |
| Paired difference in **R** (any benchmark) | No: PR #59 simulated R only against zero, which the gate blocks |
| Random-timestamp benchmark, > 1 control per event, control reuse | No |
| α per test < 0.05 (screening families, Bonferroni/Holm confirmation families) | No: PR #59 recorded rejections at 0.05 only |
| Plan-specific dependence (measured or simulated design effect) | Hash-verified, but not certified |
| Winner's curse | Only R units, family 67, BH q=0.10, screening n = 47 or 200 |

So in practice the gate can certify, for example, a confirmation in ATR units with a net effect ≥ 1.0 ATR and ≥ 200 independent events, using the studentized block bootstrap. The dominating cell has power 0.97. Every R-unit plan is currently `NOT_ASSESSABLE` until a calibration study for that estimand exists.

## Plan inputs (all required; missing, non-finite or incoherent → `NOT_ASSESSABLE`)

- `purpose`: SCREENING / CONFIRMATION.
- `effect.economic_min_net_effect` (> 0), `effect.unit` (R / ATR). Optional `effect.screening`: {estimate, n, family_size, selection_rule}.
- `dispersion`:
  - `estimand` = `PAIRED_DIFFERENCE_VS_BENCHMARK`;
  - `sigma_paired_difference` (> 0, the SD of the matched differences, not of raw outcomes);
  - `unit`; `source` (OBSERVED / PRIOR);
  - `controls_per_event` (int ≥ 1); `control_reuse` (bool).
- `frequency`: events_per_year × window_years; the expected n must be ≥ 1.
- `dependence`: `structure` (INDEPENDENT / CLUSTERED / OVERLAPPING), `horizon_bars`, `min_spacing_bars`. Non-independent plans also need `design_effect` + `design_effect_basis`.
- `costs`: base ≤ stress, `unit` equal to the effect unit.
- `benchmark`, `inference_method`.
- `datasets`: registry id, or explicit `exposure: EXPOSED`, or a verifiable `provenance` block.
- `family_size` (screening) or `confirmation_family` (confirmation).
- `alpha` in (0, 0.5], default 0.05; `power_target` in [0.5, 0.99], default 0.8.

## Rules

1. **Dataset provenance (P0).** A caller's "unseen" declaration is not accepted. A dataset counts as unseen only if one of these holds:
   - its Phase 7.26 registry record has every exposure flag false;
   - its `provenance` block points to a repo-relative manifest whose SHA-256 matches, with `declared_at < data_start ≤ data_end` and `declared_before_collection: true`.

   The gate never opens data. Manifest paths under `data_cache/`, `raw_data/`, anything containing `holdout`, data file extensions and absolute paths are refused, as are files over 1 MB. Unverifiable → `NOT_ASSESSABLE`. A confirmation on exposed data → `DATA_REQUIRED`. A protected split → `METHOD_BLOCKED` (checked with `gates.assert_no_automatic_protected_access`, without reading anything).
2. **Estimand and benchmark (P1).** Power refers to the paired difference vs the benchmark: σ must be the SD of the matched differences. Control reuse is not modelled → `METHOD_BLOCKED`. A missing benchmark, a zero benchmark, or an unconditional benchmark for confirmation → `METHOD_BLOCKED`.
3. **Design effect (P1).** There is no universal minimum. `INDEPENDENT` is rejected when `min_spacing_bars < horizon_bars`. Non-independent plans need one of two bases:
   - `PR59_CLUSTER_MODEL_MATCH` (same cluster geometry as PR #59): uses the simulated clustered cells;
   - `MEASURED_ON_PLAN_DATA` / `SIMULATED_FOR_PLAN` with a hash-verified source file: accepted, but `NOT_ASSESSABLE` until simulated.

   Anything else → `NOT_ASSESSABLE` (`DESIGN_EFFECT_UNJUSTIFIED`).
4. **Calibration scope (P1).** The analytic-minus-simulated maxima (0.034 for R vs zero; up to 0.275 for paired block methods) are reported as empirical maxima over the studied cells. They are not bounds and never certify anything.
5. **Winner's curse and MDE (P1).** A screening estimate requires `n`, `family_size` and `selection_rule`. The PR #59 inflation factor applies only to the exact configuration it was measured on; any other configuration → `NOT_ASSESSABLE`. The card reports three separate quantities:
   - the economic minimum;
   - the selection-corrected effect;
   - the indicative MDE of the screening estimate.

   Sizing uses the smaller of economic minimum and corrected effect, minus the stress costs.
6. **Inputs and domains (P1).** NaN, ±∞, booleans, out-of-domain alpha, power target, effect, σ or costs, an expected n below 1, incoherent units and missing fields all give `NOT_ASSESSABLE`, without exceptions. Below the method minimum n (≥ 30): `DATA_REQUIRED` (confirmation) or `EXPLORATORY_ONLY` (screening). Above the simulated range (400 events), power is argued only by dominance of a smaller simulated sample, with a warning. σ larger than any simulated cell gives no dominating cell, hence not ready.
7. **Confirmatory multiplicity.** A confirmation needs `confirmation_family`: {size, alpha_allocation (BONFERRONI / HOLM / FIXED_SEQUENCE), preregistration_path + sha256 (verified)}.
   - Bonferroni/Holm test at α / size.
   - In a fixed sequence, only position 1 is assessable; later positions depend on the earlier tests.

   No candidate gets full alpha by default.

## Power Decision Card — published case

BREAKOUT_ACC confirmation in R units: paired-difference σ 2.38R, 6.7 trades/year over 7.3 years, 0.3R minimum, stress +0.08R, regime-matched benchmark, studentized block bootstrap, on the Phase 7.21 discovery dataset.

| Field | Value |
|---|---|
| Status | **DATA_REQUIRED** |
| Reason | CONFIRMATION_ON_EXPOSED_DATA |
| Effect used | 0.22R |
| n expected | 49 |
| Indicative analytic n required / MDE | 919 / 0.95R (not certifying) |
| Evidence ceiling | EXPLORATORY |

With new, verified data the same plan would be `NOT_ASSESSABLE`, because R-unit paired designs are not calibrated.

## Remaining scientific limits

- Certification covers a single design, one instrument (GOLD D1, 2019–2026) and the distributions PR #59 drew. Dominance assumes the plan's paired differences behave like the simulated ones apart from σ.
- The fixed-sequence assessment covers only the first test. Holm is planned at its most stringent step.
- A wrong σ declared by the plan cannot be detected. A prior σ is flagged.
- A provenance manifest proves that the declaration came before collection and that the content hash matches. It cannot prove the data were never looked at by other means.

## Next step (proposal, not authorized here)

The 21-strategy screening proposed in V1 is now `NOT_ASSESSABLE`: R units, and α per test of 0.0024 is below the simulated 0.05. Making R-unit plans assessable needs a **PR #59-style calibration study** of R-unit paired differences. It would cover:
- k controls per event and control reuse;
- α per test down to 0.05/21;
- a BH family of 21 with its winner's-curse factors.

It would use synthetic data only and follow the same protocol rules. This needs its own authorization.

## Codex findings → changes → tests

| Finding | Change | Regression tests |
|---|---|---|
| P0 provenance | Registry or hash-verified manifest only; refused data/holdout paths; dates and `declared_before_collection` | `test_p0_*` (V1 fixture no longer ready, 7 unverifiable variants, exposed → DATA_REQUIRED, protected split) |
| P1 estimand / benchmark variance | Paired-difference σ required; certification only on the simulated design; control reuse blocked | `test_p1_raw_outcome_sigma_*`, `test_p1_uncalibrated_designs_*`, `test_p1_control_reuse_blocks`, `test_p1_missing_or_inadequate_benchmark` |
| P1 design effect | No universal floor; geometry check; PR #59 model match or verified plan source | `test_p1_clustered_without_*`, `test_p1_pr59_cluster_model_*`, `test_p1_plan_specific_deff_*`, `test_p1_independence_contradicted_*`, `test_p1_iid_bootstrap_*` |
| P1 calibration margin | Analytic numbers indicative only; dominance by simulated cells | `test_p1_analytic_power_does_not_certify`, `test_ready_only_by_a_dominating_simulated_cell` |
| P1 winner's curse / MDE | n, family and rule required; no transfer across families; three effects reported | `test_p1_screening_estimate_*`, `test_p1_curse_factor_not_transferred_*`, `test_p1_three_effects_*` |
| P1 inputs / domains | Finite-number and domain checks, unit coherence, n < 1, n < 25, n > 400, σ outside the simulated cells | `test_p1_invalid_inputs_*` (25 cases), `test_p1_not_a_mapping`, `test_p1_small_sample_*`, `test_p1_large_sample_*`, `test_p1_dispersion_above_*` |
| Confirmatory multiplicity | Preregistered, hash-verified family; α split; fixed sequence position 1 only | `test_conf_*` |
