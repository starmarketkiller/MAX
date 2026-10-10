import json
from datetime import date
from pathlib import Path

import pytest

from business_units.ai_fashion_agency import launch, pipeline, social
from business_units.ai_fashion_agency.content_engine import create_content_package
from business_units.ai_fashion_agency.identity import AGENCY_IDENTITY, agency_instagram_kit
from business_units.ai_fashion_agency.policy import ApprovalRequired
from business_units.ai_fashion_agency.projection import agency_answer, agency_state
from business_units.ai_fashion_agency.store import AgencyStore
from orchestrator_v1.nxs_schema_validator import validate

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def store(tmp_path):
    return AgencyStore(tmp_path / "agency.json")


def test_agency_identity_and_instagram_kit():
    kit = agency_instagram_kit()
    assert AGENCY_IDENTITY["name"] == "Unreal Faces"
    assert kit["bio_length"] <= 150 and "AI-generated" in kit["bio"]
    assert kit["handle_status"] == "UNVERIFIED_CHECK_IN_APP"
    assert len(kit["launch_grid"]) == 9 and "For brands" in kit["highlights"]


def test_casting_proposes_one_model_and_needs_approval(store):
    lch = launch.open_casting(store)
    assert lch["stage"] == "CASTING" and lch["stage_name"] == "Nova"
    assert lch["ranking"][0]["score"] > lch["ranking"][1]["score"]
    with pytest.raises(ValueError, match="one model at a time"):
        launch.open_casting(store)
    with pytest.raises(ApprovalRequired):
        launch.advance(store, lch["launch_id"])
    moved = launch.advance(store, lch["launch_id"], approved_by="max")
    assert moved["stage"] == "IDENTITY"


def _to_profile_kit(store):
    lch = launch.open_casting(store)
    launch.advance(store, lch["launch_id"], approved_by="max")
    with pytest.raises(ValueError, match="character sheet not generated"):
        launch.advance(store, lch["launch_id"])
    store.upsert("models", {"model_id": lch["model_id"], "status": "CHARACTER_SHEET_READY"})
    return launch.advance(store, lch["launch_id"])


def test_profile_kit_requires_real_account_and_builds_plan(store):
    lch = _to_profile_kit(store)
    kit = lch["artifacts"]["profile_kit"]
    assert kit["bio_length"] <= 150 and len(kit["launch_grid"]) == 9
    assert all(h.endswith(("unrealfaces", "_uf", ".ai")) for h in kit["handle_candidates"])
    with pytest.raises(ValueError, match="Instagram account not confirmed"):
        launch.advance(store, lch["launch_id"])
    with pytest.raises(ApprovalRequired):
        launch.record_account_created(store, lch["model_id"], platform="instagram",
                                      handle="nova.unrealfaces", approved_by="")
    launch.record_account_created(store, lch["model_id"], platform="instagram",
                                  handle="@nova.unrealfaces", approved_by="max")
    lch = launch.advance(store, lch["launch_id"])
    plan = lch["artifacts"]["content_plan"]
    assert len(plan["days"]) == 30 and not any(d["sponsored"] for d in plan["days"])
    lch = launch.advance_content_plan(store, lch["launch_id"])
    assert lch["stage"] == "PRODUCTION"


def _ready_packages(store, model_id, n):
    for i in range(n):
        brief = pipeline.build_content_brief(store, title=f"Trend remake {i}",
                                             content_category="viral_formats", hook="Watch this",
                                             script="s", caption="Which one? #AIcreator")
        pipeline.assign_model(store, brief["brief_id"], model_id=model_id, actor="t")
        store.upsert("briefs", {"brief_id": brief["brief_id"], "status": "GENERATED"})
        create_content_package(store, brief["brief_id"], media_refs=[f"hf://job{i}"],
                               review={"verdict": "APPROVE", "issues": [], "evidence": []})


def test_full_launch_cycle_then_next_model(store):
    lch = _to_profile_kit(store)
    mid = lch["model_id"]
    launch.record_account_created(store, mid, platform="instagram",
                                  handle="nova.unrealfaces", approved_by="max")
    launch.advance(store, lch["launch_id"])
    launch.advance_content_plan(store, lch["launch_id"])
    with pytest.raises(ValueError, match="0/3 content packages"):
        launch.advance(store, lch["launch_id"])
    _ready_packages(store, mid, 9)
    lch = launch.advance(store, lch["launch_id"])
    assert lch["stage"] == "PUBLISHING"
    packages = [p for p in store.snapshot()["content_packages"] if p["model_id"] == mid]
    for i, package in enumerate(packages):
        post = social.create_post_draft(store, package["package_id"], platform="instagram")
        social.transition_post(store, post["post_id"], "READY_FOR_REVIEW", actor="agency")
        social.transition_post(store, post["post_id"], "APPROVED", actor="max", approved_by="max")
        social.record_external_publication(store, post["post_id"],
                                           url=f"https://instagram.com/p/x{i}", published_by="max")
    with pytest.raises(ValueError, match="followers"):
        launch.advance(store, lch["launch_id"])
    social.record_account_metrics(store, mid, platform="instagram", followers=1200,
                                  source="instagram insights screenshot")
    lch = launch.advance(store, lch["launch_id"])
    assert lch["stage"] == "MONETIZATION"
    # One-at-a-time policy releases once the launch reaches MONETIZATION.
    nxt = launch.open_casting(store)
    assert nxt["model_id"] != mid
    with pytest.raises(ValueError, match="no STORE_READY product"):
        launch.advance(store, lch["launch_id"])
    state = agency_state(store)
    assert state["agency_name"] == "Unreal Faces" and state["published"] == 9
    schema = json.loads((ROOT / "contracts/ai-fashion-agency-state-v1.schema.json").read_text())
    assert validate(state, schema) == []


def test_review_decision_and_retire(store):
    lch = launch.open_casting(store)
    store.upsert("launches", {"launch_id": lch["launch_id"], "stage": "REVIEW"})
    with pytest.raises(ValueError, match="SCALE"):
        launch.advance(store, lch["launch_id"], approved_by="max", decision="MAYBE")
    closed = launch.advance(store, lch["launch_id"], approved_by="max", decision="RETIRE")
    assert closed["stage"] == "CLOSED"
    assert store.get("models", lch["model_id"])["status"] == "RETIRED"
    nxt = launch.open_casting(store)
    assert nxt["model_id"] != lch["model_id"]


def test_publishing_from_nexus_stays_disabled_and_metrics_are_observed(store):
    with pytest.raises(ValueError, match="observed follower count"):
        social.record_account_metrics(store, "MDL_STREET_NOVA", platform="instagram",
                                      followers=-1, source="x")
    with pytest.raises(ApprovalRequired, match="disabled"):
        from business_units.ai_fashion_agency.policy import require_approval
        require_approval("PUBLISH", "max")


def test_jarvis_answers_about_the_launch(store):
    assert "nessun lancio aperto" in agency_answer("come va il lancio?", store)[0]
    launch.open_casting(store)
    text = agency_answer("a che punto è il casting?", store)[0]
    assert text.startswith("Unreal Faces: lancio di Nova in fase CASTING")
    assert "approval of the proposed model" in text


def test_jarvis_classifies_launch_questions():
    from jarvis_v1.service import classify
    assert classify("a che punto è il casting?") == "COMMAND"
    assert classify("come va il lancio?") == "COMMAND"
    assert classify("crea una task per il casting") == "TASK_REQUEST"
