// CHART-GEOMETRY-01 — matematica pura delle geometrie.
// Fonte canonica = coordinate di dato (t epoch-secondi, price). I pixel sono SOLO una proiezione transitoria.

export const OHLC = ["open", "high", "low", "close"];
export const TF_SECONDS = { M1: 60, M5: 300, M15: 900, M30: 1800, H1: 3600, H4: 14400, D1: 86400, W1: 604800, MN1: 2592000 };
const BIG = 1e6;

export const TOOLS = [
  { id: "select", label: "Seleziona", anchors: 0 },
  { id: "hline", label: "Linea orizzontale", anchors: 1 },
  { id: "vline", label: "Linea verticale", anchors: 1 },
  { id: "trendline", label: "Diagonale", anchors: 2 },
  { id: "ray", label: "Ray", anchors: 2 },
  { id: "extended_line", label: "Linea estesa", anchors: 2 },
  { id: "rectangle", label: "Rettangolo", anchors: 2 },
  { id: "price_band", label: "Fascia di prezzo", anchors: 2 },
  { id: "text", label: "Annotazione", anchors: 1 },
  { id: "fib_retracement", label: "Fibonacci retracement", anchors: 2 },
  { id: "fib_extension", label: "Fibonacci extension", anchors: 3 },
  { id: "ruler", label: "Righello", anchors: 2 },
];
export const ANCHORS_REQUIRED = Object.fromEntries(TOOLS.filter((t) => t.id !== "select").map((t) => [t.id, t.anchors]));

export const SEMANTIC_CLASSES = [
  { id: "NONE", label: "Nessun significato", shapes: null },
  { id: "DIAG_BUY", label: "Diagonale BUY", shapes: ["trendline", "ray", "extended_line"] },
  { id: "DIAG_SELL", label: "Diagonale SELL", shapes: ["trendline", "ray", "extended_line"] },
  { id: "KEY_LEVEL_CLOSES", label: "Key level (chiusure congruenti)", shapes: ["hline", "price_band"] },
  { id: "LIQUIDITY_SPIKES", label: "Liquidità (spike congruenti)", shapes: ["hline", "price_band"] },
  { id: "ZONE_BUY_TO_SELL", label: "Zona BUY TO SELL", shapes: ["rectangle", "price_band"] },
  { id: "ZONE_SELL_TO_BUY", label: "Zona SELL TO BUY", shapes: ["rectangle", "price_band"] },
  { id: "INNER_SPACE", label: "Spazio interno tra impulsi", shapes: ["rectangle", "price_band"] },
  { id: "REACTION_ZONE", label: "Zona di possibile reazione", shapes: ["rectangle", "price_band"] },
  { id: "CONTINUATION_ZONE", label: "Zona di possibile continuazione", shapes: ["rectangle", "price_band"] },
];
export function semanticOptionsFor(type) {
  return SEMANTIC_CLASSES.filter((c) => c.shapes === null || c.shapes.includes(type));
}

export function sameInstrument(a, b) {
  const g = new Set(["XAUUSD", "GOLD"]);
  const x = String(a || "").toUpperCase(), y = String(b || "").toUpperCase();
  return x === y || (g.has(x) && g.has(y));
}

// ------------------------------------------------------------------ tempo <-> indice logico (frazionario)
export function timeToIndex(bars, t, tfSec) {
  const n = bars.length;
  if (!n || !Number.isFinite(t)) return null;
  const first = bars[0].time, last = bars[n - 1].time;
  if (t <= first) return (t - first) / tfSec;
  if (t >= last) return (n - 1) + (t - last) / tfSec;
  let lo = 0, hi = n - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (bars[mid].time <= t) lo = mid; else hi = mid - 1;
  }
  if (lo === n - 1) return lo;
  const a = bars[lo].time, b = bars[lo + 1].time;
  return lo + (t - a) / (b - a);
}

export function indexToTime(bars, idx, tfSec) {
  const n = bars.length;
  if (!n || !Number.isFinite(idx)) return null;
  if (idx <= 0) return Math.round(bars[0].time + idx * tfSec);
  if (idx >= n - 1) return Math.round(bars[n - 1].time + (idx - (n - 1)) * tfSec);
  const i = Math.floor(idx), f = idx - i;
  return Math.round(bars[i].time + f * (bars[i + 1].time - bars[i].time));
}

/** Asse temporale lineare dall'indice logico alla coordinata x, ricavato da DUE punti interi (x(0), x(1)).
 *  Necessario perche' logicalToCoordinate() di lightweight-charts e' affidabile solo per indici interi
 *  (per i frazionari restituisce 0) e coordinateToLogical() restituisce indici interi: la scala e' lineare, quindi
 *  la proiezione continua (e il clic libero esatto) si ottengono qui. */
