# NEXUS RRA-02 — Final Research Architecture Addendum

**Decision:** Scenario B — controlled evolution  
**Baseline audited:** `origin/main@a61bca3db6d2bc8ef4f477c1bf59eee827527c40`  
**Status:** ROADMAP_READY_FOR_REVIEW — no pilot executed  
**Inputs:** RRA-01, RRA-02 independent-review reconciliation, Phase 5–7 artifacts, Behavior Lab, RI-01/RI-02, edge/component registries.

This addendum does not replace RRA-02 and does not repeat the seven censuses. It converts the reconciled findings into one implementation architecture. Repository evidence wins over either AI audit; unavailable evidence remains `UNKNOWN`.

## 1. Architecture Decision Card

### Decision

Build one causal **Research Event/Feature Layer** shared by three research views:

1. **Strategy-first** evaluates an operational strategy definition.
2. **Event-first** estimates distributions after a preregistered causal event.
3. **Outcome-first** studies antecedent conditions of a preregistered movement and produces hypotheses only.

They share dataset identity, bars, causal timestamps, event/feature contracts, matching, dependence diagnostics, multiple-testing accounting, ResearchMemory, evidence grades and approval boundaries. They are adapters over the same evidence pipeline, not independent engines.

### Why

- Phase 5 already has H4 market state, causal event construction and outcomes.
- Phase 5.5 already has leakage, dataset, regime, redundancy and multiple-testing controls.
- Phase 7 already has BaselineEngineV4, matched-pair sign-flip, control-reuse accounting, dependence diagnostics, preregistration provenance and post-hoc quarantine.
- Behavior Lab already has deterministic tick-to-bar construction, H4/M15 alignment, causal event/outcome logic and block-bootstrap reporting.
- RI-01/RI-02 already provide append-only memory, bounded proposals, review, planning and human approval.

A new engine would duplicate controls and make scientific state diverge.

### Consequences

- Historical strategy IDs remain lineage identities; they are not assumed to be independent ideas.
- An event, feature or component has its own versioned identity and evidence, separate from standalone strategy status.
- Cross-engine parity is evaluated at bars → indicator → event → signal → decision → simulated order, never by aggregate P/L resemblance.
- Discovery cannot produce `SUPPORTED` without independent validation.
- Scientific rule changes remain human-approved and versioned.

### Non-decisions

- No new detector, pilot execution, protected holdout access, parameter sweep, EA change or economic promotion is authorized here.
- No replacement of Pandas or the current research engine is approved.
- No second memory, orchestrator, approval system or Control Center is introduced.

## 2. Research Capability & Gap Matrix

