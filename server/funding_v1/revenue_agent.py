"""NEXUS_REVENUE_AGENT_V1: thin, local-first coordinator.

It compiles bounded work for the canonical Orchestrator.  It cannot send
email, change price, promise delivery, sign contracts or move money.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from jarvis_v1.ministral_task_compiler import encode_bounded_output
from funding_v1.revenue_skill_pack import get_revenue_skill


def _now():
    return datetime.now(timezone.utc).isoformat()


def _canonical_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def draft_fingerprint(subject, body):
    return "sha256:" + hashlib.sha256(
        (subject.strip() + "\n" + body.strip()).encode("utf-8")).hexdigest()


def _grounded(items, supplied_text):
    haystack = supplied_text.casefold()
    return all(isinstance(item, str) and item.strip() and item.casefold() in haystack
               for item in items)


def _normalize_context(context):
    value = json.loads(json.dumps(context))
    facts = value.get("prospect_facts")
    if isinstance(facts, list) and all(isinstance(item, str) for item in facts):
        value["evidence_records"] = [
            {"evidence_id": f"E{index}", "text": text}
            for index, text in enumerate(facts, 1)
        ]
    return value


def verify_revenue_output(task_type, output, context):
    """Deterministic, task-specific validation; returns (ok, errors)."""
    errors = []
    try:
        skill = get_revenue_skill(task_type)
    except ValueError:
        return False, ["unsupported revenue task type"]
    if not isinstance(output, dict) or set(output) != skill.output_fields:
        return False, ["exact output schema required"]
    supplied = _canonical_text(context)
    evidence_key = "evidence_quotes" if task_type == "INBOUND_CLASSIFICATION" else (
        "evidence_refs" if task_type in {"OUTREACH_DRAFT", "FOLLOW_UP_DRAFT"} else "evidence")
    if evidence_key in output and not _grounded(output[evidence_key], supplied):
        errors.append("invented or ungrounded evidence")
    if task_type == "PROSPECT_FACT_EXTRACTION":
        facts = output.get("facts")
        evidence_records = {item.get("evidence_id"): item.get("text", "")
                            for item in context.get("evidence_records", [])
                            if isinstance(item, dict)}
        if not isinstance(facts, list) or not all(
                isinstance(item, dict) and set(item) == {"claim", "evidence"} and
                isinstance(item["claim"], str) and item["claim"].strip() and
                isinstance(item["evidence"], str) and
                (evidence_records.get(item["evidence"]) or item["evidence"]).casefold()
                in supplied.casefold() and
                item["claim"].casefold() in
                (evidence_records.get(item["evidence"]) or item["evidence"]).casefold()
                for item in facts):
            errors.append("facts require grounded claim/evidence pairs")
    elif task_type == "LEAD_QUALIFICATION":
        if output.get("decision") not in {"FIT", "NO_FIT"}:
            errors.append("qualification decision must be FIT or NO_FIT")
        if not isinstance(output.get("fit_score"), int) or not 0 <= output["fit_score"] <= 100:
            errors.append("fit_score must be integer 0..100")
    elif task_type == "OFFER_FIT_ANALYSIS":
        if output.get("fit") not in {"FIT", "NO_FIT", "INSUFFICIENT_EVIDENCE"}:
            errors.append("invalid offer fit")
    elif task_type == "OUTREACH_DRAFT":
        offer = context.get("offer") or {}
        approved_price = offer.get("price") or {}
        if output.get("price_mentions"):
            allowed = approved_price.get("reviewed") is True and all(
                mention == {"amount": approved_price.get("amount"),
                            "currency": approved_price.get("currency")}
                for mention in output["price_mentions"])
            if not allowed:
                errors.append("draft contains unapproved or changed price")
        if output.get("promises"):
            errors.append("commercial promises require human review and cannot pass local verifier")
    elif task_type == "INBOUND_CLASSIFICATION":
        allowed = {"REPLIED", "INTERESTED", "LOST", "AMBIGUOUS"}
        if output.get("classification") not in allowed:
            errors.append("invalid inbound classification")
        lead = context.get("lead") or {}
        proposed = output.get("recommended_status")
        from funding_v1.first_revenue import LEAD_TRANSITIONS
        if proposed not in LEAD_TRANSITIONS.get(lead.get("status"), set()):
            errors.append("invalid lifecycle proposal")
    elif task_type == "FOLLOW_UP_DRAFT":
        lead = context.get("lead") or {}
        if lead.get("status") != "CONTACTED" or not lead.get("outreach_receipt"):
            errors.append("follow-up requires verified outreach")
    elif task_type == "VENTURE_LEAD_RESEARCH":
        prospects = output.get("prospects")
        if not isinstance(prospects, list) or not 15 <= len(prospects) <= 20:
            errors.append("lead research requires 15..20 prospects")
        else:
            required = {"name", "source_ref", "public_contact", "fit_reason", "priority"}
            evidence = {item.get("evidence_id") for item in context.get("evidence_records", [])}
            if not all(isinstance(item, dict) and set(item) == required and
                       item.get("source_ref") in evidence and
                       item.get("priority") in {"HIGH", "MEDIUM", "LOW"}
                       for item in prospects):
                errors.append("prospects require grounded source references and valid priority")
    elif task_type == "VENTURE_EA_MQL5_AUDIT":
        issues = output.get("issues")
        required = {"severity", "evidence", "file", "line", "issue", "impact",
                    "recommended_action", "confidence"}
        allowed = {item.get("finding_id") for item in context.get("static_findings", [])}
        if not isinstance(issues, list) or not all(
                isinstance(item, dict) and set(item) == required and
                item.get("severity") in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"} and
                item.get("evidence") in allowed and isinstance(item.get("line"), int)
                for item in issues):
            errors.append("EA issues must reference deterministic MQL5 findings")
    elif task_type == "VENTURE_STRATEGY_ROBUSTNESS_AUDIT":
        if output.get("verdict") not in {
                "ROBUST", "BORDERLINE", "INSUFFICIENT_EVIDENCE", "FAILED"}:
            errors.append("invalid robustness verdict")
        required_checks = {"sample_size", "oos", "holdout", "cost_sensitivity",
                           "parameter_sensitivity", "long_short_asymmetry",
                           "regime_dependency", "drawdown", "clustering", "leakage",
                           "proxy_broker_caveat", "multiple_testing"}
        checks = output.get("checks")
        if not isinstance(checks, list) or {x.get("check") for x in checks
                                            if isinstance(x, dict)} != required_checks:
            errors.append("robustness report requires the frozen check set")
        if output.get("verdict") == "ROBUST" and context.get("true_holdout") is not True:
            errors.append("ROBUST requires an explicit true holdout")
    elif task_type == "VENTURE_INTELLIGENCE":
        if output.get("mode") not in {"COMPETITOR_ANALYSIS", "SUPPLIER_RESEARCH"}:
            errors.append("invalid intelligence mode")
        evidence = {item.get("evidence_id") for item in context.get("evidence_records", [])}
        facts = output.get("facts")
        if not isinstance(facts, list) or not all(
                isinstance(item, dict) and set(item) == {"claim", "source_ref"} and
                item.get("source_ref") in evidence for item in facts):
            errors.append("facts must reference supplied evidence")
        if not isinstance(output.get("inferences"), list) or not all(
                isinstance(item, dict) and set(item) == {"inference", "based_on"} and
                set(item.get("based_on", [])).issubset(evidence) for item in output.get("inferences", [])):
            errors.append("inferences must be explicitly separated and grounded")
    for key in ("missing_info", "conflicts", "blockers", "next_actions", "limitations"):
        if key in output and not isinstance(output[key], list):
            errors.append(f"{key} must be an array")
    return not errors, errors


class RevenueLocalTaskHandler:
    json_mode = True
    # Opt-in consumed by the canonical Orchestrator. Revenue work gets one
    # cheap attempt, then one stronger-local correction; legacy handlers keep
    # their existing same-tier retry behavior.
    retry_on_stronger_local = True

    def __init__(self):
        self.errors_by_task = {}

    def build_prompt(self, record):
        params = record["action_params"]
        task_type, context = params["revenue_task_type"], params["context"]
        skill = get_revenue_skill(task_type)
        retry = self.errors_by_task.get(record["task_id"], [])
        correction = ("Previous output failed: " + "; ".join(retry[:3]) +
                      ". Correct it without adding facts.\n") if record.get("retry_count") else ""
        return (correction + "Use only CONTEXT. Do not browse, contact anyone, change pricing, "
                "promise services, accept contracts or move money. Return one JSON object with "
                "exactly this shape and no prose: " + _canonical_text(skill.output_example) +
                " Evidence/evidence_refs arrays must use exact evidence_id values from CONTEXT "
                "when evidence_records are present."
                f"\nTASK_TYPE: {task_type}"
                f"\nCONTEXT: {_canonical_text(context)}")

    def verify(self, record, response_text):
        from orchestrator_v1.core.orchestrator import VerifyResult
        try:
            output = json.loads(response_text)
        except (TypeError, ValueError):
            output = None
        ok, errors = verify_revenue_output(
            record["action_params"]["revenue_task_type"], output,
            record["action_params"]["context"])
        self.errors_by_task[record["task_id"]] = errors
        return VerifyResult(passed=ok, parsed_output=output, errors=errors,
                            is_logic_error=not ok)

    def apply(self, record, verify_result):
        from orchestrator_v1.core.orchestrator import ApplyResult
        artifact = encode_bounded_output(
            record["action_params"]["revenue_task_type"], record["task_id"],
            verify_result.parsed_output)
        return ApplyResult(artifacts_created=[artifact], touches_real_repo_files=False)


class RevenueAgentCoordinator:
    ACTION = "revenue_agent_bounded_task"

    def __init__(self, store, orchestrator):
        self.store = store
        self.orchestrator = orchestrator
        self.handler = RevenueLocalTaskHandler()
        orchestrator.register_local_handler(self.ACTION, self.handler)

    def compile_manifest(self, task_type, *, context, references, created_by="revenue_agent"):
        get_revenue_skill(task_type)
        task_id = f"TASK_{uuid.uuid4().hex[:12].upper()}"
        return {
            "task_id": task_id, "title": f"Revenue Agent: {task_type}",
            "objective": f"Produce a grounded bounded {task_type} result",
            "task_type": "MAINTENANCE", "work_type": "business_analysis",
            "priority": "NORMAL", "risk_level": "A1", "scientific_risk": "NONE",
            "code_risk": "NONE", "financial_risk": "NONE",
            "required_capabilities": ["json_structured_output", "artifact_field_extraction",
                                      ],
            "deterministic_tools_available": False, "repo_scope": "NONE",
            "files_allowed": [], "files_forbidden": ["**/*", ".env"],
            "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
            "success_criteria": ["schema valid", "all evidence grounded in supplied context"],
            "verifier": f"funding_v1.revenue_agent:{task_type}",
            "estimated_complexity": "SMALL", "estimated_runtime": "2m",
            "premium_allowed": False, "preferred_executor": "TIER1_LOCAL_CHEAP",
            "fallback_executors": ["TIER2_LOCAL_STRONG"],
            "approval_required": "REVIEW_REQUIRED", "created_by": created_by,
            "created_at": _now(), "tenant_id": "tenant-1", "account_scope_id": None,
        }, {"revenue_task_type": task_type, "context": context, "references": references}

    def submit(self, task_type, *, context, references, created_by="revenue_agent"):
        context = _normalize_context(context)
        manifest, params = self.compile_manifest(
            task_type, context=context, references=references, created_by=created_by)
        return self.orchestrator.submit(manifest, action=self.ACTION, action_params=params)

    def proposal(self, task_id, output, *, recommended_action, required_approval,
                 lead_id=None, opportunity_id=None):
        record = self.orchestrator.queue.get(task_id)
        ok, errors = verify_revenue_output(record["action_params"]["revenue_task_type"], output,
                                           record["action_params"]["context"])
        return {
            "schema_version": 1,
            "proposal_id": f"NAP_{uuid.uuid4().hex[:12].upper()}",
            "proposal_only": True,
            "lead_id": lead_id,
            "opportunity_id": opportunity_id,
            "recommended_next_action": recommended_action,
            "required_approval": required_approval,
            "source_task_id": task_id,
            "verifier_status": "PASS" if ok else "FAIL",
            "verifier_errors": errors,
            "provenance": {"source": "NEXUS_REVENUE_AGENT_V1", "generated_at": _now(),
                           "task_state": record["state"]},
        }


class RevenueFollowUpPlanner:
    """Read/proposal-only; it never mutates lead lifecycle or sends outreach."""

    def __init__(self, follow_up_after=timedelta(days=3)):
        self.follow_up_after = follow_up_after

    def propose(self, lead):
        if lead.get("status") != "CONTACTED" or not lead.get("outreach_receipt"):
            return None
        sent_at = datetime.fromisoformat(lead["outreach_receipt"]["recorded_at"])
        return {"proposal_only": True, "lead_id": lead["lead_id"],
                "action": "PREPARE_FOLLOW_UP", "next_review_at":
                (sent_at + self.follow_up_after).isoformat(),
                "required_approval": "EXPLICIT_USER_APPROVAL"}


def compute_revenue_metrics(snapshot, ledger_events=None):
    leads = snapshot.get("leads", [])
    status_count = {status: sum(item.get("status") == status for item in leads)
                    for status in ("QUALIFIED", "CONTACTED", "REPLIED", "INTERESTED", "WON", "LOST")}
    revenue = snapshot.get("revenues", [])
    attention = snapshot.get("attention_events", [])
    experiment_ids = {item["experiment_id"] for item in attention}
    active_seconds = sum(item["active_decision_seconds"] for item in attention)
    latencies = [item["approval_latency_seconds"] for item in attention]
    events = ledger_events or []
    return {
        "prospects": len(snapshot.get("prospects", [])),
        "leads": len(leads), **{key.lower(): value for key, value in status_count.items()},
        "revenue": sum(item["amount"] for item in revenue),
        "cost": sum(item["cost"] for item in revenue),
        "gross_margin": sum(item["gross_margin"] for item in revenue),
        "human_intervention_count": len(attention),
        "estimated_active_decision_seconds": active_seconds,
        "human_minutes_per_revenue_experiment": (
            active_seconds / 60 / len(experiment_ids) if experiment_ids else 0),
        "approval_latency_seconds_average": (
            sum(latencies) / len(latencies) if latencies else 0),
        "ministral_retry_count": sum(item.get("event_type") == "RETRY_STARTED" for item in events),
        "ministral_failure_count": sum(item.get("event_type") in {"TASK_FAILED", "TEST_FAILED"}
                                       for item in events),
        "escalation_count": sum(item.get("event_type") == "ESCALATION_REQUIRED" for item in events),
    }
