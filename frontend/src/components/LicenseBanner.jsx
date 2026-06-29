import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldAlert, ShieldCheck, AlertOctagon, Clock, X } from "lucide-react";
import api from "@/lib/api";

const LEVEL_CFG = {
  EXPIRED: {
    icon: AlertOctagon,
    cls: "bg-rose-500/15 text-rose-300 border-rose-500/30",
    glow: "shadow-[0_0_18px_-4px_hsl(var(--destructive)/0.55)]",
    pulse: true,
  },
  CRITICAL: {
    icon: AlertOctagon,
    cls: "bg-amber-500/15 text-amber-300 border-amber-500/35",
    glow: "shadow-[0_0_14px_-4px_hsl(var(--warning)/0.55)]",
    pulse: true,
  },
  WARNING: {
    icon: ShieldAlert,
    cls: "bg-amber-500/10 text-amber-300 border-amber-500/25",
    glow: "",
    pulse: false,
  },
  OK: {
    icon: ShieldCheck,
    cls: "bg-emerald-500/10 text-emerald-300 border-emerald-500/25",
    glow: "",
    pulse: false,
  },
};

function formatDays(d) {
  if (d == null) return "—";
  if (d < 1) {
    const h = Math.max(1, Math.round(d * 24));
    return `${h}h`;
  }
  return `${Math.floor(d)}d`;
}

function messageFor(s) {
  if (!s) return "";
  if (s.level === "EXPIRED") {
    return `${s.expired_count} licenze scadute · rinnova per riattivare l'EA`;
  }
  if (s.level === "CRITICAL") {
    return `Trial in scadenza tra ${formatDays(s.days_until_expiry)} — rinnova ora`;
  }
  if (s.level === "WARNING") {
    return `License rinnovo entro ${formatDays(s.days_until_expiry)}`;
  }
  if (s.has_trial) {
    return `Trial attivo · ${formatDays(s.days_until_expiry)} rimanenti`;
  }
  if (s.has_active) return "Licenza attiva";
  // No active license but level is OK → empty state, banner should hide
  return "Licenza in attesa di attivazione";
}

export default function LicenseBanner() {
  const [summary, setSummary] = useState(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const fetch = async () => {
      try {
        const { data } = await api.get("/license/summary");
        if (!cancelled) setSummary(data);
      } catch (e) {
        // Silent — banner is non-critical
        console.warn("[LicenseBanner] fetch failed", e?.message || e);
      }
    };
    fetch();
    const iv = setInterval(fetch, 60_000); // refresh once a minute
    return () => { cancelled = true; clearInterval(iv); };
  }, []);

  // Show whenever there's something actionable: expired/critical/warning,
  // an active trial, or any license expiring within 14 days.
  const upcoming = summary?.days_until_expiry != null && summary.days_until_expiry <= 14;
  // Hide the banner if everything is fine (OK + has_active + no expiry warnings)
  const allGood = summary?.level === "OK" && summary?.has_active && !upcoming;
  const shouldShow =
    summary &&
    !dismissed &&
    !allGood &&
    (summary.level !== "OK" || summary.has_trial || upcoming);

  if (!shouldShow) return null;

  const cfg = LEVEL_CFG[summary.level] || LEVEL_CFG.OK;
  const Icon = cfg.icon;
  const isCritical = summary.level === "EXPIRED" || summary.level === "CRITICAL";

  return (
    <Link
      to="/licenses"
      data-testid="license-banner"
      className={`group hidden md:inline-flex h-9 items-center gap-2 px-3 rounded-lg border text-xs font-mono transition-all duration-300 active:scale-[0.98] ${cfg.cls} ${cfg.glow} hover:brightness-110`}
    >
      <span className="relative flex h-2 w-2 flex-shrink-0">
        <span className={`inline-flex h-2 w-2 rounded-full bg-current ${cfg.pulse ? "" : "opacity-80"}`} />
        {cfg.pulse && (
          <span className="absolute inline-flex h-2 w-2 rounded-full bg-current opacity-75 animate-ping" />
        )}
      </span>
      <Icon className="h-3.5 w-3.5 flex-shrink-0" />
      <span className="tabular truncate max-w-[220px] lg:max-w-none">
        {messageFor(summary)}
      </span>
      {isCritical && (
        <span className="hidden lg:inline ml-1 px-1.5 py-0.5 rounded bg-current/20 text-[10px] font-bold tracking-wider uppercase">
          {summary.level}
        </span>
      )}
      {!isCritical && (
        <button
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); setDismissed(true); }}
          data-testid="license-banner-dismiss"
          title="Nascondi"
          className="ml-1 opacity-50 hover:opacity-100 transition-opacity"
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </Link>
  );
}
