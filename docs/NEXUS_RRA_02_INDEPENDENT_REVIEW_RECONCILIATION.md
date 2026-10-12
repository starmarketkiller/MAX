# NEXUS RRA-02 — Independent Review Reconciliation

**Status:** CHECKPOINT_A_ADDENDUM_COMPLETE  
**Repository baseline:** `a61bca3db6d2bc8ef4f477c1bf59eee827527c40`  
**Inputs:** RRA-01 (`c544dc9`), current canonical artifacts, Claude census summary, Grok independent claims.  
**Rule:** neither AI report is authoritative; repository evidence and reproducible tests decide.

## Classification

- **VERIFIED** — directly established by current code or canonical artifact.
- **SUPPORTED** — substantial evidence exists, but a required end-to-end or independent validation is missing.
- **DISPUTED** — claims conflict or overreach the evidence.
- **STALE** — accurate for an older state, superseded on current main.
- **UNKNOWN** — sources do not support a reliable conclusion.

## Reconciliation matrix

| Area | Claude claim | Grok claim | Repository evidence | Status | Contradiction / interpretation | Technical decision | Required test | Priority |
|---|---|---|---|---|---|---|---|---|
| Max Total DD | Historical 22.83% equity DD with zero trigger; protection unresolved | A wired gate is not proof of a working protection | The historical FVG run used Research Mode and the canonical preset has `InpResearchUseTotalDD=false`, so zero triggers were expected. Separately, current code omits `g_maxDDHit` from `NXS_Prot_EntryBlocked`, clears `g_pausedUntilNextOpen` at daily rollover, and does not persist `g_maxDDHit`/`g_maxDDPeakEquity` in state schema 5 | **VERIFIED** | The historical test is invalid as proof of a calculation failure; two independent live-state bugs remain real | Do not change the formula based on the 22.83% report. Fix latch enforcement and persistence in a dedicated Safety PR after deposit/withdrawal baseline policy is frozen | Deterministic trigger, rollover, restart, corrupt snapshot, manual reset, multi-position and tester-parity cases; isolated MetaEditor compile | **CRITICAL** |
| RiskShield common path | Common preflight protects every opening path | RiskShield must be tested separately from Max DD | `NXS_CommonExposurePreflight` calls protection and RiskShield gates, but PR #36 found `NXS_DoBuy/NXS_DoSell` callers that could bypass the common preflight; the PR adds a final account-mode guard there | **SUPPORTED** | Wiring is present for known routes, but completeness is not proven by the central function alone | Build an opening-call graph and assert every `OrderSend`/opening helper is guarded; do not conflate RiskShield correctness with Max-DD correctness | Static call-graph contract plus isolated negative opening tests for primary, grid, pyramid, institutional, data-collection and re-entry routes | **CRITICAL** |
| Cross-engine parity | No detector is fully READY; Python/MT5 differences documented for MACD, ADX_RSI, SAR, RSI_DIV and stateful structures | 0 EXACT / 32 APPROXIMATE / 6 PROXY / 45 NOT_IMPLEMENTED | `contracts/strategy-registry.json` on main contains exactly 83 entries with those counts and no `EXACT` entry | **VERIFIED** | The counts describe registry declarations, not event-level proof. `APPROXIMATE` must not be read as measured mismatch | Preserve current statuses until a golden trace proves exact event parity. First candidates: MACD indicator/crossover, BREAKOUT_ACC bar-close event, and SAR closed-bar event. ORDER_BLOCK remains a fidelity study with MT5 as event ground truth, not an easy exact-parity candidate | Same bars/feed/timezone, causal timestamp, parameter freeze; compare indicator values, event timestamps/direction, filters and first divergence event-by-event | **HIGH** |
| Strategy identity | Many nominal strategies collapse onto shared components/enums | About 34 strategies use `STRAT_STRUCT_REACT` | `STRATEGY_IDENTITY_ATTRIBUTION_PREAUDIT_V1.md` gives the exact count 34. Runtime statistics and institutional aggregation are primarily keyed by `stratName`; enum reuse is still a confirmed attribution gap. Six strategies using the shared NXR engine have a stronger shared-state/behavior risk | **VERIFIED** | Shared enum does not mean shared market logic. Most cases are analytics attribution; the NXR six require behavioral isolation | Do not rename IDs or enums in RRA recovery. Add lineage fields distinguishing identity, enum attribution, shared detector/state and statistics key | Per-strategy trace showing `stratName`, enum, detector state owner and stats bucket; collision tests before any migration | **HIGH** |
| PULLBACK detector health | Phase 5.5 PULLBACK fired on about 83% and made NO_EDGE uninformative | Verify 83% without changing it to satisfy a threshold; distinguish BL-01 | `failure_memory_registry_v1.json` records 0.829 and the guard blocks it for discovery. BL-01 defines `H4_PULLBACK_AFTER_IMPULSE`, not the generic Phase 5.5 detector; current discovery output reports 95/2394 = 3.97% | **VERIFIED** | There is no contradiction: these are different detector contracts. Frequency alone is diagnostic; structural feasibility is decided by actual independent units with valid matches | Keep generic PULLBACK quarantined for discovery until its semantics are reviewed. Do not alter it merely to reduce firing. Preserve BL-01 as a distinct identity | Golden labeled examples for both definitions; firing/cluster geometry and independent-unit tests without outcome access | **HIGH** |
| Phase 7.4 inference | The sequence-specific dependence gate created adverse selection/circularity; underlying primitives remain reusable | Verify the current primary method, not only documentation | Current artifacts explicitly reject dependence-conditioned inference selection for new work. `BaselineEngineV4`, matched-pair sign-flip and ungated full-family BH remain reusable. The sequence topology for SEQ-0015 collapses on its preregistered partition; control-reuse enforcement was later wired and tested | **VERIFIED** | “Phase 7.4 failed” is too broad. The conditioned sequence gate and frozen SEQ-0015 design failed; core matching/leakage/evidence primitives did not | Primary method for new pilots: preregistered matched effect, block sign-flip/permutation, full-family BH; ESS diagnostics reported separately, never selecting the p-value method post-outcome | Null calibration and power simulation frozen before data; end-to-end test proving reuse ledger is exercised; no protected holdout | **HIGH** |
| SciPy dependency | Earlier environments had missing scientific dependency failures | SciPy is already declared | `origin/main:server/requirements-dev.txt` pins `scipy==1.18.1`; current main CI is green | **STALE** | No current dependency-contract defect is demonstrated | No dependency change. Reopen only with a reproducible clean-environment failure | Fresh CI install plus import smoke already covered by green main; record exact job if it recurs | **LOW** |
| Historical recovery | RRA-01 is partial; raw seven-census transcripts were not committed | Complete ledger, coverage and untested registry | Canonical repo has 83-strategy census, Phase 7.12 coverage artifact, edge registry, lifecycle registry, evidence/decision databases and 406 vault files. The seven raw narrative reports are unavailable outside the old session transcript | **SUPPORTED** | Existing coverage is substantial but not the requested cross-engine multidimensional recovery ledger. Missing transcript content must be `UNKNOWN`, not reconstructed | Project existing artifacts into one lineage/evidence ledger; dedupe by source artifact hash + experiment identity; extend sparse coverage rather than regenerate combinations | Schema validation, deterministic rebuild, duplicate/repetition fixtures, provenance completeness and reconciliation counts | **HIGH** |
| RI-01 / RI-02 self-improvement | Proposals are bounded, human-approved, reversible and remembered | Verify improvement against independent baselines | `evaluation.py` freezes a baseline at ACCEPTED and evaluates records after IMPLEMENTED, minimum 3. Tests prove temporal separation and both IMPROVED/NOT_IMPROVED. “Independent” currently means different reviewed record IDs; dataset/split/lineage independence is not mechanically enforced | **SUPPORTED** | Temporal pre/post separation exists. Statistical independence and equivalent measurement exposure are not yet proven | Add lineage-aware independence eligibility before treating a trial as improvement evidence; preserve current proposal-only/no-self-approval boundary | Reject duplicate dataset/split/derived experiment IDs; require unchanged rules version and comparable family; negative-control trial | **HIGH** |

