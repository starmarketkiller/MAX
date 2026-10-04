"""JARVIS_EXECUTIVE_CONVERSATION_V4.

Every mutation still goes through the exact same service methods built in
NATURAL_CONVERSATION_V3 (approval()/resume_orphaned()/create_task()) - this
layer only resolves WHICH task and proposes WHAT to do next, never a new
write path, never a direct provider/trading call, never guessed on
ambiguity.
"""
from datetime import datetime, timezone

import pytest

from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService


def message(text, conversation="c1", metadata=None, user_id="42"):
    return {"message_id": f"m-{abs(hash((text, conversation, str(metadata))))}", "user_id": user_id,
            "channel": "TEST", "conversation_id": conversation,
            "timestamp": datetime.now(timezone.utc).isoformat(), "input_type": "TEXT",
            "text": text, "attachments": [], "reply_to": None, "request_class": "UNKNOWN",
            "priority": "NORMAL", "metadata": metadata or {}}


@pytest.fixture
def service(tmp_path, monkeypatch):
    svc = JarvisService(str(tmp_path / "q.json"), str(tmp_path / "l.jsonl"),
                        str(tmp_path / "c.json"))
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    return svc


def _manifest(task_id, **changes):
    value = {
        "task_id": task_id, "title": "V4 test task", "objective": "Update src/sample.py",
        "task_type": "CODE", "work_type": "complex_code", "priority": "NORMAL",
        "risk_level": "A1", "scientific_risk": "NONE", "code_risk": "HIGH",
        "financial_risk": "NONE", "required_capabilities": ["small_python_functions"],
        "deterministic_tools_available": False, "repo_scope": "task-scoped",
        "files_allowed": ["src/sample.py"], "files_forbidden": [".env", "MQL5/**"],
        "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
        "success_criteria": ["bounded patch verified"], "verifier": "free_coding_worker_v1",
        "estimated_complexity": "SMALL", "estimated_runtime": "5m", "premium_allowed": False,
        "preferred_executor": "TIER1_LOCAL_CHEAP", "fallback_executors": ["TIER4_CODEX"],
        "approval_required": "REVIEW_REQUIRED", "created_by": "jarvis:42",
        "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
        "account_scope_id": None,
    }
    value.update(changes)
    return value


def _submit(service, task_id, state, conversation_id="c1", **record_updates):
    value = _manifest(task_id)
    service.orchestrator.submit(value, action="conversational_programming",
                                action_params={"conversation_id": conversation_id})
    if state != "QUEUED":
        service.queue.transition(task_id, "RUNNING", executor="TEST")
        if state != "RUNNING":
            service.queue.transition(task_id, state, **record_updates)
    return task_id


# A. GOAL_TO_TASK -------------------------------------------------------
def test_exploratory_goal_creates_a_draft_not_an_immediate_task(service):
    response = JarvisGateway(service).handle(message(
        "Possiamo iniziare una task per trovare prodotti in voga da vendere?"))
    assert response["status"] == "CONFIRMATION_REQUIRED"
    assert response["response_type"] == "ANSWER"
    assert len(service.queue.list_all()) == 0  # nothing created yet
    assert service.conversation_store.get("c1")["pending_confirmation"]["type"] == "TASK_DRAFT"

    confirmed = JarvisGateway(service).handle(message("sì"))
    assert confirmed["response_type"] == "TASK_ACK"
    assert len(service.queue.list_all()) == 1
    record = service.queue.get(confirmed["task_id"])
    assert "prodotti in voga" in record["manifest"]["objective"]


def test_declining_the_draft_creates_nothing(service):
    JarvisGateway(service).handle(message("Vorrei trovare un modo per vendere online"))
    assert service.conversation_store.get("c1")["pending_confirmation"]["type"] == "TASK_DRAFT"
    declined = JarvisGateway(service).handle(message("no, lascia stare"))
    assert len(service.queue.list_all()) == 0
    assert not (service.conversation_store.get("c1").get("pending_confirmation") or {})


def test_imperative_goal_creates_the_task_directly(service):
    response = JarvisGateway(service).handle(message(
        "Inizia una nuova task con l'obiettivo di guadagnare i primi 10€ in automatico"))
    assert response["response_type"] == "TASK_ACK"
    assert len(service.queue.list_all()) == 1
    record = service.queue.get(response["task_id"])
    assert "guadagnare i primi 10" in record["manifest"]["objective"]


