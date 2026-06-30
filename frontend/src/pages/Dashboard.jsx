import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import {
  Settings as SettingsIcon,
  ShieldAlert, Clock, Target,
  Menu, FileDown, HelpCircle,
  Gauge, Command as CommandIcon,
  Sun, Moon,
} from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import LicensesPage from "@/pages/Licenses";
import CoachPage from "@/pages/Coach";
import JournalPage from "@/pages/Journal";
import RiskCalcPage from "@/pages/RiskCalc";
import BacktestPage from "@/pages/Backtest";
import CalendarPage from "@/pages/CalendarPage";
import LocalBridgePage from "@/pages/LocalBridgePage";
import StrategyChainPage from "@/pages/StrategyChainPage";
import SetupWizard, { shouldShowWizard, resetWizard } from "@/components/SetupWizard";
import NotificationBell from "@/components/NotificationBell";
import LicenseBanner from "@/components/LicenseBanner";
import CoachLiveWidget from "@/components/CoachLiveWidget";
import Sidebar from "@/components/Sidebar";
import BottomNav from "@/components/BottomNav";
import CommandPalette from "@/components/CommandPalette";
import HomePage from "@/pages/dashboard/HomePage";
import StrategiesPage from "@/pages/dashboard/StrategiesPage";
import OptimizerPage from "@/pages/dashboard/OptimizerPage";
import StrategyAnalyticsPage from "@/pages/dashboard/StrategyAnalyticsPage";
import AnalyticsPage from "@/pages/dashboard/AnalyticsPage";
import WhatIfPage from "@/pages/dashboard/WhatIfPage";
import HealthScoreCard from "@/pages/dashboard/HealthScoreCard";
import TradeLifecycleDrawer from "@/pages/dashboard/TradeLifecycleDrawer";
import {
  Card, ConfirmDialog, SectionHeader,
  cls, fmtMoney, fmtSign,
  POS_TEXT, NEG_TEXT, pnlTextClass,
} from "@/pages/dashboard/shared";

