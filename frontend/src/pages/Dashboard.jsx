import { useEffect, useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import {
  Settings as SettingsIcon,
  ShieldAlert, Clock, Target,
  Menu, FileDown, HelpCircle,
  Gauge, Command as CommandIcon, Bot, Server,
  Sun, Moon,
} from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import { useVisiblePolling } from "@/lib/useVisiblePolling";
import LicensesPage from "@/pages/Licenses";
import CoachPage from "@/pages/Coach";
import JournalPage from "@/pages/Journal";
import RiskCalcPage from "@/pages/RiskCalc";
import BacktestPage from "@/pages/Backtest";
import CalendarPage from "@/pages/CalendarPage";
import LocalBridgePage from "@/pages/LocalBridgePage";
import KnowledgePage from "@/pages/KnowledgePage";
import ResearchPage from "@/pages/ResearchPage";
import SequenceExplorerPage from "@/pages/SequenceExplorerPage";
import SystemStatusPage from "@/pages/SystemStatusPage";
import MarketPage from "@/pages/MarketPage";
import ExecutionPage from "@/pages/ExecutionPage";
import LibraryPage from "@/pages/LibraryPage";
import StrategyChainPage from "@/pages/StrategyChainPage";
import SetupWizard, { shouldShowWizard, resetWizard } from "@/components/SetupWizard";
import NotificationBell from "@/components/NotificationBell";
import LicenseBanner from "@/components/LicenseBanner";
import CoachLiveWidget from "@/components/CoachLiveWidget";
import Sidebar from "@/components/Sidebar";
import BottomNav from "@/components/BottomNav";
import CommandPalette from "@/components/CommandPalette";
import DataProvenanceBadge from "@/components/DataProvenanceBadge";
import HomePage from "@/pages/dashboard/HomePage";
import StrategiesPage from "@/pages/dashboard/StrategiesPage";
import OptimizerPage from "@/pages/dashboard/OptimizerPage";
import { StrategyHubProvider } from "@/lib/strategyHub";
import { TradeHubProvider } from "@/lib/tradeHub";
import { DEFAULT_SETTINGS, SETTINGS_FIELDS, SETTINGS_BOOLS, validateSettings } from "@/contracts/settingsContract";
import StrategyAnalyticsPage from "@/pages/dashboard/StrategyAnalyticsPage";
import AnalyticsPage from "@/pages/dashboard/AnalyticsPage";
import WhatIfPage from "@/pages/dashboard/WhatIfPage";
import HealthScoreCard from "@/pages/dashboard/HealthScoreCard";
import TradeLifecycleDrawer from "@/pages/dashboard/TradeLifecycleDrawer";
import { workspaceForSection } from "@/lib/workspaces";
import {
  Card, ConfirmDialog, SectionHeader,
  cls, fmtMoney, fmtSign,
  POS_TEXT, NEG_TEXT, pnlTextClass,
} from "@/pages/dashboard/shared";

// ========================================================================
// PAGE HEADER
// ========================================================================
function PageHeader({ section, status, onMenu, onExportPdf, onShowHelp, onOpenCmd }) {
  const { theme, toggle } = useTheme();
  const location = useLocation();
  const workspace = workspaceForSection(section);
  const online = !!status?.online;
  const utilityTitles = { settings: "Settings", licenses: "Licenses / Admin", "risk-calc": "Calculator", system: "System status", coach: "AI Coach" };
  const title = workspace?.label || utilityTitles[section] || "NEXUS";
  const summary = workspace?.summary || "NEXUS terminal utility.";

  return (
    <header
      data-testid="page-header"
      className="sticky top-0 z-30 border-b border-border bg-card px-4 py-3 lg:px-8"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onMenu}
            data-testid="menu-toggle"
            aria-label="Open navigation"
            className="flex h-9 w-9 items-center justify-center rounded-md border border-border hover:bg-secondary lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2"><h1 className="text-lg font-semibold tracking-tight">{title}</h1><DataProvenanceBadge source={status?.demo ? "DEMO" : online ? "LIVE" : status ? "CACHED" : "UNAVAILABLE"} testId="online-badge" /></div>
            <p className="mt-0.5 hidden max-w-xl truncate text-xs text-muted-foreground sm:block">{summary}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <LicenseBanner />
          <Link to="/system" title="System status" className="hidden h-9 items-center gap-2 rounded-md border border-border px-2.5 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground sm:flex"><span className={cls("h-1.5 w-1.5 rounded-full", online ? "bg-emerald-500" : status ? "bg-amber-500" : "bg-zinc-500")}/><Server className="h-3.5 w-3.5"/></Link>
          {onOpenCmd && (
            <button
              onClick={onOpenCmd}
              title="Command palette (⌘K)"
              data-testid="header-cmdk-btn"
              className="hidden h-9 items-center gap-2 rounded-md border border-border px-3 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground md:inline-flex"
            >
              <CommandIcon className="h-3.5 w-3.5" />
              <span className="font-mono">Search</span>
              <kbd className="ml-1 px-1.5 py-0.5 rounded bg-background border border-border text-[10px] font-mono group-hover:border-primary/40">⌘K</kbd>
            </button>
          )}
          <Link to="/coach" title="Contextual AI (workspace context integration pending)" data-testid="header-ai-btn" className="flex h-9 w-9 items-center justify-center rounded-md border border-border text-muted-foreground hover:bg-secondary hover:text-foreground"><Bot className="h-4 w-4"/></Link>
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
      {workspace?.tabs?.length > 1 ? <nav aria-label={`${workspace.label} views`} className="mt-3 flex gap-1 overflow-x-auto border-t border-border pt-2">{workspace.tabs.map((tab) => { const active = location.pathname === tab.to; return <Link key={tab.to} to={tab.to} className={cls("whitespace-nowrap rounded-md px-2.5 py-1.5 text-xs", active ? "bg-secondary font-semibold text-foreground" : "text-muted-foreground hover:text-foreground")}>{tab.label}</Link>; })}</nav> : null}
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
  const available = used !== null && used !== undefined;
  const usedFmt = available ? (fmt ? fmt(used) : used) : "—";
  const limitFmt = fmt ? fmt(limit) : limit;
  const pct = available && limit > 0 ? (Math.abs(used) / Math.abs(limit)) * 100 : null;
  let tone = "pos";
  if (pct !== null && pct >= 90) tone = "neg";
  else if (pct !== null && pct >= 70) tone = "warn";
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
          <div className="text-[10px] text-muted-foreground mt-0.5">{pct === null ? "UNAVAILABLE" : `${Math.round(pct)}% used`}</div>
        </div>
      </div>
      {available ? <ProgressBar value={Math.abs(used)} max={Math.abs(limit)} tone={tone} /> : <div className="h-2 rounded-full bg-secondary" />}
    </div>
  );
}

