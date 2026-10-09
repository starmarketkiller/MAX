function record(data) {
  return data !== null && typeof data === "object" && !Array.isArray(data);
}

export function safeFacts(path, data) {
  if (!record(data)) return null;
  if (path === "/ready") {
    const checks = data.checks;
    if (data.ok !== true || !record(checks) || !record(checks.database) || typeof checks.database.ok !== "boolean") return null;
    if (!record(checks.queue_dispatcher) || typeof checks.queue_dispatcher.running !== "boolean") return null;
    const migrations = record(checks.migrations) ? checks.migrations : {};
    const security = record(checks.security) ? checks.security : {};
    const contracts = record(checks.contracts) ? checks.contracts : {};
    const artifacts = record(checks.artifacts) ? checks.artifacts : {};
    const queue = checks.queue_dispatcher;
    return {
      ok: true,
      version: typeof data.version === "string" ? data.version : null,
      reportedAt: typeof data.ts === "string" ? data.ts : null,
      databaseOk: checks.database.ok,
      databaseWritable: checks.database.writable === true,
      migrationsOk: migrations.ok === true,
      migrationsApplied: Array.isArray(migrations.applied) ? migrations.applied.length : null,
      securityOk: security.ok === true,
      environment: typeof security.environment === "string" ? security.environment : null,
      strategyCount: typeof contracts.strategy_count === "number" ? contracts.strategy_count : null,
      queueRunning: queue.running,
      queueEnabled: queue.enabled === true,
      queueConcurrency: typeof queue.max_concurrency === "number" ? queue.max_concurrency : null,
      workerAvailable: artifacts.worker_available === true,
    };
  }
  if (path === "/dukascopy_status") {
    const progress = data.progress;
    if (data.ok !== true || typeof data.started !== "boolean" || !record(progress) || typeof progress.days_done !== "number") return null;
    return {
      ok: true,
      started: data.started,
      daysDone: progress.days_done,
      daysTotal: typeof progress.days_total === "number" ? progress.days_total : null,
      daysWithData: typeof progress.days_with_data === "number" ? progress.days_with_data : null,
      newestDay: typeof progress.newest_day_covered === "string" ? progress.newest_day_covered : null,
      oldestDay: typeof progress.oldest_day_covered === "string" ? progress.oldest_day_covered : null,
      readyForIntraday: data.ready_for_intraday_reconfirm === true,
    };
  }
  return null;
}

export function diagnose(row) {
  const http = typeof row.http === "number" ? row.http : 0;
  const facts = row.path === "/ready" || row.path === "/dukascopy_status" ? row.facts || null : null;
  const card = {
    path: row.path,
    name: row.name || row.path,
    source: row.origin || row.path,
    observedAt: row.at || null,
    reportedAt: facts?.reportedAt || facts?.newestDay || null,
    facts,
    stationsReady: false,
    stationsRunning: false,
    stationEffect: "none",
  };
  if (http === 401 || http === 403) return { ...card, access: "AUTH_REQUIRED", state: "UNKNOWN", reason: "Sessione assente o permesso negato." };
  if (http === 404) return { ...card, access: "UNKNOWN", state: "UNKNOWN", reason: "Endpoint non trovato." };
  if (http === 429) return { ...card, access: "UNKNOWN", state: "UNKNOWN", reason: "Troppe richieste. Nessun altro tentativo." };
  if (http === 0 || http >= 500) {
    const timeout = row.api === "timeout" || row.error === "timeout";
    return { ...card, access: "UNKNOWN", state: "UNKNOWN", reason: timeout ? "Timeout." : "Endpoint non disponibile." };
  }
  if (http !== 200) return { ...card, access: "UNKNOWN", state: "UNKNOWN", reason: "Risposta non utilizzabile." };
  if (row.schema === "empty") return { ...card, access: "EMPTY_RESPONSE", state: "UNKNOWN", facts: null, reportedAt: null, reason: "Risposta vuota. Il contratto non dice che il servizio sia fermo." };
  if (row.schema !== "valid" || !facts) return { ...card, access: "AVAILABLE", state: "UNKNOWN", facts: null, reportedAt: null, reason: row.schema === "partial" || row.schema === "unexpected" ? "Dati incompleti. Payload non mostrato." : "Schema non verificato. Payload non mostrato." };
  if (row.path === "/ready") return { ...card, access: "AVAILABLE", state: "PROCESS_OBSERVED", reason: "Il processo risponde. Le 119 postazioni non diventano operative." };
  return { ...card, access: "AVAILABLE", state: "FEED_OBSERVED", reason: "Stato del feed. Nessuna postazione in esecuzione." };
}
