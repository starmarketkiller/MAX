import json
import sys
from datetime import datetime, timezone

import pytest

from funding_v1.first_revenue import FirstRevenueStore
from funding_v1.revenue_agent import (
    RevenueAgentCoordinator, RevenueFollowUpPlanner, compute_revenue_metrics,
    draft_fingerprint, verify_revenue_output,
)
from orchestrator_v1.core.ledger import EventLedger
from orchestrator_v1.core.orchestrator import Orchestrator
from orchestrator_v1.nxs_schema_validator import validate


def provenance():
    return {"source": "pytest", "confidence": "VERIFIED", "reference": "fixture"}


def build_store(tmp_path):
    ledger = EventLedger(tmp_path / "revenue-ledger.jsonl")
    store = FirstRevenueStore(tmp_path / "revenue.json", ledger=ledger)
    store.register_opportunity({
        "opportunity_id": "OPP_1", "source": "provided", "evidence": ["Local service"],
        "target_customer_type": "local business", "problem": "Manual follow-up",
        "possible_solution": "Review kit", "estimated_value": {"amount": 25, "currency": "EUR"},
        "confidence": "LOW", "next_action": "qualify", "provenance": provenance()})
    store.create_offer({
        "offer_id": "OFFER_1", "opportunity_id": "OPP_1", "problem": "Manual follow-up",
        "deliverable": "Configured review page", "price": {"amount": 25, "currency": "EUR", "reviewed": True},
        "delivery_time": "2 days", "included": ["setup"], "excluded": ["automation"],
        "status": "REVIEWED", "provenance": provenance()})
    store.create_lead({
        "lead_id": "LEAD_1", "opportunity_id": "OPP_1", "offer_id": "OFFER_1",
        "display_name": "Prospect", "customer_type": "local business",
        "source": "provided", "provenance": provenance()})
    return store, ledger


def context(store):
    state = store.snapshot()
    return {"lead": state["leads"][0], "offer": state["offers"][0],
            "opportunity": state["opportunities"][0],
            "prospect_facts": ["Prospect is a local business", "Manual follow-up is visible"]}


def test_grounded_qualification_and_invented_facts_rejected(tmp_path):
    ctx = context(build_store(tmp_path)[0])
    good = {"decision": "FIT", "fit_score": 70,
            "evidence": ["Prospect is a local business"], "reason": "Grounded fit.",
            "missing_info": ["Current workflow"]}
    assert verify_revenue_output("LEAD_QUALIFICATION", good, ctx) == (True, [])
    bad = {**good, "evidence": ["Prospect has 10 employees"]}
    ok, errors = verify_revenue_output("LEAD_QUALIFICATION", bad, ctx)
    assert not ok and "invented or ungrounded evidence" in errors

    fact_context = {"prospect_facts": ["Example is a local business"],
                    "evidence_records": [{"evidence_id": "E1",
                                          "text": "Example is a local business"}]}
    invented = {"facts": [{"claim": "Example has 10 employees", "evidence": "E1"}],
                "missing_info": []}
    ok, errors = verify_revenue_output("PROSPECT_FACT_EXTRACTION", invented, fact_context)
    assert not ok and "facts require grounded claim/evidence pairs" in errors


def test_invalid_lifecycle_and_unapproved_price_are_rejected(tmp_path):
    store, _ = build_store(tmp_path); ctx = context(store)
    inbound = {"classification": "INTERESTED", "evidence_quotes": ["Manual follow-up"],
               "recommended_status": "INTERESTED"}
    ok, errors = verify_revenue_output("INBOUND_CLASSIFICATION", inbound, ctx)
    assert not ok and "invalid lifecycle proposal" in errors
    ctx["offer"]["price"]["reviewed"] = False
    draft = {"subject": "Review kit", "body": "Manual follow-up", "evidence_refs": ["Manual follow-up"],
             "price_mentions": [{"amount": 25, "currency": "EUR"}], "promises": []}
    ok, errors = verify_revenue_output("OUTREACH_DRAFT", draft, ctx)
    assert not ok and "draft contains unapproved or changed price" in errors


