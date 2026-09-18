import React, { act } from "react";
import { createRoot } from "react-dom/client";
jest.mock("lightweight-charts", () => ({ createChart: jest.fn(), CandlestickSeries: {}, LineSeries: {} }));
import { MarketStatePanel, ParityIndicator } from "./MarketPage";

let container;
let root;
beforeEach(() => { global.IS_REACT_ACT_ENVIRONMENT = true; container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container); });
afterEach(() => { act(() => root.unmount()); container.remove(); });

test("renders explicit unavailable market state without numeric fallback", () => {
  act(() => root.render(<MarketStatePanel snapshot={null}/>));
  expect(container.textContent).toContain("UNAVAILABLE");
  expect(container.textContent).toContain("—");
  expect(container.textContent).not.toContain("0.000");
});

test("renders research provenance and canonical fields", () => {
  act(() => root.render(<MarketStatePanel snapshot={{ timestamp: "2022-01-01T00:00:00Z", regime: "UP_HIGH", directional_efficiency: 0.7, provenance: { type: "DERIVED" } }}/>));
  expect(container.textContent).toContain("DERIVED");
  expect(container.textContent).toContain("UP HIGH");
  expect(container.textContent).toContain("0.700");
});

test("parity indicator exposes partial and none mismatch states", () => {
  act(() => root.render(<ParityIndicator value="PARTIAL" explanation="schemas differ"/>));
  expect(container.textContent).toContain("PARTIAL");
  act(() => root.render(<ParityIndicator value="NONE"/>));
  expect(container.textContent).toContain("NONE");
});

test("market workspace source contains mobile Chart State Events tabs", () => {
  const source = require("fs").readFileSync(require("path").join(process.cwd(), "src/pages/MarketPage.jsx"), "utf8");
  ["chart", "state", "events"].forEach((tab) => expect(source).toContain(`\"${tab}\"`));
});
