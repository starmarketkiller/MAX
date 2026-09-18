import { useCallback, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, AlertTriangle, ArrowRight, Cpu, Gauge, Server, SlidersHorizontal } from "lucide-react";
import api from "@/lib/api";
import { useVisiblePolling } from "@/lib/useVisiblePolling";
import DataProvenanceBadge from "@/components/DataProvenanceBadge";
import { PositionsSection } from "@/pages/dashboard/HomePage";
import { Card, cls, fmtMoney, fmtPct, STRAT_LIST } from "@/pages/dashboard/shared";

const FAMILY = Object.fromEntries(STRAT_LIST.map(([id, , family]) => [id, family]));
const value = (item, formatter) => item == null ? "—" : formatter ? formatter(item) : item;

export function buildExecutionAttention(snapshot) {
  if (!snapshot) return [{ code: "snapshot", label: "Execution telemetry unavailable" }];
  const items = [];
  if (snapshot.ea?.state !== "LIVE") items.push({ code: "ea", label: snapshot.ea?.state === "STALE" ? "EA account data is stale" : "EA unavailable" });
  if (snapshot.ea?.paused === true) items.push({ code: "paused", label: "EA is paused" });
  if (snapshot.bridge?.state !== "LIVE") items.push({ code: "bridge", label: snapshot.bridge?.state === "STALE" ? "MT5 bridge is stale" : "MT5 bridge unavailable" });
  if (snapshot.risk?.state === "BLOCKED") items.push({ code: "risk", label: `Protection active: ${(snapshot.risk.protections || []).join(", ")}` });
  const dd = snapshot.risk?.drawdown_pct;
  const limit = snapshot.risk?.max_daily_dd_pct;
  if (dd != null && limit != null && limit > 0 && dd / limit >= .8) items.push({ code: "dd", label: `Drawdown near limit (${fmtPct(dd)} / ${fmtPct(limit)})` });
  if (snapshot.execution_quality?.state !== "READY") items.push({ code: "quality", label: snapshot.execution_quality?.message || "Execution quality unavailable" });
  if (snapshot.bridge?.failed_command_count > 0) items.push({ code: "commands", label: `${snapshot.bridge.failed_command_count} failed or expired bridge command(s)` });
  return items;
}

function StatusHeader({ snapshot }) {
  const cells = [
    ["EA", snapshot?.ea?.state, snapshot?.ea?.provenance],
    ["Bridge", snapshot?.bridge?.state, snapshot?.bridge?.provenance],
    ["Equity", value(snapshot?.ea?.equity, (v) => `$${fmtMoney(v)}`), snapshot?.ea?.provenance],
    ["Balance", value(snapshot?.ea?.balance, (v) => `$${fmtMoney(v)}`), snapshot?.ea?.provenance],
    ["Open", Array.isArray(snapshot?.positions?.items) ? snapshot.positions.items.length : "—", snapshot?.positions?.provenance],
    ["Risk", snapshot?.risk?.state || "UNAVAILABLE", snapshot?.risk?.provenance],
    ["Freshness", snapshot?.freshness?.age_seconds == null ? "—" : `${Math.round(snapshot.freshness.age_seconds)}s`, snapshot?.freshness?.state],
  ];
  return <Card className="p-4" testId="execution-status-header"><div className="grid grid-cols-2 gap-px overflow-hidden border border-border bg-border sm:grid-cols-4 xl:grid-cols-7">{cells.map(([label, output, source]) => <div key={label} className="min-w-0 bg-card p-3"><div className="flex items-center justify-between gap-2"><span className="eyebrow">{label}</span><DataProvenanceBadge source={source || "UNAVAILABLE"}/></div><div className="mt-2 truncate font-mono text-sm font-semibold">{output ?? "—"}</div></div>)}</div></Card>;
}

export function RiskSummary({ risk }) {
  const rows = [["Drawdown", value(risk?.drawdown_pct, fmtPct)], ["Daily limit", value(risk?.max_daily_dd_pct, fmtPct)], ["Floating P&L", value(risk?.floating_pnl, (v) => `$${fmtMoney(v)}`)], ["Exposure", value(risk?.exposure)], ["Margin level", value(risk?.margin_level, fmtPct)], ["Protection", risk?.protections?.length ? risk.protections.join(", ") : risk ? "CLEAR" : "—"]];
  return <Card className="p-4" testId="execution-risk"><div className="mb-3 flex items-center justify-between"><div><div className="eyebrow">Risk</div><h3 className="mt-1 font-semibold">Budget & protections</h3></div><DataProvenanceBadge source={risk?.provenance || "UNAVAILABLE"}/></div><dl className="divide-y divide-border">{rows.map(([label, output]) => <div key={label} className="flex justify-between gap-4 py-2 text-xs"><dt className="text-muted-foreground">{label}</dt><dd className="font-mono font-semibold">{output}</dd></div>)}</dl><Link to="/risk" className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary">Full risk controls <ArrowRight className="h-3 w-3"/></Link></Card>;
}

