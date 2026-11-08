"""Continuation from a verified coding proposal to an exact-byte apply.

WAITING_APPROVAL before a bound approval is the expected state.
The continuation does not call a model and does not requeue other task types.
"""
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from executive_v1.priority import InteractiveGate
from jarvis_v1.free_coding_worker import (
    BINDING_SCHEMA, NEWLINE_POLICY, FreeCodingWorkerHandler, baseline_digest, binding_digest,
    file_digest, proposal_digest)
from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService
from orchestrator_v1.core.dispatcher import DurableQueueDispatcher
from orchestrator_v1.core.orchestrator import Orchestrator
from orchestrator_v1.core.result_packet import build_result_packet

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "approval_continuation_a2"
SOURCE = "protocol_a_fixture/sample_counter.py"
TEST = "server/tests/test_sample_counter.py"
FIXED = (
    "def next_value(current):\n"
    "    \"\"\"Return the integer that follows current.\"\"\"\n"
    "    return current + 1"
)


def _manifest(task_id):
    return {
        "task_id": task_id, "title": "apply verified counter", "objective": "next_value",
        "task_type": "CODE", "priority": "NORMAL", "risk_level": "A0",
        "scientific_risk": "NONE", "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": ["small_python_functions"],
        "deterministic_tools_available": False, "repo_scope": "isolated",
        "files_allowed": [SOURCE], "files_forbidden": ["MQL5/**"],
        "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
        "success_criteria": ["applied bytes"], "verifier": "free_coding_worker_v1",
        "estimated_complexity": "TRIVIAL", "estimated_runtime": "1m",
        "premium_allowed": False, "preferred_executor": "TIER1_LOCAL_CHEAP",
        "fallback_executors": [], "approval_required": "REVIEW_REQUIRED",
        "created_by": "jarvis:42", "created_at": "2026-11-08T17:00:00Z",
        "tenant_id": "tenant-1", "account_scope_id": None,
    }


def _packet(task_id):
    now = datetime.now(timezone.utc).isoformat()
    return build_result_packet(
        task_id=task_id, executor="LOCAL_STRONG_MINISTRAL3B", start_time=now, end_time=now,
        files_read=[], files_changed=[], tools_or_commands=["ollama:qwen2.5:3b-instruct"],
        artifacts_created=[], tests_ran=True, tests_passed=1, tests_failed=0,
        verifier_ran=True, verifier_passed=True, verifier_errors=[], commit=None,
        push_status="NOT_APPLICABLE", decision="PATCH_READY_AWAITING_APPROVAL",
        confidence="MEDIUM", limitations=["sandbox only"], unresolved_issues=[],
        suggested_next_tasks=[], escalation_needed=False)


def _service(tmp_path, monkeypatch):
    def _forbidden(*_args, **_kwargs):
        raise AssertionError("model call is not part of continuation")

    monkeypatch.setattr("core.orchestrator.ollama_worker.call_local_model", _forbidden)
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    project = tmp_path / "project"
    shutil.copytree(FIXTURE, project)
    service = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"),
                            str(tmp_path / "conversation.json"))
    handler = FreeCodingWorkerHandler(
        project_root=project, workspace_root=tmp_path / "workspaces")
    service.orchestrator.register_local_handler("conversational_programming", handler)
    return service, handler, project


def _patch(content, source_bytes, *, attempt=0):
    changes = [{"path": SOURCE, "content": content}]
    baselines = {SOURCE: file_digest(source_bytes)}
    return {
        "changes": changes,
        "test_results": [{"argv": ["PYTHON", "-m", "pytest", TEST, "-q"], "returncode": 0,
                          "stdout": "2 passed", "stderr": ""}],
        "baselines": baselines,
        "attempt": attempt,
        "newline_policy": NEWLINE_POLICY,
        "proposal_sha256": proposal_digest(changes),
        "baseline_sha256": baseline_digest(baselines),
        "binding_schema": BINDING_SCHEMA,
        "binding_sha256": binding_digest(changes),
    }


def _plant(service, task_id, patch):
    service.orchestrator.submit(
        _manifest(task_id), action="conversational_programming",
        action_params={"test_commands": [["PYTHON", "-m", "pytest", TEST, "-q"]]})
    service.queue.transition(
        task_id, "WAITING_APPROVAL", result_packet=_packet(task_id),
        proposed_patch=patch, approval_effect="REQUEUE")
    return service.queue.get(task_id)


