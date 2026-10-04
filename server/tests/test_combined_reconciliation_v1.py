"""Combined validation after rebasing NATURAL_CONVERSATION_V3_ROUTING_RELIABILITY
on top of TELEGRAM_INTERACTIVE_UX_V1 (Codex). Both patches touch
server/jarvis_v1/service.py extensively (approval(), resume_orphaned(),
create_task(), handle(), command()) - git's 3-way merge produced no textual
conflict, but that alone proves nothing about semantic correctness. This
file specifically exercises the overlap: UI callbacks (Codex) AND natural-
language contextual mutations (this task) driving the SAME underlying
service methods, including the one scenario neither existing suite covered
on its own - the Dynamic Specialist Review staying reachable after a reject
that arrives through the NEW UI callback path.
"""
from datetime import datetime, timezone

import pytest

from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService
from jarvis_v1.telegram_adapter import TelegramAdapter
from orchestrator_v1.core.provider_connector import MockProviderAdapter, ProviderConnectorV1


def message(text, conversation="c1", metadata=None, user_id="42"):
    return {"message_id": f"m-{abs(hash((text, conversation)))}", "user_id": user_id,
            "channel": "TEST", "conversation_id": conversation,
            "timestamp": datetime.now(timezone.utc).isoformat(), "input_type": "TEXT",
            "text": text, "attachments": [], "reply_to": None, "request_class": "UNKNOWN",
            "priority": "NORMAL", "metadata": metadata or {}}


@pytest.fixture
def service(tmp_path, monkeypatch):
    svc = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"),
                        str(tmp_path / "conversation.json"))
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    return svc


@pytest.fixture
def adapter(service, tmp_path):
    return TelegramAdapter(service, tmp_path / "seen.json", token="token", allowed_users=["42"],
                           gateway=JarvisGateway(service))


def callback(adapter, update_id, data):
    return adapter.handle_update({"update_id": update_id, "callback_query": {
        "from": {"id": 42}, "message": {"chat": {"id": 99}}, "data": data}})


def flat_buttons(keyboard):
    return [button for row in keyboard for button in row]


def _manifest(task_id, **changes):
    value = {
        "task_id": task_id, "title": "Combined recon patch", "objective": "Update src/sample.py",
        "task_type": "CODE", "work_type": "complex_code", "priority": "NORMAL",
        "risk_level": "A1", "scientific_risk": "NONE", "code_risk": "HIGH",
        "financial_risk": "NONE", "required_capabilities": ["small_python_functions"],
        "deterministic_tools_available": False, "repo_scope": "task-scoped",
        "files_allowed": ["src/sample.py"], "files_forbidden": [".env", "MQL5/**"],
        "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
        "success_criteria": ["bounded patch verified"], "verifier": "free_coding_worker_v1",
        "estimated_complexity": "SMALL", "estimated_runtime": "5m", "premium_allowed": True,
        "preferred_executor": "TIER1_LOCAL_CHEAP", "fallback_executors": ["TIER4_CODEX"],
        "approval_required": "REVIEW_REQUIRED", "created_by": "jarvis:42",
        "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
        "account_scope_id": None,
    }
    value.update(changes)
    return value


def _waiting_approval_programming_task(service, task_id="TASK_WA_RECON"):
    value = _manifest(task_id)
    service.orchestrator.submit(value, action="conversational_programming",
                                action_params={"conversation_id": "c1"})
    service.queue.transition(task_id, "RUNNING", executor="TEST")
    service.queue.transition(task_id, "WAITING_APPROVAL",
                             proposed_patch={"changes": [{"path": "src/sample.py",
                                                          "content": "VALUE = 2\n"}], "test_results": []})
    return task_id


# 1-2. Approve/Reject callbacks on a valid card ------------------------------
def test_approve_callback_on_valid_card(service, adapter):
    task_id = _waiting_approval_programming_task(service)
    approved = callback(adapter, 1, f"J1|AP|{task_id}|A")
    assert approved["status"] == "QUEUED"


def test_reject_callback_on_valid_card(service, adapter):
    task_id = _waiting_approval_programming_task(service)
    rejected = callback(adapter, 2, f"J1|RJ|{task_id}|A")
    assert rejected["status"] == "FAILED"  # no provider_connector wired in this fixture


