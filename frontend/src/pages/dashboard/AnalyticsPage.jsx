import { useCallback, useMemo } from "react";
import { LineChart as LineChartIcon, ShieldAlert, Waves, Calendar, Layers } from "lucide-react";
import {
  ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, Cell,
} from "recharts";
import { useTheme } from "@/lib/theme";
import {
  Card, KpiCard, SectionHeader,
  cls, fmtMoney, fmtSign, fmtPrice,
  POS_TEXT, NEG_TEXT,
  pnlTone, pnlTextClass,
  CHART_COLORS, BAR_CHART_MARGIN,
} from "@/pages/dashboard/shared";

const DOW_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const REASON_COLORS = {
  "NXS:PROFIT": "text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  "NXS:BE":     "text-sky-700 dark:text-sky-400 bg-sky-500/10 border-sky-500/30",
  "NXS:TREND":  "text-sky-700 dark:text-sky-400 bg-sky-500/10 border-sky-500/30",
  "NXS:TIME":   "text-amber-700 dark:text-amber-400 bg-amber-500/10 border-amber-500/30",
  "NXS:NEWS":   "text-amber-700 dark:text-amber-400 bg-amber-500/10 border-amber-500/30",
  "NXS:DD":     "text-rose-700 dark:text-rose-400 bg-rose-500/10 border-rose-500/30",
  "NXS:RISK":   "text-rose-700 dark:text-rose-400 bg-rose-500/10 border-rose-500/30",
};
function reasonStyle(r) {
  return REASON_COLORS[r] || "text-muted-foreground bg-secondary border-border";
}

function heatmapBg(pnl, maxAbs) {
  if (!maxAbs) return "bg-secondary/40";
  const intensity = Math.min(1, Math.abs(pnl) / maxAbs);
  const alpha = (0.08 + intensity * 0.5).toFixed(2);
  return pnl >= 0
    ? `bg-[rgba(16,185,129,${alpha})]`
    : `bg-[rgba(244,63,94,${alpha})]`;
}

function calCellBg(pnl, maxAbs) {
  if (pnl === 0 || maxAbs === 0) return "bg-secondary/40";
  const intensity = Math.min(1, Math.abs(pnl) / maxAbs);
  const alpha = (0.15 + intensity * 0.65).toFixed(2);
  return pnl > 0
    ? `bg-[rgba(16,185,129,${alpha})]`
    : `bg-[rgba(244,63,94,${alpha})]`;
}

function corrColor(v) {
  if (v == null || isNaN(v)) return "bg-secondary";
  if (v >= 0.8)  return "bg-[rgba(244,63,94,0.85)] text-white";
  if (v >= 0.6)  return "bg-[rgba(244,63,94,0.55)] text-white";
  if (v >= 0.4)  return "bg-[rgba(244,63,94,0.3)]";
  if (v >= 0.2)  return "bg-[rgba(245,158,11,0.25)]";
  if (v >= -0.2) return "bg-secondary/60";
  if (v >= -0.5) return "bg-[rgba(16,185,129,0.25)]";
  return "bg-[rgba(16,185,129,0.5)]";
}

