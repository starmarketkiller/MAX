"""NEXUS Local Inference Gateway V1 - the only thing Render is ever allowed
to reach over the tunnel; Ollama itself stays on 127.0.0.1 and is never
exposed directly. Tests the pure interpret() core (call_local_model
monkeypatched - no real Ollama needed) and the HTTP boundary (auth,
request-size limit, unknown-endpoint rejection) against a real, ephemeral,
localhost-only server instance.
"""
import http.client
import importlib.util
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GATEWAY_PATH = ROOT / "LocalBridge" / "nexus_local_inference_gateway.py"

spec = importlib.util.spec_from_file_location("nexus_local_inference_gateway", GATEWAY_PATH)
gw = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gw
spec.loader.exec_module(gw)


VALID_OUTPUT = {
    "intent": "QUERY", "goal": None, "confidence": 0.9, "referenced_task_id": None,
    "recommended_action": None, "target_agent": None, "skill": None, "provider_preference": None,
    "needs_clarification": False, "clarification_question": None, "risk_level": "LOW",
    "reason_summary": "test",
}


def _fake_call(success=True, response_text=None, error=None):
    def _call(prompt, model=None, timeout=None, json_mode=False, ensure_single_resident=True):
        return {"success": success, "response_text": response_text, "error": error}
    return _call


# interpret() - pure core, no HTTP -----------------------------------------
def test_interpret_returns_valid_output_for_a_well_formed_model_response():
    call = _fake_call(response_text=json.dumps(VALID_OUTPUT))
    result = gw.interpret("Che facciamo adesso?", {"candidate_task_ids": []}, call_local_model=call)
    assert result["ok"] is True
    assert result["output"]["intent"] == "QUERY"


def test_interpret_rejects_a_referenced_task_id_not_in_candidates():
    bad = dict(VALID_OUTPUT, referenced_task_id="TASK_NOT_REAL")
    call = _fake_call(response_text=json.dumps(bad))
    result = gw.interpret("approvo", {"candidate_task_ids": ["TASK_REAL"]}, call_local_model=call)
    assert result["ok"] is False
    assert result["status"] == 422
    assert "CANDIDATES" in result["error"]


def test_interpret_accepts_a_referenced_task_id_that_is_in_candidates():
    good = dict(VALID_OUTPUT, intent="APPROVAL", referenced_task_id="TASK_REAL")
    call = _fake_call(response_text=json.dumps(good))
    result = gw.interpret("approvo", {"candidate_task_ids": ["TASK_REAL"]}, call_local_model=call)
    assert result["ok"] is True


def test_interpret_rejects_malformed_json():
    call = _fake_call(response_text="not json at all {{{")
    result = gw.interpret("ciao", {}, call_local_model=call)
    assert result["ok"] is False
    assert result["status"] == 422


def test_interpret_rejects_schema_invalid_output():
    bad = dict(VALID_OUTPUT); bad["intent"] = "NOT_A_REAL_INTENT"
    call = _fake_call(response_text=json.dumps(bad))
    result = gw.interpret("ciao", {}, call_local_model=call)
    assert result["ok"] is False
    assert result["status"] == 422


def test_interpret_handles_model_call_failure_cleanly():
    call = _fake_call(success=False, error="connection refused")
    result = gw.interpret("ciao", {}, call_local_model=call)
    assert result["ok"] is False
    assert result["status"] == 502


def test_interpret_handles_model_call_raising_an_exception():
    def _raising(*a, **k):
        raise TimeoutError("too slow")
    result = gw.interpret("ciao", {}, call_local_model=_raising)
    assert result["ok"] is False
    assert result["status"] == 502


def test_interpret_never_forwards_raw_ollama_responses_unvalidated():
    # Even a syntactically valid JSON object that isn't the router schema
    # (e.g. a raw Ollama-shaped payload) must be rejected, not passed through.
    call = _fake_call(response_text=json.dumps({"model": "x", "response": "hi"}))
    result = gw.interpret("ciao", {}, call_local_model=call)
    assert result["ok"] is False


# HTTP boundary - real ephemeral server --------------------------------------
@pytest.fixture
def live_server(monkeypatch):
    monkeypatch.setattr(gw.ollama_worker, "call_local_model", _fake_call(response_text=json.dumps(VALID_OUTPUT)))
    monkeypatch.setattr(gw.ollama_worker, "is_ollama_reachable", lambda timeout=2: True)
    gw._rate_limiter._hits.clear()
    gw.GatewayHandler.auth_token = "a" * 32
    server = ThreadingHTTPServer(("127.0.0.1", 0), gw.GatewayHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    thread.join(timeout=2)


def _post(server, path, body, token=None, headers=None):
    conn = http.client.HTTPConnection(*server.server_address, timeout=5)
    hdrs = {"Content-Type": "application/json"}
    if token is not None:
        hdrs["Authorization"] = f"Bearer {token}"
    if headers:
        hdrs.update(headers)
    data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
    conn.request("POST", path, body=data, headers=hdrs)
    resp = conn.getresponse()
    payload = json.loads(resp.read())
    conn.close()
    return resp.status, payload


def test_gateway_binds_only_to_localhost(live_server):
    assert live_server.server_address[0] == "127.0.0.1"


def test_unknown_endpoint_is_rejected(live_server):
    status, _ = _post(live_server, "/v1/jarvis/not-a-real-route", {"text": "x"}, token="a" * 32)
    assert status == 404


def test_ollama_is_not_directly_exposed_through_the_gateway(live_server):
    # The gateway must never proxy straight to Ollama's own API surface.
    for path in ("/api/generate", "/api/version", "/api/tags"):
        status, _ = _post(live_server, path, {"text": "x"}, token="a" * 32)
        assert status == 404


def test_missing_auth_is_rejected(live_server):
    status, payload = _post(live_server, "/v1/jarvis/interpret", {"text": "ciao"})
    assert status == 401
    assert payload["ok"] is False


def test_wrong_auth_is_rejected(live_server):
    status, _ = _post(live_server, "/v1/jarvis/interpret", {"text": "ciao"}, token="wrong-token-wrong-token-wrong!!!")
    assert status == 401


def test_correct_auth_with_valid_body_succeeds(live_server):
    status, payload = _post(live_server, "/v1/jarvis/interpret",
                            {"text": "ciao", "context_packet": {"candidate_task_ids": []}}, token="a" * 32)
    assert status == 200
    assert payload["ok"] is True
    assert payload["output"]["intent"] == "QUERY"


def test_oversized_request_is_rejected(live_server):
    huge_text = "x" * (gw.MAX_REQUEST_BYTES + 1000)
    status, payload = _post(live_server, "/v1/jarvis/interpret", {"text": huge_text}, token="a" * 32)
    assert status == 413


def test_health_endpoint_needs_no_auth(live_server):
    conn = http.client.HTTPConnection(*live_server.server_address, timeout=5)
    conn.request("GET", "/v1/jarvis/health")
    resp = conn.getresponse()
    payload = json.loads(resp.read())
    conn.close()
    assert resp.status == 200
    assert payload["ok"] is True


def test_rate_limit_rejects_after_threshold(live_server, monkeypatch):
    monkeypatch.setattr(gw, "_rate_limiter", gw._RateLimiter(per_minute=2))
    body = {"text": "ciao", "context_packet": {"candidate_task_ids": []}}
    statuses = [_post(live_server, "/v1/jarvis/interpret", body, token="a" * 32)[0] for _ in range(3)]
    assert statuses[:2] == [200, 200]
    assert statuses[2] == 429
