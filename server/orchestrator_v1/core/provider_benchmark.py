"""Free Provider Benchmark Engine V1: repeatable evaluation, never promotion."""
from __future__ import annotations

import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from path_resolver import resolve_contracts_dir
from orchestrator_v1.nxs_schema_validator import validate


BENCHMARK_VERSION = "FREE_PROVIDER_BENCHMARK_V1"
CATEGORIES = ("STRUCTURED_OUTPUT", "REASONING", "CODING", "DEBUGGING", "SYNTHESIS",
              "CLASSIFICATION", "LONG_CONTEXT", "TOOL_USE", "INSTRUCTION_FOLLOWING",
              "AMBIGUITY_ROBUSTNESS")
ROLE_CATEGORY = {
    "ROUTINE_SUMMARY": "SYNTHESIS", "CLASSIFICATION": "CLASSIFICATION",
    "RESEARCH_ASSIST": "REASONING", "CODE_REVIEW": "DEBUGGING", "CODING": "CODING",
    "DEBUGGING": "DEBUGGING", "LONG_CONTEXT_ANALYSIS": "LONG_CONTEXT",
    "SECOND_OPINION": "REASONING", "VERIFIER": "STRUCTURED_OUTPUT"}
RESULT_SCHEMA = json.loads((resolve_contracts_dir(__file__) /
                            "provider-benchmark-result.schema.json").read_text(encoding="utf-8"))


class BenchmarkBlocked(RuntimeError):
    pass


class MockBenchmarkAdapter:
    """Deterministic adapter used only in tests/evaluation artifacts."""
    def __init__(self, outcomes=None, *, state="AVAILABLE"):
        self.outcomes = outcomes or {}
        self.state = state
        self.calls = []

    def evaluate(self, case, *, idempotency_key, timeout_seconds):
        self.calls.append((case["category"], idempotency_key))
        value = self.outcomes.get(case["category"], self.outcomes.get("DEFAULT", {}))
        if isinstance(value, Exception):
            raise value
        return {"success": True, "verifier_score": 1.0, "schema_compliance": True,
                "latency_ms": 100, "token_usage": None, "quota_consumed": 0,
                "estimated_cost": 0, "hallucination_flags": [], "error_flags": [],
                "determinism_score": 1.0,
                "tool_call_correctness": 1.0 if case["category"] == "TOOL_USE" else None,
                "output_length": 120, **value}


class BenchmarkHistory:
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        if not self.path.exists():
            return []
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def append_once(self, result):
        rows = self.read()
        if any(row.get("benchmark_id") == result["benchmark_id"] for row in rows):
            return next(row for row in rows if row.get("benchmark_id") == result["benchmark_id"])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rows.append(result)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        tmp.replace(self.path)
        return result


