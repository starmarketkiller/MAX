# NEXUS Power Gate V1 (rules V1.2)

Date: 2026-10-18. Pre-experiment power assessment for trading experiments. No backtest, no screening, no holdout, no market data read.

- Module: `server/research_scripts/research_intelligence_v1/power_gate.py` (`assess(plan) -> Power Decision Card`).
- Tests: `server/tests/test_power_gate_v1.py`, with two synthetic fixtures in `server/tests/fixtures/power_gate/`.
- Calibration source: `server/research_scripts/edge_detection_capability_v1/results_v1.json` (PR #59, verdict `PIPELINE_UNDERPOWERED`), read only.
- V1.1 addresses the first Codex review of PR #60 (1 P0, 5 P1, confirmatory multiplicity). V1.2 addresses the second review (base `6a42669`: provenance P0, preregistration, calibrated range, statistical uncertainty). Both tables are at the end.

## Principle

**Only a simulated PR #59 cell, read with its Monte Carlo uncertainty, can certify power.** A plan is `POWER_READY` only when four conditions hold:

1. **Inside the qualified box.** The plan matches the simulated design (estimand, benchmark, number of controls, method, dependence model; α per test ≥ the simulated 0.05). Its n, effect and paired-difference σ also lie inside the simulated ranges for that dependence model. For independent events: n 12–400, effect 0.1–1.0 ATR, σ 3.10–3.33 ATR.
2. **Level control.** At every simulated n from the method's minimum up to the plan's n, the two-sided 95% Wilson interval of the null rejection rate (400 replications) reaches the nominal 0.05. The 0.075 ceiling is not used as evidence of calibration at 0.05.
3. **Power with uncertainty.** A dominating cell exists: cell n and effect ≤ plan, cell σ ≥ plan. Its **one-sided 95% Wilson lower bound** on power must reach the target; a point estimate above 0.80 is not enough. The card reports the point power, its Monte Carlo standard error and the lower bound.
4. **Verified independent data**, for confirmations (see rule 1 below).

Anything outside the box is `NOT_ASSESSABLE`, and the card lists the evidence that would be needed (`evidence_needed`). Analytic numbers from `power.py` are indicative only.

`POWER_READY` means "ready for protocol review". It is not `EDGE_VALIDATED` and authorizes nothing. For screening, the evidence ceiling stays `DISCOVERY_ONLY`.

## What can still be POWER_READY

Only **independent events** on the simulated design:
- paired ATR difference vs one regime-matched control, 10-bar outcome, no control reuse, α 0.05 per test;
- σ_d between 3.10 and 3.33 ATR.

| Method | Smallest qualifying cell (n, effect) | Point power | Lower 95% bound |
|---|---|---|---|
| Studentized block bootstrap | 200, 1.0 ATR | 0.970 | 0.953 |
| Block sign-flip | 200, 1.0 ATR | 0.975 | 0.959 |
| HAC Newey-West | 200, 1.0 ATR | 0.990 | 0.978 |
| IID bootstrap (independent, n ≥ 47) | 100, 1.0 ATR; 400, 0.5 ATR | 0.858; 0.863 | 0.826; 0.832 |

**Clustered or overlapping events are never `POWER_READY` today.** In the PR #59 cluster model no method has null rejections compatible with 0.05 at every simulated n. For example, the studentized block bootstrap at n=200 rejects at 0.0725, with a Wilson 95% interval of [0.051, 0.102].

**Confirmations also need a dataset that the canonical registry shows as never touched.** No such record exists in the committed ledger today, so no confirmation is `POWER_READY` until a forward dataset is registered.

## What PR #59 does not calibrate (→ NOT_ASSESSABLE) and the evidence needed

| Design | Evidence needed |
|---|---|
| Paired difference in **R** (any benchmark) | PR #59-style synthetic study of the paired difference in R with the chosen benchmark |
| Random-timestamp benchmark; > 1 control per event; control reuse | Synthetic study with that matched-control construction |
| α per test < 0.05 (screening families; Bonferroni/Holm confirmation families) | Simulated rejection counts at that α |
| n > 400, effect outside 0.1–1.0 ATR, σ outside the simulated range | Simulations at the plan's n / effect / σ |
| Plan-specific dependence (measured or simulated design effect) | Synthetic study reproducing that dependence |
| Clustered events (PR #59 cluster model) | More replications, or a method whose null rejections are compatible with 0.05 at every n |
| Winner's curse outside R / 67 / BH q=0.10 / n 47 or 200 | Screening simulation with the plan's family and selection rule |

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
- `datasets`: registry id with `symbol`, `timeframe`, `date_range` (for unseen data), or explicit `exposure: EXPOSED`. A `provenance` block is refused.
- `protocol_version` (confirmation).
- `family_size` (screening) or `confirmation_family` (confirmation).
- `alpha` in (0, 0.5], default 0.05; `power_target` in [0.5, 0.99], default 0.8.

## Rules

1. **Dataset provenance (P0).** Independence is never self-attested, so no provenance manifest is accepted, not even one with a valid hash and pertinent content. A dataset counts as unseen only if the canonical Phase 7.26 exposure registry (a reviewed, committed ledger) has a record that meets all of these:
   - every exposure flag is explicitly `False`;
   - `holdout_status` is `NOT_USED` (via the registry's own `is_genuinely_untouched`, made stricter: `UNVERIFIED` does not count);
   - the same `symbol`, `timeframe` and `date_range` as declared by the plan.

   A record with all flags false whose status is `NO_EVENTS` was traversed by a run, so it counts as exposed. Anything else → `NOT_ASSESSABLE`. A confirmation on exposed data → `DATA_REQUIRED`. A protected split → `METHOD_BLOCKED`. The gate never opens datasets or holdouts. The repo-file verifier refuses data and holdout paths.
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
6. **Inputs and domains (P1).** NaN, ±∞, booleans, out-of-domain alpha, power target, effect, σ or costs, an expected n below 1, incoherent units and missing fields all give `NOT_ASSESSABLE`, without exceptions. Below the method minimum n (≥ 30): `DATA_REQUIRED` (confirmation) or `EXPLORATORY_ONLY` (screening). n, effect or σ outside the simulated ranges → `NOT_ASSESSABLE` with `evidence_needed` (V1.2; the V1.1 dominance above n=400 was removed).
7. **Confirmatory multiplicity.** A confirmation needs `confirmation_family` (size, alpha_allocation, preregistration path + SHA-256). The plan must also declare `protocol_version`.
   - The preregistration (a small repo JSON) is checked **semantically**: the plan's experiment id is in `experiment_ids`, the list length equals the family size with no duplicates, and `alpha_allocation`, `alpha` and `protocol_version` all match the plan. For a fixed sequence, the plan's position must match its place in `experiment_ids`.
   - A document with a valid hash but incompatible content → `METHOD_BLOCKED`.
   - Bonferroni/Holm test at α / size. In a fixed sequence only position 1 is assessable.

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

- Certification covers a single design, one instrument (GOLD D1, 2019–2026) and the distributions PR #59 drew. Dominance inside the box assumes the plan's paired differences behave like the simulated ones.
- The level check uses each simulated null cell separately (400 replications each). With several cells, at least one incompatible-looking cell can appear by chance, so the check is deliberately conservative. Rejections are counted two-sided, so the power figures include a negligible share of wrong-sign rejections.
- The fixed-sequence assessment covers only the first test. Holm is planned at its most stringent step.
- A wrong σ declared by the plan cannot be detected. A prior σ is flagged.
- The registry is the only proof of independence. Its correctness depends on the review of the code that builds it.

## Next step (proposal, not authorized here)

The 21-strategy screening proposed in V1 is now `NOT_ASSESSABLE`: R units, and α per test of 0.0024 is below the simulated 0.05. Making R-unit plans assessable needs a **PR #59-style calibration study** of R-unit paired differences. It would cover:
- k controls per event and control reuse;
- α per test down to 0.05/21;
- a BH family of 21 with its winner's-curse factors.

It would use synthetic data only and follow the same protocol rules. This needs its own authorization.

## Codex findings → changes → tests

| Finding | Change | Regression tests |
|---|---|---|
| P0 provenance | (V1.1) Registry or hash-verified manifest; superseded in V1.2: registry only | `test_p0_*` (V1 fixture no longer ready, 7 unverifiable variants, exposed → DATA_REQUIRED, protected split) |
| P1 estimand / benchmark variance | Paired-difference σ required; certification only on the simulated design; control reuse blocked | `test_p1_raw_outcome_sigma_*`, `test_p1_uncalibrated_designs_*`, `test_p1_control_reuse_blocks`, `test_p1_missing_or_inadequate_benchmark` |
| P1 design effect | No universal floor; geometry check; PR #59 model match or verified plan source | `test_p1_clustered_without_*`, `test_p1_pr59_cluster_model_*`, `test_p1_plan_specific_deff_*`, `test_p1_independence_contradicted_*`, `test_p1_iid_bootstrap_*` |
| P1 calibration margin | Analytic numbers indicative only; dominance by simulated cells | `test_p1_analytic_power_does_not_certify`, `test_ready_only_by_a_dominating_simulated_cell` |
| P1 winner's curse / MDE | n, family and rule required; no transfer across families; three effects reported | `test_p1_screening_estimate_*`, `test_p1_curse_factor_not_transferred_*`, `test_p1_three_effects_*` |
| P1 inputs / domains | Finite-number and domain checks, unit coherence, n < 1, n < 25; (V1.2) n, effect, σ outside simulated ranges | `test_p1_invalid_inputs_*` (25 cases), `test_p1_not_a_mapping`, `test_p1_small_sample_*`, `test_r2_p1_effect_and_dispersion_*` |
| Confirmatory multiplicity | Preregistered, hash-verified family; α split; fixed sequence position 1 only | `test_conf_*` |

## Second Codex review (base 6a42669) → changes → tests

| Finding | Reproduced on 6a42669 | Change | Regression tests |
|---|---|---|---|
| P0 unrelated manifest with valid hash | `POWER_READY` | Manifests not accepted; registry record with explicit-False flags, `NOT_USED` status and matching identity only; traversed `NO_EVENTS` window = exposed | `test_r2_p0_*` (unrelated and pertinent manifests, identity mismatches, traversed window, UNVERIFIED / unknown flags), `test_production_registry_has_no_unseen_dataset_today` |
| P1 unrelated preregistration | `POWER_READY` | Semantic check of experiment id, family size, allocation, α, protocol version, sequence position | `test_r2_p1_unrelated_preregistration_*`, `test_r2_p1_preregistration_must_match_the_plan` (6 cases), `test_conf_fixed_sequence_*` |
| P1 dominance beyond n=400 | `POWER_READY` at n=10,000 | Qualified box on n, effect and σ; `evidence_needed` reported | `test_r2_p1_no_promotion_above_simulated_n`, `test_r2_p1_effect_and_dispersion_*` |
| P1 statistical uncertainty | `POWER_READY` on point power 0.8225 with null rejections 0.0725 | Wilson lower bound on power ≥ target; Wilson-based level check at nominal 0.05 for every simulated n in range; MC SE reported | `test_r2_p1_point_power_above_target_is_not_enough`, `test_r2_p1_clustered_level_*`, `test_r2_p1_level_uses_wilson_*` |
