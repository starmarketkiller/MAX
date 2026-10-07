import json
from datetime import date
from pathlib import Path

import pytest

from business_units.ai_fashion_agency import pipeline, social, store_integration
from business_units.ai_fashion_agency.capability_scout import scout, scout_all
from business_units.ai_fashion_agency.content_engine import brief_card, create_content_package
from business_units.ai_fashion_agency.events import AGENCY_EVENT_TYPES, ledger_sink
from business_units.ai_fashion_agency.kpis import UNAVAILABLE, agency_kpis
from business_units.ai_fashion_agency.policy import ApprovalRequired, require_approval
from business_units.ai_fashion_agency.projection import agency_answer, agency_state
from business_units.ai_fashion_agency.scouting import ingest_scout_result
from business_units.ai_fashion_agency.store import AgencyStore
from business_units.revenue import agency_revenue_projection
from orchestrator_v1.core.ledger import EventLedger
from orchestrator_v1.nxs_schema_validator import validate

ROOT = Path(__file__).resolve().parents[2]
TODAY = date(2026, 10, 7)


def schema(name):
    return json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))


def scout_item(kind="FASHION_ITEM_SCOUT", title="Suede jacket", **extra):
    return {"kind": kind, "title": title, "source": "newengen.com",
            "url": "https://newengen.com/insights/october-tiktok-trends/",
            "observed_at": "2026-10-07T20:00:00+00:00", "collector": "SUPPLIED_SESSION_TOOL",
            "confidence": 0.4, "category": "outerwear",
            "evidence": [{"evidence_id": "E1", "quote": "suede jacket with olive cargo pants"}],
            **extra}


@pytest.fixture
def events():
    return []


@pytest.fixture
def store(tmp_path, events):
    return AgencyStore(tmp_path / "agency.json", event_sink=events.append)


def assigned_brief(store, **kw):
    args = {"title": "Fan transition lookbook", "content_category": "fashion",
            "hook": "Four fall looks, one fan", "script": "overhead flat-lay swaps",
            "caption": "Which look? #AIcreator", "cta": "Comment 1-4"}
    args.update(kw)
    brief = pipeline.build_content_brief(store, **args)
    pipeline.assign_model(store, brief["brief_id"], model_id="MDL_LUXE_ELENA", actor="t")
    return store.get("briefs", brief["brief_id"])


def generated_package(store):
    brief = assigned_brief(store)
    pack = pipeline.build_generation_pack(store, brief["brief_id"], today=TODAY)
    pipeline.approve_generation_pack(store, pack["pack_id"], approved_by="user",
                                     expected_credits=pack["quoted_credits"])
    pipeline.record_generation_result(store, pack["pack_id"], "S1_CHARACTER_SHEET",
                                      credits_spent=2.25, job_id="JOB1")
    store.upsert("briefs", {"brief_id": brief["brief_id"], "status": "GENERATED"})
    return create_content_package(store, brief["brief_id"], media_refs=["hf://JOB1"],
                                  review={"verdict": "APPROVE", "issues": [], "evidence": ["E1"]})


def test_models_have_account_slots_and_seed_packs_without_invented_handles(store):
    models = {m["model_id"]: m for m in store.snapshot()["models"]}
    for model in models.values():
        assert {a["platform"] for a in model["social_accounts"]} == {"tiktok", "instagram",
                                                                     "youtube_shorts"}
        assert all(a["status"] == "NOT_CREATED" and a["handle"] is None
                   for a in model["social_accounts"])
    for mid in ("MDL_LUXE_ELENA", "MDL_STREET_NOVA"):
        pack = models[mid]["seed_pack"]
        assert len(pack["content_archetypes"]) == 3 and len(pack["viral_adaptations"]) == 3
        assert len(pack["product_placement_formats"]) == 2
        assert models[mid]["prompt_seed"] == pack["prompt_seed"]
        assert models[mid]["last_quote"]["credits"] == 2.25


