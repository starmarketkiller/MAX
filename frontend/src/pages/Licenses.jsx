import { useCallback, useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { Copy, Plus, Trash2, RefreshCcw, Power, Calendar, Globe, Smartphone } from "lucide-react";

function classNames(...c) { return c.filter(Boolean).join(" "); }

function StatusPill({ active, expired, trial }) {
  let label = "ACTIVE", cls = "bg-emerald-500/15 text-emerald-600 border-emerald-500/30";
  if (expired) { label = "EXPIRED"; cls = "bg-rose-500/15 text-rose-600 border-rose-500/30"; }
  else if (!active) { label = "DISABLED"; cls = "bg-amber-500/15 text-amber-600 border-amber-500/30"; }
  else if (trial) { label = "TRIAL"; cls = "bg-sky-500/15 text-sky-600 border-sky-500/30"; }
  return (
    <span className={classNames("px-2 py-0.5 rounded text-[10px] font-bold border", cls)}>
      {label}
    </span>
  );
}

function CreateForm({ onCreated }) {
  const [client, setClient] = useState("");
  const [plan, setPlan] = useState("STANDARD");
  const [days, setDays] = useState(365);
  const [demoOnly, setDemoOnly] = useState(false);
  const [busy, setBusy] = useState(false);
  const [lastKey, setLastKey] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      const { data } = await api.post("/license/create", {
        client, plan, days: Number(days) || 365, demo_only: demoOnly,
      });
      setLastKey(data.key);
      setClient(""); setPlan("STANDARD"); setDays(365); setDemoOnly(false);
      onCreated && onCreated();
    } catch (e) {
      console.error("create license failed", e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-xl border border-border bg-card p-5 space-y-3"
          data-testid="license-create-form">
      <div className="flex items-center gap-2 font-semibold">
        <Plus className="h-4 w-4" /> Issue new license
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label className="space-y-1 text-sm">
          <span className="text-muted-foreground text-xs">Client name</span>
          <input className="w-full px-3 py-2 rounded-md bg-background border border-border text-sm"
                 value={client} onChange={e=>setClient(e.target.value)}
                 placeholder="e.g. Mario Rossi"
                 data-testid="license-client-input"/>
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-muted-foreground text-xs">Plan</span>
          <select className="w-full px-3 py-2 rounded-md bg-background border border-border text-sm"
                  value={plan} onChange={e=>setPlan(e.target.value)}
                  data-testid="license-plan-select">
            <option value="STANDARD">STANDARD</option>
            <option value="PRO">PRO</option>
            <option value="LIFETIME">LIFETIME</option>
            <option value="VIP">VIP</option>
          </select>
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-muted-foreground text-xs">Validity (days)</span>
          <input type="number" min="1" max="3650"
                 className="w-full px-3 py-2 rounded-md bg-background border border-border text-sm"
                 value={days} onChange={e=>setDays(e.target.value)}
                 data-testid="license-days-input"/>
        </label>
        <label className="flex items-center gap-2 text-sm pt-6">
          <input type="checkbox" checked={demoOnly} onChange={e=>setDemoOnly(e.target.checked)}
                 data-testid="license-demoonly-checkbox"/>
          <span>Demo accounts only</span>
        </label>
      </div>
      <div className="flex items-center justify-between pt-2">
        {lastKey && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Generated:</span>
            <code className="font-mono text-emerald-600 dark:text-emerald-400 select-all">{lastKey}</code>
            <button type="button"
                    onClick={()=>navigator.clipboard.writeText(lastKey).catch(
                      ()=>window.alert("Copia negata dal browser: seleziona e copia manualmente."))}
                    className="p-1 hover:text-foreground" title="Copy"
                    data-testid="license-copy-last-btn">
              <Copy className="h-3.5 w-3.5"/>
            </button>
          </div>
        )}
        <button type="submit" disabled={busy}
                className="ml-auto px-4 py-2 rounded-md bg-sky-600 hover:bg-sky-500 text-white text-sm font-medium disabled:opacity-50"
                data-testid="license-create-submit-btn">
          {busy ? "Creating..." : "Create license"}
        </button>
      </div>
    </form>
  );
}

