import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid,
  Legend, BarChart, Bar, ReferenceLine,
} from "recharts";

function classNames(...c) { return c.filter(Boolean).join(" "); }

const CHART_MARGIN = { top: 5, right: 25, left: 0, bottom: 0 };
const TOOLTIP_STYLE = { background: "#0c1322", border: "1px solid #334" };
const TOOLTIP_LABEL_STYLE = { color: "#ccc" };
const LEGEND_STYLE = { fontSize: 11 };
const REF_LINE_LABEL = { value: "start", position: "left", fontSize: 9, fill: "#9ca3af" };
const TICK_STYLE = { fontSize: 10 };
const AUTO_DOMAIN = ['auto', 'auto'];

const SMALL_TICK = { fontSize: 10 };
const REF_LINE_STROKE = "#9ca3af";
const EQUITY_STROKE = "#0ea5e9";
const PRICE_STROKE = "#a78bfa";
const BAR_GOOD = "#10b981";
const BAR_BAD = "#f43f5e";

function CloseAxisDomain(closeMin, closeMax) {
  return [closeMin * 0.95, closeMax * 1.05];
}

export default function BacktestCharts({ result, cfg }) {
  const eqData = result?.equity_curve?.map((p) => ({
    ts: p.ts.slice(0, 10),
    equity: p.equity,
    close: p.close,
  })) || [];
  const closeMin = eqData.length ? Math.min(...eqData.map(d=>d.close)) : 0;
  const closeMax = eqData.length ? Math.max(...eqData.map(d=>d.close)) : 0;

  return (
    <>
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="text-sm font-semibold mb-3 flex items-center justify-between">
          <span>Equity curve vs Prezzo</span>
          <span className="text-xs text-muted-foreground">
            {result.first_ts?.slice(0,10)} → {result.last_ts?.slice(0,10)}
          </span>
        </div>
        <div style={{ width: "100%", height: 320 }}>
          <ResponsiveContainer>
            <LineChart data={eqData} margin={CHART_MARGIN}>
              <CartesianGrid strokeDasharray="3 3" stroke="#3338" vertical={false}/>
              <XAxis dataKey="ts" tick={TICK_STYLE}
                     interval={Math.max(0, Math.floor(eqData.length/8))}/>
              <YAxis yAxisId="left" tick={TICK_STYLE} domain={AUTO_DOMAIN} width={60}/>
              <YAxis yAxisId="right" orientation="right" tick={TICK_STYLE}
                     domain={CloseAxisDomain(closeMin, closeMax)} width={50}/>
              <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL_STYLE}/>
              <Legend wrapperStyle={LEGEND_STYLE}/>
              <ReferenceLine yAxisId="left" y={cfg.initial_balance}
                             stroke={REF_LINE_STROKE} strokeDasharray="3 3" label={REF_LINE_LABEL}/>
              <Line yAxisId="left" type="monotone" dataKey="equity" name="Equity €"
                    stroke={EQUITY_STROKE} strokeWidth={2} dot={false}/>
              <Line yAxisId="right" type="monotone" dataKey="close" name="Prezzo"
                    stroke={PRICE_STROKE} strokeWidth={1} dot={false} opacity={0.5}/>
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-border bg-card p-4">
          <div className="text-sm font-semibold mb-3">PnL per strategia</div>
          <div style={{ width: "100%", height: 220 }}>
            <ResponsiveContainer>
              <BarChart data={result.by_strategy}>
                <CartesianGrid strokeDasharray="3 3" stroke="#3338" vertical={false}/>
                <XAxis dataKey="strategy" tick={SMALL_TICK}/>
                <YAxis tick={SMALL_TICK}/>
                <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL_STYLE}/>
                <Bar dataKey="pnl">
                  {result.by_strategy.map((d) => (
                    <Bar key={`bar-${d.strategy}`} fill={d.pnl >= 0 ? BAR_GOOD : BAR_BAD}/>
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 space-y-1">
            {result.by_strategy.map((s) => (
              <div key={s.strategy} className="flex justify-between text-xs">
                <span className="font-mono">{s.strategy}</span>
                <span className="text-muted-foreground">{s.n} trade — WR {s.win_rate}%</span>
                <span className={s.pnl >= 0 ? "text-emerald-600 font-semibold" : "text-rose-600 font-semibold"}>
                  {s.pnl >= 0 ? "+" : ""}{s.pnl.toFixed(0)}€
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-4">
          <div className="text-sm font-semibold mb-3">Ultimi trade</div>
          <div className="overflow-y-auto" style={{ maxHeight: 280 }}>
            <table className="w-full text-xs">
              <thead className="text-[10px] text-muted-foreground sticky top-0 bg-card">
                <tr>
                  <th className="text-left py-1">Data</th><th>Dir</th><th>Strat</th>
                  <th className="text-right">Entry</th><th className="text-right">Exit</th>
                  <th className="text-right">PnL</th><th>Why</th>
                </tr>
              </thead>
              <tbody>
                {result.trades.slice(-30).reverse().map((t) => (
                  <tr key={`tr-${t.ts_open}-${t.ts_close}-${t.strategy}`} className="border-t border-border/50">
                    <td className="py-1 font-mono text-[10px]">{t.ts_close?.slice(0,10)}</td>
                    <td className={t.dir === "BUY" ? "text-emerald-600" : "text-rose-600"}>{t.dir}</td>
                    <td className="text-[10px]">{t.strategy}</td>
                    <td className="text-right font-mono">{t.entry.toFixed(2)}</td>
                    <td className="text-right font-mono">{t.exit.toFixed(2)}</td>
                    <td className={classNames("text-right font-mono font-semibold",
                        t.pnl >= 0 ? "text-emerald-600" : "text-rose-600")}>
                      {t.pnl >= 0 ? "+" : ""}{t.pnl.toFixed(0)}
                    </td>
                    <td className="text-[10px]">{t.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
