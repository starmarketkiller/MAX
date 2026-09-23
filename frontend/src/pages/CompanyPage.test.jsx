import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { CompanyHealth, DepartmentCard, DepartmentInspector, FreshnessWarning, LifecycleFieldSemantics, ProjectionFreshness, SeriousValidationPreflight, StrategyInspector, StrategyPipeline } from "./CompanyPage";

let container, root;
beforeEach(() => { global.IS_REACT_ACT_ENVIRONMENT = true; container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container); });
afterEach(() => { act(() => root.unmount()); container.remove(); });

const skeleton = { id: "EXECUTION", name: "Execution", status: "SKELETON", purpose: "Runtime execution domain.", skeleton: true, work_item_count: 0, artifact_count: 0, blocked_count: 0 };
const quant = { id: "QUANT_RESEARCH", name: "Quant Research", status: "ACTIVE", purpose: "Canonical sequence research.", skeleton: false, capabilities: ["sequence_registry"], accepted_inputs: ["dataset_version"], emitted_outputs: ["research_artifact"], required_dependencies: ["DATA"], active_work_items: [{ id: "WI-SEQ-1", source_entity_id: "SEQ-1", name: "Sequence", raw_status: "NEEDS_ADDITIONAL_SPECIFICATION", normalized_status: "BLOCKED" }], recent_artifacts: [{ id: "ART-1", name: "registry.json", source_path: "server/research/registry.json" }] };

test("skeleton department is explicit and does not fabricate activity", () => {
  act(() => root.render(<DepartmentCard department={skeleton} onOpen={() => {}} />));
  expect(container.textContent).toContain("SKELETON");
  expect(container.textContent).toContain("No operational pipeline yet");
});

test("department inspector exposes blocker, contracts and artifact provenance", () => {
  act(() => root.render(<DepartmentInspector department={quant} onClose={() => {}} />));
  expect(container.textContent).toContain("BLOCKED");
  expect(container.textContent).toContain("NEEDS_ADDITIONAL_SPECIFICATION");
  expect(container.textContent).toContain("dataset_version");
  expect(container.textContent).toContain("registry.json");
});

test("inspector is a full-screen accessible sheet on mobile", () => {
  act(() => root.render(<DepartmentInspector department={skeleton} onClose={() => {}} />));
  expect(container.querySelector('[aria-label="Department inspector"]')).not.toBeNull();
  expect(container.querySelector('[aria-label="Close department inspector"]')).not.toBeNull();
});

const strategy = { strategy_id: "SAR_LIVE", lifecycle_class: "FULL_STRATEGY_SPEC", code_registry_status: "ACTIVE", evidence_verdict: "REFUTED", evidence_is_refuted: true, governance_status: "GOVERNANCE_CONFLICT", current_stage: "STRATEGY_VALIDATION", blocked_stage: "META_FILTER_RESEARCH", next_required_stage: "STRATEGY_VALIDATION", meta_filter_structural_eligibility: "STRUCTURAL_STATUS_UNVERIFIED", meta_filter_research_readiness: "REFUTED_INAPPROPRIATE", blockers: ["Refuted strategy"], evidence_ladder: { wide_sample: { status: "FAIL", detail: "Negative evidence" } }, field_semantics: [{ field: "direction", field_knowledge: "NOT_EXTRACTED", requirement_role: "REQUIRED", note: "Audit did not extract this field." }], projection_freshness: { freshness_status: "STALE", canonical_latest_phase: "7.9A", projected_latest_phase: "7.7B", lag_description: "Newer canonical research exists.", canonical_latest_source: "server/research/7.9a.json", projected_latest_source: "server/research/7.7b.json", provenance: { canonical_sha256: "abc123" } }, provenance: { sources: ["server/research_scripts/phase7/phase7_7a/strategy_evidence_matrix_v1.json", "server/research_scripts/phase7/phase7_7b/missing_field_semantics_refinement_v1.json"] } };

test("strategy inventory renders refuted evidence separately from active code", () => {
  act(() => root.render(<StrategyPipeline strategies={[strategy]} onOpen={() => {}} />));
  expect(container.textContent).toContain("SAR_LIVE");
  expect(container.textContent).toContain("REFUTED");
  expect(container.textContent).toContain("GOVERNANCE_CONFLICT");
});

test("strategy inspector exposes evidence ladder, blocker and provenance", () => {
  act(() => root.render(<StrategyInspector strategy={strategy} onClose={() => {}} />));
  expect(container.textContent).toContain("Code registry status");
  expect(container.textContent).toContain("ACTIVE");
  expect(container.textContent).toContain("Negative evidence");
  expect(container.textContent).toContain("Refuted strategy");
  expect(container.querySelector('[aria-label="Strategy inspector"]')).not.toBeNull();
  expect(container.textContent).toContain("Lifecycle field semantics");
  expect(container.textContent).toContain("UNVERIFIED / NOT EXTRACTED");
  expect(container.textContent).toContain("NOT_EXTRACTED ≠ VERIFIED_ABSENCE");
});

