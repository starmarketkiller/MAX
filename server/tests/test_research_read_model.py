import json

import pytest
from fastapi.testclient import TestClient

import app as backend
import research_read_model


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _minimal_root(tmp_path, *, duplicate=False, broken=False, malformed=None):
    p55 = tmp_path / "server" / "research_scripts" / "phase5_5"
    p6 = tmp_path / "server" / "research_scripts" / "phase6"
    hypotheses = [{"hypothesis_id": "H1", "family_or_name": "One", "status": "OPEN"}]
    if duplicate:
        hypotheses.append({"hypothesis_id": "H1", "family_or_name": "Duplicate"})
    _write(p55 / "hypothesis_registry_v1.json", hypotheses)
    _write(p55 / "experiment_registry_v1.json", [{
        "experiment_id": "EXP1", "description": "Test",
        "hypothesis_ids": ["MISSING" if broken else "H1"],
    }])
    _write(p55 / "dataset_version_v1.json", {
        "dataset_id": "DATA1", "schema_version": 1, "source_hashes": {},
    })
    if malformed:
        target = {"hypotheses": p55 / "hypothesis_registry_v1.json",
                  "experiments": p55 / "experiment_registry_v1.json"}[malformed]
        target.write_text("{not-json", encoding="utf-8")
    return tmp_path


def test_missing_and_malformed_artifacts_do_not_break_catalog(tmp_path):
    root = _minimal_root(tmp_path, malformed="experiments")
    catalog = research_read_model.ResearchCatalog(root).build()
    assert catalog["entities"]["hypotheses"][0]["id"] == "H1"
    assert catalog["entities"]["experiments"] == []
    codes = {warning["code"] for warning in catalog["warnings"]}
    assert "MALFORMED_ARTIFACT" in codes
    assert "MISSING_ARTIFACT" in codes


def test_duplicate_ids_are_isolated_and_output_is_deterministic(tmp_path):
    catalog = research_read_model.ResearchCatalog(_minimal_root(tmp_path, duplicate=True))
    first = catalog.build()
    second = catalog.build()
    assert first == second
    assert [item["id"] for item in first["entities"]["hypotheses"]] == ["H1"]
    assert any(warning["code"] == "DUPLICATE_ID" for warning in first["warnings"])


def test_production_server_layout_is_supported(tmp_path):
    repository_root = _minimal_root(tmp_path)
    catalog = research_read_model.ResearchCatalog(repository_root / "server").build()
    assert catalog["entities"]["hypotheses"][0]["id"] == "H1"
    assert catalog["entities"]["datasets"][0]["id"] == "DATA1"


def test_broken_relations_are_reported_and_removed(tmp_path):
    catalog = research_read_model.ResearchCatalog(_minimal_root(tmp_path, broken=True)).build()
    experiment = catalog["entities"]["experiments"][0]
    assert experiment["relations"] == []
    assert any(warning["code"] == "BROKEN_RELATION" for warning in catalog["warnings"])


def test_h006_truthful_canonical_values():
    hypothesis = research_read_model.CATALOG.detail("hypotheses", research_read_model.H006_ID)
    assert hypothesis is not None
    assert hypothesis["status"] == "BORDERLINE"
    assert hypothesis["status_detail"] == "WEAK"
    assert hypothesis["evidence_grade"] == "E2"
    assert hypothesis["true_holdout_performed"] is True
    assert hypothesis["promoted_to_e3"] is False
    assert hypothesis["metrics"]["delta_p_holdout"] == pytest.approx(0.0571537349)
    assert hypothesis["metrics"]["ci_overlap"] is True
    assert hypothesis["metrics"]["buy_delta_p"] < 0
    assert hypothesis["metrics"]["sell_delta_p_diagnostic"] > 0
    assert hypothesis["execution_status"] == "NOT_TESTED"
    edge = research_read_model.CATALOG.detail("edge_components", research_read_model.H006_EDGE_ID)
    assert edge["status"] == "CANDIDATE_LIMITED"
    assert "diagnostic" in " ".join(edge["conflicts"]).lower()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "research-model.db"))
    backend.init_db()
    with TestClient(backend.app) as value:
        login = value.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        value.user_headers = {"Authorization": f"Bearer {login.json()['token']}"}
        yield value


@pytest.mark.parametrize("path", [
    "/api/research/hypotheses", "/api/research/experiments",
    "/api/research/datasets", "/api/research/evidence",
    "/api/research/edge-components", "/api/research/decision-cards",
])
def test_research_read_routes_require_authentication(client, path):
    client.cookies.clear()
    assert client.get(path).status_code == 401


def test_research_read_api_list_detail_and_filters(client):
    listing = client.get("/api/research/hypotheses?status=BORDERLINE",
                         headers=client.user_headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()["items"]] == [research_read_model.H006_ID]
    detail = client.get(f"/api/research/hypotheses/{research_read_model.H006_ID}",
                        headers=client.user_headers)
    assert detail.status_code == 200
    assert detail.json()["source"]["mode"] == "DIRECT"
    experiment = client.get(f"/api/research/experiments/{research_read_model.H006_EXPERIMENT_ID}",
                            headers=client.user_headers)
    assert experiment.status_code == 200
    assert any(rel["type"] == "EXPERIMENT_USES_DATASET"
               for rel in experiment.json()["relations"])
    missing = client.get("/api/research/hypotheses/not-found", headers=client.user_headers)
    assert missing.status_code == 404
