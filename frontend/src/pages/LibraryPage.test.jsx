import fs from "fs";
import path from "path";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { ExplainPath, filterLibraryEntities } from "./LibraryPage";

let container; let root;
beforeEach(() => { global.IS_REACT_ACT_ENVIRONMENT = true; container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container); });
afterEach(() => { act(() => root.unmount()); container.remove(); });

const entities = [
  { id: "H006", type: "Hypothesis", title: "Holdout", status: "BORDERLINE", evidence_grade: "E2", phase: "Phase6" },
  { id: "EVD-1", type: "EvidenceAudit", title: "Dependence audit", status: "AUDIT_ONLY", evidence_grade: null, phase: "Phase6.5" },
];
const relations = [{ source_id: "EVD-1", target_id: "H006", type: "AUDITS" }];

test("searches and filters the entity catalog including relation types", () => {
  expect(filterLibraryEntities(entities, relations, { query: "audits" }).map((x) => x.id)).toEqual(["H006", "EVD-1"]);
  expect(filterLibraryEntities(entities, relations, { query: "", type: "Hypothesis", evidence_grade: "E2" }).map((x) => x.id)).toEqual(["H006"]);
  expect(filterLibraryEntities(entities, relations, { query: "", phase: "Phase6.5" }).map((x) => x.id)).toEqual(["EVD-1"]);
});

test("renders a vertical deterministic explain path and separate current decision", () => {
  const explain = { path_nodes: entities.map((x) => ({ ...x, limitations: [], provenance: { source_artifact: "phase6_6/test.json" } })), typed_edges: [{ id: "REL-1", ...relations[0] }], current_decision: { status: "RETAIN_E2", evidence_grade: "E2" } };
  act(() => root.render(<MemoryRouter><ExplainPath explain={explain} /></MemoryRouter>));
  expect(container.querySelector('[data-testid="explain-path"]')).not.toBeNull();
  expect(container.textContent).toContain("AUDITS");
  expect(container.textContent).toContain("RETAIN_E2");
  expect(container.textContent).toContain("not linked by an inferred edge");
});

test("legacy knowledge and journal routes remain available and library uses workspace", () => {
  const app = fs.readFileSync(path.join(process.cwd(), "src/App.js"), "utf8");
  ["/library", "/knowledge", "/journal"].forEach((route) => expect(app).toContain(`path="${route}"`));
  const dashboard = fs.readFileSync(path.join(process.cwd(), "src/pages/Dashboard.jsx"), "utf8");
  expect(dashboard).toContain('<LibraryPage />');
});
