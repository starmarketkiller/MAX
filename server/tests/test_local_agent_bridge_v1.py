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


def test_bridge_client_has_no_generic_shell_push_or_deploy_interface():
    source=(Path(__file__).resolve().parents[2] / "LocalBridge" /
            "nexus_agent_bridge.py").read_text(encoding="utf-8")
    assert "subprocess" not in source
    assert "shell=True" not in source
    assert "git push" not in source
    assert "deploy" not in source.lower()
