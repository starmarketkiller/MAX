import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, ChevronRight, X } from "lucide-react";
import api from "@/lib/api";
import DataProvenanceBadge from "@/components/DataProvenanceBadge";
import LiveChartPage from "@/pages/LiveChartPage";
import { Card, cls } from "@/pages/dashboard/shared";

const STATE_FIELDS = [
  ["Regime", "regime"], ["Trend", "trend_state"], ["Volatility", "volatility_state"],
  ["Efficiency", "directional_efficiency"], ["Momentum", "momentum_state"],
  ["Structure", "structure_state"], ["Range position", "range_position"],
  ["Compression", "compression_state"], ["Location", "location_state"],
];
const fmt = (value) => value == null ? "—" : typeof value === "number" ? value.toFixed(3) : String(value).replaceAll("_", " ");
const stamp = (value) => value ? new Date(value).toLocaleString() : "—";

export function ParityIndicator({ value = "NONE", explanation }) {
  const tone = value === "FULL" ? "text-emerald-600 dark:text-emerald-400" : value === "PARTIAL" ? "text-amber-600 dark:text-amber-400" : "text-muted-foreground";
  return <div data-testid="market-parity" title={explanation} className="flex items-center gap-2 text-xs"><span className="text-muted-foreground">Research ↔ Live parity</span><strong className={cls("font-mono", tone)}>{value}</strong></div>;
}

export function MarketStatePanel({ snapshot, domain = "RESEARCH" }) {
  const provenance = snapshot?.provenance?.type || (domain === "RESEARCH" ? "RESEARCH" : "UNAVAILABLE");
  return <Card className="p-4" testId={`market-state-${domain.toLowerCase()}`}>
    <div className="mb-3 flex items-start justify-between gap-3"><div><div className="eyebrow">Market State</div><div className="mt-1 text-xs text-muted-foreground">{domain} · {stamp(snapshot?.timestamp)}</div></div><DataProvenanceBadge source={snapshot ? provenance : "UNAVAILABLE"}/></div>
    <dl className="divide-y divide-border">{STATE_FIELDS.map(([label, key]) => <div key={key} className="flex items-center justify-between gap-4 py-2"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="text-right font-mono text-xs font-semibold uppercase">{fmt(snapshot?.[key])}</dd></div>)}</dl>
    {snapshot?.limitations?.length ? <div className="mt-3 border-t border-border pt-3 text-[11px] leading-relaxed text-muted-foreground">{snapshot.limitations[0]}</div> : null}
  </Card>;
}

function EventInspector({ event, onClose }) {
  if (!event) return null;
  const rows = [["Detector", event.detector_version], ["Direction", event.direction], ["Magnitude", event.magnitude], ["Observation", event.observation_point], ["Source", event.source_dataset], ["Market State", event.state_snapshot_id], ["Research entity", event.linked_research_entity_id]];
  return <div className="fixed inset-0 z-50 bg-black/35" onClick={onClose}><aside role="dialog" aria-label="Market event inspector" className="absolute bottom-0 right-0 w-full max-h-[82vh] overflow-auto border border-border bg-card p-5 shadow-2xl md:bottom-auto md:top-0 md:h-full md:max-w-md" onClick={(e) => e.stopPropagation()}><button onClick={onClose} className="absolute right-4 top-4 text-muted-foreground"><X className="h-4 w-4"/></button><div className="eyebrow">Event inspector</div><h3 className="mt-2 text-lg font-semibold">{event.family}</h3><p className="mt-1 font-mono text-xs text-muted-foreground">{stamp(event.timestamp)}</p><DataProvenanceBadge source="RESEARCH" className="mt-3"/><dl className="mt-5 divide-y divide-border">{rows.map(([label,value]) => <div key={label} className="grid grid-cols-[7rem_1fr] gap-3 py-2 text-xs"><dt className="text-muted-foreground">{label}</dt><dd className="break-all font-mono">{fmt(value)}</dd></div>)}</dl></aside></div>;
}