function RiskCenterPage({ status, settings, health }) {
  if (!status || !settings) {
    return <div className="text-muted-foreground text-sm">Loading risk panel…</div>;
  }
  const positions = status.positions || [];
  const maxConcurrent = settings.MaxConcurrent ?? DEFAULT_SETTINGS.MaxConcurrent;
  const maxTrades = settings.MaxTradesPerDay ?? DEFAULT_SETTINGS.MaxTradesPerDay;
  const maxDD = settings.MaxDailyDDPct ?? DEFAULT_SETTINGS.MaxDailyDDPct;
  const eslLimitPct = settings.ESL_IsPercent ? settings.ESL_Value : 5;
  const dptTargetPct = settings.DPT_IsPercent ? settings.DPT_Value : 3;
  const antiRevLosses = settings.AntiRevengeLosses ?? 3;
  const consecLosses = status.consecLosses;
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
          <RiskBudgetRow label="Daily drawdown" used={status.drawdownPct} limit={maxDD}
            fmt={(v) => `${Number(v).toFixed(2)}%`}
            hint="EA pauses when daily DD reaches MaxDailyDDPct"
            testId="rb-daily-dd" />
          <RiskBudgetRow label="Equity Stop Loss (ESL)" used={status.floatPnLPct == null ? null : Math.abs(status.floatPnLPct)} limit={eslLimitPct}
            fmt={(v) => `${Number(v).toFixed(2)}%`}
            hint="Closes all positions when floating loss hits"
            testId="rb-esl" />
          <RiskBudgetRow label="Daily Profit Target (DPT)" used={status.dailyPnLPct} limit={dptTargetPct}
            fmt={(v) => `${Number(v).toFixed(2)}%`}
            hint="Closes & pauses for the day when reached"
            testId="rb-dpt" />
          <RiskBudgetRow label="Concurrent positions" used={positions.length} limit={maxConcurrent}
            fmt={(v) => `${v}`}
            hint="Hard cap to control margin exposure"
            testId="rb-concurrent" />
          <RiskBudgetRow label="Trades today" used={status.tradesToday} limit={maxTrades}
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
                    <span className="text-[10px] text-muted-foreground">consec={info.consec ?? "—"}</span>
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
function SettingsPage({ settings, onSave }) {
  const [local, setLocal] = useState(settings || {});
  const [history, setHistory] = useState([]);
  const [validationErrors, setValidationErrors] = useState({});
  const change = (k, v) => setLocal((s) => ({ ...s, [k]: v }));

  useVisiblePolling(async () => {
    try {
      const { data } = await api.get("/settings/history?limit=50");
      setHistory(data);
    } catch (e) { console.warn("settings history load failed", e); }
  }, 10000);

  const handleSave = async () => {
    const errors = validateSettings(local);
    setValidationErrors(errors);
    if (Object.keys(errors).length) return;
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
          {SETTINGS_FIELDS.map(([k, label, type, min, max, step]) => (
            <div key={k}>
              <label className="text-sm font-medium mb-1.5 block">{label}</label>
              <input
                data-testid={`setting-${k}`}
                type="number"
                step={step}
                min={min}
                max={max}
                value={local[k] ?? ""}
                aria-invalid={!!validationErrors[k]}
                onChange={(e) => change(k, e.target.value === "" ? "" : (type === "integer" ? Number.parseInt(e.target.value, 10) : Number.parseFloat(e.target.value)))}
                className="w-full h-10 px-3 rounded-lg bg-background border border-border focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring font-mono text-sm transition-shadow"
              />
              {validationErrors[k] && <p className="text-xs text-rose-500 mt-1">{validationErrors[k]}</p>}
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
  const [lastCommand, setLastCommand] = useState(null);
  const [commandError, setCommandError] = useState("");
  const [resourceErrors, setResourceErrors] = useState({});

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
      const results = await Promise.allSettled([
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
      const [s, h, st, sm, tr, hm, br, cal, corr, hl] = results;
      const keys = ["status", "history", "settings", "summary", "trades",
        "heatmap", "reasons", "calendar", "correlation", "health"];
      const errors = {};
      results.forEach((result, index) => {
        if (result.status === "rejected" && result.reason?.response?.status !== 401) {
          errors[keys[index]] = result.reason?.message || "request failed";
        }
      });
      setResourceErrors(errors);
      // v2.0.9 — propagate semantic bridge state from /api/ea/health into status
      const bridgeCheck = (hl.status === "fulfilled" ? hl.value.data?.checks || [] : [])
        .find((c) => c.key === "bridge");
      if (s.status === "fulfilled") setStatus({ ...s.value.data, bridgeState: bridgeCheck?.state || null });
      if (h.status === "fulfilled") setHistory(h.value.data);
      if (st.status === "fulfilled") setSettings(st.value.data);
      if (sm.status === "fulfilled") setSummary(sm.value.data);
      if (tr.status === "fulfilled") setTrades(tr.value.data);
      if (hm.status === "fulfilled") setHeatmap(hm.value.data);
      if (br.status === "fulfilled") setByReason(br.value.data);
      if (cal.status === "fulfilled") setCalendar(cal.value.data);
      if (corr.status === "fulfilled") setCorrelation(corr.value.data);
      if (hl.status === "fulfilled") setHealth(hl.value.data);
    } catch (e) {
      if (e?.response?.status !== 401) {
        console.warn("[dashboard] fetchAll failed:", e?.message || e);
      }
    }
  };

  useVisiblePolling(fetchAll, 5000, !!user);

  // AUD0-FE-CMD-001 / NXS-FE-TRUST-002: il polling si fermava su DELIVERED e
  // lo mostrava come stato verde di successo. DELIVERED provava solo che l'EA
  // aveva ricevuto il comando, non che il broker lo avesse eseguito. Ora si
  // attende uno stato terminale dichiarato dal backend.
  const commandIsTerminal = !!lastCommand?.terminal;
  useVisiblePolling(async () => {
    if (!lastCommand?.id || commandIsTerminal) return;
    try {
      const { data } = await api.get(`/command/${lastCommand.id}`);
      setLastCommand(data);
    } catch (e) { console.warn("command status failed", e); }
  }, 1500, !!lastCommand?.id && !commandIsTerminal);

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
    // AUD0-CMD-002 / AUD0-FE-CMD-005: ogni comando deve dichiarare a QUALE
    // istanza è destinato. Il target si ricava dallo stato dell'EA attualmente
    // mostrato: senza di esso il backend rifiuta la richiesta, invece di
    // consegnarla a un'istanza qualsiasi.
    const target = {
      account_id: String(status?.account ?? status?.login ?? status?.account_id ?? ""),
      symbol: status?.symbol || "",
      magic: status?.magic,
    };
    if (!target.account_id || !target.symbol) {
      setCommandError(
        "Nessuna istanza EA identificata (account/simbolo mancanti): " +
        "il comando non è stato inviato."
      );
      return;
    }
    setCommandError("");
    try {
      const { data } = await api.post("/dashboard/command", {
        action,
        target,
        payload: payload || {},
        // Le azioni ad alto impatto richiedono conferma e motivazione: la
        // dialog di conferma è già stata mostrata prima di arrivare qui.
        confirm: true,
        reason: `Azione operatore dalla dashboard: ${action}`,
      });
      setLastCommand(data);
      await fetchAll();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setCommandError(formatApiError(detail) || e?.message || "errore sconosciuto");
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
    setSettings(data.settings || data);
    await fetchAll();
  };

  return (
    <StrategyHubProvider>
    <TradeHubProvider>
    <div className="min-h-screen flex bg-background text-foreground">
      <Sidebar status={status} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />
      <main className="flex-1 min-w-0 flex flex-col">
        <PageHeader section={section} status={status} onMenu={() => setMobileOpen(true)}
                    onExportPdf={downloadTearsheet}
                    onShowHelp={() => { resetWizard(); setWizardOpen(true); }}
                    onOpenCmd={() => setCmdOpen(true)} />
        <div className="px-5 lg:px-8 pt-4 max-w-[1600px] w-full mx-auto space-y-2">
          <div className="flex flex-wrap gap-2 text-[10px] font-mono">
            <DataProvenanceBadge source={status?.demo ? "DEMO" : status?.online ? "LIVE" : status ? "CACHED" : "UNAVAILABLE"} label={status?.online ? "LIVE · EA" : undefined} />
            {["analytics", "whatif", "journal", "strategy-analytics"].includes(section) &&
              <DataProvenanceBadge source="DERIVED" label="DERIVED · LEDGER" />}
            {trades.some((t) => t.source_provenance === "RECONSTRUCTED_HISTORY") &&
              <DataProvenanceBadge source="DERIVED" label="DERIVED · RECONSTRUCTED" />}
            {["backtest", "research"].includes(section) &&
              <DataProvenanceBadge source="RESEARCH" />}
          </div>
          {lastCommand && (
            /* Verde SOLO quando il broker ha confermato l'esecuzione; rosso
               per un esito terminale negativo; ambra finché è in corso. */
            <div className={cls("rounded-lg border px-3 py-2 text-xs flex flex-wrap justify-between gap-2",
              lastCommand.broker_confirmed
                ? "border-emerald-500/30 bg-emerald-500/10"
                : (lastCommand.terminal
                    ? "border-rose-500/30 bg-rose-500/10"
                    : "border-amber-500/30 bg-amber-500/10")) }>
              <span>
                Comando <b>{lastCommand.action}</b> · {lastCommand.id}
                {lastCommand.target?.symbol && (
                  <> · target <b>{lastCommand.target.account_id}/{lastCommand.target.symbol}</b></>
                )}
              </span>
              <span className="font-mono font-bold">
                {lastCommand.status}
                {!lastCommand.broker_confirmed && lastCommand.status === "LEASED" &&
                  " · ricevuto dall'EA, esecuzione non ancora confermata"}
              </span>
            </div>
          )}
          {commandError && (
            /* AUD0-FE-CMD-004: gli errori di comando finivano solo in console. */
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-600 dark:text-rose-400 flex justify-between gap-3">
              <span>Comando non accettato: {commandError}</span>
              <button type="button" className="underline" onClick={() => setCommandError("")}>chiudi</button>
            </div>
          )}
          {Object.keys(resourceErrors).length > 0 && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-600 dark:text-amber-400">
              Dati parziali: non disponibili {Object.keys(resourceErrors).join(", ")}. Le altre sezioni continuano ad aggiornarsi.
            </div>
          )}
        </div>
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
          {section === "research" && <ResearchPage />}
          {section === "research-sequences" && <SequenceExplorerPage />}
          {section === "market" && <MarketPage />}
          {section === "execution" && <ExecutionPage onCmd={onCmd} onSelectTrade={setSelectedTrade} />}
          {section === "library" && <LibraryPage />}
          {section === "system" && <SystemStatusPage status={status} health={health} />}
          {section === "calendar" && <CalendarPage />}
          {section === "knowledge" && <KnowledgePage />}
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
    </TradeHubProvider>
    </StrategyHubProvider>
  );
}
