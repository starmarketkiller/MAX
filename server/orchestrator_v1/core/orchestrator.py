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

    def register_local_handler(self, action, handler: LocalTaskHandler):
        self.local_handlers[action] = handler

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

    def process_task(self, task_id):
        """Esegue UN ciclo completo (route -> execute -> verify -> retry/
        escalation -> result packet) per un singolo task. Ritorna il record
        aggiornato."""
        record = self.queue.get(task_id)
        if record["state"] not in ("QUEUED",):
            raise AssertionError(f"process_task richiede stato QUEUED, trovato {record['state']}")

        manifest = record["manifest"]
        decision = route(record)
        self.queue.transition(task_id, "RUNNING", executor=decision.executor)
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

        start = now_iso()
        prompt = handler.build_prompt(record)
        call = ollama_worker.call_local_model(prompt, model=decision.agent["model_or_runtime"]
                                             .split(" ")[0])
        self.ledger.append("TOOL_USED", task_id, {"tool": "ollama_local_model",
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
                if apply_result.touches_real_repo_files and approval != "AUTO":
                    self.ledger.append("APPROVAL_REQUIRED", task_id,
                                      {"reason": "il worker locale ha prodotto/verificato una "
                                                "patch per un file reale del repository - "
                                                f"approval_required={approval}, non AUTO"})
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
                    self.queue.transition(task_id, "WAITING_APPROVAL", result_packet=packet)
                    return self.queue.get(task_id)

                self.ledger.append("TASK_COMPLETED", task_id, {"handler": record["action"]})
                confidence, signals = compute_confidence(
                    verifier_ran=True, verifier_passed=True, tests_ran=True, tests_passed=1,
                    tests_failed=0, expected_artifacts=record["manifest"]["expected_artifacts"],
                    artifacts_created=apply_result.artifacts_created, schema_valid=True,
                    provenance_ok=True, contradicts_canonical=False)
                packet = build_result_packet(
                    task_id=task_id, executor=decision.executor, start_time=start,
                    end_time=now_iso(), files_read=[], files_changed=apply_result.files_changed,
                    tools_or_commands=["ollama:" + call["model"]],
                    artifacts_created=apply_result.artifacts_created, tests_ran=True,
                    tests_passed=1, tests_failed=0, verifier_ran=True, verifier_passed=True,
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

        if _attempt <= retry_escalation.RETRY_MAX_ATTEMPTS:
            self.ledger.append("RETRY_STARTED", task_id, {"attempt": _attempt + 1,
                              "classification": classification})
            self.queue.transition(task_id, "RUNNING", retry_count=_attempt)
            return self._run_local(task_id, self.queue.get(task_id), decision, _attempt=_attempt + 1)

        self.ledger.append("TASK_FAILED", task_id, {"classification": classification})
        target = retry_escalation.decide_escalation_target(
            classification, record["manifest"],
            already_tried_stronger_local=(decision.tier == "TIER2_LOCAL_STRONG"))
        return self._escalate(task_id, record, target, classification, errors)

    # ---- Escalation ----------------------------------------------------
    def _escalate(self, task_id, record, target, classification, errors):
        if target == "TIER2_LOCAL_STRONG_RETRY":
            strong_agent = next(a for a in capability_module.load_registry()["agents"]
                               if a["agent_id"] == "LOCAL_STRONG_MINISTRAL3B")
            from core.router import RouteDecision
            decision = RouteDecision("TIER2_LOCAL_STRONG", executor=strong_agent["agent_id"],
                                    agent=strong_agent, reason="escalation locale FAST->STRONG")
            self.ledger.append("RETRY_STARTED", task_id, {"escalation": "LOCAL_FAST->LOCAL_STRONG"})
            return self._run_local(task_id, record, decision, _attempt=1)

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