def test_v1_registry_file_migrates_on_restart(tmp_path):
    path = tmp_path / "agency.json"
    AgencyStore(path)
    raw = json.loads(path.read_text())
    for key in ("scout_results", "social_posts", "content_packages", "event_outbox"):
        raw.pop(key)
    for model in raw["models"]:
        model["social_accounts"] = []
    path.write_text(json.dumps(raw))
    restored = AgencyStore(path).snapshot()
    assert restored["social_posts"] == [] and restored["scout_results"] == []
    assert all(len(m["social_accounts"]) == 3 for m in restored["models"])


def test_scout_ingest_validates_provenance_dedupes_and_routes(store, events):
    with pytest.raises(ValueError, match="url"):
        ingest_scout_result(store, scout_item(url="not-a-url"))
    with pytest.raises(ValueError, match="collector"):
        ingest_scout_result(store, scout_item(collector="SEARXNG"))
    record, created = ingest_scout_result(store, scout_item())
    again, created_again = ingest_scout_result(store, scout_item(title="SUEDE  jacket!"))
    assert created and not created_again
    assert again["scout_result_id"] == record["scout_result_id"] and len(again["sightings"]) == 2
    assert len(store.snapshot()["products"]) == 1
    assert validate(record, schema("agency-scout-result-v1.schema.json")) == []
    trend, _ = ingest_scout_result(store, scout_item(kind="VIRAL_FORMAT_SCOUT",
                                                     title="Fan Transition"))
    assert store.get("inputs", trend["input_id"])["workflow"] == "VIRAL_ADAPTER"
    assert [e["event_type"] for e in events] == ["AGENCY_PRODUCT_FOUND", "AGENCY_TREND_FOUND"]


def test_real_store_pipeline_blocks_until_listing_approved(store, events):
    record, _ = ingest_scout_result(store, scout_item())
    pid = record["product_id"]
    product = store_integration.evaluate_product(store, pid)
    assert product["status"] == "EVALUATING" and product["blocked_reasons"]
    assert events[-1]["event_type"] == "AGENCY_STORE_BLOCKED"
    store.upsert("products", {"product_id": pid, "supplier": "S1", "unit_cost_eur": 30.0,
                              "target_price_eur": 89.0})
    assert store_integration.evaluate_product(store, pid)["status"] == "STORE_PENDING"
    with pytest.raises(ValueError, match="https"):
        store_integration.propose_listing(store, pid, {"kind": "EXTERNAL_STORE_LINK",
                                                       "url": "http://x"})
    with pytest.raises(ValueError, match="program"):
        store_integration.propose_listing(store, pid, {"kind": "AFFILIATE_LINK",
                                                       "url": "https://a.example/p"})
    down = store_integration.propose_listing(
        store, pid, {"kind": "EXTERNAL_STORE_LINK", "url": "https://shop.example/suede"},
        fetcher=lambda url: {"status": 404})
    assert down["availability"]["available"] is False
    with pytest.raises(ValueError, match="unreachable"):
        store_integration.approve_listing(store, pid, approved_by="user")
    candidate = store_integration.propose_listing(
        store, pid, {"kind": "EXTERNAL_STORE_LINK", "url": "https://shop.example/suede"})
    assert candidate["availability"]["status"] == "UNVERIFIED_NEEDS_HUMAN_CHECK"
    assert agency_state(store)["approvals"][0]["kind"] == "STORE_LISTING"
    blocked = pipeline.build_content_brief(store, title="Suede try-on", content_category="fashion",
                                           hook="Suede season", script="s", caption="#ad",
                                           product_id=pid)
    assert blocked["status"] == "REJECTED" and blocked["store_gate_status"] == "BLOCKED"
    with pytest.raises(ApprovalRequired):
        store_integration.approve_listing(store, pid, approved_by="")
    ready = store_integration.approve_listing(store, pid, approved_by="user")
    assert ready["status"] == "STORE_READY" and store_integration.campaign_eligible(ready)
    assert events[-1]["event_type"] == "AGENCY_STORE_READY"


