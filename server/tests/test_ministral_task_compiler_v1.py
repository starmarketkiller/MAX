"""MINISTRAL_TASK_COMPILER_V1.

Mirrors the exact test pattern already used for FreeCodingWorkerHandler
(tests/test_free_coding_worker_routing_v1.py) - a bare Orchestrator with
core.orchestrator.ollama_worker.call_local_model monkeypatched, no real
Ollama needed for the automated suite. Real smoke tests against the live
local Ministral are run separately (not in CI) and reported alongside this
diff.
"""
import json

from jarvis_v1 import delegation_report
from jarvis_v1 import ministral_task_compiler as compiler
from jarvis_v1.local_bounded_task_handler import BoundedLocalTaskHandler  # noqa: E402 - sets up sys.path for core.*

from core.orchestrator import Orchestrator  # noqa: E402
from core.router import route  # noqa: E402


def setup_orchestrator(tmp_path):
    project = tmp_path / "project"
    (project / "src").mkdir(parents=True)
    (project / "src" / "sample.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    orch = Orchestrator(tmp_path / "queue.json", tmp_path / "ledger.jsonl")
    handler = BoundedLocalTaskHandler(project_root=project)
    for template_id in compiler.TEMPLATES:
        orch.register_local_handler(template_id, handler)
    return orch, project


def submit_inspection(orch, *, verifier_feedback=None, relevant_paths=("src/sample.py",)):
    manifest, action, action_params = compiler.compile_task(
        "repo_inspection_v1", goal="Capire cosa fa src/sample.py",
        relevant_paths=list(relevant_paths), created_by="jarvis:claude_supervisor",
        verifier_feedback=verifier_feedback)
    orch.submit(manifest, action=action, action_params=action_params)
    return manifest["task_id"]


def _valid_response():
    return json.dumps({
        "summary": "Il file definisce una funzione add che somma due numeri.",
        "findings": ["Funzione add(a, b) semplice, nessuna validazione input."],
        "risks": [],
    })


def mock_ministral(monkeypatch, responses):
    """responses: list of either a response_text string, or an Exception-like
    dict {"success": False, "error": ...} - consumed one per call."""
    calls = []

    def invoke(prompt, model):
        calls.append({"prompt": prompt, "model": model})
        item = responses[min(len(calls) - 1, len(responses) - 1)]
        if isinstance(item, dict):
            return {"success": False, "model": model, "response_text": None,
                    "error": item.get("error", "mock failure"), "wall_seconds": 0.1}
        return {"success": True, "model": model, "response_text": item,
                "error": None, "wall_seconds": 0.1}
    monkeypatch.setattr("core.orchestrator.ollama_worker.call_local_model", invoke)
    return calls


# 1. semplice repo inspection -> Ministral, successo -----------------------
def test_repo_inspection_success_completes_without_approval(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    calls = mock_ministral(monkeypatch, [_valid_response()])
    task_id = submit_inspection(orch)
    assert route(orch.queue.get(task_id)).executor == "LOCAL_FAST_MINISTRAL3B"
    record = orch.process_task(task_id)
    assert len(calls) == 1
    # read_only => touches_real_repo_files=False => no approval gate at all,
    # never WAITING_APPROVAL for this template (see point 8 below).
    assert record["state"] == "COMPLETED"
    assert record["result_packet"]["decision"] == "COMPLETED"
    assert "add(a, b)" in calls[0]["prompt"] or "def add" in calls[0]["prompt"]


# 6. output malformed -> reject -----------------------------------------
def test_malformed_json_output_is_rejected_not_applied(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    mock_ministral(monkeypatch, ["questo non e' JSON per niente {{{"])
    task_id = submit_inspection(orch)
    record = orch.process_task(task_id)
    # One local retry (RETRY_MAX_ATTEMPTS=1) then escalation - never COMPLETED.
    assert record["state"] in ("ESCALATION_REQUIRED", "WAITING_PROVIDER", "FAILED")
    assert record["state"] != "COMPLETED"


def test_output_with_extra_or_missing_keys_is_rejected(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    bad = json.dumps({"summary": "ok", "findings": []})  # missing risks
    mock_ministral(monkeypatch, [bad, bad])
    task_id = submit_inspection(orch)
    record = orch.process_task(task_id)
    assert record["state"] != "COMPLETED"


def test_output_exceeding_the_bounded_limits_is_rejected(tmp_path, monkeypatch):
    # A model that ignores "massimo 5"/"massimo 3" and rambles must be
    # caught, not silently accepted - this is itself a useful FAILED signal
    # for delegation_report, not only a latency guard.
    orch, project = setup_orchestrator(tmp_path)
    rambling = json.dumps({"summary": "ok", "findings": [f"item {i}" for i in range(10)], "risks": []})
    mock_ministral(monkeypatch, [rambling, rambling])
    task_id = submit_inspection(orch)
    record = orch.process_task(task_id)
    assert record["state"] != "COMPLETED"


def test_findings_as_objects_instead_of_strings_is_rejected(tmp_path, monkeypatch):
    # Guards against a regression back to the old {path, note} shape.
    orch, project = setup_orchestrator(tmp_path)
    wrong_shape = json.dumps({"summary": "ok", "findings": [{"path": "x", "note": "y"}], "risks": []})
    mock_ministral(monkeypatch, [wrong_shape, wrong_shape])
    task_id = submit_inspection(orch)
    record = orch.process_task(task_id)
    assert record["state"] != "COMPLETED"


# 3. test failure -> Claude corregge il prompt -> Ministral retry ----------
def test_verifier_feedback_reaches_the_prompt_on_a_fresh_delegation(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    calls = mock_ministral(monkeypatch, [_valid_response()])
    task_id = submit_inspection(
        orch, verifier_feedback="Il tentativo precedente ha inventato un path fuori allowlist. "
                                "Usa SOLO i path elencati in files.")
    orch.process_task(task_id)
    assert "tentativo precedente" in calls[0]["prompt"].lower()


# 5. verifier rejection ripetuta -> escalation (no infinite loop) ---------
def test_repeated_failure_escalates_and_never_loops_forever(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    calls = mock_ministral(monkeypatch, ["not json"])
    task_id = submit_inspection(orch)
    record = orch.process_task(task_id)
    # Discovered empirically, not assumed: retry_escalation.py already tries
    # LOCAL_FAST_MINISTRAL3B twice (RETRY_MAX_ATTEMPTS=1 => original + 1
    # retry), then - since this template also matches LOCAL_STRONG_MINISTRAL3B
    # - escalates ONE MORE local tier (TIER2_LOCAL_STRONG_RETRY) for another
    # 2 attempts, before finally giving up on local execution. 4 calls total
    # is the real bounded ceiling here, not 2 - still strictly bounded, never
    # infinite, just two local tiers instead of one.
    assert len(calls) == 4
    assert record["state"] not in ("RUNNING", "QUEUED")
    assert record["state"] == "ESCALATION_REQUIRED"


# 4. task troppo complessa / capability insufficiente -> mai eseguita localmente
def test_capability_mismatch_never_calls_ministral_at_all(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    calls = mock_ministral(monkeypatch, [_valid_response()])
    manifest, action, action_params = compiler.compile_task(
        "repo_inspection_v1", goal="x", relevant_paths=["src/sample.py"],
        created_by="jarvis:claude_supervisor")
    manifest["required_capabilities"] = ["multi_file_refactor"]  # nobody has this
    orch.submit(manifest, action=action, action_params=action_params)
    record = orch.process_task(manifest["task_id"])
    assert calls == []
    assert record["state"] == "ESCALATION_REQUIRED"


# 7/8. nessuna doppia esecuzione, nessun bypass approval -------------------
def test_read_only_template_never_reaches_waiting_approval(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    mock_ministral(monkeypatch, [_valid_response()])
    task_id = submit_inspection(orch)
    record = orch.process_task(task_id)
    # Nothing was mutated (apply() always sets touches_real_repo_files=False
    # for a read_only template) - there is no patch to approve, so this is
    # not a bypass of the real approval gate, it never applies here.
    assert record["state"] != "WAITING_APPROVAL"
    assert record["result_packet"]["push_status"] == "NOT_APPLICABLE"


def test_write_capable_template_is_explicitly_refused_not_silently_allowed(tmp_path, monkeypatch):
    bad_template = compiler.MinistralTaskTemplate(
        template_id="_test_write_template", title="x", task_type="DOCUMENTATION",
        work_type="routine_summary", instructions="x", output_contract={"summary": "x"},
        required_capabilities=("summaries",), read_only=False)
    monkeypatch.setitem(compiler.TEMPLATES, "_test_write_template", bad_template)
    handler = BoundedLocalTaskHandler(project_root=tmp_path)
    record = {"action": "_test_write_template", "action_params": {},
             "manifest": {"files_allowed": []}}
    result = handler.verify(record, json.dumps({"summary": "x"}))
    assert result.passed is False


# 9. lineage completo nel Ledger -------------------------------------------
def test_delegation_report_reconstructs_full_lineage(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    mock_ministral(monkeypatch, [_valid_response()])
    task_id = submit_inspection(orch)
    orch.process_task(task_id)
    rows = delegation_report.delegation_outcomes_report(orch.ledger, orch.queue)
    assert len(rows) == 1
    row = rows[0]
    assert row["task_id"] == task_id
    assert row["template_id"] == "repo_inspection_v1"
    assert row["task_type"] == "DOCUMENTATION"
    assert row["work_type"] == "routine_summary"
    assert row["model"] == "ministral-3:3b"
    assert row["verifier_result"] == "PASSED"
    assert row["final_outcome"] == "COMPLETED"
    assert row["retry_count"] == 0
    assert row["latency_s"] is not None


def test_delegation_report_ignores_non_compiler_tasks(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    manifest = {
        "task_id": "TASK_UNRELATED", "title": "x", "objective": "x", "task_type": "CODE",
        "work_type": "complex_code", "priority": "NORMAL", "risk_level": "A1",
        "scientific_risk": "NONE", "code_risk": "HIGH", "financial_risk": "NONE",
        "required_capabilities": ["small_python_functions"], "deterministic_tools_available": False,
        "repo_scope": "task-scoped", "files_allowed": ["src/sample.py"],
        "files_forbidden": [".env"], "dependencies": [], "blockers": [],
        "expected_artifacts": ["RESULT_PACKET_V1"], "success_criteria": ["x"],
        "verifier": "x", "estimated_complexity": "SMALL", "estimated_runtime": "1m",
        "premium_allowed": False, "preferred_executor": "TIER1_LOCAL_CHEAP",
        "fallback_executors": [], "approval_required": "REVIEW_REQUIRED",
        "created_by": "test", "created_at": "2026-01-01T00:00:00+00:00",
        "tenant_id": "tenant-1", "account_scope_id": None,
    }
    orch.submit(manifest, action="some_other_action", action_params={})
    rows = delegation_report.delegation_outcomes_report(orch.ledger, orch.queue)
    assert rows == []


def test_delegation_report_counts_retries(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    mock_ministral(monkeypatch, ["not json", _valid_response()])
    task_id = submit_inspection(orch)
    orch.process_task(task_id)
    rows = delegation_report.delegation_outcomes_report(orch.ledger, orch.queue)
    assert rows[0]["retry_count"] == 1
    assert rows[0]["final_outcome"] == "COMPLETED"


# JarvisService wiring ------------------------------------------------------
def test_jarvis_service_registers_every_compiler_template(tmp_path):
    from jarvis_v1.service import JarvisService
    svc = JarvisService(str(tmp_path / "q.json"), str(tmp_path / "l.jsonl"), str(tmp_path / "c.json"))
    for template_id in compiler.TEMPLATES:
        assert template_id in svc.orchestrator.local_handlers


def test_jarvis_service_delegate_to_ministral_queues_a_real_task(tmp_path, monkeypatch):
    from jarvis_v1.service import JarvisService
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    svc = JarvisService(str(tmp_path / "q.json"), str(tmp_path / "l.jsonl"), str(tmp_path / "c.json"))
    task_id = svc.delegate_to_ministral("repo_inspection_v1", goal="x",
                                        relevant_paths=["server/app.py"])
    record = svc.queue.get(task_id)
    assert record["action"] == "repo_inspection_v1"
    assert record["state"] == "QUEUED"


# PERSIST_MINISTRAL_BOUNDED_OUTPUT_V1 ---------------------------------------
# 1. output valido -> persiste nel result packet, recuperabile end-to-end
def test_valid_output_persists_and_is_recoverable(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    mock_ministral(monkeypatch, [_valid_response()])
    task_id = submit_inspection(orch)
    record = orch.process_task(task_id)
    assert record["state"] == "COMPLETED"
    recovered = delegation_report.read_bounded_output(task_id, orch.queue)
    assert recovered is not None
    assert recovered["template_id"] == "repo_inspection_v1"
    assert recovered["task_id"] == task_id
    assert "add" in recovered["summary"].lower() or "somma" in recovered["summary"].lower()
    assert recovered["findings"] == ["Funzione add(a, b) semplice, nessuna validazione input."]
    assert recovered["risks"] == []
    assert recovered["executor"] == "LOCAL_FAST_MINISTRAL3B"
    assert recovered["verifier_passed"] is True


# 2. output invalido -> mai persistito come risultato valido
def test_invalid_output_is_never_persisted(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    mock_ministral(monkeypatch, ["not json at all", "still not json"])
    task_id = submit_inspection(orch)
    record = orch.process_task(task_id)
    assert record["state"] != "COMPLETED"
    assert delegation_report.read_bounded_output(task_id, orch.queue) is None


# 3. retry riuscito -> si conserva SOLO il risultato finale valido
def test_successful_retry_persists_only_the_final_valid_output(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    bad_summary = "scartato - questo testo non deve mai apparire nel risultato persistito"
    good = json.dumps({"summary": "Sintesi finale corretta.",
                       "findings": ["trovato dopo retry"], "risks": []})
    mock_ministral(monkeypatch, [f"{bad_summary} {{{{", good])  # 1st malformed, 2nd valid
    task_id = submit_inspection(orch)
    record = orch.process_task(task_id)
    assert record["state"] == "COMPLETED"
    recovered = delegation_report.read_bounded_output(task_id, orch.queue)
    assert recovered["summary"] == "Sintesi finale corretta."
    assert bad_summary not in str(recovered)


def test_non_compiler_task_has_no_bounded_output_to_recover(tmp_path, monkeypatch):
    orch, project = setup_orchestrator(tmp_path)
    mock_ministral(monkeypatch, [_valid_response()])
    task_id = submit_inspection(orch)
    orch.process_task(task_id)
    # A record whose artifacts_created never contains the prefix (e.g. a
    # plain file-path artifact, as FreeCodingWorkerHandler produces) must
    # decode to None, not raise or silently return garbage.
    record = orch.queue.get(task_id)
    record["result_packet"]["artifacts_created"] = ["/some/workspace/path", "src/sample.py"]
    assert compiler.decode_bounded_output(record["result_packet"]["artifacts_created"]) is None
