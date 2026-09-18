import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Activity, Calculator, KeyRound, LogOut, Moon, Server, Settings, Sun } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import { PRIMARY_WORKSPACES, UTILITY_ROUTES, workspaceForPath } from "@/lib/workspaces";

const utilityIcons = { "/risk-calc": Calculator, "/settings": Settings, "/licenses": KeyRound, "/system": Server };
const cls = (...values) => values.filter(Boolean).join(" ");

function WorkspaceNav({ pathname, onNavigate }) {
  const activeWorkspace = workspaceForPath(pathname)?.id;
  return <nav className="space-y-1 px-3" aria-label="Primary workspaces">
    <div className="px-2 pb-2 font-mono text-[9px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Workspaces</div>
    {PRIMARY_WORKSPACES.map(({ id, to, label, icon: Icon }) => {
      const active = activeWorkspace === id;
      return <Link key={id} to={to} onClick={onNavigate} data-testid={`nav-workspace-${id}`} aria-current={active ? "page" : undefined} className={cls("flex items-center gap-3 rounded-md border px-3 py-2.5 text-sm transition-colors", active ? "border-border bg-secondary text-foreground" : "border-transparent text-muted-foreground hover:bg-secondary/60 hover:text-foreground")}><Icon className={cls("h-4 w-4", active && "text-primary")} strokeWidth={1.75}/><span className="font-medium">{label}</span></Link>;
    })}
  </nav>;
}

function UtilityNav({ pathname, onNavigate }) {
  return <nav className="space-y-0.5" aria-label="Utilities">{UTILITY_ROUTES.map(({ to, label }) => { const Icon = utilityIcons[to]; const active = pathname === to; return <Link key={to} to={to} onClick={onNavigate} data-testid={`nav-utility-${to.slice(1)}`} className={cls("flex items-center gap-2 rounded-md px-2.5 py-2 text-xs transition-colors", active ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground")}><Icon className="h-3.5 w-3.5"/><span>{label}</span></Link>; })}</nav>;
}

export default function Sidebar({ status, mobileOpen, setMobileOpen }) {
  const { logout, user } = useAuth();
  const { theme, toggle } = useTheme();
  const location = useLocation();
  const [age, setAge] = useState(null);
  const touchStartX = useRef(null);

  useEffect(() => {
    if (!status?.lastUpdate) { setAge(null); return undefined; }
    const tick = () => setAge(Math.max(0, Math.round((Date.now() - new Date(status.lastUpdate).getTime()) / 1000)));
    tick(); const id = setInterval(tick, 1000); return () => clearInterval(id);
  }, [status?.lastUpdate]);

  const close = () => setMobileOpen(false);
  const bridgeState = status?.bridgeState || (status?.online ? "LIVE" : status ? "DISCONNECTED" : "UNAVAILABLE");
  const bridgeTone = bridgeState === "LIVE" ? "bg-emerald-500" : bridgeState === "UNAVAILABLE" ? "bg-zinc-500" : "bg-amber-500";

  return <>
    {mobileOpen ? <button type="button" aria-label="Close navigation" className="fixed inset-0 z-40 bg-black/45 lg:hidden" onClick={close}/> : null}
    <aside data-testid="sidebar" onTouchStart={(event) => { touchStartX.current = event.touches[0].clientX; }} onTouchEnd={(event) => { if (touchStartX.current != null && event.changedTouches[0].clientX - touchStartX.current < -50) close(); touchStartX.current = null; }} className={cls("fixed left-0 top-0 z-50 flex h-screen w-64 flex-col border-r border-border bg-card transition-transform duration-200 lg:sticky lg:z-auto lg:w-56", mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0")}>
      <div className="flex h-16 items-center gap-3 border-b border-border px-5"><div className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-secondary text-primary"><Activity className="h-4 w-4"/></div><div><div className="text-sm font-bold tracking-[0.12em]">NEXUS</div><div className="mt-0.5 text-[9px] uppercase tracking-[0.14em] text-muted-foreground">Quant Terminal</div></div></div>
      <div className="min-h-0 flex-1 overflow-y-auto py-4"><WorkspaceNav pathname={location.pathname} onNavigate={close}/></div>
      <div className="border-t border-border p-3">
        <div className="mb-3 rounded-md border border-border bg-background/50 p-2.5" data-testid="sidebar-system-state"><div className="flex items-center justify-between gap-2"><span className="text-[10px] text-muted-foreground">System</span><span className="flex items-center gap-1.5 font-mono text-[9px]"><span className={cls("h-1.5 w-1.5 rounded-full", bridgeTone)}/>{bridgeState}</span></div><div className="mt-1 font-mono text-[9px] text-muted-foreground">{age == null ? "Last update —" : `Last update ${age}s`}</div></div>
        <UtilityNav pathname={location.pathname} onNavigate={close}/>
        <div className="mt-3 flex items-center gap-1 border-t border-border pt-3"><button type="button" onClick={toggle} data-testid="theme-toggle" aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`} className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground">{theme === "dark" ? <Moon className="h-4 w-4"/> : <Sun className="h-4 w-4"/>}</button><div className="min-w-0 flex-1 truncate px-2 text-[10px] text-muted-foreground" title={user?.email || "admin"}>{user?.email || "admin"}</div><button type="button" onClick={logout} data-testid="logout-button" aria-label="Sign out" className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-rose-500/10 hover:text-rose-500"><LogOut className="h-4 w-4"/></button></div>
      </div>
    </aside>
  </>;
}
