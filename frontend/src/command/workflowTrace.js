const REAL = new Set(["DETERMINISTIC", "AGENCY_SKILL"]);
const VISIBLE = new Set(["RECORDED", "WAITING_APPROVAL"]);

export function observedStations(trace) {
  if (!trace || trace.source !== "ledger" || !Array.isArray(trace.steps)) return [];
  const seen = new Set();
  const stations = [];
  for (const step of trace.steps) {
    if (!step || typeof step.station_id !== "string") continue;
    if (!REAL.has(step.provenance) || !VISIBLE.has(step.state)) continue;
    if (seen.has(step.station_id)) continue;
    seen.add(step.station_id);
    stations.push({
      stationId: step.station_id,
      stepId: typeof step.step_id === "string" ? step.step_id : "",
      state: step.state,
      provenance: step.provenance,
      outputRef: typeof step.output_ref === "string" ? step.output_ref.slice(0, 80) : "",
    });
  }
  return stations;
}
