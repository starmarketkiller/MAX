import json
from pathlib import Path

import pytest

from funding_v1.first_revenue import FirstRevenueStore
from funding_v1.market_scout import (MarketScoutLocalHandler, codex_review_market_scout,
                                     compile_market_scout_task, compile_single_retry,
                                     validate_market_scout_output)
from orchestrator_v1.core.ledger import EventLedger
from orchestrator_v1.nxs_schema_validator import validate


def provenance():
    return {"source": "pytest", "confidence": "VERIFIED", "reference": "fixture"}


def build(tmp_path):
    ledger = EventLedger(tmp_path / "ledger.jsonl")
    return FirstRevenueStore(tmp_path / "first_revenue.json", ledger=ledger), ledger


def opportunity():
    return {"opportunity_id": "OPP_REVIEW_KIT", "source": "user candidate",
            "evidence": ["Prospect provides local services"], "target_customer_type": "local business",
            "problem": "review follow-up is manual", "possible_solution": "QR/NFC review kit",
            "estimated_value": {"amount": 25, "currency": "EUR", "status": "ESTIMATE"},
            "confidence": "LOW", "next_action": "qualify ten supplied prospects",
            "provenance": provenance()}


def offer():
    return {"offer_id": "OFFER_REVIEW_KIT_1", "opportunity_id": "OPP_REVIEW_KIT",
            "problem": "manual review follow-up", "deliverable": "one configured QR review page",
            "price": {"amount": 25, "currency": "EUR", "reviewed": True},
            "delivery_time": "2 business days", "included": ["setup"],
            "excluded": ["outreach automation"], "status": "REVIEWED", "provenance": provenance()}


def lead():
    return {"lead_id": "LEAD_001", "opportunity_id": "OPP_REVIEW_KIT",
            "offer_id": "OFFER_REVIEW_KIT_1", "display_name": "Prospect 001",
            "customer_type": "local business", "source": "user supplied", "provenance": provenance()}


def seed(store):
    store.register_opportunity(opportunity()); store.create_offer(offer()); store.create_lead(lead())


def test_end_to_end_first_revenue_and_ledger(tmp_path):
    store, ledger = build(tmp_path); seed(store)
    for status in ("QUALIFIED", "CONTACT_READY"):
        store.transition_lead("LEAD_001", status)
    with pytest.raises(PermissionError):
        store.transition_lead("LEAD_001", "CONTACTED")
    store.transition_lead("LEAD_001", "CONTACTED", approval={
        "status": "APPROVED", "approved_by": "user", "message_fingerprint": "sha256:abc"})
    for status in ("REPLIED", "INTERESTED"):
        store.transition_lead("LEAD_001", status)
    store.link_delivery_task("LEAD_001", "TASK_DELIVERY_001")
    store.transition_lead("LEAD_001", "WON")
    store.record_payment({"payment_id": "PAY_001", "offer_id": "OFFER_REVIEW_KIT_1",
                          "lead_id": "LEAD_001", "amount": 25, "currency": "EUR",
                          "method": "REVOLUT", "status": "PAID", "external_reference": "rev-observed-1",
                          "provenance": provenance(), "money_movement_capability": False})
    revenue = store.record_revenue(payment_id="PAY_001", cost=5, time_spent="45m",
                                   acquisition_source="user supplied", provenance=provenance())
    assert revenue["gross_margin"] == 20.0
    assert store.snapshot()["leads"][0]["status"] == "WON"
    assert store.snapshot()["leads"][0]["delivery_task_id"] == "TASK_DELIVERY_001"
    assert any(event["event_type"] == "FIRST_REVENUE_RECORD_UPDATED" for event in ledger.read_all())


