"""TELEGRAM_MISTRAL_DIRECT_MODE_V1 - ministral_chat.py, the Render-side
client of the Local Inference Gateway's /v1/jarvis/chat route (dormant
today, mirrors ministral_router.py's already-tested pattern exactly for
when Jarvis runs off the same machine as Ollama)."""
import io
import json
import urllib.error

from jarvis_v1 import ministral_chat


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._body = json.dumps(payload).encode()
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener_returning(payload):
    def _opener(req, timeout=None):
        return _FakeResponse(payload)
    return _opener


def test_not_configured_without_env(monkeypatch):
    monkeypatch.delenv("JARVIS_MINISTRAL_GATEWAY_URL", raising=False)
    monkeypatch.delenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", raising=False)
    result = ministral_chat.ask_mistral_direct("ciao", [])
    assert result["ok"] is False
    assert "NOT_CONFIGURED" in result["error"]
    assert "latency_ms" in result


def test_success_with_injected_opener(monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    result = ministral_chat.ask_mistral_direct(
        "ciao", [], opener=_opener_returning({"ok": True, "output": {"reply": "Ciao!"}}))
    assert result["ok"] is True
    assert result["reply"] == "Ciao!"
    assert result["latency_ms"] >= 0


def test_rejects_empty_reply_from_gateway(monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    result = ministral_chat.ask_mistral_direct(
        "ciao", [], opener=_opener_returning({"ok": True, "output": {"reply": ""}}))
    assert result["ok"] is False
    assert result["error"] == "GATEWAY_EMPTY_REPLY"


def test_handles_gateway_http_error(monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")

    def _opener(req, timeout=None):
        raise urllib.error.HTTPError("url", 401, "unauthorized", {}, io.BytesIO(b'{"error":"UNAUTHORIZED"}'))

    result = ministral_chat.ask_mistral_direct("ciao", [], opener=_opener)
    assert result["ok"] is False
    assert "GATEWAY_HTTP_401" in result["error"]


def test_handles_gateway_unreachable(monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")

    def _opener(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    result = ministral_chat.ask_mistral_direct("ciao", [], opener=_opener)
    assert result["ok"] is False
    assert "GATEWAY_UNREACHABLE" in result["error"]


def test_handles_gateway_level_rejection(monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    result = ministral_chat.ask_mistral_direct(
        "ciao", [], opener=_opener_returning({"ok": False, "error": "RATE_LIMITED"}))
    assert result["ok"] is False
    assert "GATEWAY_REJECTED" in result["error"]


def test_bounded_history_keeps_only_most_recent_turns():
    history = [{"role": "user", "text": f"msg{i}"} for i in range(50)]
    bounded = ministral_chat.bounded_history(history)
    assert len(bounded) == ministral_chat.MAX_HISTORY_TURNS
    assert bounded[-1]["text"] == "msg49"


def test_bounded_history_ignores_non_dict_entries():
    assert ministral_chat.bounded_history(["not-a-dict", 42, None]) == []


def test_default_timeout_has_real_margin_for_a_cold_gateway_call():
    # LOCAL_INFERENCE_CONNECTIVITY_V1: misurato ~49s per una chiamata a
    # freddo a ministral-3:3b su Ollama - il vecchio default (20s) falliva
    # la prima richiesta reale dopo l'avvio del gateway o dopo che il
    # keep_alive di Ollama scadeva.
    assert ministral_chat.DEFAULT_TIMEOUT_SECONDS >= 30
