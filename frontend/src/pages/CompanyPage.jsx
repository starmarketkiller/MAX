import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowRight, Boxes, GitBranch, X } from "lucide-react";
import api from "@/lib/api";
import DataProvenanceBadge from "@/components/DataProvenanceBadge";

const tone = (status) => status === "ACTIVE" || status === "READY" || status === "PASSED"
  ? "text-emerald-400" : status === "BLOCKED" || status === "FAILED" ? "text-rose-400" : "text-amber-400";
const dash = (value) => value === null || value === undefined || value === "" ? "—" : value;

export function DepartmentCard({ department, onOpen }) {
  return <button onClick={() => onOpen(department.id)} className="w-full border border-border bg-card p-4 text-left hover:border-primary/40 transition-colors">
    <div className="flex items-start justify-between gap-3"><div><div className="font-mono text-xs text-muted-foreground">{department.id}</div><div className="mt-1 font-semibold">{department.name}</div></div><span className={`font-mono text-xs ${tone(department.status)}`}>{department.status}</span></div>
    <p className="mt-3 text-xs text-muted-foreground">{department.purpose}</p>
    {department.skeleton ? <div className="mt-3 text-xs text-muted-foreground">No operational pipeline yet</div> : <div className="mt-3 flex gap-4 font-mono text-xs"><span>{department.work_item_count} work</span><span>{department.artifact_count} artifacts</span>{department.blocked_count > 0 && <span className="text-rose-400">{department.blocked_count} blocked</span>}</div>}
  </button>;
}

export function DepartmentInspector({ department, onClose }) {
  if (!department) return null;
  return <aside aria-label="Department inspector" className="fixed inset-0 z-50 overflow-y-auto bg-background p-5 md:inset-y-0 md:left-auto md:w-[520px] md:border-l md:border-border">
    <div className="flex justify-between"><div><div className="font-mono text-xs text-muted-foreground">DEPARTMENT</div><h2 className="text-xl font-semibold">{department.name}</h2></div><button aria-label="Close department inspector" onClick={onClose}><X className="h-5 w-5" /></button></div>
    <div className="mt-4 flex gap-2"><span className={`font-mono text-xs ${tone(department.status)}`}>{department.status}</span><DataProvenanceBadge source="DERIVED" /></div>
    {department.skeleton && <div className="mt-5 border border-amber-500/30 bg-amber-500/5 p-3 text-sm">SKELETON · no operational pipeline yet</div>}
    <section className="mt-6"><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Purpose</h3><p className="mt-2 text-sm">{department.purpose}</p></section>
    <section className="mt-6 grid gap-4 sm:grid-cols-2"><Contract title="Accepted inputs" values={department.accepted_inputs}/><Contract title="Emitted outputs" values={department.emitted_outputs}/><Contract title="Dependencies" values={department.required_dependencies}/><Contract title="Capabilities" values={department.capabilities}/></section>
    <section className="mt-6"><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Active work / blockers</h3><div className="mt-2 space-y-2">{department.active_work_items?.length ? department.active_work_items.slice(0,12).map(item => <div key={item.id} className="border border-border p-3"><div className="flex justify-between gap-2"><span className="font-mono text-xs">{item.source_entity_id}</span><span className={`font-mono text-[10px] ${tone(item.normalized_status)}`}>{item.normalized_status}</span></div><div className="mt-1 text-xs text-muted-foreground">Raw: {dash(item.raw_status)}</div></div>) : <div className="text-sm text-muted-foreground">No canonical work items available.</div>}</div></section>
    <section className="mt-6"><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Recent artifacts</h3><div className="mt-2 space-y-2">{department.recent_artifacts?.length ? department.recent_artifacts.map(item => <div key={item.id} className="border border-border p-3"><div className="text-sm">{item.name}</div><div className="mt-1 break-all font-mono text-[10px] text-muted-foreground">{item.source_path}</div></div>) : <div className="text-sm text-muted-foreground">No canonical artifacts available.</div>}</div></section>
    {department.datasets?.length ? <section className="mt-6"><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Datasets</h3>{department.datasets.map(item => <div key={item.id} className="mt-2 border border-border p-3"><div className="font-mono text-xs">{item.id}</div><div className="mt-1 text-xs text-muted-foreground">{dash(item.source)} · {dash(item.period)} · rows {dash(item.row_count)}</div></div>)}</section> : null}
    {department.operational_state ? <section className="mt-6"><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Operational projection</h3><pre className="mt-2 overflow-x-auto whitespace-pre-wrap border border-border p-3 font-mono text-[10px] text-muted-foreground">{JSON.stringify(department.operational_state, null, 2)}</pre></section> : null}
  </aside>;
}

