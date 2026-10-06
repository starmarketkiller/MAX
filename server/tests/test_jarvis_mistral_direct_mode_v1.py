"""TELEGRAM_MISTRAL_DIRECT_MODE_V1 - /mistral, /jarvis, /new short-circuit in
JarvisService.handle(), before classify()-based routing.

Direct local call (is_ollama_reachable/call_local_model), same pattern
query() already uses - monkeypatched here exactly like every other
jarvis_v1 service test (see test_jarvis_state_query_v1.py's fixture).
"""
from datetime import datetime, timezone

import pytest

from jarvis_v1.service import JarvisService


def message(text, conversation="c1", user_id="42"):
    return {"message_id": f"m-{abs(hash((text, conversation)))}", "user_id": user_id,
            "channel": "TEST", "conversation_id": conversation,
            "timestamp": datetime.now(timezone.utc).isoformat(), "input_type": "TEXT",
            "text": text, "attachments": [], "reply_to": None, "request_class": "UNKNOWN",
            "priority": "NORMAL", "metadata": {}}


@pytest.fixture
def service(tmp_path, monkeypatch):
    svc = JarvisService(str(tmp_path / "q.json"), str(tmp_path / "l.jsonl"),
                        str(tmp_path / "c.json"))
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    return svc


def _ok_call(response_text="Ciao! Tutto bene."):
    return lambda prompt, timeout=None, ensure_single_resident=True: {
        "success": True, "response_text": response_text, "error": None}


def test_mistral_without_ollama_returns_clear_diagnostic(service):
    response = service.handle(message("/mistral come va?"))
    assert response["status"] == "UNAVAILABLE"
    assert "non è raggiungibile" in response["summary"]


def test_mistral_empty_message_prompts_usage(service):
    response = service.handle(message("/mistral"))
    assert "Usa /mistral seguito dal tuo messaggio" in response["summary"]


def test_mistral_direct_reply_happy_path(service, monkeypatch):
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: True)
    monkeypatch.setattr("jarvis_v1.service.call_local_model", _ok_call("Risposta diretta di Mistral."))
    response = service.handle(message("/mistral ciao, come stai?"))
    assert response["summary"] == "Risposta diretta di Mistral."
    assert response["generated_by"] == "ministral-3:3b-direct"
    assert response["status"] == "COMPLETED"


def test_mistral_direct_reply_persists_bounded_history(service, monkeypatch):
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: True)
    monkeypatch.setattr("jarvis_v1.service.call_local_model", _ok_call("risposta"))
    service.handle(message("/mistral primo messaggio"))
    stored = service.conversation_store.get("c1")
    assert stored["mistral_history"] == [
        {"role": "user", "text": "primo messaggio"},
        {"role": "assistant", "text": "risposta"},
    ]


def test_mistral_history_window_is_bounded(service, monkeypatch):
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: True)
    monkeypatch.setattr("jarvis_v1.service.call_local_model", _ok_call("ok"))
    for i in range(20):
        service.handle(message(f"/mistral messaggio {i}"))
    stored = service.conversation_store.get("c1")
    from jarvis_v1.service import MISTRAL_DIRECT_HISTORY_TURNS
    assert len(stored["mistral_history"]) == MISTRAL_DIRECT_HISTORY_TURNS * 2


def test_mistral_model_failure_returns_diagnostic_not_crash(service, monkeypatch):
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: True)
    monkeypatch.setattr("jarvis_v1.service.call_local_model",
                        lambda prompt, timeout=None, ensure_single_resident=True: {
                            "success": False, "response_text": None, "error": "connection refused"})
    response = service.handle(message("/mistral ciao"))
    assert response["status"] == "UNAVAILABLE"
    assert "connection refused" in response["summary"]


def test_new_clears_mistral_history_only(service, monkeypatch):
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: True)
    monkeypatch.setattr("jarvis_v1.service.call_local_model", _ok_call("ok"))
    service.handle(message("/mistral ciao"))
    assert service.conversation_store.get("c1")["mistral_history"]
    service.handle(message("/new"))
    assert service.conversation_store.get("c1")["mistral_history"] == []


def test_jarvis_prefix_strips_and_falls_through_to_normal_routing(service):
    response = service.handle(message("/jarvis /status"))
    assert response["details"].get("view") == "SYSTEM_STATUS"


def test_bare_jarvis_prefix_defaults_to_help(service):
    response = service.handle(message("/jarvis"))
    assert "Sono Jarvis" in response["summary"]


def test_mistral_mode_does_not_affect_normal_jarvis_commands(service):
    response = service.handle(message("/status"))
    assert response["details"].get("view") == "SYSTEM_STATUS"


def test_mistral_text_never_misrouted_by_other_classifiers(service, monkeypatch):
    # Testo che altrimenti potrebbe matchare EXECUTIVE_INTENT/GOAL_TO_TASK/
    # mutation verbs - il prefisso /mistral deve comunque vincere.
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: True)
    monkeypatch.setattr("jarvis_v1.service.call_local_model", _ok_call("risposta sicura"))
    response = service.handle(message("/mistral cosa facciamo adesso, approviamo tutto?"))
    assert response["summary"] == "risposta sicura"
    assert response["generated_by"] == "ministral-3:3b-direct"


def test_different_conversations_have_independent_history(service, monkeypatch):
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: True)
    monkeypatch.setattr("jarvis_v1.service.call_local_model", _ok_call("ok"))
    service.handle(message("/mistral ciao da c1", conversation="c1"))
    service.handle(message("/mistral ciao da c2", conversation="c2"))
    assert service.conversation_store.get("c1")["mistral_history"][0]["text"] == "ciao da c1"
    assert service.conversation_store.get("c2")["mistral_history"][0]["text"] == "ciao da c2"
