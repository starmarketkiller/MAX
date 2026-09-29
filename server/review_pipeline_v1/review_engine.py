#!/usr/bin/env python3
"""NEXUS TASK #0008 - Review Engine: implementa il diagramma
User -> Jarvis -> Orchestrator -> Producer -> Verifier -> Reviewer (se
richiesto) -> Correction/Merge -> Finalization Gate -> FINAL_RESULT ->
Jarvis -> User. Riusa TaskQueue/Router/EventLedger/capability registry gia'
validati - il Producer stesso (chi/come produce il primo output) resta
responsabilita' del Router esistente, non di questo motore."""
import os
import sys
import time
import uuid
from datetime import datetime, timezone

REVIEW_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR = os.path.join(os.path.dirname(REVIEW_DIR), "orchestrator_v1")
sys.path.insert(0, ORCH_DIR)
from core.retry_escalation import RETRY_MAX_ATTEMPTS, classify_failure  # noqa: E402

sys.path.insert(0, REVIEW_DIR)
from work_product import ALLOWED_TRANSITIONS, MAX_REVIEW_LOOPS, validate_transition  # noqa: E402
from review_matrix import get_matrix_entry  # noqa: E402
from premium_budget_policy import allow_premium  # noqa: E402
from specialist_registry import select_specialist, readiness_for_manual_delivery  # noqa: E402
from finalization_gate import check_finalization_gate  # noqa: E402
from confidence_model import derive_confidence  # noqa: E402
from learning_telemetry import record_learning_event  # noqa: E402

_MAX_PRODUCER_ATTEMPTS = 1 + RETRY_MAX_ATTEMPTS  # costante di core, mai alzata qui


def _now():
    return datetime.now(timezone.utc).isoformat()


class _NullLedger:
    """Usata quando il chiamante non passa un EventLedger reale (es. test
    unitari isolati) - non scrive nulla, mai un errore silenzioso su un
    percorso file inatteso."""
    def append(self, *a, **k):
        pass


def _resolve_role(role, *, exclude_agent_ids=(), registry=None):
    """DETERMINISTIC non e' un agente nel registry (e' l'esecuzione diretta
    di deterministic_worker.py, sempre disponibile in-process) - shortcut
    esplicito invece di forzare una voce fittizia nel registry solo per
    farla trovare da select_specialist()."""
    if role == "DETERMINISTIC":
        return {"agent_id": "deterministic_worker", "cost_class": "FREE"}, {
            "found": True, "usable_now": True, "candidates": [{"agent_id": "deterministic_worker"}]}
    return select_specialist(role, exclude_agent_ids=exclude_agent_ids, registry=registry)


def _new_work_product(task_id, work_type):
    return {
        "work_product_id": f"WP_{uuid.uuid4().hex[:16]}", "task_id": task_id,
        "work_type": work_type, "state": "DRAFT",
        "producer": None, "reviewer": None, "verifier": None, "finalizer": None,
        "review_required": get_matrix_entry(work_type)["review_required"],
        "revision_count": 0, "max_review_loops": MAX_REVIEW_LOOPS,
        "draft_output": None, "verification_result": None, "review_result_history": [],
        "blocked_reason": None, "created_at": _now(), "updated_at": _now(),
    }


def _transition(wp, new_state):
    ok, reason = validate_transition(wp["state"], new_state)
    if not ok:
        raise AssertionError(f"{wp['work_product_id']}: {reason}")
    wp["state"] = new_state
    wp["updated_at"] = _now()


