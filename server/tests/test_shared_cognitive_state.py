import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orchestrator_v1.core.shared_cognitive_state import (
    ReservationConflict, RevisionConflict, SharedCognitiveState,
)
from orchestrator_v1.core.task_queue import TaskQueue


def provenance(source="test", confidence="VERIFIED"):
    return SharedCognitiveState.provenance(source, confidence=confidence)


def manifest(task_id="TASK_SHARED_1"):
    return {
        "task_id": task_id, "title": "Shared state test", "objective": "verify projection",
        "task_type": "MAINTENANCE", "priority": "NORMAL", "risk_level": "A0",
        "scientific_risk": "NONE", "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": ["log_parsing"], "deterministic_tools_available": True,
        "repo_scope": "read-only", "dependencies": [], "blockers": [],
        "expected_artifacts": ["CONTEXT_PACKET_V2"],
        "files_allowed": ["server/tests/test_shared_cognitive_state.py"],
        "files_forbidden": [], "success_criteria": ["packet projects task"],
        "verifier": "pytest", "estimated_complexity": "TRIVIAL", "estimated_runtime": "1m",
        "premium_allowed": False, "preferred_executor": "TIER0_DETERMINISTIC",
        "fallback_executors": [], "approval_required": "AUTO", "created_by": "pytest",
        "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
        "account_scope_id": None,
    }


def store(tmp_path, queue=None):
    return SharedCognitiveState(tmp_path / "shared.json", task_queue=queue)


def test_persistence_restart_and_context_packet(tmp_path):
    queue = TaskQueue(tmp_path / "queue.json")
    queue.submit(manifest())
    queue.transition("TASK_SHARED_1", "QUEUED")
    first = store(tmp_path, queue)
    first.update_current_state({
        "current_milestone": {"id": "M1", "name": "Shared state"},
        "closed_milestones": [{"id": "M0"}],
        "next_priorities": [{"id": "P0", "title": "Context"}],
        "roadmap_completion": 82,
    }, provenance=provenance("operator"), idempotency_key="state:1")
    first.upsert_decision({"decision_id": "D1", "title": "Ledger remains history",
                           "status": "ACTIVE", "decision": "Do not duplicate ledger",
                           "provenance": provenance("architecture")})

    restarted = store(tmp_path, queue)
    packet = restarted.build_context_packet(
        production_identity={"git_sha": "abcdef1", "environment": "TEST"})
    assert packet["schema_version"] == "CONTEXT_PACKET_V2"
    assert packet["production"]["git_sha"] == "abcdef1"
    assert packet["current_milestone"]["id"] == "M1"
    assert packet["active_tasks"][0]["state"] == "QUEUED"
    assert packet["active_tasks"][0]["provenance"]["source"] == "TASK_QUEUE_V1"
    assert packet["active_decisions"][0]["decision_id"] == "D1"
    from orchestrator_v1.nxs_schema_validator import validate
    schema = json.loads((Path(__file__).resolve().parents[2] / "contracts" /
                         "context-packet-v2.schema.json").read_text(encoding="utf-8"))
    assert validate(packet, schema) == []


def test_idempotency_revision_and_unverified_rejected(tmp_path):
    state = store(tmp_path)
    one = state.update_current_state({"blockers": []}, provenance=provenance(),
                                     idempotency_key="same")
    two = state.update_current_state({"blockers": [{"id": "ignored"}]},
                                     provenance=provenance(), idempotency_key="same")
    assert two["revision"] == one["revision"]
    assert two["current_state"]["blockers"] == []
    with pytest.raises(RevisionConflict):
        state.update_current_state({"blockers": []}, provenance=provenance(),
                                   expected_revision=0)
    with pytest.raises(ValueError):
        state.update_current_state({"blockers": []},
                                   provenance=provenance(confidence="UNVERIFIED"))


def test_concurrent_updates_are_serialized(tmp_path):
    state = store(tmp_path)
    errors = []

    def worker(index):
        try:
            state.upsert_workstream({"id": f"W{index}", "name": f"Work {index}",
                                     "status": "ACTIVE", "owner": f"agent-{index}",
                                     "provenance": provenance(f"thread-{index}")})
        except Exception as exc:  # pragma: no cover - asserted empty
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors
    assert len(state.snapshot()["work_graph"]["workstreams"]) == 8


def test_reservation_overlap_release_and_stale(tmp_path):
    state = store(tmp_path)
    lease = state.reserve_artifacts(owner_id="CODEX", task_id="T1", artifacts=["server/app.py"],
                                    ttl_seconds=60, provenance=provenance())
    with pytest.raises(ReservationConflict):
        state.reserve_artifacts(owner_id="CLAUDE", task_id="T2", artifacts=["server/app.py"],
                                ttl_seconds=60, provenance=provenance())
    state.release_reservation(lease["reservation_id"], lease["lease_token"])
    next_lease = state.reserve_artifacts(owner_id="CLAUDE", task_id="T2",
                                         artifacts=["server/app.py"], ttl_seconds=60,
                                         provenance=provenance())
    raw = state._load()
    for item in raw["reservations"]:
        if item["reservation_id"] == next_lease["reservation_id"]:
            item["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    state._save(raw)
    packet = state.build_context_packet()
    assert any(item["status"] == "STALE" for item in packet["artifact_reservations"])
    assert all("lease_token" not in item for item in packet["artifact_reservations"])


def test_dependencies_and_malformed_store_fail_closed(tmp_path):
    state = store(tmp_path)
    state.set_dependencies([{"from_id": "T2", "to_id": "T1", "relation": "DEPENDS_ON"}],
                           provenance=provenance())
    assert state.build_context_packet()["work_graph"]["dependencies"][0]["relation"] == "DEPENDS_ON"
    state.path.write_text("not-json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="unavailable or malformed"):
        state.snapshot()


def test_schemas_are_valid_json():
    contracts = Path(__file__).resolve().parents[2] / "contracts"
    for name in ("current-state-v1.schema.json", "work-graph-v1.schema.json",
                 "decision-registry-v1.schema.json", "artifact-reservation-v1.schema.json",
                 "context-packet-v2.schema.json"):
        assert json.loads((contracts / name).read_text(encoding="utf-8"))["$schema"]


def test_context_endpoint_is_read_only_authenticated_and_uses_runtime_sha():
    from fastapi.testclient import TestClient
    import app as backend

    route = next(route for route in backend.app.routes if route.path == "/api/jarvis/context")
    assert route.methods == {"GET"}
    with TestClient(backend.app) as client:
        assert client.get("/api/jarvis/context").status_code == 401
        backend.app.dependency_overrides[backend.require_user] = lambda: "test-user"
        try:
            response = client.get("/api/jarvis/context")
        finally:
            backend.app.dependency_overrides.pop(backend.require_user, None)
    assert response.status_code == 200
    assert response.json()["production"]["git_sha"] == backend.BUILD_GIT_SHA
    assert response.json()["schema_version"] == "CONTEXT_PACKET_V2"
