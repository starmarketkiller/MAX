"""Agency bounded skills, routed through the canonical Orchestrator.

Mirrors funding_v1.revenue_agent: a declarative skill pack, a deterministic
verifier per skill and a thin coordinator that registers one local handler.
No second router, queue or provider selection: the Orchestrator decides the
executor (local Ministral first, stronger-local retry, escalation proposal).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from funding_v1.revenue_skill_pack import RevenueSkill
from jarvis_v1.ministral_task_compiler import encode_bounded_output

from .pipeline import FORBIDDEN_CLAIM_RE


def _skill(skill_id, example):
    return RevenueSkill(skill_id=skill_id, output_fields=frozenset(example),
                        output_example=example)


AGENCY_SKILLS = {
    "VIRAL_FORMAT_ANALYSIS": _skill("agency_viral_format_analysis", {
        "format_name": "text", "hook_pattern": "text", "beats": ["text"],
        "payoff": "text", "comment_bait": "text", "audio_strategy": "PLATFORM_LIBRARY",
        "duration_seconds": 15, "evidence": ["E1"], "limitations": []}),
    "PRODUCT_OPPORTUNITY_SCOUT": _skill("agency_product_opportunity_scout", {
        "title": "text", "category": "text", "trend_evidence": ["E1"],
        "target_audience": "text", "risks": [], "missing_info": []}),
    "CONTENT_BRIEF_DRAFT": _skill("agency_content_brief_draft", {
        "title": "text", "content_category": "viral_formats", "hook": "max 8 words",
        "script": "text", "caption": "text", "cta": "text", "evidence": ["E1"]}),
    "CONTENT_REVIEW": _skill("agency_content_review", {
        "verdict": "APPROVE", "issues": [], "evidence": ["E1"]}),
    "PERFORMANCE_SUMMARY": _skill("agency_performance_summary", {
        "summary": "text", "top_items": [], "next_actions": [], "limitations": []}),
}

AUDIO_STRATEGIES = {"PLATFORM_LIBRARY", "ORIGINAL", "LICENSED"}
CONTENT_CATEGORIES = {"viral_formats", "humor", "lifestyle", "fashion", "product_content",
                      "shoots", "special_occasions", "runway_casting"}


def get_agency_skill(task_type):
    try:
        return AGENCY_SKILLS[task_type]
    except KeyError as exc:
        raise ValueError("unsupported agency task type") from exc


def _evidence_ids(context):
    return {item.get("evidence_id") for item in context.get("evidence_records", [])
            if isinstance(item, dict)}


def verify_agency_output(task_type, output, context):
    """Deterministic, skill-specific validation; returns (ok, errors)."""
    try:
        skill = get_agency_skill(task_type)
    except ValueError:
        return False, ["unsupported agency task type"]
    if not isinstance(output, dict) or set(output) != skill.output_fields:
        return False, ["exact output schema required"]
    errors = []
    evidence = _evidence_ids(context)
    refs = output.get("evidence") if "evidence" in output else output.get("trend_evidence")
    if refs is not None and (not isinstance(refs, list) or not refs or
                             not set(refs).issubset(evidence)):
        errors.append("evidence must reference supplied evidence_id values")
    if task_type == "VIRAL_FORMAT_ANALYSIS":
        if output.get("audio_strategy") not in AUDIO_STRATEGIES:
            errors.append("audio must be platform-library, original or licensed")
        if not isinstance(output.get("beats"), list) or not 2 <= len(output["beats"]) <= 8:
            errors.append("beats must list 2..8 structural beats")
        if not isinstance(output.get("duration_seconds"), int) or \
                not 5 <= output["duration_seconds"] <= 90:
            errors.append("duration_seconds must be 5..90")
    elif task_type == "CONTENT_BRIEF_DRAFT":
        if output.get("content_category") not in CONTENT_CATEGORIES:
            errors.append("invalid content category")
        if len(str(output.get("hook", "")).split()) > 8:
            errors.append("hook must be at most 8 words")
        text = " ".join(str(output.get(k, "")) for k in ("hook", "script", "caption", "cta"))
        if FORBIDDEN_CLAIM_RE.search(text):
            errors.append("misleading or absolute claim")
    elif task_type == "CONTENT_REVIEW":
        if output.get("verdict") not in {"APPROVE", "REVISE", "REJECT"}:
            errors.append("invalid review verdict")
    for key in ("limitations", "risks", "missing_info", "issues", "top_items", "next_actions"):
        if key in output and not isinstance(output[key], list):
            errors.append(f"{key} must be an array")
    return not errors, errors


class AgencyLocalTaskHandler:
    json_mode = True
    retry_on_stronger_local = True

    def __init__(self):
        self.errors_by_task = {}

    def build_prompt(self, record):
        params = record["action_params"]
        task_type, context = params["agency_task_type"], params["context"]
        skill = get_agency_skill(task_type)
        retry = self.errors_by_task.get(record["task_id"], [])
        correction = ("Previous output failed: " + "; ".join(retry[:3]) +
                      ". Correct it without adding facts.\n") if record.get("retry_count") else ""
        return (correction + "You work for the NEXUS AI Fashion Agency. Use only CONTEXT. "
                "Never copy or reuse third-party footage, never invent facts, prices or claims. "
                "Return one JSON object with exactly this shape and no prose: "
                + json.dumps(skill.output_example, ensure_ascii=False) +
                " Evidence arrays must use exact evidence_id values from CONTEXT."
                f"\nTASK_TYPE: {task_type}"
                f"\nCONTEXT: {json.dumps(context, ensure_ascii=False, sort_keys=True)}")

    def verify(self, record, response_text):
        from orchestrator_v1.core.orchestrator import VerifyResult
        try:
            output = json.loads(response_text)
        except (TypeError, ValueError):
            output = None
        ok, errors = verify_agency_output(record["action_params"]["agency_task_type"], output,
                                          record["action_params"]["context"])
        self.errors_by_task[record["task_id"]] = errors
        return VerifyResult(passed=ok, parsed_output=output, errors=errors, is_logic_error=not ok)

    def apply(self, record, verify_result):
        from orchestrator_v1.core.orchestrator import ApplyResult
        artifact = encode_bounded_output(record["action_params"]["agency_task_type"],
                                         record["task_id"], verify_result.parsed_output)
        return ApplyResult(artifacts_created=[artifact], touches_real_repo_files=False)


class AgencyTaskCoordinator:
    """Compiles bounded Agency work for the canonical Orchestrator.

    P2_TRADING_REVENUE_BACKGROUND priority: Agency work never preempts Jarvis
    interactive (P0) or explicit user tasks (P1).
    """
    ACTION = "agency_bounded_task"

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.handler = AgencyLocalTaskHandler()
        orchestrator.register_local_handler(self.ACTION, self.handler)

    def compile_manifest(self, task_type, *, created_by):
        get_agency_skill(task_type)
        return {
            "task_id": f"TASK_{uuid.uuid4().hex[:12].upper()}",
            "title": f"AI Fashion Agency: {task_type}",
            "objective": f"Produce a grounded bounded {task_type} result",
            "task_type": "MAINTENANCE", "work_type": "business_analysis",
            "priority": "NORMAL", "risk_level": "A1", "scientific_risk": "NONE",
            "code_risk": "NONE", "financial_risk": "NONE",
            "required_capabilities": ["json_structured_output", "artifact_field_extraction"],
            "deterministic_tools_available": False, "repo_scope": "NONE",
            "files_allowed": [], "files_forbidden": ["**/*", ".env"],
            "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
            "success_criteria": ["schema valid", "all evidence grounded in supplied context"],
            "verifier": f"business_units.ai_fashion_agency.skills:{task_type}",
            "estimated_complexity": "SMALL", "estimated_runtime": "2m",
            "premium_allowed": False, "preferred_executor": "TIER1_LOCAL_CHEAP",
            "fallback_executors": ["TIER2_LOCAL_STRONG"],
            "approval_required": "REVIEW_REQUIRED", "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
            "account_scope_id": None,
        }

    def submit(self, task_type, *, context, references, created_by="ai_fashion_agency"):
        manifest = self.compile_manifest(task_type, created_by=created_by)
        params = {"agency_task_type": task_type, "context": context,
                  "references": {**references, "business_unit": "AI_FASHION_AGENCY"},
                  "priority_class": "P2_TRADING_REVENUE_BACKGROUND"}
        return self.orchestrator.submit(manifest, action=self.ACTION, action_params=params)
