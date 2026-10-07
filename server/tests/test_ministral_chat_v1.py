"""TELEGRAM_MISTRAL_DIRECT_MODE_V1 - ministral_chat.py, the Render-side
client of the Local Inference Gateway's /v1/jarvis/chat route (dormant
today, mirrors ministral_router.py's already-tested pattern exactly for
when Jarvis runs off the same machine as Ollama)."""
import io
import json
import socket
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
    assert result["error"] == "GATEWAY_HTTP_401"


def test_missing_url_or_token_is_not_configured(monkeypatch):
    monkeypatch.delenv("JARVIS_MINISTRAL_GATEWAY_URL", raising=False)
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    assert ministral_chat.ask_mistral_direct("ciao", [])["error"] == "GATEWAY_NOT_CONFIGURED"
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example")
    monkeypatch.delenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", raising=False)
    assert ministral_chat.ask_mistral_direct("ciao", [])["error"] == "GATEWAY_NOT_CONFIGURED"


def test_http_403_4xx_and_5xx_have_distinct_taxonomy(monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    for status, expected in ((403, "GATEWAY_HTTP_403"), (429, "GATEWAY_HTTP_4XX"),
                             (502, "GATEWAY_HTTP_5XX")):
        def opener(req, timeout=None, code=status):
            raise urllib.error.HTTPError("url", code, "failed", {}, io.BytesIO(b"{}"))
        assert ministral_chat.ask_mistral_direct("ciao", [], opener=opener)["error"] == expected


def test_handles_gateway_unreachable(monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")

    def _opener(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    result = ministral_chat.ask_mistral_direct("ciao", [], opener=_opener)
    assert result["ok"] is False
    assert result["error"] == "GATEWAY_CONNECT_ERROR"


def test_dns_refused_and_timeout_are_distinct(monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    cases = [(socket.gaierror("dns"), "GATEWAY_DNS_ERROR"),
             (ConnectionRefusedError("refused"), "GATEWAY_CONNECT_ERROR"),
             (TimeoutError("timed out"), "GATEWAY_TIMEOUT")]
    for reason, expected in cases:
        def opener(req, timeout=None, error=reason):
            raise urllib.error.URLError(error)
        assert ministral_chat.ask_mistral_direct("ciao", [], opener=opener)["error"] == expected


def test_malformed_json_is_invalid_response(monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    class BadResponse(_FakeResponse):
        def read(self): return b"not-json"
    result = ministral_chat.ask_mistral_direct("ciao", [], opener=lambda *a, **k: BadResponse({}))
    assert result["error"] == "GATEWAY_INVALID_RESPONSE"


def test_handles_gateway_level_rejection(monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    result = ministral_chat.ask_mistral_direct(
        "ciao", [], opener=_opener_returning({"ok": False, "error": "RATE_LIMITED"}))
    assert result["ok"] is False
    assert result["error"] == "GATEWAY_REJECTED"
    model = ministral_chat.ask_mistral_direct(
        "ciao", [], opener=_opener_returning({"ok": False, "error": "MODEL_CALL_FAILED"}))
    assert model["error"] == "MODEL_CALL_FAILED"


def test_status_and_logs_never_expose_token(monkeypatch, caplog):
    token = "TOP_SECRET_GATEWAY_TOKEN"
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/path")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", token)
    ministral_chat.ask_mistral_direct("ciao", [], opener=lambda *a, **k: (_ for _ in ()).throw(
        urllib.error.URLError(ConnectionRefusedError("refused"))))
    status = ministral_chat.gateway_status()
    assert status["gateway_host"] == "gateway.example"
    assert status["token_present"] and status["token_length"] == len(token)
    assert token not in json.dumps(status) and token not in caplog.text


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
