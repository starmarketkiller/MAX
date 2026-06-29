import { useState } from "react";
import api from "@/lib/api";
import { Brain, Loader2, AlertCircle, TrendingUp, Play, Trophy, GitMerge, Pyramid, Activity, Clock } from "lucide-react";
import { toast } from "sonner";

function cn(...c) { return c.filter(Boolean).join(" "); }

const VARIANT_COLOR = {
  baseline:  "bg-slate-500/10 text-slate-300 border-slate-500/30",
  pyramid:   "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  grid:      "bg-amber-500/15 text-amber-300 border-amber-500/30",
  grid_safe: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
};

const VARIANT_ICON = {
  baseline:  Activity, pyramid: Pyramid, grid: GitMerge, grid_safe: GitMerge,
};

export default function BacktestManagementReport({ baseCfg }) {
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState(null);
  const [mtf, setMtf] = useState(null);
  const [err, setErr] = useState("");
  const [view, setView] = useState("mgmt");   // 'mgmt' | 'multi_tf'

  const runMgmt = async () => {
    setBusy(true); setErr(""); setData(null);
    try {
      const { data } = await api.post("/backtest/management_report", {
        symbol: baseCfg.symbol, period: baseCfg.period, interval: baseCfg.interval,
        strategies: baseCfg.strategies, risk_pct: baseCfg.risk_pct,
        atr_sl_mult: baseCfg.atr_sl_mult, atr_tp_mult: baseCfg.atr_tp_mult,
        min_score: baseCfg.min_score, htf_bias: baseCfg.htf_bias,
        session_london: baseCfg.session_london, session_ny: baseCfg.session_ny,
        session_asian: baseCfg.session_asian,
      });
      setData(data);
      toast.success(`Analisi completata: ${data.n_strategies} strategie × 12 varianti`);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally { setBusy(false); }
  };

  const runMultiTf = async () => {
    setBusy(true); setErr(""); setMtf(null);
    try {
      const top = (baseCfg.strategies || []).slice(0, 12);   // limit for speed
      const { data } = await api.post("/backtest/multi_tf_report", {
        symbol: baseCfg.symbol,
        strategies: top.length ? top : null,
        timeframes: ["1d", "1h", "15m"],
        atr_sl_mult: baseCfg.atr_sl_mult, atr_tp_mult: baseCfg.atr_tp_mult,
        min_score: baseCfg.min_score,
      });
      setMtf(data);
      toast.success(`Multi-TF: ${data.rows.length} righe (${data.timeframes.join(" · ")})`);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally { setBusy(false); }
  };

  const top = (data?.per_strategy || [])
    .filter((r) => r.best_metrics?.n_trades > 0)
    .sort((a, b) => (b.best_metrics.sharpe || 0) - (a.best_metrics.sharpe || 0));

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-6" data-testid="bt-mgmt-report">
      <div className="xl:col-span-4 space-y-3">
        <div className="rounded-xl border border-border bg-card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-fuchsia-400"/>
            <div className="font-bold tracking-tight">Best Management per Strategy</div>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Esegue 4 varianti di gestione (<strong>baseline · pyramid · grid · grid_safe</strong>) su <strong>ogni strategia</strong>
            in isolamento. Il Coach Claude analizza il risultato e dice quale gestione si adatta a quale strategia.
          </p>
          <div className="rounded-md border border-border bg-secondary/40 p-2 text-[11px] font-mono">
            <div className="text-muted-foreground mb-1">Config attiva (dal tab Run):</div>
            <div>Symbol: <b>{baseCfg.symbol}</b> · Period: <b>{baseCfg.period}</b> · TF: <b>{baseCfg.interval}</b></div>
            <div>SL×{baseCfg.atr_sl_mult} TP×{baseCfg.atr_tp_mult} Score≥{baseCfg.min_score}</div>
          </div>
          <button onClick={view === "mgmt" ? runMgmt : runMultiTf} disabled={busy}
            data-testid="mgmt-run"
            className={cn("w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md text-sm font-semibold",
              "bg-fuchsia-600 hover:bg-fuchsia-500 disabled:opacity-50 text-white")}>
            {busy ? <><Loader2 className="h-4 w-4 animate-spin"/>Calcolo...</> :
              view === "mgmt" ? <><Play className="h-4 w-4"/>Analizza Mgmt (12 varianti)</> :
                                <><Clock className="h-4 w-4"/>Multi-TF (1d · 1h · 15m)</>}
          </button>
          <div className="flex gap-1 p-0.5 bg-secondary/40 rounded-md text-[10px]">
            <button onClick={() => setView("mgmt")} type="button" data-testid="mgmt-view-mgmt"
              className={cn("flex-1 px-2 py-1 rounded transition-all", view === "mgmt" ? "bg-background shadow-sm" : "text-muted-foreground")}>
              Mgmt 12-variants
            </button>
            <button onClick={() => setView("multi_tf")} type="button" data-testid="mgmt-view-multitf"
              className={cn("flex-1 px-2 py-1 rounded transition-all", view === "multi_tf" ? "bg-background shadow-sm" : "text-muted-foreground")}>
              Multi-Timeframe
            </button>
          </div>
          {err && (
            <div className="flex items-start gap-2 p-2 rounded-md bg-rose-500/10 text-rose-400 text-xs">
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0"/><span>{err}</span>
            </div>
          )}
        </div>

        {data && (
          <div className="rounded-xl border border-fuchsia-500/30 bg-fuchsia-500/5 p-4" data-testid="mgmt-coach-summary">
            <div className="flex items-center gap-2 text-fuchsia-400 text-xs uppercase tracking-wider mb-2">
              <Brain className="h-3.5 w-3.5"/>Coach Analysis
            </div>
            <div className="text-sm leading-relaxed whitespace-pre-wrap">{data.coach_summary}</div>
          </div>
        )}
      </div>

      <div className="xl:col-span-8 space-y-3">
        {!data && !busy && (
          <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted-foreground">
            <Brain className="h-12 w-12 mx-auto mb-3 opacity-30"/>
            Click <strong>Analizza tutte le strategie</strong> per scoprire quale gestione (grid / pyramid / baseline) si adatta a ogni strategia.
          </div>
        )}
        {busy && (
          <div className="rounded-xl border border-border p-12 text-center">
            <Loader2 className="h-12 w-12 mx-auto mb-3 animate-spin text-fuchsia-500"/>
            <div className="text-muted-foreground">Sto eseguendo {(baseCfg.strategies?.length || 36) * 4} backtest...</div>
            <div className="text-xs text-muted-foreground/60 mt-2">~30 secondi su 3 anni daily</div>
          </div>
        )}
        {top.length > 0 && view === "mgmt" && (
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="px-4 py-2 border-b border-border bg-secondary/30 text-xs uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Trophy className="h-3.5 w-3.5"/> Best variant per strategy · ordinato per Sharpe
            </div>
            <div className="overflow-x-auto max-h-[640px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="bg-secondary/30 sticky top-0">
                  <tr className="text-left">
                    <th className="px-2 py-2 font-mono uppercase">#</th>
                    <th className="px-2 py-2 font-mono uppercase">Strategy</th>
                    <th className="px-2 py-2 font-mono uppercase">Best Mgmt</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">n</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">WR%</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">PF</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">Sharpe</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">DD%</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">Ret%</th>
                  </tr>
                </thead>
                <tbody>
                  {top.map((r, i) => {
                    const Icon = VARIANT_ICON[r.best_variant] || Activity;
                    const m = r.best_metrics;
                    return (
                      <tr key={r.strategy} className="border-t border-border/60 hover:bg-secondary/20" data-testid={`mgmt-row-${r.strategy}`}>
                        <td className="px-2 py-2 font-mono text-fuchsia-400 font-bold">{i + 1}</td>
                        <td className="px-2 py-2 font-mono font-semibold">{r.strategy}</td>
                        <td className="px-2 py-2">
                          <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-mono uppercase tracking-wider",
                            VARIANT_COLOR[r.best_variant] || "")}>
                            <Icon className="h-3 w-3"/>{r.best_variant}
                          </span>
                        </td>
                        <td className="px-2 py-2 font-mono text-right">{m.n_trades}</td>
                        <td className="px-2 py-2 font-mono text-right">{m.win_rate_pct}</td>
                        <td className="px-2 py-2 font-mono text-right">{m.profit_factor}</td>
                        <td className="px-2 py-2 font-mono text-right text-fuchsia-300">{m.sharpe}</td>
                        <td className="px-2 py-2 font-mono text-right text-rose-400">{m.max_dd_pct}</td>
                        <td className="px-2 py-2 font-mono text-right text-emerald-400">{m.total_return_pct}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {mtf && view === "multi_tf" && mtf.rows?.length > 0 && (
          <div className="rounded-xl border border-border bg-card overflow-hidden" data-testid="mtf-table">
            <div className="px-4 py-2 border-b border-border bg-secondary/30 text-xs uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Clock className="h-3.5 w-3.5"/> {mtf.symbol} · Strategia × Timeframe · {mtf.timeframes.join(" · ")}
            </div>
            <div className="overflow-x-auto max-h-[640px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="bg-secondary/30 sticky top-0">
                  <tr className="text-left">
                    <th className="px-2 py-2 font-mono uppercase">#</th>
                    <th className="px-2 py-2 font-mono uppercase">Strategy</th>
                    <th className="px-2 py-2 font-mono uppercase">TF</th>
                    <th className="px-2 py-2 font-mono uppercase">Variant</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">n</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">WR%</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">PF</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">Sharpe</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">DD%</th>
                    <th className="px-2 py-2 font-mono uppercase text-right">Ret%</th>
                  </tr>
                </thead>
                <tbody>
                  {mtf.rows.map((r, i) => (
                    <tr key={i} className="border-t border-border/60 hover:bg-secondary/20" data-testid={`mtf-row-${i}`}>
                      <td className="px-2 py-2 font-mono text-cyan-400 font-bold">{i + 1}</td>
                      <td className="px-2 py-2 font-mono font-semibold">{r.strategy}</td>
                      <td className="px-2 py-2 font-mono">
                        <span className={cn("inline-block px-1.5 py-0.5 rounded text-[10px]",
                          r.timeframe === "1d"  ? "bg-emerald-500/20 text-emerald-300" :
                          r.timeframe === "1h"  ? "bg-amber-500/20 text-amber-300" :
                                                  "bg-rose-500/20 text-rose-300")}>{r.timeframe}</span>
                      </td>
                      <td className="px-2 py-2 font-mono text-[10px] text-muted-foreground">{r.variant}</td>
                      <td className="px-2 py-2 font-mono text-right">{r.n_trades}</td>
                      <td className="px-2 py-2 font-mono text-right">{r.win_rate_pct}</td>
                      <td className="px-2 py-2 font-mono text-right">{r.profit_factor}</td>
                      <td className="px-2 py-2 font-mono text-right text-cyan-400">{r.sharpe}</td>
                      <td className="px-2 py-2 font-mono text-right text-rose-400">{r.max_dd_pct}</td>
                      <td className="px-2 py-2 font-mono text-right text-emerald-400">{r.total_return_pct}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
