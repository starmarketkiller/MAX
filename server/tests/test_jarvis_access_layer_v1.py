import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as backend
from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService, classify, classify_work_type
from jarvis_v1.telegram_adapter import TelegramAdapter
from jarvis_v1.notifications import NotificationEngine
from jarvis_v1 import configure_telegram_webhook as webhook_config
from core.dispatcher import DurableQueueDispatcher
from core import context_packet


def message(text, cls="UNKNOWN", conversation="c1", metadata=None):
    return {"message_id": f"m-{abs(hash(text))}", "user_id": "42", "channel": "TEST",
            "conversation_id": conversation, "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_type": "TEXT", "text": text, "attachments": [], "reply_to": None,
            "request_class": cls, "priority": "NORMAL", "metadata": metadata or {}}


@pytest.fixture
def service(tmp_path, monkeypatch):
    svc = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    return svc


def test_query_reads_real_ledgers_and_never_calls_premium(service):
    response = JarvisGateway(service).handle(message("Jarvis, cosa è successo oggi?"))
    assert response["response_type"] == "ANSWER"
    assert response["details"]["premium_calls"] == 0
    assert response["generated_by"] == "jarvis_deterministic_fallback"
    assert response["status"] == "PARTIAL"


def test_task_followup_and_router_ownership(service):
    created = JarvisGateway(service).handle(message(
        "Jarvis, crea una NEXUS TASK per analizzare l'opportunità Review Kit QR/NFC."))
    assert created["task_id"] and created["status"] == "QUEUED"
    record = service.queue.get(created["task_id"])
    assert record["executor"] is None  # Jarvis never selects Claude/Codex/Ministral.
    assert record["manifest"]["work_type"] == "business_analysis"
    assert created["details"]["review_required"] is True
    follow = JarvisGateway(service).handle(message("A che punto è?", conversation="c1"))
    assert follow["task_id"] == created["task_id"] and follow["status"] == "QUEUED"


def test_real_orchestrator_approval_transition(service):
    created = JarvisGateway(service).handle(message("Crea una NEXUS TASK per analizzare opportunità."))
    task_id = created["task_id"]
    service.queue.transition(task_id, "RUNNING")
    service.queue.transition(task_id, "WAITING_APPROVAL")
    approved = JarvisGateway(service).handle(message("APPROVE", "APPROVAL", metadata={
        "task_id": task_id, "approval_action": "APPROVE"}))
    assert approved["status"] == "QUEUED"
    assert any(e["event_type"] == "APPROVAL_GRANTED" for e in service.ledger.read_for_task(task_id))


def test_rejection_and_dependency_are_real_queue_transitions(service):
    parent = JarvisGateway(service).handle(message("Crea una NEXUS TASK per analizzare opportunità A."))
    child = JarvisGateway(service).handle(message("Crea una NEXUS TASK per analizzare opportunità B.",
        conversation="c2", metadata={"dependencies": [parent["task_id"]]}))
    assert child["status"] == "WAITING_DEPENDENCY"
    service.queue.transition(parent["task_id"], "RUNNING")
    service.queue.transition(parent["task_id"], "WAITING_APPROVAL")
    rejected = JarvisGateway(service).handle(message("REJECT", "APPROVAL", metadata={
        "task_id": parent["task_id"], "approval_action": "REJECT"}))
    assert rejected["status"] == "FAILED"


def test_telegram_auth_duplicate_malformed_and_rate_limit(service, tmp_path):
    adapter = TelegramAdapter(service, tmp_path / "seen.json", token="token", allowed_users=["42"],
                              gateway=JarvisGateway(service))
    update = {"update_id": 7, "message": {"from": {"id": 42}, "chat": {"id": 99},
                                              "text": "Jarvis, cosa è successo oggi?"}}
    assert adapter.handle_update(update)["response_type"] == "ANSWER"
    assert adapter.handle_update(update)["status"] == "DUPLICATE"
    with pytest.raises(PermissionError):
        adapter.handle_update({"update_id": 8, "message": {"from": {"id": 13},
                              "chat": {"id": 99}, "text": "cosa è successo oggi?"}})
    denied = [e for e in service.ledger.read_all() if e["event_type"] == "TELEGRAM_ACCESS_DENIED"]
    assert denied and denied[-1]["payload"]["authorized"] is False
    assert "13" not in json.dumps(denied[-1])
    with pytest.raises(ValueError): adapter.handle_update({"update_id": 9})
    adapter._rate["42"] = [__import__("time").time()] * 20
    with pytest.raises(RuntimeError):
        adapter.handle_update({"update_id": 10, "message": {"from": {"id": 42},
                              "chat": {"id": 99}, "text": "cosa è successo oggi?"}})


