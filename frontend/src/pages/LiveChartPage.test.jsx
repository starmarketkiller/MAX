import React, { act } from "react";
import { createRoot } from "react-dom/client";

jest.mock("lightweight-charts", () => {
  const series = { setData: jest.fn(), update: jest.fn() };
  const ts = {
    fitContent: jest.fn(),
    setVisibleLogicalRange: jest.fn(),
    getVisibleLogicalRange: jest.fn(() => ({ from: 10, to: 170 })),
    subscribeVisibleLogicalRangeChange: jest.fn(),
    unsubscribeVisibleLogicalRangeChange: jest.fn(),
  };
  const chart = {
    addSeries: jest.fn(() => series), timeScale: () => ts, applyOptions: jest.fn(), resize: jest.fn(), remove: jest.fn(), removeSeries: jest.fn(),
    subscribeClick: jest.fn(), unsubscribeClick: jest.fn(), subscribeCrosshairMove: jest.fn(), unsubscribeCrosshairMove: jest.fn(),
  };
  const createSeriesMarkers = jest.fn(() => ({ detach: jest.fn() }));
  return { createChart: jest.fn(), CandlestickSeries: {}, LineSeries: {}, createSeriesMarkers, __mocks: { series, ts, chart, createSeriesMarkers } };
});
jest.mock("@/lib/api", () => ({ __esModule: true, default: { get: jest.fn() } }));
jest.mock("@/lib/theme", () => ({ useTheme: () => ({ theme: "light" }) }));
jest.mock("@/components/CoachLiveWidget", () => ({ __esModule: true, default: () => null }));

import api from "@/lib/api";
import LiveChartPage, { toSeriesBar, markerTime } from "./LiveChartPage";

const M = require("lightweight-charts").__mocks;
let container;
let root;

const SOURCE = {
  dataset_id: "DS1", label: "DS1 reale", symbol_aliases: ["GOLD", "XAUUSD"], timeframes: ["M1", "M5", "M15", "H1"], feed_kind: "MT5_BROKER_EXPORT",
  instrument_spec: { pip_convention: { pip_price_usd_per_oz: 0.1 } },
};

function bars(n, start, step = 900, partialEvery = 0) {
  return Array.from({ length: n }, (_, i) => ({
    time: start + i * step, open: 3000 + i, high: 3001 + i, low: 2999 + i, close: 3000.5 + i, minutes_present: 15, minutes_missing: 0,
    completeness: partialEvery && i % partialEvery === 0 ? "PARTIAL" : "COMPLETE", reason: [],
  }));
}

function envelope(over = {}) {
  return {
    status: "AVAILABLE_OFFLINE", source: "REAL_HISTORICAL", dataset_id: "DS1", feed_kind: "MT5_BROKER_EXPORT", symbol_actual: "GOLD", timeframe: "M15", mode: "HISTORICAL", clock_basis: "TERMINAL_CLOCK (offset)",
    calendar_status: "UNVERIFIED", dataset_version: "abcdef0123456789", available_range: { first_iso: "2026-11-16T01:00:00+00:00", last_iso: "2026-11-20T21:59:00+00:00" }, limitations: ["X"], has_more: true,
    next_before: 1_794_000_000, bars: bars(1500, 1_794_100_000, 900, 7), ...over,
  };
}

let calls;
function route({ ohlc = () => ({ data: envelope() }), sources = { data: { status: "AVAILABLE", sources: [SOURCE], default_source: "DS1" } }, markersData = { data: { trades: [], open: [], shadows: [], visuals: [] } } } = {}) {
  calls = [];
  api.get.mockImplementation(async (url) => {
    calls.push(url);
    if (url.startsWith("/chart/sources")) return sources;
    if (url.startsWith("/chart/ohlc")) return ohlc(url);
    if (url.startsWith("/chart/markers")) return markersData;
    throw new Error("unexpected " + url);
  });
}
const flush = async () => { for (let i = 0; i < 6; i++) await act(async () => { await Promise.resolve(); }); };

beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  // CRA ha resetMocks:true: le implementazioni vanno reimpostate a ogni test
  require("lightweight-charts").createChart.mockImplementation(() => M.chart);
  M.chart.addSeries.mockImplementation(() => M.series);
  M.ts.getVisibleLogicalRange.mockImplementation(() => ({ from: 10, to: 170 }));
  M.createSeriesMarkers.mockImplementation(() => ({ detach: jest.fn() }));
  container = document.createElement("div");
  Object.defineProperty(container, "clientWidth", { value: 800, configurable: true });
  Object.defineProperty(container, "clientHeight", { value: 600, configurable: true });
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); jest.useRealTimers(); });

async function mount() {
  await act(async () => { root.render(<LiveChartPage />); });
  await flush();
}