test("H006 equivalent invalidation mechanism renders without implying missing data", () => {
  const fields = [{ field: "invalidation_stop", field_knowledge: "VERIFIED_ABSENCE", requirement_role: "SATISFIED_BY_EQUIVALENT_MECHANISM", note: "Two-sided barrier is the equivalent mechanism." }];
  act(() => root.render(<LifecycleFieldSemantics fields={fields} />));
  expect(container.textContent).toContain("VERIFIED_ABSENCE");
  expect(container.textContent).toContain("SATISFIED_BY_EQUIVALENT_MECHANISM");
  expect(container.textContent).not.toContain("UNVERIFIED / NOT EXTRACTED");
});

test("execution and risk skeleton states remain conservative", () => {
  const execution = { ...skeleton, operational_state: { state: "WAITING_FOR_QUANT_GATE", execution_candidate_count: 0 } };
  act(() => root.render(<DepartmentInspector department={execution} onClose={() => {}} />));
  expect(container.textContent).toContain("WAITING_FOR_QUANT_GATE");
  act(() => root.render(<DepartmentInspector department={{ ...skeleton, id: "RISK_PORTFOLIO", operational_state: { state: "WAITING_FOR_DEPLOYABLE_STRATEGIES", deployable_strategy_count: 0 } }} onClose={() => {}} />));
  expect(container.textContent).toContain("WAITING_FOR_DEPLOYABLE_STRATEGIES");
});

test("archived VOLBRK renders the post-validation observation without rescue", () => {
  const archived = { ...strategy, strategy_id: "VOLATILITY_BREAKOUT_CONFIRMED", research_readiness: "REFUTED_ARCHIVED", serious_validation: "FAIL", lifecycle_stage: "ARCHIVE_CURRENT_DESIGN", state_transition: { previous: "NEEDS_MORE_EVIDENCE", current: "REFUTED_ARCHIVED", rationale: "Serious validation supplied negative evidence." }, post_validation_observations: { classification: "POST_VALIDATION_OBSERVATION", BUY: { n: 56, expectancy_R: -0.7257678571, pf: 0.1455631005 }, SELL: { n: 127, expectancy_R: 0.2231102362, pf: 1.6254690742 }, caveat: "Not a rescued strategy. SELL-only would require a new hypothesis identity and new validation." } };
  act(() => root.render(<StrategyInspector strategy={archived} onClose={() => {}} />));
  expect(container.textContent).toContain("REFUTED_ARCHIVED");
  expect(container.textContent).toContain("ARCHIVE_CURRENT_DESIGN");
  expect(container.textContent).toContain("POST_VALIDATION_OBSERVATION");
  expect(container.textContent).toContain("Not a rescued strategy");
});

test("BREAKOUT_ACC inspector exposes lifecycle identity, lineage and pending experiment", () => {
  const breakout = { ...strategy, strategy_id: "BREAKOUT_ACC", formalization_verdict: "FULL_STRATEGY_SPEC_VERIFIED", static_reachability: "STATIC_REACHABILITY_PASS", research_readiness: "HOLD_NEEDS_MORE_EVIDENCE", strategy_identity: { selector: 9, master_switch: "InpStrat_BREAKOUT_ACC", signal_function: "NXS_Strat_BreakoutAcc()", timeframe: "D1" }, field_semantics: [{ field: "invalidation_stop", field_knowledge: "VERIFIED_VALUE", mechanism_origin: "FRAMEWORK_EQUIVALENT", requirement_role: "SATISFIED_BY_EQUIVALENT_MECHANISM", value: "ATR framework stop" }, { field: "cost_assumptions", field_knowledge: "NOT_EXTRACTED", mechanism_origin: "NOT_EXTRACTED", requirement_role: "NOT_REQUIRED_BY_DESIGN" }], evidence_lineage: [{ source_id: "A", identity_status: "EVIDENCE_IDENTITY_UNVERIFIED", claim: "101 trades / +4.3R" }, { source_id: "B", identity_status: "PARTIAL_IDENTITY_MATCH", claim: "Earlier Python screening" }, { source_id: "C", identity_status: "EVIDENCE_IDENTITY_UNVERIFIED", claim: "Walk-forward mismatch" }, { source_id: "D", identity_status: "EVIDENCE_IDENTITY_CONFIRMED", claim: "MT5 4 trades over 7.5 years; Python 27 trades" }], evidence_contradiction: { description: "101 trades conflicts with 4 MT5 trades." }, next_admissible_experiment: { category: "REANALYZE_EXISTING_RAW_RESULTS", executed: false, target: "Existing Python raw results" } };
  act(() => root.render(<StrategyInspector strategy={breakout} onClose={() => {}} />));
  expect(container.textContent).toContain("FULL_STRATEGY_SPEC_VERIFIED");
  expect(container.textContent).toContain("STATIC_REACHABILITY_PASS");
  expect(container.textContent).toContain("FRAMEWORK_EQUIVALENT");
  expect(container.textContent).toContain("Evidence lineage");
  expect(container.textContent).toContain("EVIDENCE_IDENTITY_CONFIRMED");
  expect(container.textContent).toContain("REANALYZE_EXISTING_RAW_RESULTS");
  expect(container.textContent).toContain("It has not been executed yet");
});

