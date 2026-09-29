"""Test per la Multi-Agent Review & Finalization Pipeline V1 (NEXUS TASK
#0008). Copre: WORK_PRODUCT_V1 fail-closed, Review Matrix, Premium Budget
Policy, Specialist Registry, Finalization Gate, Confidence Model, e i 5
acceptance test A-E richiesti dalla spec (Test B usa il registry REALE:
Claude e' oggi OFFLINE/NOT_CONFIGURED in questo repo - nessun connector
automatico esiste - quindi esercita davvero il ramo
ESCALATION_READY_FOR_MANUAL_DELIVERY; il ramo 'Claude disponibile' e'
comunque testato con un registry fittizio per provare che la logica di
merge/finalizzazione funziona quando un provider e' realmente raggiungibile)."""
import json
import os
import sys

REVIEW_DIR = os.path.join(os.path.dirname(__file__), "..", "review_pipeline_v1")
ORCH_DIR = os.path.join(os.path.dirname(__file__), "..", "orchestrator_v1")
CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "contracts")
sys.path.insert(0, os.path.abspath(REVIEW_DIR))
sys.path.insert(0, os.path.abspath(ORCH_DIR))

from nxs_schema_validator import validate  # noqa: E402
from work_product import (STATES, ALLOWED_TRANSITIONS, MAX_REVIEW_LOOPS,  # noqa: E402
                          validate_transition, build_lifecycle_definition)
from review_matrix import get_matrix_entry, build_review_matrix, REVIEW_MATRIX  # noqa: E402
from premium_budget_policy import allow_premium, build_premium_budget_policy  # noqa: E402
from specialist_registry import select_specialist, find_specialists  # noqa: E402
from finalization_gate import check_finalization_gate, _scan_for_secrets  # noqa: E402
from confidence_model import derive_confidence  # noqa: E402
from review_engine import process_work_product  # noqa: E402
from jarvis_delivery import format_task_completed_summary, explain  # noqa: E402
from escalation import CLASSIFICATIONS, specialist_role_for_classification  # noqa: E402


