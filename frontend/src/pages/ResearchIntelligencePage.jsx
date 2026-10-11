import { useEffect, useState } from "react";
import { Activity, AlertTriangle, Brain, CheckCircle2, FlaskConical, Lightbulb } from "lucide-react";
import api from "@/lib/api";
import DataProvenanceBadge from "@/components/DataProvenanceBadge";

const unavailable = value => value === null || value === undefined || value === "" ? "UNAVAILABLE" : String(value);
const badge = value => <span className="border border-border px-2 py-1 font-mono text-[10px]">{unavailable(value)}</span>;

export default function ResearchIntelligencePage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    api.get("/research/intelligence/control-center")
      .then(response => live && setData(response.data))
      .catch(() => live && setError("Research Intelligence is unavailable."));
    return () => { live = false; };
  }, []);

  if (error) return <StatePanel tone="error" title="Research Intelligence unavailable" detail={error} />;
  if (!data) return <div className="p-6 font-mono text-sm text-muted-foreground">Loading Research Intelligence…</div>;
  if (data.status === "UNAVAILABLE") return <StatePanel tone="warning" title="Canonical research data unavailable" detail={data.warnings?.[0]?.code || "UNAVAILABLE"} />;

  const loop = data.research_loop || {};
  const experiments = data.experiment_registry?.items || [];
  const queue = data.hypothesis_queue || {};
  const improvements = data.improvement_center?.items || [];
  const memory = data.research_memory?.items || [];
  const agents = data.agent_activity?.items || [];
  const approvals = data.approval_center || {};

  return <div className="space-y-5" data-testid="research-intelligence">
    <header className="flex flex-wrap items-end justify-between gap-3 border-b border-border pb-4">
      <div><div className="font-mono text-xs text-muted-foreground">RI-01 · RI-02 · READ-ONLY PROJECTION</div><h1 className="text-2xl font-semibold">Research Intelligence</h1><p className="mt-1 text-sm text-muted-foreground">Persistent experiments, hypotheses, improvements, memory and human gates.</p></div>
      <DataProvenanceBadge source="RESEARCH_MEMORY_V1" />
    </header>

    <section className="grid gap-3 md:grid-cols-3">
      <Metric icon={Activity} label="Research loop" value={loop.status} note={loop.current_phase ? `Phase: ${loop.current_phase}` : loop.reason_code} />
      <Metric icon={FlaskConical} label="Experiments" value={data.experiment_registry?.count ?? 0} note={`Last cycle: ${unavailable(loop.last_transition_at)}`} />
      <Metric icon={CheckCircle2} label="Approval center" value={approvals.count ?? 0} note="Display only · actions disabled" />
    </section>

    <Panel title="Research Loop" icon={Activity} subtitle="Current persisted loop state; no synthetic activity.">
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <Fact label="Status" value={loop.status} /><Fact label="Current phase" value={loop.current_phase} /><Fact label="Last cycle" value={loop.last_cycle} /><Fact label="Next actions" value={(loop.next_actions || []).join(", ")} />
      </div>
    </Panel>

    <Panel title="Experiment Registry" icon={FlaskConical} subtitle="Evidence records with source provenance.">
      <Table heads={["Experiment", "Status", "Dataset", "Evidence", "Source"]} empty="No persisted experiments.">
        {experiments.map(row => <tr key={row.record_id} className="border-t border-border"><td className="p-2 font-mono">{row.record_id}</td><td>{unavailable(row.status)}</td><td>{unavailable((row.datasets || []).map(item => item.dataset_id).join(", "))}</td><td>{unavailable(row.evidence_level)}</td><td className="max-w-xs break-all font-mono text-[10px]">{unavailable((row.provenance || []).map(item => item.ref).join(", "))}</td></tr>)}
      </Table>
    </Panel>

    <Panel title="Hypothesis Queue" icon={Lightbulb} subtitle="Only the latest persisted prioritization is shown.">
      {queue.status !== "AVAILABLE" ? <StatePanel title="Queue not materialized" detail={queue.reason || "NOT_MATERIALIZED"} /> : <Table heads={["Priority", "Candidate", "Family", "Evidence"]} empty="No queued hypotheses.">{(queue.items || []).map((row, index) => <tr key={row.record_id || index} className="border-t border-border"><td className="p-2">{unavailable(row.priority)}</td><td className="font-mono">{unavailable(row.record_id)}</td><td>{unavailable(row.family)}</td><td>{unavailable(row.evidence_level)}</td></tr>)}</Table>}
    </Panel>

    <Panel title="Improvement Center" icon={Brain} subtitle="Proposals and outcomes remain distinct from approved implementation.">
      <Table heads={["Proposal", "Status", "Baseline", "Success criteria", "Result"]} empty="No persisted improvement proposals.">
        {improvements.map(row => <tr key={row.record_id} className="border-t border-border"><td className="p-2 font-mono">{row.record_id}</td><td>{unavailable(row.status)}</td><td>{unavailable(row.baseline)}</td><td>{unavailable(row.success_criterion)}</td><td>{unavailable(row.results?.map(result => result.verdict).join(", "))}</td></tr>)}
      </Table>
    </Panel>

    <div className="grid gap-5 xl:grid-cols-2">
      <Panel title="Research Memory" icon={Brain} subtitle="Knowledge with explicit source and provenance.">{memory.length ? <div className="space-y-2">{memory.map(row => <article key={row.record_id} className="border border-border p-3"><div className="flex justify-between gap-2">{badge(row.type)}<span className="font-mono text-[10px] text-muted-foreground">{unavailable(row.created_at)}</span></div><p className="mt-2 text-sm">{unavailable(row.summary)}</p><div className="mt-2 break-all font-mono text-[10px] text-muted-foreground">{unavailable((row.provenance || []).map(item => item.ref).join(", "))}</div></article>)}</div> : <Empty text="No persisted observations or reviews." />}</Panel>
      <Panel title="Agent Activity" icon={Activity} subtitle="Registered research roles and persisted outcomes."><Table heads={["Agent", "Executor", "Status", "Last outcome"]} empty="No registered research agents.">{agents.map(row => <tr key={row.role_id} className="border-t border-border"><td className="p-2 font-mono">{row.role_id}</td><td>{unavailable(row.executor)}</td><td>{unavailable(row.status)}</td><td>{unavailable(row.last_outcome)}</td></tr>)}</Table></Panel>
    </div>

    <Panel title="Approval Center" icon={CheckCircle2} subtitle="Human decisions are visible; mutation controls stay disabled until the authorization contract is verified.">
      <div className="mb-3 flex items-center gap-2">{badge("READ_ONLY")}{badge(approvals.actions_enabled ? "ACTIONS_ENABLED" : "ACTIONS_DISABLED")}</div>
      <Table heads={["Record", "Kind", "Status", "Requirements"]} empty="No research decisions awaiting review.">{(approvals.items || []).map(row => <tr key={row.record_id} className="border-t border-border"><td className="p-2 font-mono">{row.record_id}</td><td>{unavailable(row.kind)}</td><td>{unavailable(row.status)}</td><td className="font-mono text-[10px]">{unavailable((row.requires || []).join(", "))}</td></tr>)}</Table>
    </Panel>
  </div>;
}