export function linearTimeAxis(x0, x1) {
  const step = x1 - x0;
  if (!Number.isFinite(x0) || !Number.isFinite(x1) || !(step > 0)) return null;
  return { xOf: (idx) => x0 + idx * step, idxOf: (x) => (x - x0) / step, step };
}

// ctx = { bars, tfSec, xOf(idx)->px|null, yOf(price)->px|null, idxOf(px)->idx|null, priceOf(px)->price|null, width, height }
export function project(anchor, ctx) {
  const idx = timeToIndex(ctx.bars, anchor.t, ctx.tfSec);
  if (idx == null) return null;
  const x = ctx.xOf(idx), y = ctx.yOf(anchor.price);
  if (x == null || y == null || !Number.isFinite(x) || !Number.isFinite(y)) return null;
  return { x, y };
}

export function unproject(x, y, ctx) {
  const idx = ctx.idxOf(x), price = ctx.priceOf(y);
  if (idx == null || price == null || !Number.isFinite(idx) || !Number.isFinite(price)) return null;
  const t = indexToTime(ctx.bars, idx, ctx.tfSec);
  if (t == null) return null;
  return { t, price, idx };
}

// ------------------------------------------------------------------ ancoraggi e snap
export function freeAnchor(t, price) {
  return { t: Math.round(t), price: Number(price), ref: { kind: "FREE", projection_id: null } };
}

export function candleAnchor(bar, field) {
  return { t: bar.time, price: bar[field], ref: { kind: "CANDLE", bar_t: bar.time, field, projection_id: null } };
}

/** mode: "free" | "ohlc" (campo piu' vicino) | "open"|"high"|"low"|"close" (campo forzato). */
export function snapAnchor(x, y, ctx, mode = "free", thresholdPx = 16) {
  const p = unproject(x, y, ctx);
  if (!p) return null;
  if (mode === "free") return freeAnchor(p.t, p.price);
  const i = Math.max(0, Math.min(ctx.bars.length - 1, Math.round(p.idx)));
  const bar = ctx.bars[i];
  if (!bar) return freeAnchor(p.t, p.price);
  if (OHLC.includes(mode)) return candleAnchor(bar, mode);
  let best = null, bestD = Infinity;
  for (const f of OHLC) {
    const py = ctx.yOf(bar[f]);
    if (py == null) continue;
    const d = Math.abs(py - y);
    if (d < bestD) { bestD = d; best = f; }
  }
  return best != null && bestD <= thresholdPx ? candleAnchor(bar, best) : freeAnchor(p.t, p.price);
}

export function nearestBar(bars, t) {
  if (!bars.length) return null;
  const idx = Math.round(Math.max(0, Math.min(bars.length - 1, timeToIndex(bars, t, 1) ?? 0)));
  let best = bars[idx], bd = Math.abs(best.time - t);
  for (const j of [idx - 1, idx + 1]) {
    if (bars[j] && Math.abs(bars[j].time - t) < bd) { best = bars[j]; bd = Math.abs(best.time - t); }
  }
  return best;
}

// ------------------------------------------------------------------ Fibonacci
export function fibRetracementPrices(a1, a2, levels) {
  // livello 0 = secondo ancoraggio, livello 1 = primo ancoraggio (convenzione dello strumento di ritracciamento)
  return levels.map((lv) => ({ level: lv, price: a2.price + (a1.price - a2.price) * lv }));
}
export function fibExtensionPrices(a, b, c, levels) {
  // proiezione trend-based: livello 0 = C, livello 1 = C + (B - A)
  return levels.map((lv) => ({ level: lv, price: c.price + (b.price - a.price) * lv }));
}

// ------------------------------------------------------------------ righello
export function formatDuration(sec) {
  const s = Math.abs(Math.round(sec));
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return `${sec < 0 ? "-" : ""}${d ? d + "g " : ""}${h || d ? h + "h " : ""}${m}m`.trim();
}
/** Unita' di ricerca: prezzo, pip, point e tick size restano grandezze SEPARATE. Convenzione iniziale XAUUSD/GOLD: 1 pip = 0,10 di prezzo. */
export function defaultUnits(symbol) {
  const gold = sameInstrument(symbol, "XAUUSD");
  return { pip_size: gold ? 0.1 : null, point: null, tick_size: null };
}
export function toPips(priceDelta, pipSize) {
  return pipSize && Number.isFinite(pipSize) && pipSize > 0 ? priceDelta / pipSize : null;
}
export function rulerMetrics(a1, a2, bars, tfSec, pipSize = null) {
  const dp = a2.price - a1.price;
  const i1 = timeToIndex(bars, a1.t, tfSec), i2 = timeToIndex(bars, a2.t, tfSec);
  return {
    dPrice: dp,
    dPips: toPips(dp, pipSize),
    dPct: a1.price ? (dp / a1.price) * 100 : null,
    dBars: i1 == null || i2 == null ? null : Math.round(i2 - i1),
    dSeconds: a2.t - a1.t,
  };
}

