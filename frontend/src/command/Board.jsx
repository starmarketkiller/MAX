import { useEffect, useRef, useState } from "react";
import { DEPARTMENTS, stationById, stationsByDepartment } from "@/command/stations";
import "@/command/floor.css";

const ROOM_W = 340;
const CELL_H = 44;
const HEADER = 32;
const GAP_X = 20;
const GAP_Y = 36;
const MARGIN = 12;
const ROWS = [["jarvis"], ["trading", "systems", "finance"], ["social", "revenue", "fashion"]];
const STRUCTURAL = [
  ["jarvis", "trading"], ["jarvis", "systems"], ["jarvis", "finance"], ["jarvis", "social"],
  ["jarvis", "revenue"], ["jarvis", "fashion"], ["trading", "finance"], ["revenue", "finance"],
  ["revenue", "social"], ["fashion", "social"], ["systems", "finance"],
];
export const SPRITES = ["scout", "news", "sentiment", "charts", "risk", "decision"].map((name) => `${process.env.PUBLIC_URL || ""}/bots/${name}.jpg`);

const STATE_LABEL = { idle: "IDLE", queued: "CODA", running: "CORRE", waiting: "ATTESA", blocked: "BLOCCO", completed: "FATTO", failed: "FAIL" };

function roomHeight(count) {
  return HEADER + Math.ceil(count / 3) * CELL_H;
}
function rank(state) {
  return { idle: 0, completed: 1, queued: 2, failed: 3, running: 4, waiting: 5, blocked: 6 }[state];
}
function chipClass(state, on) {
  if (on) return "is-on";
  if (state === "running") return "is-run";
  if (state === "blocked" || state === "failed") return "is-bad";
  if (state === "waiting") return "is-wait";
  if (state === "completed") return "is-done";
  return "";
}
function roomClass(tone) {
  if (tone === "blocked" || tone === "failed") return "is-bad";
  if (tone === "waiting") return "is-wait";
  if (tone === "running") return "is-run";
  return "";
}

