import {
  timeToIndex, indexToTime, project, unproject, snapAnchor, candleAnchor, freeAnchor, nearestBar,
  fibRetracementPrices, fibExtensionPrices, rulerMetrics, clipParametric, buildScene, sceneDistance, hitHandle,
  translateAnchors, linearTimeAxis, defaultUnits, toPips, semanticOptionsFor, sameInstrument, fmtTime, fmtPrice, ANCHORS_REQUIRED, formatDuration,
} from "./geometryMath";

const T0 = 1760000000;
const TF = 900;
const mkBars = (n, tf = TF, start = T0) =>
  Array.from({ length: n }, (_, i) => ({ time: start + i * tf, open: 2650 + i, high: 2655 + i, low: 2645 + i, close: 2652 + i }));

// contesto sintetico: 10 px per barra, prezzo 2640 in basso (y=400), 2 px per unita'; x(0)=50
function mkCtx(bars, tf = TF, over = {}) {
  return {
    bars, tfSec: tf, width: 800, height: 400,
    xOf: (i) => 50 + i * 10, yOf: (p) => 400 - (p - 2640) * 2,
    idxOf: (x) => (x - 50) / 10, priceOf: (y) => 2640 + (400 - y) / 2, ...over,
  };
}

describe("tempo <-> indice", () => {
  const bars = mkBars(20);
  test("barra esatta, frazione, estrapolazione", () => {
    expect(timeToIndex(bars, T0 + 3 * TF, TF)).toBe(3);
    expect(timeToIndex(bars, T0 + 3.5 * TF, TF)).toBeCloseTo(3.5);
    expect(timeToIndex(bars, T0 + 25 * TF, TF)).toBeCloseTo(25);
    expect(timeToIndex(bars, T0 - 2 * TF, TF)).toBeCloseTo(-2);
  });
  test("round trip tempo->indice->tempo senza variazioni (secondi interi)", () => {
    for (const t of [T0, T0 + 1, T0 + 450, T0 + 7 * TF + 13, T0 + 19 * TF, T0 + 30 * TF + 5, T0 - 400]) {
      expect(indexToTime(bars, timeToIndex(bars, t, TF), TF)).toBe(t);
    }
  });
  test("barre con gap (weekend): l'istante nel gap resta ordinato e invertibile", () => {
    const g = [...mkBars(5), ...mkBars(5, TF, T0 + 5 * TF + 172800)];
    const t = T0 + 4 * TF + 100000;
    const i = timeToIndex(g, t, TF);
    expect(i).toBeGreaterThan(4); expect(i).toBeLessThan(5);
    expect(indexToTime(g, i, TF)).toBe(t);
  });
  test("vuoto -> null", () => { expect(timeToIndex([], T0, TF)).toBeNull(); expect(indexToTime([], 1, TF)).toBeNull(); });
});

describe("proiezione dati <-> schermo", () => {
  const bars = mkBars(20);
  const ctx = mkCtx(bars);
  test("project/unproject sono inversi; la fonte canonica sono (t, price)", () => {
    const a = { t: T0 + 4 * TF, price: 2661.25 };
    const p = project(a, ctx);
    expect(p).toEqual({ x: 90, y: 400 - 21.25 * 2 });
    const u = unproject(p.x, p.y, ctx);
    expect(u.t).toBe(a.t); expect(u.price).toBeCloseTo(a.price, 9);
  });
  test("stessa geometria su un altro timeframe: ancora identica, posizione diversa", () => {
    const a = { t: T0 + 3600, price: 2650 };
    const barsH1 = mkBars(10, 3600);
    const ctxH1 = mkCtx(barsH1, 3600);
    const pM15 = project(a, ctx), pH1 = project(a, ctxH1);
    expect(pM15.x).not.toBe(pH1.x);
    expect(unproject(pM15.x, pM15.y, ctx).t).toBe(a.t);
    expect(unproject(pH1.x, pH1.y, ctxH1).t).toBe(a.t);
    expect(unproject(pH1.x, pH1.y, ctxH1).price).toBeCloseTo(a.price, 9);
  });
  test("zoom/pan: cambiare la scala non altera le coordinate dati", () => {
    const a = { t: T0 + 6 * TF, price: 2660 };
    const zoomed = mkCtx(bars, TF, { xOf: (i) => -300 + i * 40, idxOf: (x) => (x + 300) / 40, yOf: (p) => 400 - (p - 2640) * 8, priceOf: (y) => 2640 + (400 - y) / 8 });
    const p = project(a, zoomed);
    const u = unproject(p.x, p.y, zoomed);
    expect(u.t).toBe(a.t); expect(u.price).toBeCloseTo(a.price, 9);
  });
  test("scala non pronta (null) -> nessuna proiezione, nessun crash", () => {
    expect(project({ t: T0, price: 1 }, mkCtx(bars, TF, { yOf: () => null }))).toBeNull();
  });
});

