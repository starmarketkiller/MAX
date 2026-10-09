import { projectCapabilities } from "@/command/capabilities";

const CAPABILITY_LABEL = {
  PROCESS_OBSERVED: "processo osservato",
  FEED_OBSERVED: "feed osservato",
  IMPLEMENTED_UNVERIFIED: "implementata, non verificata",
  UNKNOWN: "sconosciuta",
};

export default function CapabilityMap({ live }) {
  const view = projectCapabilities(live?.rows || []);
  return (
    <section data-testid="capability-map" aria-label="Capacità reali" className="space-y-3">
      <h2 className="text-lg font-semibold">Capacità reali</h2>
      <p className="text-sm text-muted-foreground">{view.links.length} endpoint mappati. {view.simOnlyCount} postazioni restano solo nella simulazione. Nessuna task risulta in esecuzione.</p>
      <ul className="space-y-2">
        {view.links.map((link) => (
          <li key={link.stationId} data-testid={`cap-${link.stationId}`} className="border border-border p-3 text-sm">
            <details>
              <summary className="cursor-pointer">
                <span className="font-mono">{link.stationId}</span>
                <span className="text-muted-foreground"> · {CAPABILITY_LABEL[link.capability] || link.capability} · task nessuna</span>
              </summary>
              <dl className="mt-2 grid gap-1 text-xs text-muted-foreground sm:grid-cols-2">
                <div><dt className="inline">Endpoint </dt><dd className="inline font-mono">mappato GET {link.path}</dd></div>
                <div><dt className="inline">Capability </dt><dd className="inline font-mono">{link.capabilityId}</dd></div>
                <div><dt className="inline">Accesso </dt><dd className="inline font-mono">{link.access}</dd></div>
                <div><dt className="inline">Stato lettura </dt><dd className="inline font-mono">{link.state}</dd></div>
                <div><dt className="inline">Processo </dt><dd className="inline font-mono">{link.process === "OBSERVED" ? "osservato" : "non osservato"}</dd></div>
                <div><dt className="inline">Task </dt><dd className="inline font-mono">nessuna</dd></div>
                <div><dt className="inline">Osservato </dt><dd className="inline font-mono">{link.observedAt || "assente"}</dd></div>
                {link.queueLiveness ? <div><dt className="inline">Vitalità coda </dt><dd className="inline font-mono">{link.queueLiveness === "observed-on" ? "osservata accesa" : "osservata spenta"}</dd></div> : null}
              </dl>
              {link.note ? <p className="mt-2 text-xs text-muted-foreground">{link.note}</p> : null}
            </details>
          </li>
        ))}
      </ul>
    </section>
  );
}
