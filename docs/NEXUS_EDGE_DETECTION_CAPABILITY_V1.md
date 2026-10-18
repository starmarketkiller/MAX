# NEXUS P0 — Edge Detection Capability Test V1

Date: 2026-10-18. Read-only on data and engine. No holdout read, no backtest, no strategy screened, no price or dataset modified.

- Artifacts: `server/research_scripts/edge_detection_capability_v1/` (protocol, runner, results, summary, Decision Card, manifest).
- Frozen protocol: `protocol_v1.json`, sha256 `8dd988251b280e390162c979cf446eb782e3b35371c732f9215bb6624359a698`, frozen before any result was computed.
- Baseline: `main@bad01720d2b15b9ad923fe48cc09a978fe14eb21`.
- Integrity test: `server/tests/test_edge_detection_capability_v1.py`.
- Related: `docs/BL01_POWER_AND_BL02_PROPOSAL.md` (analytic power for BL-01). This test is the empirical, simulation-based counterpart for the Phase 7 edge-validation pipeline; it does not change BL-01/BL-02.

## Question

Can the existing pipeline tell a known synthetic edge from market noise, at the sample sizes NEXUS actually has?

## Design

Known effects were added only to in-memory copies of outcomes; prices and datasets were never changed.

- **Signal layer.** Real GOLD D1 series (Phase 7.27 source). Outcome: 10-bar forward return in ATR14 units. Events drawn at random (uniform, clustered with overlapping windows, or uptrend-only as a beta-only control), each paired with a regime-matched random control exactly as Phase 7.27. Effect δ ∈ {0, 0.1, 0.25, 0.5, 1.0} ATR, n ∈ {12…400}, costs 0 / 0.019 / 0.074 ATR.
- **Trade layer.** Real net-R distributions of BREAKOUT_ACC (n=47) and LIQ_SWEEP (n=42), recentred to zero, plus δR ∈ {0…0.5}, n ∈ {25…800}, costs 0 / 0.02 / 0.08 R.
- **Screening → confirmation.** 67 strategies, 0 or 3 true 0.3R edges, BH q=0.10 screen, independent confirmation.
- **Methods.** M1 = IID percentile bootstrap (as used in 7.21/7.25/7.27); M2 block sign-flip, M3 studentized block bootstrap, M4 HAC Newey-West (all from `phase7/engine`). 400 reps per cell; seeds fixed in the protocol.

## Verdict: PIPELINE_UNDERPOWERED, with a scoped calibration defect in the IID bootstrap

### Calibration (false-positive rate at α=0.05)

| Method | Independent events | Clustered events |
|---|---|---|
| M1 IID bootstrap | 0.03–0.06 at n≥47; 0.08–0.10 at n≤25 | **0.17–0.29**, CI coverage 0.71–0.85 |
| M2 block sign-flip | 0.00–0.05 | 0.03–0.08 (no power at n=12) |
| M3 studentized block bootstrap | 0.00–0.05 | 0.03–0.07 |
| M4 HAC Newey-West | 0.13 at n=12 | 0.22 at n=12 |

Effect estimates are unbiased. The block methods in the engine are calibrated and should be the primary test whenever outcome windows overlap or events cluster.

### Power (80% target)

| Net edge | Trades needed, BREAKOUT-like (sd 2.38R) | Trades needed, LIQ-like (sd 1.44R) |
|---|---|---|
| 0.2R | ~1,100 | ~400 |
| 0.3R | ~500 | ~180 |
| 0.5R | ~180 | ~65 |

- At n=47 (current D1 candidates) power is 12–34% for 0.2–0.3R edges.
- Against the regime-matched benchmark, 0.5 ATR needs ~400 independent events; the 2019–2026 D1 series holds only ~190 non-overlapping 10-day windows.
- Stress costs (0.08R) raise the requirement for 0.3R from ~500 to ~800 trades.

### Winner's curse

At n=47 any significant result estimates ~0.9R whatever the true edge (0 to 0.5R). With 67 strategies and 3 true 0.3R edges, true edges pass screening 1% of the time at n=47 (71% of positives false); at n=200, 5.8% pass both screening and confirmation.

### Alpha vs beta

Regime-matched tests resisted a beta-only selector. The trap is testing mean R against zero, which counts the gold drift (+0.55 ATR per 10 days) as edge.

### Consequence for past verdicts

Phase 7.27 ("none beats the regime-matched benchmark", n=10–39) had power ≤ ~0.2 even for 0.5 ATR edges: its result is uninformative, not evidence that the profits are pure drift. No historical verdict or registry entry is changed by this document.

## Proposed power gate

1. Declare the smallest net edge worth trading, after costs.
2. Required trades: n = DEFF × (2.8 × σ / edge)², σ from the strategy's own outcomes (prior 1.4–2.4R), DEFF = 1 if independent, ≥ 2 if clustered.
3. If the data window cannot reach n: EXPLORATORY_ONLY — no confirmatory claim, no promotion.
4. Dependence-aware tests (M2/M3) are primary when windows overlap; M1 only with demonstrated independence and n ≥ 47.
5. Size confirmations on a shrunken screening estimate (at least halved at n ≤ 200).

This is a proposal; adopting it is a separate human decision.

## Reproduction

```
pip install -r server/requirements-dev.txt   # numpy, pandas, scipy==1.18.1
python3 server/research_scripts/edge_detection_capability_v1/run_edgetest.py \
  . server/research_scripts/edge_detection_capability_v1/protocol_v1.json /tmp/results_repro.json
```

About 15 minutes on 4 cores. The manifest records the environment and the result of an independent re-run.
