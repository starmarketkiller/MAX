import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { DepartmentCard, DepartmentInspector, LifecycleFieldSemantics, StrategyInspector, StrategyPipeline } from "./CompanyPage";

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

const strategy = { strategy_id: "SAR_LIVE", lifecycle_class: "FULL_STRATEGY_SPEC", code_registry_status: "ACTIVE", evidence_verdict: "REFUTED", evidence_is_refuted: true, governance_status: "GOVERNANCE_CONFLICT", current_stage: "STRATEGY_VALIDATION", blocked_stage: "META_FILTER_RESEARCH", next_required_stage: "STRATEGY_VALIDATION", meta_filter_structural_eligibility: "STRUCTURAL_STATUS_UNVERIFIED", meta_filter_research_readiness: "REFUTED_INAPPROPRIATE", blockers: ["Refuted strategy"], evidence_ladder: { wide_sample: { status: "FAIL", detail: "Negative evidence" } }, field_semantics: [{ field: "direction", field_knowledge: "NOT_EXTRACTED", requirement_role: "REQUIRED", note: "Audit did not extract this field." }], provenance: { sources: ["server/research_scripts/phase7/phase7_7a/strategy_evidence_matrix_v1.json", "server/research_scripts/phase7/phase7_7b/missing_field_semantics_refinement_v1.json"] } };

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
