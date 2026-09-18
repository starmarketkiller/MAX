import { useEffect, useState } from "react";
import api from "@/lib/api";
import SystemObservabilityPanel from "@/components/SystemObservabilityPanel";
import HealthScoreCard from "@/pages/dashboard/HealthScoreCard";

export default function SystemStatusPage({ status, health }) {
  const [latestResearch, setLatestResearch] = useState(null);
  useEffect(() => { let active = true; api.get("/research/certificates/latest").then(({ data }) => active && setLatestResearch(data)).catch(() => active && setLatestResearch(null)); return () => { active = false; }; }, []);
  return <div className="space-y-5" data-testid="system-status-page"><SystemObservabilityPanel status={status} health={health} latestResearch={latestResearch}/><section><h2 className="mb-3 text-sm font-semibold">EA telemetry health</h2><HealthScoreCard health={health} compact/></section></div>;
}