def test_too_vague_goal_asks_for_clarification_creates_nothing(service):
    response = JarvisGateway(service).handle(message("voglio ottenere"))
    assert response["status"] == "PARTIAL"
    assert len(service.queue.list_all()) == 0


# D. CONTEXTUAL APPROVAL RESOLUTION --------------------------------------
def test_approvo_ultima_task_resolves_the_actually_pending_one_not_last_task_id(service):
    older = _submit(service, "TASK_OLD_DONE", "COMPLETED")
    pending = _submit(service, "TASK_PENDING_APPROVAL", "WAITING_APPROVAL")
    # last_task_id points at the COMPLETED one (most recently touched),
    # exactly the bug being closed - "l'ultima" must still resolve to the
    # actually-pending one, not last_task_id.
    service.conversation_store.update("c1", last_task_id=older, user_id="42")

    response = JarvisGateway(service).handle(message("Approvo l'ultima task"))
    assert response["task_id"] == pending
    assert response["status"] == "QUEUED"


def test_quali_devo_approvare_lists_without_mutating(service):
    a = _submit(service, "TASK_A", "WAITING_APPROVAL")
    b = _submit(service, "TASK_B", "WAITING_APPROVAL")
    response = JarvisGateway(service).handle(message("Quali devo approvare?"))
    assert response["response_type"] == "ANSWER"
    ids = {item["task_id"] for item in response["details"]["items"]}
    assert ids == {a, b}
    assert service.queue.get(a)["state"] == "WAITING_APPROVAL"
    assert service.queue.get(b)["state"] == "WAITING_APPROVAL"


def test_ambiguous_multiple_pending_approvals_asks_never_mutates(service):
    a = _submit(service, "TASK_AMBIG_A", "WAITING_APPROVAL")
    b = _submit(service, "TASK_AMBIG_B", "WAITING_APPROVAL")
    response = JarvisGateway(service).handle(message("Approvale"))
    assert response["response_type"] == "CLARIFICATION_REQUIRED"
    assert response["status"] == "AMBIGUOUS"
    assert service.queue.get(a)["state"] == "WAITING_APPROVAL"
    assert service.queue.get(b)["state"] == "WAITING_APPROVAL"


def test_singular_ultima_resolves_deterministically_even_with_multiple_pending(service):
    """Real production smoke test finding, 2026-10-04: 'l'ultima' carries its
    own unambiguous ordering (newest-updated-first) - 2+ WAITING_APPROVAL
    candidates must NOT trigger a clarification for this phrasing the way
    it correctly does for the generic 'approvale'/'quali devo approvare'."""
    import time
    _submit(service, "TASK_OLDER_PENDING", "WAITING_APPROVAL")
    time.sleep(0.01)
    newest = _submit(service, "TASK_NEWER_PENDING", "WAITING_APPROVAL")
    response = JarvisGateway(service).handle(message("Approvo l'ultima task"))
    assert response["task_id"] == newest
    assert response["status"] == "QUEUED"


def test_singular_ultima_resolves_even_without_the_apostrophe(service):
    """A phone's autocorrect commonly drops the apostrophe ('L ultima')."""
    pending = _submit(service, "TASK_AUTOCORRECT_CASE", "WAITING_APPROVAL")
    response = JarvisGateway(service).handle(message("Approvo L ultima task"))
    assert response["task_id"] == pending
    assert response["status"] == "QUEUED"


def test_nothing_pending_approval_gives_a_clean_answer_not_a_crash(service):
    _submit(service, "TASK_RUNNING_ONLY", "RUNNING")
    response = JarvisGateway(service).handle(message("Approvo l'ultima task"))
    assert response["response_type"] == "ERROR"
    assert response["status"] == "NONE_PENDING"


# B/F. Next action + natural response style ------------------------------
def test_wrong_state_approval_error_offers_what_is_actually_pending(service):
    escalated = _submit(service, "TASK_ESCALATED", "ESCALATION_REQUIRED",
                        escalation={"target": "MANUAL_REVIEW", "classification": "x"})
    pending = _submit(service, "TASK_REAL_PENDING", "WAITING_APPROVAL")
    response = JarvisGateway(service).handle(
        message(f"approva {escalated}"))
    assert response["response_type"] == "ERROR"
    assert "non è in attesa di approvazione" in response["summary"]
    assert pending in response["details"]["pending_approvals"]