# 3. Stale card -> no mutation ------------------------------------------------
def test_stale_card_blocks_mutation(service, adapter):
    task_id = _waiting_approval_programming_task(service)
    service.queue.transition(task_id, "QUEUED")  # state moved on since the card was rendered
    stale = callback(adapter, 3, f"J1|AP|{task_id}|A")  # card still claims WAITING_APPROVAL
    assert stale["response_type"] == "ERROR"
    assert service.queue.get(task_id)["state"] == "QUEUED"  # untouched by the stale click


# 4-5. Natural-language approve/reject via reference -------------------------
def test_approva_quella_through_full_gateway(service):
    task_id = _waiting_approval_programming_task(service)
    service.conversation_store.update("c1", last_task_id=task_id, user_id="42")
    response = JarvisGateway(service).handle(message("approva quella"))
    assert response["task_id"] == task_id and response["status"] == "QUEUED"


def test_rifiutala_through_full_gateway(service):
    task_id = _waiting_approval_programming_task(service)
    service.conversation_store.update("c1", last_task_id=task_id, user_id="42")
    response = JarvisGateway(service).handle(message("rifiutala"))
    assert response["task_id"] == task_id and response["status"] == "FAILED"


# 6-7. Resume (contextual and explicit) --------------------------------------
def test_riprendi_quella(service):
    task_id = "TASK_ORPHAN_RECON"
    value = _manifest(task_id)
    service.orchestrator.submit(value, action="conversational_programming",
                                action_params={"conversation_id": "c1"})
    service.queue.transition(task_id, "RUNNING", executor="TEST")
    service.queue.transition(task_id, "BLOCKED",
                             recovery={"classification": "ORPHANED_RUNNING_AFTER_RESTART"},
                             dispatch_last_error="ORPHANED_RUNNING_AFTER_RESTART")
    service.conversation_store.update("c1", last_task_id=task_id, user_id="42")
    response = JarvisGateway(service).handle(message("riprendi quella"))
    assert response["task_id"] == task_id and response["status"] == "QUEUED"


def test_riprendi_task_x_explicit(service):
    task_id = "TASK_ORPHAN_RECON_2"
    value = _manifest(task_id)
    service.orchestrator.submit(value, action="conversational_programming",
                                action_params={"conversation_id": "c1"})
    service.queue.transition(task_id, "RUNNING", executor="TEST")
    service.queue.transition(task_id, "BLOCKED",
                             recovery={"classification": "ORPHANED_RUNNING_AFTER_RESTART"},
                             dispatch_last_error="ORPHANED_RUNNING_AFTER_RESTART")
    response = JarvisGateway(service).handle(message(f"riprendi {task_id}"))
    assert response["task_id"] == task_id and response["status"] == "QUEUED"


# 8. Provider preference constrains a new task -------------------------------
def test_no_premium_then_new_task_has_correct_policy(service):
    JarvisGateway(service).handle(message("non usare premium"))
    response = JarvisGateway(service).handle(message("sistema il bug nel repo"))
    record = service.queue.get(response["task_id"])
    assert record["manifest"]["work_type"] == "complex_code"
    assert record["manifest"]["premium_allowed"] is False


# 9. "più tecnico" after a UI task card ---------------------------------------
def test_piu_tecnico_after_task_card(service, adapter):
    task_id = _waiting_approval_programming_task(service)
    # First, a UI card is shown (TASK_STATUS ui_action), setting last_task_id.
    card = callback(adapter, 4, f"J1|TS|{task_id}|A")
    assert card["task_id"] == task_id
    response = JarvisGateway(service).handle(message("più tecnico"))
    assert response["task_id"] == task_id
    assert "lifecycle" in response["details"]


