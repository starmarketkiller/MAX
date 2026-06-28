/* NEXUS dashboard — vanilla JS, zero build */
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
let TOKEN = localStorage.getItem("nexus_token") || "";
let pollTimer = null;
let activeTab = "overview";

// ---------- API helpers ----------
async function api(path, opts = {}) {
  const headers = opts.headers || {};
  if (TOKEN) headers["Authorization"] = "Bearer " + TOKEN;
  if (opts.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const r = await fetch(path, { ...opts, headers });
  if (r.status === 401) { logout(); throw new Error("unauthorized"); }
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch (e) {}
    throw new Error(msg);
  }
  return r.status === 204 ? null : r.json();
}
const fmt = (n, d = 2) => (n === null || n === undefined || isNaN(n)) ? "—" : Number(n).toFixed(d);
const cls = (n) => (Number(n) > 0 ? "pos" : Number(n) < 0 ? "neg" : "");

function toast(msg, ok = true) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast " + (ok ? "ok" : "bad");
  setTimeout(() => (t.className = "toast hidden"), 2600);
}

// ---------- Auth ----------
$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#loginErr").textContent = "";
  try {
    const r = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: $("#user").value, password: $("#pass").value }),
    });
    TOKEN = r.token;
    localStorage.setItem("nexus_token", TOKEN);
    enterApp(r.user);
  } catch (err) {
    $("#loginErr").textContent = "Credenziali non valide";
  }
});

function logout() {
  TOKEN = "";
  localStorage.removeItem("nexus_token");
  if (pollTimer) clearInterval(pollTimer);
  $("#app").classList.add("hidden");
  $("#login").classList.remove("hidden");
}
$("#logout").addEventListener("click", logout);

function enterApp(user) {
  $("#login").classList.add("hidden");
  $("#app").classList.remove("hidden");
  $("#whoami").textContent = user || "";
  switchTab("overview");
  startPolling();
}

// ---------- Tabs ----------
$$("#tabs button").forEach((b) =>
  b.addEventListener("click", () => switchTab(b.dataset.tab))
);
function switchTab(name) {
  activeTab = name;
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  $$(".tab").forEach((s) => s.classList.add("hidden"));
  $("#tab-" + name).classList.remove("hidden");
  loadTab(name);
}
function loadTab(name) {
  if (name === "overview") loadOverview();
  else if (name === "journal") loadJournal();
  else if (name === "strategies") loadStrategies();
  else if (name === "chain") loadChain();
  else if (name === "settings") loadSettings();
  else if (name === "bridge") loadBridge();
}

// ---------- Polling ----------
function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => {
    if (activeTab === "overview") loadOverview();
    else if (activeTab === "bridge") loadBridge();
  }, 4000);
}

// ---------- Overview ----------
async function loadOverview() {
  let d;
  try { d = await api("/api/dashboard/overview"); } catch (e) { return; }
  const anyOnline = d.eas.some((e) => e._online);
  $("#liveDot").className = "dot " + (anyOnline ? "on" : "off");

  $("#eaCards").innerHTML = d.eas.length ? d.eas.map(eaCard).join("") :
    `<div class="card muted">Nessun EA collegato. Avvia l'EA in MT5 con InpEnableWebSync=true e InpWebURL puntato a questo backend.</div>`;

  const rows = [];
  d.eas.forEach((ea) => (ea.positions || []).forEach((p) => rows.push(posRow(p))));
  $("#posTable tbody").innerHTML = rows.length ? rows.join("") :
    `<tr><td colspan="11" class="muted">Nessuna posizione aperta.</td></tr>`;
  bindCmdButtons();
}

