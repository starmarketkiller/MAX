import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, Upload, FileDown, RefreshCw, AlertTriangle, CheckCircle2,
  Zap, ShieldAlert, Cpu, Eye, Filter, Sparkles } from "lucide-react";
import api, { API, formatApiError } from "@/lib/api";
import { Card, cls } from "@/pages/dashboard/shared";
import { useStrategyHub } from "@/lib/strategyHub";

// =====================================================================
// HEATMAP HELPERS — value-driven row/cell tinting (Bloomberg-style)
// =====================================================================
function pfTone(pf) {
  if (pf == null || pf === 0) return null;
  if (pf >= 1.5) return "pos-strong";
  if (pf >= 1.1) return "pos";
  if (pf >= 0.9) return "neutral";
  if (pf >= 0.6) return "neg";
  return "neg-strong";
}
function winrateTone(wr) {
  if (wr == null) return null;
  if (wr >= 65) return "pos-strong";
  if (wr >= 55) return "pos";
  if (wr >= 45) return "neutral";
  if (wr >= 35) return "neg";
  return "neg-strong";
}
function expectancyTone(r) {
  if (r == null) return null;
  if (r >= 0.5) return "pos-strong";
  if (r > 0) return "pos";
  if (r === 0) return "neutral";
  if (r > -0.3) return "neg";
  return "neg-strong";
}
const HEAT_BG = {
  "pos-strong": "bg-emerald-500/20",
  "pos":        "bg-emerald-500/10",
  "neutral":    "",
  "neg":        "bg-rose-500/10",
  "neg-strong": "bg-rose-500/20",
};
const HEAT_TEXT = {
  "pos-strong": "text-emerald-300 font-bold",
  "pos":        "text-emerald-400",
  "neutral":    "text-muted-foreground",
  "neg":        "text-rose-400",
  "neg-strong": "text-rose-300 font-bold",
};

function HeatCell({ tone, value, align = "right" }) {
  return (
    <td className={cls(
      "px-3 py-2 tabular-nums transition-colors",
      align === "right" ? "text-right" : "",
      tone && HEAT_BG[tone],
      tone && HEAT_TEXT[tone]
    )}>
      {value}
    </td>
  );
}

const HEALTH_STATES = [
  // v2.0.9 — 8 semantic states
  "HEALTHY", "SIGNAL_BLOCKED", "SETUP_NOT_FOUND", "EXECUTED_NO_DATA",
  "NO_DATA_YET", "NOT_CALLED", "DISABLED_BY_USER", "NEEDS_REVIEW",
];

const HEALTH_COLOR = {
  HEALTHY:          "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
  SIGNAL_BLOCKED:   "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30",
  SETUP_NOT_FOUND:  "bg-slate-500/15 text-slate-600 dark:text-slate-300 border-slate-500/30",
  EXECUTED_NO_DATA: "bg-sky-500/15 text-sky-700 dark:text-sky-400 border-sky-500/30",
  NO_DATA_YET:      "bg-zinc-500/10 text-zinc-500 dark:text-zinc-400 border-zinc-500/20",
  NOT_CALLED:       "bg-orange-500/15 text-orange-700 dark:text-orange-400 border-orange-500/30",
  DISABLED_BY_USER: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
  NEEDS_REVIEW:     "bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-400 border-fuchsia-500/30",
};

// v2.0.7b — Family classification (allineato con strategy_stats.py STRATEGY_META)
const FAMILY_OPTIONS = [
  { id: "ALL",          label: "All" },
  { id: "TREND",        label: "Trend (8)" },
  { id: "REVERSAL",     label: "Reversal (4)" },
  { id: "SMC",          label: "SMC/ICT (14)" },
  { id: "INSTITUTIONAL", label: "Institutional (9)" },
];

const FAMILY_COLOR = {
  TREND:         "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30",
  REVERSAL:      "bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-400 border-fuchsia-500/30",
  SMC:           "bg-violet-500/15 text-violet-700 dark:text-violet-400 border-violet-500/30",
  INSTITUTIONAL: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
  OTHER:         "bg-slate-500/15 text-slate-600 dark:text-slate-300 border-slate-500/30",
};

