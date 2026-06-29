import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Sparkles, ChevronRight, ShieldAlert, AlertOctagon, Info, X, Loader2,
} from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

const SEV_CFG = {
  critical: { icon: AlertOctagon, cls: "text-rose-300 bg-rose-500/10 border-rose-500/30",
              dot: "bg-rose-400", glow: "shadow-[0_0_18px_-4px_hsl(var(--destructive)/0.55)]" },
  warning:  { icon: ShieldAlert, cls: "text-amber-300 bg-amber-500/10 border-amber-500/30",
              dot: "bg-amber-400", glow: "shadow-[0_0_12px_-4px_hsl(var(--warning)/0.45)]" },
  info:     { icon: Info, cls: "text-cyan-300 bg-cyan-500/10 border-cyan-500/30",
              dot: "bg-cyan-400", glow: "" },
};

function AlertRow({ alert, onApply, applyingId, dismissedIds, onDismiss }) {
  const cfg = SEV_CFG[alert.severity] || SEV_CFG.info;
  const Icon = cfg.icon;
  const isApplying = applyingId === alert.id;
  if (dismissedIds.includes(alert.id)) return null;
  return (
    <div
      data-testid={`coach-alert-${alert.id}`}
      className={`rounded-lg border px-3 py-2.5 ${cfg.cls} ${cfg.glow} group transition-all`}
    >
      <div className="flex items-start gap-2">
        <Icon className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold tracking-tight">{alert.title}</div>
          <div className="text-[11px] opacity-80 mt-0.5 leading-relaxed font-mono">{alert.body}</div>
          {alert.suggested_action && (
            <button
              onClick={() => onApply(alert)}
              disabled={isApplying}
              data-testid={`coach-alert-apply-${alert.id}`}
              className="mt-2 inline-flex items-center gap-1 px-2 py-0.5 rounded bg-current/20 text-[10px] font-bold uppercase tracking-wider hover:bg-current/40 transition-all active:scale-95"
            >
              {isApplying ? <Loader2 className="h-2.5 w-2.5 animate-spin" /> : "Apply"}
              {!isApplying && <ChevronRight className="h-2.5 w-2.5" />}
            </button>
          )}
        </div>
        <button
          onClick={() => onDismiss(alert.id)}
          className="opacity-50 hover:opacity-100 transition-opacity"
          title="Nascondi"
        >
          <X className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}

export default function CoachLiveWidget() {
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [dismissedIds, setDismissedIds] = useState([]);
  const [applyingId, setApplyingId] = useState(null);
  const popoverRef = useRef(null);

  // Poll proactive alerts every 60s
  useEffect(() => {
    let cancelled = false;
    const fetch = async () => {
      try {
        const { data } = await api.get("/coach/proactive_alerts");
        if (!cancelled) setAlerts(data.alerts || []);
      } catch (e) {
        console.warn("[CoachLiveWidget] poll failed", e?.message || e);
      }
    };
    fetch();
    const iv = setInterval(fetch, 60_000);
    return () => { cancelled = true; clearInterval(iv); };
  }, []);

  // Click outside to close
  useEffect(() => {
    if (!open) return;
    const onClick = (e) => {
      if (!popoverRef.current?.contains(e.target)) setOpen(false);
    };
    setTimeout(() => document.addEventListener("click", onClick), 50);
    return () => document.removeEventListener("click", onClick);
  }, [open]);

  const visibleAlerts = alerts.filter((a) => !dismissedIds.includes(a.id));
  const hasCritical = visibleAlerts.some((a) => a.severity === "critical");
  const hasWarning = visibleAlerts.some((a) => a.severity === "warning");
  const count = visibleAlerts.length;

  const handleApply = async (alert) => {
    if (!alert.suggested_action) return;
    setApplyingId(alert.id);
    try {
      const { data } = await api.post("/coach/apply_action", alert.suggested_action);
      toast.success(`✓ ${data.applied || "Azione applicata"}`);
      setDismissedIds((d) => [...d, alert.id]);
    } catch (e) {
      toast.error(`Errore: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setApplyingId(null);
    }
  };

  const ringClass = hasCritical
    ? "ring-rose-500/50 shadow-[0_0_24px_-4px_hsl(var(--destructive)/0.55)]"
    : hasWarning
      ? "ring-amber-500/50 shadow-[0_0_18px_-4px_hsl(var(--warning)/0.45)]"
      : "ring-primary/30 shadow-[0_0_16px_-4px_hsl(var(--primary)/0.4)]";

  return (
    <div className="fixed bottom-20 right-6 z-50" ref={popoverRef}>
      {/* Trigger button */}
      <button
        onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}
        data-testid="coach-live-widget"
        className={`relative h-12 w-12 rounded-full bg-card border ring-1 ${ringClass} flex items-center justify-center transition-all hover:scale-110 active:scale-95 group`}
      >
        <Sparkles className={`h-5 w-5 transition-colors ${hasCritical ? "text-rose-400" : hasWarning ? "text-amber-400" : "text-primary"}`} />
        {count > 0 && (
          <span className={`absolute -top-1 -right-1 min-w-5 h-5 px-1 rounded-full text-[10px] font-bold flex items-center justify-center ${
            hasCritical ? "bg-rose-500 text-white" : hasWarning ? "bg-amber-500 text-amber-950" : "bg-primary text-primary-foreground"
          }`}>
            {count}
          </span>
        )}
        {/* Pulse ring on critical */}
        {hasCritical && (
          <span className="absolute inset-0 rounded-full bg-rose-500 opacity-40 animate-ping" />
        )}
      </button>

      {/* Popover */}
      {open && (
        <div
          onClick={(e) => e.stopPropagation()}
          data-testid="coach-popover"
          className="absolute bottom-14 right-0 w-80 rounded-2xl cockpit-card border border-border shadow-[0_30px_60px_-15px_hsl(var(--primary)/0.4)] overflow-hidden fade-in"
        >
          <div className="px-4 py-3 border-b border-border bg-secondary/30 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <div className="flex-1">
              <div className="font-semibold text-sm">Coach Live</div>
              <div className="text-[10px] text-muted-foreground font-mono tracking-wider uppercase">
                {count > 0 ? `${count} alert attivi` : "tutto tranquillo"}
              </div>
            </div>
            <button
              onClick={() => {
                setOpen(false);
                let qs = "";
                try {
                  const raw = localStorage.getItem("nxs_chart_context");
                  if (raw) {
                    const ctx = JSON.parse(raw);
                    // Pass context only if it's fresh (last 5 minutes)
                    if (ctx?.symbol && ctx?.tf && (Date.now() - (ctx.ts || 0) < 300_000)) {
                      qs = `?symbol=${encodeURIComponent(ctx.symbol)}&tf=${encodeURIComponent(ctx.tf)}`;
                    }
                  }
                } catch (err) { void err; }
                nav("/coach" + qs);
              }}
              className="text-[11px] text-primary font-mono hover:underline flex items-center gap-0.5"
              data-testid="coach-popover-open-chat"
            >
              Chat <ChevronRight className="h-3 w-3" />
            </button>
          </div>

          <div className="p-3 space-y-2 max-h-[60vh] overflow-y-auto">
            {visibleAlerts.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <Sparkles className="h-8 w-8 mx-auto mb-2 opacity-30" />
                <div className="text-xs">Nessun alert. Coach sta vigilando…</div>
                <div className="text-[10px] opacity-60 mt-1 font-mono">refresh ogni 60s</div>
              </div>
            )}
            {visibleAlerts.map((a) => (
              <AlertRow
                key={a.id}
                alert={a}
                onApply={handleApply}
                applyingId={applyingId}
                dismissedIds={dismissedIds}
                onDismiss={(id) => setDismissedIds((d) => [...d, id])}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
