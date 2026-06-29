import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Library, Loader2, Search, Filter, Play, Lock, AlertCircle, Trophy, ArrowRightCircle, Zap } from "lucide-react";
import { toast } from "sonner";

function cn(...c) { return c.filter(Boolean).join(" "); }

const VARIANT_COLOR = {
  baseline:        "bg-slate-500/15 text-slate-300",
  be_1R:           "bg-sky-500/15 text-sky-300",
  trail_1_5atr:    "bg-sky-500/15 text-sky-300",
  "trail_1.5atr":  "bg-sky-500/15 text-sky-300",
  pyramid_1R:      "bg-emerald-500/15 text-emerald-300",
  pyramid_0_5R:    "bg-emerald-500/15 text-emerald-300",
  pyramid_aggr:    "bg-emerald-500/15 text-emerald-300",
  grid_safe:       "bg-cyan-500/15 text-cyan-300",
  grid_balanced:   "bg-amber-500/15 text-amber-300",
  grid_aggressive: "bg-rose-500/15 text-rose-300",
  "grid+be":       "bg-orange-500/15 text-orange-300",
};

export default function BacktestStrategyLibrary({ symbols, baseCfg, onApplyRow }) {
  const [symbol, setSymbol] = useState(baseCfg?.symbol || "XAUUSD");
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [filter, setFilter] = useState("");
  const [autoLock, setAutoLock] = useState(false);
  const [err, setErr] = useState("");

  const load = async (sym = symbol) => {
    try {
      const { data } = await api.get(`/backtest/strategy_library?symbol=${sym}`);
      setRows(data.rows || []);
    } catch (e) { setErr(e?.response?.data?.detail || e.message); }
  };

  useEffect(() => { load(symbol); /* eslint-disable-next-line */ }, [symbol]);

  const rebuild = async () => {
    setBusy(true); setErr(""); setProgress({ done: 0, total: 36 });
    try {
      const { data } = await api.post("/backtest/strategy_library/build",
        { symbol, timeframes: ["1d", "1h"] });
      setJobId(data.job_id);
    } catch (e) { setErr(e?.response?.data?.detail || e.message); setBusy(false); }
  };

  // Poll the build job
  useEffect(() => {
    if (!jobId) return;
    const it = setInterval(async () => {
      try {
        const { data } = await api.get(`/backtest/strategy_library/${jobId}`);
        setProgress({ done: data.progress, total: data.total });
        if (data.status === "done" || data.status === "failed") {
          clearInterval(it); setBusy(false); setJobId(null);
          if (data.status === "done") {
            toast.success(`Libreria ${symbol} rigenerata: ${(data.rows || []).length} preset`);
            load();
            // Auto-lock the best result if toggle is ON and the new best beats current
            if (autoLock && data.rows?.length) {
              const best = [...data.rows].sort(
                (a, b) => (b.metrics?.sharpe || 0) - (a.metrics?.sharpe || 0))[0];
              try {
                const current = await api.get("/backtest/locked_profile/all");
                const cur = (current.data.profiles || []).find((p) => p.symbol === symbol);
                const currentSharpe = cur?.metrics?.sharpe || 0;
                const newSharpe = best.metrics?.sharpe || 0;
                if (newSharpe > currentSharpe * 1.10) {
                  await api.post("/backtest/locked_profile", {
                    symbol: best.symbol,
                    timeframe: best.timeframe === "1d" ? "D1" : best.timeframe.toUpperCase(),
                    label: `Auto-Lock · ${best.strategy} · ${best.variant} (Sharpe ${best.metrics.sharpe})`,
                    base_cfg: {
                      symbol: best.symbol, period: "3y", interval: best.timeframe,
                      strategies: [best.strategy],
                      atr_sl_mult: best.atr_sl_mult, atr_tp_mult: best.atr_tp_mult,
                      min_score: 60, max_concurrent: 1, risk_pct: 1.0,
                      adx_min: 18, htf_bias: false, cooldown_bars: 3, daily_dd_cap: 5,
                      session_london: true, session_ny: true, session_asian: true,
                      initial_balance: 10000, htf_interval: "1d",
                    },
                    overrides: best.overrides, metrics: best.metrics,
                  });
                  toast.success(
                    `🚀 Auto-Lock attivato: ${best.strategy} (Sharpe ${best.metrics.sharpe} > prec ${currentSharpe})`);
                }
              } catch (e) { console.warn("auto-lock failed", e); }
            }
          } else {
            setErr(data.error || "Job failed");
          }
        }
      } catch { /* transient */ }
    }, 2000);
    return () => clearInterval(it);
  }, [jobId]);  // eslint-disable-line

  const filtered = filter
    ? rows.filter((r) => r.strategy.toLowerCase().includes(filter.toLowerCase())
                      || r.variant.toLowerCase().includes(filter.toLowerCase()))
    : rows;

  const lockProfile = async (r) => {
    try {
      await api.post("/backtest/locked_profile", {
        symbol: r.symbol, timeframe: r.timeframe === "1d" ? "D1" : r.timeframe.toUpperCase(),
        label: `Library · ${r.strategy} · ${r.variant} (Sharpe ${r.metrics.sharpe})`,
        base_cfg: {
          symbol: r.symbol, period: "3y", interval: r.timeframe,
          strategies: [r.strategy],
          atr_sl_mult: r.atr_sl_mult, atr_tp_mult: r.atr_tp_mult,
          min_score: 60, max_concurrent: 1, risk_pct: 1.0,
          adx_min: 18, htf_bias: false, cooldown_bars: 3, daily_dd_cap: 5,
          session_london: true, session_ny: true, session_asian: true,
          initial_balance: 10000, htf_interval: "1d",
        },
        overrides: r.overrides,
        metrics: r.metrics,
      });
      toast.success(`${r.strategy} su ${r.symbol} ${r.timeframe} ora è il Locked Profile attivo`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message);
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-6" data-testid="bt-library">
      <div className="xl:col-span-4 space-y-3">
        <div className="rounded-xl border border-border bg-card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Library className="h-5 w-5 text-cyan-400"/>
            <div className="font-bold tracking-tight">Strategy Library</div>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Per ogni simbolo viene generata la <strong>libreria delle 36 strategie</strong>: ognuna con il suo
            timeframe vincente e la gestione (grid/pyramid/baseline) più robusta. Ranking per Sharpe + DD.
          </p>

          <div className="grid grid-cols-1 gap-2">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Symbol</div>
              <select value={symbol} onChange={(e) => setSymbol(e.target.value)}
                data-testid="lib-symbol"
                className="w-full px-2 py-1.5 rounded-md bg-background border border-border text-sm">
                {(symbols && symbols.length ? symbols : ["XAUUSD", "EURUSD", "BTCUSD"]).map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Filtro</div>
              <div className="relative">
                <Search className="h-3.5 w-3.5 absolute left-2 top-2 text-muted-foreground"/>
                <input value={filter} onChange={(e) => setFilter(e.target.value)}
                  data-testid="lib-filter"
                  placeholder="strategia o variant..."
                  className="w-full pl-8 pr-2 py-1.5 rounded-md bg-background border border-border text-sm"/>
              </div>
            </div>
          </div>

          <div className="rounded-md border border-border bg-secondary/30 p-2 text-[11px] flex items-center justify-between">
            <span><span className="text-muted-foreground">Preset:</span> <b>{rows.length}</b>/36</span>
            <span><span className="text-muted-foreground">Visibili:</span> <b>{filtered.length}</b></span>
          </div>

          <button onClick={rebuild} disabled={busy}
            data-testid="lib-rebuild"
            className={cn("w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm font-semibold",
              "bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white")}>
            {busy ? <><Loader2 className="h-4 w-4 animate-spin"/>Rigenero {progress.done}/{progress.total}...</> :
                    <><Play className="h-4 w-4"/>Rigenera Library ({symbol})</>}
          </button>

          <label className="flex items-center gap-2 px-3 py-2 rounded-md border border-border bg-background cursor-pointer hover:bg-secondary/40 transition-all"
            data-testid="lib-autolock-row">
            <input type="checkbox" checked={autoLock} onChange={(e) => setAutoLock(e.target.checked)}
              data-testid="lib-autolock-toggle" className="accent-violet-500"/>
            <Zap className="h-3.5 w-3.5 text-violet-400"/>
            <div className="flex-1 text-[11px]">
              <div className="font-semibold">Auto-Lock best</div>
              <div className="text-muted-foreground text-[10px]">Se il nuovo best batte di +10% il Locked Profile attivo, fa lock automatico.</div>
            </div>
          </label>

          {busy && (
            <div className="h-2 bg-secondary/40 rounded-full overflow-hidden">
              <div className="h-full bg-cyan-500 transition-all"
                style={{ width: `${progress.total ? (progress.done / progress.total) * 100 : 0}%` }}/>
            </div>
          )}

          {err && (
            <div className="flex items-start gap-2 p-2 rounded-md bg-rose-500/10 text-rose-400 text-xs">
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0"/><span>{err}</span>
            </div>
          )}
        </div>
      </div>

      <div className="xl:col-span-8 space-y-3">
        {rows.length === 0 && !busy && (
          <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted-foreground">
            <Library className="h-12 w-12 mx-auto mb-3 opacity-30"/>
            Nessun preset salvato per <b>{symbol}</b>. Click <strong>Rigenera Library</strong>.
          </div>
        )}

        {rows.length > 0 && (
          <div className="rounded-xl border border-border bg-card overflow-hidden" data-testid="lib-table">
            <div className="px-4 py-2 border-b border-border bg-secondary/30 text-xs uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Trophy className="h-3.5 w-3.5"/> {symbol} · 36 strategie · best TF × best management
            </div>
            <div className="overflow-x-auto max-h-[680px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="bg-secondary/30 sticky top-0">
                  <tr className="text-left">
                    <th className="px-2 py-2 font-mono uppercase">#</th>
                    <th className="px-2 py-2 font-mono uppercase">Strategy</th>
                    <th className="px-2 py-2 font-mono uppercase">TF</th>
                    <th className="px-2 py-2 font-mono uppercase">Best Mgmt</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">n</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">WR%</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">PF</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">Sharpe</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">DD%</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">Ret%</th>
                    <th className="px-2 py-2 font-mono uppercase text-center">Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r, i) => {
                    const m = r.metrics || {};
                    return (
                      <tr key={`${r.strategy}-${r.timeframe}`} className="border-t border-border/60 hover:bg-secondary/20" data-testid={`lib-row-${r.strategy}`}>
                        <td className="px-2 py-2 font-mono text-cyan-400 font-bold">{i + 1}</td>
                        <td className="px-2 py-2 font-mono font-semibold">{r.strategy}</td>
                        <td className="px-2 py-2 font-mono">
                          <span className={cn("inline-block px-1.5 py-0.5 rounded text-[10px]",
                            r.timeframe === "1d" ? "bg-emerald-500/20 text-emerald-300" :
                            r.timeframe === "1h" ? "bg-amber-500/20 text-amber-300" :
                                                    "bg-rose-500/20 text-rose-300")}>{r.timeframe}</span>
                        </td>
                        <td className="px-2 py-2 font-mono">
                          <span className={cn("inline-block px-1.5 py-0.5 rounded text-[10px]",
                            VARIANT_COLOR[r.variant] || "bg-secondary/40 text-muted-foreground")}>{r.variant}</span>
                        </td>
                        <td className="px-2 py-2 font-mono text-right">{m.n_trades ?? "-"}</td>
                        <td className="px-2 py-2 font-mono text-right">{m.win_rate_pct ?? "-"}</td>
                        <td className="px-2 py-2 font-mono text-right">{m.profit_factor ?? "-"}</td>
                        <td className="px-2 py-2 font-mono text-right text-cyan-300">{m.sharpe ?? "-"}</td>
                        <td className="px-2 py-2 font-mono text-right text-rose-400">{m.max_dd_pct ?? "-"}</td>
                        <td className="px-2 py-2 font-mono text-right text-emerald-400">{m.total_return_pct ?? "-"}</td>
                        <td className="px-2 py-2 text-center">
                          <div className="flex items-center gap-1 justify-center">
                            {onApplyRow && (
                              <button onClick={() => { onApplyRow(r); toast.info(`${r.strategy} caricata nel tab Run`); }}
                                data-testid={`lib-apply-${r.strategy}`}
                                title="Apply to Backtest Run"
                                className="px-1.5 py-1 rounded text-[10px] uppercase tracking-wider bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 inline-flex items-center gap-1">
                                <ArrowRightCircle className="h-3 w-3"/>Apply
                              </button>
                            )}
                            <button onClick={() => lockProfile(r)}
                              data-testid={`lib-lock-${r.strategy}`}
                              title="Set as Locked Profile (EA will pull on next OnInit)"
                              className="px-1.5 py-1 rounded text-[10px] uppercase tracking-wider bg-violet-500/10 hover:bg-violet-500/20 text-violet-400 border border-violet-500/30 inline-flex items-center gap-1">
                              <Lock className="h-3 w-3"/>Lock
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
