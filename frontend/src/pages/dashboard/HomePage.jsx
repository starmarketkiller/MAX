import { useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Activity, Pause, Play, AlertOctagon,
  ShieldAlert, TrendingUp, TrendingDown, Clock, Target, Sparkles, Cpu,
  Layers, GitBranch, Radio, Zap, Gauge, Newspaper, Waves,
  X, Scissors, RotateCcw, Calendar, ChevronRight,
  LineChart as LineChartIcon,
} from "lucide-react";
import {
  Line, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip,
  Area, AreaChart,
} from "recharts";
import { useTheme } from "@/lib/theme";
import HealthScoreCard from "@/pages/dashboard/HealthScoreCard";
import LockedProfileBanner from "@/components/LockedProfileBanner";
import { DEFAULT_SETTINGS } from "@/contracts/settingsContract";
import { LIVE_STRATEGY_COUNT } from "@/contracts/strategyRegistry";
import {
  Card, Pill, SectionHeader,
  cls, fmtMoney, fmtSign, fmtPct, fmtPrice,
  POS_TEXT, NEG_TEXT,
  pnlTone, pnlTextClass, biasTone, velocityTone, bspTone, trendTone,
  bosLabel, chochLabel, qualityToneClass, reactionPriceLabel,
  STRAT_LIST, STRAT_FAMILIES, STRAT_FAMILY_COLOR, DIALOGS, CHART_COLORS, EQUITY_CHART_MARGIN, YAXIS_DOMAIN_AUTO,
  gateStyleFor,
} from "@/pages/dashboard/shared";

function volRegimeTone(r) {
  if (r === "HIGH") return "warn";
  if (r === "LOW") return "info";
  return "neutral";
}

function bosToneFor(status) {
  if (status?.bosUp) return "pos";
  if (status?.bosDown) return "neg";
  return "neutral";
}

function reactionContainerTone(detected, isBull) {
  if (!detected) return "bg-secondary/40 border-border";
  if (isBull)    return "bg-emerald-500/10 border-emerald-500/30";
  return "bg-rose-500/10 border-rose-500/30";
}

const hasValue = (value) => value !== null && value !== undefined && value !== "";
const terminalValue = (value, formatter = (item) => String(item)) => hasValue(value) ? formatter(value) : "—";
const moneyValue = (value, signed = false) => terminalValue(value, (item) => signed ? fmtSign(item) : fmtMoney(item));

function SourceBadge({ status, health }) {
  let label = null;
  let toneClass = "border-border text-muted-foreground";
  if (health?.demo === true || status?.demo === true) {
    label = "DEMO";
    toneClass = "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400";
  } else if (status?.online === true || health?.online === true) {
    label = "LIVE";
    toneClass = "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400";
  } else if (status || health) {
    label = "CACHED";
    toneClass = "border-cyan-500/25 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300";
  }
  return label ? <span className={cls("rounded-full border px-2 py-1 font-mono text-[9px] font-bold tracking-wider", toneClass)}>{label}</span> : null;
}

