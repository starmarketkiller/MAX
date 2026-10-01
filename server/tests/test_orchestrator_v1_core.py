"""Test di regressione per il NEXUS Orchestrator V1 Core
(server/orchestrator_v1/core/). Usa TaskQueue/EventLedger con path
temporanei (mai lo stato reale di runtime_state/) per essere indipendente
dall'ordine di esecuzione di altri test/run manuali."""
import os
import sys
import tempfile

ORCH_DIR = os.path.join(os.path.dirname(__file__), "..", "orchestrator_v1")
sys.path.insert(0, os.path.abspath(ORCH_DIR))

from core.task_queue import TaskQueue, new_task_id  # noqa: E402
from core.ledger import EventLedger  # noqa: E402
from core.capability import find_capable_agents, check_agent_for_task, load_registry  # noqa: E402
from core.router import route  # noqa: E402
from core.retry_escalation import classify_failure, decide_escalation_target  # noqa: E402
from core.result_packet import compute_confidence  # noqa: E402
from core.orchestrator import Orchestrator, LocalTaskHandler, VerifyResult, ApplyResult  # noqa: E402


def _manifest(task_id, **kw):
    m = {
        "task_id": task_id, "title": "t", "objective": "o", "task_type": "MAINTENANCE",
        "priority": "NORMAL", "risk_level": "A0", "scientific_risk": "NONE", "code_risk": "NONE",
        "financial_risk": "NONE", "required_capabilities": ["log_parsing"],
        "deterministic_tools_available": True, "repo_scope": "server/",
        "files_allowed": ["server/*"], "files_forbidden": ["MQL5/*"], "dependencies": [],
        "blockers": [], "expected_artifacts": [], "success_criteria": ["ok"],
        "verifier": "v.py", "estimated_complexity": "TRIVIAL", "estimated_runtime": "1m",
        "premium_allowed": False, "preferred_executor": "TIER0_DETERMINISTIC",
        "fallback_executors": [], "approval_required": "AUTO", "created_by": "test",
        "created_at": "2026-09-28T00:00:00Z", "tenant_id": "tenant-1", "account_scope_id": None,
    }
    m.update(kw)
    return m


def _tmp_orch():
    d = tempfile.mkdtemp()
    return Orchestrator(queue_path=os.path.join(d, "q.json"), ledger_path=os.path.join(d, "l.jsonl"))


def test_task_queue_rejects_invalid_manifest():
    d = tempfile.mkdtemp()
    tq = TaskQueue(path=os.path.join(d, "q.json"))
    try:
        tq.submit({"task_id": "x"})
        assert False, "doveva sollevare AssertionError per manifest incompleto"
    except AssertionError:
        pass


def test_task_queue_transition_fail_closed():
    d = tempfile.mkdtemp()
    tq = TaskQueue(path=os.path.join(d, "q.json"))
    rec = tq.submit(_manifest(new_task_id()))
    try:
        tq.transition(rec["task_id"], "COMPLETED")  # CREATED -> COMPLETED non permesso
        assert False, "transizione non permessa doveva fallire"
    except AssertionError:
        pass


def test_ledger_is_append_only_and_schema_valid():
    d = tempfile.mkdtemp()
    el = EventLedger(path=os.path.join(d, "l.jsonl"))
    el.append("TASK_CREATED", "T1", {"x": 1})
    el.append("FILE_READ", "T1", {"files": ["a.py"]})
    events = el.read_all()
    assert len(events) == 2
    assert events[0]["event_type"] == "TASK_CREATED"
    assert all("event_id" in e and "timestamp" in e for e in events)


def test_capability_enforcement_blocks_scientific_risk():
    m = _manifest(new_task_id(), task_type="CODE", scientific_risk="HIGH",
                 required_capabilities=["small_python_functions"])
    agents = find_capable_agents(m)
    assert agents == [], "un task scientific_risk=HIGH non deve mai matchare un agente locale"


def test_capability_enforcement_allows_demonstrated_capability():
    m = _manifest(new_task_id(), task_type="CODE", required_capabilities=["small_python_functions"])
    agents = find_capable_agents(m)
    assert any(a["agent_id"] == "LOCAL_STRONG_MINISTRAL3B" for a in agents)


def test_router_prefers_tier0_when_deterministic_action_present():
    record = {"manifest": _manifest(new_task_id()), "action": "run_pytest"}
    decision = route(record)
    assert decision.tier == "TIER0_DETERMINISTIC"


def test_router_escalates_scientific_risk_to_claude():
    m = _manifest(new_task_id(), scientific_risk="HIGH")
    record = {"manifest": m, "action": None}
    decision = route(record)
    assert decision.tier == "ESCALATION_REQUIRED"
    assert decision.executor == "TIER3_CLAUDE"


def test_retry_escalation_classifies_timeout_as_environment():
    assert classify_failure(["Read timed out (read timeout=180)"]) == "ENVIRONMENT"


def test_retry_escalation_classifies_import_error_as_tooling():
    assert classify_failure(["ModuleNotFoundError: no module named x"]) == "TOOLING"


def test_deterministic_remediation_uses_result_packet_tier_enum():
    manifest = _manifest("TASK_REMEDIATION_ENUM")
    assert decide_escalation_target("ENVIRONMENT", manifest) == "TIER0_DETERMINISTIC"
    assert decide_escalation_target("TOOLING", manifest) == "TIER0_DETERMINISTIC"