class FreeProviderBenchmarkEngineV1:
    def __init__(self, policy_registry, *, history_path, adapters=None):
        self.registry = policy_registry
        self.history = BenchmarkHistory(history_path)
        self.adapters = adapters or {}

    @staticmethod
    def suite():
        return [{"test_id": f"B-{index:02d}", "category": category,
                 "verifier": "DETERMINISTIC_V1"}
                for index, category in enumerate(CATEGORIES, 1)]

    def _model(self, provider_id, model_id):
        return next((m for m in self.registry.data["models"]
                     if m["provider_id"] == provider_id and m["model_id"] == model_id), None)

    def _provider(self, provider_id):
        return next((p for p in self.registry.data["providers"]
                     if p["provider_id"] == provider_id), None)

    def preview(self, request):
        mode = request.get("mode", "DRY_RUN")
        if mode not in {"MOCK", "DRY_RUN", "LIVE_EVALUATION"}:
            raise ValueError("unsupported benchmark mode")
        model = self._model(request.get("provider_id"), request.get("model_id"))
        if not model:
            raise ValueError("provider/model not present in registry")
        reasons = []
        runnable = mode == "MOCK"
        if mode == "LIVE_EVALUATION":
            provider = self._provider(model["provider_id"])
            if not request.get("live_evaluation_confirmed"):
                reasons.append("EXPLICIT_LIVE_FLAG_REQUIRED")
            if not model["configured"] or not provider or not provider["configured"]:
                reasons.append("PROVIDER_NOT_CONFIGURED")
            if model["state"] not in {"AVAILABLE", "LOW_QUOTA"} or provider["state"] not in {
                    "AVAILABLE", "LOW_QUOTA"}:
                reasons.append(f"PROVIDER_{model['state']}")
            if model["provider_id"] not in self.adapters:
                reasons.append("NO_LIVE_ADAPTER")
            runnable = not reasons
        return {"dry_run": mode == "DRY_RUN", "executed": False, "mode": mode,
                "provider_id": model["provider_id"], "model_id": model["model_id"],
                "test_count": len(CATEGORIES), "categories": list(CATEGORIES),
                "runnable": runnable, "blocking_reasons": reasons, "network_calls": 0,
                "max_retries": 1, "promotion_automatic": False}

    def run(self, request):
        plan = self.preview(request)
        mode = plan["mode"]
        if mode == "DRY_RUN":
            return plan
        if not plan["runnable"]:
            raise BenchmarkBlocked(",".join(plan["blocking_reasons"]))
        adapter = request.get("mock_adapter") if mode == "MOCK" else self.adapters[plan["provider_id"]]
        if mode == "MOCK" and not isinstance(adapter, MockBenchmarkAdapter):
            raise BenchmarkBlocked("MOCK_ADAPTER_REQUIRED")
        if getattr(adapter, "state", "UNKNOWN") not in {"AVAILABLE", "LOW_QUOTA"}:
            raise BenchmarkBlocked(f"PROVIDER_{getattr(adapter, 'state', 'UNKNOWN')}")
        budget = max(0, int(request.get("max_quota_units", len(CATEGORIES))))
        timeout = max(1, min(int(request.get("timeout_seconds", 30)), 120))
        seed = json.dumps({k: request.get(k) for k in ("provider_id", "model_id", "mode", "run_label")},
                          sort_keys=True)
        benchmark_id = "BENCH_" + hashlib.sha256(seed.encode()).hexdigest()[:16].upper()
        existing = next((r for r in self.history.read() if r.get("benchmark_id") == benchmark_id), None)
        if existing:
            return existing
        rows, quota, stopped = [], 0, None
        for case in self.suite():
            if quota >= budget:
                stopped = "FREE_QUOTA_BUDGET_REACHED"
                break
            key = f"{benchmark_id}:{case['test_id']}"
            attempts, output = 0, None
            while attempts < 2:
                attempts += 1
                try:
                    output = adapter.evaluate(case, idempotency_key=key, timeout_seconds=timeout)
                    break
                except TimeoutError:
                    if attempts == 2:
                        output = {"success": False, "verifier_score": 0, "schema_compliance": False,
                                  "latency_ms": timeout * 1000, "quota_consumed": 0,
                                  "token_usage": None, "estimated_cost": None,
                                  "hallucination_flags": [], "error_flags": ["TIMEOUT"],
                                  "tool_call_correctness": None, "output_length": 0}
            consumed = max(0, int(output.get("quota_consumed") or 0))
            quota += consumed
            rows.append({"test_id": case["test_id"], "category": case["category"],
                         "success": bool(output.get("success")),
                         "schema_compliance": bool(output.get("schema_compliance")),
                         "verifier_score": max(0.0, min(float(output.get("verifier_score") or 0), 1.0)),
                         "latency_ms": max(0, int(output.get("latency_ms") or 0)),
                         "timeout": "TIMEOUT" in (output.get("error_flags") or []),
                         "retry_count": attempts - 1, "token_usage": output.get("token_usage"),
                         "quota_consumed": consumed, "estimated_cost": output.get("estimated_cost"),
                         "hallucination_flags": output.get("hallucination_flags") or [],
                         "error_flags": output.get("error_flags") or [],
                         "determinism_score": max(0.0, min(float(output.get("determinism_score") or 0), 1.0)),
                         "tool_call_correctness": output.get("tool_call_correctness"),
                         "output_length": max(0, int(output.get("output_length") or 0))})
            if output.get("rate_limited"):
                stopped = "RATE_LIMITED"
                break
        result = self._score(plan, benchmark_id, rows, quota, stopped)
        errors = validate(result, RESULT_SCHEMA)
        if errors:
            raise AssertionError(f"PROVIDER_BENCHMARK_RESULT_V1 invalid: {errors}")
        return self.history.append_once(result)

    def _score(self, plan, benchmark_id, rows, quota, stopped):
        scores = {category: 0.0 for category in CATEGORIES}
        for row in rows:
            value = row["verifier_score"] * 100
            if row["category"] == "STRUCTURED_OUTPUT" and not row["schema_compliance"]:
                value = 0
            scores[row["category"]] = round(value, 2)
        passed = sum(1 for r in rows if r["success"] and r["verifier_score"] >= .7)
        reliability = round(100 * passed / len(rows), 2) if rows else 0.0
        latency = [r["latency_ms"] for r in rows]
        scorecard = {"QUALITY": round(statistics.mean(scores.values()), 2),
                     "RELIABILITY": reliability,
                     "SPEED": round(max(0, 100 - (statistics.mean(latency) / 50)), 2) if latency else 0,
                     "STRUCTURED_OUTPUT": scores["STRUCTURED_OUTPUT"], "CODING": scores["CODING"],
                     "REASONING": scores["REASONING"], "LONG_CONTEXT": scores["LONG_CONTEXT"],
                     "TOOL_USE": scores["TOOL_USE"],
                     "DETERMINISM": round(100 * statistics.mean(
                         [r["determinism_score"] for r in rows]), 2) if rows else 0,
                     "FREE_QUOTA_EFFICIENCY": min(100.0, round(100 * passed / max(quota, len(rows), 1), 2))}
        recommended = [role for role, category in ROLE_CATEGORY.items() if scores[category] >= 80]
        forbidden = [role for role, category in ROLE_CATEGORY.items() if scores[category] < 60]
        candidate = (plan["mode"] == "LIVE_EVALUATION" and len(rows) == len(CATEGORIES) and
                     reliability >= 80 and scorecard["STRUCTURED_OUTPUT"] >= 70 and not stopped)
        model = self._model(plan["provider_id"], plan["model_id"])
        return {"schema_version": 1, "benchmark_id": benchmark_id,
                "provider_id": plan["provider_id"], "model_id": plan["model_id"],
                "model_family": model["model_family"], "benchmark_version": BENCHMARK_VERSION,
                "timestamp": datetime.now(timezone.utc).isoformat(), "mode": plan["mode"],
                "test_count": len(rows), "passed": passed, "failed": len(rows) - passed,
                "per_category_scores": scores, "scorecard": scorecard,
                "overall_score": scorecard["QUALITY"],
                "latency_stats": {"mean_ms": round(statistics.mean(latency), 2) if latency else None,
                                  "max_ms": max(latency) if latency else None,
                                  "timeout_rate": round(sum(r["timeout"] for r in rows) / len(rows), 4) if rows else None,
                                  "retry_rate": round(sum(r["retry_count"] for r in rows) / len(rows), 4) if rows else None},
                "reliability_score": reliability,
                "quota_efficiency": scorecard["FREE_QUOTA_EFFICIENCY"],
                "recommended_roles": recommended, "forbidden_roles": forbidden,
                "confidence": "LOW" if plan["mode"] == "MOCK" else "MEDIUM",
                "evidence_level": "MOCK_ONLY" if plan["mode"] == "MOCK" else "LIVE_SINGLE_RUN",
                "production_candidate": False,
                "promotion_recommendation": "CANDIDATE" if candidate else "EVALUATION_ONLY",
                "human_approval_required": True,
                "limitations": (["Mock evidence cannot approve production use."] if plan["mode"] == "MOCK" else []) +
                               ([f"Benchmark stopped: {stopped}."] if stopped else []),
                "provenance": {"registry_id": self.registry.data["registry_id"],
                               "benchmark_version": BENCHMARK_VERSION,
                               "stopped_reason": stopped, "quota_consumed": quota}, "tests": rows}

    def list_results(self):
        return self.history.read()

    def latest(self, provider_id, model_id):
        rows = [r for r in self.history.read() if r.get("provider_id") == provider_id and
                r.get("model_id") == model_id]
        return rows[-1] if rows else None
