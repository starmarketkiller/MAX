// Shared primitives, helpers and constants used across Dashboard sub-pages.
import { ShieldAlert } from "lucide-react";

// ---------- text helpers ----------
export const fmtMoney = (v, dec = 2) =>
  v == null ? "—" :
  Number(v).toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
export const fmtSign = (v) => {
  if (v == null) return "—";
  return v >= 0 ? `+${fmtMoney(v)}` : fmtMoney(v);
};
export const fmtPct = (v) => (v == null ? "—" : `${Number(v).toFixed(2)}%`);
export const fmtPrice = (v) => (v == null ? "—" : Number(v).toFixed(2));
export const cls = (...x) => x.filter(Boolean).join(" ");

export const POS_TEXT = "text-emerald-600 dark:text-emerald-400";
export const NEG_TEXT = "text-rose-600 dark:text-rose-400";

// ---------- strategies list (v2.0.7b — 35 strategies organized by family) ----------
// Tuple: [key, label, family]
export const STRAT_LIST = [
  // TREND (8)
  ["ADX_RSI",       "ADX + RSI Trend",         "TREND"],
  ["MACD",          "MACD Trend",              "TREND"],
  ["EMA_PULLBACK",  "Trend EMA Pullback",      "TREND"],
  ["BREAKOUT_ACC",  "Breakout Acceptance",     "TREND"],
  ["LONDON_BO",     "London Breakout",         "TREND"],
  ["ICHIMOKU",      "Ichimoku Kumo Break",     "TREND"],
  ["SAR",           "Parabolic SAR",           "TREND"],
  ["TSI",           "TSI Momentum (RSI+EMA)",  "TREND"],
  // REVERSAL (4)
  ["BOLLINGER",     "Bollinger Mean Reversion","REVERSAL"],
  ["BJORGUM",       "Bjorgum Key Levels",      "REVERSAL"],
  ["BB_SQUEEZE",    "BB Squeeze Breakout",     "REVERSAL"],
  ["RSI_DIV",       "RSI Divergence",          "REVERSAL"],
  // SMC/ICT (14)
  ["LIQ_SWEEP",     "Liquidity Sweep",         "SMC"],
  ["FVG_CONT",      "FVG Continuation",        "SMC"],
  ["ORDER_BLOCK",   "Order Block Retest",      "SMC"],
  ["STRUCT_REACT",  "Structure Reaction",      "SMC"],
  ["TURTLE_SOUP",   "Turtle Soup",             "SMC"],
  ["IFVG",          "Inverted FVG + MSS",      "SMC"],
  ["FVG_MIT",       "FVG Mitigation",          "SMC"],
  ["OB_MIT",        "OB Structural Mitigation","SMC"],
  ["SH_BMS_RTO",    "Stop Hunt → BMS → RTO",   "SMC"],
  ["SMS_BMS_RTO",   "SMS → BMS → RTO",         "SMC"],
  ["SILVER_BULLET", "Silver Bullet (LO/NY KZ)","SMC"],
  ["AMD_REVERSAL",  "AMD Reversal",            "SMC"],
  ["OTE_CONT",      "OTE Continuation",        "SMC"],
  ["MALAYSIAN_SNR", "Malaysian S/R",           "SMC"],
  // INSTITUTIONAL v2.0.7 (9) — READY_FOR_BACKTEST
  ["CISD",          "Change In State of Delivery","INSTITUTIONAL"],
  ["AMD_CONT",      "AMD Continuation",        "INSTITUTIONAL"],
  ["JUDAS_SWING",   "Judas Swing",             "INSTITUTIONAL"],
  ["LDN_REVERSAL",  "London Reversal",         "INSTITUTIONAL"],
  ["NY_REVERSAL",   "NY Reversal",             "INSTITUTIONAL"],
  ["WEEKLY_EXP",    "Weekly Range Expansion",  "INSTITUTIONAL"],
  ["PO3",           "Power of Three",          "INSTITUTIONAL"],
  ["LIQ_VOID",      "Liquidity Void Cont.",    "INSTITUTIONAL"],
  ["DISP_REBAL",    "Displacement Rebalance",  "INSTITUTIONAL"],
  // RANGE / COUNTER-HTF v2.0.8
  ["RANGE_FADE",    "Range Fade (low ADX)",    "REVERSAL"],
  // ELLIOTT WAVE v2.0.20
  ["ELLIOTT",       "Elliott Wave (W2/W4/W5)", "INSTITUTIONAL"],
];

export const STRAT_FAMILIES = [
  { id: "TREND",         label: "Trend",         color: "blue" },
  { id: "REVERSAL",      label: "Reversal",      color: "fuchsia" },
  { id: "SMC",           label: "SMC/ICT",       color: "violet" },
  { id: "INSTITUTIONAL", label: "Institutional", color: "emerald" },
];

