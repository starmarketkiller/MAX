"""Artifact-backed, side-effect-free provider policy and route preview V1."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from path_resolver import resolve_contracts_dir
from orchestrator_v1.nxs_schema_validator import validate

try:
    from review_matrix import get_matrix_entry
    from premium_budget_policy import allow_premium
except ImportError:
    import sys
    review_dir = str(Path(__file__).resolve().parents[2] / "review_pipeline_v1")
    if review_dir not in sys.path:
        sys.path.insert(0, review_dir)
    from review_matrix import get_matrix_entry
    from premium_budget_policy import allow_premium


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "provider_policy_registry_v1.json"
USABLE_STATES = {"AVAILABLE", "LOW_QUOTA"}
UNUSABLE_STATES = {"EXHAUSTED", "RATE_LIMITED", "OFFLINE", "UNKNOWN"}
TASK_MANIFEST_SCHEMA = json.loads(
    (resolve_contracts_dir(__file__) / "task-manifest.schema.json").read_text(encoding="utf-8"))


class ProviderPolicyRegistryV1:
    def __init__(self, registry_path=REGISTRY_PATH, registry_data=None):
        self.source = str(registry_path)
        self.data = copy.deepcopy(registry_data) if registry_data is not None else json.loads(
            Path(registry_path).read_text(encoding="utf-8"))
        self._validate()

    def _validate(self):
        schema_path = resolve_contracts_dir(__file__) / "provider-policy-registry.schema.json"
        schema_errors = validate(self.data, json.loads(schema_path.read_text(encoding="utf-8")))
        if schema_errors:
            raise ValueError(f"provider registry schema invalid: {schema_errors}")
        if self.data.get("schema_version") != 1:
            raise ValueError("unsupported provider registry schema")
        providers = self.data.get("providers")
        models = self.data.get("models")
        if not isinstance(providers, list) or not isinstance(models, list):
            raise ValueError("provider registry requires providers and models")
        provider_ids = [item.get("provider_id") for item in providers]
        if None in provider_ids or len(provider_ids) != len(set(provider_ids)):
            raise ValueError("provider ids must be non-empty and unique")
        required = {"provider_id", "model_id", "model_family", "state", "configured",
                    "free_tier_available", "estimated_cost_class", "quota_type",
                    "quota_remaining", "context_window", "supports_tools", "supports_images",
                    "supports_structured_output", "supports_code", "supports_long_context",
                    "supports_reasoning", "privacy_class", "allowed_task_types",
                    "forbidden_task_types", "preferred_roles", "fallback_priority",
                    "last_health_check", "last_benchmark", "benchmark_score", "notes"}
        keys = []
        for model in models:
            missing = required - set(model)
            if missing:
                raise ValueError(f"model missing fields: {sorted(missing)}")
            key = (model["provider_id"], model["model_id"])
            if model["provider_id"] not in provider_ids or key in keys:
                raise ValueError("model provider is unknown or model id is duplicated")
            keys.append(key)

    def public_registry(self, runtime_statuses=None, benchmark_results=None):
        payload = copy.deepcopy(self.data)
        runtime = {item.get("provider"): item for item in (runtime_statuses or [])}
        aliases = {"CODEX": "CODEX_OPENAI", "OPENAI": "CODEX_OPENAI"}
        for item in payload["providers"]:
            match = runtime.get(item["provider_id"])
            if match is None:
                for old, new in aliases.items():
                    if new == item["provider_id"] and old in runtime:
                        match = runtime[old]
                        break
            if match:
                item["runtime_connector_state"] = match.get("state", "UNKNOWN")
        latest = {}
        for result in benchmark_results or []:
            latest[(result.get("provider_id"), result.get("model_id"))] = result
        for model in payload["models"]:
            result = latest.get((model["provider_id"], model["model_id"]))
            if result:
                model["latest_benchmark"] = {
                    "benchmark_id": result.get("benchmark_id"),
                    "timestamp": result.get("timestamp"),
                    "evidence_level": result.get("evidence_level"),
                    "promotion_recommendation": result.get("promotion_recommendation"),
                    "production_candidate": False,
                }
        payload["source_artifact"] = "orchestrator_v1/provider_policy_registry_v1.json"
        return payload

    def policy_view(self):
        return {"registry_id": self.data["registry_id"], "schema_version": 1,
                **copy.deepcopy(self.data["policy"]),
                "premium_budget_policy": "review_pipeline_v1/premium_budget_policy.py",
                "review_matrix": "review_pipeline_v1/review_matrix.py"}

    @staticmethod
    def _is_executable(model):
        return bool(model["configured"] and model.get("verified_for_production") and
                    model["state"] in USABLE_STATES)

    @staticmethod
    def _view(model, *, reason, condition=None):
        return {"provider_id": model["provider_id"], "model_id": model["model_id"],
                "model_family": model["model_family"], "state": model["state"],
                "eligible_for_execution": ProviderPolicyRegistryV1._is_executable(model),
                "reason": reason, "condition": condition,
                "estimated_cost_class": model["estimated_cost_class"]}

    def route_preview(self, manifest):
        if not isinstance(manifest, dict):
            raise ValueError("task manifest must be an object")
        manifest_errors = validate(manifest, TASK_MANIFEST_SCHEMA)
        if manifest_errors:
            raise ValueError(f"invalid TASK_MANIFEST_V1: {manifest_errors}")
        task_type = manifest["task_type"]
        work_type = manifest.get("work_type")
        complexity = manifest["estimated_complexity"]
        models = sorted(self.data["models"], key=lambda item: item["fallback_priority"])
        excluded, evaluation, premium, executable = [], [], [], []

        if manifest.get("deterministic_tools_available"):
            primary = {"provider_id": "DETERMINISTIC", "model_id": None,
                       "model_family": "DETERMINISTIC", "state": "AVAILABLE",
                       "eligible_for_execution": True,
                       "reason": "A deterministic tool is declared available.",
                       "condition": None, "estimated_cost_class": "NO_MODEL_CALL"}
            return self._plan(manifest, primary, [], [], excluded)

        review = get_matrix_entry(work_type)
        premium_allowed, approval, premium_reason = allow_premium(
            review["premium_budget_level"], local_attempt_failed=False,
            local_confidence="UNKNOWN", review_matrix_requires_review=review["review_required"])
        premium_allowed = bool(manifest["premium_allowed"] and premium_allowed and not approval)

        for model in models:
            if task_type in model["forbidden_task_types"] or task_type not in model["allowed_task_types"]:
                excluded.append({"provider_id": model["provider_id"], "model_id": model["model_id"],
                                 "reason": "TASK_TYPE_NOT_ALLOWED"})
                continue
            cost = model["estimated_cost_class"]
            if cost == "PREMIUM":
                role_match = ((work_type == "scientific_research" and model["provider_id"] == "CLAUDE") or
                              (work_type == "complex_code" and model["provider_id"] == "CODEX_OPENAI"))
                if not manifest["premium_allowed"]:
                    excluded.append({"provider_id": model["provider_id"], "model_id": model["model_id"],
                                     "reason": "PREMIUM_DISALLOWED_BY_MANIFEST"})
                elif role_match:
                    condition = None if premium_allowed else "AFTER_POLICY_CONDITION_OR_APPROVAL"
                    premium.append(self._view(model, reason=premium_reason, condition=condition))
                continue
            if model.get("free_tier_available") and model["provider_id"] != "OLLAMA_LOCAL":
                if model["state"] in {"EXHAUSTED", "RATE_LIMITED", "OFFLINE"}:
                    excluded.append({"provider_id": model["provider_id"], "model_id": model["model_id"],
                                     "reason": f"PROVIDER_{model['state']}"})
                elif self._is_executable(model):
                    executable.append(self._view(model, reason="Verified free online candidate."))
                else:
                    evaluation.append(self._view(model, reason="Evaluation-only: provider is not production verified."))
                continue
            if self._is_executable(model):
                if complexity in {"TRIVIAL", "SMALL", "MEDIUM"} or work_type == "routine_summary":
                    executable.append(self._view(model, reason="Local, verified and sufficient for declared task."))
                else:
                    excluded.append({"provider_id": model["provider_id"], "model_id": model["model_id"],
                                     "reason": "LOCAL_CAPABILITY_INSUFFICIENT_FOR_COMPLEXITY"})

        primary = executable[0] if executable else None
        return self._plan(manifest, primary, executable[1:], evaluation, excluded, premium)

    def _plan(self, manifest, primary, fallback, evaluation, excluded, premium=None):
        return {"dry_run": True, "executed": False, "provider_calls": 0,
                "estimated_premium_calls": 0, "task_id": manifest["task_id"],
                "primary": primary, "fallback": fallback,
                "evaluation_candidates": evaluation, "premium_fallback": premium or [],
                "excluded": excluded, "policy": self.policy_view(),
                "provenance": {"source_artifact": "orchestrator_v1/provider_policy_registry_v1.json",
                               "registry_id": self.data["registry_id"], "schema_version": 1}}
