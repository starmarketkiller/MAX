import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as backend
from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService
from jarvis_v1.telegram_adapter import TelegramAdapter
from jarvis_v1.notifications import NotificationEngine


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
        for path in ("activity", "agents", "approvals", "telegram/status"):
            assert client.get(f"/api/jarvis/{path}", headers=headers).status_code == 200
