# NEXUS P0 — Edge Detection Capability Test — Decision Card

- Protocol: `protocol_v1.json`, sha256 `8dd988251b280e390162c979cf446eb782e3b35371c732f9215bb6624359a698` (frozen before any result)
- Baseline: origin/main@bad0172, read-only worktree. Data: GOLD D1 discovery series (Phase 7.27 source), BREAKOUT_ACC / LIQ_SWEEP real net-R distributions. No holdout, no price/dataset modified, effects injected only into in-memory copies of outcomes.
- Runs: 90 signal cells + 150 trade cells x 400 reps; 4 screening->confirmation configs x 200 families of 67. Raw: `results_v1.json`, table: `summary_v1.txt`.

## VERDICT: PIPELINE_UNDERPOWERED (+ scoped calibration defect in the IID bootstrap)

### Calibration (type I, alpha 0.05)
| Method | Independent events | Clustered events (overlapping windows) |
|---|---|---|
| M1 IID bootstrap (used in 7.21/7.25/7.27) | 0.03-0.06 at n>=47; 0.08-0.10 at n<=25 | **0.17-0.29**, CI coverage 0.71-0.85 |
| M2 block sign-flip (engine) | 0.00-0.05 | 0.03-0.08; zero power at n=12 |
| M3 studentized block bootstrap (engine) | 0.00-0.05 | 0.03-0.07 |
| M4 HAC Newey-West (engine) | 0.13 at n=12, <=0.06 at n>=47 | 0.22 at n=12, <=0.10 at n>=47 |

Estimates are unbiased (|bias| < 0.1 ATR); coverage of M1 is 0.90-0.97 with independent events.

### Power (80% target)
- Trade layer, BREAKOUT-like distribution (sd 2.38R): 0.2R -> ~1,100 trades; 0.3R -> ~500; 0.5R -> ~180. LIQ-like (sd 1.44R): 0.2R -> ~400; 0.3R -> ~180.
- At n=47 (current candidates): power 0.12 (0.2R), 0.12-0.34 (0.3R), 0.27-0.68 (0.5R).
- Signal layer vs regime-matched benchmark (h10, ATR units, drift itself = +0.55 ATR): at n=47 power 0.12-0.21 for 0.5 ATR, 0.41-0.55 for 1.0 ATR. 80% needs ~100 independent events for 1.0 ATR, ~400 for 0.5 ATR. The whole 2019-2026 D1 series contains only ~190 non-overlapping 10-day windows.
- Stress cost 0.08R moves the n for 0.3R from ~500 to ~800.

### Winner's curse
At n=47 a significant result reports ~0.85-0.92R whatever the true edge (0 to 0.5R). Screening 67 strategies with 3 true 0.3R edges: at n=47 true edges pass screening 1% of the time, FDR among positives 71%, inflation 3.8x; at n=200 pass screening 13.5%, pass screen+confirm 5.8%, inflation 2.0x. Under total H0 the BH screen produced a false positive in 3.5-7% of families.

### Alpha vs beta
Regime-matched tests kept type I under a beta-only selector (uptrend bars only). The unconditional benchmark also rejected rarely (0.06-0.12): in this series the drift is spread across regimes. The real beta trap is testing mean R against zero, which counts the full gold drift (+0.55 ATR every 10 days) as edge.

### Implication for past verdicts
Phase 7.27 ("none beats regime-matched benchmark", n=10-39) had power <= ~0.2 even for 0.5 ATR edges: its result is uninformative, not evidence that the profits are pure drift.

## Proposed power gate (for every future strategy/hypothesis)
1. Declare delta_min = smallest net edge worth trading (after costs), in R or ATR.
2. Estimate sigma from the strategy's own outcome distribution (prior if none: 1.4-2.4R per trade).
3. n_req = DEFF x ((1.96 + 0.84) x sigma / delta_min)^2, DEFF = 1 if no overlap/clustering, else >= 2 (clusters of 4 overlapping events gave SE x1.37).
4. Expected n in the available data window < n_req -> EXPLORATORY_ONLY: no confirmatory claim, no promotion, redesign (higher frequency, pooling, forward collection).
5. Primary inference must be dependence-aware (M2/M3) whenever outcome windows overlap or events cluster; M1 only with demonstrated independence and n >= 47.
6. Never size a confirmation on the screening estimate: shrink it (at least halve it at n <= 200) before computing n_req.

## Consequence for the planned screening of the 67 Python strategies
Only 10/67 have >= 400 trades in the cost-calibrated rerun (and of those only Z_SCORE_BREAKOUT has PF > 1); 11 more have 200-399 (incl. SAR 305, MACD 231, FVG_CONT 212). The other 46 (< 200 trades) cannot be screened informatively for edges below ~0.5R. Recommended: screen only the 21 strategies with n >= 200, with M2/M3 inference and BH, as hypothesis generation only.
