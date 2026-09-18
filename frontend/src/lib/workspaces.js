import {
  BookOpen, CandlestickChart, FlaskConical, LayoutDashboard, Radio,
} from "lucide-react";

export const PRIMARY_WORKSPACES = Object.freeze([
  {
    id: "overview", label: "Overview", to: "/", icon: LayoutDashboard,
    summary: "NEXUS operating state across market, research, execution and risk.",
    routes: ["/"],
    tabs: [{ label: "Overview", to: "/" }],
  },
  {
    id: "market", label: "Market", to: "/market", icon: CandlestickChart,
    summary: "Observed price action, operational context and scheduled events.",
    routes: ["/market", "/chart", "/calendar"],
    tabs: [{ label: "Workspace", to: "/market" }, { label: "Live chart", to: "/chart" }, { label: "Calendar", to: "/calendar" }],
  },
  {
    id: "research", label: "Research", to: "/research", icon: FlaskConical,
    summary: "Hypotheses, experiments, evidence and validation tools.",
    routes: ["/research", "/backtest", "/whatif", "/strategy-analytics"],
    tabs: [{ label: "Hypotheses", to: "/research" }, { label: "Backtests", to: "/backtest" }, { label: "What-if", to: "/whatif" }, { label: "Diagnostics", to: "/strategy-analytics" }],
  },
  {
    id: "execution", label: "Execution", to: "/execution", icon: Radio,
    summary: "EA, MT5 bridge, positions, risk and signal-to-fill operations.",
    routes: ["/execution", "/strategies", "/optimizer", "/risk", "/local-bridge", "/chain", "/analytics"],
    tabs: [{ label: "Workspace", to: "/execution" }, { label: "Engines", to: "/strategies" }, { label: "Allocation", to: "/optimizer" }, { label: "Risk", to: "/risk" }, { label: "MT5", to: "/local-bridge" }, { label: "Chain", to: "/chain" }, { label: "Analytics", to: "/analytics" }],
  },
  {
    id: "library", label: "Library", to: "/library", icon: BookOpen,
    summary: "Research knowledge, evidence artifacts and operating journal.",
    routes: ["/library", "/knowledge", "/journal"],
    tabs: [{ label: "Workspace", to: "/library" }, { label: "Knowledge", to: "/knowledge" }, { label: "Journal", to: "/journal" }],
  },
]);

export const UTILITY_ROUTES = Object.freeze([
  { label: "Calculator", to: "/risk-calc" },
  { label: "Settings", to: "/settings" },
  { label: "Licenses / Admin", to: "/licenses" },
  { label: "System status", to: "/system" },
]);

export const LEGACY_ROUTES = Object.freeze([
  "/chart", "/calendar", "/backtest", "/whatif", "/strategy-analytics",
  "/strategies", "/optimizer", "/risk", "/local-bridge", "/chain",
  "/analytics", "/knowledge", "/journal", "/risk-calc", "/settings",
  "/licenses", "/coach",
]);

export function workspaceForPath(pathname) {
  return PRIMARY_WORKSPACES.find((workspace) => workspace.routes.includes(pathname)) || null;
}

export function workspaceForSection(section) {
  const path = section === "home" ? "/" : `/${section}`;
  return workspaceForPath(path);
}
