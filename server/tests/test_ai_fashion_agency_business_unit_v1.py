import json
import sys
from datetime import date
from pathlib import Path

import pytest

from business_units.ai_fashion_agency import pipeline
from business_units.ai_fashion_agency.projection import (
    agency_state, business_unit_state, jarvis_summary)
from business_units.ai_fashion_agency.simulation import run_simulation
from business_units.ai_fashion_agency.skills import (
    AGENCY_SKILLS, AgencyTaskCoordinator, verify_agency_output)
from business_units.ai_fashion_agency.store import AgencyStore
from orchestrator_v1.core.orchestrator import Orchestrator
from orchestrator_v1.nxs_schema_validator import validate

ROOT = Path(__file__).resolve().parents[2]
TODAY = date(2026, 10, 7)


def schema(name):
    return json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))


def store_ready_product(store, **overrides):
    payload = {"title": "Satin slip midi dress", "category": "dresses", "supplier": "S1",
               "unit_cost_eur": 14.0, "target_price_eur": 39.0, "trend_evidence": ["E1"]}
    payload.update(overrides)
    item = pipeline.receive_input(store, "FASHION_ITEM", payload, source="test",
                                  idempotency_key=f"p-{payload['title']}")
    product = pipeline.product_from_input(store, item)
    pipeline.transition_product(store, product["product_id"], "EVALUATING", actor="t")
    pipeline.transition_product(store, product["product_id"], "STORE_PENDING", actor="t",
                                viability=pipeline.evaluate_viability(product))
    return pipeline.transition_product(
        store, product["product_id"], "STORE_READY", actor="t",
        listing={"kind": "OWN_STORE", "url": "https://shop.example/dress"}, approved_by="user")


def brief(store, **kw):
    args = {"title": "Dress transition", "content_category": "fashion",
            "hook": "POV: hoodie to date night", "script": "beats",
            "caption": "Look 1 or 2? #ad", "cta": "Shop in bio"}
    args.update(kw)
    return pipeline.build_content_brief(store, **args)


def test_roster_is_diverse_adult_disclosed_and_schema_valid(tmp_path):
    store = AgencyStore(tmp_path / "a.json")
    models = store.snapshot()["models"]
    assert len(models) == 5 and len({m["archetype"] for m in models}) == 5
    assert all(m["status"] == "CASTING_DRAFT" for m in models)
    for model in models:
        assert validate(model, schema("agency-model-profile-v1.schema.json")) == []
        assert model["age_presentation"] == "ADULT_21_PLUS"
        assert model["ai_disclosure"]["content_label_required"] is True
    assert AgencyStore(tmp_path / "a.json").snapshot()["models"] == models  # persisted


def test_input_bus_classifies_and_is_idempotent(tmp_path):
    store = AgencyStore(tmp_path / "a.json")
    a = pipeline.receive_input(store, "TREND_VIDEO", {"source_url": "u"}, source="s",
                               idempotency_key="k1")
    b = pipeline.receive_input(store, "TREND_VIDEO", {"source_url": "u"}, source="s",
                               idempotency_key="k1")
    assert a["workflow"] == "VIRAL_ADAPTER" and len(store.snapshot()["inputs"]) == 1
    assert b["input_id"] == a["input_id"]
    assert validate(a, schema("agency-input-v1.schema.json")) == []
    with pytest.raises(ValueError):
        pipeline.receive_input(store, "RANDOM", {}, source="s", idempotency_key="k2")


def test_store_gate_blocks_commercial_content_until_store_ready(tmp_path):
    store = AgencyStore(tmp_path / "a.json")
    item = pipeline.receive_input(store, "PRODUCT", {"title": "Bag", "trend_evidence": ["E1"]},
                                  source="s", idempotency_key="bag")
    product = pipeline.product_from_input(store, item)
    blocked = brief(store, product_id=product["product_id"])
    assert blocked["status"] == "REJECTED"
    assert any("requires STORE_READY" in i for i in blocked["compliance"]["issues"])
    with pytest.raises(ValueError):  # cannot skip the lifecycle
        pipeline.transition_product(store, product["product_id"], "STORE_READY", actor="t")
    pipeline.transition_product(store, product["product_id"], "EVALUATING", actor="t")
    with pytest.raises(ValueError):  # not viable: no cost/price/supplier
        pipeline.transition_product(store, product["product_id"], "STORE_PENDING", actor="t",
                                    viability=pipeline.evaluate_viability(product))
    ready = store_ready_product(store)
    with pytest.raises(ValueError):
        pipeline.transition_product(store, ready["product_id"], "STORE_READY", actor="t")
    assert validate(ready, schema("agency-product-v1.schema.json")) == []
    ok = brief(store, product_id=ready["product_id"])
    assert ok["status"] == "DRAFT" and ok["commercial"] and ok["ad_disclosure"]


