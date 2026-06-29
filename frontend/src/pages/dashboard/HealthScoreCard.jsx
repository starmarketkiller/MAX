import { AlertOctagon } from "lucide-react";
import {
  Card, cls, POS_TEXT, NEG_TEXT, gateStyleFor,
} from "@/pages/dashboard/shared";

const HEALTH_LEVEL = {
  excellent: { ring: "stroke-emerald-500", text: POS_TEXT, badge: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30", label: "Excellent" },
  good:      { ring: "stroke-sky-500",     text: "text-sky-600 dark:text-sky-400",   badge: "bg-sky-500/10 text-sky-700 dark:text-sky-400 border-sky-500/30",   label: "Good" },
  warning:   { ring: "stroke-amber-500",   text: "text-amber-600 dark:text-amber-400", badge: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30", label: "Warning" },
  critical:  { ring: "stroke-rose-500",    text: NEG_TEXT, badge: "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/30", label: "Critical" },
};

export default function HealthScoreCard({ health, compact = false }) {
  if (!health) return null;
  const lvl = HEALTH_LEVEL[health.level] || HEALTH_LEVEL.warning;
  const score = health.score ?? 0;
  const circumference = 2 * Math.PI * 42;
  const dash = (score / 100) * circumference;
  const checks = health.checks || [];
  const anomalies = health.anomaly || [];

  return (
    <Card className="p-6 lg:p-8" testId="health-score-card">
      <div className="flex flex-col lg:flex-row gap-6 lg:items-center">
        <div className="flex items-center gap-5 lg:flex-shrink-0">
          <div className="relative w-[110px] h-[110px]" data-testid="health-ring">
            <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
              <circle cx="50" cy="50" r="42" stroke="currentColor" strokeWidth="8"
                      fill="none" className="text-border" />
              <circle cx="50" cy="50" r="42" strokeWidth="8" fill="none"
                      strokeLinecap="round"
                      strokeDasharray={`${dash} ${circumference}`}
                      className={cls("transition-all duration-700", lvl.ring)} />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className={cls("font-bold text-3xl tabular leading-none", lvl.text)}>{score}</div>
              <div className="text-[9px] text-muted-foreground uppercase tracking-[0.15em] mt-1">score</div>
            </div>
          </div>

          <div>
            <div className="eyebrow">EA health</div>
            <h3 className="font-semibold text-xl tracking-tight mt-1 flex items-center gap-2 flex-wrap">
              <span className={lvl.text}>{lvl.label}</span>
              <span className={cls("px-2 py-0.5 rounded-full text-[10px] font-bold border", lvl.badge)}>
                {checks.filter((c) => c.ok === true).length}/{checks.length} checks
              </span>
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              Composite of bridge, protections, drawdown, activity, revenge, news, vol, profit factor.
            </p>
          </div>
        </div>

        {anomalies.length > 0 && (
          <div className="flex-1 min-w-0">
            <div className="eyebrow text-rose-600 dark:text-rose-400 mb-2 flex items-center gap-1.5">
              <AlertOctagon className="h-3.5 w-3.5" /> Anomalies detected
            </div>
            <div className="space-y-1.5">
              {anomalies.map((a) => (
                <div key={a.code} data-testid={`anomaly-${a.code}`}
                     className="text-xs text-rose-700 dark:text-rose-400 bg-rose-500/10 border border-rose-500/30 px-3 py-2 rounded-lg">
                  {a.msg}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {!compact && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 mt-6">
          {checks.map((c) => {
            const st = gateStyleFor(c.ok);
            return (
              <div key={c.key}
                   data-testid={`health-check-${c.key}`}
                   className={cls("flex items-start gap-3 px-4 py-3 rounded-xl border text-xs", st.container)}>
                <div className={cls(
                  "h-5 w-5 rounded-full flex-shrink-0 flex items-center justify-center text-[10px] font-bold mt-0.5",
                  st.badge
                )}>{st.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-semibold text-foreground">{c.label}</div>
                    <span className="text-[10px] text-muted-foreground font-mono">{c.weight}w</span>
                  </div>
                  <div className="text-muted-foreground font-mono text-[11px] mt-0.5">{c.detail}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
