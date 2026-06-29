import { Bell } from "lucide-react";
import MarkdownLite from "@/pages/coach/MarkdownLite";

export function InsightChip({ ins }) {
  const palette = {
    good: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
    warn: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30",
    info: "bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/30",
  }[ins.type] || "bg-secondary text-muted-foreground border-border";
  return (
    <div className={`rounded-lg border p-3 ${palette}`} data-testid={`insight-${ins.type}`}>
      <div className="text-xs font-bold uppercase tracking-wide">{ins.title}</div>
      <div className="text-sm mt-1">{ins.body}</div>
    </div>
  );
}

export function DailyBrief({ brief, onClose }) {
  if (!brief) return null;
  return (
    <div
      className="rounded-xl border border-amber-500/40 bg-gradient-to-br from-amber-500/10 to-orange-500/5 p-5"
      data-testid="coach-daily-brief"
    >
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 rounded-lg bg-amber-500/15 flex items-center justify-center flex-shrink-0">
          <Bell className="h-5 w-5 text-amber-600 dark:text-amber-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <div className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">
              Briefing del Coach · {brief.date_key}
            </div>
            <button
              onClick={onClose}
              className="text-xs text-muted-foreground hover:text-foreground"
              data-testid="coach-brief-dismiss"
            >
              segna come letto
            </button>
          </div>
          <div className="text-sm">
            <MarkdownLite text={brief.summary} />
          </div>
        </div>
      </div>
    </div>
  );
}