# 10. Dynamic Specialist Review still reachable after a UI-driven reject -----
def test_dynamic_specialist_review_active_after_ui_reject_callback(service, adapter):
    """The one scenario neither pre-existing suite covered alone: a reject
    arriving through the NEW Telegram UI callback path (Codex) must still
    reach ProviderConnectorV1.request_review() (this task's own rework), not
    the plain FAILED dead-end - proving the rebase didn't silently drop
    either side's behaviour."""
    task_id = _waiting_approval_programming_task(service)
    claude = MockProviderAdapter("CLAUDE", "AVAILABLE", result={
        "problems_found": ["x"], "rework_instructions": "fix it",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    connector = ProviderConnectorV1(service.orchestrator, {"CLAUDE": claude})
    service.set_provider_connector(connector)

    rejected = callback(adapter, 5, f"J1|RJ|{task_id}|A")
    assert rejected["status"] == "QUEUED"  # handed back for local rework, never FAILED
    assert claude.calls  # the reviewer was actually invoked
    record = service.queue.get(task_id)
    assert record["action_params"]["rework_instructions"]
    events = [e["event_type"] for e in service.ledger.read_for_task(task_id)]
    assert "HUMAN_REJECTED" in events and "REVIEW_COMPLETED" in events


def test_dynamic_specialist_review_active_after_natural_language_reject(service):
    """Same guarantee through the natural-language 'rifiutala' door."""
    task_id = _waiting_approval_programming_task(service)
    service.conversation_store.update("c1", last_task_id=task_id, user_id="42")
    claude = MockProviderAdapter("CLAUDE", "AVAILABLE", result={
        "problems_found": ["x"], "rework_instructions": "fix it differently",
        "allowed_paths": ["src/sample.py"], "required_tests": [], "risks": []})
    connector = ProviderConnectorV1(service.orchestrator, {"CLAUDE": claude})
    service.set_provider_connector(connector)

    response = JarvisGateway(service).handle(message("rifiutala"))
    assert response["status"] == "QUEUED"
    assert claude.calls


# Real production incident, 2026-10-04: "Usa groq"/"Usa codex" sent via
# Telegram got NO reply at all. jarvis-response.schema.json's response_type
# enum was extended for PREFERENCE_SET/CLARIFICATION_REQUIRED, but
# jarvis-message.schema.json's request_class enum (validated by
# JarvisGateway.handle() on the INCOMING message, built by
# TelegramAdapter.parse_update() before the service ever runs) was not -
# every PROVIDER_PREFERENCE/NOTIFICATION_PREFERENCE message raised
# ValueError inside the webhook, which app.py maps to an HTTP 422 with no
# Telegram send() ever attempted. All of this only surfaces through the
# REAL TelegramAdapter.handle_update() webhook path - calling
# JarvisService.handle() or even JarvisGateway.handle() directly with a
# hand-built message (as every other test in this file and in
# test_natural_conversation_v3.py does) never exercises parse_update() and
# therefore never catches it. These tests go through handle_update() with a
# raw Telegram update dict specifically so this class of bug cannot hide
# behind a hand-built message again.
def _raw_text_update(update_id, text, chat_id=99, user_id=77):
    return {"update_id": update_id, "message": {"chat": {"id": chat_id},
            "from": {"id": user_id}, "text": text}}


def test_provider_preference_text_message_survives_the_real_webhook_path(tmp_path, monkeypatch):
    svc = JarvisService(str(tmp_path / "q2.json"), str(tmp_path / "l2.jsonl"),
                        str(tmp_path / "c2.json"))
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    adapter = TelegramAdapter(svc, tmp_path / "seen2.json", token="x", allowed_users=["77"],
                              gateway=JarvisGateway(svc))
    for i, text in enumerate(["Usa groq", "Usa codex", "non usare premium"]):
        response = adapter.handle_update(_raw_text_update(3000 + i, text))
        assert response["response_type"] == "PREFERENCE_SET"


def test_notification_preference_text_message_survives_the_real_webhook_path(tmp_path, monkeypatch):
    svc = JarvisService(str(tmp_path / "q3.json"), str(tmp_path / "l3.jsonl"),
                        str(tmp_path / "c3.json"))
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    adapter = TelegramAdapter(svc, tmp_path / "seen3.json", token="x", allowed_users=["77"],
                              gateway=JarvisGateway(svc))
    for i, text in enumerate(["dimmi solo quando finisce", "non disturbarmi",
                              "avvisami se serve approvazione"]):
        response = adapter.handle_update(_raw_text_update(4000 + i, text))
        assert response["response_type"] == "PREFERENCE_SET"
