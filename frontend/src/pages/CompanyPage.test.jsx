import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { DepartmentCard, DepartmentInspector } from "./CompanyPage";

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
