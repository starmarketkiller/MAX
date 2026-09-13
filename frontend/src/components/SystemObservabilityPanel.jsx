import { useEffect, useState } from "react";
import { Activity, Database, GitCommitHorizontal, Radio, Server } from "lucide-react";
import api from "@/lib/api";
import DataProvenanceBadge from "@/components/DataProvenanceBadge";
import { Card, SectionHeader } from "@/pages/dashboard/shared";

const present = (value) => value !== null && value !== undefined && value !== "";
const show = (value) => present(value) ? String(value) : "—";

function StatusCell({ label, value, source, icon: Icon, detail }) {
  return (
    <div className="min-w-0 rounded-lg border border-border bg-secondary/20 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-1.5 truncate text-[9px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          {Icon ? <Icon size={12} /> : null}{label}
        </span>
        <DataProvenanceBadge source={source} className="px-1.5 py-0.5 text-[8px]" />
      </div>
      <div className="mt-2 truncate font-mono text-sm font-semibold" title={show(value)}>{show(value)}</div>
      {detail ? <div className="mt-1 truncate text-[9px] text-muted-foreground" title={detail}>{detail}</div> : null}
    </div>
  );
}

export default function SystemObservabilityPanel({ status, health, latestResearch }) {
  const [system, setSystem] = useState({ liveness: null, readiness: null, bridge: null });

  useEffect(() => {
    let active = true;
    (async () => {
      const results = await Promise.allSettled([
        api.get("/health"), api.get("/ready"), api.get("/local_bridge/status"),
      ]);
      if (!active) return;
      const responseData = (result) => result.status === "fulfilled"
        ? result.value.data
        : result.reason?.response?.data || null;
      setSystem({
        liveness: responseData(results[0]),
        readiness: responseData(results[1]),
        bridge: responseData(results[2]),
      });
    })();
    return () => { active = false; };
  }, []);

  const backendOk = system.liveness?.ok === true;
  const readyKnown = typeof system.readiness?.ok === "boolean";
  const databaseOk = system.readiness?.checks?.database?.ok;
  const bridgeWorker = system.bridge?.worker;
  const bridgeKnown = system.bridge !== null;
  const age = present(health?.last_update_sec) ? `${Math.max(0, Math.round(Number(health.last_update_sec)))}s ago`
    : present(status?._updated_ago) ? `${Math.max(0, Math.round(Number(status._updated_ago)))}s ago` : null;

  return (
    <section data-testid="system-observability">
      <SectionHeader title="System Observability" subtitle="Runtime, data feed and research readiness" />
      <Card className="p-3 sm:p-4">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <StatusCell label="Backend" icon={Server} value={backendOk ? "ONLINE" : null} source={backendOk ? "LIVE" : "UNAVAILABLE"} detail={backendOk ? system.liveness.service : null} />
          <StatusCell label="Readiness / DB" icon={Database} value={readyKnown ? (system.readiness.ok && databaseOk ? "READY" : "NOT READY") : null} source={readyKnown ? "LIVE" : "UNAVAILABLE"} detail={present(system.liveness?.environment) ? system.liveness.environment : null} />
          <StatusCell label="EA" icon={Activity} value={health?.online === true ? "ONLINE" : health?.online === false ? "OFFLINE" : null} source={health?.demo === true ? "DEMO" : health?.online === true ? "LIVE" : health ? "CACHED" : "UNAVAILABLE"} detail={age ? `updated ${age}` : null} />
          <StatusCell label="LocalBridge" icon={Radio} value={bridgeKnown ? (bridgeWorker?.online ? "ONLINE" : "OFFLINE") : null} source={bridgeWorker?.online ? "LIVE" : bridgeKnown ? "CACHED" : "UNAVAILABLE"} detail={bridgeWorker?.timestamp || system.bridge?.timestamp || null} />
          <StatusCell label="Backend version" icon={GitCommitHorizontal} value={system.liveness?.version} source={backendOk && present(system.liveness?.version) ? "LIVE" : "UNAVAILABLE"} />
          <StatusCell label="App git commit" icon={GitCommitHorizontal} value={null} source="UNAVAILABLE" detail="Not exposed at runtime" />
          <StatusCell label="Latest data update" icon={Activity} value={age} source={age ? (health?.online ? "LIVE" : "CACHED") : "UNAVAILABLE"} />
          <StatusCell label="Latest research" icon={GitCommitHorizontal} value={latestResearch?.verdict} source={latestResearch ? "RESEARCH" : "UNAVAILABLE"} detail={latestResearch?.run_id || null} />
        </div>
      </Card>
    </section>
  );
}
