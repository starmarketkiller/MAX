import json
from datetime import datetime, timezone

from jarvis_v1.free_coding_worker import FreeCodingWorkerHandler
from core.orchestrator import Orchestrator
from core.provider_connector import MockProviderAdapter, OfflineProviderAdapter, ProviderConnectorV1
from core.specialist_review import select_reviewer_candidates, validate_rework_response


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
        "estimated_complexity": "SMALL", "estimated_runtime": "5m", "premium_allowed": True,
        "preferred_executor": "TIER1_LOCAL_CHEAP",
        "fallback_executors": ["TIER2_LOCAL_STRONG", "TIER4_CODEX"],
        "approval_required": "REVIEW_REQUIRED", "created_by": "jarvis:42",
        "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
        "account_scope_id": None,
    }
    value.update(changes)
    return value


def setup_rejected_task(tmp_path, monkeypatch, *, patch_content="VALUE = 2\n"):
    """Gets a task all the way to WAITING_APPROVAL with a real proposed_patch
    on the record, exactly like the live TASK_6FEA7BDE04D2 did, then rejects
    it - the starting point for every Dynamic Specialist Review scenario."""
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "src" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    orch = Orchestrator(tmp_path / "queue.json", tmp_path / "ledger.jsonl")
    handler = FreeCodingWorkerHandler(project_root=project, workspace_root=tmp_path / "workspaces")
    orch.register_local_handler("conversational_programming", handler)

    def invoke(prompt, model):
        return {"success": True, "model": model,
                "response_text": json.dumps({"summary": "fix", "changes": [
                    {"path": "src/sample.py", "content": patch_content}]}),
                "wall_seconds": 0.1, "error": None, "prompt_seen": prompt}
    calls = []
    def tracked_invoke(prompt, model):
        result = invoke(prompt, model)
        calls.append(result)
        return result
    monkeypatch.setattr("core.orchestrator.ollama_worker.call_local_model", tracked_invoke)

    value = manifest()
    orch.submit(value, action="conversational_programming", action_params={
        "execution_plan": {"intent": "PATCH"}, "test_commands": []})
    record = orch.process_task(value["task_id"])
    assert record["state"] == "WAITING_APPROVAL"
    assert record["proposed_patch"]["changes"][0]["path"] == "src/sample.py"
    return orch, project, value["task_id"], calls


def test_select_reviewer_candidates_is_ordered_capability_first():
    assert select_reviewer_candidates("complex_code") == ["CODEX", "CLAUDE"]
    assert select_reviewer_candidates("scientific_research") == ["CLAUDE"]
    assert select_reviewer_candidates("unknown_work_type") == ["CLAUDE"]
    # Pure and side-effect-free: mutating the result must never affect the
    # next call (a caller stores this on a task record and may append to it).
    candidates = select_reviewer_candidates("complex_code")
    candidates.append("MUTATED")
    assert select_reviewer_candidates("complex_code") == ["CODEX", "CLAUDE"]


def test_validate_rework_response_requires_every_field():
    ok, errors = validate_rework_response({
        "problems_found": ["wrong arity"], "rework_instructions": "fix the signature",
        "allowed_paths": ["src/sample.py"], "required_tests": ["server/tests/test_x.py"],
        "risks": []})
    assert ok and errors == []
    ok, errors = validate_rework_response({"problems_found": ["x"]})
    assert ok is False and len(errors) == 4  # every other required field is missing