describe("asse temporale lineare (regressione: logicalToCoordinate frazionario = 0 nel browser reale)", () => {
  test("proiezione e inversione continue, esatte anche per indici frazionari", () => {
    const ax = linearTimeAxis(4.78, 16.34);
    expect(ax.xOf(0)).toBeCloseTo(4.78, 9); expect(ax.xOf(1)).toBeCloseTo(16.34, 9);
    expect(ax.xOf(83.75)).toBeCloseTo(4.78 + 83.75 * 11.56, 9);
    for (const i of [0, 0.25, 7.5, 88, 99.25, -3.4, 250.75]) expect(ax.idxOf(ax.xOf(i))).toBeCloseTo(i, 9);
  });
  test("round trip tempo -> x -> tempo senza quantizzazione alla barra (clic libero esatto)", () => {
    const bars = mkBars(120, 3600), ax = linearTimeAxis(4.78, 16.34);
    const ctx = mkCtx(bars, 3600, { xOf: ax.xOf, idxOf: ax.idxOf });
    for (const t of [T0 + 83.75 * 3600, T0 + 91 * 3600 + 1234, T0 + 100.25 * 3600]) {
      const p = project({ t, price: 2650 }, ctx);
      expect(p.x).toBeGreaterThan(900);
      expect(unproject(p.x, p.y, ctx).t).toBe(t);
    }
  });
  test("scala degenere o non pronta -> null (nessun disegno, nessun crash)", () => {
    expect(linearTimeAxis(null, 5)).toBeNull(); expect(linearTimeAxis(5, 5)).toBeNull(); expect(linearTimeAxis(NaN, 1)).toBeNull(); expect(linearTimeAxis(10, 4)).toBeNull();
  });
});

describe("ancoraggi e snap OHLC", () => {
  const bars = mkBars(20);
  const ctx = mkCtx(bars);
  test("libero: nessun riferimento a candela", () => {
    const a = snapAnchor(100, 300, ctx, "free");
    expect(a.ref).toEqual({ kind: "FREE", projection_id: null });
    expect(a.t).toBe(T0 + 5 * TF); expect(a.price).toBeCloseTo(2690);
  });
  test.each(["open", "high", "low", "close"])("campo forzato %s: prezzo = campo della candela piu' vicina", (f) => {
    const a = snapAnchor(101, 10, ctx, f);                 // x=101 -> idx 5.1 -> barra 5
    expect(a.ref).toMatchObject({ kind: "CANDLE", bar_t: bars[5].time, field: f, projection_id: null });
    expect(a.price).toBe(bars[5][f]); expect(a.t).toBe(bars[5].time);
  });
  test("auto OHLC: aggancia il campo piu' vicino entro soglia, altrimenti libero", () => {
    const hy = ctx.yOf(bars[7].high);
    const near = snapAnchor(120, hy + 3, ctx, "ohlc");
    expect(near.ref).toMatchObject({ kind: "CANDLE", field: "high" }); expect(near.price).toBe(bars[7].high);
    const far = snapAnchor(120, hy - 80, ctx, "ohlc");
    expect(far.ref.kind).toBe("FREE");
  });
  test("candleAnchor / nearestBar", () => {
    expect(candleAnchor(bars[2], "low")).toEqual({ t: bars[2].time, price: bars[2].low, ref: { kind: "CANDLE", bar_t: bars[2].time, field: "low", projection_id: null } });
    expect(nearestBar(bars, T0 + 2 * TF + 100)).toBe(bars[2]);
    expect(nearestBar(bars, T0 + 2 * TF + 800)).toBe(bars[3]);
  });
  test("nessuna proiezione di candela inventata", () => {
    for (const f of ["open", "high", "low", "close"]) expect(candleAnchor(bars[0], f).ref.projection_id).toBeNull();
  });
});