function eaCard(ea) {
  const onBadge = ea.eaPaused ? `<span class="badge paused">IN PAUSA</span>`
    : ea._online ? `<span class="badge on">ONLINE</span>`
    : `<span class="badge off">OFFLINE</span>`;
  return `<div class="ea">
    <div class="ea-head"><span class="sym">${ea.symbol || "?"}</span>${onBadge}</div>
    <div class="kv"><span class="muted">Balance</span><b>${fmt(ea.balance)}</b></div>
    <div class="kv"><span class="muted">Equity</span><b>${fmt(ea.equity)}</b></div>
    <div class="kv"><span class="muted">Float P&L</span><b class="${cls(ea.floatPnL)}">${fmt(ea.floatPnL)}</b></div>
    <div class="kv"><span class="muted">Daily P&L</span><b class="${cls(ea.dailyPnL)}">${fmt(ea.dailyPnL)}</b></div>
    <div class="kv"><span class="muted">Drawdown</span><b>${fmt(ea.drawdownPct)}%</b></div>
    <div class="kv"><span class="muted">Trades oggi</span><b>${ea.tradesToday ?? "—"}</b></div>
    <div class="kv"><span class="muted">HTF / Vel</span><b>${ea.htfBias || "—"} / ${ea.velocity || "—"}</b></div>
    <div class="kv"><span class="muted">Sessione</span><b>${ea.session || "—"}</b></div>
    <div class="ea-actions">
      ${ea.eaPaused
        ? `<button class="cmd" data-action="resume">Riprendi</button>`
        : `<button class="cmd warn" data-action="pause">Pausa</button>`}
      <button class="cmd danger" data-action="close_all">Chiudi tutto</button>
    </div>
  </div>`;
}

function posRow(p) {
  return `<tr>
    <td>${p.ticket}</td><td>${p.symbol}</td>
    <td>${p.side}</td><td>${fmt(p.lots)}</td>
    <td>${fmt(p.openPrice)}</td><td>${fmt(p.currentPrice)}</td>
    <td>${fmt(p.sl)}</td><td>${fmt(p.tp)}</td>
    <td class="${cls(p.pnl)}">${fmt(p.pnl)}</td>
    <td>${p.strategy || "—"}</td>
    <td><button class="cmd danger" data-action="close_position" data-ticket="${p.ticket}">Chiudi</button></td>
  </tr>`;
}

function bindCmdButtons() {
  $$(".cmd").forEach((b) =>
    b.addEventListener("click", async () => {
      const body = { action: b.dataset.action };
      if (b.dataset.ticket) body.ticket = Number(b.dataset.ticket);
      try {
        await api("/api/dashboard/command", { method: "POST", body: JSON.stringify(body) });
        toast("Comando '" + body.action + "' inviato all'EA");
        setTimeout(loadOverview, 800);
      } catch (e) { toast("Errore: " + e.message, false); }
    })
  );
}

// ---------- Journal ----------
async function loadJournal() {
  const d = await api("/api/dashboard/journal");
  const s = d.summary;
  const wr = s.n ? ((s.wins / s.n) * 100).toFixed(1) : "0";
  $("#journalSummary").innerHTML = `
    <div class="card"><div class="muted">Trade totali</div><div class="stat-num">${s.n}</div></div>
    <div class="card"><div class="muted">P&L totale</div><div class="stat-num ${cls(s.total)}">${fmt(s.total)}</div></div>
    <div class="card"><div class="muted">Win rate</div><div class="stat-num">${wr}%</div></div>
    <div class="card"><div class="muted">Win / Loss</div><div class="stat-num">${s.wins||0}/${s.losses||0}</div></div>`;
  $("#journalTable tbody").innerHTML = d.trades.length ? d.trades.map((t) => `<tr>
    <td>${t.ticket}</td><td>${t.symbol||"—"}</td><td>${t.strategy||"—"}</td>
    <td>${t.side||"—"}</td><td>${fmt(t.lots)}</td>
    <td>${t.open_time||"—"}</td><td>${t.close_time||"—"}</td>
    <td class="${cls(t.pnl)}">${fmt(t.pnl)}</td><td>${t.reason||"—"}</td></tr>`).join("")
    : `<tr><td colspan="9" class="muted">Nessun trade sincronizzato. L'EA invia lo storico su /api/ea/trade_history_sync.</td></tr>`;
}

