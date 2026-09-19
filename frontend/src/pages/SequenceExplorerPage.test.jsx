import fs from "fs";
import path from "path";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { ConditionalBranch, SemanticTimeline, filterSequences } from "./SequenceExplorerPage";

let container; let root;
beforeEach(() => { global.IS_REACT_ACT_ENVIRONMENT = true; container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container); });
afterEach(() => { act(() => root.unmount()); container.remove(); });

const sequences = [
  { sequence_id: "SEQ-0003", mechanism_id: "MECH-06", mechanism_name: "BREAKOUT_ACCEPTANCE_CONTINUATION", description: "accepted breakout", priority: { tier: "HIGH_RESEARCH_PRIORITY", total_score: 17 }, implementation_status: "NEEDS_ADDITIONAL_SPECIFICATION", failure_memory_relation: "NOVEL", causal_observability_status: "OBSERVABLE_AT_DECISION_TIME", branch_group_id: "CBG-0002" },
  { sequence_id: "SEQ-0010", mechanism_id: "MECH-19", mechanism_name: "LEVEL_RECLAIM_REVERSAL", description: "reclaim", priority: { tier: "LOW_RESEARCH_PRIORITY", total_score: 10 }, implementation_status: "NOT_IMPLEMENTABLE_AS_DESCRIBED", failure_memory_relation: "DIRECT_REPEAT_OF_FAILED_IDEA", causal_observability_status: "NOT_OBSERVABLE", branch_group_id: "CBG-0001" },
];

test("filters by priority, implementation, branch and text", () => {
  expect(filterSequences(sequences, { query: "breakout", priority: "HIGH_RESEARCH_PRIORITY" }).map((x) => x.sequence_id)).toEqual(["SEQ-0003"]);
  expect(filterSequences(sequences, { query: "", failure_memory_relation: "DIRECT_REPEAT_OF_FAILED_IDEA", branch_group_id: "CBG-0001" }).map((x) => x.sequence_id)).toEqual(["SEQ-0010"]);
  expect(filterSequences(sequences, { query: "", implementation_status: "READY_FOR_FORMALIZATION" })).toEqual([]);
});

test("renders canonical semantic timeline without profitability language", () => {
  const sequence = { event_a: "BREAKOUT", transition_conditions: ["acceptance"], transition_completion_time: "t=1", prediction_start: "t=1", outcome_window: "from t=2", expected_outcome_family: ["CONTINUATION_PROBABILITY"], semantic_leakage: { as_described_verdict: "NEEDS_REFORMULATION", verdict_after_correction: "PASS", as_described_reason: "prediction preceded transition" } };
  act(() => root.render(<SemanticTimeline sequence={sequence}/>));
  expect(container.querySelector('[data-testid="semantic-timeline"]')).not.toBeNull();
  expect(container.textContent).toContain("TRANSITION COMPLETE");
  expect(container.textContent).toContain("Original: NEEDS_REFORMULATION");
  expect(container.textContent).not.toMatch(/profitable|promising edge/i);
});

test("renders a Conditional Branch rather than a contradiction", () => {
  const branch = { branch_group_id: "CBG-0002", common_antecedent: "BREAKOUT", branch_a_condition: "acceptance", branch_b_condition: "failure", expected_outcome_a: "continuation family", expected_outcome_b: "reversal family" };
  act(() => root.render(<ConditionalBranch branch={branch}/>));
  expect(container.querySelector('[data-testid="conditional-branch"]')).not.toBeNull();
  expect(container.textContent).toContain("Conditional Branch");
  expect(container.textContent).toContain("BRANCH A");
  expect(container.textContent).not.toContain("contradiction");
});

test("route stays inside Research and inspector has mobile full-screen behavior", () => {
  const app = fs.readFileSync(path.join(process.cwd(), "src/App.js"), "utf8");
  const page = fs.readFileSync(path.join(process.cwd(), "src/pages/SequenceExplorerPage.jsx"), "utf8");
  expect(app).toContain('path="/research/sequences"');
  expect(page).toContain("fixed inset-0");
  expect(page).toContain("w-[min(100%,720px)]");
  expect(page).toContain("UNAVAILABLE");
});
