import { diagnose } from "@/command/diagnostics";

const FACT_LABEL = {
  version: "Versione",
  reportedAt: "Timestamp del backend",
  databaseOk: "Database",
  databaseWritable: "Database scrivibile",
  migrationsOk: "Migrazioni",
  migrationsApplied: "Migrazioni applicate",
  securityOk: "Sicurezza",
  environment: "Ambiente",
  strategyCount: "Strategie nel contratto",
  queueRunning: "Coda accesa",
  queueEnabled: "Coda abilitata",
  queueConcurrency: "Concorrenza",
  workerAvailable: "Worker nell'immagine",
  started: "Feed partito",
  daysDone: "Giorni letti",
  daysTotal: "Giorni attesi",
  daysWithData: "Giorni con dati",
  newestDay: "Ultimo giorno coperto",
  oldestDay: "Primo giorno coperto",
  readyForIntraday: "Pronto per il reconfirm",
};

function factText(value) {
  if (value === true) return "sì";
  if (value === false) return "no";
  return String(value);
}

export default function LiveDiagnostics({ live }) {
  const cards = (live?.rows ?? []).map(diagnose);
  return (
    <section data-testid="live-diagnostics" aria-label="Diagnostica LIVE" className="space-y-3">
      <h2 className="text-lg font-semibold">Diagnostica LIVE</h2>
      <p className="text-sm text-muted-foreground">Solo letture GET già esistenti. Un processo osservato non accende le 119 postazioni. Qui non entra la simulazione.</p>
      {cards.length === 0 ? <p className="text-sm text-muted-foreground">Nessuna lettura ancora.</p> : null}
      <ul className="space-y-2">
        {cards.map((card) => (
          <li key={card.path} data-testid={`diag-${card.path}`} className="border border-border p-3 text-sm">
            <div className="font-mono text-[11px]">{card.state} · {card.access}</div>
            <div className="mt-1">{card.name}</div>
            <p className="mt-1 text-xs text-muted-foreground">{card.reason}</p>
            <dl className="mt-2 grid gap-1 text-xs text-muted-foreground sm:grid-cols-2">
              <div><dt className="inline">Fonte </dt><dd className="inline font-mono">GET {card.source}</dd></div>
              <div><dt className="inline">Osservato </dt><dd className="inline font-mono">{card.observedAt || "assente"}</dd></div>
              <div><dt className="inline">Aggiornamento noto </dt><dd className="inline font-mono">{card.reportedAt || "assente"}</dd></div>
              <div><dt className="inline">Postazioni </dt><dd className="inline">non dedotte</dd></div>
            </dl>
            {card.facts ? (
              <dl className="mt-2 grid gap-1 text-xs sm:grid-cols-2">
                {Object.entries(card.facts).filter(([, value]) => value !== null && value !== undefined).map(([key, value]) => (
                  <div key={key}><dt className="inline text-muted-foreground">{FACT_LABEL[key] || key} </dt><dd className="inline font-mono">{factText(value)}</dd></div>
                ))}
              </dl>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
