import fs from "fs";
import path from "path";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import ExecutionPage, { buildExecutionAttention, ExecutionQuality, RiskSummary } from "./ExecutionPage";
import { buildTimeline } from "./dashboard/TradeLifecycleDrawer";

let container;
let root;
beforeEach(() => { global.IS_REACT_ACT_ENVIRONMENT = true; container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container); });
afterEach(() => { act(() => root.unmount()); container.remove(); });

const snapshot = {
  freshness: { state: "LIVE", age_seconds: 2 },
  ea: { state: "LIVE", provenance: "LIVE", equity: 1010, balance: 1000, paused: false },
  positions: { state: "LIVE", provenance: "LIVE", items: [{ ticket: 7, symbol: "XAUUSD", side: "BUY", lots: 0.1, openPrice: 2300, currentPrice: null, pnl: 4, sl: null, tp: null, strategy: "ADX_RSI" }] },
  risk: { state: "CLEAR", provenance: "LIVE", drawdown_pct: 1, max_daily_dd_pct: 5, protections: [] },
  bridge: { state: "LIVE", provenance: "LIVE", worker: { online: true, host_id: "host-1", timestamp: "2026-09-18T00:00:00Z" }, commands: [], failed_command_count: 0 },
  engines: { state: "CACHED", provenance: "CACHED", items: [{ engine_id: "ADX_RSI", enabled: true, configuration_status: "ENABLED", runtime_status: "UNAVAILABLE", risk_multiplier: null, canonical_strategy_status: "UNAVAILABLE" }] },
  allocation: { state: "DERIVED", config: { enabled: true }, items: [] },
  recent_trades: { state: "DERIVED", items: [] },
  execution_quality: { state: "PARTIAL", provenance: "DERIVED", message: "Signal-to-fill telemetry incomplete", available: ["position_open_time"], missing: ["signal_timestamp", "fill_timestamp"] },
};

test("renders execution workspace, position, risk, bridge and engine truthfully", () => {
  act(() => root.render(<MemoryRouter><ExecutionPage initialSnapshot={snapshot} polling={false} onCmd={() => {}}/></MemoryRouter>));
  expect(container.querySelector('[data-testid="execution-workspace"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="position-row-7"]')).not.toBeNull();
  expect(container.textContent).toContain("ADX_RSI");
  expect(container.textContent).toContain("risk —");
  expect(container.textContent).toContain("Worker online");
  expect(container.textContent).toContain("Signal-to-fill telemetry incomplete");
});

test("position actions reuse command callback with confirmation", () => {
  const onCmd = jest.fn();
  act(() => root.render(<MemoryRouter><ExecutionPage initialSnapshot={snapshot} polling={false} onCmd={onCmd}/></MemoryRouter>));
  act(() => container.querySelector('[data-testid="close-position-7"]').click());
  expect(onCmd).toHaveBeenCalledWith("close_position", { ticket: 7 }, true, expect.any(Object));
  act(() => container.querySelector('[data-testid="partial-close-7"]').click());
  expect(onCmd).toHaveBeenCalledWith("partial_close", { ticket: 7, volume: 0.05 }, true, expect.any(Object));
});

test("missing and stale data stay explicit", () => {
  act(() => root.render(<MemoryRouter><RiskSummary risk={null}/><ExecutionQuality quality={null}/></MemoryRouter>));
  expect(container.textContent).toContain("—");
  expect(container.textContent).toContain("UNAVAILABLE");
  const attention = buildExecutionAttention({ ...snapshot, ea: { state: "STALE" }, bridge: { state: "STALE", failed_command_count: 1 }, execution_quality: { state: "UNAVAILABLE" } });
  expect(attention.map((item) => item.code)).toEqual(expect.arrayContaining(["ea", "bridge", "quality", "commands"]));
});

test("mobile tabs and all legacy routes remain available", () => {
  act(() => root.render(<MemoryRouter><ExecutionPage initialSnapshot={snapshot} polling={false} onCmd={() => {}}/></MemoryRouter>));
  ["live", "engines", "risk", "systems"].forEach((tab) => expect(container.querySelector(`[data-testid="execution-tab-${tab}"]`)).not.toBeNull());
  const app = fs.readFileSync(path.join(process.cwd(), "src/App.js"), "utf8");
  ["/strategies", "/optimizer", "/risk", "/local-bridge", "/chain", "/analytics", "/strategy-analytics"].forEach((route) => expect(app).toContain(`path="${route}"`));
});

test("trade lifecycle marks unrecorded signal order and gate phases unavailable", () => {
  const steps = buildTimeline({ ticket: 1, openTime: "2026-01-01T00:00:00Z", pnl: null });
  expect(steps.find((step) => step.title === "Signal detected").status).toBe("unavailable");
  expect(steps.find((step) => step.title === "Gate decision").detail).toContain("unavailable");
  expect(steps.find((step) => step.title === "Order sent").status).toBe("unavailable");
  expect(steps.find((step) => step.title === "Filled & live").status).toBe("done");
});
