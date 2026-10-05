"""Read-only projection of Ledger events into per-task delegation outcomes
for MINISTRAL_TASK_COMPILER_V1 templates.

No new write path: every field here is derived from events
core/orchestrator.py already appends (TASK_CREATED, TASK_STARTED,
TOOL_USED, TEST_PASSED/TEST_FAILED, RETRY_STARTED, TASK_COMPLETED,
TASK_FAILED, ESCALATION_REQUIRED). Used to answer, empirically, which
templates Ministral handles well enough to eventually promote to a
reusable skill - never used to drive routing itself (that stays
core/router.py's job, untouched).
"""
from __future__ import annotations

from . import ministral_task_compiler as compiler


def _first(events, event_type):
    return next((e for e in events if e["event_type"] == event_type), None)


def _last(events, event_type):
    matches = [e for e in events if e["event_type"] == event_type]
    return matches[-1] if matches else None


def delegation_outcome_for_task(task_id, events, record):
    """events: this task's own Ledger events, in append order. record: the
    current TaskQueue record. Returns None if this task was never created
    through a MINISTRAL_TASK_COMPILER_V1 template (action not in TEMPLATES)."""
    action = record.get("action")
    if action not in compiler.TEMPLATES:
        return None
    manifest = record.get("manifest") or {}
    started = _first(events, "TASK_STARTED")
    tool_used = _last(events, "TOOL_USED")
    completed = _first(events, "TASK_COMPLETED")
    failed = _first(events, "TASK_FAILED")
    escalation = _first(events, "ESCALATION_REQUIRED")
    retry_count = sum(1 for e in events if e["event_type"] == "RETRY_STARTED")
    verifier_result = None
    if _first(events, "TEST_PASSED"):
        verifier_result = "PASSED"
    elif _first(events, "TEST_FAILED"):
        verifier_result = "FAILED"
    latency_s = None
    if tool_used:
        latency_s = tool_used["payload"].get("wall_seconds")
    return {
        "task_id": task_id,
        "template_id": action,
        "task_type": manifest.get("task_type"),
        "work_type": manifest.get("work_type"),
        "model": tool_used["payload"].get("model") if tool_used else None,
        "executor": started["payload"].get("executor") if started else None,
        "latency_s": latency_s,
        "verifier_result": verifier_result,
        "retry_count": retry_count,
        "final_outcome": record.get("state"),
        "escalation_reason": escalation["payload"].get("classification") if escalation else (
            failed["payload"].get("reason") if failed else None),
    }


def read_bounded_output(task_id, queue):
    """PERSIST_MINISTRAL_BOUNDED_OUTPUT_V1 consumer: the one place Jarvis/
    reporting should call to recover what a MINISTRAL_TASK_COMPILER_V1
    delegation actually produced. Combines the decoded artifacts_created
    payload (template_id, task_id, summary, findings, risks) with the
    executor/verifier status already on RESULT_PACKET_V1's top level - no
    second read path, no new storage. Returns None if this task never
    completed with a bounded output (wrong template, still running, or the
    verifier rejected every attempt - a rejected attempt is never passed to
    apply(), so it can never appear here)."""
    record = queue.get(task_id)
    packet = record.get("result_packet") or {}
    decoded = compiler.decode_bounded_output(packet.get("artifacts_created"))
    if decoded is None:
        return None
    return {**decoded, "executor": packet.get("executor"),
           "verifier_passed": (packet.get("verifier") or {}).get("passed")}


def delegation_outcomes_report(ledger, queue, *, template_id=None):
    """Full report across every task ever created through a compiler
    template. Pass template_id to filter to one template."""
    events_by_task: dict[str, list] = {}
    for event in ledger.read_all():
        task_id = event.get("task_id")
        if task_id:
            events_by_task.setdefault(task_id, []).append(event)

    rows = []
    for task_id, events in events_by_task.items():
        try:
            record = queue.get(task_id)
        except KeyError:
            continue
        row = delegation_outcome_for_task(task_id, events, record)
        if row is None:
            continue
        if template_id and row["template_id"] != template_id:
            continue
        rows.append(row)
    return rows