function SystemStatusStrip({ status, health }) {
  const eaState = status?.eaPaused === true
    ? "PAUSED"
    : status?.online === true || health?.online === true
      ? "RUNNING"
      : status?.online === false || health?.online === false
        ? "OFFLINE"
        : null;
  const age = hasValue(health?.last_update_sec)
    ? `${Math.max(0, Math.round(Number(health.last_update_sec)))}s ago`
    : hasValue(status?._updated_ago)
      ? `${Math.max(0, Math.round(Number(status._updated_ago)))}s ago`
      : null;
  const fields = [
    ["EA", eaState], ["MT5 Bridge", status?.bridgeState], ["Symbol", status?.symbol],
    ["Session", status?.session], ["Regime", status?.regime], ["Updated", age],
  ];

  return (
    <Card className="p-3 sm:p-4" testId="system-status-strip">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2"><Radio size={14} className="text-cyan-400" /><span className="text-[10px] font-bold uppercase tracking-[0.18em] text-muted-foreground">System status</span></div>
        <SourceBadge status={status} health={health} />
      </div>
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-3 xl:grid-cols-6">
        {fields.map(([label, value]) => (
          <div key={label} className="min-w-0 bg-background/90 px-3 py-2.5">
            <div className="text-[9px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</div>
            <div className="mt-1 truncate font-mono text-xs font-semibold text-foreground" title={hasValue(value) ? String(value) : "Unavailable"}>{terminalValue(value)}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function CompactMetric({ label, value, tone = "neutral", icon: Icon }) {
  const toneClass = tone === "positive" ? "text-emerald-600 dark:text-emerald-400" : tone === "negative" ? "text-rose-600 dark:text-rose-400" : tone === "warning" ? "text-amber-600 dark:text-amber-400" : "text-foreground";
  return (
    <Card className="min-w-0 p-3.5">
      <div className="flex items-center justify-between gap-2"><span className="text-[9px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</span>{Icon ? <Icon size={13} className="shrink-0 text-muted-foreground" /> : null}</div>
      <div className={cls("mt-2 truncate font-mono text-lg font-semibold tracking-tight", toneClass)} title={value === "—" ? "Unavailable" : value}>{value}</div>
    </Card>
  );
}

function CoreMetrics({ status }) {
  const signedTone = (value) => !hasValue(value) ? "neutral" : Number(value) < 0 ? "negative" : Number(value) > 0 ? "positive" : "neutral";
  return (
    <section>
      <SectionHeader title="Core metrics" subtitle="Live account state" />
      <div className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-6">
        <CompactMetric label="Equity" value={moneyValue(status?.equity)} icon={TrendingUp} />
        <CompactMetric label="Balance" value={moneyValue(status?.balance)} icon={Gauge} />
        <CompactMetric label="Floating PnL" value={moneyValue(status?.floatPnL, true)} tone={signedTone(status?.floatPnL)} icon={Waves} />
        <CompactMetric label="Daily PnL" value={moneyValue(status?.dailyPnL, true)} tone={signedTone(status?.dailyPnL)} icon={Activity} />
        <CompactMetric label="Drawdown" value={terminalValue(status?.drawdownPct, fmtPct)} tone={hasValue(status?.drawdownPct) && Number(status.drawdownPct) > 0 ? "warning" : "neutral"} icon={ShieldAlert} />
        <CompactMetric label="Trades today" value={terminalValue(status?.tradesToday)} icon={Target} />
      </div>
    </section>
  );
}

function ExecutionPipeline({ status }) {
  const reactionAvailable = typeof status?.reactionDetected === "boolean";
  const positionsAvailable = Array.isArray(status?.positions);
  const gateState = status?.eaPaused === true ? "EA paused" : status?.newsBlock === true ? "News guard active" : null;
  const steps = [
    ["SCAN", "Telemetry unavailable"],
    ["SIGNAL", reactionAvailable ? (status.reactionDetected ? "Reaction detected" : "No active reaction") : "Telemetry unavailable"],
    ["GATE", gateState || "Telemetry unavailable"],
    ["EXECUTE", "Telemetry unavailable"],
    ["POSITION", positionsAvailable ? `${status.positions.length} active` : "Telemetry unavailable"],
    ["EXIT", "Telemetry unavailable"],
  ];
  return (
    <section>
      <SectionHeader title="Execution pipeline" subtitle="SCAN → SIGNAL → GATE → EXECUTE → POSITION → EXIT" />
      <Card className="p-3 sm:p-4"><div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
        {steps.map(([name, detail], index) => <div key={name} className="min-w-0 rounded-lg border border-border bg-secondary/30 px-3 py-3"><div className="flex items-center gap-2"><span className="font-mono text-[9px] text-muted-foreground">{String(index + 1).padStart(2, "0")}</span><span className="font-mono text-[10px] font-bold tracking-[0.12em] text-primary">{name}</span></div><div className="mt-2 min-h-8 text-[10px] leading-4 text-muted-foreground">{detail}</div></div>)}
      </div></Card>
    </section>
  );
}

// ========================================================================
// COMMAND CENTER
// ========================================================================
function CommandCenter({ status, onCmd }) {
  const paused = !!status?.eaPaused;
  const baseBtn = "group h-24 rounded-xl border text-sm font-semibold transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] flex flex-col items-center justify-center gap-2 active:scale-[0.97]";
  const secondaryBtn = cls(baseBtn, "border-border bg-secondary/40 hover:bg-secondary text-foreground hover:border-primary/40 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_-12px_hsl(var(--primary)/0.4)]");

  return (
    <Card className="p-6 lg:p-8" testId="command-center">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-6">
        <div>
          <div className="eyebrow flex items-center gap-1.5">
            <Radio className="h-3.5 w-3.5" /> Command center
          </div>
          <h2 className="text-2xl font-semibold tracking-tight mt-1">
            {paused ? (
              <span className="text-amber-600 dark:text-amber-400">EA paused</span>
            ) : (
              <span>EA running</span>
            )}
            <span className="text-muted-foreground font-normal text-base ml-2">· remote actions</span>
          </h2>
        </div>
        <div className="text-xs text-muted-foreground md:text-right">
          <div>Bridge poll every 1s</div>
          <div className="font-mono mt-0.5">
            {status?.symbol || "—"} · {terminalValue(status?.tradesToday)} trades today
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
        {paused ? (
          <button
            data-testid="resume-ea-button"
            onClick={() => onCmd("resume", null, false)}
            className={cls(baseBtn, "bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-400 text-white border-transparent shadow-sm")}
          >
            <Play className="h-5 w-5 group-hover:scale-110 transition-transform" />
            <span>Resume EA</span>
          </button>
        ) : (
          <button
            data-testid="pause-ea-button"
            onClick={() => onCmd("pause", null, true, DIALOGS.pause)}
            className={cls(baseBtn, "bg-foreground hover:opacity-90 text-background border-transparent shadow-sm")}
          >
            <Pause className="h-5 w-5 group-hover:scale-110 transition-transform" />
            <span>Pause EA</span>
          </button>
        )}

        <button
          data-testid="close-all-button"
          onClick={() => onCmd("close_all", null, true, DIALOGS.closeAll)}
          className={cls(baseBtn, "bg-rose-600 hover:bg-rose-700 dark:bg-rose-500 dark:hover:bg-rose-400 text-white border-transparent shadow-sm")}
        >
          <AlertOctagon className="h-5 w-5 group-hover:scale-110 transition-transform" />
          <span>Close all</span>
        </button>

        <button
          data-testid="reset-anti-revenge-button"
          onClick={() => onCmd("reset_anti_revenge", null, true, DIALOGS.resetAntiRevenge)}
          className={secondaryBtn}
        >
          <RotateCcw className="h-5 w-5 text-primary group-hover:scale-110 transition-transform" />
          <span>Reset anti-revenge</span>
        </button>

        <button
          data-testid="reset-daily-button"
          onClick={() => onCmd("reset_daily", null, true, DIALOGS.resetDaily)}
          className={secondaryBtn}
        >
          <Calendar className="h-5 w-5 text-primary group-hover:scale-110 transition-transform" />
          <span>Reset daily</span>
        </button>

        <Link
          to="/strategies"
          data-testid="strategies-shortcut"
          className={secondaryBtn}
        >
          <Layers className="h-5 w-5 text-primary group-hover:scale-110 transition-transform" />
          <span>Strategies</span>
        </Link>
      </div>
    </Card>
  );
}

// ========================================================================
// MARKET / STRUCTURE / REACTION
// ========================================================================
function MarketIntelligence({ status }) {
  const newsKnown = typeof status?.newsBlock === "boolean";
  const eslKnown = typeof status?.eslHit === "boolean";
  const dptKnown = typeof status?.dptHit === "boolean";
  return (
    <Card className="p-4" testId="market-intelligence">
      <SectionHeader
        eyebrow="Market intelligence"
        title="Live read on regime + flow"
        icon={Gauge}
        right={<span className="font-mono">{status?.session || "—"}</span>}
      />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        <Pill label="Regime" value={status?.regime} tone="info" icon={Activity} />
        <Pill label="Session" value={status?.session} tone="info" icon={Clock} />
        <Pill label="HTF" value={status?.htfBias} tone={biasTone(status?.htfBias)} icon={TrendingUp} />
        <Pill label="Velocity" value={status?.velocity} tone={velocityTone(status?.velocity)} icon={Zap} />
        <Pill label="AMD" value={status?.amdPhase}
              tone={status?.amdPhase && status.amdPhase !== "NONE" ? "info" : "neutral"} icon={Waves} />
        <Pill label="BSP" value={status?.bspPct != null ? `${Number(status.bspPct).toFixed(0)}%` : "—"}
              tone={bspTone(status?.bspPct)} icon={Gauge} />
        <Pill label="News" value={!newsKnown ? "—" : status.newsBlock ? "BLOCK" : "OPEN"}
              tone={!newsKnown ? "neutral" : status.newsBlock ? "neg" : "pos"} icon={Newspaper} />
        <Pill label="Vol regime" value={status?.volRegime || "—"}
              tone={volRegimeTone(status?.volRegime)}
              icon={Waves} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 mt-3" data-testid="protection-pills">
        <Pill label="ESL" value={!eslKnown ? "—" : status.eslHit ? "HIT" : "OK"}
              tone={!eslKnown ? "neutral" : status.eslHit ? "neg" : "pos"} icon={ShieldAlert} />
        <Pill label="DPT" value={!dptKnown ? "—" : status.dptHit ? "HIT" : "OK"}
              tone={!dptKnown ? "neutral" : status.dptHit ? "warn" : "pos"} icon={Target} />
        <Pill label="Auto-close" value={status?.autoClosePending ? "PENDING" : "—"}
              tone={status?.autoClosePending ? "warn" : "neutral"} icon={Clock} />
        <Pill label="Float %" value={status?.floatPnLPct != null ? `${Number(status.floatPnLPct).toFixed(2)}%` : "—"}
              tone={pnlTone(status?.floatPnLPct)} icon={Gauge} />
      </div>
    </Card>
  );
}

function StructureSection({ status }) {
  const trend = status?.structTrend;
  const bos = bosLabel(status);
  const choch = chochLabel(status);
  return (
    <Card className="p-4" testId="structure-section">
      <SectionHeader
        eyebrow="Structure engine"
        title="BOS · CHOCH · swings · OB · FVG"
        icon={GitBranch}
        right={<span className="font-mono">{terminalValue(status?.activeLevels)} active levels</span>}
      />
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
        <Pill label="Trend" value={trend || "—"} tone={trendTone(trend)} />
        <Pill label="BOS" value={bos} tone={bosToneFor(status)} />
        <Pill label="CHOCH" value={choch} tone={status?.chochUp || status?.chochDown ? "warn" : "neutral"} />
        <Pill label="Swing H" value={status?.lastSwingHigh ? fmtPrice(status.lastSwingHigh) : "—"} />
        <Pill label="Swing L" value={status?.lastSwingLow ? fmtPrice(status.lastSwingLow) : "—"} />
        <Pill label="Levels" value={terminalValue(status?.activeLevels)} />
      </div>
    </Card>
  );
}

function ReactionSection({ status }) {
  const r = status;
  const detectionKnown = typeof r?.reactionDetected === "boolean";
  const detected = r?.reactionDetected === true;
  const dir = r?.reactionDir;
  const quality = r?.reactionQuality;
  const isBull = dir === 1;
  const containerTone = reactionContainerTone(detected, isBull);
  return (
    <Card className="p-4" testId="reaction-section">
      <SectionHeader
        eyebrow="Reaction engine"
        title={`Trigger source · ${LIVE_STRATEGY_COUNT} strategies`}
        icon={Sparkles}
      />
      <div className={cls("rounded-xl border p-5", containerTone)}>
        {detected ? (
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className={cls("text-[10px] uppercase tracking-[0.12em] font-bold",
                isBull ? POS_TEXT : NEG_TEXT)}>
                {isBull ? "Bullish reaction" : "Bearish reaction"}
              </div>
              <div className="font-semibold text-xl mt-1 flex items-center gap-2">
                {isBull ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
                {r.reactionType}
              </div>
              <div className="text-xs text-muted-foreground mt-1 font-mono">
                @ {reactionPriceLabel(r)}
              </div>
            </div>
            <div className="text-right">
              <div className="eyebrow">Quality</div>
              <div className={cls(
                "font-mono font-bold text-4xl tabular leading-none mt-1",
                qualityToneClass(quality)
              )}>
                {hasValue(quality) ? Math.round(quality) : "—"}
                {hasValue(quality) ? <span className="text-base font-medium opacity-50">/100</span> : null}
              </div>
            </div>
          </div>
        ) : detectionKnown ? (
          <div className="text-sm text-muted-foreground flex items-center gap-2 py-2">
            <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60" />
            No reaction at current price. Scanning {terminalValue(r?.activeLevels)} levels…
          </div>
        ) : (
          <div className="text-sm text-muted-foreground py-2">Reaction telemetry unavailable</div>
        )}
      </div>
    </Card>
  );
}

// ========================================================================
// POSITIONS
// ========================================================================
function PositionsSection({ status, onClosePosition, onPartialClose }) {
  const positionsAvailable = Array.isArray(status?.positions);
  const positions = positionsAvailable ? status.positions : [];
  const totalPnl = positionsAvailable && positions.every((position) => hasValue(position.pnl))
    ? positions.reduce((sum, position) => sum + Number(position.pnl), 0)
    : null;

  return (
    <Card testId="positions-panel">
      <div className="p-6 lg:p-8 pb-4 flex flex-col md:flex-row md:items-start md:justify-between gap-3">
        <div>
          <div className="eyebrow flex items-center gap-1.5">
            <Activity className="h-3.5 w-3.5" /> Open positions
          </div>
          <h3 className="font-semibold text-lg tracking-tight mt-1">
            {positionsAvailable ? positions.length : "—"} active
            <span className="font-normal text-muted-foreground ml-2">· floating</span>{" "}
            <span className={cls("ml-1 font-mono", hasValue(totalPnl) ? pnlTextClass(totalPnl) : "text-muted-foreground")}>
              {hasValue(totalPnl) ? `$${fmtSign(totalPnl)}` : "—"}
            </span>
          </h3>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b border-border">
              <th className="px-6 lg:px-8 py-3 eyebrow font-semibold">Ticket</th>
              <th className="px-3 py-3 eyebrow font-semibold">Side</th>
              <th className="px-3 py-3 eyebrow font-semibold text-right">Lots</th>
              <th className="px-3 py-3 eyebrow font-semibold text-right">Entry → Current</th>
              <th className="px-3 py-3 eyebrow font-semibold text-right">SL / TP</th>
              <th className="px-3 py-3 eyebrow font-semibold">Strategy</th>
              <th className="px-3 py-3 eyebrow font-semibold text-right">P&amp;L</th>
              <th className="px-6 lg:px-8 py-3 eyebrow font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-6 py-16 text-center text-muted-foreground">
                  <div className="font-semibold text-base text-foreground">{positionsAvailable ? "No open positions" : "Positions unavailable"}</div>
                  <div className="text-xs mt-1.5">{positionsAvailable ? "The EA opens trades when a strategy score ≥ session threshold" : "Waiting for position data from the EA"}</div>
                </td>
              </tr>
            ) : positions.map((p) => (
              <tr
                key={p.ticket}
                data-testid={`position-row-${p.ticket}`}
                className="border-b border-border last:border-0 hover:bg-secondary/40 transition-colors"
              >
                <td className="px-6 lg:px-8 py-4 font-mono text-xs text-muted-foreground">{p.ticket}</td>
                <td className="px-3 py-4">
                  <span className={cls(
                    "px-2.5 py-1 rounded-md text-[11px] font-bold border inline-flex items-center gap-1",
                    p.side === "BUY"
                      ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30"
                      : "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/30"
                  )}>
                    {p.side === "BUY" ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                    {p.side}
                  </span>
                </td>
                <td className="px-3 py-4 text-right font-mono">{hasValue(p.lots) ? Number(p.lots).toFixed(2) : "—"}</td>
                <td className="px-3 py-4 text-right font-mono text-xs">
                  <div>{fmtPrice(p.openPrice)}</div>
                  <div className="text-muted-foreground">→ {fmtPrice(p.currentPrice)}</div>
                </td>
                <td className="px-3 py-4 text-right font-mono text-xs">
                  <div className={NEG_TEXT}>SL {fmtPrice(p.sl)}</div>
                  <div className={POS_TEXT}>TP {fmtPrice(p.tp)}</div>
                </td>
                <td className="px-3 py-4 text-xs text-muted-foreground font-mono">{p.strategy || "—"}</td>
                <td className={cls("px-3 py-4 text-right font-mono font-bold",
                  hasValue(p.pnl) ? pnlTextClass(p.pnl) : "text-muted-foreground")}>
                  {hasValue(p.pnl) ? `${Number(p.pnl) >= 0 ? "+" : ""}$${fmtMoney(p.pnl)}` : "—"}
                </td>
                <td className="px-6 lg:px-8 py-4 text-right">
                  <div className="inline-flex gap-1.5">
                    <button
                      data-testid={`partial-close-${p.ticket}`}
                      onClick={() => onPartialClose(p)}
                      className="h-8 w-8 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-secondary flex items-center justify-center transition-colors"
                      title="Partial close 50%"
                    >
                      <Scissors className="h-3.5 w-3.5" />
                    </button>
                    <button
                      data-testid={`close-position-${p.ticket}`}
                      onClick={() => onClosePosition(p)}
                      className="h-8 w-8 rounded-lg border border-rose-500/30 text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 flex items-center justify-center transition-colors"
                      title="Close this position"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ========================================================================
// EQUITY CHART
// ========================================================================
function EquityChartSection({ status, history }) {
  const { theme } = useTheme();
  const chartData = useMemo(() => {
    if (!history?.length) return [];
    return history.map((h, i) => ({
      x: i, ts: h.ts, equity: h.equity, balance: h.balance, floatPnL: h.floatPnL,
    }));
  }, [history]);

  const fpnl = status?.floatPnL;
  const dpnl = status?.dailyPnL;
  const dd = status?.drawdownPct;

  const colors = CHART_COLORS[theme] || CHART_COLORS.dark;
  const tooltipStyle = useMemo(() => ({
    background: colors.tooltipBg,
    border: `1px solid ${colors.tooltipBorder}`,
    borderRadius: 10, fontSize: 12, color: colors.tooltipText,
  }), [colors.tooltipBg, colors.tooltipBorder, colors.tooltipText]);
  const tooltipLabelStyle = useMemo(() => ({ color: colors.tooltipText }), [colors.tooltipText]);
  const yAxisTick = useMemo(() => ({ fontSize: 11, fill: colors.axis }), [colors.axis]);
  const tooltipFormatter = useCallback((v, n) => [`$${fmtMoney(v)}`, n], []);

  return (
    <Card className="p-6 lg:p-8" testId="equity-chart-section">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-5">
        <div>
          <div className="eyebrow flex items-center gap-1.5">
            <LineChartIcon className="h-3.5 w-3.5" /> Account curve
          </div>
          <h3 className="font-semibold text-lg tracking-tight mt-1">
            Equity <span className="font-normal text-muted-foreground">vs</span> balance
          </h3>
        </div>
        <div className="flex gap-6 text-right">
          <div>
            <div className="eyebrow">Float</div>
            <div className={cls("font-mono font-bold text-base tabular mt-1", hasValue(fpnl) ? pnlTextClass(fpnl) : "text-muted-foreground")}>
              {hasValue(fpnl) ? `$${fmtSign(fpnl)}` : "—"}
            </div>
          </div>
          <div>
            <div className="eyebrow">Daily</div>
            <div className={cls("font-mono font-bold text-base tabular mt-1", hasValue(dpnl) ? pnlTextClass(dpnl) : "text-muted-foreground")}>
              {hasValue(dpnl) ? `$${fmtSign(dpnl)}` : "—"}
            </div>
          </div>
          <div>
            <div className="eyebrow">DD</div>
            <div className={cls("font-mono font-bold text-base tabular mt-1", hasValue(dd) && Number(dd) >= 3 ? NEG_TEXT : "text-foreground")}>
              {terminalValue(dd, fmtPct)}
            </div>
          </div>
        </div>
      </div>

      <div className="h-72" data-testid="equity-chart">
        {chartData.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
            <AreaChart data={chartData} margin={EQUITY_CHART_MARGIN}>
              <defs>
                <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colors.equity} stopOpacity={0.45} />
                  <stop offset="60%" stopColor={colors.equity} stopOpacity={0.12} />
                  <stop offset="100%" stopColor={colors.equity} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={colors.grid} strokeDasharray="2 6" vertical={false} />
              <XAxis dataKey="x" hide />
              <YAxis
                tick={yAxisTick}
                tickLine={false}
                axisLine={false}
                width={60}
                domain={YAXIS_DOMAIN_AUTO}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                labelStyle={tooltipLabelStyle}
                formatter={tooltipFormatter}
                cursor={{ stroke: colors.equity, strokeWidth: 1, strokeDasharray: "3 3", opacity: 0.6 }}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke={colors.equity}
                strokeWidth={2.25}
                fill="url(#eqGrad)"
                animationDuration={800}
                animationEasing="ease-out"
              />
              <Line
                type="monotone"
                dataKey="balance"
                stroke={colors.balance}
                strokeWidth={1.25}
                dot={false}
                strokeDasharray="4 4"
                animationDuration={800}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-sm text-muted-foreground scanlines rounded-xl">
            <span className="font-mono tracking-wide opacity-70 blink">◉ Collecting snapshots — EA pushes every 5s</span>
          </div>
        )}
      </div>
    </Card>
  );
}

// ========================================================================
// ========================================================================
// QUICK STRATEGIES (home) — v2.0.7b: 35 strategies grouped by family
// ========================================================================
function QuickStrategies({ settings, onSave }) {
  const enabled = settings?.strategies || Object.fromEntries(STRAT_LIST.map(([k]) => [k, true]));
  const activeCount = Object.values(enabled).filter(Boolean).length;
  const total = STRAT_LIST.length;
  const grouped = STRAT_FAMILIES.map((fam) => ({
    ...fam,
    items: STRAT_LIST.filter(([, , f]) => f === fam.id),
  }));
  return (
    <Card className="p-6 lg:p-8" testId="quick-strategies">
      <SectionHeader
        eyebrow="Strategies"
        title={
          <>
            {activeCount} <span className="font-normal text-muted-foreground">of {total} active</span>
          </>
        }
        icon={Cpu}
        right={
          <Link
            to="/strategies"
            className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
            data-testid="strategies-link"
          >
            Manage <ChevronRight className="h-3 w-3" />
          </Link>
        }
      />
      <div className="space-y-4">
        {grouped.map((fam) => {
          const famActive = fam.items.filter(([k]) => enabled[k]).length;
          return (
            <div key={fam.id} data-testid={`quick-strategy-family-${fam.id}`}>
              <div className="flex items-center justify-between mb-1.5">
                <div className={cls(
                  "inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.1em] px-2 py-0.5 rounded border",
                  STRAT_FAMILY_COLOR[fam.id]
                )}>
                  {fam.label}
                  <span className="font-mono opacity-70">{famActive}/{fam.items.length}</span>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2">
                {fam.items.map(([k, label]) => {
                  const on = !!enabled[k];
                  return (
                    <button
                      key={k}
                      onClick={() => {
                        const next = { ...enabled, [k]: !on };
                        onSave({ strategies: next });
                      }}
                      data-testid={`quick-strategy-${k.toLowerCase()}`}
                      title={label}
                      className={cls(
                        "text-left px-2.5 py-2 rounded-lg border text-[10px] font-semibold transition-all duration-200 active:scale-[0.97]",
                        on
                          ? "bg-primary/10 text-primary border-primary/30 shadow-[0_0_12px_hsl(var(--primary)/0.15)]"
                          : "bg-secondary/40 text-muted-foreground border-border hover:border-primary/30 hover:text-foreground"
                      )}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className={cls(
                          "h-1.5 w-1.5 rounded-full flex-shrink-0",
                          on ? "bg-emerald-400 glow-success" : "bg-muted-foreground/40"
                        )} />
                        <span className="truncate font-mono">{k.replace(/_/g, " ")}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

// ========================================================================
// GATE / WHY NO TRADE
// ========================================================================
const SESSION_SCORE_MAP = { ASIAN: 80, LONDON: 65, OVERLAP: 60, NY: 65, AFTERNY: 80 };

function resolveSessionMinScore(status, settings) {
  const session = status?.session;
  const overrideKey = {
    ASIAN: "AsianScoreMin", LONDON: "LondonScoreMin", OVERLAP: "OverlapScoreMin",
    NY: "NYScoreMin", AFTERNY: "AfterNYScoreMin",
  }[session];
  const sessionVal = overrideKey ? settings?.[overrideKey] : undefined;
  if (sessionVal != null) return sessionVal;
  if (SESSION_SCORE_MAP[session] != null) return SESSION_SCORE_MAP[session];
  return settings?.MinEntryScore ?? DEFAULT_SETTINGS.MinEntryScore;
}

function checkHtfBias(status, reactDir, wantBuy, wantSell, dirLabel) {
  if (!reactDir) {
    return { name: "HTF bias", ok: null, detail: "Awaiting reaction direction", hint: null };
  }
  const bias = status.htfBias;
  const aligned = bias === "NEUTRAL" || (wantBuy && bias === "BULL") || (wantSell && bias === "BEAR");
  const counter = (wantBuy && bias === "BEAR") || (wantSell && bias === "BULL");
  return {
    name: "HTF bias",
    ok: aligned,
    detail: `HTF=${bias} vs intent=${dirLabel}`,
    hint: counter ? "Counter-trend trade — blocked unless price is within 0.6×ATR of yesterday H/L" : null,
  };
}

function checkVelocity(status, reactDir, wantBuy, wantSell) {
  const v = status.velocity;
  let ok = null;
  if (reactDir) {
    ok = (wantBuy && (v === "BULL" || v === "BULL_PB")) ||
         (wantSell && (v === "BEAR" || v === "BEAR_PB"));
  }
  return {
    name: "Velocity",
    ok,
    detail: `Velocity=${v || "—"}`,
    hint: v === "NEUTRAL" ? "ZLEMA slope inside ±0.5×ATR band — no momentum confirmation" : null,
  };
}

function checkNews(status) {
  if (typeof status.newsBlock !== "boolean") {
    return { name: "News filter", ok: null, detail: "Unavailable", hint: null };
  }
  return {
    name: "News filter",
    ok: !status.newsBlock,
    detail: status.newsBlock ? "Blocking high-impact news" : "Open",
    hint: status.newsBlock ? "Wait until news event clears (±30 min default)" : null,
  };
}

function checkPaused(status) {
  if (typeof status.eaPaused !== "boolean") {
    return { name: "EA paused", ok: null, detail: "Unavailable", hint: null };
  }
  return {
    name: "EA paused",
    ok: !status.eaPaused,
    detail: status.eaPaused ? "Paused via dashboard" : "Running",
    hint: status.eaPaused ? "Press Resume EA in the Command Center" : null,
  };
}

function checkConcurrent(status, settings) {
  const cur = Array.isArray(status.positions) ? status.positions.length : null;
  const max = settings?.MaxConcurrent ?? DEFAULT_SETTINGS.MaxConcurrent;
  return { name: "Max concurrent", ok: hasValue(cur) ? cur < max : null, detail: `${terminalValue(cur)} / ${max}`, hint: null };
}

function checkDailyTrades(status, settings) {
  const cur = status.tradesToday;
  const max = settings?.MaxTradesPerDay ?? DEFAULT_SETTINGS.MaxTradesPerDay;
  return { name: "Daily trades", ok: hasValue(cur) ? cur < max : null, detail: `${terminalValue(cur)} / ${max}`, hint: null };
}

function checkScore(status, sessionMinScore) {
  if (status.reactionDetected) {
    const q = hasValue(status.reactionQuality) ? Math.round(status.reactionQuality) : null;
    return {
      name: `Score ≥ ${sessionMinScore} (${status.session || "—"})`,
      ok: null,
      detail: hasValue(q) ? `Reaction Q=${q} · final score telemetry unavailable` : "Score telemetry unavailable",
      hint: null,
    };
  }
  return {
    name: `Score ≥ ${sessionMinScore} (${status.session || "—"})`,
    ok: null,
    detail: "No reaction — score depends on K/H strategies",
    hint: null,
  };
}

function GateRow({ check }) {
  const style = gateStyleFor(check.ok);
  return (
    <div className={cls("flex items-start gap-3 px-4 py-3 rounded-xl border text-xs", style.container)}>
      <div className={cls(
        "h-5 w-5 rounded-full flex-shrink-0 flex items-center justify-center text-[10px] font-bold mt-0.5",
        style.badge
      )}>
        {style.icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-foreground">{check.name}</div>
        <div className="text-muted-foreground font-mono text-[11px] mt-0.5">{check.detail}</div>
        {check.hint && (
          <div className="text-[10px] text-muted-foreground/80 mt-1 italic">→ {check.hint}</div>
        )}
      </div>
    </div>
  );
}

function WhyNoTradeHeader({ blocking, reactDir, dirLabel, wantBuy }) {
  if (blocking.length === 0 && reactDir !== 0) {
    return <span className={POS_TEXT}>All gates clear — awaiting bar close</span>;
  }
  if (reactDir === 0) {
    return <span className="text-muted-foreground">No active reaction · gates idle</span>;
  }
  return (
    <>
      {blocking.length} gate{blocking.length > 1 ? "s" : ""} blocking{" "}
      <span className="text-muted-foreground font-normal">a</span>{" "}
      <span className={wantBuy ? POS_TEXT : NEG_TEXT}>{dirLabel}</span>{" "}
      <span className="text-muted-foreground font-normal">entry</span>
    </>
  );
}

function WhyNoTrade({ status, settings }) {
  if (!status) return null;

  const sessionMinScore = resolveSessionMinScore(status, settings);
  const reactDir = status.reactionDetected ? status.reactionDir : 0;
  const wantBuy = reactDir === 1;
  const wantSell = reactDir === -1;
  let dirLabel = "—";
  if (wantBuy) dirLabel = "BUY";
  else if (wantSell) dirLabel = "SELL";

  // Mostra solo i gate effettivamente applicati dall'EA: HTF bias, velocity e
  // news sono opzionali (di default HTF/velocity sono OFF nell'EA). Includerli
  // sempre faceva apparire "blocchi" che l'EA non stava applicando davvero.
  const checks = [
    ...(settings?.UseHTFBias ? [checkHtfBias(status, reactDir, wantBuy, wantSell, dirLabel)] : []),
    ...(settings?.UseVelocityGate ? [checkVelocity(status, reactDir, wantBuy, wantSell)] : []),
    ...(settings?.UseNewsFilter ? [checkNews(status)] : []),
    checkPaused(status),
    checkConcurrent(status, settings),
    checkDailyTrades(status, settings),
    checkScore(status, sessionMinScore),
  ];

  const blocking = checks.filter((c) => c.ok === false);

  return (
    <Card className="p-6 lg:p-8" testId="why-no-trade">
      <SectionHeader
        eyebrow="Trade gate diagnostics"
        icon={ShieldAlert}
        title={
          <WhyNoTradeHeader
            blocking={blocking}
            reactDir={reactDir}
            dirLabel={dirLabel}
            wantBuy={wantBuy}
          />
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
        {checks.map((c) => (
          <GateRow key={c.name} check={c} />
        ))}
      </div>
    </Card>
  );
}

function ResearchSnapshot() {
  const links = [
    ["Backtest", "/backtest", LineChartIcon],
    ["Strategy Analytics", "/strategy-analytics", Layers],
    ["Optimizer", "/optimizer", Gauge],
    ["What-if", "/whatif", GitBranch],
  ];
  return (
    <section>
      <SectionHeader title="Research" subtitle="Experiments & validation" />
      <Card className="p-3 sm:p-4">
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {links.map(([label, to, Icon]) => (
            <Link key={to} to={to} className="group flex min-w-0 items-center justify-between gap-3 rounded-lg border border-border bg-secondary/30 px-3 py-3 transition-colors hover:border-primary/40 hover:bg-secondary">
              <span className="flex min-w-0 items-center gap-2.5"><Icon size={14} className="shrink-0 text-primary" /><span className="truncate text-xs font-semibold text-foreground">{label}</span></span>
              <ChevronRight size={13} className="shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
            </Link>
          ))}
        </div>
      </Card>
    </section>
  );
}

// ========================================================================
// HOME PAGE (default export)
// ========================================================================
export default function HomePage({ status, history, settings, health, onCmd, onSaveSettings }) {
  const isDemo = status?.demo === true || health?.demo === true;

  return (
    <div className="space-y-6 fade-in">
      {isDemo && (
        <div
          data-testid="demo-banner"
          className="rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 px-4 py-3 text-sm flex items-center gap-2"
        >
          <Sparkles className="h-4 w-4 flex-shrink-0" />
          <span><b>DEMO data</b> — real EA pushes (online: true) will replace this view automatically.</span>
        </div>
      )}

      <SystemStatusStrip status={status} health={health} />
      <CoreMetrics status={status} />
      <ExecutionPipeline status={status} />

      <section>
        <SectionHeader title="Market intelligence" subtitle="Regime, structure and reaction state" />
        <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
          <MarketIntelligence status={status} />
          <StructureSection status={status} />
          <ReactionSection status={status} />
        </div>
      </section>

      <PositionsSection
        status={status}
        onClosePosition={(p) => onCmd("close_position", { ticket: p.ticket }, true, {
          title: `Close position #${p.ticket}?`,
          body: `Sells/buys the position at market. Side: ${p.side}, lots: ${p.lots}, current P&L: $${fmtSign(p.pnl)}.`,
        })}
        onPartialClose={(p) => onCmd("partial_close", { ticket: p.ticket, volume: +(p.lots * 0.5).toFixed(2) }, true, {
          title: `Partial close 50% of #${p.ticket}?`,
          body: `Closes ${+(p.lots * 0.5).toFixed(2)} lots (of ${p.lots}). The remaining position keeps its SL/TP.`,
          danger: false,
          confirmLabel: "Close 50%",
        })}
      />

      <ResearchSnapshot />

      <section>
        <SectionHeader title="System health" subtitle="Backend and bridge diagnostics" />
        <HealthScoreCard health={health} compact />
      </section>

      <section>
        <SectionHeader title="Operational controls" subtitle="Existing account controls and diagnostics" />
        <div className="space-y-4">
          <LockedProfileBanner />
          <CommandCenter status={status} onCmd={onCmd} />
          <EquityChartSection status={status} history={history} />
          <WhyNoTrade status={status} settings={settings} />
          <QuickStrategies settings={settings} onSave={onSaveSettings} />
        </div>
      </section>
    </div>
  );
}