def test_retry_escalation_never_recommends_second_silent_retry():
    from core.retry_escalation import RETRY_MAX_ATTEMPTS
    assert RETRY_MAX_ATTEMPTS == 1


def test_confidence_high_requires_all_six_signals():
    confidence, signals = compute_confidence(
        verifier_ran=True, verifier_passed=True, tests_ran=True, tests_passed=1, tests_failed=0,
        expected_artifacts=["a.json"], artifacts_created=["a.json"], schema_valid=True,
        provenance_ok=True, contradicts_canonical=False)
    assert confidence == "HIGH"
    assert all(signals.values())


def test_confidence_drops_to_medium_if_one_signal_missing():
    confidence, signals = compute_confidence(
        verifier_ran=True, verifier_passed=True, tests_ran=True, tests_passed=1, tests_failed=0,
        expected_artifacts=["a.json"], artifacts_created=[], schema_valid=True,
        provenance_ok=True, contradicts_canonical=False)
    assert confidence == "MEDIUM"
    assert signals["artifacts_complete"] is False


def test_confidence_unknown_if_verifier_never_ran():
    confidence, _ = compute_confidence(
        verifier_ran=False, verifier_passed=False, tests_ran=False, tests_passed=0,
        tests_failed=0, expected_artifacts=[], artifacts_created=[], schema_valid=False,
        provenance_ok=False, contradicts_canonical=False)
    assert confidence == "UNKNOWN"


def test_orchestrator_deterministic_task_completes():
    orch = _tmp_orch()
    m = _manifest("TASK_DET_TEST")
    orch.submit(m, action="check_files_exist",
              action_params={"paths": ["contracts/task-manifest.schema.json"]})
    rec = orch.process_task("TASK_DET_TEST")
    assert rec["state"] == "COMPLETED"
    assert rec["result_packet"]["confidence"] == "HIGH"


def test_orchestrator_approval_boundary_blocks_real_file_writes(monkeypatch):
    """Un handler che dichiara touches_real_repo_files=True con
    approval_required != AUTO DEVE fermarsi a WAITING_APPROVAL, mai
    COMPLETED - questo e' IL test che garantisce che l'Orchestrator non
    scriva mai un file reale del repository senza revisione."""
    orch = _tmp_orch()
    # This test exercises the approval boundary after a successful local
    # proposal. It must not depend on whether Ollama happens to be installed
    # on the host running the suite (GitHub Linux has no local provider).
    monkeypatch.setattr(
        "core.orchestrator.ollama_worker.call_local_model",
        lambda prompt, model: {
            "success": True,
            "model": model,
            "response_text": '{"ok": true}',
            "wall_seconds": 0.0,
            "error": None,
        },
    )

    class FakeRealFileHandler(LocalTaskHandler):
        def build_prompt(self, task_record):
            return "irrilevante per questo test"

        def verify(self, task_record, response_text):
            return VerifyResult(passed=True, parsed_output={"ok": True})

        def apply(self, task_record, vr):
            return ApplyResult(files_changed=[], artifacts_created=["some/real/file.py"],
                              touches_real_repo_files=True, proposal_only=True)

    orch.register_local_handler("fake_real_file_action", FakeRealFileHandler())
    m = _manifest("TASK_REVIEW_TEST", task_type="CODE",
                required_capabilities=["small_python_functions"], approval_required="REVIEW_REQUIRED")
    orch.submit(m, action="fake_real_file_action", action_params={})
    rec = orch.process_task("TASK_REVIEW_TEST")
    assert rec["state"] == "WAITING_APPROVAL"
    assert rec["result_packet"]["decision"] == "PATCH_READY_AWAITING_APPROVAL"


def test_orchestrator_escalation_builds_valid_context_packet():
    orch = _tmp_orch()

    class AlwaysFail(LocalTaskHandler):
        def build_prompt(self, task_record):
            return "x"

        def verify(self, task_record, response_text):
            return VerifyResult(passed=False, errors=["sempre sbagliato"], is_logic_error=True)

        def apply(self, task_record, vr):
            raise AssertionError("non raggiungibile")

    orch.register_local_handler("always_fail_test", AlwaysFail())
    m = _manifest("TASK_ESCALATE_TEST", task_type="CODE",
                required_capabilities=["small_python_functions"])
    orch.submit(m, action="always_fail_test", action_params={})
    rec = orch.process_task("TASK_ESCALATE_TEST")
    assert rec["state"] == "ESCALATION_REQUIRED"
    ctx = rec["escalation"]["context_packet"]
    assert ctx["objective"] == "o"
    assert len(ctx["previous_attempts"]) >= 1


def test_agent_registry_unchanged_since_bakeoff():
    """I 2 agenti Ministral del bake-off restano invariati - NEXUS TASK
    #0008 ha aggiunto 3 record di READINESS (Claude/Codex/ChatGPT) accanto
    a questi, mai selezionabili in automatico (find_capable_agents li
    esclude sempre per availability/quota_state - vedi
    test_review_pipeline_v1.py)."""
    registry = load_registry()
    agent_ids = {a["agent_id"] for a in registry["agents"]}
    assert {"LOCAL_FAST_MINISTRAL3B", "LOCAL_STRONG_MINISTRAL3B"} <= agent_ids
    for agent_id in ("LOCAL_FAST_MINISTRAL3B", "LOCAL_STRONG_MINISTRAL3B"):
        agent = next(a for a in registry["agents"] if a["agent_id"] == agent_id)
        assert agent["local_or_remote"] == "LOCAL"
        assert agent["cost_class"] == "LOCAL_COMPUTE"
