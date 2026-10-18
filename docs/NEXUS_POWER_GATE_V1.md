# NEXUS Power Gate V1 (rules V1.4)

Date: 2026-10-18. Pre-experiment power assessment for trading experiments. No backtest, no screening, no holdout, no market data read.

- Module: `server/research_scripts/research_intelligence_v1/power_gate.py`.
  - Production interface: `assess(plan)`, which takes **no** calibration or registry argument.
  - Isolated logic tests: `assess_test_only(plan, cal=..., registry=...)`. Its cards are marked `test_only: true`, carry a status prefixed `TEST_ONLY:`, are never authorizing, and can never read `POWER_READY`.
- Tests: `server/tests/test_power_gate_v1.py`, with two synthetic fixtures in `server/tests/fixtures/power_gate/`.
- Calibration source: `server/research_scripts/edge_detection_capability_v1/results_v1.json` (PR #59, verdict `PIPELINE_UNDERPOWERED`), read only.
- V1.1 addresses the first Codex review of PR #60 (1 P0, 5 P1, confirmatory multiplicity). V1.2 addresses the second review (base `6a42669`: provenance P0, preregistration, calibrated range, statistical uncertainty). V1.3 addresses the third review (base `6d49b6a`: exact alpha/procedure, pre-registered level calibration, Windows-safe integrity). V1.4 closes the fourth review (base `5bb7303`: protocol provenance, synthetic-calibration override, CRLF test). All tables are at the end.

## Principle

**Only a simulated PR #59 cell, read with its Monte Carlo uncertainty, can certify power.** A plan is `POWER_READY` only when four conditions hold:

1. **Inside the qualified box.** The plan matches the simulated design (estimand, benchmark, number of controls, method, dependence model, and **exactly** the simulated test procedure: α per test = 0.05, two-sided). Its n, effect and paired-difference σ also lie inside the simulated ranges for that dependence model. For independent events: n 12–400, effect 0.1–1.0 ATR, σ 3.10–3.33 ATR.
2. **Pre-registered level qualification.** The calibration study must carry a level criterion frozen before its results. It must state:
   - `criterion` = `WILSON_UPPER_BOUND_LE_NOMINAL`;
   - `multiplicity` = `BONFERRONI_OVER_CELLS`;
   - `nominal_alpha` = 0.05, a declared confidence and a minimum number of replications per cell.

   Every simulated null cell from the method's minimum n up to the plan's n must then have its Bonferroni-adjusted Wilson **upper** bound ≤ 0.05. Neither "the interval contains 0.05" nor the 0.075 band counts as evidence of calibration.
3. **Power with uncertainty.** A dominating cell exists: cell n and effect ≤ plan, cell σ ≥ plan. Its **one-sided 95% Wilson lower bound** on power must reach the target; a point estimate above 0.80 is not enough. The card reports the point power, its Monte Carlo standard error and the lower bound.
4. **Verified independent data**, for confirmations (see rule 1 below).

Anything outside the box is `NOT_ASSESSABLE`, and the card lists the evidence that would be needed (`evidence_needed`). Analytic numbers from `power.py` are indicative only.

`POWER_READY` means "ready for protocol review". It is not `EDGE_VALIDATED` and authorizes nothing. For screening, the evidence ceiling stays `DISCOVERY_ONLY`.

## What can still be POWER_READY

**Nothing, with the current evidence.** PR #59 froze only a point-estimate band for type I, [0.025, 0.075] (`protocol_v1.json`, `success_criteria.calibration`). It has no pre-registered level qualification, so the gate returns `NOT_ASSESSABLE` (`LEVEL_CALIBRATION_NOT_PREREGISTERED`) for every plan that reaches the level stage. Writing such a criterion now, after seeing the results, would be a retroactive tolerance.

The production path never reads a level qualification from any file and ignores one carried by a calibration object. A future qualification would have to be bound to an independent, identifiable protocol whose freezing before the results is demonstrable. That is not implemented now: there is nothing to verify, and adding it would be a speculative path to `POWER_READY`.

For reference only: applied to the 400-replication counts, the strict criterion fails anyway (`test_r3_pr59_replications_fail_even_a_preregistered_criterion`). For example, 19/400 = 0.0475 gives Wilson 95% [0.0306, 0.0730], and 12/400 = 0.03 has an upper bound above 0.05 after Bonferroni.

**Evidence needed:** an independent level-calibration study whose protocol is frozen before results. It needs the criterion above, a confidence level, Bonferroni over the cells used, and enough replications per cell for the bound to be reachable (e.g. ≥ 2,000; 4,000 in the test fixture). Once such a study exists, the design that could become ready is the independent-events paired ATR difference vs one regime-matched control, two-sided α 0.05, inside the simulated n / effect / σ box, with a method whose null cells pass. The tests exercise this path with a **hypothetical** qualified calibration (`QCAL`), only through `assess_test_only`. Those cards read `TEST_ONLY:…` and cannot be promoted.

Confirmations also need a dataset that the canonical registry shows as never touched. None exists today.

## What PR #59 does not calibrate (→ NOT_ASSESSABLE) and the evidence needed

| Design | Evidence needed |
|---|---|
| Paired difference in **R** (any benchmark) | PR #59-style synthetic study of the paired difference in R with the chosen benchmark |
| Random-timestamp benchmark; > 1 control per event; control reuse | Synthetic study with that matched-control construction |
| α per test ≠ 0.05 (e.g. 0.10; screening families; Bonferroni/Holm families) or one-sided tests | Simulated rejection counts at exactly that α and sidedness |
| Level qualification (all designs) | Independent calibration study with a pre-registered Wilson-upper-bound criterion, Bonferroni over cells, sufficient replications |
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

## Integrity: which bytes are hashed

`artifact_sha256` (stdlib only, no external process) hashes **Git's canonical blob representation**, not the physical checkout:
- text files with CRLF turned into LF, which is the content Git's clean conversion stores (`GIT_CANONICAL_EOL_NORMALIZED`);
- files marked `binary` / `-text` in `.gitattributes`, hashed as is (`GIT_CANONICAL_BINARY_AS_IS`), e.g. the frozen CRLF datasets.

A Windows checkout with `core.autocrlf=true` and a Linux checkout of the same blob therefore attest the same hash. Outside a repository the representation is `PHYSICAL_BYTES_NO_GIT_REPO`, which the gate does not accept for versioned artifacts. A text blob that really contains CRLF would mismatch and fail closed.

The calibration source is accepted (`source_integrity: VERIFIED`) only when all of the following hold:
- the canonical hashes of `results_v1.json` **and** `protocol_v1.json` equal the PR #59 identities pinned in code (`PR59_RESULTS_SHA256`, `PR59_PROTOCOL_SHA256`);
- the manifest records the same two hashes;
- the results name the same protocol.

A substitute file or an edited manifest therefore fails (`FAILED:RESULTS_IDENTITY` / `FAILED:PROTOCOL_IDENTITY`). The PR #59 integrity test uses the same function. No frozen file was modified.

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

## Third Codex review (base 6d49b6a) → changes → tests

| Finding | Reproduced on 6d49b6a | Change | Regression tests |
|---|---|---|---|
| Alpha | `POWER_READY` with α=0.10, family of one | α per test must equal the simulated 0.05 exactly, and the test must be two-sided, as simulated. Anything else → `NOT_ASSESSABLE` with `evidence_needed`. | `test_r3_alpha_010_family_of_one_is_not_ready`, `test_r3_alpha_005_family_of_one_reaches_level_stage`, `test_r3_multiplicity_corrected_alpha_is_not_simulated` (families 3 and 21), `test_r3_test_sidedness_must_match` |
| Type I error | M3 19/400 = 0.0475, Wilson [0.0306, 0.0730] accepted by "interval contains 0.05" | Rule removed. A pre-registered level qualification is required (Wilson upper bound ≤ nominal, Bonferroni over cells, min replications, frozen before results). PR #59 has none → `NOT_ASSESSABLE`. | `test_r3_contains_005_rule_is_gone`, `test_r3_real_pr59_calibration_cannot_qualify_the_level`, `test_r3_pr59_replications_fail_even_a_preregistered_criterion`, `test_r3_invalid_level_qualification_is_not_assessable` (6 cases), `test_r3_cells_below_min_reps_fail` |
| SHA-256 on Windows | Physical-byte hashing breaks on a CRLF checkout | Canonical Git-blob representation (CRLF→LF for text, as-is for binary attributes), stdlib only. Calibration integrity is checked against the PR #59 manifest. The PR #59 integrity test uses the same function. | `test_r3_pr59_artifact_hash_is_the_git_blob_hash`, `test_r3_crlf_checkout_keeps_the_canonical_hash` (real git, `eol=crlf`), `test_r3_windows_crlf_copy_of_frozen_results_keeps_recorded_hash`, `test_r3_binary_attributed_files_*`, `test_r3_no_repository_*`, `test_r3_calibration_integrity_failure_is_not_assessable` |

## Fourth Codex review (base 5bb7303) → changes → tests

| Finding | Reproduced on 5bb7303 | Change | Regression tests |
|---|---|---|---|
| Protocol provenance | A substitute `protocol_v1.json` carrying a level qualification was read unchecked (integrity still `VERIFIED`) | Results and protocol identities pinned in code and cross-checked against the manifest and `results.meta`. No level qualification is read from files; production ignores any. | `test_r4_calibration_pins_*`, `test_r4_substitute_protocol_*`, `test_r4_edited_manifest_*` |
| QCAL override | `assess(READY, cal=QCAL)` → `POWER_READY`, `VERIFIED` | `assess(plan)` takes no override. Synthetic runs go only through `assess_test_only`, whose cards are `TEST_ONLY:`, non-authorizing and never `POWER_READY`. No other call site exists outside the tests. | `test_r4_production_interface_has_no_override`, `test_r4_qcal_only_yields_test_only_cards`, `test_r4_production_never_uses_a_level_qualification`, `test_r4_production_status_vocabulary_*` |
| CRLF test | The test assumed LF physical bytes, so it failed on a Windows checkout | The LF fixture is derived from canonical bytes (CRLF→LF) and checked against the pinned hash. LF, CRLF, modified and binary cases are covered. No PR #59 artifact changed. | `test_r4_frozen_results_copy_*` (LF, CRLF), `test_r4_modified_frozen_results_copy_fails`, `test_r4_binary_frozen_artifact_*` |