export function fmtPrice(p) {
  if (p == null || !Number.isFinite(p)) return "—";
  return String(Number(p.toFixed(5)));
}
export function fmtTime(t, clockBasis = "") {
  if (t == null || !Number.isFinite(t)) return "—";
  const terminal = String(clockBasis).toUpperCase().startsWith("TERMINAL");
  return new Date(t * 1000).toISOString().replace("T", " ").slice(0, 19) + (terminal ? " (terminal)" : " UTC");
}

// ------------------------------------------------------------------ geometria schermo
/** Taglia una retta (param t in [tMin,tMax] sulla direzione p1->p2) al rettangolo di vista. null se fuori. */
export function clipParametric(x1, y1, x2, y2, tMin, tMax, w, h) {
  const dx = x2 - x1, dy = y2 - y1;
  let t0 = tMin, t1 = tMax;
  const edges = [[-dx, x1], [dx, w - x1], [-dy, y1], [dy, h - y1]];
  for (const [p, q] of edges) {
    if (p === 0) { if (q < 0) return null; continue; }
    const r = q / p;
    if (p < 0) { if (r > t1) return null; if (r > t0) t0 = r; }
    else { if (r < t0) return null; if (r < t1) t1 = r; }
  }
  if (t0 > t1) return null;
  return { x1: x1 + t0 * dx, y1: y1 + t0 * dy, x2: x1 + t1 * dx, y2: y1 + t1 * dy };
}

function lineExtension(g) {
  if (g.type === "ray") return "right";
  if (g.type === "extended_line") return "both";
  return g.style?.extend || "none";
}

/** Costruisce le primitive di disegno (in pixel) da una geometria. Nessuno stato, nessun canvas. */
export function buildScene(g, ctx) {
  const prims = [], handles = [];
  const { width: w, height: h } = ctx;
  const pts = g.anchors.map((a) => project(a, ctx));
  const label = (x, y, text, align = "left") => prims.push({ kind: "label", x, y, text, align });
  g.anchors.forEach((a, i) => { if (pts[i]) handles.push({ i, x: pts[i].x, y: pts[i].y }); });
  const fullH = (price, text) => {
    const y = ctx.yOf(price);
    if (y == null) return;
    prims.push({ kind: "line", x1: 0, y1: y, x2: w, y2: y });
    if (text !== false) label(w - 6, y - 3, text ?? fmtPrice(price), "right");
  };
  switch (g.type) {
    case "hline": fullH(g.anchors[0].price); break;
    case "vline": if (pts[0]) { prims.push({ kind: "line", x1: pts[0].x, y1: 0, x2: pts[0].x, y2: h }); label(pts[0].x + 4, 12, fmtTime(g.anchors[0].t, g.clock_basis).slice(5, 16)); } break;
    case "trendline": case "ray": case "extended_line": {
      if (!pts[0] || !pts[1]) break;
      const ext = lineExtension(g);
      const tMin = ext === "left" || ext === "both" ? -BIG : 0;
      const tMax = ext === "right" || ext === "both" ? BIG : 1;
      const seg = clipParametric(pts[0].x, pts[0].y, pts[1].x, pts[1].y, tMin, tMax, w, h);
      if (seg) prims.push({ kind: "line", ...seg });
      label(pts[1].x + 6, pts[1].y - 4, fmtPrice(g.anchors[1].price));
      break;
    }
    case "rectangle": {
      if (!pts[0] || !pts[1]) break;
      const x = Math.min(pts[0].x, pts[1].x), y = Math.min(pts[0].y, pts[1].y);
      prims.push({ kind: "rect", x, y, w: Math.abs(pts[1].x - pts[0].x), h: Math.abs(pts[1].y - pts[0].y), fill: true });
      label(x + 4, y + 12, `${fmtPrice(Math.max(g.anchors[0].price, g.anchors[1].price))} / ${fmtPrice(Math.min(g.anchors[0].price, g.anchors[1].price))}`);
      break;
    }
    case "price_band": {
      const y1 = ctx.yOf(g.anchors[0].price), y2 = ctx.yOf(g.anchors[1].price);
      if (y1 == null || y2 == null) break;
      prims.push({ kind: "rect", x: 0, y: Math.min(y1, y2), w, h: Math.abs(y2 - y1), fill: true });
      label(w - 6, Math.min(y1, y2) + 12, `${fmtPrice(Math.max(g.anchors[0].price, g.anchors[1].price))} / ${fmtPrice(Math.min(g.anchors[0].price, g.anchors[1].price))}`, "right");
      break;
    }
    case "text": if (pts[0]) label(pts[0].x + 6, pts[0].y - 6, g.text || ""); break;
    case "fib_retracement": case "fib_extension": {
      const levels = g.fib_levels || [];
      const rows = g.type === "fib_retracement"
        ? (g.anchors.length === 2 ? fibRetracementPrices(g.anchors[0], g.anchors[1], levels) : [])
        : (g.anchors.length === 3 ? fibExtensionPrices(g.anchors[0], g.anchors[1], g.anchors[2], levels) : []);
      const xs = pts.filter(Boolean).map((p) => p.x);
      const x1 = xs.length ? Math.min(...xs) : 0;
      const x2 = g.style?.extend === "right" || g.style?.extend === "both" ? w : (xs.length ? Math.max(...xs) : w);
      rows.forEach((r) => {
        const y = ctx.yOf(r.price);
        if (y == null) return;
        prims.push({ kind: "line", x1, y1: y, x2, y2: y, faint: true });
        label(x1 + 4, y - 3, `${r.level} (${fmtPrice(r.price)})`);
      });
      if (pts[0] && pts[1]) prims.push({ kind: "line", x1: pts[0].x, y1: pts[0].y, x2: pts[1].x, y2: pts[1].y, dashed: true });
      if (pts[1] && pts[2]) prims.push({ kind: "line", x1: pts[1].x, y1: pts[1].y, x2: pts[2].x, y2: pts[2].y, dashed: true });
      break;
    }
    case "ruler": {
      if (!pts[0] || !pts[1]) break;
      const m = rulerMetrics(g.anchors[0], g.anchors[1], ctx.bars, ctx.tfSec, ctx.pipSize);
      prims.push({ kind: "line", x1: pts[0].x, y1: pts[0].y, x2: pts[1].x, y2: pts[1].y, dashed: true });
      prims.push({ kind: "rect", x: Math.min(pts[0].x, pts[1].x), y: Math.min(pts[0].y, pts[1].y), w: Math.abs(pts[1].x - pts[0].x), h: Math.abs(pts[1].y - pts[0].y), fill: true });
      label(Math.max(pts[0].x, pts[1].x) + 6, (pts[0].y + pts[1].y) / 2,
        `Δ ${fmtPrice(m.dPrice)}${m.dPips == null ? "" : ` = ${Number(m.dPips.toFixed(1))} pip`} (${m.dPct == null ? "—" : m.dPct.toFixed(2)}%) · ${m.dBars ?? "—"} barre · ${formatDuration(m.dSeconds)}`);
      break;
    }
    default: break;
  }
  return { prims, handles };
}