export default function Board({ states, pulses, hops, selectedId, reduceMotion, onSelect }) {
  const frame = useRef(null);
  const [fit, setFit] = useState(1);
  const [zoom, setZoom] = useState("fit");
  const rowWidths = ROWS.map((row) => MARGIN * 2 + row.length * ROOM_W + (row.length - 1) * GAP_X);
  const canvasW = Math.max(...rowWidths);
  const boxes = {};
  let y = MARGIN;
  for (const row of ROWS) {
    const height = Math.max(...row.map((id) => roomHeight(stationsByDepartment(id).length)));
    const rowW = MARGIN * 2 + row.length * ROOM_W + (row.length - 1) * GAP_X;
    const offset = (canvasW - rowW) / 2 + MARGIN;
    row.forEach((id, index) => {
      boxes[id] = { x: offset + index * (ROOM_W + GAP_X), y, h: roomHeight(stationsByDepartment(id).length) };
    });
    y += height + GAP_Y;
  }
  const canvasH = y;
  const scale = zoom === "fit" ? fit : zoom;

  useEffect(() => {
    const el = frame.current;
    if (!el) return undefined;
    const measure = () => {
      const width = el.clientWidth / canvasW;
      const height = Math.max(220, window.innerHeight - 460) / canvasH;
      setFit(Math.min(1, width, height));
    };
    measure();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(measure);
    observer?.observe(el);
    window.addEventListener("resize", measure);
    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [canvasW, canvasH]);

  const center = (stationId) => {
    const station = stationById(stationId);
    if (!station) return null;
    const box = boxes[station.departmentId];
    if (!box) return null;
    const col = station.index % 3;
    const row = Math.floor(station.index / 3);
    const cellW = ROOM_W / 3;
    return { x: box.x + col * cellW + cellW / 2, y: box.y + HEADER + row * CELL_H + CELL_H / 2 };
  };

  return (
    <div className="nx-floor border" data-testid="nexus-board">
      <div className="flex items-center justify-between gap-2 border-b px-3 py-2 nx-line">
        <p className="nx-display text-sm nx-phosphor">SALE E GATE</p>
        <div className="flex gap-2">
          <button type="button" className="nx-btn text-sm" onClick={() => setZoom((value) => Math.max(0.35, (value === "fit" ? fit : value) - 0.15))}>−</button>
          <button type="button" className="nx-btn text-sm" onClick={() => setZoom("fit")}>Tutto</button>
          <button type="button" className="nx-btn text-sm" onClick={() => setZoom((value) => Math.min(1.6, (value === "fit" ? fit : value) + 0.15))}>+</button>
        </div>
      </div>
      <div ref={frame} className="overflow-auto">
        <div className="mx-auto" style={{ width: canvasW * scale, height: canvasH * scale }}>
          <div className="relative" style={{ width: canvasW, height: canvasH, transform: `scale(${scale})`, transformOrigin: "top left" }}>
            <svg className="absolute inset-0" width={canvasW} height={canvasH} aria-hidden="true">
              {STRUCTURAL.map(([a, b]) => {
                const left = boxes[a];
                const right = boxes[b];
                return <line key={`${a}-${b}`} x1={left.x + ROOM_W / 2} y1={left.y + left.h / 2} x2={right.x + ROOM_W / 2} y2={right.y + right.h / 2} stroke="#243246" strokeWidth="1.5" />;
              })}
              {hops.map((hop) => {
                const from = center(hop.from);
                const to = center(hop.to);
                if (!from || !to) return null;
                return <line key={`${hop.from}-${hop.to}`} data-testid="nx-hop" x1={from.x} y1={from.y} x2={to.x} y2={to.y} className={reduceMotion ? undefined : "nx-flow"} stroke="#3dff8a" strokeWidth="2.5" />;
              })}
            </svg>
            {pulses.map((pulse) => {
              const point = center(pulse.id);
              if (!point) return null;
              const tone = pulse.state === "blocked" || pulse.state === "failed" ? "#ff5d73" : pulse.state === "waiting" ? "#ffb020" : "#3dff8a";
              return <span key={pulse.id} data-testid={`pulse-${pulse.id}`} className="nx-orb pointer-events-none absolute z-30 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full" style={{ left: point.x, top: point.y, background: tone }} />;
            })}
            {DEPARTMENTS.map((dept) => {
              const box = boxes[dept.id];
              const stations = stationsByDepartment(dept.id).map((station) => ({ station, state: states.get(station.id) || "idle" }));
              const tone = stations.reduce((best, item) => (rank(item.state) > rank(best) ? item.state : best), "idle");
              return (
                <section key={dept.id} className={"nx-room absolute overflow-hidden border " + roomClass(tone)} style={{ left: box.x, top: box.y, width: ROOM_W, height: box.h }}>
                  <header className="flex h-8 items-center justify-between border-b px-2 nx-line">
                    <h2 className="nx-display text-sm">{dept.name}</h2>
                    <span className="text-xs">{STATE_LABEL[tone]}</span>
                  </header>
                  {stations.map(({ station, state }) => {
                    const col = station.index % 3;
                    const row = Math.floor(station.index / 3);
                    const cellW = ROOM_W / 3;
                    return (
                      <button
                        key={station.id}
                        type="button"
                        data-testid={`station-${station.id}`}
                        onClick={() => onSelect(station.id)}
                        aria-pressed={station.id === selectedId}
                        className={"nx-chip absolute flex items-center gap-1 border px-1 text-left text-xs " + chipClass(state, station.id === selectedId)}
                        style={{ left: col * cellW + 3, top: HEADER + row * CELL_H + 3, width: cellW - 6, height: CELL_H - 6 }}
                      >
                        <img src={SPRITES[station.index % SPRITES.length]} alt="" className="h-4 w-4 shrink-0 object-cover object-top" />
                        <span className="nx-display min-w-0 truncate">{station.code}</span>
                      </button>
                    );
                  })}
                </section>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