def _load_schema(name):
    with open(os.path.join(CONTRACTS_DIR, name), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# WORK_PRODUCT_V1 lifecycle
# ---------------------------------------------------------------------------

def test_work_product_has_11_states_and_is_fail_closed():
    assert len(STATES) == 11
    assert ALLOWED_TRANSITIONS["DELIVERED"] == []
    ok, _ = validate_transition("DRAFT", "FINALIZED")
    assert ok is False
    ok, _ = validate_transition("DRAFT", "VERIFYING")
    assert ok is True


def test_work_product_lifecycle_definition_validates_against_schema():
    schema = _load_schema("work-product-lifecycle.schema.json")
    payload = build_lifecycle_definition()
    assert validate(payload, schema) == []


def test_max_review_loops_default_is_2():
    assert MAX_REVIEW_LOOPS == 2


# ---------------------------------------------------------------------------
# Review Matrix
# ---------------------------------------------------------------------------

def test_review_matrix_validates_against_schema():
    schema = _load_schema("review-matrix.schema.json")
    payload = build_review_matrix()
    assert validate(payload, schema) == []


def test_review_matrix_unrecognized_work_type_defaults_to_cautious_not_permissive():
    entry = get_matrix_entry("some_never_seen_work_type")
    assert entry["review_required"] is True
    assert entry["unrecognized_work_type"] is True


def test_review_matrix_high_risk_types_require_distinct_producer_reviewer():
    for work_type in ("scientific_research", "architecture_design", "deployment", "trading_critical"):
        assert REVIEW_MATRIX[work_type]["distinct_producer_reviewer_required"] is True


# ---------------------------------------------------------------------------
# Premium Budget Policy
# ---------------------------------------------------------------------------

def test_premium_budget_policy_validates_against_schema():
    schema = _load_schema("premium-budget-policy.schema.json")
    payload = build_premium_budget_policy()
    assert validate(payload, schema) == []


def test_free_only_never_allows_premium():
    allowed, _, _ = allow_premium("FREE_ONLY", local_attempt_failed=True, local_confidence="LOW",
                                 review_matrix_requires_review=True)
    assert allowed is False


def test_low_cost_requires_a_verified_local_failure_first():
    allowed_before, _, _ = allow_premium("LOW_COST", local_attempt_failed=False)
    allowed_after, _, _ = allow_premium("LOW_COST", local_attempt_failed=True)
    assert allowed_before is False
    assert allowed_after is True


def test_critical_review_always_requires_user_approval():
    _, requires_approval, _ = allow_premium("CRITICAL_REVIEW")
    assert requires_approval is True


def test_unknown_level_is_fail_closed():
    allowed, requires_approval, _ = allow_premium("NOT_A_REAL_LEVEL")
    assert allowed is False
    assert requires_approval is True


# ---------------------------------------------------------------------------
# Specialist Registry (usa il registry REALE del repo)
# ---------------------------------------------------------------------------

def test_specialist_registry_maps_known_providers_to_declared_roles():
    ministral = find_specialists("LOCAL_GENERALIST")
    assert any(a["agent_id"] == "LOCAL_FAST_MINISTRAL3B" for a in ministral)
    claude = find_specialists("SCIENTIFIC_RESEARCHER")
    assert any(a["agent_id"] == "CLAUDE_TIER3" for a in claude)
    codex = find_specialists("CODE_SPECIALIST")
    assert any(a["agent_id"] == "CODEX_TIER4" for a in codex)


def test_claude_is_honestly_not_usable_now_in_the_real_registry():
    """Nessuna integrazione automatica esiste oggi verso Claude - il
    registry deve dichiararlo, mai fingere disponibilita'."""
    chosen, status = select_specialist("SCIENTIFIC_RESEARCHER")
    assert chosen is None
    assert status["usable_now"] is False


def test_unavailable_provider_does_not_block_when_alternative_exists():
    fake_registry = {"agents": [
        {"agent_id": "A_EXHAUSTED", "specialist_role": "CODE_SPECIALIST", "availability": "ONLINE",
         "quota_state": "EXHAUSTED", "integration_status": "AVAILABLE", "cost_class": "CHEAP_PREMIUM"},
        {"agent_id": "A_OK", "specialist_role": "CODE_SPECIALIST", "availability": "ONLINE",
         "quota_state": "AVAILABLE", "integration_status": "AVAILABLE", "cost_class": "CHEAP_PREMIUM"},
    ]}
    chosen, status = select_specialist("CODE_SPECIALIST", registry=fake_registry)
    assert chosen["agent_id"] == "A_OK"
    assert status["usable_now"] is True


# ---------------------------------------------------------------------------
# Finalization Gate
# ---------------------------------------------------------------------------

def test_finalization_gate_rejects_secret_like_content():
    found = _scan_for_secrets({"text": "here is sk-abcdefghijklmnopqrstuvwxyz123456"})
    assert found


def test_finalization_gate_fails_closed_on_open_escalation():
    passed, failures = check_finalization_gate(
        work_product={"review_required": False, "blocked_reason": None}, verifier_passed=True,
        review_completed_if_required=True, open_escalation="TASK_X still escalated",
        provenance_complete=True, output_schema_errors=[], required_approvals_present=True,
        policy_violations=[], final_output={"ok": True})
    assert passed is False
    assert any("escalation" in f for f in failures)


def test_finalization_gate_passes_when_everything_clean():
    passed, failures = check_finalization_gate(
        work_product={"review_required": False, "blocked_reason": None}, verifier_passed=True,
        review_completed_if_required=True, open_escalation=None, provenance_complete=True,
        output_schema_errors=[], required_approvals_present=True, policy_violations=[],
        final_output={"ok": True})
    assert passed is True
    assert failures == []


# ---------------------------------------------------------------------------
# Confidence model
# ---------------------------------------------------------------------------

def test_confidence_is_never_high_if_verifier_did_not_pass():
    assert derive_confidence(verifier_passed=False, schema_valid=True) == "LOW"


def test_confidence_is_low_on_review_rejection():
    assert derive_confidence(verifier_passed=True, schema_valid=True,
                            review_decision="REJECT") == "LOW"


def test_confidence_can_reach_high_when_everything_checks_out():
    assert derive_confidence(verifier_passed=True, schema_valid=True, review_decision="APPROVE",
                            source_quality="HIGH", tests_all_passed=True,
                            unresolved_limitations=[]) == "HIGH"


# ---------------------------------------------------------------------------
# Escalation classification (estensione additiva di core/retry_escalation.py)
# ---------------------------------------------------------------------------

def test_strategic_ambiguity_classification_added_additively():
    assert "STRATEGIC_AMBIGUITY" in CLASSIFICATIONS
    assert specialist_role_for_classification("STRATEGIC_AMBIGUITY") == "STRATEGIC_GENERALIST"
    assert specialist_role_for_classification("COMPLEX_CODE_CHANGE") == "CODE_SPECIALIST"


# ---------------------------------------------------------------------------
# Acceptance tests A-E (end-to-end sul motore reale)
# ---------------------------------------------------------------------------

def test_A_local_only_finalizes_with_zero_premium_calls():
    def attempt_ok():
        return {"agent_id": "LOCAL_FAST_MINISTRAL3B", "specialist_role": "LOCAL_GENERALIST",
                "output": {"text": "riassunto"}, "verify_passed": True, "verify_errors": []}
    wp, frp, _ = process_work_product(task_id="TEST_A", work_type="routine_summary",
                                     attempts=[attempt_ok])
    assert wp["state"] == "DELIVERED"
    assert frp["premium_calls"] == 0


def test_B_local_failure_with_claude_unavailable_is_escalation_ready_for_manual_delivery():
    def attempt_fail():
        return {"agent_id": "LOCAL_FAST_MINISTRAL3B", "specialist_role": "LOCAL_GENERALIST",
                "output": {"text": "ipotesi incerta"}, "verify_passed": False,
                "verify_errors": ["claim non supportato da fonti"]}
    wp, frp, _ = process_work_product(task_id="TEST_B", work_type="scientific_research",
                                     attempts=[attempt_fail, attempt_fail])
    assert wp["state"] == "BLOCKED"
    assert "ESCALATION_READY_FOR_MANUAL_DELIVERY" in wp["blocked_reason"]
    assert frp is None


def test_B_local_failure_with_claude_available_merges_and_finalizes():
    fake_registry = {"agents": [
        {"agent_id": "CLAUDE_TIER3", "specialist_role": "SCIENTIFIC_RESEARCHER",
         "availability": "ONLINE", "quota_state": "AVAILABLE", "integration_status": "AVAILABLE",
         "cost_class": "EXPENSIVE_PREMIUM"},
    ]}

    def attempt_fail():
        return {"agent_id": "LOCAL_FAST_MINISTRAL3B", "specialist_role": "LOCAL_GENERALIST",
                "output": {"text": "ipotesi incerta"}, "verify_passed": False,
                "verify_errors": ["claim non supportato"]}

    def reviewer(_ctx):
        return {"reviewer": "CLAUDE_TIER3", "decision": "APPROVE", "issues_found": [],
                "required_changes": [], "accepted_claims": ["x"], "rejected_claims": [],
                "confidence": "HIGH", "source_refs": ["fonte1"], "needs_second_review": False,
                "merged_output": {"text": "ipotesi corretta"}}

    wp, frp, _ = process_work_product(task_id="TEST_B2", work_type="scientific_research",
                                     attempts=[attempt_fail, attempt_fail], review_fn=reviewer,
                                     registry=fake_registry, sources=["fonte1"])
    assert wp["state"] == "DELIVERED"
    assert frp["premium_calls"] == 1
    assert frp["premium_agents_used"] == ["CLAUDE_TIER3"]


def test_C_code_task_finalizes_via_deterministic_tests_no_review():
    def attempt_ok():
        return {"agent_id": "CODEX_TIER4", "specialist_role": "CODE_SPECIALIST",
                "output": {"diff": "def f(): return 1"}, "verify_passed": True, "verify_errors": []}
    wp, frp, _ = process_work_product(task_id="TEST_C", work_type="complex_code",
                                     attempts=[attempt_ok],
                                     tests={"ran": True, "passed": 5, "failed": 0})
    assert wp["state"] == "DELIVERED"
    assert frp["premium_calls"] == 0
    assert wp["reviewer"] is None


def test_D_reviewer_requests_revision_then_approves():
    fake_registry = {"agents": [
        {"agent_id": "CHATGPT_SPECIALIST", "specialist_role": "STRATEGIC_GENERALIST",
         "availability": "ONLINE", "quota_state": "AVAILABLE", "integration_status": "AVAILABLE",
         "cost_class": "CHEAP_PREMIUM"},
    ]}

    def attempt_ok():
        return {"agent_id": "LOCAL_FAST_MINISTRAL3B", "specialist_role": "LOCAL_GENERALIST",
                "output": {"text": "analisi v1"}, "verify_passed": True, "verify_errors": []}

    calls = {"n": 0}

    def reviewer(_ctx):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"reviewer": "CHATGPT_SPECIALIST", "decision": "REVISION_REQUIRED",
                    "issues_found": ["numero non giustificato"],
                    "required_changes": ["togliere il numero inventato"], "accepted_claims": [],
                    "rejected_claims": ["numero"], "confidence": "MEDIUM", "source_refs": [],
                    "needs_second_review": False, "merged_output": {"text": "analisi v1"}}
        return {"reviewer": "CHATGPT_SPECIALIST", "decision": "APPROVE", "issues_found": [],
                "required_changes": [], "accepted_claims": ["ok"], "rejected_claims": [],
                "confidence": "HIGH", "source_refs": [], "needs_second_review": False,
                "merged_output": {"text": "analisi v2 corretta"}}

    wp, frp, events = process_work_product(task_id="TEST_D", work_type="business_analysis",
                                          attempts=[attempt_ok], review_fn=reviewer,
                                          registry=fake_registry)
    assert wp["state"] == "DELIVERED"
    assert wp["revision_count"] == 1
    assert frp["changes_made_during_review"] == ["togliere il numero inventato"]
    assert events.count("REVIEW_COMPLETED") == 2


