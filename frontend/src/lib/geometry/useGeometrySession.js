import { useCallback, useEffect, useRef, useState } from "react";
import api from "@/lib/api";

const LS_KEY = "nexus.chart.geometry.session";   // solo comodita' per-browser: la verita' e' sul server (per utente)
export const PATCH_FIELDS = ["anchors", "style", "name", "description", "semantic", "fib_levels", "text", "links"];

const pick = (g) => {
  const o = {};
  PATCH_FIELDS.forEach((k) => { if (g[k] !== undefined) o[k] = JSON.parse(JSON.stringify(g[k])); });
  return o;
};
/** Patch minimo da `from` a `to`: solo i campi cambiati (per `style`, solo le chiavi cambiate). Evita di rimandare valori invariati. */
export function diffPatch(from, to) {
  const patch = {};
  PATCH_FIELDS.forEach((k) => {
    if (JSON.stringify(from[k]) === JSON.stringify(to[k])) return;
    if (k === "style" && from.style && to.style) {
      const st = {};
      Object.keys(to.style).forEach((sk) => { if (JSON.stringify(from.style[sk]) !== JSON.stringify(to.style[sk])) st[sk] = to.style[sk]; });
      if (Object.keys(st).length) patch.style = st;
    } else if (to[k] !== undefined) patch[k] = to[k];
  });
  return patch;
}
export function errText(e) {
  const d = e?.response?.data?.detail;
  if (d && typeof d === "object") return `${d.code || "ERRORE"}${d.message ? `: ${d.message}` : ""}`;
  return typeof d === "string" ? d : (e?.message || "errore di rete");
}
const lsGet = () => { try { return window.localStorage.getItem(LS_KEY); } catch (err) { void err; return null; } };
const lsSet = (v) => { try { window.localStorage.setItem(LS_KEY, v); } catch (err) { void err; } };

