import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { AUTOMATIONS } from "./graph.js";
import { classifyResponse, LIVE_READS } from "./live.js";
import { MARKER_REACHED } from "./marker.js";
import { DEPARTMENTS, STATIONS, WORKFLOWS } from "./stations.js";
import { SKILLS, WORKERS } from "./skills.js";
import { frameAt, worldById } from "./engine.js";

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

  it("non promuove una fixture e non deduce una task da un 200", () => {
    const fixture = classifyResponse({ http: 200, empty: false, source: "fixture" });
    assert.equal(fixture.live, false);
    assert.equal(fixture.task, "not_inferred");
    assert.equal(classifyResponse({ http: 401, empty: true, source: "network" }).status, "LIVE_UNAVAILABLE");
    assert.equal(classifyResponse({ http: 403, empty: true, source: "network" }).status, "LIVE_UNAVAILABLE");
    assert.equal(classifyResponse({ http: 0, empty: true, source: "network" }).status, "LIVE_UNAVAILABLE");
    assert.equal(classifyResponse({ http: 503, empty: true, source: "network" }).status, "LIVE_UNAVAILABLE");
    assert.equal(classifyResponse({ http: 404, empty: true, source: "network" }).status, "PLANNED");
    assert.equal(classifyResponse({ http: 200, empty: true, source: "network" }).status, "LIVE_IDLE");
    assert.equal(LIVE_READS.every((item) => item.path.startsWith("/")), true);
    assert.equal(MARKER_REACHED, false);
  });

  it("tiene la simulazione ferma ai gate e non chiama POST", () => {
    const frame = frameAt(worldById("ecosystem"), 0);
    assert.equal(frame.active.length > 0, true);
    const page = readFileSync(new URL("../pages/CommandFloorPage.jsx", import.meta.url), "utf8");
    const live = readFileSync(new URL("./live.js", import.meta.url), "utf8");
    assert.equal(page.includes("api.post"), false);
    assert.equal(page.includes("localStorage"), false);
    assert.equal(live.includes(".post("), false);
  });
});
