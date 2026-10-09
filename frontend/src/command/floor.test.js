const { readFileSync } = require("fs");
const path = require("path");
const { AUTOMATIONS } = require("./graph");
const { classifyResponse, isCurrent, LIVE_READS, MAX_CONCURRENCY, readLive } = require("./live");
const { MARKER_REACHED, REVIEW_MARKER } = require("./marker");
const { DEPARTMENTS, STATIONS, WORKFLOWS, stationById } = require("./stations");
const { SKILLS, WORKERS } = require("./skills");
const { layout, allowMotion } = require("./map");
const { scriptAt, workerLoad, PHASES } = require("./script");
const { eventsAt, frameAt, stationState, worldById } = require("./engine");

const readyPayload = { ok: true, checks: { database: { ok: true }, queue_dispatcher: { running: true } } };
const feedPayload = { ok: true, started: true, progress: { days_done: 12 } };

function source(relativePath) {
  return readFileSync(path.join(__dirname, relativePath), "utf8");
}

describe("floor nel frontend MAX", () => {
  test("conserva i registri del simulatore", () => {
    expect(DEPARTMENTS).toHaveLength(7);
    expect(STATIONS.filter((item) => item.departmentId === "council")).toHaveLength(9);
    expect(STATIONS).toHaveLength(119);
    expect(WORKFLOWS).toHaveLength(8);
    expect(SKILLS).toHaveLength(19);
    expect(WORKERS).toHaveLength(7);
    expect(AUTOMATIONS).toHaveLength(12);
  });

  test("non promuove un 200 generico e non tratta ogni 404 come pianificato", () => {
    const verified = classifyResponse({ path: "/ready", http: 200, data: readyPayload, source: "network" });
    expect(verified.status).toBe("LIVE_VERIFIED");
    expect(verified.schema).toBe("valid");
    expect(verified.task).toBe("not_inferred");
    expect(verified.live).toBe(true);
    const fixture = classifyResponse({ path: "/ready", http: 200, data: readyPayload, source: "fixture" });
    expect(fixture.live).toBe(false);
    const malformed = classifyResponse({ path: "/ready", http: 200, data: { ok: true, unexpected: true }, source: "network" });
    expect(malformed.status).toBe("LIVE_UNAVAILABLE");
    expect(malformed.schema).toBe("unexpected");
    const partial = classifyResponse({ path: "/dukascopy_status", http: 200, data: { ok: true, started: true, progress: {} }, source: "network" });
    expect(partial.schema).toBe("partial");
    expect(partial.status).toBe("LIVE_UNAVAILABLE");
    const idle = classifyResponse({ path: "/ready", http: 200, data: {}, source: "network" });
    expect(idle.status).toBe("LIVE_IDLE");
    const unknown = classifyResponse({ path: "/jarvis/executive-state", http: 200, data: { state: "present" }, source: "network" });
    expect(unknown.schema).toBe("unverified");
    expect(unknown.status).toBe("LIVE_UNAVAILABLE");
    for (const http of [401, 403, 404, 429, 503]) {
      const result = classifyResponse({ path: "/ready", http, data: null, source: "network", error: `http ${http}` });
      expect(result.status).toBe("LIVE_UNAVAILABLE");
      expect(result.status).not.toBe("PLANNED");
    }
    expect(classifyResponse({ path: "/ready", http: 404, data: null, source: "network" }).api).toBe("not_found");
    expect(classifyResponse({ path: "/ready", http: 0, data: null, source: "network", error: "timeout" }).api).toBe("timeout");
    expect(MARKER_REACHED).toBe(false);
    expect(REVIEW_MARKER).toBe("NEXUS_COMMAND_FLOOR_PR25_REVIEW_READY");
    expect(LIVE_READS).toHaveLength(9);
  });

  test("tiene i gate e scarta una lettura fuori ordine", () => {
    const trading = frameAt(worldById("trading"), 999);
    expect(stationState(trading.states, stationById("trading.valid"))).toBe("waiting");
    expect(stationState(trading.states, stationById("trading.exec"))).toBe("queued");
    expect(eventsAt(worldById("trading"), 999)).toHaveLength(0);
    const fault = frameAt(worldById("fault"), 999);
    expect(stationState(fault.states, stationById("systems.unit"))).toBe("failed");
    expect(stationState(fault.states, stationById("systems.ship"))).toBe("queued");
    expect(isCurrent(1, 2)).toBe(false);
    expect(isCurrent(2, 2)).toBe(true);
  });

  test("limita la concorrenza e non ritenta dopo un 429", async () => {
    let active = 0;
    let max = 0;
    let calls = 0;
    const client = {
      async get(requestPath) {
        calls += 1;
        active += 1;
        max = Math.max(max, active);
        await new Promise((resolve) => setTimeout(resolve, 15));
        active -= 1;
        if (requestPath === "/ready") {
          const error = new Error("limited");
          error.response = { status: 429 };
          throw error;
        }
        if (requestPath === "/dukascopy_status") return { status: 200, data: feedPayload };
        return { status: 200, data: { anything: true } };
      },
    };
    const result = await readLive(client, { generation: 4 });
    expect(max).toBeLessThanOrEqual(MAX_CONCURRENCY);
    expect(calls).toBe(MAX_CONCURRENCY);
    expect(result.rows.filter((row) => row.http === 429).length).toBeGreaterThanOrEqual(1);
    expect(result.rows.some((row) => row.task !== "not_inferred")).toBe(false);
  });

  test("separa simulazione e live e non chiama POST", () => {
    const page = source("../pages/CommandFloorPage.jsx");
    const live = source("./live.js");
    const app = source("../App.js");
    expect(page.includes("api.post")).toBe(false);
    expect(page.includes("localStorage")).toBe(false);
    expect(page.includes("useVisiblePolling")).toBe(true);
    expect(live.includes(".post(")).toBe(false);
    expect(live.includes("import.meta")).toBe(false);
    expect(app.includes('path="/floor"')).toBe(true);
    expect(app.includes('path="/research/control-plane"')).toBe(true);
    expect(page.includes("SIMULATION")).toBe(true);
    expect(page.includes("data-testid=\"floor-map\"") || page.includes("FloorMap")).toBe(true);
    expect(page.includes("Reset")).toBe(true);
    expect(page.includes(">0.5×<") || page.includes("0.5×")).toBe(true);
  });

  test("la mappa riusa i registri e il copione è riproducibile", () => {
    const map = layout();
    expect(map.departments).toHaveLength(8);
    expect(map.agents).toHaveLength(7);
    expect(new Set(map.agents.map((item) => item.id)).size).toBe(7);
    expect(map.units.every((item) => item.presence === "planned")).toBe(true);
    expect(map.departments.every((item) => item.presence === "repository")).toBe(true);
    const first = scriptAt(worldById("trading"), 0);
    expect(scriptAt(worldById("trading"), 0)).toEqual(first);
    expect(first.task).toBe("Market Data");
    expect(first.agent).toBe("data");
    expect(first.companyPresence).toBe("repository");
    expect(PHASES).toHaveLength(10);
    const gate = scriptAt(worldById("trading"), 999);
    expect(gate.execution).toBe("waiting");
    expect(gate.approval).toBe("approval");
    expect(gate.result).toMatch(/attesa/i);
    const fault = scriptAt(worldById("fault"), 999);
    expect(fault.execution).toBe("failed");
    const frame = frameAt(worldById("ecosystem"), 1);
    const load = workerLoad(frame);
    const busy = Object.values(load).reduce((sum, count) => sum + count, 0);
    expect(busy).toBe(frame.active.length);
    expect(allowMotion(true)).toBe(false);
    expect(allowMotion(false)).toBe(true);
  });
});
