import { stationById } from "@/command/stations";
import { observedStations } from "@/command/workflowTrace";

export default function ObservedPath({ trace }) {
  const stations = observedStations(trace);
  const note = trace?.status === "AUTH_REQUIRED"
    ? "Sessione richiesta. Nessuna postazione accesa."
    : trace?.status === "UNAVAILABLE"
      ? "Traccia non disponibile. Nessuna postazione accesa."
      : stations.length
        ? "Solo passi letti dal ledger. Le altre postazioni non risultano eseguite."
        : "Nessun percorso osservato. La simulazione non è esecuzione.";
  return (
    <section aria-label="Percorso osservato" data-testid="observed-path" className="mt-4 border border-border p-3">
      <h2 className="text-sm font-semibold">Percorso osservato</h2>
      <p className="mt-1 text-sm text-muted-foreground">{note}</p>
      {stations.length > 0 && (
        <ol className="mt-3 space-y-2">
          {stations.map((station) => {
            const known = stationById(station.stationId);
            return (
              <li key={station.stationId} data-testid={`observed-${station.stationId}`} className="font-mono text-xs">
                {station.stationId} {known ? known.name : "stazione non registrata"} · {station.state} · {station.provenance}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