describe("Fibonacci e righello", () => {
  test("retracement: 0 sul secondo ancoraggio, 1 sul primo", () => {
    const r = fibRetracementPrices({ price: 2600 }, { price: 2700 }, [0, 0.5, 0.618, 1]);
    expect(r.map((x) => x.price)).toEqual([2700, 2650, 2700 - 61.8, 2600]);
  });
  test("extension: livelli misurati da C lungo B-A, livelli utente", () => {
    const r = fibExtensionPrices({ price: 2600 }, { price: 2700 }, { price: 2650 }, [0, 1, 1.618]);
    expect(r.map((x) => x.price)).toEqual([2650, 2750, 2650 + 161.8]);
  });
  test("righello: prezzo, percentuale, barre, tempo", () => {
    const bars = mkBars(30);
    const m = rulerMetrics({ t: T0, price: 2650 }, { t: T0 + 8 * TF, price: 2665 }, bars, TF);
    expect(m.dPrice).toBe(15); expect(m.dPct).toBeCloseTo(0.566, 2); expect(m.dBars).toBe(8); expect(m.dSeconds).toBe(8 * TF);
    expect(formatDuration(8 * TF)).toBe("2h 0m");
  });
});

describe("scene (primitive in pixel)", () => {
  const bars = mkBars(30);
  const ctx = mkCtx(bars);
  const base = { clock_basis: "UTC", style: { extend: "none" } };
  const A = (i, p) => ({ t: T0 + i * TF, price: p });
  test("hline a tutta larghezza al prezzo giusto", () => {
    const s = buildScene({ ...base, type: "hline", anchors: [A(3, 2660)] }, ctx);
    const l = s.prims.find((p) => p.kind === "line");
    expect(l).toMatchObject({ x1: 0, x2: 800, y1: ctx.yOf(2660), y2: ctx.yOf(2660) });
  });
  test("vline a tutta altezza", () => {
    const s = buildScene({ ...base, type: "vline", anchors: [A(3, 2660)] }, ctx);
    expect(s.prims.find((p) => p.kind === "line")).toMatchObject({ x1: 80, x2: 80, y1: 0, y2: 400 });
  });
  test("diagonale: due ancoraggi, segmento esatto; ray estende a destra senza spostare le origini", () => {
    const g = { ...base, type: "trendline", anchors: [A(2, 2650), A(10, 2666)] };
    const seg = buildScene(g, ctx).prims.find((p) => p.kind === "line");
    expect([seg.x1, seg.y1, seg.x2, seg.y2]).toEqual([70, 380, 150, 348]);
    const ray = buildScene({ ...g, type: "ray" }, ctx).prims.find((p) => p.kind === "line");
    expect(ray.x1).toBe(70); expect(ray.x2).toBeCloseTo(800, 5); expect(ray.y2).toBeLessThan(ray.y1);
    const slope = (l) => (l.y2 - l.y1) / (l.x2 - l.x1);
    expect(slope(ray)).toBeCloseTo(slope(seg), 9);
    expect(g.anchors).toEqual([A(2, 2650), A(10, 2666)]);                    // origini intatte
  });
  test("estensione a sinistra/entrambi tramite style.extend; extended_line = entrambi", () => {
    const g = { ...base, type: "trendline", anchors: [A(10, 2680), A(14, 2686)] };
    const left = buildScene({ ...g, style: { extend: "left" } }, ctx).prims.find((p) => p.kind === "line");
    expect(left.x1).toBeCloseTo(0, 5); expect(left.x2).toBe(190);
    const both = buildScene({ ...g, type: "extended_line" }, ctx).prims.find((p) => p.kind === "line");
    expect(both.x1).toBeCloseTo(0, 5); expect(both.x2).toBeCloseTo(800, 5);
  });
  test("rettangolo e fascia di prezzo", () => {
    const r = buildScene({ ...base, type: "rectangle", anchors: [A(2, 2660), A(8, 2650)] }, ctx).prims.find((p) => p.kind === "rect");
    expect(r).toMatchObject({ x: 70, w: 60, y: ctx.yOf(2660), h: 20 });
    const b = buildScene({ ...base, type: "price_band", anchors: [A(2, 2660), A(8, 2650)] }, ctx).prims.find((p) => p.kind === "rect");
    expect(b).toMatchObject({ x: 0, w: 800, h: 20 });
  });
  test("fibonacci: una linea per livello utente", () => {
    const s = buildScene({ ...base, type: "fib_retracement", fib_levels: [0, 0.5, 1], anchors: [A(2, 2650), A(8, 2670)] }, ctx);
    expect(s.prims.filter((p) => p.kind === "line" && p.faint)).toHaveLength(3);
    expect(s.prims.some((p) => p.kind === "label" && p.text.startsWith("0.5 (2660"))).toBe(true);
  });
  test("righello con etichetta numerica", () => {
    const s = buildScene({ ...base, type: "ruler", anchors: [A(2, 2650), A(8, 2665)] }, ctx);
    expect(s.prims.find((p) => p.kind === "label").text).toMatch(/^Δ 15 \(0\.57%\) · 6 barre · 1h 30m$/);
  });
  test("handle per ogni ancoraggio visibile; fuori scala null non crasha", () => {
    expect(buildScene({ ...base, type: "trendline", anchors: [A(2, 2650), A(10, 2666)] }, ctx).handles).toHaveLength(2);
    const dead = mkCtx(bars, TF, { yOf: () => null });
    expect(buildScene({ ...base, type: "trendline", anchors: [A(2, 2650), A(10, 2666)] }, dead)).toEqual({ prims: [], handles: [] });
  });
});

