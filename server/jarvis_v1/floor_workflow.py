"""First real Jarvis to Agency handoff on the existing queue.

The simulated pipeline stays the specification. This module executes only
the stations that have a real deterministic step or an existing Agency
skill. Stations without that evidence are listed as not run and are never
written as completed steps.

One task, the existing dispatcher, no second queue. The handler returns
proposal_only so the orchestrator stops at WAITING_APPROVAL. Approving
that task does not run it again. Nothing here publishes, spends, trades,
or deploys.

A crash before the result packet is stored is not exactly-once: the task
still looks like ordinary running work.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from business_units.ai_fashion_agency.skills import verify_agency_output
from jarvis_v1.ministral_task_compiler import encode_bounded_output
from jarvis_v1.authenticated_scope import canonical_tenant_id

WORKFLOW_ID = "jarvis.fashion.handoff.v1"
ACTION = "nexus_fashion_handoff_workflow"
INTENT = "FASHION_INTERNAL_HANDOFF"

SKILL_STATIONS = (
    ("fashion.trend", "trend", "VIRAL_FORMAT_ANALYSIS"),
    ("fashion.discover", "discover", "PRODUCT_OPPORTUNITY_SCOUT"),
    ("fashion.plan", "brief", "CONTENT_BRIEF_DRAFT"),
)
NOT_RUN = (
    "fashion.model", "fashion.style", "fashion.campaign", "fashion.asset",
    "fashion.quality", "fashion.comply", "fashion.pack",
    "jarvis.result", "jarvis.response",
)
_STEP_KEYS = ("step_id", "station_id", "state", "output_ref", "provenance", "workflow_id")


def _now():
    return datetime.now(timezone.utc).isoformat()


class FloorWorkflowHandler:
    json_mode = True
    # A bad or missing model must end locally. It must not escalate to a paid provider.
    fail_closed_without_premium = True
    require_inference_gateway = True
    # Shorter than the dispatcher shutdown (25s) so a deploy does not kill a live call.
    model_timeout = 20

    def __init__(self, ledger):
        self.ledger = ledger

    def build_prompt(self, record):
        params = record["action_params"]
        context = params.get("context") if isinstance(params.get("context"), dict) else {}
        shapes = {}
        from business_units.ai_fashion_agency.skills import AGENCY_SKILLS
        for _station, _step, task_type in SKILL_STATIONS:
            shapes[task_type] = AGENCY_SKILLS[task_type].output_example
        return (
            "Return one JSON object with exactly these three keys and no prose. "
            "Use only evidence_id values present in CONTEXT. Do not invent prices, "
            "publish, spend, or contact anyone.\n"
            + json.dumps(shapes, ensure_ascii=False)
            + "\nCONTEXT: " + json.dumps(context, ensure_ascii=False, sort_keys=True)
        )

    def verify(self, record, response_text):
        from orchestrator_v1.core.orchestrator import VerifyResult
        try:
            parsed = json.loads(response_text)
        except (TypeError, ValueError):
            parsed = None
        if not isinstance(parsed, dict):
            return VerifyResult(passed=False, errors=["json object required"], is_logic_error=True)
        context = record["action_params"].get("context")
        if not isinstance(context, dict):
            return VerifyResult(passed=False, errors=["context required"], is_logic_error=True)
        outputs = {}
        errors = []
        for _station, _step, task_type in SKILL_STATIONS:
            ok, skill_errors = verify_agency_output(task_type, parsed.get(task_type), context)
            if not ok:
                errors.extend(f"{task_type}: {item}" for item in skill_errors)
            else:
                outputs[task_type] = parsed[task_type]
        title = str((outputs.get("PRODUCT_OPPORTUNITY_SCOUT") or {}).get("title") or "").strip()
        if "PRODUCT_OPPORTUNITY_SCOUT" in outputs and not title:
            errors.append("scout title is empty")
        if not errors and not self._cited_ids_are_sourced(outputs, context):
            errors.append("evidence source required")
        if errors:
            return VerifyResult(passed=False, errors=errors, is_logic_error=True)
        return VerifyResult(passed=True, parsed_output=outputs)

    @staticmethod
    def _cited_ids_are_sourced(outputs, context):
        """An id minted from the user's own note is not a source."""
        sourced = set()
        for item in context.get("evidence_records") or []:
            if not isinstance(item, dict):
                continue
            evidence_id = str(item.get("evidence_id") or "")
            source = str(item.get("source") or item.get("source_url") or "").strip()
            note = str(item.get("note") or item.get("text") or "").strip()
            if evidence_id and source and source != note and not evidence_id.startswith("USER_CONTEXT"):
                sourced.add(evidence_id)
        cited = []
        for output in outputs.values():
            refs = output.get("evidence") if "evidence" in output else output.get("trend_evidence")
            if isinstance(refs, list):
                cited.extend(refs)
        return bool(cited) and set(cited).issubset(sourced)

    def apply(self, record, verify_result):
        from orchestrator_v1.core.orchestrator import ApplyResult
        task_id = record["task_id"]
        outputs = verify_result.parsed_output
        artifacts = [encode_bounded_output(task_type, task_id, outputs[task_type])
                     for _station, _step, task_type in SKILL_STATIONS]
        artifacts.append(f"handoff:{task_id}")
        # Steps are written only after the queue stores WAITING_APPROVAL.
        return ApplyResult(artifacts_created=artifacts, touches_real_repo_files=False,
                           proposal_only=True)

    def record_committed_steps(self, task_id):
        ordered = [
            ("jarvis.intake", "intake", f"task:{task_id}", "DETERMINISTIC", "STEP_COMPLETED", "RECORDED"),
            ("jarvis.intent", "intent", f"intent:{INTENT}", "DETERMINISTIC", "STEP_COMPLETED", "RECORDED"),
            ("jarvis.plan", "plan", "plan:three-skills", "DETERMINISTIC", "STEP_COMPLETED", "RECORDED"),
            ("jarvis.orch", "orch", "queue:durable", "DETERMINISTIC", "STEP_COMPLETED", "RECORDED"),
            ("fashion.trend", "trend", "skill:VIRAL_FORMAT_ANALYSIS", "AGENCY_SKILL", "STEP_COMPLETED", "RECORDED"),
            ("fashion.discover", "discover", "skill:PRODUCT_OPPORTUNITY_SCOUT", "AGENCY_SKILL", "STEP_COMPLETED", "RECORDED"),
            ("fashion.verify", "verify", "check:scout-title", "DETERMINISTIC", "STEP_COMPLETED", "RECORDED"),
            ("fashion.plan", "brief", "skill:CONTENT_BRIEF_DRAFT", "AGENCY_SKILL", "STEP_COMPLETED", "RECORDED"),
            ("fashion.handoff", "handoff", f"handoff:{task_id}", "DETERMINISTIC", "STEP_COMPLETED", "RECORDED"),
            ("jarvis.approval", "approval", f"packet:{task_id}", "DETERMINISTIC", "TASK_WAITING_APPROVAL", "WAITING_APPROVAL"),
        ]
        for station_id, step_id, output_ref, provenance, event_type, state in ordered:
            self._step(task_id, step_id, station_id, output_ref, provenance,
                       event_type=event_type, state=state)

    def _step(self, task_id, step_id, station_id, output_ref, provenance,
              event_type="STEP_COMPLETED", state="RECORDED"):
        for event in self.ledger.read_for_task(task_id):
            payload = event.get("payload") or {}
            if event.get("event_type") == event_type and payload.get("step_id") == step_id:
                return
        self.ledger.append(event_type, task_id, {
            "step_id": step_id,
            "station_id": station_id,
            "state": state,
            "output_ref": output_ref,
            "provenance": provenance,
            "workflow_id": WORKFLOW_ID,
            "side_effects": "none",
        }, actor="floor_workflow_v1")


