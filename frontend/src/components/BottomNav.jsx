import { Link, useLocation } from "react-router-dom";
import { Menu } from "lucide-react";
import { PRIMARY_WORKSPACES, workspaceForPath } from "@/lib/workspaces";

const cls = (...values) => values.filter(Boolean).join(" ");
const mobileWorkspaces = PRIMARY_WORKSPACES.filter(({ id }) => id !== "library");

export default function BottomNav({ onMenuOpen }) {
  const location = useLocation();
  const activeWorkspace = workspaceForPath(location.pathname)?.id;
  return <nav data-testid="bottom-nav" aria-label="Mobile workspaces" className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card lg:hidden" style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
    <div className="mx-auto grid max-w-md grid-cols-5">
      {mobileWorkspaces.map(({ id, to, label, icon: Icon }) => { const active = activeWorkspace === id; return <Link key={id} to={to} data-testid={`bottomnav-${id}`} aria-current={active ? "page" : undefined} className={cls("flex flex-col items-center justify-center gap-1 py-2.5 text-[10px] transition-colors", active ? "text-primary" : "text-muted-foreground")}><Icon className="h-4.5 w-4.5" strokeWidth={active ? 2.1 : 1.65}/><span className="font-medium">{label}</span></Link>; })}
      <button type="button" onClick={onMenuOpen} data-testid="bottomnav-more" className="flex flex-col items-center justify-center gap-1 py-2.5 text-[10px] text-muted-foreground"><Menu className="h-4.5 w-4.5"/><span className="font-medium">More</span></button>
    </div>
  </nav>;
}
