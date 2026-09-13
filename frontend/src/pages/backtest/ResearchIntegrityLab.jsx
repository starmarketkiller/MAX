import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle, CheckCircle2, ChevronRight,
  FlaskConical, Loader2, RefreshCw, ShieldCheck, XCircle,
} from "lucide-react";
import api from "@/lib/api";
import { Card, SectionHeader, cls } from "@/pages/dashboard/shared";

const STAGES = ["generated", "blocked", "open_attempt", "opened", "broker_reject"];
const STAGE_LABELS = {
  generated: "GENERATED",
  blocked: "BLOCKED",
  open_attempt: "OPEN ATTEMPT",
  opened: "OPENED",
  broker_reject: "BROKER REJECT",
};

const hasValue = (value) => value !== null && value !== undefined && value !== "";
const show = (value) => hasValue(value) ? String(value) : "—";
const tf = (value) => hasValue(value) ? String(value).replace(/^PERIOD_/, "") : "—";
const period = (certificate) => `${show(certificate?.period_start)} → ${show(certificate?.period_end)}`;
const ratio = (value, generated) => {
  if (!hasValue(value) || !hasValue(generated) || Number(generated) <= 0) return "—";
  return `${((Number(value) / Number(generated)) * 100).toFixed(1)}%`;
};

function ResearchBadge() {
  return <span className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-1 font-mono text-[9px] font-bold tracking-wider text-violet-600 dark:text-violet-300">RESEARCH</span>;
}

function VerdictBadge({ verdict }) {
  const styles = {
    PASS: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
    PASS_WITH_WARNINGS: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400",
    FAIL: "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400",
  };
  const Icon = verdict === "PASS" ? CheckCircle2 : verdict === "FAIL" ? XCircle : AlertTriangle;
  return (
    <span className={cls("inline-flex items-center gap-1.5 rounded-full border px-2 py-1 font-mono text-[9px] font-bold tracking-wider", styles[verdict] || "border-border text-muted-foreground")}>
      <Icon size={11} />{show(verdict)}
    </span>
  );
}

function Field({ label, value, wide = false }) {
  return (
    <div className={cls("min-w-0 rounded-lg border border-border bg-secondary/25 px-3 py-2.5", wide && "sm:col-span-2")}>
      <div className="text-[9px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</div>
      <div className="mt-1 break-words font-mono text-xs font-semibold text-foreground">{show(value)}</div>
    </div>
  );
}

export function ResearchFunnel({ funnel, gateReasons }) {
  const generated = funnel?.generated;
  const reasons = useMemo(() => Object.entries(gateReasons || {}).sort((a, b) => Number(b[1]) - Number(a[1])), [gateReasons]);
  return (
    <div className="space-y-3" data-testid="research-funnel">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
        {STAGES.map((stage) => (
          <div key={stage} className="min-w-0 rounded-lg border border-border bg-background/70 px-3 py-3">
            <div className="font-mono text-[9px] font-bold tracking-[0.1em] text-violet-600 dark:text-violet-300">{STAGE_LABELS[stage]}</div>
            <div className="mt-2 font-mono text-xl font-bold tabular-nums text-foreground">{show(funnel?.[stage])}</div>
            <div className="mt-0.5 font-mono text-[10px] text-muted-foreground">{ratio(funnel?.[stage], generated)} of generated</div>
          </div>
        ))}
      </div>
      <div className="rounded-lg border border-border bg-secondary/20 px-3 py-3">
        <div className="mb-2 text-[9px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">Top gate reasons</div>
        {reasons.length ? (
          <div className="flex flex-wrap gap-2">
            {reasons.slice(0, 6).map(([reason, count]) => (
              <span key={reason} className="rounded-md border border-border bg-background px-2 py-1 font-mono text-[10px] text-foreground">{reason} <b>{show(count)}</b></span>
            ))}
          </div>
        ) : <div className="text-xs text-muted-foreground">No gate reasons reported</div>}
      </div>
    </div>
  );
}

function LatestRun({ certificate }) {
  return (
    <Card className="p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2"><ResearchBadge /><VerdictBadge verdict={certificate.verdict} /></div>
          <h2 className="mt-3 text-lg font-semibold tracking-tight">Latest research run</h2>
          <div className="mt-1 break-all font-mono text-[11px] text-muted-foreground">{show(certificate.run_id)}</div>
        </div>
        <div className="text-right"><div className="text-[9px] uppercase tracking-wider text-muted-foreground">Period</div><div className="mt-1 font-mono text-[10px] text-foreground">{period(certificate)}</div></div>
      </div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-7">
        <Field label="Strategy" value={certificate.strategy} />
        <Field label="Selector" value={certificate.selector} />
        <Field label="Source TF" value={tf(certificate.source_tf)} />
        <Field label="Entry TF" value={tf(certificate.entry_tf)} />
        <Field label="Mode" value={certificate.exit_mode} />
        <Field label="Code build" value={certificate.code_build} />
        <Field label="Git commit" value={certificate.git_commit} />
      </div>
      <div className="mt-2 grid grid-cols-1 gap-2 xl:grid-cols-2">
        <Field label="Config fingerprint" value={certificate.config_fingerprint} />
        <Field label="Period" value={period(certificate)} />
      </div>
    </Card>
  );
}

