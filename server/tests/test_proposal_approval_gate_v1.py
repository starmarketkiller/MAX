"""ACCEPT_ONLY proposals stop at WAITING_APPROVAL and never re-enter the queue."""
import os
import sys
import threading
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "orchestrator_v1")))

from core.dispatcher import DurableQueueDispatcher  # noqa: E402
from core.orchestrator import ApplyResult, LocalTaskHandler, Orchestrator, VerifyResult  # noqa: E402
from jarvis_v1.gateway import JarvisGateway  # noqa: E402
from jarvis_v1.service import JarvisService  # noqa: E402


def _manifest(task_id, **overrides):
    manifest = {
        "task_id": task_id, "title": "t", "objective": "o", "task_type": "CODE",
        "priority": "NORMAL", "risk_level": "A0", "scientific_risk": "NONE", "code_risk": "NONE",
        "financial_risk": "NONE", "required_capabilities": ["small_python_functions"],
        "deterministic_tools_available": False, "repo_scope": "server/",
        "files_allowed": [], "files_forbidden": ["MQL5/*"], "dependencies": [],
        "blockers": [], "expected_artifacts": [], "success_criteria": ["ok"],
        "verifier": "v.py", "estimated_complexity": "TRIVIAL", "estimated_runtime": "1m",
        "premium_allowed": False, "preferred_executor": "TIER1_LOCAL_CHEAP",
        "fallback_executors": [], "approval_required": "REVIEW_REQUIRED", "created_by": "test",
        "created_at": "2026-10-09T00:00:00Z", "tenant_id": "tenant-1", "account_scope_id": None,
    }
    manifest.update(overrides)
    return manifest


class _Handler(LocalTaskHandler):
    def __init__(self, *, proposal_only, touches):
        self.proposal_only = proposal_only
        self.touches = touches

    def build_prompt(self, task_record):
        return "local-test"

    def verify(self, task_record, response_text):
        return VerifyResult(passed=True, parsed_output={"summary": "internal"})

    def apply(self, task_record, verify_result):
        return ApplyResult(artifacts_created=["artifact:internal"],
                           touches_real_repo_files=self.touches,
                           proposal_only=self.proposal_only)


def _service(tmp_path, monkeypatch):
    calls = {"n": 0}

    def _fake(prompt, model):
        calls["n"] += 1
        return {"success": True, "model": model, "response_text": '{"ok": true}',
                "wall_seconds": 0.0, "error": None}

    monkeypatch.setattr("core.orchestrator.ollama_worker.call_local_model", _fake)
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    service = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"))
    return service, calls


def _message(text, cls="APPROVAL", task_id=None, action=None, expected_state=None):
    metadata = {"task_id": task_id, "approval_action": action or text}
    if expected_state:
        metadata["expected_state"] = expected_state
    return {"message_id": f"m-{text}-{task_id}", "user_id": "42", "channel": "TEST",
            "conversation_id": "c-approval", "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_type": "TEXT", "text": text, "attachments": [], "reply_to": None,
            "request_class": cls, "priority": "HIGH", "metadata": metadata}


def _run(service, task_id, *, proposal_only, touches):
    service.orchestrator.register_local_handler(
        "proposal_gate", _Handler(proposal_only=proposal_only, touches=touches))
    service.orchestrator.submit(_manifest(task_id), action="proposal_gate")
    return service.orchestrator.process_task(task_id)


def _granted(service, task_id):
    return [event for event in service.ledger.read_for_task(task_id)
            if event["event_type"] == "APPROVAL_GRANTED"]


def test_accept_only_persists_packet_and_does_not_complete(tmp_path, monkeypatch):
    service, calls = _service(tmp_path, monkeypatch)
    record = _run(service, "TASK_ACCEPT_ONLY", proposal_only=True, touches=False)
    assert record["state"] == "WAITING_APPROVAL"
    assert record["approval_effect"] == "ACCEPT_ONLY"
    assert record["result_packet"]["decision"] == "PROPOSAL_AWAITING_APPROVAL"
    assert record["result_packet"]["artifacts_created"] == ["artifact:internal"]
    assert calls["n"] == 1
    assert not any(event["event_type"] == "TASK_COMPLETED"
                   for event in service.ledger.read_for_task("TASK_ACCEPT_ONLY"))


def test_proposal_only_false_still_completes(tmp_path, monkeypatch):
    service, _calls = _service(tmp_path, monkeypatch)
    record = _run(service, "TASK_NORMAL", proposal_only=False, touches=False)
    assert record["state"] == "COMPLETED"
    assert "approval_effect" not in record
    assert any(event["event_type"] == "TASK_COMPLETED"
               for event in service.ledger.read_for_task("TASK_NORMAL"))


