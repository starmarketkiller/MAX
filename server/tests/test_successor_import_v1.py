"""Successor import accepts only the task, attempt and SHA already measured."""
from datetime import datetime, timezone

import pytest

from jarvis_v1.successor_import import SuccessorRejected, import_successor_result
from orchestrator_v1.core.orchestrator import Orchestrator


def _manifest(task_id):
    return {
        "task_id": task_id, "title": "successor", "objective": "import",
        "task_type": "MAINTENANCE", "priority": "NORMAL", "risk_level": "A0",
        "scientific_risk": "NONE", "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": ["log_parsing"], "deterministic_tools_available": True,
        "repo_scope": "read-only", "files_allowed": [], "files_forbidden": ["MQL5/**"],
        "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
        "success_criteria": ["completed"], "verifier": "deterministic",
        "estimated_complexity": "TRIVIAL", "estimated_runtime": "1m",
        "premium_allowed": False, "preferred_executor": "TIER0_DETERMINISTIC",
        "fallback_executors": [], "approval_required": "AUTO", "created_by": "test",
        "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
        "account_scope_id": None,
    }


def _ready(tmp_path):
    orch = Orchestrator(queue_path=str(tmp_path / "queue.json"),
                        ledger_path=str(tmp_path / "ledger.jsonl"))
    orch.submit(_manifest("TASK_OK"), action="check_files_exist",
                action_params={"paths": ["contracts/task-manifest.schema.json"]})
    orch.queue.transition("TASK_OK", "RUNNING", executor="deterministic_worker")
    orch.queue.transition("TASK_OK", "COMPLETED", result_packet={"decision": "COMPLETED"})
    orch.queue.annotate("TASK_OK", routing_measurement={
        "task_id": "TASK_OK", "attempt": 1,
        "sha": "0b3f484471ffd6651233d07d3c6e74c3de665436",
    })
    return orch


def _payload(**updates):
    value = {
        "task_id": "TASK_OK", "attempt": 1,
        "sha": "0b3f484471ffd6651233d07d3c6e74c3de665436",
        "session": "cursor-agent:bc-a7226d88-8a47-4ddf-b756-2c4b521ab2b8",
        "outcome": "esito letto dall'handoff",
    }
    value.update(updates)
    return value


def test_matching_successor_is_stored_on_the_same_record(tmp_path):
    orch = _ready(tmp_path)
    record = import_successor_result(orch, _payload())
    assert record["successor_import"]["attempt"] == 1
    assert record["successor_import"]["sha"].startswith("0b3f484")
    assert record["successor_import"]["manual"] is True
    assert record["state"] == "COMPLETED"
    events = [event["event_type"] for event in orch.ledger.read_for_task("TASK_OK")]
    assert "SUCCESSOR_RESULT_IMPORTED" in events


@pytest.mark.parametrize("field,value", [
    ("task_id", "TASK_OTHER"),
    ("attempt", 2),
    ("sha", "ffffffffffffffffffffffffffffffffffffffff"),
])
def test_wrong_correlation_writes_nothing(tmp_path, field, value):
    orch = _ready(tmp_path)
    before = orch.queue.get("TASK_OK")
    with pytest.raises(SuccessorRejected) as caught:
        import_successor_result(orch, _payload(**{field: value}))
    assert caught.value.field == ("task" if field == "task_id" else field)
    assert orch.queue.get("TASK_OK") == before
    assert "SUCCESSOR_RESULT_IMPORTED" not in [
        event["event_type"] for event in orch.ledger.read_all()
    ]
