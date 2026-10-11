"""APPROVAL_REQUIRED research actions -> ACCEPT_ONLY proposals in the existing orchestrator queue.

No second approval system: the request becomes a TASK_MANIFEST_V1 in
orchestrator_v1's TaskQueue, created directly in WAITING_APPROVAL with
approval_effect=ACCEPT_ONLY. The existing Jarvis path decides it
(PROPOSAL_ACCEPTED / PROPOSAL_REJECTED); the dispatcher never claims an
ACCEPT_ONLY task and the orchestrator refuses to execute one. Approval only
records consent: the experiment itself is still run by a person on the
research machine and comes back through ingestion.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.abspath(os.path.join(HERE, "..", "..", "orchestrator_v1"))
if ORCH not in sys.path:
    sys.path.insert(0, ORCH)

from core.ledger import EventLedger  # noqa: E402
from core.result_packet import build_result_packet, now_iso  # noqa: E402
from core.task_queue import TaskQueue  # noqa: E402

SCOPE = "research_loop_v1"
DECIDED = {"PROPOSAL_ACCEPTED": "APPROVED", "PROPOSAL_REJECTED": "REJECTED", "CANCELLED": "REJECTED"}


class ApprovalBridge:
    def __init__(self, queue_path=None, ledger_path=None, tenant_id=None):
        self.queue = TaskQueue(queue_path)
        self.ledger = EventLedger(ledger_path)
        self.tenant_id = tenant_id

    def _manifest(self, task_id, action):
        from nexus_tenant import canonical_tenant_id
        return {
            "task_id": task_id, "title": f"Research loop approval: {action['kind']}",
            "objective": action["objective"], "task_type": "RESEARCH", "work_type": "scientific_research",
            "priority": "NORMAL", "risk_level": "A2", "scientific_risk": "MEDIUM", "code_risk": "NONE",
            "financial_risk": "NONE", "required_capabilities": ["scientific_review"],
            "deterministic_tools_available": True, "repo_scope": "server/research_scripts/",
            "files_allowed": [], "files_forbidden": ["MQL5/*", "server/research_scripts/research_intelligence_v1/*"],
            "dependencies": [], "blockers": [], "expected_artifacts": ["human decision"],
            "success_criteria": ["a person approves or rejects; nothing is executed by the queue"],
            "verifier": "research_intelligence_v1.loop", "estimated_complexity": "SMALL",
            "estimated_runtime": "n/a", "premium_allowed": False, "preferred_executor": "TIER0_DETERMINISTIC",
            "fallback_executors": [], "approval_required": "EXPLICIT_USER_APPROVAL",
            "created_by": "research-director-rules", "created_at": now_iso(),
            "tenant_id": self.tenant_id or canonical_tenant_id(), "account_scope_id": None,
        }

    def request(self, action_record_id, action):
        """Idempotent on action_record_id: a retry or a resumed cycle returns the same task."""
        task_id = "TASK_RI_" + action["params_sha256"][:16].upper()
        packet = build_result_packet(
            task_id=task_id, executor="TIER0_DETERMINISTIC", start_time=now_iso(), end_time=now_iso(),
            files_read=[], files_changed=[], tools_or_commands=["research_intelligence_v1.loop"],
            artifacts_created=[action_record_id], tests_ran=False, tests_passed=0, tests_failed=0,
            verifier_ran=False, verifier_passed=False, verifier_errors=[], commit=None,
            push_status="NOT_APPLICABLE", decision="PROPOSAL_AWAITING_APPROVAL", confidence="UNKNOWN",
            limitations=["approval records consent only; execution stays manual"] + action["reasons"],
            unresolved_issues=[], suggested_next_tasks=["approve or reject"], escalation_needed=False)
        record, created = self.queue.submit_accept_only_proposal(
            self._manifest(task_id, action), idempotency_scope=SCOPE, idempotency_key=action_record_id,
            result_packet=packet, action_params={"kind": action["kind"], "params_sha256": action["params_sha256"]})
        if created:
            self.ledger.append("APPROVAL_REQUIRED", record["task_id"],
                               {"reason": action["objective"], "approval_effect": "ACCEPT_ONLY",
                                "research_action": action_record_id}, actor="research_loop_v1")
        return record["task_id"], created

    def status(self, task_id):
        try:
            state = self.queue.get(task_id)["state"]
        except KeyError:
            return "MISSING"
        return DECIDED.get(state, "WAITING")