function EquityHeatmap({ heatmap }) {
  const cells = useMemo(() => heatmap?.by_dow_hour || [], [heatmap]);
  const grid = useMemo(() => {
    const m = {};
    cells.forEach((c) => { m[`${c.dow}-${c.hour}`] = c; });
    return m;
  }, [cells]);
  const maxAbs = useMemo(
    () => cells.reduce((m, c) => Math.max(m, Math.abs(c.pnl || 0)), 0),
    [cells]
  );

  return (
    <Card className="p-6 lg:p-8" testId="equity-heatmap">
      <SectionHeader
        eyebrow="Equity heatmap"
        title="P&L by day of week × hour (GMT)"
        icon={Waves}
        right={<span className="font-mono">{cells.length} cells</span>}
      />
      <div className="overflow-x-auto">
        <table className="min-w-full text-[10px] font-mono">
          <thead>
            <tr>
              <th className="text-left text-muted-foreground px-2 py-1">DOW \ Hour</th>
              {Array.from({ length: 24 }).map((_, h) => (
                <th key={`hour-${h}`} className="text-center text-muted-foreground px-1 py-1">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {DOW_NAMES.map((dn, dow) => (
              <tr key={dn}>
                <td className="text-muted-foreground px-2 py-1 font-semibold">{dn}</td>
                {Array.from({ length: 24 }).map((_, h) => {
                  const c = grid[`${dow}-${h}`];
                  const pnl = c?.pnl || 0;
                  const count = c?.count || 0;
                  return (
                    <td
                      key={`dh-${dow}-${h}`}
                      title={count ? `${dn} ${h}:00\nP&L: $${fmtSign(pnl)}\nTrades: ${count}` : ""}
                      data-testid={`heatmap-cell-${dow}-${h}`}
                      className={cls(
                        "px-1 py-2 text-center border border-border/40",
                        heatmapBg(pnl, maxAbs)
                      )}
                    >
                      {count ? (
                        <div className={cls(
                          "font-bold text-[9px]",
                          pnl >= 0 ? POS_TEXT : NEG_TEXT
                        )}>
                          {pnl >= 0 ? "+" : ""}{Math.round(pnl)}
                        </div>
                      ) : <span className="opacity-30">·</span>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="text-[10px] text-muted-foreground mt-3 flex items-center gap-3">
        <span className="inline-block w-3 h-3 rounded bg-emerald-500/40" /> profitable
        <span className="inline-block w-3 h-3 rounded bg-rose-500/40 ml-2" /> losing
        <span className="ml-2 opacity-70">Darker = higher absolute P&amp;L · hover for details</span>
      </div>
    </Card>
  );
}

function ByReasonTable({ byReason }) {
  const rows = byReason?.by_reason || [];
  return (
    <Card testId="by-reason-card">
      <div className="p-6 lg:p-8 pb-4">
        <div className="eyebrow flex items-center gap-1.5">
          <ShieldAlert className="h-3.5 w-3.5" /> Close reason breakdown
        </div>
        <h3 className="font-semibold text-lg tracking-tight mt-1">
          {byReason?.total ?? 0} <span className="font-normal text-muted-foreground">total closures</span>
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b border-border">
              <th className="px-6 lg:px-8 py-3 eyebrow font-semibold">Reason</th>
              <th className="px-3 py-3 eyebrow font-semibold text-right">Count</th>
              <th className="px-3 py-3 eyebrow font-semibold text-right">Win rate</th>
              <th className="px-6 lg:px-8 py-3 eyebrow font-semibold text-right">Net P&amp;L</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td colSpan={4} className="px-6 py-10 text-center text-muted-foreground text-sm">
                No closures yet · they will appear here once the EA posts close events.
              </td></tr>
            ) : rows.map((r) => (
              <tr key={r.reason} className="border-b border-border last:border-0 hover:bg-secondary/40">
                <td className="px-6 lg:px-8 py-3">
                  <span className={cls("px-2 py-1 rounded-md text-[11px] font-bold border font-mono", reasonStyle(r.reason))}>
                    {r.reason}
                  </span>
                </td>
                <td className="px-3 py-3 text-right font-mono">{r.count}</td>
                <td className="px-3 py-3 text-right font-mono">{r.win_rate.toFixed(1)}%</td>
                <td className={cls("px-6 lg:px-8 py-3 text-right font-mono font-bold", pnlTextClass(r.pnl))}>
                  {r.pnl >= 0 ? "+" : ""}${fmtMoney(r.pnl)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function ratioTone(v) {
  if (v == null) return "neutral";
  if (v >= 1) return "pos";
  if (v >= 0) return "neutral";
  return "neg";
}

function RiskMetricsStrip({ risk }) {
  const r = risk || {};
  const cards = [
    { k: "sharpe",        label: "Sharpe ratio",  fmt: (v) => v?.toFixed(2),
      tone: ratioTone(r.sharpe),
      hint: ">1 good · >2 excellent · >3 outstanding" },
    { k: "sortino",       label: "Sortino ratio", fmt: (v) => v?.toFixed(2),
      tone: ratioTone(r.sortino),
      hint: "downside-only risk · >2 = robust" },
    { k: "calmar",        label: "Calmar ratio",  fmt: (v) => v?.toFixed(2),
      tone: r.calmar  >= 1 ? "pos" : "neg",
      hint: "return / max DD · >1 healthy" },
    { k: "expectancy_r",  label: "Expectancy (R)", fmt: (v) => `${v?.toFixed(2)} R`,
      tone: r.expectancy_r > 0 ? "pos" : "neg",
      hint: "average trade in R-multiples (R = avg loss)" },
    { k: "max_dd",        label: "Max drawdown",  fmt: (v) => `$${fmtMoney(v)}`,
      tone: "neg",
      hint: "peak-to-valley · realised" },
    { k: "recovery_days", label: "Recovery (d)",  fmt: (v) => `${v}`,
      tone: r.recovery_days > 30 ? "warn" : "neutral",
      hint: "days to claw back the max DD" },
  ];
  return (
    <Card className="p-6 lg:p-8" testId="risk-metrics-strip">
      <div className="eyebrow flex items-center gap-1.5 mb-1">
        <ShieldAlert className="h-3.5 w-3.5" /> Risk-adjusted metrics
      </div>
      <h3 className="font-semibold text-lg tracking-tight">
        Institutional view <span className="font-normal text-muted-foreground">· beyond win rate</span>
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mt-5">
        {cards.map(({ k, label, fmt, tone, hint }) => {
          let toneClass = "text-foreground";
          if (tone === "pos") toneClass = POS_TEXT;
          else if (tone === "neg") toneClass = NEG_TEXT;
          else if (tone === "warn") toneClass = "text-amber-600 dark:text-amber-400";
          return (
            <div key={k} className="space-y-1.5" data-testid={`risk-${k}`}>
              <div className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground font-semibold">{label}</div>
              <div className={cls("font-mono font-bold text-2xl tabular leading-none", toneClass)}>
                {fmt(r[k] ?? 0)}
              </div>
              <div className="text-[10px] text-muted-foreground/80 italic">{hint}</div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function CalendarHeatmap({ calendar }) {
  const days = useMemo(() => calendar?.days || [], [calendar]);
  const maxAbs = useMemo(
    () => days.reduce((m, d) => Math.max(m, Math.abs(d.pnl || 0)), 0),
    [days]
  );
  const weeks = useMemo(() => {
    if (days.length === 0) return [];
    const cols = [];
    let col = Array(7).fill(null);
    days.forEach((d) => {
      const date = new Date(d.date + "T00:00:00Z");
      const dow = (date.getUTCDay() + 6) % 7;
      col[dow] = d;
      if (dow === 6) {
        cols.push(col);
        col = Array(7).fill(null);
      }
    });
    if (col.some((x) => x)) cols.push(col);
    return cols;
  }, [days]);

  const totals = useMemo(() => {
    const positiveDays = days.filter((d) => d.pnl > 0).length;
    const negativeDays = days.filter((d) => d.pnl < 0).length;
    const zeroDays = days.filter((d) => d.count === 0).length;
    const totalPnL = days.reduce((s, d) => s + (d.pnl || 0), 0);
    return { positiveDays, negativeDays, zeroDays, totalPnL };
  }, [days]);

  return (
    <Card className="p-6 lg:p-8" testId="calendar-heatmap">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-5">
        <div>
          <div className="eyebrow flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5" /> Daily performance calendar
          </div>
          <h3 className="font-semibold text-lg tracking-tight mt-1">
            {calendar?.from && calendar?.to ? `${calendar.from} → ${calendar.to}` : "Loading…"}
          </h3>
        </div>
        <div className="flex gap-6 text-right text-xs">
          <div><span className="eyebrow">Green</span><div className={cls("font-mono font-bold text-base mt-1", POS_TEXT)}>{totals.positiveDays}d</div></div>
          <div><span className="eyebrow">Red</span><div className={cls("font-mono font-bold text-base mt-1", NEG_TEXT)}>{totals.negativeDays}d</div></div>
          <div><span className="eyebrow">Inactive</span><div className="font-mono font-bold text-base mt-1 text-muted-foreground">{totals.zeroDays}d</div></div>
          <div><span className="eyebrow">Net P&amp;L</span><div className={cls("font-mono font-bold text-base mt-1", pnlTextClass(totals.totalPnL))}>${fmtSign(totals.totalPnL)}</div></div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <div className="inline-flex gap-1" style={{ minWidth: "max-content" }}>
          <div className="flex flex-col gap-1 mr-1 text-[9px] text-muted-foreground pt-0.5 select-none">
            {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d, i) => (
              <div key={d} className="h-[12px] leading-3" style={{ visibility: i % 2 === 0 ? "visible" : "hidden" }}>{d}</div>
            ))}
          </div>
          {weeks.map((col, ci) => (
            <div key={`week-${col[0]?.date || ci}`} className="flex flex-col gap-1">
              {col.map((d, ri) => (
                <div
                  key={d?.date || `empty-${ci}-${ri}`}
                  data-testid={d ? `cal-cell-${d.date}` : undefined}
                  title={d ? `${d.date}\nP&L: $${fmtSign(d.pnl)}\nTrades: ${d.count}` : ""}
                  className={cls(
                    "h-[12px] w-[12px] rounded-sm border border-border/30",
                    d ? calCellBg(d.pnl, maxAbs) : "bg-transparent border-transparent"
                  )}
                />
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="text-[10px] text-muted-foreground mt-4 flex items-center gap-3">
        Less
        <span className="inline-block w-3 h-3 rounded-sm bg-rose-500/70" />
        <span className="inline-block w-3 h-3 rounded-sm bg-rose-500/30" />
        <span className="inline-block w-3 h-3 rounded-sm bg-secondary/40" />
        <span className="inline-block w-3 h-3 rounded-sm bg-emerald-500/30" />
        <span className="inline-block w-3 h-3 rounded-sm bg-emerald-500/70" />
        More · hover for details
      </div>
    </Card>
  );
}

function CorrelationMatrix({ correlation }) {
  const strats = correlation?.strategies || [];
  const matrix = correlation?.matrix || [];
  if (strats.length === 0) {
    return (
      <Card className="p-6 lg:p-8" testId="correlation-matrix-empty">
        <SectionHeader eyebrow="Strategy correlation" title="Need more data" icon={Layers} />
        <p className="text-sm text-muted-foreground">
          Correlation needs at least 3 trading days. Currently {correlation?.days ?? 0} days.
        </p>
      </Card>
    );
  }
  const dangerous = [];
  for (let i = 0; i < strats.length; i++) {
    for (let j = i + 1; j < strats.length; j++) {
      const v = matrix[i]?.[j];
      if (v != null && v >= 0.7) dangerous.push({ a: strats[i], b: strats[j], v });
    }
  }
  dangerous.sort((a, b) => b.v - a.v);

  return (
    <Card className="p-6 lg:p-8" testId="correlation-matrix">
      <SectionHeader
        eyebrow="Strategy correlation"
        title={
          <>
            {strats.length} <span className="text-muted-foreground font-normal">strategies ·</span>{" "}
            {dangerous.length > 0 ? (
              <span className={NEG_TEXT}>{dangerous.length} redundant pair{dangerous.length > 1 ? "s" : ""}</span>
            ) : (
              <span className={POS_TEXT}>well diversified</span>
            )}
          </>
        }
        icon={Layers}
        right={<span className="font-mono">{correlation?.days ?? 0} days of data</span>}
      />

      <div className="overflow-x-auto">
        <table className="text-[10px] font-mono">
          <thead>
            <tr>
              <th className="px-1 py-1"></th>
              {strats.map((s) => (
                <th key={s} className="px-1 py-1 text-muted-foreground" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}>{s}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {strats.map((s1, i) => (
              <tr key={s1}>
                <td className="text-muted-foreground pr-2 py-0.5 text-right whitespace-nowrap">{s1}</td>
                {strats.map((s2, j) => {
                  const v = matrix[i]?.[j];
                  return (
                    <td
                      key={s2}
                      data-testid={`corr-${i}-${j}`}
                      title={`${s1} ↔ ${s2}: ${v?.toFixed(3)}`}
                      className={cls(
                        "h-7 w-7 text-center border border-border/40 font-bold",
                        i === j ? "bg-foreground/10 text-muted-foreground" : corrColor(v)
                      )}
                    >{(() => {
                      if (i === j) return "—";
                      return v != null ? v.toFixed(1) : "·";
                    })()}</td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {dangerous.length > 0 && (
        <div className="mt-5 space-y-1.5">
          <div className="eyebrow text-rose-600 dark:text-rose-400">⚠ Redundant pairs (correlation ≥ 0.7)</div>
          {dangerous.slice(0, 6).map((p) => (
            <div key={`${p.a}|${p.b}`} className="text-xs text-muted-foreground font-mono">
              <span className="text-foreground font-semibold">{p.a}</span> ↔{" "}
              <span className="text-foreground font-semibold">{p.b}</span>:
              {" "}<span className={NEG_TEXT}>ρ = {p.v.toFixed(2)}</span>{" "}
              <span className="opacity-70">— consider disabling one</span>
            </div>
          ))}
        </div>
      )}
      <div className="text-[10px] text-muted-foreground mt-4 flex items-center gap-3">
        <span className="inline-block w-3 h-3 rounded-sm bg-emerald-500/50" /> uncorrelated (good)
        <span className="inline-block w-3 h-3 rounded-sm bg-amber-500/30" /> mild
        <span className="inline-block w-3 h-3 rounded-sm bg-rose-500/55" /> high (redundant)
      </div>
    </Card>
  );
}

// ========================================================================
// ANALYTICS PAGE (default export)
// ========================================================================
export default function AnalyticsPage({ summary, trades, heatmap, byReason, calendar, correlation, onSelectTrade }) {
  const { theme } = useTheme();
  const stratData = useMemo(
    () => (summary?.by_strategy || []).map((s) => ({ name: s.strategy, pnl: s.pnl, wr: s.win_rate })),
    [summary]
  );

  const colors = CHART_COLORS[theme] || CHART_COLORS.dark;
  const tooltipStyle = useMemo(() => ({
    background: colors.tooltipBg,
    border: `1px solid ${colors.tooltipBorder}`,
    borderRadius: 10, fontSize: 12, color: colors.tooltipText,
  }), [colors.tooltipBg, colors.tooltipBorder, colors.tooltipText]);
  const tooltipLabelStyle = useMemo(() => ({ color: colors.tooltipText }), [colors.tooltipText]);
  const axisTick = useMemo(() => ({ fontSize: 11, fill: colors.axis }), [colors.axis]);
  const tooltipFormatter = useCallback((v) => [`$${fmtMoney(v)}`, "P&L"], []);

  return (
    <div className="space-y-6 fade-in">
      <Card className="p-6 lg:p-8">
        <div className="eyebrow flex items-center gap-1.5">
          <LineChartIcon className="h-3.5 w-3.5" /> Performance
        </div>
        <h2 className="text-2xl font-semibold tracking-tight mt-1">
          Realised P&amp;L <span className="font-normal text-muted-foreground">by strategy</span>
        </h2>
      </Card>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
        <KpiCard label="Total trades" value={summary?.total_trades ?? 0} testId="an-total" />
        <KpiCard
          label="Win rate"
          value={`${summary?.win_rate ?? 0}%`}
          tone={(summary?.win_rate ?? 0) >= 50 ? "pos" : "neg"}
          testId="an-wr"
        />
        <KpiCard
          label="Total P&L"
          value={`$${fmtSign(summary?.total_pnl)}`}
          tone={pnlTone(summary?.total_pnl)}
          testId="an-pnl"
        />
        <KpiCard
          label="Profit factor"
          value={(summary?.profit_factor ?? 0).toFixed(2)}
          tone={(summary?.profit_factor ?? 0) >= 1 ? "pos" : "neg"}
          testId="an-pf"
        />
      </div>

      <RiskMetricsStrip risk={summary?.risk} />

      <Card className="p-6 lg:p-8">
        <div className="eyebrow mb-5">P&amp;L by strategy</div>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
            <BarChart data={stratData} margin={BAR_CHART_MARGIN}>
              <CartesianGrid stroke={colors.grid} strokeDasharray="3 3" />
              <XAxis
                dataKey="name"
                tick={axisTick}
                angle={-35}
                textAnchor="end"
                interval={0}
                height={60}
              />
              <YAxis tick={axisTick} />
              <Tooltip
                contentStyle={tooltipStyle}
                labelStyle={tooltipLabelStyle}
                formatter={tooltipFormatter}
              />
              <Bar dataKey="pnl">
                {stratData.map((d) => (
                  <Cell key={d.name} fill={d.pnl >= 0 ? "#10b981" : "#f43f5e"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card>
        <div className="p-6 lg:p-8 pb-4 eyebrow">Last trades</div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-border">
                <th className="px-6 lg:px-8 py-3 eyebrow font-semibold">Closed</th>
                <th className="px-3 py-3 eyebrow font-semibold">Side</th>
                <th className="px-3 py-3 eyebrow font-semibold">Strategy</th>
                <th className="px-3 py-3 eyebrow font-semibold text-right">Lots</th>
                <th className="px-3 py-3 eyebrow font-semibold text-right">Open → Close</th>
                <th className="px-6 lg:px-8 py-3 eyebrow font-semibold text-right">P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {(trades || []).slice(0, 25).map((t) => (
                <tr
                  key={`${t.ticket}-${t.closeTime}`}
                  data-testid={`last-trade-row-${t.ticket}`}
                  onClick={() => onSelectTrade && onSelectTrade(t)}
                  className="border-b border-border last:border-0 hover:bg-secondary/40 cursor-pointer transition-colors"
                >
                  <td className="px-6 lg:px-8 py-3 text-xs text-muted-foreground">
                    {t.closeTime ? new Date(t.closeTime).toLocaleString() : "—"}
                  </td>
                  <td className="px-3 py-3">
                    <span className={cls(
                      "px-2 py-0.5 rounded-md text-[11px] font-bold border",
                      t.side === "BUY"
                        ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30"
                        : "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/30"
                    )}>
                      {t.side}
                    </span>
                  </td>
                  <td className="px-3 py-3 font-mono text-xs text-muted-foreground">{t.strategy}</td>
                  <td className="px-3 py-3 text-right font-mono">{t.lots?.toFixed(2)}</td>
                  <td className="px-3 py-3 text-right font-mono text-xs text-muted-foreground">
                    {fmtPrice(t.openPrice)} → {fmtPrice(t.closePrice)}
                  </td>
                  <td className={cls(
                    "px-6 lg:px-8 py-3 text-right font-mono font-bold",
                    pnlTextClass(t.pnl)
                  )}>
                    {(t.pnl ?? 0) >= 0 ? "+" : ""}${fmtMoney(t.pnl)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <EquityHeatmap heatmap={heatmap} />
      <CalendarHeatmap calendar={calendar} />
      <CorrelationMatrix correlation={correlation} />
      <ByReasonTable byReason={byReason} />
    </div>
  );
}

export { REASON_COLORS };
