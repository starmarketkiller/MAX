"""LOCAL_VERIFIER_REJECTED_TO_DYNAMIC_REVIEW_V1 - the second door into the
already-existing NEXUS Dynamic Specialist Review. fail_local_bridge_task()
used to dead-end every Local Agent Bridge retry exhaustion at a hardcoded
MANUAL_REVIEW target nothing ever picks up automatically; this reuses the
exact same candidate selection / availability / policy / rework hand-back
machinery as the human-reject door (request_review), through a single
shared _begin_review() helper - one state machine, two doors - with a
MAX_REWORK_CYCLES budget shared by the WHOLE lineage so a
local-fail -> review -> local-fail -> review loop cannot run forever.
"""
import json
from datetime import datetime, timezone

from jarvis_v1.free_coding_worker import FreeCodingWorkerHandler
from core.orchestrator import Orchestrator
from core.provider_connector import MockProviderAdapter, OfflineProviderAdapter, ProviderConnectorV1
from core.specialist_review import LOCAL_VERIFIER_REJECTED_REVIEW_REQUIRED


def manifest(task_id="TASK_LOCAL_FAIL", **changes):
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
        "estimated_complexity": "SMALL", "estimated_runtime": "5m", "premium_allowed": True,
        "preferred_executor": "TIER2_LOCAL_STRONG",
        "fallback_executors": ["TIER4_CODEX"],
        "approval_required": "REVIEW_REQUIRED", "created_by": "jarvis:42",
        "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
        "account_scope_id": None,
    }
    value.update(changes)
    return value


def setup_locally_rejected_task(tmp_path, *, task_id="TASK_LOCAL_FAIL"):
    """Gets a task to ESCALATION_REQUIRED/target=MANUAL_REVIEW/
    classification=LOCAL_VERIFIER_REJECTED - exactly fail_local_bridge_task()'s
    own real trigger (the Local Agent Bridge exhausted MAX_ATTEMPTS because
    the verifier rejected the local model's output), independent of whether
    a real bridge object is wired - fail_local_bridge_task() itself only
    requires state=WAITING_PROVIDER, never touches self.local_bridge."""
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "src" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    orch = Orchestrator(tmp_path / "queue.json", tmp_path / "ledger.jsonl")
    handler = FreeCodingWorkerHandler(project_root=project, workspace_root=tmp_path / "workspaces")
    orch.register_local_handler("conversational_programming", handler)
    value = manifest(task_id=task_id)
    orch.submit(value, action="conversational_programming", action_params={
        "execution_plan": {"intent": "PATCH"}, "test_commands": []})
    orch.queue.transition(task_id, "RUNNING", executor="LOCAL_STRONG_MINISTRAL3B")
    orch.queue.transition(task_id, "WAITING_PROVIDER", local_bridge={"status": "QUEUED"})
    record = orch.fail_local_bridge_task(task_id, "LOCAL_VERIFIER_REJECTED")
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["escalation"]["target"] == "MANUAL_REVIEW"
    assert record["escalation"]["classification"] == "LOCAL_VERIFIER_REJECTED"
    return orch, project, task_id


def _resolve_with_local_rework(orch, project, task_id, calls, monkeypatch, *, patch_content):
    """Drives one local-worker retry cycle after a reviewer handed back
    REWORK_INSTRUCTIONS - same mechanism setup_rejected_task() uses
    elsewhere in this suite, reused here rather than re-implemented."""
    def invoke(prompt, model):
        return {"success": True, "model": model,
                "response_text": json.dumps({"summary": "fix", "changes": [
                    {"path": "src/sample.py", "content": patch_content}]}),
                "wall_seconds": 0.1, "error": None, "prompt_seen": prompt}
    def tracked_invoke(prompt, model):
        result = invoke(prompt, model)
        calls.append(result)
        return result
    monkeypatch.setattr("core.orchestrator.ollama_worker.call_local_model", tracked_invoke)
    return orch.process_task(task_id)


