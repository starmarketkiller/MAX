import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search, ArrowRight, LayoutDashboard, SlidersHorizontal, LineChart,
  Microscope, BookOpen, MessageSquare, Sparkles, FlaskConical,
  CalendarDays, ShieldAlert, Calculator, Settings, KeyRound,
  Play, Pause, AlertOctagon, RotateCcw, Calendar,
  Command as CommandIcon,
} from "lucide-react";

function cls(...c) { return c.filter(Boolean).join(" "); }

function commandIconClass(isActive, isDanger) {
  if (!isActive) return "bg-secondary/50";
  return isDanger ? "bg-rose-500/15 text-rose-400" : "bg-primary/15 text-primary";
}

// Lightweight fuzzy match: every query char must appear in order in the haystack.
function fuzzyMatch(needle, hay) {
  if (!needle) return true;
  const q = needle.toLowerCase();
  const h = hay.toLowerCase();
  let i = 0;
  for (const ch of q) {
    const idx = h.indexOf(ch, i);
    if (idx === -1) return false;
    i = idx + 1;
  }
  return true;
}

export default function CommandPalette({ open, onClose, onEaCmd }) {
  const nav = useNavigate();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  const commands = useMemo(() => [
    // Navigation
    { id: "nav-home", group: "Navigate", label: "Overview", hint: "Home dashboard", icon: LayoutDashboard, action: () => nav("/") },
    { id: "nav-strategies", group: "Navigate", label: "Strategies", hint: "Manage the 35 strategies", icon: SlidersHorizontal, action: () => nav("/strategies") },
    { id: "nav-analytics", group: "Navigate", label: "Analytics", hint: "Trade analytics & heatmaps", icon: LineChart, action: () => nav("/analytics") },
    { id: "nav-strat-diag", group: "Navigate", label: "Strategy Diagnostics", hint: "Full lifecycle (Det · Gate · Exec · Perf · Health)", icon: Microscope, action: () => nav("/strategy-analytics") },
    { id: "nav-journal", group: "Navigate", label: "Journal", hint: "Trade journal", icon: BookOpen, action: () => nav("/journal") },
    { id: "nav-coach", group: "Navigate", label: "AI Coach", hint: "Talk to Claude about the EA", icon: MessageSquare, action: () => nav("/coach") },
    { id: "nav-whatif", group: "Navigate", label: "What-If", hint: "Counterfactual scenarios", icon: Sparkles, action: () => nav("/whatif") },
    { id: "nav-backtest", group: "Navigate", label: "Backtest", hint: "Run backtests", icon: FlaskConical, action: () => nav("/backtest") },
    { id: "nav-calendar", group: "Navigate", label: "Calendar", hint: "Economic news calendar", icon: CalendarDays, action: () => nav("/calendar") },
    { id: "nav-risk", group: "Navigate", label: "Risk Center", hint: "Budgets vs hard limits", icon: ShieldAlert, action: () => nav("/risk") },
    { id: "nav-calc", group: "Navigate", label: "Risk Calculator", hint: "Position sizing tool", icon: Calculator, action: () => nav("/risk-calc") },
    { id: "nav-settings", group: "Navigate", label: "Settings", hint: "EA parameters & gates", icon: Settings, action: () => nav("/settings") },
    { id: "nav-licenses", group: "Navigate", label: "Licenses", hint: "License management", icon: KeyRound, action: () => nav("/licenses") },

    // EA Commands (only if onEaCmd handler is provided)
    ...(onEaCmd ? [
      { id: "ea-pause", group: "EA Command", label: "Pause EA", hint: "Stops opening new positions", icon: Pause, danger: false, action: () => onEaCmd("pause") },
      { id: "ea-resume", group: "EA Command", label: "Resume EA", hint: "Re-enables new entries", icon: Play, action: () => onEaCmd("resume") },
      { id: "ea-close-all", group: "EA Command", label: "Close all positions", hint: "Sends CLOSE_ALL — irreversible", icon: AlertOctagon, danger: true, action: () => onEaCmd("close_all") },
      { id: "ea-reset-anti", group: "EA Command", label: "Reset anti-revenge", hint: "Clears consec-loss cooldown", icon: RotateCcw, action: () => onEaCmd("reset_anti_revenge") },
      { id: "ea-reset-daily", group: "EA Command", label: "Reset daily counters", hint: "Trades-today → 0, snapshot balance", icon: Calendar, action: () => onEaCmd("reset_daily") },
    ] : []),
  ], [nav, onEaCmd]);

  const filtered = useMemo(() => {
    if (!query.trim()) return commands;
    return commands.filter((c) =>
      fuzzyMatch(query, `${c.label} ${c.hint} ${c.group}`)
    );
  }, [commands, query]);

  // Group by category
  const grouped = useMemo(() => {
    const g = {};
    filtered.forEach((c) => {
      if (!g[c.group]) g[c.group] = [];
      g[c.group].push(c);
    });
    return g;
  }, [filtered]);

  // Reset state when opening
  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Clamp active index
  useEffect(() => {
    if (active >= filtered.length) setActive(Math.max(0, filtered.length - 1));
  }, [filtered.length, active]);

  // Scroll active item into view
  useEffect(() => {
    if (!open) return;
    const el = listRef.current?.querySelector(`[data-cmd-idx="${active}"]`);
    if (el) el.scrollIntoView({ block: "nearest" });
  }, [active, open]);

  const onKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(filtered.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const cmd = filtered[active];
      if (cmd) {
        cmd.action();
        onClose();
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    }
  };

  if (!open) return null;

  let runningIdx = -1;

  return (
    <div
      className="fixed inset-0 z-[80] bg-black/60 backdrop-blur-md flex items-start justify-center pt-[12vh] px-4 fade-in"
      onClick={onClose}
      data-testid="command-palette-overlay"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl rounded-2xl bg-card border border-border shadow-[0_30px_80px_-20px_hsl(var(--primary)/0.35)] overflow-hidden ring-1 ring-primary/20"
        data-testid="command-palette"
      >
        {/* Search input */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-border bg-secondary/30">
          <Search className="h-4 w-4 text-primary flex-shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActive(0); }}
            onKeyDown={onKeyDown}
            placeholder="Vai a una pagina o esegui un comando…"
            data-testid="command-palette-input"
            className="flex-1 bg-transparent border-0 outline-none text-sm font-mono placeholder:text-muted-foreground focus:ring-0"
          />
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded border border-border bg-background text-[10px] font-mono text-muted-foreground">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div
          ref={listRef}
          className="max-h-[60vh] overflow-y-auto py-2"
          data-testid="command-palette-list"
        >
          {filtered.length === 0 && (
            <div className="px-5 py-10 text-center text-sm text-muted-foreground">
              <div className="font-mono opacity-60">no match for &quot;{query}&quot;</div>
            </div>
          )}

          {Object.entries(grouped).map(([groupName, items]) => (
            <div key={groupName}>
              <div className="px-5 py-1.5 text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground/80">
                {groupName}
              </div>
              {items.map((cmd) => {
                runningIdx += 1;
                const idx = runningIdx;
                const isActive = idx === active;
                const Icon = cmd.icon;
                return (
                  <button
                    key={cmd.id}
                    data-cmd-idx={idx}
                    data-testid={`cmd-${cmd.id}`}
                    onMouseEnter={() => setActive(idx)}
                    onClick={() => { cmd.action(); onClose(); }}
                    className={cls(
                      "w-full text-left px-5 py-2.5 flex items-center gap-3 transition-colors",
                      isActive
                        ? "bg-primary/10 text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    <div className={cls(
                      "h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors",
                      commandIconClass(isActive, cmd.danger)
                    )}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-foreground truncate">{cmd.label}</div>
                      <div className="text-[11px] text-muted-foreground truncate">{cmd.hint}</div>
                    </div>
                    {isActive && (
                      <ArrowRight className="h-3.5 w-3.5 text-primary flex-shrink-0" />
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-5 py-2.5 border-t border-border bg-secondary/20 flex items-center justify-between text-[10px] font-mono text-muted-foreground">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-background border border-border">↑↓</kbd>
              <span>navigate</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-background border border-border">↵</kbd>
              <span>select</span>
            </span>
            <span className="flex items-center gap-1">
              <kbd className="px-1 py-0.5 rounded bg-background border border-border">esc</kbd>
              <span>close</span>
            </span>
          </div>
          <div className="flex items-center gap-1">
            <CommandIcon className="h-3 w-3" />
            <span>K to open anywhere</span>
          </div>
        </div>
      </div>
    </div>
  );
}