def test_provider_status_and_no_secret_leakage(service, tmp_path):
    agents = service.agents()
    assert agents and set(agents[0]) == {"agent_id", "provider", "status", "availability", "quota_state"}
    adapter = TelegramAdapter(service, tmp_path / "seen.json", token="super-secret-token", allowed_users=["42"])
    adapter.handle_update({"update_id": 11, "message": {"from": {"id": 42},
                          "chat": {"id": 99}, "text": "cosa è successo oggi?"}})
    assert "super-secret-token" not in (tmp_path / "seen.json").read_text()
    assert "super-secret-token" not in (tmp_path / "ledger.jsonl").read_text()


def test_premium_exhausted_does_not_block_local_query(service, monkeypatch):
    monkeypatch.setattr("jarvis_v1.service.load_registry", lambda: {"agents": [{
        "agent_id": "TIER4_CODEX", "provider": "premium", "quota_state": "EXHAUSTED",
        "availability": "ONLINE"}]})
    result = JarvisGateway(service).handle(message("Cosa è successo oggi?"))
    assert result["details"]["premium_calls"] == 0
    assert result["details"]["agents"][0]["status"] == "EXHAUSTED"


def test_notification_policy_keeps_info_in_ledger(service, tmp_path):
    adapter = TelegramAdapter(service, tmp_path / "seen.json", token="", allowed_users=["42"])
    engine = NotificationEngine(service, adapter)
    result = engine.notify("INFO", "99", {"task_id": None, "priority": "INFO", "summary": "x"})
    assert result == {"sent": True, "channel": "LEDGER", "aggregated": True}
    assert service.ledger.read_all()[-1]["event_type"] == "NOTIFICATION_SENT"


def test_non_text_and_malformed_message_fail_closed(service):
    voice = message("audio"); voice["input_type"] = "VOICE"
    assert JarvisGateway(service).handle(voice)["status"] == "UNAVAILABLE"
    malformed = message("x"); malformed.pop("conversation_id")
    with pytest.raises(ValueError): JarvisGateway(service).handle(malformed)


def test_version_and_jarvis_routes_are_protected(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "api.db")); backend.init_db()
    with TestClient(backend.app) as client:
        version = client.get("/api/version")
        assert version.status_code == 200 and "git_sha" in version.json()
        assert client.get("/api/jarvis/activity").status_code == 401
        assert client.get("/api/jarvis/agents").status_code == 401
        assert client.post("/api/jarvis/telegram/webhook", json={"update_id": 1}).status_code == 401


def test_intent_and_work_type_classification_are_separate():
    assert classify("Crea una task per un riassunto di stato") == "TASK_REQUEST"
    assert classify_work_type("Crea una task per un riassunto di stato") == "routine_summary"
    assert classify_work_type("Analizza l'opportunità Review Kit QR/NFC") == "business_analysis"
    assert classify("REJECT", {"approval_action": "REJECT"}) == "REJECTION"


def test_telegram_configuration_is_fail_safe_and_secret_free(service, tmp_path):
    adapter = TelegramAdapter(service, tmp_path / "seen.json", token="secret-token", allowed_users=["42"])
    ready = adapter.configuration_status(webhook_secret_configured=True)
    partial = adapter.configuration_status(webhook_secret_configured=False)
    assert ready == {"configuration_state": "READY", "configured": True,
                     "webhook_ready": True, "allowed_user_count": 1, "token_exposed": False}
    assert partial["configuration_state"] == "PARTIAL" and partial["webhook_ready"] is False
    assert "secret-token" not in json.dumps(ready)


def test_webhook_set_and_verify_are_idempotent_and_secret_safe(monkeypatch, capsys):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-secret")
    monkeypatch.setenv("JARVIS_TELEGRAM_WEBHOOK_SECRET", "hook-secret")
    monkeypatch.setenv("NEXUS_PUBLIC_URL", "https://nexus.example")
    calls = []
    def fake_telegram(token, method, payload=None):
        calls.append((token, method, payload))
        if method == "getWebhookInfo":
            return {"ok": True, "result": {"url": "https://nexus.example/api/jarvis/telegram/webhook",
                                             "pending_update_count": 0}}
        return {"ok": True, "description": "Webhook was set"}
    monkeypatch.setattr(webhook_config, "_telegram", fake_telegram)
    assert webhook_config.main(["set"]) == 0
    assert webhook_config.main(["verify"]) == 0
    output = capsys.readouterr().out
    assert "bot-secret" not in output and "hook-secret" not in output
    assert [call[1] for call in calls] == ["setWebhook", "getWebhookInfo"]


