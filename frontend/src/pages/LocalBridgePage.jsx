import { useCallback, useEffect, useState } from "react";
import api from "@/lib/api";
import {
  Cpu, RefreshCcw, Play, Hammer, RotateCw, Power, Download,
  CheckCircle2, XCircle, Clock3, Terminal, FileCode2,
} from "lucide-react";

function cls(...c) { return c.filter(Boolean).join(" "); }

function StatusDot({ online }) {
  return (
    <span className="relative flex h-2.5 w-2.5">
      <span className={cls(
        "relative inline-flex h-2.5 w-2.5 rounded-full",
        online ? "bg-emerald-400" : "bg-rose-500"
      )} />
      {online && (
        <span className="absolute inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400 opacity-75 animate-ping" />
      )}
    </span>
  );
}

function CmdStatusBadge({ status }) {
  const map = {
    pending: { cls: "bg-amber-500/15 text-amber-400 border-amber-500/30", icon: Clock3, label: "pending" },
    running: { cls: "bg-sky-500/15 text-sky-400 border-sky-500/30 animate-pulse", icon: RotateCw, label: "running" },
    done:    { cls: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30", icon: CheckCircle2, label: "done" },
    failed:  { cls: "bg-rose-500/15 text-rose-400 border-rose-500/30", icon: XCircle, label: "failed" },
  };
  const m = map[status] || map.pending;
  const Icon = m.icon;
  return (
    <span className={cls("inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium border", m.cls)}>
      <Icon className="h-3 w-3" />{m.label}
    </span>
  );
}

export default function LocalBridgePage() {
  const [status, setStatus] = useState({ worker: { online: false }, commands: [] });
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/local_bridge/status");
      setStatus(r.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  const enqueue = async (action, payload = {}) => {
    setSending(action);
    try {
      await api.post("/local_bridge/enqueue", { action, payload, host_id: "default" });
      await load();
    } catch (e) {
      alert(`Errore: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setSending(null);
    }
  };

  const worker = status.worker || { online: false };
  const onlineSince = worker.last_seen
    ? new Date(worker.last_seen).toLocaleString()
    : "—";

  return (
    <div className="space-y-6" data-testid="local-bridge-page">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Cpu className="h-6 w-6 text-sky-500" /> MT5 Local Bridge
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
            Controlla il tuo MetaTrader 5 locale dal cloud. Compila l'EA, riavvia
            MT5, deploya nuovi file e applica template direttamente dal dashboard.
          </p>
        </div>
        <button onClick={load} disabled={loading}
                className="flex items-center gap-2 px-3 py-2 rounded-md border border-border text-sm hover:bg-secondary"
                data-testid="bridge-refresh-btn">
          <RefreshCcw className={cls("h-3.5 w-3.5", loading && "animate-spin")} />
          Aggiorna
        </button>
      </div>

      {/* Worker status card */}
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <StatusDot online={!!worker.online} />
            <div>
              <div className="text-sm font-semibold" data-testid="worker-state">
                Worker {worker.online ? "Online" : "Offline"}
              </div>
              <div className="text-xs text-muted-foreground font-mono">
                host_id: <b>default</b> · last seen: {onlineSince}
              </div>
            </div>
          </div>
          {!worker.online && (
            <a
              href="/api/downloads/local_worker"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-3 py-2 rounded-md bg-sky-600 hover:bg-sky-700 text-white text-sm"
              data-testid="download-worker-btn"
            >
              <Download className="h-4 w-4" /> Scarica Worker Python
            </a>
          )}
        </div>

        {!worker.online && (
          <div className="mt-4 p-3 rounded bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200">
            <b>Il worker non è online.</b> Per attivarlo:
            <ol className="list-decimal pl-5 mt-1 space-y-0.5">
              <li>Scarica lo script <code className="bg-secondary px-1 rounded">nexus_local_worker.py</code></li>
              <li>Installa dipendenze: <code className="bg-secondary px-1 rounded">pip install requests</code></li>
              <li>Avvia: <code className="bg-secondary px-1 rounded">python nexus_local_worker.py</code></li>
              <li>Modifica <code className="bg-secondary px-1 rounded">nexus_worker.config.json</code> con i tuoi path MT5</li>
            </ol>
          </div>
        )}

        {worker.online && (
          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            <div className="p-2 rounded bg-secondary/50">
              <div className="text-muted-foreground">Worker v.</div>
              <div className="font-mono font-semibold">{worker.version || "?"}</div>
            </div>
            <div className="p-2 rounded bg-secondary/50">
              <div className="text-muted-foreground">OS</div>
              <div className="font-mono font-semibold truncate" title={worker.os}>{worker.os || "?"}</div>
            </div>
            <div className="p-2 rounded bg-secondary/50 col-span-2">
              <div className="text-muted-foreground">MT5 path</div>
              <div className="font-mono text-[10px] truncate" title={worker.mt5_path}>{worker.mt5_path || "?"}</div>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="text-xs font-semibold uppercase text-muted-foreground mb-3 flex items-center gap-2">
          <Terminal className="h-3.5 w-3.5" /> Azioni rapide
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <ActionButton
            label="Compila EA"
            icon={Hammer}
            disabled={!worker.online || sending}
            sending={sending === "compile_ea"}
            onClick={() => enqueue("compile_ea", { source: "Experts/NEXUS_EA_v2.mq5" })}
            testId="action-compile"
            color="bg-blue-600 hover:bg-blue-700"
          />
          <ActionButton
            label="Riavvia MT5"
            icon={RotateCw}
            disabled={!worker.online || sending}
            sending={sending === "restart_mt5"}
            onClick={() => enqueue("restart_mt5")}
            testId="action-restart"
            color="bg-amber-600 hover:bg-amber-700"
          />
          <ActionButton
            label="Ping Worker"
            icon={Power}
            disabled={!worker.online || sending}
            sending={sending === "ping"}
            onClick={() => enqueue("ping")}
            testId="action-ping"
            color="bg-sky-600 hover:bg-sky-700"
          />
          <ActionButton
            label="Deploy EA v2.0.13"
            icon={FileCode2}
            disabled={!worker.online || sending}
            sending={sending === "deploy"}
            onClick={() => enqueue("deploy_files", { files: [] })}
            testId="action-deploy"
            color="bg-emerald-600 hover:bg-emerald-700"
            note="Deploya MQL5 files (full reset → riavvia MT5 dopo)"
          />
        </div>
      </div>

      {/* Recent commands */}
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="text-xs font-semibold uppercase text-muted-foreground mb-3">
          Ultimi 20 comandi
        </div>
        {status.commands?.length === 0 ? (
          <div className="text-center py-6 text-sm text-muted-foreground">
            Nessun comando ancora inviato
          </div>
        ) : (
          <div className="space-y-1.5" data-testid="cmd-history">
            {status.commands.map((c) => (
              <div key={c._id} className="flex items-start justify-between gap-3 p-2 rounded bg-secondary/30 text-xs">
                <div className="flex items-center gap-2 min-w-0">
                  <CmdStatusBadge status={c.status} />
                  <span className="font-mono font-semibold truncate">{c.action}</span>
                  <span className="text-muted-foreground text-[10px]">
                    {new Date(c.created_at).toLocaleTimeString()}
                  </span>
                </div>
                {c.error && <span className="text-rose-400 truncate max-w-md" title={c.error}>{c.error}</span>}
                {c.result?.exit_code != null && (
                  <span className={cls(
                    "font-mono",
                    c.result.exit_code === 0 ? "text-emerald-400" : "text-rose-400"
                  )}>
                    exit={c.result.exit_code}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ActionButton({ label, icon: Icon, disabled, sending, onClick, testId, color, note }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className={cls(
        "flex flex-col items-start gap-2 p-3 rounded-lg text-left text-white transition",
        disabled ? "opacity-50 cursor-not-allowed bg-secondary text-foreground" : color
      )}
    >
      <div className="flex items-center gap-2">
        {sending ? <RotateCw className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
        <span className="font-semibold text-sm">{label}</span>
      </div>
      {note && <div className="text-[10px] opacity-80">{note}</div>}
    </button>
  );
}
