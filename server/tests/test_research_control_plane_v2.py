import app as backend
import research_control_plane as rcp
from fastapi.testclient import TestClient


def test_safety_net_registries_are_projected_without_reinterpretation():
    model = rcp.CONTROL_PLANE.build()
    assert model["overview"]["census_count"] == 83
    # Phase 7.27 canonically added the cross-strategy BUY-dominance benchmark
    # and its linked hypothesis to the eight Phase 7.26 backfill records.
    assert model["overview"]["experiment_count"] == 9
    assert model["overview"]["hypothesis_count"] == 9
    assert model["overview"]["freshness"] == "CURRENT"
    h2 = next(x for x in model["catalogs"]["hypotheses"] if x["hypothesis_id"] == "H2_BREAKOUT_ACC_BUY_MORE_ROBUST_THAN_SELL")
    assert h2["lifecycle_state"] == "HYPOTHESIS"
    assert h2["validation_dataset_ids"] == []
    assert h2["tenant_id"] == "tenant-1"


def test_missing_artifact_is_partial_and_fault_isolated(monkeypatch, tmp_path):
    sources = dict(rcp.SOURCES); sources["priority_queue"] = tmp_path / "missing.json"
    monkeypatch.setattr(rcp, "SOURCES", sources)
    model = rcp.ResearchControlPlane().build()
    assert model["overview"]["freshness"] == "PARTIAL"
    assert model["catalogs"]["experiments"]
    assert model["catalogs"]["priority_queue"] == []
    assert model["warnings"]


def test_exposure_and_failures_preserve_canonical_labels():
    model = rcp.CONTROL_PLANE.build()
    exposed = next(x for x in model["catalogs"]["data_exposure"] if x["dataset_id"].startswith("BREAKOUT_ACC::2019"))
    assert exposed["mechanism_discovery_exposure"] is True
    assert "MAI un vero holdout" in exposed["holdout_status"]
    tsi = next(x for x in model["catalogs"]["failure_map"] if x["strategy_identity"] == "TSI")
    assert [x["mode"] for x in tsi["failure_modes"]] == ["IMPLEMENTATION_DEFECT"]


def test_control_plane_endpoints_require_auth(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "rcp.db")); backend.init_db()
    with TestClient(backend.app) as client:
        assert client.get("/api/research/control-plane/overview").status_code == 401
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        response = client.get("/api/research/control-plane/overview", headers=headers)
        assert response.status_code == 200 and response.json()["census_count"] == 83
        assert client.get("/api/research/control-plane/experiments", headers=headers).json()["count"] == 9
        assert client.get("/api/research/control-plane/visual-audits", headers=headers).status_code == 200
