import { DEPARTMENTS } from "./stations";
import { WORKERS } from "./skills";
import { BUSINESS_UNITS, FLOWS } from "./graph";

export const COUNCIL = { id: "council", code: "C", name: "Council", lede: "Osserva e propone. Non adotta da solo." };

function place(items, y, x0, gap) {
  return items.map((item, index) => ({ ...item, x: x0 + index * gap, y }));
}

export function layout() {
  const departments = place([...DEPARTMENTS, COUNCIL], 230, 90, 128).map((item) => ({ ...item, kind: "department", presence: "repository" }));
  const agents = place(WORKERS, 520, 90, 146).map((item) => ({ ...item, kind: "agent", presence: "repository" }));
  const units = place(BUSINESS_UNITS, 62, 90, 250).map((item) => ({ ...item, kind: "unit", presence: "planned" }));
  const byId = Object.fromEntries(departments.map((item) => [item.id, item]));
  const seen = new Set();
  const edges = [];
  for (const flow of FLOWS) {
    const from = byId[flow.from];
    const to = byId[flow.to];
    if (!from || !to) continue;
    const key = [flow.from, flow.to].sort().join(":");
    if (seen.has(key)) continue;
    seen.add(key);
    edges.push({ id: key, from: flow.from, to: flow.to, packet: flow.packet, x1: from.x, y1: from.y, x2: to.x, y2: to.y });
  }
  return { departments, agents, units, edges, width: 1100, height: 640 };
}

export function allowMotion(reduced) {
  return reduced !== true;
}
