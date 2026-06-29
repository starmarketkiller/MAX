import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { createChart, CandlestickSeries, LineSeries } from "lightweight-charts";
import {
  ChevronDown, Activity, X, Sparkles, TrendingUp, TrendingDown,
  Eye, EyeOff, RefreshCw, Layers,
} from "lucide-react";
import api from "@/lib/api";
import CoachLiveWidget from "@/components/CoachLiveWidget";

const TF_OPTIONS = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"];
const SYM_OPTIONS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "US30", "NAS100"];

const LAYER_DEFAULTS = {
  trades: true,
  shadows: false,
  visuals: true,    // OB/FVG/SNR
  open: true,
};

// --------- Theme tokens for the chart -----------
const CHART_LIGHT = {
  layout: { background: { type: "solid", color: "#ffffff" }, textColor: "#1e293b" },
  grid: { vertLines: { color: "#f1f5f9" }, horzLines: { color: "#f1f5f9" } },
  rightPriceScale: { borderColor: "#cbd5e1" },
  timeScale: {
    borderColor: "#cbd5e1",
    timeVisible: true,
    secondsVisible: false,
    // Override the locale-driven formatter to avoid Intl errors on minimal containers (en-US@posix).
    tickMarkFormatter: (time) => {
      const d = new Date(time * 1000);
      const hh = String(d.getUTCHours()).padStart(2, "0");
      const mm = String(d.getUTCMinutes()).padStart(2, "0");
      return `${hh}:${mm}`;
    },
  },
  crosshair: { mode: 1 },
  localization: {
    locale: "en-US",
    timeFormatter: (time) => {
      const d = new Date(time * 1000);
      return d.toISOString().replace("T", " ").slice(5, 16) + " UTC";
    },
  },
};
const CANDLE_STYLE = {
  upColor:        "#16a34a",
  downColor:      "#dc2626",
  borderUpColor:  "#15803d",
  borderDownColor:"#b91c1c",
  wickUpColor:    "#16a34a",
  wickDownColor:  "#dc2626",
};

function classifyVisual(v) {
  const t = (v.type || "").toUpperCase();
  if (t.includes("OB_BULL"))  return { color: "rgba(22, 163, 74, 0.18)", border: "#16a34a", label: "OB+" };
  if (t.includes("OB_BEAR"))  return { color: "rgba(220, 38, 38, 0.18)", border: "#dc2626", label: "OB-" };
  if (t.includes("FVG_BULL")) return { color: "rgba(34, 197, 94, 0.14)", border: "#22c55e", label: "FVG+" };
  if (t.includes("FVG_BEAR")) return { color: "rgba(239, 68, 68, 0.14)", border: "#ef4444", label: "FVG-" };
  if (t.includes("IFVG"))     return { color: "rgba(99, 102, 241, 0.16)", border: "#6366f1", label: "iFVG" };
  if (t.includes("SNR") || t.includes("SUPPLY") || t.includes("DEMAND"))
    return { color: "rgba(245, 158, 11, 0.16)", border: "#f59e0b", label: "S/R" };
  return { color: "rgba(100, 116, 139, 0.14)", border: "#64748b", label: t || "obj" };
}

