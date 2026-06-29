import { useState } from "react";
import { Sparkles, LineChart as LineChartIcon } from "lucide-react";
import api from "@/lib/api";
import {
  Card, SectionHeader, cls, fmtMoney,
  POS_TEXT, NEG_TEXT,
} from "@/pages/dashboard/shared";

const ALL_REASONS  = ["NXS:PROFIT", "NXS:BE", "NXS:TREND", "NXS:TIME", "NXS:NEWS", "NXS:DD", "NXS:RISK"];
const ALL_SESSIONS = ["ASIAN", "LONDON", "OVERLAP", "NY", "AFTERNY"];
const ALL_DOWS     = [[0, "Mon"], [1, "Tue"], [2, "Wed"], [3, "Thu"], [4, "Fri"], [5, "Sat"], [6, "Sun"]];

function FilterChip({ active, onClick, children, testId }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testId}
      className={cls(
        "px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all",
        active
          ? "bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/40"
          : "bg-secondary/50 text-muted-foreground border-border hover:border-rose-500/30"
      )}
    >
      {active ? "✕ " : ""}{children}
    </button>
  );
}

function FilterRow({ title, items, getKey, getLabel, getTestId, active, onToggle }) {
  return (
    <div>
      <div className="eyebrow mb-2">{title}</div>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => {
          const k = getKey(item);
          return (
            <FilterChip
              key={k}
              active={active.includes(k)}
              onClick={() => onToggle(k)}
              testId={getTestId(item)}
            >
              {getLabel(item)}
            </FilterChip>
          );
        })}
      </div>
    </div>
  );
}

function WindowPicker({ value, onChange }) {
  return (
    <div>
      <div className="eyebrow mb-2">Window</div>
      <div className="flex gap-2">
        {[30, 60, 90, 180, 365].map((d) => (
          <button
            key={d}
            onClick={() => onChange(d)}
            data-testid={`whatif-window-${d}`}
            className={cls(
              "px-3 py-1.5 rounded-lg text-xs font-semibold border",
              value === d
                ? "bg-sky-500/15 text-sky-700 dark:text-sky-400 border-sky-500/40"
                : "bg-secondary/50 text-muted-foreground border-border hover:border-sky-500/30"
            )}
          >
            {d}d
          </button>
        ))}
      </div>
    </div>
  );
}

function DeltaCard({ label, baseline, simulated, delta, fmt, hint, testId }) {
  let deltaCls = "bg-secondary/50 text-muted-foreground";
  if (delta > 0)      deltaCls = "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400";
  else if (delta < 0) deltaCls = "bg-rose-500/10 text-rose-700 dark:text-rose-400";
  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-2" data-testid={testId}>
      <div className="eyebrow">{label}</div>
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <div className="text-[10px] text-muted-foreground uppercase">Baseline</div>
          <div className="font-mono font-bold text-xl tabular">{fmt(baseline)}</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-muted-foreground uppercase">Simulated</div>
          <div className="font-mono font-bold text-xl tabular">{fmt(simulated)}</div>
        </div>
      </div>
      <div className={cls("text-center text-xs font-bold py-1.5 rounded-md font-mono", deltaCls)}>
        Δ {delta > 0 ? "+" : ""}{fmt(delta)}
      </div>
      {hint && <div className="text-[10px] text-muted-foreground/70 italic">{hint}</div>}
    </div>
  );
}

function WhatIfHeader({ onReset, onRun, busy, disabledRun }) {
  return (
    <Card className="p-6 lg:p-8">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
        <div>
          <div className="eyebrow flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5" /> Quant lab
          </div>
          <h2 className="text-2xl font-semibold tracking-tight mt-1">What-if Replay</h2>
          <p className="text-sm text-muted-foreground mt-1.5 max-w-2xl">
            Re-evaluate your closed-trade history with hypothetical exclusions.
            Toggle filters below and see how P&amp;L, Sharpe and drawdown would
            have changed if those trades had never happened. Tuning by evidence,
            not by feel.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button data-testid="whatif-reset" onClick={onReset}
                  className="h-10 px-4 rounded-lg border border-border text-sm font-medium hover:bg-secondary">
            Reset
          </button>
          <button data-testid="whatif-run" onClick={onRun}
                  disabled={busy || disabledRun}
                  className="h-10 px-5 rounded-lg bg-sky-600 hover:bg-sky-700 dark:bg-sky-500 dark:hover:bg-sky-400 text-white text-sm font-semibold transition-colors disabled:opacity-50 shadow-sm">
            {busy ? "Running…" : "Run simulation"}
          </button>
        </div>
      </div>
    </Card>
  );
}

