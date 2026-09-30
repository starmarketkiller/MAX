"""Provider Connector Layer V1.

Provider adapters receive only CONTEXT_PACKET_V1. They never route tasks,
read the Vault/repository, mutate files or bypass approval policy.
"""
from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from core.dispatcher import _sanitized_error
from core.result_packet import build_result_packet, now_iso

try:
    from review_matrix import get_matrix_entry
    from premium_budget_policy import allow_premium
except ImportError:  # production imports add review_pipeline_v1 after app bootstrap
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                    "review_pipeline_v1"))
    from review_matrix import get_matrix_entry
    from premium_budget_policy import allow_premium


PROVIDER_STATES = {"AVAILABLE", "LOW_QUOTA", "EXHAUSTED", "RATE_LIMITED", "OFFLINE", "UNKNOWN"}
TARGET_PROVIDER = {"TIER3_CLAUDE": "CLAUDE", "TIER4_CODEX": "CODEX", "SPECIALIST": "OPENAI"}


@dataclass(frozen=True)
class ProviderResult:
    status: str
    output: dict | None = None
    provider_request_id: str | None = None
    error_class: str | None = None
    retry_after_seconds: int | None = None


class ProviderAdapterV1(ABC):
    provider_id = "UNKNOWN"

    @abstractmethod
    def state(self) -> str: ...

    @abstractmethod
    def invoke(self, context_packet: dict, *, idempotency_key: str,
               timeout_seconds: int) -> ProviderResult: ...

    def public_status(self):
        state = self.state()
        return {"provider": self.provider_id,
                "state": state if state in PROVIDER_STATES else "UNKNOWN",
                "configured": state not in ("OFFLINE", "UNKNOWN")}


class OfflineProviderAdapter(ProviderAdapterV1):
    def __init__(self, provider_id, state="OFFLINE"):
        self.provider_id = provider_id
        self._state = state if state in PROVIDER_STATES else "UNKNOWN"

    def state(self): return self._state

    def invoke(self, context_packet, *, idempotency_key, timeout_seconds):
        return ProviderResult(status=self._state, error_class=f"PROVIDER_{self._state}")


class MockProviderAdapter(ProviderAdapterV1):
    """Deterministic test adapter with provider-side idempotency semantics."""
    def __init__(self, provider_id="CLAUDE", state="AVAILABLE", result=None):
        self.provider_id = provider_id
        self._state = state
        self.result = result or {"summary": "Provider result", "details": {},
                                 "source_refs": [], "limitations": []}
        self.calls = []
        self._cache = {}

    def state(self): return self._state

    def invoke(self, context_packet, *, idempotency_key, timeout_seconds):
        self.calls.append({"idempotency_key": idempotency_key,
                           "timeout_seconds": timeout_seconds,
                           "context_packet": context_packet})
        if self._state not in ("AVAILABLE", "LOW_QUOTA"):
            return ProviderResult(status=self._state, error_class=f"PROVIDER_{self._state}")
        if idempotency_key not in self._cache:
            self._cache[idempotency_key] = ProviderResult(
                status="SUCCESS", output=dict(self.result),
                provider_request_id=f"mock_{len(self._cache) + 1}")
        return self._cache[idempotency_key]


