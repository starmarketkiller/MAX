# NEXUS Research Re-Interpretation Under the New Market-Microstructure Ontology

**Purpose**: re-read prior NEXUS research through `MARKET STATE -> EVENT -> SETUP -> TRIGGER -> ENTRY -> INVALIDATION -> OUTCOME -> PROBABILITY -> EDGE -> STRATEGY`, independent of the "strategy name" each experiment was filed under. Nothing here is new research — it is extraction and re-classification of existing reports in `vault/01-Trading/`. No code, backtest, or script was run or modified while producing this document.

**How to read each entry**: EVENT (the raw market phenomenon actually tested) / SETUP (context+preconditions) / OUTCOME METRIC / BASELINE / EVIDENCE STRENGTH / ORIGINAL CONCLUSION / RE-CLASSIFICATION (which EDGE_COMPONENT this supports, refutes, or leaves unknown) / FAILURE PATTERNS.

---

## GROUP A — WICK Sweep Causal Research (discovery → confirmation → rejection)

### A1. `NEXUS - Causal Experiment 1 WICK Sweep 1R Outcome.md`

- **EVENT**: a raw price wick sweeping a prior H4 extreme (`WICK_SWEEP_REV` level registry), i.e. a **liquidity sweep** event, independent of any trade.
- **SETUP**: level = H4 candle wick ≥15 pip; event = level reaches `state=SWEPT`. Features: direction, session, day-of-week, hour, level age, touch count, penetration depth.
- **OUTCOME METRIC**: `PLUS_1R_FIRST` vs `MINUS_1R_FIRST` over a synthetic, direction-symmetric ±25 pip target computed from M1 bars (independent of the live SL25/TP100 asymmetric trade) — i.e. "did the sweep resolve favorably at all," not the strategy's real trade outcome.
- **BASELINE**: unconditioned base rate (0.547, n=190) used as the comparison for every bucket — a real baseline is present.
- **EVIDENCE STRENGTH**: single dataset (3 non-overlapping windows, Model=1 MT5 Tester), n=190 resolved, train/OOS split declared in advance; ~25 univariate comparisons run with **no multiple-comparison correction** (flagged explicitly).
- **CONCLUSION**: `HYPOTHESES_FOUND_NEED_CONFIRMATION` — Friday (+0.11 uplift) and level-age (OLD>YOUNG, weak) both stable in direction train→OOS but below the pre-declared materiality bar (CI95 still includes 0.5).
- **RE-CLASSIFICATION**: weak, unconfirmed candidate evidence for a "day-of-week liquidity positioning" component and a "level-age / staleness" component on liquidity-sweep outcomes. Touch-count and penetration depth showed **zero** discriminating signal in this population (degenerate/null) — early negative evidence against "penetration depth alone predicts sweep outcome" for this specific event definition.
- **FAILURE PATTERNS**: `MULTIPLE_COMPARISONS_NO_CORRECTION` (~25 bucket tests, explicitly flagged as reason not to promote); `AMBIGUOUS_SAME_BAR_RATE_ELEVATED` (2.6% here, a preview of a recurring pattern); discovery evidence run on Model=1 (bar-open simulation) explicitly flagged as *not* execution evidence.

### A2. `NEXUS - Causal Experiment 2 Friday Level Age Confirmation.md`

