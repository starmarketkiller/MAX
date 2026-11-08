"""T05 nucleus projection. Six scenarios, and the T04 blocks stay unresolved."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from executive_v1.nucleus_progress import (
    IsolatedConsultationSink, deliver_consultation, project, render_consultation,
    states_are_distinct, unavailable_projection,
)
from executive_v1.state import ExecutiveStateBuilder, overall_progress
from orchestrator_v1.nxs_schema_validator import validate

ROOT = Path(__file__).resolve().parents[2]
NUCLEUS_SCHEMA = json.loads((ROOT / "contracts/nexus-nucleus-progress-v1.schema.json").read_text(encoding="utf-8"))
EXECUTIVE_SCHEMA = json.loads((ROOT / "contracts/nexus-executive-state-v1.schema.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 11, 8, 6, 0, tzinfo=timezone.utc)
EVIDENCE = ["staging/nexus_operational_core_v1/T04_LOCAL_OPS_ad4939e/evidence/gateway_health.json"]


def register(points=90, previous=85, delta=5, valid_until="2026-11-09T05:35:31+01:00", status="PASS"):
    return {
        "score": {"points": points, "percent": points, "delta_points": delta, "previous_points": previous},
        "criteria": {
            "C01": {"status": status, "points": 5, "valid_until": valid_until, "proof_class": "LOCAL_RUNTIME"},
            "C04": {"status": "PASS", "points": 5, "valid_until": None, "proof_class": "AUTOMATED_TEST"},
        },
    }


def services(listening, minutes_old=0):
    stamp = (NOW - timedelta(minutes=minutes_old)).isoformat()
    return [{"name": "gateway", "port": 18766, "listening": listening, "observed_at": stamp},
            {"name": "ollama", "port": 11434, "listening": listening, "observed_at": stamp}]


def t04():
    return {
        "health_reachable": True,
        "inference_http_succeeded": False,
        "http_default_model_ok": False,
        "warmup_declared_ok": True,
        "warmup_generation_ok": False,
        "router_timeout_seconds": 4,
        "cold_start_seconds": 11.98,
        "gateway_start_idempotent": False,
        "stable_endpoint": "PREPARED_NOT_APPLIED",
        "persistent_startup": "PREPARED_NOT_APPLIED",
        "remote_connection": "REMOTE_UNCERTIFIED",
        "evidence_refs": EVIDENCE,
    }


def inference():
    return {"historical_success": True, "live_generation_ok": False,
            "model": "qwen2.5:3b-instruct", "evidence_refs": EVIDENCE}


def test_missing_register_is_unavailable_not_a_number():
    document = project(now=NOW)
    assert document["criteria"]["state"] == "UNAVAILABLE"
    assert document["criteria"]["current_points"] is None
    assert document["service_availability"]["any_online"] is None
    assert document["verified_inference"]["currently_available"] is None
    assert states_are_distinct(document)


def test_recent_score_stays_separate_from_closed_ports_and_past_inference():
    document = project(register=register(), service_observations=services(False),
                       inference=inference(), local_operations=t04(), now=NOW)
    assert validate(document, NUCLEUS_SCHEMA) == []
    assert document["criteria"]["state"] == "CURRENT"
    assert document["criteria"]["current_points"] == 10
    assert document["criteria"]["reads_as_completion"] is False
    assert document["service_availability"]["any_online"] is False
    assert {item["availability"] for item in document["service_availability"]["services"]} == {"OFFLINE"}
    assert document["verified_inference"]["historical_success"] is True
    assert document["verified_inference"]["currently_available"] is False
    codes = [block["code"] for block in document["blocks"]]
    assert codes == [
        "HEALTH_NOT_INFERENCE", "HTTP_DEFAULT_MODEL_FAILED", "WARMUP_OK_WITHOUT_GENERATION",
        "ROUTER_TIMEOUT_SHORTER_THAN_COLD_START", "GATEWAY_START_NOT_IDEMPOTENT",
        "STABLE_ENDPOINT_PREPARED_NOT_APPLIED", "REMOTE_CONNECTION_UNCERTIFIED",
    ]
    assert all(block["resolved"] is False and block["next_action"] for block in document["blocks"])
    assert {item["status"] for item in document["proposals"]} == {"PREPARED_NOT_APPLIED", "REMOTE_UNCERTIFIED"}
    assert all(item["executed"] is False for item in document["proposals"])
    text = render_consultation(document)
    assert "Punteggio criteri" in text
    assert "Disponibilita servizi" in text
    assert "Inferenza verificata" in text
    assert "porta 18766: OFFLINE" in text
    assert "disponibile ora: no" in text
    assert states_are_distinct(document)


def test_stale_observation_does_not_become_a_number_or_online():
    expired = register(valid_until="2026-11-08T05:00:00+00:00")
    expired["criteria"]["C04"]["valid_until"] = "2026-11-08T05:00:00+00:00"
    document = project(register=expired, service_observations=services(True, minutes_old=11), now=NOW)
    assert document["criteria"]["state"] == "STALE"
    assert document["criteria"]["current_points"] is None
    assert document["criteria"]["items"][0]["effective_status"] == "STALE"
    assert document["criteria"]["items"][0]["points_counted"] == 0
    assert document["service_availability"]["state"] == "STALE"
    assert document["service_availability"]["any_online"] is None
    assert document["service_availability"]["services"][0]["listening"] is None
    assert "ONLINE" not in render_consultation(document)
    assert states_are_distinct(document)


def test_regression_is_not_completion():
    document = project(register=register(points=80, previous=90, delta=-10),
                       service_observations=services(False), now=NOW)
    assert document["criteria"]["state"] == "REGRESSION"
    assert document["criteria"]["current_points"] == 10
    assert document["criteria"]["reads_as_completion"] is False
    assert states_are_distinct(document)


def test_concluded_task_with_failed_delivery_is_not_success():
    document = project(register=register(), service_observations=services(False),
                       delivery={"concluded": True, "delivered": False, "evidence_refs": EVIDENCE},
                       now=NOW)
    assert document["criteria"]["reads_as_completion"] is False
    assert document["blocks"][-1]["code"] == "TASK_CONCLUDED_DELIVERY_FAILED"
    assert document["blocks"][-1]["resolved"] is False
    assert states_are_distinct(document)


def test_accepted_proposal_without_execution_stays_unapplied():
    operations = {"stable_endpoint": "PREPARED_NOT_APPLIED",
                  "persistent_startup": "PREPARED_NOT_APPLIED",
                  "remote_connection": "REMOTE_UNCERTIFIED"}
    document = project(register=register(), local_operations=operations, now=NOW)
    assert [item["status"] for item in document["proposals"]] == [
        "PREPARED_NOT_APPLIED", "PREPARED_NOT_APPLIED", "REMOTE_UNCERTIFIED"]
    assert all(item["executed"] is False and item["reads_as_execution"] is False
               for item in document["proposals"])
    assert states_are_distinct(document)


def test_closed_port_cannot_be_reported_online_and_health_is_not_inference():
    document = project(register=register(), service_observations=services(False),
                       inference={"historical_success": True, "live_generation_ok": True,
                                  "model": "qwen2.5:3b-instruct", "evidence_refs": EVIDENCE},
                       local_operations=t04(), now=NOW)
    assert document["verified_inference"]["currently_available"] is False
    assert states_are_distinct(document)


def test_isolated_sink_persists_consultation_and_refuses_network(tmp_path):
    document = project(register=register(), service_observations=services(False),
                       inference=inference(), local_operations=t04(), now=NOW)
    path = tmp_path / "consultation.json"
    sink = IsolatedConsultationSink(path)
    saved = deliver_consultation(document, sink)
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["text"] == saved["text"]
    assert "porta 11434: OFFLINE" in loaded["text"]

    class NetworkSink:
        isolated = False
        network = True

    try:
        deliver_consultation(document, NetworkSink())
        raise AssertionError("network sink was accepted")
    except RuntimeError as exc:
        assert "not isolated" in str(exc)


def test_executive_projection_keeps_overall_progress_and_defaults_to_unavailable():
    builder = ExecutiveStateBuilder({})
    state = builder.build()
    assert validate(state, EXECUTIVE_SCHEMA) == []
    assert state["nucleus_progress"] == unavailable_projection()
    assert "MATURITY_WEIGHTS" in state["overall_progress"]["method"]
    projected = project(register=register(), service_observations=services(False), now=NOW)
    wired = ExecutiveStateBuilder({"nucleus_progress": lambda: projected}).build()
    assert wired["nucleus_progress"]["criteria"]["current_points"] == 10
    assert wired["overall_progress"]["value"] == overall_progress({
        "revenue": wired["revenue"], "trading": wired["trading"],
        "ai_fashion_agency": wired["ai_fashion_agency"], "social": wired["social"],
    })["value"]
    assert wired["overall_progress"]["value"] != 90
