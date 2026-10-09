import { useRef, useState } from "react";
import { useVisiblePolling } from "@/lib/useVisiblePolling";
import api from "@/lib/api";
import { AUTOMATIONS, BUSINESS_UNITS, FLOWS } from "@/command/graph";
import { DEPARTMENTS, STATIONS, WORKFLOWS, stationById, stationsByDepartment, workflowById } from "@/command/stations";
import { WORLDS, eventsAt, frameAt, stationState, worldById, worldLength } from "@/command/engine";
import { SKILLS, WORKERS, skillById, workerById } from "@/command/skills";
import { readLive } from "@/command/live";
import { MARKER, MARKER_REACHED } from "@/command/marker";

const ROOMS = [...DEPARTMENTS, { id: "council", code: "C", name: "Council", lede: "Osserva e propone. Non adotta da solo." }];
const STATE = { idle: "IDLE", queued: "CODA", running: "CORRE", waiting: "ATTESA", blocked: "BLOCCO", completed: "FATTO", failed: "FAIL" };

export default function CommandFloorPage() {
  const [mode, setMode] = useState("sim");
  const [worldId, setWorldId] = useState(WORLDS[0].id);
  const [beat, setBeat] = useState(0);
  const [playing, setPlaying] = useState(false);
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

  useVisiblePolling(async () => {
    if (!playing) return;
    setBeat((current) => (current + 1) % length);
  }, 1000, mode === "sim" && playing);

  useVisiblePolling(async () => {
    const mine = ++liveSeq.current;
    try {
      const next = await readLive(api);
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
          <p className="mt-1 text-sm text-muted-foreground">{MARKER_REACHED ? MARKER : `${MARKER} non ancora chiuso. La simulazione non è il backend.`}</p>
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
          setPlaying={setPlaying}
          setWorldId={setWorldId}
          setBeat={setBeat}
          roomId={roomId}
          setRoomId={setRoomId}
          frame={frame}
          selected={selected}
          selectedState={selectedState}
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
            <div className="mt-1 text-xs text-muted-foreground">HTTP {row.http || "nessuno"} · {row.at} · task {row.task}{row.error ? ` · ${row.error}` : ""}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SimPane({ world, cursor, length, playing, setPlaying, setWorldId, setBeat, roomId, setRoomId, frame, selected, selectedState, setSelectedId }) {
  const events = eventsAt(world, cursor);
  const workflow = selected ? workflowById(selected.workflowId) : null;
  return (
    <>
      <div className="flex flex-wrap gap-2">
        {WORLDS.map((item) => <button key={item.id} type="button" className={"rounded border px-3 py-2 text-xs " + (item.id === world.id ? "border-primary" : "border-border text-muted-foreground")} onClick={() => { setWorldId(item.id); setBeat(0); }}>{item.name}</button>)}
        <button type="button" className="rounded border border-border px-3 py-2 text-xs" onClick={() => setPlaying((value) => !value)}>{playing ? "Pausa" : "Play"}</button>
        <button type="button" className="rounded border border-border px-3 py-2 text-xs" onClick={() => { setPlaying(false); setBeat((value) => Math.max(0, value - 1)); }}>Indietro</button>
        <span className="self-center font-mono text-xs text-muted-foreground">{cursor + 1}/{length}</span>
        <button type="button" className="rounded border border-border px-3 py-2 text-xs" onClick={() => { setPlaying(false); setBeat((value) => Math.min(length - 1, value + 1)); }}>Avanti</button>
      </div>
      <p className="text-sm text-muted-foreground">{world.lede}</p>
      <div className="flex gap-2 overflow-x-auto">
        {ROOMS.map((room) => <button key={room.id} type="button" className={"shrink-0 rounded border px-3 py-2 text-xs " + (room.id === roomId ? "border-primary" : "border-border text-muted-foreground")} onClick={() => setRoomId(room.id)}>{room.name}</button>)}
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {stationsByDepartment(roomId).map((station) => {
          const state = stationState(frame.states, station);
          return <button key={station.id} type="button" onClick={() => setSelectedId(station.id)} className={"border p-3 text-left " + (station.id === selected?.id ? "border-primary" : "border-border")}>
            <div className="font-mono text-[10px] text-muted-foreground">{station.code} · SIMULATION</div>
            <div className="mt-1 text-sm">{station.name}</div>
            <div className="mt-1 text-xs text-muted-foreground">{STATE[state]}</div>
          </button>;
        })}
      </div>
      {selected ? <article className="border border-border p-4" aria-label={selected.name}>
        <h2 className="text-lg font-semibold">{selected.name}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{selected.role}</p>
        <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
          <Fact k="Simulazione" v={STATE[selectedState]} />
          <Fact k="Canonico" v="SIMULATION" />
          <Fact k="Gate" v={selected.gate} />
          <Fact k="Worker" v={workerById(selected.worker)?.name || selected.worker} />
          <Fact k="Skill" v={selected.skills.map((id) => skillById(id)?.name || id).join(", ")} />
          <Fact k="Entra" v={selected.input} />
          <Fact k="Esce" v={selected.output} />
          <Fact k="Catena" v={workflow ? `${workflow.stationIds.indexOf(selected.id) + 1}/${workflow.stationIds.length}` : "—"} />
        </dl>
      </article> : null}
      <section>
        <h2 className="text-xs uppercase tracking-wider text-muted-foreground">Eventi di questo passo</h2>
        <ul className="mt-2 space-y-1 text-xs">{events.length ? events.map((event) => <li key={event.provenance}>{event.type} · {event.to} · {event.provenance}</li>) : <li className="text-muted-foreground">Nessun evento.</li>}</ul>
      </section>
      <p className="font-mono text-[11px] text-muted-foreground">{STATIONS.length} postazioni · {WORKFLOWS.length} workflow · {SKILLS.length} skill · {WORKERS.length} worker · {AUTOMATIONS.length} automazioni · {FLOWS.length} flussi · {BUSINESS_UNITS.length} business unit previste, non operative</p>
    </>
  );
}

function Fact({ k, v }) {
  return <div className="border border-border px-2 py-2"><dt className="text-muted-foreground">{k}</dt><dd>{v}</dd></div>;
}
