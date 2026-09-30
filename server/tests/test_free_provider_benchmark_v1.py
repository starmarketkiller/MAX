import copy

import pytest

import app as backend
from orchestrator_v1.core.provider_benchmark import (
    BenchmarkBlocked, FreeProviderBenchmarkEngineV1, MockBenchmarkAdapter)
from orchestrator_v1.core.provider_policy import ProviderPolicyRegistryV1


PROVIDER = "GROQ"
MODEL = "QWEN_UNSPECIFIED"


def engine(tmp_path, adapter=None, registry=None):
    return FreeProviderBenchmarkEngineV1(
        registry or ProviderPolicyRegistryV1(),
        history_path=tmp_path / "history.json", adapters={PROVIDER: adapter} if adapter else {})


def request(mode="MOCK", **extra):
    value = {"provider_id": PROVIDER, "model_id": MODEL, "mode": mode,
             "run_label": "run-1", "max_quota_units": 20, "timeout_seconds": 2}
    value.update(extra)
    return value


def test_mock_excellent_produces_multidimensional_scorecard_but_never_promotes(tmp_path):
    adapter = MockBenchmarkAdapter()
    result = engine(tmp_path).run(request(mock_adapter=adapter))
    assert result["passed"] == result["test_count"] == 10
    assert result["scorecard"]["CODING"] == result["scorecard"]["REASONING"] == 100
    assert "CODING" in result["recommended_roles"]
    assert result["production_candidate"] is False
    assert result["promotion_recommendation"] == "EVALUATION_ONLY"
    assert result["human_approval_required"] is True


def test_fast_but_poor_reasoning_is_not_recommended_for_reasoning(tmp_path):
    adapter = MockBenchmarkAdapter({"REASONING": {"verifier_score": .25, "latency_ms": 5}})
    result = engine(tmp_path).run(request(mock_adapter=adapter))
    assert result["scorecard"]["SPEED"] > 90
    assert "RESEARCH_ASSIST" not in result["recommended_roles"]
    assert "SECOND_OPINION" in result["forbidden_roles"]


def test_strong_coding_recommends_coding_and_schema_failure_forbids_verifier(tmp_path):
    adapter = MockBenchmarkAdapter({
        "CODING": {"verifier_score": .95},
        "STRUCTURED_OUTPUT": {"verifier_score": .95, "schema_compliance": False}})
    result = engine(tmp_path).run(request(mock_adapter=adapter))
    assert "CODING" in result["recommended_roles"]
    assert result["scorecard"]["STRUCTURED_OUTPUT"] == 0
    assert "VERIFIER" in result["forbidden_roles"]


def test_rate_limit_stops_before_budget_and_history_is_idempotent(tmp_path):
    adapter = MockBenchmarkAdapter({"REASONING": {"rate_limited": True, "quota_consumed": 1}})
    runner = engine(tmp_path)
    first = runner.run(request(mock_adapter=adapter))
    call_count = len(adapter.calls)
    second = runner.run(request(mock_adapter=adapter))
    assert first == second and len(adapter.calls) == call_count
    assert first["test_count"] == 2
    assert first["provenance"]["stopped_reason"] == "RATE_LIMITED"
    assert first["provenance"]["quota_consumed"] <= 20


def test_offline_mock_and_unconfigured_live_are_blocked_without_calls(tmp_path):
    offline = MockBenchmarkAdapter(state="OFFLINE")
    with pytest.raises(BenchmarkBlocked, match="PROVIDER_OFFLINE"):
        engine(tmp_path).run(request(mock_adapter=offline))
    runner = engine(tmp_path)
    plan = runner.preview(request("LIVE_EVALUATION", live_evaluation_confirmed=True))
    assert plan["runnable"] is False
    assert "PROVIDER_NOT_CONFIGURED" in plan["blocking_reasons"]
    assert plan["network_calls"] == 0


def test_dry_run_never_calls_and_live_candidate_still_requires_human_approval(tmp_path):
    adapter = MockBenchmarkAdapter()
    runner = engine(tmp_path, adapter)
    plan = runner.run(request("DRY_RUN"))
    assert plan["executed"] is False and plan["network_calls"] == 0 and adapter.calls == []
    data = copy.deepcopy(ProviderPolicyRegistryV1().data)
    for provider in data["providers"]:
        if provider["provider_id"] == PROVIDER:
            provider.update(configured=True, state="AVAILABLE")
    for model in data["models"]:
        if model["provider_id"] == PROVIDER:
            model.update(configured=True, state="AVAILABLE")
    live_runner = engine(tmp_path / "live", adapter, ProviderPolicyRegistryV1(registry_data=data))
    result = live_runner.run(request("LIVE_EVALUATION", live_evaluation_confirmed=True))
    assert result["promotion_recommendation"] == "CANDIDATE"
    assert result["production_candidate"] is False and result["human_approval_required"] is True


def test_history_preserves_distinct_versions_and_policy_reads_latest_without_promotion(tmp_path):
    runner = engine(tmp_path)
    first = runner.run(request(mock_adapter=MockBenchmarkAdapter(), run_label="a"))
    second = runner.run(request(mock_adapter=MockBenchmarkAdapter(), run_label="b"))
    assert len(runner.list_results()) == 2 and first["benchmark_id"] != second["benchmark_id"]
    public = runner.registry.public_registry(benchmark_results=runner.list_results())
    model = next(m for m in public["models"] if m["provider_id"] == PROVIDER)
    assert model["latest_benchmark"]["benchmark_id"] == second["benchmark_id"]
    assert model["latest_benchmark"]["production_candidate"] is False


def test_benchmark_endpoints_are_protected_and_preview_has_no_network(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "benchmark-api.db")); backend.init_db()
    from fastapi.testclient import TestClient
    with TestClient(backend.app) as client:
        assert client.get("/api/jarvis/providers/benchmarks").status_code == 401
        assert client.post("/api/jarvis/providers/benchmarks/preview", json=request("DRY_RUN")).status_code == 401
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        preview = client.post("/api/jarvis/providers/benchmarks/preview",
                              headers=headers, json=request("DRY_RUN"))
        assert preview.status_code == 200
        assert preview.json()["network_calls"] == 0 and preview.json()["executed"] is False