def test_manual_send_requires_fresh_fingerprint_and_observed_receipt(tmp_path):
    store, _ = build_store(tmp_path)
    store.transition_lead("LEAD_1", "QUALIFIED")
    store.transition_lead("LEAD_1", "CONTACT_READY")
    fingerprint = draft_fingerprint("Subject", "Body")
    with pytest.raises(PermissionError, match="fingerprint mismatch"):
        store.record_manual_send("LEAD_1", approved_fingerprint="sha256:stale",
                                 draft_fingerprint=fingerprint, approved_by="max",
                                 receipt_reference="gmail-manual-1")
    store.record_manual_send("LEAD_1", approved_fingerprint=fingerprint,
                             draft_fingerprint=fingerprint, approved_by="max",
                             receipt_reference="gmail-manual-1")
    lead = store.snapshot()["leads"][0]
    assert lead["status"] == "CONTACTED"
    assert lead["outreach_receipt"]["mode"] == "MANUAL_SEND_WITH_RECORDED_APPROVAL"


def test_followup_requires_verified_outreach_and_reply_cancels_it(tmp_path):
    store, _ = build_store(tmp_path); planner = RevenueFollowUpPlanner()
    invalid_draft = {"subject": "Follow up", "body": "Manual follow-up",
                     "evidence_refs": ["Manual follow-up"]}
    ok, errors = verify_revenue_output("FOLLOW_UP_DRAFT", invalid_draft, context(store))
    assert not ok and "follow-up requires verified outreach" in errors
    assert planner.propose(store.snapshot()["leads"][0]) is None
    store.transition_lead("LEAD_1", "QUALIFIED"); store.transition_lead("LEAD_1", "CONTACT_READY")
    fp = draft_fingerprint("S", "B")
    store.record_manual_send("LEAD_1", approved_fingerprint=fp, draft_fingerprint=fp,
                             approved_by="max", receipt_reference="gmail-1")
    proposal = planner.propose(store.snapshot()["leads"][0])
    assert proposal["proposal_only"] is True and proposal["required_approval"] == "EXPLICIT_USER_APPROVAL"
    contacted_context = context(store)
    assert verify_revenue_output("FOLLOW_UP_DRAFT", invalid_draft, contacted_context) == (True, [])
    inbound = {"classification": "REPLIED", "evidence_quotes": ["Manual follow-up"],
               "recommended_status": "REPLIED"}
    assert verify_revenue_output("INBOUND_CLASSIFICATION", inbound, contacted_context) == (True, [])
    store.transition_lead("LEAD_1", "REPLIED")
    assert planner.propose(store.snapshot()["leads"][0]) is None


def test_local_execution_uses_orchestrator_and_produces_proposal(tmp_path, monkeypatch):
    store, _ = build_store(tmp_path)
    orch = Orchestrator(queue_path=str(tmp_path / "queue.json"), ledger_path=str(tmp_path / "ledger.jsonl"))
    coordinator = RevenueAgentCoordinator(store, orch)
    response = {"decision": "FIT", "fit_score": 70,
                "evidence": ["Prospect is a local business"], "reason": "Grounded fit.",
                "missing_info": []}
    orchestrator_module = sys.modules[Orchestrator.__module__]
    monkeypatch.setattr(orchestrator_module.ollama_worker, "call_local_model",
                        lambda *a, **k: {"success": True, "response_text": json.dumps(response),
                                         "model": "ministral-3:3b", "wall_seconds": 0.1})
    task_id = coordinator.submit("LEAD_QUALIFICATION", context=context(store),
                                 references={"lead_id": "LEAD_1"})
    record = orch.process_task(task_id)
    assert record["state"] == "COMPLETED"
    assert record["executor"] == "LOCAL_FAST_MINISTRAL3B"
    proposal = coordinator.proposal(task_id, response, recommended_action="REVIEW_OUTREACH_DRAFT",
                                    required_approval="REVIEW_REQUIRED", lead_id="LEAD_1",
                                    opportunity_id="OPP_1")
    assert proposal["proposal_only"] is True and proposal["verifier_status"] == "PASS"
    schema = json.loads((__import__("pathlib").Path(__file__).resolve().parents[2] /
                         "contracts/next-action-proposal-v1.schema.json").read_text())
    assert validate(proposal, schema) == []


