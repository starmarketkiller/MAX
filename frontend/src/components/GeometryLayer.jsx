// CHART-GEOMETRY-01 — strumenti geometrici manuali sopra la Chart NEXUS.
// Canonico = (tempo, prezzo) dei dati. Il canvas e' una proiezione ricalcolata a ogni zoom/pan/resize/cambio timeframe.
// Una geometria e' un'annotazione dell'utente: NON e' un segnale e non crea ordini.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import useGeometrySession, { errText } from "@/lib/geometry/useGeometrySession";
import {
  TOOLS, ANCHORS_REQUIRED, SEMANTIC_CLASSES, semanticOptionsFor, TF_SECONDS, buildScene, sceneDistance, hitHandle, snapAnchor,
  translateAnchors, unproject, project, linearTimeAxis, defaultUnits, fmtPrice, fmtTime, nearestBar, candleAnchor, freeAnchor, sameInstrument, OHLC,
} from "@/lib/geometry/geometryMath";

const SWATCHES = ["#2962ff", "#ef4444", "#16a34a", "#f59e0b", "#a855f7", "#06b6d4", "#e5e7eb", "#111827"];
const DASH = { solid: [], dashed: [6, 4], dotted: [2, 3] };
const SNAP_MODES = [["free", "Libero"], ["ohlc", "Auto OHLC"], ["open", "Open"], ["high", "High"], ["low", "Low"], ["close", "Close"]];
const TOOL_GLYPH = { select: "⌖", hline: "─", vline: "│", trendline: "╱", ray: "↗", extended_line: "⟷", rectangle: "▭", price_band: "☰", text: "T", fib_retracement: "Fib", fib_extension: "FibX", ruler: "📏" };
const DEFAULT_COLOR = { rectangle: "#f59e0b", price_band: "#f59e0b", fib_retracement: "#a855f7", fib_extension: "#a855f7", ruler: "#06b6d4", text: "#e5e7eb" };

function parseTime(str) {
  const m = String(str).trim().match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/);
  if (!m) return null;
  const ms = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0));
  return Number.isFinite(ms) ? Math.round(ms / 1000) : null;
}

function Field({ label, children }) {
  return <label className="block text-[10px] text-muted-foreground mt-1.5">{label}{children}</label>;
}
const inputCls = "mt-0.5 w-full rounded border border-border bg-background px-1.5 py-0.5 text-[11px] font-mono text-foreground";
const btnCls = "rounded border border-border bg-card px-1.5 py-0.5 text-[11px] hover:bg-muted disabled:opacity-40";

const LS_UNITS = "nexus.chart.units.";
function loadUnits(symbol) {
  try {
    const raw = window.localStorage.getItem(LS_UNITS + String(symbol).toUpperCase());
    if (raw) return { ...defaultUnits(symbol), ...JSON.parse(raw) };
  } catch (err) { void err; }
  return defaultUnits(symbol);
}
const Portal = ({ el, children }) => (el ? createPortal(children, el) : children);

/** `shared` (opzionale): stato e sessione condivisi fra piu' grafici { S, tool, setTool, snapMode, setSnapMode, selectedId, setSelectedId,
 *  activeLayer, setActiveLayer, units, setUnits, toolbarEl, panelEl, hint }. `chrome=false`: il grafico non mostra toolbar/pannello e non ascolta la tastiera.
 *  `onPick(tool, anchor, info)`: gestisce gli strumenti "pick:*" (selezione di punti per le schede evento) al posto del disegno. */
