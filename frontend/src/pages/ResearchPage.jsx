import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Database, FlaskConical, Link2 } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import DataProvenanceBadge from "@/components/DataProvenanceBadge";
import { Card } from "@/pages/dashboard/shared";

const EMPTY = { experiments: [], datasets: [], evidence: [] };
const show = (value) => value === null || value === undefined || value === "" ? "—" : String(value);

function RelationLink({ relation }) {
  const anchor = relation.target_id || relation.source_id;
  return (
    <a href={`#${encodeURIComponent(anchor)}`} className="rounded border border-border bg-secondary/40 px-2 py-1 font-mono text-[10px] hover:bg-secondary">
      {relation.type} · {anchor}
    </a>
  );
}

export default function ResearchPage() {
  const [hypotheses, setHypotheses] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [related, setRelated] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get("/research/hypotheses"), api.get("/research/experiments"),
      api.get("/research/datasets"), api.get("/research/evidence"),
    ]).then(([hypothesisResponse, experimentResponse, datasetResponse, evidenceResponse]) => {
      if (!active) return;
      const items = hypothesisResponse.data?.items || [];
      setHypotheses(items);
      setSelectedId(items.find((item) => item.id === "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT")?.id || items[0]?.id || null);
      setRelated({ experiments: experimentResponse.data?.items || [], datasets: datasetResponse.data?.items || [], evidence: evidenceResponse.data?.items || [] });
    }).catch((requestError) => active && setError(formatApiError(requestError?.response?.data?.detail || requestError.message)))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedId) { setDetail(null); return undefined; }
    let active = true;
    api.get(`/research/hypotheses/${encodeURIComponent(selectedId)}`)
      .then(({ data }) => active && setDetail(data))
      .catch((requestError) => active && setError(formatApiError(requestError?.response?.data?.detail || requestError.message)));
    return () => { active = false; };
  }, [selectedId]);

  const relationIds = useMemo(() => {
    const connected = new Set(detail?.id ? [detail.id] : []);
    const all = [detail, ...related.experiments, ...related.datasets, ...related.evidence].filter(Boolean);
    let changed = true;
    while (changed) {
      changed = false;
      all.flatMap((item) => item.relations || []).forEach((relation) => {
        if (connected.has(relation.source_id) || connected.has(relation.target_id)) {
          if (!connected.has(relation.source_id) || !connected.has(relation.target_id)) changed = true;
          connected.add(relation.source_id); connected.add(relation.target_id);
        }
      });
    }
    return connected;
  }, [detail, related]);
  const relevant = (items) => items.filter((item) => relationIds.has(item.id));

  return (
    <div className="space-y-4 fade-in" data-testid="research-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><div className="eyebrow">Canonical read model v1</div><h1 className="text-2xl font-semibold tracking-tight">Research</h1><p className="mt-1 text-sm text-muted-foreground">Hypotheses, evidence and stable research relations.</p></div>
        <DataProvenanceBadge source="RESEARCH" />
      </div>
      {error ? <Card className="border-rose-500/30 p-3 text-sm text-rose-600 dark:text-rose-400"><AlertTriangle className="mr-2 inline h-4 w-4" />{error}</Card> : null}
      {loading ? <Card className="p-8 text-center text-sm text-muted-foreground">Loading canonical research catalog…</Card> : (
        <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(240px,0.75fr)_minmax(0,2fr)]">
          <Card className="min-w-0 p-3">
            <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Hypotheses · {hypotheses.length}</div>
            <div className="max-h-[68vh] space-y-1 overflow-y-auto">
              {hypotheses.map((item) => <button key={item.id} type="button" onClick={() => setSelectedId(item.id)} className={`w-full rounded-md border px-3 py-2 text-left ${item.id === selectedId ? "border-sky-500/40 bg-sky-500/10" : "border-transparent hover:bg-secondary/60"}`}><div className="truncate font-mono text-[11px]">{item.id}</div><div className="mt-1 flex items-center justify-between gap-2 text-xs text-muted-foreground"><span className="truncate">{show(item.status)}</span><span className="font-mono">{show(item.evidence_grade)}</span></div></button>)}
              {!hypotheses.length ? <div className="p-4 text-sm text-muted-foreground">No hypotheses available.</div> : null}
            </div>
          </Card>
          <div className="min-w-0 space-y-4">
            {detail ? <Card className="min-w-0 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><div className="break-all font-mono text-xs text-muted-foreground">{detail.id}</div><h2 className="mt-1 text-lg font-semibold">{show(detail.title)}</h2></div><div className="flex gap-2"><span className="rounded border border-border px-2 py-1 font-mono text-xs">{show(detail.status)}</span><span className="rounded border border-violet-500/30 bg-violet-500/10 px-2 py-1 font-mono text-xs text-violet-700 dark:text-violet-300">{show(detail.evidence_grade)}</span></div></div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{[["Holdout", detail.true_holdout_performed === true ? "Performed" : "—"], ["E3 promotion", detail.promoted_to_e3 === false ? "No" : show(detail.promoted_to_e3)], ["Execution", detail.execution_status], ["ΔP holdout", detail.metrics?.delta_p_holdout == null ? null : Number(detail.metrics.delta_p_holdout).toFixed(3)]].map(([label, value]) => <div key={label} className="rounded-md border border-border bg-secondary/30 p-3"><div className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">{label}</div><div className="mt-1 font-mono text-sm tabular-nums">{show(value)}</div></div>)}</div>
              {detail.grade_cap_reason ? <div className="mt-4 rounded-md border border-amber-500/25 bg-amber-500/10 p-3 text-sm"><span className="font-semibold">Grade cap:</span> {detail.grade_cap_reason}</div> : null}
              <div className="mt-4"><div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground"><Link2 size={12}/>Relations</div><div className="flex flex-wrap gap-2">{(detail.relations || []).map((relation) => <RelationLink key={`${relation.type}-${relation.source_id}-${relation.target_id}`} relation={relation}/>)}</div></div>
              <div className="mt-4 border-t border-border pt-3 font-mono text-[10px] text-muted-foreground">Source: {show(detail.source?.source_file)} · {detail.source?.mode || "—"}</div>
            </Card> : null}
            <div className="grid min-w-0 gap-4 xl:grid-cols-3">
              {[["Experiments", FlaskConical, relevant(related.experiments)], ["Datasets", Database, relevant(related.datasets)], ["Evidence", Link2, relevant(related.evidence)]].map(([label, Icon, items]) => <Card key={label} className="min-w-0 p-3"><div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground"><Icon size={12}/>{label}</div><div className="space-y-2">{items.map((item) => <div id={item.id} key={item.id} className="rounded border border-border bg-secondary/30 p-2"><div className="break-all font-mono text-[10px]">{item.id}</div><div className="mt-1 text-xs text-muted-foreground">{show(item.status)}</div></div>)}{!items.length ? <div className="text-xs text-muted-foreground">No direct canonical relation.</div> : null}</div></Card>)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
