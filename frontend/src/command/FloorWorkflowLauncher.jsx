import { useRef, useState } from "react";
import api, { formatApiError } from "@/lib/api";

function newKey() {
  return window.crypto?.randomUUID?.() || `floor-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function FloorWorkflowLauncher({ trace, onLaunched, onRefresh }) {
  const [objective, setObjective] = useState("");
  const [context, setContext] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const key = useRef(newKey());

  async function launch(event) {
    event.preventDefault();
    if (!confirmed || busy) return;
    setBusy(true); setError("");
    try {
      const evidence = context.trim()
        ? [{ evidence_id: "USER_CONTEXT_1", note: context.trim().slice(0, 4000) }]
        : [];
      const response = await api.post("/jarvis/floor-workflow", {
        objective: objective.trim(), context: { evidence_records: evidence },
      }, { headers: { "Idempotency-Key": key.current } });
      onLaunched(response.data.task_id);
      key.current = newKey();
      setConfirmed(false);
    } catch (caught) {
      setError(formatApiError(caught?.response?.data?.detail || caught.message));
    } finally { setBusy(false); }
  }

  async function decide(action) {
    if (busy || trace?.state !== "WAITING_APPROVAL" || trace?.approval_effect !== "ACCEPT_ONLY") return;
    setBusy(true); setError("");
    try {
      await api.post(`/jarvis/approvals/${trace.task_id}`, { action });
      await onRefresh();
    } catch (caught) {
      setError(formatApiError(caught?.response?.data?.detail || caught.message));
    } finally { setBusy(false); }
  }

  return (
    <section className="mb-4 border border-border p-4" aria-label="Avvia workflow reale">
      <h2 className="text-sm font-semibold">Jarvis → Agency · workflow reale</h2>
      <p className="mt-1 text-xs text-muted-foreground">Produce una proposta interna verificata. Accettare non pubblica e non consegna nulla.</p>
      <form onSubmit={launch} className="mt-3 space-y-2">
        <label className="block text-xs">Obiettivo
          <input value={objective} onChange={(event) => setObjective(event.target.value)} minLength={3} maxLength={500} required className="mt-1 w-full rounded border border-border bg-background p-2" />
        </label>
        <label className="block text-xs">Contesto fornito dall’utente
          <textarea value={context} onChange={(event) => setContext(event.target.value)} maxLength={4000} minLength={1} required rows={3} className="mt-1 w-full rounded border border-border bg-background p-2" />
        </label>
        <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /> Confermo l’avvio del workflow interno.</label>
        <button type="submit" disabled={busy || !confirmed || objective.trim().length < 3 || !context.trim()} className="rounded border border-primary px-3 py-2 text-xs disabled:opacity-50">{busy ? "Invio…" : "Avvia workflow"}</button>
      </form>
      {error ? <p role="alert" className="mt-2 text-xs text-destructive">{error}</p> : null}
      {trace?.task_id ? <div className="mt-3 text-xs">
        <p><strong>Task:</strong> {trace.task_id} · {trace.state || "UNKNOWN"}</p>
        <p>Artifact interni: {trace.artifact_count || 0}. Contenuti sensibili non esposti.</p>
        {trace.state === "WAITING_APPROVAL" && trace.approval_effect === "ACCEPT_ONLY" ? <div className="mt-2 flex gap-2">
          <button type="button" disabled={busy} onClick={() => decide("APPROVE")} className="rounded border px-3 py-1">Approva proposta</button>
          <button type="button" disabled={busy} onClick={() => decide("REJECT")} className="rounded border px-3 py-1">Rifiuta proposta</button>
        </div> : null}
      </div> : null}
    </section>
  );
}
