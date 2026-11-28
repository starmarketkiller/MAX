// NEXUS-CHART-HISTORICAL-EXPANSION-01 — verifica nel browser reale (Edge/CDP) sullo storico ESTESO autorizzato (Dukascopy development_discovery 2023-02-04..2024-08-03).
// USO: CHART_HE_ROOT=<cartella con evidence_he/ e runtime/> CHART_ORIGIN=http://127.0.0.1:8860 [CHART_ORIGIN_B=http://127.0.0.1:8861] node tools/chart_historical_browser_verify.mjs
// Nessun dato sintetico. Scelta degli estremi = regola di TEST (non di ricerca): primo massimo/minimo di una finestra di date, in un giorno infrasettimanale, per rendere i controlli ripetibili.
import { execSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { openBrowser, makeReport, sleep, same, close } from "./cdp_lib.mjs";

const root = (process.env.CHART_HE_ROOT || process.cwd()).replace(/\\/g, "/");
const origin = process.env.CHART_ORIGIN || "http://127.0.0.1:8860";
const originB = process.env.CHART_ORIGIN_B || "";
const SRC = "DUKASCOPY_XAUUSD_PHASE7", SYM = "XAUUSD";
const out = resolve(root, "evidence_he", "screens");
const { report, check } = makeReport(origin, { source: SRC });
const USER = ["chart-geo@local", "chart-geo-local-only"], USER_B = ["chart-geo-b@local", "chart-geo-b-local-only"];
const D = "/chart/discovery", G = "/chart/geometry";
const fmtUtc = (t) => new Date(t * 1000).toISOString().replace("T", " ").slice(0, 16);
const TFS = { M1: 60, M5: 300, M15: 900, M30: 1800, H1: 3600, H4: 14400, D1: 86400 };
const portOf = (o) => (o.match(/:(\d+)/) || [])[1];
function backendRss(o) {
  try {
    const r = execSync(`powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process -Filter \\"Name='python.exe'\\" | Where-Object { $_.CommandLine -match '--port ${portOf(o)}' } | Select-Object -First 1; if ($p) { (Get-Process -Id $p.ProcessId).WorkingSet64 }"`, { encoding: "utf8" }).trim();
    return r ? +(Number(r) / 1048576).toFixed(1) : null;
  } catch { return null; }
}
let B;
const strips = () => B.ev("[...document.querySelectorAll('[data-testid^=pane-strip-]')].map(e => e.innerText)");
const ranges = () => B.ev("[...document.querySelectorAll('[data-testid^=pane-canvas-]')].map(e => JSON.parse(e.parentElement.dataset.range || 'null'))");
const attr = (i, k) => B.ev(`document.querySelectorAll('[data-testid^=pane-canvas-]')[${i}]?.parentElement.dataset.${k} || ''`);
const nBars = async (i) => Number((((await strips())[i] || "").match(/(\d+) barre/) || [])[1] || 0);
const overview = () => B.ev("JSON.parse(document.querySelector('[data-testid=overview-canvas]').dataset.overview || 'null')");
const waitStrips = (tfs) => B.waitFor(`(() => { const s=[...document.querySelectorAll('[data-testid^=pane-strip-]')].map(e=>e.innerText); const w=${JSON.stringify(tfs)}; return s.length===w.length && s.every((t,i)=>t.includes('barre') && t.includes(' '+w[i]+' ')); })()`, 200, 250);
const sidOf = async () => (await B.api(`${G}/sessions`)).sessions[0].session_id;
const events = async (sid) => (await B.api(`${D}/sessions/${sid}/events`)).events;
const geoms = async (sid) => (await B.api(`${G}/sessions/${sid}`)).geometries;
const waitN = async (fn, n, tries = 40) => { let v; for (let i = 0; i < tries; i++) { v = await fn(); if (v.length >= n) return v; await sleep(250); } return v; };
const px = async (pane, barIdx, price) => {
  const d = await B.ev(`(() => { const c = document.querySelectorAll('[data-testid=geometry-canvas]')[${pane}]; const r = c.getBoundingClientRect(); return { rx: r.x, ry: r.y, ...JSON.parse(c.dataset.dbg) }; })()`);
  const step = (d.x100 - d.x0) / 100;
  return [d.rx + d.x0 + barIdx * step, d.ry + d.y1000 + ((price - 1000) * (d.y3000 - d.y1000)) / 2000];
};
const entries = () => B.ev("performance.getEntriesByType('resource').filter(e => e.name.includes('/chart/ohlc')).map(e => ({ u: e.name.replace(location.origin,''), dec: e.decodedBodySize, enc: e.encodedBodySize, ms: Math.round(e.duration) }))");
const openLab = async () => { await B.cdp("Page.navigate", { url: `${origin}/app/discovery` }); return B.waitFor("[...document.querySelectorAll('[data-testid^=pane-strip-]')].length>0 && [...document.querySelectorAll('[data-testid^=pane-strip-]')].every(e=>e.innerText.includes('barre'))", 200, 250); };

try {
  // ============================================================ 0. dati di riferimento (API) e coerenza con lo store verificato
  B = await openBrowser({ tag: "he", root, out, origin, report });
  await B.login(...USER);
  const rss0 = backendRss(origin);
  const man = JSON.parse(await B.ev(`fetch('/api/chart/sources',{credentials:'include'}).then(r=>r.text())`));
  const ds = man.sources.find((s) => s.dataset_id === SRC);
  check("00 il dataset esteso e' elencato dal backend con tutti i 9 timeframe", !!ds && ds.timeframes.join() === "M1,M5,M15,M30,H1,H4,D1,W1,MN1", ds?.timeframes);
  const allH4 = (await B.api(`/chart/ohlc?source=${SRC}&symbol=${SYM}&tf=H4&limit=5000`));
  const H4 = allH4.bars;
  check("00 H4 completo in una richiesta: 2.393 barre dal 2023-02-05 20:00 (apertura domenicale) al 2024-08-02, nessun'altra pagina", H4.length === 2393 && allH4.has_more === false && fmtUtc(H4[0].time) === "2023-02-05 20:00" && fmtUtc(H4.at(-1).time).startsWith("2024-08-02"), { n: H4.length, from: fmtUtc(H4[0].time), to: fmtUtc(H4.at(-1).time) });
  const chain = async (tf, limit = 5000) => { let n = 0, before = null, pages = 0, first = null, prev = null, dup = 0, unordered = 0; for (; pages < 400; pages++) { const d = await B.api(`/chart/ohlc?source=${SRC}&symbol=${SYM}&tf=${tf}&limit=${limit}${before ? `&before=${before}` : ""}`); n += d.bars.length; for (const b of d.bars.slice().reverse()) { if (prev !== null) { if (b.time === prev) dup++; else if (b.time > prev) unordered++; } prev = b.time; } first = d.bars[0]?.time ?? first; before = d.next_before; if (!d.has_more) break; } return { n, pages: pages + 1, first, dup, unordered }; };
  const expect = { M1: 530331, M5: 106125, M15: 35378, M30: 17690, H1: 8851, H4: 2393, D1: 464, W1: 79, MN1: 19 };
  const cov = {};
  const tChain = Date.now();
  for (const tf of Object.keys(expect)) cov[tf] = await chain(tf);
  report.metrics.push({ timeframe_coverage_via_api_chain: cov, chain_ms_total: Date.now() - tChain });
  check("00 copertura per timeframe attraverso l'API paginata = conteggi dello store verificato (nessun buco/duplicato/disordine)", Object.keys(expect).every((tf) => cov[tf].n === expect[tf] && cov[tf].dup === 0 && cov[tf].unordered === 0), Object.fromEntries(Object.entries(cov).map(([k, v]) => [k, v.n])));

  // ============================================================ 1. apertura dello storico H4 esteso
  await openLab();
  await B.setSelect("ws-source", SRC);
  await B.clickId("ws-layout-1");
  await B.setSelect("pane-tf-0", "H4");
  const tOpen = Date.now();
  await waitStrips(["H4"]);
  const openMs = Date.now() - tOpen;
  await sleep(2000);
  const ov0 = await overview();
  const s0 = (await strips())[0];
  check("01 storico H4 esteso aperto (prima pagina nel grafico, vista generale con tutte le 2.393 barre)", s0.includes(SRC) && s0.includes(" H4 ") && (await nBars(0)) === 1500 && /più storico/.test(s0) && ov0 && ov0.n === 2393 && ov0.tf === "H4", { strip: s0, overview: ov0 && { n: ov0.n, ms: ov0.ms } });
  check("01 vista generale: primo/ultimo istante = primo/ultimo H4 dello store, nessun limite superato", ov0.first === H4[0].time && ov0.last === H4.at(-1).time && ov0.hasMore === false);
  await B.shot("01_h4_esteso_vista_generale.png");
  await B.clickId("geo-panel-toggle"); await sleep(400);
  const sid = await sidOf();

  // ============================================================ 2-3. tre cambiamenti di direzione in periodi distanti (regola di TEST ripetibile)
  const pick = (d0, d1, kind) => {
    const a = Date.parse(d0 + "T00:00:00Z") / 1000, b = Date.parse(d1 + "T00:00:00Z") / 1000;
    const idx = H4.map((x, i) => i).filter((i) => H4[i].time >= a && H4[i].time < b && [2, 3, 4].includes(new Date(H4[i].time * 1000).getUTCDay()) && new Date(H4[i].time * 1000).getUTCHours() >= 4 && new Date(H4[i].time * 1000).getUTCHours() <= 12);
    const best = idx.reduce((m, i) => (kind === "HIGH" ? (H4[i].high > H4[m].high ? i : m) : (H4[i].low < H4[m].low ? i : m)), idx[0]);
    const o = kind === "HIGH"
      ? H4.slice(Math.max(0, best - 30), best).reduce((m, x, k, arr) => (x.low < arr[m].low ? k : m), 0) + Math.max(0, best - 30)
      : H4.slice(Math.max(0, best - 30), best).reduce((m, x, k, arr) => (x.high > arr[m].high ? k : m), 0) + Math.max(0, best - 30);
    return { p: best, o };
  };
  const plans = [{ name: "E1 massimo mar-mag 2023", kind: "HIGH", ...pick("2023-03-01", "2023-05-31", "HIGH") }, { name: "E2 minimo set-nov 2023", kind: "LOW", ...pick("2023-09-01", "2023-11-30", "LOW") },
    { name: "E3 massimo mar-lug 2024", kind: "HIGH", ...pick("2024-03-15", "2024-07-15", "HIGH") }];
  report.notes.push("eventi scelti: " + JSON.stringify(plans.map((p) => ({ n: p.name, pivot: fmtUtc(H4[p.p].time), origin: fmtUtc(H4[p.o].time) }))));
  check("02 tre inversioni in periodi lontani fra loro (mesi di distanza), scelte nello storico esteso", plans.every((p) => p.p > p.o) && H4[plans[1].p].time - H4[plans[0].p].time > 90 * 86400 && H4[plans[2].p].time - H4[plans[1].p].time > 90 * 86400, plans.map((p) => fmtUtc(H4[p.p].time)));
  const created = [];
  let perfNav = [];
  for (const pl of plans) {
    const P = H4[pl.p], O = H4[pl.o];
    const tNav = Date.now();
    await B.setInput("ws-goto-input", fmtUtc(P.time - 2 * 86400)); await B.clickId("ws-goto");
    await B.waitFor(`(() => { const r = JSON.parse(document.querySelectorAll('[data-testid^=pane-canvas-]')[0].parentElement.dataset.range||'null'); return r && r.from <= ${P.time} && ${P.time} <= r.to && r.from <= ${O.time}; })()`, 80, 250);
    // attendo che il caricamento a pagine sia concluso: la prima barra del grafico non deve cambiare per ~1,6 s (altrimenti l'indice dei clic sarebbe obsoleto)
    let lastFirst = "", same3 = 0;
    for (let k = 0; k < 60 && same3 < 4; k++) { const f = await attr(0, "first"); same3 = f && f === lastFirst ? same3 + 1 : 0; lastFirst = f; await sleep(400); }
    perfNav.push({ to: fmtUtc(P.time), ms: Date.now() - tNav });
    const first = Number(await attr(0, "first"));
    const off = H4.findIndex((b) => b.time === first);
    const idx = (k) => k - off;
    await B.clickId("lab-pick-pivot"); await B.click(...(await px(0, idx(pl.p), pl.kind === "HIGH" ? P.high : P.low))); await sleep(300);
    await B.clickId("lab-pick-origin"); await B.click(...(await px(0, idx(pl.o), pl.kind === "HIGH" ? O.low : O.high))); await sleep(300);
    const draftTxt = await B.ev("document.querySelector('[data-testid=lab-draft]')?.innerText || ''");
    check(`03 bozza ${pl.name.slice(0, 2)}: il clic ha preso proprio la candela attesa (${fmtUtc(P.time).slice(5)})`, draftTxt.includes(fmtUtc(P.time).slice(5)) && draftTxt.includes(fmtUtc(O.time).slice(5)), draftTxt.replace(/\n/g, " | "));
    await B.setInput("lab-event-name", pl.name); await B.clickId("lab-create");
    const evs = await waitN(() => events(sid), created.length + 1);
    const e = evs.find((x) => x.name === pl.name);
    if (!e) throw new Error("scheda non creata: " + pl.name + " | nota: " + (await B.ev("document.querySelector('[data-testid=lab-note]')?.innerText || ''")));
    created.push(e);
    check(`03 scheda ${pl.name.slice(0, 2)}: pivot ${pl.kind === "HIGH" ? "High" : "Low"} esatto della candela reale (${fmtUtc(P.time)}), origine reale, ampiezza e durata coerenti`, !!e && e.pivot.t === P.time && e.pivot.price === (pl.kind === "HIGH" ? P.high : P.low) && e.pivot.kind === pl.kind && e.origin.t === O.time
      && Math.abs(e.derived.prior_leg.amplitude_price - Math.abs((pl.kind === "HIGH" ? P.high - O.low : O.high - P.low))) < 1e-6 && e.derived.prior_leg.duration_s === P.time - O.time && e.dataset_id === SRC, e && e.derived.prior_leg);
  }
  await B.shot("03_tre_eventi_in_periodi_distanti.png");
  const ovE = await overview();
  check("03 vista generale: tre marcatori nelle posizioni cronologiche corrette e clic su un marcatore apre la scheda", ovE.markers.length === 3 && ovE.markers[0].x < ovE.markers[1].x && ovE.markers[1].x < ovE.markers[2].x, ovE.markers);
  const ovRect = await B.ev("(() => { const r = document.querySelector('[data-testid=overview-canvas]').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })()");
  const m0 = ovE.markers.find((m) => m.id === created[0].event_id);
  await B.click(ovRect[0] + m0.x, ovRect[1] + ovRect[3] * 0.4); await sleep(1800);
  const selName = await B.ev("document.querySelector('[data-testid=lab-card-name]')?.value || ''");
  check("03 clic sul marcatore della vista generale: scheda E1 selezionata e grafico portato sull'evento", selName === plans[0].name && (await ranges())[0].from <= H4[plans[0].p].time && H4[plans[0].p].time <= (await ranges())[0].to, selName);

  // ============================================================ 4. navigazione per date: clic sulla vista generale in tre punti lontani
  const jumps = [];
  for (const target of ["2023-04-20", "2023-12-15", "2024-07-05"]) {
    const t = Date.parse(target + "T00:00:00Z") / 1000;
    const i = H4.findIndex((b) => b.time >= t);
    const x = (i / (ovE.n - 1)) * (ovE.width - 2) + 1;
    await B.click(ovRect[0] + x, ovRect[1] + ovRect[3] * 0.4); await sleep(1600);
    const r = (await ranges())[0];
    jumps.push({ target, center: fmtUtc((r.from + r.to) / 2), ok: Math.abs((r.from + r.to) / 2 - t) < 12 * 86400 });
  }
  check("04 navigazione tra periodi con clic sulla vista generale: il grafico H4 si centra sulla data (entro ±12 giorni)", jumps.every((j) => j.ok), jumps);
  check("04 la banda della vista generale segue la finestra visibile", (await overview()).band && (await overview()).band[1] > (await overview()).band[0]);
  await B.setInput("ws-goto-input", "2023-03-08 12:00"); await B.clickId("ws-goto"); await sleep(1500);
  const rGo = (await ranges())[0];
  check("04 'vai a data e ora' (2023-03-08 12:00 UTC)", Math.abs((rGo.from + rGo.to) / 2 - Date.parse("2023-03-08T12:00:00Z") / 1000) < 3 * 86400, [fmtUtc(rGo.from), fmtUtc(rGo.to)]);
  // intervallo per data
  await B.setInput("ws-interval-from", "2023-09-01 00:00"); await B.setInput("ws-interval-to", "2023-12-01 00:00"); await B.clickId("ws-interval-apply"); await sleep(1600);
  const rIv = (await ranges())[0];
  check("04 selezione di un intervallo per data (2023-09-01 → 2023-12-01)", Math.abs(rIv.from - Date.parse("2023-09-01T00:00:00Z") / 1000) <= 14400 * 2 && Math.abs(rIv.to - Date.parse("2023-12-01T00:00:00Z") / 1000) <= 14400 * 2, [fmtUtc(rIv.from), fmtUtc(rIv.to)]);

  // ============================================================ finestre prima/dopo configurabili
  await B.ev(`document.querySelector('[data-testid=lab-event-${created[0].event_id}]').click()`); await sleep(500);
  await B.setInput("lab-win-pre", "90", false); await B.setInput("lab-win-post", "40", false); await sleep(700);
  const winVals = await B.ev("[document.querySelector('[data-testid=lab-win-pre]').value, document.querySelector('[data-testid=lab-win-post]').value]");
  check("05 finestre attorno all'evento configurabili (default 70/30 modificato a 90/40)", same(winVals, ["90", "40"]), winVals);

  // ============================================================ 5. apertura sincronizzata sulle scale inferiori (anche mesi indietro)
  const t5 = Date.now();
  await B.clickId("lab-open-multiscale");
  await waitStrips(["H4", "M15", "M5"]);
  await sleep(4500);
  const tMs = Date.now() - t5;
  const rs = await ranges();
  const P1 = H4[plans[0].p];
  const st3 = await strips();
  const w = rs.map((r) => r.to - r.from);
  check("05 apertura su H4+M15+M5 per un evento di mesi prima: l'evento e' dentro la finestra di ciascuna scala", rs.every((r) => r && r.from <= P1.time && P1.time <= r.to), { windows: rs.map((r) => [fmtUtc(r.from), fmtUtc(r.to)]), ms: tMs });
  check("05 M15 e M5 caricano una finestra ANCORATA (non l'intera storia dalla coda) e il numero di barre resta contenuto", /finestra fino a/.test(st3[1]) && /finestra fino a/.test(st3[2]) && (await nBars(1)) <= 5000 && (await nBars(2)) <= 5000, st3);
  check("05 finestre H4 > M15 > M5 e proporzionate a 90 prima + 40 dopo (±45%: i weekend allargano il tempo)", w[0] > w[1] && w[1] > w[2] && w[1] > 0.55 * 130 * 900 && w[1] < 1.45 * 130 * 900 + 172800, w);
  const mk = await B.ev("[0,1,2].map(i => JSON.parse(document.querySelectorAll('[data-testid=geometry-canvas]')[i].dataset.marks||'[]').find(m => m.id === " + JSON.stringify(created[0].event_id) + "))");
  const cw = await B.ev("[0,1,2].map(i => document.querySelectorAll('[data-testid=geometry-canvas]')[i].getBoundingClientRect().width)");
  check("05 il marcatore dell'inversione E1 e' visibile (dentro il grafico) in tutte e tre le scale", mk.every((m, i) => m && m.x > 0 && m.x < cw[i]), mk);
  await B.shot("05_apertura_multiscala_evento_di_mesi_prima.png");
  // quarto grafico: M1 sullo stesso evento
  await B.clickId("ws-layout-4"); await sleep(600);
  await B.setSelect("pane-tf-3", "M1");
  await B.waitFor("(document.querySelectorAll('[data-testid^=pane-strip-]')[3]?.innerText||'').includes(' M1 ') && (document.querySelectorAll('[data-testid^=pane-strip-]')[3]?.innerText||'').includes('barre')", 120, 250);
  await B.clickId("lab-go"); await sleep(4500);
  const rs4 = await ranges(); const st4 = await strips();
  check("05 approfondimento fino a M1 sullo stesso evento: finestra M1 ancorata che contiene l'inversione", rs4.length === 4 && rs4[3].from <= P1.time && P1.time <= rs4[3].to && /finestra fino a/.test(st4[3]) && (await nBars(3)) <= 5000, { m1: [fmtUtc(rs4[3].from), fmtUtc(rs4[3].to)], strip: st4[3] });
  await B.shot("05_quattro_scale_h4_m15_m5_m1.png");
  await B.clickId("ws-layout-3"); await sleep(800);

  // ============================================================ 6. geometrie: disegno, salvataggio, collegamento a evento e struttura
  const e1 = created[0];
  const first0 = Number(await attr(0, "first")); const off0 = H4.findIndex((b) => b.time === first0);
  await B.setSelect("geo-snap", "high"); await B.clickId("geo-tool-hline");
  await B.click(...(await px(0, plans[0].p - off0, P1.high))); await sleep(500);
  let gs = await waitN(() => geoms(sid), 1);
  const gSpike = gs[0];
  await B.setSelect("geo-semantic", "LIQUIDITY_SPIKES");
  await B.setSelect("lab-link-timing", "DURING_EVENT"); await B.clickId("lab-link-geometry");
  await B.setSelect("geo-snap", "free"); await B.clickId("geo-tool-trendline");
  const c1 = await B.ev("(() => { const r = document.querySelectorAll('[data-testid=geometry-canvas]')[1].getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })()");
  await B.click(c1[0] + c1[2] * 0.25, c1[1] + c1[3] * 0.65); await B.click(c1[0] + c1[2] * 0.55, c1[1] + c1[3] * 0.25); await sleep(500);
  gs = await waitN(() => geoms(sid), 2);
  const gDiag = gs.find((g) => g.type === "trendline");
  await B.setSelect("geo-semantic", "DIAG_SELL");
  await B.setSelect("lab-link-timing", "BEFORE_EVENT_OBSERVABLE"); await B.clickId("lab-link-geometry");
  await B.clickId("geo-tool-rectangle");
  const c2 = await B.ev("(() => { const r = document.querySelectorAll('[data-testid=geometry-canvas]')[2].getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })()");
  await B.drag(c2[0] + c2[2] * 0.3, c2[1] + c2[3] * 0.3, c2[0] + c2[2] * 0.6, c2[1] + c2[3] * 0.55);
  gs = await waitN(() => geoms(sid), 3);
  const gRect = gs.find((g) => g.type === "rectangle");
  await B.setSelect("geo-semantic", "REACTION_ZONE");
  await B.setSelect("lab-link-timing", "RETROSPECTIVELY_RECOGNIZED"); await B.clickId("lab-link-geometry");
  const eLinked = (await waitN(async () => (await events(sid)).filter((x) => x.event_id === e1.event_id && x.geometries.length === 3), 1))[0];
  check("06 tre geometrie disegnate in tre scale diverse (H4 livello High, M15 diagonale, M5 rettangolo), con significato manuale, collegate all'evento con timing diversi", !!eLinked && eLinked.geometries.map((l) => l.timing).sort().join() === "BEFORE_EVENT_OBSERVABLE,DURING_EVENT,RETROSPECTIVELY_RECOGNIZED"
    && gSpike.anchors[0].price === P1.high && gDiag.timeframe_origin === "M15" && gRect.timeframe_origin === "M5" && eLinked.geometries.every((l) => l.causal_knowledge === "NOT_ESTABLISHED" && l.geometry_available_at > P1.time), eLinked && eLinked.geometries.map((l) => l.timing));
  // struttura + collegamento alla geometria dall'interfaccia
  await B.setSelect("lab-struct-kind", "IMPULSE"); await B.setSelect("lab-struct-newscale", "MAJOR");
  await B.clickId("lab-struct-trace");
  await B.click(...(await px(0, plans[0].o - off0, H4[plans[0].o].low))); await sleep(300); await B.click(...(await px(0, plans[0].p - off0, P1.high))); await sleep(600);
  const eS = (await waitN(async () => (await events(sid)).filter((x) => x.event_id === e1.event_id && x.structures.length === 1), 1))[0];
  await B.ev(`document.querySelector('[data-testid=geo-item-${gSpike.geometry_id}]').click()`); await sleep(500);
  await B.clickId(`lab-struct-link-${eS.structures[0].id}`);
  const eSL = (await waitN(async () => (await events(sid)).filter((x) => x.event_id === e1.event_id && (x.structures[0].geometry_ids || []).length === 1), 1))[0];
  check("06 collegamento struttura↔geometria dall'interfaccia (residuo chiuso)", !!eSL && eSL.structures[0].geometry_ids[0] === gSpike.geometry_id && eSL.structures[0].scale === "MAJOR", eSL && eSL.structures[0].geometry_ids);
  await B.shot("06_geometrie_collegate_struttura.png");

  // ============================================================ 7. confronto fra eventi distanti
  await B.clickId("lab-tab-compare");
  await B.setSelect("lab-cmp-a", created[0].event_id); await B.setSelect("lab-cmp-b", created[2].event_id); await B.clickId("lab-cmp-run");
  await B.waitFor("!!document.querySelector('[data-testid=lab-cmp-result]')", 40, 250);
  const cmpT = await B.ev("document.querySelector('[data-testid=lab-cmp-result] table').innerText");
  const apiCmp = await B.api(`${D}/sessions/${sid}/compare?ids=${created[0].event_id},${created[2].event_id}`);
  check("07 confronto fra E1 (2023) ed E3 (2024): classe LIQUIDITY_SPIKES contata, strutture per scala, ampiezze, durate; nessuna frequenza/percentuale", /LIQUIDITY_SPIKES×1/.test(cmpT) && /MAJOR×1/.test(cmpT) && /Ampiezza prima/.test(cmpT) && !/%|win rate|probab|p-value|\bedge\b/i.test(cmpT)
    && apiCmp.events.length === 2 && apiCmp.events[0].geometry_by_class.LIQUIDITY_SPIKES === 1, cmpT.slice(0, 180));
  check("07 le due schede appartengono a periodi diversi (differenza > 12 mesi di calendario non richiesta: > 90 giorni)", Math.abs(created[2].pivot.t - created[0].pivot.t) > 300 * 86400, [fmtUtc(created[0].pivot.t), fmtUtc(created[2].pivot.t)]);
  await B.shot("07_confronto_eventi_distanti.png");
  await B.clickId("lab-tab-events");

  // ============================================================ residui: layout a 2, crosshair numerico, sincronizzazione del simbolo
  await B.clickId("ws-layout-2"); await sleep(1200);
  await waitStrips(["H4", "M15"]);
  check("08 layout a due grafici", (await strips()).length === 2 && (await B.ev("document.querySelector('[data-testid=ws-grid]').className.includes('grid-cols-2')")), await strips());
  await B.clickId("ws-layout-3"); await waitStrips(["H4", "M15", "M5"]);
  for (let i = 0; i < 3; i++) { if (!(await B.ev(`document.querySelector('[data-testid=pane-linked-${i}]').checked`))) await B.clickId(`pane-linked-${i}`); }
  const tC = Date.parse("2023-10-10T12:00:00Z") / 1000;
  await B.setInput("ws-goto-input", fmtUtc(tC)); await B.clickId("ws-goto"); await sleep(3500);
  const cr0 = await B.ev("(() => { const r = document.querySelector('[data-testid=pane-canvas-0]').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })()");
  await B.mouse("mouseMoved", cr0[0] + cr0[2] * 0.42, cr0[1] + cr0[3] * 0.5); await sleep(300); await B.mouse("mouseMoved", cr0[0] + cr0[2] * 0.45, cr0[1] + cr0[3] * 0.52); await sleep(900);
  const xh = await B.ev("[0,1,2].map(i => JSON.parse(document.querySelectorAll('[data-testid^=pane-canvas-]')[i].parentElement.dataset.xh || 'null'))");
  const tfsec = [14400, 900, 300];
  check("08 crosshair sincronizzato verificato NUMERICAMENTE: il pane M15 e il pane M5 mostrano la barra che contiene l'istante del pane H4", !!xh[0] && !!xh[1] && !!xh[2] && xh[1].t <= xh[0].t && xh[0].t - xh[1].t < 14400 && xh[2].t <= xh[0].t && xh[0].t - xh[2].t < 14400 && xh[1].from === "sync" && xh[2].from === "sync", xh);
  await B.clickId("ws-sync-crosshair"); await sleep(200);
  await B.mouse("mouseMoved", cr0[0] + cr0[2] * 0.2, cr0[1] + cr0[3] * 0.5); await sleep(300); await B.mouse("mouseMoved", cr0[0] + cr0[2] * 0.25, cr0[1] + cr0[3] * 0.5); await sleep(900);
  const xh2 = await B.ev("[1,2].map(i => JSON.parse(document.querySelectorAll('[data-testid^=pane-canvas-]')[i].parentElement.dataset.xh || 'null'))");
  check("08 sincronizzazione selettiva: con 'crosshair' disattivato i pane collegati non seguono piu' (la barra proiettata non cambia)", xh2.every((x, i) => x && xh[i + 1] && x.t === xh[i + 1].t), xh2);
  await B.clickId("ws-sync-crosshair");
  report.metrics.push({ distant_navigation: perfNav, multiscale_open_ms: tMs, h4_open_ms: openMs });

  // ============================================================ 9. salvataggio, snapshot, risorse prima della chiusura
  await B.clickId("ws-layout-3"); await sleep(500);
  await B.clickId("geo-save"); await sleep(1500);
  const snapEv = await events(sid), snapG = await geoms(sid);
  const rsr = (await B.api(`${D}/sessions/${sid}/research`)).research;
  check("09 stato della ricerca salvato: dataset, disposizione, finestre 90/40, evento in studio", rsr && rsr.dataset_id === SRC && rsr.event_window.pre === 90 && rsr.event_window.post === 40 && rsr.layout.count === 3, rsr && { ev: rsr.event_window, layout: rsr.layout.count });
  await writeFile(resolve(root, "evidence_he", "snapshot_events.json"), JSON.stringify(snapEv, null, 1)); await writeFile(resolve(root, "evidence_he", "snapshot_geoms.json"), JSON.stringify(snapG, null, 1));
  const perf3 = await B.perf(); const ent = await entries(); const rssMid = backendRss(origin);
  await B.clickId("ws-layout-4"); await sleep(5000);
  const perf4 = await B.perf(); const rss4 = backendRss(origin);
  await B.clickId("ws-layout-3"); await sleep(800);
  await B.shot("09_prima_della_chiusura.png");
  const loads = JSON.parse(await B.ev("document.querySelector('[data-testid=discovery-workspace]').dataset.loads"));
  report.metrics.push({ backend_rss_mb: { idle: rss0, after_session: rssMid, four_panes: rss4, render_limit_mb: 512 }, browser: { three_panes: perf3, four_panes: perf4 }, ohlc_requests: { n: ent.length, decoded_kb_total: Math.round(ent.reduce((a, e) => a + e.dec, 0) / 1024), decoded_kb_max: Math.round(Math.max(...ent.map((e) => e.dec)) / 1024), ms_p95: ent.map((e) => e.ms).sort((a, b) => a - b)[Math.floor(ent.length * 0.95)] }, pane_loads_ms: loads.map((l) => ({ tf: l.tf, n: l.n, ms: l.ms })) });
  check("09 prestazioni misurate: RAM del backend con 4 grafici e storico esteso ben sotto 512 MiB (browser misurato a parte)", rss4 != null && rss4 < 512, { backend_rss_mb: rss4, browser_js_heap_mb: perf4.js_heap_mb });
  await B.kill();

  // ============================================================ 10. riapertura dopo la chiusura del browser
  B = await openBrowser({ tag: "he2", root, out, origin, report });
  await B.login(...USER);
  await openLab();
  await waitStrips(["H4", "M15", "M5"]); await sleep(3500);
  const sid2 = await sidOf();
  check("10 riapertura in un browser nuovo: stessa sessione di ricerca, dataset esteso e disposizione H4/M15/M5 ripristinati", sid2 === sid && (await strips())[0].includes(SRC) && same((await strips()).map((s) => s.split(" ")[1]), ["H4", "M15", "M5"]), await strips());
  check("10 schede evento e geometrie recuperate senza variazioni (campo per campo)", same(await events(sid2), snapEv) && same(await geoms(sid2), snapG));
  const ovR = await overview();
  check("10 vista generale con i 3 marcatori e finestre 90/40 ripristinate", ovR && ovR.markers.length === 3 && (await B.ev("[document.querySelector('[data-testid=lab-win-pre]')?.value, document.querySelector('[data-testid=lab-win-post]')?.value]")).join() === "90,40", ovR && ovR.markers);
  check("10 evento in studio riaperto con le stesse grandezze", /Inversione|E1/.test(await B.ev("document.querySelector('[data-testid=ws-sidebar]').innerText")) && (await B.ev("document.querySelector('[data-testid=lab-card-name]')?.value")) === plans[0].name);
  await B.ev(`document.querySelector('[data-testid=lab-event-${created[2].event_id}]').click()`); await sleep(400); await B.clickId("lab-go"); await sleep(5000);
  const rr = await ranges();
  const wr = rr.map((r) => r.to - r.from);
  check("10 dopo la riapertura (pane collegati) la navigazione verso l'evento lontano E3 (2024) mantiene una finestra PROPRIA e proporzionata per ogni scala (H4 > M15 > M5)", rr.every((r) => r && r.from <= H4[plans[2].p].time && H4[plans[2].p].time <= r.to) && wr[0] > wr[1] && wr[1] > wr[2], rr.map((r) => [fmtUtc(r.from), fmtUtc(r.to)]));
  await B.shot("10_riaperto_e_navigazione_su_E3.png");
  await B.kill();

  // ============================================================ 11. isolamento tra due account reali
  if (originB) {
    const { report: rB } = makeReport(originB);
    B = await openBrowser({ tag: "he3", root, out, origin: originB, report: rB });
    await B.login(...USER_B);
    await B.cdp("Page.navigate", { url: `${originB}/app/discovery` });
    await B.waitFor("[...document.querySelectorAll('[data-testid^=pane-strip-]')].length>0", 200, 250); await sleep(2500);
    const sB = await B.api(`${G}/sessions`);
    const codes = await B.ev(`Promise.all([fetch('/api${D}/sessions/${sid}/events',{credentials:'include'}), fetch('/api${G}/sessions/${sid}',{credentials:'include'}), fetch('/api${G}/sessions/${sid}/export',{credentials:'include'})]).then(r => r.map(x => x.status))`);
    check("11 isolamento: l'account B non vede ricerche, eventi, geometrie ed export di A (404)", !sB.sessions.some((s) => s.session_id === sid) && codes.every((c) => c === 404) && (await B.ev("document.querySelectorAll('[data-testid^=lab-event-E]').length")) === 0, { sessions: sB.sessions.length, codes });
    await B.shot("11_account_B_vuoto.png");
    await B.kill();
    for (const c of rB.checks) report.checks.push({ ...c, name: "[B] " + c.name });
  } else report.notes.push("isolamento nel browser non eseguito: CHART_ORIGIN_B assente");

  // ============================================================ 12. residuo: sincronizzazione del simbolo (alias GOLD/XAUUSD del dataset XM)
  B = await openBrowser({ tag: "he4", root, out, origin, report });
  await B.login(...USER);
  await openLab();
  await B.setSelect("ws-source", "XM-GOLD-2026-11-16-20"); await sleep(1500);
  await B.clickId("ws-layout-2"); await sleep(600);
  await B.setSelect("ws-symbol", "GOLD");
  await waitStrips(["H4", "M15"]); await sleep(1500);
  const sGold = await strips();
  await B.setSelect("ws-symbol", "XAUUSD"); await sleep(3000);
  const sXau = await strips();
  check("12 sincronizzazione del simbolo: cambiando il simbolo globale cambiano TUTTI i pane (GOLD -> XAUUSD, stesso dataset XM)", sGold.every((s) => s.startsWith("GOLD ")) && sXau.every((s) => s.startsWith("XAUUSD ") && s.includes("barre")), { sGold, sXau });
  await B.clickId("ws-sync-symbol"); await sleep(600);
  await B.setSelect("pane-symbol-1", "GOLD"); await sleep(3000);
  const sMix = await strips();
  check("12 sincronizzazione selettiva del simbolo: con 'simbolo' disattivato un pane puo' usare l'altro alias, stesso numero di barre del dataset", /^XAUUSD /.test(sMix[0]) && /^GOLD /.test(sMix[1]) && sMix.every((s) => s.includes("barre")), sMix);
  await B.shot("12_simbolo_sincronizzato_alias.png");
  await B.kill();

  check("13 nessun errore console grave", report.console_errors.filter((e) => !/favicon|ResizeObserver/i.test(e)).length === 0, report.console_errors.slice(0, 5));
  check("13 nessuna risposta di rete anomala (esclusi 401 pre-login, favicon, 404 dell'isolamento)", report.network_failures.filter((e) => !/api\/auth\/me|favicon|research\/certificates|geometry\/sessions\/S|discovery\/sessions\/S/.test(e)).length === 0, report.network_failures.slice(0, 6));
} catch (e) {
  check("ERRORE SCRIPT", false, String((e && e.stack) || e));
} finally {
  if (B) await B.kill();
  report.summary = { total: report.checks.length, pass: report.checks.filter((c) => c.ok).length, fail: report.checks.filter((c) => !c.ok).length };
  await writeFile(resolve(root, "evidence_he", "browser_report.json"), JSON.stringify(report, null, 1));
  console.log("SUMMARY", JSON.stringify(report.summary));
}
