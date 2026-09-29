import os
import sys
from datetime import datetime, timezone

ORCH_DIR = os.path.join(os.path.dirname(__file__), "..", "orchestrator_v1")
sys.path.insert(0, os.path.abspath(ORCH_DIR))

from core.dispatcher import DurableQueueDispatcher  # noqa: E402
from core.orchestrator import Orchestrator  # noqa: E402


def manifest(task_id, **updates):
    value = {
        "task_id": task_id, "title": "dispatcher test", "objective": "test",
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
    value.update(updates)
    return value


def build(tmp_path):
    orch = Orchestrator(queue_path=str(tmp_path / "queue.json"),
                        ledger_path=str(tmp_path / "ledger.jsonl"))
    dispatcher = DurableQueueDispatcher(orch, poll_seconds=0.01, lease_seconds=30,
                                        shutdown_timeout_seconds=1)
    return orch, dispatcher


def submit_deterministic(orch, task_id, dependencies=None):
    orch.submit(manifest(task_id), dependencies=dependencies or [], action="check_files_exist",
                action_params={"paths": ["contracts/task-manifest.schema.json"]})


def test_dispatcher_consumes_queued_task_and_emits_lifecycle(tmp_path):
    orch, dispatcher = build(tmp_path)
    submit_deterministic(orch, "TASK_DISPATCH_1")
    assert dispatcher.run_once() is True
    record = orch.queue.get("TASK_DISPATCH_1")
    assert record["state"] == "COMPLETED"
    assert record["dispatch_claim"] is None
    events = [event["event_type"] for event in orch.ledger.read_for_task("TASK_DISPATCH_1")]
    assert "TASK_CLAIMED" in events
    assert "TASK_EXECUTION_STARTED" in events
    assert "TASK_STARTED" in events
    assert "TASK_CLAIM_RELEASED" in events


def test_claim_prevents_double_execution(tmp_path):
    orch, dispatcher = build(tmp_path)
    submit_deterministic(orch, "TASK_DISPATCH_ONCE")
    claimed = orch.queue.claim_next("other-dispatcher", lease_seconds=60)
    assert claimed["task_id"] == "TASK_DISPATCH_ONCE"
    assert orch.queue.claim_next(dispatcher.owner_id, lease_seconds=60) is None
    try:
        orch.process_task("TASK_DISPATCH_ONCE")
        assert False, "manual execution must not bypass an active claim"
    except AssertionError as exc:
        assert "claimed by another dispatcher" in str(exc)


def test_dependencies_promote_only_after_parent_completed(tmp_path):
    orch, dispatcher = build(tmp_path)
    submit_deterministic(orch, "TASK_PARENT")
    submit_deterministic(orch, "TASK_CHILD", dependencies=["TASK_PARENT"])
    assert orch.queue.get("TASK_CHILD")["state"] == "WAITING_DEPENDENCY"
    dispatcher.run_once()
    assert orch.queue.get("TASK_PARENT")["state"] == "COMPLETED"
    dispatcher.run_once()
    assert orch.queue.get("TASK_CHILD")["state"] == "COMPLETED"


def test_restart_blocks_orphaned_running_fail_closed(tmp_path):
    orch, dispatcher = build(tmp_path)
    submit_deterministic(orch, "TASK_ORPHAN")
    orch.queue.transition("TASK_ORPHAN", "RUNNING", executor="deterministic_worker")
    assert dispatcher.start() is True
    assert dispatcher.stop() is True
    record = orch.queue.get("TASK_ORPHAN")
    assert record["state"] == "BLOCKED"
    assert record["recovery"]["classification"] == "ORPHANED_RUNNING_AFTER_RESTART"
    assert any(event["event_type"] == "TASK_ORPHANED"
               for event in orch.ledger.read_for_task("TASK_ORPHAN"))


def test_dispatcher_does_not_bypass_router_or_premium_gate(tmp_path):
    orch, dispatcher = build(tmp_path)
    orch.submit(manifest("TASK_SCIENCE", scientific_risk="HIGH",
                         deterministic_tools_available=False,
                         preferred_executor="TIER1_LOCAL_CHEAP"),
                action="unknown_action", action_params={})
    dispatcher.run_once()
    record = orch.queue.get("TASK_SCIENCE")
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["escalation"]["target"] == "TIER3_CLAUDE"
    assert record["dispatch_claim"] is None


def test_pre_execution_failure_is_released_with_backoff(tmp_path):
    orch, dispatcher = build(tmp_path)
    submit_deterministic(orch, "TASK_RETRY")

    def fail_before_running(task_id, claim_token=None):
        raise OSError("temporary queue/runtime failure")

    orch.process_task = fail_before_running
    assert dispatcher.run_once() is True
    record = orch.queue.get("TASK_RETRY")
    assert record["state"] == "QUEUED"
    assert record["dispatch_claim"] is None
    assert record["dispatch_next_attempt_at"] is not None
    assert record["dispatch_last_error"] == "OSError"
    assert any(event["event_type"] == "TASK_DISPATCH_RETRY"
               for event in orch.ledger.read_for_task("TASK_RETRY"))


def test_exception_after_running_is_blocked_not_replayed(tmp_path):
    orch, dispatcher = build(tmp_path)
    submit_deterministic(orch, "TASK_AMBIGUOUS")
    original = orch.process_task

    def fail_after_running(task_id, claim_token=None):
        orch.queue.assert_claim(task_id, claim_token)
        orch.queue.transition(task_id, "RUNNING", executor="deterministic_worker")
        raise RuntimeError("process interrupted after execution started")

    orch.process_task = fail_after_running
    assert dispatcher.run_once() is True
    record = orch.queue.get("TASK_AMBIGUOUS")
    assert record["state"] == "BLOCKED"
    assert record["recovery"]["classification"] == "DISPATCH_EXECUTION_AMBIGUOUS"
    assert dispatcher.run_once() is False
    orch.process_task = original
