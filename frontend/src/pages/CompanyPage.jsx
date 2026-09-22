import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Boxes, GitBranch, X } from "lucide-react";
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
  const [strategy, setStrategy] = useState(null);
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
    {department.id === "QUANT_RESEARCH" ? <StrategyPipeline strategies={department.strategies || []} onOpen={setStrategy} /> : null}
    {strategy ? <StrategyInspector strategy={strategy} onClose={() => setStrategy(null)} /> : null}
  </aside>;
}

export function StrategyPipeline({ strategies, onOpen }) {
  return <section className="mt-6" data-testid="strategy-pipeline">
    <div className="flex items-end justify-between gap-3"><div><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Strategy pipeline</h3><p className="mt-1 text-xs text-muted-foreground">Code status and evidence status are independent.</p></div><span className="font-mono text-xs">{strategies.length}</span></div>
    <div className="mt-3 overflow-x-auto"><table className="w-full min-w-[720px] border-collapse text-left text-xs"><thead className="text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="border-b border-border py-2 pr-3">Strategy</th><th className="border-b border-border py-2 pr-3">Lifecycle</th><th className="border-b border-border py-2 pr-3">Evidence</th><th className="border-b border-border py-2 pr-3">Stage</th><th className="border-b border-border py-2 pr-3">Blocker</th><th className="border-b border-border py-2">Meta-filter</th></tr></thead>
      <tbody>{strategies.map(item => <tr key={item.strategy_id} className="border-b border-border/60 align-top"><td className="py-3 pr-3"><button className="font-mono text-left text-primary hover:underline" onClick={() => onOpen(item)}>{item.strategy_id}</button>{item.governance_status && <div className="mt-1 font-mono text-[10px] text-rose-400">{item.governance_status}</div>}</td><td className="py-3 pr-3 font-mono">{dash(item.lifecycle_class)}</td><td className={`py-3 pr-3 font-mono ${item.evidence_is_refuted ? "text-rose-400" : ""}`}>{dash(item.evidence_verdict)}</td><td className="py-3 pr-3 font-mono">{dash(item.current_stage)}</td><td className="max-w-[210px] py-3 pr-3 text-muted-foreground">{dash(item.blockers?.[0])}</td><td className="py-3 font-mono">{dash(item.meta_filter_research_readiness)}</td></tr>)}</tbody></table></div>
  </section>;
}

export function StrategyInspector({ strategy, onClose }) {
  return <div aria-label="Strategy inspector" className="fixed inset-0 z-[60] overflow-y-auto bg-background p-5 md:inset-y-0 md:left-auto md:w-[560px] md:border-l md:border-border">
    <div className="flex justify-between gap-3"><div><div className="font-mono text-xs text-muted-foreground">STRATEGY PIPELINE</div><h2 className="break-all text-lg font-semibold">{strategy.strategy_id}</h2></div><button aria-label="Close strategy inspector" onClick={onClose}><X className="h-5 w-5" /></button></div>
    <div className="mt-4 flex flex-wrap gap-2"><DataProvenanceBadge source="RESEARCH" />{strategy.governance_status && <span className="border border-rose-500/30 px-2 py-0.5 font-mono text-[10px] text-rose-400">{strategy.governance_status}</span>}</div>
    <section className="mt-6 grid gap-3 sm:grid-cols-2"><Fact label="Code registry status" value={strategy.code_registry_status}/><Fact label="Evidence verdict" value={strategy.evidence_verdict}/><Fact label="Lifecycle" value={strategy.lifecycle_class}/><Fact label="Current stage" value={strategy.current_stage}/><Fact label="Blocked stage" value={strategy.blocked_stage}/><Fact label="Next required stage" value={strategy.next_required_stage}/><Fact label="Structural eligibility" value={strategy.meta_filter_structural_eligibility}/><Fact label="Research readiness" value={strategy.meta_filter_research_readiness}/></section>
    <section className="mt-6"><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Evidence ladder</h3><div className="mt-2 space-y-2">{Object.entries(strategy.evidence_ladder || {}).map(([key, value]) => <div key={key} className="border border-border p-3"><div className="flex justify-between gap-3"><span className="font-mono text-xs">{key}</span><span className={`font-mono text-[10px] ${tone(value?.status)}`}>{dash(value?.status)}</span></div>{value?.detail && <p className="mt-2 text-xs text-muted-foreground">{value.detail}</p>}</div>)}</div></section>
    <LifecycleFieldSemantics fields={strategy.field_semantics || []} />
    <section className="mt-6"><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Blockers / next evidence</h3>{strategy.blockers?.length ? strategy.blockers.map((item, index) => <p key={index} className="mt-2 border border-border p-3 text-xs text-muted-foreground">{item}</p>) : <p className="mt-2 text-xs text-muted-foreground">UNAVAILABLE</p>}</section>
    <section className="mt-6"><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Provenance</h3><div className="mt-2 space-y-1">{strategy.provenance?.sources?.map(source => <div key={source} className="break-all font-mono text-[10px] text-muted-foreground">{source}</div>)}</div></section>
    <p className="mt-6 border-t border-border pt-3 text-[11px] text-muted-foreground">Code ACTIVE does not imply evidence validated, live capital active, or deployability.</p>
  </div>;
}

export function LifecycleFieldSemantics({ fields }) {
  return <section className="mt-6" data-testid="lifecycle-field-semantics"><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Lifecycle field semantics</h3><p className="mt-1 text-[11px] text-muted-foreground">NOT_EXTRACTED ≠ VERIFIED_ABSENCE</p>
    {fields.length ? <div className="mt-3 overflow-x-auto"><table className="w-full min-w-[520px] border-collapse text-left text-xs"><thead className="text-[10px] uppercase tracking-wider text-muted-foreground"><tr><th className="border-b border-border py-2 pr-3">Field</th><th className="border-b border-border py-2 pr-3">Knowledge</th><th className="border-b border-border py-2">Requirement role</th></tr></thead><tbody>{fields.map(item => <tr key={item.field} className="border-b border-border/60 align-top"><td className="py-3 pr-3 font-mono">{item.field}</td><td className="py-3 pr-3 font-mono">{item.field_knowledge === "NOT_EXTRACTED" ? "UNVERIFIED / NOT EXTRACTED" : dash(item.field_knowledge)}</td><td className="py-3 font-mono">{dash(item.requirement_role)}{item.note && <details className="mt-2 font-sans text-[11px] text-muted-foreground"><summary className="cursor-pointer">Note</summary><p className="mt-1">{item.note}</p></details>}</td></tr>)}</tbody></table></div> : <div className="mt-2 text-xs text-muted-foreground">UNAVAILABLE</div>}
  </section>;
}

function Fact({ label, value }) { return <div className="border border-border p-3"><div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div><div className="mt-1 break-words font-mono text-xs">{dash(value)}</div></div>; }

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