export default function GeometryLayer({ chartRef, seriesRef, bars, meta, symbol, tf, source, epoch, dark = false, shared = null, chrome = true, onPick = null, paneId = "main" }) {
  const Local = useGeometrySession({ enabled: !shared });
  const S = shared ? shared.S : Local;
  const { geoms, layers } = S;
  const wrapRef = useRef(null);
  const canvasRef = useRef(null);
  const [toolL, setToolL] = useState("select");
  const [snapL, setSnapL] = useState("free");
  const [selL, setSelL] = useState(null);
  const [layerL, setLayerL] = useState("default");
  const [unitsL, setUnitsL] = useState(() => loadUnits(symbol));
  const tool = shared ? shared.tool : toolL, setTool = shared ? shared.setTool : setToolL;
  const snapMode = shared ? shared.snapMode : snapL, setSnapMode = shared ? shared.setSnapMode : setSnapL;
  const selectedId = shared ? shared.selectedId : selL, setSelectedId = shared ? shared.setSelectedId : setSelL;
  const activeLayer = shared ? shared.activeLayer : layerL, setActiveLayer = shared ? shared.setActiveLayer : setLayerL;
  const units = shared ? shared.units : unitsL;
  const setUnits = (u) => { if (shared) shared.setUnits(u); else { setUnitsL(u); try { window.localStorage.setItem(LS_UNITS + String(symbol).toUpperCase(), JSON.stringify(u)); } catch (err) { void err; } } };
  const [panelOpen, setPanelOpen] = useState(false);       // pannello chiuso di default: si apre da solo selezionando un oggetto
  const [note, setNote] = useState(null);
  const [tick, setTick] = useState(0);
  const [newName, setNewName] = useState("");
  const [newLayerName, setNewLayerName] = useState("");

  // ---- stato corrente leggibile dai gestori nativi (che vivono fuori dal ciclo di render) ----
  const R = useRef({});
  R.current = { tool, snapMode, selectedId, geoms, layers, bars, meta, symbol, tf, source, activeLayer, S, onPick, paneId, chrome, pipSize: units?.pip_size || null };
  useEffect(() => { if (selectedId && chrome) setPanelOpen(true); }, [selectedId, chrome]);
  const draftRef = useRef(null);          // { tool, anchors:[], cursor, downXY, down }
  const dragRef = useRef(null);           // { gid, mode:'handle'|'move', i, start, base }
  const overrideRef = useRef({});         // gid -> anchors in anteprima durante il trascinamento
  const hoverRef = useRef(null);
  const dirtyRef = useRef(true);
  const interceptRef = useRef(false);
  const suppressClickUntil = useRef(0);
  const sigRef = useRef("");
  const dark_ = useRef(dark); dark_.current = dark;

  const dirty = () => { dirtyRef.current = true; };
  useEffect(dirty, [geoms, layers, selectedId, tool, tick, bars, dark, units?.pip_size]);   // eslint-disable-line react-hooks/exhaustive-deps

  const layerState = useMemo(() => Object.fromEntries(layers.map((l) => [l.layer_id, l])), [layers]);
  const visibleGeoms = useMemo(() => geoms.filter((g) => g.status === "ACTIVE" && g.style?.visible !== false
    && (layerState[g.style?.layer]?.visible ?? true) && sameInstrument(g.symbol, symbol)), [geoms, layerState, symbol]);
  const visibleRef = useRef([]); visibleRef.current = visibleGeoms;
  const selected = geoms.find((g) => g.geometry_id === selectedId) || null;

  // ---- contesto di proiezione dal grafico reale ----
  const getCtx = useCallback(() => {
    const chart = chartRef.current, series = seriesRef.current, el = wrapRef.current;
    const b = R.current.bars;
    if (!chart || !series || !el || !b || !b.length) return null;
    const ts = chart.timeScale();
    let width = el.clientWidth, height = el.clientHeight;
    try { const w = ts.width(); if (w > 0) width = w; } catch (err) { void err; }
    try { const p = chart.paneSize ? chart.paneSize(0) : null; if (p && p.height > 0) height = p.height; } catch (err) { void err; }
    const axis = linearTimeAxis(ts.logicalToCoordinate(0), ts.logicalToCoordinate(1));   // scala lineare: vedi linearTimeAxis
    if (!axis) return null;
    return {
      bars: b, tfSec: TF_SECONDS[R.current.tf] || 900, width, height, pipSize: R.current.pipSize,
      xOf: axis.xOf, idxOf: axis.idxOf,
      yOf: (p) => series.priceToCoordinate(p), priceOf: (y) => series.coordinateToPrice(y),
    };
  }, [chartRef, seriesRef]);

  // ---- disegno ----
  const drawGeom = useCallback((g, c, k, opts = {}) => {
    const { prims, handles } = buildScene(g, c);
    const color = g.style?.color || "#2962ff";
    const halo = dark_.current ? "#0b0f19" : "#ffffff";
    prims.forEach((p) => {
      k.save();
      k.strokeStyle = color; k.fillStyle = color;
      k.lineWidth = (g.style?.width || 2) + (opts.selected ? 1 : 0);
      k.setLineDash(p.dashed ? [4, 4] : (DASH[g.style?.dash] || []));
      if (p.faint) k.globalAlpha = 0.65;
      if (opts.preview) k.globalAlpha = 0.75;
      if (p.kind === "line") { k.beginPath(); k.moveTo(p.x1, p.y1); k.lineTo(p.x2, p.y2); k.stroke(); }
      else if (p.kind === "rect") {
        k.globalAlpha = (opts.preview ? 0.5 : 1) * (g.style?.fill_opacity ?? 0.15);
        k.fillRect(p.x, p.y, p.w, p.h);
        k.globalAlpha = opts.preview ? 0.75 : 1; k.lineWidth = 1; k.setLineDash([]); k.strokeRect(p.x, p.y, p.w, p.h);
      } else if (p.kind === "label" && g.style?.show_labels !== false) {
        k.font = "11px ui-monospace, Menlo, monospace"; k.textAlign = p.align === "right" ? "right" : "left";
        k.lineWidth = 3; k.setLineDash([]); k.strokeStyle = halo; k.strokeText(p.text, p.x, p.y); k.fillText(p.text, p.x, p.y);
      }
      k.restore();
    });
    const cls = g.semantic?.class && g.semantic.class !== "NONE" ? SEMANTIC_CLASSES.find((x) => x.id === g.semantic.class) : null;
    const first = handles[0];
    if (first && (g.name || cls)) {
      k.save(); k.font = "bold 10px ui-monospace, Menlo, monospace"; k.textAlign = "left"; k.lineWidth = 3; k.strokeStyle = halo; k.fillStyle = color;
      const txt = [g.name, cls ? `[${cls.label}]` : ""].filter(Boolean).join(" ");
      k.strokeText(txt, first.x + 6, first.y + 14); k.fillText(txt, first.x + 6, first.y + 14); k.restore();
    }
    if (opts.selected || opts.preview) {
      handles.forEach((h) => {
        k.save(); k.beginPath(); k.arc(h.x, h.y, 5, 0, Math.PI * 2); k.fillStyle = halo; k.fill(); k.lineWidth = 2; k.strokeStyle = color; k.stroke();
        if (g.anchors[h.i]?.ref?.kind === "CANDLE") { k.beginPath(); k.arc(h.x, h.y, 2, 0, Math.PI * 2); k.fillStyle = color; k.fill(); }
        k.restore();
      });
    }
  }, []);

  const draw = useCallback(() => {
    const canvas = canvasRef.current, el = wrapRef.current;
    if (!canvas || !el) return;
    const k = canvas.getContext ? canvas.getContext("2d") : null;
    if (!k) return;
    const dpr = window.devicePixelRatio || 1, W = el.clientWidth, H = el.clientHeight;
    if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) { canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr); }
    k.setTransform(dpr, 0, 0, dpr, 0, 0);
    k.clearRect(0, 0, W, H);
    const c = getCtx();
    if (!c) return;
    k.save(); k.beginPath(); k.rect(0, 0, c.width, c.height); k.clip();
    const proj = [];
    for (const g of visibleRef.current) {
      const ov = overrideRef.current[g.geometry_id];
      const gg = ov ? { ...g, anchors: ov } : g;
      drawGeom(gg, c, k, { selected: g.geometry_id === R.current.selectedId });
      if (proj.length < 60) proj.push({ id: g.geometry_id, type: g.type, pts: gg.anchors.map((a) => { const p = project(a, c); return p ? [Math.round(p.x * 10) / 10, Math.round(p.y * 10) / 10] : null; }) });
    }
    canvas.dataset.dbg = JSON.stringify({ w: c.width, h: c.height, n: c.bars.length, tf: R.current.tf, x0: c.xOf(0), x100: c.xOf(100), y1000: c.yOf(1000), y3000: c.yOf(3000), vr: (() => { try { return chartRef.current.timeScale().getVisibleLogicalRange(); } catch (err) { return null; } })() });
    canvas.dataset.rulers = JSON.stringify(visibleRef.current.filter((g) => g.type === "ruler").map((g) => ({ id: g.geometry_id, text: (buildScene(g, c).prims.find((p) => p.kind === "label") || {}).text })));
    canvas.dataset.proj = JSON.stringify(proj);       // proiezione corrente (diagnostica di sola lettura, usata dalla verifica nel browser)
    const d = draftRef.current;
    if (d) {
      const anchors = d.cursor ? [...d.anchors, d.cursor] : d.anchors;
      const need = ANCHORS_REQUIRED[d.tool];
      if (anchors.length >= need) drawGeom({ type: d.tool, anchors: anchors.slice(0, need), style: { color: DEFAULT_COLOR[d.tool] || "#2962ff", width: 2, dash: "solid", fill_opacity: 0.15, extend: "none" }, fib_levels: d.tool === "fib_retracement" ? [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1] : [0, 0.618, 1, 1.272, 1.618], clock_basis: R.current.meta?.clock_basis || "" }, c, k, { preview: true });
      else if (anchors.length === 1 && c) drawGeom({ type: "text", text: "", anchors, style: { color: "#2962ff" } }, c, k, { preview: true });
    }
    const hv = hoverRef.current;
    if (hv && (R.current.tool !== "select")) {
      k.save(); k.strokeStyle = "#94a3b8"; k.lineWidth = 1; k.setLineDash([2, 3]);
      k.beginPath(); k.moveTo(hv.x, 0); k.lineTo(hv.x, c.height); k.moveTo(0, hv.y); k.lineTo(c.width, hv.y); k.stroke(); k.restore();
      if (hv.anchor) {
        k.save(); k.font = "11px ui-monospace, Menlo, monospace"; k.fillStyle = dark_.current ? "#e2e8f0" : "#0f172a";
        const tag = `${fmtPrice(hv.anchor.price)} · ${fmtTime(hv.anchor.t, R.current.meta?.clock_basis).slice(5, 16)}${hv.anchor.ref?.kind === "CANDLE" ? ` · ${hv.anchor.ref.field.toUpperCase()}` : ""}`;
        k.fillText(tag, Math.min(hv.x + 10, c.width - 170), Math.max(14, hv.y - 8)); k.restore();
      }
    }
    k.restore();
  }, [drawGeom, getCtx]);

  // ricalcolo continuo "a firma": zoom, pan, resize, scala prezzi, cambio timeframe/dataset
  useEffect(() => {
    let raf = 0;
    const loop = () => {
      raf = requestAnimationFrame(loop);
      const chart = chartRef.current, series = seriesRef.current, el = wrapRef.current;
      let sig = "none";
      if (chart && series && el) {
        try {
          const r = chart.timeScale().getVisibleLogicalRange();
          const b = R.current.bars;
          sig = [el.clientWidth, el.clientHeight, r ? r.from.toFixed(3) : "", r ? r.to.toFixed(3) : "", series.priceToCoordinate(1000), series.priceToCoordinate(3000), chart.timeScale().logicalToCoordinate(0), chart.timeScale().logicalToCoordinate(100), b.length, b.length ? b[b.length - 1].time : 0, R.current.tf, epoch].join("|");
        } catch (err) { sig = "err"; }
      }
      if (sig !== sigRef.current || dirtyRef.current) { sigRef.current = sig; dirtyRef.current = false; draw(); }
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [chartRef, seriesRef, draw, epoch]);

  // cambio di contesto (simbolo/timeframe/dataset): la bozza non e' piu' valida; le geometrie salvate restano (stessi (t, prezzo))
  useEffect(() => { draftRef.current = null; dragRef.current = null; overrideRef.current = {}; dirty(); }, [symbol, tf, source]);

  // ---- creazione ----
  const makeBody = useCallback((type, anchors) => {
    const m = R.current.meta || {};
    const body = {
      type, symbol: R.current.symbol, dataset_id: m.dataset_id || R.current.source || "", source: m.feed_kind || R.current.source || "",
      clock_basis: m.clock_basis || "", timeframe_origin: R.current.tf, anchors, name: "",
      style: { color: DEFAULT_COLOR[type] || "#2962ff", layer: R.current.layers.some((l) => l.layer_id === R.current.activeLayer) ? R.current.activeLayer : "default" },
    };
    if (type === "text") body.text = "Nota";
    return body;
  }, []);

  const finalize = useCallback(async (type, anchors) => {
    draftRef.current = null; dirty();
    try {
      const o = await R.current.S.create(makeBody(type, anchors));
      setSelectedId(o.geometry_id); setTool("select"); setNote(null);
    } catch (e) { setNote(errText(e)); }
  }, [makeBody]);

  // ---- interazione (gestori nativi in fase di cattura sul contenitore del grafico) ----
  useEffect(() => {
    const el = wrapRef.current;
    const host = el ? el.parentElement : null;
    if (!host) return undefined;
    const local = (e) => { const r = el.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
    const inUi = (e) => !!(e.target && e.target.closest && e.target.closest("[data-geo-ui]"));
    const hitTest = (c, x, y) => {
      const sel = R.current.selectedId;
      const list = visibleRef.current;
      const ordered = [...list].sort((a, b) => (a.geometry_id === sel ? 1 : 0) - (b.geometry_id === sel ? 1 : 0));
      let best = null, bd = 7;
      for (const g of ordered) {
        const ov = overrideRef.current[g.geometry_id];
        const sc = buildScene(ov ? { ...g, anchors: ov } : g, c);
        if (g.geometry_id === sel) { const h = hitHandle(sc, x, y); if (h) return { g, handle: h.i }; }
        const d = sceneDistance(sc, x, y);
        if (d <= bd) { bd = d; best = { g, handle: null }; }
      }
      return best;
    };
    const stop = (e) => { e.preventDefault(); e.stopPropagation(); };

    const onDown = (e) => {
      if (e.button !== 0 || inUi(e)) return;
      const c = getCtx(); if (!c) return;
      const { x, y } = local(e);
      if (x < 0 || y < 0 || x > c.width || y > c.height) return;
      const t = R.current.tool;
      if (t.startsWith("pick:")) {                              // selezione di un punto per la scheda evento (nessun disegno)
        interceptRef.current = true; stop(e);
        const a = snapAnchor(x, y, c, "ohlc", 60);
        if (a && R.current.onPick) R.current.onPick(t, a, { paneId: R.current.paneId, tf: R.current.tf, bars: R.current.bars, meta: R.current.meta });
        return;
      }
      if (t !== "select") {
        interceptRef.current = true; stop(e);
        const a = snapAnchor(x, y, c, R.current.snapMode);
        if (!a) return;
        const need = ANCHORS_REQUIRED[t];
        let d = draftRef.current;
        if (!d || d.tool !== t) d = draftRef.current = { tool: t, anchors: [], cursor: null, downXY: { x, y }, dragStart: false };
        d.anchors.push(a);
        if (d.anchors.length === 1) { d.downXY = { x, y }; d.dragStart = true; } else d.dragStart = false;
        if (d.anchors.length >= need) finalize(t, d.anchors.slice(0, need)); else dirty();
        try { host.setPointerCapture(e.pointerId); } catch (err) { void err; }
        return;
      }
      const hit = hitTest(c, x, y);
      if (!hit) { setSelectedId(null); return; }               // sul vuoto: il grafico gestisce pan/zoom
      interceptRef.current = true; stop(e);
      setSelectedId(hit.g.geometry_id);
      if (hit.g.style?.locked) { setNote("Oggetto bloccato: sbloccarlo dall'ispettore per modificarlo."); return; }
      const start = unproject(x, y, c);
      dragRef.current = { gid: hit.g.geometry_id, mode: hit.handle != null ? "handle" : "move", i: hit.handle, start, base: hit.g.anchors, moved: false };
      try { host.setPointerCapture(e.pointerId); } catch (err) { void err; }
    };

    const onMove = (e) => {
      const c = getCtx(); if (!c) return;
      const { x, y } = local(e);
      const t = R.current.tool;
      const inside = x >= 0 && y >= 0 && x <= c.width && y <= c.height;
      const dr = dragRef.current;
      if (dr) {
        stop(e);
        const sm = R.current.snapMode;
        if (dr.mode === "handle") {
          const a = snapAnchor(x, y, c, sm);
          if (a) { const arr = dr.base.map((q) => q); arr[dr.i] = a; overrideRef.current[dr.gid] = arr; dr.moved = true; dirty(); }
        } else {
          const cur = unproject(x, y, c);
          if (cur && dr.start) { overrideRef.current[dr.gid] = translateAnchors(dr.base, cur.t - dr.start.t, cur.price - dr.start.price); dr.moved = true; dirty(); }
        }
        return;
      }
      if (t !== "select" && inside) {
        const a = snapAnchor(x, y, c, t.startsWith("pick:") ? "ohlc" : R.current.snapMode, t.startsWith("pick:") ? 60 : 16);
        hoverRef.current = { x, y, anchor: a };
        const d = draftRef.current;
        if (d && d.tool === t) d.cursor = a;
        host.style.cursor = "crosshair"; dirty(); return;
      }
      hoverRef.current = null;
      if (t === "select" && inside) { const hit = hitTest(c, x, y); host.style.cursor = hit ? (hit.handle != null ? "grab" : "move") : ""; }
      else host.style.cursor = "";
      if (draftRef.current) dirty();
    };

    const onUp = (e) => {
      const d = draftRef.current;
      const dr = dragRef.current;
      if (interceptRef.current) { stop(e); suppressClickUntil.current = performance.now() + 60; }
      interceptRef.current = false;
      try { host.releasePointerCapture(e.pointerId); } catch (err) { void err; }
      if (dr) {
        dragRef.current = null;
        const arr = overrideRef.current[dr.gid];
        delete overrideRef.current[dr.gid];
        dirty();
        if (dr.moved && arr) {
          const same = JSON.stringify(arr.map((a) => [a.t, a.price])) === JSON.stringify(dr.base.map((a) => [a.t, a.price]));
          if (!same) R.current.S.update(dr.gid, { anchors: arr }).then(() => setNote(null)).catch((er) => setNote(errText(er)));
        }
        return;
      }
      if (d && d.dragStart && d.anchors.length === 1 && ANCHORS_REQUIRED[d.tool] === 2) {
        const c = getCtx(); if (!c) return;
        const { x, y } = local(e);
        if (Math.hypot(x - d.downXY.x, y - d.downXY.y) > 8) {           // trascinamento: secondo ancoraggio al rilascio
          const a = snapAnchor(x, y, c, R.current.snapMode);
          if (a) finalize(d.tool, [d.anchors[0], a]);
        }
      }
    };
    const eat = (e) => { if (interceptRef.current || performance.now() < suppressClickUntil.current) { e.stopPropagation(); } };
    const onKey = (e) => {
      const tag = (e.target && e.target.tagName) || "";
      if (/INPUT|TEXTAREA|SELECT/.test(tag) || (e.target && e.target.isContentEditable)) return;
      const mod = e.ctrlKey || e.metaKey;
      if (e.key === "Escape") { draftRef.current = null; setTool("select"); dirty(); }
      else if (mod && e.key.toLowerCase() === "z" && !e.shiftKey) { e.preventDefault(); R.current.S.undo().catch((er) => setNote(errText(er))); }
      else if (mod && (e.key.toLowerCase() === "y" || (e.key.toLowerCase() === "z" && e.shiftKey))) { e.preventDefault(); R.current.S.redo().catch((er) => setNote(errText(er))); }
      else if ((e.key === "Delete" || e.key === "Backspace") && R.current.selectedId) {
        const g = R.current.geoms.find((x) => x.geometry_id === R.current.selectedId);
        if (g && g.style?.locked) { setNote("Oggetto bloccato: non eliminabile."); return; }
        e.preventDefault(); R.current.S.archive(R.current.selectedId).then(() => setSelectedId(null)).catch((er) => setNote(errText(er)));
      }
    };
    host.addEventListener("pointerdown", onDown, true);
    host.addEventListener("pointermove", onMove, true);
    host.addEventListener("pointerup", onUp, true);
    host.addEventListener("pointercancel", onUp, true);
    ["mousedown", "mouseup", "touchstart", "click"].forEach((n) => host.addEventListener(n, eat, true));
    if (R.current.chrome) window.addEventListener("keydown", onKey);
    return () => {
      host.removeEventListener("pointerdown", onDown, true); host.removeEventListener("pointermove", onMove, true);
      host.removeEventListener("pointerup", onUp, true); host.removeEventListener("pointercancel", onUp, true);
      ["mousedown", "mouseup", "touchstart", "click"].forEach((n) => host.removeEventListener(n, eat, true));
      window.removeEventListener("keydown", onKey); host.style.cursor = "";
    };
  }, [getCtx, finalize]);

  // ---- helpers pannello ----
  const upd = (patch) => selected && S.update(selected.geometry_id, patch).then(() => setNote(null)).catch((e) => setNote(errText(e)));
  const updStyle = (style) => upd({ style });
  const editAnchor = (i, patch) => {
    if (!selected) return;
    const anchors = selected.anchors.map((a, j) => (j === i ? { ...a, ...patch } : a));
    upd({ anchors });
  };
  const snapAnchorTo = (i, field) => {
    const a = selected.anchors[i];
    const bar = nearestBar(bars, a.t);
    if (bar) editAnchor(i, candleAnchor(bar, field));
  };
  const stepCandle = (i, dir) => {
    const a = selected.anchors[i];
    const idx = bars.findIndex((b) => b.time === (a.ref?.bar_t ?? a.t));
    const nb = bars[idx + dir];
    if (nb && a.ref?.kind === "CANDLE") editAnchor(i, candleAnchor(nb, a.ref.field));
  };
  const download = async () => {
    try {
      const doc = await S.exportSession();
      const blob = new Blob([JSON.stringify(doc, null, 1)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${(S.session?.name || "analisi").replace(/[^A-Za-z0-9_-]+/g, "_")}.nexus-geometry.json`;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    } catch (e) { setNote(errText(e)); }
  };
  const onImportFile = async (ev) => {
    const f = ev.target.files && ev.target.files[0];
    ev.target.value = "";
    if (!f) return;
    try { await S.importSession(JSON.parse(await f.text()), `Importata ${new Date().toISOString().slice(0, 16)}`); setNote("Sessione importata come nuova sessione."); setSelectedId(null); }
    catch (e) { setNote(`Import rifiutato — ${errText(e)}`); }
  };

  const savedTxt = S.status.state === "saving" ? "salvataggio…" : S.status.state === "saved" ? `salvato ${new Date(S.status.at).toISOString().slice(11, 19)}`
    : S.status.state === "unavailable" ? "memoria non disponibile" : S.status.state === "error" ? "errore" : "pronto";

  return (
    <>
      <div ref={wrapRef} className="absolute inset-x-0 top-0 bottom-1 z-10 pointer-events-none" data-testid="geometry-layer">
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" data-testid="geometry-canvas" />
      </div>

      {chrome && <Portal el={shared?.toolbarEl}><div className={`${shared?.toolbarEl ? "flex flex-wrap" : "absolute top-10 left-2 z-30 flex flex-col"} gap-0.5 rounded-md border border-border bg-card/95 p-1 shadow`} data-geo-ui data-testid="geometry-toolbar">
        {TOOLS.map((t) => (
          <button key={t.id} type="button" title={t.label} aria-label={t.label} aria-pressed={tool === t.id} data-testid={`geo-tool-${t.id}`}
            className={`h-7 min-w-7 px-1 rounded text-[11px] font-bold ${tool === t.id ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}
            onClick={(e) => { e.stopPropagation(); draftRef.current = null; setTool(t.id); setNote(null); dirty(); }}>{TOOL_GLYPH[t.id]}</button>
        ))}
        <div className="h-px bg-border my-0.5" />
        <button type="button" className="h-7 rounded text-[11px] hover:bg-muted disabled:opacity-30" title="Annulla (Ctrl+Z)" data-testid="geo-undo" disabled={!S.stackInfo.undo}
          onClick={(e) => { e.stopPropagation(); S.undo().catch((er) => setNote(errText(er))); }}>↶</button>
        <button type="button" className="h-7 rounded text-[11px] hover:bg-muted disabled:opacity-30" title="Ripeti (Ctrl+Y)" data-testid="geo-redo" disabled={!S.stackInfo.redo}
          onClick={(e) => { e.stopPropagation(); S.redo().catch((er) => setNote(errText(er))); }}>↷</button>
        <button type="button" className="h-7 rounded text-[11px] hover:bg-muted" title="Pannello geometrie" data-testid="geo-panel-toggle"
          onClick={(e) => { e.stopPropagation(); setPanelOpen((v) => !v); }}>☷</button>
      </div></Portal>}

      {tool.startsWith("pick:") && (
        <div className="absolute top-2 left-1/2 -translate-x-1/2 z-30 rounded bg-primary text-primary-foreground border border-border px-2 py-0.5 text-[11px] font-mono" data-geo-ui data-testid={`geo-pick-hint-${paneId}`}>
          {shared?.hint || "Clic su una candela"} · Esc annulla
        </div>
      )}
      {tool !== "select" && !tool.startsWith("pick:") && (
        <div className="absolute top-2 left-1/2 -translate-x-1/2 z-30 rounded bg-card/95 border border-border px-2 py-0.5 text-[11px] font-mono" data-geo-ui data-testid="geo-hint">
          {TOOLS.find((t) => t.id === tool)?.label}: {ANCHORS_REQUIRED[tool]} {ANCHORS_REQUIRED[tool] === 1 ? "clic" : "ancoraggi (clic-clic o trascina)"} · Esc annulla · snap: {SNAP_MODES.find((s) => s[0] === snapMode)?.[1]}
        </div>
      )}

      {chrome && panelOpen && (
        <Portal el={shared?.panelEl}><div className={shared?.panelEl ? "w-full rounded-md border border-border bg-card/95 p-2 text-[11px]" : "absolute top-10 right-16 z-30 w-[300px] max-h-[calc(100%-3rem)] overflow-y-auto rounded-md border border-border bg-card/95 p-2 text-[11px] shadow"} data-geo-ui data-testid="geometry-panel"
          onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-between gap-1">
            <b className="tracking-wide">GEOMETRIE · memoria grafica</b>
            <span data-testid="geo-status" className={S.status.state === "error" || S.status.state === "unavailable" ? "text-rose-600" : "text-emerald-600"}>{savedTxt}</span>
          </div>
          <div className="text-[10px] text-muted-foreground">Annotazioni dell'utente: non sono segnali e non generano ordini.</div>
          {(note || S.status.error) && <div className="mt-1 rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-amber-700 dark:text-amber-400" role="status" data-testid="geo-note">{note || S.status.error}</div>}

          <Field label="Sessione di analisi">
            <select className={inputCls} data-testid="geo-session-select" value={S.sessionId || ""} onChange={(e) => { setSelectedId(null); S.loadSession(e.target.value).catch((er) => setNote(errText(er))); }}>
              {S.sessions.map((s) => <option key={s.session_id} value={s.session_id}>{s.name} ({s.object_count})</option>)}
            </select>
          </Field>
          <div className="mt-1 flex gap-1">
            <input className={inputCls} placeholder="nuova sessione…" value={newName} data-testid="geo-new-session-name" onChange={(e) => setNewName(e.target.value)} />
            <button type="button" className={btnCls} data-testid="geo-new-session" disabled={!newName.trim()}
              onClick={() => S.createSession(newName.trim(), symbol).then(() => { setNewName(""); setSelectedId(null); }).catch((er) => setNote(errText(er)))}>+</button>
          </div>
          <div className="mt-1 flex gap-1">
            <button type="button" className={btnCls} data-testid="geo-save" onClick={() => S.reload().then(() => setNote("Analisi salvata e riletta dal server.")).catch((er) => setNote(errText(er)))}>Salva/Rileggi</button>
            <button type="button" className={btnCls} data-testid="geo-export" onClick={download}>Esporta</button>
            <label className={`${btnCls} cursor-pointer`}>Importa<input type="file" accept="application/json,.json" className="hidden" data-testid="geo-import-file" onChange={onImportFile} /></label>
          </div>

          <Field label="Aggancio (snap)">
            <select className={inputCls} data-testid="geo-snap" value={snapMode} onChange={(e) => setSnapMode(e.target.value)}>
              {SNAP_MODES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </Field>

          <div className="mt-2 font-bold">Unità (separate)</div>
          <div className="grid grid-cols-3 gap-1" data-testid="geo-units">
            {[["pip_size", "pip"], ["point", "point"], ["tick_size", "tick"]].map(([k, lbl]) => (
              <label key={k} className="text-[10px] text-muted-foreground">{lbl}
                <input className={inputCls} data-testid={`geo-units-${k}`} inputMode="decimal" defaultValue={units?.[k] ?? ""} placeholder="n/d"
                  onBlur={(e) => { const v = e.target.value.trim() === "" ? null : Number(e.target.value); if (v === null || (Number.isFinite(v) && v > 0)) setUnits({ ...units, [k]: v }); }} />
              </label>
            ))}
          </div>
          <div className="text-[10px] text-muted-foreground">Prezzo, pip, point e tick size non si convertono tra loro. Ricerca XAUUSD: 1 pip = 0,10 di prezzo (modificabile).</div>

          <div className="mt-2 font-bold">Livelli</div>
          {layers.map((l) => (
            <div key={l.layer_id} className="flex items-center gap-1" data-testid={`geo-layer-${l.layer_id}`}>
              <input type="radio" name="geo-active-layer" checked={activeLayer === l.layer_id} onChange={() => setActiveLayer(l.layer_id)} title="livello attivo per i nuovi oggetti" />
              <span className="flex-1 truncate">{l.name}</span>
              <button type="button" className={btnCls} title="visibilita'" data-testid={`geo-layer-vis-${l.layer_id}`} onClick={() => S.setLayer(l.layer_id, { visible: !l.visible }).catch((er) => setNote(errText(er)))}>{l.visible ? "👁" : "—"}</button>
              <button type="button" className={btnCls} title="blocco" data-testid={`geo-layer-lock-${l.layer_id}`} onClick={() => S.setLayer(l.layer_id, { locked: !l.locked }).catch((er) => setNote(errText(er)))}>{l.locked ? "🔒" : "🔓"}</button>
            </div>
          ))}
          <div className="mt-1 flex gap-1">
            <input className={inputCls} placeholder="nuovo livello…" value={newLayerName} data-testid="geo-new-layer-name" onChange={(e) => setNewLayerName(e.target.value)} />
            <button type="button" className={btnCls} data-testid="geo-new-layer" disabled={!newLayerName.trim()}
              onClick={() => S.setLayer(`L${Date.now().toString(36)}`, { name: newLayerName.trim() }).then(() => setNewLayerName("")).catch((er) => setNote(errText(er)))}>+</button>
          </div>

          <div className="mt-2 font-bold">Oggetti ({visibleGeoms.length}/{geoms.filter((g) => g.status === "ACTIVE").length})</div>
          <ul className="max-h-32 overflow-y-auto" data-testid="geo-object-list">
            {geoms.filter((g) => g.status === "ACTIVE").map((g) => (
              <li key={g.geometry_id}>
                <button type="button" data-testid={`geo-item-${g.geometry_id}`} onClick={() => setSelectedId(g.geometry_id)}
                  className={`w-full text-left truncate rounded px-1 py-0.5 ${g.geometry_id === selectedId ? "bg-primary/15" : "hover:bg-muted"} ${sameInstrument(g.symbol, symbol) ? "" : "opacity-50"}`}>
                  <span style={{ color: g.style?.color }}>■</span> {g.name || TOOLS.find((t) => t.id === g.type)?.label}
                  {g.semantic?.class !== "NONE" ? ` · ${SEMANTIC_CLASSES.find((c) => c.id === g.semantic.class)?.label}` : ""}{g.style?.locked ? " 🔒" : ""}{g.style?.visible === false ? " (nascosto)" : ""}
                </button>
              </li>
            ))}
          </ul>

          {selected && (
            <div className="mt-2 border-t border-border pt-1" data-testid="geo-inspector" key={`${selected.geometry_id}:${selected.revision}`}>
              <div className="font-bold">{TOOLS.find((t) => t.id === selected.type)?.label} <span className="font-normal text-muted-foreground">rev {selected.revision}</span></div>
              <Field label="Nome"><input className={inputCls} data-testid="geo-name" defaultValue={selected.name} onBlur={(e) => e.target.value !== selected.name && upd({ name: e.target.value })} onKeyDown={(e) => e.key === "Enter" && e.target.blur()} /></Field>
              {selected.type === "text" && <Field label="Testo"><input className={inputCls} data-testid="geo-text" defaultValue={selected.text} onBlur={(e) => e.target.value.trim() && e.target.value !== selected.text && upd({ text: e.target.value })} /></Field>}
              <Field label="Descrizione"><textarea className={inputCls} rows={2} data-testid="geo-description" defaultValue={selected.description} onBlur={(e) => e.target.value !== selected.description && upd({ description: e.target.value })} /></Field>
              <div className="mt-1.5 flex flex-wrap items-center gap-1">
                {SWATCHES.map((c) => <button key={c} type="button" aria-label={`colore ${c}`} data-testid={`geo-color-${c.slice(1)}`} className="h-4 w-4 rounded-sm border border-border" style={{ background: c, outline: selected.style.color === c ? "2px solid currentColor" : "none" }} onClick={() => updStyle({ color: c })} />)}
              </div>
              <div className="mt-1 grid grid-cols-3 gap-1">
                <select className={inputCls} data-testid="geo-width" value={selected.style.width} onChange={(e) => updStyle({ width: Number(e.target.value) })}>{[1, 2, 3, 4, 6].map((w) => <option key={w} value={w}>{w}px</option>)}</select>
                <select className={inputCls} data-testid="geo-dash" value={selected.style.dash} onChange={(e) => updStyle({ dash: e.target.value })}>{["solid", "dashed", "dotted"].map((w) => <option key={w}>{w}</option>)}</select>
                <select className={inputCls} data-testid="geo-extend" value={selected.style.extend} onChange={(e) => updStyle({ extend: e.target.value })}>{["none", "right", "left", "both"].map((w) => <option key={w} value={w}>{`estendi: ${w}`}</option>)}</select>
              </div>
              <div className="mt-1 grid grid-cols-2 gap-1">
                <select className={inputCls} data-testid="geo-layer-select" value={selected.style.layer} onChange={(e) => updStyle({ layer: e.target.value })}>{layers.map((l) => <option key={l.layer_id} value={l.layer_id}>{l.name}</option>)}</select>
                <select className={inputCls} data-testid="geo-fill" value={selected.style.fill_opacity} onChange={(e) => updStyle({ fill_opacity: Number(e.target.value) })}>{[0, 0.05, 0.15, 0.3, 0.5].map((w) => <option key={w} value={w}>{`riempimento ${w}`}</option>)}</select>
              </div>
              <div className="mt-1 flex gap-3">
                <label><input type="checkbox" data-testid="geo-locked" checked={!!selected.style.locked} onChange={(e) => updStyle({ locked: e.target.checked })} /> bloccato</label>
                <label><input type="checkbox" data-testid="geo-visible" checked={selected.style.visible !== false} onChange={(e) => updStyle({ visible: e.target.checked })} /> visibile</label>
              </div>
              <Field label="Significato attribuito dall'utente (la forma non cambia)">
                <select className={inputCls} data-testid="geo-semantic" value={selected.semantic.class} onChange={(e) => upd({ semantic: { class: e.target.value, ...(selected.semantic.note ? { note: selected.semantic.note } : {}) } })}>
                  {semanticOptionsFor(selected.type).map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
                </select>
              </Field>
              <div className="text-[10px] text-amber-700 dark:text-amber-400">Etichetta dell'utente: non è un segnale operativo.</div>
              <div className="mt-1.5 font-bold">Ancoraggi (clock: {selected.clock_basis || "n/d"})</div>
              {selected.anchors.map((a, i) => (
                <div key={i} className="mt-1 rounded border border-border p-1" data-testid={`geo-anchor-${i}`}>
                  <div className="flex gap-1">
                    <input className={inputCls} data-testid={`geo-anchor-time-${i}`} defaultValue={fmtTime(a.t, selected.clock_basis).slice(0, 19)} title="YYYY-MM-DD HH:MM:SS"
                      onBlur={(e) => { const t = parseTime(e.target.value); if (t != null && t !== a.t) editAnchor(i, { t, ref: { kind: "FREE", projection_id: null } }); }} />
                    <input className={inputCls} data-testid={`geo-anchor-price-${i}`} defaultValue={fmtPrice(a.price)} inputMode="decimal"
                      onBlur={(e) => { const p = Number(e.target.value); if (Number.isFinite(p) && p !== a.price) editAnchor(i, { price: p, ref: { kind: "FREE", projection_id: null } }); }} />
                  </div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-1 text-[10px] text-muted-foreground">
                    <span data-testid={`geo-anchor-ref-${i}`}>{a.ref?.kind === "CANDLE" ? `candela ${a.ref.field.toUpperCase()} @ ${fmtTime(a.ref.bar_t, selected.clock_basis).slice(5, 16)}` : "libero"}</span>
                    {OHLC.map((f) => <button key={f} type="button" className={btnCls} data-testid={`geo-snap-${i}-${f}`} title={`aggancia a ${f} della candela piu' vicina`} onClick={() => snapAnchorTo(i, f)}>{f[0].toUpperCase()}</button>)}
                    {a.ref?.kind === "CANDLE" && <>
                      <button type="button" className={btnCls} onClick={() => stepCandle(i, -1)} title="candela precedente">◀</button>
                      <button type="button" className={btnCls} onClick={() => stepCandle(i, 1)} title="candela successiva">▶</button>
                      <button type="button" className={btnCls} onClick={() => editAnchor(i, { ref: { kind: "FREE", projection_id: null } })}>libera</button>
                    </>}
                  </div>
                </div>
              ))}
              <div className="mt-1 text-[10px] text-muted-foreground break-all" data-testid="geo-meta">
                id {selected.geometry_id} · {selected.origin} · autore {selected.author}<br />
                dataset {selected.dataset_id || "n/d"} · fonte {selected.source || "n/d"} · {selected.symbol} {selected.timeframe_origin}<br />
                creata {fmtTime(Math.round(selected.created_at), "UTC")} · disponibile {fmtTime(Math.round(selected.available_at), "UTC")} · stato {selected.status}
              </div>
              <button type="button" className={`${btnCls} mt-1 w-full text-rose-600`} data-testid="geo-delete" disabled={!!selected.style.locked}
                onClick={() => S.archive(selected.geometry_id).then(() => setSelectedId(null)).catch((er) => setNote(errText(er)))}>Elimina (annullabile)</button>
            </div>
          )}
        </div></Portal>
      )}
    </>
  );
}
