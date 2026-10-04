"""JARVIS_CONTEXTUAL_MUTATION_RESOLUTION_V1.

Found live: after Jarvis shows exactly one WAITING_APPROVAL task (via
"Quali devo approvare?" or the "Da approvare" quick-action button), a bare
"Approvo" fell through to the generic fallback instead of resolving to that
task. Fixed by delegating to the EXACT SAME live-requeried
executive_approval_reference() resolver "l'ultima" already uses - the only
new piece is WHEN to try: only right after an approval-filtered listing
(conversation_store.last_view == "APPROVAL_LIST"), never guessed from thin
air and never bypassing the existing 0/1/2+-candidate or stale-state logic.
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
        "task_id": task_id, "title": "Contextual mutation test task", "objective": "Update src/sample.py",
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


# 1. una sola WAITING_APPROVAL mostrata -> Approvo approva quella ---------
def test_bare_approvo_after_single_pending_listing_resolves_and_approves(service):
    task_id = _submit(service, "TASK_SOLO_PENDING", "WAITING_APPROVAL")
    listing = JarvisGateway(service).handle(message("Quali devo approvare?"))
    assert listing["details"]["view"] == "TASK_LIST"
    response = JarvisGateway(service).handle(message("Approvo"))
    assert response["task_id"] == task_id
    assert service.queue.get(task_id)["state"] == "QUEUED"


# 2. stesso principio per Rifiuto ------------------------------------------
def test_bare_rifiuto_after_single_pending_listing_resolves_and_rejects(service):
    task_id = _submit(service, "TASK_SOLO_REJECT", "WAITING_APPROVAL")
    JarvisGateway(service).handle(message("Quali devo approvare?"))
    response = JarvisGateway(service).handle(message("Rifiuto"))
    assert response["task_id"] == task_id
    assert service.queue.get(task_id)["state"] != "WAITING_APPROVAL"


# 3. 2+ candidate -> chiarimento, mai mutazione ----------------------------
def test_bare_approvo_with_multiple_pending_asks_never_mutates(service):
    a = _submit(service, "TASK_MULTI_A", "WAITING_APPROVAL")
    b = _submit(service, "TASK_MULTI_B", "WAITING_APPROVAL")
    JarvisGateway(service).handle(message("Quali devo approvare?"))
    response = JarvisGateway(service).handle(message("Approvo"))
    assert response["status"] == "AMBIGUOUS"
    assert service.queue.get(a)["state"] == "WAITING_APPROVAL"
    assert service.queue.get(b)["state"] == "WAITING_APPROVAL"


# 4. candidato diventato stale -> no mutation ------------------------------
def test_candidate_gone_stale_between_listing_and_approvo_causes_no_mutation(service):
    task_id = _submit(service, "TASK_WILL_GO_STALE", "WAITING_APPROVAL")
    JarvisGateway(service).handle(message("Quali devo approvare?"))
    # Simulates the task moving on through some other path (another
    # channel, a callback, a timeout) between the listing and this message.
    service.queue.transition(task_id, "CANCELLED", cancellation={"actor": "someone_else"})
    response = JarvisGateway(service).handle(message("Approvo"))
    assert response["status"] == "NONE_PENDING"
    assert service.queue.get(task_id)["state"] == "CANCELLED"


# 5. ultima vista non approval -> Approvo non indovina ---------------------
def test_bare_approvo_does_not_guess_when_last_view_was_unrelated(service):
    task_id = _submit(service, "TASK_UNRELATED_VIEW", "WAITING_APPROVAL")
    JarvisGateway(service).handle(message("Quali devo approvare?"))
    # A different view in between must clear the approval-list context.
    service.conversation_store.update("c1", last_task_id=task_id, user_id="42")
    JarvisGateway(service).handle(message("Dettagli tecnici"))
    response = JarvisGateway(service).handle(message("Approvo"))
    assert response.get("task_id") != task_id
    assert service.queue.get(task_id)["state"] == "WAITING_APPROVAL"


def test_bare_approvo_does_nothing_special_with_no_prior_context_at_all(service):
    task_id = _submit(service, "TASK_NO_CONTEXT", "WAITING_APPROVAL")
    response = JarvisGateway(service).handle(message("Approvo"))
    assert response.get("task_id") != task_id
    assert service.queue.get(task_id)["state"] == "WAITING_APPROVAL"


# 6. "Approvo l'ultima task" resta invariato -------------------------------
def test_approvo_ultima_task_phrasing_still_works_unaffected(service):
    _submit(service, "TASK_OLDER", "WAITING_APPROVAL")
    newest = _submit(service, "TASK_NEWEST", "WAITING_APPROVAL")
    response = JarvisGateway(service).handle(message("Approvo l'ultima task"))
    assert response["task_id"] == newest


# 7. callback Approva/Rifiuta resta invariato ------------------------------
def test_telegram_approve_callback_is_unaffected(service):
    task_id = _submit(service, "TASK_CALLBACK", "WAITING_APPROVAL")
    msg = message(f"Telegram action APPROVE for {task_id}",
                 metadata={"ui_action": "APPROVE", "task_id": task_id})
    response = JarvisGateway(service).handle(msg)
    assert response["task_id"] == task_id
    assert service.queue.get(task_id)["state"] == "QUEUED"


def test_quick_action_approvals_button_is_unaffected(service):
    task_id = _submit(service, "TASK_QUICK_APPROVALS", "WAITING_APPROVAL")
    msg = message("Telegram quick action APPROVALS",
                 metadata={"ui_action": "QUICK_ACTION", "quick_action": "APPROVALS"})
    response = JarvisGateway(service).handle(msg)
    assert response["details"]["view"] == "TASK_LIST"
    assert task_id in [item["task_id"] for item in response["details"]["items"]]
    assert service.queue.get(task_id)["state"] == "WAITING_APPROVAL"  # listing, never a mutation