export const STRAT_FAMILY_COLOR = {
  TREND:         "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30",
  REVERSAL:      "bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-400 border-fuchsia-500/30",
  SMC:           "bg-violet-500/15 text-violet-700 dark:text-violet-400 border-violet-500/30",
  INSTITUTIONAL: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
};

// ---------- dialog presets ----------
export const DIALOGS = Object.freeze({
  pause: {
    title: "Pause the EA?",
    body: "Stops opening new positions. Open positions remain managed (BE / Trail) until resumed.",
  },
  closeAll: {
    title: "Close all positions?",
    body: "Sends CLOSE_ALL to the EA. All NEXUS-magic positions are closed at market. Irreversible.",
  },
  resetAntiRevenge: {
    title: "Reset anti-revenge?",
    body: "Clears the anti-revenge cooldown and consecutive-loss counter. The EA can resume opening trades immediately.",
    danger: false,
    confirmLabel: "Reset",
  },
  resetDaily: {
    title: "Reset daily counters?",
    body: "Sets trades-today to 0 and snapshots the current balance as daily baseline.",
    danger: false,
    confirmLabel: "Reset",
  },
});

// ---------- chart constants ----------
export const CHART_COLORS = {
  light: {
    grid: "#e2e8f0",
    axis: "#64748b",
    tooltipBg: "#ffffff",
    tooltipBorder: "#e2e8f0",
    tooltipText: "#0f172a",
    equity: "#0891b2",
    balance: "#94a3b8",
    equityFillFrom: "rgba(8, 145, 178, 0.30)",
    equityFillTo: "rgba(8, 145, 178, 0.00)",
  },
  dark: {
    grid: "rgba(56, 189, 248, 0.08)",
    axis: "#64748b",
    tooltipBg: "rgba(13, 19, 32, 0.95)",
    tooltipBorder: "rgba(34, 211, 238, 0.25)",
    tooltipText: "#e2e8f0",
    equity: "#22d3ee",
    balance: "#475569",
    equityFillFrom: "rgba(34, 211, 238, 0.35)",
    equityFillTo: "rgba(34, 211, 238, 0.00)",
  },
};
export const EQUITY_CHART_MARGIN = { top: 5, right: 10, left: 0, bottom: 0 };
export const BAR_CHART_MARGIN = { top: 10, right: 10, left: 0, bottom: 50 };
export const YAXIS_DOMAIN_AUTO = ["auto", "auto"];

// ---------- pure tone helpers ----------
export function pnlTone(value) {
  return (value ?? 0) >= 0 ? "pos" : "neg";
}
export function pnlTextClass(value) {
  return (value ?? 0) >= 0 ? POS_TEXT : NEG_TEXT;
}
export function biasTone(bias) {
  if (bias === "BULL") return "pos";
  if (bias === "BEAR") return "neg";
  return "neutral";
}
export function velocityTone(velocity) {
  if (velocity?.includes?.("BULL")) return "pos";
  if (velocity?.includes?.("BEAR")) return "neg";
  return "neutral";
}
export function sweepTone(dir) {
  if (dir === "BUY") return "pos";
  if (dir === "SELL") return "neg";
  return "neutral";
}
export function bspTone(pct) {
  if (pct == null) return "neutral";
  if (pct > 55) return "pos";
  if (pct < 45) return "neg";
  return "neutral";
}
export function trendTone(trend) {
  if (trend === "UP") return "pos";
  if (trend === "DN") return "neg";
  return "neutral";
}
export function bosLabel(status) {
  if (status?.bosUp) return "UP";
  if (status?.bosDown) return "DOWN";
  return "—";
}
export function chochLabel(status) {
  if (status?.chochUp) return "UP";
  if (status?.chochDown) return "DOWN";
  return "—";
}
export function qualityToneClass(quality) {
  if (quality >= 80) return POS_TEXT;
  if (quality >= 60) return "text-foreground";
  return "text-muted-foreground";
}
export function reactionPriceLabel(reaction) {
  if (reaction?.reactionType === "SWING_LOW" && reaction.lastSwingLow) return fmtPrice(reaction.lastSwingLow);
  if (reaction?.reactionType === "SWING_HIGH" && reaction.lastSwingHigh) return fmtPrice(reaction.lastSwingHigh);
  return "active zone";
}

// ---------- shared building-block components ----------
export function Card({ children, className, testId, interactive = false }) {
  return (
    <div
      data-testid={testId}
      className={cls(
        "cockpit-card",
        interactive && "hover-lift cursor-pointer",
        className
      )}
    >
      {children}
    </div>
  );
}

