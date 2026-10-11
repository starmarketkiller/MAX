import React, { act } from "react";
import { createRoot } from "react-dom/client";
import ResearchIntelligencePage from "./ResearchIntelligencePage";
import api from "@/lib/api";

jest.mock("@/lib/api", () => ({ __esModule: true, default: { get: jest.fn() } }));

const available = {
  status: "HEALTHY",
  research_loop: { status: "IDLE_NOT_RUN", reason_code: "NO_PERSISTED_LOOP_TRANSITION", next_actions: [] },
  experiment_registry: { count: 1, items: [{ record_id: "EXP-1", status: "COMPLETED", datasets: [{ dataset_id: "D-1" }], evidence_level: "E1", provenance: [{ ref: "memory.jsonl" }] }] },
  hypothesis_queue: { status: "NOT_MATERIALIZED", reason: "No persisted PRIORITIZATION record", items: [] },
  improvement_center: { items: [{ record_id: "IMP-1", status: "PROPOSED", baseline: "B1", success_criterion: "C1", results: [] }] },
  research_memory: { items: [{ record_id: "R-1", type: "REVIEW", created_at: "2026-10-11T10:00:00Z", summary: "Reviewed evidence", provenance: [{ ref: "memory.jsonl" }] }] },
  agent_activity: { items: [{ role_id: "researcher", executor: "LOCAL", status: "INACTIVE", last_outcome: null }] },
  approval_center: { count: 1, actions_enabled: false, items: [{ record_id: "IMP-1", kind: "IMPROVEMENT_PROPOSAL", status: "PROPOSED", requires: ["HUMAN_REVIEW"] }] },
};

let host, root;
beforeEach(() => { global.IS_REACT_ACT_ENVIRONMENT = true; host = document.createElement("div"); document.body.appendChild(host); root = createRoot(host); });
afterEach(() => { act(() => root.unmount()); host.remove(); jest.clearAllMocks(); });
const render = async payload => { api.get.mockResolvedValue({ data: payload }); await act(async () => root.render(<ResearchIntelligencePage />)); await act(async () => { await Promise.resolve(); }); };

test("renders canonical sections and keeps approval controls read-only", async () => {
  await render(available);
  expect(api.get).toHaveBeenCalledWith("/research/intelligence/control-center");
  expect(host.textContent).toContain("Research Intelligence");
  expect(host.textContent).toContain("IDLE_NOT_RUN");
  expect(host.textContent).toContain("EXP-1");
  expect(host.textContent).toContain("No persisted PRIORITIZATION record");
  expect(host.textContent).toContain("ACTIONS_DISABLED");
  expect(host.querySelectorAll("button")).toHaveLength(0);
});

test("renders explicit unavailable state instead of simulated statistics", async () => {
  await render({ status: "UNAVAILABLE", warnings: [{ code: "RESEARCH_MEMORY_NOT_FOUND" }] });
  expect(host.textContent).toContain("Canonical research data unavailable");
  expect(host.textContent).toContain("RESEARCH_MEMORY_NOT_FOUND");
  expect(host.textContent).not.toContain("Experiment Registry");
});

test("renders empty persisted sections without inventing activity", async () => {
  await render({ ...available, experiment_registry: { count: 0, items: [] }, improvement_center: { items: [] }, research_memory: { items: [] }, agent_activity: { items: [] }, approval_center: { open_count: 0, actions_enabled: false, items: [] } });
  expect(host.textContent).toContain("No persisted experiments");
  expect(host.textContent).toContain("No persisted improvement proposals");
  expect(host.textContent).toContain("No persisted observations or reviews");
});