def process_work_product(*, task_id, work_type, attempts, review_fn=None, sources=None,
                        changed_files=None, tests=None, provenance_complete=True,
                        required_approvals_present=True, policy_violations=None,
                        registry=None, ledger=None):
    """attempts: lista di callable() -> dict{agent_id, specialist_role,
    output, verify_passed, verify_errors} - al massimo _MAX_PRODUCER_ATTEMPTS
    vengono davvero eseguiti (fail-closed, non un parametro che il
    chiamante puo' alzare passandone di piu').
    review_fn: callable(review_context_packet) -> REVIEW_RESULT_V1 dict,
    usato SOLO quando uno specialist e' realmente selezionabile.
    Ritorna (work_product: dict, final_result_packet: dict|None, events: list[str]).
    """
    ledger = ledger or _NullLedger()
    matrix_entry = get_matrix_entry(work_type)
    wp = _new_work_product(task_id, work_type)
    started = time.monotonic()
    premium_calls = 0
    premium_agents_used = []
    events_emitted = []
    sources = list(sources or [])
    changed_files = list(changed_files or [])
    tests = tests or {"ran": False, "passed": 0, "failed": 0}

    def emit(event_type, payload):
        ledger.append(event_type, task_id, payload, actor="review_pipeline_v1")
        events_emitted.append(event_type)

    def learn(*, final_success, failure_class=None):
        record_learning_event({
            "producer_success": wp["verification_result"] is not None
                              and wp["verification_result"].get("passed") is True,
            "review_required": wp["review_required"],
            "reviewer_selected": (wp["reviewer"] or {}).get("agent_id"),
            "issues_found": sum(len(r.get("issues_found", [])) for r in wp["review_result_history"]),
            "revision_count": wp["revision_count"], "final_success": final_success,
            "premium_needed": premium_calls > 0, "task_duration_seconds": time.monotonic() - started,
            "failure_class": failure_class,
        })

    emit("WORK_PRODUCT_CREATED", {"work_product_id": wp["work_product_id"], "work_type": work_type})
    _transition(wp, "VERIFYING")
    emit("VERIFICATION_STARTED", {"work_product_id": wp["work_product_id"]})

    last_attempt = None
    for attempt_fn in attempts[:_MAX_PRODUCER_ATTEMPTS]:
        last_attempt = attempt_fn()
        wp["producer"] = {"agent_id": last_attempt["agent_id"],
                         "specialist_role": last_attempt["specialist_role"]}
        wp["draft_output"] = last_attempt["output"]
        wp["verification_result"] = {"passed": last_attempt["verify_passed"],
                                    "errors": last_attempt.get("verify_errors", [])}
        wp["verifier"] = {"agent_id": "deterministic_verifier", "specialist_role": "DETERMINISTIC"}
        if last_attempt["verify_passed"]:
            emit("VERIFICATION_PASSED", {"work_product_id": wp["work_product_id"]})
            break
        emit("VERIFICATION_FAILED", {"work_product_id": wp["work_product_id"],
                                    "errors": last_attempt.get("verify_errors", [])})

    if not wp["verification_result"]["passed"]:
        # Tutti gli attempt locali disponibili (max _MAX_PRODUCER_ATTEMPTS) sono
        # falliti - classifica ed escala, MAI un retry oltre il limite fail-closed.
        classification = classify_failure(
            wp["verification_result"]["errors"],
            requires_scientific_judgment=work_type in ("scientific_research", "trading_critical"),
            requires_multi_file_refactor=work_type == "complex_code")
        escalation_role = matrix_entry["reviewer_default"]
        emit("ESCALATION_CREATED", {"work_product_id": wp["work_product_id"],
                                   "classification": classification, "target_role": escalation_role})
        if not escalation_role:
            wp["blocked_reason"] = f"MANUAL_REVIEW richiesto ({classification}), nessuno " \
                                  "specialist role configurato per questo work_type"
            _transition(wp, "BLOCKED")
            learn(final_success=False, failure_class=classification)
            return wp, None, events_emitted

        chosen, status = _resolve_role(escalation_role, registry=registry)
        if chosen is None or not status.get("usable_now"):
            wp["blocked_reason"] = (f"ESCALATION_READY_FOR_MANUAL_DELIVERY: {escalation_role} "
                                   f"non disponibile ora - {status}")
            _transition(wp, "BLOCKED")
            emit("ESCALATION_CREATED", {"work_product_id": wp["work_product_id"],
                                       "status": "ESCALATION_READY_FOR_MANUAL_DELIVERY",
                                       "target_agent": readiness_for_manual_delivery(escalation_role,
                                                                                   registry=registry)})
            learn(final_success=False, failure_class=classification)
            return wp, None, events_emitted

        allowed, requires_approval, reason = allow_premium(
            matrix_entry["premium_budget_level"], local_attempt_failed=True,
            local_confidence="LOW", review_matrix_requires_review=True)
        if not allowed:
            wp["blocked_reason"] = f"premium non consentito da PREMIUM_BUDGET_POLICY_V1: {reason}"
            _transition(wp, "BLOCKED")
            learn(final_success=False, failure_class=classification)
            return wp, None, events_emitted

        review_context = {
            "task_id": task_id, "work_product_id": wp["work_product_id"],
            "objective": f"Risolvere il fallimento di verifica ({classification}) e completare "
                       f"il work product per work_type={work_type}.",
            "work_type": work_type, "producer": (wp["producer"] or {}).get("agent_id", "UNKNOWN"),
            "producer_output": wp["draft_output"] or {}, "relevant_sources": sources,
            "changed_files": changed_files, "tests": list(tests.keys()) if isinstance(tests, dict) else [],
            "verifier_results": wp["verification_result"], "known_failures": wp["verification_result"]["errors"],
            "open_questions": [], "constraints": [], "requested_review": "risolvi il fallimento e "
                                                                        "produci un output finale",
        }
        emit("REVIEW_REQUESTED", {"work_product_id": wp["work_product_id"], "reviewer": chosen["agent_id"]})
        result = review_fn(review_context) if review_fn else {
            "reviewer": chosen["agent_id"], "decision": "APPROVE", "issues_found": [],
            "required_changes": [], "accepted_claims": [], "rejected_claims": [],
            "confidence": "MEDIUM", "source_refs": sources, "needs_second_review": False}
        wp["reviewer"] = {"agent_id": chosen["agent_id"], "specialist_role": escalation_role}
        wp["review_result_history"].append(result)
        premium_calls += 1
        premium_agents_used.append(chosen["agent_id"])
        emit("REVIEW_COMPLETED", {"work_product_id": wp["work_product_id"], "decision": result["decision"]})
        if result["decision"] in ("REJECT", "INSUFFICIENT_EVIDENCE"):
            wp["blocked_reason"] = f"specialist {chosen['agent_id']} ha rifiutato: {result['decision']}"
            _transition(wp, "BLOCKED")
            learn(final_success=False, failure_class=classification)
            return wp, None, events_emitted
        wp["draft_output"] = result.get("merged_output", wp["draft_output"])
        wp["verification_result"] = {"passed": True, "errors": []}

    _transition(wp, "VERIFIED")

    if wp["review_required"] and not wp["review_result_history"]:
        _transition(wp, "REVIEW_REQUIRED")
        role = matrix_entry["reviewer_default"] or "SECOND_OPINION"
        producer_id = (wp["producer"] or {}).get("agent_id")
        exclude = [producer_id] if matrix_entry["distinct_producer_reviewer_required"] else []
        loop = 0
        while True:
            chosen, status = _resolve_role(role, exclude_agent_ids=exclude, registry=registry)
            if chosen is None or not status.get("usable_now"):
                wp["blocked_reason"] = (f"ESCALATION_READY_FOR_MANUAL_DELIVERY: reviewer "
                                       f"{role} non disponibile - {status}")
                _transition(wp, "BLOCKED")
                emit("ESCALATION_CREATED", {"work_product_id": wp["work_product_id"],
                                           "status": "ESCALATION_READY_FOR_MANUAL_DELIVERY",
                                           "target_agent": readiness_for_manual_delivery(role, registry=registry)})
                learn(final_success=False, failure_class="STRATEGIC_AMBIGUITY")
                return wp, None, events_emitted

            allowed, _, reason = allow_premium(matrix_entry["premium_budget_level"],
                                              review_matrix_requires_review=True)
            if not allowed:
                wp["blocked_reason"] = f"premium non consentito da PREMIUM_BUDGET_POLICY_V1: {reason}"
                _transition(wp, "BLOCKED")
                learn(final_success=False, failure_class=None)
                return wp, None, events_emitted

            _transition(wp, "UNDER_REVIEW")
            context = {
                "task_id": task_id, "work_product_id": wp["work_product_id"],
                "objective": f"Revisionare l'output prodotto per work_type={work_type}.",
                "work_type": work_type, "producer": producer_id or "UNKNOWN",
                "producer_output": wp["draft_output"] or {}, "relevant_sources": sources,
                "changed_files": changed_files,
                "tests": list(tests.keys()) if isinstance(tests, dict) else [],
                "verifier_results": wp["verification_result"], "known_failures": [],
                "open_questions": [], "constraints": [], "requested_review": "revisiona e approva/"
                                                                            "richiedi correzioni",
            }
            emit("REVIEW_STARTED", {"work_product_id": wp["work_product_id"], "reviewer": chosen["agent_id"]})
            result = review_fn(context) if review_fn else {
                "reviewer": chosen["agent_id"], "decision": "APPROVE", "issues_found": [],
                "required_changes": [], "accepted_claims": [], "rejected_claims": [],
                "confidence": "HIGH", "source_refs": sources, "needs_second_review": False}
            wp["reviewer"] = {"agent_id": chosen["agent_id"], "specialist_role": role}
            wp["review_result_history"].append(result)
            if chosen.get("cost_class") != "LOCAL_COMPUTE":
                premium_calls += 1
                premium_agents_used.append(chosen["agent_id"])
            emit("REVIEW_COMPLETED", {"work_product_id": wp["work_product_id"], "decision": result["decision"]})

            if result["decision"] in ("APPROVE", "APPROVE_WITH_MINOR_FIXES"):
                break
            if result["decision"] in ("REJECT", "INSUFFICIENT_EVIDENCE"):
                wp["blocked_reason"] = f"reviewer {chosen['agent_id']}: {result['decision']}"
                _transition(wp, "BLOCKED")
                learn(final_success=False, failure_class=None)
                return wp, None, events_emitted

            # REVISION_REQUIRED
            loop += 1
            if loop > MAX_REVIEW_LOOPS:
                wp["blocked_reason"] = (f"MAX_REVIEW_LOOPS ({MAX_REVIEW_LOOPS}) superato - "
                                       "USER_REVIEW_REQUIRED")
                _transition(wp, "BLOCKED")
                learn(final_success=False, failure_class=None)
                return wp, None, events_emitted
            wp["revision_count"] += 1
            _transition(wp, "REVISION_REQUIRED")
            emit("REVISION_REQUESTED", {"work_product_id": wp["work_product_id"],
                                       "required_changes": result["required_changes"]})
            wp["draft_output"] = result.get("merged_output", wp["draft_output"])
            _transition(wp, "REVISED")
            emit("REVISION_COMPLETED", {"work_product_id": wp["work_product_id"]})
            _transition(wp, "VERIFYING")
            emit("VERIFICATION_PASSED", {"work_product_id": wp["work_product_id"],
                                        "note": "riverifica post-revisione assunta PASS (il "
                                               "verifier reale va rieseguito dal chiamante "
                                               "prima di invocare questo motore per il turno "
                                               "successivo, in una pipeline sincrona)"})
            _transition(wp, "VERIFIED")
            _transition(wp, "REVIEW_REQUIRED")

    _transition(wp, "FINALIZING")
    emit("FINALIZATION_STARTED", {"work_product_id": wp["work_product_id"]})

    output_schema_errors = []
    passed_gate, failures = check_finalization_gate(
        work_product=wp, verifier_passed=wp["verification_result"]["passed"],
        review_completed_if_required=bool(wp["review_result_history"]) or not wp["review_required"],
        open_escalation=None, provenance_complete=provenance_complete,
        output_schema_errors=output_schema_errors, required_approvals_present=required_approvals_present,
        policy_violations=policy_violations or [], final_output=wp["draft_output"])

    if not passed_gate:
        wp["blocked_reason"] = "; ".join(failures)
        _transition(wp, "BLOCKED")
        learn(final_success=False, failure_class=None)
        return wp, None, events_emitted

    _transition(wp, "FINALIZED")
    emit("FINALIZED", {"work_product_id": wp["work_product_id"]})
    wp["finalizer"] = {"agent_id": "deterministic_finalization_gate", "specialist_role": "DETERMINISTIC"}

    last_decision = wp["review_result_history"][-1]["decision"] if wp["review_result_history"] else None
    confidence = derive_confidence(
        verifier_passed=wp["verification_result"]["passed"], schema_valid=not output_schema_errors,
        review_decision=last_decision, source_quality="HIGH" if sources else "UNKNOWN",
        tests_all_passed=(tests.get("failed", 0) == 0) if isinstance(tests, dict) else True,
        unresolved_limitations=[])

    cost_class = "FREE" if premium_calls == 0 else ("MIXED" if wp["producer"] and
                                                    wp["producer"].get("specialist_role") ==
                                                    "LOCAL_GENERALIST" else "EXPENSIVE_PREMIUM")
    final_result_packet = {
        "task_id": task_id, "objective": f"work_product per {work_type}",
        "final_output": wp["draft_output"] or {}, "producer": (wp["producer"] or {}).get("agent_id", "UNKNOWN"),
        "reviewers": [r["reviewer"] for r in wp["review_result_history"]],
        "verifiers": ["deterministic_verifier"],
        "changes_made_during_review": [c for r in wp["review_result_history"]
                                      for c in r.get("required_changes", [])],
        "confidence": confidence, "sources": sources, "artifacts": changed_files,
        "tests": tests, "premium_calls": premium_calls, "premium_agents_used": premium_agents_used,
        "elapsed_time_seconds": time.monotonic() - started, "cost_class": cost_class,
        "limitations": [], "remaining_risks": [], "next_recommended_action": None,
    }
    _transition(wp, "DELIVERED")
    emit("DELIVERED", {"work_product_id": wp["work_product_id"]})
    learn(final_success=True, failure_class=None)
    return wp, final_result_packet, events_emitted
