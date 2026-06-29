import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { Wand2, Loader2, Trophy, AlertCircle, Sparkles, Play, X, Lock, Check } from "lucide-react";
import { toast } from "sonner";

function cn(...c) { return c.filter(Boolean).join(" "); }

// Sensible default ranges for the most-impactful EA parameters
const PARAM_PRESETS = {
  atr_sl_mult:        { label: "ATR × SL",       defaults: [1.2, 1.5, 1.8, 2.1, 2.5] },
  atr_tp_mult:        { label: "ATR × TP",       defaults: [2.0, 2.5, 3.0, 3.5, 4.0] },
  min_score:          { label: "Min Score",      defaults: [55, 60, 65, 70, 75] },
  adx_min:            { label: "ADX min",        defaults: [0, 15, 18, 22, 25] },
  risk_pct:           { label: "Rischio %",      defaults: [0.5, 1.0, 1.5, 2.0] },
  cooldown_bars:      { label: "Cooldown bars",  defaults: [0, 2, 4, 6] },
  breakeven_R:        { label: "Breakeven R",    defaults: [0, 0.5, 1.0, 1.5] },
  trailing_atr_mult:  { label: "Trail ATR×",     defaults: [0, 1.0, 1.5, 2.0] },
};

const OBJECTIVES = [
  { v: "sharpe",           l: "Sharpe Ratio"  },
  { v: "profit_factor",    l: "Profit Factor" },
  { v: "total_return_pct", l: "Total Return %"},
];