def test_telegram_webhook_invalid_secret_and_authorized_delivery(tmp_path, monkeypatch):
    svc = JarvisService(str(tmp_path / "webhook-queue.json"), str(tmp_path / "webhook-ledger.jsonl"))
    adapter = TelegramAdapter(svc, tmp_path / "webhook-seen.json", token="token", allowed_users=["42"],
                              gateway=JarvisGateway(svc))
    monkeypatch.setattr(backend, "JARVIS_TELEGRAM", adapter)
    monkeypatch.setenv("JARVIS_TELEGRAM_WEBHOOK_SECRET", "hook-secret")
    monkeypatch.setattr(adapter, "send", lambda chat_id, response: {"sent": True, "reason": None})
    update = {"update_id": 77, "message": {"from": {"id": 42}, "chat": {"id": 99},
                                             "text": "Jarvis, cosa è successo oggi?"}}
    with TestClient(backend.app) as client:
        assert client.post("/api/jarvis/telegram/webhook", json=update,
                           headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"}).status_code == 401
        accepted = client.post("/api/jarvis/telegram/webhook", json=update,
                               headers={"X-Telegram-Bot-Api-Secret-Token": "hook-secret"})
        assert accepted.status_code == 200 and accepted.json()["response"]["response_type"] == "ANSWER"
        duplicate = client.post("/api/jarvis/telegram/webhook", json=update,
                                headers={"X-Telegram-Bot-Api-Secret-Token": "hook-secret"})
        assert duplicate.json()["response"]["status"] == "DUPLICATE"


def test_completed_task_with_verified_producer_output_delivers_finalized_result(service):
    """NEXUS TASK #0009 - Jarvis non consegna mai il risultato grezzo: un
    task COMPLETED con verifier.passed=True su un work_type con
    review_required=False deve arrivare a FINALIZED tramite la pipeline.
    (Il work_type di default di Jarvis, business_analysis, RICHIEDE review
    per costruzione - vedi test successivo - quindi qui si forza
    esplicitamente il caso senza review, esattamente come farebbe in
    futuro un work_type dichiarato via manifest metadata.)"""
    created = JarvisGateway(service).handle(message(
        "Jarvis, crea una NEXUS TASK per un riassunto di routine."))
    task_id = created["task_id"]
    service.queue.transition(task_id, "RUNNING")
    service.queue.transition(task_id, "COMPLETED", result_packet={
        "task_id": task_id, "executor": "LOCAL_FAST_MINISTRAL3B",
        "verifier": {"ran": True, "passed": True, "errors": []},
        "files_read": ["a.md"], "files_changed": [], "tests": {"ran": False, "passed": 0, "failed": 0}})
    follow = JarvisGateway(service).handle(message("A che punto è?", conversation="c1"))
    assert follow["status"] == "FINALIZED"
    assert follow["details"]["final_result_packet"]["premium_calls"] == 0
    assert "TASK COMPLETED" in follow["summary"]


def test_completed_task_needing_unconnected_review_is_escalation_ready_for_manual_delivery(service):
    """work_type di default (business_analysis) impone review_required=True -
    con nessun provider STRATEGIC_GENERALIST connesso nel registry reale,
    Jarvis deve dirlo esplicitamente, mai fingere un completamento."""
    created = JarvisGateway(service).handle(message(
        "Jarvis, crea una NEXUS TASK per analizzare l'opportunità Review Kit QR/NFC."))
    task_id = created["task_id"]
    service.queue.transition(task_id, "RUNNING")
    service.queue.transition(task_id, "COMPLETED", result_packet={
        "task_id": task_id, "executor": "LOCAL_FAST_MINISTRAL3B",
        "verifier": {"ran": True, "passed": True, "errors": []}})
    follow = JarvisGateway(service).handle(message("A che punto è?", conversation="c1"))
    assert follow["status"] == "ESCALATION_READY_FOR_MANUAL_DELIVERY"
    assert "review" in follow["summary"].lower()
    assert "pacchetto di escalation" in follow["summary"]


def test_completed_task_review_pipeline_result_is_cached_across_followups(service, monkeypatch):
    created = JarvisGateway(service).handle(message("Jarvis, crea una NEXUS TASK per un riassunto di stato."))
    task_id = created["task_id"]
    service.queue.transition(task_id, "RUNNING")
    service.queue.transition(task_id, "COMPLETED", result_packet={
        "task_id": task_id, "executor": "LOCAL_FAST_MINISTRAL3B",
        "verifier": {"ran": True, "passed": True, "errors": []}})
    calls = {"n": 0}
    from review_engine import process_work_product as _real
    def _counting(*a, **k):
        calls["n"] += 1
        return _real(*a, **k)
    monkeypatch.setattr("jarvis_v1.service.process_work_product", _counting)
    JarvisGateway(service).handle(message("A che punto è?", conversation="c1"))
    JarvisGateway(service).handle(message("A che punto è ora?", conversation="c1",
                                         metadata={"task_id": task_id}))
    assert calls["n"] == 1


def test_authenticated_jarvis_api_uses_real_service(tmp_path, monkeypatch):
    svc = JarvisService(str(tmp_path / "api-queue.json"), str(tmp_path / "api-ledger.jsonl"))
    monkeypatch.setattr(backend, "JARVIS_SERVICE", svc)
    monkeypatch.setattr(backend, "JARVIS_GATEWAY", JarvisGateway(svc))
    monkeypatch.setattr(backend, "JARVIS_TELEGRAM", TelegramAdapter(
        svc, tmp_path / "api-seen.json", token="token", allowed_users=["42"]))
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "auth.db")); backend.init_db()
    with TestClient(backend.app) as client:
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        body = message("Crea una NEXUS TASK per analizzare opportunità API.")
        created = client.post("/api/jarvis/message", json=body, headers=headers)
        assert created.status_code == 200
        task_id = created.json()["task_id"]
        assert client.get(f"/api/jarvis/tasks/{task_id}", headers=headers).status_code == 200
        for path in ("activity", "agents", "approvals", "telegram/status", "dispatcher/status"):
            assert client.get(f"/api/jarvis/{path}", headers=headers).status_code == 200
        diagnostics = client.get(f"/api/jarvis/tasks/{task_id}/diagnostics", headers=headers)
        assert diagnostics.status_code == 200
        assert diagnostics.json()["action"] == "jarvis_task"