| Capability | Existing evidence / primitive | State | Reuse decision | Minimal gap / verification |
|---|---|---|---|---|
| Dataset identity and drift | `phase5_5/dataset_version_v1.json`, `phase7/engine/dataset_version_guard.py` | IMPLEMENTED | REUSE | Project all engines into one dataset lineage key; do not infer independence from different record IDs |
| Deterministic H4 bars | `phase5/build_h4_bars.py` | IMPLEMENTED | REUSE | Golden trace against the exact MT5 export/feed |
| Tick-derived M15/H4 bars | `behavior_lab_v1/bars.py`, `ticks.py` | IMPLEMENTED for BL scope | ADAPT | Generalize contract, not implementation, to additional timeframes only when data exists |
| M1–W1 universal bars | No single canonical builder covering all | PARTIAL | ADAPT | One timeframe-parameterized contract and fixture suite; no new engine |
| Market-state features | `phase5/build_market_state.py`, Phase 5.5 provenance/redundancy | IMPLEMENTED H4 | REUSE | Version feature knowledge time and timeframe explicitly |
| Events | `phase5/build_events.py` (BREAKOUT, FAILED_BREAKOUT, SWEEP, RECLAIM, RETEST and others) | IMPLEMENTED H4 | REUSE | Canonical event envelope and detector-health link |
| Behavior Lab event family | `behavior_lab_v1/events.py` | IMPLEMENTED for BL-01 | REUSE IN SCOPE | Do not conflate BL pullback with generic Phase 5.5 PULLBACK |
| Generic PULLBACK | Phase 5.5 firing rate about 83% and discovery quarantine | DEFECTIVE_FOR_DISCOVERY / semantics unresolved | DO NOT USE for discovery | Label examples and role review; frequency alone is not a fix criterion |
| Baseline matching | `phase7/engine/baseline_engine_v4.py` | IMPLEMENTED | REUSE | Freeze matching policy per experiment and record insufficient-control reasons |
| Control reuse | `control_reuse_ledger.py` | IMPLEMENTED | REUSE | Require exercised-ledger assertion end-to-end |
| Multiple testing | `multiple_testing_v2.py`, Phase 5.5 ledger | IMPLEMENTED | REUSE | Full preregistered family; no post-outcome family changes |
| Dependence | `dependence_diagnostics_v2.py`, block bootstrap, ACF/ESS | IMPLEMENTED | REUSE AS DIAGNOSTIC | Do not revive dependence-conditioned p-value/BH selection |
| Leakage/preregistration | Phase 5.5 guard; Phase 7 provenance guard | IMPLEMENTED | REUSE | Cross-platform canonical bytes for frozen artifacts remains a repair item |
| Cost modelling | Phase 7 policies and Behavior Lab analysis | IMPLEMENTED in bounded paths | ADAPT | One versioned cost-profile reference for all three paradigms |
| Sequence research | Phase 7 sequence engine and causal guard | PARTIAL; frozen SEQ-0015 topology failed | SELECTIVE REUSE | Reuse causality/contracts, not the failed conditioned gate |
| Research memory | `research_intelligence_v1/memory.py`, hash-chained JSONL | OPERATIONAL | REUSE | Add dataset/split/lineage independence eligibility |
| Autonomous loop | RI-02 planner/review/evaluation/approval bridge | PARTIAL OPERATIONAL | REUSE | Trials below; no self-approval |
| Cross-engine fidelity | many Phase 7 family-specific artifacts | PARTIAL | CONSOLIDATE | Canonical trace contract and comparator for first three families |
| TradingView | Pine implementations/manual Strategy Tester evidence | PARTIAL/MANUAL | REFERENCE | Manual export adapter with provenance; no fake automation |
| Hardware efficiency | no representative benchmark | MISSING | ADD BOUNDED BENCHMARK | Compare candidates only after correctness fixture passes |

## 3. Research Paradigms Integration Design

### Shared causal record

Every observation crossing the shared layer must carry:

- `dataset_id`, content hash, feed, instrument, timezone/calendar;
- `timeframe`, source bar interval, `observed_at`, `known_at`;
- detector/feature/component ID and version;
- parameters and code commit;
- source engine and source artifact;
- split identity and exposure class (`DISCOVERY`, `SELECTION`, `TEST`, protected classes);
- direction, magnitude and causal anchors;
- lineage IDs linking aliases, variants and derived datasets.

### Strategy-first adapter

Consumes a frozen strategy definition and shared causal records, then maps them to eligibility, entry, exit, risk and execution intent. Its evidence remains attached to the complete strategy version. It may reference component evidence but cannot inherit validation automatically.

### Event-first adapter

Consumes a frozen event population, matched non-events, outcomes and costs. It reports conditional distributions and incremental effects. The event family, matching cells, horizons and multiple-testing family are fixed before outcome access.

### Outcome-first adapter

Starts from all eligible outcomes under a frozen definition, samples the reference/non-outcome population from the same opportunity set, and examines only features known before outcome onset. Output is `HYPOTHESIS_CANDIDATE`, never edge validation.

### Shared stage boundary

`DIAGNOSTIC → SELECTION → TEST → ECONOMIC_SECONDARY → EVIDENCE → MEMORY`

- Diagnostic is outcome-blind.
- Selection is hashed before test access.
- Test retains non-evaluable cells with reason codes where required by the frozen family.
- Economic analysis cannot redefine the statistical family.
- Memory stores failures, invalid runs and inconclusive results as first-class records.

## 4. Market Perception and Component Intelligence

### Detector contract

Each detector must expose:

