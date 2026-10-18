# NEXUS Power Gate V1

Date: 2026-10-18. Pre-experiment power assessment for trading experiments. No backtest, no screening, no holdout, no market data read.

- Module: `server/research_scripts/research_intelligence_v1/power_gate.py` (`assess(plan) -> Power Decision Card`).
- Tests: `server/tests/test_power_gate_v1.py` (22 tests).
- Calibration source: `server/research_scripts/edge_detection_capability_v1/results_v1.json` (PR #59, verdict `PIPELINE_UNDERPOWERED`), read only.

## Reused architecture (nothing duplicated)

| Need | Existing component |
|---|---|
| n required, MDE, power of the "CI low > 0" criterion | `research_intelligence_v1/power.py` |
| One-shot splits (locked validation, final holdout) | `gates.protected_splits()` / `assert_no_automatic_protected_access` |
| Minimum closed events for any economic reading (30) | `review.MIN_CLOSED_FOR_FIRST_READ` |
| Dataset exposure | `phase7/phase7_26/data_exposure_registry_v1.json` |
| Calibration of power, dependence, inference methods, winner's curse | PR #59 frozen results |
| Canonical hashing | `memory.canonical` / `sha256_text` |

The gate writes nothing: no ResearchMemory append, no registry or strategy state change. A card can later be attached to an `EXPERIMENT_PLAN` by the existing loop.

## Plan inputs (all required; missing → `NOT_ASSESSABLE`)

`purpose` (SCREENING / CONFIRMATION) · `effect` (minimum net effect after base costs, unit R or ATR, source ECONOMIC_MINIMUM / SCREENING_ESTIMATE / PRIOR_LITERATURE) · `dispersion.sigma` (+ OBSERVED or prior) · `frequency` (events per year × window years) · `dependence.structure` (INDEPENDENT / CLUSTERED / OVERLAPPING, optional declared design effect) · `costs` (base, stress) · `benchmark` · `inference_method` · `datasets` (registry id, or explicit UNSEEN_FORWARD / UNSEEN_NEW_SOURCE / EXPOSED) · `family_size` for screening · optional `power_target` (0.8) and `alpha` (0.05).

## Rules, calibrated on PR #59

1. **Benchmark.** Missing benchmark → METHOD_BLOCKED. Testing against zero is also blocked, because it counts the gold drift as edge. An unconditional benchmark is blocked for confirmation.
2. **Inference vs dependence.** The IID bootstrap is blocked under clustered or overlapping outcomes (type I 0.17–0.29 in PR #59). Minimum n per method: block sign-flip 25, HAC 47, studentized block bootstrap 30.
3. **Protected splits** (one-shot) → METHOD_BLOCKED.
4. **Design effect.** For clustered or overlapping outcomes the gate uses the larger of the declared value and the PR #59 empirical value, **2.449** (variance ratio, clustered vs independent).
5. **Costs.** The effect is reduced by the stress − base cost difference.
6. **Winner's curse.** A SCREENING_ESTIMATE is divided by the PR #59 inflation factor for its sample size: ×3.85 at n ≤ 47, ×2.01 up to n = 200, and ×2.01 above as well, since nothing larger was measured.
7. **Analytic margin.** The analytic formula overstates the PR #59 simulated power by at most **0.034**. The gate therefore sizes on a power target of target + 0.034.
8. **Screening alpha.** Screening uses α / family_size (Bonferroni). This is more conservative than the BH procedure actually used for screening.
9. **Classification:**
   - POWER_READY: expected n ≥ n_required and effective n ≥ 30;
   - DATA_REQUIRED: a confirmation that is underpowered or runs on exposed data;
   - EXPLORATORY_ONLY: an underpowered screening, or an effect that does not survive stress costs or shrinkage.

POWER_READY means "ready for protocol review". It is not EDGE_VALIDATED, it authorizes nothing, and the evidence ceiling stays DISCOVERY_ONLY for screening.

## Methodology limits

- The analytic power is a planning estimate, calibrated only inside the PR #59 range (n 25–800, σ 1.44–2.38R, IID trade resampling, one instrument). Outside that range the card warns `OUTSIDE_PR59_CALIBRATED_RANGE`.
- The design effect 2.449 comes from one stylized clustering model (clusters of 4 events, 2 bars apart). Stronger dependence must be declared.
- The winner's-curse factors come from two sample sizes (47, 200) and one true effect (0.3R).
- σ declared as a prior (not OBSERVED) is flagged. The gate cannot detect a wrong σ.
- Bonferroni at the screening stage understates the power of a BH screen. This is a deliberately conservative choice.
- Heavy tails and skew beyond the two PR #59 distributions are not modelled.

## Power Decision Card — published case

BREAKOUT_ACC confirmation: σ 2.38R observed, 6.7 trades/year over 7.3 years, 0.3R minimum, stress +0.08R, regime-matched benchmark, studentized block bootstrap, on the Phase 7.21 discovery dataset:

| Field | Value |
|---|---|
| Status | **DATA_REQUIRED** |
| Reasons | UNDERPOWERED_AT_EXPECTED_N, CONFIRMATION_ON_EXPOSED_DATA |
| Effect used | 0.22R (after stress costs) |
| n expected / required | 48 / 1,006 |
| Power at expected n | 0.09 |
| MDE at expected n | 1.04R |
| Years required at this frequency | 150 |
| Evidence ceiling | EXPLORATORY |

## Proposal: first economically informative screening

The gate was applied to a screening of the 21 strategies that have at least 200 trades in the cost-calibrated rerun:
- family of 21, regime-matched benchmark, studentized block bootstrap, stress +0.08R;
- σ entered as a prior, because per-trade R is not committed for these strategies;
- each row reflects one trade count from the rerun.

| Trades | σ = 1.44R, 0.3R | σ = 1.44R, 0.5R | σ = 2.38R, 0.3R | σ = 2.38R, 0.5R |
|---|---|---|---|---|
| 212 | EXPLORATORY (power 0.21) | **READY** (0.89) | EXPLORATORY (0.05) | EXPLORATORY (0.32) |
| 305 | EXPLORATORY (0.36) | **READY** (0.98) | EXPLORATORY (0.08) | EXPLORATORY (0.52) |
| 460 | EXPLORATORY (0.59) | **READY** (1.00) | EXPLORATORY (0.15) | EXPLORATORY (0.77) |
| 1,316 | **READY** (0.99) | **READY** (1.00) | EXPLORATORY (0.62) | **READY** (1.00) |

What this means: a 21-strategy screening is informative only for net edges of about 0.5R, and only for strategies with low dispersion or several hundred trades. Below that, a positive result would be a hypothesis, not evidence.

Proposed sequence. Each step needs its own authorization; nothing below is authorized by this document.

1. **Collect per-trade R for the 21 strategies.** Use outputs already produced by the cost-calibrated rerun, if they exist on the research PC. This needs no new backtest. Also record the data window of the rerun, which is not stored in the committed artifacts.
2. **Re-run the gate with the observed σ.** Only strategies that are POWER_READY at a pre-declared minimum net effect (proposal: 0.5R) enter the screening. The others stay NOT_ASSESSABLE or EXPLORATORY_ONLY, with their card on record.
3. **Screening rules.** Regime-matched benchmark, studentized block bootstrap, BH at q = 0.10 over the declared family, evidence ceiling DISCOVERY_ONLY.
4. **Confirmation.** Every positive result goes to a new card with purpose CONFIRMATION, effect source SCREENING_ESTIMATE (shrunk), and unseen data only (forward collection or an independent feed). The card must be POWER_READY before any confirmation protocol is drafted.
