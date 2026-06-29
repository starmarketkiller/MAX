import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard, MessageSquare, ShieldAlert, BookOpen, Menu,
} from "lucide-react";

function cls(...c) { return c.filter(Boolean).join(" "); }

// 4 sezioni principali per il bottom nav mobile
const BOTTOM_ITEMS = [
  { to: "/",        label: "Home",    icon: LayoutDashboard },
  { to: "/coach",   label: "Coach",   icon: MessageSquare },
  { to: "/journal", label: "Journal", icon: BookOpen },
  { to: "/risk",    label: "Risk",    icon: ShieldAlert },
];

export default function BottomNav({ onMenuOpen }) {
  const loc = useLocation();

  return (
    <nav
      data-testid="bottom-nav"
      className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-card/95 backdrop-blur-lg border-t border-border safe-area-bottom"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="grid grid-cols-5 max-w-md mx-auto">
        {BOTTOM_ITEMS.map(({ to, label, icon: Icon }) => {
          const active = loc.pathname === to;
          return (
            <Link
              key={to}
              to={to}
              data-testid={`bottomnav-${label.toLowerCase()}`}
              className={cls(
                "flex flex-col items-center justify-center gap-0.5 py-2.5 transition-colors",
                active
                  ? "text-sky-600 dark:text-sky-400"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className={cls("h-5 w-5", active && "scale-110")} strokeWidth={active ? 2.25 : 1.75} />
              <span className={cls("text-[10px] font-medium", active && "font-bold")}>{label}</span>
              {active && (
                <span className="absolute top-0 h-0.5 w-8 bg-sky-500 rounded-b-full" />
              )}
            </Link>
          );
        })}
        <button
          onClick={onMenuOpen}
          data-testid="bottomnav-more"
          className="flex flex-col items-center justify-center gap-0.5 py-2.5 text-muted-foreground hover:text-foreground"
        >
          <Menu className="h-5 w-5" strokeWidth={1.75} />
          <span className="text-[10px] font-medium">More</span>
        </button>
      </div>
    </nav>
  );
}
