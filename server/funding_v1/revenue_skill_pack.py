"""Declarative bounded skill pack for the local-first Revenue Agent."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RevenueSkill:
    skill_id: str
    output_fields: frozenset[str]
    output_example: dict
    max_retries: int = 1
    default_executor: str = "LOCAL_FAST_MINISTRAL3B"
    escalation_rule: str = "VERIFIER_FAILURE_AFTER_RETRY_OR_AMBIGUITY_OR_HIGH_RISK"
    telemetry: tuple[str, ...] = (
        "attempts", "verifier_status", "latency_seconds", "executor",
        "escalation_target", "premium_calls",
    )


def _skill(skill_id, example):
    return RevenueSkill(skill_id=skill_id, output_fields=frozenset(example),
                        output_example=example)


REVENUE_SKILLS = {
    "PROSPECT_FACT_EXTRACTION": _skill("prospect_fact_extraction", {
        "facts": [{"claim": "short claim", "evidence": "E1"}], "missing_info": []}),
    "LEAD_QUALIFICATION": _skill("lead_qualification", {
        "decision": "FIT", "fit_score": 0, "evidence": ["E1"],
        "reason": "max 2 sentences", "missing_info": []}),
    "OFFER_FIT_ANALYSIS": _skill("offer_fit", {
        "fit": "INSUFFICIENT_EVIDENCE", "matched_problem": "text",
        "evidence": ["E1"], "conflicts": []}),
    "OUTREACH_DRAFT": _skill("outreach_draft", {
        "subject": "text", "body": "text", "evidence_refs": ["E1"],
        "price_mentions": [], "promises": []}),
    "INBOUND_CLASSIFICATION": _skill("inbound_classification", {
        "classification": "REPLIED", "evidence_quotes": ["exact input quote"],
        "recommended_status": "REPLIED"}),
    "FOLLOW_UP_DRAFT": _skill("followup_draft", {
        "subject": "text", "body": "text", "evidence_refs": ["E1"]}),
    "PIPELINE_SUMMARY": _skill("pipeline_summary", {
        "summary": "text", "blockers": [], "next_actions": []}),
    "REVENUE_EXPERIMENT_SUMMARY": _skill("revenue_experiment_summary", {
        "summary": "text", "observed_metrics": {}, "limitations": []}),
    "VENTURE_LEAD_RESEARCH": _skill("venture_lead_research", {
        "prospects": [], "summary": "text", "limitations": []}),
    "VENTURE_EA_MQL5_AUDIT": _skill("venture_ea_mql5_audit", {
        "issues": [], "summary": "text", "limitations": []}),
    "VENTURE_STRATEGY_ROBUSTNESS_AUDIT": _skill("venture_strategy_robustness_audit", {
        "verdict": "INSUFFICIENT_EVIDENCE", "checks": [], "summary": "text",
        "limitations": []}),
    "VENTURE_INTELLIGENCE": _skill("venture_intelligence", {
        "mode": "COMPETITOR_ANALYSIS", "entities": [], "comparison": [],
        "ranking": [], "risks": [], "opportunities": [], "facts": [],
        "inferences": [], "limitations": []}),
}


def get_revenue_skill(task_type):
    try:
        return REVENUE_SKILLS[task_type]
    except KeyError as exc:
        raise ValueError("unsupported revenue task type") from exc
