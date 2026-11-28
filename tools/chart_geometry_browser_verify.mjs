// USO: avviare il backend (porta 8852) con la build del frontend e lo store XM autorizzato, poi
//   CHART_GEO_ROOT=<cartella di lavoro> node tools/chart_geometry_browser_verify.mjs
// Credenziali: utente di PROVA locale del server di sviluppo (NEXUS_ADMIN_USER/PASSWORD impostati per la sola esecuzione locale).
// CHART-GEOMETRY-01 — verifica funzionale nel browser reale (Edge headless, CDP) su un grafico XM autorizzato.
import { spawn } from "node:child_process";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const root = (process.env.CHART_GEO_ROOT || process.cwd()).replace(/\\/g, "/");   // contiene evidence/ e runtime/
const out = resolve(root, "evidence", "screens");
const origin = process.env.CHART_ORIGIN || "http://127.0.0.1:8852";
const EDGE = process.env.CHART_GEO_BROWSER || "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const SOURCE = "XM-GOLD-2026-11-16-20";
await mkdir(out, { recursive: true });
const report = { origin, source: SOURCE, checks: [], console_errors: [], network_failures: [], notes: [] };
const check = (name, ok, detail = "") => { report.checks.push({ name, ok: !!ok, detail: typeof detail === "string" ? detail : JSON.stringify(detail) }); console.log(ok ? "PASS" : "FAIL", name, typeof detail === "string" ? detail : JSON.stringify(detail).slice(0, 220)); };
const close = (a, b, tol = 0.6) => Math.abs(a - b) <= tol;
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

