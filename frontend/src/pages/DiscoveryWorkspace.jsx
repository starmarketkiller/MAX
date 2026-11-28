// CHART-MULTISCALE-DISCOVERY-01 — multigrafico sincronizzato + Reverse Discovery Lab V1 (solo RETROSPECTIVE_DISCOVERY).
// Dati: stessa API e stessa guardia di partizione della Chart reale. Nessun replay causale, nessuna validazione, nessun segnale.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import api from "@/lib/api";
import { useTheme } from "@/lib/theme";
import ChartPane from "@/components/ChartPane";
import DiscoveryPanel from "@/components/DiscoveryPanel";
import useGeometrySession, { errText } from "@/lib/geometry/useGeometrySession";
import useDiscovery, { pivotKindFromAnchor } from "@/lib/geometry/useDiscovery";
import { TF_SECONDS, defaultUnits } from "@/lib/geometry/geometryMath";

const TF_ORDER = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"];
const PANE_IDS = ["p0", "p1", "p2", "p3"];
const parseUtc = (s) => {
  const m = String(s).trim().match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/);
  return m ? Math.round(Date.UTC(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0)) / 1000) : null;
};
const fmtUtc = (t) => new Date(t * 1000).toISOString().replace("T", " ").slice(0, 16);
const btn = "rounded border border-border bg-card px-1.5 py-0.5 text-[11px] hover:bg-muted disabled:opacity-40";
const sel = "rounded border border-border bg-background px-1 py-0.5 text-[11px] font-mono";

