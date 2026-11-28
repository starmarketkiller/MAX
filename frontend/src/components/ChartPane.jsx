// CHART-MULTISCALE-DISCOVERY-01 — un grafico del multigrafico. Stessa API dati e stessa guardia di partizione della Chart reale:
// nessun dato sintetico, nessun accesso fuori dalle finestre autorizzate. Espone un'API imperativa al workspace (registry).
import { useCallback, useEffect, useRef, useState } from "react";
import { createChart, CandlestickSeries } from "lightweight-charts";
import api from "@/lib/api";
import GeometryLayer from "@/components/GeometryLayer";
import { TF_SECONDS } from "@/lib/geometry/geometryMath";

const FIRST_VIEW_BARS = 160;
const INITIAL = 1500;
const PAGE = 1000;
const LIGHT = { layout: { background: { type: "solid", color: "#ffffff" }, textColor: "#1e293b" }, grid: { vertLines: { color: "#f1f5f9" }, horzLines: { color: "#f1f5f9" } }, rightPriceScale: { borderColor: "#cbd5e1" } };
const DARK = { layout: { background: { type: "solid", color: "#0b0f17" }, textColor: "#94a3b8" }, grid: { vertLines: { color: "rgba(148,163,184,.08)" }, horzLines: { color: "rgba(148,163,184,.08)" } }, rightPriceScale: { borderColor: "#273244" } };
const CANDLE = { upColor: "#16a34a", downColor: "#dc2626", borderUpColor: "#15803d", borderDownColor: "#b91c1c", wickUpColor: "#16a34a", wickDownColor: "#dc2626" };
const hhmm = (time) => { const d = new Date(time * 1000); return `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`; };
const fmtT = (t) => new Date(t * 1000).toISOString().replace("T", " ").slice(0, 16);

function toSeriesBar(b) {            // PARTIAL/GAP/OPEN non sono disegnate come barre complete (come nella Chart reale)
  const base = { time: b.time, open: b.open, high: b.high, low: b.low, close: b.close };
  if (b.completeness === "PARTIAL") return { ...base, color: "rgba(100,116,139,0.5)", wickColor: "#64748b", borderColor: "#64748b" };
  if (b.completeness === "GAP") return { ...base, color: "rgba(245,158,11,0.3)", wickColor: "#f59e0b", borderColor: "#f59e0b" };
  return base;
}
const isCancel = (e) => e?.code === "ERR_CANCELED" || e?.name === "CanceledError" || e?.name === "AbortError";

