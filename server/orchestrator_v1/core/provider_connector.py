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
from core.specialist_review import (HUMAN_REJECTED_REWORK_REQUESTED, select_reviewer_candidates,
                                   validate_rework_response)
from core.context_packet import build_review_packet

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
    def __init__(self, orchestrator, adapters=None, *, timeout_seconds=90, max_attempts=2,
                 telegram_notifier=None):
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
        # Optional callable(chat_id, response_dict) for the NEXUS Dynamic
        # Specialist Review's proactive push (entering/resuming
        # WAITING_REVIEW_PROVIDER). Defaults to a no-op so this class stays
        # fully testable without Telegram wired - no existing caller breaks.
        self.telegram_notifier = telegram_notifier

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
        escalation = record.get("escalation") or {}
        target = escalation.get("target")
        is_review = escalation.get("classification") == HUMAN_REJECTED_REWORK_REQUESTED
        # A dynamic specialist review already resolved `target` to a live
        # provider_id (select_reviewer_candidates + state() check) - never a
        # fixed tier name, so it is used directly instead of through
        # TARGET_PROVIDER (which maps a single hardcoded tier -> provider for
        # the normal, non-review escalation path, unchanged below).
        provider_id = target if is_review else TARGET_PROVIDER.get(target)
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

        passed, errors = (validate_rework_response(result.output) if is_review
                         else self._verify_output(result.output))
        if not passed:
            self.queue.transition(task_id, "ESCALATION_REQUIRED", provider_execution={
                "status": "VERIFICATION_FAILED", "provider": provider_id,
                "errors": errors, "premium_calls": attempts, "duration_seconds": duration})
            self.ledger.append("PROVIDER_FAILED", task_id,
                {"provider": provider_id, "failure_class": "VERIFICATION_FAILED"},
                actor="provider_connector_v1")
            return self.queue.get(task_id)

        if is_review:
            return self._apply_rework(task_id, result, provider_id, key, attempts, duration, request)

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
            escalation = record.get("escalation") or {}
            retry_at = (record.get("provider_execution") or {}).get("retry_not_before")
            if retry_at:
                try:
                    if datetime.fromisoformat(retry_at) > datetime.now(timezone.utc):
                        continue
                except ValueError:
                    continue
            candidates = escalation.get("candidates")
            if candidates:
                if self._advance_candidate_escalation(record, escalation):
                    return True
                continue
            target = escalation.get("target")
            provider_id = TARGET_PROVIDER.get(target)
            if provider_id and provider_id in self.adapters and self.adapters[provider_id].state() in (
                    "AVAILABLE", "LOW_QUOTA"):
                self.process_task(record["task_id"])
                return True
        # WAITING_REVIEW_PROVIDER is a distinct, persistent "nobody capable is
        # available right now" state (see task_queue.py) - this is its only
        # watcher. No continuous premium polling: it runs on the same cadence
        # as the rest of this idle-dispatch cycle, never a tight loop of its
        # own.
        for record in self.queue.list_by_state("WAITING_REVIEW_PROVIDER"):
            escalation = record.get("escalation") or {}
            candidates = escalation.get("candidates") or []
            chosen = self._first_usable_candidate(candidates)
            if chosen:
                self.queue.transition(record["task_id"], "ESCALATION_REQUIRED",
                                      escalation={**escalation, "target": chosen})
                self.ledger.append("REVIEW_PROVIDER_RESUMED", record["task_id"],
                    {"provider": chosen}, actor="provider_connector_v1")
                self._notify(record, f"{chosen} e' tornato disponibile: riprendo la review "
                            f"della patch rifiutata ({record['task_id']}).",
                            "REVIEW_PROVIDER_RESUMED")
                self.process_task(record["task_id"])
                return True
            # Bookkeeping only - no state change, no loss of the original
            # patch/verifier result (still on the record as proposed_patch).
            self.queue.annotate(record["task_id"], escalation={
                **escalation, "candidate_states": self._candidate_states(candidates),
                "last_checked_at": now_iso()})
        return False

    def _first_usable_candidate(self, candidates):
        for provider_id in candidates:
            adapter = self.adapters.get(provider_id)
            if adapter and adapter.state() in ("AVAILABLE", "LOW_QUOTA"):
                return provider_id
        return None

    def _candidate_states(self, candidates):
        return {provider_id: (self.adapters[provider_id].state() if provider_id in self.adapters
                             else "UNKNOWN") for provider_id in candidates}

    def _notify(self, record, summary, status):
        """Best-effort proactive push - never raises, never part of the
        state machine's correctness. No Telegram wired (e.g. most tests) ->
        silently a no-op, same as every other optional dependency here."""
        if not self.telegram_notifier:
            return
        created_by = str((record.get("manifest") or {}).get("created_by") or "")
        if not created_by.startswith("jarvis:"):
            return
        chat_id = created_by.split(":", 1)[1]
        try:
            self.telegram_notifier(chat_id, {"summary": summary, "status": status,
                                            "task_id": record["task_id"]})
        except Exception:
            pass

    def _advance_candidate_escalation(self, record, escalation):
        """Shared by request_review()'s initial classification and run_once()'s
        ongoing scan of ESCALATION_REQUIRED-with-candidates records - same
        capability > availability > cost > preference decision either way,
        never two implementations of it."""
        task_id = record["task_id"]
        candidates = escalation["candidates"]
        chosen = self._first_usable_candidate(candidates)
        if chosen:
            self.queue.annotate(task_id, escalation={**escalation, "target": chosen})
            self.process_task(task_id)
            return True
        states = self._candidate_states(candidates)
        self.queue.transition(task_id, "WAITING_REVIEW_PROVIDER", escalation={
            **escalation, "candidate_states": states, "last_checked_at": now_iso()})
        self.ledger.append("WAITING_REVIEW_PROVIDER", task_id,
            {"candidates": candidates, "candidate_states": states,
             "reject_reason": escalation.get("reject_reason")}, actor="provider_connector_v1")
        unavailable = ", ".join(f"{pid} {state}" for pid, state in states.items())
        self._notify(record, f"Patch di {task_id} rifiutata. Nessun reviewer disponibile ora "
                    f"({unavailable}). Ti aggiorno appena uno torna disponibile.",
                    "WAITING_REVIEW_PROVIDER")
        return False

    def request_review(self, task_id, reject_reason):
        """Entry point for the NEXUS Dynamic Specialist Review: a human
        REJECTed a proposed patch. Never writes/executes a patch itself -
        only selects an ordered list of candidate reviewers (capability),
        hands off to the existing availability/policy/call machinery above,
        and the result either feeds REWORK_INSTRUCTIONS back to the local
        worker (_apply_rework) or parks the task in WAITING_REVIEW_PROVIDER
        until one becomes available (_advance_candidate_escalation)."""
        record = self.queue.get(task_id)
        if record["state"] != "WAITING_APPROVAL":
            raise AssertionError("specialist review requires WAITING_APPROVAL")
        candidates = select_reviewer_candidates(record["manifest"].get("work_type"))
        context = build_review_packet(record, reject_reason)
        escalation = {"target": None, "classification": HUMAN_REJECTED_REWORK_REQUESTED,
                     "candidates": candidates, "context_packet": context,
                     "reject_reason": reject_reason}
        self.queue.transition(task_id, "ESCALATION_REQUIRED", escalation=escalation)
        self.ledger.append("HUMAN_REJECTED", task_id, {"reason": reject_reason},
                           actor="provider_connector_v1")
        self.ledger.append("REVIEW_REQUESTED", task_id, {"candidates": candidates},
                           actor="provider_connector_v1")
        self._advance_candidate_escalation(self.queue.get(task_id), escalation)
        return self.queue.get(task_id)

    def _apply_rework(self, task_id, result, provider_id, key, attempts, duration, request):
        """A specialist review never completes the task - its output is
        corrective instructions for the SAME local worker that produced the
        rejected patch. Reuses the exact existing retry-with-feedback
        mechanism (LocalTaskHandler.build_prompt reading
        action_params.rework_instructions), never a second code path for
        'apply a reviewer's patch'."""
        output = result.output
        feedback = (
            f"Una revisione specialistica ({provider_id}) ha esaminato la patch rifiutata "
            f"dall'utente e ha trovato: {'; '.join(output.get('problems_found') or []) or '(nessun problema elencato)'}.\n"
            f"Istruzioni correttive: {output['rework_instructions']}\n"
            f"Test richiesti: {', '.join(output.get('required_tests') or []) or '(quelli gia\' previsti)'}\n"
            f"Rischi segnalati: {'; '.join(output.get('risks') or []) or '(nessuno)'}")
        record = self.queue.get(task_id)
        action_params = dict(record.get("action_params") or {})
        action_params["rework_instructions"] = feedback
        execution = {"status": "REWORK_RECEIVED", "provider": provider_id,
                     "provider_request_id": result.provider_request_id, "idempotency_key": key,
                     "premium_calls": attempts, "duration_seconds": duration, "verified": True,
                     "output": output, "provenance": request}
        self.queue.transition(task_id, "QUEUED", action_params=action_params,
                              provider_execution=execution, retry_count=0)
        self.ledger.append("REVIEW_COMPLETED", task_id,
            {"provider": provider_id, "problems_found": output.get("problems_found")},
            actor="provider_connector_v1")
        self.ledger.append("REWORK_INSTRUCTIONS_RECEIVED", task_id, {"provider": provider_id},
                           actor="provider_connector_v1")
        return self.queue.get(task_id)
