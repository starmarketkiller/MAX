// CHART-MULTISCALE-DISCOVERY-01 — pannello del Reverse Discovery Lab V1 (RETROSPECTIVE_DISCOVERY, selezione manuale).
// Mostra associazioni geometriche, ipotesi e osservazioni: nessuna validazione, nessun segnale, nessuna statistica.
import { useMemo, useState } from "react";
import { errText } from "@/lib/geometry/useGeometrySession";
import { formatSpan } from "@/lib/geometry/useDiscovery";
import { fmtPrice, fmtTime, TOOLS } from "@/lib/geometry/geometryMath";

const SC = [["MAJOR", "Scala maggiore"], ["INTERMEDIATE", "Scala intermedia"], ["MINOR", "Scala minore"], ["UNCLASSIFIED", "Non classificata"]];
const TIMING = [["BEFORE_EVENT_OBSERVABLE", "Osservabile prima dell'evento"], ["DURING_EVENT", "Formata durante l'evento"], ["RETROSPECTIVELY_RECOGNIZED", "Riconosciuta retrospettivamente"]];
const HYP = ["OPEN", "SUPPORTED_BY_OBSERVATION", "CONTRADICTED_BY_OBSERVATION", "DISCARDED"];
const CLS = [["UNCLASSIFIED", "Non classificato"], ["MAJOR_REVERSAL", "Inversione maggiore"], ["INTERMEDIATE_REVERSAL", "Inversione intermedia"], ["MINOR_REVERSAL", "Inversione minore"], ["FALSE_START", "Falsa partenza"], ["CONTINUATION", "Continuazione"]];
const ANALOG = [["ANALOG_WITH_REVERSAL", "Analogo con inversione"], ["ANALOG_NO_REVERSAL", "Analogo SENZA inversione"], ["RELATED", "Correlato"]];
const inp = "mt-0.5 w-full rounded border border-border bg-background px-1.5 py-0.5 text-[11px] font-mono text-foreground";
const btn = "rounded border border-border bg-card px-1.5 py-0.5 text-[11px] hover:bg-muted disabled:opacity-40";
const H = ({ children }) => <div className="mt-2 font-bold text-[11px]">{children}</div>;

function AddText({ placeholder, onAdd, testid, extra }) {
  const [v, setV] = useState("");
  return (
    <div className="flex gap-1 mt-1">
      <input className={inp} placeholder={placeholder} value={v} data-testid={`${testid}-input`} onChange={(e) => setV(e.target.value)} />
      {extra}
      <button type="button" className={btn} data-testid={`${testid}-add`} disabled={!v.trim()} onClick={() => { onAdd(v.trim()); setV(""); }}>+</button>
    </div>
  );
}

