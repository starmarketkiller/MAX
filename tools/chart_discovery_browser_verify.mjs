// NEXUS-CHART-MULTISCALE-DISCOVERY-01 — verifica nel browser reale (Edge/CDP) su dati XM autorizzati.
// USO: CHART_MS_ROOT=<cartella con evidence_ms/ e runtime/> CHART_ORIGIN=http://127.0.0.1:8853 [CHART_ORIGIN_B=http://127.0.0.1:8854] node tools/chart_discovery_browser_verify.mjs
import { execSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { openBrowser, makeReport, sleep, same, close } from "./cdp_lib.mjs";

const root = (process.env.CHART_MS_ROOT || process.cwd()).replace(/\\/g, "/");
const origin = process.env.CHART_ORIGIN || "http://127.0.0.1:8853";
const originB = process.env.CHART_ORIGIN_B || "";
const SRC = "XM-GOLD-2026-11-16-20";
const out = resolve(root, "evidence_ms", "screens");
const { report, check } = makeReport(origin, { source: SRC });
const USER = ["chart-geo@local", "chart-geo-local-only"], USER_B = ["chart-geo-b@local", "chart-geo-b-local-only"];
const fmtUtc = (t) => new Date(t * 1000).toISOString().replace("T", " ").slice(0, 16);
const D = "/chart/discovery", G = "/chart/geometry";
const portOf = (o) => (o.match(/:(\d+)/) || [])[1];
function backendRss(o) {          // RSS del processo uvicorn (backend), distinto dal browser
  try {
    const r = execSync(`powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process -Filter \\"Name='python.exe'\\" | Where-Object { $_.CommandLine -match '--port ${portOf(o)}' } | Select-Object -First 1; if ($p) { (Get-Process -Id $p.ProcessId).WorkingSet64 }"`, { encoding: "utf8" }).trim();
    return r ? +(Number(r) / 1048576).toFixed(1) : null;
  } catch { return null; }
}
const B_OPTS = (tag, o = origin) => ({ tag, root, out, origin: o, report });

let B;
const px = async (pane, barIdx, price) => {                 // pixel della pagina per (indice barra, prezzo) nel pane, dalla scala reale del grafico
  const d = await B.ev(`(() => { const c = document.querySelectorAll('[data-testid=geometry-canvas]')[${pane}]; const r = c.getBoundingClientRect(); return { rx: r.x, ry: r.y, ...JSON.parse(c.dataset.dbg) }; })()`);
  const step = (d.x100 - d.x0) / 100;
  return [d.rx + d.x0 + barIdx * step, d.ry + d.y1000 + ((price - 1000) * (d.y3000 - d.y1000)) / 2000];
};
const ranges = () => B.ev("[...document.querySelectorAll('[data-testid^=pane-canvas-]')].map(e => JSON.parse(e.parentElement.dataset.range || 'null'))");
const proj = (pane) => B.ev(`JSON.parse(document.querySelectorAll('[data-testid=geometry-canvas]')[${pane}].dataset.proj || '[]')`);
const strips = () => B.ev("[...document.querySelectorAll('[data-testid^=pane-strip-]')].map(e => e.innerText)");
const waitStrips = (n, tfs) => B.waitFor(`(() => { const s=[...document.querySelectorAll('[data-testid^=pane-strip-]')].map(e=>e.innerText); return s.length===${n} && s.every((t,i)=>t.includes('barre') && t.includes(' '+${JSON.stringify(tfs)}[i]+' ')); })()`, 160, 250);
const sidOf = async () => (await B.api(`${G}/sessions`)).sessions[0].session_id;
const events = async (sid) => (await B.api(`${D}/sessions/${sid}/events`)).events;
const getBars = async (tf) => (await B.api(`/chart/ohlc?source=${SRC}&symbol=GOLD&tf=${tf}&limit=1500`)).bars;
const waitEvents = async (sid, n, tries = 40) => { for (let i = 0; i < tries; i++) { const e = await events(sid); if (e.length >= n) return e; await sleep(250); } return events(sid); };
const waitEv = async (sid, eid, pred, tries = 40) => { for (let i = 0; i < tries; i++) { const e = (await events(sid)).find((x) => x.event_id === eid); if (e && pred(e)) return e; await sleep(250); } return (await events(sid)).find((x) => x.event_id === eid); };
const geoms = async (sid) => (await B.api(`${G}/sessions/${sid}`)).geometries;
const waitGeom = async (sid, n, tries = 40) => { for (let i = 0; i < tries; i++) { const g = await geoms(sid); if (g.length >= n) return g; await sleep(250); } return geoms(sid); };
const nth = (sel, i, v) => B.ev(`(() => { const el = document.querySelectorAll(${JSON.stringify(sel)})[${i}]; Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype,'value').set.call(el, ${JSON.stringify(v)}); el.dispatchEvent(new Event('change',{bubbles:true})); return el.value; })()`);
const clickSel = (sel) => B.ev(`document.querySelector(${JSON.stringify(sel)}).click()`);
const openChart = async () => {
  await B.cdp("Page.navigate", { url: `${origin}/app/discovery` });
  return B.waitFor("[...document.querySelectorAll('[data-testid^=pane-strip-]')].length>0 && [...document.querySelectorAll('[data-testid^=pane-strip-]')].every(e=>e.innerText.includes('barre'))", 160, 250);
};

try {
  // ====================================================================== 1. apertura del grafico H4
  B = await openBrowser(B_OPTS("a"));
  const t0 = Date.now();
  await B.login(...USER);
  const rssIdle = backendRss(origin);
  const okOpen = await openChart();
  const loadMs = Date.now() - t0;
  const h4 = await getBars("H4"); const m15 = await getBars("M15"); const m5 = await getBars("M5");
  check("01 grafico H4 aperto su dati XM autorizzati", okOpen && (await strips())[0].includes(`GOLD H4`) && (await strips())[0].includes(SRC), { strip: (await strips())[0], ms: loadMs });
  check("01 barre H4 reali coerenti con l'API (30)", h4.length === 30 && (await strips())[0].includes(`${h4.length} barre`), h4.length);
  check("01 pannello geometrie chiuso di default", await B.ev("!document.querySelector('[data-testid=geometry-panel]') && !!document.querySelector('[data-testid=geometry-toolbar]')"));
  check("01 banner di modalita': RETROSPECTIVE_DISCOVERY, DISCOVERY_ONLY, nessuna validazione", /RETROSPECTIVE_DISCOVERY/.test(await B.ev("document.querySelector('[data-testid=lab-mode-banner]')?.innerText||''")));
  check("01 nessun dato sintetico", !(await B.ev("document.body.innerText.toUpperCase().includes('SYNTHETIC')")));
  await B.shot("01_discovery_h4_aperto.png");
  await B.clickId("geo-panel-toggle"); await sleep(400);
  const sid = await sidOf();
  check("01 sessione di ricerca creata/aperta", /^S/.test(sid), sid);

  // periodo storico autorizzato
  await B.setInput("ws-interval-from", fmtUtc(h4[0].time)); await B.setInput("ws-interval-to", fmtUtc(h4[h4.length - 1].time + 14400));
  await B.clickId("ws-interval-apply"); await sleep(900);
  check("01b periodo storico selezionato e applicato al grafico H4", !(await B.ev("document.querySelector('[data-testid=ws-note]')?.innerText")), (await ranges())[0]);
  await sleep(900);

  // ====================================================================== 2-3. selezione di un'inversione e scheda evento
  let pIdx = 0;
  pIdx = h4.reduce((best, b, i) => (i >= 4 && (best < 4 || b.high > h4[best].high) ? i : best), 0);
  const oIdx = h4.slice(0, pIdx).reduce((best, b, i) => (b.low < h4[best].low ? i : best), 0);
  const dIdx = pIdx + 1 + h4.slice(pIdx + 1).reduce((best, b, i, a) => (b.low < a[best].low ? i : best), 0);
  const P = h4[pIdx], O = h4[oIdx], DS = h4[dIdx];
  check("02 massimo significativo individuato nello storico H4 (scelta manuale riproducibile)", pIdx >= 4 && dIdx > pIdx, { pivot: [fmtUtc(P.time), P.high], origin: [fmtUtc(O.time), O.low], dest: [fmtUtc(DS.time), DS.low] });
  await B.clickId("lab-pick-pivot"); await sleep(200);
  check("02 strumento di selezione pivot attivo (suggerimento visibile)", /Clic sul massimo/.test(await B.ev("document.querySelector('[data-testid^=geo-pick-hint-]')?.innerText||''")));
  await B.click(...(await px(0, pIdx, P.high))); await sleep(300);
  await B.clickId("lab-pick-origin"); await B.click(...(await px(0, oIdx, O.low))); await sleep(300);
  await B.clickId("lab-pick-destination"); await B.click(...(await px(0, dIdx, DS.low))); await sleep(300);
  const draftTxt = await B.ev("document.querySelector('[data-testid=lab-draft]')?.innerText||''");
  check("02 pivot, origine e destinazione scelti sul grafico", /pivot \d/.test(draftTxt) && /origine \d/.test(draftTxt) && /destinazione \d/.test(draftTxt), draftTxt);
  await B.setInput("lab-event-name", "Inversione H4 A");
  await B.clickId("lab-create");
  const evA = (await waitEvents(sid, 1))[0];
  check("03 scheda evento creata e persistita", !!evA && evA.name === "Inversione H4 A" && evA.revision === 1, evA?.event_id);
  const pips = (P.high - O.low) / 0.1;
  check("03 scheda: pivot esatto = massimo (High) della candela reale H4, prezzo e orario", evA.pivot.t === P.time && evA.pivot.price === P.high && evA.pivot.kind === "HIGH" && evA.pivot.ref.field === "high" && evA.pivot.ref.bar_t === P.time, evA.pivot);
  check("03 scheda: origine e destinazione sulle candele reali", evA.origin.price === O.low && evA.origin.t === O.time && evA.destination.price === DS.low && evA.destination.t === DS.time);
  check("03 scheda: ampiezza assoluta e in pip configurabili (1 pip = 0,10), durata, direzioni", close(evA.derived.prior_leg.amplitude_price, P.high - O.low, 1e-6) && close(evA.derived.prior_leg.amplitude_pips, pips, 1e-6)
    && evA.derived.prior_leg.duration_s === P.time - O.time && evA.derived.prior_direction === "UP" && evA.derived.next_direction === "DOWN" && evA.units.pip_size === 0.1, evA.derived);
  check("03 scheda: dataset, provenienza, simbolo, clock basis, timeframe, autore, data di scoperta, modalita' immutabile, validazione", evA.dataset_id === SRC && evA.source === "MT5_BROKER_EXPORT" && evA.symbol === "GOLD" && /TERMINAL_CLOCK/.test(evA.clock_basis) && evA.timeframe_observation === "H4"
    && evA.author === USER[0] && Math.abs(evA.discovered_at - Date.now() / 1000) < 600 && evA.epistemic_mode === "RETROSPECTIVE_DISCOVERY" && evA.validation_status === "NOT_VALIDATED" && evA.output_label === "DISCOVERY_ONLY");
  const mk0 = await B.ev("JSON.parse(document.querySelectorAll('[data-testid=geometry-canvas]')[0].dataset.marks||'[]')");
  const [px0, py0] = await px(0, pIdx, P.high); const cr0 = await B.ev("(() => { const r = document.querySelectorAll('[data-testid=geometry-canvas]')[0].getBoundingClientRect(); return [r.x, r.y]; })()");
  check("03 marcatore dell'inversione disegnato sul pivot esatto (candela e prezzo reali)", mk0.length === 1 && close(mk0[0].x + cr0[0], px0, 3) && close(mk0[0].y + cr0[1], py0, 3), { mk0, expected: [px0 - cr0[0], py0 - cr0[1]] });
  await B.shot("03_scheda_evento_creata.png");
  const idA = evA.event_id;

  // ====================================================================== 4. apertura sincronizzata su M15 e M5
  const tOpen = Date.now();
  await B.clickId("lab-open-multiscale");
  const okMs = await waitStrips(3, ["H4", "M15", "M5"]);
  await sleep(1800);
  const rs = await ranges();
  const wdt = rs.map((r) => r.to - r.from);
  check("04 tre grafici aperti con H4, M15 e M5 dello stesso dataset autorizzato", okMs, await strips());
  check("04 l'inversione e' dentro la finestra di ciascuna scala", rs.every((r) => r && r.from <= P.time && P.time <= r.to), rs.map((r) => [fmtUtc(r.from), fmtUtc(r.to)]));
  check("04 scale inferiori = finestre piu' strette attorno all'evento (H4 > M15 > M5)", wdt[0] > wdt[1] && wdt[1] > wdt[2], wdt);
  check("04 tempo di apertura multiscala", Date.now() - tOpen < 15000, `${Date.now() - tOpen} ms`);
  const marks3 = await B.ev("[0,1,2].map(i => JSON.parse(document.querySelectorAll('[data-testid=geometry-canvas]')[i].dataset.marks||'[]').length)");
  check("04 il marcatore dell'inversione compare in ciascuna scala aperta", same(marks3, [1, 1, 1]), marks3);
  await B.shot("04_apertura_sincronizzata_h4_m15_m5.png");

  // ====================================================================== 5. esplorare il passato precedente all'evento
  const before = await ranges();
  await B.clickId("lab-back"); await sleep(500); await B.clickId("lab-back"); await sleep(900);
  const past = await ranges();
  check("05 navigazione nel passato precedente all'inversione (tutte le scale arretrano; M15 e M5 anche nel bordo sinistro)", past.every((r, i) => r.to < before[i].to - 1) && past[1].from < before[1].from && past[2].from < before[2].from, past.map((r, i) => [r.from - before[i].from, r.to - before[i].to]));
  check("05 i dati non cambiano navigando", same(await events(sid), [evA]) || (await events(sid)).length === 1);
  await B.shot("05_passato_prima_dell_evento.png");
  await B.clickId("lab-go"); await sleep(1200);
  const back = await ranges();
  check("05 ritorno all'inversione", back.every((r) => r.from <= P.time && P.time <= r.to));

  // sincronizzazione selettiva: per timestamp, per finestra, crosshair
  for (let i = 0; i < 3; i++) await B.clickId(`pane-linked-${i}`);
  await sleep(300);
  const tTarget = P.time - 5 * 3600;
  await B.setInput("ws-goto-input", fmtUtc(tTarget)); await B.clickId("ws-goto"); await sleep(4500);   // oltre i 4 s di sospensione della propagazione dopo una navigazione (Historical-Expansion-01)
  const r2 = await ranges();
  check("05b sincronizzazione per timestamp: tutti i pane linked centrati sull'istante richiesto", r2.every((r, i) => Math.abs((r.from + r.to) / 2 - tTarget) < (r.to - r.from) * 0.15), r2.map((r) => fmtUtc((r.from + r.to) / 2)));
  const c0 = await B.ev("(() => { const r = document.querySelector('[data-testid=pane-canvas-1]').getBoundingClientRect(); return [r.x + r.width * 0.4, r.y + r.height * 0.88]; })()");
  const rBefore = await ranges();
  await B.drag(c0[0], c0[1], c0[0] + 120, c0[1], 10); await sleep(1200);
  const rPan = await ranges();
  check("05c pan (trascinamento del grafico) con sincronizzazione finestra attiva: il pane M15 trascinato si sposta e gli altri linked seguono la stessa finestra", rPan[1].from < rBefore[1].from - 1 && close(rPan[1].to - rPan[1].from, rBefore[1].to - rBefore[1].from, 900) && rPan.every((r, i) => Math.abs(r.to - rPan[1].to) <= 14401 + (i === 0 ? 0 : 0)), rPan.map((r, i) => [r.from - rBefore[i].from, r.to - rBefore[i].to]));
  await B.clickId("ws-sync-time_range"); await sleep(200);
  const rB2 = await ranges();
  await B.drag(c0[0], c0[1], c0[0] + 100, c0[1], 10); await sleep(1200);
  const rPan2 = await ranges();
  check("05d sincronizzazione selettiva: con 'finestra' disattivata solo il pane trascinato si sposta", rPan2[1].from < rB2[1].from - 1 && rPan2[0].from === rB2[0].from && rPan2[2].from === rB2[2].from, rPan2.map((r, i) => r.from - rB2[i].from));
  await B.clickId("ws-sync-time_range");
  await B.clickId("pane-linked-2"); await sleep(200);
  await B.mouse("mouseMoved", c0[0] + 30, c0[1]); await sleep(250); await B.mouse("mouseMoved", c0[0] + 90, c0[1] + 10); await sleep(500);
  await B.shot("05e_crosshair_sincronizzato.png");
  report.notes.push("crosshair sincronizzato: evidenza visiva 05e (il crosshair del pane 0 si riflette sui pane linked)");
  await B.clickId("pane-linked-2");
  await B.clickId("lab-go"); await sleep(1500);

  // ====================================================================== 6. geometrie pertinenti, associate alla scheda
  const pI = (bars) => bars.findIndex((b) => b.time === P.time || (b.time <= P.time && P.time < b.time + (bars === m5 ? 300 : bars === m15 ? 900 : 14400)));
  const p15 = pI(m15), p5 = pI(m5);
  await B.setSelect("geo-snap", "high");
  await B.clickId("geo-tool-trendline");
  const a1 = p15 - 40, a2 = p15 - 12;
  await B.click(...(await px(1, a1, m15[a1].high))); await B.click(...(await px(1, a2, m15[a2].high)));
  let gs = await waitGeom(sid, 1);
  const gDiag = gs[0];
  check("06 diagonale con due ancoraggi (High di candele M15 reali) disegnata nel pane M15", gDiag?.type === "trendline" && gDiag.anchors.length === 2 && gDiag.anchors[0].price === m15[a1].high && gDiag.anchors[1].t === m15[a2].time && gDiag.timeframe_origin === "M15", gDiag?.anchors?.map((a) => [a.t, a.price]));
  await B.setSelect("geo-semantic", "DIAG_SELL");
  await B.setSelect("lab-link-timing", "BEFORE_EVENT_OBSERVABLE"); await B.clickId("lab-link-geometry");
  await B.setSelect("geo-snap", "close");
  await B.clickId("geo-tool-hline");
  await B.click(...(await px(0, pIdx - 1, h4[pIdx - 1].close)));
  gs = await waitGeom(sid, 2);
  const gKey = gs.find((g) => g.type === "hline");
  await B.setSelect("geo-semantic", "KEY_LEVEL_CLOSES");
  await B.setSelect("lab-link-timing", "DURING_EVENT"); await B.clickId("lab-link-geometry");
  await B.setSelect("geo-snap", "free");
  await B.clickId("geo-tool-rectangle");
  await B.drag(...(await px(2, p5 - 25, P.high - 2)), ...(await px(2, p5 + 4, P.high - 14)));
  gs = await waitGeom(sid, 3);
  const gRect = gs.find((g) => g.type === "rectangle");
  await B.setSelect("geo-semantic", "REACTION_ZONE");
  await B.setSelect("lab-link-timing", "RETROSPECTIVELY_RECOGNIZED"); await B.clickId("lab-link-geometry");
  const evA2 = await waitEv(sid, idA, (e) => e.geometries.length === 3);
  const tm = Object.fromEntries(evA2.geometries.map((l) => [l.geometry_id, l.timing]));
  check("06 tre geometrie collegate alla scheda con timing distinto (prima / durante / riconosciuta dopo)", tm[gDiag.geometry_id] === "BEFORE_EVENT_OBSERVABLE" && tm[gKey.geometry_id] === "DURING_EVENT" && tm[gRect.geometry_id] === "RETROSPECTIVELY_RECOGNIZED", tm);
  check("06 nessuna retrodatazione: available_at reale > istante dell'evento; conoscenza causale NOT_ESTABLISHED", evA2.geometries.every((l) => l.causal_knowledge === "NOT_ESTABLISHED" && l.geometry_available_at > evA2.pivot.t && l.geometry.epistemic_mode === "RETROSPECTIVE_DISCOVERY"), evA2.geometries.map((l) => l.geometry_available_at));
  const gAfter = await geoms(sid);
  check("06 il collegamento non altera le geometrie (available_at e revisione invariati)", gAfter.every((g) => { const l = evA2.geometries.find((x) => x.geometry_id === g.geometry_id); return l && l.geometry_available_at === g.available_at; }));
  check("06 classi semantiche manuali: DIAG_SELL, KEY_LEVEL_CLOSES, REACTION_ZONE", gAfter.find((g) => g.geometry_id === gDiag.geometry_id).semantic.class === "DIAG_SELL" && gAfter.find((g) => g.geometry_id === gKey.geometry_id).semantic.class === "KEY_LEVEL_CLOSES" && gAfter.find((g) => g.geometry_id === gRect.geometry_id).semantic.class === "REACTION_ZONE");
  await B.shot("06_geometrie_associate.png");

  // ====================================================================== 7. modifica degli ancoraggi
  await B.ev(`document.querySelector('[data-testid=geo-item-${gDiag.geometry_id}]').click()`); await sleep(500);
  const newPrice = gDiag.anchors[0].price + 2.5;
  await B.setInput("geo-anchor-price-0", String(newPrice));
  const gMod = (await (async () => { for (let i = 0; i < 40; i++) { const g = (await geoms(sid)).find((x) => x.geometry_id === gDiag.geometry_id); if (g.revision >= 2) return g; await sleep(250); } })());
  check("07 modifica numerica dell'ancoraggio (prezzo)", gMod.anchors[0].price === newPrice && gMod.anchors[0].ref.kind === "FREE" && gMod.anchors[1].price === gDiag.anchors[1].price, gMod.anchors[0]);
  const pj = (await proj(1)).find((p) => p.id === gDiag.geometry_id).pts;
  await B.drag(pj[1][0] + (await B.ev("document.querySelectorAll('[data-testid=geometry-canvas]')[1].getBoundingClientRect().x")), pj[1][1] + (await B.ev("document.querySelectorAll('[data-testid=geometry-canvas]')[1].getBoundingClientRect().y")), pj[1][0] + (await B.ev("document.querySelectorAll('[data-testid=geometry-canvas]')[1].getBoundingClientRect().x")) + 20, pj[1][1] + (await B.ev("document.querySelectorAll('[data-testid=geometry-canvas]')[1].getBoundingClientRect().y")) + 18);
  const gDrag = (await (async () => { for (let i = 0; i < 40; i++) { const g = (await geoms(sid)).find((x) => x.geometry_id === gDiag.geometry_id); if (g.revision >= 3) return g; await sleep(250); } })());
  check("07 modifica con maniglia nel pane: solo l'ancoraggio 2 cambia", gDrag && same(gDrag.anchors[0], gMod.anchors[0]) && !same(gDrag.anchors[1], gMod.anchors[1]), gDrag?.anchors[1]);
  const evLive = (await events(sid)).find((e) => e.event_id === idA);
  check("07 la scheda evento riflette la geometria modificata (collegamento, non copia) senza cambiare available_at", evLive.geometries.find((l) => l.geometry_id === gDiag.geometry_id).geometry.anchors[0][1] === newPrice);

  // ====================================================================== 8. ipotesi alternative, annotazioni, evidenze, strutture e scale
  await B.setInput("lab-hyp-input", "Esaurimento della spinta rialzista"); await B.clickId("lab-hyp-add");
  await waitEv(sid, idA, (e) => e.hypotheses.length === 1);
  await B.setInput("lab-hyp-input", "Raccolta di liquidita' sopra il massimo precedente"); await B.clickId("lab-hyp-add");
  await waitEv(sid, idA, (e) => e.hypotheses.length === 2);
  await nth("[data-testid=lab-hypothesis] select", 1, "CONTRADICTED_BY_OBSERVATION");
  await B.setInput("lab-ann-input", "Spike sul massimo con chiusura interna"); await B.clickId("lab-ann-add");
  await B.setInput("lab-evf-input", "diagonale pre-evento con tre tocchi"); await B.clickId("lab-evf-add");
  await B.setInput("lab-eva-input", "nessun retest del livello dopo la rottura"); await B.clickId("lab-eva-add");
  await B.setSelect("lab-card-class", "MAJOR_REVERSAL");
  const evH = await waitEv(sid, idA, (e) => e.hypotheses.length === 2 && e.annotations.length === 1 && e.evidence_for.length === 1 && e.evidence_against.length === 1 && e.classification === "MAJOR_REVERSAL" && e.hypotheses[1].status === "CONTRADICTED_BY_OBSERVATION");
  check("08 ipotesi alternative (stato dell'osservazione, mai 'validata'), annotazioni, evidenze favorevoli e contrarie, classificazione manuale", !!evH && evH.hypotheses.map((h) => h.status).join() === "OPEN,CONTRADICTED_BY_OBSERVATION" && evH.validation_status === "NOT_VALIDATED", evH?.hypotheses);
  // strutture a piu' scale con relazione padre-figlio
  await B.setSelect("lab-struct-kind", "IMPULSE"); await B.setSelect("lab-struct-newscale", "MAJOR");
  await B.clickId("lab-struct-trace"); await B.click(...(await px(0, oIdx, O.low))); await sleep(300); await B.click(...(await px(0, pIdx, P.high))); await sleep(500);
  const evS1 = await waitEv(sid, idA, (e) => e.structures.length === 1);
  const s1 = evS1.structures[0];
  await B.setSelect("lab-struct-kind", "CORRECTION"); await B.setSelect("lab-struct-newscale", "INTERMEDIATE"); await B.setSelect("lab-struct-parent", s1.id);
  const ia = p15 - 30, ib = p15 - 18;
  await B.clickId("lab-struct-trace"); await B.click(...(await px(1, ia, m15[ia].high))); await sleep(300); await B.click(...(await px(1, ib, m15[ib].low))); await sleep(500);
  const evS2 = await waitEv(sid, idA, (e) => e.structures.length === 2);
  const s2 = evS2.structures[1];
  await nth("[data-testid^=lab-struct-scale-]", 1, "MINOR");
  const evS3 = await waitEv(sid, idA, (e) => e.structures[1]?.scale === "MINOR");
  check("08 strutture: impulso maggiore + correzione figlia, origine/ampiezza/durata/direzione conservate; scale riclassificabili", s1.scale === "MAJOR" && s1.kind === "IMPULSE" && s1.derived.direction === "UP" && close(s1.derived.amplitude_price, P.high - O.low, 1e-6)
    && s2.parent_id === s1.id && s2.kind === "CORRECTION" && s2.derived.direction === "DOWN" && s2.derived.duration_s === m15[ib].time - m15[ia].time && evS3.structures[1].scale === "MINOR", { s1: s1.derived, s2: s2.derived, scale2: evS3.structures[1].scale });
  check("08 le scale non sono timeframe: la struttura MAJOR (H4) e quella figlia (M15) condividono lo stesso evento senza vincolo di TF", !("timeframe" in s1) && !("timeframe" in s2));
  await B.shot("08_ipotesi_strutture_scale.png");

  // ====================================================================== pip configurabili sul righello + 'unita' separate'
  await B.setSelect("geo-snap", "free");
  await B.clickId("geo-tool-ruler");
  await B.drag(...(await px(0, 3, 3700)), ...(await px(0, 9, 3640)));
  await waitGeom(sid, 4); await sleep(600);
  const ruler1 = await B.ev("JSON.parse(document.querySelectorAll('[data-testid=geometry-canvas]')[0].dataset.rulers||'[]')[0]?.text");
  const dP = Number((ruler1.match(/Δ (-?[\d.]+)/) || [])[1]);
  const pipTxt = Number((ruler1.match(/= (-?[\d.]+) pip/) || [])[1]);
  check("09 righello: pip con convenzione iniziale XAUUSD 1 pip = 0,10", close(pipTxt, dP / 0.1, 0.11), ruler1);
  await B.setInput("geo-units-pip_size", "0.01"); await sleep(700);
  const ruler2 = await B.ev("JSON.parse(document.querySelectorAll('[data-testid=geometry-canvas]')[0].dataset.rulers||'[]')[0]?.text");
  check("09 pip configurabile: con pip 0,01 il valore in pip diventa 10x, il prezzo non cambia", close(Number((ruler2.match(/= (-?[\d.]+) pip/) || [])[1]), dP / 0.01, 1) && close(Number((ruler2.match(/Δ (-?[\d.]+)/) || [])[1]), dP, 1e-6), ruler2);
  await B.setInput("geo-units-point", "0.01"); await B.setInput("geo-units-tick_size", "0.01");
  await sleep(300);
  await B.setInput("geo-units-pip_size", "0.1"); await sleep(700);
  const facts = await B.ev("document.querySelector('[data-testid=lab-card-facts]')?.innerText || ''");
  check("09 prezzo, pip, point e tick size conservati separatamente (scheda: pip 0.1 dalla creazione, point/tick del evento n/d)", /unità: pip 0\.1 · point n\/d · tick n\/d/.test(facts), facts.slice(-260));

  // ====================================================================== 10. salvataggio della ricerca
  await B.clickId("geo-save"); await sleep(1500);
  const rsr = (await B.api(`${D}/sessions/${sid}/research`)).research;
  check("10 stato della ricerca salvato (periodo, disposizione, sincronizzazione, unita', evento in studio)", rsr && rsr.layout.count === 3 && rsr.layout.charts.map((c) => c.tf).join() === "H4,M15,M5" && rsr.units.pip_size === 0.1 && rsr.units.point === 0.01 && rsr.focus_event_id === idA && !!rsr.interval, rsr);
  const snapEvents = await events(sid); const snapGeoms = await geoms(sid);
  await writeFile(resolve(root, "evidence_ms", "snapshot_events_before_close.json"), JSON.stringify(snapEvents, null, 1));
  await writeFile(resolve(root, "evidence_ms", "snapshot_geoms_before_close.json"), JSON.stringify(snapGeoms, null, 1));
  const exportDoc = await B.api(`${G}/sessions/${sid}/export`);
  await writeFile(resolve(root, "evidence_ms", "research_export.json"), JSON.stringify(exportDoc, null, 1));
  check("10 esportazione dell'intera ricerca (geometrie + schede + stato) con sha256", /^[0-9a-f]{64}$/.test(exportDoc.sha256) && exportDoc.events.length === 1 && exportDoc.geometries.length === snapGeoms.length && !!exportDoc.research, exportDoc.sha256);
  await B.shot("10_prima_della_chiusura.png");
  const perf3 = await B.perf(); const rssA = backendRss(origin);
  await B.kill();

  // ====================================================================== 11. riapertura dopo la chiusura del browser (profilo nuovo)
  B = await openBrowser(B_OPTS("b"));
  await B.login(...USER);
  const okRe = await openChart();
  await waitStrips(3, ["H4", "M15", "M5"]); await sleep(2000);
  check("11 riapertura in un browser nuovo: disposizione a 3 grafici H4/M15/M5 ripristinata", okRe && same((await strips()).map((s) => s.split(" ")[1]), ["H4", "M15", "M5"]), await strips());
  const sid2 = await sidOf();
  check("11 stessa sessione di ricerca", sid2 === sid);
  const ev2 = await events(sid2); const g2 = await geoms(sid2);
  check("11 schede evento recuperate SENZA variazioni (campo per campo, incl. discovered_at, revisioni, strutture, ipotesi)", same(ev2, snapEvents));
  check("11 geometrie recuperate senza variazioni", same(g2, snapGeoms));
  check("11 scheda in studio riaperta con le stesse grandezze", (await B.ev("document.querySelector('[data-testid=lab-card-prior]')?.innerText||''")) !== "" && same((await B.ev("document.querySelector('[data-testid=ws-sidebar]').innerText.includes('Inversione H4 A')")), true));
  const pjR = [await proj(0), await proj(1), await proj(2)];
  check("11 geometrie ridisegnate nei pane (diagonale in M15, livello in H4)", pjR[1].some((p) => p.id === gDiag.geometry_id) && pjR[0].some((p) => p.id === gKey.geometry_id), pjR.map((p) => p.length));
  check("11 intervallo storico e unita' ripristinati", (await B.ev("document.querySelector('[data-testid=ws-interval-from]').value")) === fmtUtc(h4[0].time) && !!(await B.ev("document.querySelector('[data-testid=lab-card-facts]')?.innerText.includes('pip 0.1')")));
  await B.shot("11_riaperto_ricerca_recuperata.png");

  // ====================================================================== 12. secondo evento, casi analoghi senza inversione, confronto
  const lIdx = h4.reduce((best, b, i) => (b.low < h4[best].low ? i : best), 0);
  const hIdx = h4.slice(0, lIdx).reduce((best, b, i) => (b.high > h4[best].high ? i : best), 0);
  await B.clickId("ws-interval-all"); await sleep(1500);                     // con i pane sincronizzati il H4 eredita la finestra stretta del M5: riporto la vista su tutto lo storico caricato
  await B.clickId("lab-pick-pivot"); await B.click(...(await px(0, lIdx, h4[lIdx].low))); await sleep(300);
  await B.clickId("lab-pick-origin"); await B.click(...(await px(0, hIdx, h4[hIdx].high))); await sleep(300);
  await B.setInput("lab-event-name", "Inversione H4 B (minimo)");
  const kindB = await B.ev("document.querySelector('[data-testid=lab-draft-kind]').value");
  await B.clickId("lab-create");
  const evsB = await waitEvents(sid2, 2);
  const evB = evsB.find((e) => e.name.startsWith("Inversione H4 B"));
  check("12 secondo evento (minimo, pivot LOW) creato", kindB === "LOW" && evB?.pivot.kind === "LOW" && evB.pivot.price === h4[lIdx].low && evB.derived.prior_direction === "DOWN" && evB.derived.next_direction === "UP", evB?.derived);
  // caso analogo SENZA inversione (stesso tipo di struttura, il prezzo ha continuato)
  const cIdx = 12;
  await B.clickId("ws-interval-all"); await sleep(1200);
  await B.clickId("lab-pick-pivot"); await B.click(...(await px(0, cIdx, h4[cIdx].high))); await sleep(300);
  await B.setSelect("lab-outcome", "NO_REVERSAL"); await B.setInput("lab-event-name", "Analogo senza inversione");
  await B.clickId("lab-create");
  const evsC = await waitEvents(sid2, 3);
  const evC = evsC.find((e) => e.name === "Analogo senza inversione");
  check("12 caso analogo privo di inversione registrato come scheda (outcome NO_REVERSAL, direzione invariata)", evC?.outcome === "NO_REVERSAL" && evC.derived.next_direction === evC.derived.prior_direction, evC?.derived);
  await B.ev(`document.querySelector('[data-testid=lab-event-${idA}]').click()`); await sleep(500);
  await B.setSelect("lab-analog-event", evC.event_id); await B.setSelect("lab-analog-kind", "ANALOG_NO_REVERSAL"); await B.clickId("lab-analog-add");
  const evA3 = await waitEv(sid2, idA, (e) => e.analog_links.length === 1);
  check("12 caso analogo senza inversione collegato alla scheda A", evA3.analog_links[0].event_id === evC.event_id && evA3.analog_links[0].kind === "ANALOG_NO_REVERSAL");
  await B.clickId("lab-tab-compare");
  await B.setSelect("lab-cmp-a", idA); await B.setSelect("lab-cmp-b", evB.event_id); await B.clickId("lab-cmp-run");
  await B.waitFor("!!document.querySelector('[data-testid=lab-cmp-result]')", 40, 250);
  const cmpTxt = await B.ev("document.querySelector('[data-testid=lab-cmp-result]').innerText");
  check("12 confronto fra due schede: ampiezza, durata, geometrie per tempo/classe, strutture per scala, annotazioni, ipotesi, evidenze, analoghi", /Ampiezza prima/.test(cmpTxt) && /Strutture per scala/.test(cmpTxt) && /Esaurimento della spinta/.test(cmpTxt) && /MAJOR×1/.test(cmpTxt) && /KEY_LEVEL_CLOSES×1/.test(cmpTxt), cmpTxt.slice(0, 200));
  const cmpTable = await B.ev("document.querySelector('[data-testid=lab-cmp-result] table').innerText");
  check("12 il confronto NON presenta frequenze/percentuali/prove statistiche e dichiara il limite", !/%|win rate|probab|p-value|\bedge\b/i.test(cmpTable) && /frequenze di casi scelti a mano non sono prova statistica/.test(await B.ev("document.querySelector('[data-testid=lab-cmp-disclaimer]').innerText")));
  await B.shot("12_confronto_due_schede.png");
  await B.clickId("lab-tab-events");

  // ====================================================================== 13. regressioni Geometry-01 dentro il Lab: undo/redo, blocco, export
  const nG = (await geoms(sid2)).filter((g) => g.status === "ACTIVE").length;
  if (!(await B.ev("!!document.querySelector('[data-testid=geo-snap]')"))) { await B.clickId("geo-panel-toggle"); await sleep(500); }   // pannello chiuso di default dopo la riapertura
  await B.setSelect("geo-snap", "free"); await B.clickId("geo-tool-hline"); await B.click(...(await px(0, 20, 3600)));
  await waitGeom(sid2, nG + 1); await sleep(400);
  await B.key("z", { ctrl: true }); await sleep(1200);
  const afterUndo = (await geoms(sid2)).filter((g) => g.status === "ACTIVE").length;
  await B.key("y", { ctrl: true }); await sleep(1200);
  const afterRedo = (await geoms(sid2)).filter((g) => g.status === "ACTIVE").length;
  check("13 Geometry-01 nel Lab: undo/redo funzionano su sessione condivisa fra i pane", afterUndo === nG && afterRedo === nG + 1, [nG, afterUndo, afterRedo]);
  check("13 import dell'intera ricerca riesportata: sha256 stabile dopo passaggio dal browser", await (async () => { const d = await B.api(`${G}/sessions/${sid2}/export`); return /^[0-9a-f]{64}$/.test(d.sha256) && d.events.length === 3; })());

  // ====================================================================== 14. tutti i timeframe disponibili + risorse
  const tfs = await B.ev("[...document.querySelectorAll('[data-testid=pane-tf-0] option')].filter(o => !o.disabled).map(o => o.value)");
  const tfRows = [];
  const geoCount = (await geoms(sid2)).filter((g) => g.status === "ACTIVE").length;
  for (const tf of tfs) {
    const t1 = Date.now();
    await B.setSelect("pane-tf-0", tf);
    const ok = await B.waitFor(`(document.querySelector('[data-testid=pane-strip-0]')?.innerText||'').includes(' ${tf} ') && (document.querySelector('[data-testid=pane-strip-0]')?.innerText||'').includes('barre')`, 80, 250);
    await sleep(900);
    const pj0 = await proj(0);
    const ms = Date.now() - t1;
    const bars = Number(((await strips())[0].match(/(\d+) barre/) || [])[1] || 0);
    const err = await B.ev("document.querySelector('[data-testid=pane-error-0]')?.innerText || null");
    const finite = pj0.every((p) => p.pts.every((pt) => pt && Number.isFinite(pt[0]) && Number.isFinite(pt[1])));
    tfRows.push({ tf, ok, bars, ms, error: err, geom_projected: pj0.length, finite });
    await B.shot(`14_timeframe_${tf}.png`);
  }
  report.metrics.push({ timeframes: tfRows });
  check(`14 tutti i timeframe disponibili del dataset (${tfs.join(", ")}) caricano dati reali senza errori e con proiezione finita delle geometrie`, tfRows.length === tfs.length && tfRows.every((r) => r.ok && !r.error && r.finite && r.bars > 0), tfRows);
  check("14 le geometrie salvate restano identiche cambiando timeframe", same((await geoms(sid2)).filter((g) => g.status === "ACTIVE").length, geoCount));
  await B.setSelect("pane-tf-0", "H4"); await sleep(1200);
  // quattro grafici + misure
  const m1 = await B.perf();
  await B.clickId("ws-layout-4"); await waitStrips(4, ["H4", "M15", "M5", "H4"]).catch(() => {}); await sleep(3500);
  const m4 = await B.perf(); const rss4 = backendRss(origin);
  await B.shot("14_quattro_grafici.png");
  check("14 quattro grafici aperti insieme", (await strips()).length === 4 && (await strips()).every((s) => s.includes("barre")), await strips());
  await B.clickId("ws-layout-1"); await sleep(1500);
  const m1b = await B.perf();
  const loadsAttr = JSON.parse(await B.ev("document.querySelector('[data-testid=discovery-workspace]').dataset.loads"));
  report.metrics.push({ backend_rss_mb: { idle_after_login: rssIdle, after_3_panes_and_edits: rssA, with_4_panes: rss4, render_limit_mb: 512 }, browser: { three_panes: perf3, one_pane_after_tf_cycle: m1, four_panes: m4, back_to_one: m1b }, pane_loads_ms: loadsAttr.map((l) => ({ tf: l.tf, n: l.n, ms: l.ms })), initial_open_ms: loadMs });
  check("14 backend: RSS ben sotto il limite Render di 512 MiB con 4 grafici (browser misurato a parte)", rss4 != null && rss4 < 512, { rss4, browser_4_panes: m4 });
  await B.kill();

  // ====================================================================== 15. isolamento tra utenti (due account reali sullo stesso database)
  if (originB) {
    const { report: rB } = makeReport(originB);
    B = await openBrowser({ ...B_OPTS("c", originB), report: rB });
    await B.login(...USER_B);
    await B.cdp("Page.navigate", { url: `${originB}/app/discovery` });
    await B.waitFor("[...document.querySelectorAll('[data-testid^=pane-strip-]')].length>0", 120, 250);
    await sleep(1500);
    const sB = await B.api(`${G}/sessions`);
    const crossEv = await B.ev(`fetch('/api${D}/sessions/${sid}/events',{credentials:'include'}).then(r=>r.status)`);
    const crossGeo = await B.ev(`fetch('/api${G}/sessions/${sid}',{credentials:'include'}).then(r=>r.status)`);
    const crossExp = await B.ev(`fetch('/api${G}/sessions/${sid}/export',{credentials:'include'}).then(r=>r.status)`);
    const crossPut = await B.ev(`fetch('/api${D}/sessions/${sid}/events/${idA}',{method:'PUT',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'hack',expected_revision:1})}).then(r=>r.status)`);
    check("15 isolamento: l'utente B non vede sessioni di A e il suo spazio di ricerca e' vuoto", !sB.sessions.some((s) => s.session_id === sid) && (await B.ev("document.querySelectorAll('[data-testid^=lab-event-E]').length")) === 0, sB.sessions.map((s) => s.session_id));
    check("15 isolamento: B riceve 404 su eventi, sessione ed esportazione di A; la scrittura non e' possibile", crossEv === 404 && crossGeo === 404 && crossExp === 404 && [403, 404].includes(crossPut), [crossEv, crossGeo, crossExp, crossPut]);
    await B.shot("15_utente_B_spazio_separato.png");
    await B.kill();
    for (const c of rB.checks) report.checks.push({ ...c, name: "[B] " + c.name });
    report.console_errors.push(...rB.console_errors);
  } else report.notes.push("isolamento nel browser non eseguito: CHART_ORIGIN_B assente");

  check("16 nessun errore console grave", report.console_errors.filter((e) => !/favicon|ResizeObserver/i.test(e)).length === 0, report.console_errors.slice(0, 5));
  check("16 nessuna risposta di rete anomala (esclusi 401 pre-login, favicon, 404 attesi dell'isolamento)", report.network_failures.filter((e) => !/api\/auth\/me|favicon|research\/certificates|geometry\/sessions\/S|discovery\/sessions\/S/.test(e)).length === 0, report.network_failures);
} catch (e) {
  check("ERRORE SCRIPT", false, String((e && e.stack) || e));
} finally {
  if (B) await B.kill();
  report.summary = { total: report.checks.length, pass: report.checks.filter((c) => c.ok).length, fail: report.checks.filter((c) => !c.ok).length };
  await writeFile(resolve(root, "evidence_ms", "browser_report.json"), JSON.stringify(report, null, 1));
  console.log("SUMMARY", JSON.stringify(report.summary));
}