def test_second_verifier_failure_escalates_without_premium(tmp_path, monkeypatch):
    store, _ = build_store(tmp_path)
    orch = Orchestrator(queue_path=str(tmp_path / "queue.json"), ledger_path=str(tmp_path / "ledger.jsonl"))
    coordinator = RevenueAgentCoordinator(store, orch)
    calls = []
    def invalid(*args, **kwargs):
        calls.append(1)
        return {"success": True, "response_text": '{"invalid":true}',
                "model": "ministral-3:3b", "wall_seconds": 0.1}
    orchestrator_module = sys.modules[Orchestrator.__module__]
    monkeypatch.setattr(orchestrator_module.ollama_worker, "call_local_model", invalid)
    task_id = coordinator.submit("LEAD_QUALIFICATION", context=context(store), references={})
    record = orch.process_task(task_id)
    assert len(calls) == 2
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["manifest"]["premium_allowed"] is False
    assert record["escalation"]["target"] == "TIER3_CLAUDE"
    assert all(event["event_type"] != "PROVIDER_CALL_COMPLETED" for event in orch.ledger.read_all())


def test_fast_rejection_is_corrected_once_by_strong_local(tmp_path, monkeypatch):
    store, _ = build_store(tmp_path)
    orch = Orchestrator(queue_path=str(tmp_path / "queue.json"),
                        ledger_path=str(tmp_path / "ledger.jsonl"))
    coordinator = RevenueAgentCoordinator(store, orch)
    valid = {"decision": "FIT", "fit_score": 70,
             "evidence": ["Prospect is a local business"],
             "reason": "Grounded fit.", "missing_info": []}
    responses = ['{"invalid":true}', json.dumps(valid)]
    module = sys.modules[Orchestrator.__module__]
    monkeypatch.setattr(module.ollama_worker, "call_local_model", lambda *a, **k: {
        "success": True, "response_text": responses.pop(0),
        "model": "ministral-3:3b", "wall_seconds": 0.1})
    task_id = coordinator.submit("LEAD_QUALIFICATION", context=context(store), references={})
    record = orch.process_task(task_id)
    assert record["state"] == "COMPLETED"
    assert record["executor"] == "LOCAL_STRONG_MINISTRAL3B"
    assert record["retry_count"] == 1
    events = orch.ledger.read_for_task(task_id)
    assert sum(event["event_type"] == "TEST_FAILED" for event in events) == 1
    assert any(event["event_type"] == "RETRY_STARTED" and
               event["payload"].get("escalation") == "LOCAL_FAST->LOCAL_STRONG"
               for event in events)


def test_metrics_separate_attention_from_approval_latency(tmp_path):
    store, ledger = build_store(tmp_path)
    now = datetime.now(timezone.utc).isoformat()
    store.record_attention({"experiment_id": "EXP_1", "intervention_type": "APPROVAL",
                            "active_decision_seconds": 90, "approval_latency_seconds": 7200,
                            "recorded_at": now, "provenance": provenance()})
    store.record_attention({"experiment_id": "EXP_1", "intervention_type": "REVIEW",
                            "active_decision_seconds": 30, "approval_latency_seconds": 60,
                            "recorded_at": now, "provenance": provenance()})
    operational_events = ledger.read_all() + [
        {"event_type": "RETRY_STARTED"}, {"event_type": "TEST_FAILED"},
        {"event_type": "ESCALATION_REQUIRED"},
    ]
    metrics = compute_revenue_metrics(store.snapshot(), operational_events)
    assert metrics["human_intervention_count"] == 2
    assert metrics["estimated_active_decision_seconds"] == 120
    assert metrics["human_minutes_per_revenue_experiment"] == 2
    assert metrics["approval_latency_seconds_average"] == 3630
    assert metrics["ministral_retry_count"] == 1
    assert metrics["ministral_failure_count"] == 1
    assert metrics["escalation_count"] == 1


