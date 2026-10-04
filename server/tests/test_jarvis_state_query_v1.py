"""STATE_QUERY: fix for a real live-smoke-test gap.

"Fammi vedere le task bloccate" and the bare word "Bloccate" both fell
through to UNKNOWN before this fix - classify() had no intent at all for
a colloquial "show me tasks in state X" request. This reuses the exact
same ownership-scoped listing (_user_scoped_tasks) and TASK_LIST rendering
shape already used by /tasks - no new UI/rendering code.
"""
from datetime import datetime, timezone

import pytest

from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService, classify


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
        "task_id": task_id, "title": "State query test task", "objective": "Update src/sample.py",
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


# classify() -----------------------------------------------------------
def test_classify_recognizes_explicit_state_phrase():
    assert classify("Fammi vedere le task bloccate") == "STATE_QUERY"


def test_classify_recognizes_bare_state_word():
    assert classify("Bloccate") == "STATE_QUERY"
    assert classify("bloccate") == "STATE_QUERY"


def test_classify_recognizes_other_state_synonyms():
    assert classify("Mostrami le task completate") == "STATE_QUERY"
    assert classify("quali sono in coda?") == "STATE_QUERY"


def test_classify_perche_e_bloccata_still_wins_as_follow_up():
    # Regression guard: the existing diagnostic phrasing must still route to
    # FOLLOW_UP (contextual "why is THIS task blocked"), never to the new
    # bulk-listing STATE_QUERY.
    assert classify("Perché è bloccata?") == "FOLLOW_UP"


# end-to-end -------------------------------------------------------------
def test_state_query_lists_escalation_required_tasks_for_bloccate(service):
    escalated = _submit(service, "TASK_STUCK", "ESCALATION_REQUIRED",
                        escalation={"target": "MANUAL_REVIEW", "classification": "x"})
    _submit(service, "TASK_DONE", "COMPLETED")
    response = JarvisGateway(service).handle(message("Fammi vedere le task bloccate"))
    assert response["response_type"] == "ANSWER"
    assert response["details"]["view"] == "TASK_LIST"
    ids = [item["task_id"] for item in response["details"]["items"]]
    assert escalated in ids
    assert "TASK_DONE" not in ids


def test_state_query_bare_word_matches_same_as_full_sentence(service):
    escalated = _submit(service, "TASK_STUCK2", "ESCALATION_REQUIRED",
                        escalation={"target": "MANUAL_REVIEW", "classification": "x"})
    response = JarvisGateway(service).handle(message("Bloccate"))
    assert response["details"]["view"] == "TASK_LIST"
    assert escalated in [item["task_id"] for item in response["details"]["items"]]


def test_state_query_no_matching_tasks_gives_a_clean_empty_answer(service):
    response = JarvisGateway(service).handle(message("Fammi vedere le task completate"))
    assert response["response_type"] == "ANSWER"
    assert response["details"]["items"] == []


def test_state_query_only_shows_the_caller_own_tasks(service):
    _submit(service, "TASK_OTHER_USER", "ESCALATION_REQUIRED",
           conversation_id="c2", escalation={"target": "MANUAL_REVIEW", "classification": "x"})
    response = JarvisGateway(service).handle(message("Bloccate", conversation="c1", user_id="999"))
    assert response["details"]["items"] == []
