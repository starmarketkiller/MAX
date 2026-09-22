import json

import app as backend
import strategy_pipeline_read_model as sp
from fastapi.testclient import TestClient


def test_strategy_projection_separates_code_and_evidence():
    model = sp.StrategyPipelineCatalog().build()
    by_id = {item["strategy_id"]: item for item in model["items"]}
    assert model["count"] == 7
    sar = by_id["SAR_LIVE"]
    assert sar["code_registry_status"] == "ACTIVE"
    assert sar["evidence_is_refuted"] is True
    assert sar["governance_status"] == "GOVERNANCE_CONFLICT"
    assert sar["deployable"] is None
    assert sar["execution_candidate"] is False
    assert sar["meta_filter_structural_eligibility"] == "STRUCTURAL_STATUS_UNVERIFIED"
    assert sar["meta_filter_structural_eligibility_raw_7_7b"] == "NOT_ELIGIBLE"
    assert sar["structural_status_correction_applied"] is True
    assert by_id["H006_LIQUIDITY_SWEEP_RECLAIM"]["evidence_verdict"].startswith("RETAIN_E2")
    assert by_id["BREAKOUT_ACC"]["meta_filter_ready"] is False
    h006 = by_id["H006_LIQUIDITY_SWEEP_RECLAIM"]
    invalidation = next(item for item in h006["field_semantics"] if item["field"] == "invalidation_stop")
    assert invalidation["field_knowledge"] == "VERIFIED_ABSENCE"
    assert invalidation["requirement_role"] == "SATISFIED_BY_EQUIVALENT_MECHANISM"
    assert h006["meta_filter_structural_eligibility"] == "STRUCTURALLY_ELIGIBLE"
    assert not h006["structural_limitation"]


def test_not_extracted_is_not_treated_as_absent_or_status_change():
    model = sp.StrategyPipelineCatalog().build()
    by_id = {item["strategy_id"]: item for item in model["items"]}
    for strategy_id in ("WICK_SWEEP_RECLAIM", "SAR_LIVE", "ADX_RSI", "BREAKOUT_ACC"):
        item = by_id[strategy_id]
        assert any(field["field_knowledge"] == "NOT_EXTRACTED" for field in item["field_semantics"])
        assert item["field_semantics_status_changed"] is False
    assert model["meta_filter_ready_count"] == 0
    assert model["execution_candidate_count"] == 0
    assert model["deployable_count"] == 0
    assert all(item["deployable"] is None for item in model["items"])


def test_pipeline_and_provenance_are_artifact_backed():
    model = sp.StrategyPipelineCatalog().build()
    assert model["meta_filter_ready_count"] == 0
    assert model["execution_candidate_count"] == 0
    assert model["pipeline_stages"][-1] == "PORTFOLIO_RISK"
    assert all(item["provenance"]["sources"] for item in model["items"])
    assert all(item["current_stage"] == "STRATEGY_VALIDATION" for item in model["items"])


def test_fault_isolation_keeps_other_sources_available(monkeypatch, tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{bad", encoding="utf-8")
    sources = dict(sp.SOURCES)
    sources["meta_filter_eligibility"] = broken
    monkeypatch.setattr(sp, "SOURCES", sources)
    model = sp.StrategyPipelineCatalog().build()
    assert model["count"] == 7
    assert any(item["error"] == "JSONDecodeError" for item in model["warnings"])


def test_missing_field_refinement_is_fault_isolated(monkeypatch, tmp_path):
    baseline = {item["strategy_id"]: item["meta_filter_structural_eligibility"] for item in sp.StrategyPipelineCatalog().build()["items"]}
    sources = dict(sp.SOURCES)
    sources["missing_field_semantics"] = tmp_path / "missing.json"
    monkeypatch.setattr(sp, "SOURCES", sources)
    model = sp.StrategyPipelineCatalog().build()
    assert model["count"] == 7
    assert all(item["field_semantics"] == [] for item in model["items"])
    assert {item["strategy_id"]: item["meta_filter_structural_eligibility"] for item in model["items"]} == baseline
    assert model["meta_filter_ready_count"] == 0
    assert any(item["source"].endswith("missing.json") for item in model["warnings"])


def test_malformed_strategy_isolated(monkeypatch, tmp_path):
    original = json.loads(sp.SOURCES["lifecycle"].read_text(encoding="utf-8"))
    original["payload"]["deep_dive_candidates"]["BROKEN"] = "not-an-object"
    malformed = tmp_path / "lifecycle.json"
    malformed.write_text(json.dumps(original), encoding="utf-8")
    sources = dict(sp.SOURCES)
    sources["lifecycle"] = malformed
    monkeypatch.setattr(sp, "SOURCES", sources)
    model = sp.StrategyPipelineCatalog().build()
    assert model["count"] == 7
    assert any(item["error"] == "MalformedStrategy" for item in model["warnings"])


def test_strategy_routes_are_authenticated(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "strategy-company.db"))
    backend.init_db()
    with TestClient(backend.app) as client:
        assert client.get("/api/company/strategies").status_code == 401
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        listing = client.get("/api/company/strategies", headers=headers)
        assert listing.status_code == 200
        assert listing.json()["count"] == 7
        assert client.get("/api/company/strategies/SAR_LIVE", headers=headers).status_code == 200
        assert client.get("/api/company/strategies/UNKNOWN", headers=headers).status_code == 404

