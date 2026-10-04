from datetime import datetime, timezone

import pytest

from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService
from jarvis_v1.telegram_adapter import TelegramAdapter


def message(text, conversation="c1", metadata=None):
    return {"message_id": f"m-{text}-{conversation}", "user_id": "42", "channel": "TEST",
            "conversation_id": conversation, "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_type": "TEXT", "text": text, "attachments": [], "reply_to": None,
            "request_class": "UNKNOWN", "priority": "NORMAL", "metadata": metadata or {}}


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


def create(service, conversation="c1"):
    return JarvisGateway(service).handle(message(
        "Crea una NEXUS task per analizzare una opportunità.", conversation=conversation))


def callback(adapter, update_id, data):
    return adapter.handle_update({"update_id": update_id, "callback_query": {
        "from": {"id": 42}, "message": {"chat": {"id": 99}}, "data": data}})


def flat_buttons(keyboard):
    return [button for row in keyboard for button in row]


def test_normal_task_card_and_contextual_read_buttons(service):
    response = create(service)
    rendered = TelegramAdapter.render_response(response)
    buttons = flat_buttons(TelegramAdapter.build_keyboard(response))
    assert "Stato: QUEUED" in rendered
    assert "Task:" in rendered and "Executor: NON ASSEGNATO" in rendered
    assert {button["text"] for button in buttons} >= {
        "Aggiorna stato", "Dettagli tecnici", "Lifecycle", "Diagnostica"}
    assert "Approva" not in {button["text"] for button in buttons}


def test_waiting_approval_buttons_call_existing_service_and_double_click_is_safe(service, adapter):
    task_id = create(service)["task_id"]
    service.queue.transition(task_id, "RUNNING")
    record = service.queue.transition(task_id, "WAITING_APPROVAL")
    response = JarvisGateway(service).handle(message("A che punto è?"))
    labels = {button["text"] for button in flat_buttons(adapter.build_keyboard(response))}
    assert {"Approva", "Rifiuta"} <= labels

    approved = callback(adapter, 101, f"J1|AP|{task_id}|A")
    stale = callback(adapter, 102, f"J1|AP|{task_id}|A")
    assert record["state"] == "WAITING_APPROVAL"
    assert approved["status"] == "QUEUED"
    assert stale["response_type"] == "ERROR" and stale["status"] == "QUEUED"
    assert sum(event["event_type"] == "APPROVAL_GRANTED"
               for event in service.ledger.read_for_task(task_id)) == 1


def test_reject_callback_uses_service_and_is_state_guarded(service, adapter):
    task_id = create(service)["task_id"]
    service.queue.transition(task_id, "RUNNING")
    service.queue.transition(task_id, "WAITING_APPROVAL")
    rejected = callback(adapter, 103, f"J1|RJ|{task_id}|A")
    assert rejected["status"] == "FAILED"
    assert any(event["event_type"] == "APPROVAL_REJECTED"
               for event in service.ledger.read_for_task(task_id))


def test_orphaned_blocked_card_can_resume_through_service_only(service, adapter):
    task_id = create(service)["task_id"]
    service.queue.transition(task_id, "RUNNING")
    service.queue.transition(task_id, "BLOCKED", dispatch_last_error="ORPHANED_RUNNING_AFTER_RESTART",
                             recovery={"classification": "ORPHANED_RUNNING_AFTER_RESTART"})
    response = JarvisGateway(service).handle(message("A che punto è?"))
    labels = {button["text"] for button in flat_buttons(adapter.build_keyboard(response))}
    assert "Riprendi" in labels
    resumed = callback(adapter, 104, f"J1|RS|{task_id}|B")
    assert resumed["status"] == "QUEUED"
    assert any(event["event_type"] == "TASK_RESUMED"
               for event in service.ledger.read_for_task(task_id))


def test_unsupported_recovery_never_exposes_or_executes_resume(service, adapter):
    task_id = create(service)["task_id"]
    service.queue.transition(task_id, "BLOCKED",
                             recovery={"classification": "DISPATCH_EXECUTION_AMBIGUOUS"})
    response = JarvisGateway(service).handle(message("A che punto è?"))
    assert "Riprendi" not in {b["text"] for b in flat_buttons(adapter.build_keyboard(response))}
    refused = callback(adapter, 105, f"J1|RS|{task_id}|B")
    assert refused["response_type"] == "ERROR"
    assert service.queue.get(task_id)["state"] == "BLOCKED"


def test_technical_details_show_classification_target_verifier_and_decision(service, adapter):
    task_id = create(service)["task_id"]
    service.queue.transition(task_id, "RUNNING", executor="LOCAL_STRONG_MINISTRAL3B")
    service.queue.transition(task_id, "BLOCKED", dispatch_attempts=2, retry_count=1,
                             recovery={"classification": "ORPHANED_RUNNING_AFTER_RESTART"})
    service.queue.annotate(task_id, escalation={"classification": "CAPABILITY_MISMATCH",
                                                "target": "CODEX_TIER4"},
                           result_packet={"decision": "ESCALATE",
                                          "verifier": {"passed": False, "errors": ["gap"]}})
    response = callback(adapter, 106, f"J1|TD|{task_id}|B")
    rendered = adapter.render_response(response)
    assert "Escalation classification: CAPABILITY_MISMATCH" in rendered
    assert "Escalation target/provider: CODEX_TIER4" in rendered
    assert "Result decision: ESCALATE" in rendered
    assert "Verifier: False" in rendered


def test_lifecycle_is_paginated_and_has_show_more(service, adapter):
    task_id = create(service)["task_id"]
    for index in range(14):
        service.ledger.append("TASK_STATUS_REQUESTED", task_id, {"attempt": index}, actor="test")
    first = callback(adapter, 107, f"J1|LC|{task_id}|0")
    assert len(first["details"]["lifecycle"]) == 6
    assert first["details"]["lifecycle_has_more"] is True
    assert "Mostra altro" in {b["text"] for b in flat_buttons(adapter.build_keyboard(first))}
    second = callback(adapter, 108, f"J1|LC|{task_id}|1")
    assert second["details"]["lifecycle_page"] == 1
    assert second["details"]["lifecycle"] != first["details"]["lifecycle"]


def test_agents_are_real_rows_with_navigation(service, adapter):
    response = JarvisGateway(service).handle(message("/agents"))
    rendered = adapter.render_response(response)
    assert response["details"]["view"] == "AGENT_LIST"
    assert response["details"]["items"]
    first = response["details"]["items"][0]
    assert first["agent_id"] in rendered
    assert first["role"] in rendered
    assert first["capabilities"][0] in rendered
    details = callback(adapter, 109, f"J1|AD|{first['agent_id']}")
    assert details["details"]["view"] == "AGENT_DETAIL"
    labels = {b["text"] for b in flat_buttons(adapter.build_keyboard(details))}
    assert {"Capabilities", "Provider status"} <= labels


def test_unknown_fallback_has_quick_actions_and_existing_commands_still_work(service, adapter):
    response = JarvisGateway(service).handle(message("blorptastic"))
    labels = {b["text"] for b in flat_buttons(adapter.build_keyboard(response))}
    assert labels == {"Stato NEXUS", "Le mie task", "Agenti", "Help"}
    status = callback(adapter, 110, "J1|Q|STATUS")
    assert status["details"]["view"] == "SYSTEM_STATUS"
    for command in ("/start", "/help", "/status", "/tasks", "/approvals", "/agents"):
        assert JarvisGateway(service).handle(message(command))["response_type"] == "ANSWER"