def _message(task_id, patch, **extra):
    metadata = {
        "task_id": task_id, "approval_action": "APPROVE",
        "attempt": patch["attempt"], "proposal_sha256": patch["proposal_sha256"],
        "baseline_sha256": patch["baseline_sha256"],
        "binding_schema": patch["binding_schema"], "binding_sha256": patch["binding_sha256"],
    }
    metadata.update(extra)
    return {
        "message_id": f"m-{task_id}-{metadata.get('attempt')}", "user_id": "42",
        "channel": "TEST", "conversation_id": "c-approval",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_type": "TEXT", "text": "APPROVE", "attachments": [], "reply_to": None,
        "request_class": "APPROVAL", "priority": "HIGH", "metadata": metadata,
    }


def _approve(service, task_id, patch, **extra):
    return JarvisGateway(service).handle(_message(task_id, patch, **extra))


def _events(service, task_id, event_type):
    return [event for event in service.ledger.read_for_task(task_id)
            if event["event_type"] == event_type]


def test_newline_policy_is_exact_bytes():
    assert NEWLINE_POLICY == "preserve_proposal_bytes"
    content = "a\nb\n"
    assert file_digest(content.encode("utf-8")) != file_digest(content.replace("\n", "\r\n").encode("utf-8"))


def test_without_approval_project_is_unchanged(tmp_path, monkeypatch):
    service, handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    record = _plant(service, "TASK_WAIT", patch)
    verified = handler.verify(record, (
        '{"summary":"fix","changes":[{"path":"%s","content":%s}]}' % (SOURCE, __import__("json").dumps(FIXED))))
    assert verified.passed
    assert (project / SOURCE).read_bytes() == before
    assert service.queue.get("TASK_WAIT")["state"] == "WAITING_APPROVAL"


