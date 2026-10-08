import json
import urllib.error
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import app as backend

from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService, classify
from jarvis_v1.telegram_adapter import TelegramAdapter


def _message(text, update_id=1, callback_data=None):
    if callback_data is not None:
        return {"update_id": update_id, "callback_query": {"id": f"cb-{update_id}",
                "from": {"id": 42}, "data": callback_data,
                "message": {"chat": {"id": 42}}}}
    return {"update_id": update_id, "message": {"from": {"id": 42},
            "chat": {"id": 42}, "text": text}}


def _service(tmp_path):
    return JarvisService(queue_path=tmp_path / "queue.json",
                         ledger_path=tmp_path / "ledger.jsonl",
                         conversation_path=tmp_path / "conversations.json")


def _adapter(tmp_path, service):
    return TelegramAdapter(service, state_path=tmp_path / "telegram.json",
                           token="test-token", allowed_users={"42"},
                           gateway=JarvisGateway(service))


def test_slash_help_bypasses_active_mistral_router(monkeypatch, tmp_path):
    service = _service(tmp_path)
    adapter = _adapter(tmp_path, service)
    monkeypatch.setenv("JARVIS_MINISTRAL_ROUTER_ENABLED", "true")
    monkeypatch.setenv("JARVIS_MINISTRAL_ROUTER_MODE", "ACTIVE")
    monkeypatch.setattr("jarvis_v1.ministral_router.resolve_intent_via_router",
                        lambda *_a, **_k: (_ for _ in ()).throw(
                            AssertionError("slash command must bypass router")))
    response = adapter.handle_update(_message("/help"))
    assert "Sono Jarvis" in response["summary"]
    assert response["details"]["view"] if "view" in response["details"] else True


def test_callback_then_text_message_remains_usable(tmp_path):
    service = _service(tmp_path)
    adapter = _adapter(tmp_path, service)
    first = adapter.handle_update(_message("", 10, "J1|Q|TASKS"))
    second = adapter.handle_update(_message("/help", 11))
    assert first["details"]["view"] == "TASK_LIST"
    assert "Sono Jarvis" in second["summary"]


def test_bare_show_task_reference_routes_to_result(tmp_path):
    service = _service(tmp_path)
    task_id = service.create_task({
        "message_id": "create", "user_id": "42", "channel": "TEST",
        "conversation_id": "telegram:42", "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_type": "TEXT", "text": "crea una task per riepilogare", "attachments": [],
        "reply_to": None, "request_class": "TASK_REQUEST", "priority": "NORMAL", "metadata": {}})["task_id"]
    assert classify(f"Fammi vedere {task_id}") == "TASK_RESULT"
    before = len(service.queue.list_all())
    response = service.handle({
        "message_id": "show", "user_id": "42", "channel": "TEST",
        "conversation_id": "telegram:42", "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_type": "TEXT", "text": f"Fammi vedere {task_id}", "attachments": [],
        "reply_to": None, "request_class": "UNKNOWN", "priority": "NORMAL", "metadata": {}})
    assert response["details"]["view"] == "TASK_RESULT"
    assert response["status"] == "RESULT_UNAVAILABLE"
    assert len(service.queue.list_all()) == before


def test_cognitive_request_uses_local_mistral_without_creating_task(monkeypatch, tmp_path):
    service = _service(tmp_path)
    monkeypatch.setattr("jarvis_v1.ministral_chat.ask_mistral_direct",
                        lambda *_a, **_k: {"ok": True, "reply": "Analisi locale bounded."})
    before = len(service.queue.list_all())
    msg = {"message_id": "cog", "user_id": "42", "channel": "TEST",
           "conversation_id": "telegram:42", "timestamp": datetime.now(timezone.utc).isoformat(),
           "input_type": "TEXT", "text": "Jarvis, cosa consiglieresti per migliorare il reparto Social?",
           "attachments": [], "reply_to": None, "request_class": "UNKNOWN",
           "priority": "NORMAL", "metadata": {}}
    response = service.handle(msg)
    assert response["summary"] == "Analisi locale bounded."
    assert response["generated_by"] == "ministral-3:3b-direct"
    assert response["details"]["premium_calls"] == 0
    assert len(service.queue.list_all()) == before


def test_cognitive_request_offline_has_explicit_fallback(monkeypatch, tmp_path):
    service = _service(tmp_path)
    monkeypatch.setattr("jarvis_v1.ministral_chat.ask_mistral_direct",
                        lambda *_a, **_k: {"ok": False, "error": "GATEWAY_TIMEOUT"})
    msg = {"message_id": "offline", "user_id": "42", "channel": "TEST",
           "conversation_id": "telegram:42", "timestamp": datetime.now(timezone.utc).isoformat(),
           "input_type": "TEXT", "text": "Jarvis, parliamo del progetto.", "attachments": [],
           "reply_to": None, "request_class": "UNKNOWN", "priority": "NORMAL", "metadata": {}}
    response = service.handle(msg)
    assert response["status"] == "UNAVAILABLE"
    assert "GATEWAY_TIMEOUT" in response["summary"]
    assert response["details"]["premium_calls"] == 0


