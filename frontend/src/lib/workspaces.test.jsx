import fs from "fs";
import path from "path";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import BottomNav from "../components/BottomNav";
import { OverviewDomains, buildAttentionItems } from "../pages/dashboard/HomePage";
import { ThemeProvider, useTheme } from "./theme";
import { LEGACY_ROUTES, PRIMARY_WORKSPACES, workspaceForPath } from "./workspaces";

let container;
let root;

beforeEach(() => { global.IS_REACT_ACT_ENVIRONMENT = true; container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container); });
afterEach(() => { act(() => root.unmount()); container.remove(); localStorage.clear(); document.documentElement.classList.remove("dark"); });

test("defines exactly five primary workspaces and maps legacy areas", () => {
  expect(PRIMARY_WORKSPACES.map(({ id }) => id)).toEqual(["overview", "market", "research", "execution", "library"]);
  expect(workspaceForPath("/calendar").id).toBe("market");
  expect(workspaceForPath("/backtest").id).toBe("research");
  expect(workspaceForPath("/local-bridge").id).toBe("execution");
  expect(workspaceForPath("/knowledge").id).toBe("library");
});

test("all declared legacy routes remain registered in App", () => {
  const appSource = fs.readFileSync(path.join(process.cwd(), "src", "App.js"), "utf8");
  LEGACY_ROUTES.forEach((route) => expect(appSource).toContain(`path="${route}"`));
});

test("mobile navigation exposes Overview, Market, Research, Execution and More", () => {
  act(() => root.render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/research"]}><BottomNav onMenuOpen={() => {}}/></MemoryRouter>));
  ["overview", "market", "research", "execution"].forEach((id) => expect(container.querySelector(`[data-testid="bottomnav-${id}"]`)).not.toBeNull());
  expect(container.querySelector('[data-testid="bottomnav-more"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="bottomnav-research"]').getAttribute("aria-current")).toBe("page");
});

test("Overview renders truthful H006 status and unavailable states", () => {
  const hypothesis = { id: "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT", status: "BORDERLINE", evidence_grade: "E2", promoted_to_e3: false, grade_cap_reason: "true holdout BORDERLINE, no E3 promotion" };
  act(() => root.render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><OverviewDomains status={null} health={null} settings={{}} hypothesis={hypothesis} researchError=""/></MemoryRouter>));
  expect(container.textContent).toContain("BORDERLINE");
  expect(container.textContent).toContain("E2");
  expect(container.textContent).toContain("NOT PROMOTED");
  expect(container.textContent).toContain("UNAVAILABLE");
  act(() => root.render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><OverviewDomains status={null} health={null} settings={{}} hypothesis={null} researchError="offline"/></MemoryRouter>));
  expect(container.textContent).toContain("Research API unavailable");
});

test("attention list is empty when no exception is present", () => {
  expect(buildAttentionItems({ status: { bridgeState: "LIVE", drawdownPct: 1, eslHit: false, dptHit: false }, health: {}, settings: { MaxDailyDDPct: 5 }, hypothesis: {}, researchError: "" })).toEqual([]);
});

function ThemeHarness() { const { theme, toggle } = useTheme(); return <button onClick={toggle}>{theme}</button>; }

test("dark default and light toggle remain supported", () => {
  act(() => root.render(<ThemeProvider><ThemeHarness/></ThemeProvider>));
  expect(document.documentElement.classList.contains("dark")).toBe(true);
  act(() => container.querySelector("button").click());
  expect(container.textContent).toBe("light");
  expect(document.documentElement.classList.contains("dark")).toBe(false);
});