def test_store_ready_requires_listing_and_human_approval(tmp_path):
    store = AgencyStore(tmp_path / "a.json")
    item = pipeline.receive_input(store, "FASHION_ITEM", {
        "title": "Dress", "supplier": "S", "unit_cost_eur": 5, "target_price_eur": 30,
        "trend_evidence": ["E1"]}, source="s", idempotency_key="d")
    p = pipeline.product_from_input(store, item)
    pipeline.transition_product(store, p["product_id"], "EVALUATING", actor="t")
    pipeline.transition_product(store, p["product_id"], "STORE_PENDING", actor="t",
                                viability=pipeline.evaluate_viability(p))
    with pytest.raises(ValueError, match="listing"):
        pipeline.transition_product(store, p["product_id"], "STORE_READY", actor="t",
                                    listing={"kind": "OWN_STORE"}, approved_by="user")
    with pytest.raises(ValueError, match="human approval"):
        pipeline.transition_product(store, p["product_id"], "STORE_READY", actor="t",
                                    listing={"kind": "OWN_STORE", "url": "https://x"})


@pytest.mark.parametrize("override,issue", [
    ({"production_method": "OVERLAY_ON_ORIGINAL"}, "third-party footage"),
    ({"audio_source": "RIPPED_FROM_VIDEO"}, "audio"),
    ({"caption": "Guaranteed results #ad"}, "claim"),
])
def test_compliance_rejects_reposts_unlicensed_audio_and_false_claims(tmp_path, override, issue):
    store = AgencyStore(tmp_path / "a.json")
    rejected = brief(store, **override)
    assert rejected["status"] == "REJECTED"
    assert any(issue in i for i in rejected["compliance"]["issues"])


def test_model_assignment_respects_fit_category_and_status(tmp_path):
    store = AgencyStore(tmp_path / "a.json")
    product = store_ready_product(store)
    b = brief(store, product_id=product["product_id"])
    assignment = pipeline.assign_model(store, b["brief_id"], actor="t")
    assert assignment["model_id"] == "MDL_LUXE_ELENA"  # 'dresses' brand fit
    assert store.get("briefs", b["brief_id"])["status"] == "ASSIGNED"
    store.upsert("models", {"model_id": "MDL_STREET_NOVA", "status": "RETIRED"})
    humor = brief(store, title="Cat steals my headphones", content_category="humor",
                  caption="Who wins? #AIcreator")
    ranked = pipeline.score_models(humor, store.snapshot()["models"])
    assert "MDL_STREET_NOVA" not in {r["model_id"] for r in ranked}
    assert {r["model_id"] for r in ranked} <= {"MDL_ACTIVE_MAYA", "MDL_CUTE_KAI"}


