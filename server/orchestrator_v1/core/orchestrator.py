#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - classe Orchestrator top-level.

Collega: TaskQueue, EventLedger, Router, deterministic_worker, ollama_worker,
retry_escalation, context_packet, result_packet.

Per i task TIER1/2 (locali via Ministral) il "come" concreto (prompt da
mandare, come verificare la risposta, come applicare l'output) e' delegato
a un LocalTaskHandler registrato per action - il Core resta generico, ogni
tipo concreto di task (fix di un test fragile, backfill di una metrica,
ecc.) porta la propria logica, cosi' come gia' fatto nei pilot delle fasi
precedenti (Claude orchestra, il worker locale fa il lavoro).

Approval boundary (Fase 14 del task): un handler che produce un cambiamento
a un file REALE del repository (non sandbox) deve dichiararlo
(`ApplyResult.touches_real_repo_files=True`) - se `approval_required` del
manifest non e' AUTO, l'Orchestrator si ferma a WAITING_APPROVAL SENZA
scrivere il file reale, anche se il worker locale ha gia' prodotto e
verificato (in sandbox) una patch corretta."""
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR = os.path.dirname(CORE_DIR)
sys.path.insert(0, ORCH_DIR)

from core.task_queue import TaskQueue  # noqa: E402
from core.ledger import EventLedger  # noqa: E402
from core.router import route  # noqa: E402
from core import deterministic_worker  # noqa: E402
from core import ollama_worker  # noqa: E402
from core import retry_escalation  # noqa: E402
from core.context_packet import build_from_task_record  # noqa: E402
from core.result_packet import build_result_packet, compute_confidence, now_iso  # noqa: E402
from core import capability as capability_module  # noqa: E402


@dataclass
class VerifyResult:
    passed: bool
    parsed_output: Any = None
    errors: list = field(default_factory=list)
    is_logic_error: bool = False  # True se il worker ha risposto ma con un output SBAGLIATO
                                  # (non un crash/timeout) - usato dalla classificazione fallimenti


@dataclass
class ApplyResult:
    files_changed: list = field(default_factory=list)
    artifacts_created: list = field(default_factory=list)
    touches_real_repo_files: bool = False
    proposal_only: bool = False  # True se il cambiamento e' solo PROPOSTO (verificato in
                                # sandbox) ma non applicato al file reale - stato tipico di
                                # WAITING_APPROVAL


class LocalTaskHandler:
    """Interfaccia che ogni tipo concreto di task locale deve implementare."""

    def build_prompt(self, task_record) -> str:
        raise NotImplementedError

    def verify(self, task_record, response_text) -> VerifyResult:
        raise NotImplementedError

    def apply(self, task_record, verify_result: VerifyResult) -> ApplyResult:
        raise NotImplementedError


class Orchestrator:
    def __init__(self, queue_path=None, ledger_path=None):
        self.queue = TaskQueue(path=queue_path)
        self.ledger = EventLedger(path=ledger_path)
        self.local_handlers = {}  # action -> LocalTaskHandler
        self.local_bridge = None

    def register_local_handler(self, action, handler: LocalTaskHandler):
        self.local_handlers[action] = handler

    def set_local_bridge(self, bridge):
        """Attach an outbound-only executor transport; routing stays in Core."""
        self.local_bridge = bridge

    def submit(self, manifest, dependencies=None, action=None, action_params=None):
        record = self.queue.submit(manifest, dependencies=dependencies, action=action,
                                  action_params=action_params)
        self.ledger.append("TASK_CREATED", record["task_id"],
                          {"title": manifest["title"], "task_type": manifest["task_type"]})
        deps_ok = all(self.queue.get(d)["state"] == "COMPLETED" for d in (dependencies or []))
        new_state = "QUEUED" if deps_ok else "WAITING_DEPENDENCY"
        self.queue.transition(record["task_id"], new_state)
        self.ledger.append("TASK_QUEUED" if new_state == "QUEUED" else "TASK_BLOCKED",
                          record["task_id"], {"reason": "dependencies pending" if not deps_ok else ""})
        return record["task_id"]

    def submit_idempotent(self, manifest, *, idempotency_scope, idempotency_key,
                          dependencies=None, action=None, action_params=None):
        record, created = self.queue.submit_idempotent(
            manifest, idempotency_scope=idempotency_scope,
            idempotency_key=idempotency_key, dependencies=dependencies,
            action=action, action_params=action_params)
        if created:
            self.ledger.append("TASK_CREATED", record["task_id"],
                               {"title": manifest["title"], "task_type": manifest["task_type"]})
            event_type = "TASK_QUEUED" if record["state"] == "QUEUED" else "TASK_BLOCKED"
            self.ledger.append(event_type, record["task_id"], {
                "reason": "" if record["state"] == "QUEUED" else "dependencies pending"})
        return record["task_id"], created

    def process_task(self, task_id, claim_token=None):
        """Esegue UN ciclo completo (route -> execute -> verify -> retry/
        escalation -> result packet) per un singolo task. Ritorna il record
        aggiornato."""
        record = self.queue.get(task_id)
        if record.get("approval_effect") == "ACCEPT_ONLY":
            raise AssertionError(f"ACCEPT_ONLY non e' eseguibile: {task_id}")
        record = self.queue.try_promote(task_id)  # WAITING_DEPENDENCY -> QUEUED se ora pronto
        self.queue.assert_claim(task_id, claim_token)
        if record["state"] not in ("QUEUED",):
            raise AssertionError(f"process_task richiede stato QUEUED, trovato {record['state']}")

        manifest = record["manifest"]
        decision = route(record)
        self.queue.transition(task_id, "RUNNING", executor=decision.executor)
        # All execution/escalation builders must receive the canonical RUNNING
        # projection, never the stale QUEUED snapshot read before transition.
        record = self.queue.get(task_id)
        self.ledger.append("TASK_STARTED", task_id, {"tier": decision.tier,
                          "executor": decision.executor, "reason": decision.reason})

        if decision.tier == "TIER0_DETERMINISTIC":
            return self._run_deterministic(task_id, record, decision)
        if decision.tier in ("TIER1_LOCAL_CHEAP", "TIER2_LOCAL_STRONG"):
            return self._run_local(task_id, record, decision)
        # ESCALATION_REQUIRED diretta dal router (nessun tentativo locale possibile)
        return self._escalate(task_id, record, decision.executor, "ROUTER_DIRECT_ESCALATION", [])

    # ---- TIER 0 ------------------------------------------------------
    def _run_deterministic(self, task_id, record, decision):
        start = now_iso()
        action = record["action"]
        params = record["action_params"]
        self.ledger.append("TOOL_USED", task_id, {"tool": action, "params_keys": list(params)})
        result = deterministic_worker.execute(action, params)

        if result["files_read"]:
            self.ledger.append("FILE_READ", task_id, {"files": result["files_read"]})
        if result["files_changed"]:
            self.ledger.append("FILE_CHANGED", task_id, {"files": result["files_changed"]})

        if result["success"]:
            # Approval boundary (§14): un'azione deterministica che scrive un file REALE
            # del repository deve rispettare la stessa regola di un'azione locale - vale
            # per QUALUNQUE tier, non solo per Ministral. Gap trovato durante NEXUS TASK
            # #0003 (la prima azione TIER0 di questo Core a scrivere davvero un file reale)
            # e corretto qui, nel Core, non nel singolo task.
            touches_real_repo = bool(result["files_changed"])
            approval = record["manifest"]["approval_required"]
            if touches_real_repo and approval != "AUTO":
                self.ledger.append("APPROVAL_REQUIRED", task_id,
                                  {"reason": "azione deterministica ha modificato/proposto "
                                            f"modifiche a file reali - approval_required="
                                            f"{approval}, non AUTO", "files": result["files_changed"]})
                packet = build_result_packet(
                    task_id=task_id, executor="deterministic_worker", start_time=start,
                    end_time=now_iso(), files_read=result["files_read"], files_changed=[],
                    tools_or_commands=result["tools_or_commands"],
                    artifacts_created=result["files_changed"], tests_ran=True, tests_passed=1,
                    tests_failed=0, verifier_ran=True, verifier_passed=True, verifier_errors=[],
                    commit=None, push_status="NOT_APPLICABLE",
                    decision="PATCH_READY_AWAITING_APPROVAL", confidence="MEDIUM",
                    limitations=["modifica verificata ma non applicata - in attesa di "
                               "approvazione"], unresolved_issues=[],
                    suggested_next_tasks=["approvare la modifica proposta"],
                    escalation_needed=False)
                self.queue.transition(task_id, "WAITING_APPROVAL", result_packet=packet,
                                     approval_effect="REQUEUE")
                return self.queue.get(task_id)

            self.ledger.append("TASK_COMPLETED", task_id, {"action": action})
            packet = build_result_packet(
                task_id=task_id, executor="deterministic_worker", start_time=start,
                end_time=now_iso(), files_read=result["files_read"],
                files_changed=result["files_changed"],
                tools_or_commands=result["tools_or_commands"], artifacts_created=[],
                tests_ran=(action == "run_pytest"),
                tests_passed=1 if (action == "run_pytest" and result["success"]) else 0,
                tests_failed=0, verifier_ran=True, verifier_passed=True, verifier_errors=[],
                commit=None, push_status="NOT_APPLICABLE", decision="COMPLETED",
                confidence="HIGH", limitations=[], unresolved_issues=[],
                suggested_next_tasks=[], escalation_needed=False)
            self.queue.transition(task_id, "COMPLETED", result_packet=packet)
            return self.queue.get(task_id)

        # FAIL -> classificazione (TOOLING/ENVIRONMENT tipicamente, per un'azione
        # deterministica un "fallimento di logica del modello" non si applica)
        classification = retry_escalation.classify_failure(result["errors"])
        self.ledger.append("TASK_FAILED", task_id, {"action": action, "errors": result["errors"],
                          "classification": classification})
        target = retry_escalation.decide_escalation_target(classification, record["manifest"])
        return self._escalate(task_id, record, target, classification, result["errors"])

    # ---- TIER 1/2 (locale via Ministral) ------------------------------
    def _run_local(self, task_id, record, decision, _attempt=1):
        handler = self.local_handlers.get(record["action"])
        if handler is None:
            self.ledger.append("TASK_FAILED", task_id,
                              {"reason": f"nessun LocalTaskHandler registrato per azione "
                                        f"'{record['action']}'"})
            return self._escalate(task_id, record, "MANUAL_REVIEW", "TOOLING",
                                 [f"handler mancante per {record['action']}"])

        # Floor and sector handlers stay on this process. The bridge stores
        # action_params and is only for the two mapped workstation actions.
        stays_here = bool(getattr(handler, "skip_model", False)
                          or getattr(handler, "require_inference_gateway", False))
        if self.local_bridge is not None and not stays_here:
            if self.local_bridge.dispatch(record, decision, handler):
                return self.queue.get(task_id)
            self.ledger.append("TASK_FAILED", task_id,
                              {"classification": "LOCAL_BRIDGE_OFFLINE",
                               "executor": decision.executor})
            target = retry_escalation.decide_escalation_target(
                "ENVIRONMENT", record["manifest"],
                already_tried_stronger_local=(decision.tier == "TIER2_LOCAL_STRONG"))
            return self._escalate(task_id, record, target, "LOCAL_BRIDGE_OFFLINE",
                                  ["authorized local bridge unavailable"])

        start = now_iso()
        if getattr(handler, "skip_model", False):
            produced = handler.deterministic_response(record)
            call = {"success": isinstance(produced, str) and bool(produced),
                    "model": "deterministic",
                    "response_text": produced if isinstance(produced, str) else "",
                    "wall_seconds": 0.0,
                    "error": None if isinstance(produced, str) and produced else "deterministic output missing"}
            tool_name = "deterministic"
        else:
            prompt = handler.build_prompt(record)
            call_kwargs = {"model": decision.agent["model_or_runtime"].split(" ")[0]}
            # Additive opt-in: legacy handlers and their test doubles retain the
            # exact two-argument call contract.
            if bool(getattr(handler, "json_mode", False)):
                call_kwargs["json_mode"] = True
            if getattr(handler, "model_timeout", None):
                call_kwargs["timeout"] = int(handler.model_timeout)
            use_gateway = (os.environ.get("NEXUS_ENV") == "LIVE"
                           and getattr(handler, "require_inference_gateway", False))
            if use_gateway:
                from jarvis_v1.inference_gateway_client import complete_json
                call = complete_json(prompt, timeout=call_kwargs.get("timeout", 20))
            else:
                call = ollama_worker.call_local_model(prompt, **call_kwargs)
            tool_name = "inference_gateway" if use_gateway else "ollama_local_model"
        self.ledger.append("TOOL_USED", task_id, {"tool": tool_name,
                          "model": call["model"], "wall_seconds": call.get("wall_seconds")})

        if not call["success"]:
            errors = [call["error"]]
            classification = retry_escalation.classify_failure(errors)
        else:
            vr = handler.verify(record, call["response_text"])
            if vr.passed:
                apply_result = handler.apply(record, vr)
                self.ledger.append("TEST_PASSED", task_id, {"handler": record["action"]})
                if apply_result.files_changed:
                    self.ledger.append("FILE_CHANGED", task_id,
                                      {"files": apply_result.files_changed})

                approval = record["manifest"]["approval_required"]
                accept_only = bool(apply_result.proposal_only) and not bool(apply_result.touches_real_repo_files)
                requeue_gate = bool(apply_result.touches_real_repo_files) and approval != "AUTO"
                if accept_only:
                    self.ledger.append("APPROVAL_REQUIRED", task_id,
                                      {"reason": "proposta interna senza modifica di file; "
                                                "approval_effect=ACCEPT_ONLY",
                                       "approval_effect": "ACCEPT_ONLY"})
                    packet = build_result_packet(
                        task_id=task_id, executor=decision.executor, start_time=start,
                        end_time=now_iso(), files_read=[], files_changed=[],
                        tools_or_commands=["ollama:" + call["model"]],
                        artifacts_created=apply_result.artifacts_created,
                        tests_ran=True, tests_passed=1, tests_failed=0, verifier_ran=True,
                        verifier_passed=True, verifier_errors=[], commit=None,
                        push_status="NOT_APPLICABLE", decision="PROPOSAL_AWAITING_APPROVAL",
                        confidence="MEDIUM",
                        limitations=["proposta interna persistita; nessuna patch e nessuna "
                                     "azione esterna"],
                        unresolved_issues=[],
                        suggested_next_tasks=["approvare o rifiutare la proposta senza eseguirla"],
                        escalation_needed=False)
                    self.queue.transition(task_id, "WAITING_APPROVAL", result_packet=packet,
                                         approval_effect="ACCEPT_ONLY")
                    if hasattr(handler, "record_committed_steps"):
                        handler.record_committed_steps(task_id)
                    return self.queue.get(task_id)
                if requeue_gate:
                    self.ledger.append("APPROVAL_REQUIRED", task_id,
                                      {"reason": "il worker locale ha prodotto/verificato una "
                                                "patch per un file reale del repository - "
                                                f"approval_required={approval}, non AUTO",
                                       "approval_effect": "REQUEUE"})
                    packet = build_result_packet(
                        task_id=task_id, executor=decision.executor, start_time=start,
                        end_time=now_iso(), files_read=[], files_changed=[],
                        tools_or_commands=["ollama:" + call["model"]],
                        artifacts_created=apply_result.artifacts_created,
                        tests_ran=True, tests_passed=1, tests_failed=0, verifier_ran=True,
                        verifier_passed=True, verifier_errors=[], commit=None,
                        push_status="NOT_APPLICABLE", decision="PATCH_READY_AWAITING_APPROVAL",
                        confidence="MEDIUM", limitations=["patch verificata solo in sandbox, "
                                                          "non applicata al file reale - "
                                                          "in attesa di approvazione"],
                        unresolved_issues=[], suggested_next_tasks=["approvare/applicare la "
                                                                   "patch proposta"],
                        escalation_needed=False)
                    # Kept on the record, not only referenced by path, so a
                    # later human REJECT can hand the real content to a
                    # specialist reviewer without re-deriving it (see
                    # core/context_packet.py:build_review_packet).
                    proposed_patch = {"changes": vr.parsed_output.get("changes", []),
                                     "test_results": vr.parsed_output.get("test_results", [])}
                    self.queue.transition(task_id, "WAITING_APPROVAL", result_packet=packet,
                                         proposed_patch=proposed_patch,
                                         approval_effect="REQUEUE")
                    return self.queue.get(task_id)

                self.ledger.append("TASK_COMPLETED", task_id, {"handler": record["action"]})
                confidence, signals = compute_confidence(
                    verifier_ran=True, verifier_passed=True, tests_ran=False, tests_passed=0,
                    tests_failed=0, expected_artifacts=record["manifest"]["expected_artifacts"],
                    artifacts_created=apply_result.artifacts_created, schema_valid=True,
                    provenance_ok=True, contradicts_canonical=False)
                packet = build_result_packet(
                    task_id=task_id, executor=decision.executor, start_time=start,
                    end_time=now_iso(), files_read=[], files_changed=apply_result.files_changed,
                    tools_or_commands=["ollama:" + call["model"]],
                    artifacts_created=apply_result.artifacts_created, tests_ran=False,
                    tests_passed=0, tests_failed=0, verifier_ran=True, verifier_passed=True,
                    verifier_errors=[], commit=None, push_status="NOT_APPLICABLE",
                    decision="COMPLETED", confidence=confidence, limitations=[],
                    unresolved_issues=[], suggested_next_tasks=[], escalation_needed=False)
                self.queue.transition(task_id, "COMPLETED", result_packet=packet)
                return self.queue.get(task_id)

            errors = vr.errors
            self.ledger.append("TEST_FAILED", task_id, {"handler": record["action"],
                              "errors": errors})
            classification = retry_escalation.classify_failure(
                errors, is_logic_error_not_crash=vr.is_logic_error)

        if getattr(handler, "fail_closed_without_premium", False):
            self.ledger.append("TASK_FAILED", task_id, {
                "classification": classification,
                "errors": [str(item)[:300] for item in errors]})
            self.queue.transition(task_id, "BLOCKED",
                                 dispatch_last_error=str(errors[0])[:500] if errors else classification)
            return self.queue.get(task_id)

        if (getattr(handler, "retry_on_stronger_local", False) and
                decision.tier == "TIER1_LOCAL_CHEAP"):
            self.ledger.append("RETRY_STARTED", task_id,
                              {"attempt": _attempt + 1,
                               "classification": classification,
                               "escalation": "LOCAL_FAST->LOCAL_STRONG"})
            self.queue.transition(task_id, "RUNNING", retry_count=_attempt)
            target = retry_escalation.decide_escalation_target(
                "LOCAL_MODEL_CAPABILITY", record["manifest"],
                already_tried_stronger_local=False)
            return self._escalate(task_id, self.queue.get(task_id), target,
                                  classification, errors)

        if (not getattr(handler, "retry_on_stronger_local", False) and
                _attempt <= retry_escalation.RETRY_MAX_ATTEMPTS):
            self.ledger.append("RETRY_STARTED", task_id, {"attempt": _attempt + 1,
                              "classification": classification})
            self.queue.transition(task_id, "RUNNING", retry_count=_attempt)
            return self._run_local(task_id, self.queue.get(task_id), decision, _attempt=_attempt + 1)

        self.ledger.append("TASK_FAILED", task_id, {"classification": classification})
        target = retry_escalation.decide_escalation_target(
            classification, record["manifest"],
            already_tried_stronger_local=(decision.tier == "TIER2_LOCAL_STRONG"))
        return self._escalate(task_id, record, target, classification, errors)

    def accept_local_bridge_result(self, task_id, *, executor, response_text,
                                   verification, bridge_id):
        """Validate a bounded client receipt and finalize it through the usual gate."""
        record = self.queue.get(task_id)
        if record["state"] != "WAITING_PROVIDER":
            raise AssertionError("local bridge result requires WAITING_PROVIDER")
        handler = self.local_handlers.get(record.get("action"))
        if handler is None:
            raise AssertionError("local bridge handler unavailable")
        if hasattr(handler, "verify_bridge_submission"):
            verified = handler.verify_bridge_submission(record, response_text, verification)
        else:
            if not isinstance(verification, dict) or verification.get("passed") is not True:
                raise AssertionError("local bridge verifier receipt rejected")
            verified = handler.verify(record, response_text)
        if not verified.passed:
            raise AssertionError("local bridge verifier receipt rejected: " +
                                 "; ".join(verified.errors))
        parsed = verified.parsed_output
        if not hasattr(handler, "verify_bridge_submission"):
            apply_result = handler.apply(record, verified)
            if apply_result.touches_real_repo_files:
                raise AssertionError("generic bridge result cannot mutate repository files")
            packet = build_result_packet(
                task_id=task_id, executor=executor,
                start_time=record.get("started_at") or now_iso(), end_time=now_iso(),
                files_read=[], files_changed=[],
                tools_or_commands=["local_agent_bridge_v1", "ollama:" +
                                   str(verification.get("model") or "local")],
                artifacts_created=apply_result.artifacts_created, tests_ran=True,
                tests_passed=1, tests_failed=0, verifier_ran=True, verifier_passed=True,
                verifier_errors=[], commit=None, push_status="NOT_APPLICABLE",
                decision="COMPLETED", confidence="MEDIUM", limitations=[],
                unresolved_issues=[], suggested_next_tasks=[], escalation_needed=False)
            self.ledger.append("TASK_COMPLETED", task_id,
                               {"handler": record["action"], "bridge_id": bridge_id})
            self.queue.transition(task_id, "COMPLETED", result_packet=packet,
                                  local_bridge={"status": "COMPLETED", "bridge_id": bridge_id,
                                                "verification": "PASSED"})
            return self.queue.get(task_id)
        tests = parsed.get("test_results") or []
        artifacts = [f"local-bridge://{bridge_id}/{task_id}"] + [
            item["path"] for item in parsed["changes"]]
        packet = build_result_packet(
            task_id=task_id, executor=executor, start_time=record.get("started_at") or now_iso(),
            end_time=now_iso(), files_read=[], files_changed=[],
            tools_or_commands=["local_agent_bridge_v1", "ollama:" +
                               str(verification.get("model") or "local")],
            artifacts_created=artifacts, tests_ran=bool(tests),
            tests_passed=sum(1 for item in tests if item.get("returncode") == 0),
            tests_failed=sum(1 for item in tests if item.get("returncode") != 0),
            verifier_ran=True, verifier_passed=True, verifier_errors=[], commit=None,
            push_status="NOT_PUSHED", decision="PATCH_READY_AWAITING_APPROVAL",
            confidence="MEDIUM", limitations=["patch verified in isolated local bridge workspace; "
                                               "not applied to canonical repository"],
            unresolved_issues=[], suggested_next_tasks=["review and approve the proposed patch"],
            escalation_needed=False)
        self.ledger.append("APPROVAL_REQUIRED", task_id,
                           {"reason": "local bridge produced a bounded verified repository patch",
                            "bridge_id": bridge_id})
        # Kept on the record, not only referenced by the local-bridge:// path,
        # so a later human REJECT can hand the real content to a specialist
        # reviewer (see core/context_packet.py:build_review_packet).
        proposed_patch = {"changes": parsed.get("changes", []), "test_results": tests}
        self.queue.transition(task_id, "WAITING_APPROVAL", result_packet=packet,
                              local_bridge={"status": "COMPLETED", "bridge_id": bridge_id,
                                            "verification": "PASSED"},
                              proposed_patch=proposed_patch,
                              approval_effect="REQUEUE")
        return self.queue.get(task_id)

    def fail_local_bridge_task(self, task_id, failure_class):
        record = self.queue.get(task_id)
        if record["state"] != "WAITING_PROVIDER":
            return record
        packet = build_result_packet(
            task_id=task_id, executor=record.get("executor") or "local_agent_bridge_v1",
            start_time=record.get("started_at") or now_iso(), end_time=now_iso(),
            files_read=[], files_changed=[], tools_or_commands=["local_agent_bridge_v1"],
            artifacts_created=[], tests_ran=False, tests_passed=0, tests_failed=0,
            verifier_ran=False, verifier_passed=False, verifier_errors=[failure_class],
            commit=None, push_status="NOT_APPLICABLE", decision="ESCALATION_REQUIRED",
            confidence="UNKNOWN", limitations=["local bridge exhausted its bounded retry"],
            unresolved_issues=[failure_class], suggested_next_tasks=["manual review"],
            escalation_needed=True, escalation_reason=failure_class,
            escalation_target_tier="MANUAL_REVIEW")
        self.queue.transition(task_id, "ESCALATION_REQUIRED", result_packet=packet,
                              escalation={"target": "MANUAL_REVIEW",
                                          "classification": failure_class},
                              dispatch_last_error=failure_class)
        self.ledger.append("ESCALATION_REQUIRED", task_id,
                           {"target": "MANUAL_REVIEW", "classification": failure_class})
        return self.queue.get(task_id)

    ORPHANED_RUNNING_AFTER_RESTART = "ORPHANED_RUNNING_AFTER_RESTART"

    def resume_orphaned_task(self, task_id, *, requested_by=None):
        """SAFE_ORPHANED_TASK_RESUME_V1: an explicit, auditable, human-
        triggered resume for a task recover_orphaned_running() fail-closed
        parked into BLOCKED after a process restart - never an automatic
        global resume at boot (that stays exactly as conservative as before),
        and never a free-form write into the queue store. Every precondition
        below must hold or this fails closed with no state change at all -
        same discipline as every other guard in this module (AssertionError,
        no silent partial effect)."""
        record = self.queue.get(task_id)
        if record["state"] != "BLOCKED":
            raise AssertionError(f"resume requires BLOCKED, got {record['state']}")
        recovery = record.get("recovery") or {}
        if recovery.get("classification") != self.ORPHANED_RUNNING_AFTER_RESTART:
            raise AssertionError("resume only applies to ORPHANED_RUNNING_AFTER_RESTART, "
                                 f"got {recovery.get('classification')!r}")
        if record.get("dispatch_claim"):
            raise AssertionError("resume refused: an active dispatch claim still exists")
        if self.local_bridge is not None:
            job_status = self.local_bridge.job_status(task_id)
            if job_status in self.local_bridge.ACTIVE_JOB_STATES:
                raise AssertionError(f"resume refused: bridge job is still {job_status}")
        if self._workflow_steps_without_packet(record):
            raise AssertionError(
                "resume refused: workflow steps are recorded without a durable approval packet")
        self.ledger.append("TASK_RECOVERY_REQUESTED", task_id,
            {"previous_cause": recovery.get("classification"),
             "previous_recovered_at": recovery.get("recovered_at"),
             "requested_by": requested_by or "unknown"}, actor="orphan_recovery_v1")
        # Only the operational fields that caused BLOCKED are cleared - retry
        # count, escalation, proposed_patch, action_params (rework
        # instructions included) and every other lineage field are untouched.
        # The Ledger already holds TASK_ORPHANED/TASK_BLOCKED forever
        # (append-only) - clearing `recovery` here loses nothing, it only
        # stops a resolved cause from looking like a live one.
        # A crash before approval_effect and the result packet are persisted
        # is not exactly-once. The record still looks like an ordinary RUNNING
        # task, so this explicit resume returns it to QUEUED. Once both fields
        # are stored, resume restores WAITING_APPROVAL and the dispatcher
        # cannot claim the task.
        if record.get("approval_effect") == "ACCEPT_ONLY" and record.get("result_packet"):
            self.queue.transition(task_id, "WAITING_APPROVAL", dispatch_last_error=None, recovery=None)
            self.ledger.append("TASK_RESUMED", task_id,
                {"previous_cause": self.ORPHANED_RUNNING_AFTER_RESTART,
                 "requested_by": requested_by or "unknown",
                 "restored_state": "WAITING_APPROVAL",
                 "approval_effect": "ACCEPT_ONLY"}, actor="orphan_recovery_v1")
            return self.queue.get(task_id)
        self.queue.transition(task_id, "QUEUED", dispatch_last_error=None, recovery=None)
        self.ledger.append("TASK_RESUMED", task_id,
            {"previous_cause": self.ORPHANED_RUNNING_AFTER_RESTART,
             "requested_by": requested_by or "unknown"}, actor="orphan_recovery_v1")
        # Deliberately NOT executing the handler/bridge directly here - the
        # task goes back through QUEUED exactly like any other task, so the
        # normal DurableQueueDispatcher claims and routes it (same Router,
        # same policy, same dispatch() idempotency guard already covered by
        # LOCAL_BRIDGE_REWORK_REDISPATCH_FIX_V1).
        return self.queue.get(task_id)

    def _workflow_steps_without_packet(self, record):
        """Steps written before the approval packet must not be run again."""
        if record.get("approval_effect") == "ACCEPT_ONLY" and record.get("result_packet"):
            return False
        task_id = record["task_id"]
        for event in self.ledger.read_for_task(task_id):
            payload = event.get("payload") or {}
            if (event.get("event_type") in {"STEP_COMPLETED", "TASK_WAITING_APPROVAL"}
                    and str(payload.get("workflow_id") or "").startswith("jarvis.")):
                return True
        return False

    # ---- Escalation ----------------------------------------------------
    def _escalate(self, task_id, record, target, classification, errors):
        current = self.queue.get(task_id)
        if current["state"] == "ESCALATION_REQUIRED":
            return current
        record = current
        if target == "TIER2_LOCAL_STRONG_RETRY":
            strong_agent = next(a for a in capability_module.load_registry()["agents"]
                               if a["agent_id"] == "LOCAL_STRONG_MINISTRAL3B")
            from core.router import RouteDecision
            decision = RouteDecision("TIER2_LOCAL_STRONG", executor=strong_agent["agent_id"],
                                    agent=strong_agent, reason="escalation locale FAST->STRONG")
            self.queue.transition(task_id, "RUNNING", executor=strong_agent["agent_id"])
            self.ledger.append("RETRY_STARTED", task_id, {"escalation": "LOCAL_FAST->LOCAL_STRONG"})
            return self._run_local(task_id, self.queue.get(task_id), decision, _attempt=1)

        if target == "APPROVAL_REQUIRED":
            self.ledger.append("APPROVAL_REQUIRED", task_id, {"classification": classification})
            self.queue.transition(task_id, "WAITING_APPROVAL")
            return self.queue.get(task_id)

        self.ledger.append("ESCALATION_REQUIRED", task_id, {"target": target,
                          "classification": classification, "errors": [str(e) for e in errors]})
        context_packet = build_from_task_record(record, [{"executor": record.get("executor"),
                                                          "errors": errors,
                                                          "summary": classification}],
                                                classification, target)
        packet = build_result_packet(
            task_id=task_id, executor=record.get("executor") or "unknown", start_time=now_iso(),
            end_time=now_iso(), files_read=[], files_changed=[], tools_or_commands=[],
            artifacts_created=[], tests_ran=False, tests_passed=0, tests_failed=0,
            verifier_ran=False, verifier_passed=False, verifier_errors=[str(e) for e in errors],
            commit=None, push_status="NOT_APPLICABLE", decision="ESCALATION_REQUIRED",
            confidence="UNKNOWN", limitations=[], unresolved_issues=[str(e) for e in errors],
            suggested_next_tasks=[f"assegnare a {target}"], escalation_needed=True,
            escalation_reason=classification, escalation_target_tier=target)
        self.queue.transition(task_id, "ESCALATION_REQUIRED", result_packet=packet,
                             escalation={"target": target, "classification": classification,
                                       "context_packet": context_packet})
        return self.queue.get(task_id)