test("mostra barre reali dalla fonte scelta e dichiara dataset, feed e stato; nessuna fonte sintetica richiesta", async () => {
  route();
  await mount();
  const ohlcCalls = calls.filter((c) => c.startsWith("/chart/ohlc"));
  expect(ohlcCalls.length).toBeGreaterThan(0);
  expect(ohlcCalls[0]).toContain("source=DS1");
  expect(ohlcCalls[0]).toContain("tf=M15");
  expect(calls.join(" ")).not.toContain("SYNTHETIC");
  const lastSet = M.series.setData.mock.calls.slice(-1)[0][0];
  expect(lastSet).toHaveLength(1500);
  expect(container.querySelector('[data-testid="chart-dataset-strip"]').textContent).toContain("DS1");
  expect(container.querySelector('[data-testid="chart-dataset-strip"]').textContent).toContain("MT5_BROKER_EXPORT");
  expect(container.querySelector('[data-testid="provenance-historical"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="chart-mode"]').textContent).toBe("HISTORICAL");
  expect(container.querySelector('[data-testid="chart-source-select"]').value).toBe("DS1");
});

test("le barre PARTIAL non sono disegnate come complete", () => {
  const full = toSeriesBar({ time: 1, open: 1, high: 2, low: 0.5, close: 1.5, completeness: "COMPLETE" });
  const part = toSeriesBar({ time: 1, open: 1, high: 2, low: 0.5, close: 1.5, completeness: "PARTIAL" });
  const gap = toSeriesBar({ time: 1, open: 1, high: 2, low: 0.5, close: 1.5, completeness: "GAP" });
  expect(full.color).toBeUndefined();
  expect(part.color).toContain("rgba");
  expect(gap.borderColor).toBe("#f59e0b");
});

test("stato UNAVAILABLE: messaggio esplicito, nessuna candela, nessun fallback sintetico", async () => {
  route({ ohlc: () => ({ data: { status: "UNAVAILABLE", reason: "SOURCE_UNREACHABLE", detail: "STORE_UNREACHABLE", bars: [] } }) });
  await mount();
  const err = container.querySelector('[data-testid="chart-error"]');
  expect(err).not.toBeNull();
  expect(err.textContent).toContain("SOURCE_UNREACHABLE");
  expect(err.textContent).toContain("Nessun dato sintetico");
  const sets = M.series.setData.mock.calls;
  expect(sets.every((c) => c[0].length === 0)).toBe(true);
  expect(calls.join(" ")).not.toContain("SYNTHETIC_DEMO");
});

test("errore 403 (partizione non autorizzata): nessun dato mostrato", async () => {
  route({ ohlc: () => { const e = new Error("x"); e.response = { status: 403, data: { detail: { code: "PARTITION_NOT_AUTHORIZED" } } }; throw e; } });
  await mount();
  expect(container.querySelector('[data-testid="chart-error"]').textContent).toContain("PARTITION_NOT_AUTHORIZED");
  expect(M.series.setData.mock.calls.every((c) => c[0].length === 0)).toBe(true);
});

test("nessun fitContent e nessun polling per un dataset storico, anche dopo 60 secondi e dopo il cambio di timeframe", async () => {
  jest.useFakeTimers();
  route();
  await mount();
  const before = calls.filter((c) => c.startsWith("/chart/ohlc")).length;
  await act(async () => { jest.advanceTimersByTime(60000); });
  await flush();
  expect(calls.filter((c) => c.startsWith("/chart/ohlc")).length).toBe(before);
  await act(async () => { container.querySelector('[data-testid="chart-tf-H1"]').click(); });
  await flush();
  expect(calls.filter((c) => c.startsWith("/chart/ohlc")).slice(-1)[0]).toContain("tf=H1");
  expect(M.ts.fitContent).not.toHaveBeenCalled();
});

test("modalita' LIVE: aggiorna solo la coda con update(), senza setData ne' fitContent", async () => {
  jest.useFakeTimers();
  route({ ohlc: (url) => ({ data: envelope({ status: "AVAILABLE_LIVE", mode: "LIVE", bars: url.includes("limit=3") ? bars(3, 1_795_000_000) : bars(1500, 1_794_100_000) }) }) });
  await mount();
  const setDataCalls = M.series.setData.mock.calls.length;
  await act(async () => { jest.advanceTimersByTime(5200); });
  await flush();
  expect(M.series.update).toHaveBeenCalled();
  expect(M.series.setData.mock.calls.length).toBe(setDataCalls);
  expect(M.ts.fitContent).not.toHaveBeenCalled();
  expect(container.querySelector('[data-testid="chart-mode"]').textContent).toBe("LIVE");
});

test("caricamento progressivo a sinistra: prepende e conserva la porzione visibile", async () => {
  route({ ohlc: (url) => url.includes("before=1794000000") ? { data: envelope({ bars: bars(1000, 1_793_000_000), has_more: false, next_before: null }) } : { data: envelope() } });
  await mount();
  const handler = M.ts.subscribeVisibleLogicalRangeChange.mock.calls.slice(-1)[0][0];
  M.series.setData.mockClear();
  M.ts.setVisibleLogicalRange.mockClear();
  await act(async () => { handler({ from: 5, to: 160 }); });
  await flush();
  const older = calls.filter((c) => c.startsWith("/chart/ohlc") && c.includes("before=1794000000"));
  expect(older).toHaveLength(1);
  expect(older[0]).toContain("limit=1000");
  const merged = M.series.setData.mock.calls.slice(-1)[0][0];
  expect(merged).toHaveLength(2500);
  expect(merged[0].time).toBe(1_793_000_000);
  const view = M.ts.setVisibleLogicalRange.mock.calls.slice(-1)[0][0];
  expect(view).toEqual({ from: 10 + 1000, to: 170 + 1000 });                       // stessa finestra visibile, traslata di 1000 barre
  expect(M.ts.fitContent).not.toHaveBeenCalled();
  await act(async () => { handler({ from: 2, to: 120 }); });                          // fine dataset: nessun'altra richiesta
  await flush();
  expect(calls.filter((c) => c.includes("before=")).length).toBe(1);
});