function WhatIfFilters({ state, knownReasons, knownStrategies }) {
  const {
    daysWindow, setDaysWindow,
    excludeReasons, toggleReason,
    excludeStrategies, toggleStrategy,
    excludeSessions, toggleSession,
    excludeDows, toggleDow,
    totalExcl,
  } = state;
  return (
    <Card className="p-6 lg:p-8" testId="whatif-filters">
      <div className="space-y-5">
        <WindowPicker value={daysWindow} onChange={setDaysWindow} />
        <FilterRow
          title="Exclude close reasons"
          items={knownReasons}
          getKey={(r) => r}
          getLabel={(r) => r}
          getTestId={(r) => `whatif-reason-${r.replace(/[^a-z0-9]/gi, "")}`}
          active={excludeReasons}
          onToggle={toggleReason}
        />
        <FilterRow
          title="Exclude strategies"
          items={knownStrategies}
          getKey={(s) => s}
          getLabel={(s) => s}
          getTestId={(s) => `whatif-strategy-${s}`}
          active={excludeStrategies}
          onToggle={toggleStrategy}
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <FilterRow
            title="Exclude sessions"
            items={ALL_SESSIONS}
            getKey={(s) => s}
            getLabel={(s) => s}
            getTestId={(s) => `whatif-session-${s}`}
            active={excludeSessions}
            onToggle={toggleSession}
          />
          <FilterRow
            title="Exclude days of week"
            items={ALL_DOWS}
            getKey={([d]) => d}
            getLabel={([, label]) => label}
            getTestId={([d]) => `whatif-dow-${d}`}
            active={excludeDows}
            onToggle={toggleDow}
          />
        </div>
        {totalExcl > 0 && (
          <div className="text-xs text-muted-foreground border-t border-border pt-3">
            <span className="text-foreground font-semibold">{totalExcl}</span>{" "}
            exclusion{totalExcl > 1 ? "s" : ""} configured · click <b>Run simulation</b> to see the impact.
          </div>
        )}
      </div>
    </Card>
  );
}

