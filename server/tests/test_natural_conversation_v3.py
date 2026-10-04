"""NATURAL_CONVERSATION_V3 + ROUTING_RELIABILITY.

Jarvis must understand explicit and contextual mutation intents (riprendi/
approva/rifiuta/annulla, bare or via a contextual reference like "quella"/
"l'ultima"/a clitic pronoun contraction like "approvala") with absolute
precedence over generic conversational task creation, resolve bare
references fail-closed against a small bounded conversation-state object
(never guessing, never inventing a task_id), and capture provider/premium/
notification preferences as plain metadata/policy hints that ride through
the EXISTING orchestrator path - never a bypass of approval, recovery, or
provider policy, and never a direct provider call from this layer.
"""
from datetime import datetime, timedelta, timezone

from jarvis_v1.conversation_store import ConversationStore
from jarvis_v1.service import JarvisService, classify


def message(text, conversation="conv-1", metadata=None, user_id="42"):
    return {"message_id": f"m-{abs(hash((text, conversation, str(metadata))))}", "user_id": user_id,
            "channel": "TEST", "conversation_id": conversation,
            "timestamp": datetime.now(timezone.utc).isoformat(), "input_type": "TEXT",
            "text": text, "attachments": [], "reply_to": None, "request_class": "UNKNOWN",
            "priority": "NORMAL", "metadata": metadata or {}}


def service(tmp_path, monkeypatch=None):
    svc = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"),
                        str(tmp_path / "conversations.json"))
    if monkeypatch:
        monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    return svc


