"""SAFE_ORPHANED_TASK_RESUME_V1 - explicit, authenticated, auditable resume
of a task recover_orphaned_running() fail-closed parked into BLOCKED after a
process restart. Deliberately NOT an automatic resume at boot - every
precondition in Orchestrator.resume_orphaned_task() is exercised here in
isolation, plus the HTTP endpoint and the Telegram command, both of which
call that exact same method (no duplicated logic anywhere).
"""
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import app as backend
from jarvis_v1.free_coding_worker import FreeCodingWorkerHandler
from jarvis_v1.service import JarvisService, classify
from orchestrator_v1.core.local_agent_bridge import LocalAgentBridgeV1
from orchestrator_v1.core.orchestrator import Orchestrator


SECRET = "s" * 48


def manifest(task_id="TASK_ORPHAN", **changes):
    value = {
        "task_id": task_id, "title": "Orphan recovery patch", "objective": "Update src/sample.py",
        "task_type": "CODE", "work_type": "complex_code", "priority": "NORMAL",
        "risk_level": "A1", "scientific_risk": "NONE", "code_risk": "HIGH",
        "financial_risk": "NONE", "required_capabilities": ["small_python_functions",
                                                                  "unit_test_writing"],
        "deterministic_tools_available": False, "repo_scope": "task-scoped",
        "files_allowed": ["src/sample.py"], "files_forbidden": [".env", "MQL5/**"],
        "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
        "success_criteria": ["bounded patch verified"], "verifier": "free_coding_worker_v1",
        "estimated_complexity": "SMALL", "estimated_runtime": "5m", "premium_allowed": False,
        "preferred_executor": "TIER2_LOCAL_STRONG", "fallback_executors": ["TIER4_CODEX"],
        "approval_required": "REVIEW_REQUIRED", "created_by": "jarvis:99",
        "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
        "account_scope_id": None,
    }
    value.update(changes)
    return value


def build(tmp_path, *, with_bridge=True):
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "src" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    orch = Orchestrator(tmp_path / "queue.json", tmp_path / "ledger.jsonl")
    handler = FreeCodingWorkerHandler(project_root=project, workspace_root=tmp_path / "workspaces")
    orch.register_local_handler("conversational_programming", handler)
    bridge = None
    if with_bridge:
        bridge = LocalAgentBridgeV1(orch, state_path=tmp_path / "bridge.json", secret=SECRET)
        orch.set_local_bridge(bridge)
        bridge.heartbeat("pc-1", ["complex_code_change"])
    return orch, bridge


def submit_and_orphan(orch, value=None, *, cause="ORPHANED_RUNNING_AFTER_RESTART"):
    """Gets a task to RUNNING (the real precondition recover_orphaned_running()
    acts on) then either runs the REAL production recovery path, or - for the
    'wrong cause' regression test - a different BLOCKED cause entirely."""
    value = value or manifest()
    task_id = value["task_id"]
    orch.submit(value, action="conversational_programming", action_params={
        "execution_plan": {"intent": "PATCH"}, "test_commands": []})
    orch.queue.transition(task_id, "RUNNING", executor="TEST")
    if cause == "ORPHANED_RUNNING_AFTER_RESTART":
        orphaned = orch.queue.recover_orphaned_running("dispatcher:test")
        assert task_id in orphaned
        # recover_orphaned_running() itself only mutates queue state - the
        # Ledger entries are appended by DurableQueueDispatcher.start()
        # (dispatcher.py:54-59). Replayed here so the lifecycle this test
        # inspects matches what a real restart actually produces.
        orch.ledger.append("TASK_ORPHANED", task_id,
            {"classification": "ORPHANED_RUNNING_AFTER_RESTART", "action": "BLOCKED_FAIL_CLOSED"},
            actor="durable_queue_dispatcher_v1")
        orch.ledger.append("TASK_BLOCKED", task_id,
            {"reason": "orphaned RUNNING task after process restart; manual review required"},
            actor="durable_queue_dispatcher_v1")
    else:
        orch.queue.transition(task_id, "BLOCKED", dispatch_last_error=cause,
                              recovery={"classification": cause, "recovered_by": "test",
                                        "recovered_at": "2020-01-01T00:00:00+00:00"})
    return task_id


