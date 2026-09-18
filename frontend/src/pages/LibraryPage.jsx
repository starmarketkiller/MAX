import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BookOpen, ChevronRight, Filter, Search, X } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import DataProvenanceBadge from "@/components/DataProvenanceBadge";
import { Card } from "@/pages/dashboard/shared";

const show = (value) => value === null || value === undefined || value === "" ? "—" : String(value);
const FILTER_FIELDS = ["type", "evidence_grade", "phase", "status"];

export function filterLibraryEntities(items, relations, filters) {
  const query = (filters.query || "").trim().toLowerCase();
  return items.filter((item) => {
    if (FILTER_FIELDS.some((field) => filters[field] && String(item[field] || "").toLowerCase() !== filters[field].toLowerCase())) return false;
    if (!query) return true;
    const relationText = relations.filter((r) => r.source_id === item.id || r.target_id === item.id).map((r) => r.type).join(" ");
    return `${item.id} ${item.title} ${item.type} ${item.status} ${relationText}`.toLowerCase().includes(query);
  });
}

function SelectFilter({ label, field, value, options, onChange }) {
  return <label className="block"><span className="mb-1 block font-mono text-[9px] uppercase tracking-widest text-muted-foreground">{label}</span><select aria-label={label} value={value} onChange={(event) => onChange(field, event.target.value)} className="h-9 w-full rounded-md border border-border bg-background px-2 text-xs"><option value="">All</option>{options.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>;
}

function EntityRow({ item, onSelect }) {
  const isAudit = item.type === "EvidenceAudit";
  return <button type="button" onClick={() => onSelect(item.id)} className="grid w-full min-w-0 grid-cols-[minmax(0,1fr)_auto] gap-3 border-b border-border px-3 py-3 text-left last:border-0 hover:bg-secondary/50" data-testid={`library-entity-${item.id}`}>
    <span className="min-w-0"><span className="flex flex-wrap items-center gap-2"><span className="truncate font-mono text-[11px] font-semibold">{item.id}</span>{item.type === "Evidence" ? <span className="rounded border border-violet-500/30 px-1.5 py-0.5 font-mono text-[9px] text-violet-700 dark:text-violet-300">PRIMARY</span> : null}{isAudit ? <span className="rounded border border-amber-500/30 px-1.5 py-0.5 font-mono text-[9px] text-amber-700 dark:text-amber-300">AUDIT</span> : null}</span><span className="mt-1 block truncate text-xs text-muted-foreground">{show(item.title)} · {show(item.type)}</span></span>
    <span className="flex items-center gap-2"><span className="text-right font-mono text-[10px]"><span className="block">{show(item.status)}</span><span className="text-muted-foreground">{show(item.evidence_grade)} · {show(item.phase)}</span></span><ChevronRight className="h-4 w-4 text-muted-foreground" /></span>
  </button>;
}

export function ExplainPath({ explain }) {
  if (!explain) return <div className="py-8 text-center text-sm text-muted-foreground">Explain Path unavailable.</div>;
  const incoming = (id) => explain.typed_edges?.filter((edge) => edge.source_id === id || edge.target_id === id) || [];
  return <div className="space-y-0" data-testid="explain-path">{(explain.path_nodes || []).map((node, index) => <div key={node.id} className="relative pl-7">
    {index ? <div className="absolute left-[9px] top-0 h-full border-l border-border" /> : null}
    <span className="absolute left-1 top-4 h-3 w-3 rounded-full border border-sky-500/50 bg-background" />
    <div className="mb-3 rounded-md border border-border bg-secondary/25 p-3"><div className="flex flex-wrap justify-between gap-2"><span className="break-all font-mono text-[11px] font-semibold">{node.id}</span><span className="font-mono text-[9px] text-muted-foreground">{show(node.phase)}</span></div><div className="mt-1 text-xs">{show(node.title)}</div><div className="mt-2 flex flex-wrap gap-1">{incoming(node.id).map((edge) => <span key={`${edge.id}-${node.id}`} className="rounded border border-border px-1.5 py-0.5 font-mono text-[9px]">{edge.type}</span>)}</div>{node.limitations?.[0] ? <p className="mt-2 text-[11px] text-amber-700 dark:text-amber-300">{node.limitations[0]}</p> : null}<div className="mt-2 break-all font-mono text-[9px] text-muted-foreground">{show(node.provenance?.source_artifact)}</div></div>
  </div>)}{explain.current_decision ? <div className="ml-7 rounded-md border border-violet-500/25 bg-violet-500/10 p-3"><div className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">Current decision · not linked by an inferred edge</div><div className="mt-1 font-mono text-sm">{show(explain.current_decision.status)} · {show(explain.current_decision.evidence_grade)}</div></div> : null}</div>;
}

function Inspector({ detail, explain, onClose }) {
  if (!detail) return null;
  const attrs = detail.attributes || {};
  const primary = attrs.evidence_classification;
  return <div className="fixed inset-0 z-50 bg-black/50 lg:inset-y-0 lg:left-auto lg:w-[min(620px,48vw)]" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><aside role="dialog" aria-modal="true" aria-label="Entity inspector" className="ml-auto h-full w-[min(100%,620px)] overflow-y-auto border-l border-border bg-card p-4 shadow-2xl" data-testid="library-inspector"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">{detail.type} · {show(detail.phase)}</div><h2 className="mt-1 break-all text-lg font-semibold">{detail.id}</h2><p className="mt-1 text-sm text-muted-foreground">{show(detail.title)}</p></div><button aria-label="Close inspector" onClick={onClose} className="rounded-md border border-border p-2 hover:bg-secondary"><X className="h-4 w-4" /></button></div>
    <div className="mt-4 flex flex-wrap gap-2"><DataProvenanceBadge source="RESEARCH" /><span className="rounded border border-border px-2 py-1 font-mono text-[10px]">{show(detail.status)}</span><span className="rounded border border-border px-2 py-1 font-mono text-[10px]">{show(detail.evidence_grade)}</span>{attrs.promoted_to_e3 === false ? <span className="rounded border border-amber-500/30 px-2 py-1 font-mono text-[10px] text-amber-700 dark:text-amber-300">NOT PROMOTED</span> : null}</div>
    <div className="mt-5 grid gap-2 sm:grid-cols-2">{[["Source", detail.provenance?.source_artifact], ["Commit", detail.provenance?.commit], ["SHA", detail.provenance?.canonical_sha256], ["Schema", detail.provenance?.schema_version]].map(([label, value]) => <div key={label} className="min-w-0 rounded border border-border bg-secondary/25 p-2"><div className="font-mono text-[9px] uppercase text-muted-foreground">{label}</div><div className="mt-1 break-all font-mono text-[10px]">{show(value)}</div></div>)}</div>
    {primary ? <div className="mt-4 rounded-md border border-border p-3 text-xs"><div className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">Evidence classification</div><p className="mt-2">{show(primary.conclusion)} · {show(primary.evidence_grade)} · {show(primary.validation_integrity)}</p>{primary.grade_cap_reason ? <p className="mt-2 text-muted-foreground">{primary.grade_cap_reason}</p> : null}</div> : null}
    {attrs.sample?.dependence_flag ? <div className="mt-3 rounded-md border border-amber-500/25 bg-amber-500/10 p-3 text-xs">Dependence: <strong>{attrs.sample.dependence_flag}</strong> · Directional baseline: {attrs.baseline?.direction_aware ? "v3 / audit only" : "No"}</div> : null}
    {attrs.is_edge === false ? <div className="mt-3 rounded-md border border-amber-500/25 bg-amber-500/10 p-3 font-mono text-xs">is_edge=false · is_validated={String(attrs.is_validated)}</div> : null}
    <div className="mt-5"><div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Relations</div><div className="space-y-1">{[...(detail.relations_in || []), ...(detail.relations_out || [])].map((r) => <div key={r.id} className="break-all rounded border border-border px-2 py-1.5 font-mono text-[10px]">{r.source_id} — {r.type} → {r.target_id}</div>)}{!(detail.relations_in?.length || detail.relations_out?.length) ? <div className="text-xs text-muted-foreground">No explicit relation in the Phase 6.6 model.</div> : null}</div></div>
    <div className="mt-6 border-t border-border pt-4"><h3 className="mb-3 text-sm font-semibold">Explain Path</h3><ExplainPath explain={explain} /></div>
  </aside></div>;
}

export default function LibraryPage() {
  const [entities, setEntities] = useState([]); const [relations, setRelations] = useState([]); const [warnings, setWarnings] = useState([]);
  const [filters, setFilters] = useState({ query: "", type: "", evidence_grade: "", phase: "", status: "" });
  const [filterOpen, setFilterOpen] = useState(false); const [selected, setSelected] = useState(null); const [detail, setDetail] = useState(null); const [explain, setExplain] = useState(null); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => { let active = true; Promise.all([api.get("/library/entities"), api.get("/library/relations")]).then(([a, b]) => { if (!active) return; setEntities(a.data?.items || []); setRelations(b.data?.items || []); setWarnings(a.data?.warnings || []); }).catch((err) => active && setError(formatApiError(err?.response?.data?.detail || err.message))).finally(() => active && setLoading(false)); return () => { active = false; }; }, []);
  useEffect(() => { if (!selected) { setDetail(null); setExplain(null); return; } let active = true; Promise.all([api.get(`/library/entities/${encodeURIComponent(selected)}`), api.get(`/library/explain/${encodeURIComponent(selected)}`)]).then(([a, b]) => { if (active) { setDetail(a.data); setExplain(b.data); } }).catch((err) => active && setError(formatApiError(err?.response?.data?.detail || err.message))); return () => { active = false; }; }, [selected]);
  const filtered = useMemo(() => filterLibraryEntities(entities, relations, filters), [entities, relations, filters]);
  const options = (field) => [...new Set(entities.map((item) => item[field]).filter(Boolean))].sort();
  const update = (field, value) => setFilters((old) => ({ ...old, [field]: value }));
  return <div className="space-y-4 fade-in" data-testid="library-page"><div className="flex flex-wrap items-end justify-between gap-3"><div><div className="eyebrow">Canonical knowledge</div><h1 className="text-2xl font-semibold tracking-tight">Library</h1><p className="mt-1 text-sm text-muted-foreground">Research memory, explicit relations and explainable decisions.</p></div><div className="flex gap-2"><DataProvenanceBadge source="RESEARCH" /><a href="/app/knowledge" className="rounded-md border border-border px-2.5 py-1.5 text-xs hover:bg-secondary">Raw / Legacy Knowledge</a></div></div>
    {error ? <Card className="border-rose-500/30 p-3 text-sm text-rose-600"><AlertTriangle className="mr-2 inline h-4 w-4" />{error}</Card> : null}
    {warnings.length ? <Card className="border-amber-500/25 p-3 text-xs text-amber-700 dark:text-amber-300"><AlertTriangle className="mr-2 inline h-4 w-4" />{warnings.length} catalog warning(s). Malformed or broken records were isolated.</Card> : null}
    <Card className="overflow-hidden"><div className="flex gap-2 border-b border-border p-3"><div className="relative min-w-0 flex-1"><Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" /><input aria-label="Search entities" value={filters.query} onChange={(e) => update("query", e.target.value)} placeholder="Search ID, title, type, status or relation" className="h-9 w-full rounded-md border border-border bg-background pl-9 pr-3 text-sm" /></div><button className="rounded-md border border-border px-3 lg:hidden" onClick={() => setFilterOpen((v) => !v)}><Filter className="h-4 w-4" /></button></div>
      <div className="grid min-w-0 lg:grid-cols-[210px_minmax(0,1fr)]"><aside className={`${filterOpen ? "block" : "hidden"} space-y-3 border-b border-border p-3 lg:block lg:border-b-0 lg:border-r`}><SelectFilter label="Type" field="type" value={filters.type} options={options("type")} onChange={update}/><SelectFilter label="Grade" field="evidence_grade" value={filters.evidence_grade} options={options("evidence_grade")} onChange={update}/><SelectFilter label="Phase" field="phase" value={filters.phase} options={options("phase")} onChange={update}/><SelectFilter label="Status" field="status" value={filters.status} options={options("status")} onChange={update}/></aside><section className="min-w-0"><div className="flex items-center justify-between border-b border-border px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground"><span>Entity index</span><span>{filtered.length} / {entities.length}</span></div>{loading ? <div className="p-8 text-center text-sm text-muted-foreground">Loading canonical catalog…</div> : filtered.map((item) => <EntityRow key={item.id} item={item} onSelect={setSelected} />)}{!loading && !filtered.length ? <div className="p-8 text-center text-sm text-muted-foreground"><BookOpen className="mx-auto mb-2 h-5 w-5" />No matching entities.</div> : null}</section></div>
    </Card><Inspector detail={detail} explain={explain} onClose={() => setSelected(null)} /></div>;
}
