import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as backend
from jarvis_v1.free_coding_worker import FreeCodingWorkerHandler
from orchestrator_v1.core.local_agent_bridge import LocalAgentBridgeV1
from orchestrator_v1.core.orchestrator import Orchestrator
from orchestrator_v1.core.provider_connector import MockProviderAdapter, ProviderConnectorV1
from orchestrator_v1.core.router import route


SECRET = "s" * 48


def manifest(task_id="TASK_BRIDGE", **changes):
    value = {
        "task_id": task_id, "title": "Bridge bounded patch", "objective": "Update src/sample.py",
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
        "approval_required": "REVIEW_REQUIRED", "created_by": "test",
        "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
        "account_scope_id": None,
    }
    value.update(changes)
    return value


def build(tmp_path, *, secret=SECRET, heartbeat=True):
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "src" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    orch = Orchestrator(tmp_path / "queue.json", tmp_path / "ledger.jsonl")
    handler = FreeCodingWorkerHandler(project_root=project, workspace_root=tmp_path / "workspaces")
    orch.register_local_handler("conversational_programming", handler)
    bridge = LocalAgentBridgeV1(orch, state_path=tmp_path / "bridge.json", secret=secret)
    orch.set_local_bridge(bridge)
    if heartbeat:
        bridge.heartbeat("pc-1", ["complex_code_change"])
    return orch, bridge


def submit(orch, value=None):
    value = value or manifest()
    orch.submit(value, action="conversational_programming", action_params={
        "execution_plan": {"intent": "PATCH"}, "test_commands": []})
    return value["task_id"]


def queue_for_bridge(orch, task_id):
    record = orch.process_task(task_id)
    assert record["state"] == "WAITING_PROVIDER"


def test_offline_bridge_fails_closed_to_normal_escalation(tmp_path):
    orch, _ = build(tmp_path, heartbeat=False)
    task_id = submit(orch)
    record = orch.process_task(task_id)
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["result_packet"]["escalation_needed"]["needed"] is True