describe("hit-test, clipping, traslazione", () => {
  const bars = mkBars(30);
  const ctx = mkCtx(bars);
  const A = (i, p) => ({ t: T0 + i * TF, price: p });
  test("segmento, interno del rettangolo e maniglia", () => {
    const sc = buildScene({ type: "trendline", clock_basis: "", style: {}, anchors: [A(2, 2650), A(10, 2666)] }, ctx);
    expect(sceneDistance(sc, 110, 364)).toBeLessThan(1);
    expect(sceneDistance(sc, 110, 300)).toBeGreaterThan(40);
    expect(hitHandle(sc, 72, 382)).toMatchObject({ i: 0 });
    expect(hitHandle(sc, 300, 100)).toBeNull();
    const rc = buildScene({ type: "rectangle", clock_basis: "", style: {}, anchors: [A(2, 2660), A(8, 2650)] }, ctx);
    expect(sceneDistance(rc, 100, 370)).toBe(0);
  });
  test("clipParametric: fuori dalla vista -> null", () => {
    expect(clipParametric(-50, -50, -10, -10, 0, 1, 100, 100)).toBeNull();
    expect(clipParametric(10, 10, 20, 20, 0, 1e6, 100, 100)).toMatchObject({ x2: 100, y2: 100 });
  });
  test("traslazione: stessi delta dati, ancoraggi a candela diventano liberi", () => {
    const anchors = [candleAnchor(bars[3], "high"), freeAnchor(T0 + 9 * TF, 2670)];
    const moved = translateAnchors(anchors, 1800, -5);
    expect(moved[0]).toEqual({ t: bars[3].time + 1800, price: bars[3].high - 5, ref: { kind: "FREE", projection_id: null } });
    expect(moved[1].t).toBe(T0 + 9 * TF + 1800);
  });
});