function Metric({icon: Icon,label,value,note}) { return <div className="border border-border p-4"><Icon className="h-4 w-4 text-primary"/><div className="mt-3 text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div><div className="mt-1 font-mono text-lg">{unavailable(value)}</div><div className="mt-1 text-xs text-muted-foreground">{unavailable(note)}</div></div>; }
function Panel({title,icon:Icon,subtitle,children}) { return <section className="border border-border p-4"><div className="mb-4 flex gap-3"><Icon className="mt-0.5 h-4 w-4 text-primary"/><div><h2 className="text-sm font-semibold">{title}</h2><p className="text-xs text-muted-foreground">{subtitle}</p></div></div>{children}</section>; }
function Fact({label,value}) { return <div className="border border-border p-3"><div className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</div><div className="mt-1 break-words font-mono text-xs">{unavailable(value)}</div></div>; }
function Empty({text}) { return <div className="border border-dashed border-border p-4 text-sm text-muted-foreground">{text}</div>; }
function StatePanel({title,detail,tone="neutral"}) { return <div className={`border p-5 ${tone === "error" ? "border-rose-500/30 text-rose-400" : tone === "warning" ? "border-amber-500/30" : "border-border"}`}><div className="flex gap-2"><AlertTriangle className="h-4 w-4"/><div><div className="text-sm font-semibold">{title}</div><div className="mt-1 font-mono text-xs text-muted-foreground">{detail}</div></div></div></div>; }
function Table({heads,children,empty}) { const count = Array.isArray(children) ? children.length : children ? 1 : 0; if (!count) return <Empty text={empty}/>; return <div className="overflow-x-auto border border-border"><table className="w-full min-w-[720px] text-left text-xs"><thead className="bg-secondary/40 text-[10px] uppercase text-muted-foreground"><tr>{heads.map(head => <th key={head} className="p-2">{head}</th>)}</tr></thead><tbody>{children}</tbody></table></div>; }
