import json
from pathlib import Path

import company_control_plane as cp
import app as backend
from fastapi.testclient import TestClient


def test_department_slots_and_real_vs_skeleton():
    model = cp.CompanyControlPlane().build()
    departments = {item["id"]: item for item in model["departments"]}
    assert len(departments) == 7
    assert departments["QUANT_RESEARCH"]["status"] == "ACTIVE"
    assert departments["QUANT_RESEARCH"]["work_item_count"] > 0
    assert departments["EXECUTION"]["skeleton"] is True
    assert departments["EXECUTION"]["message"] == "no operational pipeline yet"
    assert departments["SCIENTIFIC_QA"]["operational_state"]["holdout_access_status"] is not None
    assert departments["QUANT_RESEARCH"]["operational_state"]["strategy_count"] == 7
    assert departments["EXECUTION"]["operational_state"]["state"] == "WAITING_FOR_QUANT_GATE"
    assert departments["RISK_PORTFOLIO"]["operational_state"]["state"] == "WAITING_FOR_DEPLOYABLE_STRATEGIES"


def test_status_mapping_preserves_raw_status():
    model = cp.CompanyControlPlane().build()
    blocked = next(item for item in model["work_items"] if item["raw_status"] == "NEEDS_ADDITIONAL_SPECIFICATION")
    assert blocked["normalized_status"] == "BLOCKED"
    assert cp.normalize_status("READY_FOR_FORMALIZATION") == "READY"
    assert cp.normalize_status("NOT_IMPLEMENTABLE_AS_DESCRIBED") == "BLOCKED"


def test_provenance_and_dependencies_are_explicit():
    model = cp.CompanyControlPlane().build()
    assert model["artifacts"]
    assert all(item["provenance"]["direct"] for item in model["artifacts"])
    assert all(item["relation"] == "REVIEWED_BY" for item in model["dependencies"])
    assert not any("profit" in json.dumps(item).lower() for item in model["work_items"])
    assert cp.CompanyControlPlane().department("DATA")["datasets"]


def test_missing_artifact_is_fault_isolated(monkeypatch, tmp_path):
    sources = dict(cp.SOURCES)
    sources["dataset_integrity"] = tmp_path / "missing.json"
    monkeypatch.setattr(cp, "SOURCES", sources)
    model = cp.CompanyControlPlane().build()
    assert len(model["departments"]) == 7
    assert any(item["source"].endswith("missing.json") for item in model["warnings"])


def test_company_routes_are_authenticated(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "company.db"))
    backend.init_db()
    with TestClient(backend.app) as client:
        assert client.get("/api/company/overview").status_code == 401
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        overview = client.get("/api/company/overview", headers=headers)
        assert overview.status_code == 200
        assert len(overview.json()["departments"]) == 7
        assert client.get("/api/company/departments/QUANT_RESEARCH", headers=headers).status_code == 200
        assert client.get("/api/company/departments/UNKNOWN", headers=headers).status_code == 404