def test_no_payment_movement_and_paid_requires_evidence(tmp_path):
    store, _ = build(tmp_path); seed(store)
    base = {"payment_id": "PAY_BAD", "offer_id": "OFFER_REVIEW_KIT_1", "lead_id": "LEAD_001",
            "amount": 25, "currency": "EUR", "method": "REVOLUT", "status": "PAID",
            "external_reference": None, "provenance": provenance(), "money_movement_capability": False}
    with pytest.raises(ValueError, match="external reference"):
        store.record_payment(base)
    with pytest.raises(ValueError, match="cannot move money"):
        store.record_payment({**base, "status": "PENDING", "money_movement_capability": True})


def test_offer_without_price_review_stays_draft(tmp_path):
    store, _ = build(tmp_path); store.register_opportunity(opportunity())
    store.create_offer({**offer(), "price": {"amount": 25, "currency": "EUR", "reviewed": False},
                        "status": "ACTIVE"})
    assert store.snapshot()["offers"][0]["status"] == "DRAFT"


def test_market_scout_compiler_validator_and_codex_review():
    prospect = {"prospect_id": "P1", "facts": ["Prospect provides local services",
                                                  "Website has no visible review follow-up"]}
    task = compile_market_scout_task(prospect)
    assert task["network_allowed"] is False and task["outreach_allowed"] is False
    raw = json.dumps({"problem": "No visible review follow-up",
                      "evidence": ["Website has no visible review follow-up"],
                      "possible_offer": "QR review follow-up starter kit", "fit_score": 65,
                      "reason": "The supplied evidence indicates a bounded manual follow-up gap.",
                      "missing_info": ["Current review workflow"]})
    ok, errors, output = validate_market_scout_output(raw)
    assert ok and not errors
    review = codex_review_market_scout(task, output)
    assert review["grounding"] == "PASS"
    assert review["commercial_decision"] == "NOT_PERFORMED"
    assert review["outreach_approved"] is False and review["payment_authorized"] is False
    retry = compile_single_retry(task, ["missing_info must be array max 2"])
    assert "corrected JSON only" in retry and "Do not add facts" in retry


def test_market_scout_handler_opts_into_json_mode_and_one_bounded_correction():
    handler = MarketScoutLocalHandler()
    assert handler.json_mode is True
    record = {"task_id": "TASK_SCOUT", "retry_count": 0,
              "action_params": {"prospect": {"prospect_id": "P1", "facts": ["fact"]}}}
    assert "Do not browse" in handler.build_prompt(record)
    failed = handler.verify(record, '{"problem":"x"}')
    assert failed.passed is False and failed.is_logic_error is True
    record["retry_count"] = 1
    correction = handler.build_prompt(record)
    assert "previous output failed deterministic validation" in correction
    assert "Do not add facts" in correction


def test_contract_examples_validate():
    root = Path(__file__).resolve().parents[2]; contracts = root / "contracts"
    now = "2026-10-05T00:00:00+00:00"
    examples = {
        "offer-v1.schema.json": {**offer(), "created_at": now, "updated_at": now},
        "lead-v1.schema.json": {**lead(), "status": "DISCOVERED", "outreach_approval": {},
                                "delivery_task_id": None,
                                "created_at": now, "updated_at": now},
        "payment-v1.schema.json": {"payment_id": "PAY_001", "offer_id": "OFFER_REVIEW_KIT_1",
            "lead_id": "LEAD_001", "amount": 25, "currency": "EUR", "method": "REVOLUT",
            "status": "PENDING", "external_reference": None, "observed_at": now,
            "provenance": provenance(), "money_movement_capability": False},
        "revenue-v1.schema.json": {"revenue_id": "REV_001", "payment_id": "PAY_001",
            "amount": 25, "currency": "EUR", "cost": 5, "gross_margin": 20,
            "offer_id": "OFFER_REVIEW_KIT_1", "lead_id": "LEAD_001", "payment_method": "REVOLUT",
            "payment_status": "PAID", "time_spent": "45m", "acquisition_source": "user supplied",
            "recorded_at": now, "provenance": provenance()}}
    for filename, example in examples.items():
        schema = json.loads((contracts / filename).read_text(encoding="utf-8"))
        assert validate(example, schema) == [], filename