def test_reject_routes_to_available_preferred_reviewer_codex(tmp_path, monkeypatch):
    orch, project, task_id, calls = setup_rejected_task(tmp_path, monkeypatch, patch_content="VALUE = 2\n")
    codex = MockProviderAdapter("CODEX", "AVAILABLE", result={
        "problems_found": ["wrong value"], "rework_instructions": "use VALUE = 3, not 2",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    claude = MockProviderAdapter("CLAUDE", "AVAILABLE")
    connector = ProviderConnectorV1(orch, {"CODEX": codex, "CLAUDE": claude})

    record = connector.request_review(task_id, "human rejected: wrong value")
    assert codex.calls and not claude.calls  # preference respected: Codex tried first and used
    assert record["state"] == "QUEUED"  # handed back to the local worker, never completed here
    assert record["action_params"]["rework_instructions"]
    events = [e["event_type"] for e in orch.ledger.read_for_task(task_id)]
    assert "HUMAN_REJECTED" in events and "REVIEW_COMPLETED" in events
    assert "REWORK_INSTRUCTIONS_RECEIVED" in events

    # The local worker retries with the reviewer's feedback and succeeds.
    record = orch.process_task(task_id)
    assert len(calls) == 2  # original attempt + the reworked attempt
    assert "use VALUE = 3" in calls[-1]["prompt_seen"]
    assert record["state"] == "WAITING_APPROVAL"
    assert record["proposed_patch"]["changes"][0]["content"] == "VALUE = 2\n"


def test_codex_exhausted_falls_back_to_claude_not_blocked(tmp_path, monkeypatch):
    # The exact principle the user asked for: "Codex preferito" must never
    # mean "task blocked if Codex is exhausted".
    orch, project, task_id, calls = setup_rejected_task(tmp_path, monkeypatch)
    codex = MockProviderAdapter("CODEX", "EXHAUSTED")
    claude = MockProviderAdapter("CLAUDE", "AVAILABLE", result={
        "problems_found": [], "rework_instructions": "looks fine, just re-run tests",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    connector = ProviderConnectorV1(orch, {"CODEX": codex, "CLAUDE": claude})

    record = connector.request_review(task_id, "human rejected")
    assert claude.calls  # Claude was used
    assert record["state"] == "QUEUED"
    assert record["escalation"]["target"] == "CLAUDE"


def test_both_reviewers_unavailable_parks_without_losing_state(tmp_path, monkeypatch):
    orch, project, task_id, calls = setup_rejected_task(tmp_path, monkeypatch)
    codex = MockProviderAdapter("CODEX", "EXHAUSTED")
    claude = MockProviderAdapter("CLAUDE", "OFFLINE")
    connector = ProviderConnectorV1(orch, {"CODEX": codex, "CLAUDE": claude})

    record = connector.request_review(task_id, "human rejected")
    assert record["state"] == "WAITING_REVIEW_PROVIDER"
    assert codex.calls == [] and claude.calls == []  # nobody was actually invoked
    assert record["escalation"]["candidates"] == ["CODEX", "CLAUDE"]
    assert record["escalation"]["candidate_states"] == {"CODEX": "EXHAUSTED", "CLAUDE": "OFFLINE"}
    # Nothing is lost: the original rejected patch and its verifier result
    # are still right there, ready for the eventual review.
    assert record["proposed_patch"]["changes"][0]["path"] == "src/sample.py"
    events = [e["event_type"] for e in orch.ledger.read_for_task(task_id)]
    assert "WAITING_REVIEW_PROVIDER" in events

    # A poll while still nobody is available is pure bookkeeping - no state
    # change, no loss.
    assert connector.run_once() is False
    record = orch.queue.get(task_id)
    assert record["state"] == "WAITING_REVIEW_PROVIDER"
    assert record["proposed_patch"]["changes"][0]["path"] == "src/sample.py"


def test_resumes_automatically_once_a_reviewer_becomes_available(tmp_path, monkeypatch):
    orch, project, task_id, calls = setup_rejected_task(tmp_path, monkeypatch)
    codex = MockProviderAdapter("CODEX", "EXHAUSTED")
    claude = MockProviderAdapter("CLAUDE", "OFFLINE", result={
        "problems_found": ["x"], "rework_instructions": "fix x",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    connector = ProviderConnectorV1(orch, {"CODEX": codex, "CLAUDE": claude})
    connector.request_review(task_id, "human rejected")
    assert orch.queue.get(task_id)["state"] == "WAITING_REVIEW_PROVIDER"

    claude._state = "AVAILABLE"  # the provider comes back - no human action
    advanced = connector.run_once()
    assert advanced is True
    record = orch.queue.get(task_id)
    assert record["state"] == "QUEUED"
    assert claude.calls
    events = [e["event_type"] for e in orch.ledger.read_for_task(task_id)]
    assert "REVIEW_PROVIDER_RESUMED" in events


def test_proactive_notification_on_wait_and_on_resume(tmp_path, monkeypatch):
    orch, project, task_id, calls = setup_rejected_task(tmp_path, monkeypatch)
    codex = MockProviderAdapter("CODEX", "EXHAUSTED")
    claude = MockProviderAdapter("CLAUDE", "OFFLINE", result={
        "problems_found": [], "rework_instructions": "retry", "allowed_paths": ["src/sample.py"],
        "required_tests": [], "risks": []})
    pushed = []
    connector = ProviderConnectorV1(orch, {"CODEX": codex, "CLAUDE": claude},
                                    telegram_notifier=lambda chat_id, response: pushed.append(
                                        (chat_id, response)))
    connector.request_review(task_id, "human rejected")
    assert len(pushed) == 1
    chat_id, response = pushed[0]
    assert chat_id == "42"  # from manifest()'s created_by="jarvis:42"
    assert response["status"] == "WAITING_REVIEW_PROVIDER"
    assert "Codex" in response["summary"] or "CODEX" in response["summary"]

    claude._state = "AVAILABLE"
    connector.run_once()
    assert len(pushed) == 2
    assert pushed[1][1]["status"] == "REVIEW_PROVIDER_RESUMED"


def test_notifier_failure_never_breaks_the_state_machine(tmp_path, monkeypatch):
    orch, project, task_id, calls = setup_rejected_task(tmp_path, monkeypatch)
    codex = MockProviderAdapter("CODEX", "OFFLINE")
    claude = MockProviderAdapter("CLAUDE", "OFFLINE")
    def broken_notifier(chat_id, response):
        raise RuntimeError("Telegram is down")
    connector = ProviderConnectorV1(orch, {"CODEX": codex, "CLAUDE": claude},
                                    telegram_notifier=broken_notifier)
    record = connector.request_review(task_id, "human rejected")
    assert record["state"] == "WAITING_REVIEW_PROVIDER"  # unaffected by the notifier raising


def test_malformed_reviewer_response_does_not_falsely_complete(tmp_path, monkeypatch):
    orch, project, task_id, calls = setup_rejected_task(tmp_path, monkeypatch)
    codex = MockProviderAdapter("CODEX", "AVAILABLE", result={"summary": "not the review shape"})
    connector = ProviderConnectorV1(orch, {"CODEX": codex, "CLAUDE": OfflineProviderAdapter("CLAUDE")})
    record = connector.request_review(task_id, "human rejected")
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["provider_execution"]["status"] == "VERIFICATION_FAILED"
    # Never silently treated as COMPLETED/approved - and never loses the
    # original patch while retrying.
    assert record["proposed_patch"]["changes"][0]["path"] == "src/sample.py"


def test_non_coding_rejection_keeps_the_original_failed_dead_end(tmp_path):
    # NEXUS Dynamic Specialist Review is additive, scoped to
    # conversational_programming: every other rejected task must behave
    # exactly as before (regression guard for the pre-existing contract
    # test in test_jarvis_access_layer_v1.py).
    orch = Orchestrator(tmp_path / "queue.json", tmp_path / "ledger.jsonl")
    value = manifest(task_id="TASK_NON_CODE", work_type="business_analysis")
    orch.submit(value, action="jarvis_task", action_params={})
    orch.queue.transition("TASK_NON_CODE", "RUNNING")
    orch.queue.transition("TASK_NON_CODE", "WAITING_APPROVAL")
    record = orch.queue.get("TASK_NON_CODE")
    assert record.get("action") != "conversational_programming"
    # No ProviderConnectorV1/request_review ever gets called for this
    # record by service.py's approval() when action != conversational_programming
    # or no connector is wired - the queue transition path itself is identical
    # to before this feature existed.
    orch.queue.transition("TASK_NON_CODE", "FAILED")
    assert orch.queue.get("TASK_NON_CODE")["state"] == "FAILED"
