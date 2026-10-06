import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from funding_v1.first_revenue import FirstRevenueStore
from funding_v1.revenue_agent import RevenueAgentCoordinator
from funding_v1.revenue_automation import (
    ProspectAcquisition, RevenueAutomationRunner, RevenueResultDelivery, RevenueScheduler,
)
from funding_v1.revenue_skill_pack import REVENUE_SKILLS
from orchestrator_v1.core.orchestrator import Orchestrator
from orchestrator_v1.nxs_schema_validator import validate


ROOT = Path(__file__).resolve().parents[2]


def build(tmp_path):
    store = FirstRevenueStore(tmp_path / "revenue.json")
    orchestrator = Orchestrator(queue_path=str(tmp_path / "queue.json"),
                                ledger_path=str(tmp_path / "ledger.jsonl"))
    return store, RevenueAgentCoordinator(store, orchestrator), orchestrator


def test_skill_pack_is_complete_local_first_and_single_retry():
    assert set(REVENUE_SKILLS) == {
        "PROSPECT_FACT_EXTRACTION", "LEAD_QUALIFICATION", "OFFER_FIT_ANALYSIS",
        "OUTREACH_DRAFT", "INBOUND_CLASSIFICATION", "FOLLOW_UP_DRAFT",
        "PIPELINE_SUMMARY", "REVENUE_EXPERIMENT_SUMMARY",
    }
    assert all(skill.max_retries == 1 for skill in REVENUE_SKILLS.values())
    assert all(skill.default_executor == "LOCAL_STRONG_MINISTRAL3B"
               for skill in REVENUE_SKILLS.values())
    assert all("premium_calls" in skill.telemetry for skill in REVENUE_SKILLS.values())


def test_prospect_acquisition_preserves_provenance_and_deduplicates(tmp_path):
    store, _, _ = build(tmp_path)
    acquisition = ProspectAcquisition(store)
    source = [{"display_name": "Example", "website": "https://www.example.test/path",
               "evidence": ["Public directory lists Example"]}]
    first = acquisition.ingest(source, source="AUTHORIZED_FEED",
                               source_reference="feed://batch-1")
    second = acquisition.ingest(source, source="AUTHORIZED_FEED",
                                source_reference="feed://batch-2")
    assert len(first["accepted"]) == 1 and not first["duplicates"]
    assert len(second["duplicates"]) == 1
    prospects = store.snapshot()["prospects"]
    assert len(prospects) == 1
    assert prospects[0]["duplicate_observations"] == 1
    assert prospects[0]["provenance"]["reference"] == "feed://batch-1"

    schema = json.loads((ROOT / "contracts/prospect-v1.schema.json").read_text(encoding="utf-8"))
    assert validate(prospects[0], schema) == []


def test_acquisition_rejects_missing_evidence_and_unusable_identity(tmp_path):
    store, _, _ = build(tmp_path)
    result = ProspectAcquisition(store).ingest(
        [{"display_name": "No evidence"}, {"evidence": ["fact"]}],
        source="AUTHORIZED_FEED", source_reference="feed://bad")
    assert len(result["rejected"]) == 2
    assert store.snapshot()["prospects"] == []


def test_scheduler_is_persistent_idempotent_and_notifies_jarvis_sink(tmp_path):
    store, coordinator, orchestrator = build(tmp_path)
    acquisition = ProspectAcquisition(store)
    acquisition.ingest([{"display_name": "Example", "website": "example.test",
                         "evidence": ["Directory evidence"]}],
                       source="AUTHORIZED_FEED", source_reference="feed://1")
    notifications = []
    scheduler = RevenueScheduler(tmp_path / "scheduler.json", coordinator, store,
                                 notification_sink=notifications.append)
    first = scheduler.tick()
    second = RevenueScheduler(tmp_path / "scheduler.json", coordinator, store,
                              notification_sink=notifications.append).tick()
    assert len(first["scheduled"]) == 1
    assert second["scheduled"] == []
    task = orchestrator.queue.get(first["scheduled"][0]["task_id"])
    assert task["state"] == "QUEUED"
    assert task["action"] == RevenueAgentCoordinator.ACTION
    assert notifications[0]["type"] == "REVENUE_TASKS_SCHEDULED"


