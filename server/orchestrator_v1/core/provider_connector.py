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
from core.specialist_review import (HUMAN_REJECTED_REWORK_REQUESTED,
                                   LOCAL_VERIFIER_REJECTED_REVIEW_REQUIRED,
                                   select_reviewer_candidates, validate_rework_response)
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
    # LOCAL_VERIFIER_REJECTED_TO_DYNAMIC_REVIEW_V1: a rework cycle is "used"
    # only once a reviewer's REWORK_INSTRUCTIONS actually reach the local
    # worker (_apply_rework) - a provider that is merely unavailable (parked
    # in WAITING_REVIEW_PROVIDER) never consumes one. The budget is shared by
    # the WHOLE lineage regardless of which door (human reject or local
    # verifier reject) opened each cycle, so a loop like
    # "local fail -> review -> local fail -> review -> ..." cannot run
    # forever - it always terminates at MANUAL_REVIEW.
    MAX_REWORK_CYCLES = 2

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
        is_review = escalation.get("classification") in (
            HUMAN_REJECTED_REWORK_REQUESTED, LOCAL_VERIFIER_REJECTED_REVIEW_REQUIRED)
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
            # LOCAL_VERIFIER_REJECTED_TO_DYNAMIC_REVIEW_V1: a FRESH
            # fail_local_bridge_task() escalation (no `candidates` key yet -
            # that is exactly what distinguishes it from one already in
            # review, including a budget-exhausted terminal one, whose
            # classification is LOCAL_VERIFIER_REJECTED_REVIEW_REQUIRED, not
            # this raw failure_class string) is converted into a real
            # Dynamic Specialist Review escalation here, once. Scoped
            # deliberately to this one failure_class - a different
            # MANUAL_REVIEW cause (e.g. LOCAL_MODEL_UNAVAILABLE) still dead-
            # ends exactly as before, unchanged.
            if (escalation.get("target") == "MANUAL_REVIEW" and
                    escalation.get("classification") == "LOCAL_VERIFIER_REJECTED"):
                self.request_review_after_local_failure(record["task_id"],
                                                        escalation["classification"])
                return True
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
            escalation, _ = self._refresh_candidates(record, escalation)
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

    def _refresh_candidates(self, record, escalation):
        """CANDIDATE_REFRESH_WITH_PROVENANCE_V1: a task must never stay stuck
        forever on the reviewer list that existed the moment it was rejected
        - a later deploy/policy change (e.g. a new FREE_ONLINE reviewer) has
        to reach already-escalated/parked tasks too, not just future ones.

        `initial_candidates` is written once (in request_review) and never
        overwritten again - the historical snapshot/lineage. `candidates` is
        the EFFECTIVE list, recomputed here from the current policy
        (select_reviewer_candidates - the single source of truth for
        capability; availability/cost/policy are still enforced exactly as
        before, by _first_usable_candidate and process_task's _policy() gate,
        unchanged) every time a task is about to be advanced or re-checked.

        Pure w.r.t. side effects when nothing changed (idempotent: calling
        this repeatedly with an unchanged policy returns the same effective
        list and appends nothing to the Ledger) - only an actual add/remove
        is recorded, so a quiet WAITING_REVIEW_PROVIDER poll never spams the
        audit trail on its own.
        """
        task_id = record["task_id"]
        work_type = (record.get("manifest") or {}).get("work_type")
        effective = select_reviewer_candidates(work_type)
        previous = escalation.get("candidates") or []
        initial = escalation.get("initial_candidates") or previous or effective
        updated = {**escalation, "candidates": effective, "initial_candidates": initial}
        if effective == previous:
            return updated, False
        added = [p for p in effective if p not in previous]
        removed = [p for p in previous if p not in effective]
        self.ledger.append("REVIEW_CANDIDATES_REFRESHED", task_id, {
            "work_type": work_type, "initial_candidates": initial,
            "previous_candidates": previous, "effective_candidates": effective,
            "added": added, "removed": removed}, actor="provider_connector_v1")
        return updated, True

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
        escalation, _ = self._refresh_candidates(record, escalation)
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

    def _rework_cycles_used(self, task_id):
        """Counted from the Ledger (append-only, never reset) rather than a
        stored field on the record - correct even for a lineage whose first
        cycle happened before this budget existed (e.g. a task already
        reworked once via the human-reject door), with no migration needed."""
        return sum(1 for event in self.ledger.read_for_task(task_id)
                  if event["event_type"] == "REWORK_INSTRUCTIONS_RECEIVED")

    def _begin_review(self, task_id, reject_reason, classification):
        """Shared entry point for both doors into the NEXUS Dynamic
        Specialist Review - a human REJECTed a WAITING_APPROVAL patch
        (request_review) or the Local Agent Bridge exhausted its bounded
        retries because the verifier rejected the local model's own output
        (request_review_after_local_failure). Same candidate selection,
        availability/policy/call machinery and rework hand-back either way -
        one state machine, two doors - and MAX_REWORK_CYCLES is enforced
        here, once, shared by the whole lineage regardless of which door
        opened each prior cycle."""
        cycles_used = self._rework_cycles_used(task_id)
        if cycles_used >= self.MAX_REWORK_CYCLES:
            record = self.queue.get(task_id)
            self.queue.transition(task_id, "ESCALATION_REQUIRED", escalation={
                "target": "MANUAL_REVIEW", "classification": classification,
                "reject_reason": reject_reason, "rework_budget_exhausted": True})
            self.ledger.append("REWORK_BUDGET_EXHAUSTED", task_id,
                {"cycles_used": cycles_used, "max_cycles": self.MAX_REWORK_CYCLES,
                 "classification": classification}, actor="provider_connector_v1")
            self._notify(record, f"Budget di rework esaurito per {task_id} "
                        f"({cycles_used}/{self.MAX_REWORK_CYCLES} cicli usati). "
                        "Serve una revisione manuale.", "MANUAL_REVIEW")
            return self.queue.get(task_id)
        record = self.queue.get(task_id)
        candidates = select_reviewer_candidates(record["manifest"].get("work_type"))
        context = build_review_packet(record, reject_reason)
        escalation = {"target": None, "classification": classification,
                     "candidates": candidates, "initial_candidates": list(candidates),
                     "context_packet": context, "reject_reason": reject_reason}
        self.queue.transition(task_id, "ESCALATION_REQUIRED", escalation=escalation)
        self.ledger.append("REVIEW_REQUESTED", task_id,
            {"candidates": candidates, "cycles_used_before": cycles_used,
             "max_cycles": self.MAX_REWORK_CYCLES}, actor="provider_connector_v1")
        self._advance_candidate_escalation(self.queue.get(task_id), escalation)
        return self.queue.get(task_id)

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
        self.ledger.append("HUMAN_REJECTED", task_id, {"reason": reject_reason},
                           actor="provider_connector_v1")
        return self._begin_review(task_id, reject_reason, HUMAN_REJECTED_REWORK_REQUESTED)

    def request_review_after_local_failure(self, task_id, failure_class):
        """LOCAL_VERIFIER_REJECTED_TO_DYNAMIC_REVIEW_V1: the second door into
        the same Dynamic Specialist Review. fail_local_bridge_task() already
        parked the task at ESCALATION_REQUIRED/target=MANUAL_REVIEW when the
        Local Agent Bridge exhausted its bounded retries because the
        verifier rejected the local model's own output - never a human
        reject, and no proposed_patch exists yet (the attempt never reached
        WAITING_APPROVAL). build_review_packet() already degrades
        gracefully to '(nessuna patch disponibile)' for that case, reused
        unchanged - no second context-building path."""
        record = self.queue.get(task_id)
        if record["state"] != "ESCALATION_REQUIRED":
            raise AssertionError(
                f"local-failure review requires ESCALATION_REQUIRED, got {record['state']}")
        escalation = record.get("escalation") or {}
        if escalation.get("target") != "MANUAL_REVIEW" or escalation.get("classification") != failure_class:
            raise AssertionError("local-failure review only applies to fail_local_bridge_task's "
                                 "own fresh MANUAL_REVIEW escalation")
        self.ledger.append("LOCAL_VERIFIER_REJECTED", task_id, {"failure_class": failure_class},
                           actor="provider_connector_v1")
        return self._begin_review(task_id, f"local verifier rejected: {failure_class}",
                                  LOCAL_VERIFIER_REJECTED_REVIEW_REQUIRED)

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