export default function ChartPane({ paneId, index, source, symbol, tf, tfs, onTf, symbols, onSymbol, symbolLocked, linked, onLinked, dark, registry, onRange, onCrosshair, onLoaded, shared, onPick }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);
  const barsRef = useRef([]);
  const metaRef = useRef(null);
  const genRef = useRef(0);
  const ctrlRef = useRef(null);
  const nextBeforeRef = useRef(null);
  const hasMoreRef = useRef(false);
  const pendingRef = useRef({ kind: "tail" });
  const ignoreRange = useRef(0);
  const ignoreXh = useRef(0);
  const pagingRef = useRef(false);
  const pageRef = useRef(null);
  const ctxKeyRef = useRef("");
  const anchorRef = useRef(null);          // finestra ancorata: ultimo istante (esclusivo) del dato caricato; null = coda del dataset
  const cbs = useRef({});
  cbs.current = { onRange, onCrosshair, onLoaded };
  const [bars, setBars] = useState([]);
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [epoch, setEpoch] = useState(0);
  const [anchorEnd, setAnchorEnd] = useState(null);
  anchorRef.current = anchorEnd;

  // ---- grafico (ricreato solo al cambio tema)
  useEffect(() => {
    if (!containerRef.current) return undefined;
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth, height: containerRef.current.clientHeight, ...(dark ? DARK : LIGHT),
      timeScale: { borderColor: dark ? "#273244" : "#cbd5e1", timeVisible: true, secondsVisible: false, tickMarkFormatter: hhmm },
      crosshair: { mode: 1 }, localization: { locale: "en-US", timeFormatter: fmtT },
    });
    const series = chart.addSeries(CandlestickSeries, CANDLE);
    chartRef.current = chart; seriesRef.current = series;
    setEpoch((e) => e + 1);
    const onResize = () => { if (containerRef.current) chart.resize(containerRef.current.clientWidth, containerRef.current.clientHeight); };
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(onResize) : null;
    if (ro) ro.observe(containerRef.current);
    const onVisible = (r) => {
      if (r && containerRef.current) containerRef.current.parentElement.dataset.range = JSON.stringify(r);     // diagnostica di sola lettura
      if (r && Date.now() >= ignoreRange.current && !pagingRef.current) cbs.current.onRange?.(paneId, r);
    };
    chart.timeScale().subscribeVisibleTimeRangeChange(onVisible);
    const onXh = (p) => {
      if (Date.now() < ignoreXh.current) return;
      if (containerRef.current) containerRef.current.parentElement.dataset.xh = typeof p?.time === "number" ? JSON.stringify({ t: p.time, from: "local" }) : "";
      cbs.current.onCrosshair?.(paneId, typeof p?.time === "number" ? p.time : null);
    };
    chart.subscribeCrosshairMove(onXh);
    const onLogical = (r) => {                                  // paginazione all'indietro quando si scorre verso il bordo sinistro
      if (!r || r.from > 15 || !hasMoreRef.current || pagingRef.current || !nextBeforeRef.current) return;
      pageRef.current().catch(() => {});
    };
    chart.timeScale().subscribeVisibleLogicalRangeChange(onLogical);
    return () => { if (ro) ro.disconnect(); try { chart.remove(); } catch (err) { void err; } chartRef.current = null; seriesRef.current = null; };
  }, [dark]);   // eslint-disable-line react-hooks/exhaustive-deps

  const apply = useCallback((o, { prepend }) => {
    const incoming = o.bars || [];
    const merged = prepend ? [...incoming, ...barsRef.current] : incoming;
    barsRef.current = merged;
    metaRef.current = o;
    nextBeforeRef.current = o.next_before;
    hasMoreRef.current = !!o.has_more;
    setBars(merged); setMeta(o);
    return incoming.length;
  }, []);

  async function fetchPage(before, initial = false) {
    const q = `/chart/ohlc?source=${encodeURIComponent(source)}&symbol=${encodeURIComponent(symbol)}&tf=${tf}&limit=${before && !initial ? PAGE : INITIAL}${before ? `&before=${before}` : ""}`;
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    const { data } = await api.get(q, { signal: ctrl.signal });
    return data;
  }
  async function page() {
    if (pagingRef.current || !hasMoreRef.current) return 0;
    pagingRef.current = true;
    const gen = genRef.current;
    try {
      const data = await fetchPage(nextBeforeRef.current);
      if (gen !== genRef.current || (data.status !== "AVAILABLE_OFFLINE" && data.status !== "AVAILABLE_LIVE")) return 0;
      const ts = chartRef.current?.timeScale();
      const r = ts?.getVisibleLogicalRange();
      const added = apply(data, { prepend: true });
      pendingRef.current = { kind: "shift", added, range: r };
      return added;
    } finally { pagingRef.current = false; }
  }

  pageRef.current = page;

  // ---- caricamento al cambio di contesto (fonte, simbolo, timeframe)
  useEffect(() => {
    if (!source || !symbol || !tf) return undefined;
    const key = source + "|" + symbol;
    if (ctxKeyRef.current !== key) {                   // un altro dataset/simbolo ha un'altra copertura: si riparte dalla coda, senza richieste con l'ancora vecchia
      const had = ctxKeyRef.current !== "" && anchorRef.current != null;
      ctxKeyRef.current = key;
      if (had) { anchorRef.current = null; setAnchorEnd(null); return undefined; }
    }
    const gen = ++genRef.current;
    if (ctrlRef.current) { try { ctrlRef.current.abort(); } catch (err) { void err; } }
    barsRef.current = []; setBars([]); setMeta(null); setError(null); setLoading(true);
    const t0 = performance.now();
    (async () => {
      try {
        const data = await fetchPage(anchorRef.current, true);
        if (gen !== genRef.current) return;
        if (data.status !== "AVAILABLE_OFFLINE" && data.status !== "AVAILABLE_LIVE") {
          setError(`Dato non disponibile: ${data.reason || data.status}. Nessun dato sintetico viene mostrato.`);
          return;
        }
        if (data.timeframe && data.timeframe !== tf) { setError("Risposta non coerente con la richiesta: scartata."); return; }
        if (!pendingRef.current || pendingRef.current.kind === "shift") pendingRef.current = { kind: "tail" };
        apply(data, { prepend: false });
        cbs.current.onLoaded?.(paneId, { tf, n: (data.bars || []).length, ms: Math.round(performance.now() - t0), source, symbol });
      } catch (e) {
        if (isCancel(e) || gen !== genRef.current) return;
        const st = e?.response?.status;
        setError(st === 403 ? "Dati non autorizzati per il Chart (partizione). Nessun dato mostrato." : st === 401 ? "Sessione scaduta." : "Errore di rete o dato non disponibile.");
      } finally { if (gen === genRef.current) setLoading(false); }
    })();
    return undefined;
  }, [source, symbol, tf, anchorEnd]);   // eslint-disable-line react-hooks/exhaustive-deps

  const setRange = useCallback((r) => {
    const chart = chartRef.current, b = barsRef.current;
    if (!chart || !b.length || !r) return false;
    const step = TF_SECONDS[tf] || 900;
    const from = Math.max(r.from, b[0].time), to = Math.min(r.to, b[b.length - 1].time + step);
    ignoreRange.current = Date.now() + 300;
    try {
      if (from >= to) chart.timeScale().fitContent();
      else chart.timeScale().setVisibleRange({ from, to });
      return true;
    } catch (err) { void err; return false; }
  }, [tf]);

  // ---- dati nella serie + posizionamento della vista
  useEffect(() => {
    const series = seriesRef.current, chart = chartRef.current;
    if (!series || !chart) return;
    series.setData(bars.map(toSeriesBar));
    const host = containerRef.current && containerRef.current.parentElement;
    if (host) { host.dataset.first = bars.length ? String(bars[0].time) : ""; host.dataset.last = bars.length ? String(bars[bars.length - 1].time) : ""; host.dataset.n = String(bars.length); }     // diagnostica di sola lettura
    if (!bars.length) return;
    const p = pendingRef.current;
    ignoreRange.current = Date.now() + 400;
    if (p.kind === "shift" && p.range) {
      chart.timeScale().setVisibleLogicalRange({ from: p.range.from + p.added, to: p.range.to + p.added });
    } else if (p.kind === "range") {
      if (!setRange(p.range)) chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, bars.length - FIRST_VIEW_BARS), to: bars.length + 5 });
    } else {
      chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, bars.length - FIRST_VIEW_BARS), to: bars.length + 5 });
    }
    pendingRef.current = { kind: "keep" };
  }, [bars, epoch, setRange]);

  // ---- API imperativa per il workspace
  useEffect(() => {
    const step = () => TF_SECONDS[tf] || 900;
    const api_ = {
      paneId, tf,
      getBars: () => barsRef.current,
      getMeta: () => metaRef.current,
      getRange: () => { try { return chartRef.current?.timeScale().getVisibleRange() || null; } catch (err) { return null; } },
      setRange: (r) => setRange(r),
      // porta la vista su [from, to]; se il dato non e' ancora caricato fin li' pagina all'indietro (guardia di partizione permettendo)
      // Periodi lunghi: poche pagine all'indietro dalla coda; se la destinazione e' piu' lontana (o oltre la fine di una finestra ancorata) si CARICA UNA FINESTRA
      // contigua che termina poco dopo la destinazione (parametro `before` gia' supportato dall'API): niente caricamento dell'intero storico nel browser.
      focusRange: async (r) => {
        const reanchor = () => {
          const end = Math.round(r.to + (r.to - r.from) * 0.3);
          pendingRef.current = { kind: "range", range: r };
          anchorRef.current = end;
          setAnchorEnd(end);
          return true;
        };
        const lastT = () => barsRef.current[barsRef.current.length - 1].time + step();
        if (barsRef.current.length && anchorRef.current != null && r.to > lastT()) return reanchor();
        let paged = 0;
        for (let i = 0; i < 4 && barsRef.current.length && barsRef.current[0].time > r.from && hasMoreRef.current; i += 1) { if ((await pageRef.current()) === 0) break; paged += 1; }
        if (barsRef.current.length && barsRef.current[0].time > r.from && hasMoreRef.current) return reanchor();
        if (!barsRef.current.length) { pendingRef.current = { kind: "range", range: r }; return true; }
        if (paged) {                                      // le barre prepese sono nello stato React ma non ancora nella serie: l'intervallo va applicato DOPO il setData (effetto sui dati), poi confermato
          pendingRef.current = { kind: "range", range: r };
          await new Promise((res) => setTimeout(res, 160));
          pendingRef.current = { kind: "keep" };
          return setRange(r);
        }
        pendingRef.current = { kind: "keep" };
        return setRange(r);
      },
      toTail: () => { pendingRef.current = { kind: "tail" }; anchorRef.current = null; setAnchorEnd(null); },
      anchored: () => anchorRef.current,
      setPending: (r) => { pendingRef.current = r ? { kind: "range", range: r } : { kind: "tail" }; },
      shiftBy: (sec) => { const cur = api_.getRange(); return cur ? setRange({ from: cur.from + sec, to: cur.to + sec }) : false; },
      setCrosshairTime: (t) => {
        const chart = chartRef.current, series = seriesRef.current, b = barsRef.current;
        if (!chart || !series || !b.length) return;
        ignoreXh.current = Date.now() + 90;
        const host = containerRef.current && containerRef.current.parentElement;
        try {
          if (t == null || t < b[0].time || t > b[b.length - 1].time + step()) { chart.clearCrosshairPosition(); if (host) host.dataset.xh = ""; return; }
          let lo = 0, hi = b.length - 1;
          while (lo < hi) { const m = (lo + hi + 1) >> 1; if (b[m].time <= t) lo = m; else hi = m - 1; }
          chart.setCrosshairPosition(b[lo].close, b[lo].time, series);
          if (host) host.dataset.xh = JSON.stringify({ t: b[lo].time, close: b[lo].close, from: "sync" });      // diagnostica di sola lettura: barra su cui e' stato proiettato il crosshair
        } catch (err) { void err; }
      },
      chartRef, seriesRef,
    };
    if (registry) registry.current[paneId] = api_;
    return () => { if (registry && registry.current[paneId] === api_) delete registry.current[paneId]; };
  }, [paneId, tf, registry, setRange]);   // eslint-disable-line react-hooks/exhaustive-deps

  const n = bars.length;
  return (
    <div className="flex flex-col min-w-0 min-h-0 border border-border rounded-md overflow-hidden bg-card" data-testid={`pane-${index}`}>
      <div className="shrink-0 flex flex-wrap items-center gap-1.5 px-2 py-1 border-b border-border text-[11px]">
        <b className="font-mono">{index + 1}</b>
        <select className="rounded border border-border bg-background px-1 py-0.5 font-mono" value={tf} data-testid={`pane-tf-${index}`} onChange={(e) => onTf(index, e.target.value)}>
          {["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"].map((t) => <option key={t} value={t} disabled={!tfs.includes(t)}>{t}{tfs.includes(t) ? "" : " (n/d)"}</option>)}
        </select>
        {!symbolLocked && (
          <select className="rounded border border-border bg-background px-1 py-0.5 font-mono" value={symbol} data-testid={`pane-symbol-${index}`} onChange={(e) => onSymbol(index, e.target.value)}>
            {symbols.map((s) => <option key={s}>{s}</option>)}
          </select>
        )}
        <label className="flex items-center gap-1"><input type="checkbox" checked={linked} data-testid={`pane-linked-${index}`} onChange={(e) => onLinked(index, e.target.checked)} />sync</label>
        <span className="text-muted-foreground font-mono truncate" data-testid={`pane-strip-${index}`}>
          {meta ? `${symbol} ${tf} · ${n} barre · ${meta.dataset_id || source}${meta.has_more ? " · più storico" : " · inizio dataset"}${anchorEnd != null ? ` · finestra fino a ${fmtT(anchorEnd)}` : ""}` : loading ? "caricamento…" : "—"}
        </span>
        {anchorEnd != null && <button type="button" className="rounded border border-border bg-card px-1.5 py-0.5 hover:bg-muted" data-testid={`pane-tail-${index}`} title="torna ai dati più recenti" onClick={() => registry.current[paneId]?.toTail()}>↦ coda</button>}
      </div>
      <div className="relative flex-1 min-h-0">
        <div ref={containerRef} className="absolute inset-0" data-testid={`pane-canvas-${index}`} />
        <GeometryLayer chartRef={chartRef} seriesRef={seriesRef} bars={bars} meta={meta} symbol={symbol} tf={tf} source={source} epoch={epoch} dark={dark}
          shared={shared} chrome={index === 0} onPick={onPick} paneId={paneId} />
        {error && <div className="absolute inset-0 z-20 flex items-center justify-center p-4 text-center text-xs font-mono text-muted-foreground bg-card/85" role="alert" data-testid={`pane-error-${index}`}>{error}</div>}
      </div>
    </div>
  );
}