function Protection({ label, value }) {
  const known = typeof value === "boolean";
  return (
    <div className="rounded-lg border border-border bg-secondary/25 px-3 py-2.5">
      <div className="text-[9px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cls("mt-1 font-mono text-xs font-bold", !known ? "text-muted-foreground" : value ? "text-emerald-600 dark:text-emerald-400" : "text-foreground")}>
        {!known ? "—" : value ? "ENABLED" : "DISABLED"}
      </div>
    </div>
  );
}

function CertificateDetail({ detail, funnel, loading, error, onClose }) {
  if (loading) return <Card className="p-8 text-center"><Loader2 className="mx-auto h-6 w-6 animate-spin text-violet-500" /><div className="mt-2 text-xs text-muted-foreground">Loading certificate…</div></Card>;
  if (error) return <Card className="border-rose-500/30 p-5 text-sm text-rose-600 dark:text-rose-400">{error}</Card>;
  if (!detail) return null;
  const protections = detail.opt_in || {};
  const integrityItems = [
    ["Fail reasons", detail.fail_reasons],
    ["Warnings", detail.warnings],
  ];
  return (
    <Card className="p-4 sm:p-5" testId="certificate-detail">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3 border-b border-border pb-4">
        <div><div className="flex items-center gap-2"><ResearchBadge /><VerdictBadge verdict={detail.verdict} /></div><h2 className="mt-3 text-lg font-semibold">Certificate detail</h2><div className="mt-1 break-all font-mono text-[11px] text-muted-foreground">{show(detail.run_id)}</div></div>
        <button type="button" onClick={onClose} className="rounded-lg border border-border px-3 py-2 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground">Close detail</button>
      </div>

      <div className="space-y-5">
        <section><SectionHeader title="Identity" /><div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4"><Field label="Run ID" value={detail.run_id} /><Field label="Config fingerprint" value={detail.config_fingerprint} /><Field label="Strategy" value={detail.strategy} /><Field label="Selector" value={detail.selector} /></div></section>
        <section><SectionHeader title="Environment" /><div className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-7"><Field label="Source TF" value={tf(detail.source_tf)} /><Field label="Entry TF" value={tf(detail.entry_tf)} /><Field label="Leverage" value={detail.leverage} /><Field label="Lot mode" value={detail.lot_mode} /><Field label="Fixed lot" value={detail.fixed_lot} /><Field label="Code build" value={detail.code_build} /><Field label="Git commit" value={detail.git_commit} /></div></section>
        <section><SectionHeader title="Research protections" /><div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6"><Protection label="RiskShield" value={protections.risk_shield} /><Protection label="ESL" value={protections.esl} /><Protection label="DailyDD" value={protections.daily_dd} /><Protection label="TotalDD" value={protections.total_dd} /><Protection label="Ruin" value={protections.ruin} /><Protection label="DPT" value={protections.dpt} /></div></section>
        <section><SectionHeader title="Funnel" /><ResearchFunnel funnel={funnel?.funnel || detail.funnel} gateReasons={funnel?.gate_reason_counts || detail.gate_reason_counts} /></section>
        <section><SectionHeader title="Integrity" /><div className="grid grid-cols-1 gap-2 md:grid-cols-3"><Field label="Verdict" value={detail.verdict} />{integrityItems.map(([label, value]) => <Field key={label} label={label} value={value} />)}</div></section>
        <section><SectionHeader title="Gate breakdown" /><div className="overflow-x-auto rounded-lg border border-border"><table className="w-full min-w-[420px] text-xs"><thead><tr className="border-b border-border bg-secondary/30 text-left text-[9px] uppercase tracking-wider text-muted-foreground"><th className="px-3 py-2">Gate reason</th><th className="px-3 py-2 text-right">Count</th><th className="px-3 py-2 text-right">% generated</th></tr></thead><tbody>{Object.entries(funnel?.gate_reason_counts || detail.gate_reason_counts || {}).length ? Object.entries(funnel?.gate_reason_counts || detail.gate_reason_counts || {}).sort((a,b) => Number(b[1])-Number(a[1])).map(([reason,count]) => <tr key={reason} className="border-b border-border last:border-0"><td className="px-3 py-2 font-mono">{reason}</td><td className="px-3 py-2 text-right font-mono">{show(count)}</td><td className="px-3 py-2 text-right font-mono text-muted-foreground">{ratio(count, (funnel?.funnel || detail.funnel)?.generated)}</td></tr>) : <tr><td colSpan={3} className="px-3 py-5 text-center text-muted-foreground">No gate reasons reported</td></tr>}</tbody></table></div></section>
      </div>
    </Card>
  );
}

