import json

import pytest

import app as backend
from orchestrator_v1.core.groq_evaluation import GroqEvaluationAdapterV1
from orchestrator_v1.core.provider_benchmark import BenchmarkBlocked, FreeProviderBenchmarkEngineV1
from orchestrator_v1.core.provider_policy import ProviderPolicyRegistryV1


MODEL = "configured/test-model"
HEADERS = {"x-ratelimit-limit-requests": "1000", "x-ratelimit-remaining-requests": "997",
           "x-ratelimit-limit-tokens": "8000", "x-ratelimit-remaining-tokens": "7900",
           "x-ratelimit-reset-requests": "1h", "x-ratelimit-reset-tokens": "5s"}


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def adapter(tmp_path, transport, *, key="groq-secret", enabled=True, models=(MODEL,)):
    return GroqEvaluationAdapterV1(api_key=key, enabled=enabled, model_ids=models,
        treasury_path=tmp_path / "treasury.json", transport=transport)


def runner(tmp_path, groq):
    return FreeProviderBenchmarkEngineV1(ProviderPolicyRegistryV1(),
        history_path=tmp_path / "history.json", adapters={"GROQ": groq})


def request(**updates):
    data = {"provider_id": "GROQ", "model_id": MODEL, "mode": "LIVE_EVALUATION",
            "live_evaluation_confirmed": True, "max_quota_units": 10,
            "timeout_seconds": 2, "run_label": "groq-live-test"}
    data.update(updates)
    return data


def good_response():
    return 200, HEADERS, {"choices": [{"message": {"content": json.dumps(
        {"answer": "verified response", "confidence": "medium"})}}],
        "usage": {"total_tokens": 12}}


def test_missing_key_and_disabled_flag_fail_closed_with_zero_network(tmp_path):
    transport = FakeTransport([])
    missing = adapter(tmp_path, transport, key="")
    disabled = adapter(tmp_path, transport, enabled=False)
    for item in (missing, disabled):
        plan = runner(tmp_path, item).preview(request())
        assert plan["runnable"] is False
        assert "PROVIDER_NOT_CONFIGURED" in plan["blocking_reasons"]
    assert transport.calls == []


def test_live_200_records_benchmark_quota_and_never_enables_production(tmp_path):
    transport = FakeTransport([good_response()] * 10)
    groq = adapter(tmp_path, transport)
    result = runner(tmp_path, groq).run(request())
    assert result["test_count"] == 10 and result["passed"] == 10
    assert result["promotion_recommendation"] == "CANDIDATE"
    assert result["production_candidate"] is False and result["human_approval_required"] is True
    assert len(transport.calls) == 10
    assert all(call["headers"]["Authorization"] == "Bearer groq-secret" for call in transport.calls)
    treasury = groq.treasury.read()
    assert treasury["requests_used"] == 3 and treasury["requests_remaining"] == 997
    assert treasury["tokens_used"] == 100 and treasury["observed_requests"] == 10
    assert "groq-secret" not in json.dumps(result) and "groq-secret" not in json.dumps(treasury)


def test_429_stops_immediately_and_saves_quota_headers(tmp_path):
    transport = FakeTransport([(429, {**HEADERS, "retry-after": "3"}, {"error": {}})])
    groq = adapter(tmp_path, transport)
    result = runner(tmp_path, groq).run(request(run_label="rate-limit"))
    assert len(transport.calls) == 1 and result["test_count"] == 1
    assert result["provenance"]["stopped_reason"] == "RATE_LIMITED"
    assert groq.treasury.read()["retry_after_seconds"] == 3


def test_timeout_retries_once_with_same_idempotency_key(tmp_path):
    transport = FakeTransport([TimeoutError(), TimeoutError()])
    result = runner(tmp_path, adapter(tmp_path, transport)).run(request(run_label="timeout"))
    assert len(transport.calls) == 2 and result["test_count"] == 1
    assert result["tests"][0]["retry_count"] == 1
    assert transport.calls[0]["headers"]["Idempotency-Key"] == \
           transport.calls[1]["headers"]["Idempotency-Key"]


def test_model_unavailable_is_failed_not_crash(tmp_path):
    transport = FakeTransport([(404, HEADERS, {"error": {"message": "not found"}})] * 10)
    result = runner(tmp_path, adapter(tmp_path, transport)).run(request(run_label="missing-model"))
    assert result["failed"] == 10
    assert all("MODEL_UNAVAILABLE" in item["error_flags"] for item in result["tests"])
    assert result["promotion_recommendation"] == "EVALUATION_ONLY"


def test_discovery_is_configurable_and_fail_closed(tmp_path):
    transport = FakeTransport([(200, HEADERS, {"data": [
        {"id": MODEL, "active": True}, {"id": "other", "active": True}]})])
    groq = adapter(tmp_path, transport, models=(MODEL, "not-available"))
    discovery = groq.discover()
    assert discovery["eligible"] == [MODEL]
    assert discovery["configured"] == [MODEL, "not-available"]
    no_key_transport = FakeTransport([])
    assert adapter(tmp_path, no_key_transport, key="").discover()["reason"] == \
           "GROQ_EVALUATION_NOT_CONFIGURED"
    assert no_key_transport.calls == []


def test_zero_budget_blocks_and_status_never_exposes_secret(tmp_path):
    transport = FakeTransport([])
    groq = adapter(tmp_path, transport)
    plan = runner(tmp_path, groq).preview(request(max_quota_units=0))
    assert "QUOTA_BUDGET_REQUIRED" in plan["blocking_reasons"]
    assert "groq-secret" not in json.dumps(groq.status())
    assert groq.status()["production_routing_enabled"] is False


def test_groq_endpoints_are_protected_and_secret_free(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "groq-api.db")); backend.init_db()
    from fastapi.testclient import TestClient
    with TestClient(backend.app) as client:
        assert client.get("/api/jarvis/providers/groq/status").status_code == 401
        assert client.get("/api/jarvis/providers/groq/quota").status_code == 401
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        status = client.get("/api/jarvis/providers/groq/status", headers=headers)
        assert status.status_code == 200
        assert set(status.json()) == {"provider_id", "mode", "configured",
                                      "live_evaluation_enabled", "api_key_present",
                                      "configured_model_count", "state",
                                      "production_routing_enabled"}
        blocked = client.post("/api/jarvis/providers/benchmarks/execute", headers=headers,
                              json=request())
        assert blocked.status_code in (409, 422)