test("selezione temporale: richiede la finestra attorno alla data scelta", async () => {
  route();
  await mount();
  const input = container.querySelector('[data-testid="chart-goto-input"]');
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
    setter.call(input, "2026-11-18T10:30");
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await act(async () => { container.querySelector('[data-testid="chart-goto-form"]').dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
  await flush();
  const last = calls.filter((c) => c.startsWith("/chart/ohlc")).slice(-1)[0];
  const before = Number(new URL("http://x" + last).searchParams.get("before"));
  const target = Date.parse("2026-11-18T10:30:00Z") / 1000;
  expect(before).toBeGreaterThan(target);
  expect(before - target).toBeLessThan(900 * INITIAL_FRACTION + 1);
});
const INITIAL_FRACTION = 400;

test("marker dei trade: il campo `time` (backend) e `closeTime` sono entrambi riconosciuti, nessuno inventato", async () => {
  expect(markerTime({ closeTime: "2026-11-17T10:00:00Z" })).toBe(Date.parse("2026-11-17T10:00:00Z") / 1000);
  expect(markerTime({ time: "2026-11-17T10:00:00Z" })).toBe(Date.parse("2026-11-17T10:00:00Z") / 1000);
  expect(markerTime({ time: 1_794_000_000 })).toBe(1_794_000_000);
  expect(markerTime({})).toBeNull();
  route({ markersData: { data: { trades: [{ time: "2026-11-17T10:00:00Z", pnl: 5, strategy: "S1" }], open: [], shadows: [], visuals: [] } } });
  await mount();
  const withTime = M.createSeriesMarkers.mock.calls.filter((c) => c[1].length === 1);
  expect(withTime.length).toBeGreaterThan(0);
  route();
  M.createSeriesMarkers.mockClear();
  await act(async () => { root.render(<div />); });
  await act(async () => { root.render(<LiveChartPage />); });
  await flush();
  expect(M.createSeriesMarkers.mock.calls.every((c) => c[1].length === 0)).toBe(true);
});

test("nessuna fonte configurata: indisponibilita' esplicita", async () => {
  route({ sources: { data: { status: "UNAVAILABLE", reason: "CHART_STORE_NOT_CONFIGURED", sources: [] } } });
  await mount();
  expect(container.querySelector('[data-testid="chart-error"]').textContent).toContain("CHART_STORE_NOT_CONFIGURED");
  expect(calls.some((c) => c.startsWith("/chart/ohlc"))).toBe(false);
});

test("cambio di fonte: nessuna richiesta con un simbolo che la nuova fonte non contiene", async () => {
  const DS2 = { ...SOURCE, dataset_id: "DS2", label: "DS2", symbol_aliases: ["XAUUSD"], timeframes: ["M5", "M15"], feed_kind: "DUKASCOPY" };
  route({ sources: { data: { status: "AVAILABLE", sources: [SOURCE, DS2], default_source: "DS1" } } });
  await mount();
  const sel = container.querySelector('[data-testid="chart-source-select"]');
  await act(async () => {
    Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, "value").set.call(sel, "DS2");
    sel.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await flush();
  const urls = calls.filter((c) => c.startsWith("/chart/ohlc"));
  expect(urls.some((u) => u.includes("source=DS2") && u.includes("symbol=XAUUSD"))).toBe(true);
  expect(urls.some((u) => u.includes("source=DS2") && u.includes("symbol=GOLD"))).toBe(false);
  expect(container.querySelector('[data-testid="chart-symbol-select"]').value).toBe("XAUUSD");
});

test("selezione temporale: la vista e' centrata sull'indice della barra richiesta", async () => {
  const start = 1_794_100_000;
  route({ ohlc: () => ({ data: envelope({ bars: bars(452, start, 900), has_more: false, next_before: null }) }) });
  await mount();
  M.ts.setVisibleLogicalRange.mockClear();
  const target = start + 200 * 900;                                                  // barra n. 200
  const input = container.querySelector('[data-testid="chart-goto-input"]');
  const d = new Date(target * 1000).toISOString().slice(0, 16);
  await act(async () => {
    Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set.call(input, d);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await act(async () => { container.querySelector('[data-testid="chart-goto-form"]').dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
  await flush();
  const view = M.ts.setVisibleLogicalRange.mock.calls.slice(-1)[0][0];
  expect(view.from).toBeLessThan(200);
  expect(view.to).toBeGreaterThan(200);
  expect(Math.abs((view.from + view.to) / 2 - 200)).toBeLessThan(2);
});
