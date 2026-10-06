"""NEXUS_LOCAL_TASK_LEDGER_V1 - task_handoff.py renders the already-canonical
TaskQueue record + RESULT_PACKET_V1 + Activity Ledger events into
task.md/result.md/handoff.md/verifier_report.json/execution_log.jsonl.
Pure read + render: never mutates the task, never a second data model.
"""
from datetime import datetime, timezone

import pytest

from jarvis_v1 import task_handoff
from jarvis_v1.service import JarvisService


def _manifest(task_id):
    return {
        "task_id": task_id, "title": "Handoff test task", "objective": "Analizza i CSV MT5",
        "task_type": "RESEARCH", "work_type": "business_analysis", "priority": "NORMAL",
        "risk_level": "A1", "scientific_risk": "LOW", "code_risk": "NONE",
        "financial_risk": "NONE", "required_capabilities": ["repo.read", "csv.inspect"],
        "deterministic_tools_available": False, "repo_scope": "read-only analysis",
        "files_allowed": [], "files_forbidden": ["MQL5/**", ".env", "**/*secret*"],
        "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
        "success_criteria": ["source-backed"], "verifier": "independent_review",
        "estimated_complexity": "SMALL", "estimated_runtime": "durable", "premium_allowed": False,
        "preferred_executor": "TIER1_LOCAL_CHEAP", "fallback_executors": [],
        "approval_required": "AUTO", "created_by": "jarvis:42",
        "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
        "account_scope_id": None,
    }


RESULT_PACKET = {
    "task_id": "TASK_HANDOFF_1", "executor": "TIER1_LOCAL_CHEAP",
    "start_time": "2026-10-06T10:00:00+00:00", "end_time": "2026-10-06T10:05:00+00:00",
    "files_read": ["server/mt5_data_v1/csv_formats.py"],
    "files_changed": [], "tools_or_commands": ["repo.read"],
    "artifacts_created": ["analysis.md"],
    "tests": {"ran": True, "passed": 5, "failed": 0},
    "verifier": {"ran": True, "passed": True, "errors": []},
    "commit": None, "push_status": "NOT_APPLICABLE",
    "decision": "Trovate 2 anomalie nei CSV analizzati.",
    "confidence": "HIGH", "limitations": ["Solo 3 file campionati"],
    "unresolved_issues": ["Formato broker non verificato"],
    "suggested_next_tasks": ["Verificare formato export broker reale"],
    "escalation_needed": {"needed": False, "reason": None, "target_tier": None},
}


@pytest.fixture
def service(tmp_path, monkeypatch):
    svc = JarvisService(str(tmp_path / "q.json"), str(tmp_path / "l.jsonl"), str(tmp_path / "c.json"))
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    return svc


def _submit_completed(service, task_id="TASK_HANDOFF_1"):
    service.orchestrator.submit(_manifest(task_id), action="conversational_programming",
                               action_params={"conversation_id": "c1"})
    service.queue.transition(task_id, "RUNNING", executor="TIER1_LOCAL_CHEAP")
    service.queue.transition(task_id, "COMPLETED", result_packet=RESULT_PACKET)
    return task_id


def test_write_task_artifacts_returns_none_for_unknown_task(service):
    assert task_handoff.write_task_artifacts(service, "TASK_DOES_NOT_EXIST") is None


def test_write_task_artifacts_creates_all_five_files(service, tmp_path):
    task_id = _submit_completed(service)
    paths = task_handoff.write_task_artifacts(service, task_id, out_dir=tmp_path / "out")
    assert set(paths) == set(task_handoff.ARTIFACT_FILENAMES)
    for p in paths.values():
        assert __import__("pathlib").Path(p).exists()


def test_task_md_contains_core_manifest_fields(service, tmp_path):
    task_id = _submit_completed(service)
    paths = task_handoff.write_task_artifacts(service, task_id, out_dir=tmp_path / "out")
    content = open(paths["task.md"], encoding="utf-8").read()
    assert "Handoff test task" in content
    assert "Analizza i CSV MT5" in content
    assert "COMPLETED" in content


def test_handoff_md_contains_verifiable_fields_not_chain_of_thought(service, tmp_path):
    task_id = _submit_completed(service)
    paths = task_handoff.write_task_artifacts(service, task_id, out_dir=tmp_path / "out")
    content = open(paths["handoff.md"], encoding="utf-8").read()
    assert "Trovate 2 anomalie nei CSV analizzati." in content
    assert "server/mt5_data_v1/csv_formats.py" in content
    assert "Solo 3 file campionati" in content
    assert "Verificare formato export broker reale" in content
    assert "ran=True passed=5 failed=0" in content


def test_verifier_report_json_mirrors_result_packet_verifier(service, tmp_path):
    task_id = _submit_completed(service)
    paths = task_handoff.write_task_artifacts(service, task_id, out_dir=tmp_path / "out")
    import json
    report = json.loads(open(paths["verifier_report.json"], encoding="utf-8").read())
    assert report["task_id"] == task_id
    assert report["verifier"]["passed"] is True
    assert report["tests"]["passed"] == 5


def test_execution_log_jsonl_contains_only_this_tasks_events(service, tmp_path):
    task_id = _submit_completed(service)
    service.orchestrator.submit(_manifest("TASK_OTHER"), action="conversational_programming",
                                action_params={"conversation_id": "c1"})
    paths = task_handoff.write_task_artifacts(service, task_id, out_dir=tmp_path / "out")
    import json
    lines = open(paths["execution_log.jsonl"], encoding="utf-8").read().splitlines()
    events = [json.loads(line) for line in lines]
    assert events
    assert all(e["task_id"] == task_id for e in events)


def test_result_md_reflects_unterminated_task_honestly(service, tmp_path):
    service.orchestrator.submit(_manifest("TASK_RUNNING_1"), action="conversational_programming",
                               action_params={"conversation_id": "c1"})
    service.queue.transition("TASK_RUNNING_1", "RUNNING", executor="TIER1_LOCAL_CHEAP")
    paths = task_handoff.write_task_artifacts(service, "TASK_RUNNING_1", out_dir=tmp_path / "out")
    content = open(paths["result.md"], encoding="utf-8").read()
    assert "N/D" in content


def test_write_task_artifacts_is_idempotent_and_reflects_latest_state(service, tmp_path):
    service.orchestrator.submit(_manifest("TASK_EVOLVING"), action="conversational_programming",
                               action_params={"conversation_id": "c1"})
    service.queue.transition("TASK_EVOLVING", "RUNNING", executor="TIER1_LOCAL_CHEAP")
    out = tmp_path / "out"
    task_handoff.write_task_artifacts(service, "TASK_EVOLVING", out_dir=out)
    service.queue.transition("TASK_EVOLVING", "COMPLETED", result_packet=dict(RESULT_PACKET, task_id="TASK_EVOLVING"))
    task_handoff.write_task_artifacts(service, "TASK_EVOLVING", out_dir=out)
    content = (out / "task.md").read_text(encoding="utf-8")
    assert "COMPLETED" in content