def test_local_verifier_rejected_routes_into_dynamic_review(tmp_path):
    orch, project, task_id = setup_locally_rejected_task(tmp_path)
    groq = MockProviderAdapter("GROQ", "AVAILABLE", result={
        "problems_found": ["x"], "rework_instructions": "fix x",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    connector = ProviderConnectorV1(orch, {"GROQ": groq})

    advanced = connector.run_once()
    assert advanced is True
    record = orch.queue.get(task_id)
    assert record["state"] == "QUEUED"  # review completed, handed back for rework
    assert record["escalation"]["classification"] == LOCAL_VERIFIER_REJECTED_REVIEW_REQUIRED
    events = [e["event_type"] for e in orch.ledger.read_for_task(task_id)]
    assert "LOCAL_VERIFIER_REJECTED" in events
    assert "REVIEW_REQUESTED" in events and "REVIEW_COMPLETED" in events
    assert "REWORK_INSTRUCTIONS_RECEIVED" in events


def test_groq_available_reviews_without_premium(tmp_path):
    orch, project, task_id = setup_locally_rejected_task(tmp_path)
    groq = MockProviderAdapter("GROQ", "AVAILABLE", result={
        "problems_found": ["wrong value"], "rework_instructions": "use VALUE = 3, not 2",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    codex = MockProviderAdapter("CODEX", "AVAILABLE")
    claude = MockProviderAdapter("CLAUDE", "AVAILABLE")
    connector = ProviderConnectorV1(orch, {"GROQ": groq, "CODEX": codex, "CLAUDE": claude})

    connector.run_once()
    assert groq.calls and not codex.calls and not claude.calls  # zero premium
    record = orch.queue.get(task_id)
    assert record["state"] == "QUEUED"
    assert "use VALUE = 3" in record["action_params"]["rework_instructions"]


def test_groq_unavailable_falls_back_to_codex_or_claude(tmp_path):
    orch, project, task_id = setup_locally_rejected_task(tmp_path)
    groq = MockProviderAdapter("GROQ", "OFFLINE")
    codex = MockProviderAdapter("CODEX", "AVAILABLE", result={
        "problems_found": [], "rework_instructions": "retry with a comment line",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    claude = MockProviderAdapter("CLAUDE", "AVAILABLE")
    connector = ProviderConnectorV1(orch, {"GROQ": groq, "CODEX": codex, "CLAUDE": claude})

    connector.run_once()
    assert codex.calls and not claude.calls  # preference respected, Claude never touched
    assert orch.queue.get(task_id)["escalation"]["target"] == "CODEX"


def test_all_unavailable_parks_in_waiting_review_provider(tmp_path):
    orch, project, task_id = setup_locally_rejected_task(tmp_path)
    groq = MockProviderAdapter("GROQ", "OFFLINE")
    codex = MockProviderAdapter("CODEX", "EXHAUSTED")
    claude = MockProviderAdapter("CLAUDE", "OFFLINE")
    connector = ProviderConnectorV1(orch, {"GROQ": groq, "CODEX": codex, "CLAUDE": claude})

    connector.run_once()
    record = orch.queue.get(task_id)
    assert record["state"] == "WAITING_REVIEW_PROVIDER"
    assert groq.calls == [] and codex.calls == [] and claude.calls == []


def test_provider_unavailable_does_not_consume_rework_cycle(tmp_path):
    orch, project, task_id = setup_locally_rejected_task(tmp_path)
    connector = ProviderConnectorV1(orch, {
        "GROQ": MockProviderAdapter("GROQ", "OFFLINE"),
        "CODEX": MockProviderAdapter("CODEX", "OFFLINE"),
        "CLAUDE": MockProviderAdapter("CLAUDE", "OFFLINE")})

    connector.run_once()
    assert orch.queue.get(task_id)["state"] == "WAITING_REVIEW_PROVIDER"
    assert connector._rework_cycles_used(task_id) == 0
    # A second idle poll while still nobody is available - still zero.
    connector.run_once()
    assert connector._rework_cycles_used(task_id) == 0


def test_review_completed_hands_back_to_local_worker(tmp_path):
    orch, project, task_id = setup_locally_rejected_task(tmp_path)
    groq = MockProviderAdapter("GROQ", "AVAILABLE", result={
        "problems_found": ["missing comment"], "rework_instructions": "add one comment line at the top",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    connector = ProviderConnectorV1(orch, {"GROQ": groq})
    connector.run_once()
    record = orch.queue.get(task_id)
    assert record["state"] == "QUEUED"
    assert record["provider_execution"]["status"] == "REWORK_RECEIVED"
    assert "add one comment line" in record["action_params"]["rework_instructions"]


def test_verifier_passes_reaches_waiting_approval(tmp_path, monkeypatch):
    orch, project, task_id = setup_locally_rejected_task(tmp_path)
    groq = MockProviderAdapter("GROQ", "AVAILABLE", result={
        "problems_found": ["x"], "rework_instructions": "fix it",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    connector = ProviderConnectorV1(orch, {"GROQ": groq})
    connector.run_once()
    assert orch.queue.get(task_id)["state"] == "QUEUED"

    calls = []
    record = _resolve_with_local_rework(orch, project, task_id, calls, monkeypatch,
                                        patch_content="VALUE = 2\n")
    assert record["state"] == "WAITING_APPROVAL"
    assert record["proposed_patch"]["changes"][0]["content"] == "VALUE = 2\n"
    assert record["result_packet"]["decision"] == "PATCH_READY_AWAITING_APPROVAL"


def test_verifier_fails_again_triggers_second_cycle(tmp_path):
    orch, project, task_id = setup_locally_rejected_task(tmp_path)
    groq = MockProviderAdapter("GROQ", "AVAILABLE", result={
        "problems_found": ["x"], "rework_instructions": "fix it (attempt 1)",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    connector = ProviderConnectorV1(orch, {"GROQ": groq})
    connector.run_once()
    assert orch.queue.get(task_id)["state"] == "QUEUED"
    assert connector._rework_cycles_used(task_id) == 1

    # The local worker's SECOND attempt also fails the verifier - back to
    # WAITING_PROVIDER then fail_local_bridge_task(), exactly like the first.
    orch.queue.transition(task_id, "RUNNING", executor="LOCAL_STRONG_MINISTRAL3B")
    orch.queue.transition(task_id, "WAITING_PROVIDER", local_bridge={"status": "QUEUED"})
    failed = orch.fail_local_bridge_task(task_id, "LOCAL_VERIFIER_REJECTED")
    assert failed["state"] == "ESCALATION_REQUIRED"
    assert failed["escalation"]["target"] == "MANUAL_REVIEW"

    groq.result = {"problems_found": ["y"], "rework_instructions": "fix it (attempt 2)",
                   "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []}
    # Two LOCAL_VERIFIER_REJECTED cycles for the same task build a
    # byte-identical context packet (same reject_reason, no proposed_patch
    # either time) - MockProviderAdapter's own idempotency-key cache would
    # otherwise replay cycle 1's cached result instead of calling invoke()
    # again. A real provider has no such cache; this is a test-double
    # artifact, not production behaviour.
    groq._cache = {}
    advanced = connector.run_once()
    assert advanced is True  # a SECOND review cycle starts - budget not yet exhausted
    record = orch.queue.get(task_id)
    assert record["state"] == "QUEUED"
    assert "attempt 2" in record["action_params"]["rework_instructions"]
    assert connector._rework_cycles_used(task_id) == 2


def test_third_failure_hits_manual_review_budget_exhausted(tmp_path):
    orch, project, task_id = setup_locally_rejected_task(tmp_path)
    groq = MockProviderAdapter("GROQ", "AVAILABLE", result={
        "problems_found": [], "rework_instructions": "attempt 1",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    pushed = []
    connector = ProviderConnectorV1(orch, {"GROQ": groq},
                                    telegram_notifier=lambda chat_id, response: pushed.append(response))

    # Cycle 1.
    connector.run_once()
    orch.queue.transition(task_id, "RUNNING", executor="LOCAL_STRONG_MINISTRAL3B")
    orch.queue.transition(task_id, "WAITING_PROVIDER", local_bridge={"status": "QUEUED"})
    orch.fail_local_bridge_task(task_id, "LOCAL_VERIFIER_REJECTED")
    # Cycle 2.
    groq.result = {"problems_found": [], "rework_instructions": "attempt 2",
                   "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []}
    connector.run_once()
    assert connector._rework_cycles_used(task_id) == 2
    orch.queue.transition(task_id, "RUNNING", executor="LOCAL_STRONG_MINISTRAL3B")
    orch.queue.transition(task_id, "WAITING_PROVIDER", local_bridge={"status": "QUEUED"})
    orch.fail_local_bridge_task(task_id, "LOCAL_VERIFIER_REJECTED")

    # Third failure - budget (2) already fully used, no third review is
    # ever requested (groq.calls must NOT grow past the first 2).
    calls_before = len(groq.calls)
    advanced = connector.run_once()
    assert advanced is True
    assert len(groq.calls) == calls_before  # no third provider call was made
    record = orch.queue.get(task_id)
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["escalation"]["target"] == "MANUAL_REVIEW"
    assert record["escalation"]["rework_budget_exhausted"] is True
    events = [e["event_type"] for e in orch.ledger.read_for_task(task_id)]
    assert "REWORK_BUDGET_EXHAUSTED" in events
    assert pushed and pushed[-1]["status"] == "MANUAL_REVIEW"


def test_lineage_and_task_id_unchanged_across_cycles(tmp_path):
    orch, project, task_id = setup_locally_rejected_task(tmp_path, task_id="TASK_LINEAGE_CHECK")
    groq = MockProviderAdapter("GROQ", "AVAILABLE", result={
        "problems_found": ["x"], "rework_instructions": "fix it",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    connector = ProviderConnectorV1(orch, {"GROQ": groq})
    connector.run_once()
    record = orch.queue.get(task_id)
    assert record["task_id"] == "TASK_LINEAGE_CHECK"
    assert record["manifest"]["task_id"] == "TASK_LINEAGE_CHECK"
    assert len(orch.queue.list_all()) == 1  # no new task was ever created


def test_mixed_doors_share_one_rework_budget(tmp_path, monkeypatch):
    """REWORK_CYCLES budget is per-lineage, not per-door: a human-reject
    cycle followed by a local-verifier-reject cycle must together count as
    2/2, exhausting the budget - exactly the scenario the user called out
    explicitly ('il conteggio deve includere anche i cicli gia' fatti dopo
    rejection umana, non resettarsi')."""
    from test_dynamic_specialist_review_v1 import setup_rejected_task

    orch, project, task_id, calls = setup_rejected_task(tmp_path, monkeypatch)
    claude = MockProviderAdapter("CLAUDE", "AVAILABLE", result={
        "problems_found": ["x"], "rework_instructions": "human-door fix",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    connector = ProviderConnectorV1(orch, {"CLAUDE": claude})

    connector.request_review(task_id, "human rejected")  # cycle 1 (human door)
    assert connector._rework_cycles_used(task_id) == 1

    orch.queue.transition(task_id, "RUNNING", executor="LOCAL_STRONG_MINISTRAL3B")
    orch.queue.transition(task_id, "WAITING_PROVIDER", local_bridge={"status": "QUEUED"})
    orch.fail_local_bridge_task(task_id, "LOCAL_VERIFIER_REJECTED")
    claude.result = {"problems_found": ["y"], "rework_instructions": "local-door fix",
                     "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []}
    connector.run_once()  # cycle 2 (local-verifier door)
    assert connector._rework_cycles_used(task_id) == 2

    orch.queue.transition(task_id, "RUNNING", executor="LOCAL_STRONG_MINISTRAL3B")
    orch.queue.transition(task_id, "WAITING_PROVIDER", local_bridge={"status": "QUEUED"})
    orch.fail_local_bridge_task(task_id, "LOCAL_VERIFIER_REJECTED")
    calls_before = len(claude.calls)
    connector.run_once()  # third attempt - budget already exhausted by the mix
    assert len(claude.calls) == calls_before
    record = orch.queue.get(task_id)
    assert record["escalation"]["target"] == "MANUAL_REVIEW"
    assert record["escalation"]["rework_budget_exhausted"] is True
