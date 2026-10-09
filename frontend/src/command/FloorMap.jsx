import { useEffect, useRef, useState } from "react";
import { allowMotion, assignmentLinks, centerFor, chooseLayout, layout, panBy, zoomBy } from "@/command/map";
import { stationsByDepartment } from "@/command/stations";
import { workerLoad } from "@/command/script";

const STATE_COLOR = {
  idle: "hsl(var(--muted-foreground))",
  queued: "hsl(var(--muted-foreground))",
  running: "hsl(var(--primary))",
  waiting: "#d97706",
  blocked: "#dc2626",
  completed: "#059669",
  failed: "#dc2626",
};

function worst(ids, states) {
  const order = ["idle", "completed", "queued", "failed", "running", "waiting", "blocked"];
  let best = "idle";
  ids.forEach((id) => {
    const state = states.get(id) || "idle";
    if (order.indexOf(state) > order.indexOf(best)) best = state;
  });
  return best;
}

export default function FloorMap({ frame, selectedId, onSelect }) {
  const [mode, setMode] = useState("desktop");
  const [view, setView] = useState(centerFor("desktop"));
  const [motion, setMotion] = useState(true);
  const drag = useRef(null);
  const map = layout(mode);
  const load = workerLoad(frame);
  const links = assignmentLinks(frame, map);

  useEffect(() => {
    const motionMedia = window.matchMedia("(prefers-reduced-motion: reduce)");
    const phoneMedia = window.matchMedia("(max-width: 700px)");
    const apply = () => {
      setMotion(allowMotion(motionMedia.matches));
      const next = chooseLayout(phoneMedia.matches ? 390 : 1100);
      setMode(next);
      setView(centerFor(next));
    };
    apply();
    motionMedia.addEventListener?.("change", apply);
    phoneMedia.addEventListener?.("change", apply);
    return () => {
      motionMedia.removeEventListener?.("change", apply);
      phoneMedia.removeEventListener?.("change", apply);
    };
  }, []);

  function pointerDown(event) {
    if (event.target.closest("[data-node]")) return;
    drag.current = { id: event.pointerId, x: event.clientX, y: event.clientY, ox: view.x, oy: view.y };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function pointerMove(event) {
    if (!drag.current || drag.current.id !== event.pointerId) return;
    setView(panBy(view, event.clientX - drag.current.x, event.clientY - drag.current.y));
  }
  function pointerUp(event) {
    if (drag.current?.id === event.pointerId) drag.current = null;
  }
  function select(id, event) {
    event.stopPropagation();
    onSelect(id);
  }

  return (
    <div data-testid="floor-map" className="relative overflow-hidden rounded-md border border-border bg-card">
      <div className="flex flex-wrap gap-2 border-b border-border p-2">
        <button type="button" className="min-h-11 rounded border border-border px-3 text-sm" onClick={() => setView((current) => zoomBy(current, 0.15))}>Zoom +</button>
        <button type="button" className="min-h-11 rounded border border-border px-3 text-sm" onClick={() => setView((current) => zoomBy(current, -0.15))}>Zoom −</button>
        <button type="button" className="min-h-11 rounded border border-border px-3 text-sm" onClick={() => setView(centerFor(mode))}>Centra</button>
        <span className="self-center text-xs text-muted-foreground">Trascina solo lo sfondo. Il dito sulla mappa non scorre la pagina.</span>
      </div>
      <svg data-testid="floor-surface" viewBox={`0 0 ${map.width} ${map.height}`} className="h-[62vh] min-h-[360px] w-full touch-none" role="img" aria-label="Mappa dell'ecosistema" onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp}>
        <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
          {links.map((link) => <line key={link.id} x1={link.x1} y1={link.y1} x2={link.x2} y2={link.y2} stroke="hsl(var(--primary))" strokeWidth="3" />)}
          {links.filter((link) => link.animate && motion).map((link) => (
            <circle key={`${link.id}-motion`} r="7" fill="hsl(var(--primary))">
              <animateMotion dur="1.8s" repeatCount="indefinite" path={`M ${link.x1} ${link.y1} L ${link.x2} ${link.y2}`} />
            </circle>
          ))}
          {map.units.map((unit) => (
            <g key={unit.id} data-node="true" data-testid={`node-unit-${unit.id}`} onPointerUp={(event) => select(`unit:${unit.id}`, event)}>
              <rect x={unit.x - 88} y={unit.y - 24} width="176" height="48" rx="8" fill="hsl(var(--card))" stroke="hsl(var(--border))" strokeDasharray="4 4" />
              <text x={unit.x} y={unit.y + 5} textAnchor="middle" fontSize={unit.labelSize} fill="hsl(var(--muted-foreground))">{unit.name.split(" / ")[0]}</text>
            </g>
          ))}
          {map.departments.map((dept) => {
            const ids = stationsByDepartment(dept.id).map((item) => item.id);
            const state = worst(ids, frame.states);
            const chosen = selectedId === `dept:${dept.id}`;
            return (
              <g key={dept.id} data-node="true" data-testid={`node-${dept.id}`} onPointerUp={(event) => select(`dept:${dept.id}`, event)}>
                <circle cx={dept.x} cy={dept.y} r={chosen ? dept.radius + 4 : dept.radius} fill="hsl(var(--card))" stroke={STATE_COLOR[state]} strokeWidth={chosen ? 5 : 3} />
                <text x={dept.x} y={dept.y + 6} textAnchor="middle" fontSize={dept.labelSize} fill="hsl(var(--foreground))">{dept.name}</text>
              </g>
            );
          })}
          {map.agents.map((agent) => {
            const chosen = selectedId === `worker:${agent.id}`;
            const busy = load[agent.id] || 0;
            return (
              <g key={agent.id} data-node="true" data-testid={`node-worker-${agent.id}`} onPointerUp={(event) => select(`worker:${agent.id}`, event)}>
                <rect x={agent.x - 70} y={agent.y - 26} width="140" height="52" rx="26" fill="hsl(var(--card))" stroke={busy ? "hsl(var(--primary))" : "hsl(var(--border))"} strokeWidth={chosen ? 4 : 2} />
                <text x={agent.x} y={agent.y + 6} textAnchor="middle" fontSize={agent.labelSize} fill="hsl(var(--foreground))">{agent.name.replace(" worker", "")} · {busy}</text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