const STATUS_COLOR = {
  OPERATIONAL:        "text-emerald-600",
  READY_FOR_BACKTEST: "text-sky-600",
  WEAK:               "text-orange-600",
  UNKNOWN:            "text-muted-foreground",
};

const SECTION_TABS = [
  { id: "health",      label: "E. Health Status",  icon: Eye },
  { id: "detection",   label: "A. Detection",      icon: Activity },
  { id: "gate",        label: "B. Gate",           icon: ShieldAlert },
  { id: "execution",   label: "C. Execution",      icon: Zap },
  { id: "performance", label: "D. Performance",    icon: Cpu },
  { id: "shadow",      label: "F. Shadow / Skipped", icon: Sparkles },
];

function StatTile({ label, value, hint, color }) {
  return (
    <Card className="p-4">
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cls("text-2xl font-bold mt-1 tabular-nums", color)}>{value}</div>
      {hint && <div className="text-[11px] text-muted-foreground mt-0.5">{hint}</div>}
    </Card>
  );
}

function HealthBadge({ state }) {
  return (
    <span className={cls(
      "inline-block px-2 py-0.5 rounded text-[10px] font-bold border tabular-nums",
      HEALTH_COLOR[state] || HEALTH_COLOR.NEEDS_REVIEW
    )} data-testid={`health-badge-${state}`}>
      {state}
    </span>
  );
}

function FamilyBadge({ family }) {
  if (!family) return null;
  return (
    <span className={cls(
      "inline-block px-1.5 py-0.5 rounded text-[9px] font-semibold border tabular-nums",
      FAMILY_COLOR[family] || FAMILY_COLOR.OTHER
    )} data-testid={`family-badge-${family}`}>
      {family}
    </span>
  );
}

function sumRTextClass(v) {
  if (v > 0) return "text-emerald-600";
  if (v < 0) return "text-rose-600";
  return "";
}