def test_perche_e_bloccata_gives_a_concrete_next_action(service):
    task_id = _submit(service, "TASK_WHY_BLOCKED", "BLOCKED",
                      recovery={"classification": "ORPHANED_RUNNING_AFTER_RESTART"},
                      dispatch_last_error="ORPHANED_RUNNING_AFTER_RESTART")
    service.conversation_store.update("c1", last_task_id=task_id, user_id="42")
    response = JarvisGateway(service).handle(message("Perché è bloccata?"))
    assert response["task_id"] == task_id
    assert "riprenda" in response["summary"].lower() or "recuperabile" in response["summary"].lower()
    assert any(a.get("type") == "RESUME" for a in response["actions"])


# E. EXECUTIVE INTENTS -----------------------------------------------------
def test_cosa_facciamo_adesso_proposes_the_top_priority(service):
    _submit(service, "TASK_QUEUED_LOW", "QUEUED")
    pending = _submit(service, "TASK_NEEDS_APPROVAL", "WAITING_APPROVAL")
    response = JarvisGateway(service).handle(message("Cosa facciamo adesso?"))
    assert response["task_id"] == pending  # WAITING_APPROVAL outranks QUEUED
    assert response["response_type"] == "ANSWER"


def test_continua_tu_does_not_crash_with_no_open_tasks(service):
    response = JarvisGateway(service).handle(message("Continua tu"))
    assert response["response_type"] == "ANSWER"
    assert response["status"] == "COMPLETED"


def test_risolvi_tu_resumes_a_safely_recoverable_blocked_task(service):
    task_id = _submit(service, "TASK_RESOLVI_TU", "BLOCKED",
                      recovery={"classification": "ORPHANED_RUNNING_AFTER_RESTART"},
                      dispatch_last_error="ORPHANED_RUNNING_AFTER_RESTART")
    response = JarvisGateway(service).handle(message("Risolvi tu se puoi, altrimenti dimmi cosa serve"))
    assert response["task_id"] == task_id
    assert response["status"] == "QUEUED"  # actually resumed, not just described


def test_risolvi_tu_refuses_to_act_when_nothing_is_safely_automatable(service):
    task_id = _submit(service, "TASK_RESOLVI_TU_MANUAL", "ESCALATION_REQUIRED",
                      escalation={"target": "MANUAL_REVIEW", "classification": "LOCAL_VERIFIER_REJECTED"})
    response = JarvisGateway(service).handle(message("Risolvi tu se puoi, altrimenti dimmi cosa serve"))
    assert response["task_id"] == task_id
    assert service.queue.get(task_id)["state"] == "ESCALATION_REQUIRED"  # untouched, no autonomy invented
    assert "non posso risolverla" in response["summary"].lower()


# Safety / no-regression ----------------------------------------------------
def test_classify_precedence_for_new_intents():
    from jarvis_v1.service import classify
    assert classify("Approvo l'ultima task") == "EXECUTIVE_APPROVAL_REFERENCE"
    assert classify("Quali devo approvare?") == "EXECUTIVE_APPROVAL_REFERENCE"
    assert classify("Possiamo iniziare una task per trovare prodotti in voga da vendere?") == "GOAL_TO_TASK"
    assert classify("Inizia una nuova task con l'obiettivo di guadagnare i primi 10€ in automatico") == "GOAL_TO_TASK"
    assert classify("Cosa facciamo adesso?") == "EXECUTIVE_INTENT"
    assert classify("Continua tu") == "EXECUTIVE_INTENT"
    assert classify("Cosa consigli?") == "EXECUTIVE_INTENT"
    # "quella"/"questa" still resolve as plain last_task_id (V3, unaffected).
    assert classify("approva quella") == "APPROVAL"


def test_natural_conversation_v3_mutations_still_work_unaffected(service):
    task_id = _submit(service, "TASK_V3_STILL_WORKS", "WAITING_APPROVAL")
    service.conversation_store.update("c1", last_task_id=task_id, user_id="42")
    response = JarvisGateway(service).handle(message("approva quella"))
    assert response["task_id"] == task_id
    assert response["status"] == "QUEUED"