/** Sessione di geometrie persistente: ogni modifica e' una richiesta con revisione attesa, serializzata (nessuna corsa). */
export default function useGeometrySession({ enabled = true } = {}) {
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [session, setSession] = useState(null);
  const [layers, setLayers] = useState([]);
  const [geoms, setGeoms] = useState([]);
  const [status, setStatus] = useState({ state: "idle", at: null, error: null });
  const [stackInfo, setStackInfo] = useState({ undo: 0, redo: 0 });
  const geomsRef = useRef([]);
  const undoRef = useRef([]);
  const redoRef = useRef([]);
  const chainRef = useRef(Promise.resolve());
  const sidRef = useRef(null);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);

  const setG = useCallback((list) => { geomsRef.current = list; setGeoms(list); }, []);
  const bump = () => setStackInfo({ undo: undoRef.current.length, redo: redoRef.current.length });
  const ok = () => mounted.current && setStatus({ state: "saved", at: Date.now(), error: null });
  const fail = (e) => { if (mounted.current) setStatus((s) => ({ state: "error", at: s.at, error: errText(e) })); throw e; };
  const B = "/chart/geometry";

  // le richieste di scrittura sono accodate: ognuna parte quando la precedente e' conclusa
  const enqueue = useCallback((fn) => {
    const run = chainRef.current.then(() => { if (mounted.current) setStatus((s) => ({ ...s, state: "saving" })); return fn(); });
    chainRef.current = run.catch(() => {});
    return run;
  }, []);

  const loadSession = useCallback(async (sid) => {
    const { data } = await api.get(`${B}/sessions/${sid}`);
    if (!mounted.current) return null;
    sidRef.current = sid;
    setSessionId(sid); setSession(data.session); setLayers(data.layers); setG(data.geometries);
    undoRef.current = []; redoRef.current = []; bump();
    lsSet(sid);
    return data;
  }, [setG]);

  const refreshSessions = useCallback(async () => {
    const { data } = await api.get(`${B}/sessions`);
    if (mounted.current) setSessions(data.sessions || []);
    return data.sessions || [];
  }, []);

  const createSession = useCallback(async (name, symbol = "") => {
    const { data } = await api.post(`${B}/sessions`, { name, symbol });
    await refreshSessions();
    await loadSession(data.session_id);
    return data;
  }, [loadSession, refreshSessions]);

  // avvio: riapre l'ultima sessione (se esiste ancora per questo utente), altrimenti la piu' recente, altrimenti ne crea una
  useEffect(() => {
    if (!enabled) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const list = await refreshSessions();
        if (cancelled) return;
        const last = lsGet();
        const pickId = (last && list.some((s) => s.session_id === last)) ? last : list[0]?.session_id;
        if (pickId) await loadSession(pickId);
        else await createSession("Analisi 1");
        if (!cancelled && mounted.current) setStatus({ state: "idle", at: null, error: null });
      } catch (e) {
        if (!cancelled && mounted.current) setStatus({ state: "unavailable", at: null, error: errText(e) });
      }
    })();
    return () => { cancelled = true; };
  }, [enabled, refreshSessions, loadSession, createSession]);

  const upsertLocal = (obj) => {
    const list = geomsRef.current.filter((g) => g.geometry_id !== obj.geometry_id);
    if (obj.status !== "ARCHIVED") list.push(obj);
    setG(list.sort((a, b) => a.created_at - b.created_at || a.geometry_id.localeCompare(b.geometry_id)));
  };

  const create = useCallback((body, { record = true } = {}) => enqueue(async () => {
    try {
      const { data } = await api.post(`${B}/sessions/${sidRef.current}/objects`, body);
      upsertLocal(data);
      if (record) { undoRef.current.push({ kind: "create", gid: data.geometry_id }); redoRef.current = []; bump(); }
      ok();
      return data;
    } catch (e) { return fail(e); }
  }), [enqueue]);   // eslint-disable-line react-hooks/exhaustive-deps

  const patchNow = async (gid, patch) => {
    const cur = geomsRef.current.find((g) => g.geometry_id === gid);
    if (!cur) throw new Error("oggetto non presente");
    const { data } = await api.put(`${B}/sessions/${sidRef.current}/objects/${gid}`, { ...patch, expected_revision: cur.revision });
    upsertLocal(data);
    return { before: pick(cur), after: pick(data), data };
  };
  // undo/redo: riporta l'oggetto allo stato `target` inviando solo la differenza rispetto allo stato corrente
  const restoreTo = async (gid, target) => {
    const cur = geomsRef.current.find((g) => g.geometry_id === gid);
    if (!cur) throw new Error("oggetto non presente");
    const patch = diffPatch(pick(cur), target);
    if (!Object.keys(patch).length) return cur;
    return (await patchNow(gid, patch)).data;
  };

  const update = useCallback((gid, patch, { record = true } = {}) => enqueue(async () => {
    try {
      const r = await patchNow(gid, patch);
      if (record) { undoRef.current.push({ kind: "update", gid, before: r.before, after: r.after }); redoRef.current = []; bump(); }
      ok();
      return r.data;
    } catch (e) { return fail(e); }
  }), [enqueue]);   // eslint-disable-line react-hooks/exhaustive-deps

  const statusNow = async (gid, action) => {
    const cur = geomsRef.current.find((g) => g.geometry_id === gid) || (await api.get(`${B}/sessions/${sidRef.current}/objects/${gid}`)).data;
    const { data } = await api.post(`${B}/sessions/${sidRef.current}/objects/${gid}/${action}`, { expected_revision: cur.revision });
    upsertLocal(data);
    return data;
  };

  const archive = useCallback((gid, { record = true } = {}) => enqueue(async () => {
    try {
      const d = await statusNow(gid, "archive");
      if (record) { undoRef.current.push({ kind: "archive", gid }); redoRef.current = []; bump(); }
      ok();
      return d;
    } catch (e) { return fail(e); }
  }), [enqueue]);   // eslint-disable-line react-hooks/exhaustive-deps

  const undo = useCallback(() => enqueue(async () => {
    const op = undoRef.current.pop();
    if (!op) return null;
    try {
      if (op.kind === "create") await statusNow(op.gid, "archive");
      else if (op.kind === "archive") await statusNow(op.gid, "restore");
      else await restoreTo(op.gid, op.before);
      redoRef.current.push(op); bump(); ok();
      return op;
    } catch (e) { undoRef.current.push(op); bump(); return fail(e); }
  }), [enqueue]);   // eslint-disable-line react-hooks/exhaustive-deps

  const redo = useCallback(() => enqueue(async () => {
    const op = redoRef.current.pop();
    if (!op) return null;
    try {
      if (op.kind === "create") await statusNow(op.gid, "restore");
      else if (op.kind === "archive") await statusNow(op.gid, "archive");
      else await restoreTo(op.gid, op.after);
      undoRef.current.push(op); bump(); ok();
      return op;
    } catch (e) { redoRef.current.push(op); bump(); return fail(e); }
  }), [enqueue]);   // eslint-disable-line react-hooks/exhaustive-deps

  const setLayer = useCallback((lid, patch) => enqueue(async () => {
    try {
      const { data } = await api.put(`${B}/sessions/${sidRef.current}/layers/${lid}`, patch);
      setLayers(data.layers); ok();
      return data.layers;
    } catch (e) { return fail(e); }
  }), [enqueue]);   // eslint-disable-line react-hooks/exhaustive-deps

  const renameSession = useCallback((name) => enqueue(async () => {
    try {
      const { data } = await api.put(`${B}/sessions/${sidRef.current}`, { name });
      setSession(data); await refreshSessions(); ok();
    } catch (e) { fail(e); }
  }), [enqueue, refreshSessions]);

  const exportSession = useCallback(async () => (await api.get(`${B}/sessions/${sidRef.current}/export`)).data, []);

  const importSession = useCallback(async (doc, name) => {
    try {
      const payload = name ? { ...doc, _import_name: name } : doc;
      const { data } = await api.post(`${B}/import`, payload);
      await refreshSessions();
      await loadSession(data.session_id);
      ok();
      return data;
    } catch (e) { return fail(e); }
  }, [refreshSessions, loadSession]);

  const reload = useCallback(async () => { if (sidRef.current) { await loadSession(sidRef.current); await refreshSessions(); } }, [loadSession, refreshSessions]);

  return {
    sessions, sessionId, session, layers, geoms, status, stackInfo,
    create, update, archive, undo, redo, setLayer, renameSession, createSession, loadSession, exportSession, importSession, reload, refreshSessions,
  };
}