// ========================================================================
// PAGE HEADER
// ========================================================================
function PageHeader({ status, onMenu, onExportPdf, onShowHelp, onOpenCmd }) {
  const { theme, toggle } = useTheme();
  const paused = !!status?.eaPaused;
  const online = !!status?.online;
  const equity = status?.equity ?? 0;
  const balance = status?.balance ?? 0;

  return (
    <header
      data-testid="page-header"
      className="bg-card/70 backdrop-blur-xl border-b border-border px-4 lg:px-8 py-4 sticky top-0 z-30"
    >
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onMenu}
            data-testid="menu-toggle"
            aria-label="Open navigation"
            className="lg:hidden h-10 w-10 rounded-lg border border-border flex items-center justify-center hover:bg-secondary active:scale-95 transition-transform"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="min-w-0">
            <div className="eyebrow font-mono tabular">
              {status?.symbol || "XAUUSD"} · MAGIC {status?.magic ?? "—"}
            </div>
            <div className="flex items-center gap-3 mt-1">
              <span className="font-semibold text-xl tracking-tight">
                {paused
                  ? <span className="text-amber-400">Paused</span>
                  : <span className="text-foreground">Running</span>
                }
              </span>
              <span
                data-testid="online-badge"
                className={cls(
                  "px-2.5 py-0.5 rounded-full text-[10px] font-bold border flex items-center gap-1.5 font-mono tracking-wider",
                  online
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                    : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                )}
              >
                <span className="relative flex h-1.5 w-1.5">
                  <span className={cls(
                    "relative inline-flex h-1.5 w-1.5 rounded-full",
                    online ? "bg-emerald-400 glow-success" : "bg-amber-400 glow-warning"
                  )} />
                  {online && (
                    <span className="absolute inline-flex h-1.5 w-1.5 rounded-full pulse-ring text-emerald-400" />
                  )}
                </span>
                {online ? "LIVE" : "DEMO"}
              </span>
            </div>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-6 px-5 py-2.5 rounded-xl bg-secondary/40 border border-border backdrop-blur-sm">
          <div>
            <div className="eyebrow">Equity</div>
            <div className="font-mono font-bold text-lg tabular leading-none mt-1 text-foreground">${fmtMoney(equity)}</div>
          </div>
          <div className="h-8 w-px bg-border" />
          <div>
            <div className="eyebrow">Balance</div>
            <div className="font-mono font-bold text-lg tabular leading-none mt-1 text-muted-foreground">
              ${fmtMoney(balance)}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <LicenseBanner />
          {onOpenCmd && (
            <button
              onClick={onOpenCmd}
              title="Command palette (⌘K)"
              data-testid="header-cmdk-btn"
              className="hidden md:inline-flex h-9 px-3 rounded-lg border border-border hover:border-primary/40 hover:bg-secondary/60 text-xs items-center gap-2 text-muted-foreground hover:text-foreground transition-colors group"
            >
              <CommandIcon className="h-3.5 w-3.5 group-hover:text-primary transition-colors" />
              <span className="font-mono">Search</span>
              <kbd className="ml-1 px-1.5 py-0.5 rounded bg-background border border-border text-[10px] font-mono group-hover:border-primary/40">⌘K</kbd>
            </button>
          )}
          <button onClick={toggle}
                  title={theme === "dark" ? "Tema chiaro" : "Tema scuro"}
                  aria-label="Cambia tema"
                  data-testid="header-theme-toggle"
                  className="h-9 w-9 rounded-lg border border-border hover:bg-secondary flex items-center justify-center">
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          <NotificationBell />
          {onExportPdf && (
            <button onClick={onExportPdf} title="Esporta PDF tear-sheet"
                    className="h-9 px-3 rounded-lg border border-border hover:bg-secondary text-xs flex items-center gap-1.5"
                    data-testid="header-export-pdf-btn">
              <FileDown className="h-3.5 w-3.5"/>
              <span className="hidden md:inline">PDF</span>
            </button>
          )}
          {onShowHelp && (
            <button onClick={onShowHelp} title="Apri tour guidato"
                    className="h-9 w-9 rounded-lg border border-border hover:bg-secondary flex items-center justify-center"
                    data-testid="header-help-btn">
              <HelpCircle className="h-4 w-4"/>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

// ========================================================================
// RISK CENTER PAGE
// ========================================================================
function ProgressBar({ value, max, tone = "neutral" }) {
  const pct = Math.max(0, Math.min(100, (Math.abs(value) / Math.abs(max || 1)) * 100));
  const colors = {
    pos:     "bg-emerald-500",
    neg:     "bg-rose-500",
    warn:    "bg-amber-500",
    info:    "bg-sky-500",
    neutral: "bg-muted-foreground",
  };
  return (
    <div className="h-2 rounded-full bg-secondary overflow-hidden">
      <div
        className={cls("h-full rounded-full transition-all duration-500", colors[tone] || colors.neutral)}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function RiskBudgetRow({ label, used, limit, fmt, hint, testId }) {
  const usedFmt = fmt ? fmt(used) : used;
  const limitFmt = fmt ? fmt(limit) : limit;
  const pct = limit > 0 ? (Math.abs(used) / Math.abs(limit)) * 100 : 0;
  let tone = "pos";
  if (pct >= 90) tone = "neg";
  else if (pct >= 70) tone = "warn";
  let valueColor = POS_TEXT;
  if (tone === "neg") valueColor = NEG_TEXT;
  else if (tone === "warn") valueColor = "text-amber-600 dark:text-amber-400";
  return (
    <div data-testid={testId} className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="font-semibold text-sm">{label}</div>
          {hint && <div className="text-[11px] text-muted-foreground mt-0.5">{hint}</div>}
        </div>
        <div className="text-right font-mono text-xs">
          <span className={cls("font-bold text-base", valueColor)}>{usedFmt}</span>
          <span className="text-muted-foreground"> / {limitFmt}</span>
          <div className="text-[10px] text-muted-foreground mt-0.5">{Math.round(pct)}% used</div>
        </div>
      </div>
      <ProgressBar value={Math.abs(used)} max={Math.abs(limit)} tone={tone} />
    </div>
  );
}

function RiskCenterPage({ status, settings, health }) {
  if (!status || !settings) {
    return <div className="text-muted-foreground text-sm">Loading risk panel…</div>;
  }
  const positions = status.positions || [];
  const maxConcurrent = settings.MaxConcurrent ?? 4;
  const maxTrades = settings.MaxTradesPerDay ?? 12;
  const maxDD = settings.MaxDailyDDPct ?? 3;
  const eslLimitPct = settings.ESL_IsPercent ? settings.ESL_Value : 5;
  const dptTargetPct = settings.DPT_IsPercent ? settings.DPT_Value : 3;
  const antiRevLosses = settings.AntiRevengeLosses ?? 3;
  const consecLosses = status.consecLosses ?? 0;
  const maxHold = settings.MaxHoldHours ?? 12;
  const positionsHeld = positions.map((p) => {
    if (!p.openTime) return 0;
    const opened = new Date(p.openTime).getTime();
    return (Date.now() - opened) / (1000 * 3600);
  });
  const longestHold = positionsHeld.length ? Math.max(...positionsHeld) : 0;

  return (
    <div className="space-y-6 fade-in" data-testid="risk-center-page">
      <Card className="p-6 lg:p-8 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <div className="eyebrow flex items-center gap-1.5">
            <ShieldAlert className="h-3.5 w-3.5" /> Risk control
          </div>
          <h2 className="text-2xl font-semibold tracking-tight mt-1">Live budget vs limits</h2>
          <p className="text-sm text-muted-foreground mt-1.5">
            Everything that can stop the EA — visualised against its hard limit.
          </p>
        </div>
        <div className="flex gap-6">
          <div className="text-right">
            <div className="eyebrow">Equity</div>
            <div className="font-mono font-bold text-lg tabular mt-1">${fmtMoney(status.equity)}</div>
          </div>
          <div className="text-right">
            <div className="eyebrow">Float</div>
            <div className={cls("font-mono font-bold text-lg tabular mt-1", pnlTextClass(status.floatPnL))}>
              ${fmtSign(status.floatPnL)}
            </div>
          </div>
        </div>
      </Card>

      <HealthScoreCard health={health} compact={false} />

      <Card className="p-6 lg:p-8" testId="risk-budgets">
        <SectionHeader eyebrow="Budgets vs limits" title="How close are we to a hard stop?" icon={Gauge} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-10 gap-y-6">
          <RiskBudgetRow label="Daily drawdown" used={status.drawdownPct ?? 0} limit={maxDD}
            fmt={(v) => `${Number(v).toFixed(2)}%`}
            hint="EA pauses when daily DD reaches MaxDailyDDPct"
            testId="rb-daily-dd" />
          <RiskBudgetRow label="Equity Stop Loss (ESL)" used={Math.abs(status.floatPnLPct ?? 0)} limit={eslLimitPct}
            fmt={(v) => `${Number(v).toFixed(2)}%`}
            hint="Closes all positions when floating loss hits"
            testId="rb-esl" />
          <RiskBudgetRow label="Daily Profit Target (DPT)" used={status.dailyPnLPct ?? 0} limit={dptTargetPct}
            fmt={(v) => `${Number(v).toFixed(2)}%`}
            hint="Closes & pauses for the day when reached"
            testId="rb-dpt" />
          <RiskBudgetRow label="Concurrent positions" used={positions.length} limit={maxConcurrent}
            fmt={(v) => `${v}`}
            hint="Hard cap to control margin exposure"
            testId="rb-concurrent" />
          <RiskBudgetRow label="Trades today" used={status.tradesToday ?? 0} limit={maxTrades}
            fmt={(v) => `${v}`}
            hint="EA stops opening new entries after this"
            testId="rb-trades-today" />
          <RiskBudgetRow label="Anti-revenge losses" used={consecLosses} limit={antiRevLosses}
            fmt={(v) => `${v}`}
            hint="Forces cooldown after N consecutive losses"
            testId="rb-anti-revenge" />
          <RiskBudgetRow label="Longest position hold" used={Math.round(longestHold)} limit={maxHold}
            fmt={(v) => `${v}h`}
            hint="Auto-close on positions held too long"
            testId="rb-max-hold" />
          {/* Margin level: when no open positions the broker reports 0 → show "—" instead of rosso. */}
          {status.marginLevel == null || status.marginLevel === 0 ? (
            <RiskBudgetRow label="Margin level" used={0} limit={1000}
              fmt={() => "—"}
              hint="Nessuna posizione aperta · nessun margine impegnato"
              testId="rb-margin" />
          ) : (
            <RiskBudgetRow label="Margin level" used={Math.max(0, 1000 - status.marginLevel)} limit={1000}
              fmt={(v) => `${(1000 - v).toFixed(0)}%`}
              hint="Above 200% is safe · below 100% = margin call"
              testId="rb-margin" />
          )}
        </div>
      </Card>

      {status.strategyCooldowns && Object.keys(status.strategyCooldowns).length > 0 && (
        <Card className="p-6 lg:p-8" testId="strategy-cooldown-card">
          <SectionHeader eyebrow="Per-strategy cooldown" title="Active cooldowns" icon={Clock} />
          <div className="space-y-2">
            {Object.entries(status.strategyCooldowns).map(([name, info]) => {
              const until = info?.untilTs ? new Date(info.untilTs * 1000) : null;
              const remainingMin = until ? Math.max(0, (until - Date.now()) / 60000) : 0;
              const active = remainingMin > 0;
              return (
                <div key={name}
                     className={cls(
                       "flex items-center justify-between px-4 py-3 rounded-xl border text-sm",
                       active ? "bg-amber-500/10 border-amber-500/30" : "bg-secondary/40 border-border"
                     )}>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs">{name}</span>
                    <span className="text-[10px] text-muted-foreground">consec={info.consec ?? 0}</span>
                  </div>
                  <span className={cls("font-mono text-xs",
                    active ? "text-amber-700 dark:text-amber-400" : "text-muted-foreground")}>
                    {active ? `${Math.round(remainingMin)}m left` : "ready"}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}

// ========================================================================
// SETTINGS PAGE
// ========================================================================
const SETTINGS_FIELDS = [
  ["RiskPercent", "Risk per trade (%)"],
  ["MaxLot", "Max lot size"],
  ["MaxTradesPerDay", "Max trades / day"],
  ["MaxConcurrent", "Max concurrent positions"],
  ["MaxDailyDDPct", "Max daily DD (%)"],
  ["MinEntryScore", "Min entry score"],
  ["ATR_SL_Mult", "ATR SL multiplier"],
  ["ATR_TP_Mult", "ATR TP multiplier"],
  ["BE_TriggerATR", "BE trigger (ATR)"],
  ["TrailActivateATR", "Trail activate (ATR)"],
  ["TrailDistanceATR", "Trail distance (ATR)"],
  ["AsianScoreMin", "Asian session min score"],
  ["LondonScoreMin", "London session min score"],
  ["OverlapScoreMin", "Overlap session min score"],
  ["NYScoreMin", "NY session min score"],
  ["AfterNYScoreMin", "After-NY session min score"],
  ["AntiRevengeLosses", "Anti-revenge losses"],
  ["AntiRevengeMin", "Anti-revenge cooldown (min)"],
  ["SwingWing", "Swing wing (fractal)"],
  ["OBDisplacement", "OB displacement (ATR)"],
  ["FVGMinBody", "FVG min body (ATR)"],
  ["ReactionTol", "Reaction tolerance (ATR)"],
  ["ESL_Value", "ESL · Equity SL value"],
  ["DPT_Value", "DPT · Daily target value"],
  ["MaxHoldHours", "Max hold (hours)"],
  ["MaxLossPosPct", "Max loss / position (%)"],
  ["AutoCloseMin", "Auto-close before market (min)"],
  ["MarketCloseGMT", "Market close hour (GMT)"],
  ["ConfluenceBonus2", "Confluence bonus (2 strat)"],
  ["ConfluenceBonus3", "Confluence bonus (3 strat)"],
  ["ConfluenceBonus4", "Confluence bonus (4+ strat)"],
  ["ADXRsiScoreCap", "ADX_RSI score cap"],
  ["MaxConsecPerStrategy", "Max consec / strategy"],
  ["StrategyCooldownMin", "Strategy cooldown (min)"],
  ["MaxSpreadAtrPct", "Max spread (% of ATR)"],
  ["MaxSpreadPoints", "Max spread (points)"],
  ["LowVolAtrPct", "Low vol threshold (ATR%)"],
  ["HighVolAtrPct", "High vol threshold (ATR%)"],
];
const SETTINGS_BOOLS = [
  ["UseHTFBias", "HTF Bias gate"],
  ["UseVelocityGate", "Velocity gate"],
  ["UseNewsFilter", "News filter"],
  ["UseAMD", "AMD model"],
  ["UseBSP", "Buyer/Seller Pressure"],
  ["UseSessions", "Session thresholds"],
  ["UseStructure", "Structure engine"],
  ["UseReaction", "Reaction engine"],
  ["UseStructReact", "Structure Reaction (FVG/OB trigger engine)"],
  ["EnableCloseAndReverse", "Close & Reverse"],
  ["UseESL", "Equity Stop Loss (ESL)"],
  ["ESL_IsPercent", "ESL value is percent"],
  ["UseDPT", "Daily Profit Target (DPT)"],
  ["DPT_IsPercent", "DPT value is percent"],
  ["UseMaxHold", "Max hold time per position"],
  ["UseMaxLossPos", "Max loss per position"],
  ["UseAutoClose", "Auto-close before market"],
  ["UseConfluence", "Confluence scoring"],
  ["UseStrategyCooldown", "Per-strategy cooldown"],
  ["UseMTFValidation", "MTF (H1+H4) validation"],
  ["UseDynamicSpread", "Dynamic spread filter"],
  ["UseVolatilityRegime", "Volatility regime detection"],
];

function SettingsPage({ settings, onSave }) {
  const [local, setLocal] = useState(settings || {});
  const [history, setHistory] = useState([]);
  const change = (k, v) => setLocal((s) => ({ ...s, [k]: v }));

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const { data } = await api.get("/settings/history?limit=50");
        if (alive) setHistory(data);
      } catch (e) { console.warn("settings history load failed", e); }
    };
    load();
    const id = setInterval(load, 10000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const handleSave = async () => {
    await onSave(local);
    try {
      const { data } = await api.get("/settings/history?limit=50");
      setHistory(data);
    } catch (e) { console.warn("settings history refresh failed", e); }
  };

  return (
    <div className="space-y-6 fade-in">
      <Card className="p-6 lg:p-8 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <div className="eyebrow flex items-center gap-1.5">
            <SettingsIcon className="h-3.5 w-3.5" /> Configuration
          </div>
          <h2 className="text-2xl font-semibold tracking-tight mt-1">
            Settings <span className="font-normal text-muted-foreground">· risk &amp; gates</span>
          </h2>
        </div>
        <button
          data-testid="save-settings-button"
          onClick={handleSave}
          className="h-11 px-6 rounded-lg bg-primary text-primary-foreground text-sm font-semibold transition-all shadow-[0_0_18px_hsl(var(--primary)/0.35)] hover:shadow-[0_0_28px_hsl(var(--primary)/0.55)] hover:brightness-110 active:scale-[0.98]"
        >
          Save settings
        </button>
      </Card>

      <Card className="p-6 lg:p-8">
        <div className="eyebrow mb-5">Numeric parameters</div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {SETTINGS_FIELDS.map(([k, label]) => (
            <div key={k}>
              <label className="text-sm font-medium mb-1.5 block">{label}</label>
              <input
                data-testid={`setting-${k}`}
                type="number"
                step="0.01"
                value={local[k] ?? ""}
                onChange={(e) => change(k, parseFloat(e.target.value))}
                className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring font-mono text-sm transition-shadow"
              />
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-6 lg:p-8">
        <div className="eyebrow mb-5">Intelligent gates</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {SETTINGS_BOOLS.map(([k, label]) => {
            const on = !!local[k];
            return (
              <div key={k} className="flex items-center justify-between border border-border rounded-xl px-4 py-3.5 bg-secondary/40">
                <div className="flex items-center gap-3">
                  <Target className="h-4 w-4 text-muted-foreground" />
                  <div className="text-sm font-medium">{label}</div>
                </div>
                <button
                  data-testid={`setting-bool-${k}`}
                  role="switch"
                  aria-checked={on}
                  onClick={() => change(k, !on)}
                  className={cls(
                    "relative h-6 w-11 rounded-full transition-all",
                    on
                      ? "bg-primary shadow-[0_0_12px_hsl(var(--primary)/0.5)]"
                      : "bg-muted border border-border"
                  )}
                >
                  <span className={cls(
                    "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform",
                    on ? "translate-x-5" : "translate-x-0.5"
                  )} />
                </button>
              </div>
            );
          })}
        </div>
      </Card>

      <Card testId="settings-history-card">
        <div className="p-6 lg:p-8 pb-4">
          <div className="eyebrow flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" /> Change history
          </div>
          <h3 className="font-semibold text-lg tracking-tight mt-1">
            {history.length} <span className="font-normal text-muted-foreground">recorded changes</span>
          </h3>
          <p className="text-xs text-muted-foreground mt-1.5">
            Every save logs old → new value. Useful to correlate setting changes with performance after.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-border">
                <th className="px-6 lg:px-8 py-3 eyebrow font-semibold">When</th>
                <th className="px-3 py-3 eyebrow font-semibold">User</th>
                <th className="px-3 py-3 eyebrow font-semibold">Key</th>
                <th className="px-3 py-3 eyebrow font-semibold text-right">From</th>
                <th className="px-6 lg:px-8 py-3 eyebrow font-semibold text-right">To</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr><td colSpan={5} className="px-6 py-10 text-center text-muted-foreground text-sm">
                  No changes recorded yet. Save any setting to log it here.
                </td></tr>
              ) : history.flatMap((row) => {
                const ts = row.ts ? new Date(row.ts).toLocaleString() : "—";
                return Object.entries(row.changes || {}).map(([key, diff]) => (
                  <tr key={`${row.ts}-${key}`}
                      data-testid={`history-row-${key}`}
                      className="border-b border-border last:border-0 hover:bg-secondary/40">
                    <td className="px-6 lg:px-8 py-3 text-xs text-muted-foreground font-mono whitespace-nowrap">{ts}</td>
                    <td className="px-3 py-3 text-xs text-muted-foreground">{row.user || "—"}</td>
                    <td className="px-3 py-3 font-mono text-xs text-foreground">{key}</td>
                    <td className="px-3 py-3 text-right font-mono text-xs text-muted-foreground">
                      {diff.from === null || diff.from === undefined ? "—" : JSON.stringify(diff.from)}
                    </td>
                    <td className="px-6 lg:px-8 py-3 text-right font-mono text-xs font-bold text-sky-600 dark:text-sky-400">
                      {JSON.stringify(diff.to)}
                    </td>
                  </tr>
                ));
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// ========================================================================
// SHELL
// ========================================================================
export default function Dashboard({ section = "home" }) {
  const { user, checking } = useAuth();
  const [status, setStatus] = useState(null);
  const [settings, setSettings] = useState(null);
  const [history, setHistory] = useState([]);
  const [summary, setSummary] = useState(null);
  const [trades, setTrades] = useState([]);
  const [heatmap, setHeatmap] = useState(null);
  const [byReason, setByReason] = useState(null);
  const [calendar, setCalendar] = useState(null);
  const [correlation, setCorrelation] = useState(null);
  const [health, setHealth] = useState(null);
  const [selectedTrade, setSelectedTrade] = useState(null);
  const [dialog, setDialog] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);

  // Global Cmd+K / Ctrl+K listener
  useEffect(() => {
    const onKey = (e) => {
      const meta = e.metaKey || e.ctrlKey;
      if (meta && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        setCmdOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (user && shouldShowWizard()) setWizardOpen(true);
  }, [user]);

  const downloadTearsheet = async () => {
    try {
      const apiBase = process.env.REACT_APP_BACKEND_URL;
      const r = await fetch(`${apiBase}/api/report/tearsheet.pdf`, { credentials: "include" });
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `NEXUS_tearsheet_${new Date().toISOString().slice(0,10)}.pdf`;
      document.body.appendChild(a); a.click();
      URL.revokeObjectURL(url); a.remove();
    } catch (e) { console.error("PDF download failed", e); }
  };

  const fetchAll = async () => {
    try {
      const [s, h, st, sm, tr, hm, br, cal, corr, hl] = await Promise.all([
        api.get("/ea/status"),
        api.get("/ea/history?limit=120"),
        api.get("/settings"),
        api.get("/analytics/summary"),
        api.get("/analytics/trades?limit=30"),
        api.get("/analytics/heatmap"),
        api.get("/analytics/by_reason"),
        api.get("/analytics/calendar?days=365"),
        api.get("/analytics/correlation"),
        api.get("/ea/health"),
      ]);
      // v2.0.9 — propagate semantic bridge state from /api/ea/health into status
      const bridgeCheck = (hl.data?.checks || []).find((c) => c.key === "bridge");
      setStatus({ ...s.data, bridgeState: bridgeCheck?.state || null });
      setHistory(h.data);
      setSettings(st.data);
      setSummary(sm.data);
      setTrades(tr.data);
      setHeatmap(hm.data);
      setByReason(br.data);
      setCalendar(cal.data);
      setCorrelation(corr.data);
      setHealth(hl.data);
    } catch (e) {
      if (e?.response?.status !== 401) {
        console.warn("[dashboard] fetchAll failed:", e?.message || e);
      }
    }
  };

  useEffect(() => {
    if (!user) return;
    fetchAll();
    const id = setInterval(fetchAll, 5000);
    return () => clearInterval(id);
  }, [user]);

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;

  const onCmd = async (action, payload = null, needsConfirm = false, dialogOpts = {}) => {
    if (needsConfirm) {
      setDialog({ action, payload, ...dialogOpts });
      return;
    }
    await doCmd(action, payload);
  };

  const doCmd = async (action, payload) => {
    try {
      await api.post("/command", { action, payload: payload || {} });
      await fetchAll();
    } catch (e) {
      console.error("Command failed", e);
    }
  };

  const onConfirmDialog = async () => {
    if (!dialog) return;
    await doCmd(dialog.action, dialog.payload);
    setDialog(null);
  };

  const saveSettings = async (patch) => {
    const { data } = await api.post("/settings", patch);
    setSettings(data);
    await fetchAll();
  };

  return (
    <div className="min-h-screen flex bg-background text-foreground">
      <Sidebar status={status} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />
      <main className="flex-1 min-w-0 flex flex-col">
        <PageHeader status={status} onMenu={() => setMobileOpen(true)}
                    onExportPdf={downloadTearsheet}
                    onShowHelp={() => { resetWizard(); setWizardOpen(true); }}
                    onOpenCmd={() => setCmdOpen(true)} />
        <div
          className="flex-1 p-5 lg:p-8 max-w-[1600px] w-full mx-auto pb-24 lg:pb-8"
          data-testid={`dashboard-section-${section}`}
        >
          {section === "home" && (
            <HomePage
              status={status}
              history={history}
              settings={settings}
              health={health}
              onCmd={onCmd}
              onSaveSettings={saveSettings}
            />
          )}
          {section === "risk" && (
            <RiskCenterPage status={status} settings={settings} health={health} />
          )}
          {section === "whatif" && (
            <WhatIfPage trades={trades} byReason={byReason} summary={summary} />
          )}
          {section === "strategies" && (
            <StrategiesPage
              key={`strat-${settings?._updatedAt || JSON.stringify(settings?.strategies || {})}`}
              settings={settings}
              status={status}
              onSave={saveSettings}
            />
          )}
          {section === "optimizer" && <OptimizerPage />}
          {section === "analytics" && (
            <AnalyticsPage
              summary={summary} trades={trades}
              heatmap={heatmap} byReason={byReason}
              calendar={calendar} correlation={correlation}
              onSelectTrade={setSelectedTrade}
            />
          )}
          {section === "settings" && (
            <SettingsPage
              key={`set-${settings?._updatedAt || (settings ? Object.keys(settings).length : 0)}`}
              settings={settings}
              onSave={saveSettings}
            />
          )}
          {section === "licenses" && <LicensesPage />}
          {section === "coach" && <CoachPage />}
          {section === "journal" && <JournalPage />}
          {section === "risk-calc" && <RiskCalcPage />}
          {section === "backtest" && <BacktestPage />}
          {section === "calendar" && <CalendarPage />}
          {section === "strategy-analytics" && <StrategyAnalyticsPage />}
          {section === "chain" && <StrategyChainPage />}
          {section === "local-bridge" && <LocalBridgePage />}
        </div>
      </main>

      <ConfirmDialog
        open={!!dialog}
        title={dialog?.title || ""}
        body={dialog?.body || ""}
        danger={dialog?.danger !== false}
        confirmLabel={dialog?.confirmLabel || "Confirm"}
        onConfirm={onConfirmDialog}
        onCancel={() => setDialog(null)}
        testId="action-confirm-dialog"
      />

      <TradeLifecycleDrawer
        trade={selectedTrade}
        onClose={() => setSelectedTrade(null)}
      />

      <BottomNav onMenuOpen={() => setMobileOpen(true)} />

      {wizardOpen && (
        <SetupWizard user={user} onClose={() => setWizardOpen(false)} />
      )}

      <CommandPalette
        open={cmdOpen}
        onClose={() => setCmdOpen(false)}
        onEaCmd={(action) => {
          // Trigger confirmation dialogs for destructive commands
          const map = {
            close_all: { needsConfirm: true, dialog: { title: "Close all positions?", body: "Sends CLOSE_ALL to the EA. Irreversible." } },
            pause: { needsConfirm: true, dialog: { title: "Pause the EA?", body: "Stops opening new positions." } },
            reset_anti_revenge: { needsConfirm: true, dialog: { title: "Reset anti-revenge?", body: "Clears the cooldown counter.", danger: false, confirmLabel: "Reset" } },
            reset_daily: { needsConfirm: true, dialog: { title: "Reset daily counters?", body: "Trades-today → 0.", danger: false, confirmLabel: "Reset" } },
          };
          const cfg = map[action];
          if (cfg) onCmd(action, null, cfg.needsConfirm, cfg.dialog);
          else onCmd(action, null, false);
        }}
      />

      <CoachLiveWidget />
    </div>
  );
}
