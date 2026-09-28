"""Test per il Funding Priority & Opportunity Framework V1 (NEXUS TASK
#0005). Verifica: schemi validi, separazione TECHNICAL_PRIORITY/
FUNDING_PRIORITY, pesi di scoring espliciti (sommano 1.0), determinismo dei
builder, coerenza della priority queue generata."""
import json
import os
import sys

FUNDING_DIR = os.path.join(os.path.dirname(__file__), "..", "funding_v1")
ORCH_DIR = os.path.join(os.path.dirname(__file__), "..", "orchestrator_v1")
CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "contracts")
sys.path.insert(0, os.path.abspath(FUNDING_DIR))
sys.path.insert(0, os.path.abspath(ORCH_DIR))

from opportunity_scoring import (FUNDING_DIMENSION_WEIGHTS, TECHNICAL_CRITERIA_WEIGHTS,  # noqa: E402
                                 score_funding_priority, score_technical_priority)
from nxs_schema_validator import validate  # noqa: E402
from build_example_opportunities import build as build_opportunities  # noqa: E402
from build_opportunity_priority_queue import build as build_queue  # noqa: E402


def _load_schema(name):
    with open(os.path.join(CONTRACTS_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def test_funding_weights_sum_to_one():
    assert abs(sum(FUNDING_DIMENSION_WEIGHTS.values()) - 1.0) < 1e-9


def test_technical_weights_sum_to_one():
    assert abs(sum(TECHNICAL_CRITERIA_WEIGHTS.values()) - 1.0) < 1e-9


def test_scoring_functions_return_0_to_100():
    dims = {k: list(v.keys())[0] for k, v in __import__("opportunity_scoring")
           .FUNDING_DIMENSION_POINTS.items()}
    score, breakdown = score_funding_priority(dims)
    assert 0 <= score <= 100
    assert set(breakdown.keys()) == set(FUNDING_DIMENSION_WEIGHTS.keys())


def test_all_example_opportunities_validate_against_schema():
    schema = _load_schema("opportunity.schema.json")
    payload = build_opportunities()
    assert len(payload["opportunities"]) >= 5
    for opp in payload["opportunities"]:
        errors = validate(opp, schema)
        assert errors == [], f"{opp['opportunity_id']}: {errors}"


def test_technical_and_funding_priority_are_genuinely_independent_axes():
    """Il test che conta di piu': il ranking per technical_priority NON deve
    essere identico al ranking per funding_priority - altrimenti i due assi
    sarebbero de facto fusi, contraddicendo l'obiettivo esplicito del
    framework."""
    payload = build_opportunities()
    by_technical = sorted(payload["opportunities"], key=lambda o: -o["technical_priority"]["score"])
    by_funding = sorted(payload["opportunities"], key=lambda o: -o["funding_priority"]["score"])
    technical_order = [o["opportunity_id"] for o in by_technical]
    funding_order = [o["opportunity_id"] for o in by_funding]
    assert technical_order != funding_order, "i due ranking non devono essere identici"


def test_priority_queue_validates_against_schema():
    schema = _load_schema("opportunity-priority-queue.schema.json")
    payload = build_queue()
    errors = validate(payload, schema)
    assert errors == [], errors


def test_priority_queue_builder_is_deterministic():
    p1 = build_queue()
    p2 = build_queue()
    # generated_at cambia (volatile) - il resto no
    p1.pop("generated_at")
    p2.pop("generated_at")
    assert p1 == p2


def test_funding_can_finance_technical_is_never_auto_inferred():
    """funding_can_finance_technical deve essere dichiarato esplicitamente
    (None o una lista scritta a mano) - MAI calcolato da una correlazione
    statistica fra i due punteggi."""
    payload = build_queue()
    from build_opportunity_priority_queue import FUNDING_CAN_FINANCE_TECHNICAL
    for entry in payload["combined_view"]:
        oid = entry["opportunity_id"]
        expected = FUNDING_CAN_FINANCE_TECHNICAL.get(oid)
        assert entry["funding_can_finance_technical"] == expected
