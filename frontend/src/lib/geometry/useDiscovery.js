import { useCallback, useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { errText } from "@/lib/geometry/useGeometrySession";

const D = "/chart/discovery";
export const WRITABLE = ["name", "dataset_id", "source", "symbol", "clock_basis", "timeframe_observation", "outcome", "pivot", "origin", "destination", "units",
  "classification", "size_class", "geometries", "structures", "annotations", "hypotheses", "evidence_for", "evidence_against", "analog_links", "status"];

/** Pivot, origine e destinazione dal punto scelto: il tipo (massimo/minimo) e' dedotto dal campo della candela e correggibile dall'utente. */
export function pivotKindFromAnchor(anchor, bar) {
  const f = anchor?.ref?.field;
  if (f === "high") return "HIGH";
  if (f === "low") return "LOW";
  if (bar) return anchor.price >= (bar.high + bar.low) / 2 ? "HIGH" : "LOW";
  return "HIGH";
}

export function formatSpan(sec) {
  const s = Math.abs(Math.round(sec));
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return `${d ? `${d}g ` : ""}${h || d ? `${h}h ` : ""}${m}m`.trim();
}

/** Schede evento + stato della ricerca per la sessione `sid` (solo RETROSPECTIVE_DISCOVERY). Scritture serializzate. */
export default function useDiscovery(sid) {
  const [events, setEvents] = useState([]);
  const [research, setResearchState] = useState(null);
  const [loadedSid, setLoadedSid] = useState(null);
  const [status, setStatus] = useState({ state: "idle", error: null, at: null });
  const eventsRef = useRef([]);
  const chain = useRef(Promise.resolve());
  const sidRef = useRef(sid);
  sidRef.current = sid;
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);

  const setE = useCallback((list) => { eventsRef.current = list; setEvents(list); }, []);
  const enqueue = useCallback((fn) => {
    const run = chain.current.then(() => { if (mounted.current) setStatus((s) => ({ ...s, state: "saving" })); return fn(); });
    chain.current = run.catch(() => {});
    return run.then((v) => { if (mounted.current) setStatus({ state: "saved", error: null, at: Date.now() }); return v; },
      (e) => { if (mounted.current) setStatus((s) => ({ state: "error", error: errText(e), at: s.at })); throw e; });
  }, []);

  const reload = useCallback(async () => {
    if (!sidRef.current) return;
    const [ev, rs] = await Promise.all([api.get(`${D}/sessions/${sidRef.current}/events`), api.get(`${D}/sessions/${sidRef.current}/research`)]);
    if (!mounted.current) return;
    setE(ev.data.events || []);
    setResearchState(rs.data.research);
    setLoadedSid(sidRef.current);
  }, [setE]);

  useEffect(() => {
    setE([]); setResearchState(null); setLoadedSid(null);
    if (!sid) return undefined;
    let cancelled = false;
    reload().catch((e) => { if (!cancelled && mounted.current) setStatus({ state: "unavailable", error: errText(e), at: null }); });
    return () => { cancelled = true; };
  }, [sid, reload, setE]);

  const upsert = (ev) => {
    const list = eventsRef.current.filter((x) => x.event_id !== ev.event_id);
    if (ev.status !== "ARCHIVED") list.push(ev);
    setE(list.sort((a, b) => a.discovered_at - b.discovered_at || a.event_id.localeCompare(b.event_id)));
  };

  const createEvent = useCallback((body) => enqueue(async () => {
    const { data } = await api.post(`${D}/sessions/${sidRef.current}/events`, body);
    upsert(data);
    return data;
  }), [enqueue]);   // eslint-disable-line react-hooks/exhaustive-deps

  /** `patch`: solo i campi cambiati (liste intere comprese); la revisione attesa e' quella corrente nel client. */
  const updateEvent = useCallback((eid, patch) => enqueue(async () => {
    const cur = eventsRef.current.find((x) => x.event_id === eid);
    if (!cur) throw new Error("evento non presente");
    const { data } = await api.put(`${D}/sessions/${sidRef.current}/events/${eid}`, { ...patch, expected_revision: cur.revision });
    upsert(data);
    return data;
  }), [enqueue]);   // eslint-disable-line react-hooks/exhaustive-deps

  const archiveEvent = useCallback((eid) => enqueue(async () => {
    const cur = eventsRef.current.find((x) => x.event_id === eid);
    const { data } = await api.post(`${D}/sessions/${sidRef.current}/events/${eid}/archive`, { expected_revision: cur.revision });
    upsert(data);
    return data;
  }), [enqueue]);   // eslint-disable-line react-hooks/exhaustive-deps

  const saveResearch = useCallback((body) => enqueue(async () => {
    const { data } = await api.put(`${D}/sessions/${sidRef.current}/research`, body);
    setResearchState(data.research);
    return data;
  }), [enqueue]);

  const compare = useCallback(async (ids) => (await api.get(`${D}/sessions/${sidRef.current}/compare?ids=${ids.join(",")}`)).data, []);

  return { events, research, loaded: !!sid && loadedSid === sid, status, createEvent, updateEvent, archiveEvent, saveResearch, compare, reload };
}