def test_unbound_or_mismatched_approval_does_not_write(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_BIND", patch)
    missing = _message("TASK_BIND", patch)
    missing["metadata"].pop("proposal_sha256")
    refused = JarvisGateway(service).handle(missing)
    wrong_proposal = _approve(service, "TASK_BIND", patch, proposal_sha256="0" * 64)
    wrong_attempt = _approve(service, "TASK_BIND", patch, attempt=9)
    wrong_baseline = _approve(service, "TASK_BIND", patch, baseline_sha256="1" * 64)
    assert service.queue.get("TASK_BIND")["state"] == "WAITING_APPROVAL"
    assert (project / SOURCE).read_bytes() == before
    assert refused["status"] != "COMPLETED"
    assert wrong_proposal["status"] != "COMPLETED"
    assert wrong_attempt["status"] != "COMPLETED"
    assert wrong_baseline["status"] != "COMPLETED"
    assert _events(service, "TASK_BIND", "FILE_CHANGED") == []


def test_changed_baseline_is_rejected_before_write(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_DRIFT", patch)
    drifted = before + b"\n# drifted\n"
    (project / SOURCE).write_bytes(drifted)
    response = _approve(service, "TASK_DRIFT", patch)
    assert response["status"] != "COMPLETED"
    assert (project / SOURCE).read_bytes() == drifted
    assert service.queue.get("TASK_DRIFT")["state"] == "WAITING_APPROVAL"


def test_disallowed_path_is_rejected_before_write(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    patch["changes"] = [{"path": "../outside.py", "content": "x = 1\n"}]
    patch["proposal_sha256"] = proposal_digest(patch["changes"])
    _plant(service, "TASK_PATH", patch)
    response = _approve(service, "TASK_PATH", patch)
    assert response["status"] != "COMPLETED"
    assert not (project.parent / "outside.py").exists()
    assert (project / SOURCE).read_bytes() == before


def test_approved_proposal_is_applied_without_a_model_call(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_APPLY", patch)
    response = _approve(service, "TASK_APPLY", patch)
    record = service.queue.get("TASK_APPLY")
    applied = (project / SOURCE).read_bytes()
    receipt = record["application_receipt"]
    assert response["status"] == "COMPLETED"
    assert record["state"] == "COMPLETED"
    assert record["result_packet"]["decision"] == "COMPLETED"
    assert record["result_packet"]["verifier"]["passed"] is True
    assert applied == FIXED.encode("utf-8")
    assert b"\r\n" not in applied
    assert receipt["newline_policy"] == NEWLINE_POLICY
    assert receipt["proposal_sha256"] == patch["proposal_sha256"]
    assert receipt["applied_sha256"] == file_digest(applied)
    assert receipt["proposal_sha256"] == receipt["applied_sha256"]
    assert receipt["binding_schema"] == BINDING_SCHEMA
    assert receipt["binding_sha256"] == binding_digest(patch["changes"])
    assert receipt["applied_binding_sha256"] == receipt["binding_sha256"]
    assert receipt["baseline_sha256"] == patch["baseline_sha256"]
    assert receipt["attempt"] == 0
    assert receipt["proposal_sha256"] != file_digest(before)
    assert _events(service, "TASK_APPLY", "TASK_COMPLETED")


def test_repeat_and_late_approval_have_no_second_effect(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_ONCE", patch)
    assert _approve(service, "TASK_ONCE", patch)["status"] == "COMPLETED"
    applied = (project / SOURCE).read_bytes()
    changes = len(_events(service, "TASK_ONCE", "FILE_CHANGED"))
    again = _approve(service, "TASK_ONCE", patch)
    late = _approve(service, "TASK_ONCE", patch, expected_state="WAITING_APPROVAL")
    assert again["status"] == "COMPLETED"
    assert late["response_type"] == "ERROR"
    assert (project / SOURCE).read_bytes() == applied
    assert len(_events(service, "TASK_ONCE", "FILE_CHANGED")) == changes
    assert service.queue.get("TASK_ONCE")["state"] == "COMPLETED"


def test_failed_verification_does_not_complete(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    unchanged = before.decode("utf-8").replace("\r\n", "\n")
    patch = _patch(unchanged, before)
    _plant(service, "TASK_RED", patch)
    response = _approve(service, "TASK_RED", patch)
    record = service.queue.get("TASK_RED")
    assert response["status"] == "FAILED"
    assert record["state"] == "FAILED"
    assert record["result_packet"]["decision"] != "COMPLETED"
    assert "application_receipt" not in record
    assert (project / SOURCE).read_bytes() == before


def test_unbound_coding_proposal_keeps_requeue_and_does_not_write(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    _plant(service, "TASK_LEGACY", {"changes": [{"path": SOURCE, "content": FIXED}],
                                    "test_results": []})
    response = JarvisGateway(service).handle({
        "message_id": "m-legacy", "user_id": "42", "channel": "TEST",
        "conversation_id": "c-approval", "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_type": "TEXT", "text": "APPROVE", "attachments": [], "reply_to": None,
        "request_class": "APPROVAL", "priority": "HIGH",
        "metadata": {"task_id": "TASK_LEGACY", "approval_action": "APPROVE"},
    })
    assert response["status"] == "QUEUED"
    assert (project / SOURCE).read_bytes() == before
    assert service.queue.get("TASK_LEGACY")["state"] == "QUEUED"


def test_queued_grant_applies_the_stored_proposal(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_RESUME", patch)
    service.queue.annotate("TASK_RESUME", approval_grant={
        "task_id": "TASK_RESUME", "attempt": patch["attempt"],
        "proposal_sha256": patch["proposal_sha256"],
        "baseline_sha256": patch["baseline_sha256"],
        "binding_schema": patch["binding_schema"],
        "binding_sha256": patch["binding_sha256"],
    })
    service.queue.transition("TASK_RESUME", "QUEUED")
    updated = service.orchestrator.process_task("TASK_RESUME")
    assert updated["state"] == "COMPLETED"
    assert (project / SOURCE).read_bytes() == FIXED.encode("utf-8")


def test_interactive_yield_still_blocks_background_claim(tmp_path):
    gate = InteractiveGate()
    orch = Orchestrator(queue_path=str(tmp_path / "q.json"), ledger_path=str(tmp_path / "l.jsonl"))
    claimed = []
    orch.queue.claim_next = lambda *_args, **_kwargs: claimed.append(1)
    dispatcher = DurableQueueDispatcher(orch, yield_predicate=gate.background_should_yield)
    with gate.interactive():
        assert dispatcher.run_once() is False and claimed == []
    dispatcher.run_once()
    assert claimed == [1]