def test_orphaned_blocked_task_resumes_to_queued(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit_and_orphan(orch)
    before = orch.queue.get(task_id)
    assert before["state"] == "BLOCKED"

    record = orch.resume_orphaned_task(task_id, requested_by="test-user")
    assert record["state"] == "QUEUED"
    assert record["dispatch_last_error"] is None
    assert record["recovery"] is None

    events = [e["event_type"] for e in orch.ledger.read_for_task(task_id)]
    assert "TASK_RECOVERY_REQUESTED" in events and "TASK_RESUMED" in events
    # The Ledger is append-only - the original orphan cause is never erased,
    # only the record's live `recovery` field is cleared.
    assert "TASK_ORPHANED" in events and "TASK_BLOCKED" in events


def test_blocked_for_a_different_cause_is_refused(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit_and_orphan(orch, value=manifest(task_id="TASK_OTHER_CAUSE"),
                                cause="DISPATCH_EXECUTION_AMBIGUOUS")
    with pytest.raises(AssertionError, match="ORPHANED_RUNNING_AFTER_RESTART"):
        orch.resume_orphaned_task(task_id)
    assert orch.queue.get(task_id)["state"] == "BLOCKED"  # untouched


def test_task_not_blocked_is_refused(tmp_path):
    orch, bridge = build(tmp_path)
    value = manifest(task_id="TASK_NOT_BLOCKED")
    orch.submit(value, action="conversational_programming", action_params={
        "execution_plan": {"intent": "PATCH"}, "test_commands": []})
    with pytest.raises(AssertionError, match="requires BLOCKED"):
        orch.resume_orphaned_task(value["task_id"])


def test_active_dispatch_claim_is_refused(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit_and_orphan(orch, value=manifest(task_id="TASK_ACTIVE_CLAIM"))
    # Defensive edge case: recover_orphaned_running() always clears
    # dispatch_claim, but the guard must not trust that blindly.
    orch.queue.annotate(task_id, dispatch_claim={
        "owner_id": "dispatcher:other", "token": "tok", "claimed_at": "2020-01-01T00:00:00+00:00",
        "lease_expires_at": "2099-01-01T00:00:00+00:00"})
    with pytest.raises(AssertionError, match="active dispatch claim"):
        orch.resume_orphaned_task(task_id)
    assert orch.queue.get(task_id)["state"] == "BLOCKED"


def test_active_bridge_job_is_refused(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit_and_orphan(orch, value=manifest(task_id="TASK_ACTIVE_BRIDGE_JOB"))
    data = bridge._load()
    data["jobs"][task_id] = {
        "job_id": "lab_leased", "task_id": task_id, "status": "LEASED",
        "capability": bridge.CAPABILITY, "executor": "TIER2_LOCAL_STRONG", "model": "ministral3b",
        "prompt": "x", "task_record": {}, "attempts": 1,
        "lease": {"bridge_id": "pc-1", "token": "t", "expires_at": "2099-01-01T00:00:00+00:00"},
        "created_at": "2020-01-01T00:00:00+00:00", "updated_at": "2020-01-01T00:00:00+00:00",
        "result_id": None, "result_digest": None,
    }
    bridge._save(data)
    with pytest.raises(AssertionError, match="bridge job is still LEASED"):
        orch.resume_orphaned_task(task_id)
    assert orch.queue.get(task_id)["state"] == "BLOCKED"


def test_double_resume_never_double_dispatches(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit_and_orphan(orch, value=manifest(task_id="TASK_DOUBLE_RESUME"))
    first = orch.resume_orphaned_task(task_id)
    assert first["state"] == "QUEUED"
    # The second call finds state=QUEUED, not BLOCKED - fails closed, no
    # second QUEUED transition, no second dispatch.
    with pytest.raises(AssertionError, match="requires BLOCKED"):
        orch.resume_orphaned_task(task_id)
    assert orch.queue.get(task_id)["state"] == "QUEUED"
    resumed_events = [e for e in orch.ledger.read_for_task(task_id)
                      if e["event_type"] == "TASK_RESUMED"]
    assert len(resumed_events) == 1


def test_lineage_and_provenance_are_untouched(tmp_path):
    orch, bridge = build(tmp_path)
    value = manifest(task_id="TASK_LINEAGE", premium_allowed=True)
    task_id = value["task_id"]
    orch.submit(value, action="conversational_programming", action_params={
        "execution_plan": {"intent": "PATCH"}, "test_commands": []})
    # Give it real lineage before orphaning it: a proposed_patch and an
    # escalation record, exactly as a rejected-then-reworked task would have.
    orch.queue.annotate(task_id, proposed_patch={"changes": [{"path": "src/sample.py",
                        "content": "VALUE = 2\n"}], "test_results": []},
                        escalation={"target": "CLAUDE", "classification": "HUMAN_REJECTED_REWORK_REQUESTED",
                                   "candidates": ["GROQ", "CODEX", "CLAUDE"],
                                   "initial_candidates": ["CODEX", "CLAUDE"]})
    orch.queue.transition(task_id, "RUNNING", executor="TEST", retry_count=1)
    orch.queue.recover_orphaned_running("dispatcher:test")

    record = orch.resume_orphaned_task(task_id)
    assert record["proposed_patch"]["changes"][0]["content"] == "VALUE = 2\n"
    assert record["escalation"]["target"] == "CLAUDE"
    assert record["escalation"]["initial_candidates"] == ["CODEX", "CLAUDE"]
    assert record["retry_count"] == 1  # not reset - not part of this fix's scope


def test_e2e_resume_through_dispatcher_and_bridge_to_waiting_approval(tmp_path):
    """The exact production scenario: a task stuck RUNNING gets orphaned to
    BLOCKED by a restart, is explicitly resumed, and the normal dispatcher
    picks it up and routes it through the Local Agent Bridge to completion -
    resume_orphaned_task() never executes the handler itself."""
    from orchestrator_v1.core.dispatcher import DurableQueueDispatcher

    orch, bridge = build(tmp_path)
    task_id = submit_and_orphan(orch, value=manifest(task_id="TASK_E2E_RESUME", premium_allowed=True))
    assert orch.queue.get(task_id)["state"] == "BLOCKED"

    record = orch.resume_orphaned_task(task_id, requested_by="test-user")
    assert record["state"] == "QUEUED"

    dispatcher = DurableQueueDispatcher(orch, poll_seconds=0.01)
    worked = dispatcher.run_once()
    assert worked is True
    after = orch.queue.get(task_id)
    assert after["state"] == "WAITING_PROVIDER"  # dispatcher -> _run_local -> bridge.dispatch()

    claim = bridge.claim("pc-1", ["complex_code_change"])
    assert claim is not None and claim["task_id"] == task_id
    response = json.dumps({"summary": "bounded", "changes": [
        {"path": "src/sample.py", "content": "VALUE = 2\n"}]})
    verification = {"passed": True, "model": "ministral", "test_results": []}
    final = bridge.submit_result(task_id, "pc-1", claim["lease"]["token"], "result-1",
                                 response, verification)
    assert final["state"] == "WAITING_APPROVAL"
    assert final["proposed_patch"]["changes"][0]["content"] == "VALUE = 2\n"

    events = [e["event_type"] for e in orch.ledger.read_for_task(task_id)]
    assert events.index("TASK_RESUMED") < events.index("RESULT_DELIVERED")


def test_http_endpoint_requires_auth_and_maps_resume_outcomes(tmp_path, monkeypatch):
    orch, bridge = build(tmp_path)
    task_id = submit_and_orphan(orch, value=manifest(task_id="TASK_HTTP_RESUME"))
    service = JarvisService(queue_path=tmp_path / "unused_queue.json",
                            ledger_path=tmp_path / "unused_ledger.json")
    service.orchestrator = orch
    service.queue = orch.queue
    service.ledger = orch.ledger
    monkeypatch.setattr(backend, "JARVIS_SERVICE", service)
    client = TestClient(backend.app)

    # require_mutation is really wired in - an unauthenticated caller is
    # rejected before resume_orphaned_task() is ever reached.
    denied = client.post(f"/api/jarvis/tasks/{task_id}/resume-orphaned")
    assert denied.status_code in (401, 403)

    backend.app.dependency_overrides[backend.require_mutation] = lambda: "test-admin"
    try:
        ok = client.post(f"/api/jarvis/tasks/{task_id}/resume-orphaned")
        assert ok.status_code == 200
        assert ok.json()["state"] == "QUEUED"

        refused = client.post(f"/api/jarvis/tasks/{task_id}/resume-orphaned")
        assert refused.status_code == 409
        assert refused.json()["detail"]["code"] == "RESUME_REFUSED"

        missing = client.post("/api/jarvis/tasks/TASK_DOES_NOT_EXIST/resume-orphaned")
        assert missing.status_code == 404
    finally:
        backend.app.dependency_overrides.pop(backend.require_mutation, None)


def test_telegram_command_calls_the_same_recovery_service(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit_and_orphan(orch, value=manifest(task_id="TASK_TG_RESUME",
                                                      created_by="jarvis:77"))
    service = JarvisService(queue_path=tmp_path / "unused_queue.json",
                            ledger_path=tmp_path / "unused_ledger.json")
    service.orchestrator = orch
    service.queue = orch.queue
    service.ledger = orch.ledger

    message = {"message_id": "m1", "conversation_id": "conv-1", "user_id": 77,
              "channel": "telegram", "input_type": "TEXT", "priority": "NORMAL",
              "text": f"riprendi {task_id}", "metadata": {}}
    response = service.command(message)
    assert response["task_id"] == task_id
    assert response["status"] == "QUEUED"
    assert orch.queue.get(task_id)["state"] == "QUEUED"


def test_telegram_resume_on_wrong_state_reports_refusal_not_a_crash(tmp_path):
    orch, bridge = build(tmp_path)
    value = manifest(task_id="TASK_TG_REFUSED", created_by="jarvis:77")
    orch.submit(value, action="conversational_programming", action_params={
        "execution_plan": {"intent": "PATCH"}, "test_commands": []})
    service = JarvisService(queue_path=tmp_path / "unused_queue.json",
                            ledger_path=tmp_path / "unused_ledger.json")
    service.orchestrator = orch
    service.queue = orch.queue
    service.ledger = orch.ledger

    message = {"message_id": "m2", "conversation_id": "conv-2", "user_id": 77,
              "channel": "telegram", "input_type": "TEXT", "priority": "NORMAL",
              "text": f"riprendi {value['task_id']}", "metadata": {}}
    response = service.command(message)
    assert response["response_type"] == "ERROR"
    assert response["status"] == "REFUSED"


# --- RESUME_COMMAND_ROUTING_PRECEDENCE_FIX_V1 -------------------------------
# The real production bug: "riprendi TASK_4517052FD6EC" never reached
# command() at all - classify() routed it to TASK_REQUEST first (is_
# programming_request() already claims the bare word "riprendi" for a
# different, pre-existing meaning), so create_task() ran and made a brand
# new task (TASK_D47B5B49D79F) instead of resuming the referenced one. The
# tests above call service.command() directly, which exercises the handler
# but NOT the classify() gate that actually failed in production - these new
# ones go through service.handle(), the real top-level entry point, so this
# class of bug cannot hide again.

@pytest.mark.parametrize("verb", ["riprendi", "riattiva", "resume"])
def test_classify_explicit_resume_with_task_id_routes_to_command(verb):
    assert classify(f"{verb} TASK_4517052FD6EC") == "COMMAND"
    assert classify(f"{verb} la task TASK_4517052FD6EC per favore") == "COMMAND"
    assert classify(f"TASK_4517052FD6EC, {verb} questa") == "COMMAND"


def test_classify_bare_riprendi_without_task_id_is_unaffected():
    # No task_id present - must still fall through to the pre-existing
    # conversational-programming continuation path, unchanged.
    assert classify("riprendi il lavoro sul modulo di autenticazione") == "TASK_REQUEST"
    assert classify("riprendi pure quando vuoi") == "TASK_REQUEST"


@pytest.mark.parametrize("verb", ["riprendi", "riattiva", "resume"])
def test_handle_resume_with_task_id_does_not_create_a_new_task(tmp_path, verb):
    """The exact repro: 'riprendi TASK_4517052FD6EC' through the real
    top-level service.handle() entry point - the one classify() actually
    gates - must resume the SAME task_id and create nothing new."""
    orch, bridge = build(tmp_path)
    task_id = submit_and_orphan(orch, value=manifest(task_id="TASK_REAL_REPRO",
                                                      created_by="jarvis:77"))
    before_count = len(orch.queue.list_all())
    service = JarvisService(queue_path=tmp_path / "unused_queue.json",
                            ledger_path=tmp_path / "unused_ledger.json")
    service.orchestrator = orch
    service.queue = orch.queue
    service.ledger = orch.ledger

    message = {"message_id": "m3", "conversation_id": "conv-3", "user_id": 77,
              "channel": "telegram", "input_type": "TEXT", "priority": "NORMAL",
              "text": f"{verb} {task_id}", "metadata": {}}
    response = service.handle(message)

    assert response["task_id"] == task_id  # the SAME task_id, never a new one
    assert response["status"] == "QUEUED"
    assert orch.queue.get(task_id)["state"] == "QUEUED"
    assert len(orch.queue.list_all()) == before_count  # no new task created


def test_handle_bare_riprendi_without_task_id_still_creates_a_task(tmp_path):
    """Regression guard: the pre-existing conversational-programming
    continuation behaviour (bare 'riprendi', no explicit task_id) must be
    completely unaffected by this fix."""
    orch, bridge = build(tmp_path, with_bridge=False)
    service = JarvisService(queue_path=tmp_path / "unused_queue.json",
                            ledger_path=tmp_path / "unused_ledger.json")
    service.orchestrator = orch
    service.queue = orch.queue
    service.ledger = orch.ledger

    before_count = len(orch.queue.list_all())
    message = {"message_id": "m4", "conversation_id": "conv-4", "user_id": 77,
              "channel": "telegram", "input_type": "TEXT", "priority": "NORMAL",
              "text": "riprendi il lavoro sul modulo di autenticazione", "metadata": {}}
    response = service.handle(message)

    assert response["response_type"] == "TASK_ACK"
    assert len(orch.queue.list_all()) == before_count + 1  # a new task IS created, as before
