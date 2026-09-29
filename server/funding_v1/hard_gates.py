#!/usr/bin/env python3
"""NEXUS TASK #0006 - Hard Gates V1: un punteggio alto NON puo' MAI
bypassare un gate reale - calcolo deterministico, ordine di precedenza
esplicito e documentato (mai un punteggio ponderato che li fonde)."""

GATE_ORDER_NOTE = (
    "Precedenza fissa: legal/policy risk > capitale (a zero capitale, BOOTSTRAP_0_100) > "
    "capacita' mancanti > qualita' dell'evidenza. Un hard_gate BLOCKED_* non e' mai "
    "sovrascritto da un punteggio funding/technical alto."
)


def compute_hard_gate(*, legal_or_policy_risk_flag, capital_scenarios, capability_coverage,
                      evidence_confidence, has_next_cheapest_validation_step):
    if legal_or_policy_risk_flag:
        return "BLOCKED_BY_LEGAL_OR_POLICY_RISK"

    if not capital_scenarios["BOOTSTRAP_0_100"]["feasible"]:
        return "BLOCKED_BY_CAPITAL"

    blocking_statuses = {"MISSING", "EXTERNAL_SERVICE_REQUIRED"}
    if any(v in blocking_statuses for v in capability_coverage["per_capability"].values()):
        return "BLOCKED_BY_CAPABILITY"

    if evidence_confidence == "LOW" and not has_next_cheapest_validation_step:
        return "BLOCKED_BY_MISSING_DATA"

    return {
        "LOW": "RESEARCH_REQUIRED",
        "MEDIUM": "READY_FOR_VALIDATION",
        "HIGH": "READY_FOR_MVP",
        "VALIDATED": "READY_FOR_MARKET_TEST",
    }[evidence_confidence]