describe("vocabolario e formattazione", () => {
  test("significato attribuibile solo a forme compatibili; NONE sempre", () => {
    expect(semanticOptionsFor("trendline").map((c) => c.id)).toEqual(["NONE", "DIAG_BUY", "DIAG_SELL"]);
    expect(semanticOptionsFor("rectangle").map((c) => c.id)).toContain("ZONE_BUY_TO_SELL");
    expect(semanticOptionsFor("rectangle").map((c) => c.id)).not.toContain("DIAG_BUY");
    expect(semanticOptionsFor("text").map((c) => c.id)).toEqual(["NONE"]);
  });
  test("numero di ancoraggi per strumento", () => {
    expect(ANCHORS_REQUIRED).toMatchObject({ hline: 1, trendline: 2, ray: 2, rectangle: 2, fib_extension: 3, ruler: 2, text: 1 });
  });
  test("alias strumento e formati", () => {
    expect(sameInstrument("GOLD", "xauusd")).toBe(true); expect(sameInstrument("EURUSD", "GOLD")).toBe(false);
    expect(fmtTime(T0, "UTC")).toMatch(/UTC$/); expect(fmtTime(T0, "TERMINAL_EEST")).toMatch(/\(terminal\)$/);
    expect(fmtPrice(2650.123456789)).toBe("2650.12346"); expect(fmtPrice(null)).toBe("—");
  });
});


describe("unita' e pip configurabili (prezzo, pip, point, tick restano separati)", () => {
  test("convenzione iniziale XAUUSD/GOLD: 1 pip = 0,10 di prezzo; altri strumenti: nessun pip inventato", () => {
    expect(defaultUnits("GOLD")).toEqual({ pip_size: 0.1, point: null, tick_size: null });
    expect(defaultUnits("xauusd").pip_size).toBe(0.1);
    expect(defaultUnits("EURUSD")).toEqual({ pip_size: null, point: null, tick_size: null });
  });
  test("toPips: configurabile, null se il pip non e' noto o non valido", () => {
    expect(toPips(1.25, 0.1)).toBeCloseTo(12.5, 9);
    expect(toPips(1.25, 0.01)).toBeCloseTo(125, 9);
    expect(toPips(1.25, null)).toBeNull(); expect(toPips(1.25, 0)).toBeNull(); expect(toPips(1.25, -1)).toBeNull();
  });
  test("righello: i pip dipendono dalla configurazione, il prezzo no", () => {
    const bars = mkBars(30);
    const a1 = { t: T0, price: 2650 }, a2 = { t: T0 + 8 * TF, price: 2665 };
    expect(rulerMetrics(a1, a2, bars, TF, 0.1).dPips).toBeCloseTo(150, 9);
    expect(rulerMetrics(a1, a2, bars, TF, 0.01).dPips).toBeCloseTo(1500, 9);
    expect(rulerMetrics(a1, a2, bars, TF, null).dPips).toBeNull();
    expect(rulerMetrics(a1, a2, bars, TF, 0.1).dPrice).toBe(15);
  });
  test("etichetta del righello con pip", () => {
    const ctx = mkCtx(mkBars(30), TF, { pipSize: 0.1 });
    const sc = buildScene({ type: "ruler", clock_basis: "", style: {}, anchors: [{ t: T0 + 2 * TF, price: 2650 }, { t: T0 + 8 * TF, price: 2665 }] }, ctx);
    expect(sc.prims.find((p) => p.kind === "label").text).toMatch(/^Δ 15 = 150 pip \(0\.57%\) · 6 barre · 1h 30m$/);
  });
});