export default function BacktestOptimizer({ baseCfg }) {
  const [enabledParams, setEnabledParams] = useState({
    atr_sl_mult: true, atr_tp_mult: true, min_score: true, adx_min: false,
    risk_pct: false, cooldown_bars: false, breakeven_R: false, trailing_atr_mult: false,
  });
  const [objective, setObjective] = useState("sharpe");
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [savingIdx, setSavingIdx] = useState(null);
  const [savedIdx, setSavedIdx] = useState(null);
  const pollRef = useRef(null);

  const activeKeys = Object.keys(enabledParams).filter((k) => enabledParams[k]);
  const totalCombos = activeKeys.length
    ? activeKeys.reduce((acc, k) => acc * PARAM_PRESETS[k].defaults.length, 1)
    : 0;

  const start = async () => {
    if (!activeKeys.length) { setError("Seleziona almeno un parametro da ottimizzare."); return; }
    if (totalCombos > 500) { setError(`Troppe combinazioni (${totalCombos}). Massimo 500.`); return; }
    setError("");
    const grid = {};
    activeKeys.forEach((k) => { grid[k] = PARAM_PRESETS[k].defaults; });
    try {
      const { data } = await api.post("/backtest/optimize", {
        base: baseCfg, grid, objective, max_runs: 500, walk_forward: true,
      });
      setJobId(data.job_id);
      setStatus({ status: "queued", progress: 0, total: data.total });
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    }
  };

  const cancel = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    setJobId(null); setStatus(null);
  };

  // Poll job status
  useEffect(() => {
    if (!jobId) return;
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get(`/backtest/optimize/${jobId}`);
        setStatus(data);
        if (data.status === "done" || data.status === "failed") {
          clearInterval(pollRef.current); pollRef.current = null;
        }
      } catch { /* ignore transient */ }
    }, 1500);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [jobId]);

  const pct = status?.total ? Math.round((status.progress / status.total) * 100) : 0;

  const saveAsLocked = async (idx) => {
    const r = status?.top_results?.[idx];
    if (!r) return;
    setSavingIdx(idx);
    try {
      const payload = {
        symbol: baseCfg.symbol,
        timeframe: baseCfg.interval === "1d" ? "D1" :
                   baseCfg.interval === "4h" ? "H4" :
                   baseCfg.interval === "1h" ? "H1" :
                   baseCfg.interval === "30m" ? "M30" :
                   baseCfg.interval === "15m" ? "M15" :
                   baseCfg.interval.toUpperCase(),
        base_cfg: baseCfg,
        overrides: r.overrides,
        metrics: r.metrics,
        test_metrics: r.test_metrics || null,
        label: `Auto-Optimizer #${idx + 1} · ${baseCfg.symbol} ${baseCfg.interval} · ` +
               `PF ${r.metrics?.profit_factor} / DD ${r.metrics?.max_dd_pct}%`,
      };
      await api.post("/backtest/locked_profile", payload);
      setSavedIdx(idx);
      toast.success(`Profilo #${idx + 1} salvato. L'EA lo userà al prossimo OnInit().`);
    } catch (e) {
      toast.error(`Errore: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setSavingIdx(null);
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-6" data-testid="bt-optimizer">
      {/* LEFT: setup */}
      <div className="xl:col-span-5 space-y-3">
        <div className="rounded-xl border border-border bg-card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Wand2 className="h-5 w-5 text-violet-400"/>
            <div className="font-bold tracking-tight">AI Auto-Optimizer</div>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Il Coach esegue un <strong>grid search</strong> sui parametri selezionati e poi rivalida i top-10 su un set
            <strong> walk-forward</strong> (70% train / 30% test) per evitare overfitting. Alla fine Claude analizza i
            risultati e suggerisce la combinazione più robusta.
          </p>

          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Parametri da ottimizzare</div>
            <div className="space-y-1.5">
              {Object.entries(PARAM_PRESETS).map(([key, p]) => (
                <label key={key} className={cn("flex items-center gap-2 px-3 py-2 rounded-md border cursor-pointer transition-all",
                  enabledParams[key] ? "border-violet-500/50 bg-violet-500/5" : "border-border hover:border-border/80")}>
                  <input type="checkbox" checked={enabledParams[key]}
                    onChange={(e) => setEnabledParams((s) => ({...s, [key]: e.target.checked}))}
                    data-testid={`opt-param-${key}`} className="accent-violet-500"/>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium">{p.label}</div>
                    <div className="text-[10px] text-muted-foreground font-mono">
                      {p.defaults.join(" · ")}
                    </div>
                  </div>
                  <div className="text-[10px] text-muted-foreground">×{p.defaults.length}</div>
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-2">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Obiettivo</div>
              <select value={objective} onChange={(e) => setObjective(e.target.value)}
                className="w-full px-2 py-1.5 rounded-md bg-background border border-border text-sm" data-testid="opt-objective">
                {OBJECTIVES.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
              </select>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Combinazioni</div>
              <div className={cn("px-2 py-1.5 rounded-md border text-sm font-mono",
                totalCombos > 500 ? "border-rose-500/50 bg-rose-500/10 text-rose-400"
                                  : "border-border bg-background")} data-testid="opt-total">
                {totalCombos}
              </div>
            </div>
          </div>

          {!jobId && (
            <button onClick={start} disabled={!activeKeys.length}
              className={cn("w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm font-semibold transition-all",
                "bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white")} data-testid="opt-start">
              <Play className="h-4 w-4"/> Avvia Optimization
            </button>
          )}
          {jobId && status?.status !== "done" && status?.status !== "failed" && (
            <button onClick={cancel}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm font-semibold bg-rose-600/80 hover:bg-rose-500/80 text-white" data-testid="opt-cancel">
              <X className="h-4 w-4"/> Interrompi
            </button>
          )}
          {error && (
            <div className="flex items-start gap-2 p-2 rounded-md bg-rose-500/10 text-rose-400 text-xs" data-testid="opt-error">
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0"/><span>{error}</span>
            </div>
          )}
        </div>

        {/* Progress card */}
        {status && (
          <div className="rounded-xl border border-border bg-card p-4 space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-xs uppercase tracking-wider text-muted-foreground">Job</div>
              <div className={cn("text-[10px] font-mono uppercase px-2 py-0.5 rounded",
                status.status === "done"    ? "bg-emerald-500/10 text-emerald-400" :
                status.status === "failed"  ? "bg-rose-500/10 text-rose-400" :
                                              "bg-amber-500/10 text-amber-400")}>{status.status}</div>
            </div>
            <div className="text-sm font-mono">{status.progress || 0}/{status.total || "?"} combinazioni</div>
            <div className="h-2 bg-secondary/40 rounded-full overflow-hidden">
              <div className={cn("h-full transition-all",
                status.status === "failed" ? "bg-rose-500" : "bg-violet-500")}
                style={{ width: `${pct}%` }}/>
            </div>
            {status.error && (
              <div className="text-[11px] text-rose-400 pt-1" data-testid="opt-job-error">{status.error}</div>
            )}
          </div>
        )}
      </div>

      {/* RIGHT: results */}
      <div className="xl:col-span-7 space-y-3">
        {(!status?.top_results?.length) && (
          <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted-foreground" data-testid="opt-empty">
            <Trophy className="h-12 w-12 mx-auto mb-3 opacity-30"/>
            Scegli i parametri a sinistra e lancia l&apos;optimizer. I top-10 risultati appariranno qui.
          </div>
        )}

        {status?.coach_summary && (
          <div className="rounded-xl border border-violet-500/30 bg-violet-500/5 p-4" data-testid="opt-coach-summary">
            <div className="flex items-center gap-2 text-violet-400 text-xs uppercase tracking-wider mb-2">
              <Sparkles className="h-3.5 w-3.5"/>Coach Analysis
            </div>
            <div className="text-sm leading-relaxed whitespace-pre-wrap">{status.coach_summary}</div>
          </div>
        )}

        {status?.top_results?.length > 0 && (
          <div className="rounded-xl border border-border bg-card overflow-hidden" data-testid="opt-results-table">
            <div className="px-4 py-2 border-b border-border bg-secondary/30 text-xs uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Trophy className="h-3.5 w-3.5"/>Top 10 risultati (train) + walk-forward test
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-secondary/30">
                  <tr className="text-left">
                    <th className="px-2 py-2 font-mono uppercase">#</th>
                    <th className="px-2 py-2 font-mono uppercase">Parametri</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">Trade</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">PF</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">Sharpe</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">DD %</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">Ret %</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">Test PF</th>
                    <th className="px-2 py-2 font-mono uppercase text-center">Lock</th>
                  </tr>
                </thead>
                <tbody>
                  {status.top_results.map((r, i) => (
                    <tr key={i} className="border-t border-border/60 hover:bg-secondary/20">
                      <td className="px-2 py-2 font-mono text-violet-400 font-bold">{i + 1}</td>
                      <td className="px-2 py-2 font-mono text-[11px]">
                        {Object.entries(r.overrides).map(([k, v]) => (
                          <span key={k} className="inline-block px-1.5 py-0.5 mr-1 mb-0.5 rounded bg-secondary/40">
                            {k.replace(/_/g, " ")}: <b>{v}</b>
                          </span>
                        ))}
                      </td>
                      <td className="px-2 py-2 font-mono text-right">{r.metrics?.n_trades ?? "-"}</td>
                      <td className="px-2 py-2 font-mono text-right">{r.metrics?.profit_factor ?? "-"}</td>
                      <td className="px-2 py-2 font-mono text-right">{r.metrics?.sharpe ?? "-"}</td>
                      <td className="px-2 py-2 font-mono text-right text-rose-400">{r.metrics?.max_dd_pct ?? "-"}</td>
                      <td className="px-2 py-2 font-mono text-right text-emerald-400">{r.metrics?.total_return_pct ?? "-"}</td>
                      <td className="px-2 py-2 font-mono text-right text-cyan-400">
                        {r.test_metrics?.profit_factor ?? "—"}
                      </td>
                      <td className="px-2 py-2 text-center">
                        <button onClick={() => saveAsLocked(i)} disabled={savingIdx !== null}
                          data-testid={`opt-lock-${i}`}
                          className={cn("px-2 py-1 rounded text-[10px] uppercase tracking-wider transition-all flex items-center gap-1",
                            savedIdx === i ? "bg-emerald-500/20 text-emerald-400" :
                            savingIdx === i ? "bg-amber-500/20 text-amber-400" :
                            "bg-violet-500/10 hover:bg-violet-500/20 text-violet-400 border border-violet-500/30")}>
                          {savedIdx === i ? <><Check className="h-3 w-3"/>OK</> :
                           savingIdx === i ? <><Loader2 className="h-3 w-3 animate-spin"/>...</> :
                           <><Lock className="h-3 w-3"/>Lock</>}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {status.status === "done" && (
              <div className="px-4 py-2 border-t border-border bg-secondary/30 text-[11px] text-muted-foreground flex items-center gap-1">
                <Loader2 className="h-3 w-3 hidden"/>
                Walk-forward test PF in cyan: se è vicino al train PF, il setup è <strong>robusto</strong>.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