function WhatIfResults({ result }) {
  return (
    <Card className="p-6 lg:p-8" testId="whatif-result">
      <SectionHeader
        eyebrow="Simulation result"
        title={
          <>
            {result.delta?.excluded} trade{result.delta?.excluded !== 1 ? "s" : ""} removed{" "}
            <span className="text-muted-foreground font-normal">over last {result.window_days}d</span>
          </>
        }
        icon={LineChartIcon}
        right={
          <span className={cls("font-mono text-sm font-bold",
            result.delta?.total_pnl >= 0 ? POS_TEXT : NEG_TEXT)}>
            Δ P&L {result.delta?.total_pnl >= 0 ? "+" : ""}${fmtMoney(result.delta?.total_pnl)}
          </span>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <DeltaCard testId="dc-pnl" label="Total P&L"
                   baseline={result.baseline?.total_pnl}
                   simulated={result.simulated?.total_pnl}
                   delta={result.delta?.total_pnl}
                   fmt={(v) => `$${fmtMoney(v || 0)}`}
                   hint="positive = excluding those trades would have helped" />
        <DeltaCard testId="dc-trades" label="Total trades"
                   baseline={result.baseline?.trades}
                   simulated={result.simulated?.trades}
                   delta={result.delta?.trades}
                   fmt={(v) => `${v}`}
                   hint={`${Math.abs(result.delta?.trades)} trades removed`} />
        <DeltaCard testId="dc-wr" label="Win rate"
                   baseline={result.baseline?.win_rate}
                   simulated={result.simulated?.win_rate}
                   delta={result.delta?.win_rate}
                   fmt={(v) => `${Number(v || 0).toFixed(1)}%`}
                   hint="higher = better entry quality" />
        <DeltaCard testId="dc-pf" label="Profit factor"
                   baseline={result.baseline?.profit_factor}
                   simulated={result.simulated?.profit_factor}
                   delta={result.delta?.profit_factor}
                   fmt={(v) => Number(v || 0).toFixed(2)}
                   hint=">1.5 healthy, >2 strong" />
        <DeltaCard testId="dc-sharpe" label="Sharpe ratio"
                   baseline={result.baseline?.risk?.sharpe}
                   simulated={result.simulated?.risk?.sharpe}
                   delta={result.delta?.sharpe}
                   fmt={(v) => Number(v || 0).toFixed(2)}
                   hint="risk-adjusted return · the institutional metric" />
        <DeltaCard testId="dc-maxdd" label="Max drawdown"
                   baseline={result.baseline?.risk?.max_dd}
                   simulated={result.simulated?.risk?.max_dd}
                   delta={-(result.delta?.max_dd || 0)}
                   fmt={(v) => `$${fmtMoney(Math.abs(v || 0))}`}
                   hint="lower = smoother equity curve" />
      </div>

      <div className="mt-6 px-4 py-3 rounded-xl bg-sky-500/10 border border-sky-500/25 text-xs text-sky-800 dark:text-sky-300">
        <b>Reading this:</b> if Δ Sharpe is positive AND Δ P&L is only slightly
        negative, you&apos;ve found a configuration that&apos;s more <i>stable</i> for the
        same money — usually a better real-world setup. Conversely a small Δ P&L
        improvement with worse Sharpe means you got lucky on a few trades.
      </div>
    </Card>
  );
}

function useWhatIfState() {
  const [excludeReasons,    setExcludeReasons]    = useState([]);
  const [excludeStrategies, setExcludeStrategies] = useState([]);
  const [excludeSessions,   setExcludeSessions]   = useState([]);
  const [excludeDows,       setExcludeDows]       = useState([]);
  const [daysWindow,        setDaysWindow]        = useState(90);

  const makeToggler = (arr, setter) => (v) =>
    setter(arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

  const reset = () => {
    setExcludeReasons([]); setExcludeStrategies([]);
    setExcludeSessions([]); setExcludeDows([]);
  };
  const totalExcl = excludeReasons.length + excludeStrategies.length
                  + excludeSessions.length + excludeDows.length;

  return {
    excludeReasons, excludeStrategies, excludeSessions, excludeDows, daysWindow,
    toggleReason:   makeToggler(excludeReasons,    setExcludeReasons),
    toggleStrategy: makeToggler(excludeStrategies, setExcludeStrategies),
    toggleSession:  makeToggler(excludeSessions,   setExcludeSessions),
    toggleDow:      makeToggler(excludeDows,       setExcludeDows),
    setDaysWindow, reset, totalExcl,
  };
}

export default function WhatIfPage({ byReason, summary }) {
  const state = useWhatIfState();
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const knownStrategies = Array.from(new Set((summary?.by_strategy || []).map((s) => s.strategy)));
  const knownReasons = (() => {
    const fromData = new Set((byReason?.by_reason || []).map((r) => r.reason));
    ALL_REASONS.forEach((r) => fromData.add(r));
    return Array.from(fromData);
  })();

  const runSimulation = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/analytics/whatif", {
        excludeReasons:    state.excludeReasons,
        excludeStrategies: state.excludeStrategies,
        excludeSessions:   state.excludeSessions,
        excludeDows:       state.excludeDows,
        daysWindow:        state.daysWindow,
      });
      setResult(data);
    } catch (e) {
      // Surface the failure to the dev console (errors are kept; warns were removed).
      // The UI keeps the previous result so the user can simply click "Run" again.
      console.error("[whatif] simulation failed:", e?.response?.data?.detail || e?.message || e);
    } finally {
      setBusy(false);
    }
  };

  const resetAll = () => { state.reset(); setResult(null); };

  return (
    <div className="space-y-6 fade-in" data-testid="whatif-page">
      <WhatIfHeader
        onReset={resetAll}
        onRun={runSimulation}
        busy={busy}
        disabledRun={state.totalExcl === 0}
      />
      <WhatIfFilters
        state={state}
        knownReasons={knownReasons}
        knownStrategies={knownStrategies}
      />
      {result && <WhatIfResults result={result} />}
    </div>
  );
}
