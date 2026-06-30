import { useState, useMemo } from "react";
import { Layers, Cpu, Lock, Filter, Sparkles } from "lucide-react";
import { Card, cls, STRAT_LIST, STRAT_FAMILIES, STRAT_FAMILY_COLOR } from "@/pages/dashboard/shared";
import { useStrategyHub } from "@/lib/strategyHub";

const READY_FOR_BACKTEST = new Set([
  "CISD", "AMD_CONT", "JUDAS_SWING", "LDN_REVERSAL", "NY_REVERSAL",
  "WEEKLY_EXP", "PO3", "LIQ_VOID", "DISP_REBAL",
]);

export default function StrategiesPage({ settings, onSave, status }) {
  const { open: openStrategy } = useStrategyHub();
  const enabled = settings?.strategies || Object.fromEntries(STRAT_LIST.map(([k]) => [k, true]));
  const [local, setLocal] = useState(enabled);
  const [familyFilter, setFamilyFilter] = useState("ALL");

  const toggle = (k) => setLocal((s) => ({ ...s, [k]: !s[k] }));
  const blocked = status?.newsBlock;
  const activeCount = Object.values(local).filter(Boolean).length;
  const total = STRAT_LIST.length;

  const familyCounts = useMemo(() => {
    const m = {};
    STRAT_LIST.forEach(([, , fam]) => { m[fam] = (m[fam] || 0) + 1; });
    return m;
  }, []);

  const filtered = useMemo(() => (
    familyFilter === "ALL" ? STRAT_LIST : STRAT_LIST.filter(([, , fam]) => fam === familyFilter)
  ), [familyFilter]);

  const toggleFamily = (famId, turnOn) => {
    const next = { ...local };
    STRAT_LIST.forEach(([k, , fam]) => {
      if (fam === famId) next[k] = turnOn;
    });
    setLocal(next);
  };

  return (
    <div className="space-y-6 fade-in">
      <Card className="p-6 lg:p-8 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <div className="eyebrow flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5" /> Strategies
          </div>
          <h2 className="text-2xl font-semibold tracking-tight mt-1">
            <span className="font-normal text-muted-foreground">{total} engines · </span>
            {activeCount} <span className="font-normal text-muted-foreground">live</span>
          </h2>
          <p className="text-sm text-muted-foreground mt-1.5">
            Trend {familyCounts.TREND} · Reversal {familyCounts.REVERSAL} · SMC/ICT {familyCounts.SMC} ·{" "}
            <span className="text-emerald-600 dark:text-emerald-400 font-medium">
              Institutional {familyCounts.INSTITUTIONAL} <Sparkles className="inline h-3 w-3" />
            </span>
          </p>
        </div>
        <button
          data-testid="save-strategies-button"
          onClick={() => onSave({ strategies: local })}
          className="h-11 px-6 rounded-lg bg-sky-600 hover:bg-sky-700 dark:bg-sky-500 dark:hover:bg-sky-400 text-white text-sm font-semibold shadow-sm transition-colors"
        >
          Save changes
        </button>
      </Card>

      {blocked && (
        <div className="rounded-xl bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/30 px-4 py-2.5 text-sm flex items-center gap-2">
          <Lock className="h-4 w-4" /> News filter is currently blocking all entries.
        </div>
      )}

      {/* Family filter chips + bulk on/off */}
      <Card className="p-4 lg:p-5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground mr-1">
            <Filter className="h-3 w-3" /> Family:
          </span>
          <button
            onClick={() => setFamilyFilter("ALL")}
            data-testid="strat-family-chip-ALL"
            className={cls(
              "px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors",
              familyFilter === "ALL"
                ? "border-sky-500 bg-sky-500/10 text-sky-700 dark:text-sky-400"
                : "border-border text-muted-foreground hover:bg-secondary/60"
            )}
          >
            All ({total})
          </button>
          {STRAT_FAMILIES.map((f) => (
            <button
              key={f.id}
              onClick={() => setFamilyFilter(f.id)}
              data-testid={`strat-family-chip-${f.id}`}
              className={cls(
                "px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors",
                familyFilter === f.id
                  ? "border-sky-500 bg-sky-500/10 text-sky-700 dark:text-sky-400"
                  : "border-border text-muted-foreground hover:bg-secondary/60"
              )}
            >
              {f.label} ({familyCounts[f.id] || 0})
            </button>
          ))}
          {familyFilter !== "ALL" && (
            <div className="ml-auto flex items-center gap-2">
              <button
                onClick={() => toggleFamily(familyFilter, true)}
                data-testid="bulk-enable-family"
                className="px-2.5 py-1 rounded-md text-[10px] font-semibold border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-500/10"
              >
                Enable all
              </button>
              <button
                onClick={() => toggleFamily(familyFilter, false)}
                data-testid="bulk-disable-family"
                className="px-2.5 py-1 rounded-md text-[10px] font-semibold border border-rose-500/30 text-rose-700 dark:text-rose-400 hover:bg-rose-500/10"
              >
                Disable all
              </button>
            </div>
          )}
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map(([key, label, family]) => {
          const on = !!local[key];
          const isRFB = READY_FOR_BACKTEST.has(key);
          return (
            <Card
              key={key}
              testId={`strategy-card-${key.toLowerCase()}`}
              className={cls("p-5 flex items-center justify-between transition-colors", on && "border-sky-500/30")}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className={cls(
                  "h-10 w-10 rounded-lg flex items-center justify-center flex-shrink-0",
                  on ? "bg-sky-500/10 text-sky-600 dark:text-sky-400" : "bg-secondary text-muted-foreground"
                )}>
                  <Cpu className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <button onClick={() => openStrategy(key)}
                      data-testid={`strategy-open-${key.toLowerCase()}`}
                      className="font-semibold text-sm leading-tight truncate text-left hover:text-primary hover:underline transition-colors">
                      {label}
                    </button>
                    {isRFB && (
                      <span className="inline-flex items-center gap-0.5 text-[9px] font-bold text-sky-600" title="Ready for backtest">
                        <Sparkles className="h-2.5 w-2.5" /> RFB
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground mt-1 font-mono flex items-center gap-1.5">
                    {key}
                    <span className={cls(
                      "px-1 py-0.5 rounded text-[8px] font-bold border tabular-nums",
                      STRAT_FAMILY_COLOR[family]
                    )}>{family}</span>
                  </div>
                </div>
              </div>
              <button
                role="switch"
                aria-checked={on}
                onClick={() => toggle(key)}
                data-testid={`strategy-toggle-${key.toLowerCase()}`}
                className={cls(
                  "relative h-6 w-11 rounded-full transition-colors flex-shrink-0 ml-3",
                  on ? "bg-sky-600 dark:bg-sky-500" : "bg-secondary border border-border"
                )}
              >
                <span className={cls(
                  "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform",
                  on ? "translate-x-5" : "translate-x-0.5"
                )} />
              </button>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
