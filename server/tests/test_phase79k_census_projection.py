import json

import app as backend
import projection_freshness as freshness
import strategy_census_read_model as census
import strategy_pipeline_read_model as pipeline
from fastapi.testclient import TestClient


def _breakout():
    return next(item for item in pipeline.CATALOG.build()["items"] if item["strategy_id"] == "BREAKOUT_ACC")


def test_breakout_projects_corrected_phase79k_without_promotion():
    item = _breakout()
    assert item["canonical_strategy_identity"] == "BREAKOUT_ACC_INTENDED_D1_V1"
    assert item["dataset_version"] == "V2"
    assert item["scientific_verdict"] == "MECHANISM_PARTIALLY_SUPPORTED"
    assert item["scientific_confidence"].startswith("BASSA")
    assert "NON CASUALITA' ED EDGE INCREMENTALE ANCORA DA VERIFICARE" in item["non_randomness_and_incremental_edge"]
    assert "NON E' IDENTIFICABILE" in item["trend_alignment_effect"]
    assert item["natural_horizon_status"].startswith("NO")
    assert item["meta_filter_ready"] is False
    assert item["execution_candidate"] is False
    assert item["deployable"] is False
    model = pipeline.CATALOG.build()
    assert (model["meta_filter_ready_count"], model["execution_candidate_count"], model["deployable_count"]) == (0, 0, 0)


def test_funnel_populations_and_corrected_outcome_denominators_are_separate():
    item = _breakout()
    assert item["research_funnel"] == {"live_observed": 67, "opened": 47, "blocked": 11, "broker_reject": 9, "b_only": 8, "total_events": 75}
    changes = item["outcome_change_audit"]
    assert changes["binary_outcome_flips"] == 4
    assert changes["binary_outcome_flip_denominator"] == 46
    assert changes["coverage_status_changes"] == 1
    assert changes["coverage_transition"] == {"from": "UNKNOWN", "to": "UNKNOWN_CENSORED", "coverage_bars": 51}
    assert "5 cambi continuation/failure" not in json.dumps(item)
    assert "10,6%" not in json.dumps(item)


def test_fixed_horizon_and_measurement_boundaries_preserve_denominators():
    item = _breakout()
    buy, sell = item["fixed_horizon_results"]["BUY"], item["fixed_horizon_results"]["SELL"]
    assert (buy["n_continuation_v2"], buy["denominator_v2_excludes_censored"], buy["pct_continuation_v2"]) == (25, 36, 69.4)
    assert (sell["n_continuation_v2"], sell["denominator_v2_excludes_censored"], sell["pct_continuation_v2"], sell["n_censored_v2"]) == (2, 10, 20.0, 1)
    bounds = item["measurement_boundaries"]
    assert "75 eventi" in bounds["post_signal"]
    assert "47 OPENED" in bounds["post_fill"]
    assert "non N giorni di calendario" in bounds["market_bars"]
    assert bounds["ema100"]["n_evaluable_for_ema100"] == 72
    assert bounds["ema100"]["n_not_evaluable_insufficient_warmup"] == 3


def test_phase_authorities_and_freshness_are_scope_specific():
    item = _breakout()
    authorities = {entry["scope"]: entry for entry in item["source_authority"]}
    assert authorities["IMPLEMENTATION_AUDIT"]["phase"] == "7.10"
    assert authorities["CENSUS_AND_LINEAGE"]["phase"] == "7.11"
    assert authorities["STRATEGY_RESEARCH"]["phase"] == "7.9K"
    assert authorities["FORMALIZATION"]["status"] == "HISTORICAL"
    assert authorities["DATASET"]["supersedes"].endswith("breakout_acc_intended_d1_v1_dataset.json")
    assert authorities["STRATEGY_RESEARCH"]["status"] == "HISTORICAL"
    assert authorities["STRATEGY_RESEARCH"]["superseded_by"].endswith("breakoutacc_decision_card_v1.json")
    assert item["projection_freshness"]["freshness_status"] == "STALE"
    assert item["projection_freshness"]["canonical_latest_phase"] == "7.21"
    assert item["projection_freshness"]["projected_latest_phase"] == "7.9K"
    assert item["research_readiness"] == "HOLD_NEEDS_MORE_EVIDENCE"


def test_complete_census_keeps_overlapping_dimensions_separate():
    model = census.CATALOG.build()
    assert model["count"] == model["declared_count"] == 83
    assert model["categories_are_overlapping"] is True
    assert sum(value for value in model["counts_by_category"].values() if isinstance(value, int)) > 83
    crt = census.CATALOG.get("CRT")
    fvg = census.CATALOG.get("FVG_MIT_WINDOW")
    assert crt["implementation"]["live_mql5"] is True
    assert crt["registry_gap"]["verified"] is True
    assert fvg["registry_gap"]["severity"].startswith("HIGH")
    assert crt["enablement_configuration"]["effective_enabled"] is None
    assert crt["operational_eligibility"] is None
    assert crt["audit_coverage"]["covered"] is False


def test_census_fault_isolation(monkeypatch, tmp_path):
    missing = tmp_path / "missing.json"
    sources = dict(census.SOURCES)
    sources["audit"] = missing
    monkeypatch.setattr(census, "SOURCES", sources)
    model = census.StrategyCensusCatalog().build()
    assert model["count"] == 83
    assert model["warnings"]
    assert all(item["audit_coverage"]["covered"] is False for item in model["items"])


def test_authenticated_census_routes(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "census.db"))
    backend.init_db()
    with TestClient(backend.app) as client:
        assert client.get("/api/company/strategy-census").status_code == 401
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        result = client.get("/api/company/strategy-census", headers=headers)
        assert result.status_code == 200 and result.json()["count"] == 83
        assert client.get("/api/company/strategy-census/CRT", headers=headers).json()["registry_gap"]["verified"] is True
        assert client.get("/api/company/strategy-census/NOPE", headers=headers).status_code == 404
