import { DEPARTMENTS } from "./stations";
import { WORKERS } from "./skills";
import { BUSINESS_UNITS } from "./graph";
import { assignments } from "./script";

export const COUNCIL = { id: "council", code: "C", name: "Council", lede: "Osserva e propone. Non adotta da solo." };

export function chooseLayout(width) {
  return width < 700 ? "phone" : "desktop";
}

export function centerFor(mode) {
  return mode === "phone" ? { x: 0, y: 0, k: 1 } : { x: 0, y: 0, k: 1 };
}

export function panBy(view, dx, dy) {
  return { ...view, x: view.x + dx, y: view.y + dy };
}

export function zoomBy(view, delta) {
  const k = Math.min(1.8, Math.max(0.7, Math.round((view.k + delta) * 100) / 100));
  return { ...view, k };
}

function column(items, x, y0, gap, extra) {
  return items.map((item, index) => ({ ...item, x, y: y0 + index * gap, ...extra }));
}

export function layout(mode = "desktop") {
  const rooms = [...DEPARTMENTS, COUNCIL];
  if (mode === "phone") {
    const departments = column(rooms, 200, 250, 86, { kind: "department", presence: "repository", labelSize: 20, radius: 38 });
    const agents = WORKERS.map((item, index) => ({
      ...item,
      kind: "agent",
      presence: "repository",
      labelSize: 18,
      x: index % 2 === 0 ? 110 : 290,
      y: 980 + Math.floor(index / 2) * 78,
    }));
    const units = BUSINESS_UNITS.map((item, index) => ({
      ...item,
      kind: "unit",
      presence: "planned",
      labelSize: 16,
      x: index % 2 === 0 ? 110 : 290,
      y: 48 + Math.floor(index / 2) * 64,
    }));
    return { departments, agents, units, width: 400, height: 1280, mode };
  }
  const departments = rooms.map((item, index) => ({ ...item, kind: "department", presence: "repository", labelSize: 22, radius: 48, x: 120 + index * 150, y: 250 }));
  const agents = WORKERS.map((item, index) => ({ ...item, kind: "agent", presence: "repository", labelSize: 18, x: 140 + index * 160, y: 520 }));
  const units = BUSINESS_UNITS.map((item, index) => ({ ...item, kind: "unit", presence: "planned", labelSize: 16, x: 160 + index * 260, y: 70 }));
  return { departments, agents, units, width: 1280, height: 680, mode };
}

export function assignmentLinks(frame, map) {
  const departments = Object.fromEntries(map.departments.map((item) => [item.id, item]));
  const agents = Object.fromEntries(map.agents.map((item) => [item.id, item]));
  return assignments(frame).flatMap((row) => {
    const from = departments[row.departmentId];
    const to = agents[row.worker];
    if (!from || !to) return [];
    return [{
      id: `${row.stationId}>${row.worker}`,
      stationId: row.stationId,
      departmentId: row.departmentId,
      worker: row.worker,
      state: row.state,
      x1: from.x,
      y1: from.y,
      x2: to.x,
      y2: to.y,
      animate: row.state === "running",
    }];
  });
}

export function allowMotion(reduced) {
  return reduced !== true;
}