test("Serious Validation Preflight is rendered as a read-only twelve item protocol", () => {
  const protocol = { name: "NEXUS_SERIOUS_VALIDATION_PREFLIGHT_CHECKLIST_V1", provenance: "server/research_scripts/phase7/phase7_9a/serious_validation_preflight_checklist_v1.json", items: Array.from({ length: 12 }, (_, index) => ({ id: index + 1, item: `Check ${index + 1}`, verify: `Verify ${index + 1}` })) };
  act(() => root.render(<SeriousValidationPreflight protocol={protocol} />));
  expect(container.textContent).toContain("Protocol / checklist · read-only · not completion state");
  expect(container.textContent).toContain("Check 12");
  expect(container.querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
});

test("Product Platform card and inspector expose distinct ownership and freshness", () => {
  const product = { id: "PRODUCT_PLATFORM", name: "Product / Control Plane", status: "ACTIVE", purpose: "Project canonical state without deciding scientific truth.", skeleton: false, work_item_count: 0, artifact_count: 0, blocked_count: 0, capabilities: ["company_dashboard", "freshness_tracking"], accepted_inputs: ["canonical_artifacts"], emitted_outputs: ["freshness_state"], required_dependencies: ["QUANT_RESEARCH", "SCIENTIFIC_QA", "DATA", "COMPUTE_INFRA"], operational_state: { freshness_status: "STALE", current_count: 1, stale_count: 1, partial_count: 5, unknown_count: 0 }, freshness_records: [strategy.projection_freshness && { ...strategy.projection_freshness, entity_id: "BREAKOUT_ACC" }] };
  act(() => root.render(<DepartmentCard department={product} onOpen={() => {}} />));
  expect(container.textContent).toContain("Product / Control Plane");
  expect(container.textContent).toContain("STALE");
  act(() => root.render(<DepartmentInspector department={product} onClose={() => {}} />));
  expect(container.textContent).toContain("freshness_tracking");
  expect(container.textContent).toContain("Operational freshness summary");
  expect(container.textContent).toContain("QUANT_RESEARCH");
});

test("global warning and Company Health show artifact-backed dimensions", () => {
  act(() => root.render(<><FreshnessWarning records={[strategy.projection_freshness]} /><CompanyHealth items={[{ department_id: "PRODUCT_PLATFORM", status: "STALE", status_dimension: "FRESHNESS", reason: "Strategy projection behind canonical research." }, { department_id: "EXECUTION", status: "WAITING_FOR_QUANT_GATE", status_dimension: "OPERATIONAL", reason: "Execution remains gated." }]} /></>));
  expect(container.textContent).toContain("Research projection stale");
  expect(container.textContent).toContain("Company Health");
  expect(container.textContent).toContain("WAITING_FOR_QUANT_GATE");
});

test("strategy freshness is independent from scientific readiness and shows provenance", () => {
  const breakout = { ...strategy, strategy_id: "BREAKOUT_ACC", research_readiness: "HOLD_NEEDS_MORE_EVIDENCE", projection_freshness: { ...strategy.projection_freshness, canonical_latest_phase: "7.9F", projected_latest_phase: "7.9B", canonical_latest_source: "server/research_scripts/phase7/phase7_9f/breakout_acc_identity_adjudication_v1.json", projected_latest_source: "server/research_scripts/phase7/phase7_9b/breakout_acc_formalization_decision_v1.json" } };
  act(() => root.render(<StrategyInspector strategy={breakout} onClose={() => {}} />));
  expect(container.textContent).toContain("HOLD_NEEDS_MORE_EVIDENCE");
  expect(container.textContent).toContain("Projection freshness");
  expect(container.textContent).toContain("7.9F");
  expect(container.textContent).toContain("7.9B");
  expect(container.textContent).toContain("STALE");
  expect(container.textContent).not.toContain("identity adjudication verdict");
});

test("projection freshness handles unavailable records explicitly", () => {
  act(() => root.render(<ProjectionFreshness record={null} />));
  expect(container.textContent).toContain("UNKNOWN");
});
