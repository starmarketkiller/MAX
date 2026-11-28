// Libreria CDP minima per le verifiche nel browser reale (Edge/Chrome headless). Nessuna dipendenza esterna (Node >= 22: WebSocket globale).
import { spawn } from "node:child_process";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

export const sleep = delay;
export const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
export const close = (a, b, tol = 0.6) => Math.abs(a - b) <= tol;

export function makeReport(origin, extra = {}) {
  const report = { origin, checks: [], console_errors: [], network_failures: [], notes: [], metrics: [], ...extra };
  const check = (name, ok, detail = "") => {
    const d = typeof detail === "string" ? detail : JSON.stringify(detail);
    report.checks.push({ name, ok: !!ok, detail: d.slice(0, 600) });
    console.log(ok ? "PASS" : "FAIL", name, d.slice(0, 200));
  };
  return { report, check };
}

export async function openBrowser({ tag, root, out, origin, report, edge, width = 1440, height = 900 }) {
  const profile = resolve(root, "runtime", `edge-profile-${tag}`);
  await mkdir(out, { recursive: true });
  await rm(profile, { recursive: true, force: true }).catch(() => {});
  const exe = edge || process.env.CHART_BROWSER || "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
  const proc = spawn(exe, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--remote-debugging-port=0", `--user-data-dir=${profile}`, `--window-size=${width},${height}`, "about:blank"], { stdio: "ignore" });
  let port = "";
  for (let i = 0; i < 80 && !port; i++) { try { port = (await readFile(resolve(profile, "DevToolsActivePort"), "utf8")).split(/\r?\n/)[0]; } catch { await delay(250); } }
  if (!port) throw new Error("browser non avviato");
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
  const mouse = (type, x, y, extra = {}) => cdp("Input.dispatchMouseEvent", { type, x, y, button: type === "mouseMoved" || type === "mouseWheel" ? "none" : "left", buttons: type === "mouseReleased" ? 0 : (type === "mouseMoved" ? (extra.buttons || 0) : 1), clickCount: type === "mouseMoved" || type === "mouseWheel" ? 0 : 1, ...extra });
  const click = async (x, y) => { await mouse("mouseMoved", x, y); await delay(60); await mouse("mousePressed", x, y); await delay(40); await mouse("mouseReleased", x, y); await delay(160); };
  const drag = async (x1, y1, x2, y2, steps = 8) => {
    await mouse("mouseMoved", x1, y1); await delay(60); await mouse("mousePressed", x1, y1); await delay(60);
    for (let i = 1; i <= steps; i++) { await mouse("mouseMoved", x1 + ((x2 - x1) * i) / steps, y1 + ((y2 - y1) * i) / steps, { buttons: 1 }); await delay(25); }
    await mouse("mouseReleased", x2, y2); await delay(250);
  };
  const waitFor = async (expr, tries = 100, ms = 250) => { for (let i = 0; i < tries; i++) { try { if (await ev(expr)) return true; } catch { /* pagina in navigazione */ } await delay(ms); } return false; };
  await cdp("Page.enable"); await cdp("Runtime.enable"); await cdp("Network.enable"); await cdp("DOM.enable"); await cdp("Performance.enable");
  await viewport(width, height);
  const api = (path) => ev(`fetch('/api${path}',{credentials:'include'}).then(r=>r.json())`);
  const setSelect = (id, v) => ev(`(() => { const el = document.querySelector('[data-testid=${id}]'); Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype,'value').set.call(el, ${JSON.stringify(v)}); el.dispatchEvent(new Event('change',{bubbles:true})); return el.value; })()`);
  const setInput = (id, v, blur = true) => ev(`(() => { const el = document.querySelector('[data-testid=${id}]'); el.focus(); const proto = el.tagName==='TEXTAREA'?HTMLTextAreaElement:HTMLInputElement; Object.getOwnPropertyDescriptor(proto.prototype,'value').set.call(el, ${JSON.stringify(v)}); el.dispatchEvent(new Event('input',{bubbles:true})); ${blur ? "el.blur();" : ""} return el.value; })()`);
  const clickId = (id) => ev(`(() => { const el = document.querySelector('[data-testid=${id}]'); if(!el) return false; el.click(); return true; })()`);
  const key = (k, mods = {}) => ev(`window.dispatchEvent(new KeyboardEvent('keydown',{key:${JSON.stringify(k)},bubbles:true,cancelable:true,ctrlKey:${!!mods.ctrl},shiftKey:${!!mods.shift}}))`);
  const setFile = async (testid, path) => {
    const { root: dom } = await cdp("DOM.getDocument", { depth: 1 });
    const { nodeId } = await cdp("DOM.querySelector", { nodeId: dom.nodeId, selector: `[data-testid=${testid}]` });
    await cdp("DOM.setFileInputFiles", { nodeId, files: [path.replace(/\//g, "\\")] });
  };
  const login = async (user, pass) => {
    await cdp("Page.navigate", { url: `${origin}/app/login` });
    await waitFor("!!document.querySelector('[data-testid=login-email-input]')");
    await ev(`(() => { const set = (s, v) => { const el = document.querySelector(s); Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
      set('[data-testid=login-email-input]', ${JSON.stringify(user)}); set('[data-testid=login-password-input]', ${JSON.stringify(pass)}); document.querySelector('[data-testid=login-submit-button]').click(); return true; })()`);
    await waitFor("!location.pathname.includes('login')");
  };
  // risorse del browser (separate da quelle del backend): heap JS, DOM, task CPU
  const perf = async () => {
    const m = Object.fromEntries((await cdp("Performance.getMetrics")).metrics.map((x) => [x.name, x.value]));
    const heap = await ev("performance.memory ? performance.memory.usedJSHeapSize : null");
    return { js_heap_mb: heap == null ? null : +(heap / 1048576).toFixed(1), cdp_js_heap_mb: +(m.JSHeapUsedSize / 1048576).toFixed(1), dom_nodes: m.Nodes, listeners: m.JSEventListeners, task_s: +m.TaskDuration.toFixed(2), script_s: +m.ScriptDuration.toFixed(2), layout_s: +m.LayoutDuration.toFixed(2) };
  };
  const kill = async () => { try { await cdp("Browser.close", {}, 5000); } catch { /* chiuso */ } try { proc.kill(); } catch { /* gia' chiuso */ } await delay(800); };
  return { cdp, ev, shot, viewport, mouse, click, drag, waitFor, api, setSelect, setInput, clickId, key, setFile, login, perf, kill, pid: proc.pid };
}