export function EnginesPanel({ engines, allocation }) {
  const rows = engines?.items || [];
  return <Card className="p-4" testId="execution-engines"><div className="mb-3 flex flex-wrap items-center justify-between gap-3"><div><div className="eyebrow">Execution engines</div><h3 className="mt-1 font-semibold">Runtime configuration</h3><p className="mt-1 text-[11px] text-muted-foreground">Executable engines, not canonical validated edges.</p></div><div className="flex gap-2"><DataProvenanceBadge source={engines?.provenance || "UNAVAILABLE"}/><Link to="/strategies" className="text-xs font-semibold text-primary">Manage</Link></div></div>{rows.length ? <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">{rows.map((engine) => <div key={engine.engine_id} className="border border-border bg-background/40 p-3"><div className="flex items-center justify-between gap-2"><span className="truncate font-mono text-xs font-semibold">{engine.engine_id}</span><span className={cls("text-[10px] font-semibold", engine.enabled ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground")}>{engine.configuration_status || (engine.enabled ? "ENABLED" : "DISABLED")}</span></div><div className="mt-2 flex justify-between text-[10px] text-muted-foreground"><span>{FAMILY[engine.engine_id] || "UNCLASSIFIED"}</span><span className="font-mono">risk {engine.risk_multiplier == null ? "—" : `×${engine.risk_multiplier}`}</span></div><div className="mt-1 text-[10px] text-muted-foreground">Runtime state: {engine.runtime_status || "UNAVAILABLE"} · Canonical strategy: {engine.canonical_strategy_status}</div></div>)}</div> : <div className="py-8 text-center text-xs text-muted-foreground">Engine configuration unavailable.</div>}<div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3"><div className="text-xs"><span className="font-semibold">Allocation</span><span className="ml-2 text-muted-foreground">{allocation?.config?.enabled === true ? "AUTO" : allocation?.config ? "MANUAL / OFF" : "UNAVAILABLE"}</span></div><Link to="/optimizer" className="inline-flex items-center gap-1 text-xs font-semibold text-primary"><SlidersHorizontal className="h-3 w-3"/>Allocation detail</Link></div></Card>;
}

export function ExecutionQuality({ quality, trades, onSelectTrade }) {
  return <Card className="p-4" testId="execution-quality"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="eyebrow">Execution quality / Signal → Fill</div><h3 className="mt-1 font-semibold">{quality?.message || "Signal-to-fill telemetry unavailable"}</h3></div><DataProvenanceBadge source={quality?.provenance || "UNAVAILABLE"} label={quality?.state || "UNAVAILABLE"}/></div><div className="mt-4 grid gap-3 md:grid-cols-2"><div className="border border-border p-3"><div className="text-xs font-semibold">Available</div><div className="mt-2 flex flex-wrap gap-1">{quality?.available?.map((field) => <span key={field} className="rounded border border-border px-2 py-1 font-mono text-[10px]">{field}</span>) || <span className="text-xs text-muted-foreground">—</span>}</div></div><div className="border border-border p-3"><div className="text-xs font-semibold">Missing for reliable join</div><div className="mt-2 flex flex-wrap gap-1">{quality?.missing?.map((field) => <span key={field} className="rounded border border-amber-500/30 px-2 py-1 font-mono text-[10px] text-amber-700 dark:text-amber-400">{field}</span>) || <span className="text-xs text-muted-foreground">—</span>}</div></div></div>{trades?.length ? <div className="mt-4 border-t border-border pt-3"><div className="mb-2 text-xs font-semibold">Recent actual trades</div><div className="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">{trades.slice(0, 6).map((trade) => <button key={trade.trade_uid || trade.ticket} onClick={() => onSelectTrade?.(trade)} className="flex justify-between gap-2 border border-border p-2 text-left text-xs hover:bg-secondary"><span className="truncate font-mono">{trade.strategy || trade.symbol || trade.ticket}</span><span className="font-mono">{trade.pnl == null ? "—" : `$${fmtMoney(trade.pnl)}`}</span></button>)}</div></div> : null}</Card>;
}

function SystemsPanel({ bridge }) {
  const worker = bridge?.worker;
  return <Card className="p-4" testId="execution-systems"><div className="flex items-start justify-between gap-3"><div><div className="eyebrow">MT5 / Bridge</div><h3 className="mt-1 font-semibold">{worker ? `Worker ${worker.online ? "online" : "offline"}` : "Worker unavailable"}</h3></div><DataProvenanceBadge source={bridge?.provenance || "UNAVAILABLE"}/></div><dl className="mt-3 divide-y divide-border text-xs"><div className="flex justify-between py-2"><dt className="text-muted-foreground">Host</dt><dd className="font-mono">{worker?.host_id || "—"}</dd></div><div className="flex justify-between py-2"><dt className="text-muted-foreground">Last heartbeat</dt><dd className="font-mono">{worker?.timestamp ? new Date(worker.timestamp).toLocaleString() : "—"}</dd></div><div className="flex justify-between py-2"><dt className="text-muted-foreground">Queue</dt><dd className="font-mono">{Array.isArray(bridge?.commands) ? `${bridge.commands.length} recent` : "—"}</dd></div></dl><Link to="/local-bridge" className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary">Bridge detail <ArrowRight className="h-3 w-3"/></Link></Card>;
}