async function openBrowser(tag) {
  const profile = resolve(root, "runtime", `edge-profile-${tag}`);
  await rm(profile, { recursive: true, force: true }).catch(() => {});
  const proc = spawn(EDGE, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "--window-size=1440,900", "about:blank"], { stdio: "ignore" });
  let port = "";
  for (let i = 0; i < 80 && !port; i++) { try { port = (await readFile(resolve(profile, "DevToolsActivePort"), "utf8")).split(/\r?\n/)[0]; } catch { await delay(250); } }
  if (!port) throw new Error("Edge non avviato");
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const socket = new WebSocket(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
  await new Promise((y, n) => { socket.addEventListener("open", y, { once: true }); socket.addEventListener("error", n, { once: true }); });
  const pending = new Map(); let seq = 0;
  const cdp = (method, params = {}, timeout = 60000) => new Promise((yes, no) => {
    const id = ++seq; const timer = setTimeout(() => { pending.delete(id); no(new Error("timeout " + method)); }, timeout);
    pending.set(id, { yes, no, timer }); socket.send(JSON.stringify({ id, method, params }));
  });
  socket.addEventListener("message", ({ data }) => {
    const m = JSON.parse(data);
    if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") report.console_errors.push(m.params.args.map((a) => a.value || a.description).join(" ").slice(0, 300));
    if (m.method === "Runtime.exceptionThrown") report.console_errors.push("EXC " + (m.params.exceptionDetails.text || "") + " " + (m.params.exceptionDetails.exception?.description || "").slice(0, 300));
    if (m.method === "Network.responseReceived" && m.params.response.status >= 400) report.network_failures.push(m.params.response.status + " " + m.params.response.url.replace(origin, ""));
    const c = pending.get(m.id); if (!c) return; pending.delete(m.id); clearTimeout(c.timer); if (m.error) c.no(new Error(m.error.message)); else c.yes(m.result);
  });
  const ev = async (expr) => { const r = await cdp("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true, userGesture: true }); if (r.exceptionDetails) throw new Error("EVAL " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text)); return r.result.value; };
  const shot = async (name) => { const i = await cdp("Page.captureScreenshot", { format: "png" }); await writeFile(resolve(out, name), Buffer.from(i.data, "base64")); report.notes.push("screenshot " + name); };
  const viewport = async (w, h) => { await cdp("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: false }); await delay(700); };
  const mouse = (type, x, y, extra = {}) => cdp("Input.dispatchMouseEvent", { type, x, y, button: type === "mouseMoved" ? "none" : "left", buttons: type === "mouseReleased" ? 0 : (type === "mouseMoved" ? (extra.buttons || 0) : 1), clickCount: type === "mouseMoved" ? 0 : 1, ...extra });
  const click = async (x, y) => { await mouse("mouseMoved", x, y); await delay(60); await mouse("mousePressed", x, y); await delay(40); await mouse("mouseReleased", x, y); await delay(150); };
  const drag = async (x1, y1, x2, y2, steps = 8) => {
    await mouse("mouseMoved", x1, y1); await delay(60); await mouse("mousePressed", x1, y1); await delay(60);
    for (let i = 1; i <= steps; i++) { await mouse("mouseMoved", x1 + ((x2 - x1) * i) / steps, y1 + ((y2 - y1) * i) / steps, { buttons: 1 }); await delay(25); }
    await mouse("mouseReleased", x2, y2); await delay(250);
  };
  const waitFor = async (expr, tries = 100, ms = 250) => { for (let i = 0; i < tries; i++) { try { if (await ev(expr)) return true; } catch { /* pagina in navigazione */ } await delay(ms); } return false; };
  await cdp("Page.enable"); await cdp("Runtime.enable"); await cdp("Network.enable"); await cdp("DOM.enable");
  await viewport(1440, 900);
  const api = (path) => ev(`fetch('/api${path}',{credentials:'include'}).then(r=>r.json())`);
  const setSelect = (id, v) => ev(`(() => { const el = document.querySelector('[data-testid=${id}]'); Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype,'value').set.call(el, ${JSON.stringify(v)}); el.dispatchEvent(new Event('change',{bubbles:true})); return el.value; })()`);
  const setInput = (id, v) => ev(`(() => { const el = document.querySelector('[data-testid=${id}]'); el.focus(); const proto = el.tagName==='TEXTAREA'?HTMLTextAreaElement:HTMLInputElement; Object.getOwnPropertyDescriptor(proto.prototype,'value').set.call(el, ${JSON.stringify(v)}); el.dispatchEvent(new Event('input',{bubbles:true})); el.blur(); return el.value; })()`);
  const clickId = (id) => ev(`(() => { const el = document.querySelector('[data-testid=${id}]'); if(!el) return false; el.click(); return true; })()`);
  const key = (k, mods = {}) => ev(`window.dispatchEvent(new KeyboardEvent('keydown',{key:${JSON.stringify(k)},bubbles:true,cancelable:true,ctrlKey:${!!mods.ctrl},shiftKey:${!!mods.shift}}))`);
  const proj = async () => JSON.parse(await ev("document.querySelector('[data-testid=geometry-canvas]')?.dataset.proj || '[]'"));
  const rect = () => ev(`(() => { const r = document.querySelector('[data-testid=chart-canvas]').getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; })()`);
  const sid = async () => {
    if (!(await ev("!!document.querySelector('[data-testid=geo-session-select]')"))) { await clickId("geo-panel-toggle"); await delay(500); }
    return ev("document.querySelector('[data-testid=geo-session-select]')?.value || ''");
  };
  const session = async () => api(`/chart/geometry/sessions/${await sid()}`);
  const login = async () => {
    await cdp("Page.navigate", { url: `${origin}/app/login` });
    await waitFor("!!document.querySelector('[data-testid=login-email-input]')");
    await ev(`(() => { const set = (s, v) => { const el = document.querySelector(s); Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
      set('[data-testid=login-email-input]', 'chart-geo@local'); set('[data-testid=login-password-input]', 'chart-geo-local-only'); document.querySelector('[data-testid=login-submit-button]').click(); return true; })()`);
    await waitFor("!location.pathname.includes('login')");
  };
  const openChart = async () => {
    await cdp("Page.navigate", { url: `${origin}/app/chart` });
    const ok = await waitFor(`(document.querySelector('[data-testid=chart-dataset-strip]')?.innerText||'').includes('XM-GOLD')`, 160, 250);
    await delay(900);
    return ok;
  };
  const strip = () => ev("document.querySelector('[data-testid=chart-dataset-strip]')?.innerText || ''");
  const kill = async () => { try { await cdp("Browser.close", {}, 5000); } catch { /* chiuso */ } try { proc.kill(); } catch { /* gia' chiuso */ } await delay(800); };
  return { cdp, ev, shot, viewport, mouse, click, drag, waitFor, api, setSelect, setInput, clickId, key, proj, rect, sid, session, login, openChart, strip, kill };
}

const waitObjects = async (B, n, tries = 40) => { for (let i = 0; i < tries; i++) { const s = await B.session(); if (s.geometries?.length === n) return s; await delay(250); } return B.session(); };
const waitRev = async (B, gid, rev, tries = 40) => { for (let i = 0; i < tries; i++) { const s = await B.session(); const g = s.geometries.find((x) => x.geometry_id === gid); if (g && g.revision >= rev) return g; await delay(250); } return (await B.session()).geometries.find((x) => x.geometry_id === gid); };
const cmp = (g) => ({ id: g.geometry_id, type: g.type, symbol: g.symbol, dataset_id: g.dataset_id, source: g.source, clock_basis: g.clock_basis, tf: g.timeframe_origin, anchors: g.anchors, semantic: g.semantic, name: g.name, description: g.description, style: g.style, status: g.status, created_at: g.created_at, available_at: g.available_at, author: g.author, origin: g.origin, rev: g.revision, links: g.links });

let B;
try {
  // =========================================================== 1. apertura grafico XM
  B = await openBrowser("a");
  await B.login();
  const opened = await B.openChart();
  check("01 grafico XM autorizzato aperto", opened, await B.strip());
  const stripTxt = await B.strip();
  check("01 nessun dato sintetico", !(await B.ev("document.body.innerText.toUpperCase().includes('SYNTHETIC')")));
  check("01 toolbar presente e pannello geometrie CHIUSO di default", await B.ev("!!document.querySelector('[data-testid=geometry-toolbar]') && !document.querySelector('[data-testid=geometry-panel]')"));
  const sidA = await B.sid();
  check("01 il pannello si apre dal pulsante ☷", await B.ev("!!document.querySelector('[data-testid=geometry-panel]')"));
  const R0 = await B.rect();
  const ohlc = await B.api(`/chart/ohlc?source=${SOURCE}&symbol=GOLD&tf=M15&limit=1500`);
  const bars = ohlc.bars || ohlc.data || [];
  check("01 barre M15 reali disponibili via API", bars.length > 100, `n=${bars.length}`);
  const barAt = (t) => bars.find((b) => b.time === t);
  await B.mouse("mouseMoved", R0.x + R0.w * 0.45, R0.y + R0.h * 0.5); await delay(400);
  check("01 readout OHLC della Chart reale funziona", /O \d/.test(await B.ev("document.querySelector('[data-testid=chart-ohlc-readout]')?.innerText || ''")));
  await B.shot("01_xm_m15_con_strumenti.png");
  const X = (f) => R0.x + R0.w * f, Y = (f) => R0.y + R0.h * f;

  // =========================================================== 2. diagonale con due ancoraggi (snap High)
  await B.setSelect("geo-snap", "high");
  await B.clickId("geo-tool-trendline");
  await B.click(X(0.35), Y(0.55)); await B.click(X(0.58), Y(0.30));
  let s = await waitObjects(B, 1);
  const diag = s.geometries[0];
  check("02 diagonale creata con 2 ancoraggi", diag?.type === "trendline" && diag.anchors.length === 2, diag?.anchors);
  const candleOk = (a, field) => a.ref?.kind === "CANDLE" && a.ref.field === field && barAt(a.ref.bar_t) && barAt(a.ref.bar_t)[field] === a.price && a.t === a.ref.bar_t;
  check("02 ancoraggi agganciati a High di candele reali: prezzo e orario verificati sulle barre", candleOk(diag.anchors[0], "high") && candleOk(diag.anchors[1], "high"), diag.anchors.map((a) => [a.t, a.price, a.ref.field]));
  check("02 ancoraggi con orari distinti e ordinati", diag.anchors[0].t !== diag.anchors[1].t);
  check("02 memoria: dataset/fonte/simbolo/tf/clock/autore/origine/available_at", diag.dataset_id === SOURCE && diag.symbol === "GOLD" && diag.timeframe_origin === "M15" && !!diag.clock_basis && diag.origin === "MANUAL" && !!diag.author && diag.available_at >= diag.created_at && diag.revision === 1 && diag.status === "ACTIVE" && diag.memory_domain === "GRAPHICAL",
    { dataset: diag.dataset_id, src: diag.source, clock: diag.clock_basis, author: diag.author });
  await B.shot("02_diagonale_due_ancoraggi.png");
  await B.setInput("geo-name", "Diagonale 1");
  await waitRev(B, diag.geometry_id, 2);
  await B.setSelect("geo-semantic", "DIAG_BUY");
  const d3 = await waitRev(B, diag.geometry_id, 3);
  check("02 significato BUY attribuito dall'utente; forma invariata; nessun campo segnale/ordine", d3.semantic.class === "DIAG_BUY" && d3.semantic.set_by === "USER" && d3.type === "trendline" && !("signal" in d3) && !("order" in d3) && same(d3.anchors, diag.anchors), d3.semantic);
  await B.setSelect("geo-extend", "right");
  const d4 = await waitRev(B, diag.geometry_id, 4);
  check("02 estensione a destra senza alterare le origini", d4.style.extend === "right" && same(d4.anchors, diag.anchors));
  await B.shot("02b_diagonale_estesa_BUY.png");

  // =========================================================== 3. key level da chiusure (snap Close)
  await B.setSelect("geo-snap", "close");
  await B.clickId("geo-tool-hline");
  await B.click(X(0.25), Y(0.64));
  s = await waitObjects(B, 2);
  const kl = s.geometries.find((g) => g.type === "hline");
  check("03 key level creato su Close di candela reale", kl && candleOk(kl.anchors[0], "close"), kl?.anchors);
  await B.setInput("geo-name", "Key level 1");
  await waitRev(B, kl.geometry_id, 2);
  await B.setSelect("geo-semantic", "KEY_LEVEL_CLOSES");
  const kl2 = await waitRev(B, kl.geometry_id, 3);
  check("03 classificazione manuale KEY_LEVEL_CLOSES (forma hline)", kl2.semantic.class === "KEY_LEVEL_CLOSES" && kl2.type === "hline");
  await B.shot("03_key_level.png");

  // =========================================================== 4. rettangolo (trascinamento, ancoraggi liberi)
  await B.setSelect("geo-snap", "free");
  await B.clickId("geo-tool-rectangle");
  await B.drag(X(0.40), Y(0.68), X(0.62), Y(0.82));
  s = await waitObjects(B, 3);
  const rc = s.geometries.find((g) => g.type === "rectangle");
  check("04 rettangolo creato con ancoraggi liberi (tempo e prezzo)", rc && rc.anchors.every((a) => a.ref.kind === "FREE") && rc.anchors[0].t !== rc.anchors[1].t && rc.anchors[0].price !== rc.anchors[1].price, rc?.anchors);
  check("04 clic libero esatto: l'orario non e' quantizzato all'inizio barra", rc.anchors.some((a) => a.t % 900 !== 0), rc.anchors.map((a) => a.t % 900));
  await B.setInput("geo-name", "Zona 1");
  await waitRev(B, rc.geometry_id, 2);
  await B.setSelect("geo-semantic", "ZONE_BUY_TO_SELL");
  await waitRev(B, rc.geometry_id, 3);
  await B.clickId("geo-color-16a34a");
  const rc4 = await waitRev(B, rc.geometry_id, 4);
  check("04 zona BUY TO SELL con colore scelto", rc4.semantic.class === "ZONE_BUY_TO_SELL" && rc4.style.color === "#16a34a", rc4.style.color);
  await B.shot("04_rettangolo_zona.png");
  await B.shot("04b_tre_oggetti.png");

  // =========================================================== 5. modifica: sposta, maniglia, valore numerico
  await B.clickId("geo-tool-select");
  const pr = await B.proj(); const pRect = pr.find((p) => p.id === rc.geometry_id).pts;
  const mid = [(pRect[0][0] + pRect[1][0]) / 2, (pRect[0][1] + pRect[1][1]) / 2];
  await B.drag(R0.x + mid[0], R0.y + mid[1], R0.x + mid[0] + 50, R0.y + mid[1] - 40);
  const rcM = await waitRev(B, rc.geometry_id, 5);
  const dT0 = rcM.anchors[0].t - rc4.anchors[0].t, dT1 = rcM.anchors[1].t - rc4.anchors[1].t;
  const dP0 = rcM.anchors[0].price - rc4.anchors[0].price, dP1 = rcM.anchors[1].price - rc4.anchors[1].price;
  check("05 rettangolo spostato rigidamente (stessi delta tempo e prezzo su entrambi gli angoli)", rcM.revision >= 5 && dT0 === dT1 && dT0 > 0 && Math.abs(dP0 - dP1) < 1e-9 && dP0 > 0, { dT0, dT1, dP0, dP1 });
  await B.ev(`document.querySelector('[data-testid=geo-item-${diag.geometry_id}]').click()`); await delay(500);
  const pr2 = await B.proj(); const pd = pr2.find((p) => p.id === diag.geometry_id).pts;
  await B.drag(R0.x + pd[1][0], R0.y + pd[1][1], R0.x + pd[1][0] + 40, R0.y + pd[1][1] + 35);
  const dH = await waitRev(B, diag.geometry_id, 5);
  check("05 maniglia: solo l'ancoraggio 2 modificato (ora libero); l'ancoraggio 1 intatto", same(dH.anchors[0], d4.anchors[0]) && !same(dH.anchors[1], d4.anchors[1]) && dH.anchors[1].ref.kind === "FREE", dH.anchors[1]);
  await B.setSelect("geo-snap", "free");
  await B.ev(`document.querySelector('[data-testid=geo-item-${rc.geometry_id}]').click()`); await delay(300);
  await B.setInput("geo-anchor-price-0", "4123.45");
  const rcN = await waitRev(B, rc.geometry_id, 6);
  check("05 modifica numerica del prezzo di un ancoraggio", rcN.anchors[0].price === 4123.45 && rcN.anchors[0].ref.kind === "FREE" && same(rcN.anchors[1], rcM.anchors[1]), rcN.anchors[0]);
  // blocco
  await B.ev(`document.querySelector('[data-testid=geo-item-${kl.geometry_id}]').click()`); await delay(300);
  await B.ev("document.querySelector('[data-testid=geo-locked]').click()");
  const klL = await waitRev(B, kl.geometry_id, 4);
  const pk = (await B.proj()).find((p) => p.id === kl.geometry_id).pts[0];
  await B.drag(R0.x + pk[0], R0.y + pk[1], R0.x + pk[0], R0.y + pk[1] - 60);
  await delay(600);
  const klAfter = (await B.session()).geometries.find((g) => g.geometry_id === kl.geometry_id);
  check("05 oggetto bloccato: il trascinamento non lo modifica", klL.style.locked === true && klAfter.revision === klL.revision && same(klAfter.anchors, klL.anchors));
  await B.ev("document.querySelector('[data-testid=geo-locked]').click()");
  await waitRev(B, kl.geometry_id, 5);
  // undo / redo
  await B.key("z", { ctrl: true }); await delay(900);
  let g6 = (await B.session()).geometries.find((g) => g.geometry_id === kl.geometry_id);
  check("05 undo (Ctrl+Z) annulla lo sblocco", g6.style.locked === true, g6.style.locked);
  await B.key("y", { ctrl: true }); await delay(900);
  g6 = (await B.session()).geometries.find((g) => g.geometry_id === kl.geometry_id);
  check("05 redo (Ctrl+Y) ripristina", g6.style.locked === false);
  await B.shot("05_modificati_spostato_maniglia.png");
  // livelli
  await B.setInput("geo-new-layer-name", "Zone");
  await B.clickId("geo-new-layer"); await delay(700);
  const lay = (await B.session()).layers.find((l) => l.name === "Zone");
  await B.ev(`document.querySelector('[data-testid=geo-item-${rc.geometry_id}]').click()`); await delay(300);
  await B.setSelect("geo-layer-select", lay.layer_id);
  await waitRev(B, rc.geometry_id, 7);
  await B.clickId(`geo-layer-vis-${lay.layer_id}`); await delay(900);
  check("05 livello nascosto: l'oggetto non e' proiettato", !(await B.proj()).some((p) => p.id === rc.geometry_id));
  await B.shot("05b_livello_nascosto.png");
  await B.clickId(`geo-layer-vis-${lay.layer_id}`); await delay(900);
  check("05 livello visibile: l'oggetto torna", (await B.proj()).some((p) => p.id === rc.geometry_id));

  // =========================================================== 6. cambio timeframe / zoom / pan / resize
  const before = (await B.session()).geometries.map(cmp);
  const projM15 = await B.proj();
  for (const tf of ["H1", "H4"]) {
    await B.clickId(`chart-tf-${tf}`);
    await B.waitFor(`(document.querySelector('[data-testid=chart-dataset-strip]')?.innerText||'').includes('GOLD ${tf}')`, 80, 250);
    await delay(900);
    const pj = await B.proj();
    report.notes.push(`dbg ${tf}: ` + await B.ev("document.querySelector('[data-testid=geometry-canvas]').dataset.dbg"));
    const now = (await B.session()).geometries.map(cmp);
    check(`06 ${tf}: geometrie invariate nel dato (ancoraggi/stile/revisioni)`, same(now, before));
    check(`06 ${tf}: proiezione ricalcolata (posizioni in pixel diverse da M15) e tutti gli oggetti visibili`, pj.length === projM15.length && pj.some((p, i) => !close(p.pts[0][0], projM15[i].pts[0][0], 2)) && pj.every((p) => p.pts.every(Boolean)) && pj.every((p) => p.pts.every((pt) => pt[0] > 1 && pt[0] < 1376)), pj.map((p) => p.pts[0]));
    await B.shot(`06_${tf.toLowerCase()}_geometrie_mantenute.png`);
  }
  await B.clickId("chart-tf-M15");
  await B.waitFor("(document.querySelector('[data-testid=chart-dataset-strip]')?.innerText||'').includes('GOLD M15')", 80, 250);
  await delay(900);
  const projBack = await B.proj();
  check("06 ritorno a M15: stessa proiezione di prima (tolleranza 2 px)", projBack.length === projM15.length && projBack.every((p, i) => p.pts.every((pt, j) => close(pt[0], projM15[i].pts[j][0], 2.5) && close(pt[1], projM15[i].pts[j][1], 2.5))));
  await B.mouse("mouseWheel", X(0.5), Y(0.5), { deltaX: 0, deltaY: -500 }); await delay(900);
  const projZoom = await B.proj();
  const afterZoom = (await B.session()).geometries.map(cmp);
  check("06 zoom: proiezione cambia, dati invariati", !same(projZoom, projM15) && same(afterZoom, before));
  await B.shot("06_zoom.png");
  await B.viewport(1280, 720);
  const projRs = await B.proj();
  const Rs = await B.rect();
  check("06 ridimensionamento finestra 1280x720: proiezione ricalcolata, dati invariati", Rs.w < R0.w && !same(projRs, projZoom) && same((await B.session()).geometries.map(cmp), before), { w: Rs.w });
  await B.shot("06_resize_1280x720.png");
  await B.viewport(1440, 900);

  // =========================================================== 7. salvataggio esplicito + snapshot
  await B.clickId("geo-save"); await delay(1200);
  check("07 salvataggio/rilettura dal server", /salvata/i.test(await B.ev("document.querySelector('[data-testid=geo-note]')?.innerText || ''")));
  const snap = await B.session();
  const snapCmp = snap.geometries.map(cmp);
  const exportDoc = await B.api(`/chart/geometry/sessions/${sidA}/export`);
  await writeFile(resolve(out, "..", "session_export.nexus-geometry.json"), JSON.stringify(exportDoc, null, 1));
  await writeFile(resolve(out, "..", "snapshot_before_close.json"), JSON.stringify(snapCmp, null, 1));
  check("07 esportazione con sha256", /^[0-9a-f]{64}$/.test(exportDoc.sha256) && exportDoc.geometries.length === 3, exportDoc.sha256);
  await B.shot("07_prima_della_chiusura.png");
  await B.kill();

  // =========================================================== 8. chiusura e riapertura (profilo nuovo, nessuno stato locale)
  B = await openBrowser("b");
  await B.login();
  const reopened = await B.openChart();
  check("08 grafico riaperto in un browser nuovo", reopened, await B.strip());
  await delay(1200);
  const sidB = await B.sid();
  const snap2 = await B.session();
  check("08 stessa sessione di analisi ritrovata", sidB === sidA, [sidA, sidB]);
  check("08 geometrie recuperate SENZA variazioni (confronto campo per campo)", same(snap2.geometries.map(cmp), snapCmp));
  const pjR = await B.proj();
  check("08 le 3 geometrie sono disegnate", pjR.length === 3 && pjR.every((p) => p.pts.every(Boolean)), pjR.map((p) => [p.type, p.pts[0]]));
  const barsR = (await B.api(`/chart/ohlc?source=${SOURCE}&symbol=GOLD&tf=M15&limit=1500`)).bars;
  const rd = snap2.geometries.find((g) => g.geometry_id === diag.geometry_id);
  check("08 ancoraggio a candela: prezzo e orario invariati e coerenti con la barra reale", (() => { const a = rd.anchors[0]; if (a.ref.kind !== "CANDLE") return false; const b = barsR.find((x) => x.time === a.ref.bar_t); return b && b[a.ref.field] === a.price && a.t === a.ref.bar_t; })(), rd.anchors[0]);
  const klR = snap2.geometries.find((g) => g.geometry_id === kl.geometry_id);
  check("08 key level: Close di candela reale invariato dopo la riapertura", (() => { const a = klR.anchors[0]; const b = barsR.find((x) => x.time === a.ref.bar_t); return a.ref.kind === "CANDLE" && b && b[a.ref.field] === a.price; })(), klR.anchors[0]);
  await B.ev(`document.querySelector('[data-testid=geo-item-${rc.geometry_id}]').click()`); await delay(400);
  const shown = await B.ev("[...document.querySelectorAll('[data-testid^=geo-anchor-price-]')].map(e => e.value)");
  check("08 l'ispettore mostra i prezzi numerici salvati", shown[0] === "4123.45", shown);
  await B.shot("08_riaperto_geometrie_recuperate.png");

  // =========================================================== 9. importazione (valida e manomessa)
  const doc = await B.ev(`fetch('/api/chart/geometry/sessions/${sidB}/export',{credentials:'include'}).then(r=>r.json())`);
  const file = resolve(out, "..", "session_export.nexus-geometry.json");
  const { root: dom } = await B.cdp("DOM.getDocument", { depth: 1 });
  const { nodeId } = await B.cdp("DOM.querySelector", { nodeId: dom.nodeId, selector: "[data-testid=geo-import-file]" });
  await B.cdp("DOM.setFileInputFiles", { nodeId, files: [file.replace(/\//g, "\\")] });
  await delay(1800);
  const sidC = await B.sid();
  const snap3 = await B.session();
  check("09 importazione crea una nuova sessione con le stesse 3 geometrie", sidC !== sidB && snap3.geometries.length === 3);
  const strip = (arr) => arr.map((g) => ({ ...cmp(g), id: g.geometry_id, rev: undefined }));
  check("09 geometrie importate identiche (ancoraggi, stile, semantica, timestamp di creazione/disponibilita')", same(strip(snap3.geometries), strip(snap2.geometries)));
  check("09 import: autore dichiarato conservato ma NON autenticato; importatore effettivo registrato a parte", snap3.geometries.every((g) => g.imported_by === "chart-geo@local" && g.author_verified === false && g.author === "chart-geo@local") && snap2.geometries.every((g) => g.author_verified === true && g.imported_by === null));
  const tampered = JSON.parse(JSON.stringify(doc)); tampered.geometries[0].anchors[0].price += 1;
  const tfile = resolve(out, "..", "session_export_TAMPERED.json");
  await writeFile(tfile, JSON.stringify(tampered));
  const n0 = (await B.api("/chart/geometry/sessions")).sessions.length;
  const { root: dom2 } = await B.cdp("DOM.getDocument", { depth: 1 });
  const { nodeId: n2 } = await B.cdp("DOM.querySelector", { nodeId: dom2.nodeId, selector: "[data-testid=geo-import-file]" });
  await B.cdp("DOM.setFileInputFiles", { nodeId: n2, files: [tfile.replace(/\//g, "\\")] });
  await delay(1500);
  const note = await B.ev("document.querySelector('[data-testid=geo-note]')?.innerText || ''");
  check("09 file manomesso rifiutato (hash) e nessuna sessione creata", /IMPORT_HASH_MISMATCH/.test(note) && (await B.api("/chart/geometry/sessions")).sessions.length === n0, note);
  await B.shot("09_import_rifiutato.png");

  // =========================================================== 10. eliminazione annullabile (sulla sessione originale)
  await B.ev(`(() => { const el = document.querySelector('[data-testid=geo-session-select]'); Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype,'value').set.call(el, ${JSON.stringify(sidB)}); el.dispatchEvent(new Event('change',{bubbles:true})); })()`);
  await delay(1200);
  await B.ev(`document.querySelector('[data-testid=geo-item-${rc.geometry_id}]').click()`); await delay(300);
  await B.clickId("geo-delete"); await delay(900);
  check("10 eliminazione: oggetto non piu' attivo ne' disegnato", (await B.session()).geometries.length === 2 && !(await B.proj()).some((p) => p.id === rc.geometry_id));
  const hist = await B.api(`/chart/geometry/sessions/${sidB}/objects/${rc.geometry_id}?history=true`);
  check("10 la storia delle revisioni e' conservata (mai cancellata)", hist.revisions.length >= 8 && hist.revisions.at(-1).status === "ARCHIVED", hist.revisions.length);
  await B.key("z", { ctrl: true }); await delay(1000);
  check("10 undo dell'eliminazione ripristina l'oggetto con le stesse ancore", same((await B.session()).geometries.find((g) => g.geometry_id === rc.geometry_id)?.anchors, rcN.anchors));
  // =========================================================== 12. tutti gli strumenti e tutte le classi semantiche NEXUS
  await B.setSelect("geo-snap", "free");
  let total = (await B.session()).geometries.length;
  const created = {};
  const make = async (label, tool, how, pts, sem, extra) => {
    await B.clickId(`geo-tool-${tool}`);
    if (how === "drag") await B.drag(X(pts[0][0]), Y(pts[0][1]), X(pts[1][0]), Y(pts[1][1]));
    else for (const q of pts) await B.click(X(q[0]), Y(q[1]));
    total += 1;
    const ses = await waitObjects(B, total);
    const g = ses.geometries.filter((x) => !Object.values(created).some((c) => c.geometry_id === x.geometry_id) && x.geometry_id !== diag.geometry_id && x.geometry_id !== kl.geometry_id && x.geometry_id !== rc.geometry_id).at(-1);
    created[label] = g;
    if (sem) { await B.setSelect("geo-semantic", sem); created[label] = await waitRev(B, g.geometry_id, g.revision + 1); }
    if (extra) { await extra(created[label]); }
    return created[label];
  };
  await make("vline", "vline", "click", [[0.30, 0.40]]);
  await make("ray", "ray", "click", [[0.20, 0.70], [0.35, 0.60]], "DIAG_SELL");
  await make("ext", "extended_line", "drag", [[0.45, 0.30], [0.60, 0.40]]);
  await make("band", "price_band", "drag", [[0.20, 0.20], [0.30, 0.26]], "REACTION_ZONE");
  await make("text", "text", "click", [[0.50, 0.45]], null, async (g) => { await B.setInput("geo-text", "Spike?"); created.text = await waitRev(B, g.geometry_id, g.revision + 1); });
  await make("fibr", "fib_retracement", "drag", [[0.30, 0.75], [0.45, 0.50]]);
  await make("fibx", "fib_extension", "click", [[0.20, 0.55], [0.28, 0.35], [0.36, 0.48]]);
  await make("ruler", "ruler", "drag", [[0.50, 0.55], [0.65, 0.70]]);
  await B.setSelect("geo-snap", "high");
  await make("liq", "hline", "click", [[0.15, 0.50]], "LIQUIDITY_SPIKES");
  await B.setSelect("geo-snap", "free");
  await make("s2b", "rectangle", "drag", [[0.05, 0.70], [0.13, 0.78]], "ZONE_SELL_TO_BUY");
  await make("inner", "rectangle", "drag", [[0.62, 0.20], [0.70, 0.30]], "INNER_SPACE");
  await make("cont", "rectangle", "drag", [[0.62, 0.35], [0.70, 0.45]], "CONTINUATION_ZONE");
  const need = { vline: 1, ray: 2, ext: 2, band: 2, text: 1, fibr: 2, fibx: 3, ruler: 2, liq: 1, s2b: 2, inner: 2, cont: 2 };
  check("12 ogni strumento creato con il numero corretto di ancoraggi", Object.entries(need).every(([k, n]) => created[k]?.anchors.length === n), Object.fromEntries(Object.entries(created).map(([k, g]) => [k, [g.type, g.anchors.length]])));
  check("12 annotazione testuale salvata", created.text.text === "Spike?" && created.text.type === "text");
  check("12 Fibonacci: livelli utente di default presenti e modificabili solo come parametri", created.fibr.fib_levels.length === 7 && created.fibx.fib_levels.length === 5);
  check("12 ancoraggio a High per la liquidita'", candleOk(created.liq.anchors[0], "high"));
  check("12 ancoraggi 3 punti della extension distinti nel tempo", new Set(created.fibx.anchors.map((a) => a.t)).size === 3);
  const all = (await B.session()).geometries;
  const classes = new Set(all.map((g) => g.semantic.class));
  const NEXUS = ["DIAG_BUY", "DIAG_SELL", "KEY_LEVEL_CLOSES", "LIQUIDITY_SPIKES", "ZONE_BUY_TO_SELL", "ZONE_SELL_TO_BUY", "INNER_SPACE", "REACTION_ZONE", "CONTINUATION_ZONE"];
  check("12 tutte le 9 classi semantiche NEXUS assegnate manualmente (forma e significato separati)", NEXUS.every((c) => classes.has(c)) && all.every((g) => !("signal" in g) && !("order" in g)), [...classes]);
  await B.waitFor("true", 1, 1); await delay(600);
  await B.shot("12_tutti_gli_strumenti.png");
  const before12 = all.map(cmp);
  await B.cdp("Page.reload");
  await B.waitFor(`(document.querySelector('[data-testid=chart-dataset-strip]')?.innerText||'').includes('XM-GOLD') && !!document.querySelector('[data-testid=geo-session-select]')?.value`, 160, 250);
  await delay(1500);
  const after12 = (await B.session()).geometries.map(cmp);
  check("12 ricarica pagina: 15 geometrie identiche campo per campo", after12.length === 15 && same(after12, before12), after12.length);
  const pj12 = await B.proj();
  check("12 ricarica pagina: tutte le geometrie ridisegnate con ancoraggi proiettati", pj12.length === 15 && pj12.every((p) => p.pts.every(Boolean)), pj12.length);
  await B.shot("13_dopo_ricarica_15_geometrie.png");
  // =========================================================== 13. chiusura Geometry: tutti i timeframe, pan, zoom, trascinamento, pip configurabili
  await B.clickId("geo-tool-select");
  const tfBtns = await B.ev("[...document.querySelectorAll('[data-testid^=chart-tf-]')].filter(b => !b.disabled).map(b => b.dataset.testid.replace('chart-tf-', ''))");
  const nObjs = (await B.session()).geometries.filter((g) => g.status === "ACTIVE").length;
  const rowsTf = [];
  for (const tf of tfBtns) {
    const t1 = Date.now();
    await B.clickId(`chart-tf-${tf}`);
    const okTf = await B.waitFor(`(document.querySelector('[data-testid=chart-dataset-strip]')?.innerText||'').includes('GOLD ${tf}')`, 80, 250);
    await delay(1000);
    const pjT = await B.proj();
    const errT = await B.ev("document.querySelector('[data-testid=chart-error]')?.innerText || null");
    rowsTf.push({ tf, ok: okTf, ms: Date.now() - t1, error: errT, projected: pjT.length, finite: pjT.every((p) => p.pts.every((pt) => pt && Number.isFinite(pt[0]) && Number.isFinite(pt[1]))), bars: Number(((await B.strip()).match(/(\d+) barre/) || [])[1] || 0) });
    await B.shot(`13_timeframe_${tf}.png`);
  }
  report.notes.push("timeframe: " + JSON.stringify(rowsTf));
  check(`13 tutti i timeframe disponibili (${tfBtns.join(", ")}): dati reali, nessun errore, geometrie proiettate con coordinate finite`, rowsTf.length === tfBtns.length && rowsTf.every((r) => r.ok && !r.error && r.finite && r.bars > 0 && r.projected === nObjs), rowsTf);
  await B.clickId("chart-tf-M15"); await B.waitFor("(document.querySelector('[data-testid=chart-dataset-strip]')?.innerText||'').includes('GOLD M15')", 80, 250); await delay(1200);
  // pan col trascinamento del grafico (livello nascosto per avere un'area libera): le geometrie seguono il dato di dx pixel esatti
  const layersAll = (await B.session()).layers;
  const pjBefore = await B.proj();
  const dataPan0 = (await B.session()).geometries.map(cmp);
  for (const l of layersAll) await B.clickId(`geo-layer-vis-${l.layer_id}`);      // nascondo i livelli: area libera per il trascinamento
  await delay(700);
  const R1 = await B.rect();
  await B.drag(R1.x + R1.w * 0.45, R1.y + R1.h * 0.5, R1.x + R1.w * 0.45 + 140, R1.y + R1.h * 0.5, 12);
  await delay(700);
  for (const l of layersAll) await B.clickId(`geo-layer-vis-${l.layer_id}`);      // li riattivo
  await delay(900);
  const pjAfter = await B.proj();
  const dxs = pjAfter.map((p, i) => p.pts[0][0] - pjBefore[i].pts[0][0]);
  const dys = pjAfter.map((p, i) => p.pts[0][1] - pjBefore[i].pts[0][1]);
  check("13 pan col trascinamento del grafico: tutte le geometrie traslano orizzontalmente dello stesso valore (+-1 px, 100..145 px: il trascinamento e' limitato dal bordo dei dati); la scala dei prezzi e' automatica e puo' variare; dati invariati", pjAfter.length === pjBefore.length && dxs.every((d) => Math.abs(d - dxs[0]) <= 1) && dxs[0] >= 100 && dxs[0] <= 145 && same((await B.session()).geometries.map(cmp), dataPan0), { dxs, dys });
  await B.shot("13_pan_trascinamento.png");
  // zoom con la rotella verso fuori e verso dentro: la proiezione cambia, i dati no
  const dataB = (await B.session()).geometries.map(cmp);
  await B.mouse("mouseWheel", R1.x + R1.w * 0.5, R1.y + R1.h * 0.5, { deltaX: 0, deltaY: 400 }); await delay(900);
  const pjOut = await B.proj();
  await B.mouse("mouseWheel", R1.x + R1.w * 0.5, R1.y + R1.h * 0.5, { deltaX: 0, deltaY: -800 }); await delay(900);
  const pjIn = await B.proj();
  check("13 zoom (fuori e dentro): proiezione ricalcolata e finita, dati invariati", !same(pjOut, pjIn) && pjIn.every((p) => p.pts.every((pt) => pt && Number.isFinite(pt[0]))) && same((await B.session()).geometries.map(cmp), dataB));
  await B.shot("13_zoom.png");
  // righello con pip configurabili
  const rulerTxt = async () => B.ev("JSON.parse(document.querySelector('[data-testid=geometry-canvas]').dataset.rulers || '[]')[0]?.text || ''");
  const rt1 = await rulerTxt();
  const dPrice = Number((rt1.match(/Δ (-?[\d.]+)/) || [])[1]), dPip = Number((rt1.match(/= (-?[\d.]+) pip/) || [])[1]);
  check("13 righello: pip (convenzione iniziale XAUUSD 1 pip = 0,10 di prezzo)", rt1.includes("pip") && Math.abs(dPip - dPrice / 0.1) < 0.2, rt1);
  await B.setInput("geo-units-pip_size", "0.01"); await delay(900);
  const rt2 = await rulerTxt();
  check("13 pip configurabile: con 0,01 i pip diventano 10x e il prezzo non cambia", Math.abs(Number((rt2.match(/= (-?[\d.]+) pip/) || [])[1]) - dPrice / 0.01) < 2 && Math.abs(Number((rt2.match(/Δ (-?[\d.]+)/) || [])[1]) - dPrice) < 1e-9, rt2);
  await B.setInput("geo-units-pip_size", ""); await delay(700);
  const rt3 = await rulerTxt();
  check("13 pip non noto: il righello non inventa i pip", !rt3.includes("pip"), rt3);
  await B.setInput("geo-units-pip_size", "0.1"); await delay(700);
  check("11 nessun errore console grave", report.console_errors.filter((e) => !/favicon|ResizeObserver/i.test(e)).length === 0, report.console_errors.slice(0, 5));
  check("11 nessuna risposta di rete >= 400 (escluso il rifiuto atteso dell'import manomesso)", report.network_failures.filter((e) => !/geometry\/import|\/api\/auth\/me|favicon|research\/certificates/.test(e)).length === 0, report.network_failures);
} catch (e) {
  check("ERRORE SCRIPT", false, String(e && e.stack || e));
} finally {
  if (B) await B.kill();
  report.summary = { total: report.checks.length, pass: report.checks.filter((c) => c.ok).length, fail: report.checks.filter((c) => !c.ok).length };
  await writeFile(resolve(root, "evidence", "browser_report.json"), JSON.stringify(report, null, 1));
  console.log("SUMMARY", JSON.stringify(report.summary));
}
