import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Activity, LogOut, Sun, Moon,
  LayoutDashboard, SlidersHorizontal, LineChart as LineChartIcon,
  Settings as SettingsIcon, ShieldAlert, Sparkles, BookOpen, MessageSquare,
  FlaskConical, CalendarDays, Calculator, KeyRound, Microscope, CandlestickChart,
  Link2, Cpu,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";

function cls(...c) { return c.filter(Boolean).join(" "); }

const SIDEBAR_ITEMS = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/chart", label: "Live Chart", icon: CandlestickChart },
  { to: "/strategies", label: "Strategies", icon: SlidersHorizontal },
  { to: "/analytics", label: "Analytics", icon: LineChartIcon },
  { to: "/strategy-analytics", label: "Strat Diag", icon: Microscope },
  { to: "/journal", label: "Journal", icon: BookOpen },
  { to: "/coach", label: "AI Coach", icon: MessageSquare },
  { to: "/whatif", label: "What-if", icon: Sparkles },
  { to: "/backtest", label: "Backtest", icon: FlaskConical },
  { to: "/chain", label: "Chain", icon: Link2 },
  { to: "/local-bridge", label: "MT5 Bridge", icon: Cpu },
  { to: "/calendar", label: "Calendar", icon: CalendarDays },
  { to: "/risk", label: "Risk", icon: ShieldAlert },
  { to: "/risk-calc", label: "Calculator", icon: Calculator },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
  { to: "/licenses", label: "Licenses", icon: KeyRound },
];

function deriveBridgeState({ bridgeState, online, lastSec }) {
  if (bridgeState) return bridgeState;
  if (online) return "LIVE";
  if (lastSec == null) return "NOT_INITIALIZED";
  return "DISCONNECTED";
}

function BridgeStatusCard({ online, lastSec, stale, bridgeState }) {
  // v2.0.9 — 4 semantic states from /api/ea/health
  const state = deriveBridgeState({ bridgeState, online, lastSec });
  const stateConfig = {
    LIVE:             { dot: "bg-emerald-400", glow: "glow-success", label: "Bridge live",         pulse: true,  badgeCls: "" },
    IDLE:             { dot: "bg-amber-400",   glow: "glow-warning", label: "Bridge idle",         pulse: false, badgeCls: "text-amber-400 border-amber-500/30 bg-amber-500/15" },
    DISCONNECTED:     { dot: "bg-rose-500",    glow: "glow-danger",  label: "Bridge disconnected", pulse: false, badgeCls: "text-rose-400 border-rose-500/30 bg-rose-500/15" },
    NOT_INITIALIZED:  { dot: "bg-zinc-500",    glow: "",             label: "Bridge not ready",    pulse: false, badgeCls: "text-zinc-400 border-zinc-500/30 bg-zinc-500/10" },
  };
  const cfg = stateConfig[state] || stateConfig.NOT_INITIALIZED;
  return (
    <div className="rounded-lg border border-border bg-secondary/40 px-3 py-3 space-y-2" data-testid={`bridge-status-${state}`}>
      <div className="flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          <span className={cls("relative inline-flex h-2 w-2 rounded-full", cfg.dot, cfg.glow)} />
          {cfg.pulse && (
            <span className="absolute inline-flex h-2 w-2 rounded-full pulse-ring text-emerald-400" />
          )}
        </span>
        <span className="text-xs font-medium text-foreground">{cfg.label}</span>
      </div>
      <div className="text-[11px] text-muted-foreground font-mono tabular" data-testid="connection-last-update">
        {lastSec != null ? `${lastSec}s ago` : "no data"}
      </div>
      {state !== "LIVE" && state !== "NOT_INITIALIZED" && (
        <span
          className={cls("inline-block px-1.5 py-0.5 rounded text-[10px] font-bold border", cfg.badgeCls)}
          data-testid={`bridge-state-badge-${state}`}
        >
          {state}
        </span>
      )}
      {state === "NOT_INITIALIZED" && (
        <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-zinc-500/10 text-zinc-400 border border-zinc-500/20" data-testid="demo-badge">
          DEMO DATA
        </span>
      )}
    </div>
  );
}

