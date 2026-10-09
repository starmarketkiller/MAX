import { eventsAt, frameAt, stopIndex } from "./engine";
import { stationById, stationsByDepartment } from "./stations";
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

export function phaseOf(station, state, eventType) {
  if (!station || state === "queued" || state === "idle") return null;
  if (state === "failed" || state === "blocked") return "result";
  if (state === "waiting" && station.gate === "approval") return "approval";
  if (state === "waiting") return null;
  if (eventType === "start" && state === "running") return "event";
  if (state === "running" && (station.skills.includes("verify") || station.skills.includes("quality"))) return "check";
  if (state === "running") return "run";
  if (state === "completed") return "output";
  return null;
}

export function recordedOutput(state, output) {
  if (state === "running" || state === "completed") return { text: output, kind: "registry" };
  return { text: "Non prodotto in questo passo", kind: "absent" };
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
  const eventType = eventsAt(world, Math.max(0, beat)).find((item) => item.to === station?.id)?.type || null;
  const output = station ? recordedOutput(state, station.output) : { text: "Assente", kind: "absent" };
  const result = state === "failed" ? "Fallito. Non diventa un pass."
    : state === "blocked" ? "Bloccato. Nessuna azione reale."
      : state === "waiting" ? "In attesa di un permesso. Non è un'approvazione concessa."
        : state === "completed" ? "Passo chiuso dentro la simulazione."
          : state === "running" ? "Simulazione in corso. Nessun effetto esterno."
            : "Non dedotto.";
  return {
    phase: phaseOf(station, state, eventType),
    beat: Math.max(0, beat),
    index,
    stop,
    event: station ? station.input : world.lede,
    eventType,
    company: station ? station.departmentId : world.runs[0].label,
    companyPresence: "repository",
    plannedUnits: units.map((item) => ({ id: item.id, name: item.name, status: item.status })),
    task: station ? station.name : "Nessuna task",
    agent: worker ? worker.id : null,
    agentName: worker ? worker.name : "Nessun agente",
    dependencies: station ? station.dependencies : [],
    execution: state,
    output: output.text,
    outputKind: output.kind,
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
    const output = recordedOutput(item.state, station.output);
    rows.push({
      runId: item.runId,
      stationId: station.id,
      name: station.name,
      departmentId: station.departmentId,
      worker: station.worker,
      state: item.state,
      output: output.text,
      outputKind: output.kind,
      dependencies: station.dependencies,
    });
  }
  return rows;
}

export function departmentSnapshot(departmentId, frame) {
  return stationsByDepartment(departmentId).map((station) => {
    const state = frame.states.get(station.id) || "idle";
    const output = recordedOutput(state, station.output);
    return { id: station.id, name: station.name, state, dependencies: station.dependencies, output: output.text, outputKind: output.kind, presence: "repository" };
  }).filter((item) => item.state !== "idle");
}

export function workerLoad(frame) {
  const load = {};
  for (const row of assignments(frame)) load[row.worker] = (load[row.worker] || 0) + 1;
  return load;
}
