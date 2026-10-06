"""NEXUS_LOCAL_TASK_LEDGER_V1 - renders the already-canonical task record
into the artifact set the operator asked for (task.md, result.md,
handoff.md, verifier_report.json, execution_log.jsonl).

Deliberately NOT a new task store: every field rendered here already lives
in TaskQueue's record (manifest + state) and its result_packet
(RESULT_PACKET_V1, core/result_packet.py - already built and attached by
core/orchestrator.py on every COMPLETED/WAITING_APPROVAL/ESCALATION_REQUIRED
transition) plus the Activity Ledger (core/ledger.py, already a
task_id-filterable JSONL - read_for_task() IS execution_log.jsonl, this
module just writes a per-task copy of it). Pure read + render: the only
write this module performs is the artifact directory itself, never task
state, never the queue, never the ledger.

handoff.md deliberately contains only verifiable actions/outputs already
recorded in RESULT_PACKET_V1 (files read/changed, tests, verifier result,
limitations, unresolved issues, suggested next tasks) - never a model's
chain-of-thought, which is never stored here because it was never an input
to this module in the first place.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

ARTIFACT_FILENAMES = ("task.md", "result.md", "handoff.md", "verifier_report.json", "execution_log.jsonl")

# NEXUS_LOCAL_TASK_LEDGER_V1 asked for CREATED/RUNNING/WAITING_REVIEW/
# COMPLETED/FAILED/BLOCKED - TaskQueue already has a richer, pre-existing
# state machine. Mapped here for documentation, never used to rename or
# duplicate the real states (core/task_queue.py remains the only source of
# truth for what state a task is actually in).
STATE_ALIAS = {
    "QUEUED": "CREATED", "RUNNING": "RUNNING", "WAITING_PROVIDER": "RUNNING",
    "WAITING_APPROVAL": "WAITING_REVIEW", "COMPLETED": "COMPLETED",
    "FAILED": "FAILED", "BLOCKED": "BLOCKED", "ESCALATION_REQUIRED": "BLOCKED",
    "CANCELLED": "FAILED",
}


def task_artifacts_dir(service, task_id: str) -> Path:
    base = Path(service.conversation_store.path).resolve().parent / "task_artifacts"
    return base / task_id


def _manifest(record: dict) -> dict:
    return record.get("manifest") or {}


def _bullets(items, empty="(nessuno)") -> str:
    items = [str(i) for i in (items or []) if str(i).strip()]
    return "\n".join(f"- {i}" for i in items) if items else empty


def render_task_md(record: dict) -> str:
    m = _manifest(record)
    lines = [
        f"# {record['task_id']}", "",
        f"- **Titolo:** {m.get('title') or '-'}",
        f"- **Obiettivo:** {m.get('objective') or '-'}",
        f"- **Stato:** {record.get('state')} (alias canonico: {STATE_ALIAS.get(record.get('state'), 'UNKNOWN')})",
        f"- **Creato da:** {m.get('created_by') or '-'}",
        f"- **Creato il:** {m.get('created_at') or '-'}",
        f"- **Aggiornato il:** {record.get('updated_at') or '-'}",
        f"- **Executor:** {record.get('executor') or 'non assegnato'}",
        f"- **Capability consentite (allowed_capabilities):** {', '.join(m.get('required_capabilities') or []) or '-'}",
        f"- **Path vietati (forbidden_capabilities):** {', '.join(m.get('files_forbidden') or []) or '-'}",
        f"- **Approvazione richiesta:** {m.get('approval_required') or '-'}",
    ]
    return "\n".join(lines) + "\n"


def render_result_md(record: dict) -> str:
    packet = record.get("result_packet") or {}
    lines = [f"# Risultato - {record['task_id']}", "",
             f"**Decisione:** {packet.get('decision') or 'N/D (task non ancora terminata)'}",
             f"**Confidence:** {packet.get('confidence') or 'N/D'}",
             f"**Stato finale:** {record.get('state')}", ""]
    if packet.get("commit"):
        lines.append(f"**Commit:** {packet['commit']} (push: {packet.get('push_status')})")
    return "\n".join(lines) + "\n"


def render_handoff_md(record: dict, events: list) -> str:
    packet = record.get("result_packet") or {}
    tests = packet.get("tests") or {}
    verifier = packet.get("verifier") or {}
    escalation = packet.get("escalation_needed") or {}
    lines = [
        f"# Handoff - {record['task_id']}", "",
        "## Cosa è stato fatto",
        packet.get("decision") or "(nessuna decisione registrata - task non terminata)", "",
        "## Input usati / file letti", _bullets(packet.get("files_read")), "",
        "## File prodotti / modificati", _bullets(packet.get("files_changed")), "",
        "## Artifact creati", _bullets(packet.get("artifacts_created")), "",
        "## Test eseguiti",
        (f"ran={tests.get('ran')} passed={tests.get('passed')} failed={tests.get('failed')}"
         if tests else "(nessun test registrato)"), "",
        "## Verifier",
        (f"ran={verifier.get('ran')} passed={verifier.get('passed')}" if verifier else "(nessuna verifica registrata)"),
        _bullets(verifier.get("errors"), empty=""), "",
        "## Assunzioni e limiti dichiarati", _bullets(packet.get("limitations")), "",
        "## Cosa non è stato verificato", _bullets(packet.get("unresolved_issues")), "",
        "## Cosa deve controllare Claude/Codex in futuro", _bullets(packet.get("suggested_next_tasks")), "",
        "## Escalation",
        (f"necessaria={escalation.get('needed')} motivo={escalation.get('reason')} "
         f"tier={escalation.get('target_tier')}" if escalation else "(nessuna)"), "",
        f"_Generato da TaskQueue + RESULT_PACKET_V1 + Activity Ledger ({len(events)} eventi) - "
        f"nessun chain-of-thought salvato, solo azioni/output verificabili già registrati altrove._",
    ]
    return "\n".join(lines) + "\n"


def build_verifier_report_json(record: dict) -> dict:
    packet = record.get("result_packet") or {}
    return {"task_id": record["task_id"], "state": record.get("state"),
           "verifier": packet.get("verifier") or {}, "tests": packet.get("tests") or {}}


def write_task_artifacts(service, task_id: str, out_dir: Optional[Path] = None) -> Optional[dict]:
    """Returns {filename: path} on success, None if task_id is unknown.
    Idempotent and safe to call repeatedly (e.g. lazily, every time a user
    asks for task details) - always re-renders from current canonical
    state, never accumulates stale copies."""
    try:
        record = service.queue.get(task_id)
    except KeyError:
        return None
    events = service.ledger.read_for_task(task_id)
    out = Path(out_dir) if out_dir else task_artifacts_dir(service, task_id)
    out.mkdir(parents=True, exist_ok=True)

    (out / "task.md").write_text(render_task_md(record), encoding="utf-8")
    (out / "result.md").write_text(render_result_md(record), encoding="utf-8")
    (out / "handoff.md").write_text(render_handoff_md(record, events), encoding="utf-8")
    (out / "verifier_report.json").write_text(
        json.dumps(build_verifier_report_json(record), indent=2, ensure_ascii=False), encoding="utf-8")
    with open(out / "execution_log.jsonl", "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return {name: str(out / name) for name in ARTIFACT_FILENAMES}