def _manifest(task_id, **changes):
    value = {
        "task_id": task_id, "title": "NC3 test task", "objective": "Update src/sample.py",
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


def _submit(svc, task_id, state, **record_updates):
    value = _manifest(task_id)
    svc.orchestrator.submit(value, action="conversational_programming",
                            action_params={"conversation_id": "conv-1"})
    if state != "QUEUED":
        svc.queue.transition(task_id, "RUNNING", executor="TEST")
        if state != "RUNNING":
            svc.queue.transition(task_id, state, **record_updates)
    return task_id


def _orphaned_blocked_task(svc, task_id="TASK_ORPHAN_NC3"):
    _submit(svc, task_id, "BLOCKED",
           recovery={"classification": "ORPHANED_RUNNING_AFTER_RESTART",
                     "recovered_by": "test", "recovered_at": "2020-01-01T00:00:00+00:00"},
           dispatch_last_error="ORPHANED_RUNNING_AFTER_RESTART")
    return task_id


def _waiting_approval_task(svc, task_id="TASK_WA_NC3"):
    _submit(svc, task_id, "WAITING_APPROVAL")
    return task_id


# 1. --------------------------------------------------------------------
def test_explicit_resume_with_task_id_zero_new_task(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    task_id = _orphaned_blocked_task(svc)
    before = len(svc.queue.list_all())
    response = svc.handle(message(f"riprendi {task_id}"))
    assert response["task_id"] == task_id
    assert response["status"] == "QUEUED"
    assert len(svc.queue.list_all()) == before  # no new task created


# 2. --------------------------------------------------------------------
def test_resume_quella_with_valid_last_task_id(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    task_id = _orphaned_blocked_task(svc)
    svc.conversation_store.update("conv-1", last_task_id=task_id, user_id="42")
    response = svc.handle(message("riprendi quella"))
    assert response["task_id"] == task_id
    assert response["status"] == "QUEUED"


def test_resume_quella_falls_back_to_continuation_when_not_orphaned(tmp_path, monkeypatch):
    # The SAME phrase, but the resolved task is NOT actually BLOCKED/
    # orphaned - must fall back to the pre-existing conversational-
    # programming continuation (create_task), never a refusal.
    svc = service(tmp_path, monkeypatch)
    task_id = _submit(svc, "TASK_NOT_ORPHAN", "WAITING_APPROVAL")
    svc.conversation_store.update("conv-1", last_task_id=task_id, user_id="42")
    response = svc.handle(message("riprendi quella"))
    assert response["response_type"] == "TASK_ACK"  # create_task()'s own response shape
    assert response["task_id"] != task_id  # a NEW follow-up task, old pre-existing behaviour


# 3. --------------------------------------------------------------------
def test_approve_quella(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    task_id = _waiting_approval_task(svc)
    svc.conversation_store.update("conv-1", last_task_id=task_id, user_id="42")
    response = svc.handle(message("approva quella"))
    assert response["task_id"] == task_id
    assert response["status"] == "QUEUED"


def test_approve_clitic_form(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    task_id = _waiting_approval_task(svc)
    svc.conversation_store.update("conv-1", last_task_id=task_id, user_id="42")
    response = svc.handle(message("approvala"))
    assert response["task_id"] == task_id
    assert response["status"] == "QUEUED"


# 4. --------------------------------------------------------------------
def test_rifiutala(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    task_id = _waiting_approval_task(svc)
    svc.conversation_store.update("conv-1", last_task_id=task_id, user_id="42")
    response = svc.handle(message("rifiutala"))
    assert response["task_id"] == task_id
    # No provider_connector wired in this fixture - the pre-existing,
    # already-tested FAILED dead-end (unchanged).
    assert response["status"] == "FAILED"


# 5. --------------------------------------------------------------------
def test_piu_tecnico_uses_last_task(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    task_id = _submit(svc, "TASK_BLOCKED_TECH", "BLOCKED",
                      dispatch_last_error="SOME_FAILURE")
    svc.conversation_store.update("conv-1", last_task_id=task_id, user_id="42")
    response = svc.handle(message("più tecnico"))
    assert response["task_id"] == task_id
    assert "lifecycle" in response["details"]  # technical=True view


# 6. --------------------------------------------------------------------
def test_ambiguous_reference_asks_for_clarification_zero_mutation(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    task_id = _waiting_approval_task(svc)
    # No last_task_id ever set for this conversation - a bare "approva
    # quella" has nothing to resolve against.
    response = svc.handle(message("approva quella"))
    assert response["status"] == "AMBIGUOUS"
    assert response["response_type"] == "CLARIFICATION_REQUIRED"
    assert svc.queue.get(task_id)["state"] == "WAITING_APPROVAL"  # untouched


# 7. --------------------------------------------------------------------
def test_provider_preference_becomes_policy_hint_not_direct_call(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    pref_response = svc.handle(message("falla controllare da Codex"))
    assert pref_response["response_type"] == "PREFERENCE_SET"
    assert svc.conversation_store.get("conv-1")["preferred_provider"] == "CODEX"
    task_response = svc.handle(message("sistema il bug nel repo", conversation="conv-1"))
    task_id = task_response["task_id"]
    record = svc.queue.get(task_id)
    assert record["action_params"]["policy_hints"]["preferred_provider"] == "CODEX"
    # Never a direct call - no provider adapter exists on this bare
    # JarvisService fixture at all, so any direct call would have raised.


# 8. --------------------------------------------------------------------
def test_no_premium_preference_constrains_new_task(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    svc.handle(message("non usare premium"))
    assert svc.conversation_store.get("conv-1")["premium_allowed"] is False
    response = svc.handle(message("implementa una funzione nel repo"))
    record = svc.queue.get(response["task_id"])
    # complex_code would normally default premium_allowed=True - the
    # preference overrides it via the EXISTING, already-wired manifest field.
    assert record["manifest"]["work_type"] == "complex_code"
    assert record["manifest"]["premium_allowed"] is False


# 9. --------------------------------------------------------------------
def test_use_groq_preference_without_bypassing_policy(tmp_path, monkeypatch):
    from orchestrator_v1.core.specialist_review import select_reviewer_candidates
    svc = service(tmp_path, monkeypatch)
    svc.handle(message("usa Groq prima"))
    assert svc.conversation_store.get("conv-1")["preferred_provider"] == "GROQ"
    response = svc.handle(message("sistema il bug nel repo"))
    record = svc.queue.get(response["task_id"])
    assert record["action_params"]["policy_hints"]["preferred_provider"] == "GROQ"
    # The hint is stored, not enforced as a bypass - select_reviewer_candidates()
    # (capability > availability > cost > preference) is completely untouched.
    assert select_reviewer_candidates("complex_code") == ["GROQ", "CODEX", "CLAUDE"]


# 10. -------------------------------------------------------------------
def test_notification_preference_on_complete(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    response = svc.handle(message("dimmi solo quando finisce"))
    assert response["response_type"] == "PREFERENCE_SET"
    assert svc.conversation_store.get("conv-1")["notification_mode"] == "ON_COMPLETE"
    task_response = svc.handle(message("sistema il bug nel repo"))
    task_id = task_response["task_id"]
    assert svc.should_notify(task_id, "RUNNING") is False
    assert svc.should_notify(task_id, "WAITING_APPROVAL") is True
    assert svc.should_notify(task_id, "COMPLETED") is True


def test_notification_preference_silent_and_blocked_only(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    svc.handle(message("non disturbarmi"))
    task_response = svc.handle(message("sistema il bug nel repo"))
    task_id = task_response["task_id"]
    assert svc.should_notify(task_id, "WAITING_APPROVAL") is False
    assert svc.should_notify(task_id, "BLOCKED") is False

    svc2 = service(tmp_path / "second", monkeypatch)
    svc2.handle(message("fammi sapere solo se si blocca"))
    task2 = svc2.handle(message("sistema il bug nel repo"))["task_id"]
    assert svc2.should_notify(task2, "RUNNING") is False
    assert svc2.should_notify(task2, "BLOCKED") is True


def test_should_notify_defaults_to_true_with_no_preference_set(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    task_response = svc.handle(message("sistema il bug nel repo"))
    assert svc.should_notify(task_response["task_id"], "RUNNING") is True


# 11. -------------------------------------------------------------------
def test_generic_task_creation_still_works(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    response = svc.handle(message("sistema il bug nel repo"))
    assert response["response_type"] == "TASK_ACK"
    assert svc.queue.get(response["task_id"])["state"] in ("QUEUED", "RUNNING", "WAITING_APPROVAL")


# 12. -------------------------------------------------------------------
def test_explicit_mutation_outranks_generic_creation(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    task_id = _waiting_approval_task(svc)
    before = len(svc.queue.list_all())
    response = svc.handle(message(f"approva {task_id}"))
    assert response["task_id"] == task_id
    assert response["status"] == "QUEUED"
    assert len(svc.queue.list_all()) == before  # no generic task was created instead


def test_classify_precedence_table_directly():
    assert classify("approva TASK_ABC123") == "APPROVAL"
    assert classify("rifiuta TASK_ABC123") == "REJECTION"
    assert classify("riprendi TASK_ABC123") == "COMMAND"
    assert classify("approvala") == "APPROVAL"
    assert classify("rifiutala") == "REJECTION"
    assert classify("annullala") == "COMMAND"
    assert classify("riprendi quella") == "COMMAND"
    assert classify("non usare premium") == "PROVIDER_PREFERENCE"
    assert classify("usa Groq prima") == "PROVIDER_PREFERENCE"
    assert classify("dimmi solo quando finisce") == "NOTIFICATION_PREFERENCE"
    assert classify("non disturbarmi") == "NOTIFICATION_PREFERENCE"
    # Bare verb, nothing to resolve against - untouched, pre-existing meaning.
    assert classify("riprendi il lavoro sul modulo di autenticazione") == "TASK_REQUEST"
    assert classify("sistema il bug nel repo") == "TASK_REQUEST"


# 13. -------------------------------------------------------------------
def test_stale_task_state_fails_closed(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    # last_task_id points at a task that no longer exists in the queue.
    svc.conversation_store.update("conv-1", last_task_id="TASK_DOES_NOT_EXIST", user_id="42")
    response = svc.handle(message("approva quella"))
    assert response["response_type"] == "ERROR"
    assert response["status"] == "UNKNOWN"


def test_resume_on_stale_reference_falls_back_safely(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    svc.conversation_store.update("conv-1", last_task_id="TASK_DOES_NOT_EXIST", user_id="42")
    response = svc.handle(message("riprendi quella"))
    # KeyError on the stale reference -> falls back to the pre-existing
    # conversational continuation (create_task), never a crash.
    assert response["response_type"] == "TASK_ACK"


# 14. -------------------------------------------------------------------
def test_conversation_state_ttl_and_cleanup(tmp_path):
    store = ConversationStore(tmp_path / "conversations.json", ttl_seconds=60)
    store.update("conv-old", last_task_id="TASK_OLD", user_id="42")
    data = store._load()
    data["conv-old"]["updated_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    store._save(data)
    store.update("conv-fresh", last_task_id="TASK_FRESH", user_id="42")

    assert store.get("conv-old") == {}  # stale - returned as empty, fail closed
    assert store.get("conv-fresh")["last_task_id"] == "TASK_FRESH"

    purged = store.purge_stale()
    assert purged == 1
    remaining = store._load()
    assert "conv-old" not in remaining and "conv-fresh" in remaining


# 15. -------------------------------------------------------------------
def test_no_regression_on_existing_button_driven_approval(tmp_path, monkeypatch):
    # The pre-existing metadata-driven flow (inline keyboard button callback)
    # must behave exactly as before - no text parsing involved at all.
    svc = service(tmp_path, monkeypatch)
    task_id = _waiting_approval_task(svc)
    response = svc.handle(message("", metadata={"task_id": task_id, "approval_action": "APPROVE"}))
    assert response["task_id"] == task_id
    assert response["status"] == "QUEUED"


def test_no_regression_on_existing_cancel_flow(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    task_id = _submit(svc, "TASK_CANCEL_NC3", "QUEUED")
    first = svc.handle(message(f"annulla {task_id}"))
    assert first["status"] == "CONFIRMATION_REQUIRED"
    second = svc.handle(message("conferma", metadata={"confirm_cancel": True, "task_id": task_id}))
    assert second["status"] == "CANCELLED"


def test_no_regression_on_existing_help_and_status_commands(tmp_path, monkeypatch):
    svc = service(tmp_path, monkeypatch)
    help_response = svc.handle(message("/help"))
    assert help_response["response_type"] == "ANSWER"
    status_response = svc.handle(message("/status"))
    assert status_response["details"]["view"] == "SYSTEM_STATUS"
