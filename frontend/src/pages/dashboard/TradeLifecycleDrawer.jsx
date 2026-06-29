import { useMemo } from "react";
import {
  X, Activity, Gauge, ShieldCheck, Send, CheckCircle2,
  Cog, Flag, TrendingUp, TrendingDown,
} from "lucide-react";
import {
  cls, fmtMoney, fmtPrice,
  POS_TEXT, NEG_TEXT,
} from "@/pages/dashboard/shared";
import { REASON_COLORS } from "@/pages/dashboard/AnalyticsPage";

function DrawerRow({ label, value, mono, className }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-semibold">{label}</div>
      <div className={cls("text-sm mt-1 truncate", mono && "font-mono tabular", className)}>{value}</div>
    </div>
  );
}

// =====================================================================
// TIMELINE — vertical animated step list (signal → score → gate → entry → manage → close)
// =====================================================================
function TimelineStep({ icon: Icon, title, detail, status, idx, isLast }) {
  // status: "done" | "neutral" | "fail"
  const dotClasses = {
    done:    "bg-emerald-500/15 text-emerald-400 ring-emerald-500/40 shadow-[0_0_12px_hsl(var(--success)/0.45)]",
    neutral: "bg-primary/10 text-primary ring-primary/30 shadow-[0_0_10px_hsl(var(--primary)/0.35)]",
    fail:    "bg-rose-500/15 text-rose-400 ring-rose-500/40 shadow-[0_0_10px_hsl(var(--destructive)/0.4)]",
  };
  const dotCls = dotClasses[status] || dotClasses.neutral;
  return (
    <div
      className={cls(
        "relative pl-12 pb-6 fade-up",
        `fade-up-${Math.min(idx, 5)}`
      )}
    >
      {/* Vertical connector */}
      {!isLast && (
        <span className="absolute left-[18px] top-9 bottom-0 w-px bg-gradient-to-b from-primary/40 to-border/30" />
      )}
      {/* Dot */}
      <div className={cls(
        "absolute left-0 top-0 h-9 w-9 rounded-full flex items-center justify-center ring-2 border border-card",
        dotCls
      )}>
        <Icon className="h-4 w-4" />
      </div>
      {/* Content */}
      <div className="pt-1.5">
        <div className="text-sm font-semibold text-foreground">{title}</div>
        {detail && (
          <div className="text-xs text-muted-foreground mt-0.5 font-mono">{detail}</div>
        )}
      </div>
    </div>
  );
}

function closeStatus(won, isStopout) {
  if (won) return "done";
  if (isStopout) return "fail";
  return "neutral";
}

function buildTimeline(trade) {
  const won = (trade.pnl ?? 0) >= 0;
  const reason = trade.reason || "—";
  // Determine if the trade was a clean win, a stop-out, or another close type
  const isStopout = reason && /SL|STOP/i.test(reason);
  // isTP retained for future use but currently we just style winners vs losers

  return [
    {
      icon: Activity,
      title: "Signal detected",
      detail: `${trade.strategy || "—"} · ${trade.side || "—"} @ ${trade.session || "?"}`,
      status: "done",
    },
    {
      icon: Gauge,
      title: "Score computed",
      detail: trade.score != null
        ? `Final score ${trade.score} · regime ${trade.regime || "—"}`
        : "Score not recorded",
      status: "done",
    },
    {
      icon: ShieldCheck,
      title: "Gates passed",
      detail: "HTF · velocity · news · concurrent · daily — all clear",
      status: "done",
    },
    {
      icon: Send,
      title: "Order sent",
      detail: `${trade.side || "—"} ${trade.lots?.toFixed(2) || "?"} lots @ ${fmtPrice(trade.openPrice)}`,
      status: "done",
    },
    {
      icon: CheckCircle2,
      title: "Filled & live",
      detail: trade.openTime ? new Date(trade.openTime).toLocaleString() : "—",
      status: "done",
    },
    {
      icon: Cog,
      title: "Position managed",
      detail: `SL ${fmtPrice(trade.sl)} · TP ${fmtPrice(trade.tp)}`,
      status: "done",
    },
    {
      icon: won ? Flag : Flag,
      title: won ? "Closed in profit" : "Closed in loss",
      detail: `${reason} · ${trade.closeTime ? new Date(trade.closeTime).toLocaleString() : "—"}`,
      status: won ? "done" : isStopout ? "fail" : "neutral",
    },
  ];
}

