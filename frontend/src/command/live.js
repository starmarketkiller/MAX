import { safeFacts } from "./diagnostics";

export const MAX_CONCURRENCY = 3;
export const ENDPOINT_TIMEOUT_MS = 8000;

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

function objectRecord(data) {
  return data !== null && typeof data === "object" && !Array.isArray(data);
}

function readinessSchema(data) {
  if (!objectRecord(data) || data.ok !== true || !objectRecord(data.checks)) return "unexpected";
  const database = data.checks.database;
  const queue = data.checks.queue_dispatcher;
  if (!objectRecord(database) || typeof database.ok !== "boolean") return "partial";
  if (!objectRecord(queue) || typeof queue.running !== "boolean") return "partial";
  return "valid";
}

function feedSchema(data) {
  if (!objectRecord(data) || data.ok !== true || typeof data.started !== "boolean" || !objectRecord(data.progress)) return "unexpected";
  if (typeof data.progress.days_done !== "number") return "partial";
  return "valid";
}

const KNOWN_SCHEMAS = {
  "/ready": readinessSchema,
  "/dukascopy_status": feedSchema,
};

export function isCurrent(generation, current) {
  return generation === current;
}

export function classifyResponse({ path, http, data, source, error }) {
  const base = { live: false, task: "not_inferred", observed: null, schema: "not_applicable", api: "unexpected" };
  if (http === 401 || http === 403) return { ...base, status: "LIVE_UNAVAILABLE", api: "unauthorized" };
  if (http === 404) return { ...base, status: "LIVE_UNAVAILABLE", api: "not_found" };
  if (http === 429) return { ...base, status: "LIVE_UNAVAILABLE", api: "limited" };
  if (http === 0 || http >= 500) return { ...base, status: "LIVE_UNAVAILABLE", api: error === "timeout" ? "timeout" : "offline" };
  if (http !== 200) return { ...base, status: "LIVE_UNAVAILABLE", api: "unexpected" };
  const empty = data == null || (Array.isArray(data) && data.length === 0) || (objectRecord(data) && Object.keys(data).length === 0);
  if (empty) return { ...base, status: "LIVE_IDLE", api: "available", schema: "empty" };
  const validator = KNOWN_SCHEMAS[path];
  if (!validator) return { ...base, status: "LIVE_UNAVAILABLE", api: "available", schema: "unverified" };
  const schema = validator(data);
  if (schema !== "valid") return { ...base, status: "LIVE_UNAVAILABLE", api: "available", schema };
  const observed = path === "/ready"
    ? { databaseOk: data.checks.database.ok, queueRunning: data.checks.queue_dispatcher.running }
    : { started: data.started, daysDone: data.progress.days_done };
  return { status: "LIVE_VERIFIED", live: source === "network", task: "not_inferred", observed, schema: "valid", api: "available" };
}

function failureKind(error) {
  const http = error?.response?.status;
  if (typeof http === "number") return { http, error: http === 429 ? "rate limit, non ripetuto" : `http ${http}` };
  const timedOut = error?.code === "ECONNABORTED" || error?.code === "ETIMEDOUT" || /timeout/i.test(error?.message || "");
  return { http: 0, error: timedOut ? "timeout" : "offline" };
}

async function mapLimit(items, limit, worker) {
  const results = new Array(items.length);
  let cursor = 0;
  const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (cursor < items.length) {
      const index = cursor;
      cursor += 1;
      results[index] = await worker(items[index], index);
    }
  });
  await Promise.all(runners);
  return results;
}

export async function readLive(client, options = {}) {
  const at = new Date().toISOString();
  const generation = options.generation ?? 0;
  let stopForLimit = false;
  const rows = await mapLimit(LIVE_READS, MAX_CONCURRENCY, async (spec) => {
    if (stopForLimit) {
      const judged = classifyResponse({ path: spec.path, http: 429, data: null, source: "network", error: "rate limit, non ripetuto" });
      return { ...spec, ...judged, facts: null, http: 429, at, origin: spec.path, entityId: null, error: "rate limit, non ripetuto", generation };
    }
    try {
      const response = await client.get(spec.path, { timeout: ENDPOINT_TIMEOUT_MS });
      const judged = classifyResponse({ path: spec.path, http: response.status, data: response.data, source: "network" });
      return { ...spec, ...judged, facts: safeFacts(spec.path, response.data), http: response.status, at, origin: spec.path, entityId: null, error: null, generation };
    } catch (error) {
      const failed = failureKind(error);
      if (failed.http === 429) stopForLimit = true;
      const judged = classifyResponse({ path: spec.path, http: failed.http, data: null, source: "network", error: failed.error });
      return { ...spec, ...judged, facts: null, http: failed.http, at, origin: spec.path, entityId: null, error: failed.error, generation };
    }
  });
  return { at, generation, rows };
}