def test_brief_card_and_generation_pack_v2_fields(store, events):
    brief = assigned_brief(store)
    pack = pipeline.build_generation_pack(store, brief["brief_id"], today=TODAY)
    card = brief_card(store, brief["brief_id"])
    assert card["model"] == "Elena" and card["store_gate_status"] == "NOT_COMMERCIAL"
    assert card["generation_cost_estimate"]["quoted_credits"] == 2.25
    assert card["approval_status"] == "WAITING_APPROVAL" and card["platform"] == "tiktok"
    assert {"AGENCY_APPROVAL_REQUIRED", "AGENCY_CASTING_REQUIRED"} <= {e["event_type"] for e in events}
    assert pack["credits_spent"] == 0
    assert agency_state(store)["credits_spent"] == 0


def test_content_package_social_draft_and_publish_is_disabled(store, events):
    package = generated_package(store)
    assert package["state"] == "READY"
    assert validate(package, schema("agency-content-package-v1.schema.json")) == []
    post = social.create_post_draft(store, package["package_id"])
    assert post["state"] == "DRAFT" and post["blockers"]  # account NOT_CREATED
    assert validate(post, schema("agency-social-post-v1.schema.json")) == []
    social.transition_post(store, post["post_id"], "READY_FOR_REVIEW", actor="agency")
    with pytest.raises(ApprovalRequired):
        social.transition_post(store, post["post_id"], "APPROVED", actor="agency")
    social.transition_post(store, post["post_id"], "APPROVED", actor="user", approved_by="user")
    with pytest.raises(ValueError, match="NOT_CREATED"):
        social.transition_post(store, post["post_id"], "SCHEDULED", actor="user",
                               planned_at="2026-10-10T18:00:00+00:00")
    # A human creates the account; scheduling stays an internal dry-run plan.
    model = store.get("models", post["model_id"])
    accounts = [{**a, "status": "ACTIVE", "handle": "@human_created"} if a["platform"] == "tiktok"
                else a for a in model["social_accounts"]]
    store.upsert("models", {"model_id": model["model_id"], "social_accounts": accounts})
    store.upsert("social_posts", {"post_id": post["post_id"], "blockers": []})
    scheduled = social.transition_post(store, post["post_id"], "SCHEDULED", actor="user",
                                       planned_at="2026-10-10T18:00:00+00:00")
    assert scheduled["adapter_payload"]["dry_run"] is True
    with pytest.raises(ApprovalRequired, match="disabled"):
        social.transition_post(store, post["post_id"], "PUBLISHED", actor="user",
                               approved_by="user")
    assert agency_state(store)["published"] == 0
    assert "AGENCY_SOCIAL_SCHEDULED" in {e["event_type"] for e in events}


def test_policy_is_fail_closed_and_irreversible_actions_disabled():
    assert require_approval("SCOUT", None)["mode"] == "AUTONOMOUS"
    for action in ("SPEND_CREDITS", "PUT_PRODUCT_ONLINE", "SCHEDULE_POST", "CREATE_SOCIAL_ACCOUNT"):
        with pytest.raises(ApprovalRequired):
            require_approval(action, None)
        assert require_approval(action, "user")["mode"] == "APPROVED"
    for action in ("PUBLISH", "SPONSOR", "CONTACT_BRAND", "ACCEPT_AGREEMENT", "MAKE_PAYMENT"):
        with pytest.raises(ApprovalRequired, match="disabled"):
            require_approval(action, "user")
    with pytest.raises(ApprovalRequired, match="fail-closed"):
        require_approval("SOMETHING_NEW", "user")


def test_cost_tracking_alert_and_revenue_projection_v2(store, events):
    for i in range(9):
        pipeline.record_cost(store, "generation_credits", credits=2.5, idempotency_key=f"c{i}")
    assert events[-1]["event_type"] == "AGENCY_COST_ALERT"
    ready = store_integration
    record, _ = ingest_scout_result(store, scout_item(supplier="S", unit_cost_eur=30.0,
                                                      target_price_eur=89.0))
    pid = record["product_id"]
    ready.evaluate_product(store, pid)
    ready.propose_listing(store, pid, {"kind": "AFFILIATE_LINK", "program": "P",
                                       "url": "https://aff.example/p"})
    ready.approve_listing(store, pid, approved_by="user")
    event = pipeline.record_revenue_event(
        store, stream="affiliate", amount_eur=12.0, costs_eur=2.0, model_id="MDL_LUXE_ELENA",
        campaign_id="CMP_1", product_id=pid, content_id="BRF_1", channel="tiktok",
        external_reference="aff-order-1", disclosed=True, source="affiliate_dashboard",
        idempotency_key="r1")
    assert event["net_revenue_eur"] == 10.0 and event["business_unit_id"] == "AI_FASHION_AGENCY"
    assert validate(event, schema("agency-revenue-event-v1.schema.json")) == []
    projection = agency_revenue_projection(store)
    assert validate(projection, schema("business-unit-revenue-v1.schema.json")) == []
    assert projection["gross_revenue_eur"] == 12.0 and projection["costs_eur"] == 2.0
    assert projection["top_product"] == pid and projection["credits_valued_in_eur"] is False
    assert events[-1]["event_type"] == "AGENCY_REVENUE_EVENT"


