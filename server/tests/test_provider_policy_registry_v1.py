import copy
import json
from datetime import datetime, timezone

import app as backend
from orchestrator_v1.core.provider_policy import ProviderPolicyRegistryV1


def manifest(**changes):
    base = {"task_id": "TASK_POLICY_1", "title": "Policy preview", "objective": "Preview routing",
            "task_type": "DOCUMENTATION", "work_type": "routine_summary", "priority": "NORMAL",
            "risk_level": "A0", "scientific_risk": "NONE", "code_risk": "NONE",
            "financial_risk": "NONE", "required_capabilities": ["summaries"],
            "deterministic_tools_available": False, "repo_scope": "read-only",
            "files_allowed": [], "files_forbidden": [], "dependencies": [], "blockers": [],
            "expected_artifacts": ["route-preview"], "success_criteria": ["dry run"],
            "verifier": "deterministic", "estimated_complexity": "SMALL",
            "estimated_runtime": "1m", "premium_allowed": False,
            "preferred_executor": "TIER1_LOCAL_CHEAP", "fallback_executors": [],
            "approval_required": "AUTO", "created_by": "test",
            "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
            "account_scope_id": None}
    base.update(changes)
    return base


def test_registry_has_required_provider_and_model_fields_and_no_secrets():
    registry = ProviderPolicyRegistryV1()
    public = registry.public_registry()
    assert {p["provider_id"] for p in public["providers"]} == {
        "OLLAMA_LOCAL", "CLAUDE", "CODEX_OPENAI", "GEMINI", "GROQ",
        "OPENROUTER", "HUGGING_FACE"}
    serialized = json.dumps(public).lower()
    assert "api_key" not in serialized and "token" not in serialized and "secret" not in serialized
    required = {"provider_id", "model_id", "model_family", "state", "configured",
                "free_tier_available", "estimated_cost_class", "quota_type",
                "quota_remaining", "context_window", "supports_tools", "supports_images",
                "supports_structured_output", "supports_code", "supports_long_context",
                "supports_reasoning", "privacy_class", "allowed_task_types",
                "forbidden_task_types", "preferred_roles", "fallback_priority",
                "last_health_check", "last_benchmark", "benchmark_score", "notes"}
    assert all(required <= set(model) for model in public["models"])


def test_deterministic_then_simple_local_and_dry_run_never_calls_provider():
    registry = ProviderPolicyRegistryV1()
    deterministic = registry.route_preview(manifest(deterministic_tools_available=True))
    local = registry.route_preview(manifest())
    assert deterministic["primary"]["provider_id"] == "DETERMINISTIC"
    assert local["primary"]["provider_id"] == "OLLAMA_LOCAL"
    assert local["dry_run"] is True and local["executed"] is False
    assert local["provider_calls"] == local["estimated_premium_calls"] == 0


def test_heavy_noncritical_exposes_free_models_only_as_evaluation_candidates():
    plan = ProviderPolicyRegistryV1().route_preview(manifest(estimated_complexity="LARGE"))
    ids = {item["provider_id"] for item in plan["evaluation_candidates"]}
    assert {"GROQ", "OPENROUTER", "GEMINI", "HUGGING_FACE"} <= ids
    assert all(item["eligible_for_execution"] is False for item in plan["evaluation_candidates"])
    # The verified local runtime may remain primary; unverified online options
    # are visible for evaluation but may not displace it.
    assert plan["primary"]["provider_id"] == "OLLAMA_LOCAL"


def test_complex_code_and_science_offer_correct_premium_policy_candidates():
    registry = ProviderPolicyRegistryV1()
    code = registry.route_preview(manifest(task_type="CODE", work_type="complex_code",
        estimated_complexity="XLARGE", premium_allowed=True))
    science = registry.route_preview(manifest(task_type="RESEARCH", work_type="scientific_research",
        estimated_complexity="LARGE", premium_allowed=True))
    assert [p["provider_id"] for p in code["premium_fallback"]] == ["CODEX_OPENAI"]
    assert [p["provider_id"] for p in science["premium_fallback"]] == ["CLAUDE"]
    assert code["estimated_premium_calls"] == science["estimated_premium_calls"] == 0


def test_free_exhausted_offline_and_premium_disallowed_are_excluded():
    data = copy.deepcopy(ProviderPolicyRegistryV1().data)
    for model in data["models"]:
        if model["provider_id"] == "GROQ":
            model["state"] = "EXHAUSTED"
    plan = ProviderPolicyRegistryV1(registry_data=data).route_preview(
        manifest(estimated_complexity="LARGE"))
    assert "GROQ" not in {p["provider_id"] for p in plan["evaluation_candidates"]}
    assert any(x["provider_id"] == "GROQ" and x["reason"] == "PROVIDER_EXHAUSTED"
               for x in plan["excluded"])
    no_premium = ProviderPolicyRegistryV1().route_preview(manifest(
        task_type="CODE", work_type="complex_code", estimated_complexity="XLARGE",
        premium_allowed=False))
    assert no_premium["premium_fallback"] == []
    assert any(x["provider_id"] == "CODEX_OPENAI" and
               x["reason"] == "PREMIUM_DISALLOWED_BY_MANIFEST" for x in no_premium["excluded"])


def test_provider_policy_endpoints_are_protected_and_preview_is_pure(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "policy-api.db"))
    backend.init_db()
    from fastapi.testclient import TestClient
    with TestClient(backend.app) as client:
        assert client.get("/api/jarvis/providers").status_code == 401
        assert client.get("/api/jarvis/providers/policy").status_code == 401
        assert client.post("/api/jarvis/providers/route-preview", json=manifest()).status_code == 401
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        providers = client.get("/api/jarvis/providers", headers=headers)
        policy = client.get("/api/jarvis/providers/policy", headers=headers)
        preview = client.post("/api/jarvis/providers/route-preview", headers=headers,
                              json={"manifest": manifest()})
        assert providers.status_code == 200 and providers.json()["count"] == 7
        assert policy.status_code == 200 and policy.json()["fail_closed"] is True
        assert preview.status_code == 200 and preview.json()["provider_calls"] == 0