def test_auth_replay_and_wrong_secret_are_rejected(tmp_path):
    _, bridge = build(tmp_path)
    body = b'{}'; timestamp = str(int(bridge.clock())); nonce = "unique"
    canonical = "\n".join(["POST", "/x", timestamp, nonce, hashlib.sha256(body).hexdigest()])
    signature = hmac.new(SECRET.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    bridge.verify_request(bridge_id="pc-1", method="POST", path="/x", timestamp=timestamp,
                          nonce=nonce, body=body, signature=signature)
    with pytest.raises(PermissionError, match="replayed"):
        bridge.verify_request(bridge_id="pc-1", method="POST", path="/x", timestamp=timestamp,
                              nonce=nonce, body=body, signature=signature)
    with pytest.raises(PermissionError, match="signature"):
        bridge.verify_request(bridge_id="pc-1", method="POST", path="/x", timestamp=timestamp,
                              nonce="other", body=body, signature="0" * 64)


def test_heartbeat_endpoint_requires_valid_hmac_and_never_exposes_secret(tmp_path, monkeypatch):
    _, bridge = build(tmp_path, heartbeat=False)
    monkeypatch.setattr(backend, "JARVIS_LOCAL_AGENT_BRIDGE", bridge)
    client = TestClient(backend.app)
    path = "/api/jarvis/local-bridge/heartbeat"
    raw = json.dumps({"status": "ONLINE", "capabilities": ["complex_code_change"]},
                     separators=(",", ":")).encode()
    timestamp, nonce = str(int(bridge.clock())), "endpoint-nonce"
    canonical = "\n".join(["POST", path, timestamp, nonce, hashlib.sha256(raw).hexdigest()])
    signature = hmac.new(SECRET.encode(), canonical.encode(), hashlib.sha256).hexdigest()
    denied = client.post(path, content=raw, headers={"content-type": "application/json",
                         "x-nexus-bridge-id": "pc-1", "x-nexus-bridge-timestamp": timestamp,
                         "x-nexus-bridge-nonce": "bad", "x-nexus-bridge-signature": "0" * 64})
    assert denied.status_code == 401 and SECRET not in denied.text
    accepted = client.post(path, content=raw, headers={"content-type": "application/json",
                           "x-nexus-bridge-id": "pc-1", "x-nexus-bridge-timestamp": timestamp,
                           "x-nexus-bridge-nonce": nonce,
                           "x-nexus-bridge-signature": signature})
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ONLINE"
    assert SECRET not in accepted.text


def test_claim_is_capability_bound_and_single_lease(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit(orch); queue_for_bridge(orch, task_id)
    assert bridge.claim("pc-1", ["other_capability"]) is None
    first = bridge.claim("pc-1", ["complex_code_change"])
    assert first["task_id"] == task_id
    assert set(first["task_record"]) == {"task_id", "manifest", "action", "action_params"}
    assert "dispatch_claim" not in first["task_record"]
    event_types = [item["event_type"] for item in orch.ledger.read_for_task(task_id)]
    assert "TASK_CLAIMED" in event_types and "TASK_EXECUTION_STARTED" in event_types
    assert bridge.claim("pc-1", ["complex_code_change"]) is None
    with pytest.raises(PermissionError):
        bridge.renew(task_id, "pc-1", "wrong-lease")


def test_heartbeat_status_becomes_offline_when_stale(tmp_path):
    now = [1000.0]
    orch = Orchestrator(tmp_path / "queue.json", tmp_path / "ledger.jsonl")
    bridge = LocalAgentBridgeV1(orch, state_path=tmp_path / "bridge.json", secret=SECRET,
                                heartbeat_ttl=20, clock=lambda: now[0])
    bridge.heartbeat("pc-1", ["complex_code_change"])
    assert bridge.status("pc-1")["status"] == "ONLINE"
    now[0] += 21
    assert bridge.status("pc-1")["status"] == "OFFLINE"


def test_scope_and_test_receipts_fail_closed(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit(orch); queue_for_bridge(orch, task_id)
    claim = bridge.claim("pc-1", ["complex_code_change"])
    escaped = json.dumps({"summary": "bad", "changes": [{"path": "../escape.py",
                                                               "content": "x=1\n"}]})
    with pytest.raises(AssertionError, match="verifier receipt rejected"):
        bridge.submit_result(task_id, "pc-1", claim["lease"]["token"], "r1", escaped,
                             {"passed": True, "model": "m", "test_results": []})


def test_success_is_idempotent_result_packet_and_waits_for_approval(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit(orch); queue_for_bridge(orch, task_id)
    claim = bridge.claim("pc-1", ["complex_code_change"])
    response = json.dumps({"summary": "bounded", "changes": [
        {"path": "src/sample.py", "content": "VALUE = 2\n"}]})
    verification = {"passed": True, "model": "ministral",
                    "test_results": [{"argv": ["PYTHON", "-m", "py_compile",
                                                 "src/sample.py"], "returncode": 0}]}
    first = bridge.submit_result(task_id, "pc-1", claim["lease"]["token"], "result-1",
                                 response, verification)
    assert first["state"] == "WAITING_APPROVAL"
    assert first["result_packet"]["decision"] == "PATCH_READY_AWAITING_APPROVAL"
    assert first["result_packet"]["push_status"] == "NOT_PUSHED"
    assert bridge.submit_result(task_id, "pc-1", "ignored", "result-1",
                                response, verification)["state"] == "WAITING_APPROVAL"
    with pytest.raises(PermissionError, match="different payload"):
        bridge.submit_result(task_id, "pc-1", "ignored", "result-1",
                             response + " ", verification)


def test_retry_is_bounded_to_one_and_completed_task_cannot_be_reclaimed(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit(orch); queue_for_bridge(orch, task_id)
    first = bridge.claim("pc-1", ["complex_code_change"])
    assert bridge.report_failure(task_id, "pc-1", first["lease"]["token"],
                                 "MODEL_OFFLINE")["retry_scheduled"] is True
    second = bridge.claim("pc-1", ["complex_code_change"])
    assert bridge.report_failure(task_id, "pc-1", second["lease"]["token"],
                                 "MODEL_OFFLINE")["retry_scheduled"] is False
    failed = orch.queue.get(task_id)
    assert failed["state"] == "ESCALATION_REQUIRED"
    assert failed["result_packet"]["decision"] == "ESCALATION_REQUIRED"
    assert bridge.claim("pc-1", ["complex_code_change"]) is None


def _seed_job(bridge, task_id, status):
    """Directly write a job row in a given status - used only for EXPIRED,
    which nothing in this module ever actually assigns (see
    ACTIVE_JOB_STATES' docstring) but the guard must still treat as inactive
    for forward compatibility."""
    data = bridge._load()
    data["jobs"][task_id] = {
        "job_id": "lab_seed", "task_id": task_id, "status": status,
        "capability": bridge.CAPABILITY, "executor": "TIER2_LOCAL_STRONG",
        "model": "ministral3b", "prompt": "STALE_PROMPT_FROM_PREVIOUS_LIFECYCLE",
        "task_record": {}, "attempts": 0, "lease": None,
        "created_at": "2020-01-01T00:00:00+00:00", "updated_at": "2020-01-01T00:00:00+00:00",
        "result_id": None, "result_digest": None,
    }
    bridge._save(data)


def test_active_job_states_are_exactly_queued_and_leased():
    # LOCAL_BRIDGE_REWORK_REDISPATCH_FIX_V1's own audit, pinned so a future
    # change to this module can't silently reintroduce a third "active" value
    # (e.g. a RUNNING/EXECUTING/CLAIMED alias) without a deliberate review.
    assert LocalAgentBridgeV1.ACTIVE_JOB_STATES == {"QUEUED", "LEASED"}


def test_completed_existing_job_allows_rework_redispatch(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit(orch)
    record = orch.process_task(task_id)
    assert record["state"] == "WAITING_PROVIDER"
    claim = bridge.claim("pc-1", ["complex_code_change"])
    response = json.dumps({"summary": "bounded", "changes": [
        {"path": "src/sample.py", "content": "VALUE = 2\n"}]})
    verification = {"passed": True, "model": "ministral", "test_results": []}
    first = bridge.submit_result(task_id, "pc-1", claim["lease"]["token"], "result-1",
                                 response, verification)
    assert first["state"] == "WAITING_APPROVAL"
    assert bridge._load()["jobs"][task_id]["status"] == "COMPLETED"

    # A legitimate rework of the SAME task_id (no new task created) hands it
    # back to QUEUED, exactly like ProviderConnectorV1._apply_rework does.
    orch.queue.transition(task_id, "QUEUED")
    second = orch.process_task(task_id)
    assert second["state"] == "WAITING_PROVIDER"  # NOT stuck in RUNNING - the exact production bug
    job = bridge._load()["jobs"][task_id]
    assert job["status"] == "QUEUED"  # a brand new job row, not the stale COMPLETED one
    assert job["prompt"] != "STALE_PROMPT_FROM_PREVIOUS_LIFECYCLE"
    reclaimed = bridge.claim("pc-1", ["complex_code_change"])
    assert reclaimed is not None and reclaimed["task_id"] == task_id


def test_failed_existing_job_allows_rework_redispatch(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit(orch)
    orch.process_task(task_id)
    first_claim = bridge.claim("pc-1", ["complex_code_change"])
    bridge.report_failure(task_id, "pc-1", first_claim["lease"]["token"], "MODEL_OFFLINE")
    second_claim = bridge.claim("pc-1", ["complex_code_change"])
    bridge.report_failure(task_id, "pc-1", second_claim["lease"]["token"], "MODEL_OFFLINE")
    assert bridge._load()["jobs"][task_id]["status"] == "FAILED"  # retries exhausted
    assert orch.queue.get(task_id)["state"] == "ESCALATION_REQUIRED"

    orch.queue.transition(task_id, "QUEUED")
    record = orch.process_task(task_id)
    assert record["state"] == "WAITING_PROVIDER"  # redispatch allowed, as before this fix too
    assert bridge._load()["jobs"][task_id]["status"] == "QUEUED"
    assert bridge.claim("pc-1", ["complex_code_change"]) is not None


def test_expired_existing_job_allows_rework_redispatch(tmp_path):
    # Nothing in this module assigns "EXPIRED" today (see ACTIVE_JOB_STATES'
    # docstring) - this pins the guard's behaviour anyway, for forward
    # compatibility with a future lease-sweep that might.
    orch, bridge = build(tmp_path)
    task_id = submit(orch)
    _seed_job(bridge, task_id, "EXPIRED")
    record = orch.process_task(task_id)
    assert record["state"] == "WAITING_PROVIDER"
    job = bridge._load()["jobs"][task_id]
    assert job["status"] == "QUEUED"
    assert job["prompt"] != "STALE_PROMPT_FROM_PREVIOUS_LIFECYCLE"


def test_queued_job_blocks_double_dispatch(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit(orch)
    record = orch.process_task(task_id)
    assert record["state"] == "WAITING_PROVIDER"
    job_before = bridge._load()["jobs"][task_id]
    assert job_before["status"] == "QUEUED"

    decision = route(orch.queue.get(task_id))
    handler = orch.local_handlers["conversational_programming"]
    dispatched_again = bridge.dispatch(orch.queue.get(task_id), decision, handler)
    assert dispatched_again is True  # caller-visible contract unchanged
    job_after = bridge._load()["jobs"][task_id]
    assert job_after == job_before  # but nothing was rewritten - still the same in-flight job


def test_leased_job_blocks_double_dispatch(tmp_path):
    orch, bridge = build(tmp_path)
    task_id = submit(orch)
    orch.process_task(task_id)
    bridge.claim("pc-1", ["complex_code_change"])
    job_before = bridge._load()["jobs"][task_id]
    assert job_before["status"] == "LEASED"

    decision = route(orch.queue.get(task_id))
    handler = orch.local_handlers["conversational_programming"]
    dispatched_again = bridge.dispatch(orch.queue.get(task_id), decision, handler)
    assert dispatched_again is True
    job_after = bridge._load()["jobs"][task_id]
    assert job_after == job_before  # still leased to the same bridge - no second job created


def test_rework_after_human_reject_redispatches_through_the_bridge(tmp_path):
    """LOCAL_BRIDGE_REWORK_REDISPATCH_FIX_V1's own motivating scenario,
    replayed end-to-end exactly as it happened in production on
    TASK_4517052FD6EC: a bridge-executed patch is rejected, GROQ (modeled
    here as a MockProviderAdapter - the real adapter is covered by
    test_groq_review_adapter_v1.py) sends back REWORK_INSTRUCTIONS for the
    SAME task_id, and the bridge must accept a brand new job for it instead
    of silently no-op'ing on the first run's COMPLETED job entry."""
    orch, bridge = build(tmp_path)
    # premium_allowed=True: ProviderConnectorV1.process_task's own budget gate
    # (unrelated to this fix) requires it before a reviewer call is allowed
    # through, same as every other Dynamic Specialist Review test.
    task_id = submit(orch, manifest(task_id="TASK_BRIDGE_REWORK", premium_allowed=True))
    record = orch.process_task(task_id)
    assert record["state"] == "WAITING_PROVIDER"
    claim = bridge.claim("pc-1", ["complex_code_change"])
    response = json.dumps({"summary": "bounded", "changes": [
        {"path": "src/sample.py", "content": "VALUE = 2\n"}]})
    verification = {"passed": True, "model": "ministral", "test_results": []}
    first = bridge.submit_result(task_id, "pc-1", claim["lease"]["token"], "result-1",
                                 response, verification)
    assert first["state"] == "WAITING_APPROVAL"
    assert first["proposed_patch"]["changes"][0]["content"] == "VALUE = 2\n"
    assert bridge._load()["jobs"][task_id]["status"] == "COMPLETED"

    reviewer = MockProviderAdapter("CLAUDE", "AVAILABLE", result={
        "problems_found": ["wrong value"], "rework_instructions": "use VALUE = 3, not 2",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    connector = ProviderConnectorV1(orch, {"CLAUDE": reviewer})
    rejected = connector.request_review(task_id, "human rejected: wrong value")
    assert rejected["state"] == "QUEUED"  # handed back for local rework, never completed here
    assert rejected["escalation"]["target"] == "CLAUDE"

    second = orch.process_task(task_id)
    assert second["state"] == "WAITING_PROVIDER"  # NOT stuck in RUNNING - the exact bug
    job = bridge._load()["jobs"][task_id]
    assert job["status"] == "QUEUED"  # a fresh job, not the stale COMPLETED one from the first run

    second_claim = bridge.claim("pc-1", ["complex_code_change"])
    assert second_claim is not None and second_claim["task_id"] == task_id
    assert "VALUE = 3" in second_claim["prompt"]  # the rework instructions reached the new job

    reworked_response = json.dumps({"summary": "fixed", "changes": [
        {"path": "src/sample.py", "content": "VALUE = 3\n"}]})
    final = bridge.submit_result(task_id, "pc-1", second_claim["lease"]["token"], "result-2",
                                 reworked_response, verification)
    assert final["state"] == "WAITING_APPROVAL"
    assert final["proposed_patch"]["changes"][0]["content"] == "VALUE = 3\n"
    assert final["result_packet"]["decision"] == "PATCH_READY_AWAITING_APPROVAL"  # fresh, not stale


def test_bridge_client_has_no_generic_shell_push_or_deploy_interface():
    source=(Path(__file__).resolve().parents[2] / "LocalBridge" /
            "nexus_agent_bridge.py").read_text(encoding="utf-8")
    assert "subprocess" not in source
    assert "shell=True" not in source
    assert "git push" not in source
    assert "deploy" not in source.lower()