function Contract({ title, values }) { return <div><h3 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{title}</h3><div className="mt-2 space-y-1">{values?.length ? values.map(v => <div key={v} className="font-mono text-xs">{v}</div>) : <div className="text-xs text-muted-foreground">UNAVAILABLE</div>}</div></div>; }

export default function CompanyPage() {
  const [overview, setOverview] = useState(null), [selected, setSelected] = useState(null), [error, setError] = useState(null);
  useEffect(() => { api.get("/company/overview").then(r => setOverview(r.data)).catch(() => setError("Company read model unavailable")); }, []);
  const blockers = useMemo(() => overview?.blockers || [], [overview]);
  const openDepartment = async (id) => { try { setSelected((await api.get(`/company/departments/${id}`)).data); } catch { setError("Department detail unavailable"); } };
  if (error && !overview) return <div className="border border-rose-500/30 p-6"><DataProvenanceBadge source="UNAVAILABLE"/><p className="mt-3 text-sm">{error}</p></div>;
  if (!overview) return <div className="p-6 font-mono text-sm text-muted-foreground">Loading company control plane…</div>;
  return <div className="space-y-5" data-testid="company-control-plane">
    <header className="flex flex-wrap items-end justify-between gap-3 border-b border-border pb-4"><div><div className="font-mono text-xs text-muted-foreground">NEXUS COMPANY</div><h1 className="text-2xl font-semibold">Company Control Plane</h1><p className="mt-1 text-sm text-muted-foreground">Departments, canonical work, gates and dependencies.</p></div><DataProvenanceBadge source="DERIVED" /></header>
    {overview.warnings?.length > 0 && <div className="flex gap-2 border border-amber-500/30 bg-amber-500/5 p-3 text-sm"><AlertTriangle className="h-4 w-4"/>Degraded source coverage: {overview.warnings.length} artifact warning(s).</div>}
    <section><div className="mb-2 flex items-center gap-2"><Boxes className="h-4 w-4"/><h2 className="text-sm font-semibold">Department status</h2></div><div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{overview.departments.map(d => <DepartmentCard key={d.id} department={d} onOpen={openDepartment}/>)}</div></section>
    <div className="grid gap-4 xl:grid-cols-2"><Queue title="Blocked work" items={blockers}/><Queue title="Pending gates" items={overview.pending_gates}/></div>
    <div className="grid gap-4 xl:grid-cols-2"><section className="border border-border bg-card p-4"><h2 className="text-sm font-semibold">Recent artifacts</h2><div className="mt-3 space-y-2">{overview.recent_artifacts?.map(a => <div key={a.id} className="flex items-center justify-between gap-3 border-t border-border pt-2"><div className="min-w-0"><div className="truncate text-sm">{a.name}</div><div className="truncate font-mono text-[10px] text-muted-foreground">{a.source_path}</div></div><DataProvenanceBadge source="RESEARCH" /></div>)}</div></section><section className="border border-border bg-card p-4"><div className="flex items-center gap-2"><GitBranch className="h-4 w-4"/><h2 className="text-sm font-semibold">Dependencies</h2></div><div className="mt-3 font-mono text-sm">{overview.dependencies?.length ?? "—"} explicit relations</div><p className="mt-2 text-xs text-muted-foreground">Only artifact-backed work-item → gate relations are included.</p></section></div>
    <DepartmentInspector department={selected} onClose={() => setSelected(null)}/>
  </div>;
}

function Queue({ title, items=[] }) { return <section className="border border-border bg-card p-4"><h2 className="text-sm font-semibold">{title}</h2><div className="mt-3 space-y-2">{items.length ? items.slice(0,10).map(item => <div key={item.id} className="flex items-center justify-between gap-3 border-t border-border pt-2"><div className="min-w-0"><div className="truncate font-mono text-xs">{item.source_entity_id || item.work_item_id}</div><div className="truncate text-xs text-muted-foreground">{item.name}</div></div><span className={`font-mono text-[10px] ${tone(item.normalized_status)}`}>{item.normalized_status}</span></div>) : <div className="text-sm text-muted-foreground">No canonical items.</div>}</div></section>; }