def test_revenue_agent_has_no_email_or_payment_execution_capability():
    from funding_v1 import revenue_agent
    source = __import__("inspect").getsource(revenue_agent)
    assert "send_message(" not in source and "create_draft(" not in source
    assert "record_payment(" not in source and "record_revenue(" not in source


def test_end_to_end_proposal_manual_send_and_reply_classification(tmp_path):
    store, _ = build_store(tmp_path)
    orch = Orchestrator(queue_path=str(tmp_path / "queue.json"), ledger_path=str(tmp_path / "ledger.jsonl"))
    coordinator = RevenueAgentCoordinator(store, orch)
    ctx = context(store)
    qualification = {"decision": "FIT", "fit_score": 70,
                     "evidence": ["Prospect is a local business"],
                     "reason": "Grounded fit.", "missing_info": []}
    task_id = coordinator.submit("LEAD_QUALIFICATION", context=ctx,
                                 references={"lead_id": "LEAD_1"})
    proposal = coordinator.proposal(
        task_id, qualification, recommended_action="PREPARE_OUTREACH_DRAFT",
        required_approval="REVIEW_REQUIRED", lead_id="LEAD_1", opportunity_id="OPP_1")
    assert proposal["verifier_status"] == "PASS"
    store.transition_lead("LEAD_1", "QUALIFIED")
    store.transition_lead("LEAD_1", "CONTACT_READY")
    draft = {"subject": "Review kit", "body": "Manual follow-up",
             "evidence_refs": ["Manual follow-up"], "price_mentions": [], "promises": []}
    assert verify_revenue_output("OUTREACH_DRAFT", draft, context(store)) == (True, [])
    fingerprint = draft_fingerprint(draft["subject"], draft["body"])
    store.record_manual_send("LEAD_1", approved_fingerprint=fingerprint,
                             draft_fingerprint=fingerprint, approved_by="max",
                             receipt_reference="gmail-observed-001")
    inbound = {"classification": "REPLIED", "evidence_quotes": ["Manual follow-up"],
               "recommended_status": "REPLIED"}
    assert verify_revenue_output("INBOUND_CLASSIFICATION", inbound, context(store)) == (True, [])
    store.transition_lead("LEAD_1", "REPLIED")
    assert store.snapshot()["leads"][0]["status"] == "REPLIED"


@pytest.mark.parametrize(("task_type", "output"), [
    ("PROSPECT_FACT_EXTRACTION", {"facts": [{"claim": "Local business",
                                              "evidence": "Prospect is a local business"}],
                                    "missing_info": []}),
    ("LEAD_QUALIFICATION", {"decision": "FIT", "fit_score": 70,
                             "evidence": ["Prospect is a local business"],
                             "reason": "Grounded.", "missing_info": []}),
    ("OFFER_FIT_ANALYSIS", {"fit": "FIT", "matched_problem": "Manual follow-up",
                            "evidence": ["Manual follow-up"], "conflicts": []}),
    ("OUTREACH_DRAFT", {"subject": "Review kit", "body": "Manual follow-up",
                        "evidence_refs": ["Manual follow-up"], "price_mentions": [],
                        "promises": []}),
    ("PIPELINE_SUMMARY", {"summary": "No actions executed", "blockers": [],
                          "next_actions": []}),
    ("REVENUE_EXPERIMENT_SUMMARY", {"summary": "No revenue observed",
                                    "observed_metrics": {}, "limitations": []}),
])
def test_each_non_stateful_task_contract_has_a_passing_fixture(tmp_path, task_type, output):
    assert verify_revenue_output(task_type, output, context(build_store(tmp_path)[0])) == (True, [])