def test_generation_pack_requires_quote_and_exact_approval_and_never_spends(tmp_path):
    store = AgencyStore(tmp_path / "a.json")
    product = store_ready_product(store)
    b = brief(store, product_id=product["product_id"])
    pipeline.assign_model(store, b["brief_id"], actor="t")
    pack = pipeline.build_generation_pack(store, b["brief_id"], today=TODAY)
    assert validate(pack, schema("agency-generation-pack-v1.schema.json")) == []
    assert pack["state"] == "WAITING_APPROVAL" and pack["quoted_credits"] == 2.25
    assert pack["credits_spent"] == 0 and pack["unquoted_steps"] == ["S2_VIDEO"]
    with pytest.raises(ValueError, match="re-quote"):
        pipeline.approve_generation_pack(store, pack["pack_id"], approved_by="user",
                                         expected_credits=5)
    with pytest.raises(ValueError, match="approval"):
        pipeline.approve_generation_pack(store, pack["pack_id"], approved_by="",
                                         expected_credits=2.25)
    with pytest.raises(ValueError, match="approved"):
        pipeline.record_generation_result(store, pack["pack_id"], "S1_CHARACTER_SHEET",
                                          credits_spent=2.25, job_id="J1")
    approved = pipeline.approve_generation_pack(store, pack["pack_id"], approved_by="user",
                                                expected_credits=2.25)
    assert approved["state"] == "APPROVED" and approved["credits_spent"] == 0
    with pytest.raises(ValueError, match="exceeded"):
        pipeline.record_generation_result(store, pack["pack_id"], "S1_CHARACTER_SHEET",
                                          credits_spent=3, job_id="J1")
    pipeline.record_generation_result(store, pack["pack_id"], "S1_CHARACTER_SHEET",
                                      credits_spent=2.25, job_id="J1")
    assert agency_state(store)["credits_spent"] == 2.25


def test_stale_quote_is_not_approvable(tmp_path):
    store = AgencyStore(tmp_path / "a.json")
    product = store_ready_product(store)
    b = brief(store, product_id=product["product_id"])
    pipeline.assign_model(store, b["brief_id"], actor="t")
    pack = pipeline.build_generation_pack(store, b["brief_id"], today=date(2026, 11, 30))
    assert pack["state"] == "WAITING_QUOTE" and pack["quoted_credits"] == 0


def test_revenue_attribution_requires_store_gate_disclosure_and_reference(tmp_path):
    store = AgencyStore(tmp_path / "a.json")
    product = store_ready_product(store)
    common = {"model_id": "MDL_LUXE_ELENA", "campaign_id": "CMP_1",
              "product_id": product["product_id"], "content_id": "BRF_1", "channel": "tiktok"}
    with pytest.raises(ValueError, match="disclosed"):
        pipeline.record_revenue_event(store, stream="affiliate", amount_eur=10,
                                      external_reference="ord-1", disclosed=False,
                                      idempotency_key="r0", **common)
    with pytest.raises(ValueError, match="external reference"):
        pipeline.record_revenue_event(store, stream="own_store", amount_eur=10,
                                      external_reference="", disclosed=True,
                                      idempotency_key="r0", **common)
    event = pipeline.record_revenue_event(store, stream="own_store", amount_eur=39,
                                          external_reference="order-1", disclosed=True,
                                          idempotency_key="r1", **common)
    pipeline.record_revenue_event(store, stream="own_store", amount_eur=39,
                                  external_reference="order-1", disclosed=True,
                                  idempotency_key="r1", **common)
    pipeline.record_cost(store, "store_fees", eur=4, idempotency_key="fee-1")
    assert validate(event, schema("agency-revenue-event-v1.schema.json")) == []
    state = agency_state(store)
    assert state["revenue_eur"] == 39 and state["costs_eur"] == 4 and state["profit_eur"] == 35
    assert state["top_model"] == "MDL_LUXE_ELENA" and state["top_campaign"] == "CMP_1"


def test_agency_skill_runs_through_canonical_orchestrator(tmp_path, monkeypatch):
    orch = Orchestrator(queue_path=str(tmp_path / "q.json"), ledger_path=str(tmp_path / "l.jsonl"))
    coordinator = AgencyTaskCoordinator(orch)
    bad = {**AGENCY_SKILLS["VIRAL_FORMAT_ANALYSIS"].output_example,
           "audio_strategy": "RIPPED", "evidence": ["E9"]}
    calls = []

    def model(*a, **k):
        calls.append(1)
        return {"success": True, "response_text": json.dumps(bad), "model": "m",
                "wall_seconds": 0.1}
    monkeypatch.setattr(sys.modules[Orchestrator.__module__].ollama_worker,
                        "call_local_model", model)
    ctx = {"evidence_records": [{"evidence_id": "E1", "text": "x"}]}
    task_id = coordinator.submit("VIRAL_FORMAT_ANALYSIS", context=ctx, references={})
    record = orch.process_task(task_id)
    assert len(calls) == 2 and record["state"] == "ESCALATION_REQUIRED"
    assert record["manifest"]["premium_allowed"] is False
    assert record["action_params"]["references"]["business_unit"] == "AI_FASHION_AGENCY"
    ok, errors = verify_agency_output("VIRAL_FORMAT_ANALYSIS", bad, ctx)
    assert not ok and any("audio" in e for e in errors) and any("evidence" in e for e in errors)


