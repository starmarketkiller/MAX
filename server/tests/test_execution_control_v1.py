import json
import csv
import threading
from pathlib import Path

import pytest

from orchestrator_v1.core.execution_control import (
    ExecutionControl, InvalidTransition, UnmetDependency, WorkInProgressLimit, load_seed,
)
from orchestrator_v1.core.shared_cognitive_state import SharedCognitiveState
from orchestrator_v1.core.task_queue import TaskQueue
from orchestrator_v1.nxs_schema_validator import validate
from orchestrator_v1.run_execution_control_v1 import main


ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "server" / "orchestrator_v1" / "execution_control_seed_v1.json"
SCHEMA = ROOT / "contracts" / "execution-control-v1.schema.json"


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
        "history_source": "EVENT_LEDGER_V1",
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
