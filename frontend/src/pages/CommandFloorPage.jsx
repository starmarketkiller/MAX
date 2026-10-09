import { useEffect, useRef, useState } from "react";
import { useVisiblePolling } from "@/lib/useVisiblePolling";
import api from "@/lib/api";
import { AUTOMATIONS, BUSINESS_UNITS, FLOWS } from "@/command/graph";
import { DEPARTMENTS, STATIONS, WORKFLOWS, stationById, stationsByDepartment, workflowById } from "@/command/stations";
import { WORLDS, eventsAt, frameAt, stationState, worldById, worldLength } from "@/command/engine";
import { SKILLS, WORKERS, skillById, workerById } from "@/command/skills";
import { readLive } from "@/command/live";
import { MARKER, MARKER_REACHED, REVIEW_MARKER, REVIEW_READY } from "@/command/marker";
import FloorMap from "@/command/FloorMap";
import { PHASES, assignments, departmentSnapshot, scriptAt, workerLoad } from "@/command/script";

const ROOMS = [...DEPARTMENTS, { id: "council", code: "C", name: "Council", lede: "Osserva e propone. Non adotta da solo." }];
const STATE = { idle: "IDLE", queued: "CODA", running: "CORRE", waiting: "ATTESA", blocked: "BLOCCO", completed: "FATTO", failed: "FAIL" };

export default function CommandFloorPage() {
  const [mode, setMode] = useState("sim");
  const [worldId, setWorldId] = useState(WORLDS[0].id);
  const [beat, setBeat] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1000);
  const [roomId, setRoomId] = useState("trading");
  const [selectedId, setSelectedId] = useState("trading.data");
  const [live, setLive] = useState(null);
  const [liveError, setLiveError] = useState("");
  const liveSeq = useRef(0);
  const world = worldById(worldId);
  const length = worldLength(world);
  const cursor = Math.min(beat, length - 1);
  const frame = frameAt(world, cursor);
  const selected = stationById(selectedId);
  const selectedState = selected ? stationState(frame.states, selected) : "idle";

  useEffect(() => {
    if (mode !== "sim" || !playing) return undefined;
    const timer = window.setInterval(() => setBeat((current) => (current + 1) % length), speed);
    return () => window.clearInterval(timer);
  }, [mode, playing, speed, length]);

  useVisiblePolling(async () => {
    const mine = ++liveSeq.current;
    try {
      const next = await readLive(api, { generation: mine });
      if (mine !== liveSeq.current) return;
      setLive(next);
      setLiveError("");
    } catch {
      if (mine !== liveSeq.current) return;
      setLive(null);
      setLiveError("offline");
    }
  }, 30000, mode === "live");

  return (
    <div className="space-y-4" data-testid="command-floor">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Visual Floor</div>
          <h1 className="text-2xl font-semibold tracking-tight">Command floor</h1>
          <p className="mt-1 text-sm text-muted-foreground">{MARKER} {MARKER_REACHED ? "acceso" : "spento"}. {REVIEW_READY ? `${REVIEW_MARKER}: pronta alla revisione, non operativa.` : `${REVIEW_MARKER} non ancora chiuso.`}</p>
        </div>
        <div className="flex gap-2">
          <button type="button" className={"rounded border px-3 py-2 text-xs " + (mode === "live" ? "border-primary text-primary" : "border-border text-muted-foreground")} onClick={() => setMode("live")}>Dati veri</button>
          <button type="button" className={"rounded border px-3 py-2 text-xs " + (mode === "sim" ? "border-primary text-foreground" : "border-border text-muted-foreground")} onClick={() => setMode("sim")}>Simulazione</button>
        </div>
      </div>

      {mode === "live" ? <LivePane live={live} error={liveError} /> : (
        <SimPane
          world={world}
          cursor={cursor}
          length={length}
          playing={playing}
          speed={speed}
          setSpeed={setSpeed}
          setPlaying={setPlaying}
          setWorldId={setWorldId}
          setBeat={setBeat}
          roomId={roomId}
          setRoomId={setRoomId}
          frame={frame}
          selected={selected}
          selectedState={selectedState}
          selectedId={selectedId}
          setSelectedId={setSelectedId}
        />
      )}
    </div>
  );
}

