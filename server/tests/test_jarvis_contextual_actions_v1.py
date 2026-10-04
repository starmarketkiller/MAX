"""JARVIS_CONTEXTUAL_ACTIONS_V1.

Makes the generic "I didn't understand" fallback and its Telegram quick
actions reflect the user's actual live task counts instead of 4 static
shortcuts shown no matter what. This is explicitly NOT the proactive
milestone (Jarvis never speaks first here) - every response here is still
triggered by an incoming user message, read-only, and reuses the exact
service methods STATE_QUERY/V3/V4 already shipped (_user_scoped_tasks,
state_query). See PROACTIVE_JARVIS_CORE_V1 for actual spontaneous events.
"""
from datetime import datetime, timezone

import pytest

from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService
from jarvis_v1.telegram_adapter import TelegramAdapter


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
        "task_id": task_id, "title": "Contextual actions test task", "objective": "Update src/sample.py",
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


def _unknown(service, text="blah blah blah not a recognized phrase at all"):
    return JarvisGateway(service).handle(message(text))


# 1. zero task rilevanti -----------------------------------------------
def test_no_relevant_tasks_falls_back_to_minimal_static_buttons(service):
    response = _unknown(service)
    assert response["details"].get("view") != "CONTEXTUAL_FALLBACK"
    assert "Non ho riconosciuto una richiesta operativa precisa" in response["summary"]
    keyboard = TelegramAdapter.build_keyboard(response)
    labels = [btn["text"] for row in keyboard for btn in row]
    assert labels == ["Stato NEXUS", "Le mie task", "Agenti", "Help"]


# 2. solo escalation -------------------------------------------------
def test_only_escalation_shows_a_single_review_bucket(service):
    _submit(service, "TASK_STUCK", "ESCALATION_REQUIRED",
           escalation={"target": "MANUAL_REVIEW", "classification": "x"})
    response = _unknown(service)
    assert response["details"]["view"] == "CONTEXTUAL_FALLBACK"
    categories = response["details"]["categories"]
    assert categories == [{"code": "REVIEW", "label": "Da rivedere", "count": 1}]
    assert "1 task da rivedere" in response["summary"]
    keyboard = TelegramAdapter.build_keyboard(response)
    assert keyboard == [[{"text": "Da rivedere (1)", "callback_data": "J1|Q|REVIEW"}]]


# 3. solo approval -----------------------------------------------------
def test_only_approval_shows_a_single_approvals_bucket(service):
    _submit(service, "TASK_PENDING", "WAITING_APPROVAL")
    response = _unknown(service)
    categories = response["details"]["categories"]
    assert categories == [{"code": "APPROVALS", "label": "Da approvare", "count": 1}]
    assert "1 task da approvare" in response["summary"]


# 4. piu' categorie contemporaneamente ----------------------------------
def test_multiple_categories_join_correctly_in_the_summary(service):
    for i in range(8):
        _submit(service, f"TASK_REVIEW_{i}", "ESCALATION_REQUIRED",
               escalation={"target": "MANUAL_REVIEW", "classification": "x"})
    for i in range(2):
        _submit(service, f"TASK_APPROVE_{i}", "WAITING_APPROVAL")
    response = _unknown(service)
    assert response["summary"] == (
        "Non ho capito bene la richiesta, ma al momento hai 8 task da rivedere e 2 task da approvare.")
    categories = response["details"]["categories"]
    assert [c["code"] for c in categories] == ["REVIEW", "APPROVALS"]
    assert [c["count"] for c in categories] == [8, 2]
    keyboard = TelegramAdapter.build_keyboard(response)
    assert keyboard == [[{"text": "Da rivedere (8)", "callback_data": "J1|Q|REVIEW"},
                         {"text": "Da approvare (2)", "callback_data": "J1|Q|APPROVALS"}]]


# 5. quick action -> corretto STATE_QUERY --------------------------------
@pytest.mark.parametrize("code,task_id,state,record_updates", [
    ("REVIEW", "TASK_QA_REVIEW", "ESCALATION_REQUIRED",
     {"escalation": {"target": "MANUAL_REVIEW", "classification": "x"}}),
    ("APPROVALS", "TASK_QA_APPROVE", "WAITING_APPROVAL", {}),
    ("RUNNING", "TASK_QA_RUNNING", "RUNNING", {}),
    ("FAILED", "TASK_QA_FAILED", "FAILED", {}),
    ("COMPLETED", "TASK_QA_DONE", "COMPLETED", {}),
])
def test_quick_action_code_routes_to_the_matching_state_query(service, code, task_id, state, record_updates):
    _submit(service, task_id, state, **record_updates)
    msg = message(f"Telegram quick action {code}",
                 metadata={"ui_action": "QUICK_ACTION", "quick_action": code})
    response = JarvisGateway(service).handle(msg)
    assert response["details"]["view"] == "TASK_LIST"
    ids = [item["task_id"] for item in response["details"]["items"]]
    assert task_id in ids


# 6. ownership filtering --------------------------------------------------
def test_categories_only_count_the_caller_own_tasks(service):
    _submit(service, "TASK_OTHER_USER", "ESCALATION_REQUIRED", conversation_id="c2",
           escalation={"target": "MANUAL_REVIEW", "classification": "x"})
    response = JarvisGateway(service).handle(
        message("blah blah blah not a recognized phrase at all", conversation="c1", user_id="999"))
    assert response["details"].get("view") != "CONTEXTUAL_FALLBACK"


# 7. stale callback --------------------------------------------------------
def test_stale_quick_action_on_now_empty_category_gives_a_clean_answer(service):
    # No task in ESCALATION_REQUIRED/BLOCKED at all - simulates a button
    # rendered when the bucket was non-empty, tapped after it emptied out.
    msg = message("Telegram quick action REVIEW",
                 metadata={"ui_action": "QUICK_ACTION", "quick_action": "REVIEW"})
    response = JarvisGateway(service).handle(msg)
    assert response["response_type"] == "ANSWER"
    assert response["details"]["items"] == []
    assert "Nessuna tua task in stato" in response["summary"]


# 8. nessuna mutation -------------------------------------------------------
def test_contextual_fallback_and_quick_actions_never_mutate_state(service):
    task_id = _submit(service, "TASK_UNTOUCHED", "ESCALATION_REQUIRED",
                      escalation={"target": "MANUAL_REVIEW", "classification": "x"})
    before = service.queue.get(task_id)["state"]
    _unknown(service)
    msg = message("Telegram quick action REVIEW",
                 metadata={"ui_action": "QUICK_ACTION", "quick_action": "REVIEW"})
    JarvisGateway(service).handle(msg)
    after = service.queue.get(task_id)["state"]
    assert before == after == "ESCALATION_REQUIRED"


# 9. regressione -------------------------------------------------------------
def test_normal_task_card_keyboard_is_unaffected(service):
    task_id = _submit(service, "TASK_CARD", "WAITING_APPROVAL")
    response = {"task_id": task_id, "status": "WAITING_APPROVAL",
               "details": {"state": "WAITING_APPROVAL"}, "response_type": "TASK_STATUS"}
    keyboard = TelegramAdapter.build_keyboard(response)
    labels = [btn["text"] for row in keyboard for btn in row]
    assert "Approva" in labels and "Rifiuta" in labels
    assert not any("Da rivedere" in label or "Da approvare" in label for label in labels)
