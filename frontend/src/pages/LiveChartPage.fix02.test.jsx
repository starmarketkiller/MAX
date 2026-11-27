// CHART-REAL-DATA-V1-FIX-01: FIX-02 (risposte obsolete, CRDV1R-02) e FIX-03 (Vai-a-data, CRDV1R-03).
// Le due prove "INDEPENDENT" sono i riproduttori della review CRDV1R (IndependentRace.test.jsx), riportate senza ammorbidire le asserzioni.
import React, { act } from "react";
import { createRoot } from "react-dom/client";

jest.mock("lightweight-charts", () => {
  const series = { setData: jest.fn(), update: jest.fn() };
  const ts = {
    fitContent: jest.fn(), setVisibleLogicalRange: jest.fn(), getVisibleLogicalRange: jest.fn(() => ({ from: 10, to: 170 })),
    subscribeVisibleLogicalRangeChange: jest.fn(), unsubscribeVisibleLogicalRangeChange: jest.fn(),
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
import LiveChartPage, { responseMatches, resolveTarget } from "./LiveChartPage";

const M = require("lightweight-charts").__mocks;
let container;
let root;

const SOURCE = {
  dataset_id: "DS1", label: "DS1 reale", symbol_aliases: ["GOLD", "XAUUSD"], timeframes: ["M1", "M5", "M15", "M30", "H1", "H4"], feed_kind: "MT5_BROKER_EXPORT",
  instrument_spec: { pip_convention: { pip_price_usd_per_oz: 0.1 } },
};
const DS2 = { ...SOURCE, dataset_id: "DS2", label: "DS2" };
const STEP = { M1: 60, M5: 300, M15: 900, M30: 1800, H1: 3600, H4: 14400 };
const T0 = 1_794_096_000;                                  // multiplo di 3600: gli istanti di test sono esprimibili al minuto nell'input

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
    next_before: 1_794_000_000, bars: bars(1500, T0, 900, 7), ...over,
  };
}
const q = (url) => Object.fromEntries(new URLSearchParams(url.split("?")[1]));
function deferred() {
  let resolve; let reject;
  const promise = new Promise((a, b) => { resolve = a; reject = b; });
  return { promise, resolve, reject };
}
// risposta fedele alla richiesta: dataset/timeframe/simbolo dell'URL (come fa il backend reale)
const faithful = (nBars = 40, over = () => ({})) => (url) => {
  const p = q(url);
  return { data: envelope({ dataset_id: p.source, timeframe: p.tf, symbol_requested: p.symbol, bars: bars(nBars, T0, STEP[p.tf]), has_more: false, next_before: null, ...over(p) }) };
};

let calls;
function route({ ohlc = faithful(), sources = { data: { status: "AVAILABLE", sources: [SOURCE, DS2], default_source: "DS1" } }, markers = () => ({ data: { trades: [], open: [], shadows: [], visuals: [] } }) } = {}) {
  calls = [];
  api.get.mockImplementation(async (url) => {
    calls.push(url);
    if (url.startsWith("/chart/sources")) return sources;
    if (url.startsWith("/chart/ohlc")) return ohlc(url);
    if (url.startsWith("/chart/markers")) return markers(url);
    throw new Error("unexpected " + url);
  });
}
const flush = async () => { for (let i = 0; i < 8; i++) await act(async () => { await Promise.resolve(); }); };
const $ = (id) => container.querySelector(`[data-testid="${id}"]`);
const strip = () => ($("chart-dataset-strip")?.textContent || "");
const lastSet = () => M.series.setData.mock.calls.slice(-1)[0]?.[0];
const lastView = () => M.ts.setVisibleLogicalRange.mock.calls.slice(-1)[0]?.[0];
const handler = () => M.ts.subscribeVisibleLogicalRangeChange.mock.calls.slice(-1)[0][0];

beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
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
afterEach(() => { act(() => root.unmount()); container.remove(); });

async function mount() { await act(async () => { root.render(<LiveChartPage />); }); await flush(); }
const click = async (id) => { await act(async () => { $(id).click(); }); await flush(); };
const selectValue = async (id, v) => {
  await act(async () => {
    const el = $(id);
    Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, "value").set.call(el, v);
    el.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await flush();
};
const goto = async (iso) => {
  await act(async () => {
    const el = $("chart-goto-input");
    Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set.call(el, iso);
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await act(async () => { $("chart-goto-form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })); });
  await flush();
};
const isoOf = (t) => new Date(t * 1000).toISOString().slice(0, 16);

// =====================================================================================
// FIX-02 — risposte obsolete
// =====================================================================================
test("INDEPENDENT late M15 response must not replace the selected H1 series", async () => {
  const late = deferred();
  route({ ohlc: (url) => (url.includes("tf=M15") ? late.promise : { data: envelope({ timeframe: "H1", bars: bars(5, T0, 3600), has_more: false }) }) });
  await mount();
  await click("chart-tf-H1");
  expect(strip()).toContain("GOLD H1");
  await act(async () => late.resolve({ data: envelope({ timeframe: "M15", bars: bars(9, T0, 900), has_more: false }) }));
  await flush();
  expect(strip()).toContain("GOLD H1");
  expect(lastSet()).toHaveLength(5);
});

test("INDEPENDENT previous dataset response must not replace newly selected dataset", async () => {
  const old = deferred();
  route({ ohlc: (u) => (u.includes("source=DS1") ? old.promise : { data: envelope({ dataset_id: "DS2", bars: bars(3, T0), has_more: false }) }) });
  await mount();
  await selectValue("chart-source-select", "DS2");
  expect(strip()).toContain("DS2");
  await act(async () => old.resolve({ data: envelope({ dataset_id: "DS1", bars: bars(7, T0), has_more: false }) }));
  await flush();
  expect($("chart-source-select").value).toBe("DS2");
  expect(strip()).toContain("DS2");
});

test("cambio rapido H4 -> M5: la risposta H4 tardiva non sostituisce M5 (candele, provenienza, caricamento)", async () => {
  const h4 = deferred();
  route({ ohlc: (url) => (url.includes("tf=H4") ? h4.promise : faithful(30)(url)) });
  await mount();
  await click("chart-tf-H4");
  await click("chart-tf-M5");
  expect(strip()).toContain("GOLD M5");
  const setCalls = M.series.setData.mock.calls.length;
  await act(async () => h4.resolve(faithful(11)("/chart/ohlc?source=DS1&symbol=GOLD&tf=H4&limit=1500")));
  await flush();
  expect(strip()).toContain("GOLD M5");
  expect(strip()).toContain("30 barre");
  expect(lastSet()).toHaveLength(30);
  expect(M.series.setData.mock.calls.length).toBe(setCalls);           // nessun setData causato dalla risposta obsoleta
  expect($("chart-refresh").disabled).toBe(false);                      // indicatore di caricamento coerente col contesto corrente
  expect($("chart-loading")).toBeNull();
});

test("cambio rapido M5 -> M15 -> H1: qualunque ordine di arrivo lascia H1", async () => {
  for (const order of [["M5", "M15"], ["M15", "M5"]]) {
    const d = { M5: deferred(), M15: deferred() };
    route({ ohlc: (url) => { const t = q(url).tf; return d[t] ? d[t].promise : faithful(12)(url); } });
    await act(async () => { root.render(<div />); });
    await mount();
    await click("chart-tf-M5");
    await click("chart-tf-M15");
    await click("chart-tf-H1");
    expect(strip()).toContain("GOLD H1");
    for (const t of order) {
      await act(async () => d[t].resolve(faithful(7)(`/chart/ohlc?source=DS1&symbol=GOLD&tf=${t}&limit=1500`)));
      await flush();
    }
    expect(strip()).toContain("GOLD H1");
    expect(lastSet()).toHaveLength(12);
  }
});

test("cambio simbolo: ne' candele ne' marker del simbolo precedente sopravvivono", async () => {
  const oldOhlc = deferred();
  const oldMarkers = deferred();
  const trade = (s) => ({ strategy: s, pnl: 5, closeTime: T0 + 900 });
  route({
    ohlc: (url) => (q(url).symbol === "GOLD" && url.includes("tf=M15") && calls.filter((c) => c.startsWith("/chart/ohlc")).length === 1 ? oldOhlc.promise : faithful(4)(url)),
    markers: (url) => (url.includes("symbol=GOLD") ? oldMarkers.promise : { data: { trades: [trade("XAU_STRAT")], open: [], shadows: [], visuals: [] } }),
  });
  await mount();
  await selectValue("chart-symbol-select", "XAUUSD");
  await act(async () => { oldOhlc.resolve(faithful(9)("/chart/ohlc?source=DS1&symbol=GOLD&tf=M15&limit=1500")); oldMarkers.resolve({ data: { trades: [trade("GOLD_STRAT")], open: [], shadows: [], visuals: [] } }); });
  await flush();
  expect(lastSet()).toHaveLength(4);
  const labels = M.createSeriesMarkers.mock.calls.flatMap((c) => c[1].map((m) => m.text));
  expect(labels.some((t) => t.includes("GOLD_STRAT"))).toBe(false);
  expect(labels.some((t) => t.includes("XAU_STRAT"))).toBe(true);
});

test("paginazione pendente durante il cambio di timeframe: scartata, e non blocca la paginazione del nuovo contesto", async () => {
  const page = deferred();
  route({ ohlc: (url) => {
    const p = q(url);
    if (p.before && p.tf === "M15") return page.promise;
    if (p.tf === "H1") return { data: envelope({ timeframe: "H1", bars: bars(30, T0, 3600), has_more: true, next_before: T0 - 3600 }) };
    return { data: envelope({ timeframe: "M15", bars: bars(50, T0, 900), has_more: true, next_before: T0 - 900 }) };
  } });
  await mount();
  await act(async () => handler()({ from: 5, to: 100 }));                              // avvia la paginazione M15
  await flush();
  expect(calls.filter((c) => c.includes("before="))).toHaveLength(1);
  await click("chart-tf-H1");
  expect(strip()).toContain("GOLD H1");
  await act(async () => page.resolve({ data: envelope({ timeframe: "M15", bars: bars(1000, T0 - 900000, 900), has_more: true, next_before: 1 }) }));
  await flush();
  expect(strip()).toContain("GOLD H1");
  expect(strip()).toContain("30 barre");
  expect(lastSet()).toHaveLength(30);
  await act(async () => handler()({ from: 5, to: 100 }));                              // il nuovo contesto puo' paginare (il contatore del vecchio non lo blocca)
  await flush();
  expect(calls.filter((c) => c.includes("tf=H1") && c.includes("before="))).toHaveLength(1);
});

test("richieste concorrenti (due navigazioni): vince l'ultima avviata, l'esito della precedente (lenta) e' ignorato", async () => {
  const slow = deferred();
  let n = 0;
  route({ ohlc: (url) => { if (!q(url).before) return faithful(20)(url); n += 1; return n === 1 ? slow.promise : { data: envelope({ bars: bars(1500, T0, 900), has_more: true, next_before: T0 }) }; } });
  await mount();
  await goto(isoOf(T0 + 100 * 900));                                                    // 1a navigazione: lenta
  await goto(isoOf(T0 + 1125 * 900));                                                   // 2a navigazione: veloce
  expect(lastSet()).toHaveLength(1500);
  const sets = M.series.setData.mock.calls.length;
  await act(async () => slow.resolve({ data: envelope({ bars: bars(1500, T0 - 1500 * 900, 900), has_more: true, next_before: 1 }) }));
  await flush();
  expect(M.series.setData.mock.calls.length).toBe(sets);
  expect(Math.abs((lastView().from + lastView().to) / 2 - 1125)).toBeLessThan(2);
});

test("refresh manuale durante il caricamento iniziale: l'esito iniziale (obsoleto) e' ignorato", async () => {
  const slow = deferred();
  let n = 0;
  route({ ohlc: (url) => { n += 1; return n === 1 ? slow.promise : faithful(33)(url); } });
  await act(async () => { root.render(<LiveChartPage />); });
  await flush();
  expect($("chart-refresh").disabled).toBe(true);                                       // caricamento in corso
  await act(async () => slow.resolve(faithful(99)("/chart/ohlc?source=DS1&symbol=GOLD&tf=M15&limit=1500")));
  await flush();
  expect(lastSet()).toHaveLength(99);
  await click("chart-refresh");
  expect(lastSet()).toHaveLength(33);
  expect(strip()).toContain("33 barre");
});

test("errore obsoleto: un errore tardivo del contesto precedente non cancella i dati ne' mostra messaggi", async () => {
  const late = deferred();
  route({ ohlc: (url) => (url.includes("tf=M15") ? late.promise : faithful(8)(url)) });
  await mount();
  await click("chart-tf-H1");
  await act(async () => late.reject({ response: { status: 503, data: { detail: { code: "SEGMENT_HASH_MISMATCH" } } } }));
  await flush();
  expect($("chart-error")).toBeNull();
  expect(strip()).toContain("GOLD H1");
  expect(lastSet()).toHaveLength(8);
});

test("errore obsoleto sulla paginazione: non mostra errori sul contesto corrente", async () => {
  const page = deferred();
  route({ ohlc: (url) => (q(url).before ? page.promise : faithful(8, () => ({ has_more: true, next_before: 5 }))(url)) });
  await mount();
  await act(async () => handler()({ from: 5, to: 100 }));
  await flush();
  await click("chart-tf-H1");
  await act(async () => page.reject({ response: { status: 403, data: { detail: { code: "PARTITION_NOT_AUTHORIZED" } } } }));
  await flush();
  expect($("chart-error")).toBeNull();
  expect(strip()).toContain("GOLD H1");
});

test("richieste annullate: il cambio di contesto aborta le richieste in volo (signal)", async () => {
  const signals = [];
  api.get.mockImplementation(async (url, opts) => {
    if (url.startsWith("/chart/sources")) return { data: { status: "AVAILABLE", sources: [SOURCE, DS2], default_source: "DS1" } };
    if (url.startsWith("/chart/markers")) return { data: { trades: [], open: [], shadows: [], visuals: [] } };
    signals.push(opts?.signal);
    return new Promise(() => {});
  });
  await mount();
  await click("chart-tf-H1");
  expect(signals.length).toBeGreaterThanOrEqual(2);
  expect(signals[0].aborted).toBe(true);
  expect(signals[signals.length - 1].aborted).toBe(false);
});

test("smontaggio e rimontaggio: la risposta tardiva dell'istanza smontata non tocca la nuova", async () => {
  const late = deferred();
  const errors = jest.spyOn(console, "error").mockImplementation(() => {});
  route({ ohlc: (url) => (calls.filter((c) => c.startsWith("/chart/ohlc")).length === 1 ? late.promise : faithful(6)(url)) });
  await mount();
  await act(async () => { root.render(<div />); });
  await mount();                                                                        // nuova istanza: richiesta veloce
  expect(lastSet()).toHaveLength(6);
  await act(async () => late.resolve(faithful(77)("/chart/ohlc?source=DS1&symbol=GOLD&tf=M15&limit=1500")));
  await flush();
  expect(lastSet()).toHaveLength(6);
  expect(strip()).toContain("6 barre");
  expect(errors.mock.calls.filter((c) => String(c[0]).includes("unmounted") || String(c[0]).includes("not wrapped"))).toHaveLength(0);
  errors.mockRestore();
});

test("identita' della risposta: dataset/timeframe/simbolo non coerenti con la richiesta sono scartati", async () => {
  route({ ohlc: () => ({ data: envelope({ timeframe: "H1", bars: bars(5, T0, 3600), has_more: false }) }) });   // risponde H1 a una richiesta M15
  await mount();
  expect($("chart-error").textContent).toContain("non coerente");
  expect(M.series.setData.mock.calls.every((c) => c[0].length === 0)).toBe(true);
  expect(responseMatches({ dataset_id: "A", timeframe: "M5" }, { source: "A", tf: "M5", symbol: "GOLD" })).toBe(true);
  expect(responseMatches({ dataset_id: "B" }, { source: "A", tf: "M5", symbol: "GOLD" })).toBe(false);
  expect(responseMatches({ symbol_requested: "XAUUSD" }, { source: "A", tf: "M5", symbol: "GOLD" })).toBe(false);
});

// =====================================================================================
// FIX-03 — Vai-a-data
// =====================================================================================
const gotoRoute = (list, extra = {}) => route({ ohlc: (url) => (q(url).before ? { data: envelope({ bars: list, has_more: true, next_before: list[0].time, ...extra }) } : faithful(40)(url)) });

test("goto: data gia' presente -> vista centrata sulla barra, nessuna nota", async () => {
  const list = bars(1500, T0, 900);
  gotoRoute(list);
  await mount();
  const target = T0 + 1125 * 900;
  await goto(isoOf(target));
  expect(calls.some((c) => c.includes(`before=${target + 375 * 900}`))).toBe(true);
  const v = lastView();
  expect(Math.abs((v.from + v.to) / 2 - 1125)).toBeLessThan(2);
  expect($("chart-goto-note")).toBeNull();
});

test("goto: data non ancora caricata -> una sola richiesta con intervallo che contiene il target", async () => {
  gotoRoute(bars(1500, T0 - 800 * 900, 900));
  await mount();
  const before = calls.length;
  const target = T0 - 100 * 900;
  await goto(isoOf(target));
  const added = calls.slice(before).filter((c) => c.startsWith("/chart/ohlc"));
  expect(added).toHaveLength(1);
  expect(Number(q(added[0]).before)).toBeGreaterThan(target);
  expect(lastSet()[Math.round((lastView().from + lastView().to) / 2)].time).toBeLessThanOrEqual(target + 900);
});

test("goto: data oltre l'ultima barra -> nota esplicita e coda mostrata", async () => {
  gotoRoute(bars(1500, T0, 900));
  await mount();
  await goto(isoOf(T0 + 1500 * 900 + 7 * 86400));
  expect($("chart-goto-note").textContent).toContain("oltre l'ultima barra");
});

test("goto: data senza contrattazioni (buco) -> nota e vista sulla barra successiva", async () => {
  const list = [...bars(600, T0, 900), ...bars(600, T0 + 600 * 900 + 4 * 3600, 900)];
  gotoRoute(list);
  await mount();
  const gapTarget = T0 + 600 * 900 + 2 * 3600;
  await goto(isoOf(gapTarget));
  expect($("chart-goto-note").textContent).toContain("Nessuna contrattazione");
  expect(Math.abs((lastView().from + lastView().to) / 2 - 600)).toBeLessThan(2);
});

test("goto: data precedente alla copertura -> nota e prima barra disponibile", async () => {
  route({ ohlc: (url) => (q(url).before ? { data: envelope({ bars: bars(1500, T0, 900), has_more: false, next_before: null }) } : faithful(40)(url)) });
  await mount();
  await goto(isoOf(T0 - 5 * 86400));
  expect($("chart-goto-note").textContent).toContain("precedente alla copertura");
});

test("goto: intervallo non autorizzato (403) -> messaggio nella nota, il grafico precedente resta", async () => {
  route({ ohlc: (url) => (q(url).before ? Promise.reject({ response: { status: 403, data: { detail: { code: "PARTITION_NOT_AUTHORIZED" } } } }) : faithful(40)(url)) });
  await mount();
  const setCalls = M.series.setData.mock.calls.length;
  await goto(isoOf(T0 - 86400 * 30));
  expect($("chart-goto-note").textContent).toContain("non autorizzati");
  expect($("chart-error")).toBeNull();
  expect(M.series.setData.mock.calls.length).toBe(setCalls);
  expect(strip()).toContain("40 barre");
});

test("goto: cambio timeframe durante la navigazione -> la risposta del goto e' scartata", async () => {
  const slow = deferred();
  route({ ohlc: (url) => (q(url).before && q(url).tf === "M15" ? slow.promise : faithful(25)(url)) });
  await mount();
  await goto(isoOf(T0 + 3600));
  await click("chart-tf-H1");
  await act(async () => slow.resolve({ data: envelope({ bars: bars(1500, T0, 900), has_more: false, next_before: null }) }));
  await flush();
  expect(strip()).toContain("GOLD H1");
  expect(lastSet()).toHaveLength(25);
  expect($("chart-goto-note")).toBeNull();
});

test("goto: cambio dataset durante la navigazione -> la risposta del goto e' scartata", async () => {
  const slow = deferred();
  route({ ohlc: (url) => (q(url).before && q(url).source === "DS1" ? slow.promise : faithful(25)(url)) });
  await mount();
  await goto(isoOf(T0 + 3600));
  await selectValue("chart-source-select", "DS2");
  await act(async () => slow.resolve({ data: envelope({ dataset_id: "DS1", bars: bars(1500, T0, 900), has_more: false, next_before: null }) }));
  await flush();
  expect(strip()).toContain("DS2");
  expect(lastSet()).toHaveLength(25);
});

test("goto: dataset a copertura incompleta (barre PARTIAL) -> la data e' risolta senza presentare le barre come complete", async () => {
  const list = bars(1500, T0, 900, 3);
  gotoRoute(list);
  await mount();
  await goto(isoOf(T0 + 1125 * 900));
  expect(lastSet().some((b) => b.color && b.color.startsWith("rgba"))).toBe(true);
  expect(container.querySelector('[data-testid="chart-partial-legend"]')).not.toBeNull();
});

test("goto: un range-change emesso in modo sincrono durante setData NON avvia paginazioni e non sposta la vista", async () => {
  gotoRoute(bars(1500, T0, 900));
  await mount();
  M.series.setData.mockImplementation(() => { handler()({ from: 3, to: 80 }); });        // evento "stale" durante l'applicazione dei dati (causa di CRDV1R-03)
  const before = calls.filter((c) => c.includes("before=")).length;
  await goto(isoOf(T0 + 1125 * 900));
  expect(calls.filter((c) => c.includes("before=")).length - before).toBe(1);            // solo la richiesta del goto
  expect(Math.abs((lastView().from + lastView().to) / 2 - 1125)).toBeLessThan(2);
});

test("goto: la paginazione successiva conserva la vista sul target (offset calcolato sul range ATTUALE)", async () => {
  gotoRoute(bars(1500, T0, 900));
  await mount();
  await goto(isoOf(T0 + 1125 * 900));
  M.ts.getVisibleLogicalRange.mockImplementation(() => ({ from: 20, to: 180 }));         // l'utente ha scorrotto: il range al completamento e' questo
  M.ts.setVisibleLogicalRange.mockClear();
  await act(async () => handler()({ from: 20, to: 180 }));
  await flush();
  expect(lastView()).toEqual({ from: 20 + 1500, to: 180 + 1500 });
});

test("goto: dichiara l'orologio del dataset e non sostiene UTC assoluto (clock terminale)", async () => {
  route();
  await mount();
  expect($("chart-goto-clock").textContent).toContain("UTC assoluto non verificato");
});

test("goto: input vuoto -> nessuna richiesta; con secondi (formato esteso) la data e' comunque letta", async () => {
  route();
  await mount();
  const before = calls.length;
  await goto("");
  expect(calls.length).toBe(before);
  await goto(isoOf(T0 + 3600) + ":15");
  expect(calls.length).toBe(before + 1);
});

test("resolveTarget: copertura per barre che contengono la data (non solo uguaglianza esatta)", () => {
  const b = bars(10, 1000, 900);
  expect(resolveTarget(b, 1000 + 450, 900, true)).toEqual({ centre: 1000, note: null });
  expect(resolveTarget(b, 1000 + 900, 900, true)).toEqual({ centre: 1900, note: null });
});
