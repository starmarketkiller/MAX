import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { createChart, CandlestickSeries, LineSeries } from "lightweight-charts";
import {
  ChevronDown, Activity, X, Sparkles, TrendingUp, TrendingDown,
  Eye, EyeOff, RefreshCw, Layers,
} from "lucide-react";
import api from "@/lib/api";
import { useVisiblePolling } from "@/lib/useVisiblePolling";
import CoachLiveWidget from "@/components/CoachLiveWidget";
import DataProvenanceBadge from "@/components/DataProvenanceBadge";
import GeometryLayer from "@/components/GeometryLayer";
import { useTheme } from "@/lib/theme";

const TF_OPTIONS = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"];

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
const CHART_DARK = {
  ...CHART_LIGHT,
  layout: { background: { type: "solid", color: "#0b0f17" }, textColor: "#94a3b8" },
  grid: { vertLines: { color: "rgba(148,163,184,.08)" }, horzLines: { color: "rgba(148,163,184,.08)" } },
  rightPriceScale: { borderColor: "#273244" },
  timeScale: { ...CHART_LIGHT.timeScale, borderColor: "#273244" },
};
export const chartThemeFor = (theme) => theme === "dark" ? CHART_DARK : CHART_LIGHT;
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
      className="absolute z-50 bg-card shadow-2xl rounded-xl border border-border p-4 max-w-xs"
      style={{ left: data.x, top: data.y, transform: "translate(-50%, -110%)" }}
      onClick={(e) => e.stopPropagation()}
      data-testid="chart-context-popover"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500 font-bold">
            {data.kind}
          </div>
          <div className="text-sm font-bold text-foreground mt-0.5">{data.title}</div>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="space-y-1.5 text-xs">
        {data.rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between gap-3">
            <span className="text-slate-500">{r.label}</span>
            <span className={`font-mono font-semibold ${r.tone === "pos" ? "text-emerald-600" : r.tone === "neg" ? "text-rose-600" : "text-foreground"}`}>
              {r.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------
// CHART-REAL-DATA-V1: dati REALI (store verificato) o stato esplicito di indisponibilita'.
// Nessun fallback sintetico. La navigazione storica non viene resettata dal polling (nessun fitContent nel ciclo di aggiornamento).
// ---------------------------------------------------------------------------------------------
const INITIAL_BARS = 1500;
const PAGE_BARS = 1000;
const FIRST_VIEW_BARS = 160;
const TF_SECONDS = { M1: 60, M5: 300, M15: 900, M30: 1800, H1: 3600, H4: 14400, D1: 86400, W1: 604800, MN1: 2592000 };
const COMPLETENESS_LABEL = {
  COMPLETE: "COMPLETE",
  PARTIAL: "PARTIAL (calendario non verificato o bordo di copertura)",
  GAP: "GAP (minuti mancanti non spiegati)",
  OPEN: "OPEN (barra in formazione)",
};

function withAlpha(hex, alpha) {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h, 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}

/** Barra del dataset -> punto della serie. PARTIAL/GAP/OPEN NON sono disegnate come barre complete. */
export function toSeriesBar(b) {
  const base = { time: b.time, open: b.open, high: b.high, low: b.low, close: b.close };
  const up = b.close >= b.open;
  const main = up ? CANDLE_STYLE.upColor : CANDLE_STYLE.downColor;
  if (b.completeness === "PARTIAL") return { ...base, color: withAlpha(main, 0.4), wickColor: withAlpha(main, 0.55), borderColor: withAlpha(main, 0.7) };
  if (b.completeness === "GAP") return { ...base, color: withAlpha(main, 0.25), wickColor: "#f59e0b", borderColor: "#f59e0b" };
  if (b.completeness === "OPEN") return { ...base, color: "rgba(100,116,139,0.45)", wickColor: "#64748b", borderColor: "#64748b" };
  return base;
}

export function markerTime(t) {
  const raw = t.closeTime ?? t.time;
  if (raw == null) return null;
  if (typeof raw === "number") return raw > 1e12 ? Math.floor(raw / 1000) : raw;
  const ms = new Date(raw).getTime();
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : null;
}

function describeError(err) {
  const status = err?.response?.status;
  const code = err?.response?.data?.detail?.code || err?.response?.data?.detail || "";
  if (status === 403) return { kind: "PARTITION", text: `Dati non autorizzati per il Chart (${code || "403"}). Nessun dato mostrato.` };
  if (status === 503) return { kind: "INTEGRITY", text: `Dati non verificabili (${code || "503"}). Nessun dato mostrato.` };
  if (status === 422) return { kind: "REQUEST", text: `Richiesta non valida (${code || "422"}).` };
  if (status === 401) return { kind: "AUTH", text: "Sessione scaduta: accedi di nuovo." };
  return { kind: "NETWORK", text: "Errore di rete: impossibile contattare il backend." };
}

const EMPTY_MARKERS = { trades: [], open: [], shadows: [], visuals: [] };
const isCancel = (e) => e?.code === "ERR_CANCELED" || e?.name === "CanceledError" || e?.name === "AbortError";
const fmtTime = (t) => new Date(t * 1000).toISOString().replace("T", " ").slice(0, 16);

/** FIX-02: la risposta appartiene alla richiesta che l'ha prodotta? Confronta l'identita' dichiarata dal backend (quando presente) con il contesto della richiesta. */
export function responseMatches(data, ctx) {
  if (!data || typeof data !== "object") return false;
  if (data.dataset_id && ctx.source && data.dataset_id !== ctx.source) return false;
  if (data.timeframe && data.timeframe !== ctx.tf) return false;
  if (data.symbol_requested && String(data.symbol_requested).toUpperCase() !== String(ctx.symbol).toUpperCase()) return false;
  return true;
}

/** FIX-03: dove cade la data richiesta rispetto alle barre ricevute? Restituisce l'istante su cui centrare la vista e, se non e' esatta, una nota esplicita. */
export function resolveTarget(bars, target, step, hasMore) {
  if (!bars.length) return { centre: null, note: "Nessuna barra nell'intervallo richiesto." };
  const idx = bars.findIndex((b) => b.time >= target);
  if (idx === -1) return { centre: bars[bars.length - 1].time, note: `Data richiesta oltre l'ultima barra disponibile (${fmtTime(bars[bars.length - 1].time)}): mostrata la coda.` };
  if (bars[idx].time === target) return { centre: target, note: null };
  if (idx > 0 && bars[idx - 1].time + step > target) return { centre: bars[idx - 1].time, note: null };      // la data cade dentro una barra esistente
  if (idx === 0 && !hasMore) return { centre: bars[0].time, note: `Data richiesta precedente alla copertura: mostrata la prima barra disponibile (${fmtTime(bars[0].time)}).` };
  return { centre: bars[idx].time, note: `Nessuna contrattazione registrata nell'istante richiesto: mostrata la barra successiva (${fmtTime(bars[idx].time)}).` };
}

function clockHint(meta) {
  const basis = String(meta?.clock_basis || "").toUpperCase();
  if (!meta) return "orologio del dataset";
  if (basis.startsWith("TERMINAL")) return "orologio terminale · UTC assoluto non verificato";
  if (basis.startsWith("UTC")) return "UTC";
  return "orologio del dataset (non verificato)";
}

function ControlBar({ sources, source, setSource, symbol, setSymbol, tf, setTf, tfs, layers, setLayers, refreshing, onRefresh, lastPrice, meta, gotoValue, setGotoValue, onGoto, mode }) {
  const [openLayers, setOpenLayers] = useState(false);
  const cur = sources.find((s) => s.dataset_id === source);
  const aliases = cur?.symbol_aliases?.length ? cur.symbol_aliases : [symbol];
  return (
    <div className="flex flex-wrap items-center gap-2 px-3 py-2 border-b border-border bg-card sticky top-0 z-30">
      <select
        value={source || ""}
        onChange={(e) => setSource(e.target.value)}
        className="h-9 max-w-[220px] px-2.5 rounded-lg border border-border bg-background text-xs font-mono font-bold focus:outline-none focus:ring-2 focus:ring-cyan-400"
        data-testid="chart-source-select"
        title="Fonte dati"
      >
        {sources.length === 0 && <option value="">Nessuna fonte</option>}
        {sources.map((s) => <option key={s.dataset_id} value={s.dataset_id}>{s.label || s.dataset_id}</option>)}
      </select>

      <select
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        className="h-9 px-2.5 rounded-lg border border-border bg-background text-sm font-mono font-bold tracking-tight focus:outline-none focus:ring-2 focus:ring-cyan-400"
        data-testid="chart-symbol-select"
      >
        {aliases.map((s) => <option key={s} value={s}>{s}</option>)}
      </select>

      <div className="flex gap-0.5 bg-secondary rounded-lg p-0.5">
        {TF_OPTIONS.map((t) => {
          const ok = tfs.includes(t);
          return (
            <button
              key={t}
              onClick={() => ok && setTf(t)}
              disabled={!ok}
              data-testid={`chart-tf-${t}`}
              title={ok ? t : `${t}: non disponibile in questo dataset`}
              className={`h-7 px-2 rounded-md text-[11px] font-mono font-bold transition-all ${
                tf === t ? "bg-foreground text-background" : ok ? "text-muted-foreground hover:text-foreground" : "text-muted-foreground/30 cursor-not-allowed"
              }`}
            >
              {t}
            </button>
          );
        })}
      </div>

      <span
        data-testid="chart-mode"
        className={`px-2 py-1 rounded-md text-[10px] font-mono font-bold tracking-wider border ${mode === "LIVE" ? "border-emerald-500/40 text-emerald-600" : "border-teal-500/40 text-teal-600"}`}
        title={mode === "LIVE" ? "Dato in aggiornamento" : "Dato storico statico: nessun aggiornamento automatico"}
      >
        {mode}
      </span>

      {lastPrice != null && (
        <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-md bg-secondary border border-border">
          <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Last</span>
          <span className="text-sm font-mono font-bold text-foreground tabular-nums" data-testid="chart-last-price">{lastPrice.toFixed(2)}</span>
        </div>
      )}

      <DataProvenanceBadge
        source={meta?.source || "UNAVAILABLE"}
        label={meta?.status === "AVAILABLE_OFFLINE" ? "REAL · HISTORICAL" : meta?.status || "UNAVAILABLE"}
        title={meta ? `Dataset ${meta.dataset_id || "-"} · ${meta.feed_kind || "-"}` : "Nessun dato"}
      />

      <form
        className="flex items-center gap-1"
        onSubmit={(e) => { e.preventDefault(); onGoto(); }}
        data-testid="chart-goto-form"
      >
        <input
          type="datetime-local"
          value={gotoValue}
          onChange={(e) => setGotoValue(e.target.value)}
          className="h-9 px-2 rounded-lg border border-border bg-background text-xs font-mono"
          data-testid="chart-goto-input"
          title="Data e ora (stessa base oraria del dataset: vedi indicazione orologio)"
        />
        <button type="submit" className="h-9 px-2.5 rounded-lg border border-slate-300 text-xs font-semibold hover:border-cyan-500" data-testid="chart-goto-button">Vai</button>
        <span className="hidden md:inline text-[10px] font-mono text-muted-foreground" data-testid="chart-goto-clock" title="La data inserita e' interpretata sulla stessa base oraria del dataset; nessun fuso del broker e' stato dedotto">
          {clockHint(meta)}
        </span>
      </form>

      <div className="flex-1" />

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
        title="Ricarica (non cambia lo zoom)"
      >
        <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
      </button>
      {cur && <span className="sr-only" data-testid="chart-source-current">{cur.dataset_id}</span>}
    </div>
  );
}

function DatasetStrip({ meta, hasMore, nBars }) {
  if (!meta) return null;
  const range = meta.available_range;
  return (
    <div className="shrink-0 px-3 py-1 text-[11px] font-mono text-muted-foreground border-b border-border flex flex-wrap gap-x-3" data-testid="chart-dataset-strip">
      <span>dataset <b className="text-foreground">{meta.dataset_id}</b></span>
      <span>feed {meta.feed_kind}{meta.broker_server ? ` · ${meta.broker_server}` : ""}</span>
      <span>{meta.symbol_actual} {meta.timeframe}</span>
      {range && <span>copertura {range.first_iso?.slice(0, 16).replace("T", " ")} → {range.last_iso?.slice(0, 16).replace("T", " ")}</span>}
      <span>clock {String(meta.clock_basis || "").split(" ")[0] || "?"}</span>
      <span>calendario {meta.calendar_status || "?"}</span>
      <span>ver {String(meta.dataset_version || "").slice(0, 8)}</span>
      <span>{nBars} barre{hasMore ? " · altre a sinistra" : " · inizio dataset"}</span>
      {(meta.limitations || []).length > 0 && <span className="text-amber-600" title={meta.limitations.join("\n")}>limiti: {meta.limitations.length}</span>}
    </div>
  );
}

export default function LiveChartPage({ embedded = false }) {
  const { theme } = useTheme();
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const barsRef = useRef([]);
  const metaRef = useRef(null);
  const viewRef = useRef(null);
  const genRef = useRef(0);                 // generazione: ogni cambio di contesto o nuovo caricamento iniziale invalida TUTTE le richieste precedenti
  const ctxKeyRef = useRef("");
  const pagerRef = useRef(null);            // generazione della paginazione in corso (una sola per generazione)
  const inflightRef = useRef(new Set());
  const mountedRef = useRef(true);
  const viewLockRef = useRef(false);        // true mentre il grafico applica dati/vista: i range-change sincroni non sono scrolling dell'utente
  const markersGenRef = useRef(0);
  const [gotoNote, setGotoNote] = useState(null);
  const [sources, setSources] = useState([]);
  const [source, setSource] = useState("");
  const [symbolSel, setSymbol] = useState("GOLD");
  const [tfSel, setTf] = useState("M15");
  const [layers, setLayers] = useState(LAYER_DEFAULTS);
  const [refreshing, setRefreshing] = useState(false);
  const [bars, setBars] = useState([]);
  const [meta, setMeta] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [nextBefore, setNextBefore] = useState(null);
  const [error, setError] = useState(null);
  const [markers, setMarkers] = useState({ trades: [], open: [], shadows: [], visuals: [] });
  const [popover, setPopover] = useState(null);
  const [lastPrice, setLastPrice] = useState(null);
  const [hover, setHover] = useState(null);
  const [gotoValue, setGotoValue] = useState("");
  const [epoch, setEpoch] = useState(0);
  const nextBeforeRef = useRef(null);
  const hasMoreRef = useRef(false);

  const cur = sources.find((s) => s.dataset_id === source);
  const tfs = cur?.timeframes || [];
  // valori EFFETTIVI coerenti con la fonte scelta: mai una richiesta con simbolo/timeframe che il dataset non contiene
  const symbol = cur && !cur.symbol_aliases.includes(symbolSel) ? cur.symbol_aliases[0] : symbolSel;
  const tf = cur && !cur.timeframes.includes(tfSel) ? (cur.timeframes.includes("M15") ? "M15" : cur.timeframes[0]) : tfSel;
  const mode = meta?.mode === "LIVE" ? "LIVE" : "HISTORICAL";

  // -------- FIX-02: contesto di richiesta = fonte + simbolo + timeframe (+ generazione). Una risposta di un contesto precedente non puo' toccare lo stato corrente --------
  const ctxKey = `${source}|${symbol}|${tf}`;
  if (ctxKeyRef.current !== ctxKey) {       // aggiornamento idempotente del ref durante il render: invalida subito le richieste del contesto precedente
    ctxKeyRef.current = ctxKey;
    genRef.current += 1;
    pagerRef.current = null;
  }
  const isCurrent = useCallback((gen) => mountedRef.current && gen === genRef.current, []);
  const abortAll = useCallback(() => {
    inflightRef.current.forEach((c) => { try { c.abort(); } catch (err) { void err; } });
    inflightRef.current.clear();
  }, []);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; genRef.current += 1; abortAll(); };
  }, [abortAll]);
  // cambio di contesto: annulla le richieste e svuota candele, provenienza, indicatori e note del contesto precedente (nessuna contaminazione visibile)
  useEffect(() => {
    abortAll();
    barsRef.current = [];
    metaRef.current = null;
    nextBeforeRef.current = null;
    hasMoreRef.current = false;
    viewRef.current = null;
    setBars([]);
    setMeta(null);
    setHasMore(false);
    setNextBefore(null);
    setLastPrice(null);
    setError(null);
    setGotoNote(null);
    setHover(null);
    setPopover(null);
    setRefreshing(false);
  }, [ctxKey, abortAll]);

  // -------- Chart init (ricreato solo al cambio tema: la vista viene salvata e ripristinata) --------
  useEffect(() => {
    if (!containerRef.current) return undefined;
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      ...chartThemeFor(theme),
    });
    const candleSeries = chart.addSeries(CandlestickSeries, CANDLE_STYLE);
    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    setEpoch((e) => e + 1);
    const onResize = () => {
      if (!containerRef.current) return;
      chart.resize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    };
    window.addEventListener("resize", onResize);
    // il contenitore cambia altezza anche senza resize della finestra (es. compare la striscia del dataset): l'asse dei tempi deve restare visibile
    const observer = typeof ResizeObserver !== "undefined" ? new ResizeObserver(onResize) : null;
    if (observer) observer.observe(containerRef.current);
    return () => {
      window.removeEventListener("resize", onResize);
      if (observer) observer.disconnect();
      try { viewRef.current = chart.timeScale().getVisibleLogicalRange(); } catch (err) { void err; }
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
    };
  }, [theme]);

  // -------- Etichetta oraria coerente con l'orologio del dataset (nessun "UTC" se non certificato) --------
  useEffect(() => {
    if (!chartRef.current) return;
    const terminal = String(meta?.clock_basis || "").toUpperCase().startsWith("TERMINAL");
    chartRef.current.applyOptions({
      localization: {
        locale: "en-US",
        timeFormatter: (time) => new Date(time * 1000).toISOString().replace("T", " ").slice(5, 16) + (terminal ? " terminal" : " UTC"),
      },
    });
  }, [meta?.clock_basis, epoch]);

  // -------- Fonti --------
  const loadSources = useCallback(async () => {
    try {
      const { data } = await api.get("/chart/sources");
      const list = (data.sources || []).filter((s) => s.dataset_id && s.timeframes);
      setSources(list);
      if (!list.length) {
        setError({ kind: "UNAVAILABLE", text: `Nessuna fonte dati reale disponibile (${data.reason || "NO_DATASETS"}). Nessun dato sintetico viene mostrato.` });
        return;
      }
      setSource((prev) => prev && list.some((s) => s.dataset_id === prev) ? prev : (data.default_source && list.some((s) => s.dataset_id === data.default_source) ? data.default_source : list[0].dataset_id));
    } catch (e) {
      setError(describeError(e));
    }
  }, []);
  useEffect(() => { loadSources(); }, [loadSources]);

  // allinea la selezione dell'utente ai valori effettivi (la richiesta usa gia' quelli effettivi)
  useEffect(() => {
    if (symbolSel !== symbol) setSymbol(symbol);
    if (tfSel !== tf) setTf(tf);
  }, [symbolSel, symbol, tfSel, tf]);

  const applyResponse = useCallback((o, { prepend = false, view = "tail", target = null } = {}) => {
    if (o.status !== "AVAILABLE_OFFLINE" && o.status !== "AVAILABLE_LIVE") {
      barsRef.current = [];
      setBars([]);
      setMeta(null);
      setHasMore(false);
      setLastPrice(null);
      setError({ kind: "UNAVAILABLE", text: `Dato non disponibile: ${o.reason || o.status}${o.detail ? ` (${o.detail})` : ""}. Nessun dato sintetico viene mostrato.` });
      return;
    }
    setError(null);
    const incoming = o.bars || [];
    let centre = target;
    if (!prepend) {
      if (view === "target" && target != null) {                 // FIX-03: dichiara dove cade davvero la data richiesta
        const r = resolveTarget(incoming, target, TF_SECONDS[o.timeframe] || 900, !!o.has_more);
        centre = r.centre;
        setGotoNote(r.note ? { kind: "info", text: r.note } : null);
      } else {
        setGotoNote(null);
      }
    }
    const merged = prepend ? [...incoming, ...barsRef.current] : incoming;
    barsRef.current = merged;
    metaRef.current = o;
    nextBeforeRef.current = o.next_before;
    hasMoreRef.current = !!o.has_more;
    setBars(merged);
    setMeta(o);
    setHasMore(!!o.has_more);
    setNextBefore(o.next_before);
    if (!prepend && merged.length) setLastPrice(merged[merged.length - 1].close);
    viewRef.current = prepend ? viewRef.current : { kind: view, n: merged.length, added: incoming.length, target: centre };
  }, []);

  // -------- Carico iniziale al cambio di fonte/timeframe (l'unico momento in cui la vista viene riposizionata) --------
  const loadInitial = useCallback(async (before = null, target = null) => {
    if (!source) return;
    abortAll();                                  // un nuovo caricamento sostituisce qualunque richiesta (paginazione, refresh, caricamento precedente)
    const gen = ++genRef.current;
    pagerRef.current = null;
    const ctrl = new AbortController();
    inflightRef.current.add(ctrl);
    const ctx = { source, symbol, tf };
    setRefreshing(true);
    try {
      const q = `/chart/ohlc?source=${encodeURIComponent(source)}&symbol=${encodeURIComponent(symbol)}&tf=${tf}&limit=${INITIAL_BARS}${before ? `&before=${before}` : ""}`;
      const { data } = await api.get(q, { signal: ctrl.signal });
      if (!isCurrent(gen)) return;               // la cancellazione non basta: una risposta gia' completata ma obsoleta viene comunque ignorata
      if (!responseMatches(data, ctx)) {
        setError({ kind: "CONTEXT", text: "Risposta non coerente con la richiesta (dataset/simbolo/timeframe): scartata. Nessun dato mostrato." });
        return;
      }
      applyResponse(data, { view: before ? "target" : "tail", target });
    } catch (e) {
      if (isCancel(e) || !isCurrent(gen)) return;
      if (target == null) {
        barsRef.current = [];
        setBars([]);
        setMeta(null);
        setError(describeError(e));
      } else {                                   // FIX-03: una navigazione fallita (es. intervallo non autorizzato) non cancella il grafico gia' mostrato
        setGotoNote({ kind: "error", text: describeError(e).text });
      }
    } finally {
      inflightRef.current.delete(ctrl);
      if (isCurrent(gen)) setRefreshing(false);
    }
  }, [source, symbol, tf, applyResponse, abortAll, isCurrent]);
  useEffect(() => { loadInitial(); }, [loadInitial]);

  // -------- Marker (non inventati: solo cio' che restituisce il ledger) --------
  const loadMarkers = useCallback(async () => {
    const my = ++markersGenRef.current;          // una risposta marker di un simbolo precedente non puo' sovrascrivere quelli del simbolo corrente
    setMarkers(EMPTY_MARKERS);
    try {
      const { data: m } = await api.get(`/chart/markers?symbol=${symbol}`);
      if (!mountedRef.current || my !== markersGenRef.current) return;
      setMarkers({ trades: m.trades || m.markers || [], open: m.open || [], shadows: m.shadows || [], visuals: m.visuals || [] });
    } catch (e) { void e; }
  }, [symbol]);
  useEffect(() => { loadMarkers(); }, [loadMarkers]);

  useEffect(() => {
    try { localStorage.setItem("nxs_chart_context", JSON.stringify({ symbol, tf, source, ts: Date.now() })); } catch (err) { void err; }
  }, [symbol, tf, source]);

  // -------- Aggiornamento LIVE: solo coda, senza setData ne' fitContent --------
  const refreshTail = useCallback(async () => {
    if (!source || !candleSeriesRef.current) return;
    const gen = genRef.current;                  // un refresh concorrente non puo' applicare una coda a dati sostituiti nel frattempo (contesto o navigazione)
    const ctrl = new AbortController();
    inflightRef.current.add(ctrl);
    try {
      const { data } = await api.get(`/chart/ohlc?source=${encodeURIComponent(source)}&symbol=${encodeURIComponent(symbol)}&tf=${tf}&limit=3`, { signal: ctrl.signal });
      if (!isCurrent(gen) || !responseMatches(data, { source, symbol, tf }) || !candleSeriesRef.current) return;
      if (data.status !== "AVAILABLE_LIVE" && data.status !== "AVAILABLE_OFFLINE") return;
      (data.bars || []).forEach((b) => candleSeriesRef.current.update(toSeriesBar(b)));
      const last = (data.bars || []).slice(-1)[0];
      if (last) setLastPrice(last.close);
    } catch (e) { void e; } finally { inflightRef.current.delete(ctrl); }
  }, [source, symbol, tf, isCurrent]);
  useVisiblePolling(refreshTail, 5000, mode === "LIVE");

  // -------- Push barre: setData solo quando cambiano i dati; la vista e' gestita esplicitamente (mai fitContent) --------
  useEffect(() => {
    if (!candleSeriesRef.current) return;
    viewLockRef.current = true;                  // FIX-03: eventi di range-change emessi DURANTE setData/riposizionamento non sono scrolling dell'utente e non devono avviare paginazioni
    try {
      candleSeriesRef.current.setData(bars.map(toSeriesBar));
      const ts = chartRef.current?.timeScale();
      const v = viewRef.current;
      if (!ts || !bars.length) return;
      if (v && v.kind === "tail") {
        ts.setVisibleLogicalRange({ from: Math.max(0, bars.length - FIRST_VIEW_BARS), to: bars.length + 5 });
      } else if (v && v.kind === "target") {
        const idx = bars.findIndex((b) => b.time >= v.target);                    // centra la vista sulla barra risolta (non su un indice presunto)
        const centre = idx < 0 ? bars.length - 1 : idx;
        ts.setVisibleLogicalRange({ from: Math.max(0, centre - FIRST_VIEW_BARS / 2), to: centre + FIRST_VIEW_BARS / 2 });
      } else if (v && v.from !== undefined) {
        ts.setVisibleLogicalRange({ from: v.from, to: v.to });
      }
      viewRef.current = null;
    } finally {
      viewLockRef.current = false;
    }
  }, [bars, epoch]);

  // -------- Caricamento progressivo a sinistra, con vista conservata --------
  const loadOlder = useCallback(async () => {
    if (pagerRef.current !== null || !hasMoreRef.current || nextBeforeRef.current == null || !source) return;
    const gen = genRef.current;                  // la paginazione appartiene a UNA generazione/contesto: se cambia, il suo esito e' scartato
    pagerRef.current = gen;
    const cursor = nextBeforeRef.current;
    const ctrl = new AbortController();
    inflightRef.current.add(ctrl);
    const ctx = { source, symbol, tf };
    try {
      const q = `/chart/ohlc?source=${encodeURIComponent(source)}&symbol=${encodeURIComponent(symbol)}&tf=${tf}&limit=${PAGE_BARS}&before=${cursor}`;
      const { data } = await api.get(q, { signal: ctrl.signal });
      if (!isCurrent(gen) || nextBeforeRef.current !== cursor) return;       // contesto o base dati sostituiti mentre la richiesta era in corso
      if (!responseMatches(data, ctx)) {
        setError({ kind: "CONTEXT", text: "Pagina non coerente con la richiesta (dataset/simbolo/timeframe): scartata." });
        return;
      }
      if (data.status !== "AVAILABLE_OFFLINE" && data.status !== "AVAILABLE_LIVE") {
        applyResponse(data);
        return;
      }
      const range = chartRef.current?.timeScale().getVisibleLogicalRange();  // vista ATTUALE al completamento (non quella catturata all'avvio: l'utente puo' aver continuato a scorrere)
      const added = (data.bars || []).length;
      applyResponse(data, { prepend: true });
      if (range) viewRef.current = { from: range.from + added, to: range.to + added };    // stessa porzione visibile, spostata dell'offset delle barre aggiunte
    } catch (e) {
      if (isCancel(e) || !isCurrent(gen)) return;
      setError(describeError(e));
    } finally {
      inflightRef.current.delete(ctrl);
      if (pagerRef.current === gen) pagerRef.current = null;
    }
  }, [source, symbol, tf, applyResponse, isCurrent]);

  useEffect(() => {
    if (!chartRef.current) return undefined;
    const ts = chartRef.current.timeScale();
    const handler = (range) => { if (!viewLockRef.current && range && range.from < 25) loadOlder(); };
    ts.subscribeVisibleLogicalRangeChange(handler);
    return () => ts.unsubscribeVisibleLogicalRangeChange(handler);
  }, [loadOlder, epoch]);

  // -------- Selezione temporale --------
  const onGoto = useCallback(() => {
    if (!gotoValue) return;
    const ms = Date.parse(gotoValue + (gotoValue.length === 16 ? ":00Z" : "Z"));    // l'input e' letto come orologio del dataset (UTC/terminale), non come fuso locale: nessun fuso del broker e' dedotto
    if (!Number.isFinite(ms)) {
      setGotoNote({ kind: "error", text: "Data non valida: usa il formato aaaa-mm-gg hh:mm." });
      return;
    }
    const step = TF_SECONDS[tf] || 900;
    const target = Math.floor(ms / 1000);
    setGotoNote(null);
    loadInitial(target + Math.floor(INITIAL_BARS * 0.25) * step, target);       // un'unica richiesta il cui intervallo contiene il target; il target resta fisso nel viewRef finche' non e' applicato
  }, [gotoValue, tf, loadInitial]);

  // -------- Lettura OHLC della candela sotto il cursore --------
  useEffect(() => {
    if (!chartRef.current) return undefined;
    const chart = chartRef.current;
    const handler = (param) => {
      if (!param || param.time == null) { setHover(null); return; }
      const b = barsRef.current.find((x) => x.time === param.time);
      setHover(b || null);
    };
    chart.subscribeCrosshairMove(handler);
    return () => chart.unsubscribeCrosshairMove(handler);
  }, [epoch]);

  // -------- Marker trade (campo `closeTime` o `time`) --------
  const allMarkers = useMemo(() => {
    const arr = [];
    if (layers.trades) {
      markers.trades.forEach((t) => {
        const ts = markerTime(t);
        if (ts == null) return;
        const pnlKnown = t.pnl !== null && t.pnl !== undefined;
        const won = pnlKnown ? Number(t.pnl) >= 0 : null;
        arr.push({
          time: ts,
          position: won === true ? "belowBar" : "aboveBar",
          color: won === null ? "#64748b" : won ? "#16a34a" : "#dc2626",
          shape: won === true ? "arrowUp" : won === false ? "arrowDown" : "circle",
          text: `${t.strategy || "?"} · ${pnlKnown ? `${won ? "+" : ""}${Number(t.pnl).toFixed(0)}` : "—"}`,
          _payload: { kind: "trade", trade: t },
        });
      });
    }
    if (layers.shadows) {
      markers.shadows.forEach((s) => {
        const ts = Math.floor(new Date(s.detected_at).getTime() / 1000);
        if (!Number.isFinite(ts)) return;
        arr.push({ time: ts, position: "aboveBar", color: "#a855f7", shape: "circle", text: `Shadow · ${s.strategy || "?"}`, _payload: { kind: "shadow", shadow: s } });
      });
    }
    return arr.sort((a, b) => a.time - b.time);
  }, [layers.trades, layers.shadows, markers.trades, markers.shadows]);

  useEffect(() => {
    if (!candleSeriesRef.current) return;
    import("lightweight-charts").then(({ createSeriesMarkers }) => {
      try {
        candleSeriesRef.current?._markerPlugin?.detach?.();
        if (candleSeriesRef.current) {
          candleSeriesRef.current._markerPlugin = createSeriesMarkers(candleSeriesRef.current, allMarkers.map(({ _payload, ...m }) => m));
        }
      } catch (err) {
        console.warn("[LiveChart] marker plugin err", err?.message);
      }
    });
  }, [allMarkers, epoch]);

  // -------- Click -> popover --------
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current) return undefined;
    const chart = chartRef.current;
    const handler = (param) => {
      if (!param.point || !param.time) { setPopover(null); return; }
      const t = param.time;
      const candidate = allMarkers.map((m) => ({ ...m, dist: Math.abs(m.time - t) })).sort((a, b) => a.dist - b.dist)[0];
      if (!candidate || candidate.dist > (TF_SECONDS[tf] || 900) * 3) { setPopover(null); return; }
      const px = param.point.x;
      const py = param.point.y;
      const payload = candidate._payload || {};
      if (payload.kind === "trade") {
        const t2 = payload.trade;
        const pnlKnown = t2.pnl !== null && t2.pnl !== undefined;
        const won = pnlKnown ? Number(t2.pnl) >= 0 : null;
        setPopover({
          x: px, y: py, kind: "Closed trade", title: `${t2.strategy || "?"} · ${t2.side || "?"}`,
          rows: [
            { label: "P&L", value: pnlKnown ? `${won ? "+" : ""}$${Number(t2.pnl).toFixed(2)}` : "—", tone: won === null ? undefined : won ? "pos" : "neg" },
            { label: "Score", value: t2.score ?? "—" },
            { label: "Lots", value: t2.lots == null ? "—" : Number(t2.lots).toFixed(2) },
            { label: "Reason", value: t2.reason || "—" },
            { label: "Session", value: t2.session || "—" },
          ],
        });
      } else if (payload.kind === "shadow") {
        const s = payload.shadow;
        setPopover({
          x: px, y: py, kind: "Shadow trade", title: `${s.strategy || "?"} · ${s.side || "?"}`,
          rows: [
            { label: "Blocker", value: s.blocker || "—" },
            { label: "Hypoth. R", value: s.would_have_r != null ? s.would_have_r.toFixed(2) : "—", tone: s.would_have_r == null ? undefined : s.would_have_r > 0 ? "pos" : "neg" },
            { label: "Score", value: s.score ?? "—" },
            { label: "HTF", value: s.htf_bias || "—" },
          ],
        });
      }
    };
    chart.subscribeClick(handler);
    return () => chart.unsubscribeClick(handler);
  }, [allMarkers, tf, epoch]);

  // -------- Zone/livelli del layer "visuals" (vuoto finche' il backend non ne fornisce) --------
  const lineSeriesRefs = useRef([]);
  useEffect(() => {
    if (!chartRef.current) return;
    lineSeriesRefs.current.forEach((s) => {
      try { chartRef.current.removeSeries(s); } catch (err) { void err; }
    });
    lineSeriesRefs.current = [];
    if (!layers.visuals) return;
    markers.visuals.slice(0, 30).forEach((v) => {
      const cfg = classifyVisual(v);
      const priceCenter = v.price;
      const priceTop = v.top != null ? v.top : priceCenter;
      const priceBot = v.bottom != null ? v.bottom : priceCenter;
      if (priceCenter == null && priceTop == null) return;
      const isZone = priceTop != null && priceBot != null && priceTop !== priceBot;
      (isZone ? [priceTop, priceBot] : [priceCenter]).forEach((px, idx) => {
        if (px == null) return;
        try {
          const s = chartRef.current.addSeries(LineSeries, { color: cfg.border, lineWidth: 1, lineStyle: idx === 0 ? 2 : 3, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
          if (bars.length) s.setData([{ time: bars[0].time, value: px }, { time: bars[bars.length - 1].time, value: px }]);
          lineSeriesRefs.current.push(s);
        } catch (err) {
          console.warn("[LiveChart] visual line err", err?.message);
        }
      });
    });
  }, [markers.visuals, layers.visuals, bars, epoch]);

  const pip = cur?.instrument_spec?.pip_convention;
  const pipSize = pip && typeof pip === "object" ? pip.pip_price_usd_per_oz : null;

  return (
    <div className={embedded ? "h-[430px] min-h-[360px] bg-card flex flex-col" : "fixed inset-0 bg-card flex flex-col"} data-testid="live-chart-page" onClick={() => setPopover(null)}>
      <ControlBar
        sources={sources} source={source} setSource={setSource}
        symbol={symbol} setSymbol={setSymbol}
        tf={tf} setTf={setTf} tfs={tfs}
        layers={layers} setLayers={setLayers}
        refreshing={refreshing} onRefresh={() => loadInitial()}
        lastPrice={lastPrice} meta={meta}
        gotoValue={gotoValue} setGotoValue={setGotoValue} onGoto={onGoto} mode={mode}
      />
      <DatasetStrip meta={meta} hasMore={hasMore} nBars={bars.length} />
      {gotoNote && (
        <div className={`shrink-0 px-3 py-1 text-[11px] font-mono border-b border-border ${gotoNote.kind === "error" ? "text-rose-600" : "text-amber-700"}`} data-testid="chart-goto-note" role="status">
          {gotoNote.text}
        </div>
      )}

      <div className="relative flex-1 min-h-0">
        <div ref={containerRef} className="absolute inset-x-0 top-0 bottom-1" data-testid="chart-canvas" />
        {/* CHART-GEOMETRY-01: strumenti geometrici manuali + memoria grafica persistente (non tocca dati, markers ne' guardia) */}
        <GeometryLayer chartRef={chartRef} seriesRef={candleSeriesRef} bars={bars} meta={meta} symbol={symbol} tf={tf} source={source} epoch={epoch} dark={theme === "dark"} />

        {hover && (
          <div className="absolute top-2 left-2 z-20 rounded-md bg-card/90 border border-border px-2 py-1 text-[11px] font-mono pointer-events-none" data-testid="chart-ohlc-readout">
            {new Date(hover.time * 1000).toISOString().replace("T", " ").slice(0, 16)} · O {hover.open.toFixed(2)} H {hover.high.toFixed(2)} L {hover.low.toFixed(2)} C {hover.close.toFixed(2)}
            {" · "}Δ {(hover.close - hover.open).toFixed(2)}{pipSize ? ` (${((hover.close - hover.open) / pipSize).toFixed(1)} pip @ ${pipSize} USD/oz)` : ""}
            {" · "}<span className={hover.completeness === "COMPLETE" ? "text-emerald-600" : "text-amber-600"} title={(hover.reason || []).join(", ")}>{COMPLETENESS_LABEL[hover.completeness] || hover.completeness}</span>
            {" · "}min {hover.minutes_present}{hover.minutes_missing ? ` (−${hover.minutes_missing})` : ""}
          </div>
        )}

        <div className="absolute bottom-8 left-2 right-2 flex flex-wrap gap-1.5 pointer-events-none">
          {layers.trades && (
            <span className="px-2 py-0.5 rounded-md bg-card/90 border border-emerald-500/30 text-[10px] font-bold text-emerald-700 dark:text-emerald-400">
              ▲ {markers.trades.filter(t => t.pnl != null && t.pnl >= 0).length} wins · ▼ {markers.trades.filter(t => t.pnl != null && t.pnl < 0).length} losses
            </span>
          )}
          {layers.shadows && markers.shadows.length > 0 && (
            <span className="px-2 py-0.5 rounded-md bg-card/90 border border-purple-500/30 text-[10px] font-bold text-purple-700 dark:text-purple-400">● {markers.shadows.length} shadow</span>
          )}
          {layers.visuals && markers.visuals.length > 0 && (
            <span className="px-2 py-0.5 rounded-md bg-card/90 border border-amber-500/30 text-[10px] font-bold text-amber-700 dark:text-amber-400">▭ {markers.visuals.length} zones</span>
          )}
          {bars.some((b) => b.completeness && b.completeness !== "COMPLETE") && (
            <span className="px-2 py-0.5 rounded-md bg-card/90 border border-amber-500/30 text-[10px] font-bold text-amber-700 dark:text-amber-400" data-testid="chart-partial-legend">
              barre sbiadite = PARTIAL/GAP (non complete)
            </span>
          )}
        </div>

        {popover && <ContextPopover data={popover} onClose={() => setPopover(null)} />}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center p-6 text-center text-sm font-mono text-muted-foreground bg-card/80" data-testid="chart-error" role="alert">
            <div className="max-w-md"><div className="text-[10px] tracking-widest font-bold mb-1">{error.kind}</div>{error.text}</div>
          </div>
        )}
        {!error && bars.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm font-mono" data-testid="chart-loading">
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> Caricamento dati reali…
          </div>
        )}
      </div>
      {!embedded && <CoachLiveWidget />}
    </div>
  );
}