export function SectionHeader({ eyebrow, title, icon: Icon, right }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-5">
      <div>
        <div className="eyebrow flex items-center gap-1.5">
          {Icon && <Icon className="h-3.5 w-3.5" />}
          {eyebrow}
        </div>
        <h3 className="font-semibold text-lg tracking-tight mt-1">{title}</h3>
      </div>
      {right && <div className="text-xs text-muted-foreground">{right}</div>}
    </div>
  );
}

function toneTextClass(tone, neutralClass) {
  if (tone === "pos") return POS_TEXT;
  if (tone === "neg") return NEG_TEXT;
  return neutralClass;
}

export function KpiCard({ label, value, sub, tone, icon: Icon, testId, delta }) {
  const valueTone = toneTextClass(tone, "text-foreground");
  const subTone = toneTextClass(tone, "text-muted-foreground");
  return (
    <Card className="p-6 hover-lift group" testId={testId}>
      <div className="flex items-center justify-between mb-4">
        <div className="eyebrow">{label}</div>
        {Icon && (
          <div className="h-7 w-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center transition-colors group-hover:bg-primary/20">
            <Icon className="h-3.5 w-3.5" />
          </div>
        )}
      </div>
      <div className={cls(
        "font-mono font-bold text-3xl leading-none tracking-tight tabular",
        valueTone
      )}>
        {value}
      </div>
      <div className="flex items-center gap-2 mt-3 min-h-[1.25rem]">
        {delta != null && delta !== "" && (
          <span className={cls(
            "inline-flex items-center gap-0.5 font-mono text-[10px] font-bold tabular px-1.5 py-0.5 rounded",
            tone === "neg"
              ? "text-rose-400 bg-rose-500/10 border border-rose-500/20"
              : "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20"
          )}>
            {tone === "neg" ? "▼" : "▲"} {delta}
          </span>
        )}
        {sub && <div className={cls("text-xs font-medium", subTone)}>{sub}</div>}
      </div>
    </Card>
  );
}

export function Pill({ label, value, tone = "neutral", icon: Icon }) {
  const styles = {
    neutral: "bg-secondary/50 text-foreground border-border",
    pos: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/25",
    neg: "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/25",
    warn: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30",
    info: "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border-cyan-500/25",
  };
  return (
    <div className={cls(
      "px-3 py-2.5 rounded-lg border text-xs flex items-center justify-between gap-3 transition-colors hover:border-primary/30",
      styles[tone] || styles.neutral
    )}>
      <span className="uppercase tracking-[0.08em] font-semibold flex items-center gap-1.5 opacity-90">
        {Icon && <Icon className="h-3 w-3" />}
        {label}
      </span>
      <span className="font-mono text-[11px] font-bold tabular">{value || "—"}</span>
    </div>
  );
}

export function ConfirmDialog({ open, title, body, danger = true, confirmLabel = "Confirm", onConfirm, onCancel, testId }) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 fade-in"
      data-testid={testId}
      onClick={onCancel}
    >
      <div
        className="bg-card text-card-foreground rounded-2xl shadow-2xl border border-border max-w-md w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-4 mb-5">
          <div className={cls(
            "h-10 w-10 rounded-xl flex items-center justify-center flex-shrink-0",
            danger ? "bg-rose-500/15 text-rose-600 dark:text-rose-400" : "bg-sky-500/15 text-sky-600 dark:text-sky-400"
          )}>
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <div className="font-semibold text-lg leading-tight">{title}</div>
            <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{body}</p>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            data-testid="confirm-cancel"
            className="h-10 px-4 rounded-lg border border-border text-sm font-medium hover:bg-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            data-testid="confirm-confirm"
            className={cls(
              "h-10 px-5 rounded-lg text-sm font-semibold text-white transition-colors",
              danger
                ? "bg-rose-600 hover:bg-rose-700 dark:bg-rose-500 dark:hover:bg-rose-400"
                : "bg-sky-600 hover:bg-sky-700 dark:bg-sky-500 dark:hover:bg-sky-400"
            )}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// Shared gate-style helper (used by Home gates AND Health card)
export const GATE_STYLES = {
  pass: {
    container: "bg-emerald-500/10 border-emerald-500/25",
    badge: "bg-emerald-500 text-white",
    icon: "✓",
  },
  fail: {
    container: "bg-rose-500/10 border-rose-500/25",
    badge: "bg-rose-500 text-white",
    icon: "✕",
  },
  idle: {
    container: "bg-secondary/40 border-border",
    badge: "bg-muted text-muted-foreground",
    icon: "•",
  },
};
export function gateStyleFor(ok) {
  if (ok === true) return GATE_STYLES.pass;
  if (ok === false) return GATE_STYLES.fail;
  return GATE_STYLES.idle;
}