export default function MarketPage() {
  const [latest, setLatest] = useState(null);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");
  const [family, setFamily] = useState("");
  const [direction, setDirection] = useState("");
  const [range, setRange] = useState("ALL");
  const [selected, setSelected] = useState(null);
  const [mobileTab, setMobileTab] = useState("chart");

  const load = useCallback(async () => {
    setError("");
    const params = new URLSearchParams({ symbol: "XAUUSD", timeframe: "H4", limit: "250" });
    if (family) params.set("event_family", family);
    if (direction) params.set("direction", direction);
    if (range !== "ALL") params.set("from", new Date(Date.now() - Number(range) * 86400000).toISOString());
    const [stateResult, eventResult] = await Promise.allSettled([api.get("/market/state/latest?symbol=XAUUSD&timeframe=H4"), api.get(`/market/events?${params}`)]);
    if (stateResult.status === "fulfilled") setLatest(stateResult.value.data);
    else setLatest(null);
    if (eventResult.status === "fulfilled") setEvents(eventResult.value.data?.items || []);
    else setEvents([]);
    if (stateResult.status === "rejected" || eventResult.status === "rejected") setError("Market history is partially unavailable.");
  }, [family, direction, range]);
  useEffect(() => { load(); }, [load]);
  const families = useMemo(() => [...new Set(events.map((event) => event.family))].sort(), [events]);
  const show = (tab) => cls(mobileTab !== tab && "hidden", "md:block");

  return <div className="space-y-4 fade-in" data-testid="market-workspace">
    <div className="flex flex-wrap items-end justify-between gap-3"><div><div className="eyebrow">Canonical Market workspace</div><h2 className="mt-1 text-xl font-semibold">XAUUSD · H4</h2><div className="mt-2 flex flex-wrap gap-2"><DataProvenanceBadge source="RESEARCH"/><DataProvenanceBadge source={latest?.operational?.provenance?.type || "UNAVAILABLE"} label="OPERATIONAL"/></div></div><ParityIndicator value={latest?.semantic_parity || "NONE"} explanation={latest?.parity_explanation}/></div>
    {error ? <div className="flex items-center gap-2 border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400"><AlertTriangle className="h-4 w-4"/>{error}</div> : null}
    <div className="grid grid-cols-3 border border-border bg-card md:hidden">{["chart","state","events"].map((tab) => <button key={tab} onClick={() => setMobileTab(tab)} className={cls("px-3 py-2 text-xs font-semibold capitalize", mobileTab === tab && "bg-secondary")}>{tab}</button>)}</div>
    <div className="grid gap-4 md:grid-cols-[minmax(0,2fr)_minmax(260px,1fr)]"><div className={cls(show("chart"), "overflow-hidden border border-border bg-card")}><LiveChartPage embedded/></div><div className={show("state")}><MarketStatePanel snapshot={latest?.research}/><div className="mt-3"><MarketStatePanel snapshot={latest?.operational} domain="OPERATIONAL"/></div></div></div>
    <Card className={cls(show("events"), "p-4")} testId="market-event-timeline"><div className="flex flex-wrap items-center justify-between gap-3"><div><div className="eyebrow">Event timeline</div><p className="mt-1 text-xs text-muted-foreground">Historical Research events; no live stream.</p></div><div className="flex flex-wrap gap-2"><select value={family} onChange={(e) => setFamily(e.target.value)} className="h-8 rounded border border-border bg-background px-2 text-xs"><option value="">All families</option>{families.map((item) => <option key={item}>{item}</option>)}</select><select value={direction} onChange={(e) => setDirection(e.target.value)} className="h-8 rounded border border-border bg-background px-2 text-xs"><option value="">All directions</option><option value="1">Bullish</option><option value="-1">Bearish</option><option value="0">Neutral</option></select><select value={range} onChange={(e) => setRange(e.target.value)} className="h-8 rounded border border-border bg-background px-2 text-xs"><option value="ALL">All time</option><option value="30">30 days</option><option value="7">7 days</option></select></div></div><div className="mt-3 divide-y divide-border">{events.length ? events.map((event) => <button key={event.event_id} onClick={() => setSelected(event)} className="grid w-full grid-cols-[5rem_1fr_auto] items-center gap-3 py-3 text-left hover:bg-secondary/50"><span className="font-mono text-[11px] text-muted-foreground">{new Date(event.timestamp).toLocaleDateString()}</span><span><span className="block text-xs font-semibold">{event.family}</span><span className="font-mono text-[10px] text-muted-foreground">dir {fmt(event.direction)} · mag {fmt(event.magnitude)}</span></span><ChevronRight className="h-4 w-4 text-muted-foreground"/></button>) : <div className="flex items-center justify-center gap-2 py-10 text-xs text-muted-foreground"><Activity className="h-4 w-4"/>No indexed market events for this filter.</div>}</div></Card>
    <EventInspector event={selected} onClose={() => setSelected(null)}/>
  </div>;
}