def test_conversation_v2_persists_last_task_and_recovers_after_restart(tmp_path, monkeypatch):
    queue = tmp_path / "queue.json"
    ledger = tmp_path / "ledger.jsonl"
    context = tmp_path / "conversation.json"
    first = JarvisService(queue, ledger, context)
    created = JarvisGateway(first).handle(message("Crea una task per analizzare opportunità."))
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    restarted = JarvisService(queue, ledger, context)
    follow = JarvisGateway(restarted).handle(message("A che punto è?"))
    assert follow["task_id"] == created["task_id"]
    assert follow["status"] == "QUEUED"


def test_missing_context_retrieves_latest_compatible_task(tmp_path):
    svc = JarvisService(tmp_path / "queue.json", tmp_path / "ledger.jsonl",
                        tmp_path / "context-a.json")
    created = JarvisGateway(svc).handle(message("Crea una task per analizzare opportunità."))
    recovered = JarvisService(tmp_path / "queue.json", tmp_path / "ledger.jsonl",
                              tmp_path / "context-b.json")
    follow = JarvisGateway(recovered).handle(message("A che punto è?"))
    assert follow["task_id"] == created["task_id"]


def test_task_details_expose_failure_diagnostics_without_guessing(service):
    created = JarvisGateway(service).handle(message("Crea una task per analizzare opportunità."))
    task_id = created["task_id"]
    service.queue.transition(task_id, "BLOCKED", dispatch_last_error="RuntimeError: exact failure",
                             recovery={"classification": "DISPATCH_EXECUTION_AMBIGUOUS"})
    details = JarvisGateway(service).handle(message(
        f"Mostrami i dettagli tecnici della task {task_id}", conversation="new"))
    assert details["task_id"] == task_id
    assert details["status"] == "BLOCKED"
    assert details["details"]["dispatch_last_error"] == "RuntimeError: exact failure"
    assert details["details"]["recovery"]["classification"] == "DISPATCH_EXECUTION_AMBIGUOUS"


