import { useRef, useState } from "react";
import api, { formatApiError } from "@/lib/api";

function newKey() {
  return window.crypto?.randomUUID?.() || `floor-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function FloorWorkflowLauncher({ trace, onLaunched, onRefresh }) {
  const [objective, setObjective] = useState("");
  const [context, setContext] = useState("");
  const [source, setSource] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const key = useRef(newKey());
  const note = context.trim();
  const origin = source.trim();
  const ready = confirmed && objective.trim().length >= 3 && note.length > 0 && origin.length >= 3 && origin !== note;

  async function launch(event) {
    event.preventDefault();
    if (!ready || busy) return;
    setBusy(true); setError("");
    try {
      const response = await api.post("/jarvis/floor-workflow", {
        objective: objective.trim(),
        context: {
          user_input: note.slice(0, 4000),
          evidence_records: [{ evidence_id: "SRC_1", note: note.slice(0, 4000), source: origin.slice(0, 4000) }],
        },
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
      <p className="mt-1 text-xs text-muted-foreground">Produce una proposta interna. La fonte la indichi tu: non è una verifica indipendente. Accettare non pubblica e non consegna nulla.</p>
      <form onSubmit={launch} className="mt-3 space-y-2">
        <label className="block text-xs">Obiettivo
          <input value={objective} onChange={(event) => setObjective(event.target.value)} minLength={3} maxLength={500} required className="mt-1 w-full rounded border border-border bg-background p-2" />
        </label>
        <label className="block text-xs">Nota
          <textarea value={context} onChange={(event) => setContext(event.target.value)} maxLength={4000} minLength={1} required rows={3} className="mt-1 w-full rounded border border-border bg-background p-2" />
        </label>
        <label className="block text-xs">Fonte esterna
          <input value={source} onChange={(event) => setSource(event.target.value)} minLength={3} maxLength={4000} required className="mt-1 w-full rounded border border-border bg-background p-2" />
        </label>
        <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} /> Confermo l’avvio del workflow interno.</label>
        <button type="submit" disabled={busy || !ready} className="rounded border border-primary px-3 py-2 text-xs disabled:opacity-50">{busy ? "Invio…" : "Avvia workflow"}</button>
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