def test_kpis_report_unavailable_instead_of_inventing(store):
    kpis = agency_kpis(store.snapshot())
    assert kpis["views"] == UNAVAILABLE and kpis["CTR"] == UNAVAILABLE
    assert kpis["ROI"] == UNAVAILABLE and kpis["gross_revenue"] == 0
    assert agency_state(store)["followers"] == UNAVAILABLE


def test_jarvis_answers_executive_questions(store):
    brief = assigned_brief(store)
    pipeline.build_generation_pack(store, brief["brief_id"], today=TODAY)
    ingest_scout_result(store, scout_item())
    answers = {q: agency_answer(q, store)[0] for q in (
        "cosa devo approvare per l'agenzia?", "quanto sta guadagnando l'agenzia?",
        "abbiamo prodotti pronti?", "quali modelle hanno account?",
        "quale modella cresce di più?", "quali modelle stanno lavorando?",
        "quale campagna è più promettente?", "come va l'agenzia?")}
    assert "generazione Higgsfield per Elena (2.25 crediti)" in answers["cosa devo approvare per l'agenzia?"]
    assert "Nessun ricavo osservato" in answers["quanto sta guadagnando l'agenzia?"]
    assert "0 store-ready" in answers["abbiamo prodotti pronti?"]
    assert "Suede jacket" in answers["abbiamo prodotti pronti?"]
    assert "account attivi 0/15" in answers["quali modelle hanno account?"]
    assert "UNAVAILABLE" in answers["quale modella cresce di più?"]
    assert "Elena" in answers["quali modelle stanno lavorando?"]
    assert "nessuna campagna commerciale" in answers["quale campagna è più promettente?"]
    assert answers["come va l'agenzia?"].startswith("AI Fashion Agency:")
    state = agency_state(store)
    assert validate(state, schema("ai-fashion-agency-state-v1.schema.json")) == []


def test_jarvis_service_routes_and_lists_agency_approvals(tmp_path):
    from jarvis_v1.local_operations import OperationsProjection
    from jarvis_v1.service import JarvisService, classify

    service = JarvisService(queue_path=tmp_path / "q.json", ledger_path=tmp_path / "l.jsonl",
                            conversation_path=tmp_path / "c.json")
    agency = AgencyStore(tmp_path / "a.json")
    brief = assigned_brief(agency)
    pipeline.build_generation_pack(agency, brief["brief_id"], today=TODAY)
    service.set_operations_projection(OperationsProjection(
        revenue_store=None, revenue_runner=None, revenue_scheduler=None,
        queue=service.queue, agency_store=agency))
    msg = {"message_id": "m", "user_id": "u", "channel": "TELEGRAM", "conversation_id": "c",
           "timestamp": "2026-10-07T00:00:00+00:00", "input_type": "TEXT", "attachments": [],
           "reply_to": None, "request_class": "UNKNOWN", "priority": "NORMAL", "metadata": {}}
    assert classify("abbiamo prodotti pronti?") == "COMMAND"
    products = service.handle({**msg, "text": "abbiamo prodotti pronti?"})
    assert products["summary"].startswith("Agenzia: 0 prodotti trovati")
    listing = service.handle({**msg, "text": "quali devo approvare"})
    assert "AI Fashion Agency: 1 decisioni in attesa" in listing["summary"]
    assert listing["details"]["business_unit_approvals"][0]["kind"] == "GENERATION_PACK"
    units = service.operations_projection.business_units()
    assert validate(units[0], schema("business-unit-state-v1.schema.json")) == []


