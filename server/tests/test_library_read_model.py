import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

import app as backend
import library_read_model


SOURCE = Path(__file__).resolve().parents[1] / "research_scripts" / "phase6_6"


def test_phase66_catalog_preserves_historical_truth_and_posthoc_guardrails():
    catalog = library_read_model.LibraryCatalog(SOURCE)
    result = catalog.list_entities()
    by_id = {item["id"]: item for item in result["items"]}
    hypothesis = catalog.detail("H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT")
    primary = catalog.detail("EVD-H006-PRIMARY-001")
    audit = catalog.detail("EVD-H006-AUDIT-001")
    posthoc = catalog.detail("SELL_SWEEP_RECLAIM_ASYMMETRY")
    assert hypothesis["status"] == "BORDERLINE"
    assert hypothesis["evidence_grade"] == "E2"
    assert hypothesis["attributes"]["promoted_to_e3"] is False
    assert primary["type"] == "Evidence" and primary["phase"] == "Phase6"
    assert audit["type"] == "EvidenceAudit" and audit["phase"] == "Phase6.5"
    assert audit["attributes"]["sample"]["dependence_flag"] == "HIGH"
    assert audit["attributes"]["baseline"]["direction_aware"] is True
    assert posthoc["attributes"]["is_edge"] is False
    assert posthoc["attributes"]["is_validated"] is False
    assert not any(item["id"].startswith("H007") for item in result["items"])


def test_relations_are_explicit_valid_and_broken_targets_are_isolated():
    catalog = library_read_model.LibraryCatalog(SOURCE)
    result = catalog.list_relations()
    assert result["count"] == 9
    assert {item["type"] for item in result["items"]} <= library_read_model.RELATION_TYPES
    assert sum(w["code"] == "BROKEN_RELATION" for w in result["warnings"]) == 2


def test_explain_path_is_deterministic_and_decision_is_not_an_inferred_edge():
    catalog = library_read_model.LibraryCatalog(SOURCE)
    first = catalog.explain("H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT")
    second = catalog.explain("H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT")
    assert first == second
    assert first["current_decision"]["status"] == "RETAIN_E2"
    assert first["provenance"]["inferred_relations"] is False
    decision_id = first["current_decision"]["id"]
    assert not any(decision_id in (edge["source_id"], edge["target_id"]) for edge in first["typed_edges"])


def test_malformed_artifact_duplicate_id_and_broken_relation_do_not_break_catalog(tmp_path):
    for name in library_read_model.FILES.values():
        shutil.copy2(SOURCE / name, tmp_path / name)
    (tmp_path / "artifact_manifest.json").write_text("{bad", encoding="utf-8")
    evidence_path = tmp_path / "h006_evidence_v2.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["payload"]["retroactive_methodological_audit"]["identity"]["evidence_id"] = "EVD-H006-PRIMARY-001"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    catalog = library_read_model.LibraryCatalog(tmp_path)
    result = catalog.list_entities()
    codes = {warning["code"] for warning in result["warnings"]}
    assert result["count"] > 0
    assert "ARTIFACT_UNAVAILABLE" in codes
    assert "DUPLICATE_ENTITY_ID" in codes
    assert "CANONICAL_SHA_MISMATCH" in codes
    assert "BROKEN_RELATION" in codes


def test_library_routes_require_auth_and_support_filters(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "library.db"))
    backend.init_db()
    monkeypatch.setattr(library_read_model, "CATALOG", library_read_model.LibraryCatalog(SOURCE))
    with TestClient(backend.app) as client:
        assert client.get("/api/library/entities").status_code == 401
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        response = client.get("/api/library/entities?type=Evidence&evidence_grade=E2&q=primary", headers=headers)
        assert response.status_code == 200
        assert [item["id"] for item in response.json()["items"]] == ["EVD-H006-PRIMARY-001"]
        assert client.get("/api/library/entities/EVD-H006-PRIMARY-001", headers=headers).status_code == 200
        explain = client.get("/api/library/explain/H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT", headers=headers)
        assert explain.status_code == 200
        assert explain.json()["current_decision"]["status"] == "RETAIN_E2"
        assert client.get("/api/library/relations?relation_type=AUDITS", headers=headers).json()["count"] == 2
        assert client.get("/api/library/entities/nope", headers=headers).status_code == 404