function ThemeToggle({ theme, onToggle }) {
  return (
    <button
      onClick={onToggle}
      data-testid="theme-toggle"
      className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-border text-sm hover:bg-secondary/60 transition-colors"
    >
      <span className="flex items-center gap-2 text-muted-foreground">
        {theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        {theme === "dark" ? "Dark" : "Light"}
      </span>
      <span className="text-[11px] text-muted-foreground">toggle</span>
    </button>
  );
}

function NavList({ items, pathname, onItemClick }) {
  return (
    <nav className="flex-1 min-h-0 overflow-y-auto px-3 space-y-1 pb-2">
      {items.map(({ to, label, icon: Icon }) => {
        const active = pathname === to;
        return (
          <Link
            key={to}
            to={to}
            onClick={onItemClick}
            data-testid={`nav-${label.toLowerCase()}`}
            className={cls(
              "group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200",
              active
                ? "bg-primary/10 text-foreground font-semibold"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
            )}
          >
            {active && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r-full bg-primary shadow-[0_0_10px_hsl(var(--primary)/0.6)]" />
            )}
            <Icon
              className={cls(
                "h-4 w-4 transition-colors",
                active ? "text-primary" : "group-hover:text-primary/80"
              )}
              strokeWidth={1.75}
            />
            <span>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

export default function Sidebar({ status, mobileOpen, setMobileOpen }) {
  const { logout, user } = useAuth();
  const { theme, toggle } = useTheme();
  const loc = useLocation();

  const online = !!status?.online;
  const [lastSec, setLastSec] = useState(null);
  const lastUpdate = status?.lastUpdate;

  useEffect(() => {
    if (!lastUpdate) { setLastSec(null); return undefined; }
    const tick = () => setLastSec(Math.round((Date.now() - new Date(lastUpdate).getTime()) / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [lastUpdate]);

  const stale = lastSec != null && lastSec > 15;
  const closeMobile = () => setMobileOpen(false);

  // Swipe-to-close (mobile only)
  const touchStartX = useRef(null);
  const onTouchStart = (e) => { touchStartX.current = e.touches[0].clientX; };
  const onTouchEnd = (e) => {
    if (touchStartX.current == null) return;
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    if (dx < -50) closeMobile();   // swipe left = close
    touchStartX.current = null;
  };

  return (
    <>
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/40 backdrop-blur-sm z-40 fade-in"
          onClick={closeMobile}
        />
      )}

      <aside
        data-testid="sidebar"
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        className={cls(
          "fixed lg:sticky top-0 left-0 z-50 lg:z-auto",
          "h-screen w-72 sm:w-64 flex flex-col",
          "bg-card border-r border-border shadow-2xl lg:shadow-none",
          "transition-transform duration-300 ease-out",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div className="px-6 pt-6 pb-8 flex items-center gap-3">
          <div className="relative h-10 w-10 rounded-xl bg-primary/15 text-primary flex items-center justify-center ring-1 ring-primary/30 shadow-[0_0_18px_hsl(var(--primary)/0.35)]">
            <Activity className="h-5 w-5" strokeWidth={2.25} />
          </div>
          <div>
            <div className="font-bold text-lg tracking-tight leading-none">NEXUS</div>
            <div className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground mt-1.5">
              EA Control Center
            </div>
          </div>
        </div>

        <NavList items={SIDEBAR_ITEMS} pathname={loc.pathname} onItemClick={closeMobile} />

        <div className="px-4 pb-4 space-y-3">
          <BridgeStatusCard online={online} lastSec={lastSec} stale={stale} bridgeState={status?.bridgeState} />
          <ThemeToggle theme={theme} onToggle={toggle} />

          <div className="px-3 py-2 text-[11px] text-muted-foreground">
            Signed in as <span className="font-semibold text-foreground">{user?.email || "admin"}</span>
          </div>
          <button
            onClick={logout}
            data-testid="logout-button"
            className="flex items-center gap-2 w-full text-sm text-muted-foreground hover:text-rose-600 dark:hover:text-rose-400 px-3 py-2 rounded-lg hover:bg-rose-500/10 transition-colors"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>
    </>
  );
}