def test_file_proposal_keeps_requeue_effect(tmp_path, monkeypatch):
    service, calls = _service(tmp_path, monkeypatch)
    record = _run(service, "TASK_REQUEUE", proposal_only=True, touches=True)
    assert record["state"] == "WAITING_APPROVAL"
    assert record["approval_effect"] == "REQUEUE"
    assert record["result_packet"]["decision"] == "PATCH_READY_AWAITING_APPROVAL"
    approved = JarvisGateway(service).handle(_message("APPROVE", task_id="TASK_REQUEUE", action="APPROVE"))
    assert approved["status"] == "QUEUED"
    assert calls["n"] == 1
    assert service.queue.claim_next("worker-1")["task_id"] == "TASK_REQUEUE"


def test_accept_only_approve_and_reject_do_not_reexecute(tmp_path, monkeypatch):
    service, calls = _service(tmp_path, monkeypatch)
    _run(service, "TASK_YES", proposal_only=True, touches=False)
    _run(service, "TASK_NO", proposal_only=True, touches=False)
    approved = JarvisGateway(service).handle(_message("APPROVE", task_id="TASK_YES", action="APPROVE"))
    rejected = JarvisGateway(service).handle(_message("REJECT", task_id="TASK_NO", action="REJECT"))
    assert approved["status"] == "PROPOSAL_ACCEPTED"
    assert rejected["status"] == "PROPOSAL_REJECTED"
    assert service.queue.get("TASK_YES")["state"] == "PROPOSAL_ACCEPTED"
    assert service.queue.get("TASK_NO")["state"] == "PROPOSAL_REJECTED"
    assert calls["n"] == 2
    assert service.queue.claim_next("worker-1") is None
    with pytest.raises(AssertionError):
        service.orchestrator.process_task("TASK_YES")
    dispatcher = DurableQueueDispatcher(service.orchestrator, poll_seconds=0.05, lease_seconds=30)
    assert dispatcher.run_once() is False