function LicenseRow({ lic, onChanged, onError }) {
  // Il backend calcola lo stato: EXPIRED tiene conto anche della revoca.
  const expired = lic.status === "EXPIRED";
  const expDate = lic.expires_at ? new Date(lic.expires_at * 1000) : null;
  const expStr = expDate ? expDate.toLocaleDateString() : "never";
  const lastSeen = lic.last_verified_at
    ? new Date(lic.last_verified_at * 1000).toLocaleString() : "—";

  // AUD0-FE-LIC-004: abilitazione, estensione e revoca partivano al primo
  // click, senza conferma né motivazione registrata.
  const run = async (fn) => {
    try { await fn(); onChanged(); }
    catch (e) { onError(formatApiError(e?.response?.data?.detail) || e.message); }
  };

  const toggleActive = () => {
    if (lic.active) {
      // eslint-disable-next-line no-alert
      const reason = window.prompt(
        `Disabilitare la licenza ${lic.fingerprint}?\n\n` +
        "L'EA associato smetterà di validarsi al prossimo controllo.\n" +
        "Indica il motivo (registrato nell'audit):");
      if (!reason) return;
      return run(() => api.patch(`/license/${lic.id}`, { active: false, reason }));
    }
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Riattivare la licenza ${lic.fingerprint}?`)) return;
    return run(() => api.patch(`/license/${lic.id}`, { active: true, reason: "riattivazione" }));
  };

  const extend = (n) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(
      `Estendere di ${n} giorni la licenza ${lic.fingerprint}?\n\n` +
      `Scadenza attuale: ${expStr}`)) return;
    return run(() => api.patch(`/license/${lic.id}`,
      { extend_days: n, reason: `estensione di ${n} giorni` }));
  };

  const remove = () => {
    // eslint-disable-next-line no-alert
    const reason = window.prompt(
      `Revocare la licenza ${lic.fingerprint}?\n\n` +
      "La licenza resta nello storico ma non sarà più valida.\n" +
      "Indica il motivo (obbligatorio, registrato nell'audit):");
    if (!reason) return;
    return run(() => api.delete(`/license/${lic.id}`, { params: { reason } }));
  };

  return (
    <tr className="border-t border-border hover:bg-secondary/40 transition-colors"
        data-testid={`license-row-${lic.id}`}>
      <td className="py-3 px-3">
        {/* AUD0-FE-LIC-001 / AUD0-FE-LIC-002: la tabella mostrava la chiave
            riutilizzabile per intero, con copia in un click. Ora il backend
            restituisce solo un'impronta non riutilizzabile. */}
        <div className="flex items-center gap-2">
          <code className="font-mono text-xs" title="Impronta: la chiave completa non è recuperabile">
            {lic.fingerprint}
          </code>
        </div>
      </td>
      <td className="py-3 px-3 text-sm">{lic.client || "—"}</td>
      <td className="py-3 px-3 text-sm">{lic.plan}</td>
      <td className="py-3 px-3 text-sm font-mono">{lic.account || "—"}</td>
      <td className="py-3 px-3 text-sm">
        <StatusPill active={lic.active} expired={expired} trial={lic.trial}/>
      </td>
      <td className="py-3 px-3 text-sm">{expStr}</td>
      <td className="py-3 px-3 text-xs text-muted-foreground">{lastSeen}</td>
      <td className="py-3 px-3">
        <div className="flex items-center justify-end gap-1">
          <button onClick={()=>extend(30)} title="+30 days"
                  className="p-1.5 hover:bg-secondary rounded text-muted-foreground hover:text-foreground"
                  data-testid={`license-extend-${lic.id}`}>
            <Calendar className="h-3.5 w-3.5"/>
          </button>
          <button onClick={toggleActive} title={lic.active ? "Disable" : "Enable"}
                  className={classNames("p-1.5 rounded",
                    lic.active ? "text-amber-600 hover:bg-amber-500/10" : "text-emerald-600 hover:bg-emerald-500/10")}
                  data-testid={`license-toggle-${lic.id}`}>
            <Power className="h-3.5 w-3.5"/>
          </button>
          <button onClick={remove} title="Delete"
                  className="p-1.5 text-rose-600 hover:bg-rose-500/10 rounded"
                  data-testid={`license-delete-${lic.id}`}>
            <Trash2 className="h-3.5 w-3.5"/>
          </button>
        </div>
      </td>
    </tr>
  );
}

export default function LicensesPage() {
  const [licenses, setLicenses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState("");
  const [enforcement, setEnforcement] = useState("");

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/license/list");
      setLicenses(data.licenses || []);
      setMode(data.mode || "");
      setEnforcement(data.enforcement || "");
      setError("");
    } catch (e) {
      console.error("license fetch failed", e);
      setError(formatApiError(e?.response?.data?.detail) || "caricamento licenze fallito");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  return (
    <div className="space-y-6" data-testid="licenses-page">
      {/* AUD0-LIC-001: se l'enforcement è disattivato, la pagina non deve
          far credere che le licenze stiano proteggendo qualcosa. */}
      {enforcement === "disabled" && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
          <b>Enforcement disattivato</b> (NEXUS_LICENSE_MODE={mode}). Qualunque
          chiave viene accettata dall'EA: questa pagina è amministrativa, non
          sta proteggendo l'accesso al prodotto.
        </div>
      )}
      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-700 dark:text-rose-400 flex justify-between gap-3">
          <span>{error}</span>
          <button type="button" className="underline" onClick={()=>setError("")}>chiudi</button>
        </div>
      )}
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Licenses</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage NEXUS EA license keys, account bindings and expirations.
          </p>
        </div>
        <button onClick={fetchAll} disabled={loading}
                className="flex items-center gap-2 px-3 py-2 rounded-md border border-border text-sm hover:bg-secondary"
                data-testid="license-refresh-btn">
          <RefreshCcw className={classNames("h-3.5 w-3.5", loading && "animate-spin")}/>
          Refresh
        </button>
      </div>

      {/* URL banner - so user can always find/share the backend URL */}
      <div className="rounded-xl border border-sky-500/30 bg-gradient-to-br from-sky-500/10 to-indigo-500/5 p-5"
           data-testid="dashboard-url-banner">
        <div className="flex items-start gap-3 flex-wrap">
          <div className="flex-shrink-0 h-10 w-10 rounded-lg bg-sky-500/15 flex items-center justify-center">
            <Globe className="h-5 w-5 text-sky-600 dark:text-sky-400"/>
          </div>
          <div className="flex-1 min-w-[260px]">
            <div className="text-xs font-bold uppercase tracking-wider text-sky-700 dark:text-sky-300">
              Dashboard URL — salvalo
            </div>
            <div className="text-sm font-mono mt-1 break-all select-all" data-testid="dashboard-url-value">
              {window.location.origin}
            </div>
            <div className="text-xs text-muted-foreground mt-2 flex items-center gap-1.5">
              <Smartphone className="h-3 w-3"/>
              Apri questo link dal tuo telefono e aggiungi alla schermata home per accesso rapido.
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <button onClick={() => navigator.clipboard.writeText(window.location.origin)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium"
                    data-testid="dashboard-url-copy">
              <Copy className="h-3 w-3"/> Copia URL
            </button>
            <a href={window.location.origin} target="_blank" rel="noreferrer"
               className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border text-xs hover:bg-secondary text-center">
              Apri in nuova tab
            </a>
          </div>
        </div>
      </div>

      <CreateForm onCreated={fetchAll}/>

      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="px-5 py-3 border-b border-border bg-secondary/30 text-sm font-semibold">
          Active licenses ({licenses.length})
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted-foreground bg-secondary/20">
              <tr>
                <th className="text-left py-2 px-3 font-medium">Impronta</th>
                <th className="text-left py-2 px-3 font-medium">Client</th>
                <th className="text-left py-2 px-3 font-medium">Plan</th>
                <th className="text-left py-2 px-3 font-medium">Account</th>
                <th className="text-left py-2 px-3 font-medium">Status</th>
                <th className="text-left py-2 px-3 font-medium">Expires</th>
                <th className="text-left py-2 px-3 font-medium">Ultima verifica</th>
                <th className="text-right py-2 px-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {licenses.length === 0 ? (
                <tr>
                  <td colSpan="8" className="py-8 text-center text-muted-foreground">
                    No licenses yet. Create one above to get started.
                  </td>
                </tr>
              ) : licenses.map((lic) => (
                <LicenseRow key={lic.id} lic={lic} onChanged={fetchAll} onError={setError}/>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