def test_cancel_requires_confirmation_and_never_cancels_running(service):
    created = JarvisGateway(service).handle(message("Crea una task per analizzare opportunità."))
    task_id = created["task_id"]
    ask = JarvisGateway(service).handle(message(f"Annulla la task {task_id}"))
    assert ask["status"] == "CONFIRMATION_REQUIRED"
    assert service.queue.get(task_id)["state"] == "QUEUED"
    done = JarvisGateway(service).handle(message(
        f"Conferma annullamento task {task_id}", metadata={"task_id": task_id, "confirm_cancel": True}))
    assert done["status"] == "CANCELLED"
    assert any(e["event_type"] == "TASK_CANCELLED" for e in service.ledger.read_for_task(task_id))

    running = JarvisGateway(service).handle(message("Crea una task per analizzare opportunità B.", conversation="c2"))
    service.queue.transition(running["task_id"], "RUNNING")
    JarvisGateway(service).handle(message(f"Annulla la task {running['task_id']}", conversation="c2"))
    refused = JarvisGateway(service).handle(message(
        f"Conferma annullamento task {running['task_id']}", conversation="c2",
        metadata={"task_id": running["task_id"], "confirm_cancel": True}))
    assert refused["status"] == "RUNNING"


@pytest.mark.parametrize("command", ["/start", "/help", "/status", "/tasks", "/approvals", "/agents"])
def test_conversation_commands_are_useful_not_unavailable(service, command):
    response = JarvisGateway(service).handle(message(command))
    assert response["response_type"] == "ANSWER"
    assert "unavailable" not in response["summary"].lower()


def test_unknown_request_gets_conversational_fallback(service):
    response = JarvisGateway(service).handle(message("blorptastic"))
    assert response["response_type"] == "ANSWER"
    assert response["status"] == "PARTIAL"
    assert response["actions"][0]["type"] == "HELP"


def test_telegram_cancel_callback_and_details(service, tmp_path):
    created = JarvisGateway(service).handle(message("Crea una task per analizzare opportunità."))
    adapter = TelegramAdapter(service, tmp_path / "seen-v2.json", token="token", allowed_users=["42"],
                              gateway=JarvisGateway(service))
    update = {"update_id": 901, "callback_query": {"from": {"id": 42},
              "message": {"chat": {"id": 99}}, "data": f"DETAILS:{created['task_id']}"}}
    response = adapter.handle_update(update)
    assert response["task_id"] == created["task_id"]
    assert "lifecycle" in response["details"]


def test_tasks_command_projects_rich_recent_task_rows(service):
    first = JarvisGateway(service).handle(message("Crea una task per analizzare opportunità Alpha."))
    second = JarvisGateway(service).handle(message(
        "Crea una task per analizzare opportunità Beta.", conversation="c2"))
    service.queue.transition(first["task_id"], "CANCELLED")
    response = JarvisGateway(service).handle(message("/tasks"))
    assert response["details"]["view"] == "TASK_LIST"
    assert len(response["details"]["items"]) == 2
    assert all(set(("task_id", "state", "title", "updated_at")) <= set(item)
               for item in response["details"]["items"])
    rendered = TelegramAdapter.render_response(response)
    assert first["task_id"] in rendered and second["task_id"] in rendered
    assert "opportunità Alpha" in rendered and "CANCELLED" in rendered


def test_status_command_includes_queue_counts_and_dispatcher(service):
    created = JarvisGateway(service).handle(message("Crea una task per analizzare opportunità."))
    service.queue.transition(created["task_id"], "BLOCKED")
    service.set_dispatcher_status_provider(lambda: {
        "enabled": True, "running": True, "status": "RUNNING", "max_concurrency": 1})
    response = JarvisGateway(service).handle(message("/status"))
    assert response["details"]["task_states"]["BLOCKED"] == 1
    assert response["details"]["dispatcher"]["status"] == "RUNNING"
    rendered = TelegramAdapter.render_response(response)
    assert "Blocked: 1" in rendered and "Dispatcher: RUNNING" in rendered


def test_blocked_followup_automatically_exposes_cause_and_next_step(service):
    created = JarvisGateway(service).handle(message("Crea una task per analizzare opportunità."))
    task_id = created["task_id"]
    service.queue.transition(task_id, "BLOCKED",
        dispatch_last_error="RuntimeError: worker interrupted",
        recovery={"classification": "DISPATCH_EXECUTION_AMBIGUOUS"})
    response = JarvisGateway(service).handle(message("A che punto è?"))
    assert response["details"]["dispatch_last_error"] == "RuntimeError: worker interrupted"
    assert response["details"]["recovery"]["classification"] == "DISPATCH_EXECUTION_AMBIGUOUS"
    assert "recupero" in response["details"]["next_step"].lower()
    rendered = TelegramAdapter.render_response(response)
    assert "Causa: RuntimeError: worker interrupted" in rendered
    assert "Recovery: DISPATCH_EXECUTION_AMBIGUOUS" in rendered
    assert "Prossimo passo:" in rendered


