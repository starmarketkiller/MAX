import React, { act } from "react";
import { createRoot } from "react-dom/client";
import ResearchControlPlanePage from "./ResearchControlPlanePage";
import api from "@/lib/api";

jest.mock("@/lib/api", () => ({ __esModule: true, default: { get: jest.fn() } }));
const response = path => {
  if (path.endsWith("overview")) return {census_count:83,experiment_count:8,hypothesis_count:8,dataset_count:11,strategy_count:4,failure_mode_count:11,forward_or_oos_experiments:3,implementation_defect_strategies:1,freshness:"CURRENT",projected_through:"7.26",canonical_research_through:"7.26",strategies:[{strategy_id:"BREAKOUT_ACC",latest_verdict:"EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION",freshness:{state:"CURRENT"}}]};
  if (path.endsWith("hypotheses")) return {items:[{hypothesis_id:"H2",statement:"Observation under test",lifecycle_state:"HYPOTHESIS",discovery_dataset_id:"D1",validation_dataset_ids:[]}]};
  if (path.endsWith("failure-map")) return {items:[{strategy_identity:"TSI",failure_modes:[{mode:"IMPLEMENTATION_DEFECT",note:"fixed",evidence_ref:"artifact"}]}]};
  if (path.endsWith("visual-audits")) return {items:[{id:"event_stagea",stage:"STAGEA",event_id:"event",fidelity_grade:"NOT_AVAILABLE"},{id:"event_stageb",stage:"STAGEB",event_id:"event",fidelity_grade:"NOT_AVAILABLE"}]};
  return {items:[]};
};

let host, root;
beforeEach(()=>{global.IS_REACT_ACT_ENVIRONMENT=true;host=document.createElement("div");document.body.appendChild(host);root=createRoot(host);api.get.mockImplementation(path=>Promise.resolve({data:response(path)}));});
afterEach(()=>{act(()=>root.unmount());host.remove();jest.clearAllMocks();});
const flush=()=>act(async()=>{await Promise.resolve();await Promise.resolve();});

test("renders source-backed overview and freshness",async()=>{await act(async()=>root.render(<ResearchControlPlanePage/>));await flush();expect(host.textContent).toContain("Research Command Center");expect(host.textContent).toContain("83");expect(host.textContent).toContain("CURRENT");});
test("hypothesis lifecycle stays a hypothesis with separate datasets",async()=>{await act(async()=>root.render(<ResearchControlPlanePage/>));await flush();act(()=>[...host.querySelectorAll("button")].find(x=>x.textContent==="Hypotheses").click());expect(host.textContent).toContain("HYPOTHESIS");expect(host.textContent).toContain("UNAVAILABLE");});
test("failure drilldown and visual stages render without inference",async()=>{await act(async()=>root.render(<ResearchControlPlanePage/>));await flush();act(()=>[...host.querySelectorAll("button")].find(x=>x.textContent==="Failures").click());expect(host.textContent).toContain("IMPLEMENTATION_DEFECT");act(()=>[...host.querySelectorAll("button")].find(x=>x.textContent==="Visual audit").click());expect(host.textContent).toContain("Stage A");act(()=>[...host.querySelectorAll("button")].find(x=>x.textContent==="Stage B").click());expect(host.querySelector("img").alt).toContain("STAGEB");});