def test_scheduler_triggers_reply_and_experiment_once(tmp_path):
    store, coordinator, _ = build(tmp_path)
    store.register_opportunity({"opportunity_id": "OPP_1", "source": "test",
        "evidence": ["e"], "target_customer_type": "local", "problem": "p",
        "possible_solution": "s", "estimated_value": {}, "confidence": "LOW",
        "next_action": "n", "provenance": {"confidence": "VERIFIED"}})
    store.create_offer({"offer_id": "OFFER_1", "opportunity_id": "OPP_1", "problem": "p",
        "deliverable": "d", "price": {"amount": 10, "currency": "EUR", "reviewed": True},
        "delivery_time": "1d", "included": [], "excluded": [], "status": "REVIEWED",
        "provenance": {"confidence": "VERIFIED"}})
    store.create_lead({"lead_id": "LEAD_1", "opportunity_id": "OPP_1", "offer_id": "OFFER_1",
        "display_name": "Lead", "customer_type": "local", "source": "test",
        "provenance": {"confidence": "VERIFIED"}})
    store.transition_lead("LEAD_1", "QUALIFIED")
    store.transition_lead("LEAD_1", "CONTACT_READY")
    store.record_manual_send("LEAD_1", approved_fingerprint="fp", draft_fingerprint="fp",
                             approved_by="max", receipt_reference="receipt")
    scheduler = RevenueScheduler(tmp_path / "scheduler.json", coordinator, store)
    result = scheduler.tick(
        reply_events=[{"lead_id": "LEAD_1", "message_id": "MSG_1", "text": "Interested"}],
        experiments=[{"experiment_id": "EXP_1", "review_due": "2026-10-06"}])
    types = {item["task_type"] for item in result["scheduled"]}
    assert types == {"INBOUND_CLASSIFICATION", "REVENUE_EXPERIMENT_SUMMARY"}
    assert scheduler.tick(
        reply_events=[{"lead_id": "LEAD_1", "message_id": "MSG_1", "text": "Interested"}],
        experiments=[{"experiment_id": "EXP_1", "review_due": "2026-10-06"}]
    )["scheduled"] == []


def test_scheduler_plans_due_follow_up_once(tmp_path):
    store, coordinator, _ = build(tmp_path)
    store.register_opportunity({"opportunity_id": "OPP_1", "source": "test",
        "evidence": ["e"], "target_customer_type": "local", "problem": "p",
        "possible_solution": "s", "estimated_value": {}, "confidence": "LOW",
        "next_action": "n", "provenance": {"confidence": "VERIFIED"}})
    store.create_offer({"offer_id": "OFFER_1", "opportunity_id": "OPP_1", "problem": "p",
        "deliverable": "d", "price": {"amount": 10, "currency": "EUR", "reviewed": True},
        "delivery_time": "1d", "included": [], "excluded": [], "status": "REVIEWED",
        "provenance": {"confidence": "VERIFIED"}})
    store.create_lead({"lead_id": "LEAD_1", "opportunity_id": "OPP_1", "offer_id": "OFFER_1",
        "display_name": "Lead", "customer_type": "local", "source": "test",
        "provenance": {"confidence": "VERIFIED"}})
    store.transition_lead("LEAD_1", "QUALIFIED")
    store.transition_lead("LEAD_1", "CONTACT_READY")
    store.record_manual_send("LEAD_1", approved_fingerprint="fp", draft_fingerprint="fp",
                             approved_by="max", receipt_reference="receipt")
    lead = store.snapshot()["leads"][0]
    sent_at = datetime.fromisoformat(lead["outreach_receipt"]["recorded_at"])
    scheduler = RevenueScheduler(tmp_path / "scheduler.json", coordinator, store)
    assert scheduler.tick(now=sent_at + timedelta(days=2))["scheduled"] == []
    due = scheduler.tick(now=sent_at + timedelta(days=4))["scheduled"]
    assert [item["task_type"] for item in due] == ["FOLLOW_UP_DRAFT"]
    assert scheduler.tick(now=sent_at + timedelta(days=5))["scheduled"] == []


