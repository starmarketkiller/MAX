import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { AUTOMATIONS } from "./graph.js";
import { classifyResponse, isCurrent, LIVE_READS, MAX_CONCURRENCY, readLive } from "./live.js";
import { MARKER_REACHED, REVIEW_MARKER } from "./marker.js";
import { DEPARTMENTS, STATIONS, WORKFLOWS, stationById } from "./stations.js";
import { SKILLS, WORKERS } from "./skills.js";
import { eventsAt, frameAt, stationState, worldById } from "./engine.js";

const readyPayload = { ok: true, checks: { database: { ok: true }, queue_dispatcher: { running: true } } };
const feedPayload = { ok: true, started: true, progress: { days_done: 12 } };

describe("floor nel frontend MAX", () => {
  it("conserva i registri del simulatore", () => {
    assert.equal(DEPARTMENTS.length, 7);
    assert.equal(STATIONS.filter((item) => item.departmentId === "council").length, 9);
    assert.equal(STATIONS.length, 119);
    assert.equal(WORKFLOWS.length, 8);
    assert.equal(SKILLS.length, 19);
    assert.equal(WORKERS.length, 7);
    assert.equal(AUTOMATIONS.length, 12);
  });

  it("non promuove un 200 generico e non tratta ogni 404 come pianificato", () => {
    const verified = classifyResponse({ path: "/ready", http: 200, data: readyPayload, source: "network" });
    assert.equal(verified.status, "LIVE_VERIFIED");
    assert.equal(verified.schema, "valid");
    assert.equal(verified.task, "not_inferred");
    assert.equal(verified.live, true);
    const fixture = classifyResponse({ path: "/ready", http: 200, data: readyPayload, source: "fixture" });
    assert.equal(fixture.live, false);
    const malformed = classifyResponse({ path: "/ready", http: 200, data: { ok: true, unexpected: true }, source: "network" });
    assert.equal(malformed.status, "LIVE_UNAVAILABLE");
    assert.equal(malformed.schema, "unexpected");
    const partial = classifyResponse({ path: "/dukascopy_status", http: 200, data: { ok: true, started: true, progress: {} }, source: "network" });
    assert.equal(partial.schema, "partial");
    assert.equal(partial.status, "LIVE_UNAVAILABLE");
    const idle = classifyResponse({ path: "/ready", http: 200, data: {}, source: "network" });
    assert.equal(idle.status, "LIVE_IDLE");
    const unknown = classifyResponse({ path: "/jarvis/executive-state", http: 200, data: { state: "present" }, source: "network" });
    assert.equal(unknown.schema, "unverified");
    assert.equal(unknown.status, "LIVE_UNAVAILABLE");
    for (const http of [401, 403, 404, 429, 503]) {
      const result = classifyResponse({ path: "/ready", http, data: null, source: "network", error: http === 0 ? "offline" : `http ${http}` });
      assert.equal(result.status, "LIVE_UNAVAILABLE");
      assert.notEqual(result.status, "PLANNED");
    }
    assert.equal(classifyResponse({ path: "/ready", http: 404, data: null, source: "network" }).api, "not_found");
    assert.equal(classifyResponse({ path: "/ready", http: 0, data: null, source: "network", error: "timeout" }).api, "timeout");
    assert.equal(MARKER_REACHED, false);
    assert.equal(REVIEW_MARKER, "NEXUS_COMMAND_FLOOR_PR25_REVIEW_READY");
    assert.equal(LIVE_READS.length, 9);
  });

  it("tiene i gate e scarta una lettura fuori ordine", () => {
    const trading = frameAt(worldById("trading"), 999);
    assert.equal(stationState(trading.states, stationById("trading.valid")), "waiting");
    assert.equal(stationState(trading.states, stationById("trading.exec")), "queued");
    assert.equal(eventsAt(worldById("trading"), 999).length, 0);
    const fault = frameAt(worldById("fault"), 999);
    assert.equal(stationState(fault.states, stationById("systems.unit")), "failed");
    assert.equal(stationState(fault.states, stationById("systems.ship")), "queued");
    assert.equal(isCurrent(1, 2), false);
    assert.equal(isCurrent(2, 2), true);
  });

  it("limita la concorrenza e non ritenta dopo un 429", async () => {
    let active = 0;
    let max = 0;
    let calls = 0;
    const client = {
      async get(path) {
        calls += 1;
        active += 1;
        max = Math.max(max, active);
        await new Promise((resolve) => setTimeout(resolve, 15));
        active -= 1;
        if (path === "/ready") {
          const error = new Error("limited");
          error.response = { status: 429 };
          throw error;
        }
        if (path === "/dukascopy_status") return { status: 200, data: feedPayload };
        return { status: 200, data: { anything: true } };
      },
    };
    const result = await readLive(client, { generation: 4 });
    assert.equal(max <= MAX_CONCURRENCY, true);
    assert.equal(calls, MAX_CONCURRENCY);
    assert.equal(result.rows.filter((row) => row.http === 429).length >= 1, true);
    assert.equal(result.rows.some((row) => row.task !== "not_inferred"), false);
  });

  it("separa simulazione e live e non chiama POST", () => {
    const page = readFileSync(new URL("../pages/CommandFloorPage.jsx", import.meta.url), "utf8");
    const live = readFileSync(new URL("./live.js", import.meta.url), "utf8");
    const app = readFileSync(new URL("../App.js", import.meta.url), "utf8");
    assert.equal(page.includes("api.post"), false);
    assert.equal(page.includes("localStorage"), false);
    assert.equal(page.includes("useVisiblePolling"), true);
    assert.equal(live.includes(".post("), false);
    assert.equal(app.includes('path="/floor"'), true);
    assert.equal(app.includes('path="/research/control-plane"'), true);
    assert.equal(page.includes("SIMULATION"), true);
  });
});
