import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from jarvis_v1.free_coding_worker import FreeCodingWorkerHandler
from core.orchestrator import Orchestrator
from core.provider_connector import MockProviderAdapter, ProviderConnectorV1
from core.provider_policy import ProviderPolicyRegistryV1
from core.router import route


def manifest(task_id="TASK_CODING", **changes):
    value = {
        "task_id": task_id, "title": "Bounded code patch", "objective": "Update src/sample.py",
        "task_type": "CODE", "work_type": "complex_code", "priority": "NORMAL",
        "risk_level": "A1", "scientific_risk": "NONE", "code_risk": "HIGH",
        "financial_risk": "NONE",
        "required_capabilities": ["small_python_functions", "unit_test_writing"],
        "deterministic_tools_available": False, "repo_scope": "task-scoped",
        "files_allowed": ["src/sample.py"], "files_forbidden": [".env", "MQL5/**"],
        "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
        "success_criteria": ["bounded patch verified"], "verifier": "free_coding_worker_v1",
        "estimated_complexity": "SMALL", "estimated_runtime": "5m", "premium_allowed": False,
        "preferred_executor": "TIER1_LOCAL_CHEAP",
        "fallback_executors": ["TIER2_LOCAL_STRONG", "TIER4_CODEX"],
        "approval_required": "REVIEW_REQUIRED", "created_by": "test",
        "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
        "account_scope_id": None,
    }
    value.update(changes)
    return value


def setup_orchestrator(tmp_path):
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "src" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    orch = Orchestrator(tmp_path / "queue.json", tmp_path / "ledger.jsonl")
    handler = FreeCodingWorkerHandler(project_root=project,
                                      workspace_root=tmp_path / "workspaces")
    orch.register_local_handler("conversational_programming", handler)
    return orch, project


def submit(orch, value=None, *, test_commands=None):
    value = value or manifest()
    orch.submit(value, action="conversational_programming", action_params={
        "execution_plan": {"intent": "PATCH"}, "test_commands": test_commands or []})
    return value["task_id"]


def local_success(monkeypatch, content="VALUE = 2\n"):
    calls = []
    def invoke(prompt, model):
        calls.append({"prompt": prompt, "model": model})
        return {"success": True, "model": model,
                "response_text": json.dumps({"summary": "bounded fix", "changes": [
                    {"path": "src/sample.py", "content": content}]}),
                "wall_seconds": 0.1, "error": None}
    monkeypatch.setattr("core.orchestrator.ollama_worker.call_local_model", invoke)
    return calls


def test_local_route_uses_core_ollama_handler_and_stops_for_approval(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    calls = local_success(monkeypatch)
    task_id = submit(orch)
    assert route(orch.queue.get(task_id)).tier == "TIER2_LOCAL_STRONG"
    record = orch.process_task(task_id)
    assert len(calls) == 1
    assert record["executor"] == "LOCAL_STRONG_MINISTRAL3B"
    assert record["state"] == "WAITING_APPROVAL"
    assert record["result_packet"]["decision"] == "PATCH_READY_AWAITING_APPROVAL"
    assert (project / "src" / "sample.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    proposal = Path(record["result_packet"]["artifacts_created"][0])
    assert (proposal / "src" / "sample.py").read_text(encoding="utf-8") == "VALUE = 2\n"


def test_missing_capability_never_executes_local(tmp_path, monkeypatch):
    orch, _ = setup_orchestrator(tmp_path)
    calls = local_success(monkeypatch)
    task_id = submit(orch, manifest(required_capabilities=["multi_file_refactor"]))
    record = orch.process_task(task_id)
    assert calls == []
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["escalation"]["target"] == "TIER4_CODEX"


def test_local_unavailable_routes_fail_closed_without_worker_call(tmp_path, monkeypatch):
    orch, _ = setup_orchestrator(tmp_path)
    calls = local_success(monkeypatch)
    from core import capability
    registry = copy.deepcopy(capability.load_registry())
    for agent in registry["agents"]:
        if agent["local_or_remote"] == "LOCAL": agent["availability"] = "OFFLINE"
    monkeypatch.setattr("core.capability.load_registry", lambda: registry)
    task_id = submit(orch)
    record = orch.process_task(task_id)
    assert calls == []
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["escalation"]["target"] == "TIER4_CODEX"


def test_evaluation_only_free_provider_is_never_production_execution():
    preview = ProviderPolicyRegistryV1().route_preview(manifest())
    assert preview["executed"] is False and preview["provider_calls"] == 0
    assert preview["evaluation_candidates"]
    assert all(candidate["eligible_for_execution"] is False
               for candidate in preview["evaluation_candidates"])


def test_premium_disallowed_never_calls_adapter(tmp_path):
    orch, _ = setup_orchestrator(tmp_path)
    task_id = submit(orch, manifest(required_capabilities=["multi_file_refactor"]))
    orch.process_task(task_id)
    adapter = MockProviderAdapter(provider_id="CODEX")
    connector = ProviderConnectorV1(orch, {"CODEX": adapter})
    record = connector.process_task(task_id)
    assert record["provider_execution"]["status"] == "POLICY_BLOCKED"
    assert adapter.calls == []


def test_worker_cannot_change_tier_and_retry_is_bounded_to_one(tmp_path, monkeypatch):
    orch, _ = setup_orchestrator(tmp_path)
    calls = []
    def invalid(prompt, model):
        calls.append(model)
        return {"success": True, "model": model,
                "response_text": json.dumps({"summary": "x", "provider": "CODEX",
                    "changes": [{"path": "src/sample.py", "content": "VALUE=3\n"}]}),
                "wall_seconds": 0.1, "error": None}
    monkeypatch.setattr("core.orchestrator.ollama_worker.call_local_model", invalid)
    task_id = submit(orch)
    record = orch.process_task(task_id)
    assert len(calls) == 2  # initial attempt + exactly one bounded retry
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["escalation"]["target"] == "TIER4_CODEX"
    events = orch.ledger.read_for_task(task_id)
    assert any(event["event_type"] == "RETRY_STARTED" for event in events)
    assert any(event["event_type"] == "ESCALATION_REQUIRED" for event in events)


def test_command_allowlist_rejects_shell_and_out_of_scope_patch(tmp_path):
    orch, _ = setup_orchestrator(tmp_path)
    handler = orch.local_handlers["conversational_programming"]
    record = {"task_id": "TASK_DIRECT", "manifest": manifest(), "action_params": {
        "test_commands": [["bash", "-c", "anything"]]}}
    response = json.dumps({"summary": "x", "changes": [
        {"path": "src/sample.py", "content": "VALUE=2\n"}]})
    assert handler.verify(record, response).passed is False
    escaped = json.dumps({"summary": "x", "changes": [
        {"path": "../escape.py", "content": "x=1\n"}]})
    assert handler.verify(record, escaped).passed is False
    record["action_params"]["test_commands"] = [
        ["PYTHON", "-m", "pytest", "server/app.py", "--override-ini=anything"]]
    assert handler.verify(record, response).passed is False