export default function DiscoveryWorkspace() {
  const { theme } = useTheme();
  const S = useGeometrySession({ enabled: true });
  const Disc = useDiscovery(S.sessionId);
  const [sources, setSources] = useState([]);
  const [source, setSource] = useState("");
  const [symbol, setSymbol] = useState("GOLD");
  const [count, setCount] = useState(1);
  const [panes, setPanes] = useState(["H4", "M15", "M5", "H1"].map((tf) => ({ tf, linked: true })));
  const [paneSymbols, setPaneSymbols] = useState(["GOLD", "GOLD", "GOLD", "GOLD"]);
  const [sync, setSync] = useState({ time_range: true, crosshair: true, symbol: true });
  const [tool, setTool] = useState("select");
  const [snapMode, setSnapMode] = useState("free");
  const [selectedId, setSelectedId] = useState(null);
  const [activeLayer, setActiveLayer] = useState("default");
  const [units, setUnits] = useState(defaultUnits("GOLD"));
  const [toolbarEl, setToolbarEl] = useState(null);
  const [panelEl, setPanelEl] = useState(null);
  const [draft, setDraft] = useState({});
  const [structForm, setStructForm] = useState({ kind: "IMPULSE", scale: "MAJOR", parent_id: null });
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [interval, setIntervalState] = useState(null);
  const [gotoVal, setGotoVal] = useState("");
  const [note, setNote] = useState(null);
  const [loads, setLoads] = useState([]);
  const [error, setError] = useState(null);

  const registry = useRef({});
  const st = useRef({});
  const lastRange = useRef(null);
  const structOrigin = useRef(null);
  const pendingFocus = useRef(null);
  const restored = useRef(null);
  const saveTimer = useRef(null);
  const cur = sources.find((s) => s.dataset_id === source);
  const tfs = cur?.timeframes || [];
  const symbols = cur?.symbol_aliases || [symbol];
  st.current = { panes, sync, count, tfs, selectedEventId };

  // ---- fonti autorizzate
  useEffect(() => {
    let off = false;
    api.get("/chart/sources").then(({ data }) => {
      if (off) return;
      const list = (data.sources || []).filter((s) => s.dataset_id && s.timeframes);
      setSources(list);
      if (!list.length) setError(`Nessuna fonte dati reale disponibile (${data.reason || "NO_DATASETS"}). Nessun dato sintetico viene mostrato.`);
      setSource((p) => (p && list.some((s) => s.dataset_id === p) ? p : (data.default_source && list.some((s) => s.dataset_id === data.default_source) ? data.default_source : list[0]?.dataset_id || "")));
    }).catch((e) => setError(errText(e)));
    return () => { off = true; };
  }, []);
  useEffect(() => {
    if (cur && !cur.symbol_aliases.includes(symbol)) setSymbol(cur.symbol_aliases[0]);
  }, [cur, symbol]);
  // il pane puo' usare solo timeframe del dataset: altrimenti ripiega sul piu' vicino disponibile (nessuna richiesta fuori copertura)
  useEffect(() => {
    if (!tfs.length) return;
    setPanes((ps) => ps.map((p) => (tfs.includes(p.tf) ? p : { ...p, tf: tfs.includes("H4") ? "H4" : tfs[tfs.length - 1] })));
  }, [tfs.join(",")]);   // eslint-disable-line react-hooks/exhaustive-deps

  // ---- ripristino della ricerca salvata (una volta per sessione)
  useEffect(() => {
    if (!S.sessionId || !Disc.loaded || restored.current === S.sessionId || !sources.length) return;
    restored.current = S.sessionId;
    const r = Disc.research;
    if (r) {
      if (r.layout) { setCount(r.layout.count); setPanes(PANE_IDS.map((_, i) => r.layout.charts[i] || { tf: "H4", linked: true })); setSync(r.layout.sync); }
      if (r.units) setUnits(r.units);
      if (r.dataset_id && sources.some((s) => s.dataset_id === r.dataset_id)) setSource(r.dataset_id);
      if (r.symbol) setSymbol(r.symbol);
      if (r.interval) setIntervalState(r.interval);
      if (r.focus_event_id) setSelectedEventId(r.focus_event_id);
    }
  }, [S.sessionId, Disc.loaded, Disc.research, sources]);   // eslint-disable-line react-hooks/exhaustive-deps

  // ---- salvataggio automatico dello stato della ricerca (disposizione, sincronizzazione, unita', intervallo, evento in studio)
  useEffect(() => {
    if (!S.sessionId || restored.current !== S.sessionId || !source) return undefined;
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      Disc.saveResearch({ name: S.session?.name || "", dataset_id: source, symbol, interval, units,
        layout: { count, charts: panes.slice(0, count).map((p) => ({ tf: p.tf, linked: p.linked })), sync }, focus_event_id: selectedEventId }).catch(() => {});
    }, 500);
    return () => clearTimeout(saveTimer.current);
  }, [count, panes, sync, units, interval, source, symbol, selectedEventId, S.sessionId, restored.current]);   // eslint-disable-line react-hooks/exhaustive-deps

  // ---- sincronizzazione selettiva (finestra temporale e crosshair), con guardie anti-eco nei pane
  const onRange = useCallback((pid, r) => {
    lastRange.current = r;
    const { panes: ps, sync: sy, count: n } = st.current;
    const i = PANE_IDS.indexOf(pid);
    if (!sy.time_range || !ps[i]?.linked) return;
    for (let k = 0; k < n; k += 1) if (k !== i && ps[k].linked) registry.current[PANE_IDS[k]]?.setRange(r);
  }, []);
  const onCrosshair = useCallback((pid, t) => {
    const { panes: ps, sync: sy, count: n } = st.current;
    const i = PANE_IDS.indexOf(pid);
    if (!sy.crosshair || !ps[i]?.linked) return;
    for (let k = 0; k < n; k += 1) if (k !== i && ps[k].linked) registry.current[PANE_IDS[k]]?.setCrosshairTime(t);
  }, []);

  const goTo = useCallback((ev, { pre = 70, post = 30 } = {}) => {
    const t = ev.pivot.t;
    for (let i = 0; i < st.current.count; i += 1) {
      const reg = registry.current[PANE_IDS[i]];
      const w = TF_SECONDS[st.current.panes[i].tf] || 900;
      if (reg) reg.focusRange({ from: t - pre * w, to: t + post * w });
    }
  }, []);
  const tryFocus = useCallback(() => {
    const p = pendingFocus.current;
    if (!p) return;
    const { panes: ps, count: n } = st.current;
    const ready = ps.slice(0, n).every((x, i) => { const r = registry.current[PANE_IDS[i]]; return r && r.tf === x.tf && r.getBars().length > 0; });
    if (!ready) return;
    pendingFocus.current = null;
    setTimeout(() => goTo(p), 300);
  }, [goTo]);
  const onLoaded = useCallback((pid, info) => { setLoads((l) => [...l.slice(-39), { pane: pid, ...info, at: Date.now() }]); tryFocus(); }, [tryFocus]);

  const nav = useMemo(() => ({
    goTo: (ev) => goTo(ev),
    openMultiscale: (ev) => {                       // scala osservata + scale inferiori disponibili (M15, M5 se il dataset le ha): le scale non sono timeframe fissi
      const { tfs: av } = st.current;
      const obs = ev.timeframe_observation;
      const oi = TF_ORDER.indexOf(obs);
      const lower = TF_ORDER.filter((t) => av.includes(t) && TF_ORDER.indexOf(t) < oi);
      const want = [obs];
      for (const t of ["M15", "M5"]) if (lower.includes(t)) want.push(t);
      for (const t of [...lower].reverse()) if (want.length < 3 && !want.includes(t)) want.push(t);
      const list = want.slice(0, 4);
      pendingFocus.current = ev;
      setCount(list.length);
      setPanes((ps) => ps.map((p, i) => (i < list.length ? { ...p, tf: list[i], linked: false } : p)));      // finestre indipendenti per scala; la sincronizzazione si riattiva per pane
      setTimeout(tryFocus, 400);
    },
    back: () => { for (let i = 0; i < st.current.count; i += 1) { const reg = registry.current[PANE_IDS[i]]; const r = reg?.getRange(); if (r) reg.shiftBy(-(r.to - r.from) / 2); } },
    forward: () => { for (let i = 0; i < st.current.count; i += 1) { const reg = registry.current[PANE_IDS[i]]; const r = reg?.getRange(); if (r) reg.shiftBy((r.to - r.from) / 2); } },
  }), [goTo, tryFocus]);

  // ---- pannelli: cambio TF mantiene la finestra temporale corrente
  const onTf = useCallback((i, tf) => {
    const reg = registry.current[PANE_IDS[i]];
    const r = reg?.getRange();
    if (r) reg.setPending(r);
    setPanes((ps) => ps.map((p, k) => (k === i ? { ...p, tf } : p)));
  }, []);
  const onLinked = useCallback((i, v) => setPanes((ps) => ps.map((p, k) => (k === i ? { ...p, linked: v } : p))), []);
  const onPaneSymbol = useCallback((i, s) => setPaneSymbols((a) => a.map((x, k) => (k === i ? s : x))), []);
  const symOf = (i) => (sync.symbol ? symbol : paneSymbols[i] || symbol);

  // ---- punti scelti sul grafico per le schede evento / strutture
  const onPick = useCallback((t, a, info) => {
    if (t === "pick:pivot") {
      const bar = (info.bars || []).find((b) => b.time === a.ref?.bar_t);
      setDraft((d) => ({ ...d, pivot: a, kind: pivotKindFromAnchor(a, bar), tf: info.tf, paneId: info.paneId, meta: { dataset_id: info.meta?.dataset_id, source: info.meta?.feed_kind, clock_basis: info.meta?.clock_basis } }));
      setTool("select");
    } else if (t === "pick:origin") { setDraft((d) => ({ ...d, origin: a })); setTool("select"); }
    else if (t === "pick:destination") { setDraft((d) => ({ ...d, destination: a })); setTool("select"); }
    else if (t === "pick:struct_origin") { structOrigin.current = a; setTool("pick:struct_dest"); }
    else if (t === "pick:struct_dest") {
      const o = structOrigin.current;
      structOrigin.current = null;
      setTool("select");
      const ev = Disc.events.find((e) => e.event_id === st.current.selectedEventId);
      if (!o || !ev) { setNote("Seleziona prima una scheda evento."); return; }
      Disc.updateEvent(ev.event_id, { structures: [...ev.structures, { kind: structForm.kind, scale: structForm.scale, parent_id: structForm.parent_id, origin: o, destination: a, geometry_ids: [] }] })
        .then(() => setNote(null)).catch((e) => setNote(errText(e)));
    }
  }, [Disc, structForm]);

  const createFromDraft = useCallback(async ({ name, outcome }) => {
    if (!draft.pivot) throw new Error("Scegli prima il pivot sul grafico.");
    const body = {
      name: name || `Evento ${Disc.events.length + 1}`, dataset_id: draft.meta?.dataset_id || source, source: draft.meta?.source || "", symbol: symbol,
      clock_basis: draft.meta?.clock_basis || "", timeframe_observation: draft.tf, outcome,
      pivot: { t: draft.pivot.t, price: draft.pivot.price, ref: draft.pivot.ref, kind: draft.kind || "HIGH" },
      origin: draft.origin ? { t: draft.origin.t, price: draft.origin.price, ref: draft.origin.ref } : null,
      destination: draft.destination ? { t: draft.destination.t, price: draft.destination.price, ref: draft.destination.ref } : null,
      units,
    };
    const ev = await Disc.createEvent(body);
    setSelectedEventId(ev.event_id);
    setDraft({});
    return ev;
  }, [draft, Disc, source, symbol, units]);

  const shared = { S, tool, setTool, snapMode, setSnapMode, selectedId, setSelectedId, activeLayer, setActiveLayer, units, setUnits, toolbarEl, panelEl,
    hint: tool === "pick:pivot" ? "Clic sul massimo o minimo significativo (candela)" : tool === "pick:origin" ? "Clic sull'origine del movimento" : tool === "pick:destination" ? "Clic sulla destinazione"
      : tool === "pick:struct_origin" ? "Struttura: clic sull'origine" : tool === "pick:struct_dest" ? "Struttura: clic sulla destinazione" : "" };

  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape" && tool.startsWith("pick:")) setTool("select"); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tool]);

  const applyInterval = (a, b) => {
    const f = parseUtc(a), t = parseUtc(b);
    if (f == null || t == null || f >= t) { setNote("Intervallo non valido (AAAA-MM-GG [HH:MM] UTC, inizio < fine)."); return; }
    setIntervalState({ from_t: f, to_t: t });
    registry.current[PANE_IDS[0]]?.focusRange({ from: f, to: t });
    setNote(null);
  };
  const gotoTime = () => {
    const t = parseUtc(gotoVal);
    if (t == null) { setNote("Data non valida (AAAA-MM-GG HH:MM UTC)."); return; }
    for (let i = 0; i < count; i += 1) {
      if (!panes[i].linked) continue;
      const reg = registry.current[PANE_IDS[i]];
      const r = reg?.getRange();
      const w = r ? r.to - r.from : 100 * (TF_SECONDS[panes[i].tf] || 900);
      reg?.focusRange({ from: t - w / 2, to: t + w / 2 });
    }
    setNote(null);
  };

  const gridCls = count === 1 ? "grid-cols-1" : count === 2 ? "grid-cols-2" : count === 3 ? "grid-cols-3" : "grid-cols-2 grid-rows-2";
  return (
    <div className="fixed inset-0 bg-card flex flex-col" data-testid="discovery-workspace" data-loads={JSON.stringify(loads.slice(-12))}>
      <div className="shrink-0 flex flex-wrap items-center gap-2 px-3 py-1.5 border-b border-border text-[11px]">
        <b className="tracking-wide">REVERSE DISCOVERY LAB</b>
        <select className={sel} value={source} data-testid="ws-source" onChange={(e) => setSource(e.target.value)}>{sources.map((s) => <option key={s.dataset_id} value={s.dataset_id}>{s.label || s.dataset_id}</option>)}</select>
        <select className={sel} value={symbol} data-testid="ws-symbol" onChange={(e) => setSymbol(e.target.value)}>{symbols.map((s) => <option key={s}>{s}</option>)}</select>
        <span>Grafici:</span>
        {[1, 2, 3, 4].map((n) => <button key={n} type="button" className={`${btn} ${count === n ? "bg-primary text-primary-foreground" : ""}`} data-testid={`ws-layout-${n}`} onClick={() => setCount(n)}>{n}</button>)}
        <span>Sync:</span>
        {[["time_range", "finestra"], ["crosshair", "crosshair"], ["symbol", "simbolo"]].map(([k, l]) => (
          <label key={k} className="flex items-center gap-1"><input type="checkbox" checked={sync[k]} data-testid={`ws-sync-${k}`} onChange={(e) => setSync({ ...sync, [k]: e.target.checked })} />{l}</label>
        ))}
        <input className={`${sel} w-36`} placeholder="vai a AAAA-MM-GG HH:MM" value={gotoVal} data-testid="ws-goto-input" onChange={(e) => setGotoVal(e.target.value)} />
        <button type="button" className={btn} data-testid="ws-goto" onClick={gotoTime}>Vai</button>
        <span className="text-muted-foreground">Periodo:</span>
        <IntervalInputs interval={interval} onApply={applyInterval} onAll={() => { registry.current[PANE_IDS[0]]?.getBars().length && registry.current[PANE_IDS[0]].focusRange({ from: registry.current[PANE_IDS[0]].getBars()[0].time, to: registry.current[PANE_IDS[0]].getBars().slice(-1)[0].time + 1 }); setIntervalState(null); }} />
        <span className="ml-auto text-muted-foreground" data-testid="ws-session">{S.session?.name || "…"} · sessione {S.sessionId?.slice(-5) || "—"}</span>
      </div>
      {note && <div className="shrink-0 px-3 py-0.5 text-[11px] text-amber-700 dark:text-amber-400 border-b border-border" role="status" data-testid="ws-note">{note}</div>}
      {error && <div className="shrink-0 px-3 py-1 text-[11px] text-rose-600" role="alert" data-testid="ws-error">{error}</div>}
      <div className="flex-1 min-h-0 flex">
        <div className={`flex-1 min-w-0 min-h-0 grid gap-1.5 p-1.5 ${gridCls}`} data-testid="ws-grid">
          {PANE_IDS.slice(0, count).map((pid, i) => (
            <ChartPane key={pid} paneId={pid} index={i} source={source} symbol={symOf(i)} tf={panes[i].tf} tfs={tfs} onTf={onTf} symbols={symbols} onSymbol={onPaneSymbol}
              symbolLocked={sync.symbol} linked={panes[i].linked} onLinked={onLinked} dark={theme === "dark"} registry={registry} onRange={onRange} onCrosshair={onCrosshair}
              onLoaded={onLoaded} shared={shared} onPick={onPick} />
          ))}
        </div>
        <aside className="w-[380px] shrink-0 overflow-y-auto border-l border-border p-2 space-y-2" data-testid="ws-sidebar">
          <div ref={setToolbarEl} data-testid="geo-toolbar-slot" />
          <DiscoveryPanel events={Disc.events} selectedEventId={selectedEventId} setSelectedEventId={setSelectedEventId} draft={draft} setDraft={setDraft} tool={tool} setTool={setTool}
            units={units} symbol={symbol} createFromDraft={createFromDraft} update={Disc.updateEvent} archive={Disc.archiveEvent} nav={nav} geoms={S.geoms} selectedGeomId={selectedId}
            structForm={structForm} setStructForm={setStructForm} compare={Disc.compare} status={Disc.status} note={note} setNote={setNote} />
          <div ref={setPanelEl} data-testid="geo-panel-slot" />
        </aside>
      </div>
    </div>
  );
}

function IntervalInputs({ interval, onApply, onAll }) {
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  useEffect(() => { if (interval) { setA(fmtUtc(interval.from_t)); setB(fmtUtc(interval.to_t)); } }, [interval]);
  return (
    <>
      <input className={`${sel} w-32`} placeholder="da AAAA-MM-GG HH:MM" value={a} data-testid="ws-interval-from" onChange={(e) => setA(e.target.value)} />
      <input className={`${sel} w-32`} placeholder="a AAAA-MM-GG HH:MM" value={b} data-testid="ws-interval-to" onChange={(e) => setB(e.target.value)} />
      <button type="button" className={btn} data-testid="ws-interval-apply" onClick={() => onApply(a, b)}>Applica</button>
      <button type="button" className={btn} data-testid="ws-interval-all" onClick={onAll}>Tutto lo storico caricato</button>
    </>
  );
}
