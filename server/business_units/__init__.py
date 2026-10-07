"""NEXUS Business Units: shared, read-only operating-model contract.

A Business Unit is an internal company of NEXUS (Trading, Revenue, Social,
AI Fashion Agency, ...).  It owns its domain state and policies but never its
own orchestrator, queue, memory or CRM: work is routed through the canonical
Orchestrator / TaskQueue / EventLedger and supervised by Jarvis.

This module only defines the common projection every unit publishes so Jarvis
and the future NEXUS_EXECUTIVE_STATE_V1 can read all units the same way.
"""
from __future__ import annotations

from datetime import datetime, timezone

BUSINESS_UNIT_STATE_SCHEMA = "BUSINESS_UNIT_STATE_V1"
HEALTH_VALUES = ("GREEN", "AMBER", "RED", "NOT_STARTED")
DECISION_VALUES = ("NONE", "HUMAN_APPROVAL_REQUIRED", "HUMAN_REVIEW_REQUIRED")

# Units known to the executive layer.  Only AI_FASHION_AGENCY publishes this
# projection today; the others keep their existing projections until migrated.
REGISTERED_UNITS = {
    "AI_FASHION_AGENCY": "business_units.ai_fashion_agency.projection:business_unit_state",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def build_business_unit_state(*, unit_id, name, mission, state, health, inputs, workers,
                              capabilities, kpis, costs_eur, revenue_eur, risks, tasks,
                              evidence, next_gate, decision, generated_at=None):
    if health not in HEALTH_VALUES:
        raise ValueError("invalid business unit health")
    if decision.get("status") not in DECISION_VALUES:
        raise ValueError("invalid business unit decision status")
    return {
        "schema_version": BUSINESS_UNIT_STATE_SCHEMA, "unit_id": unit_id, "name": name,
        "mission": mission, "state": state, "health": health, "inputs": list(inputs),
        "workers": list(workers), "capabilities": list(capabilities), "kpis": dict(kpis),
        "costs_eur": round(float(costs_eur), 2), "revenue_eur": round(float(revenue_eur), 2),
        "net_eur": round(float(revenue_eur) - float(costs_eur), 2),
        "risks": list(risks), "tasks": dict(tasks), "evidence": list(evidence),
        "next_gate": next_gate, "decision": dict(decision),
        "generated_at": generated_at or _now(),
    }