def test_end_to_end_simulation_reaches_waiting_approval_with_zero_spend(tmp_path):
    result = run_simulation(tmp_path)
    steps = [t[0] for t in result["trace"]]
    assert steps == ["PRODUCT_RECEIVED", "COMMERCIAL_BRIEF_BEFORE_STORE", "STORE_GATE",
                     "VIRAL_ADAPTER", "CONTENT_BRIEF", "MODEL_ASSIGNMENT", "GENERATION_PACK"]
    assert result["brief_rejected_before_store"]["status"] == "REJECTED"
    assert result["product"]["status"] == "STORE_READY"
    assert result["generation_pack"]["state"] == "WAITING_APPROVAL"
    assert result["brief"]["viral_reference"]["media_retained"] is False
    assert result["credits_spent"] == 0
    state = result["agency_state"]
    assert validate(state, schema("ai-fashion-agency-state-v1.schema.json")) == []
    assert validate(result["business_unit_state"], schema("business-unit-state-v1.schema.json")) == []
    assert state["campaigns_active"] == 1 and state["store_ready"] == 1
    assert state["awaiting_approval"] == 1
    assert result["business_unit_state"]["decision"]["status"] == "HUMAN_APPROVAL_REQUIRED"
    summary = result["jarvis_summary"]
    assert "1 campagna pronta" in summary and "1 prodotto store-ready" in summary
    assert "in attesa di approvazione" in summary and "crediti spesi 0" in summary


def test_jarvis_agency_command_reads_projection(tmp_path):
    from jarvis_v1.local_operations import OperationsProjection
    from jarvis_v1.service import classify

    store = AgencyStore(tmp_path / "a.json")
    projection = OperationsProjection(revenue_store=None, revenue_runner=None,
                                      revenue_scheduler=None, agency_store=store)
    data = projection.agency()
    assert data["models_total"] == 5 and data["summary"].startswith("AI Fashion Agency:")
    assert OperationsProjection(revenue_store=None, revenue_runner=None,
                                revenue_scheduler=None).agency() is None
    assert classify("come va l'agenzia?") == "COMMAND"
    assert classify("/agency") == "COMMAND"
    assert jarvis_summary(agency_state(store)).endswith("crediti spesi 0.")
    assert business_unit_state(store)["health"] == "NOT_STARTED"


def _message(text):
    return {"message_id": "m1", "user_id": "u1", "channel": "TELEGRAM",
            "conversation_id": "c1", "timestamp": "2026-10-07T00:00:00+00:00",
            "input_type": "TEXT", "text": text, "attachments": [], "reply_to": None,
            "request_class": "UNKNOWN", "priority": "NORMAL", "metadata": {}}


def test_jarvis_service_answers_agency_without_hijacking_other_commands(tmp_path):
    from jarvis_v1.local_operations import OperationsProjection
    from jarvis_v1.service import JarvisService

    service = JarvisService(queue_path=tmp_path / "q.json", ledger_path=tmp_path / "l.jsonl",
                            conversation_path=tmp_path / "c.json")
    service.set_operations_projection(OperationsProjection(
        revenue_store=None, revenue_runner=None, revenue_scheduler=None,
        queue=service.queue, agency_store=AgencyStore(tmp_path / "a.json")))
    for text in ("/agency", "come va l'agenzia?", "quante modelle abbiamo?"):
        response = service.handle(_message(text))
        assert response["details"]["view"] == "AI_FASHION_AGENCY_STATE", text
        assert response["details"]["models_total"] == 5
    cancel = service.handle(_message("annulla la task dell'agenzia"))
    assert (cancel.get("details") or {}).get("view") != "AI_FASHION_AGENCY_STATE"
