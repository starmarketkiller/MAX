import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  X, Power, Gauge, FlaskConical, Activity, TrendingUp, Save, AlertTriangle, Sparkles,
} from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { cls, fmtMoney, fmtPct, POS_TEXT, NEG_TEXT } from "@/pages/dashboard/shared";

function Stat({ label, value, tone }) {
  const toneCls = tone === "pos" ? POS_TEXT : tone === "neg" ? NEG_TEXT : "text-foreground";
  return (
    <div className="rounded-lg border border-border bg-secondary/30 px-3 py-2">
      <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-semibold">{label}</div>
      <div className={cls("text-sm font-mono tabular mt-0.5", toneCls)}>{value}</div>
    </div>
  );
}

// Vista unica per strategia: stato live, metriche reali + rischio, miglior
// config backtest, diagnostica e ultimi trade. Azioni cross-sezione.
export default function StrategyDrawer({ name, onClose }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [riskInput, setRiskInput] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setErr(null);
    try {
      const { data: d } = await api.get(`/strategies/${encodeURIComponent(name)}/overview`);
      setData(d);
      setRiskInput(d?.risk_mult != null ? String(d.risk_mult) : "");
    } catch (e) { setErr(formatApiError(e)); } finally { setLoading(false); }
  }, [name]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const toggleEnabled = async () => {
    if (!data) return;
    setBusy(true); setErr(null);
    try {
      await api.post("/coach/apply_action", {
        type: data.enabled ? "disable_strategy" : "enable_strategy", name,
      });
      await load();
    } catch (e) { setErr(formatApiError(e)); } finally { setBusy(false); }
  };

  const saveRisk = async () => {
    setBusy(true); setErr(null);
    try {
      const v = riskInput === "" ? null : parseFloat(riskInput);
      await api.post("/strategies/risk_manual", { overrides: { [name]: v } });
      await load();
    } catch (e) { setErr(formatApiError(e)); } finally { setBusy(false); }
  };

  const live = data?.live;
  const bt = data?.backtest_best;

  return (
    <div className="fixed inset-0 z-[70] bg-black/60 backdrop-blur-md" onClick={onClose} data-testid="strategy-drawer">
      <aside
        onClick={(e) => e.stopPropagation()}
        className="absolute right-0 top-0 h-full w-full max-w-lg cockpit-card border-l border-border shadow-[0_0_60px_-20px_hsl(var(--primary)/0.5)] overflow-y-auto rounded-none">
        {/* Header */}
        <div className="p-6 border-b border-border flex items-start justify-between gap-4 sticky top-0 bg-card/80 backdrop-blur-xl z-10">
          <div>
            <div className="eyebrow flex items-center gap-1.5"><Activity className="h-3.5 w-3.5" /> Strategy Hub</div>
            <h2 className="font-bold text-2xl tracking-tight mt-1">{name}</h2>
            <div className={cls("text-xs mt-1 font-semibold", data?.enabled ? POS_TEXT : NEG_TEXT)}>
              {data?.enabled ? "● Attiva" : "○ Disattivata"}
              {data?.auto_scaling && <span className="text-muted-foreground font-normal"> · auto-scaling ON</span>}
            </div>
          </div>
          <button onClick={onClose} data-testid="strategy-drawer-close"
            className="h-9 w-9 rounded-lg border border-border hover:bg-secondary flex items-center justify-center">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {err && (
            <div className="flex items-center gap-2 text-sm text-rose-600 dark:text-rose-400 border border-rose-500/40 rounded-lg px-3 py-2">
              <AlertTriangle className="h-4 w-4" /> {err}
            </div>
          )}
          {loading ? (
            <div className="text-sm text-muted-foreground">Caricamento…</div>
          ) : (
            <>
              {/* Azioni */}
              <div className="flex flex-wrap gap-2">
                <button onClick={toggleEnabled} disabled={busy}
                  data-testid="strategy-drawer-toggle"
                  className={cls(
                    "h-10 px-4 rounded-lg flex items-center gap-2 text-sm font-semibold border transition-colors",
                    data?.enabled
                      ? "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/40 hover:bg-rose-500/20"
                      : "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/40 hover:bg-emerald-500/20"
                  )}>
                  <Power className="h-4 w-4" /> {data?.enabled ? "Disattiva live" : "Riattiva live"}
                </button>
                <button onClick={() => { onClose(); navigate(`/whatif?exclude=${encodeURIComponent(name)}`); }}
                  data-testid="strategy-drawer-whatif"
                  className="h-10 px-4 rounded-lg flex items-center gap-2 text-sm font-semibold border border-border bg-secondary hover:bg-secondary/70 transition-colors">
                  <Sparkles className="h-4 w-4" /> Simula senza questa
                </button>
              </div>

              {/* Rischio per-strategia */}
              <section>
                <div className="eyebrow flex items-center gap-1.5 mb-2"><Gauge className="h-3.5 w-3.5" /> Rischio per-strategia</div>
                <div className="flex items-center gap-2">
                  <input type="number" step="0.1" min="0" value={riskInput}
                    onChange={(e) => setRiskInput(e.target.value)} placeholder="auto"
                    data-testid="strategy-drawer-risk-input"
                    className="w-24 h-9 px-2 rounded-lg border border-border bg-background text-sm font-mono text-right" />
                  <span className="text-xs text-muted-foreground">× moltiplicatore lotto</span>
                  <button onClick={saveRisk} disabled={busy}
                    data-testid="strategy-drawer-risk-save"
                    className="h-9 px-3 rounded-lg border border-border hover:bg-secondary flex items-center gap-1.5 text-sm">
                    <Save className="h-3.5 w-3.5" /> Salva
                  </button>
                </div>
                {live && <div className="text-[11px] text-muted-foreground mt-1">{live.reason}</div>}
              </section>

              {/* Metriche live realizzate */}
              <section>
                <div className="eyebrow flex items-center gap-1.5 mb-2"><TrendingUp className="h-3.5 w-3.5" /> Risultati reali</div>
                {live ? (
                  <div className="grid grid-cols-3 gap-2">
                    <Stat label="Trade" value={live.trades} />
                    <Stat label="Win %" value={fmtPct(live.win_rate)} />
                    <Stat label="Profit factor" value={live.profit_factor} tone={live.profit_factor >= 1 ? "pos" : "neg"} />
                    <Stat label="Net" value={fmtMoney(live.net)} tone={live.net >= 0 ? "pos" : "neg"} />
                    <Stat label="Max DD %" value={fmtPct(live.max_dd_pct)} />
                    <Stat label="Lotto eff." value={`×${live.effective_mult}`} />
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Nessun trade reale ancora registrato per questa strategia.</div>
                )}
              </section>

              {/* Miglior config backtest */}
              <section>
                <div className="eyebrow flex items-center gap-1.5 mb-2"><FlaskConical className="h-3.5 w-3.5" /> Miglior backtest</div>
                {bt ? (
                  <div className="rounded-lg border border-border bg-secondary/30 p-3">
                    <div className="text-sm font-semibold">{bt.symbol} · {bt.variant} · {bt.timeframe}</div>
                    <div className="grid grid-cols-3 gap-2 mt-2">
                      <Stat label="Sharpe" value={bt.metrics?.sharpe} tone="pos" />
                      <Stat label="PF" value={bt.metrics?.profit_factor} />
                      <Stat label="Win %" value={fmtPct(bt.metrics?.win_rate)} />
                      <Stat label="Max DD %" value={fmtPct(bt.metrics?.max_dd)} />
                      <Stat label="Return %" value={fmtPct(bt.metrics?.return_pct)} />
                      <Stat label="Trade" value={bt.metrics?.n_trades} />
                    </div>
                    {data.backtest_by_symbol?.length > 1 && (
                      <div className="text-[11px] text-muted-foreground mt-2">
                        Testata anche su: {data.backtest_by_symbol.filter((r) => r.symbol !== bt.symbol).map((r) => r.symbol).join(", ")}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Nessun risultato di backtest in libreria.</div>
                )}
              </section>

              {/* Ultimi trade */}
              <section>
                <div className="eyebrow flex items-center gap-1.5 mb-2"><Activity className="h-3.5 w-3.5" /> Ultimi trade</div>
                {data.recent_trades?.length ? (
                  <div className="overflow-x-auto rounded-lg border border-border">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-[10px] uppercase tracking-wider text-muted-foreground border-b border-border">
                          <th className="px-2 py-2">Simbolo</th>
                          <th className="px-2 py-2">Lato</th>
                          <th className="px-2 py-2 text-right">Lotti</th>
                          <th className="px-2 py-2 text-right">P&L</th>
                          <th className="px-2 py-2">Motivo</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.recent_trades.map((t) => (
                          <tr key={t.ticket} className="border-b border-border/50">
                            <td className="px-2 py-1.5">{t.symbol}</td>
                            <td className="px-2 py-1.5">{t.side}</td>
                            <td className="px-2 py-1.5 text-right tabular">{t.lots}</td>
                            <td className={cls("px-2 py-1.5 text-right tabular", (t.pnl || 0) >= 0 ? POS_TEXT : NEG_TEXT)}>{fmtMoney(t.pnl)}</td>
                            <td className="px-2 py-1.5 text-muted-foreground truncate max-w-[120px]">{t.reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Nessun trade recente.</div>
                )}
              </section>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