export default function ResearchIntegrityLab() {
  const [certificates, setCertificates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedRun, setSelectedRun] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailFunnel, setDetailFunnel] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

  const loadCertificates = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const { data } = await api.get("/research/certificates?limit=100");
      setCertificates(Array.isArray(data?.certificates) ? data.certificates : []);
    } catch (requestError) {
      setCertificates([]);
      setError(requestError?.response?.status === 404 ? "No research certificate available" : "Research certificates unavailable");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadCertificates(); }, [loadCertificates]);

  const openDetail = useCallback(async (runId) => {
    setSelectedRun(runId); setDetail(null); setDetailFunnel(null); setDetailError(""); setDetailLoading(true);
    try {
      const encoded = encodeURIComponent(runId);
      const [certificateResponse, funnelResponse] = await Promise.all([
        api.get(`/research/certificates/${encoded}`),
        api.get(`/research/certificates/${encoded}/funnel`),
      ]);
      setDetail(certificateResponse.data);
      setDetailFunnel(funnelResponse.data);
    } catch (requestError) {
      setDetailError(requestError?.response?.status === 404 ? "Research certificate not found" : "Certificate detail unavailable");
    } finally { setDetailLoading(false); }
  }, []);

  const latest = certificates[0] || null;
  return (
    <div className="space-y-5" data-testid="research-integrity-lab">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><FlaskConical className="h-5 w-5 text-violet-500" /><h2 className="text-xl font-bold tracking-tight">Research Lab</h2><ResearchBadge /></div><p className="mt-1 text-xs text-muted-foreground">Quantitative integrity certificates and execution funnel.</p></div><button type="button" onClick={loadCertificates} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs hover:bg-secondary disabled:opacity-50"><RefreshCw size={13} className={loading ? "animate-spin" : ""} />Refresh</button></div>

      {loading ? <Card className="p-10 text-center"><Loader2 className="mx-auto h-7 w-7 animate-spin text-violet-500" /><div className="mt-2 text-xs text-muted-foreground">Loading research certificates…</div></Card>
        : error ? <Card className="border-rose-500/30 p-5 text-sm text-rose-600 dark:text-rose-400">{error}</Card>
          : !latest ? <Card className="p-10 text-center"><ShieldCheck className="mx-auto h-8 w-8 text-muted-foreground/40" /><div className="mt-3 font-semibold">No research certificate available</div></Card>
            : <><LatestRun certificate={latest} /><section><SectionHeader title="Quantitative integrity funnel" subtitle="Counts preserved from the latest research certificate" /><Card className="p-4"><ResearchFunnel funnel={latest.funnel} gateReasons={latest.gate_reason_counts} /></Card></section></>}

      {!loading && !error && certificates.length > 0 && (
        <section><SectionHeader title="Recent certificates" subtitle={`${certificates.length} research run${certificates.length === 1 ? "" : "s"}`} /><Card><div className="overflow-x-auto"><table className="w-full min-w-[980px] text-xs"><thead><tr className="border-b border-border bg-secondary/25 text-left text-[9px] uppercase tracking-wider text-muted-foreground"><th className="px-4 py-3">Verdict</th><th className="px-3 py-3">Strategy</th><th className="px-3 py-3">Run ID</th><th className="px-3 py-3">Period</th><th className="px-3 py-3">TF</th><th className="px-3 py-3">RAW/RECIPE</th><th className="px-3 py-3 text-right">Generated</th><th className="px-3 py-3 text-right">Opened</th><th className="px-3 py-3 text-right">Blocked</th><th className="px-3 py-3">Git commit</th><th className="px-4 py-3" aria-label="Open detail" /></tr></thead><tbody>{certificates.map((certificate) => <tr key={certificate.run_id} tabIndex={0} role="button" onClick={() => openDetail(certificate.run_id)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openDetail(certificate.run_id); } }} className={cls("cursor-pointer border-b border-border transition-colors last:border-0 hover:bg-secondary/40 focus:bg-secondary/40 focus:outline-none", selectedRun === certificate.run_id && "bg-violet-500/5")}><td className="px-4 py-3"><VerdictBadge verdict={certificate.verdict} /></td><td className="px-3 py-3 font-semibold">{show(certificate.strategy)}</td><td className="max-w-[220px] truncate px-3 py-3 font-mono text-[10px]" title={show(certificate.run_id)}>{show(certificate.run_id)}</td><td className="px-3 py-3 font-mono text-[10px]">{period(certificate)}</td><td className="px-3 py-3 font-mono">{tf(certificate.source_tf)} → {tf(certificate.entry_tf)}</td><td className="px-3 py-3 font-mono">{show(certificate.exit_mode)}</td><td className="px-3 py-3 text-right font-mono">{show(certificate.funnel?.generated)}</td><td className="px-3 py-3 text-right font-mono">{show(certificate.funnel?.opened)}</td><td className="px-3 py-3 text-right font-mono">{show(certificate.funnel?.blocked)}</td><td className="px-3 py-3 font-mono text-[10px]">{show(certificate.git_commit)}</td><td className="px-4 py-3"><ChevronRight size={14} className="text-muted-foreground" /></td></tr>)}</tbody></table></div></Card></section>
      )}

      {selectedRun && <CertificateDetail detail={detail} funnel={detailFunnel} loading={detailLoading} error={detailError} onClose={() => { setSelectedRun(null); setDetail(null); setDetailFunnel(null); setDetailError(""); }} />}
    </div>
  );
}
