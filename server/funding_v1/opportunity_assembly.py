#!/usr/bin/env python3
"""NEXUS TASK #0006 - assembla una OPPORTUNITY_V1 completa a partire dai
campi di INPUT (dichiarati) calcolando TUTTI i campi derivati con la
STESSA logica deterministica per ogni opportunity - evita di duplicare le
regole di priority_status/hard_gate/capital_scenarios/capability_coverage
in ogni singolo builder di dataset."""
import os
import sys

FUNDING_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, FUNDING_DIR)
from opportunity_scoring import score_funding_priority, score_technical_priority  # noqa: E402
from capability_coverage import compute_capability_coverage  # noqa: E402
from capital_scenarios import compute_capital_scenarios  # noqa: E402
from hard_gates import compute_hard_gate  # noqa: E402


def _derive_priority_status(input_type, evidence_confidence):
    """Regola deterministica esplicita - NEXUS TASK #0006 punto 12: mai
    presentare un'assunzione come validazione di mercato."""
    if input_type == "ASSUMPTION":
        return "HYPOTHESIS_BASED" if evidence_confidence == "HIGH" else "PROVISIONAL"
    if input_type == "DECLARED_BY_USER":
        return "HYPOTHESIS_BASED" if evidence_confidence != "VALIDATED" else "VALIDATED"
    # VALIDATED_WITH_EXTERNAL_DATA
    return "VALIDATED" if evidence_confidence == "VALIDATED" else "HYPOTHESIS_BASED"


def assemble_opportunity(*, opportunity_id, title, description, category, status, dimensions,
                        technical_criteria, technical_rationale, funding_rationale,
                        required_capabilities, evidence_confidence, input_type,
                        next_cheapest_validation_step, legal_or_policy_risk_flag=False,
                        created_by, created_at, dimension_estimation_method,
                        lifecycle_state="IDEA"):
    funding_score, funding_breakdown = score_funding_priority(dimensions)
    technical_score, technical_breakdown = score_technical_priority(technical_criteria)
    capability_coverage = compute_capability_coverage(required_capabilities)
    capital_scenarios = compute_capital_scenarios(dimensions, funding_breakdown)
    priority_status = _derive_priority_status(input_type, evidence_confidence)
    hard_gate = compute_hard_gate(
        legal_or_policy_risk_flag=legal_or_policy_risk_flag, capital_scenarios=capital_scenarios,
        capability_coverage=capability_coverage, evidence_confidence=evidence_confidence,
        has_next_cheapest_validation_step=bool(next_cheapest_validation_step))

    return {
        "opportunity_id": opportunity_id, "title": title, "description": description,
        "category": category, "status": status, "dimensions": dimensions,
        "technical_priority": {"score": technical_score, "criteria": technical_criteria,
                              "rationale": technical_rationale},
        "funding_priority": {"score": funding_score, "weighted_breakdown": funding_breakdown,
                            "rationale": funding_rationale},
        "created_by": created_by, "created_at": created_at,
        "provenance": {"dimension_estimation_method": dimension_estimation_method,
                     "reviewed": False},
        "evidence_confidence": evidence_confidence, "priority_status": priority_status,
        "hard_gate": hard_gate, "capital_scenario_priorities": capital_scenarios,
        "required_capabilities": required_capabilities,
        "capability_coverage": capability_coverage, "lifecycle_state": lifecycle_state,
        "next_cheapest_validation_step": next_cheapest_validation_step,
        "learning_record": {
            "initial_score": None, "initial_confidence": None, "user_decision": None,
            "validation_cost": None, "human_time": None, "machine_time": None, "result": None,
            "first_revenue_if_any": None, "actual_time_to_cash": None, "failure_reason": None,
            "prediction_error": None,
        },
        "legal_or_policy_risk_flag": legal_or_policy_risk_flag, "input_type": input_type,
    }
