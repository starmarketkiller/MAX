"""Import one declared successor result onto the canonical task record.

The result is accepted only when task_id, attempt and sha match the
routing_measurement already stored on that record. A mismatch writes nothing.
This is not a second queue and it does not claim or dispatch the task.
"""
from __future__ import annotations

from .task_handoff import redact


class SuccessorRejected(ValueError):
    def __init__(self, field):
        super().__init__(field)
        self.field = field


def import_successor_result(orchestrator, payload):
    if not isinstance(payload, dict):
        raise SuccessorRejected("payload")
    task_id = payload.get("task_id")
    try:
        record = orchestrator.queue.get(task_id)
    except KeyError:
        raise SuccessorRejected("task") from None
    measurement = record.get("routing_measurement") or {}
    if measurement.get("task_id") != task_id:
        raise SuccessorRejected("task")
    if payload.get("attempt") != measurement.get("attempt"):
        raise SuccessorRejected("attempt")
    if payload.get("sha") != measurement.get("sha"):
        raise SuccessorRejected("sha")
    session = str(payload.get("session") or "").strip()
    if not session:
        raise SuccessorRejected("session")
    imported = {
        "task_id": task_id,
        "attempt": payload["attempt"],
        "sha": payload["sha"],
        "session": session,
        "manual": True,
        "outcome": redact(str(payload.get("outcome") or "")),
    }
    orchestrator.queue.annotate(task_id, successor_import=imported)
    orchestrator.ledger.append("SUCCESSOR_RESULT_IMPORTED", task_id, {
        "attempt": payload["attempt"], "sha": payload["sha"],
        "session": session, "manual": True,
    })
    return orchestrator.queue.get(task_id)