function LivePane({ live, error }) {
  return (
    <section aria-label="Letture canoniche">
      <p className="text-sm text-muted-foreground">{error ? "Backend non raggiungibile. Nessun dato simulato al suo posto." : live ? `Origine Axios condiviso. Sonda ${live.at}. Una risposta 200 non significa che una task stia girando.` : "Lettura in corso."}</p>
      <ul className="mt-3 space-y-2">
        {(live?.rows ?? []).map((row) => (
          <li key={row.path} className="border border-border p-3 text-sm">
            <div className={row.live ? "text-emerald-400" : "text-amber-400"}>{row.status}</div>
            <div className="mt-1">{row.name}</div>
            <div className="mt-1 font-mono text-[11px] text-muted-foreground">{row.stationId} → {row.capabilityId} → GET {row.path}</div>
            <div className="mt-1 text-xs text-muted-foreground">HTTP {row.http || "nessuno"} · {row.api} · schema {row.schema} · {row.at} · task {row.task}{row.error ? ` · ${row.error}` : ""}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SimPane({ world, cursor, length, playing, speed, setSpeed, setPlaying, setWorldId, setBeat, roomId, setRoomId, frame, selected, selectedState, selectedId, setSelectedId }) {
  const events = eventsAt(world, cursor);
  const story = scriptAt(world, cursor);
  const load = workerLoad(frame);
  const active = assignments(frame);
  const workflow = selected ? workflowById(selected.workflowId) : null;
  const speeds = [{ ms: 2000, label: "0.5×" }, { ms: 1000, label: "1×" }, { ms: 500, label: "2×" }];
  return (
    <>
      <div data-testid="sim-controls" className="flex flex-wrap gap-2">
        {WORLDS.map((item) => <button key={item.id} type="button" className={"min-h-11 rounded border px-3 py-2 text-xs " + (item.id === world.id ? "border-primary" : "border-border text-muted-foreground")} onClick={() => { setWorldId(item.id); setBeat(0); setPlaying(false); }}>{item.name}</button>)}
        <button type="button" className="min-h-11 rounded border border-border px-3 py-2 text-xs" onClick={() => setPlaying((value) => !value)}>{playing ? "Pausa" : "Play"}</button>
        <button type="button" className="min-h-11 rounded border border-border px-3 py-2 text-xs" onClick={() => { setPlaying(false); setBeat((value) => Math.max(0, value - 1)); }}>Indietro</button>
        <span className="self-center font-mono text-xs text-muted-foreground">{cursor + 1}/{length}</span>
        <button type="button" className="min-h-11 rounded border border-border px-3 py-2 text-xs" onClick={() => { setPlaying(false); setBeat((value) => Math.min(length - 1, value + 1)); }}>Avanti</button>
        <button type="button" className="min-h-11 rounded border border-border px-3 py-2 text-xs" onClick={() => { setPlaying(false); setBeat(0); }}>Reset</button>
        {speeds.map((item) => <button key={item.ms} type="button" className={"min-h-11 rounded border px-3 py-2 text-xs " + (speed === item.ms ? "border-primary" : "border-border text-muted-foreground")} onClick={() => setSpeed(item.ms)}>{item.label}</button>)}
      </div>
      <p className="text-sm text-muted-foreground">{world.lede} Simulazione deterministica: stesso passo, stesso stato. Nessun ordine, deploy o pubblicazione.</p>
      <div className="flex gap-1 overflow-x-auto pb-1" aria-label="Fasi">
        {PHASES.map((phase) => <span key={phase.id} className={"shrink-0 rounded border px-2 py-1 text-[11px] " + (story.phase === phase.id ? "border-primary text-foreground" : "border-border text-muted-foreground")}>{phase.label}</span>)}
      </div>
      <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground" aria-label="Legenda">
        <span>Oro = in corso</span><span>Ambra = attesa</span><span>Rosso = blocco o fail</span><span>Verde = passo chiuso</span><span>Tratteggio = previsto, non operativo</span>
      </div>
      <FloorMap frame={frame} selectedId={selectedId} onSelect={setSelectedId} />
      <div className="flex gap-2 overflow-x-auto">
        {ROOMS.map((room) => <button key={room.id} type="button" className={"min-h-11 shrink-0 rounded border px-3 py-2 text-xs " + (room.id === roomId ? "border-primary" : "border-border text-muted-foreground")} onClick={() => setRoomId(room.id)}>{room.name}</button>)}
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {stationsByDepartment(roomId).map((station) => {
          const state = stationState(frame.states, station);
          return <button key={station.id} type="button" onClick={() => setSelectedId(station.id)} className={"min-h-11 border p-3 text-left " + (station.id === selected?.id ? "border-primary" : "border-border")}>
            <div className="font-mono text-[10px] text-muted-foreground">{station.code} · SIMULATION</div>
            <div className="mt-1 text-sm">{station.name}</div>
            <div className="mt-1 text-xs text-muted-foreground">{STATE[state]}</div>
          </button>;
        })}
      </div>
      <Detail selectedId={selectedId} selected={selected} selectedState={selectedState} story={story} workflow={workflow} load={load} active={active} frame={frame} />
      <section>
        <h2 className="text-xs uppercase tracking-wider text-muted-foreground">Eventi di questo passo</h2>
        <ul className="mt-2 space-y-1 text-xs">{events.length ? events.map((event) => <li key={event.provenance}>SIMULATION · {event.type} · {event.to} · {event.provenance}</li>) : <li className="text-muted-foreground">Nessun evento.</li>}</ul>
      </section>
      <p className="font-mono text-[11px] text-muted-foreground">{STATIONS.length} postazioni · {WORKFLOWS.length} workflow · {SKILLS.length} skill · {WORKERS.length} worker condivisi · {AUTOMATIONS.length} automazioni · {FLOWS.length} flussi · {BUSINESS_UNITS.length} business unit previste, non operative</p>
    </>
  );
}

function Detail({ selectedId, selected, selectedState, story, workflow, load, active, frame }) {
  if (selectedId.startsWith("worker:")) {
    const id = selectedId.slice(7);
    const worker = workerById(id);
    const jobs = active.filter((item) => item.worker === id);
    return (
      <article data-testid="floor-detail" className="border border-border p-4" aria-label={worker?.name || id}>
        <h2 className="text-lg font-semibold">{worker?.name || id}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{worker?.note} Agente condiviso, non copiato per azienda. Presenza: repository.</p>
        <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
          <Fact k="Carico simulato" v={String(load[id] || 0)} />
          <Fact k="Task" v={jobs.map((item) => item.name).join(", ") || "Nessuna"} />
          <Fact k="Aziende" v={jobs.map((item) => item.departmentId).join(", ") || "Nessuna"} />
          <Fact k="Stato" v={jobs.map((item) => STATE[item.state]).join(", ") || "IDLE"} />
          <Fact k="Dipendenze" v={jobs.flatMap((item) => item.dependencies).join(", ") || "Nessuna"} />
          <Fact k="Output di registro" v={jobs.map((item) => item.output).join(" · ") || "Assente"} />
          <Fact k="Tipo output" v={jobs.every((item) => item.outputKind === "absent") ? "non prodotto" : "registro, non osservato fuori dalla simulazione"} />
        </dl>
      </article>
    );
  }
  if (selectedId.startsWith("unit:")) {
    const unit = BUSINESS_UNITS.find((item) => item.id === selectedId.slice(5));
    return (
      <article data-testid="floor-detail" className="border border-border p-4">
        <h2 className="text-lg font-semibold">{unit?.name || selectedId}</h2>
        <p className="mt-1 text-sm text-muted-foreground">Prevista nel masterplan. Non è un'entità del repository e non è un dato LIVE.</p>
        <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
          <Fact k="Presenza" v="planned" />
          <Fact k="Reparti collegati" v={(unit?.departments || []).join(", ")} />
        </dl>
      </article>
    );
  }
  if (selectedId.startsWith("dept:")) {
    const room = ROOMS.find((item) => item.id === selectedId.slice(5));
    const rows = departmentSnapshot(room?.id, frame);
    return (
      <article data-testid="floor-detail" className="border border-border p-4" aria-label={room?.name || "Reparto"}>
        <h2 className="text-lg font-semibold">{room?.name}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{room?.lede} Presenza: repository. Non è una business unit pianificata.</p>
        <ul className="mt-3 space-y-2 text-xs">
          {rows.length ? rows.map((row) => <li key={row.id} className="border border-border p-2">{row.name} · {STATE[row.state] || row.state} · dipende da {row.dependencies.join(", ") || "niente"} · {row.output}</li>) : <li>Nessuna task in questo passo.</li>}
        </ul>
      </article>
    );
  }
  if (selected) {
    const station = selected;
    return (
      <article data-testid="floor-detail" className="border border-border p-4" aria-label={station?.name || story.company}>
        <h2 className="text-lg font-semibold">{station ? station.name : story.company}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{station ? station.role : "Reparto del repository. Le business unit che lo citano restano previste."}</p>
        <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
          <Fact k="Evento" v={story.event} />
          <Fact k="Azienda" v={`${story.company} · ${story.companyPresence}`} />
          <Fact k="Task" v={story.task} />
          <Fact k="Agente" v={story.agentName} />
          <Fact k="Dipendenze" v={story.dependencies.join(", ") || "Nessuna"} />
          <Fact k="Esecuzione" v={STATE[story.execution] || story.execution} />
          <Fact k="Output" v={story.outputKind === "registry" ? `${story.output} · di registro, non un esito LIVE` : story.output} />
          <Fact k="Validazione" v={story.validation} />
          <Fact k="Approvazione" v={story.approval === "none" ? "Non richiesta in questo passo" : story.execution === "waiting" ? "In attesa, non concessa" : story.approval} />
          <Fact k="Risultato" v={story.result} />
          {station ? <Fact k="Simulazione" v={STATE[selectedState]} /> : null}
          {station ? <Fact k="Skill" v={station.skills.map((id) => skillById(id)?.name || id).join(", ")} /> : null}
          {station ? <Fact k="Catena" v={workflow ? `${workflow.stationIds.indexOf(station.id) + 1}/${workflow.stationIds.length}` : "—"} /> : null}
          <Fact k="Unità previste" v={story.plannedUnits.map((item) => item.name).join(", ") || "Nessuna"} />
        </dl>
      </article>
    );
  }
  return null;
}

function Fact({ k, v }) {
  return <div className="border border-border px-2 py-2"><dt className="text-muted-foreground">{k}</dt><dd>{v}</dd></div>;
}