## First three event-parity families

1. **MACD 12/26/9 closed-bar crossover** — numerical parity fixtures already exist; extend from indicator tolerance to exact causal crossover timestamps and direction on a shared bar export.
2. **BREAKOUT_ACC** — bar-close logic and dedicated execution traces make it suitable for an event-level golden trace without tick-path ambiguity.
3. **SAR closed-bar event** — independent validation artifacts and a deterministic indicator definition make it preferable to a stateful liquidity/zone detector.

`ORDER_BLOCK` is deliberately excluded from the first exact-parity tranche: it is stateful and tick-sensitive, and existing research correctly treats MT5 event export as the ground truth rather than pretending a bar-driven Python clone is identical.

## Three reproducible improvement trials

### RI-TRIAL-01 — Provenance completeness

- **Baseline:** rate of `DATASET_HASH_MISSING` under one frozen review-rules version.
- **Intervention:** mandatory provenance verifier before experiment ingestion.
- **Result set:** at least three later experiments with distinct source dataset hashes and non-overlapping experiment lineage.
- **Success:** finding rate reduced by at least 50%; duplicate/derived datasets are ineligible.

### RI-TRIAL-02 — Invalid experiment prevention latency

- **Baseline:** elapsed work and artifacts produced before detecting firing/geometry or matching infeasibility.
- **Intervention:** outcome-blind detector-health plus structural-feasibility preflight.
- **Result set:** three preregistered families, including one intentionally infeasible negative control; no outcome access.
- **Success:** infeasible family rejected before outcome contract/test execution, with lower runtime and zero false admission of the negative control.

### RI-TRIAL-03 — Cross-engine first-divergence detection

- **Baseline:** known cross-engine discrepancies detected only after aggregate result comparison.
- **Intervention:** canonical golden-trace comparator over bars, indicators, events, filters and simulated order intents.
- **Result set:** MACD, BREAKOUT_ACC and SAR traces, with seeded timestamp/value/direction defects as controls.
- **Success:** all seeded defects localized to the first divergent layer; zero silent parity promotion; runtime and memory recorded.

## Consolidated plan

1. **SAFETY:** Max-DD latch/persistence PR; separately adjudicate PR #36 for DEMO/LIVE. No live enablement.
2. **RECOVER:** build a deterministic Historical Evidence Ledger projection from existing registries/artifacts; unavailable census transcript data remains `UNKNOWN`.
3. **COVERAGE:** extend the existing Phase 7.12 sparse matrix with engine, timeframe, dataset, variant, cost and evidence lineage; never materialize the full Cartesian product.
4. **REPAIR:** prioritize Max-DD, opening-route guard coverage, generic PULLBACK semantics, shared NXR state attribution and sequence-inference quarantine.
5. **PARITY:** run the three small golden-trace trials above before attempting stateful detectors.
6. **SELF-IMPROVE:** add lineage-aware independence to RI trials and execute the three bounded improvement trials.
7. **EXPLORE:** only after recovery/repair gates, rank the 20 most informative questions by uncertainty reduction, feasibility and reuse—not historical PF.

## Non-actions

No EA change, holdout access, sweep, merge, deploy, live trading, registry identity migration or scientific promotion was performed for this reconciliation.
