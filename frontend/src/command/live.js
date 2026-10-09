export const LIVE_READS = [
  { name: "Monitoring", stationId: "systems.watch", capabilityId: "process-readiness", path: "/ready" },
  { name: "Market Feed Status", stationId: "trading.data", capabilityId: "market-feed-backfill", path: "/dukascopy_status" },
  { name: "Executive State", stationId: "jarvis.state", capabilityId: "executive-state", path: "/jarvis/executive-state" },
  { name: "Company Overview", stationId: "systems.req", capabilityId: "company-overview", path: "/company/overview" },
  { name: "Jarvis Task Status", stationId: "jarvis.monitor", capabilityId: "task-activity", path: "/jarvis/activity" },
  { name: "Jarvis Queue", stationId: "jarvis.orch", capabilityId: "dispatcher", path: "/jarvis/dispatcher/status" },
  { name: "Revenue", stationId: "revenue.find", capabilityId: "revenue-automation", path: "/revenue/automation/status" },
  { name: "Trading Research", stationId: "trading.research", capabilityId: "research-overview", path: "/research/control-plane/overview" },
  { name: "Approvals", stationId: "jarvis.approval", capabilityId: "approvals", path: "/jarvis/approvals" },
];

export function classifyResponse({ http, empty, source }) {
  if (http === 401 || http === 403) return { status: "LIVE_UNAVAILABLE", live: false, task: "not_inferred" };
  if (http === 404) return { status: "PLANNED", live: false, task: "not_inferred" };
  if (http === 0 || http >= 500) return { status: "LIVE_UNAVAILABLE", live: false, task: "not_inferred" };
  if (http === 200 && empty) return { status: "LIVE_IDLE", live: source === "network", task: "not_inferred" };
  if (http === 200) return { status: "LIVE_VERIFIED", live: source === "network", task: "not_inferred" };
  return { status: "LIVE_UNAVAILABLE", live: false, task: "not_inferred" };
}

function emptyBody(data) {
  if (data == null) return true;
  if (Array.isArray(data)) return data.length === 0;
  if (typeof data === "object") return Object.keys(data).length === 0;
  return false;
}

export async function readLive(client) {
  const at = new Date().toISOString();
  const rows = [];
  for (const spec of LIVE_READS) {
    try {
      const response = await client.get(spec.path, { timeout: 8000 });
      const judged = classifyResponse({ http: response.status, empty: emptyBody(response.data), source: "network" });
      rows.push({ ...spec, ...judged, http: response.status, at, origin: spec.path, entityId: null, error: null });
    } catch (error) {
      const http = error?.response?.status ?? 0;
      const judged = classifyResponse({ http, empty: true, source: "network" });
      rows.push({ ...spec, ...judged, http, at, origin: spec.path, entityId: null, error: http === 0 ? "offline" : `http ${http}` });
    }
  }
  return { at, rows };
}