def test_conversation_reset_preserves_task_queue(tmp_path):
    service = _service(tmp_path)
    service.conversation_store.update("telegram:42", last_task_id="TASK_X", pending_action="x")
    before = list(service.queue.list_all())
    msg = {"message_id": "reset", "user_id": "42", "channel": "TEST",
           "conversation_id": "telegram:42", "timestamp": datetime.now(timezone.utc).isoformat(),
           "input_type": "TEXT", "text": "/reset", "attachments": [], "reply_to": None,
           "request_class": "UNKNOWN", "priority": "NORMAL", "metadata": {}}
    response = service.handle(msg)
    assert response["details"]["canonical_state_preserved"] is True
    assert service.conversation_store.get("telegram:42") == {}
    assert service.queue.list_all() == before


def test_processed_response_is_persisted_until_delivery(tmp_path):
    service = _service(tmp_path)
    adapter = _adapter(tmp_path, service)
    response = adapter.handle_update(_message("/help", 50))
    assert adapter.pending_response(50)["response_id"] == response["response_id"]
    assert adapter.handle_update(_message("/help", 50))["status"] == "DUPLICATE"
    adapter.mark_delivered(50)
    assert adapter.pending_response(50) is None
    reloaded = _adapter(tmp_path, service)
    assert reloaded.pending_response(50) is None


def test_telegram_delivery_retries_once_without_secret_leak(monkeypatch, tmp_path):
    service = _service(tmp_path)
    adapter = _adapter(tmp_path, service)
    calls = []

    class _OK:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_a): return False

    def opener(req, timeout=10):
        calls.append((req.full_url, req.data))
        if len(calls) == 1:
            raise urllib.error.URLError("temporary")
        return _OK()

    monkeypatch.setattr("jarvis_v1.telegram_adapter.urllib.request.urlopen", opener)
    result = adapter.send("42", {"summary": "ok", "details": {}, "status": "COMPLETED",
                                  "response_type": "ANSWER", "priority": "NORMAL"})
    assert result["sent"] is True
    assert len(calls) == 2
    assert all(b"test-token" not in (body or b"") for _url, body in calls)


def test_callback_ack_uses_answer_callback_query(monkeypatch, tmp_path):
    service = _service(tmp_path)
    adapter = _adapter(tmp_path, service)
    captured = []
    monkeypatch.setattr(adapter, "_telegram_request",
                        lambda method, payload, **_k: captured.append((method, payload)) or
                        {"ok": True, "failure_class": None, "retryable": False})
    assert adapter.answer_callback("cb-1")["sent"] is True
    assert captured == [("answerCallbackQuery", {"callback_query_id": "cb-1"})]


def test_webhook_delivery_failure_replays_response_without_reprocessing(monkeypatch, tmp_path):
    service = _service(tmp_path)
    adapter = _adapter(tmp_path, service)
    monkeypatch.setattr(backend, "JARVIS_TELEGRAM", adapter)
    monkeypatch.setenv("JARVIS_TELEGRAM_WEBHOOK_SECRET", "hook-secret")
    deliveries = iter([{"sent": False, "reason": "TELEGRAM_URLERROR"},
                       {"sent": True, "reason": None}])
    monkeypatch.setattr(adapter, "send", lambda *_a, **_k: next(deliveries))
    update = _message("/help", 88)
    with TestClient(backend.app) as client:
        first = client.post("/api/jarvis/telegram/webhook", json=update,
                            headers={"X-Telegram-Bot-Api-Secret-Token": "hook-secret"})
        assert first.status_code == 503
        received_before = len([e for e in service.ledger.read_all()
                               if e["event_type"] == "TELEGRAM_UPDATE_RECEIVED"])
        second = client.post("/api/jarvis/telegram/webhook", json=update,
                             headers={"X-Telegram-Bot-Api-Secret-Token": "hook-secret"})
        assert second.status_code == 200
        assert "Sono Jarvis" in second.json()["response"]["summary"]
        received_after = len([e for e in service.ledger.read_all()
                              if e["event_type"] == "TELEGRAM_UPDATE_RECEIVED"])
        assert received_after == received_before


def test_concurrent_duplicate_update_is_processed_once(tmp_path):
    service = _service(tmp_path)
    calls = 0
    lock = threading.Lock()

    class _Gateway:
        def handle(self, message):
            nonlocal calls
            with lock:
                calls += 1
            time.sleep(0.05)
            return service.handle(message)

    adapter = TelegramAdapter(service, state_path=tmp_path / "concurrent.json",
                              token="t", allowed_users={"42"}, gateway=_Gateway())
    update = _message("/help", 99)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _n: adapter.handle_update(update), range(2)))
    assert calls == 1
    assert sorted(result.get("status") == "DUPLICATE" for result in results) == [False, True]
