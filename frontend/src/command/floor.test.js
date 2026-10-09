const { readFileSync } = require("fs");
const path = require("path");
const { AUTOMATIONS } = require("./graph");
const { classifyResponse, isCurrent, LIVE_READS, MAX_CONCURRENCY, readLive } = require("./live");
const { MARKER_REACHED, REVIEW_MARKER } = require("./marker");
const { DEPARTMENTS, STATIONS, WORKFLOWS, stationById } = require("./stations");
const { SKILLS, WORKERS } = require("./skills");
const { layout, allowMotion, assignmentLinks, chooseLayout, panBy, zoomBy } = require("./map");
const { scriptAt, workerLoad, PHASES, departmentSnapshot, phaseOf } = require("./script");
const { diagnose, safeFacts } = require("./diagnostics");
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
    expect(page.includes('useState("board")')).toBe(true);
    expect(page.includes("NEXUS")).toBe(true);
    expect(page.includes("FLOOR")).toBe(true);
    expect(source("./FloorMap.jsx").includes("touch-none")).toBe(true);
    expect(source("./live.js").includes("frameAt")).toBe(false);
    expect(source("./live.js").includes("scriptAt")).toBe(false);
    const sim = page.slice(page.indexOf("function SimPane"), page.indexOf("function Detail"));
    expect(sim.includes("LiveDiagnostics")).toBe(false);
    expect(sim.includes("live-diagnostics")).toBe(false);
    expect(page.includes("data-testid=\"live-diagnostics\"") || source("./LiveDiagnostics.jsx").includes("live-diagnostics")).toBe(true);
    expect(source("./diagnostics.js").includes(".post(")).toBe(false);
    expect(source("./engine.js").includes("diagnose")).toBe(false);
  });

  test("la diagnostica non promuove il ready e non tratta il 401 come blocco", () => {
    const ready = diagnose({
      path: "/ready",
      name: "Monitoring",
      http: 200,
      at: "2026-10-09T15:15:54.007332+00:00",
      origin: "/ready",
      schema: "valid",
      api: "available",
      facts: safeFacts("/ready", { ...readyPayload, version: "5.4.0", ts: "2026-10-09T15:15:54.007332+00:00", checks: { ...readyPayload.checks, database: { ok: true, path: "/data/nexus.db", token: "secret" }, queue_dispatcher: { running: true } } }),
    });
    expect(ready.state).toBe("PROCESS_OBSERVED");
    expect(ready.stationsReady).toBe(false);
    expect(ready.stationsRunning).toBe(false);
    expect(ready.stationEffect).toBe("none");
    expect(ready.observedAt).toBe("2026-10-09T15:15:54.007332+00:00");
    expect(ready.reportedAt).toBe("2026-10-09T15:15:54.007332+00:00");
    expect(ready.source).toBe("/ready");
    expect(JSON.stringify(ready.facts)).not.toMatch(/nexus\.db|token|secret/);
    const denied = diagnose({ path: "/company/overview", name: "Company", http: 401, at: "T1", origin: "/company/overview", api: "unauthorized", facts: { revenue: 10 } });
    expect(denied.access).toBe("AUTH_REQUIRED");
    expect(denied.state).toBe("UNKNOWN");
    expect(denied.facts).toBe(null);
    expect(`${denied.state} ${denied.access}`).not.toContain("BLOCKED");
    expect(diagnose({ path: "/jarvis/activity", http: 0, at: "T2", origin: "/jarvis/activity", api: "offline", error: "offline" }).state).toBe("UNKNOWN");
    expect(diagnose({ path: "/jarvis/dispatcher/status", http: 503, at: "T3", origin: "/jarvis/dispatcher/status", api: "offline" }).reason).toBe("Endpoint non disponibile.");
    const feed = diagnose({ path: "/dukascopy_status", http: 200, at: "OBS", origin: "/dukascopy_status", schema: "valid", facts: safeFacts("/dukascopy_status", { ...feedPayload, progress: { days_done: 12, newest_day_covered: "2026-10-09" } }) });
    expect(feed.state).toBe("FEED_OBSERVED");
    expect(feed.source).toBe("/dukascopy_status");
    expect(feed.observedAt).toBe("OBS");
    expect(feed.reportedAt).toBe("2026-10-09");
    expect(feed.stationsRunning).toBe(false);
    expect(diagnose({ path: "/jarvis/executive-state", http: 200, at: "T4", origin: "/jarvis/executive-state", schema: "unverified", facts: { secret: "no" } }).facts).toBe(null);
  });

  test("una risposta vuota non è IDLE", () => {
    for (const requestPath of ["/ready", "/dukascopy_status", "/company/overview"]) {
      const card = diagnose({ path: requestPath, http: 200, at: "T", origin: requestPath, schema: "empty", api: "available", facts: null });
      expect(card.state).toBe("UNKNOWN");
      expect(card.access).toBe("EMPTY_RESPONSE");
      expect(card.state).not.toBe("IDLE");
    }
  });

  test("la mappa riusa i registri e il copione è riproducibile", () => {
    const map = layout();
    const phone = layout("phone");
    expect(chooseLayout(390)).toBe("phone");
    expect(phone.width).toBe(400);
    expect(phone.departments.every((item) => item.labelSize >= 18)).toBe(true);
    expect(map.departments).toHaveLength(8);
    expect(map.agents).toHaveLength(7);
    expect(new Set(map.agents.map((item) => item.id)).size).toBe(7);
    expect(map.units.every((item) => item.presence === "planned")).toBe(true);
    expect(map.departments.every((item) => item.presence === "repository")).toBe(true);
    const first = scriptAt(worldById("trading"), 0);
    expect(scriptAt(worldById("trading"), 0)).toEqual(first);
    expect(first.task).toBe("Market Data");
    expect(first.agent).toBe("data");
    expect(first.phase).toBe("event");
    expect(first.phase).not.toBe("company");
    expect(first.outputKind).toBe("registry");
    expect(PHASES).toHaveLength(10);
    const gate = scriptAt(worldById("trading"), 999);
    expect(gate.execution).toBe("waiting");
    expect(gate.approval).toBe("approval");
    expect(gate.phase).toBe("approval");
    expect(gate.outputKind).toBe("absent");
    expect(gate.result).toMatch(/attesa/i);
    expect(phaseOf({ gate: "none", skills: [] }, "queued", null)).toBeNull();
    const fault = scriptAt(worldById("fault"), 999);
    expect(fault.execution).toBe("failed");
    expect(fault.phase).toBe("result");
    const frame = frameAt(worldById("ecosystem"), 1);
    const load = workerLoad(frame);
    const busy = Object.values(load).reduce((sum, count) => sum + count, 0);
    expect(busy).toBe(frame.active.length);
    const links = assignmentLinks(frameAt(worldById("trading"), 0), phone);
    expect(links.map((item) => item.stationId)).toEqual(["trading.data"]);
    expect(links[0].animate).toBe(true);
    expect(assignmentLinks(frameAt(worldById("trading"), 999), phone).every((item) => item.animate === false)).toBe(true);
    const rows = departmentSnapshot("trading", frameAt(worldById("trading"), 0));
    expect(rows.some((item) => item.dependencies.includes("trading.data"))).toBe(true);
    expect(rows.every((item) => item.presence === "repository")).toBe(true);
    expect(panBy({ x: 1, y: 2, k: 1 }, 4, 5)).toEqual({ x: 5, y: 7, k: 1 });
    expect(zoomBy({ x: 0, y: 0, k: 1 }, 2).k).toBe(1.8);
    expect(allowMotion(true)).toBe(false);
    expect(allowMotion(false)).toBe(true);
  });

  test("un tocco sul nodo seleziona il reparto", () => {
    global.IS_REACT_ACT_ENVIRONMENT = true;
    window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
    const React = require("react");
    const { createRoot } = require("react-dom/client");
    const FloorMap = require("./FloorMap").default;
    const selected = [];
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    React.act(() => {
      root.render(React.createElement(FloorMap, { frame: frameAt(worldById("trading"), 0), selectedId: "", onSelect: (id) => selected.push(id) }));
    });
    const node = container.querySelector("[data-testid='node-trading']");
    expect(node).not.toBeNull();
    React.act(() => {
      node.dispatchEvent(new MouseEvent("pointerup", { bubbles: true }));
    });
    expect(selected).toEqual(["dept:trading"]);
    expect(container.querySelector("[data-testid='floor-surface']").getAttribute("class")).toContain("touch-none");
    React.act(() => root.unmount());
    container.remove();
  });

  test("la board della preview rende ogni postazione e solo i salti reali", () => {
    global.IS_REACT_ACT_ENVIRONMENT = true;
    const React = require("react");
    const { createRoot } = require("react-dom/client");
    const Board = require("./Board").default;
    const { SPRITES } = require("./Board");
    const world = worldById("trading");
    const frame = frameAt(world, 1);
    const hops = eventsAt(world, 1).flatMap((event) => (event.from ? [{ from: event.from, to: event.to }] : []));
    expect(SPRITES).toHaveLength(6);
    expect(hops.length).toBeGreaterThan(0);
    const selected = [];
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);
    React.act(() => {
      root.render(React.createElement(Board, {
        states: frame.states,
        pulses: frame.active.map((item) => ({ id: item.stationId, state: item.state })),
        hops,
        selectedId: "trading.data",
        reduceMotion: true,
        onSelect: (id) => selected.push(id),
      }));
    });
    const shown = container.querySelectorAll("[data-testid^='station-']");
    expect(shown.length).toBe(STATIONS.filter((item) => item.departmentId !== "council").length);
    React.act(() => {
      container.querySelector("[data-testid='station-trading.news']").dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    expect(selected).toEqual(["trading.news"]);
    expect(container.querySelectorAll("[data-testid='nx-hop']").length).toBe(hops.length);
    expect(container.querySelector("img").getAttribute("src")).toContain("/bots/scout.jpg");
    React.act(() => root.unmount());
    container.remove();
  });
});