class FloorWorkflowCoordinator:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.handler = FloorWorkflowHandler(orchestrator.ledger)
        orchestrator.register_local_handler(ACTION, self.handler)

    def submit(self, *, objective, context, created_by, tenant_id=None,
               idempotency_key=None):
        tenant_id = tenant_id or canonical_tenant_id()
        manifest = {
            "task_id": f"TASK_{uuid.uuid4().hex[:12].upper()}",
            "title": "Fashion handoff, internal only",
            "objective": objective,
            "task_type": "MAINTENANCE", "work_type": "business_analysis",
            "priority": "NORMAL", "risk_level": "A1", "scientific_risk": "NONE",
            "code_risk": "NONE", "financial_risk": "NONE",
            "required_capabilities": ["json_structured_output", "artifact_field_extraction"],
            "deterministic_tools_available": False, "repo_scope": "NONE",
            "files_allowed": [], "files_forbidden": ["**/*", ".env"],
            "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
            "success_criteria": ["schema valid", "stopped before any external action"],
            "verifier": "business_units.ai_fashion_agency.skills",
            "estimated_complexity": "SMALL", "estimated_runtime": "2m",
            "premium_allowed": False, "preferred_executor": "TIER1_LOCAL_CHEAP",
            "fallback_executors": ["TIER2_LOCAL_STRONG"],
            "approval_required": "REVIEW_REQUIRED", "created_by": created_by,
            "created_at": _now(), "tenant_id": tenant_id, "account_scope_id": None,
        }
        params = {"objective": objective, "context": context, "workflow_id": WORKFLOW_ID,
                  "priority_class": "P2_TRADING_REVENUE_BACKGROUND"}
        if idempotency_key:
            return self.orchestrator.submit_idempotent(
                manifest, action=ACTION, action_params=params,
                idempotency_scope=f"{tenant_id}:{created_by}:{WORKFLOW_ID}",
                idempotency_key=idempotency_key)
        return self.orchestrator.submit(manifest, action=ACTION, action_params=params)


