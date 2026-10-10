import { diagnose } from "./diagnostics";
import { LIVE_READS } from "./live";
import { STATIONS } from "./stations";

const NOTES = {
  "systems.watch": "Il processo osservato non accende la postazione.",
  "trading.data": "Il feed osservato non accende la postazione.",
  "jarvis.orch": "La coda accesa nel ready non è una task di questa postazione.",
  "systems.req": "I reparti del payload non sono i reparti del Floor.",
  "trading.exec": "Legge cio' che l'EA ha confermato. Da qui non parte nessun ordine.",
};

function linkFrom(spec, row, queueLiveness) {
  const card = row ? diagnose(row) : null;
  const http = typeof row?.http === "number" ? row.http : null;
  const base = {
    stationId: spec.stationId,
    name: spec.name,
    capabilityId: spec.capabilityId,
    path: spec.path,
    endpoint: "MAPPED",
    capability: "UNKNOWN",
    process: "NOT_OBSERVED",
    task: "UNKNOWN",
    access: card?.access || "UNKNOWN",
    state: card?.state || "UNKNOWN",
    observedAt: card?.observedAt || null,
    queueLiveness: spec.stationId === "jarvis.orch" ? queueLiveness : null,
    note: NOTES[spec.stationId] || null,
  };
  if (!row) return base;
  if (http === 401 || http === 403) {
    return { ...base, capability: "IMPLEMENTED_UNVERIFIED", access: "AUTH_REQUIRED", state: "UNKNOWN" };
  }
  if (http === 429 || http === 0 || http >= 500 || card?.access === "EMPTY_RESPONSE") return base;
  if (spec.path === "/ready" && card?.state === "PROCESS_OBSERVED") {
    return { ...base, capability: "PROCESS_OBSERVED", process: "OBSERVED" };
  }
  if (spec.path === "/dukascopy_status" && card?.state === "FEED_OBSERVED") {
    return { ...base, capability: "FEED_OBSERVED" };
  }
  if (card?.access === "AVAILABLE" && card?.state === "UNKNOWN") {
    return { ...base, capability: "IMPLEMENTED_UNVERIFIED" };
  }
  return base;
}

export function projectCapabilities(rows) {
  const byPath = new Map((rows || []).map((row) => [row.path, row]));
  const ready = diagnose(byPath.get("/ready") || { path: "/ready", http: 0 });
  const queueLiveness = ready.facts?.queueRunning === true ? "observed-on" : ready.facts?.queueRunning === false ? "observed-off" : null;
  const links = LIVE_READS.map((spec) => linkFrom(spec, byPath.get(spec.path), queueLiveness));
  const mapped = new Set(links.map((item) => item.stationId));
  return {
    links,
    stationCount: STATIONS.length,
    simOnlyCount: STATIONS.filter((station) => !mapped.has(station.id)).length,
  };
}