def test_E_reviewer_provider_exhausted_blocks_without_silent_bypass():
    fake_registry = {"agents": [
        {"agent_id": "CHATGPT_SPECIALIST", "specialist_role": "STRATEGIC_GENERALIST",
         "availability": "ONLINE", "quota_state": "EXHAUSTED", "integration_status": "AVAILABLE",
         "cost_class": "CHEAP_PREMIUM"},
    ]}

    def attempt_ok():
        return {"agent_id": "LOCAL_FAST_MINISTRAL3B", "specialist_role": "LOCAL_GENERALIST",
                "output": {"text": "analisi v1"}, "verify_passed": True, "verify_errors": []}

    wp, frp, _ = process_work_product(task_id="TEST_E", work_type="business_analysis",
                                     attempts=[attempt_ok], registry=fake_registry)
    assert wp["state"] == "BLOCKED"
    assert frp is None
    assert "non disponibile" in wp["blocked_reason"]


def test_max_review_loops_exceeded_blocks_instead_of_looping_forever():
    fake_registry = {"agents": [
        {"agent_id": "CHATGPT_SPECIALIST", "specialist_role": "STRATEGIC_GENERALIST",
         "availability": "ONLINE", "quota_state": "AVAILABLE", "integration_status": "AVAILABLE",
         "cost_class": "CHEAP_PREMIUM"},
    ]}

    def attempt_ok():
        return {"agent_id": "LOCAL_FAST_MINISTRAL3B", "specialist_role": "LOCAL_GENERALIST",
                "output": {"text": "v1"}, "verify_passed": True, "verify_errors": []}

    def always_revise(_ctx):
        return {"reviewer": "CHATGPT_SPECIALIST", "decision": "REVISION_REQUIRED",
                "issues_found": ["x"], "required_changes": ["fix"], "accepted_claims": [],
                "rejected_claims": [], "confidence": "LOW", "source_refs": [],
                "needs_second_review": False, "merged_output": {"text": "v_next"}}

    wp, frp, _ = process_work_product(task_id="TEST_LOOP", work_type="business_analysis",
                                     attempts=[attempt_ok], review_fn=always_revise,
                                     registry=fake_registry)
    assert wp["state"] == "BLOCKED"
    assert frp is None
    assert "MAX_REVIEW_LOOPS" in wp["blocked_reason"]