export default function DiscoveryPanel({ events, selectedEventId, setSelectedEventId, draft, setDraft, tool, setTool, units, symbol, createFromDraft, update, archive,
  nav, geoms, selectedGeomId, structForm, setStructForm, eventWindow = { pre: 70, post: 30 }, setEventWindow = () => {}, compare, status, note, setNote, hasPivotTool = true }) {
  const [tab, setTab] = useState("events");
  const [name, setName] = useState("");
  const [outcome, setOutcome] = useState("REVERSAL");
  const [timing, setTiming] = useState("BEFORE_EVENT_OBSERVABLE");
  const [hypStatus, setHypStatus] = useState("OPEN");
  const [analogId, setAnalogId] = useState("");
  const [analogKind, setAnalogKind] = useState("ANALOG_NO_REVERSAL");
  const [cmpA, setCmpA] = useState("");
  const [cmpB, setCmpB] = useState("");
  const [cmp, setCmp] = useState(null);
  const ev = events.find((e) => e.event_id === selectedEventId) || null;
  const run = (p) => p.then(() => setNote(null)).catch((e) => setNote(errText(e)));
  const upd = (patch) => ev && run(update(ev.event_id, patch));

  const depth = useMemo(() => {
    const d = {};
    if (!ev) return d;
    const by = Object.fromEntries(ev.structures.map((s) => [s.id, s]));
    ev.structures.forEach((s) => { let n = 0, cur = s; while (cur && cur.parent_id && n < 20) { n += 1; cur = by[cur.parent_id]; } d[s.id] = n; });
    return d;
  }, [ev]);
  const pt = (p) => (p ? `${fmtTime(p.t, "").slice(5, 16)} @ ${fmtPrice(p.price)}${p.ref?.kind === "CANDLE" ? ` (${p.ref.field.toUpperCase()})` : ""}` : "—");
  const pips = (leg) => (leg ? `${fmtPrice(leg.amplitude_price)}${leg.amplitude_pips == null ? "" : ` = ${Number(leg.amplitude_pips.toFixed(1))} pip`} · ${formatSpan(leg.duration_s)}` : "—");
  const pickBtn = (id, label, ok) => (
    <button type="button" className={`${btn} ${tool === id ? "bg-primary text-primary-foreground" : ""}`} data-testid={`lab-${id.replace(":", "-")}`} onClick={() => setTool(tool === id ? "select" : id)}>{ok ? "✓ " : ""}{label}</button>
  );

  return (
    <div className="text-[11px]" data-testid="discovery-panel">
      <div className="flex items-center justify-between">
        <b>REVERSE DISCOVERY LAB · retrospettiva</b>
        <span data-testid="lab-status" className={status.state === "error" ? "text-rose-600" : "text-emerald-600"}>{status.state === "saved" ? "salvato" : status.state === "saving" ? "salvataggio…" : status.state === "error" ? "errore" : "pronto"}</span>
      </div>
      <div className="text-[10px] text-amber-700 dark:text-amber-400" data-testid="lab-mode-banner">
        Modalità RETROSPECTIVE_DISCOVERY: il futuro è visibile. Solo ipotesi/osservazioni (DISCOVERY_ONLY): nessuna validazione, nessun segnale, nessun replay causale. Associazione geometrica ≠ spiegazione causale ≠ edge predittivo.
      </div>
      {(note || status.error) && <div className="mt-1 rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-amber-700 dark:text-amber-400" role="status" data-testid="lab-note">{note || status.error}</div>}
      <div className="mt-1 flex gap-1">
        {[["events", "Eventi"], ["compare", "Confronto"]].map(([k, l]) => <button key={k} type="button" className={`${btn} ${tab === k ? "bg-primary text-primary-foreground" : ""}`} data-testid={`lab-tab-${k}`} onClick={() => setTab(k)}>{l}</button>)}
      </div>

      {tab === "events" && (<>
        <H>Nuova scheda evento (selezione manuale)</H>
        <div className="flex flex-wrap gap-1">
          {pickBtn("pick:pivot", "1 · Pivot (massimo/minimo)", !!draft.pivot)}
          {pickBtn("pick:origin", "2 · Origine", !!draft.origin)}
          {pickBtn("pick:destination", "3 · Destinazione", !!draft.destination)}
        </div>
        <div className="mt-1 font-mono text-[10px] text-muted-foreground" data-testid="lab-draft">
          pivot {pt(draft.pivot)} {draft.pivot ? `· ${draft.kind} · TF ${draft.tf}` : ""}<br />origine {pt(draft.origin)} · destinazione {pt(draft.destination)}
        </div>
        <div className="mt-1 grid grid-cols-2 gap-1">
          <select className={inp} data-testid="lab-draft-kind" value={draft.kind || "HIGH"} onChange={(e) => setDraft({ ...draft, kind: e.target.value })}><option value="HIGH">Pivot: massimo</option><option value="LOW">Pivot: minimo</option></select>
          <select className={inp} data-testid="lab-outcome" value={outcome} onChange={(e) => setOutcome(e.target.value)}><option value="REVERSAL">Inversione</option><option value="NO_REVERSAL">Analogo SENZA inversione</option></select>
        </div>
        <div className="mt-1 flex gap-1">
          <input className={inp} placeholder="nome scheda" value={name} data-testid="lab-event-name" onChange={(e) => setName(e.target.value)} />
          <button type="button" className={btn} data-testid="lab-create" disabled={!draft.pivot} onClick={() => run(createFromDraft({ name: name.trim(), outcome }).then(() => setName("")))}>Crea</button>
          <button type="button" className={btn} data-testid="lab-draft-clear" onClick={() => setDraft({})}>×</button>
        </div>

        <H>Schede ({events.length})</H>
        <ul className="max-h-28 overflow-y-auto" data-testid="lab-event-list">
          {events.map((e) => (
            <li key={e.event_id}>
              <button type="button" data-testid={`lab-event-${e.event_id}`} onClick={() => setSelectedEventId(e.event_id)}
                className={`w-full text-left truncate rounded px-1 py-0.5 ${e.event_id === selectedEventId ? "bg-primary/15" : "hover:bg-muted"}`}>
                {e.outcome === "NO_REVERSAL" ? "∅ " : e.pivot.kind === "HIGH" ? "▲ " : "▼ "}{e.name || "(senza nome)"} · {fmtTime(e.pivot.t, "").slice(5, 16)}
              </button>
            </li>
          ))}
        </ul>

        {ev && (
          <div className="mt-2 border-t border-border pt-1" data-testid="lab-event-card" key={`${ev.event_id}:${ev.revision}`}>
            <div className="font-bold">Scheda {ev.name || ev.event_id} <span className="font-normal text-muted-foreground">rev {ev.revision}</span></div>
            <div className="grid grid-cols-2 gap-1">
              <label className="text-[10px] text-muted-foreground">Nome<input className={inp} data-testid="lab-card-name" defaultValue={ev.name} onBlur={(e) => e.target.value !== ev.name && upd({ name: e.target.value })} /></label>
              <label className="text-[10px] text-muted-foreground">Classificazione manuale
                <select className={inp} data-testid="lab-card-class" value={ev.classification} onChange={(e) => upd({ classification: e.target.value })}>{CLS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            </div>
            <div className="mt-1 font-mono text-[10px] leading-4" data-testid="lab-card-facts">
              {ev.symbol} · {ev.timeframe_observation} · {ev.dataset_id} · {ev.source} · clock {String(ev.clock_basis).split(" ")[0] || "n/d"}<br />
              pivot {ev.pivot.kind === "HIGH" ? "massimo" : "minimo"} {pt(ev.pivot)} · prima {ev.derived.prior_direction === "UP" ? "↑" : "↓"} → dopo {ev.derived.next_direction === "UP" ? "↑" : "↓"}<br />
              movimento precedente (origine {pt(ev.origin)}): <b data-testid="lab-card-prior">{pips(ev.derived.prior_leg)}</b><br />
              movimento successivo (destinazione {pt(ev.destination)}): <b data-testid="lab-card-next">{pips(ev.derived.next_leg)}</b><br />
              unità: pip {units?.pip_size ?? "n/d"} · point {ev.units?.point ?? "n/d"} · tick {ev.units?.tick_size ?? "n/d"} (prezzo, pip, point, tick restano separati)<br />
              scoperta {fmtTime(Math.round(ev.discovered_at), "UTC")} · autore {ev.author}{ev.author_verified ? "" : ` (dichiarato; importato da ${ev.imported_by})`}<br />
              modalità <b>{ev.epistemic_mode}</b> (immutabile) · validazione <b data-testid="lab-card-validation">{ev.validation_status}</b>
            </div>

            <H>Navigazione</H>
            <div className="flex items-center gap-1 text-[10px] text-muted-foreground" data-testid="lab-window">
              finestra attorno all'evento (barre di ciascuna scala; default modificabile, non una regola):
              <input className={`${inp} !w-14`} type="number" min="1" max="2000" value={eventWindow.pre} data-testid="lab-win-pre" onChange={(e) => setEventWindow({ ...eventWindow, pre: Math.max(1, Math.min(2000, Number(e.target.value) || 1)) })} /> prima
              <input className={`${inp} !w-14`} type="number" min="0" max="2000" value={eventWindow.post} data-testid="lab-win-post" onChange={(e) => setEventWindow({ ...eventWindow, post: Math.max(0, Math.min(2000, Number(e.target.value) || 0)) })} /> dopo
            </div>
            <div className="mt-1 flex flex-wrap gap-1">
              <button type="button" className={btn} data-testid="lab-go" onClick={() => nav.goTo(ev)}>Vai all'inversione</button>
              <button type="button" className={btn} data-testid="lab-open-multiscale" onClick={() => nav.openMultiscale(ev)}>Apri sulle scale inferiori</button>
              <button type="button" className={btn} data-testid="lab-back" onClick={() => nav.back()}>◀ Passato prima dell'evento</button>
              <button type="button" className={btn} data-testid="lab-forward" onClick={() => nav.forward()}>▶</button>
            </div>

            <H>Geometrie associate ({ev.geometries.length})</H>
            <div className="text-[10px] text-muted-foreground">Presente nel grafico ≠ conoscibile prima dell'evento: <code>available_at</code> non si retrodata.</div>
            {ev.geometries.map((lk) => (
              <div key={lk.id} className="mt-0.5 flex items-center gap-1" data-testid={`lab-geom-${lk.geometry_id}`}>
                <span className="truncate flex-1">{TOOLS.find((t) => t.id === lk.geometry?.type)?.label || lk.geometry_id} {lk.geometry?.semantic_class !== "NONE" ? `· ${lk.geometry?.semantic_class}` : ""}</span>
                <select className={`${inp} !w-40`} value={lk.timing} data-testid={`lab-geom-timing-${lk.geometry_id}`} onChange={(e) => upd({ geometries: ev.geometries.map((x) => (x.id === lk.id ? { ...x, timing: e.target.value } : x)) })}>{TIMING.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
                <span title="conoscenza causale" className="text-[9px] text-amber-700 dark:text-amber-400">{lk.causal_knowledge}</span>
                <button type="button" className={btn} onClick={() => upd({ geometries: ev.geometries.filter((x) => x.id !== lk.id) })}>×</button>
              </div>
            ))}
            <div className="mt-1 flex gap-1">
              <select className={inp} value={timing} data-testid="lab-link-timing" onChange={(e) => setTiming(e.target.value)}>{TIMING.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
              <button type="button" className={btn} data-testid="lab-link-geometry" disabled={!selectedGeomId || !geoms.some((g) => g.geometry_id === selectedGeomId)}
                onClick={() => upd({ geometries: [...ev.geometries, { geometry_id: selectedGeomId, timing }] })}>Associa selezionata</button>
            </div>

            <H>Strutture e scale ({ev.structures.length})</H>
            <div className="text-[10px] text-muted-foreground">Le scale descrivono dimensione e relazioni, non timeframe fissi né teorie d'onda.</div>
            {ev.structures.map((s) => (
              <div key={s.id} className="mt-0.5 flex items-center gap-1" style={{ paddingLeft: depth[s.id] * 10 }} data-testid={`lab-struct-${s.id}`}>
                <span className="font-mono truncate flex-1">{s.kind === "IMPULSE" ? "impulso" : s.kind === "CORRECTION" ? "correzione" : "gruppo"} {s.derived.direction === "UP" ? "↑" : s.derived.direction === "DOWN" ? "↓" : "·"} {pips(s.derived)}{s.parent_id ? ` (figlio di ${s.parent_id.slice(-4)})` : ""}</span>
                <select className={`${inp} !w-32`} value={s.scale} data-testid={`lab-struct-scale-${s.id}`} onChange={(e) => upd({ structures: ev.structures.map((x) => (x.id === s.id ? { ...x, scale: e.target.value } : x)) })}>{SC.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
                <button type="button" className={btn} onClick={() => upd({ structures: ev.structures.filter((x) => x.id !== s.id && x.parent_id !== s.id) })}>×</button>
              </div>
            ))}
            {ev.structures.map((s) => (
              <div key={`g${s.id}`} className="mt-0.5 flex flex-wrap items-center gap-1 text-[10px] text-muted-foreground" style={{ paddingLeft: depth[s.id] * 10 }} data-testid={`lab-struct-geoms-${s.id}`}>
                geometrie della struttura {s.id.slice(-4)}: {(s.geometry_ids || []).length === 0 ? "nessuna" : (s.geometry_ids || []).map((gid) => (
                  <span key={gid} className="rounded border border-border px-1" data-testid={`lab-struct-geom-${s.id}-${gid}`}>{TOOLS.find((t) => t.id === geoms.find((g) => g.geometry_id === gid)?.type)?.label || gid}
                    <button type="button" className="ml-1" aria-label="scollega" onClick={() => upd({ structures: ev.structures.map((x) => (x.id === s.id ? { ...x, geometry_ids: x.geometry_ids.filter((q) => q !== gid) } : x)) })}>×</button></span>
                ))}
                <button type="button" className={btn} data-testid={`lab-struct-link-${s.id}`} disabled={!selectedGeomId || !geoms.some((g) => g.geometry_id === selectedGeomId) || (s.geometry_ids || []).includes(selectedGeomId)}
                  onClick={() => upd({ structures: ev.structures.map((x) => (x.id === s.id ? { ...x, geometry_ids: [...(x.geometry_ids || []), selectedGeomId] } : x)) })}>collega la geometria selezionata</button>
              </div>
            ))}
            <div className="mt-1 grid grid-cols-3 gap-1">
              <select className={inp} data-testid="lab-struct-kind" value={structForm.kind} onChange={(e) => setStructForm({ ...structForm, kind: e.target.value })}><option value="IMPULSE">impulso</option><option value="CORRECTION">correzione</option><option value="GEOMETRY_GROUP">gruppo geometrie</option></select>
              <select className={inp} data-testid="lab-struct-newscale" value={structForm.scale} onChange={(e) => setStructForm({ ...structForm, scale: e.target.value })}>{SC.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
              <select className={inp} data-testid="lab-struct-parent" value={structForm.parent_id || ""} onChange={(e) => setStructForm({ ...structForm, parent_id: e.target.value || null })}><option value="">(nessun padre)</option>{ev.structures.map((s) => <option key={s.id} value={s.id}>{s.kind} {s.id.slice(-4)}</option>)}</select>
            </div>
            <button type="button" className={`${btn} mt-1 ${tool.startsWith("pick:struct") ? "bg-primary text-primary-foreground" : ""}`} data-testid="lab-struct-trace" onClick={() => setTool(tool.startsWith("pick:struct") ? "select" : "pick:struct_origin")}>Traccia struttura (2 clic: origine, destinazione)</button>

            <H>Annotazioni ({ev.annotations.length})</H>
            {ev.annotations.map((a) => <div key={a.id} className="mt-0.5" data-testid="lab-annotation">• {a.text}</div>)}
            <AddText placeholder="annotazione…" testid="lab-ann" onAdd={(t) => upd({ annotations: [...ev.annotations, { text: t }] })} />

            <H>Ipotesi alternative ({ev.hypotheses.length})</H>
            {ev.hypotheses.map((h) => (
              <div key={h.id} className="mt-0.5 flex items-center gap-1" data-testid="lab-hypothesis">
                <span className="flex-1">{h.text}</span>
                <select className={`${inp} !w-44`} value={h.status} onChange={(e) => upd({ hypotheses: ev.hypotheses.map((x) => (x.id === h.id ? { ...x, status: e.target.value } : x)) })}>{HYP.map((v) => <option key={v}>{v}</option>)}</select>
              </div>
            ))}
            <AddText placeholder="ipotesi alternativa…" testid="lab-hyp" onAdd={(t) => upd({ hypotheses: [...ev.hypotheses, { text: t, status: hypStatus }] })}
              extra={<select className={`${inp} !w-24`} value={hypStatus} onChange={(e) => setHypStatus(e.target.value)}>{HYP.map((v) => <option key={v}>{v}</option>)}</select>} />

            <H>Evidenze favorevoli ({ev.evidence_for.length}) / contrarie ({ev.evidence_against.length})</H>
            {ev.evidence_for.map((x) => <div key={x.id} className="mt-0.5 text-emerald-700 dark:text-emerald-400" data-testid="lab-evidence-for">＋ {x.text}</div>)}
            <AddText placeholder="evidenza favorevole…" testid="lab-evf" onAdd={(t) => upd({ evidence_for: [...ev.evidence_for, { text: t }] })} />
            {ev.evidence_against.map((x) => <div key={x.id} className="mt-0.5 text-rose-700 dark:text-rose-400" data-testid="lab-evidence-against">－ {x.text}</div>)}
            <AddText placeholder="evidenza contraria…" testid="lab-eva" onAdd={(t) => upd({ evidence_against: [...ev.evidence_against, { text: t }] })} />

            <H>Casi analoghi ({ev.analog_links.length})</H>
            {ev.analog_links.map((a) => <div key={a.id} className="mt-0.5" data-testid="lab-analog">↔ {events.find((x) => x.event_id === a.event_id)?.name || a.event_id} · {ANALOG.find((k) => k[0] === a.kind)?.[1]}</div>)}
            <div className="mt-1 flex gap-1">
              <select className={inp} value={analogId} data-testid="lab-analog-event" onChange={(e) => setAnalogId(e.target.value)}><option value="">(altro evento)</option>{events.filter((x) => x.event_id !== ev.event_id && !ev.analog_links.some((a) => a.event_id === x.event_id)).map((x) => <option key={x.event_id} value={x.event_id}>{x.name || x.event_id}</option>)}</select>
              <select className={inp} value={analogKind} data-testid="lab-analog-kind" onChange={(e) => setAnalogKind(e.target.value)}>{ANALOG.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
              <button type="button" className={btn} data-testid="lab-analog-add" disabled={!analogId} onClick={() => { upd({ analog_links: [...ev.analog_links, { event_id: analogId, kind: analogKind }] }); setAnalogId(""); }}>+</button>
            </div>
            <button type="button" className={`${btn} mt-2 w-full text-rose-600`} data-testid="lab-archive" onClick={() => run(archive(ev.event_id).then(() => setSelectedEventId(null)))}>Archivia scheda (reversibile)</button>
          </div>
        )}
      </>)}

      {tab === "compare" && (
        <div data-testid="lab-compare">
          <H>Confronto fra schede</H>
          <div className="grid grid-cols-2 gap-1">
            <select className={inp} data-testid="lab-cmp-a" value={cmpA} onChange={(e) => setCmpA(e.target.value)}><option value="">scheda A</option>{events.map((e) => <option key={e.event_id} value={e.event_id}>{e.name || e.event_id}</option>)}</select>
            <select className={inp} data-testid="lab-cmp-b" value={cmpB} onChange={(e) => setCmpB(e.target.value)}><option value="">scheda B</option>{events.map((e) => <option key={e.event_id} value={e.event_id}>{e.name || e.event_id}</option>)}</select>
          </div>
          <button type="button" className={`${btn} mt-1`} data-testid="lab-cmp-run" disabled={!cmpA || !cmpB || cmpA === cmpB} onClick={() => compare([cmpA, cmpB]).then(setCmp).catch((e) => setNote(errText(e)))}>Confronta</button>
          {cmp && (
            <div className="mt-1" data-testid="lab-cmp-result">
              <div className="rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-amber-700 dark:text-amber-400" data-testid="lab-cmp-disclaimer">{cmp.disclaimer}</div>
              <table className="mt-1 w-full text-[10px] font-mono border-collapse">
                <tbody>
                  {[["Nome", (r) => r.name || r.event_id], ["Esito", (r) => r.outcome], ["Pivot", (r) => `${r.pivot.kind} ${fmtPrice(r.pivot.price)}`],
                    ["Ampiezza prima", (r) => (r.prior_leg ? `${fmtPrice(r.prior_leg.amplitude_price)}${r.prior_leg.amplitude_pips == null ? "" : ` = ${Number(r.prior_leg.amplitude_pips.toFixed(1))} pip`}` : "—")],
                    ["Durata prima", (r) => (r.prior_leg ? formatSpan(r.prior_leg.duration_s) : "—")],
                    ["Ampiezza dopo", (r) => (r.next_leg ? fmtPrice(r.next_leg.amplitude_price) : "—")],
                    ["Geometrie per tempo", (r) => TIMING.map(([k]) => `${r.geometry_by_timing[k]}`).join(" / ")],
                    ["Geometrie per classe", (r) => Object.entries(r.geometry_by_class).map(([k, v]) => `${k}×${v}`).join(", ") || "—"],
                    ["Strutture per scala", (r) => Object.entries(r.structures_by_scale).map(([k, v]) => `${k}×${v}`).join(", ") || "—"],
                    ["Annotazioni", (r) => r.annotations.join(" | ") || "—"], ["Ipotesi", (r) => r.hypotheses.map((h) => `${h.text} [${h.status}]`).join(" | ") || "—"],
                    ["Evidenze +/−", (r) => `${r.evidence_for}/${r.evidence_against}`],
                    ["Analoghi (con/senza inv.)", (r) => `${r.analogs.ANALOG_WITH_REVERSAL}/${r.analogs.ANALOG_NO_REVERSAL}`]].map(([label, f]) => (
                    <tr key={label} className="border-t border-border"><th className="text-left align-top pr-1 text-muted-foreground">{label}</th>{cmp.events.map((r) => <td key={r.event_id} className="align-top pr-1" data-testid={`lab-cmp-${label}`}>{f(r)}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