export default function ExecutionPage({ onCmd, onSelectTrade, initialSnapshot = null, polling = true }) {
  const [snapshot, setSnapshot] = useState(initialSnapshot);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("live");
  const load = useCallback(async () => { try { const { data } = await api.get("/execution/snapshot"); setSnapshot(data); setError(""); } catch (err) { setError("Execution snapshot unavailable"); } }, []);
  useVisiblePolling(load, 10000, polling);
  const attention = useMemo(() => buildExecutionAttention(snapshot), [snapshot]);
  const show = (name) => cls(tab !== name && "hidden", "md:block");
  const status = snapshot ? { ...snapshot.ea, online: snapshot.ea?.state === "LIVE", positions: snapshot.positions?.items } : null;
  return <div className="space-y-4 fade-in" data-testid="execution-workspace">
    <div className="flex flex-wrap items-end justify-between gap-3"><div><div className="eyebrow">Operational workspace</div><h2 className="mt-1 text-xl font-semibold">Execution</h2></div><div className="flex gap-2"><DataProvenanceBadge source={snapshot?.ea?.provenance || "UNAVAILABLE"} label={`EA ${snapshot?.ea?.state || "UNAVAILABLE"}`}/><DataProvenanceBadge source={snapshot?.bridge?.provenance || "UNAVAILABLE"} label={`BRIDGE ${snapshot?.bridge?.state || "UNAVAILABLE"}`}/><DataProvenanceBadge source={snapshot?.risk?.provenance || "UNAVAILABLE"} label={`RISK ${snapshot?.risk?.state || "UNAVAILABLE"}`}/></div></div>
    {error ? <div className="border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-700 dark:text-rose-400">{error}</div> : null}
    <StatusHeader snapshot={snapshot}/>
    {attention.length ? <Card className="p-4" testId="execution-attention"><div className="eyebrow mb-2 flex items-center gap-1"><AlertTriangle className="h-3 w-3"/>Needs attention</div><div className="grid gap-2 sm:grid-cols-2">{attention.map((item) => <div key={item.code} className="border-l-2 border-amber-500 bg-amber-500/5 px-3 py-2 text-xs">{item.label}</div>)}</div></Card> : null}
    <div className="grid grid-cols-4 border border-border bg-card md:hidden">{["live","engines","risk","systems"].map((name) => <button key={name} data-testid={`execution-tab-${name}`} onClick={() => setTab(name)} className={cls("px-2 py-2 text-xs font-semibold capitalize", tab === name && "bg-secondary")}>{name}</button>)}</div>
    <div className={show("live")}><div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]"><PositionsSection status={status} onClosePosition={(position) => onCmd("close_position", { ticket: position.ticket }, true, { title: "Close this position?", body: `Ticket ${position.ticket} will be closed at market.` })} onPartialClose={(position) => onCmd("partial_close", { ticket: position.ticket, volume: position.lots == null ? null : +(position.lots * .5).toFixed(2) }, true, { title: "Partial close 50%?", body: `Ticket ${position.ticket}: close half the current volume.` })}/><RiskSummary risk={snapshot?.risk}/></div></div>
    <div className={show("engines")}><EnginesPanel engines={snapshot?.engines} allocation={snapshot?.allocation}/></div>
    <div className={show("risk")}><div className="md:hidden"><RiskSummary risk={snapshot?.risk}/></div></div>
    <div className={show("systems")}><div className="grid gap-4 lg:grid-cols-2"><SystemsPanel bridge={snapshot?.bridge}/><ExecutionQuality quality={snapshot?.execution_quality} trades={snapshot?.recent_trades?.items} onSelectTrade={onSelectTrade}/></div></div>
    <div className="flex flex-wrap gap-3 border-t border-border pt-3 text-xs"><Link to="/analytics" className="inline-flex items-center gap-1 text-primary"><Activity className="h-3 w-3"/>Execution analytics</Link><Link to="/strategy-analytics" className="inline-flex items-center gap-1 text-primary"><Gauge className="h-3 w-3"/>Runtime diagnostics</Link><Link to="/chain" className="inline-flex items-center gap-1 text-primary"><Cpu className="h-3 w-3"/>Strategy chain</Link><Link to="/local-bridge" className="inline-flex items-center gap-1 text-primary"><Server className="h-3 w-3"/>System detail</Link></div>
  </div>;
}
