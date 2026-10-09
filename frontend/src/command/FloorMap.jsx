import { useEffect, useRef, useState } from "react";
import { layout, allowMotion } from "@/command/map";
import { stationsByDepartment } from "@/command/stations";
import { assignments, workerLoad } from "@/command/script";

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
  const map = layout();
  const [view, setView] = useState({ x: 20, y: 10, k: 0.92 });
  const [motion, setMotion] = useState(true);
  const drag = useRef(null);
  const load = workerLoad(frame);
  const active = assignments(frame);
  const focus = active[0] || null;

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setMotion(allowMotion(media.matches));
    apply();
    media.addEventListener?.("change", apply);
    return () => media.removeEventListener?.("change", apply);
  }, []);

  function pointerDown(event) {
    if (event.target.closest("[data-node]")) return;
    drag.current = { id: event.pointerId, x: event.clientX, y: event.clientY, ox: view.x, oy: view.y };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function pointerMove(event) {
    if (!drag.current || drag.current.id !== event.pointerId) return;
    setView((current) => ({ ...current, x: drag.current.ox + event.clientX - drag.current.x, y: drag.current.oy + event.clientY - drag.current.y }));
  }
  function pointerUp(event) {
    if (drag.current?.id === event.pointerId) drag.current = null;
  }

  const agentById = Object.fromEntries(map.agents.map((item) => [item.id, item]));
  const deptById = Object.fromEntries(map.departments.map((item) => [item.id, item]));
  const packet = focus && agentById[focus.worker] && deptById[focus.departmentId]
    ? { x1: deptById[focus.departmentId].x, y1: deptById[focus.departmentId].y, x2: agentById[focus.worker].x, y2: agentById[focus.worker].y }
    : null;

  return (
    <div data-testid="floor-map" className="relative overflow-hidden rounded-md border border-border bg-card">
      <div className="flex flex-wrap gap-2 border-b border-border p-2">
        <button type="button" className="min-h-11 rounded border border-border px-3 text-xs" onClick={() => setView((v) => ({ ...v, k: Math.min(1.8, v.k + 0.15) }))}>Zoom +</button>
        <button type="button" className="min-h-11 rounded border border-border px-3 text-xs" onClick={() => setView((v) => ({ ...v, k: Math.max(0.55, v.k - 0.15) }))}>Zoom −</button>
        <button type="button" className="min-h-11 rounded border border-border px-3 text-xs" onClick={() => setView({ x: 20, y: 10, k: 0.92 })}>Centra</button>
        <span className="self-center text-[11px] text-muted-foreground">Trascina lo sfondo. I pallini in alto sono previsti, non operativi.</span>
      </div>
      <svg viewBox={`0 0 ${map.width} ${map.height}`} className="h-[68vh] min-h-[420px] w-full touch-none" role="img" aria-label="Mappa dell'ecosistema" onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp}>
        <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
          {map.edges.map((edge) => {
            const hot = focus && (edge.from === focus.departmentId || edge.to === focus.departmentId);
            return <line key={edge.id} x1={edge.x1} y1={edge.y1} x2={edge.x2} y2={edge.y2} stroke={hot ? "hsl(var(--primary))" : "hsl(var(--border))"} strokeWidth={hot ? 2.5 : 1} />;
          })}
          {packet ? <line x1={packet.x1} y1={packet.y1} x2={packet.x2} y2={packet.y2} stroke="hsl(var(--primary))" strokeWidth="2" strokeDasharray="6 6" /> : null}
          {packet && motion ? (
            <circle r="6" fill="hsl(var(--primary))">
              <animateMotion dur="1.8s" repeatCount="indefinite" path={`M ${packet.x1} ${packet.y1} L ${packet.x2} ${packet.y2}`} />
            </circle>
          ) : null}
          {map.units.map((unit) => (
            <g key={unit.id} data-node="true" onClick={() => onSelect(`unit:${unit.id}`)} className="cursor-pointer">
              <rect x={unit.x - 96} y={unit.y - 22} width="192" height="44" rx="8" fill="none" stroke="hsl(var(--border))" strokeDasharray="4 4" />
              <text x={unit.x} y={unit.y + 4} textAnchor="middle" fontSize="11" fill="hsl(var(--muted-foreground))">{unit.name.split(" / ")[0]}</text>
            </g>
          ))}
          {map.departments.map((dept) => {
            const ids = stationsByDepartment(dept.id).map((item) => item.id);
            const state = worst(ids, frame.states);
            const chosen = selectedId === `dept:${dept.id}`;
            return (
              <g key={dept.id} data-node="true" data-testid={`node-${dept.id}`} onClick={() => onSelect(`dept:${dept.id}`)} className="cursor-pointer">
                <circle cx={dept.x} cy={dept.y} r={chosen ? 34 : 30} fill="hsl(var(--card))" stroke={STATE_COLOR[state]} strokeWidth={chosen ? 4 : 2.5} />
                <text x={dept.x} y={dept.y + 4} textAnchor="middle" fontSize="12" fill="hsl(var(--foreground))">{dept.name}</text>
              </g>
            );
          })}
          {map.agents.map((agent) => {
            const chosen = selectedId === `worker:${agent.id}`;
            const busy = load[agent.id] || 0;
            return (
              <g key={agent.id} data-node="true" data-testid={`node-worker-${agent.id}`} onClick={() => onSelect(`worker:${agent.id}`)} className="cursor-pointer">
                <rect x={agent.x - 52} y={agent.y - 22} width="104" height="44" rx="22" fill="hsl(var(--card))" stroke={busy ? "hsl(var(--primary))" : "hsl(var(--border))"} strokeWidth={chosen ? 3 : 1.5} />
                <text x={agent.x} y={agent.y + 4} textAnchor="middle" fontSize="11" fill="hsl(var(--foreground))">{agent.name.replace(" worker", "")} · {busy}</text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
