import json
import csv
import multiprocessing
import os
import threading
import time
from pathlib import Path

import pytest

from orchestrator_v1.core.execution_control import (
    ExecutionControl, InvalidTransition, SeedCollision, UnmetDependency, WorkInProgressLimit,
    load_seed,
)
from orchestrator_v1.core.shared_cognitive_state import SharedCognitiveState, SharedStateLockTimeout
from orchestrator_v1.core.task_queue import TaskQueue
from orchestrator_v1.nxs_schema_validator import validate
from orchestrator_v1.run_execution_control_v1 import main


ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "server" / "orchestrator_v1" / "execution_control_seed_v1.json"
SCHEMA = ROOT / "contracts" / "execution-control-v1.schema.json"


def _process_transition(path, item_id, start, results):
    try:
        registry = ExecutionControl(SharedCognitiveState(path, lock_timeout_seconds=5))
        start.wait(10)
        registry.transition(item_id, "IN_PROGRESS", reason="multiprocess start")
        results.put((item_id, "OK"))
    except Exception as exc:  # pragma: no cover - asserted through child result
        results.put((item_id, type(exc).__name__))


def _process_hold_lock(path, acquired, release):
    state = SharedCognitiveState(path, lock_timeout_seconds=5)

    def hold(_state):
        acquired.set()
        release.wait(10)
        return False

    state._transaction(hold)


def _process_crash_before_persist(path, acquired):
    state = SharedCognitiveState(path, lock_timeout_seconds=5)

    def crash(_state):
        acquired.set()
        os._exit(17)

    state._transaction(crash)


def _process_crash_during_persist(path):
    import orchestrator_v1.core.shared_cognitive_state as shared_module
    state = SharedCognitiveState(path, lock_timeout_seconds=5)

    def crash_replace(_source, _target):
        os._exit(18)

    shared_module.os.replace = crash_replace
    state.update_current_state({"next_priorities": ["not-persisted"]},
                               provenance=state.provenance("crash-test"))


def provenance(source="pytest"):
    return {"source": source, "reference": "test", "confidence": "VERIFIED"}


def item(item_id, status="BACKLOG", *, kind="IMPLEMENTATION", dependencies=None,
         blockers=None, owner="CODEX"):
    return {
        "id": item_id, "title": item_id, "kind": kind, "status": status,
        "owner": {"agent_id": owner, "role": "IMPLEMENTER"},
        "completion_criteria": ["deterministic evidence exists"],
        "dependencies": dependencies or [], "blockers": blockers or [],
        "provenance": provenance(),
    }


def control(tmp_path, limit=2):
    return ExecutionControl(SharedCognitiveState(tmp_path / "state.json"),
                            implementation_wip_limit=limit)


def test_seed_contract_and_reuse_policy_are_valid():
    seed = load_seed(SEED)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert validate(seed, schema) == []
    assert seed["policy"] == {
        "canonical_source": "NEXUS_SHARED_COGNITIVE_STATE_V1.work_graph",
        "runtime_source": "TASK_QUEUE_V1",
        "history_source": "NEXUS_SHARED_COGNITIVE_STATE_V1.work_graph.embedded_history",
        "implementation_wip_limit": 2,
        "github_sync": "DISABLED_NOT_AUTHORIZED",
    }


def test_seed_import_is_persistent_and_idempotent(tmp_path):
    first = control(tmp_path)
    report = first.import_seed(load_seed(SEED))
    revision = first.shared_state.snapshot()["revision"]
    assert report["implementation_wip"]["active"] == 1
    assert {entry["id"] for entry in report["items"]} >= {
        "M1-EXECUTION-CONTROL-V1", "SCALPER-BASELINE-DECISION-RESEARCH",
        "CLAUDE-ACTIVE-WORK-RECONCILIATION",
    }
    restarted = control(tmp_path)
    restarted.import_seed(load_seed(SEED))
    assert restarted.shared_state.snapshot()["revision"] == revision