def _owned(record, owner, tenant_id=None):
    if not owner or record.get("action") != ACTION:
        return False
    manifest = record.get("manifest") or {}
    return (manifest.get("created_by") == f"jarvis:{owner}"
            and manifest.get("tenant_id") == (tenant_id or canonical_tenant_id()))


def owns_floor_task(record, *, owner, tenant_id):
    return _owned(record, owner, tenant_id)


def project_trace(queue, ledger, task_id=None, *, owner, tenant_id=None):
    """Sanitized read for one owner and the canonical tenant.

    A missing owner, another user, or another tenant returns an empty trace.
    The response never includes that task id.
    """
    record = None
    if task_id:
        try:
            candidate = queue.get(task_id)
        except KeyError:
            candidate = None
        if candidate is not None and _owned(candidate, owner, tenant_id):
            record = candidate
    else:
        rows = [row for row in queue.list_all() if _owned(row, owner, tenant_id)]
        record = max(rows, key=lambda row: row.get("updated_at") or "") if rows else None
    if record is None:
        return {"source": "ledger", "task_id": None, "state": None, "approval_effect": None,
                "decision": None, "artifact_count": 0, "artifacts": [], "delivery": "not_sent",
                "steps": [], "not_run": []}
    steps = []
    for event in ledger.read_for_task(record["task_id"]):
        if event.get("event_type") not in {"STEP_COMPLETED", "TASK_WAITING_APPROVAL"}:
            continue
        payload = event.get("payload") or {}
        if payload.get("workflow_id") != WORKFLOW_ID:
            continue
        if payload.get("provenance") not in {"DETERMINISTIC", "AGENCY_SKILL"}:
            continue
        if payload.get("state") not in {"RECORDED", "WAITING_APPROVAL"}:
            continue
        steps.append({key: payload.get(key) for key in _STEP_KEYS} | {
            "recorded_at": event.get("timestamp")})
    packet = record.get("result_packet") or {}
    artifacts = []
    for value in packet.get("artifacts_created") or []:
        kind = str(value).split(":", 1)[0][:48]
        artifacts.append({"kind": kind, "available": True})
    return {
        "source": "ledger",
        "task_id": record["task_id"],
        "state": record.get("state"),
        "approval_effect": record.get("approval_effect"),
        "decision": packet.get("decision"),
        "artifact_count": len(packet.get("artifacts_created") or []),
        "artifacts": artifacts,
        "delivery": "not_sent",
        "steps": steps,
        "not_run": list(NOT_RUN),
    }