def test_events_reach_canonical_ledger_and_jarvis_only_when_attention(tmp_path):
    ledger = EventLedger(path=str(tmp_path / "ledger.jsonl"))
    pushed = []
    store = AgencyStore(tmp_path / "a.json", event_sink=ledger_sink(ledger, pushed.append))
    ingest_scout_result(store, scout_item(kind="TREND_SCOUT", title="Fan Transition"))
    brief = assigned_brief(store)
    pipeline.build_generation_pack(store, brief["brief_id"], today=TODAY)
    logged = [e["event_type"] for e in ledger.read_all()]
    assert "AGENCY_TREND_FOUND" in logged and "AGENCY_APPROVAL_REQUIRED" in logged
    assert {e["event_type"] for e in pushed} <= {"AGENCY_APPROVAL_REQUIRED",
                                                 "AGENCY_CASTING_REQUIRED"}
    assert "AGENCY_TREND_FOUND" not in {e["event_type"] for e in pushed}
    event_schema = schema("agency-event-v1.schema.json")
    assert all(validate(e, event_schema) == [] for e in store.snapshot()["event_outbox"])
    nexus_enum = schema("nexus-event.schema.json")["properties"]["event_type"]["enum"]
    assert set(AGENCY_EVENT_TYPES) <= set(nexus_enum)


def test_capability_scout_searches_registry_first_and_installs_nothing():
    results = scout_all()
    assert {r["capability"] for r in results} == {"social_publishing", "web_scouting",
                                                  "analytics", "store_integration"}
    assert all(r["installed_now"] == [] for r in results)
    social_result = scout("social_publishing")
    assert social_result["resolution"] == "EXTERNAL_CANDIDATES"
    assert {c["candidate"]: c["stage"] for c in social_result["candidates"]}["Activepieces"] == "REJECTED"


def test_agency_keywords_do_not_hijack_task_creation():
    from jarvis_v1.service import classify
    assert classify("crea una task per analizzare la campagna marketing") == "TASK_REQUEST"
    assert classify("quale campagna è più promettente?") == "COMMAND"
    assert classify("annulla la task dell'agenzia") == "COMMAND"  # cancel handled first in command()


def test_realistic_dry_run_on_real_evidence_reaches_waiting_approval(tmp_path, monkeypatch):
    import sys
    from business_units.ai_fashion_agency.dry_run_v2 import run
    from orchestrator_v1.core.orchestrator import Orchestrator

    def unreachable(*a, **k):  # same outcome as this container: no local Ollama
        return {"success": False, "response_text": None, "error": "connection refused",
                "model": "ministral-3:3b", "wall_seconds": 0.0}
    monkeypatch.setattr(sys.modules[Orchestrator.__module__].ollama_worker,
                        "call_local_model", unreachable)
    result = run(tmp_path)
    steps = {t["step"]: t for t in result["transitions"]}
    assert steps["STORE_GATE"]["status"] == "EVALUATING"
    assert steps["COMMERCIAL_BRIEF"]["status"] == "REJECTED"
    assert steps["VIRAL_ANALYSIS"]["state"] == "ESCALATION_REQUIRED"
    assert steps["VIRAL_ANALYSIS"]["verifier_passed"] is True
    assert steps["MODEL_ASSIGNMENT"]["model_id"] in {"MDL_LUXE_ELENA", "MDL_STREET_NOVA"}
    assert steps["GENERATION_PACK"]["state"] == "WAITING_APPROVAL"
    assert result["provenance"]["sources"] == ["https://newengen.com/insights/october-tiktok-trends/"]
    assert result["guarantees"] == {"credits_spent": 0, "published_content": 0,
                                    "external_outreach": 0, "store_opened": False}
    assert "AGENCY_APPROVAL_REQUIRED" in result["ledger_event_types"]
    assert "nessuna campagna attiva" in result["jarvis_answers"]["quale campagna è più promettente?"]