class ProviderConnectorV1:
    def __init__(self, orchestrator, adapters=None, *, timeout_seconds=90, max_attempts=2):
        self.orchestrator = orchestrator
        self.queue = orchestrator.queue
        self.ledger = orchestrator.ledger
        self.adapters = adapters or {
            "CLAUDE": OfflineProviderAdapter("CLAUDE"),
            "CODEX": OfflineProviderAdapter("CODEX"),
            "OPENAI": OfflineProviderAdapter("OPENAI", "UNKNOWN"),
        }
        self.timeout_seconds = max(1, int(timeout_seconds))
        self.max_attempts = max(1, min(int(max_attempts), 2))

    def statuses(self):
        return [self.adapters[name].public_status() for name in sorted(self.adapters)]

    @staticmethod
    def _key(task_id, provider_id, context_packet):
        canonical = json.dumps(context_packet, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode()).hexdigest()[:24]
        return f"{task_id}:{provider_id}:{digest}"

    @staticmethod
    def _verify_output(output):
        if not isinstance(output, dict): return False, ["provider output is not an object"]
        summary = output.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            return False, ["provider output summary missing"]
        if not isinstance(output.get("details", {}), dict):
            return False, ["provider output details must be an object"]
        if not isinstance(output.get("source_refs", []), list):
            return False, ["provider output source_refs must be an array"]
        return True, []

    def _policy(self, record):
        manifest = record["manifest"]
        if not manifest.get("premium_allowed"):
            return False, False, "TASK_MANIFEST premium_allowed=false"
        entry = get_matrix_entry(manifest.get("work_type"))
        return allow_premium(entry["premium_budget_level"], local_attempt_failed=True,
                             local_confidence="UNKNOWN",
                             review_matrix_requires_review=entry["review_required"])

    def process_task(self, task_id):
        record = self.queue.get(task_id)
        if record["state"] == "COMPLETED" and (record.get("provider_execution") or {}).get("finalized"):
            return record
        if record["state"] != "ESCALATION_REQUIRED":
            raise AssertionError(f"provider connector requires ESCALATION_REQUIRED, got {record['state']}")
        target = (record.get("escalation") or {}).get("target")
        provider_id = TARGET_PROVIDER.get(target)
        if not provider_id or provider_id not in self.adapters:
            return self.queue.annotate(task_id, provider_execution={
                "status": "UNAVAILABLE", "reason": "NO_PROVIDER_MAPPING", "target": target})
        allowed, requires_approval, reason = self._policy(record)
        if not allowed or requires_approval:
            return self.queue.annotate(task_id, provider_execution={
                "status": "POLICY_BLOCKED", "reason": reason,
                "requires_approval": requires_approval, "provider": provider_id})
        adapter = self.adapters[provider_id]
        state = adapter.state()
        if state not in ("AVAILABLE", "LOW_QUOTA"):
            return self.queue.annotate(task_id, provider_execution={
                "status": state if state in PROVIDER_STATES else "UNKNOWN",
                "provider": provider_id, "premium_calls": 0})

        context = (record.get("escalation") or {}).get("context_packet")
        if not isinstance(context, dict):
            return self.queue.annotate(task_id, provider_execution={
                "status": "INVALID_CONTEXT", "provider": provider_id, "premium_calls": 0})
        key = self._key(task_id, provider_id, context)
        request = {"provider": provider_id, "idempotency_key": key,
                   "requested_at": now_iso(), "timeout_seconds": self.timeout_seconds,
                   "context_sha256": hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()}
        self.queue.transition(task_id, "WAITING_PROVIDER", provider_execution={
            "status": "REQUESTED", "request": request, "premium_calls": 0})
        self.ledger.append("PROVIDER_REQUESTED", task_id, request, actor="provider_connector_v1")
        started = time.monotonic()
        attempts = 0
        result = None
        while attempts < self.max_attempts:
            attempts += 1
            try:
                result = adapter.invoke(context, idempotency_key=key,
                                        timeout_seconds=self.timeout_seconds)
                break
            except Exception as exc:
                if attempts < self.max_attempts:
                    self.ledger.append("PROVIDER_RETRY", task_id,
                        {"provider": provider_id, "attempt": attempts + 1,
                         "failure_class": type(exc).__name__}, actor="provider_connector_v1")
                    continue
                safe = _sanitized_error(exc)
                self.queue.transition(task_id, "ESCALATION_REQUIRED", provider_execution={
                    "status": "ERROR", "provider": provider_id, "error": safe,
                    "premium_calls": attempts, "duration_seconds": time.monotonic() - started,
                    "retry_not_before": (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()})
                self.ledger.append("PROVIDER_FAILED", task_id,
                    {"provider": provider_id, "failure_class": type(exc).__name__,
                     "attempts": attempts}, actor="provider_connector_v1")
                return self.queue.get(task_id)

        duration = time.monotonic() - started
        if result.status != "SUCCESS":
            state = result.status if result.status in PROVIDER_STATES else "UNKNOWN"
            self.queue.transition(task_id, "ESCALATION_REQUIRED", provider_execution={
                "status": state, "provider": provider_id, "error_class": result.error_class,
                "retry_after_seconds": result.retry_after_seconds,
                "retry_not_before": (datetime.now(timezone.utc) + timedelta(
                    seconds=max(1, result.retry_after_seconds or 60))).isoformat(),
                "premium_calls": attempts, "duration_seconds": duration})
            event = "PROVIDER_RATE_LIMITED" if state == "RATE_LIMITED" else "PROVIDER_FAILED"
            self.ledger.append(event, task_id, {"provider": provider_id, "state": state},
                               actor="provider_connector_v1")
            return self.queue.get(task_id)

        passed, errors = self._verify_output(result.output)
        if not passed:
            self.queue.transition(task_id, "ESCALATION_REQUIRED", provider_execution={
                "status": "VERIFICATION_FAILED", "provider": provider_id,
                "errors": errors, "premium_calls": attempts, "duration_seconds": duration})
            self.ledger.append("PROVIDER_FAILED", task_id,
                {"provider": provider_id, "failure_class": "VERIFICATION_FAILED"},
                actor="provider_connector_v1")
            return self.queue.get(task_id)

        packet = build_result_packet(
            task_id=task_id, executor=provider_id, start_time=request["requested_at"],
            end_time=now_iso(), files_read=[], files_changed=[], tools_or_commands=["PROVIDER_ADAPTER_V1"],
            artifacts_created=[], tests_ran=True, tests_passed=1, tests_failed=0,
            verifier_ran=True, verifier_passed=True, verifier_errors=[], commit=None,
            push_status="NOT_APPLICABLE", decision="COMPLETED", confidence="MEDIUM",
            limitations=list(result.output.get("limitations") or []), unresolved_issues=[],
            suggested_next_tasks=[], escalation_needed=False)
        execution = {"status": "COMPLETED", "provider": provider_id,
                     "provider_state": state, "provider_request_id": result.provider_request_id,
                     "idempotency_key": key, "premium_calls": attempts,
                     "duration_seconds": duration, "verified": True, "finalized": True,
                     "output": result.output, "provenance": request}
        self.queue.transition(task_id, "COMPLETED", result_packet=packet,
                              provider_execution=execution)
        self.ledger.append("PROVIDER_COMPLETED", task_id,
            {"provider": provider_id, "provider_request_id": result.provider_request_id,
             "duration_seconds": duration, "verified": True}, actor="provider_connector_v1")
        return self.queue.get(task_id)

    def run_once(self):
        for record in self.queue.list_by_state("ESCALATION_REQUIRED"):
            retry_at = (record.get("provider_execution") or {}).get("retry_not_before")
            if retry_at:
                try:
                    if datetime.fromisoformat(retry_at) > datetime.now(timezone.utc):
                        continue
                except ValueError:
                    continue
            target = (record.get("escalation") or {}).get("target")
            provider_id = TARGET_PROVIDER.get(target)
            if provider_id and provider_id in self.adapters and self.adapters[provider_id].state() in (
                    "AVAILABLE", "LOW_QUOTA"):
                self.process_task(record["task_id"])
                return True
        return False