def test_transition_dependency_and_verification_gates(tmp_path):
    registry = control(tmp_path)
    registry.register(item("A"), idempotency_key="A")
    registry.register(item("B", dependencies=["A"]), idempotency_key="B")
    with pytest.raises(UnmetDependency):
        registry.transition("B", "READY", reason="attempt")
    registry.transition("A", "READY", reason="planned")
    registry.transition("A", "IN_PROGRESS", reason="started")
    registry.transition("A", "REVIEW", reason="implementation complete")
    with pytest.raises(ValueError, match="evidence"):
        registry.transition("A", "VERIFIED", reason="review")
    registry.transition("A", "VERIFIED", reason="review passed",
                        verification={"evidence": ["pytest:test_execution_control_v1"]})
    registry.transition("B", "READY", reason="dependency verified")
    with pytest.raises(InvalidTransition):
        registry.transition("B", "DELIVERED", reason="skip gates")
    with pytest.raises(ValueError, match="already exists"):
        registry.register(item("A"), idempotency_key="different-key")


def test_implementation_wip_limit_is_atomic_under_concurrency(tmp_path):
    registry = control(tmp_path, limit=2)
    for name in ("A", "B", "C"):
        registry.register(item(name, status="READY"), idempotency_key=name)
    errors = []

    def start(name):
        try:
            registry.transition(name, "IN_PROGRESS", reason="concurrent start")
        except WorkInProgressLimit as exc:
            errors.append(exc)

    threads = [threading.Thread(target=start, args=(name,)) for name in ("A", "B", "C")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    report = registry.report()
    assert report["implementation_wip"]["active"] == 2
    assert report["implementation_wip"]["within_limit"] is True
    assert len(errors) == 1


def test_implementation_wip_limit_is_atomic_across_processes(tmp_path):
    registry = control(tmp_path, limit=2)
    for name in ("A", "B", "C"):
        registry.register(item(name, status="READY"), idempotency_key=name)
    ctx = multiprocessing.get_context("spawn")
    start, results = ctx.Event(), ctx.Queue()
    processes = [ctx.Process(target=_process_transition,
                             args=(str(registry.shared_state.path), name, start, results))
                 for name in ("A", "B", "C")]
    for process in processes:
        process.start()
    start.set()
    outcomes = [results.get(timeout=15) for _ in processes]
    for process in processes:
        process.join(15)
        assert process.exitcode == 0
    report = registry.report()
    assert sorted(status for _, status in outcomes) == ["OK", "OK", "WorkInProgressLimit"]
    assert report["implementation_wip"]["active"] == 2
    assert len(report["items"]) == 3
    assert sum(entry["status"] == "READY" for entry in report["items"]) == 1


def test_same_task_process_collision_is_idempotent_without_lost_history(tmp_path):
    registry = control(tmp_path)
    registry.register(item("A", status="READY"), idempotency_key="A")
    ctx = multiprocessing.get_context("spawn")
    start, results = ctx.Event(), ctx.Queue()
    processes = [ctx.Process(target=_process_transition,
                             args=(str(registry.shared_state.path), "A", start, results))
                 for _ in range(2)]
    for process in processes:
        process.start()
    start.set()
    outcomes = [results.get(timeout=15) for _ in processes]
    for process in processes:
        process.join(15)
        assert process.exitcode == 0
    current = registry.report()["items"][0]
    assert [status for _, status in outcomes] == ["OK", "OK"]
    assert current["status"] == "IN_PROGRESS"
    assert [event["to"] for event in current["transition_history"]] == ["READY", "IN_PROGRESS"]


def test_abandoned_lock_and_crashes_preserve_canonical_state(tmp_path):
    state = SharedCognitiveState(tmp_path / "state.json")
    state.update_current_state({"next_priorities": ["baseline"]},
                               provenance=state.provenance("test"))
    baseline = state.snapshot()
    ctx = multiprocessing.get_context("spawn")

    acquired = ctx.Event()
    before = ctx.Process(target=_process_crash_before_persist,
                         args=(str(state.path), acquired))
    before.start()
    assert acquired.wait(10)
    before.join(10)
    assert before.exitcode == 17
    assert SharedCognitiveState(state.path).snapshot() == baseline

    during = ctx.Process(target=_process_crash_during_persist, args=(str(state.path),))
    during.start()
    during.join(10)
    assert during.exitcode == 18
    recovered = SharedCognitiveState(state.path)
    assert recovered.snapshot() == baseline
    assert not list(tmp_path.glob("state.json.*.tmp"))
    recovered.update_current_state({"next_priorities": ["recovered"]},
                                   provenance=recovered.provenance("test"))
    assert recovered.snapshot()["current_state"]["next_priorities"] == ["recovered"]


def test_lock_timeout_is_observable_and_fail_closed(tmp_path):
    state = SharedCognitiveState(tmp_path / "state.json")
    contender = SharedCognitiveState(state.path, lock_timeout_seconds=0.1)
    baseline = state.snapshot()
    ctx = multiprocessing.get_context("spawn")
    acquired, release = ctx.Event(), ctx.Event()
    holder = ctx.Process(target=_process_hold_lock,
                         args=(str(state.path), acquired, release))
    holder.start()
    assert acquired.wait(10)
    with pytest.raises(SharedStateLockTimeout, match="timed out"):
        contender.update_current_state({"next_priorities": ["must-not-write"]},
                                       provenance=contender.provenance("test"))
    release.set()
    holder.join(10)
    assert holder.exitcode == 0
    assert state.snapshot() == baseline


def test_seed_remains_idempotent_after_key_rotation_and_advanced_state(tmp_path):
    registry = control(tmp_path)
    seed = load_seed(SEED)
    registry.import_seed(seed)
    registry.transition("M1-EXECUTION-CONTROL-V1", "REVIEW", reason="ready for review")
    registry.handoff("M1-EXECUTION-CONTROL-V1", from_owner="CODEX",
                     to_owner={"agent_id": "CLAUDE", "role": "REVIEWER"},
                     reason="independent review", acceptance=["decision card"])
    for index in range(1001):
        registry.shared_state.update_current_state(
            {"next_priorities": [str(index)]}, provenance=provenance("rotation"),
            idempotency_key=f"rotation:{index}")
    before = registry.shared_state.snapshot()
    restarted = control(tmp_path)
    restarted.import_seed(seed)
    after = restarted.shared_state.snapshot()
    assert after["revision"] == before["revision"]
    m1 = next(entry for entry in after["work_graph"]["workstreams"]
              if entry["id"] == "M1-EXECUTION-CONTROL-V1")
    assert m1["status"] == "REVIEW"
    assert m1["owner"]["agent_id"] == "CLAUDE"
    assert len(m1["handoffs"]) == 1


def test_seed_semantic_collision_fails_without_partial_import(tmp_path):
    registry = control(tmp_path)
    seed = load_seed(SEED)
    registry.import_seed(seed)
    before = registry.shared_state.snapshot()
    incompatible = json.loads(json.dumps(seed))
    incompatible["items"][0]["title"] = "incompatible replacement"
    with pytest.raises(SeedCollision, match="conflicts"):
        registry.import_seed(incompatible)
    assert registry.shared_state.snapshot() == before

    forged = control(tmp_path)
    raw = forged.shared_state._load()
    first = raw["work_graph"]["workstreams"][0]
    first["owner"] = {"agent_id": "UNTRACED", "role": "IMPLEMENTER"}
    with forged.shared_state._locked():
        forged.shared_state._save(raw)
    forged_before = forged.shared_state.snapshot()
    with pytest.raises(SeedCollision, match="conflicts"):
        forged.import_seed(seed)
    assert forged.shared_state.snapshot() == forged_before


def test_blocked_requires_reason_and_handoff_is_owned_idempotent(tmp_path):
    registry = control(tmp_path)
    registry.register(item("A", status="READY"), idempotency_key="A")
    with pytest.raises(ValueError, match="blocker"):
        registry.transition("A", "BLOCKED", reason="blocked")
    registry.transition("A", "IN_PROGRESS", reason="start")
    with pytest.raises(PermissionError):
        registry.handoff("A", from_owner="CLAUDE",
                         to_owner={"agent_id": "SCALPER", "role": "RESEARCHER"},
                         reason="wrong owner", acceptance=["artifact"])
    registry.handoff("A", from_owner="CODEX",
                     to_owner={"agent_id": "CLAUDE", "role": "REVIEWER"},
                     reason="independent review", acceptance=["review report"],
                     idempotency_key="handoff:A:1")
    revision = registry.shared_state.snapshot()["revision"]
    registry.handoff("A", from_owner="CODEX",
                     to_owner={"agent_id": "CLAUDE", "role": "REVIEWER"},
                     reason="independent review", acceptance=["review report"],
                     idempotency_key="handoff:A:1")
    state = registry.shared_state.snapshot()
    assert state["revision"] == revision
    task = next(entry for entry in state["work_graph"]["workstreams"] if entry["id"] == "A")
    assert task["owner"]["agent_id"] == "CLAUDE"
    assert len(task["handoffs"]) == 1


def test_report_exposes_suspended_work_and_cli(tmp_path, capsys):
    registry = control(tmp_path)
    blocked = item("A", status="BLOCKED", blockers=[{
        "code": "WAITING_HUMAN", "reason": "approval required", "requires_human": True,
    }])
    registry.register(blocked, idempotency_key="A")
    report = registry.report()
    assert report["suspended"][0]["id"] == "A"
    assert report["github_sync"] == "DISABLED_NOT_AUTHORIZED"
    assert main(["report", "--state", str(tmp_path / "state.json")]) == 0
    output = capsys.readouterr().out
    assert "Implementation WIP: 0/2" in output
    assert "WAITING_HUMAN" not in output
    assert "approval required" in output


def test_report_projects_runtime_queue_without_copying_it(tmp_path):
    queue = TaskQueue(tmp_path / "queue.json")
    queue.submit({
        "task_id": "TASK_M1_RUNTIME", "title": "Runtime child", "objective": "project it",
        "task_type": "MAINTENANCE", "priority": "NORMAL", "risk_level": "A0",
        "scientific_risk": "NONE", "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": ["reporting"], "deterministic_tools_available": True,
        "repo_scope": "read-only", "dependencies": [], "blockers": [],
        "expected_artifacts": ["report"], "files_allowed": [], "files_forbidden": [],
        "success_criteria": ["visible"], "verifier": "pytest",
        "estimated_complexity": "TRIVIAL", "estimated_runtime": "1m",
        "premium_allowed": False, "preferred_executor": "TIER0_DETERMINISTIC",
        "fallback_executors": [], "approval_required": "AUTO", "created_by": "pytest",
        "created_at": "2026-10-13T00:00:00+00:00", "tenant_id": "test",
        "account_scope_id": None,
    })
    queue.transition("TASK_M1_RUNTIME", "QUEUED")
    state = SharedCognitiveState(tmp_path / "state.json", task_queue=queue)
    report = ExecutionControl(state).report()
    assert report["active_runtime_tasks"][0]["task_id"] == "TASK_M1_RUNTIME"
    assert state.snapshot()["work_graph"]["workstreams"] == []


def test_policy_module_has_no_network_or_github_mutation_imports():
    source = (ROOT / "server" / "orchestrator_v1" / "core" /
              "execution_control.py").read_text(encoding="utf-8")
    assert "import requests" not in source
    assert "import subprocess" not in source
    assert "gh " not in source


def test_branch_and_pr_inventory_is_complete_and_evidence_backed():
    inventory = ROOT / "docs" / "execution_control" / "BRANCH_PR_CLASSIFICATION_V1.csv"
    with inventory.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    branches = [row for row in rows if row["record_type"] == "BRANCH"]
    prs = [row for row in rows if row["record_type"] == "PR"]
    assert len(branches) == 66
    assert {row["name"] for row in prs} == {"10", "13", "17"}
    assert sum(row["classification"] == "INTEGRATED_BY_ANCESTRY" for row in branches) == 36
    assert all(len(row["tip_sha"]) == 40 and row["evidence"] for row in rows)
