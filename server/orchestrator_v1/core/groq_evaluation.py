"""Groq evaluation-only adapter and Free Quota Treasury V1-lite."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from core.provider_connector import ProviderAdapterV1, ProviderResult
from core.specialist_review import REVIEWER_SYSTEM_PROMPT


GROQ_BASE_URL = "https://api.groq.com/openai/v1"
RATE_HEADERS = ("x-ratelimit-limit-requests", "x-ratelimit-remaining-requests",
                "x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens",
                "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens", "retry-after")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _integer(value):
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class FreeQuotaTreasuryV1Lite:
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        if not self.path.exists():
            return {"provider_id": "GROQ", "requests_used": None, "requests_remaining": None,
                    "tokens_used": None, "tokens_remaining": None, "reset_time": None,
                    "last_updated": None, "source": "GROQ_RESPONSE_HEADERS",
                    "observed_requests": 0}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def update(self, headers):
        normalized = {str(k).lower(): v for k, v in dict(headers or {}).items()}
        previous = self.read()
        limit_requests = _integer(normalized.get("x-ratelimit-limit-requests"))
        remaining_requests = _integer(normalized.get("x-ratelimit-remaining-requests"))
        limit_tokens = _integer(normalized.get("x-ratelimit-limit-tokens"))
        remaining_tokens = _integer(normalized.get("x-ratelimit-remaining-tokens"))
        data = {"provider_id": "GROQ",
                "requests_used": (limit_requests - remaining_requests
                                  if limit_requests is not None and remaining_requests is not None else None),
                "requests_remaining": remaining_requests,
                "tokens_used": (limit_tokens - remaining_tokens
                                if limit_tokens is not None and remaining_tokens is not None else None),
                "tokens_remaining": remaining_tokens,
                "reset_time": normalized.get("x-ratelimit-reset-requests") or
                              normalized.get("x-ratelimit-reset-tokens"),
                "request_reset": normalized.get("x-ratelimit-reset-requests"),
                "token_reset": normalized.get("x-ratelimit-reset-tokens"),
                "retry_after_seconds": _integer(normalized.get("retry-after")),
                "last_updated": _now(), "source": "GROQ_RESPONSE_HEADERS",
                "observed_requests": int(previous.get("observed_requests") or 0) + 1}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.path)
        return data


class UrllibGroqTransport:
    def request(self, method, url, *, headers, payload=None, timeout=30):
        body = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status, dict(response.headers), json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            try:
                response_body = json.loads(exc.read().decode())
            except Exception:
                response_body = {}
            return exc.code, dict(exc.headers or {}), response_body
        except (TimeoutError, urllib.error.URLError) as exc:
            if isinstance(exc, TimeoutError) or isinstance(getattr(exc, "reason", None), TimeoutError):
                raise TimeoutError("Groq evaluation request timed out") from None
            raise RuntimeError("Groq evaluation network unavailable") from None


class GroqEvaluationAdapterV1:
    provider_id = "GROQ"

    def __init__(self, *, api_key=None, enabled=False, model_ids=None, treasury_path,
                 transport=None):
        self._api_key = api_key or ""
        self.enabled = bool(enabled)
        self.model_ids = tuple(dict.fromkeys(model_ids or ()))[:3]
        self.treasury = FreeQuotaTreasuryV1Lite(treasury_path)
        self.transport = transport or UrllibGroqTransport()
        self.state = "AVAILABLE" if self.configured else "OFFLINE"

    @property
    def configured(self):
        return bool(self.enabled and self._api_key and self.model_ids)

    @classmethod
    def from_environment(cls, *, treasury_path, transport=None):
        models = [item.strip() for item in os.environ.get(
            "NEXUS_GROQ_EVALUATION_MODELS", "").split(",") if item.strip()]
        enabled = os.environ.get("NEXUS_GROQ_LIVE_EVALUATION_ENABLED", "false").lower() == "true"
        return cls(api_key=os.environ.get("GROQ_API_KEY"), enabled=enabled,
                   model_ids=models, treasury_path=treasury_path, transport=transport)

    def status(self):
        return {"provider_id": "GROQ", "mode": "EVALUATION_ONLY",
                "configured": self.configured, "live_evaluation_enabled": self.enabled,
                "api_key_present": bool(self._api_key), "configured_model_count": len(self.model_ids),
                "state": self.state, "production_routing_enabled": False}

    def describe_model(self, model_id):
        if model_id not in self.model_ids:
            return None
        value = model_id.lower()
        family = "QWEN" if "qwen" in value else ("LLAMA" if "llama" in value else
                 ("GPT_OSS" if "gpt-oss" in value else "OTHER"))
        return {"provider_id": "GROQ", "model_id": model_id, "model_family": family,
                "state": self.state, "configured": self.configured,
                "verified_for_production": False, "free_tier_available": True,
                "estimated_cost_class": "FREE_TIER_EVALUATION", "quota_type": "RESPONSE_HEADERS",
                "quota_remaining": None, "context_window": None, "supports_tools": None,
                "supports_images": None, "supports_structured_output": None, "supports_code": None,
                "supports_long_context": None, "supports_reasoning": None,
                "privacy_class": "REMOTE_REDACTED_CONTEXT_ONLY", "allowed_task_types": [],
                "forbidden_task_types": [], "preferred_roles": ["EVALUATION_ONLY"],
                "fallback_priority": 999, "last_health_check": None, "last_benchmark": None,
                "benchmark_score": None, "notes": "Runtime-configured evaluation model."}

    def discover(self, *, timeout_seconds=10):
        if not self.configured:
            return {"available": [], "configured": list(self.model_ids),
                    "eligible": [], "reason": "GROQ_EVALUATION_NOT_CONFIGURED"}
        status, headers, body = self.transport.request("GET", f"{GROQ_BASE_URL}/models",
            headers=self._headers(), timeout=timeout_seconds)
        self.treasury.update(headers)
        if status == 429:
            return {"available": [], "configured": list(self.model_ids), "eligible": [],
                    "reason": "RATE_LIMITED"}
        if status != 200:
            return {"available": [], "configured": list(self.model_ids), "eligible": [],
                    "reason": f"HTTP_{status}"}
        available = sorted(item.get("id") for item in body.get("data", [])
                           if isinstance(item, dict) and item.get("active") is not False and item.get("id"))
        return {"available": available, "configured": list(self.model_ids),
                "eligible": [model for model in self.model_ids if model in available], "reason": None}

    def _headers(self):
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json",
                "User-Agent": "NEXUS-Groq-Evaluation-V1"}

    def evaluate(self, case, *, idempotency_key, timeout_seconds):
        if not self.configured:
            raise RuntimeError("Groq evaluation is not configured")
        model_id = case.get("model_id")
        if model_id not in self.model_ids:
            return self._failure("MODEL_NOT_CONFIGURED")
        prompt = ("Return only JSON with keys answer and confidence. "
                  f"Benchmark category: {case['category']}. Test id: {case['test_id']}. "
                  "Give a concise, policy-safe response to: explain the requested capability.")
        started = time.monotonic()
        status, headers, body = self.transport.request("POST", f"{GROQ_BASE_URL}/chat/completions",
            headers={**self._headers(), "Idempotency-Key": idempotency_key},
            payload={"model": model_id, "messages": [{"role": "user", "content": prompt}],
                     "temperature": 0, "max_completion_tokens": 256}, timeout=timeout_seconds)
        treasury = self.treasury.update(headers)
        latency = int((time.monotonic() - started) * 1000)
        if status == 429:
            return {**self._failure("RATE_LIMITED", latency), "rate_limited": True,
                    "quota_metadata": treasury}
        if status in (400, 404):
            return {**self._failure("MODEL_UNAVAILABLE", latency), "quota_metadata": treasury}
        if status != 200:
            return {**self._failure(f"PROVIDER_HTTP_{status}", latency), "quota_metadata": treasury}
        choices = body.get("choices") or []
        content = (((choices[0] if choices else {}).get("message") or {}).get("content") or "")
        try:
            parsed = json.loads(content)
            schema_ok = isinstance(parsed, dict) and isinstance(parsed.get("answer"), str)
        except (json.JSONDecodeError, TypeError):
            schema_ok = False
        usage = body.get("usage") or {}
        return {"success": schema_ok, "verifier_score": 1.0 if schema_ok else 0.3,
                "schema_compliance": schema_ok, "latency_ms": latency,
                "token_usage": usage.get("total_tokens"), "quota_consumed": 1,
                "estimated_cost": None, "hallucination_flags": [],
                "error_flags": [] if schema_ok else ["INVALID_JSON_SCHEMA"],
                "determinism_score": 1.0, "tool_call_correctness": None,
                "output_length": len(content), "quota_metadata": treasury}

    @staticmethod
    def _failure(reason, latency=0):
        return {"success": False, "verifier_score": 0, "schema_compliance": False,
                "latency_ms": latency, "token_usage": None, "quota_consumed": 0,
                "estimated_cost": None, "hallucination_flags": [], "error_flags": [reason],
                "determinism_score": 0, "tool_call_correctness": None, "output_length": 0}


class GroqReviewAdapter(ProviderAdapterV1):
    """FREE_ONLINE reviewer for the NEXUS Dynamic Specialist Review -
    deliberately a SEPARATE class from GroqEvaluationAdapterV1, never that
    one promoted to production. Reuses only the transport
    (UrllibGroqTransport/GROQ_BASE_URL); its own credential (GROQ_API_KEY -
    sharing a credential with the evaluation adapter is not the same as
    sharing production authorization) and its own, independently configured
    model (NEXUS_GROQ_REVIEW_MODEL - evaluation's NEXUS_GROQ_EVALUATION_MODELS
    stays evaluation-only, untouched by this class).

    Never writes or executes a patch: invoke() only ever returns the bounded
    review shape; core/specialist_review.py:validate_rework_response() is
    the sole gate deciding whether that shape is acceptable, and
    ProviderConnectorV1._apply_rework() is the only place a rework ever
    reaches the local worker - identical contract to ClaudeProviderAdapter,
    same REVIEWER_SYSTEM_PROMPT, by design."""
    provider_id = "GROQ"

    def __init__(self, *, api_key=None, model_id=None, transport=None,
                failure_threshold=3, cooldown_seconds=120):
        self._api_key = api_key or ""
        self._model_id = model_id or ""
        self.transport = transport or UrllibGroqTransport()
        # A small inline breaker, not app.py's _CircuitBreaker: importing
        # from app.py here would be circular (app.py imports this module).
        # Same semantics (N consecutive failures -> timed cooldown).
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._failures = 0
        self._open_until = 0.0

    @classmethod
    def from_environment(cls, *, transport=None):
        return cls(api_key=os.environ.get("GROQ_API_KEY"),
                   model_id=os.environ.get("NEXUS_GROQ_REVIEW_MODEL", "openai/gpt-oss-120b"),
                   transport=transport)

    @property
    def configured(self):
        return bool(self._api_key and self._model_id)

    def _breaker_open(self):
        if self._open_until and time.time() < self._open_until:
            return True
        if self._open_until:
            self._open_until = 0.0
            self._failures = 0
        return False

    def _record(self, ok):
        if ok:
            self._failures = 0
            return
        self._failures += 1
        if self._failures >= self._failure_threshold:
            self._open_until = time.time() + self._cooldown_seconds

    def state(self):
        if not self.configured:
            return "OFFLINE"
        if self._breaker_open():
            return "RATE_LIMITED"
        return "AVAILABLE"

    @staticmethod
    def _extract_json(text):
        # Mirrors ClaudeProviderAdapter._extract_json in app.py exactly -
        # duplicated on purpose (a few lines, no cross-module dependency for
        # it) rather than shared, same reasoning as elsewhere in this
        # feature (e.g. evaluate_auto_approval.py's SELF_PROTECTED_PATHS).
        value = (text or "").strip()
        if value.startswith("```"):
            value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
            value = re.sub(r"\s*```$", "", value)
        return json.loads(value)

    def invoke(self, context_packet, *, idempotency_key, timeout_seconds):
        payload = {"model": self._model_id, "temperature": 0, "max_completion_tokens": 1536,
                  "messages": [{"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
                              {"role": "user",
                               "content": json.dumps(context_packet, ensure_ascii=False)}]}
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json",
                  "User-Agent": "NEXUS-Groq-Review-V1", "Idempotency-Key": idempotency_key}
        try:
            status, _headers, body = self.transport.request(
                "POST", f"{GROQ_BASE_URL}/chat/completions", headers=headers, payload=payload,
                timeout=timeout_seconds)
        except TimeoutError:
            self._record(False)
            return ProviderResult(status="UNKNOWN", error_class="GROQ_TIMEOUT")
        except RuntimeError:
            self._record(False)
            return ProviderResult(status="UNKNOWN", error_class="GROQ_NETWORK_UNAVAILABLE")

        if status == 429:
            self._record(False)
            return ProviderResult(status="RATE_LIMITED", error_class="GROQ_RATE_LIMITED")
        if status in (401, 403):
            self._record(False)
            return ProviderResult(status="OFFLINE", error_class=f"GROQ_AUTH_{status}")
        if status != 200:
            self._record(False)
            # Covers 400/404 (e.g. this account cannot see the configured
            # model) and any other non-success status - never assumed to be
            # the same thing as "no quota left", always its own diagnostic.
            return ProviderResult(status="UNKNOWN", error_class=f"GROQ_HTTP_{status}")

        self._record(True)
        choices = body.get("choices") or []
        content = (((choices[0] if choices else {}).get("message") or {}).get("content") or "")
        try:
            parsed = self._extract_json(content)
        except (json.JSONDecodeError, ValueError):
            # Transport succeeded; the model just didn't follow the shape -
            # validate_rework_response() rejects this, same as Claude's.
            parsed = {"unparsed_response": content}
        return ProviderResult(status="SUCCESS", output=parsed,
                             provider_request_id=f"groq:{idempotency_key[:16]}")