# ---------------------------------------------------------------------------
# Jarvis delivery
# ---------------------------------------------------------------------------

def test_jarvis_summary_never_shows_full_chain_of_work():
    def attempt_ok():
        return {"agent_id": "LOCAL_FAST_MINISTRAL3B", "specialist_role": "LOCAL_GENERALIST",
                "output": {"text": "riassunto"}, "verify_passed": True, "verify_errors": []}
    _, frp, _ = process_work_product(task_id="TEST_FMT", work_type="routine_summary",
                                    attempts=[attempt_ok])
    summary = format_task_completed_summary(frp)
    assert summary.startswith("TASK COMPLETED")
    assert "Premium calls: 0" in summary


def test_jarvis_explain_answers_from_packet_only():
    def attempt_ok():
        return {"agent_id": "LOCAL_FAST_MINISTRAL3B", "specialist_role": "LOCAL_GENERALIST",
                "output": {"text": "riassunto"}, "verify_passed": True, "verify_errors": []}
    _, frp, _ = process_work_product(task_id="TEST_EXPLAIN", work_type="routine_summary",
                                    attempts=[attempt_ok])
    answer = explain(frp, "Chi ha lavorato su questa task?")
    assert "LOCAL_FAST_MINISTRAL3B" in answer
    assert explain(frp, "domanda non riconosciuta xyz") is None