def test_scheduler_plans_stale_pipeline_review_without_mutating_lead(tmp_path):
    store, coordinator, _ = build(tmp_path)
    store.register_opportunity({"opportunity_id": "OPP_1", "source": "test",
        "evidence": ["e"], "target_customer_type": "local", "problem": "p",
        "possible_solution": "s", "estimated_value": {}, "confidence": "LOW",
        "next_action": "n", "provenance": {"confidence": "VERIFIED"}})
    store.create_offer({"offer_id": "OFFER_1", "opportunity_id": "OPP_1", "problem": "p",
        "deliverable": "d", "price": {"amount": 10, "currency": "EUR", "reviewed": True},
        "delivery_time": "1d", "included": [], "excluded": [], "status": "REVIEWED",
        "provenance": {"confidence": "VERIFIED"}})
    store.create_lead({"lead_id": "LEAD_1", "opportunity_id": "OPP_1", "offer_id": "OFFER_1",
        "display_name": "Lead", "customer_type": "local", "source": "test",
        "provenance": {"confidence": "VERIFIED"}})
    store.transition_lead("LEAD_1", "QUALIFIED")
    lead = store.snapshot()["leads"][0]
    updated_at = datetime.fromisoformat(lead["updated_at"])
    scheduler = RevenueScheduler(tmp_path / "scheduler.json", coordinator, store)
    planned = scheduler.tick(now=updated_at + timedelta(days=8))["scheduled"]
    assert [item["task_type"] for item in planned] == ["PIPELINE_SUMMARY"]
    assert store.snapshot()["leads"][0]["status"] == "QUALIFIED"


def test_verified_result_is_delivered_to_jarvis_sink_once(tmp_path, monkeypatch):
    import sys
    store, coordinator, orchestrator = build(tmp_path)
    response = {"decision": "FIT", "fit_score": 70, "evidence": ["E1"],
                "reason": "Grounded", "missing_info": []}
    module = sys.modules[Orchestrator.__module__]
    monkeypatch.setattr(module.ollama_worker, "call_local_model",
                        lambda *a, **k: {"success": True, "response_text": __import__("json").dumps(response),
                                         "model": "ministral-3:3b", "wall_seconds": 0.1})
    task_id = coordinator.submit("LEAD_QUALIFICATION",
                                 context={"prospect_facts": ["Fact"]}, references={"lead_id": "L1"})
    orchestrator.process_task(task_id)
    notifications = []
    delivery = RevenueResultDelivery(tmp_path / "delivery.json", orchestrator.queue,
                                     notifications.append)
    assert delivery.poll() == [task_id]
    assert delivery.poll() == []
    assert notifications[0]["response_type"] == "REVENUE_AGENT_RESULT"
    assert notifications[0]["details"]["verified_output"]["decision"] == "FIT"
    assert notifications[0]["details"]["premium_calls"] == 0


def test_background_runner_is_idempotent_and_stops_cleanly(tmp_path):
    store, coordinator, orchestrator = build(tmp_path)
    ProspectAcquisition(store).ingest(
        [{"display_name": "Example", "website": "example.test",
          "evidence": ["Directory evidence"]}],
        source="AUTHORIZED_FEED", source_reference="feed://1")
    scheduler = RevenueScheduler(tmp_path / "scheduler.json", coordinator, store)
    delivery = RevenueResultDelivery(tmp_path / "delivery.json", orchestrator.queue, lambda _: None)
    runner = RevenueAutomationRunner(scheduler, delivery, interval_seconds=60)
    first = runner.run_once()
    second = runner.run_once()
    assert len(first["scheduled"]) == 1
    assert second["scheduled"] == []
    assert runner.status()["last_error_class"] is None
    assert runner.start() is True
    assert runner.start() is False
    assert runner.stop() is True


def test_background_runner_isolates_failure_without_sensitive_details(tmp_path):
    errors = []
    class Broken:
        def tick(self):
            raise RuntimeError("secret=must-not-be-forwarded")
    runner = RevenueAutomationRunner(Broken(), None, error_sink=errors.append)
    try:
        runner.start()
        import time
        deadline = time.time() + 2
        while not errors and time.time() < deadline:
            time.sleep(0.01)
    finally:
        runner.stop()
    assert errors == [{"type": "REVENUE_AUTOMATION_DEGRADED",
                       "failure_class": "RuntimeError"}]
