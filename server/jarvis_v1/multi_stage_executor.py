"""Durable sequential executor over the existing Orchestrator and Queue.

The coordinator creates ordinary child TASK_MANIFEST_V1 records.  It never
calls a model/tool directly and never selects a provider: each child is routed
and verified by the canonical Orchestrator.  Parent progress is persisted in
TaskQueue annotations, so a process restart can resume by polling child state.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone

from core.result_packet import build_result_packet
from core.task_queue import new_task_id
from . import ministral_task_compiler
from .local_operations import build_execution_plan


def _now():
    return datetime.now(timezone.utc).isoformat()


class MultiStageExecutor:
    ACTION = "multi_stage_operations_v1"
    ACTIVE_PARENT_STATES = {"WAITING_PROVIDER", "RUNNING"}

    def __init__(self, orchestrator, *, capability_resolver=None, notification_sink=None,
                 interval_seconds=2):
        self.orchestrator = orchestrator
        self.queue = orchestrator.queue
        self.ledger = orchestrator.ledger
        self.capability_resolver = capability_resolver
        self.notification_sink = notification_sink or (lambda event: None)
        self.interval_seconds = max(.2, float(interval_seconds))
        self._stop = threading.Event()
        self._thread = None
        self.last_error_class = None
        self.last_tick_at = None

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())

    def start(self):
        if self.running:
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="nexus-multi-stage", daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout_seconds=10):
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout_seconds)
        return not self.running

    def status(self):
        return {"running": self.running, "last_tick_at": self.last_tick_at,
                "last_error_class": self.last_error_class,
                "interval_seconds": self.interval_seconds}

    def submit(self, *, objective, created_by, conversation_id, relevant_paths=None,
               priority_class="P1_USER_TASK", premium_allowed=False):
        priority_map = {"P0_JARVIS_INTERACTIVE": "URGENT", "P1_USER_TASK": "HIGH",
                        "P2_TRADING_REVENUE_BACKGROUND": "NORMAL", "P3_RESEARCH": "LOW",
                        "P4_MAINTENANCE": "LOW"}
        task_id = new_task_id()
        manifest = {
            "task_id": task_id, "title": objective[:120], "objective": objective,
            "task_type": "MAINTENANCE", "work_type": "routine_summary",
            "priority": priority_map.get(priority_class, "NORMAL"), "risk_level": "A1",
            "scientific_risk": "NONE", "code_risk": "NONE", "financial_risk": "NONE",
            "required_capabilities": ["summaries", "artifact_field_extraction"],
            "deterministic_tools_available": False, "repo_scope": "read-only operations",
            "files_allowed": list(relevant_paths or []),
            "files_forbidden": [".env", "**/.env", "**/*secret*", "MQL5/**"],
            "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
            "success_criteria": ["every required step is independently verified"],
            "verifier": "multi_stage_final_verifier_v1", "estimated_complexity": "MEDIUM",
            "estimated_runtime": "durable", "premium_allowed": bool(premium_allowed),
            "preferred_executor": "TIER1_LOCAL_CHEAP",
            "fallback_executors": (["TIER2_LOCAL_STRONG", "TIER3_CLAUDE"]
                                   if premium_allowed else ["TIER2_LOCAL_STRONG"]),
            "approval_required": "REVIEW_REQUIRED", "created_by": created_by,
            "created_at": _now(), "tenant_id": "tenant-1", "account_scope_id": None,
        }
        plan = build_execution_plan(
            objective, authorized_capabilities=manifest["required_capabilities"],
            resolver=self.capability_resolver)
        self.orchestrator.submit(
            manifest, action=self.ACTION,
            action_params={"conversation_id": conversation_id, "priority_class": priority_class,
                           "relevant_paths": list(relevant_paths or [])})
        # Remove the parent from the normal Dispatcher before its next poll;
        # only children are executable work items.
        self.queue.transition(task_id, "RUNNING", executor="MULTI_STAGE_COORDINATOR")
        self.queue.transition(task_id, "WAITING_PROVIDER", multi_stage_execution=plan)
        self.ledger.append("TASK_STARTED", task_id,
                           {"mode": "MULTI_STAGE", "priority_class": priority_class},
                           actor="multi_stage_executor_v1")
        self.notification_sink({"event_type": "TASK_STARTED", "task_id": task_id,
                                "status": "RUNNING", "summary": f"{task_id} avviata."})
        return task_id

    def run_once(self):
        processed = []
        for parent in self.queue.list_all():
            if parent.get("action") != self.ACTION or parent.get("state") not in self.ACTIVE_PARENT_STATES:
                continue
            self._advance(parent["task_id"])
            processed.append(parent["task_id"])
        self.last_tick_at = _now()
        self.last_error_class = None
        return processed

    def _advance(self, task_id):
        parent = self.queue.get(task_id)
        plan = parent.get("multi_stage_execution") or {}
        created = datetime.fromisoformat(parent["created_at"])
        if (datetime.now(timezone.utc) - created).total_seconds() > int(
                plan.get("task_total_budget_seconds", 900)):
            return self._block_parent(parent, plan, "TASK_TOTAL_BUDGET_EXCEEDED")
        steps = plan.get("steps") or []
        current = next((s for s in steps if s["state"] not in {"VERIFIED", "COMPLETED"}), None)
        if current is None:
            return self._complete_parent(parent, plan)
        if current.get("authorization_result") != "AUTHORIZED":
            current["state"] = "BLOCKED"
            return self._block_parent(parent, plan, "CAPABILITY_NOT_AUTHORIZED")

        child_id = current.get("child_task_id")
        if not child_id:
            return self._submit_step(parent, plan, current)
        child = self.queue.get(child_id)
        state = child["state"]
        if state == "COMPLETED":
            packet = child.get("result_packet") or {}
            if not (packet.get("verifier") or {}).get("passed"):
                current["state"] = "FAILED"
                return self._block_parent(parent, plan, "CHILD_COMPLETED_WITHOUT_VERIFIER")
            current["state"] = "VERIFIED"
            current["result_packet"] = packet
            current["completed_at"] = _now()
            self.queue.annotate(parent["task_id"], multi_stage_execution=plan)
            self.ledger.append("STEP_COMPLETED", parent["task_id"],
                               {"step_id": current["step_id"], "child_task_id": child_id,
                                "verifier": current.get("verifier")},
                               actor="multi_stage_executor_v1")
            return self._advance(parent["task_id"])
        if state == "WAITING_APPROVAL":
            current["state"] = "WAITING_APPROVAL"
            self.queue.annotate(parent["task_id"], multi_stage_execution=plan)
            return self._wait_parent(parent, "WAITING_APPROVAL", "TASK_WAITING_APPROVAL")
        if state == "WAITING_PROVIDER" and not child.get("escalation"):
            # Normal Local Agent Bridge lease/execution, not a premium wait.
            return None
        if state in {"ESCALATION_REQUIRED", "WAITING_PROVIDER", "WAITING_REVIEW_PROVIDER"}:
            current["state"] = "WAITING_FOR_PREMIUM"
            self.queue.annotate(parent["task_id"], multi_stage_execution=plan)
            return self._wait_parent(parent, "WAITING_FOR_PREMIUM", "TASK_ESCALATED")
        if state in {"FAILED", "BLOCKED", "CANCELLED"}:
            current["state"] = "FAILED" if state == "FAILED" else "BLOCKED"
            return self._block_parent(parent, plan, f"CHILD_{state}")

    def _submit_step(self, parent, plan, step):
        prior = [s.get("result_packet") for s in plan["steps"] if s.get("result_packet")]
        context_note = (" Prior verified steps: " + str(len(prior))) if prior else ""
        manifest, action, params = ministral_task_compiler.compile_task(
            "repo_inspection_v1",
            goal=f"{parent['manifest']['objective']}\nCurrent required capability: "
                 f"{step['required_capability']}.{context_note}",
            relevant_paths=(parent.get("action_params") or {}).get("relevant_paths", []),
            created_by=f"multi_stage:{parent['task_id']}",
            conversation_id=(parent.get("action_params") or {}).get("conversation_id"))
        manifest["priority"] = parent["manifest"]["priority"]
        manifest["required_capabilities"] = sorted(set(
            manifest["required_capabilities"] + [step["required_capability"]]))
        manifest["premium_allowed"] = parent["manifest"]["premium_allowed"]
        manifest["fallback_executors"] = parent["manifest"]["fallback_executors"]
        params.update({"parent_task_id": parent["task_id"], "step_id": step["step_id"]})
        self.orchestrator.submit(manifest, action=action, action_params=params)
        step.update({"state": "RUNNING", "child_task_id": manifest["task_id"],
                     "started_at": _now()})
        plan["current_step"] = step["step_id"]
        self.queue.annotate(parent["task_id"], multi_stage_execution=plan)
        self.ledger.append("TASK_CREATED", manifest["task_id"],
                           {"parent_task_id": parent["task_id"], "step_id": step["step_id"]},
                           actor="multi_stage_executor_v1")

    def _complete_parent(self, parent, plan):
        if not plan.get("steps") or any(s.get("state") != "VERIFIED" for s in plan["steps"]):
            return self._block_parent(parent, plan, "FINAL_VERIFIER_INCOMPLETE_STEPS")
        artifacts = [f"task://{s['child_task_id']}" for s in plan["steps"]]
        packet = build_result_packet(
            task_id=parent["task_id"], executor="MULTI_STAGE_COORDINATOR",
            start_time=parent.get("started_at") or parent["created_at"], end_time=_now(),
            files_read=[], files_changed=[], tools_or_commands=["orchestrator_child_tasks"],
            artifacts_created=artifacts, tests_ran=True, tests_passed=len(plan["steps"]),
            tests_failed=0, verifier_ran=True, verifier_passed=True, verifier_errors=[],
            commit=None, push_status="NOT_APPLICABLE", decision="COMPLETED",
            confidence="MEDIUM", limitations=["read-only bounded multi-stage execution"],
            unresolved_issues=[], suggested_next_tasks=[], escalation_needed=False)
        plan["current_step"] = None
        self.queue.transition(parent["task_id"], "COMPLETED", result_packet=packet,
                              multi_stage_execution=plan)
        self.ledger.append("TASK_COMPLETED", parent["task_id"],
                           {"verified_steps": len(plan["steps"])}, actor="multi_stage_executor_v1")
        self.notification_sink({"event_type": "TASK_COMPLETED", "task_id": parent["task_id"],
                                "status": "COMPLETED",
                                "summary": f"{parent['task_id']} completata: {len(plan['steps'])} step verificati."})

    def _wait_parent(self, parent, step_state, event_type):
        self.ledger.append(event_type, parent["task_id"], {"step_state": step_state},
                           actor="multi_stage_executor_v1")
        self.notification_sink({"event_type": event_type, "task_id": parent["task_id"],
                                "status": step_state, "summary": f"{parent['task_id']}: {step_state}."})

    def _block_parent(self, parent, plan, reason):
        self.queue.transition(parent["task_id"], "BLOCKED", multi_stage_execution=plan,
                              dispatch_last_error=reason,
                              recovery={"classification": reason, "recovered_at": None})
        self.ledger.append("TASK_FAILED", parent["task_id"], {"classification": reason},
                           actor="multi_stage_executor_v1")
        self.notification_sink({"event_type": "TASK_FAILED", "task_id": parent["task_id"],
                                "status": "BLOCKED", "summary": f"{parent['task_id']} bloccata: {reason}."})

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception as exc:
                self.last_error_class = type(exc).__name__
            self._stop.wait(self.interval_seconds)
