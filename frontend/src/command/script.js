import { frameAt, stopIndex } from "./engine";
import { stationById } from "./stations";
import { workerById } from "./skills";
import { BUSINESS_UNITS } from "./graph";

export const PHASES = [
  { id: "event", label: "Evento" },
  { id: "company", label: "Azienda" },
  { id: "task", label: "Task" },
  { id: "agent", label: "Agente" },
  { id: "deps", label: "Dipendenze" },
  { id: "run", label: "Esecuzione" },
  { id: "output", label: "Output" },
  { id: "check", label: "Validazione" },
  { id: "approval", label: "Approvazione" },
  { id: "result", label: "Risultato" },
];

export function phaseOf(station, index) {
  if (!station) return "event";
  if (station.gate === "nogo") return "result";
  if (station.gate === "approval") return "approval";
  if (station.skills.includes("verify") || station.skills.includes("quality")) return "check";
  if (index === 0) return "event";
  if (index === 1) return "company";
  if (index === 2) return "task";
  return "run";
}

export function scriptAt(world, beat) {
  const frame = frameAt(world, beat);
  const focus = frame.active[0] || null;
  const station = focus ? stationById(focus.stationId) : null;
  const run = focus ? world.runs.find((item) => item.id === focus.runId) : world.runs[0];
  const index = station && run ? Math.max(0, run.stationIds.indexOf(station.id)) : 0;
  const stop = run ? stopIndex(run.stationIds, run.failAt) : 0;
  const worker = station ? workerById(station.worker) : null;
  const units = station ? BUSINESS_UNITS.filter((item) => item.departments.includes(station.departmentId)) : [];
  const state = focus ? focus.state : "idle";
  const result = state === "failed" ? "Fallito. Non diventa un pass."
    : state === "blocked" ? "Bloccato. Nessuna azione reale."
      : state === "waiting" ? "In attesa di un permesso."
        : state === "completed" ? "Passo chiuso dentro la simulazione."
          : "Simulazione in corso. Nessun effetto esterno.";
  return {
    phase: phaseOf(station, index),
    beat: Math.max(0, beat),
    stop,
    event: station ? station.input : world.lede,
    company: station ? station.departmentId : world.runs[0].label,
    companyPresence: "repository",
    plannedUnits: units.map((item) => ({ id: item.id, name: item.name, status: item.status })),
    task: station ? station.name : "Nessuna task",
    agent: worker ? worker.id : null,
    agentName: worker ? worker.name : "Nessun agente",
    dependencies: station ? station.dependencies : [],
    execution: state,
    output: station ? station.output : "Assente",
    validation: station ? station.verifier : "registry",
    approval: station ? station.gate : "none",
    result,
    stationId: station ? station.id : null,
    runId: focus ? focus.runId : null,
  };
}

export function assignments(frame) {
  const rows = [];
  for (const item of frame.active) {
    const station = stationById(item.stationId);
    if (!station) continue;
    rows.push({
      runId: item.runId,
      stationId: station.id,
      name: station.name,
      departmentId: station.departmentId,
      worker: station.worker,
      state: item.state,
      output: station.output,
      dependencies: station.dependencies,
    });
  }
  return rows;
}

export function workerLoad(frame) {
  const load = {};
  for (const row of assignments(frame)) load[row.worker] = (load[row.worker] || 0) + 1;
  return load;
}