- **EVENT/SETUP**: identical WICK sweep event, independent 2-month out-of-sample period (immediately preceding A1's data).
- **OUTCOME METRIC**: same synthetic ±1R race, frozen thresholds (age cutoff = 20700s from A1, never recalculated).
- **BASELINE**: same base-rate design as A1 — proper pre-registered confirmatory test, not exploratory.
- **EVIDENCE STRENGTH**: n=135 resolved, single confirmatory window, cross-checked for stability across BUY/SELL and first/second half of the period.
- **CONCLUSION**: `NO_HYPOTHESIS_CONFIRMED`. Friday effect **REFUTED** (sign flips: +0.11 → −0.056). Level-age effect `INCONCLUSIVE` — positive in aggregate but sign-inverts between the two halves of this very window.
- **RE-CLASSIFICATION**: direct refutation of "Friday" as a liquidity-sweep-outcome predictor. Level-age remains an open, fragile lead (not yet an edge component).
- **FAILURE PATTERNS**: none new; demonstrates the value of a genuine held-out confirmatory design (this is a positive methodology example, not a failure).

### A3. `NEXUS - Causal Experiment 3 Level Age Final Confirmation.md`

- **EVENT/SETUP**: same WICK sweep event, third independent period (earliest of the three, Jan–Mar 2026), same frozen age threshold.
- **OUTCOME METRIC**: same synthetic ±1R race.
- **BASELINE**: same base-rate design.
- **EVIDENCE STRENGTH**: n=170 resolved; effect checked for stability across both halves and BUY/SELL — this time the negative effect is *stable* across both, unlike Experiment 2's instability.
- **CONCLUSION**: `LEVEL_AGE_REJECTED`. Direction flips again (now stably negative: OLD<YOUNG). Across 3 independent periods the age effect is +, + (unstable), − (stable) — **not reproducible**.
- **RE-CLASSIFICATION**: **REFUTED** — "level age at sweep" is not a usable edge component for the WICK-sweep event as defined here. The entire WICK-sweep-outcome causal thread is formally closed for lack of a robust predictive feature (of direction, session, hour, day-of-week, age, touch-count, penetration — none survive). `WICK_SWEEP_REV` is explicitly retained only as a **negative research baseline**.
- **FAILURE PATTERNS**: this triad (A1→A2→A3) is the project's cleanest demonstration of why a single confirmatory pass is not enough — a hypothesis can pass one out-of-sample test by chance and fail the next. Worth carrying forward as a general "one-confirmation-is-not-enough" discipline note, not a specific bug.

---

## GROUP B — Structural (SH_BMS_RTO) Dataset & TRUE_BREAK/RETEST Causal Research

### B1. `NEXUS - Causal Research Thread 2 Phase A Structural Instrumentation.md` / `...Phase A1 Shared Sweep Instrumentation.md`

- **EVENT**: generalizing beyond WICK — instrumenting the full **SWEEP → TRUE_BREAK → RETEST → INVALIDATE** lifecycle for structural levels (daily/weekly/monthly/Asia/equal highs-lows) consumed by `SH_BMS_RTO`.
- **SETUP**: read-only causal hooks added at the exact state-machine transition points (no trading logic touched); canonical, deduplicated, cross-consumer-safe SWEEP event source built in Phase A.1.
- **OUTCOME METRIC**: none yet — pure infrastructure/feasibility (event counts: 3456 events Phase A, cross-consumer dedup 262 in Phase A.1).
- **BASELINE**: N/A (instrumentation only), trading parity (bit-identical SHA256) verified repeatedly.
- **EVIDENCE STRENGTH**: engineering verification (parity, determinism), not a statistical claim.
- **CONCLUSION**: `READY_FOR_STRUCTURAL_DATASET` both times.
- **RE-CLASSIFICATION**: not itself edge evidence, but it is the causal-integrity foundation for everything in Group B below. Important secondary finding: the detector `NXS_DetectSweepExt()` was discovered here to leak ~65% incoherent observations (`confirmed=true` with `dir=NONE`) — root-caused later in Group D.
- **FAILURE PATTERNS**: `MULTI_TF_PASS_DUPLICATE_OBSERVATION` (2225 multipass duplicates from the same tick being evaluated once per TF pass) — this exact mechanism reappears as the root cause of major sample loss later in B3/B5.

### B2. `NEXUS - Causal Research Thread 2 Reclaim False Break Feasibility.md`

- **EVENT**: audit/design only — surveying which strategies/detectors could support a generalized SWEEP→FALSE_BREAK(reclaim)/TRUE_BREAK→RETEST lifecycle across sources (not just WICK).
- **SETUP/OUTCOME**: none executed; feasibility table only.
- **CONCLUSION**: `HOLD_NEEDS_CAUSAL_HOOKS` — richer event families (SH_BMS_RTO, SilverBullet, SNXSSweepExt) lack persistent level identity/penetration/explicit TRUE_BREAK-RETEST events; only WICK_RECLAIM was execution-ready without new hooks.
- **RE-CLASSIFICATION**: scoping document; motivates Group B's later instrumentation work. No edge claim.

### B3. `NEXUS - Structural Dataset v1.md` (SUPERSEDED) → `NEXUS - Structural Dataset v1 Causal Linkage Integrity Audit.md`

- **EVENT**: SWEEP/TRUE_BREAK/RETEST/INVALIDATE events on structural levels (not trades).
- **SETUP**: 4 windows (~7.8 months), event-level dataset (`at_sweep.csv`, `at_true_break.csv`).
- **OUTCOME**: label coverage only (no predictive analysis) — `TRUE_BREAK_OCCURRED` initially reported at **19.5%** in v1.
- **CRITICAL BUG FOUND IN AUDIT**: the v1 linkage was **level-scoped, not episode-scoped** — a `structural_level_id` (e.g. `Asia-High_2026.01.23`) can host multiple independent sweep→invalidate episodes over time, and v1 attributed a TRUE_BREAK from *any* episode of that level to *every* sweep of that level. Corrected true rate: **1.16%** (47/4045), a ~17x overstatement.
- **RE-CLASSIFICATION**: this is not itself an edge finding — it is a **data-integrity correction** that invalidates any naive read of "how often do structural levels truly break" from v1. The corrected v2 (episode-scoped) dataset is the valid basis for B4 onward.
- **FAILURE PATTERN**: `LEVEL_SCOPE_VS_EPISODE_SCOPE_LEAKAGE` — catalogued in detail below (#6).

### B4. `NEXUS - Structural Lifecycle Sample Recovery.md`

- **EVENT**: same SWEEP→TRUE_BREAK lifecycle; root-causing why 69.3% of TRUE_BREAK episodes were excluded in the prior thread (`Causal Research Thread 3 True Break Quality`, see B7 below).
- **ROOT CAUSE FOUND**: `NXS_CollectAllSignals`'s multi-TF-pass architecture lets 6 different timeframes mutate the *same shared* SH_BMS_RTO state within a single real tick, using inconsistent per-TF bar data — producing "redundant after close" / "true break after close" artifacts that are not genuine noise but **cross-episode contamination** in the Python-side heuristic reconstruction.
- **FIX**: additive `episodeSeq` counter on the real state machine (never read by any trading decision) — gives ground-truth episode identity instead of reconstructing it after the fact.
- **OUTCOME**: sample recovered from 60 → 159 resolved TRUE_BREAK outcomes (exclusion rate 69.3% → 0%); trading parity re-verified bit-identical (104/104 trades, same SHA256).
- **RE-CLASSIFICATION**: pure infrastructure fix; unlocks Group B5-B8 below. Also discloses that 288 TRUE_BREAK/INVALIDATE events remain orphan even after the fix (traced fully in B6) — a legitimate exclusion, not a new bug.
- **FAILURE PATTERN**: `MULTI_TF_PASS_DESYNC` (root cause, catalogued below #7); demonstrates that a Python-side heuristic reconstruction of episode identity can silently contaminate a dataset even when each individual event field is causally correct.

### B5. `NEXUS - Phase C1 Orphan TRUE_BREAK Audit.md`

- **EVENT**: same lifecycle; explaining the 288 orphan TRUE_BREAK events left after B4's fix.
- **FINDING**: 100% attributable to `CANONICAL_DEDUP_EPISODE_COLLISION` (multiple SH_BMS_RTO episodes sharing one canonical SWEEP row) — 0% unexplained. Also found and fixed a **cosmetic counting bug**: `event_id` is not unique across Tester windows (resets to 1 each run), causing a diagnostic print to undercount orphans (283 vs true 288) — the underlying population/exclusion logic was never affected, only one print statement.
- **OUTCOME**: population rebuilt with a deterministic episode-linking map (`episode_sweep_link`), raising resolved TRUE_BREAK outcomes from 159 → 344.
- **RE-CLASSIFICATION**: further causal-integrity work; sets up B7 Final v3.
- **FAILURE PATTERN**: `EVENT_ID_NOT_UNIQUE_ACROSS_WINDOWS` (catalogued below #5) — first documented here, but the same root cause reappears in B3's Structural Causal Experiment 1 (see B8).

### B6. `NEXUS - Structural Causal Experiment 1.md` / `...2 Confirmatory.md` / `...3 Economic Bridge.md`

- **EVENT**: at the moment of SWEEP, does any causally-known feature predict `TRUE_BREAK_OBSERVED` vs `INVALIDATED_NO_BREAK`? I.e. **liquidity sweep → structural break** transition probability.
- **SETUP**: population = SH_BMS_RTO episodes (932 valid in Experiment 1, after excluding `NO_LIFECYCLE_OBSERVED` and post-close artifacts). Note: Experiment 1 itself found and fixed a second `event_id`-not-unique-across-windows bug (cross-window collision corrupting w1 to zero episodes) before analysis — same failure pattern as B5, independently rediscovered.
- **OUTCOME METRIC**: binary TRUE_BREAK_OBSERVED, base rate ~8.2%.
- **BASELINE**: base rate is the comparison baseline throughout; explicit **39 bucket tests** (Exp.1), declared thresholds (`|uplift|≥0.10` in both TRAIN and OOS).
- **EVIDENCE STRENGTH — Experiment 1**: n=932 (642 train / 290 OOS), single dataset, 3 `WEAK_HINT`s found (penetration/ATR top quartile, age<1h, source_tf=D1) — none promoted (`PROMISING_HYPOTHESIS=0`).
- **EVIDENCE STRENGTH — Experiment 2 (independent w0 period, n=941)**: `penetration_per_atr` Q4 **CONFIRMED** (+11.3pp uplift, multi-tag, BUY/SELL balanced). The other two hints (`age<1h`, `source_tf=D1`) were **declassified to INCONCLUSIVE_FINAL** after discovering they are ~87-92% the same subset and are in reality a hidden proxy for "Asia-Low sweep" (deterministic `created_time` formula artifact) whose entire uplift lives in the BUY-only Asia-Low side (0% TRUE_BREAK on Asia-High/SELL) — a textbook confound caught by the mandated BUY/SELL robustness check.
- **EVIDENCE STRENGTH — Experiment 3 (independent wA period, n=717)**: `penetration_per_atr` Q4 replicates in **direction** (+6.48pp, p=9.3e-05) but **falls below the materiality bar** (10pp) used to promote it in Experiment 2 — by the project's own no-lowering-the-bar discipline, this is treated as a failed final replication. Economic bridge to `AT_TRUE_BREAK` outcome (n=13 in the qualifying group) shows a nominal +20.8pp uplift but on a microscopic sample.
- **CONCLUSION (final, Experiment 3)**: `STRUCTURAL_HYPOTHESIS_REFUTED_FINAL`.
- **RE-CLASSIFICATION**: `penetration_per_atr` at sweep as a precursor of structural TRUE_BREAK is **UNKNOWN/WEAK, not confirmed** — 2 of 3 independent periods showed a positive, statistically real but below-materiality-bar effect; treat as suggestive of a genuine but small "displacement magnitude at sweep → break probability" relationship, worth revisiting with more data, not an edge component today. Age<1h/source_tf=D1 as break predictors are **REFUTED** (confound-driven artifacts).
- **FAILURE PATTERNS**: `EVENT_ID_NOT_UNIQUE_ACROSS_WINDOWS` (rediscovered independently); `CONFOUNDED_FEATURE_VIA_DETERMINISTIC_MAPPING` (catalogued below #17) — the Asia-Low/BUY confound is one of the cleanest documented examples in the whole corpus of why BUY/SELL and multi-tag robustness checks matter.

### B7. `NEXUS - Causal Research Thread 3 True Break Quality.md` (v1, pre-recovery) → `NEXUS - Causal Research Thread 2 Phase A Structural Instrumentation` lineage → `NEXUS - Causal Research Thread 3 Final v3.md` (post-recovery)

- **EVENT**: given a TRUE_BREAK has already occurred, do known-at-that-moment features predict CONTINUATION (+1R) vs FAILURE (−1R)?
- **v1 (pre-B4/B5 fixes)**: n=107 raw, only 60 resolved after excluding post-close artifacts (69.3% exclusion) — **below the pre-declared minimum of 150** → `HOLD_INSUFFICIENT_TRUE_BREAK_SAMPLE`, **no analysis performed** (a correct, disciplined stop).
- **v3 (post B4+B5 fixes, `episode_sweep_link` v3 population)**: 558 valid TRUE_BREAK, 344 resolved (166 discovery / 178 validation). **54 bucket/hypothesis tests**, 15 frozen features (penetration/ATR, regime, structure trend, direction, source_tf, etc.). Logistic regression and shallow decision tree both tested; neither beats the majority-class baseline out-of-sample (tree leaves attenuate or reverse on validation).
- **OUTCOME METRIC**: `PLUS_1R_FIRST` vs `MINUS_1R_FIRST`, R=25 pip, base rate 48.5% (n=344).
- **BASELINE**: base rate + majority-class baseline for the model comparison — both present.
- **CONCLUSION**: `NO_PROMISING_HYPOTHESIS` — a stronger, sample-adequate closure (not a sample-insufficiency closure).
- **RE-CLASSIFICATION**: **REFUTED** as an edge source — none of penetration/ATR, regime, structure-trend-alignment, source timeframe, or their combination (linear or shallow-tree) predict TRUE_BREAK continuation vs failure once population is correctly built and adequately sized.
- **FAILURE PATTERN**: demonstrates the correct use of a pre-declared minimum-sample stop rule (positive methodology, not a failure) — contrast with LEVEL_REACTION/LEVEL_CONFLUENCE (Group F) where a near-breakeven small sample was initially over-trusted.

### B8. `NEXUS - Causal Research Thread 4 Retest Quality.md`

- **EVENT**: given a RETEST is observed (SWEEP→TRUE_BREAK→RETEST fully linked), do known-at-retest features predict HOLD vs FAIL?
- **SETUP**: n=88 RETEST episodes, 64 resolved (≥50 minimum met), 57 bucket tests, 15 frozen features.
- **OUTCOME METRIC**: `RETEST_HOLD_OR_FAIL`; base rate 46.9%. Economic secondary target verified to be **structurally identical** to the primary target in this dataset (HOLD ≡ PLUS_1R_FIRST exactly) — no structural/economic divergence possible here.
- **BASELINE**: base rate + majority-class baseline (logistic regression underperforms it: 0.406 vs 0.531).
- **CONCLUSION**: `NO_PROMISING_HYPOTHESIS` (all 3 top `WEAK_HINT`s dominated by a single tag/direction; shallow tree leaves invert on validation).
- **RE-CLASSIFICATION**: **REFUTED** as an edge source — retest-quality features (distance/ATR, trend alignment at retest, regime change sweep→break→retest) do not predict retest outcome in this dataset.

---

## GROUP C — Unified Level Engine Infrastructure (WICK migration, Phases A–E)

*(`NEXUS - Unified Level Engine Phase A WICK Telemetry Shadow.md`, `...Phase B Causal Non-Interference Validation.md`, `...Phase C WICK Read Path Migration.md`, `...Phase D WICK Authority Parity Gate.md`, `...Phase E Final Soak and Research Handoff.md`)*

- **EVENT/SETUP**: none — this is a 5-phase infrastructure migration replacing `WICK_SWEEP_REV`'s legacy internal state with a shared, structured `SNXSUnifiedLevel`/`SNXSReactionEvent` registry (CREATED→FRESH→TOUCHED→SWEPT→RECLAIMED/INVALIDATED/CONSUMED lifecycle), read-authoritative only after exhaustive parity proof.
- **OUTCOME/BASELINE**: not a strategy result — the outcome metric is **bit-identical trading parity** (SHA256 of trade CSV) between legacy and new engine, proven across dozens of paired ON/OFF and LEGACY/NEW-AUTHORITY runs, plus a deliberate fault-injection test (corrupted SL value) that correctly triggered the fail-safe fallback in all 35/35 cases.
- **EVIDENCE STRENGTH**: extremely high for the *engineering claim* (determinism, zero mismatch across ~1700+ decision checks per run, multiple independent windows) — essentially proof by exhaustive comparison, not statistical inference.
- **CONCLUSION**: `MIGRATION_READY` (Phase D) → `READY_FOR_CAUSAL_RESEARCH` (Phase E). Phase E explicitly **freezes `WICK_SWEEP_REV`/Unified Level Engine as a negative research baseline** (fixture: 178 trades, PF≈0.78, negative) — value is as a "labeled laboratory" of sweep events with known outcomes, not as a strategy to optimize.
- **RE-CLASSIFICATION**: this is the causal-integrity plumbing underlying Group A's findings. The Phase E feature-availability matrix explicitly separates `AVAILABLE_NOW` (level_id, source, side, age, touch count, penetration) from `REQUIRES_NEW_CAUSAL_HOOK` (ATR-normalized penetration, regime/trend context) — useful today for scoping any future WICK-family causal experiment.
- **FAILURE PATTERNS**: `CAUSAL_HOOK_MISMATCH` — during Phase C, the read-path comparator itself had 2 real bugs (missing multi-TF guard causing 367 false mismatches; reading own throttle write before the legacy read, causing self-negation) that were caught and fixed by the parity gate *before* they could ever reach a real trade — a positive example of fail-safe design catching its own bugs. Also documents the Model=1 vs Model=4 (bar-open vs real-tick) granularity difference producing different raw trade counts on the "same" period — a recurring theme flagged wherever a Model=1 result is compared to a Model=4 fixture.

---

## GROUP D — SNXSSweepExt Detector Bug (uninitialized-memory failure)

### D1. `NEXUS - SNXSSweepExt Detector Integrity Fix.md` / D2. `NEXUS - SNXSSweepExt Semantic Impact Audit.md`

- **EVENT**: root-causing the "confirmed=true, dir=NONE" anomaly discovered in Group B1 (Fase A.1) affecting ~65% of raw sweep observations.
- **ROOT CAUSE**: `SNXSSweepExt s; s.dir = DIR_NONE;` did **not** actually leave the struct's other 15 fields zero-initialized (contrary to a code comment asserting MQL5 auto-zeroes local structs) — verified directly via diagnostic prints showing astronomical stack-garbage doubles in `level`/`refHigh`/`refLow` and a null string handle in `levelTag`, recurring with exact 1-in-7-call periodicity (stack-frame reuse in the multi-TF-pass loop).
- **FIX**: explicit initialization of all 16 fields; verified the semantic invariant `confirmed==true ⇒ dir∈{BUY,SELL} ∧ level>0 ∧ levelTag≠""` holds in every one of the 10 detection branches.
- **IMPACT DISCOVERED**: 5 pre-existing, unguarded consumers of `SNXSSweepExt` (`TURTLE_SOUP`, `AMD_REVERSAL`, `JUDAS_SWING`, `LDN_REVERSAL`, `PO3`) read `sweptXXX`/`refHigh`/`refLow` fields **without ever checking `confirmed`/`dir`** — meaning their historical backtests were partly built on stack garbage. Concretely isolated: in one 3-month window, `AMD_REVERSAL`'s two historical winning trades (+$93.4 aggregate) were shown to be **entirely artifacts** of a garbage `sw.refLow` value used directly in the SL calculation (`slPrice = sw.refLow - 0.4*atr`) — with the fix, the same period produces a single real trade, a loss (-$24.3).
- **OUTCOME/BASELINE**: full determinism re-verified post-fix (bit-identical repeat runs); per-strategy isolation runs (Research Mode) confirm 0 behavior change for `TURTLE_SOUP`/`JUDAS_SWING`/`LDN_REVERSAL`/`PO3` *in the tested window* (0 trades either way) — but they remain code-level EXPOSED, so any historical baseline of theirs from a *different* window is not verifiable retroactively without re-running the same before/after comparison.
- **RE-CLASSIFICATION**: **not an edge finding**, but critical for the failure-memory: any pre-fix historical result for `AMD_REVERSAL` is `INVALIDATED_BY_UNINITIALIZED_STATE_BUG`. `TURTLE_SOUP`/`JUDAS_SWING`/`LDN_REVERSAL`/`PO3` results carry an unresolved risk flag pending a dedicated re-check on their respective productive windows.
- **FAILURE PATTERN**: `UNINITIALIZED_STRUCT_MEMORY` (catalogued below #8) — one of the most consequential bugs in the whole corpus: it directly fabricated a fake historical "edge" for a live strategy family.

---

## GROUP E — WICK_SWEEP_REV / WICK_SWEEP_RECLAIM Live Strategy Reports (dated, market-event framing)

### E1. `NEXUS EA - Audit Structure-Reaction-LEVEL_REACTION e WICK_SWEEP Bloccato dal Terzo Cancello (10-09).md`

- **EVENT**: comparative architecture audit of three "level reaction" event families: `STRUCT_REACT` (SMC zone touch+pin-bar reaction), `LEVEL_REACTION` (pivot/SNR touch with breach-depth gate and delayed confirmation), `WICK_SWEEP_REVERSAL` (H4 wick sweep, immediate fade).
- **KEY FINDING (market-event relevant)**: the Structure Engine's swing highs/lows are wick-based exactly like WICK_SWEEP's levels, but require a symmetric fractal confirmation (3 bars each side) — WICK_SWEEP has **no such isolation requirement**, meaning any wick ≥15 pip becomes a level even mid-sequence, which the audit flags as likely capturing "noise" rather than selective liquidity grabs (165 sweep events in ~80 days H4 = ~2/day, far more frequent than the "rare pattern" hypothesis assumed).
- **OUTCOME/BASELINE**: none new here (descriptive), but crucially documents that `LEVEL_REACTION`'s cited 99.5%/78.9%/69.1% reversal-by-breach-depth percentages come from an **external Python pivot study never re-verified against LEVEL_REACTION itself** — flagged explicitly as "an historical input, not a validated edge here."
- **RE-CLASSIFICATION**: proposes (design only) a unified "Level Engine dataset" (penetration bins, MFE/MAE, reclaim, structural break, time-to-reaction) that generalizes what Group B/F each did piecemeal — this is essentially the blueprint for the new ontology applied to the level-reaction family specifically.
- **FAILURE PATTERN**: `THIRD_SILENT_GATE` (catalogued below #12) — `NXS_StrategyKnown()` registry whitelist silently blocked all 165 real WICK_SWEEP_REV sweep events from ever opening a trade until the strategy was registered in the source-of-truth JSON; this same gate class had already blocked 7 other strategies and PIVOT_WICK historically.

### E2. `NEXUS EA - LEVEL_REACTION, Merge Vero di PIVOT_WICK STRUCT_REACT MALAYSIAN_SNR (06-09).md`

- **EVENT**: merges two independent level sources (H1/H4/D1 wick pivots + H4 close-based S/R) with a breach-depth gate derived from an external 7402-pivot study (<20 pip: 99.7% reversal; 20-50: 99.1%; 50-100: 96.9%; >100pip: 69.1%).
- **RE-CLASSIFICATION**: strong prior candidate for a "breach-depth as reversal-probability gradient" edge component — but note this prior comes from a **different level population** (generic M15 zigzag pivots) than the one it is applied to (H1/H4/D1 pivots + H4 S/R) and was **never independently re-measured** on the actual LEVEL_REACTION population (flagged in E1 too). Treat as UNKNOWN, imported-prior, not validated-on-target.

### E3. `NEXUS EA - LEVEL_REACTION Primo Risultato...` / `...3 Anni, il Quasi Pareggio Non Regge...` (07-09)

- **EVENT**: same LEVEL_REACTION touch/breach event, executed as a real (simulated) trade.
- **OUTCOME METRIC**: PF, win rate, net PnL vs breakeven win-rate threshold.
- **BASELINE**: breakeven threshold computed from realized payoff ratio — explicit and appropriate baseline.
- **EVIDENCE — 3 months**: 338 trades, PF 0.95, gap to breakeven only **-1.1pp** — "best first result of the level-reaction family" (compare LEVEL_CONFLUENCE variants at -3.2 to -11pp).
- **EVIDENCE — 3 years**: 1833 trades, PF **0.80**, gap widens to **-4.2pp** (SELL side gap -6.4pp, much worse than the 3-month BUY/SELL near-parity).
- **CONCLUSION**: "close the family, same lesson as LEVEL_CONFLUENCE."
- **RE-CLASSIFICATION**: **REFUTED at scale** — breach-depth gate + dual level source improves quality of the small-sample signal (best in family) but does not produce a positive-PF edge once tested on 5.4x the sample. Useful negative evidence: neither pivot-wick nor close-based-S/R touch+delayed-confirm, even filtered by breach depth, is by itself a working liquidity-reaction edge.
- **FAILURE PATTERN**: `SMALL_SAMPLE_NEAR_BREAKEVEN_MISTAKEN_FOR_CONFIRMATION` (catalogued below #13) — explicitly named by the author as "the same pattern as LEVEL_CONFLUENCE, confirmed twice now."

### E4. `NEXUS EA - WICK_SWEEP_REV Registrato, 50 Trade Reali...` (10-09)

- **EVENT**: first *real* trades from WICK_SWEEP_REV after the registry gate (E1) was fixed.
- **OUTCOME**: 50 trades, PF 0.97, net -$5.77, WR 20%, 25 BUY/25 SELL — explicitly reported as descriptive only, not an edge verdict (still confounded by a telemetry bug: the "one attempt per level" throttle was found broken, meaning some trades may be late retries on stale levels rather than genuinely fresh sweeps).
- **RE-CLASSIFICATION**: consistent with the WICK_SWEEP_REV negative baseline established elsewhere (Group A/C).
- **FAILURE PATTERN**: a second, independent bug is found in the same report — the RAW exit-authority invariant cannot distinguish an opt-in protection (ESL) closing a position from a genuine "third silent module" violation, because MT5's `DEAL_REASON` field collapses every EA-initiated close to `"expert"`, losing the `NXS:DD`/`NXS:RISK` tag written in the deal comment. Catalogued below as #9-adjacent (telemetry/authority-tagging mismatch, related to but distinct from cost/signal-price issues).

### E5. `NEXUS EA - WICK_SWEEP Entry Timing Study...` (11-09) — the largest single report in this corpus

This report chronicles an entire discovery→shadow→execution→counterfactual→tick-replay pipeline for a **liquidity-reclaim** event built on top of the WICK sweep.

- **EVENT (core)**: after a WICK sweep (`IMMEDIATE_FADE`, i.e. entering immediately at the sweep), does waiting for the price to **reclaim the trigger price** (a liquidity-reclaim / false-break confirmation event) improve outcome vs entering immediately?
- **v1 methodology bug**: initial Python replay treated every qualifying wick as an independent, permanent level (never replaced) — produced 18,232 "trigger" events vs 181 real ones (~100x overcount), because the live strategy keeps only ONE active level per side, replaced (not accumulated) on every new wick. Fixed (v2): sequential single-active-level replay, closing the gap to 239 vs 181 (residual +32% gap explained later as an OHLC-vs-tick-sampling artifact, never fully eliminated in the Python layer).
- **SETUP (Python v2, all history 2023-2026)**: `RECLAIM_TRIGGER` entry model available on 75.6% of sweeps, WR 16.0%→24.6%, sacrificing only 1.7% of TP outcomes — first hint of a **liquidity-reclaim confirmation edge**.
- **MQL5 tick-level shadow validation**: after 3 failed parity attempts (each due to a `CAUSAL_HOOK_MISMATCH` — see below), achieved **exact parity** (181 shadow sweeps == 181 canonical sweeps) on run #4. On this shadow (idealized fill exactly at `trigger_price`): **WR 59.2%, PF 5.80, expectancy +48.98 pip/trade** — a dramatic apparent edge.
- **REAL EXECUTION TEST (`WICK_SWEEP_RECLAIM`, selector 55)**: same cohort of sweeps, same M15-gated reclaim cadence, real MT5 market orders. Result: **112 trades, WR 48.21%, PF 0.80** — the edge **evaporates**. Root cause fully quantified: the shadow assumed a fill exactly at `trigger_price`; a real market order fills at the price prevailing when the M15-gated reclaim confirmation arrives, which had already slipped a **median +42.6 pip** in the favorable direction (|slippage|>10pip in 86% of cases) — because SL/TP remain fixed absolute prices anchored to the stale trigger, this favorable slippage shrinks the distance to TP and lengthens the distance to a now-rare SL, exactly explaining the shadow's inflated PF.
- **COUNTERFACTUAL (FILL_ANCHORED)**: re-anchoring SL/TP to the real fill instead of the trigger was tested as a fix — **REFUTED**: PF marginally worse (0.72 vs 0.76), 36 real wins converted to losses, 0 losses saved.
- **TICK-LEVEL REPLAY (MODEL A: RECLAIM_TICK / MODEL B: RECLAIM_LIMIT_RETEST)**: genuinely tick-level detection (bypassing the M15 gate) and exact-price limit-retest were both tested via a from-scratch Dukascopy tick replay (after fixing a UTC vs UTC+3 timezone bug and a ~21% tick-coverage gap). **Both REFUTED**: MODEL A PF 0.75 (worse than the already-weak 0.78-0.80 real baseline), MODEL B PF 0.67, available on only 57.5% of setups and converting almost every real winning trade into a loss.
- **FINAL VERDICT**: entire `WICK_SWEEP_RECLAIM` research line closed. **No variant (M15-gated real, tick-detection, tick-limit-retest, fill-anchored) shows a usable edge.**
- **RE-CLASSIFICATION**: this is the corpus's cleanest, most rigorously falsified case of **`SHADOW_EXECUTION_ASSUMPTION`** (edge component: "liquidity reclaim confirmation" — REFUTED specifically for immediate-market-order execution at M15 cadence on this event definition; the underlying market phenomenon — that a reclaimed sweep is more likely to continue favorably — may still be real, since the shadow's WR of 59.2% on a real (not idealized) event population is far above the 16.9% no-confirmation baseline; what is refuted is that this can be captured tradeably at this cadence/fill-model, not necessarily that the phenomenon itself is illusory). This distinction (phenomenon vs execution-capturability) is exactly the kind of nuance the new ontology is meant to preserve.
- **FAILURE PATTERNS** (all formally catalogued by the source report itself as reusable "Failure Memory," referencing `NEXUS - Failure Memory (Registro Pattern di Fallimento Metodologico) (12-09)`): `SHADOW_EXECUTION_ASSUMPTION`, `TIMEZONE_MISMATCH` (MT5 UTC+3 vs Dukascopy UTC, verified via 2 independent price/timestamp anchors), `DATA_COVERAGE_GAP` (Dukascopy tick fetch missing ~21% of weekday hours even after gap-fill, flagged not silently included), `CAUSAL_HOOK_MISMATCH` (3 sequential shadow-parity failures, each from the diagnostic hook sitting at a different point in the real `OnTick()` pipeline than the strategy it was meant to mirror — including discovery of a global "New Bar Gate" that samples all strategies once per M15 bar, not per tick).

### E6. `NEXUS EA - WICK_SWEEP_RECLAIM_TICK - Design Candidate Non Implementato (12-09).md`

- Pure design note (unimplemented) proposing a genuinely tick-level ARM+reclaim variant bypassing the New Bar Gate. **UNKNOWN/untested** — explicitly requires a fresh shadow validation before any implementation, to avoid the exact `CAUSAL_HOOK_MISMATCH` pattern from E5.

---

## GROUP F — LEVEL_REACTION / PIVOT_WICK / STRUCT_LEVEL_SWEEP (level-touch/breach family)

### F1. `NEXUS EA - PIVOT_WICK step2 e OneShotLevel Analizzati, Nessun Fix (03-09).md`

- **EVENT**: fractal pivot + wick-rejection touch (M15).
- **9 isolated filter variants tested** (entry-side c1-c6, exit/sizing-side d1-d5) against a c1 baseline (503 trades, WR 44.9%, PF 0.79):
  - `OneShotLevel` (c2): -28% volume, **no quality change** (WR/PF/avg-win-loss statistically identical) — reduces net loss only by trading less of the same negative edge.
  - `RequireCloseConfirm` (c3): **only isolated variant with a real quality improvement** (WR 44.9%→47.8%, PF 0.79→0.91) on the 3-month sample — but **does not hold at 3-year scale** (WR 41.4%, PF 0.73 on 1799 trades) — re-classified as a small-sample artifact.
  - `AvoidBuildup` (c4): bit-identical to baseline — filter verified wired into the code but never actually triggers (threshold never reached in this data) — **inert, not tested**.
  - `RequireWick` (c5): genuinely worse (WR 41.4%, PF 0.68) on a collapsed sample (87 trades).
  - Combining all 4 (c6): 5 trades — statistically meaningless.
  - Exit-side filters (ATR-partial, fixed-pip-partial, volume-partial, streak-sizing, regime-veto): all either inert (rounds to the same 0.01-lot floor) or, when real (RegimeVeto), reduce volume without changing PF (same "volume≠edge" pattern as OneShotLevel).
- **CONCLUSION**: none of 9 isolated variants nor several combinations push PIVOT_WICK above breakeven; the one apparent quality win doesn't survive scale.
- **RE-CLASSIFICATION**: **REFUTED** — pivot-fractal + wick-rejection touch (with or without close-confirmation, one-shot-per-level, buildup-avoidance, or regime veto) shows no PF>1 edge on M15 GOLD in the tested history. Negative evidence specifically against "requiring candle-close confirmation of a wick rejection" and "requiring a true wick (not just touch)" as standalone fixes for a pivot-touch reversal setup.
- **FAILURE PATTERNS**: `SMALL_SAMPLE_NEAR_BREAKEVEN_MISTAKEN_FOR_CONFIRMATION` (RequireCloseConfirm case, catalogued below #13); `VOLUME_REDUCTION_MISTAKEN_FOR_EDGE_IMPROVEMENT` (OneShotLevel, RegimeVeto, catalogued below #15); `STACKED_FILTERS_COLLAPSE_SAMPLE` (c6/d6 producing 5 and 0 trades, catalogued below #14); `DUPLICATE_TEST_NOT_ISOLATING_VARIABLE` (d1 "ATR partial" test compared ON-vs-ON because the flag's default had silently changed to `true` weeks earlier — no variable was actually isolated, catalogued below #21).

### F2. `NEXUS EA - Dataset Python STRUCT_LEVEL_SWEEP, Risultati e Scoperta Bias Livelli Stantii (10-09).md`

- **EVENT**: generalized structural level (SWING/WICK_H4/PIVOT-H1-H4-D1/SNR_H4) touch+penetration, offline Python replay across full simulated history (13,224 candidate levels, 484,552 touch events).
- **KEY FINDING — stale-level bias**: the "100+ pip breach" bin initially showed nonsensical stats (36% reclaim, MFE median **-1640 pip** at a 1-hour horizon) — traced to levels created a year earlier at a completely different (simulated) price regime being "touched" for the first time after $2600+ of secular drift. This is not a sweep at all, it's stale-level noise. Re-filtering to levels touched within 30 days of creation: the same bin becomes 73.6% reclaim, MFE median +30.9 pip — a completely different, sane reading.
- **SECOND FINDING**: below 100 pip breach, reclaim is ~100% almost everywhere — likely because 100 pip ($10) is a trivial fraction of this instrument's volatility at simulated $4000-5500 price levels; the bin scheme is probably too coarse and should extend past 100 pip or normalize by ATR.
- **THIRD FINDING**: first-touch levels (n=12,250, 2.5% of all touches) reclaim more (95.5%) and penetrate less (34.8 pip median) than repeat-touch levels (72.9% reclaim, 52.9 pip median) — first-touch is a real, distinct regime from repeat-touch.
- **RE-CLASSIFICATION**: this is design/exploratory data work, not yet a tested strategy — but it is genuinely useful **positive evidence for level-age filtering as a data-quality requirement** (distinct from Group A's finding that level-age is not itself predictive of *sweep outcome* — here the finding is that level age must be *bounded* for any touch/breach statistic to be meaningful at all, a data-hygiene point, not a trading signal). Also usable evidence that "first touch vs repeat touch" is a real, distinguishing state for a future setup definition. No strategy or live outcome was measured — **UNKNOWN as an edge**, but a validated dataset-construction lesson.
- **FAILURE PATTERN**: `STALE_LEVEL_AGE_BIAS` (catalogued below #20) — distinct from, but related to, the level-age-as-predictor question from Group A.

### F3. `NEXUS EA - STRUCT_LEVEL_SWEEP, Audit Structure Engine e Design Nuovo Filone (10-09).md`

- Pure audit + design (no test run): documents that the live `NXS_Structure.mqh`/`NXS_Reaction.mqh` engine never measures sweep/breach *depth* (only in/out-of-tolerance touch), and proposes a `STRUCT_LEVEL_SWEEP` design (persistent multi-level pool, breach-depth binning, tight SL beyond the breach, BE + runner, non-martingale re-entry on a *new* level after a stop). **UNKNOWN/untested** — no code written, no data collected on the live engine yet (only the offline Python work in F2 exists so far for this family).

---

## GROUP G — Strategy Foundry (native hypotheses, open-source mining, causal screening, implementation)

### G1. `NEXUS - Strategy Foundry Phase 1.md`

- 10 native event hypotheses formalized (failed-breakout-fade, volatility-compression-percentile-breakout, impulse/pullback time-compression, session-compression→expansion, regime-conditional-momentum, multi-TF liquidity-sweep confluence, displacement-imbalance-stack, retest-rejection-speed, volatility-expansion-exhaustion-fade, weekly-open-gap fade/continuation) — plus 30 open-source EA candidates mined and classified (novelty map). No testing in this phase (specs + audit only).
- **RE-CLASSIFICATION**: none yet decidable — this is the hypothesis-generation layer; see Phase 2 (G2) for outcomes.

### G2. `NEXUS - Strategy Foundry Phase 2 Causal Screening.md`

All hypotheses tested with a genuine discovery/validation (70/30 chronological) split and R-multiple expectancy metric — **this is a model example of the correct methodology** (declared thresholds, baselines for every hypothesis, no post-hoc feature tuning).

| Hypothesis (EVENT) | n (disc+val) | Result | Verdict |
|---|---|---|---|
| Failed Breakout Fade (a **false-break/liquidity-trap reversal** event) | 278 | sign inverts disc→val (+0.134R→−0.214R); continuation baseline stays positive both segments | `NO_EDGE` — **refutes** "failed breakout → fade" as a standalone edge; continuation after breakout appears to be the more robust phenomenon here |
| Volatility Compression Percentile Breakout | 196 | consistently **negative**, worse than the no-compression baseline in both segments | `NO_EDGE` — refutes "compression precedes expansion" as *helpful*; suggests compression may be actively counterproductive as a precondition |
| Session Compression → London Expansion | 215 | sign inverts (−0.100R→+0.385R); baseline (no compression precondition) stays consistently positive | `NO_EDGE` — refutes the specific compression precondition; London-open breakout itself (baseline) shows a real, consistent positive signature worth separate attention |
| Displacement Continuation via Imbalance Stack (2+ same-direction FVGs) | 68 | consistent but **opposite-signed** to the hypothesis (stack predicts failure, not continuation); single-gap baseline mild positive | `NO_EDGE` for continuation — flagged as an unconfirmed **future** fade hypothesis (not tested cleanly here — would be circular to "confirm" on the same data that revealed it) |
| Regime-Conditional Momentum Persistence (TRENDING gate on ROC signal) | 3047+953 (disc), 915+286 (val) | TRENDING expectancy ~flat (+0.008/+0.058), not different from non-trending (−0.040/**+0.073**) | Hypothesis closed: **regime-as-standalone-gate does not add value** to a raw momentum signal here |
| Asian Range Breakout Fade (open-source) | 636 | consistent sign but economically negligible (~0.01-0.03R, below any realistic cost) | `NO_EDGE` |
| **Volatility_Breakout — confirmed-breakout arm** (range breakout + TR>1.0×ATR confirmation) | 927 | **consistent AND growing**: +0.037R (disc) → +0.133R (val) | `PROMOTE_TO_IMPLEMENTATION` — the corpus's clearest surviving native **volatility-expansion-breakout** signal |
| Volatility_Breakout — fade arm | 858 | negative, and a specification artifact (near-zero-R degenerate events) inflates MAE stats | `NO_EDGE` (with an explicitly flagged measurement artifact, not leakage) |
| Weekly Day Reversal (Monday fades Friday) | 50 | sign inverts, n too small | `INSUFFICIENT_SAMPLE` |

- **RE-CLASSIFICATION**: this phase is the single best-controlled evidence in the corpus **against** "compression precedes expansion" and "failed breakout fades" as standalone native hypotheses, and the best-controlled evidence **for** "ATR-confirmed range breakout continuation" (Volatility_Breakout confirmed arm) as a real, promotable volatility-expansion edge component.

### G3. `NEXUS - Strategy Foundry Phase 3 Volatility Breakout Implementation.md`

- **EVENT**: same ATR-confirmed range-breakout event, ported faithfully to Python (927/927 identical events vs Phase 2 screening) and to MQL5 (selector 56).
- **SIGNAL-LEVEL PARITY**: MT5 vs Python — 0 signal-logic mismatches; discrepancies fully explained by bar-alignment/tick-timing and a global exposure-cap gate (both environment effects, not signal-logic bugs).
- **LIVE (Fast Structural) TEST**: 6 months real-tick, n=14, PF 1.165, but concentrated in 2 of 5 active months (Mar+Aug), one month (July) with zero signals, marked BUY/SELL asymmetry (PF 0.73 vs 2.24) on too-small per-side samples.
- **CONCLUSION**: `HOLD_NEEDS_MORE_EVIDENCE` — explicitly *not* promoted to a full 3-year validation despite PF>1, because the live sample is too thin and temporally concentrated to trust.
- **RE-CLASSIFICATION**: **EDGE_COMPONENT: volatility-expansion-breakout — SUPPORTED, MEDIUM strength** (large, clean offline discovery+validation sample; faithful, bug-free signal-level port to the live engine; but live/executable sample still thin, n=14). This is the strongest surviving native (non-borrowed) edge candidate found via the Foundry process, but not yet at "confirmed edge" status per the new framework's own bar.
- Also documents a real infrastructure bug found along the way: a brand-new strategy silently produced 0 trades from 1047 raw signals because the auto-generated strategy whitelist (`NXS_StrategyKnown()`) had not been updated — same class of bug as `THIRD_SILENT_GATE` in E1.

---

## GROUP H — SAR / MACD / ADX_RSI Trend/Momentum Validation

### H1. `NEXUS - First Serious 3Y Validation SAR MACD.md`

- **EVENT**: PSAR-flip+EMA9/21-cross (**trend-reversal/trend-persistence** signal) for SAR; MACD-cross+EMA200-gate (**momentum**) for MACD — both H4, 3-year real-tick MT5 Model=4.
- **OUTCOME METRIC**: PF, expectancy, yearly/half decomposition, OOS split, cost-stress robustness (native/conservative/stress spread).
- **BASELINE**: explicit multi-criterion gate (PF>1, ≥2/3 years non-materially negative, no extreme directional dependence, OOS doesn't collapse, cost-robust).
- **SAR**: n=240, PF 1.281, DD 6.65%. 2 of 3 years non-materially negative (Year 3 carries nearly all profit). OOS (last 22.5%) **improves** on every metric. Cost-stress barely dents PF (1.281→1.277). **One failing criterion**: SELL PF=0.84 over the full 3 years (92 trades, 38% of sample) — a real, quantifiable, if not extreme, directional asymmetry, resolved in the OOS segment (SELL PF 1.26 there) but present in aggregate. **Verdict: `SERIOUS_VALIDATION_BORDERLINE`.**
- **MACD**: n=115, PF 1.122 (thin margin), only 1 of 3 years positive (Year1 −$165, Year2 −$49, Year3 +$763 — Year3 alone exceeds the entire 3-year net), IS segment (77.5% of sample) net-negative (PF 0.968) with **SELL PF=0.13 in-sample** (near-total collapse), OOS strong but that's exactly the problem — the whole positive 3-year record rides on the most recent 22.5%. **Verdict: `SERIOUS_VALIDATION_FAIL`** (two clean-failing criteria, not borderline). No rescue attempted (explicitly disallowed).
- **RE-CLASSIFICATION**: SAR — **trend-persistence/reversal signal, BORDERLINE SUPPORTED**, medium-high evidence strength (multi-year real-tick, OOS-improving, cost-robust) but with a real, unresolved directional (SELL-side) weakness that must be treated as part of the edge's true shape, not noise to filter away. MACD — **REFUTED as a standalone 3-year edge**; its apparent profitability is a recency/regime artifact (nearly all of it in the final 22.5% of the sample), a textbook illustration of why "the aggregate PF is positive" is insufficient evidence without temporal decomposition.
- **FAILURE PATTERN**: neither is a "failure" of process — both are examples of a properly-run 3-year decomposition correctly separating a real (if imperfect) signal from a recency-driven false one. Worth flagging as a positive counter-example to failure patterns elsewhere.

### H2. `NEXUS - SAR Independent Historical Confirmation.md`

- **EVENT**: attempt to find a genuinely untouched pre-2023 period to test SAR's trend-persistence signal independent of the training/validation history.
- **KEY STRUCTURAL FINDING**: **no period before 2023-09-01 has real MT5 tick data on this broker/demo at all** (`real ticks begin from 2023.09.11`) — the "Serious 3Y" window (H1) already consumes essentially the entire tick-real history available in this environment. This is reported transparently as an absolute environmental data limit, not worked around with synthetic ticks.
- **SUPPLEMENTARY (non-equivalent) EVIDENCE**: same frozen SAR config replayed on the Python engine (different engine, different position sizing, not $-comparable) on the true pre-2023 Dukascopy history: PF 0.93 (2019-08→2021-08) and 0.97 (2021-08→2023-08) — both **just under 1**, with the same SELL-side weakness pattern (SELL PF 0.73-0.78 vs BUY ~1.02-1.04) persisting across a completely different engine and period.
- **CONCLUSION**: `SAR_INDEPENDENT_CONFIRMATION_BORDERLINE` — not a PASS (the only available independent evidence is negative-leaning and cross-engine) and not a FAIL (the decisive MT5 real-tick test is structurally impossible here, not failed).
- **RE-CLASSIFICATION**: the SELL-side asymmetry of the SAR signal is now supported by **two independent engines and periods** — raises confidence that it is a structural property of the PSAR+EMA9/21 signal itself (or possibly of this era of gold's price behavior generally) rather than overfitting to the MT5 3-year window. This is genuine cross-validation evidence, just not of the type originally requested.
- **FAILURE PATTERN**: a good example of transparently reporting an environment-imposed limit (tick-data availability boundary) rather than silently substituting synthetic data — flagged as a positive methodology note, and as an important environmental constraint for any future SAR/MACD replication effort (`ENVIRONMENT_TICK_DATA_BOUNDARY`, informational, not a bug).

### H3. `NEXUS EA - ADX_RSI D1 Confermata Positiva sul Vero MT5, BUY Domina (04-09).md` / H4. `NEXUS EA - MACD H4 Confermata Positiva, Terza Conferma BUY-Dominante (04-09).md`

- **EVENT**: ADX/RSI-based D1 trend-following signal; MACD H4 signal (different config from H1's MACD) — both single 3-year MT5 backtests.
- **ADX_RSI**: n=51, PF 2.04, but **BUY 44 trades / SELL 7 trades** — SELL is pure noise (net ~$28 on 7 trades). MAX DD 59.6% of a $1000 account — flagged by the author as severe.
- **MACD (H4 variant)**: n=199, PF 1.53, **BUY 129/SELL 70**, SELL again near-breakeven ("+$162, practically breakeven noise").
- Both reports explicitly note this is the **third same-day confirmation of the identical BUY-dominant pattern** (with BOLLINGER also same day) and flag the leading hypothesis as: this likely reflects the period's secular gold rally (+125% over 2023-09→2026-08, independently verified on Dukascopy) rather than a genuine trend/momentum edge independent of regime.
- **RE-CLASSIFICATION**: **EDGE_COMPONENT: directional trend-following in a strong bull regime — SUPPORTED only conditionally, LOW-MEDIUM strength.** These are single, non-cross-validated MT5 backtests over a period the reports themselves flag as regime-confounded (one dominant secular trend). Should **not** be read as "trend persistence" or "momentum" edge components independent of market regime — that distinction has not been tested (no regime-segmented or bear/range-period validation exists in this corpus for ADX_RSI/MACD-H4/BOLLINGER's BUY-dominance).
- **FAILURE PATTERN**: `TREND_DRIVEN_EDGE_CONFOUND` (catalogued below #18) — the reports self-flag this, an unusually disciplined admission worth preserving.

### H4b. `NEXUS EA - SAR Confermata Positiva Invalidata, il Bug Nascondeva un Freno di Sicurezza (08-09).md` → `NEXUS EA - SAR Verdetto Definitivo, Confermata Sopravvive PipSeq No (08-09).md`

- **EVENT**: same SAR family, but with `PipSeq` (chained re-entry after a pip move — a distinct, session/streak-driven re-entry mechanism, not the base sweep/trend event).
- **BUG FOUND**: `InpRiskProfile` was silently forcing the BALANCED preset (hard 5% daily-DD cap) regardless of the `.ini`'s explicit `Custom`/`InpMaxDailyDDPct=100.0` request — meaning the "confirmed positive" PipSeq-stress-test result (PF 2.02, DD 34.39% balance) was actually running with an unrequested safety net. Once the bug was fixed and the true unconstrained-risk config ran: **PF dropped to 1.90, DD balance jumped to 42.54%, DD equity to 53.67%** (well past any usable threshold) — the "airbag" had been silently preventing worse compounding of same-day losses.
- **RESOLUTION**: re-running the other 4 (non-PipSeq) windows showed them **byte-identical** pre/post-fix — the bug only manifests when a strategy attempts *multiple new position opens on an already-bad day* (PipSeq's re-entry mechanism), which the base SAR candle-align config never does. Base SAR config confirmed still valid (PF1.37-1.57 across step22-25); only the PipSeq variant is invalidated.
- **RE-CLASSIFICATION**: not a market-event finding — a **risk-infrastructure integrity finding**. Important because it shows a backtest "edge" can be partly an artifact of an *unintended, undisclosed risk control* rather than the signal itself — the true risk profile of a signal is only knowable once every implicit safety mechanism is either removed or explicitly declared.
- **FAILURE PATTERN**: `HIDDEN_SAFETY_NET_MASKING_TRUE_RISK` (catalogued below #11); also demonstrates that "theoretical exposure to a bug does not imply real impact — it depends on the exact mechanism" (verified twice in the same day per the source note) — a useful general auditing principle.

---

## GROUP I — ESL (Equity Stop Loss) Discovery and Correction

### `NEXUS EA - Scoperta ESL, Costo Nascosto Trasversale a Tutti i Test (06-09).md` → `...ESL Corretto, Disattivarlo Peggiora ADX_RSI (06-09).md`

- **EVENT**: not a market event — a **risk-management mechanism** (account-level equity circuit breaker, forced-close at -5% floating equity) whose interaction with ADX_RSI's wide (10×ATR) targets was mis-diagnosed on first pass.
- **INITIAL (WRONG) READ**: ESL-tagged exits ("dd" in trade comments) were, per-trade, the single most costly exit category (avg -$85 to -$87 vs -$23 to -$30 for genuine SL) — naively suggesting ESL was "hurting" the strategy.
- **CORRECTED READ (explicit A/B test, ESL on vs off, same 51 trades)**: disabling ESL **worsens** the result materially — PF 2.04→1.26, net +$1675.65→+$573.18, max DD equity $596→**$1470 (147% of a $1000 deposit — margin-call territory)**. The 7 SELL trades specifically go from near-breakeven (+$28, 14.3% WR) to a **total loss with 0% WR** when the safety net is removed on the exact same trades — direct proof ESL was cutting losses at the right moment, not prematurely.
- **RE-CLASSIFICATION**: not an edge component, but a **methodology lesson explicitly generalized by the source reports**: a high average cost within one exit category does not imply that removing the category improves the result — the correct test is always the direct with/without comparison on identical trades, never the isolated-category cost alone.
- **FAILURE PATTERN**: `COST_CATEGORY_MISREAD_AS_NET_HARM` — a specific instance of drawing a causal conclusion from a marginal/conditional statistic (catalogued below #22, related to but distinct from `HIDDEN_SAFETY_NET_MASKING_TRUE_RISK` — here the safety net helps and the analyst initially misread it as harmful; in H4b the opposite situation occurs, a hidden safety net inflating a result that looked purely signal-driven). The two together form a matched pair worth remembering: **safety mechanisms can equally mask a signal's true weakness (H4b) or be misdiagnosed as unwanted cost when they are in fact doing their job (Group I)** — never trust either direction without a controlled comparison.

---

## GROUP J — Broker Cost Model & 67-Strategy Cost-Calibrated Re-Evaluation

### J1. `NEXUS - Broker Cost Model Audit.md`

- **EVENT**: not a market event — an audit of whether the Python backtest engine's cost assumptions (`retail_standard`: 25 pip spread, `ecn`: 9 pip, both $0 commission) reflect reality.
- **MEASUREMENT**: live broker spread sampled directly (900 ticks / 15 min): median 5.4 pip. Commission measured from 79 real historical deals: **exactly $0.00** on every one. No scaling/double-counting bug found in the cost-application code (verified via an independent gross-vs-net reconciliation).
- **IMPACT TEST (3 representative strategies)**: `EMA_PULLBACK`'s verdict **flips FAIL→PASS** (PF 0.93→1.28) purely from correcting the spread assumption (old model was eating 123% of gross edge; realistic model eats 34%). `BREAKOUT_ACC` and a genuinely negative strategy (`THREE_BAR_DELIVERY_BREAK`) are unaffected either way.
- **RE-CLASSIFICATION**: **critical validity finding, not an edge component itself** — but essential context for every PF number computed via `server/backtest.py`'s cost presets anywhere else in this corpus (including several Strategy Foundry results): a PF near 1.0 under the old cost model is not reliable evidence of "no edge" and must be re-checked under the broker-realistic model.
- **FAILURE PATTERN**: `COST_MODEL_MISCALIBRATION` (catalogued below #10).

### J2. `NEXUS - 37 Strategy Cost-Calibrated Re-Evaluation.md`

- **EVENT**: same cost-model correction, extended and statistically re-derived (24.1M real ticks, 75 days) into 3 frozen cost profiles (BROKER_BASELINE $0.55/5.5pip, CONSERVATIVE $0.70/7pip, STRESS $1.30/13pip — each anchored to a measured percentile, not an arbitrary multiplier), then applied to **all 67** research-implemented strategies (not 37 — a scope correction made in the same report).
- **RESULT**: **13 historical false negatives** identified (strategies that FAIL under the old cost model but PASS under BROKER_BASELINE), including `MALAYSIAN_SNR_V2_STAGE3`, `FVG_MIT_WINDOW`, `Z_SCORE_BREAKOUT`, `AMD_CONT`, `ICHIMOKU`, `NY_REVERSAL`, `SH_BMS_RTO_V2`, `LONDON_BO`, and others (full list in the report). **0 false positives** (nothing that passed old-cost fails new-cost, as expected since old costs were strictly higher). 28 strategies remain genuinely negative under both models. 18 strategies classified `ROBUST_POSITIVE` and promoted to `SERIOUS_BACKTEST_CANDIDATE`.
- **RE-CLASSIFICATION**: this does not itself validate any strategy as a true edge (no walk-forward/OOS/live confirmation performed here beyond the existing OOS 60-100% slice) — but it substantially **changes which prior "no edge" verdicts in this corpus should be considered provisional** rather than final, specifically for any strategy in the false-negative list whose earlier closure (in other reports) relied on the old cost model.
- **FAILURE PATTERN**: same `COST_MODEL_MISCALIBRATION`, now quantified project-wide.

---

# SYNTHESIS

## EDGE_COMPONENTS — supported (with strength), refuted, or unknown

### Supported (evidence in hand)

| Edge component | What supports it | Strength |
|---|---|---|
| **Volatility-expansion breakout** (range breakout confirmed by TR > 1.0×ATR on the breakout bar) | Strategy Foundry Phase 2 (n=927, consistent growing effect discovery→validation, +0.037R→+0.133R); Phase 3 faithful MT5 port with 0 signal-logic mismatches (927/927 identical events) | **MEDIUM** — large, clean offline sample + bug-free live port, but live/executable sample thin (n=14, `HOLD_NEEDS_MORE_EVIDENCE`, not yet a confirmed edge |
| **Trend-persistence/reversal via PSAR flip + EMA9/21** (SAR family) | 3-year MT5 real-tick (PF 1.281, OOS improves on every metric, cost-robust); independent cross-engine (Python, different sizing) evidence on a disjoint pre-2023 period shows the same directional signature | **MEDIUM-HIGH** for the phenomenon existing at all, but the edge is asymmetric — see refutation-adjacent caveat below |
| **Broker cost realism as a validity gate** (not a market edge, but a required correction) | 24.1M real ticks + 79 real deals measured; flips 13/67 strategy verdicts | **STRONG** — directly measured, not estimated |
| **Liquidity reclaim as a favorable confirmation *signature*** (not yet a tradeable edge) | WICK_SWEEP shadow: real (not idealized) sweep→reclaim population shows WR 59.2% vs 16.9% no-confirmation baseline — a real, large gap in the underlying phenomenon | **WEAK-MEDIUM as phenomenon, REFUTED as a currently-executable edge** — see refutation table; the gap between "phenomenon is real" and "capturable by any tested execution model" is the central lesson of Group E5 |

### Refuted (with reason)

| Edge component (as tested) | Reason refuted | Source |
|---|---|---|
| Day-of-week (Friday) effect on WICK-sweep outcome | Sign inverts across 2 of 3 independent confirmatory periods | A1-A3 |
| Level age (OLD vs YOUNG) as WICK-sweep-outcome predictor | Sign inverts / unstable across all 3 independent periods | A1-A3 |
| `penetration_per_atr` / age<1h / source_tf=D1 as TRUE_BREAK precursor (structural, SH_BMS_RTO) | age/source_tf are confounds for "Asia-Low/BUY" only; penetration/ATR replicates direction but misses the pre-declared materiality bar on 3rd independent period | B6 |
| TRUE_BREAK-quality features (15 frozen features) predicting continuation vs failure | No signal on adequate sample (n=344), model doesn't beat majority baseline | B7 |
| RETEST-quality features (15 frozen features) predicting HOLD vs FAIL | No signal on adequate sample (n=64) | B8 |
| Failed-breakout fade | Sign inverts discovery→validation | G2 |
| Volatility-compression-percentile precondition before breakout | Consistently negative, worse than no-compression baseline | G2 |
| Session (Asia) compression → London-open expansion precondition | Sign inverts; plain London-open breakout (no precondition) stays positive | G2 |
| Displacement/imbalance-stack continuation | Opposite-signed, consistent (stack → failure, not continuation) | G2 |
| Regime (ADX trending) as a standalone gate on a momentum signal | No material expectancy difference trending vs non-trending | G2 |
| Pivot-fractal + wick-rejection touch (PIVOT_WICK, all isolated/combined variants) | No PF>1 variant found; sole apparent improvement (close-confirmation) fails at 3-year scale | F1 |
| Pivot+SNR breach-depth-gated level reaction (LEVEL_REACTION/LEVEL_CONFLUENCE family) | Best-in-family small-sample near-breakeven result widens to PF 0.80 at 3-year scale | E3 |
| WICK-sweep immediate fade (`WICK_SWEEP_REV`) | Persistently negative baseline (PF 0.78-0.97) across every validated run; formally frozen as negative research baseline | Group C, E4 |
| WICK-sweep liquidity-reclaim, executed (M15-gated real, tick-detection, tick-limit-retest, fill-anchored variants) | Shadow edge (PF 5.80) is an execution-price fiction; every real-execution variant tested has PF ≤ 0.80 | E5 |
| MACD (H4, 3-year) as a standalone edge | Only 1 of 3 years positive; entire net profit from final 22.5% of sample; in-sample SELL PF 0.13 | H1 |

### Directionally-conditional / caveated (neither cleanly supported nor refuted)

| Edge component | Caveat |
|---|---|
| ADX_RSI / MACD(H4-variant) / BOLLINGER "BUY-dominant confirmed positive" | Single, non-regime-controlled MT5 backtests over a period with a +125% secular gold rally; authors themselves flag likely trend-regime confound rather than a genuine trend/momentum edge independent of regime — **not validated as regime-independent** |
| SAR's SELL-side weakness | Structural, appears on 2 independent engines/periods (PF 0.84 3y MT5; PF 0.73-0.78 pre-2023 Python) — this is real evidence the *edge itself is asymmetric*, not evidence the edge is absent; treat SAR as "BUY-dominant trend-persistence signal with a documented SELL-side deficiency," not a symmetric edge |

### Unknown / untested

- `STRUCT_LEVEL_SWEEP` as a live strategy (design + offline Python exploratory stats exist; no MQL5 telemetry, no trade-level test, no SL/TP/BE/runner logic ever built or run)
- `WICK_TICK_NATIVE` (backlog idea, zero implementation)
- Breach-depth (>100pip "structural break" threshold) as validated on the *actual* LEVEL_REACTION/STRUCT_LEVEL_SWEEP populations (the 99.5/78.9/69.1% figures come from an unrelated, unreplicated external pivot study)
- Displacement-imbalance-stack **fade** (opposite-sign finding from G2, explicitly reserved for a fresh, non-circular discovery/validation split — never tested cleanly)
- COT/positioning data as a signal source (no clean data pipeline built)
- Raw-level reclaim (vs trigger-price reclaim) distinction for `WICK_SWEEP_RECLAIM` (hooks identified, `SNxsWickShadowEvent.reclaimed_level` exists but was never wired into the Unified Level Engine)
- OB/FVG level replication in the STRUCT_LEVEL_SWEEP Python dataset (deferred, ATR-dependency not yet handled)
- TURTLE_SOUP / JUDAS_SWING / LDN_REVERSAL / PO3 historical baselines on windows where they produced real trades (code-level exposed to the uninitialized-memory bug from Group D, but not yet re-verified on any window where they actually traded)

---

## FAILURE PATTERN CATALOG (consolidated, all instances found)

1. **`MULTIPLE_COMPARISONS_NO_CORRECTION`** — WICK Sweep Experiment 1 ran ~25 univariate bucket comparisons, Structural Causal Experiment 1 ran 39, Thread 3 ran 54, Thread 4 ran 57 — none formally corrected for multiple comparisons; mitigated only by requiring out-of-sample confirmation before promotion (`NEXUS - Causal Experiment 1 WICK Sweep 1R Outcome.md`, `NEXUS - Structural Causal Experiment 1.md`, `NEXUS - Causal Research Thread 3 Final v3.md`, `NEXUS - Causal Research Thread 4 Retest Quality.md`).

2. **`AMBIGUOUS_SAME_BAR_RATE_ELEVATED`** — a fixed R=25 pip threshold on H4 GOLD produces 27-46% unresolved/ambiguous outcomes across nearly every causal experiment in the corpus, always excluded rather than imputed but a persistent power/precision limitation (`NEXUS - Causal Experiment 1...md` 2.6%, `Structural Causal Experiment 3` 45.6%, `Causal Research Thread 3 True Break Quality` 43.9%, `Causal Research Thread 3 Final v3` 38.4%, `Structural Dataset v1` 34.9-45.6%).

3. **`SHADOW_EXECUTION_ASSUMPTION`** — a virtual/shadow simulation assuming an idealized fill (exactly at trigger price) is not performance evidence until validated against real execution. Central failure of the WICK_SWEEP_RECLAIM line: shadow PF 5.80 vs real PF 0.78-0.80 (`NEXUS EA - WICK_SWEEP Entry Timing Study...md`, §7-11).

4. **`TIMEZONE_MISMATCH`** — combining MT5 timestamps (broker time, UTC+3) with an external tick source (Dukascopy, UTC) without a declared/verified offset produced impossible slippage figures (100-400+ pip) and negative-PnL "TP" outcomes on the first pass (`NEXUS EA - WICK_SWEEP Entry Timing Study...md`, §12-13).

5. **`DATA_COVERAGE_GAP`** — Dukascopy tick fetch missing ~53% of weekday hours on first attempt, ~21% residual after gap-fill retries; flagged via a `data_gap_suspect` field and excluded from aggregate stats rather than silently included (`NEXUS EA - WICK_SWEEP Entry Timing Study...md`, §12).

6. **`CAUSAL_HOOK_MISMATCH`** — a diagnostic/shadow hook attached at a different point in the real execution pipeline than the logic it is meant to mirror diverges even when its internal logic is identical. Occurred 3 times sequentially in the same shadow-validation effort (one-shot mismatch, pre-New-Bar-Gate sampling, pre-upstream-gates sampling) before reaching exact parity (`NEXUS EA - WICK_SWEEP Entry Timing Study...md`, §6); also the root cause of 2 bugs caught (and safely fail-closed) by the Unified Level Engine's comparator in Phase C (`NEXUS - Unified Level Engine Phase C WICK Read Path Migration.md`).

7. **`EVENT_ID_NOT_UNIQUE_ACROSS_WINDOWS`** — `event_id` resets to 1 on every separate Tester run/window; indexing lifecycle events by `event_id` alone (instead of `(window_id, event_id)`) silently collapses cross-window collisions, corrupting labels. Found and fixed independently in at least 2 places: `NEXUS - Structural Causal Experiment 1.md` (2108/2382 event_ids shared across windows, one window's episodes zeroed out) and `NEXUS - Phase C1 Orphan TRUE_BREAK Audit.md` (283 vs 288 cosmetic undercount in a diagnostic print).

8. **`LEVEL_SCOPE_VS_EPISODE_SCOPE_LEAKAGE`** — linking lifecycle events (TRUE_BREAK/RETEST/INVALIDATE) at the granularity of a `structural_level_id` (a price level, which can host many independent sweep episodes over time) instead of a proper episode identity causes cross-episode leakage. Overstated `TRUE_BREAK_OCCURRED` by ~17x (19.5% vs true 1.16%) in `NEXUS - Structural Dataset v1.md`, corrected in `NEXUS - Structural Dataset v1 Causal Linkage Integrity Audit.md`.

9. **`MULTI_TF_PASS_DESYNC`** — `NXS_CollectAllSignals`'s architecture evaluates the same shared strategy state once per active timeframe pass within a single real tick; the first pass to arrive mutates shared state, later passes in the same tick see already-mutated state and use inconsistent per-TF bar data. Root cause of ~69.3% spurious exclusion rate in the pre-fix TRUE_BREAK-quality dataset (`NEXUS - Structural Lifecycle Sample Recovery.md`) and of thousands of multipass-duplicate sweep observations (`NEXUS - Causal Research Thread 2 Phase A1 Shared Sweep Instrumentation.md`).

10. **`UNINITIALIZED_STRUCT_MEMORY`** — a local MQL5 struct (`SNXSSweepExt`) was not reliably zero-initialized by the runtime despite a code comment asserting it would be; produced `confirmed=true, dir=NONE` garbage states affecting ~65% of raw detector observations, and fabricated a fully fictitious historical winning trade for `AMD_REVERSAL` via a garbage `refLow` value used directly in an SL calculation (`NEXUS - SNXSSweepExt Detector Integrity Fix.md`, `NEXUS - SNXSSweepExt Semantic Impact Audit.md`).

11. **`SIGNAL_PRICE_VS_EXECUTION_PRICE_MISMATCH`** — SL/TP computed from a signal/trigger price that can be several bars stale by the time a real market order fills; measured median 42.6 pip favorable slippage on WICK_SWEEP_RECLAIM, which mechanically inflated the shadow's apparent PF and could not be fixed by re-anchoring to the real fill (that made results worse) — flagged by the source report as a potentially general issue for any strategy computing SL/TP at signal-generation time rather than execution time (`NEXUS EA - WICK_SWEEP Entry Timing Study...md`, §10-11).

12. **`COST_MODEL_MISCALIBRATION`** — the Python backtest engine's `retail_standard` cost preset (25 pip spread) is ~4.6x the measured real broker median spread (5.5 pip); flips the PASS/FAIL verdict on 13 of 67 strategies, most dramatically `EMA_PULLBACK` (PF 0.93 FAIL → 1.28 PASS) (`NEXUS - Broker Cost Model Audit.md`, `NEXUS - 37 Strategy Cost-Calibrated Re-Evaluation.md`).

13. **`HIDDEN_SAFETY_NET_MASKING_TRUE_RISK`** — `InpRiskProfile` silently forced a 5%-daily-DD BALANCED preset regardless of an explicit `Custom`/100% request; a SAR-PipSeq "confirmed positive" stress-test result (PF 2.02) was actually running under an unrequested safety cap — the true unconstrained result was materially worse (PF 1.90, DD equity 53.67% vs 45.47%) (`NEXUS EA - SAR Confermata Positiva Invalidata...md`, `NEXUS EA - SAR Verdetto Definitivo...md`).

14. **`THIRD_SILENT_GATE`** — the auto-generated strategy whitelist (`NXS_StrategyKnown()`/registry) silently rejects any real signal from a strategy not yet registered in the source-of-truth JSON, producing a false "zero trades" reading that looks like "no edge" but is actually an infrastructure gap. Documented for WICK_SWEEP_REV (`NEXUS EA - Audit Structure-Reaction-LEVEL_REACTION...md`), previously for 7 other strategies, and again for `VOLATILITY_BREAKOUT_CONFIRMED` (`NEXUS - Strategy Foundry Phase 3...md`).

15. **`SMALL_SAMPLE_NEAR_BREAKEVEN_MISTAKEN_FOR_CONFIRMATION`** — a small-sample result close to the breakeven win-rate threshold is not confirmation; the gap-to-breakeven can widen severalfold (or the sign can reverse) once the sample scales 5-6x. Documented explicitly, twice, as "the same pattern" by the source reports: `LEVEL_CONFLUENCE` and `LEVEL_REACTION` (`NEXUS EA - LEVEL_REACTION 3 Anni...md`) and `PIVOT_WICK RequireCloseConfirm` (`NEXUS EA - PIVOT_WICK step2...md`, Addendum 8).

16. **`VOLUME_REDUCTION_MISTAKEN_FOR_EDGE_IMPROVEMENT`** — a filter that reduces trade count reduces net loss/gain proportionally without necessarily changing win rate, payoff, or PF; must always be checked against PF/expectancy, not net PnL alone. Documented for `OneShotLevel` and `RegimeVeto` on PIVOT_WICK (`NEXUS EA - PIVOT_WICK step2...md`).

17. **`STACKED_FILTERS_COLLAPSE_SAMPLE`** — combining several individually-tested filters (even inert or mildly negative ones) can collapse the sample to statistical meaninglessness (5 trades, then 0 trades) before any combined effect can be measured (`NEXUS EA - PIVOT_WICK step2...md`, Addenda 3 and 7).

18. **`CONFOUNDED_FEATURE_VIA_DETERMINISTIC_MAPPING`** — two apparently-independent, apparently-confirmed features (`age_seconds<1h`, `source_tf=D1`) turned out to be ~87-92% the same subset due to a hidden deterministic formula artifact (`created_time` anchoring), and their entire uplift was concentrated in one hardcoded direction-mapped sub-segment (Asia-Low/BUY, 42.2% vs Asia-High/SELL 0.0%) — caught only by the mandated BUY/SELL and multi-tag robustness checks (`NEXUS - Structural Causal Experiment 2 Confirmatory.md`).

19. **`TREND_DRIVEN_EDGE_CONFOUND`** — a strongly BUY-dominant "confirmed positive" result on 3 different indicator families (ADX_RSI, MACD-H4, BOLLINGER) on the same day is most plausibly explained by the period's +125% secular gold rally, not by a trend/momentum edge independent of regime; the reports self-flag this rather than claiming a validated edge (`NEXUS EA - ADX_RSI D1 Confermata Positiva...md`, `NEXUS EA - MACD H4 Confermata Positiva...md`).

20. **`STALE_LEVEL_AGE_BIAS`** — an unbounded-lifetime level pool produces "touches" on levels created up to a year earlier, at a completely different price regime, generating nonsensical MFE/MAE statistics (median MFE_1h of -1640 pip) until filtered to a bounded freshness window (<=30 days), after which the same bin reads sanely (`NEXUS EA - Dataset Python STRUCT_LEVEL_SWEEP...md`).

21. **`COST_CATEGORY_MISREAD_AS_NET_HARM`** — a high average per-trade cost within one exit category (ESL-forced closes averaging -$85 to -$87 vs -$23 to -$30 for genuine stop-losses) does not imply removing that category improves the result; the correct test is a direct with/without comparison on identical trades, which showed the opposite (disabling ESL turned a near-breakeven SELL side into a total loss) (`NEXUS EA - Scoperta ESL...md`, `NEXUS EA - ESL Corretto...md`).

22. **`DUPLICATE_TEST_NOT_ISOLATING_VARIABLE`** — a test intended to isolate one variable (`InpEnableSplit=true`) compared ON against ON because the flag's default had silently changed to `true` earlier in the same session, producing a byte-identical "control" result that isolated nothing (`NEXUS EA - PIVOT_WICK step2...md`, Addendum 4).

23. **`ENVIRONMENT_TICK_DATA_BOUNDARY`** (informational, not a code bug) — this broker/demo's real-tick history begins 2023-09-11; no period before that date can be tested with genuine real ticks in this environment, a hard boundary discovered while attempting an independent pre-2023 SAR validation (`NEXUS - SAR Independent Historical Confirmation.md`).

24. **`EXIT_AUTHORITY_TAG_LOSS`** — MT5's `DEAL_REASON` field collapses every EA-initiated close (including opt-in protections like ESL) to a generic `"expert"` code, losing the specific `NXS:DD`/`NXS:RISK` tag written in the deal comment — causing the RAW-mode exit-authority invariant to falsely flag legitimate opt-in protection closes as unexplained "OTHER" violations (`NEXUS EA - WICK_SWEEP_REV Registrato, 50 Trade Reali...md`).

---

## Files reviewed (this pass)

Causal/structural research: `NEXUS - Causal Experiment 1/2/3`, `NEXUS - Causal Research Thread 2 Phase A/Phase A1/Reclaim False Break Feasibility`, `NEXUS - Causal Research Thread 3 Final v3/True Break Quality`, `NEXUS - Causal Research Thread 4 Retest Quality`, `NEXUS - Structural Dataset v1` (+ Causal Linkage Integrity Audit), `NEXUS - Structural Lifecycle Sample Recovery`, `NEXUS - Phase C1 Orphan TRUE_BREAK Audit`, `NEXUS - Structural Causal Experiment 1/2/3`, `NEXUS - Unified Level Engine Phase A/B/C/D/E`, `NEXUS - SNXSSweepExt Detector Integrity Fix`, `NEXUS - SNXSSweepExt Semantic Impact Audit`.

Strategy Foundry: Phase 1, Phase 2 (Causal Screening), Phase 3 (Volatility Breakout Implementation).

Validation: `NEXUS - First Serious 3Y Validation SAR MACD`, `NEXUS - SAR Independent Historical Confirmation`.

Cost model: `NEXUS - Broker Cost Model Audit`, `NEXUS - 37 Strategy Cost-Calibrated Re-Evaluation`.

Dated NEXUS EA reports: Audit Structure-Reaction-LEVEL_REACTION e WICK_SWEEP (10-09); LEVEL_REACTION Merge (06-09); LEVEL_REACTION Primo Risultato / 3 Anni (07-09); WICK_SWEEP_REV Registrato (10-09); WICK_SWEEP Entry Timing Study (11-09); WICK_SWEEP_RECLAIM_TICK Design Candidate (12-09); PIVOT_WICK step2 (03-09); Dataset Python STRUCT_LEVEL_SWEEP (10-09); STRUCT_LEVEL_SWEEP Audit (10-09); Scoperta ESL / ESL Corretto (06-09); ADX_RSI D1 Confermata (04-09); MACD H4 Confermata (04-09); SAR Confermata Positiva Invalidata / SAR Verdetto Definitivo (08-09).

**Total: 34 source reports reviewed and re-classified.**