export default function TradeLifecycleDrawer({ trade, onClose }) {
  const steps = useMemo(() => (trade ? buildTimeline(trade) : []), [trade]);
  // buildTimeline is a stable module-level function; intentionally not in deps.
  if (!trade) return null;
  const pnl = trade.pnl ?? 0;
  const won = pnl >= 0;
  return (
    <div
      className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-md"
      onClick={onClose}
      data-testid="trade-lifecycle-overlay"
    >
      <div
        className="absolute right-0 top-0 h-full w-full max-w-md cockpit-card border-l border-border shadow-[0_0_60px_-20px_hsl(var(--primary)/0.5)] overflow-y-auto rounded-none"
        style={{ animation: "nx-slide-in 0.35s cubic-bezier(0.22, 1, 0.36, 1) both" }}
        onClick={(e) => e.stopPropagation()}
        data-testid="trade-lifecycle-drawer"
      >
        <style>{`
          @keyframes nx-slide-in {
            from { transform: translateX(20px); opacity: 0; }
            to   { transform: translateX(0); opacity: 1; }
          }
        `}</style>

        {/* HEADER */}
        <div className="p-6 border-b border-border flex items-start justify-between gap-4 sticky top-0 bg-card/80 backdrop-blur-xl z-10">
          <div>
            <div className="eyebrow flex items-center gap-1.5">
              <span className="font-mono">TRADE #{trade.ticket}</span>
              <span
                className={cls(
                  "px-1.5 py-0.5 rounded text-[9px] font-bold border",
                  trade.side === "BUY"
                    ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                    : "bg-rose-500/15 text-rose-400 border-rose-500/30"
                )}
              >
                {trade.side === "BUY"
                  ? <TrendingUp className="inline h-2.5 w-2.5 -mt-px" />
                  : <TrendingDown className="inline h-2.5 w-2.5 -mt-px" />}
                {" "}{trade.side || "—"}
              </span>
            </div>
            <h3 className="font-semibold text-xl tracking-tight mt-1.5 font-mono">
              {trade.strategy || "—"}
            </h3>
            <div className="text-[11px] text-muted-foreground mt-1 font-mono tabular">
              {trade.symbol || "—"} · {trade.closeTime ? new Date(trade.closeTime).toLocaleString() : "—"}
            </div>
          </div>
          <button
            onClick={onClose}
            data-testid="trade-drawer-close"
            className="h-9 w-9 rounded-lg border border-border flex items-center justify-center hover:bg-secondary hover:border-primary/40 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* P&L Hero */}
          <div className={cls(
            "rounded-2xl border p-5 text-center relative overflow-hidden",
            won
              ? "bg-emerald-500/10 border-emerald-500/30 shadow-[0_0_30px_-10px_hsl(var(--success)/0.5)]"
              : "bg-rose-500/10 border-rose-500/30 shadow-[0_0_30px_-10px_hsl(var(--destructive)/0.5)]"
          )}>
            <div className="eyebrow">Realised P&amp;L</div>
            <div className={cls(
              "font-mono font-bold text-4xl tabular mt-2 leading-none",
              won ? POS_TEXT : NEG_TEXT
            )}>
              {won ? "+" : ""}${fmtMoney(pnl)}
            </div>
            <div className={cls(
              "mt-2 text-xs font-semibold uppercase tracking-[0.18em] font-mono",
              won ? POS_TEXT : NEG_TEXT
            )}>
              {won ? "◉ Winning trade" : "◯ Losing trade"}
            </div>
          </div>

          {/* Timeline */}
          <div>
            <div className="eyebrow mb-4 flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5" /> Execution timeline
            </div>
            <div data-testid="trade-timeline">
              {steps.map((s, i) => (
                <TimelineStep
                  key={s.title}
                  {...s}
                  idx={i}
                  isLast={i === steps.length - 1}
                />
              ))}
            </div>
          </div>

          {/* Snapshot grid */}
          <div>
            <div className="eyebrow mb-3">Snapshot</div>
            <div className="grid grid-cols-2 gap-3">
              <DrawerRow label="Lots" value={trade.lots?.toFixed(2) ?? "—"} mono />
              <DrawerRow label="Magic" value={trade.magic ?? "—"} mono />
              <DrawerRow label="Open price" value={fmtPrice(trade.openPrice)} mono />
              <DrawerRow label="Close price" value={fmtPrice(trade.closePrice)} mono />
              <DrawerRow label="SL" value={fmtPrice(trade.sl)} mono className={NEG_TEXT} />
              <DrawerRow label="TP" value={fmtPrice(trade.tp)} mono className={POS_TEXT} />
            </div>
          </div>

          {/* Decision context */}
          <div>
            <div className="eyebrow mb-3">Decision context</div>
            <div className="grid grid-cols-2 gap-3">
              <DrawerRow label="Reason"
                         value={trade.reason || "—"}
                         className={REASON_COLORS[trade.reason]?.includes("emerald") ? POS_TEXT : NEG_TEXT}
                         mono />
              <DrawerRow label="Score" value={trade.score ?? "—"} mono />
              <DrawerRow label="Session" value={trade.session || "—"} mono />
              <DrawerRow label="Regime" value={trade.regime || "—"} mono />
            </div>
          </div>

          <div className="text-[11px] text-muted-foreground/70 italic leading-relaxed border-t border-border pt-4">
            Tip: extra context (HTF bias, AMD phase, all 35 strategy scores at trigger bar)
            will appear here as soon as the EA pushes them with the trade reason record.
            Currently shown fields are populated from <code className="font-mono">db.trades</code> and
            <code className="font-mono"> db.trade_reasons</code>.
          </div>
        </div>
      </div>
    </div>
  );
}
