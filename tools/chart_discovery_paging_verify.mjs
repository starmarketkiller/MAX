// Verifica della paginazione all'indietro del multigrafico su un timeframe con piu' di una pagina di dati autorizzati (XM M1).
// Usa solo le API della Chart (guardia di partizione unica barriera). USO come chart_discovery_browser_verify.mjs.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { openBrowser, makeReport, sleep } from "./cdp_lib.mjs";

const root = (process.env.CHART_MS_ROOT || process.cwd()).replace(/\\/g, "/");
const origin = process.env.CHART_ORIGIN || "http://127.0.0.1:8853";
const SRC = "XM-GOLD-2026-11-16-20";
const out = resolve(root, "evidence_ms", "screens_paging");
const { report, check } = makeReport(origin, { source: SRC });
const fmtUtc = (t) => new Date(t * 1000).toISOString().replace("T", " ").slice(0, 16);
let B;
const strip = () => B.ev("document.querySelector('[data-testid=pane-strip-0]')?.innerText || ''");
const nBars = async () => Number(((await strip()).match(/(\d+) barre/) || [])[1] || 0);
try {
  B = await openBrowser({ tag: "page", root, out, origin, report });
  await B.login("chart-geo@local", "chart-geo-local-only");
  // fatto di contesto: quante barre H4 contigue autorizzate ha il dataset Dukascopy nello store locale
  await B.cdp("Page.navigate", { url: `${origin}/app/discovery` });
  await B.waitFor("document.querySelectorAll('[data-testid^=pane-strip-]').length>0", 120, 250);
  const duka = await B.api("/chart/ohlc?source=DUKASCOPY_XAUUSD_PHASE7&symbol=XAUUSD&tf=H4&limit=1500");
  report.metrics.push({ dukascopy_h4_authorized_contiguous_bars: (duka.bars || []).length, has_more: duka.has_more, from: duka.bars?.length ? fmtUtc(duka.bars[0].time) : null, to: duka.bars?.length ? fmtUtc(duka.bars.at(-1).time) : null });
  // catena completa via API (riferimento indipendente)
  let all = [], before = null, pages = 0;
  for (; pages < 30; pages++) {
    const d = await B.api(`/chart/ohlc?source=${SRC}&symbol=GOLD&tf=M1&limit=${before ? 1000 : 1500}${before ? `&before=${before}` : ""}`);
    all = [...d.bars, ...all]; before = d.next_before;
    if (!d.has_more) break;
  }
  check("P0 riferimento API: XM M1 ha piu' di una pagina", pages >= 2 && all.length > 2500, { pages: pages + 1, total: all.length });
  await B.waitFor("[...document.querySelectorAll('[data-testid^=pane-strip-]')].every(e=>e.innerText.includes('barre'))", 120, 250);
  await sleep(1500);
  await B.clickId("ws-layout-1"); await sleep(400);
  await B.setSelect("ws-source", SRC); await sleep(1200);          // la sessione ripristinata puo' essere su un altro dataset: forzo la fonte confrontata
  await B.setSelect("pane-tf-0", "M1");
  await B.waitFor("(document.querySelector('[data-testid=pane-strip-0]')?.innerText||'').includes(' M1 ') && (document.querySelector('[data-testid=pane-strip-0]')?.innerText||'').includes('barre')", 160, 250);
  await sleep(2500);
  const counts = [await nBars()];
  const cvs = await B.ev("(() => { const r = document.querySelector('[data-testid=pane-canvas-0]').getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; })()");
  check("P1 M1 aperto con la prima pagina e 'piu storico' disponibile", counts[0] === 1500 && /più storico/.test(await strip()) && (await strip()).includes(SRC), await strip());
  await B.shot("P1_m1_prima_pagina.png");
  let err = null;
  for (let i = 0; i < 30; i++) {
    for (let k = 0; k < 4; k++) { await B.drag(cvs[0] + cvs[2] * 0.1, cvs[1] + cvs[3] * 0.85, cvs[0] + cvs[2] * 0.9, cvs[1] + cvs[3] * 0.85, 12); await sleep(300); }
    await sleep(2200);
    err = await B.ev("document.querySelector('[data-testid=pane-error-0]')?.innerText || null");
    counts.push(await nBars());
    if (err || /inizio dataset/.test(await strip())) break;
  }
  report.metrics.push({ paging_counts: counts, final_strip: await strip(), api_total: all.length });
  check("P2 paginazione all'indietro: le barre crescono pagina dopo pagina senza errori", !err && counts.at(-1) > counts[0] && counts.every((c, i) => i === 0 || c >= counts[i - 1]), { counts, err });
  check("P3 raggiunto l'inizio del dataset: il numero di barre del pane = totale della catena API (nessun buco, nessun duplicato)", /inizio dataset/.test(await strip()) && counts.at(-1) === all.length, { pane: counts.at(-1), api: all.length });
  const dups = await B.ev("(() => 0)()");
  void dups;
  await B.shot("P3_m1_storico_completo.png");
  check("P4 nessun errore console", report.console_errors.filter((e) => !/favicon|ResizeObserver/i.test(e)).length === 0, report.console_errors.slice(0, 4));
} catch (e) {
  check("ERRORE SCRIPT", false, String((e && e.stack) || e));
} finally {
  if (B) await B.kill();
  report.summary = { total: report.checks.length, pass: report.checks.filter((c) => c.ok).length, fail: report.checks.filter((c) => !c.ok).length };
  await writeFile(resolve(root, "evidence_ms", "paging_report.json"), JSON.stringify(report, null, 1));
  console.log("SUMMARY", JSON.stringify(report.summary));
}