// ---------- Strategies ----------
async function loadStrategies() {
  const d = await api("/api/dashboard/strategy_stats");
  if (!d.stats.length) {
    $("#stratWrap").innerHTML = `<div class="card muted">Nessuna statistica strategia ricevuta ancora.</div>`;
    return;
  }
  $("#stratWrap").innerHTML = d.stats.map((blk) => {
    const rows = (blk.data.strategies || []).map((r) => `<tr>
      <td>${r.name}</td><td>${r.enabled ? "✓" : "—"}</td>
      <td>${r.called||0}</td><td>${r.signals||0}</td><td>${r.executed||0}</td>
      <td class="pos">${r.wins||0}</td><td class="neg">${r.losses||0}</td>
      <td>${r.health||"—"}</td></tr>`).join("");
    return `<h3>${blk.symbol}</h3><div class="table-wrap"><table>
      <thead><tr><th>Strategia</th><th>On</th><th>Called</th><th>Signals</th>
      <th>Exec</th><th>Win</th><th>Loss</th><th>Health</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="8" class="muted">—</td></tr>`}</tbody></table></div>`;
  }).join("");
}

// ---------- Strategy Chain ----------
async function loadChain() {
  const cfg = await api("/api/strategy_chain/config");
  $("#chainJson").value = JSON.stringify(cfg, null, 2);
}
$("#chainSave").addEventListener("click", async () => {
  try {
    const cfg = JSON.parse($("#chainJson").value);
    await api("/api/strategy_chain/config", { method: "PUT", body: JSON.stringify(cfg) });
    $("#chainMsg").textContent = "Salvato ✓"; toast("Strategy chain salvata");
  } catch (e) { $("#chainMsg").textContent = "JSON non valido: " + e.message; }
});

// ---------- Settings ----------
async function loadSettings() {
  const s = await api("/api/dashboard/settings");
  $("#settingsForm").innerHTML = Object.entries(s).map(([k, v]) => {
    if (typeof v === "boolean") {
      return `<div class="field"><label>${k}</label>
        <select data-key="${k}" data-type="bool">
          <option value="true" ${v ? "selected" : ""}>true</option>
          <option value="false" ${!v ? "selected" : ""}>false</option></select></div>`;
    }
    return `<div class="field"><label>${k}</label>
      <input data-key="${k}" data-type="num" value="${v}" /></div>`;
  }).join("");
  $("#lockedJson").value = JSON.stringify(await api("/api/dashboard/locked_profiles"), null, 2);
}
$("#settingsSave").addEventListener("click", async () => {
  const out = {};
  $$("#settingsForm [data-key]").forEach((el) => {
    out[el.dataset.key] = el.dataset.type === "bool" ? el.value === "true" : Number(el.value);
  });
  try {
    await api("/api/dashboard/settings", { method: "PUT", body: JSON.stringify(out) });
    $("#settingsMsg").textContent = "Salvato ✓"; toast("Settings salvati");
  } catch (e) { $("#settingsMsg").textContent = "Errore: " + e.message; }
});
$("#lockedSave").addEventListener("click", async () => {
  try {
    const data = JSON.parse($("#lockedJson").value);
    await api("/api/dashboard/locked_profiles", { method: "PUT", body: JSON.stringify(data) });
    $("#lockedMsg").textContent = "Salvato ✓"; toast("Locked profiles salvati");
  } catch (e) { $("#lockedMsg").textContent = "JSON non valido: " + e.message; }
});

// ---------- Local Bridge ----------
async function loadBridge() {
  const d = await api("/api/local_bridge/status");
  $("#bridgeHosts").innerHTML = d.hosts.length ? d.hosts.map((h) => `
    <div class="card">
      <div class="ea-head"><b>${h.host_id}</b>
        <span class="badge ${h.online ? "on" : "off"}">${h.online ? "ONLINE" : "OFFLINE"}</span></div>
      <div class="kv"><span class="muted">Versione</span><b>${h.version || "—"}</b></div>
      <div class="kv"><span class="muted">OS</span><b>${h.os || "—"}</b></div>
    </div>`).join("")
    : `<div class="card muted">Nessun worker collegato. Avvia nexus_local_worker.py sul PC con MT5.</div>`;
  $("#bridgeCmds tbody").innerHTML = d.commands.length ? d.commands.map((c) => `<tr>
    <td>${new Date(c.created_at * 1000).toLocaleString()}</td>
    <td>${c.host_id}</td><td>${c.action}</td><td>${c.status}</td><td>${c.error || ""}</td></tr>`).join("")
    : `<tr><td colspan="5" class="muted">—</td></tr>`;
}
$("#bridgeSend").addEventListener("click", async () => {
  const body = { action: $("#bridgeAction").value, host_id: $("#bridgeHost").value || "default", payload: {} };
  try {
    await api("/api/local_bridge/enqueue", { method: "POST", body: JSON.stringify(body) });
    $("#bridgeMsg").textContent = "Inviato ✓"; toast("Comando worker accodato");
    setTimeout(loadBridge, 800);
  } catch (e) { $("#bridgeMsg").textContent = "Errore: " + e.message; }
});

// ---------- Boot ----------
(async function boot() {
  if (TOKEN) {
    try { const m = await api("/api/auth/me"); enterApp(m.user); }
    catch (e) { logout(); }
  }
})();
