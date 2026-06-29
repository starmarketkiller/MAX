function classNames(...c) { return c.filter(Boolean).join(" "); }

function Metric({ label, value, tone = "default", sub }) {
  const cls = {
    default: "border-border bg-card",
    good:    "border-emerald-500/30 bg-emerald-500/5",
    warn:    "border-amber-500/30 bg-amber-500/5",
    bad:     "border-rose-500/30 bg-rose-500/5",
    primary: "border-sky-500/30 bg-sky-500/5",
  }[tone];
  return (
    <div className={classNames("rounded-xl border p-3", cls)}>
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-lg font-bold mt-0.5 font-mono">{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
    </div>
  );
}

function thresholdTone(val, goodAt, warnAt) {
  if (val >= goodAt) return "good";
  if (val >= warnAt) return "warn";
  return "bad";
}
function inverseTone(absVal, goodCap, warnCap) {
  if (absVal <= goodCap) return "good";
  if (absVal <= warnCap) return "warn";
  return "bad";
}

export default function BacktestMetrics({ metrics: m, tradesCount, bars }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <Metric tone={m.total_return_pct >= 0 ? "good" : "bad"}
              label="Return totale"
              value={`${m.total_return_pct >= 0 ? "+" : ""}${m.total_return_pct}%`}
              sub={`vs Buy&Hold ${m.buy_hold_return_pct >= 0 ? "+" : ""}${m.buy_hold_return_pct}%`}/>
      <Metric tone="primary" label="Final balance"
              value={`${m.final_balance.toFixed(0)}€`}
              sub={`da ${m.initial_balance.toFixed(0)}€`}/>
      <Metric tone={thresholdTone(m.win_rate_pct, 50, 40)}
              label="Win rate"
              value={`${m.win_rate_pct}%`}
              sub={`${m.wins}W / ${m.losses}L`}/>
      <Metric tone={thresholdTone(m.profit_factor, 1.5, 1)}
              label="Profit factor" value={m.profit_factor}/>
      <Metric tone={thresholdTone(m.sharpe, 1, 0)}
              label="Sharpe" value={m.sharpe}/>
      <Metric tone={thresholdTone(m.sortino, 1, 0)}
              label="Sortino" value={m.sortino}/>
      <Metric tone={inverseTone(Math.abs(m.max_dd_pct), 10, 20)}
              label="Max DD" value={`${m.max_dd_pct}%`}/>
      <Metric label="Trade" value={tradesCount} sub={`${bars} barre`}/>
    </div>
  );
}