- stable `detector_id` and semantic version;
- event family: structure, liquidity, breakout/retest, BOS/CHOCH/MSS, OB/FVG/CRT, pattern/sequence, indicator, regime, session or confluence;
- supported timeframe(s), required fields and warm-up;
- observation bar and `known_at` rule;
- direction/magnitude schema;
- repaint/lookahead declaration;
- state ownership and cross-timeframe dependencies;
- implementation locations per engine;
- fixture/evidence references;
- health state: `IMPLEMENTED_UNVERIFIED`, `VALIDATED_ON_FIXTURE`, `DEFECTIVE`, `MISSING`, `QUARANTINED`.

No detector is built merely because its family is named here. Existing implementations are audited first. `MISSING` is not inferred when sources are incomplete; use `UNKNOWN`.

### Timeframe boundary

M1, M5, M15, M30, H1, H4, D1 and W1 use the same envelope but separate detector support declarations. Higher-timeframe data becomes knowable only after its bar closes. A lower-timeframe event may reference the last closed higher-timeframe state, never the still-forming bar.

### Component catalog projection

Project existing strategy/component registries into:

- detector;
- feature;
- regime/context;
- trigger;
- entry;
- exit;
- risk;
- execution.

Preserve all 83 historical strategy identities for lineage. Placeholder/wrapper identities remain visible but do not create duplicate executable components. `STRAT_STRUCT_REACT` sharing is recorded separately from signal origin, strategy identity, state ownership and analytics attribution.

### Incremental-contribution protocol

For a component with a plausible mechanism:

1. freeze baseline and `baseline + component`;
2. use identical opportunities, dataset, split, period, costs, direction and execution assumptions;
3. match or pair observations before outcomes;
4. report effect difference, interval, nominal sample, dependence diagnostics and regime stability;
5. account for the complete tested component family;
6. quarantine post-hoc slices;
7. require independent validation before `SUPPORTED`.

No confidence bonus, vote count or strategy count substitutes for measured incremental contribution.

## 5. Cross-Engine Parity Roadmap

### Canonical trace contract

Each trace row contains dataset/feed version, normalized bar timestamp, bar OHLC/volume semantics, indicator inputs/value, detector state, event timestamp/direction, eligibility filters, signal, simulated order intent, and—only when comparable—fill/cost fields.

Comparison order:

1. input bytes and feed metadata;
2. calendar/timezone and bar construction;
3. indicator formula and warm-up;
4. event identity and causal timestamp;
5. filters and decision eligibility;
6. signal direction;
7. simulated order intent;
8. execution/fill differences.

Stop at the first divergence and assign it in a Residual Attribution Matrix. Allowed conclusions:

- `EXACT_ON_FIXTURE`;
- `EXPLAINED_FEED_DIFFERENCE`;
- `EXPLAINED_EXECUTION_DIFFERENCE`;
- `LOGIC_MISMATCH`;
- `INSUFFICIENT_DATA`.

### First tranche

1. **MACD 12/26/9 closed-bar crossover** — reuse existing parity fixtures and explicitly freeze MT5 main/signal formula, warm-up, closed-bar indexing, timestamp and direction.
2. **BREAKOUT_ACC bar-close** — reuse Phase 7.9 event/reconstruction/execution parity artifacts; compare event eligibility before economic outputs.
3. **SAR closed-bar** — build a small common-bar fixture around the frozen SAR definition and localize the historically observed sign disagreement.

ORDER_BLOCK and other stateful/tick-sensitive families follow only after this trace contract works. MT5 remains the operational EA reference; parity does not prove profitability.

## 6. Event-first Pilot Protocol — SWEEP V1

**Status:** design only; discovery data only; not authorized to run.

- **Mechanism:** price breaches a prior causal rolling extreme and closes back inside; direction is reversal from the swept side.
- **Population:** all eligible H4 bars on the authorized discovery split after warm-up, not only events with convenient outcomes.
- **Event source:** existing Phase 5 `SWEEP`; version and firing/cluster health must pass before outcome access.
- **Controls:** BaselineEngineV4, within split; match direction, volatility bucket, Phase 5.5 regime, session/time-of-day and opportunity availability. Freeze calipers, controls/event and max reuse.
- **Primary outcome:** target-first at one preregistered ATR threshold/horizon chosen from an existing canonical contract, not selected from results.
- **Secondary outcomes:** MFE/MAE and time-to-resolution, explicitly secondary.
- **Costs:** every statistically admitted cell receives the same frozen zero/broker/conservative/stress profiles.
- **Dependence:** cluster, ACF, block-bootstrap ESS and overlap reported separately; no conditioned BH gate.
- **Multiplicity:** include every preregistered direction/regime cell, with non-evaluable cells retained as specified.
- **Power:** outcome-blind event/control counts determine feasibility; insufficient independent units yields `NOT_FEASIBLE`, not a larger search.
- **Stops:** semantic mismatch, data drift, leakage, unhealthy event geometry, inadequate controls or preregistered power failure stop before outcome testing.