// ------------------------------------------------------------------ hit-test
export function distPointSegment(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1, dy = y2 - y1;
  const l2 = dx * dx + dy * dy;
  const t = l2 === 0 ? 0 : Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / l2));
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}

/** Distanza (px) minima fra il punto e la scena; per i rettangoli l'interno conta come hit (distanza 0). */
export function sceneDistance(scene, px, py) {
  let best = Infinity;
  for (const p of scene.prims) {
    if (p.kind === "line") best = Math.min(best, distPointSegment(px, py, p.x1, p.y1, p.x2, p.y2));
    else if (p.kind === "rect") {
      const inside = px >= p.x && px <= p.x + p.w && py >= p.y && py <= p.y + p.h;
      if (inside) best = Math.min(best, 0);
      else {
        const dx = Math.max(p.x - px, 0, px - (p.x + p.w)), dy = Math.max(p.y - py, 0, py - (p.y + p.h));
        best = Math.min(best, Math.hypot(dx, dy));
      }
    } else if (p.kind === "label") {
      const wTxt = Math.max(20, String(p.text).length * 6.2);
      const x0 = p.align === "right" ? p.x - wTxt : p.x;
      if (px >= x0 && px <= x0 + wTxt && py >= p.y - 12 && py <= p.y + 3) best = Math.min(best, 0);
    }
  }
  return best;
}

export function hitHandle(scene, px, py, radius = 9) {
  let best = null, bd = Infinity;
  for (const hnd of scene.handles) {
    const d = Math.hypot(hnd.x - px, hnd.y - py);
    if (d <= radius && d < bd) { best = hnd; bd = d; }
  }
  return best;
}

/** Trasla tutti gli ancoraggi nello spazio dei dati (dt secondi, dp prezzo). Gli ancoraggi a candela diventano liberi. */
export function translateAnchors(anchors, dt, dp) {
  return anchors.map((a) => freeAnchor(a.t + dt, a.price + dp));
}

export function describeDraft(tool, anchors) {
  const need = ANCHORS_REQUIRED[tool] || 0;
  return need > anchors.length ? `${tool}: clic per l'ancoraggio ${anchors.length + 1}/${need}` : "";
}