function ShadowSkippedTable({ symbol }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [totals, setTotals] = useState({ total_strategies: 0, total_blocked: 0 });

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api.get("/analytics/shadow", { params: symbol ? { symbol } : {} })
      .then(({ data }) => {
        if (!alive) return;
        setRows(data.rows || []);
        setTotals({ total_strategies: data.total_strategies || 0, total_blocked: data.total_blocked || 0 });
      })
      .catch(() => alive && setRows([]))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [symbol]);

  if (loading) return <Card className="p-6 text-sm text-muted-foreground">Loading shadow data...</Card>;
  if (rows.length === 0) {
    return (
      <Card className="p-6 text-sm text-muted-foreground" data-testid="shadow-empty">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="h-4 w-4 text-sky-500" />
          <span className="font-semibold text-foreground">Shadow Trading Log · v2.0.8</span>
        </div>
        Nessun signal bloccato registrato ancora. Compila e attacca l&apos;EA v2.0.8 con
        <code className="px-1 mx-1 rounded bg-secondary text-[10px]">InpEnableShadowTrading=true</code>
        per iniziare a raccogliere dati forensics.
      </Card>
    );
  }
  return (
    <Card className="overflow-x-auto" data-testid="shadow-skipped-table">
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="text-sm font-semibold flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-sky-500" />
          Shadow / Skipped Trades · {totals.total_strategies} strategies · {totals.total_blocked} blocked
        </div>
      </div>
      <table className="w-full text-xs">
        <thead className="bg-secondary/60">
          <tr>
            <th className="text-left px-3 py-2">Strategy</th>
            <th className="text-right px-3 py-2">Blocked</th>
            <th className="text-right px-3 py-2">W-Win</th>
            <th className="text-right px-3 py-2">W-Loss</th>
            <th className="text-right px-3 py-2">WinRate%</th>
            <th className="text-right px-3 py-2">Avg R</th>
            <th className="text-right px-3 py-2">Sum R</th>
            <th className="text-left px-3 py-2">Dominant Blocker</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.strategy} className="border-t border-border" data-testid={`shadow-row-${r.strategy}`}>
              <td className="px-3 py-2 font-mono font-semibold">{r.strategy}</td>
              <td className="px-3 py-2 text-right tabular-nums">{r.blocked}</td>
              <td className="px-3 py-2 text-right tabular-nums text-emerald-600">{r.would_win}</td>
              <td className="px-3 py-2 text-right tabular-nums text-rose-600">{r.would_loss}</td>
              <td className="px-3 py-2 text-right tabular-nums">{(r.win_rate || 0).toFixed(1)}</td>
              <td className="px-3 py-2 text-right tabular-nums">{(r.avg_r || 0).toFixed(2)}</td>
              <td className={cls(
                "px-3 py-2 text-right tabular-nums font-semibold",
                sumRTextClass(r.sum_r)
              )}>
                {r.sum_r > 0 ? "+" : ""}{(r.sum_r || 0).toFixed(2)}
              </td>
              <td className="px-3 py-2 text-muted-foreground">{r.dominant_blocker}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function UploadCard({ onUploaded }) {
  const [file, setFile] = useState(null);
  const [symbol, setSymbol] = useState("XAUUSD");
  const [timeframe, setTimeframe] = useState("PERIOD_M15");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    if (!file) { setErr("Seleziona un CSV"); return; }
    setBusy(true); setErr("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("symbol", symbol);
      fd.append("timeframe", timeframe);
      fd.append("source", "manual");
      await api.post("/analytics/strategy_stats/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setFile(null);
      onUploaded?.();
    } catch (e) {
      setErr(formatApiError(e?.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="p-5 space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold">
        <Upload className="h-4 w-4" /> Upload CSV from EA
      </div>
      <p className="text-xs text-muted-foreground">
        Il CSV viene generato da MQL5 in <code>MQL5/Files/NEXUS/nexus_stats_*.csv</code>
      </p>
      <div className="grid grid-cols-2 gap-2">
        <input
          data-testid="stats-upload-symbol"
          className="h-9 px-3 rounded-md border border-border bg-background text-sm"
          placeholder="Symbol" value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
        />
        <input
          data-testid="stats-upload-tf"
          className="h-9 px-3 rounded-md border border-border bg-background text-sm"
          placeholder="Timeframe" value={timeframe}
          onChange={(e) => setTimeframe(e.target.value)}
        />
      </div>
      <input
        data-testid="stats-upload-file"
        type="file" accept=".csv"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
        className="text-xs file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:bg-secondary file:text-secondary-foreground file:cursor-pointer"
      />
      {err && <div className="text-xs text-rose-500">{err}</div>}
      <button
        data-testid="stats-upload-submit"
        onClick={submit} disabled={busy || !file}
        className="h-9 px-4 rounded-md bg-sky-600 hover:bg-sky-700 text-white text-sm font-medium disabled:opacity-50"
      >
        {busy ? "Uploading..." : "Upload & analyze"}
      </button>
    </Card>
  );
}

// Healthbar color lookup — replaces a nested ternary chain
const HEALTH_BAR_BG = {
  emerald: "bg-emerald-500",
  amber: "bg-amber-500",
  rose: "bg-rose-500",
  orange: "bg-orange-500",
  sky: "bg-sky-500",
};
function healthBarClass(colorClass) {
  if (!colorClass) return "bg-slate-500";
  for (const [key, cls] of Object.entries(HEALTH_BAR_BG)) {
    if (colorClass.includes(key)) return cls;
  }
  return "bg-slate-500";
}

function HealthDistribution({ buckets }) {
  const total = HEALTH_STATES.reduce((s, k) => s + (buckets[k] || 0), 0) || 1;
  return (
    <Card className="p-5 space-y-3">
      <div className="text-sm font-semibold">Strategy Health Distribution</div>
      <div className="space-y-1.5">
        {HEALTH_STATES.map((k) => {
          const v = buckets[k] || 0;
          const pct = (v / total) * 100;
          return (
            <div key={k} className="flex items-center gap-2 text-xs" data-testid={`health-row-${k}`}>
              <HealthBadge state={k} />
              <div className="flex-1 h-2 rounded-full bg-secondary overflow-hidden">
                <div
                  className={cls("h-full transition-all", healthBarClass(HEALTH_COLOR[k]))}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <div className="w-8 tabular-nums text-right text-muted-foreground">{v}</div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function GlobalBlockersCard({ blockers }) {
  const entries = Object.entries(blockers || {})
    .filter(([k]) => k !== "NONE")
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  const max = entries[0]?.[1] || 1;
  return (
    <Card className="p-5 space-y-3">
      <div className="text-sm font-semibold">Global Blocker Funnel</div>
      <div className="space-y-1.5">
        {entries.map(([k, v]) => (
          <div key={k} className="flex items-center gap-2 text-xs">
            <div className="w-32 font-mono text-muted-foreground truncate">{k}</div>
            <div className="flex-1 h-2 rounded-full bg-secondary overflow-hidden">
              <div className="h-full bg-amber-500" style={{ width: `${(v / max) * 100}%` }} />
            </div>
            <div className="w-12 tabular-nums text-right">{v.toLocaleString()}</div>
          </div>
        ))}
        {entries.length === 0 && <div className="text-xs text-muted-foreground">No blocked attempts.</div>}
      </div>
    </Card>
  );
}

function HealthTable({ rows }) {
  const { open: openStrategy } = useStrategyHub();
  return (
    <Card className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="bg-secondary/60 sticky top-0 backdrop-blur-md z-10">
          <tr>
            <th className="text-left px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Strategy</th>
            <th className="text-left px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Family</th>
            <th className="text-left px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Health</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Called</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Setup</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Exec</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">PF</th>
            <th className="text-left px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Dominant Blocker</th>
            <th className="text-left px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const pft = pfTone(r.profit_factor);
            return (
              <tr key={r.name}
                  className="border-t border-border/60 hover:bg-primary/[0.04] transition-colors group"
                  data-testid={`health-row-strat-${r.name}`}>
                <td className="px-3 py-2.5 font-mono font-semibold">
                  <button onClick={() => openStrategy(r.name)}
                    data-testid={`strat-diag-open-${r.name}`}
                    className="text-left hover:text-primary hover:underline transition-colors">
                    {r.name}
                  </button>
                  {r.status_meta === "READY_FOR_BACKTEST" && (
                    <span className="ml-1.5 inline-flex items-center gap-0.5 text-[9px] text-primary">
                      <Sparkles className="h-2.5 w-2.5" /> RFB
                    </span>
                  )}
                </td>
                <td className="px-3 py-2.5"><FamilyBadge family={r.family} /></td>
                <td className="px-3 py-2.5"><HealthBadge state={r.health} /></td>
                <td className="px-3 py-2.5 text-right tabular-nums font-mono">{r.called?.toLocaleString()}</td>
                <td className="px-3 py-2.5 text-right tabular-nums font-mono">{r.setup?.toLocaleString()}</td>
                <td className="px-3 py-2.5 text-right tabular-nums font-mono">{r.executed?.toLocaleString()}</td>
                <HeatCell
                  tone={pft}
                  value={<span className="font-mono">{(r.profit_factor || 0).toFixed(2)}</span>}
                />
                <td className="px-3 py-2.5 text-muted-foreground font-mono text-[11px]">{r.dominant_blocker}</td>
                <td className="px-3 py-2.5 text-muted-foreground italic text-[11px]">{r.action}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}

function GenericTable({ rows, columns }) {
  return (
    <Card className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="bg-secondary/60 sticky top-0 backdrop-blur-md z-10">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={cls(
                "px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground",
                c.align === "right" ? "text-right" : "text-left"
              )}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.name || i}
                className="border-t border-border/60 hover:bg-primary/[0.04] transition-colors">
              {columns.map((c) => (
                <td key={c.key} className={cls(
                  "px-3 py-2.5",
                  c.align === "right" ? "text-right tabular-nums font-mono" : "font-mono"
                )}>
                  {c.render ? c.render(r[c.key], r) : (r[c.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

// Performance table — Bloomberg-style heatmap on WR/Expectancy/PF
function PerfTable({ rows }) {
  return (
    <Card className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="bg-secondary/60 sticky top-0 backdrop-blur-md z-10">
          <tr>
            <th className="text-left px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Strategy</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">W</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">L</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">BE</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Win %</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Expe (R)</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">PF</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Avg W (R)</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Avg L (R)</th>
            <th className="text-right px-3 py-2.5 text-[10px] uppercase tracking-wider font-bold text-muted-foreground">Hold (s)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const wrt = winrateTone(r.winrate_pct);
            const ext = expectancyTone(r.expectancy_R);
            const pft = pfTone(r.profit_factor);
            return (
              <tr key={r.name || i}
                  className="border-t border-border/60 hover:bg-primary/[0.04] transition-colors">
                <td className="px-3 py-2.5 font-mono font-semibold">{r.name}</td>
                <td className="px-3 py-2.5 text-right tabular-nums font-mono text-emerald-400">{r.wins || 0}</td>
                <td className="px-3 py-2.5 text-right tabular-nums font-mono text-rose-400">{r.losses || 0}</td>
                <td className="px-3 py-2.5 text-right tabular-nums font-mono text-muted-foreground">{r.breakeven || 0}</td>
                <HeatCell tone={wrt} value={<span className="font-mono">{(r.winrate_pct || 0).toFixed(1)}%</span>} />
                <HeatCell tone={ext} value={<span className="font-mono">{(r.expectancy_R || 0).toFixed(2)}</span>} />
                <HeatCell tone={pft} value={<span className="font-mono">{(r.profit_factor || 0).toFixed(2)}</span>} />
                <td className="px-3 py-2.5 text-right tabular-nums font-mono text-emerald-400/80">{(r.avg_R_win || 0).toFixed(2)}</td>
                <td className="px-3 py-2.5 text-right tabular-nums font-mono text-rose-400/80">{(r.avg_R_loss || 0).toFixed(2)}</td>
                <td className="px-3 py-2.5 text-right tabular-nums font-mono text-muted-foreground">{Math.round(r.avg_holding_sec || 0).toLocaleString()}</td>
              </tr>
            );
          })}
          {rows.length === 0 && (
            <tr>
              <td colSpan={10} className="px-3 py-10 text-center text-sm text-muted-foreground">
                No performance data yet — execute trades or upload the EA CSV.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </Card>
  );
}

const DETECTION_COLS = [
  { key: "name", label: "Strategy" },
  { key: "enabled", label: "Enabled", render: (v) => v ? "✓" : "—" },
  { key: "called", label: "Called", align: "right",
    render: (v) => (v || 0).toLocaleString() },
  { key: "setup", label: "Setup", align: "right",
    render: (v) => (v || 0).toLocaleString() },
  { key: "signals", label: "Signals", align: "right",
    render: (v) => (v || 0).toLocaleString() },
  { key: "setup_rate_pct", label: "Setup rate %", align: "right",
    render: (v) => `${(v || 0).toFixed(1)}%` },
  { key: "avg_score_base", label: "Avg score base", align: "right",
    render: (v) => (v || 0).toFixed(1) },
];

const GATE_COLS = [
  { key: "name", label: "Strategy" },
  { key: "blk_MTF",         label: "MTF",        align: "right" },
  { key: "blk_VELOCITY",    label: "Velocity",   align: "right" },
  { key: "blk_HTF",         label: "HTF",        align: "right" },
  { key: "blk_NEWS",        label: "News",       align: "right" },
  { key: "blk_SCORE_BELOW", label: "Score<",     align: "right" },
  { key: "blk_PROTECTIONS", label: "Prot.",      align: "right" },
  { key: "blk_PREFLIGHT",   label: "Preflight",  align: "right" },
  { key: "blk_SEND_FAILED", label: "Send fail",  align: "right" },
  { key: "blk_COOLDOWN",    label: "Cooldown",   align: "right" },
  { key: "blk_SPREAD",      label: "Spread",     align: "right" },
  { key: "dominant_blocker", label: "Dominant" },
];

const EXEC_COLS = [
  { key: "name", label: "Strategy" },
  { key: "executed", label: "Trades opened", align: "right" },
  { key: "sltp_invalid", label: "SL/TP invalid", align: "right" },
  { key: "order_fail", label: "Order send fail", align: "right" },
  { key: "avg_spread_pts", label: "Avg spread pts", align: "right",
    render: (v) => (v || 0).toFixed(1) },
  { key: "avg_score_final", label: "Avg score @entry", align: "right",
    render: (v) => (v || 0).toFixed(1) },
  { key: "avg_threshold", label: "Avg threshold", align: "right",
    render: (v) => (v || 0).toFixed(1) },
];

const PERF_COLS = [
  { key: "name", label: "Strategy" },
  { key: "wins", label: "W", align: "right" },
  { key: "losses", label: "L", align: "right" },
  { key: "breakeven", label: "BE", align: "right" },
  { key: "winrate_pct", label: "Win %", align: "right",
    render: (v) => `${(v || 0).toFixed(1)}%` },
  { key: "expectancy_R", label: "Expe (R)", align: "right",
    render: (v) => (v || 0).toFixed(2) },
  { key: "profit_factor", label: "PF", align: "right",
    render: (v) => (v || 0).toFixed(2) },
  { key: "avg_R_win", label: "Avg W (R)", align: "right",
    render: (v) => (v || 0).toFixed(2) },
  { key: "avg_R_loss", label: "Avg L (R)", align: "right",
    render: (v) => (v || 0).toFixed(2) },
  { key: "avg_holding_sec", label: "Hold (s)", align: "right",
    render: (v) => Math.round(v || 0).toLocaleString() },
];

export default function StrategyAnalyticsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [tab, setTab] = useState("health");
  const [symbol, setSymbol] = useState("");
  const [symbolOptions, setSymbolOptions] = useState([]);
  const [meta, setMeta] = useState(null);
  const [familyFilter, setFamilyFilter] = useState("ALL");

  const loadMeta = useCallback(async () => {
    try {
      const { data: m } = await api.get("/analytics/strategy_meta");
      setMeta(m);
    } catch (e) {
      // meta is optional — log so dev can spot real failures
      console.warn("[StrategyAnalyticsPage] loadMeta failed:", e?.message || e);
    }
  }, []);

  const loadSymbols = useCallback(async () => {
    try {
      const { data: d } = await api.get("/analytics/strategy_stats/symbols");
      setSymbolOptions(d.items || []);
      if (!symbol && d.items?.length) {
        // Auto-pick most recent ea_push, fallback to latest of any source
        const ea = d.items.find((x) => x.source === "ea_push");
        setSymbol((ea || d.items[0]).symbol);
      }
    } catch (e) {
      console.warn("[StrategyAnalyticsPage] loadSymbols failed:", e?.message || e);
    }
  }, [symbol]);

  const load = useCallback(async (sym) => {
    setLoading(true); setErr("");
    try {
      const target = sym !== undefined ? sym : symbol;
      const q = target ? `?symbol=${encodeURIComponent(target)}` : "";
      const { data: d } = await api.get(`/analytics/strategy_stats/latest${q}`);
      setData(d);
    } catch (e) {
      setErr(formatApiError(e?.response?.data?.detail) || "Errore caricamento");
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => { loadSymbols(); loadMeta(); }, [loadSymbols, loadMeta]);
  useEffect(() => { if (symbol) load(symbol); }, [symbol, load]);

  const downloadMarkdown = async () => {
    try {
      const q = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
      const r = await api.get(`/analytics/strategy_stats/markdown${q}`,
        { responseType: "blob" });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `NEXUS_strategy_report_${data?.symbol || "x"}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErr(formatApiError(e?.response?.data?.detail) || "Errore download");
    }
  };

  const sections = data?.sections || {};
  const metaByName = useMemo(() => {
    const m = {};
    (meta?.strategies || []).forEach((s) => { m[s.name] = s; });
    return m;
  }, [meta]);

  // Enrich health rows with family/status_meta from /analytics/strategy_meta when EA didn't provide them
  const allHealthRows = useMemo(() => (sections.health || []).map((r) => ({
    ...r,
    family: r.family || metaByName[r.name]?.family || "OTHER",
    status_meta: r.status_meta || metaByName[r.name]?.status || "UNKNOWN",
  })), [sections.health, metaByName]);

  const healthRows = useMemo(() => (
    familyFilter === "ALL"
      ? allHealthRows
      : allHealthRows.filter((r) => r.family === familyFilter)
  ), [allHealthRows, familyFilter]);

  const rows = data?.rows || [];

  const isEmpty = !data || data.empty || rows.length === 0;

  return (
    <div className="space-y-6 fade-in" data-testid="strategy-analytics-page">
      <Card className="p-6 lg:p-8 flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        <div>
          <div className="eyebrow flex items-center gap-1.5">
            <Activity className="h-3.5 w-3.5" /> Strategy Analytics
          </div>
          <h2 className="text-2xl font-semibold tracking-tight mt-1">
            Full lifecycle diagnostics
          </h2>
          <p className="text-sm text-muted-foreground mt-1.5">
            Detection → Gate → Execution → Performance → Health · per le <b>{meta?.total ?? 35}</b> strategie EA
            {meta?.families?.INSTITUTIONAL > 0 && (
              <span className="ml-2 inline-flex items-center gap-1 text-[10px] text-emerald-600">
                <Sparkles className="h-3 w-3" /> v2.0.7 +{meta.families.INSTITUTIONAL} INSTITUTIONAL
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            data-testid="stats-symbol-select"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="h-9 px-3 rounded-md border border-border bg-background text-sm w-40"
          >
            {symbolOptions.length === 0 && <option value="">No data</option>}
            {symbolOptions.map((o) => (
              <option key={o.symbol} value={o.symbol}>
                {o.symbol} · {o.source} ({o.count})
              </option>
            ))}
          </select>
          <button
            data-testid="stats-reload"
            onClick={() => load()} disabled={loading}
            className="h-9 px-4 rounded-md border border-border text-sm font-medium hover:bg-secondary/60 inline-flex items-center gap-1.5"
          >
            <RefreshCw className={cls("h-3.5 w-3.5", loading && "animate-spin")} />
            Reload
          </button>
          <button
            data-testid="stats-download-md"
            onClick={downloadMarkdown} disabled={isEmpty}
            className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50 inline-flex items-center gap-1.5 shadow-[0_0_14px_hsl(var(--primary)/0.3)] hover:brightness-110 active:scale-[0.98] transition-all"
          >
            <FileDown className="h-3.5 w-3.5" /> Report .md
          </button>
        </div>
      </Card>

      {data && !data.empty && (
        <div className="rounded-md border border-sky-500/30 bg-sky-500/5 px-4 py-2.5 text-xs flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="font-semibold text-sky-700 dark:text-sky-400">Snapshot:</span>
          <span><b>Symbol:</b> {data.symbol}</span>
          <span><b>TF:</b> {data.timeframe}</span>
          <span><b>Source:</b> <code className={cls("px-1.5 py-0.5 rounded text-[10px]",
            data.source === "ea_push" ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
                                       : "bg-amber-500/15 text-amber-700 dark:text-amber-400"
          )}>{data.source}</code></span>
          <span><b>Saved:</b> {data.created_at?.replace("T", " ").substring(0, 19)} UTC</span>
        </div>
      )}

      {err && (
        <div className="rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400 px-3 py-2 text-sm flex items-center gap-2">
          <AlertTriangle className="h-4 w-4" /> {err}
        </div>
      )}

      {isEmpty ? (
        <Card className="p-6 lg:p-10">
          <div className="text-center space-y-4">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-secondary">
              <Upload className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <div className="text-base font-semibold">Nessun report disponibile</div>
              <p className="text-sm text-muted-foreground mt-1">
                Carica un CSV generato dall&apos;EA (cartella MQL5/Files/NEXUS/) per vedere<br/>
                il funnel Detection → Execution e la classificazione Health di ogni strategia.
              </p>
            </div>
            <div className="max-w-md mx-auto pt-2">
              <UploadCard onUploaded={load} />
            </div>
          </div>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatTile label="Called" value={(data.total_called || 0).toLocaleString()} />
            <StatTile label="Setup" value={(data.total_setup || 0).toLocaleString()}
              hint={`${data.total_called ? ((data.total_setup / data.total_called) * 100).toFixed(1) : 0}% rate`} />
            <StatTile label="Executed" value={(data.total_executed || 0).toLocaleString()}
              hint={`${data.total_setup ? ((data.total_executed / data.total_setup) * 100).toFixed(1) : 0}% of setup`} />
            <StatTile label="Wins" value={data.total_wins || 0} color="text-emerald-600" />
            <StatTile label="Losses" value={data.total_losses || 0} color="text-rose-600" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <HealthDistribution buckets={data.buckets || {}} />
            <GlobalBlockersCard blockers={data.global_blockers || {}} />
            <UploadCard onUploaded={load} />
          </div>

          <div className="flex flex-wrap gap-2 border-b border-border">
            {SECTION_TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                data-testid={`stats-tab-${id}`}
                onClick={() => setTab(id)}
                className={cls(
                  "px-4 py-2 text-sm inline-flex items-center gap-1.5 border-b-2 -mb-px transition-colors",
                  tab === id
                    ? "border-sky-600 dark:border-sky-400 text-foreground font-semibold"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                )}
              >
                <Icon className="h-3.5 w-3.5" /> {label}
              </button>
            ))}
          </div>

          <div className="mt-2">
            {tab === "health" && (
              <>
                <div className="flex items-center gap-2 mb-3 flex-wrap" data-testid="family-filter-bar">
                  <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                    <Filter className="h-3 w-3" /> Family:
                  </span>
                  {FAMILY_OPTIONS.map((f) => (
                    <button
                      key={f.id}
                      data-testid={`family-chip-${f.id}`}
                      onClick={() => setFamilyFilter(f.id)}
                      className={cls(
                        "px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all active:scale-[0.97]",
                        familyFilter === f.id
                          ? "border-primary bg-primary/10 text-primary shadow-[0_0_12px_hsl(var(--primary)/0.25)]"
                          : "border-border text-muted-foreground hover:bg-secondary/60 hover:border-primary/30"
                      )}
                    >
                      {f.label}
                    </button>
                  ))}
                  {familyFilter !== "ALL" && (
                    <span className="text-[10px] text-muted-foreground ml-1">
                      {healthRows.length} / {allHealthRows.length} mostrate
                    </span>
                  )}
                </div>
                {tab === "health" && (() => {
                  const allNoData = healthRows.length > 0 &&
                    healthRows.every((r) => r.health === "NO_DATA_YET" || r.health === "NOT_CALLED");
                  if (allNoData) {
                    return (
                      <Card className="p-6 text-sm" data-testid="health-no-data-cta">
                        <div className="flex items-start gap-3">
                          <Sparkles className="h-5 w-5 text-sky-500 flex-shrink-0 mt-0.5" />
                          <div className="space-y-2">
                            <div className="font-semibold text-foreground">L&apos;EA non ha ancora esportato dati telemetrici</div>
                            <div className="text-muted-foreground">
                              Tutte le strategie sono in stato <code className="px-1 rounded bg-secondary text-[10px]">NO_DATA_YET</code>.
                              Per popolare la diagnostica:
                            </div>
                            <ol className="list-decimal list-inside text-muted-foreground space-y-1 ml-1">
                              <li>Compila l&apos;EA in MetaEditor (F7) e attaccalo a un chart attivo (XAUUSD M15 o BTCUSD H1)</li>
                              <li>Verifica che <code className="px-1 rounded bg-secondary text-[10px]">InpStatsEnable=true</code> e <code className="px-1 rounded bg-secondary text-[10px]">InpStatsPushToBackend=true</code></li>
                              <li>Aspetta 5 minuti — il primo CSV viene esportato a <code className="px-1 rounded bg-secondary text-[10px]">MQL5/Files/NEXUS/nexus_stats_*.csv</code></li>
                              <li>Ricarica questa pagina (Reload)</li>
                            </ol>
                          </div>
                        </div>
                      </Card>
                    );
                  }
                  return <HealthTable rows={healthRows} />;
                })()}
              </>
            )}
            {tab === "detection"   && <GenericTable rows={sections.detection || []}   columns={DETECTION_COLS} />}
            {tab === "gate"        && <GenericTable rows={sections.gate || []}        columns={GATE_COLS} />}
            {tab === "execution"   && <GenericTable rows={sections.execution || []}   columns={EXEC_COLS} />}
            {tab === "performance" && <PerfTable rows={sections.performance || []} />}
            {tab === "shadow"      && <ShadowSkippedTable symbol={symbol} />}
          </div>

          {data.best && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <Card className="p-4 border-emerald-500/30">
                <div className="text-[11px] uppercase tracking-wider text-emerald-600">Best</div>
                <div className="text-lg font-bold mt-1">{data.best.name}</div>
                <div className="text-xs text-muted-foreground">PF {data.best.pf?.toFixed(2)}</div>
              </Card>
              <Card className="p-4 border-rose-500/30">
                <div className="text-[11px] uppercase tracking-wider text-rose-600">Worst</div>
                <div className="text-lg font-bold mt-1">{data.worst?.name || "—"}</div>
                <div className="text-xs text-muted-foreground">PF {data.worst?.pf?.toFixed(2) || "—"}</div>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
}