def test_repeated_and_concurrent_approve_is_idempotent(tmp_path, monkeypatch):
    service, _calls = _service(tmp_path, monkeypatch)
    _run(service, "TASK_ONCE", proposal_only=True, touches=False)
    gateway = JarvisGateway(service)
    assert gateway.handle(_message("APPROVE", task_id="TASK_ONCE", action="APPROVE"))["status"] == "PROPOSAL_ACCEPTED"
    again = gateway.handle(_message("APPROVE-2", task_id="TASK_ONCE", action="APPROVE"))
    assert again["status"] == "PROPOSAL_ACCEPTED"
    assert len(_granted(service, "TASK_ONCE")) == 1

    service_b, _ignored = _service(tmp_path / "race", monkeypatch)
    _run(service_b, "TASK_RACE", proposal_only=True, touches=False)
    barrier = threading.Barrier(2)
    outcomes = []

    def _approve():
        barrier.wait()
        outcomes.append(JarvisGateway(service_b).handle(
            _message("APPROVE", task_id="TASK_RACE", action="APPROVE"))["status"])

    threads = [threading.Thread(target=_approve) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes == ["PROPOSAL_ACCEPTED", "PROPOSAL_ACCEPTED"]
    assert service_b.queue.get("TASK_RACE")["state"] == "PROPOSAL_ACCEPTED"
    assert len(_granted(service_b, "TASK_RACE")) == 1
    assert service_b.queue.claim_next("worker-race") is None


def _of_type(service, task_id, event_type):
    return [event for event in service.ledger.read_for_task(task_id)
            if event["event_type"] == event_type]


def test_telegram_card_repeat_returns_the_stored_decision(tmp_path, monkeypatch):
    service, calls = _service(tmp_path, monkeypatch)
    _run(service, "TASK_CARD", proposal_only=True, touches=False)
    gateway = JarvisGateway(service)
    card = {"expected_state": "WAITING_APPROVAL"}
    first = gateway.handle(_message("APPROVE", task_id="TASK_CARD", action="APPROVE", **card))
    assert first["response_type"] == "APPROVAL"
    assert first["status"] == "PROPOSAL_ACCEPTED"
    assert len(_granted(service, "TASK_CARD")) == 1
    model_calls = calls["n"]

    second = gateway.handle(_message("APPROVE-2", task_id="TASK_CARD", action="APPROVE", **card))
    assert second["response_type"] == "APPROVAL"
    assert second["status"] == "PROPOSAL_ACCEPTED"
    assert len(_granted(service, "TASK_CARD")) == 1

    opposite = gateway.handle(_message("REJECT", task_id="TASK_CARD", action="REJECT", **card))
    assert opposite["response_type"] == "ERROR"
    assert service.queue.get("TASK_CARD")["state"] == "PROPOSAL_ACCEPTED"
    assert _of_type(service, "TASK_CARD", "APPROVAL_REJECTED") == []
    assert calls["n"] == model_calls
    assert service.queue.claim_next("card-worker") is None

    _run(service, "TASK_CARD_NO", proposal_only=True, touches=False)
    rejected = gateway.handle(_message("REJECT", task_id="TASK_CARD_NO", action="REJECT", **card))
    assert rejected["status"] == "PROPOSAL_REJECTED"
    assert len(_of_type(service, "TASK_CARD_NO", "APPROVAL_REJECTED")) == 1
    again = gateway.handle(_message("REJECT-2", task_id="TASK_CARD_NO", action="REJECT", **card))
    assert again["response_type"] == "APPROVAL"
    assert again["status"] == "PROPOSAL_REJECTED"
    assert len(_of_type(service, "TASK_CARD_NO", "APPROVAL_REJECTED")) == 1
    flipped = gateway.handle(_message("APPROVE", task_id="TASK_CARD_NO", action="APPROVE", **card))
    assert flipped["response_type"] == "ERROR"
    assert service.queue.get("TASK_CARD_NO")["state"] == "PROPOSAL_REJECTED"
    assert _granted(service, "TASK_CARD_NO") == []


def test_legacy_waiting_task_without_effect_still_requeues(tmp_path, monkeypatch):
    service, calls = _service(tmp_path, monkeypatch)
    created = JarvisGateway(service).handle({
        "message_id": "m-create", "user_id": "42", "channel": "TEST", "conversation_id": "c1",
        "timestamp": datetime.now(timezone.utc).isoformat(), "input_type": "TEXT",
        "text": "Crea una NEXUS TASK per analizzare un archivio.", "attachments": [],
        "reply_to": None, "request_class": "UNKNOWN", "priority": "NORMAL", "metadata": {},
    })
    task_id = created["task_id"]
    service.queue.transition(task_id, "RUNNING")
    service.queue.transition(task_id, "WAITING_APPROVAL")
    assert "approval_effect" not in service.queue.get(task_id)
    approved = JarvisGateway(service).handle(_message("APPROVE", task_id=task_id, action="APPROVE"))
    assert approved["status"] == "QUEUED"
    assert calls["n"] == 0


def test_orphaned_accept_only_with_packet_is_not_requeued(tmp_path, monkeypatch):
    service, _calls = _service(tmp_path, monkeypatch)
    service.orchestrator.submit(_manifest("TASK_CRASH"), action="proposal_gate")
    service.queue.transition("TASK_CRASH", "RUNNING")
    service.queue.annotate(
        "TASK_CRASH", approval_effect="ACCEPT_ONLY",
        result_packet={"decision": "PROPOSAL_AWAITING_APPROVAL", "artifacts_created": ["artifact:internal"]})
    assert service.queue.recover_orphaned_running("dispatcher-test") == ["TASK_CRASH"]
    restored = service.orchestrator.resume_orphaned_task("TASK_CRASH", requested_by="tester")
    assert restored["state"] == "WAITING_APPROVAL"
    assert service.queue.claim_next("worker-1") is None

    service.orchestrator.submit(_manifest("TASK_OLD_CRASH", task_type="MAINTENANCE",
                                          required_capabilities=["log_parsing"],
                                          deterministic_tools_available=True,
                                          preferred_executor="TIER0_DETERMINISTIC",
                                          approval_required="AUTO"),
                                action="check_files_exist",
                                action_params={"paths": ["contracts/task-manifest.schema.json"]})
    service.queue.transition("TASK_OLD_CRASH", "RUNNING")
    assert service.queue.recover_orphaned_running("dispatcher-test") == ["TASK_OLD_CRASH"]
    legacy = service.orchestrator.resume_orphaned_task("TASK_OLD_CRASH", requested_by="tester")
    assert legacy["state"] == "QUEUED"
    claimed = service.queue.claim_next("worker-2")
    assert claimed["task_id"] == "TASK_OLD_CRASH"
    service.queue.release_claim("TASK_OLD_CRASH", claimed["dispatch_claim"]["token"])