function ContextPopover({ data, onClose }) {
  if (!data) return null;
  return (
    <div
      className="absolute z-50 bg-white shadow-2xl rounded-xl border border-slate-200 p-4 max-w-xs"
      style={{ left: data.x, top: data.y, transform: "translate(-50%, -110%)" }}
      onClick={(e) => e.stopPropagation()}
      data-testid="chart-context-popover"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500 font-bold">
            {data.kind}
          </div>
          <div className="text-sm font-bold text-slate-800 mt-0.5">{data.title}</div>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="space-y-1.5 text-xs">
        {data.rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between gap-3">
            <span className="text-slate-500">{r.label}</span>
            <span className={`font-mono font-semibold ${r.tone === "pos" ? "text-emerald-600" : r.tone === "neg" ? "text-rose-600" : "text-slate-800"}`}>
              {r.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TopBar({ symbol, setSymbol, tf, setTf, layers, setLayers, refreshing, onRefresh, lastPrice, ohlcSource }) {
  const [openLayers, setOpenLayers] = useState(false);
  return (
    <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-200 bg-white sticky top-0 z-30">
      {/* Symbol */}
      <select
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        className="h-9 px-2.5 rounded-lg border border-slate-300 bg-white text-sm font-mono font-bold tracking-tight focus:outline-none focus:ring-2 focus:ring-cyan-400"
        data-testid="chart-symbol-select"
      >
        {SYM_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
      </select>

      {/* Timeframe pills */}
      <div className="flex gap-0.5 bg-slate-100 rounded-lg p-0.5">
        {TF_OPTIONS.map((t) => (
          <button
            key={t}
            onClick={() => setTf(t)}
            data-testid={`chart-tf-${t}`}
            className={`h-7 px-2 rounded-md text-[11px] font-mono font-bold transition-all ${
              tf === t ? "bg-slate-900 text-white" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Last price */}
      {lastPrice && (
        <div className="hidden sm:flex items-center gap-1 ml-2 px-2.5 py-1 rounded-md bg-slate-100 border border-slate-200">
          <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Last</span>
          <span className="text-sm font-mono font-bold text-slate-800 tabular-nums">{lastPrice.toFixed(2)}</span>
        </div>
      )}

      {ohlcSource === "synthetic" && (
        <span className="hidden md:inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-700 border border-amber-300">
          DEMO
        </span>
      )}

      <div className="flex-1" />

      {/* Layer toggle */}
      <div className="relative">
        <button
          onClick={() => setOpenLayers((v) => !v)}
          data-testid="chart-layers-toggle"
          className="h-9 px-2.5 rounded-lg border border-slate-300 hover:border-cyan-500 hover:bg-cyan-50 inline-flex items-center gap-1 text-xs font-semibold text-slate-700 transition-colors"
        >
          <Layers className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Layers</span>
          <ChevronDown className="h-3 w-3" />
        </button>
        {openLayers && (
          <div className="absolute right-0 top-10 w-48 rounded-xl bg-white border border-slate-200 shadow-xl p-2 z-40" onClick={(e) => e.stopPropagation()}>
            {[
              { k: "trades",  label: "Closed trades", icon: TrendingUp },
              { k: "open",    label: "Open positions", icon: Activity },
              { k: "shadows", label: "Shadow trades", icon: Sparkles },
              { k: "visuals", label: "OB / FVG / SNR", icon: Eye },
            ].map(({ k, label, icon: Icon }) => (
              <button
                key={k}
                onClick={() => setLayers({ ...layers, [k]: !layers[k] })}
                data-testid={`chart-layer-${k}`}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-slate-100 text-xs"
              >
                <Icon className="h-3.5 w-3.5 text-slate-500" />
                <span className="flex-1 text-left">{label}</span>
                {layers[k] ? <Eye className="h-3.5 w-3.5 text-emerald-600" /> : <EyeOff className="h-3.5 w-3.5 text-slate-400" />}
              </button>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={onRefresh}
        disabled={refreshing}
        data-testid="chart-refresh"
        className="h-9 w-9 rounded-lg border border-slate-300 hover:border-cyan-500 hover:bg-cyan-50 flex items-center justify-center text-slate-700 transition-colors active:scale-95"
        title="Refresh"
      >
        <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
      </button>
    </div>
  );
}

export default function LiveChartPage() {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const [symbol, setSymbol] = useState("XAUUSD");
  const [tf, setTf] = useState("M15");
  const [layers, setLayers] = useState(LAYER_DEFAULTS);
  const [refreshing, setRefreshing] = useState(false);
  const [bars, setBars] = useState([]);
  const [ohlcSource, setOhlcSource] = useState("");
  const [markers, setMarkers] = useState({ trades: [], open: [], shadows: [], visuals: [] });
  const [popover, setPopover] = useState(null);
  const [lastPrice, setLastPrice] = useState(null);

  // -------- Chart init --------
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      width:  containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      ...CHART_LIGHT,
    });
    const candleSeries = chart.addSeries(CandlestickSeries, CANDLE_STYLE);
    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    const onResize = () => {
      if (!containerRef.current) return;
      chart.resize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
    };
  }, []);

  // -------- Load data --------
  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const [{ data: o }, { data: m }] = await Promise.all([
        api.get(`/chart/ohlc?symbol=${symbol}&tf=${tf}&limit=300`),
        api.get(`/chart/markers?symbol=${symbol}`),
      ]);
      setBars(o.bars || []);
      setOhlcSource(o.source || "");
      setMarkers({
        trades:  m.trades  || [],
        open:    m.open    || [],
        shadows: m.shadows || [],
        visuals: m.visuals || [],
      });
      if (o.bars?.length) setLastPrice(o.bars[o.bars.length - 1].close);
    } catch (e) {
      console.warn("[LiveChart] load failed", e?.message || e);
    } finally {
      setRefreshing(false);
    }
  }, [symbol, tf]);

  useEffect(() => { load(); }, [load]);

  // Persist current chart context so the Coach widget can pick it up.
  useEffect(() => {
    try {
      localStorage.setItem("nxs_chart_context",
        JSON.stringify({ symbol, tf, ts: Date.now() }));
    } catch (err) { void err; }
  }, [symbol, tf]);

  // Live refresh every 5s
  useEffect(() => {
    const iv = setInterval(load, 5000);
    return () => clearInterval(iv);
  }, [load]);

  // -------- Push bars to chart --------
  useEffect(() => {
    if (!candleSeriesRef.current || !bars.length) return;
    candleSeriesRef.current.setData(bars);
    if (chartRef.current) chartRef.current.timeScale().fitContent();
  }, [bars]);

  // -------- Push markers --------
  const allMarkers = useMemo(() => {
    const arr = [];
    if (layers.trades) {
      markers.trades.forEach((t) => {
        if (!t.closeTime) return;
        const ts = Math.floor(new Date(t.closeTime).getTime() / 1000);
        const won = (t.pnl ?? 0) >= 0;
        arr.push({
          time: ts,
          position: won ? "belowBar" : "aboveBar",
          color: won ? "#16a34a" : "#dc2626",
          shape: won ? "arrowUp" : "arrowDown",
          text: `${t.strategy || "?"} · ${won ? "+" : ""}${(t.pnl || 0).toFixed(0)}`,
          _payload: { kind: "trade", trade: t },
        });
      });
    }
    if (layers.shadows) {
      markers.shadows.forEach((s) => {
        const ts = Math.floor(new Date(s.detected_at).getTime() / 1000);
        arr.push({
          time: ts,
          position: "aboveBar",
          color: "#a855f7",
          shape: "circle",
          text: `Shadow · ${s.strategy || "?"}`,
          _payload: { kind: "shadow", shadow: s },
        });
      });
    }
    return arr.sort((a, b) => a.time - b.time);
  }, [layers.trades, layers.shadows, markers.trades, markers.shadows]);

  useEffect(() => {
    if (!candleSeriesRef.current) return;
    // Use new v5 marker plugin
    import("lightweight-charts").then(({ createSeriesMarkers }) => {
      try {
        candleSeriesRef.current._markerPlugin?.detach?.();
        candleSeriesRef.current._markerPlugin =
          createSeriesMarkers(candleSeriesRef.current,
            allMarkers.map(({ _payload, ...m }) => m));
      } catch (err) {
        console.warn("[LiveChart] marker plugin err", err?.message);
      }
    });
  }, [allMarkers]);

  // -------- Click → context popover --------
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current) return;
    const chart = chartRef.current;
    const handler = (param) => {
      if (!param.point || !param.time) {
        setPopover(null);
        return;
      }
      // Find closest marker within 3 bars
      const t = param.time;
      const candidate = allMarkers
        .map((m) => ({ ...m, dist: Math.abs(m.time - t) }))
        .sort((a, b) => a.dist - b.dist)[0];
      if (!candidate || candidate.dist > 60 * 30 * 3) {
        setPopover(null);
        return;
      }
      const rect = containerRef.current?.getBoundingClientRect();
      const px = param.point.x;
      const py = param.point.y;
      const payload = candidate._payload || {};
      if (payload.kind === "trade") {
        const t2 = payload.trade;
        const won = (t2.pnl ?? 0) >= 0;
        setPopover({
          x: px, y: py,
          kind: "Closed trade",
          title: `${t2.strategy || "?"} · ${t2.side || "?"}`,
          rows: [
            { label: "P&L",     value: `${won ? "+" : ""}$${(t2.pnl || 0).toFixed(2)}`, tone: won ? "pos" : "neg" },
            { label: "Score",   value: t2.score ?? "—" },
            { label: "Lots",    value: (t2.lots ?? 0).toFixed(2) },
            { label: "Reason",  value: t2.reason || "—" },
            { label: "Session", value: t2.session || "—" },
          ],
        });
      } else if (payload.kind === "shadow") {
        const s = payload.shadow;
        setPopover({
          x: px, y: py,
          kind: "Shadow trade",
          title: `${s.strategy || "?"} · ${s.side || "?"}`,
          rows: [
            { label: "Blocker",   value: s.blocker || "—" },
            { label: "Hypoth. R", value: s.would_have_r != null ? s.would_have_r.toFixed(2) : "—",
              tone: (s.would_have_r ?? 0) > 0 ? "pos" : "neg" },
            { label: "Score",     value: s.score ?? "—" },
            { label: "HTF",       value: s.htf_bias || "—" },
          ],
        });
      }
    };
    chart.subscribeClick(handler);
    return () => chart.unsubscribeClick(handler);
  }, [allMarkers]);

  // -------- Render visual zones as price lines (OB/FVG) --------
  const lineSeriesRefs = useRef([]);
  useEffect(() => {
    if (!chartRef.current) return;
    // Remove previous
    lineSeriesRefs.current.forEach((s) => {
      try { chartRef.current.removeSeries(s); }
      catch (err) { /* series may already be detached */ void err; }
    });
    lineSeriesRefs.current = [];
    if (!layers.visuals) return;
    markers.visuals.slice(0, 30).forEach((v) => {
      const cfg = classifyVisual(v);
      const priceCenter = v.price;
      const priceTop    = v.top    != null ? v.top    : priceCenter;
      const priceBot    = v.bottom != null ? v.bottom : priceCenter;
      if (priceCenter == null && priceTop == null) return;
      const isZone = priceTop != null && priceBot != null && priceTop !== priceBot;
      const lines  = isZone ? [priceTop, priceBot] : [priceCenter];
      lines.forEach((px, idx) => {
        if (px == null) return;
        try {
          const s = chartRef.current.addSeries(LineSeries, {
            color: cfg.border,
            lineWidth: 1,
            lineStyle: idx === 0 ? 2 : 3, // top dashed, bottom dotted
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
          });
          if (bars.length) {
            s.setData([
              { time: bars[0].time, value: px },
              { time: bars[bars.length - 1].time, value: px },
            ]);
          }
          lineSeriesRefs.current.push(s);
        } catch (err) {
          console.warn("[LiveChart] visual line err", err?.message);
        }
      });
    });
  }, [markers.visuals, layers.visuals, bars]);

  return (
    <div className="fixed inset-0 bg-white flex flex-col" data-testid="live-chart-page" onClick={() => setPopover(null)}>
      <TopBar
        symbol={symbol} setSymbol={setSymbol}
        tf={tf} setTf={setTf}
        layers={layers} setLayers={setLayers}
        refreshing={refreshing} onRefresh={load}
        lastPrice={lastPrice}
        ohlcSource={ohlcSource}
      />

      <div className="relative flex-1">
        <div ref={containerRef} className="absolute inset-0" data-testid="chart-canvas" />

        {/* Bottom legend strip */}
        <div className="absolute bottom-2 left-2 right-2 flex flex-wrap gap-1.5 pointer-events-none">
          {layers.trades && (
            <span className="px-2 py-0.5 rounded-md bg-white/90 backdrop-blur border border-emerald-300 text-[10px] font-bold text-emerald-700">
              ▲ {markers.trades.filter(t => (t.pnl ?? 0) >= 0).length} wins · ▼ {markers.trades.filter(t => (t.pnl ?? 0) < 0).length} losses
            </span>
          )}
          {layers.shadows && markers.shadows.length > 0 && (
            <span className="px-2 py-0.5 rounded-md bg-white/90 backdrop-blur border border-purple-300 text-[10px] font-bold text-purple-700">
              ● {markers.shadows.length} shadow
            </span>
          )}
          {layers.visuals && markers.visuals.length > 0 && (
            <span className="px-2 py-0.5 rounded-md bg-white/90 backdrop-blur border border-amber-300 text-[10px] font-bold text-amber-700">
              ▭ {markers.visuals.length} zones
            </span>
          )}
        </div>

        {popover && <ContextPopover data={popover} onClose={() => setPopover(null)} />}

        {bars.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm font-mono">
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> Loading chart…
          </div>
        )}
      </div>
      <CoachLiveWidget />
    </div>
  );
}