def test_technical_details_render_executor_retries_and_lifecycle(service):
    created = JarvisGateway(service).handle(message("Crea una task per analizzare opportunità."))
    task_id = created["task_id"]
    service.queue.transition(task_id, "BLOCKED", retry_count=2, dispatch_attempts=3,
                             executor="LOCAL_FAST_MINISTRAL3B")
    response = JarvisGateway(service).handle(message(
        f"Mostrami i dettagli tecnici della task {task_id}"))
    rendered = TelegramAdapter.render_response(response)
    assert "Executor: LOCAL_FAST_MINISTRAL3B" in rendered
    assert "Retry: 2" in rendered
    assert "Dispatcher attempts: 3" in rendered
    assert "Lifecycle:" in rendered


def test_telegram_send_uses_rich_renderer(service, tmp_path, monkeypatch):
    adapter = TelegramAdapter(service, tmp_path / "seen-rich.json", token="token", allowed_users=["42"])
    captured = {}
    class Result:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
    def fake_open(request, timeout=10):
        captured.update(json.loads(request.data.decode()))
        return Result()
    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    response = {"summary": "Hai 1 task recente.", "details": {"view": "TASK_LIST", "items": [{
        "task_id": "TASK_ABC", "state": "QUEUED", "title": "Analisi utile",
        "updated_at": "2026-09-29T20:00:00+00:00"}], "counts": {"QUEUED": 1}},
        "task_id": None, "status": "COMPLETED", "priority": "NORMAL"}
    assert adapter.send("99", response)["sent"] is True
    assert "TASK_ABC — QUEUED — Analisi utile" in captured["text"]
    assert captured["text"] != response["summary"]


def test_telegram_research_task_direct_escalation_without_git_binary(tmp_path, monkeypatch):
    """Production regression: slim image has no git executable/.git checkout."""
    monkeypatch.setenv("RENDER_GIT_COMMIT", "06beb15466a3478f507069febf13ce0c3373ee3a")
    monkeypatch.setattr(context_packet.subprocess, "run",
                        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("git")))
    svc = JarvisService(tmp_path / "queue-escalate.json", tmp_path / "ledger-escalate.jsonl",
                        tmp_path / "conversation-escalate.json")
    adapter = TelegramAdapter(svc, tmp_path / "seen-escalate.json", token="token",
                              allowed_users=["42"], gateway=JarvisGateway(svc))
    response = adapter.handle_update({"update_id": 9901, "message": {
        "from": {"id": 42}, "chat": {"id": 99},
        "text": "Jarvis, crea una task per analizzare una opportunità generica."}})
    dispatcher = DurableQueueDispatcher(svc.orchestrator, poll_seconds=0.01)
    assert dispatcher.run_once() is True
    record = svc.queue.get(response["task_id"])
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["executor"] == "MANUAL_REVIEW"
    assert record["escalation"]["target"] == "MANUAL_REVIEW"
    assert record["escalation"]["context_packet"]["current_head"] == "06beb15466a3478f507069febf13ce0c3373ee3a"
    assert record["result_packet"]["escalation_needed"] == {
        "needed": True, "reason": "ROUTER_DIRECT_ESCALATION", "target_tier": "MANUAL_REVIEW"}
    assert record["dispatch_last_error"] is None
    # Re-entering the builder is deterministic and does not duplicate lifecycle events.
    before = len(svc.ledger.read_for_task(response["task_id"]))
    repeated = svc.orchestrator._escalate(response["task_id"], record, "MANUAL_REVIEW",
                                          "ROUTER_DIRECT_ESCALATION", [])
    assert repeated == record
    assert len(svc.ledger.read_for_task(response["task_id"])) == before


def test_current_head_falls_back_without_git_or_runtime_sha(monkeypatch):
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    monkeypatch.delenv("NEXUS_GIT_SHA", raising=False)
    monkeypatch.setattr(context_packet.subprocess, "run",
                        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("git")))
    assert context_packet._current_head() == "0000000"
