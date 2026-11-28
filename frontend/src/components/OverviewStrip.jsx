// CHART-HISTORICAL-EXPANSION-01 — vista generale dello storico (H4) con navigazione diretta agli eventi salvati.
// Carica SOLO barre aggregate (una richiesta da <= 5000 barre, poche pagine al massimo): nessun tick, nessun caricamento dell'intero archivio.
import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { timeToIndex } from "@/lib/geometry/geometryMath";

const LIMIT = 5000;
const MAX_PAGES = 3;
const PREFERRED = ["H4", "D1", "H1"];
const fmtDay = (t) => new Date(t * 1000).toISOString().slice(0, 10);

export default function OverviewStrip({ source, symbol, tfs, marks, viewRange, onGoto, onSelectEvent, dark }) {
  const wrapRef = useRef(null);
  const canvasRef = useRef(null);
  const [data, setData] = useState({ bars: [], tf: null, hasMore: false, loading: true, error: null, ms: null });
  const [width, setWidth] = useState(0);
  const tf = PREFERRED.find((t) => (tfs || []).includes(t)) || null;

  useEffect(() => {
    if (!source || !symbol || !tf) return undefined;
    let off = false;
    setData({ bars: [], tf, hasMore: false, loading: true, error: null, ms: null });
    (async () => {
      const t0 = performance.now();
      try {
        let bars = [], before = null, more = false;
        for (let p = 0; p < MAX_PAGES; p += 1) {
          const { data: d } = await api.get(`/chart/ohlc?source=${encodeURIComponent(source)}&symbol=${encodeURIComponent(symbol)}&tf=${tf}&limit=${LIMIT}${before ? `&before=${before}` : ""}`);
          if (d.status !== "AVAILABLE_OFFLINE" && d.status !== "AVAILABLE_LIVE") throw new Error(d.reason || d.status);
          bars = [...(d.bars || []), ...bars];
          more = !!d.has_more; before = d.next_before;
          if (!more) break;
        }
        if (!off) setData({ bars, tf, hasMore: more, loading: false, error: null, ms: Math.round(performance.now() - t0) });
      } catch (e) {
        if (!off) setData({ bars: [], tf, hasMore: false, loading: false, error: e?.response?.status === 403 ? "Dati non autorizzati (partizione)" : "Dati non disponibili", ms: null });
      }
    })();
    return () => { off = true; };
  }, [source, symbol, tf]);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return undefined;
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => setWidth(el.clientWidth)) : null;
    setWidth(el.clientWidth);
    if (ro) ro.observe(el);
    return () => { if (ro) ro.disconnect(); };
  }, []);

  const H = 64;
  const geom = (() => {
    const b = data.bars;
    if (!b.length || !width) return null;
    let lo = Infinity, hi = -Infinity;
    for (const x of b) { if (x.low < lo) lo = x.low; if (x.high > hi) hi = x.high; }
    const xOf = (i) => (b.length > 1 ? (i / (b.length - 1)) * (width - 2) + 1 : width / 2);
    const yOf = (p) => H - 14 - ((p - lo) / (hi - lo || 1)) * (H - 22);
    const step = data.tf === "D1" ? 86400 : data.tf === "H1" ? 3600 : 14400;
    const idxOfT = (t) => Math.max(0, Math.min(b.length - 1, timeToIndex(b, t, step) ?? 0));
    return { b, lo, hi, xOf, yOf, idxOfT };
  })();

  useEffect(() => {
    const c = canvasRef.current;
    if (!c || !geom) return;
    const dpr = window.devicePixelRatio || 1;
    c.width = Math.round(width * dpr); c.height = Math.round(H * dpr);
    const k = c.getContext("2d");
    if (!k) return;
    k.setTransform(dpr, 0, 0, dpr, 0, 0);
    k.clearRect(0, 0, width, H);
    const { b, xOf, yOf, idxOfT } = geom;
    const band = viewRange ? [xOf(idxOfT(viewRange.from)), xOf(idxOfT(viewRange.to))] : null;
    if (band) { k.fillStyle = dark ? "rgba(96,165,250,0.18)" : "rgba(37,99,235,0.15)"; k.fillRect(band[0], 0, Math.max(2, band[1] - band[0]), H - 12); }
    k.beginPath();
    b.forEach((x, i) => { const px = xOf(i), py = yOf(x.close); if (i === 0) k.moveTo(px, py); else k.lineTo(px, py); });
    k.lineWidth = 1; k.strokeStyle = dark ? "#94a3b8" : "#475569"; k.stroke();
    k.font = "9px ui-monospace, Menlo, monospace"; k.fillStyle = dark ? "#94a3b8" : "#475569"; k.textAlign = "left";
    let lastM = "", n = 0;
    b.forEach((x, i) => {
      const m = new Date(x.time * 1000).toISOString().slice(0, 7);
      if (m !== lastM) { lastM = m; if (n++ % 2 === 0) { k.fillRect(xOf(i), H - 12, 1, 4); k.fillText(m.slice(2), xOf(i) + 2, H - 2); } }
    });
    const mk = [];
    for (const m of marks || []) {
      const i = idxOfT(m.t), px = xOf(i);
      mk.push({ id: m.id, x: Math.round(px * 10) / 10 });
      const col = m.selected ? "#f59e0b" : "#a855f7";
      const up = m.kind === "LOW", py = yOf(m.price);
      k.beginPath(); k.moveTo(px, py + (up ? 3 : -3)); k.lineTo(px - 5, py + (up ? 12 : -12)); k.lineTo(px + 5, py + (up ? 12 : -12)); k.closePath();
      k.strokeStyle = col; k.fillStyle = col; k.lineWidth = 2;
      if (m.outcome === "NO_REVERSAL") k.stroke(); else k.fill();
    }
    c.dataset.overview = JSON.stringify({ n: b.length, tf: data.tf, first: b[0].time, last: b[b.length - 1].time, width, markers: mk, band: band ? band.map((v) => Math.round(v * 10) / 10) : null, hasMore: data.hasMore, ms: data.ms });
  }, [geom, marks, viewRange, width, dark, data.tf, data.hasMore, data.ms]);

  const onClick = (e) => {
    if (!geom) return;
    const r = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - r.left;
    const near = (marks || []).map((m) => ({ m, d: Math.abs(geom.xOf(geom.idxOfT(m.t)) - x) })).filter((o) => o.d <= 8).sort((a, b) => a.d - b.d)[0];
    if (near) { onSelectEvent(near.m.id); return; }
    const i = Math.max(0, Math.min(geom.b.length - 1, Math.round((x / (width - 2)) * (geom.b.length - 1))));
    onGoto(geom.b[i].time);
  };

  const b = data.bars;
  return (
    <div ref={wrapRef} className="shrink-0 border-b border-border pt-1 pb-0.5" data-testid="overview-strip">
      <div className="flex items-center gap-2 px-1.5 text-[10px] text-muted-foreground font-mono leading-4">
        <b className="text-foreground">Vista generale {data.tf || "—"}</b>
        <span data-testid="overview-info">{data.loading ? "caricamento…" : data.error ? data.error : `${b.length} barre · ${fmtDay(b[0].time)} → ${fmtDay(b[b.length - 1].time)}${data.hasMore ? " · oltre il limite caricato" : ""} · ${data.ms} ms`}</span>
        <span className="ml-auto">clic = vai a quella data · triangolo = scheda evento</span>
      </div>
      <canvas ref={canvasRef} style={{ width: "100%", height: H, display: "block", cursor: "pointer" }} onClick={onClick} data-testid="overview-canvas" />
    </div>
  );
}