Use `FAILED_BREAKOUT` instead only through a separate preregistration; do not choose between the two after reading outcomes.

## 7. Outcome-first Pilot Protocol — ATR Movement Antecedents V1

**Status:** design only; hypothesis generation, not validation.

- **Outcome:** first future move exceeding a single frozen ATR multiple within a frozen horizon, direction declared; censoring and simultaneous-target rules fixed.
- **Opportunity set:** every eligible bar in the authorized discovery split after warm-up.
- **Cases:** all qualifying outcomes, not a hand-picked sample.
- **References:** non-outcome/opposite-outcome observations drawn from the same opportunity set, within split.
- **Matching/adjustment:** volatility, session, causal regime and calendar exposure; matching rules frozen before feature association.
- **Features:** only values with `known_at <= outcome_origin`; no future path, resolved-event label or post-origin regime.
- **Immortal-time control:** origin is fixed at the observation bar for cases and controls; controls must remain eligible for the same horizon.
- **Overlap/dependence:** cluster overlapping horizons and report event/episode views; one market path cannot masquerade as independent evidence.
- **Selection bias:** feature list and transformations come from the frozen registry; no adaptive threshold search.
- **Multiplicity:** one declared family across all tested features/directions; BH or stricter policy frozen before execution.
- **Output:** effect estimate, interval, adjusted p/q, nominal/independent sample diagnostics and stability. Surviving associations become preregisterable hypotheses requiring independent data.
- **Stops:** low power, excessive overlap, no valid control pool, dataset drift, leakage or provenance failure.

## 8. Research Self-Improvement Trial Plan

### Trial 1 — Provenance completeness

- **Baseline:** frozen pre-intervention sample of eligible historical experiments; percentage containing dataset hash, split, period, code commit, parameters, output hash and lineage.
- **Intervention:** existing ingestion plus mandatory provenance check before canonical memory admission.
- **Metric:** complete/eligible; false-block rate separately.
- **Acceptance:** preregistered improvement over baseline with no acceptance of seeded missing-lineage controls; cost and latency recorded.

### Trial 2 — Invalid experiment prevention

- **Baseline:** historical time/artifacts produced before detecting structural invalidity.
- **Intervention:** outcome-blind detector-health, feasibility, data and preregistration preflight.
- **Metric:** invalid runs stopped before expensive execution, false blocks of valid controls, time/RAM avoided.
- **Acceptance:** all seeded invalid controls rejected at the correct layer; no degradation on valid fixtures.

### Trial 3 — First divergence localization

- **Baseline:** analyst time and accuracy using aggregate-result comparison.
- **Intervention:** canonical trace comparator and residual attribution.
- **Metric:** time to first divergent layer, localization accuracy on seeded bar/value/timestamp/direction defects, silent false parity.
- **Acceptance:** every seeded defect localized, zero false `EXACT_ON_FIXTURE`, lower median diagnosis time.

### Independent evaluation guard

RI-01/RI-02 must compare dataset fingerprints, split identity, time overlap, timeframe derivation and experiment lineage. Different record IDs or filenames do not prove independence. Trials, including failures, are appended to the existing ResearchMemory. Agents cannot approve their own rule, risk or production changes.

## 9. Research Efficiency Benchmark Plan

Correctness precedes speed. Use representative workloads:

1. multi-year H4 market-state/event build;
2. tick-to-M15/H4 Behavior Lab bar construction;
3. matched-control construction and one frozen event family;
4. outcome-first feature scan over a frozen feature registry.

Record wall time, peak RSS, input/output rows, throughput, artifact hash and event parity. Establish current Pandas baseline first. Test Polars for columnar transforms, DuckDB for filtered/joined persistent datasets, and Numba only for measured numerical hot loops. A candidate is adoptable only if:

- event/output parity passes the same fixtures;
- provenance and deterministic serialization remain intact;
- representative speed or memory improvement meets a preregistered threshold;
- integration complexity and fallback are documented.

No whole-engine migration follows from a microbenchmark.

## 10. Consolidated RECOVER / REPAIR / EXPLORE Roadmap

### SAFETY — prerequisite

- Complete Max-DD PR review and separately integrate the DEMO/LIVE account gate after semantic rebase.
- Do not enable live trading.

### RECOVER

1. Project existing strategy, evidence, decision, Phase 2–7, TradingView, MT5 and vault artifacts into the Historical Evidence Ledger.
2. Deduplicate by artifact hash + experiment identity + dataset/split lineage.
3. Build Strategy Lineage and Identity/Attribution projection; unavailable seven-census details remain `UNKNOWN`.
4. Connect records to existing ResearchMemory rather than copying it.

**Gate:** deterministic rebuild, provenance completeness report, no retroactive mutation of original results.

### COVERAGE

1. Extend the existing sparse coverage model with Strategy × Component × Timeframe × Regime × Session × Direction × Entry × Exit × Dataset × Engine.
2. Populate only observed cells and evidence-supported gaps.
3. Build the Untested Experiment Registry using `UNKNOWN` when absence is unprovable.
4. Rank Top 20 questions by uncertainty reduction, falsifiability, feasibility and component reuse.

**Gate:** no Cartesian materialization; counts reconcile to lineage/evidence sources.

### REPAIR

1. Cross-platform canonical-byte handling for frozen artifacts without rewriting protected scientific content.
2. Generic PULLBACK semantic/health review, distinct from BL-01.
3. Cross-timeframe ATR/RSI/ADX/MACD/structure state audit and deterministic guards.
4. `STRAT_STRUCT_REACT` attribution and six NXR shared-state analysis without changing operational enums.
5. Preserve valid Phase 7 inference primitives; quarantine only the failed conditioned sequence method/design.

**Gate:** each repair has a failure fixture, passing regression and explicit affected-experiment list.

### PARITY

1. Canonical trace schema/comparator.
2. MACD fixture.
3. BREAKOUT_ACC fixture.
4. SAR fixture.
5. Residual Attribution Matrix and first-divergence report.

**Gate:** three reports with no false parity promotion; economic status unchanged.

### SELF-IMPROVE

Run the three bounded trials above through RI-01/RI-02 after lineage-aware independence is implemented. Preserve proposal-only/human approval.

**Gate:** baseline and intervention use comparable measurement rules; failed trials retained.

### EXPLORE

After the prior gates, submit—but do not auto-run—the SWEEP event-first and ATR movement outcome-first preregistrations. BL-H4M15 remains 6/6; no new variants or protected holdout access.

**Gate:** explicit human approval, discovery-only data, frozen family/power/stop rules.

## 11. Ecosystem responsibilities

- **ResearchMemory:** scientific history, review, failures and proposals.
- **Capability registry:** who/what can perform an authorized step; a capability is not permission.
- **Orchestrator:** task routing, leases, retry/escalation and approval boundary.
- **Research Control Center:** read model and human decision surface, not a research engine.
- **Jarvis:** executive explanation and approved task initiation, not scientific authority.
- **Business units:** reuse shared research services while keeping data ownership, authorization and evidence namespaces distinct.

## 12. Protection ledger

- BL-H4M15 budget remains 6/6.
- No automatic variant, holdout read, mass search, economic promotion or operational-engine modification.
- Outcomes remain distinct: `REFUTED` (evidence against), `INCONCLUSIVE` (insufficient/mixed), `INVALID` (method/data defect), `NOT_FEASIBLE` (preregistered structural/power gate cannot be met).
- A scientific criterion can change only through a separately reviewed proposal; the research loop cannot self-approve it.

## 13. Next decision

After Safety closes, authorize the **RECOVER projection specification** only: schema mapping from existing artifacts into the Historical Evidence Ledger and sparse Coverage Matrix. Do not authorize either pilot until RECOVER, COVERAGE, REPAIR and first-tranche PARITY gates are reviewed.

Marker: `NEXUS_RRA_02_FINAL_RESEARCH_ARCHITECTURE_ADDENDUM_READY_FOR_REVIEW`
