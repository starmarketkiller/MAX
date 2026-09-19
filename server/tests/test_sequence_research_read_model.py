import shutil
from pathlib import Path

from fastapi.testclient import TestClient

import app as backend
import sequence_research_read_model as model


SOURCE = Path(__file__).resolve().parents[1] / "research_scripts" / "phase7" / "phase7_2"


def test_real_catalog_maps_priority_failure_memory_and_readiness():
    catalog = model.SequenceResearchCatalog(SOURCE)
    result = catalog.list_sequences()
    assert result["count"] == 20
    seq3 = catalog.detail("SEQ-0003")
    assert seq3["priority"]["tier"] == "HIGH_RESEARCH_PRIORITY"
    assert seq3["priority"]["total_score"] == 17
    assert seq3["failure_memory_relation"] == "NOVEL"
    assert seq3["semantic_leakage"]["as_described_verdict"] == "NEEDS_REFORMULATION"
    assert seq3["semantic_leakage_status_after_correction"] == "PASS"
    assert seq3["provenance"]["outcome_tested"] is False
    readiness = catalog.readiness_summary()
    assert readiness["ready_for_phase_7_3"] is True
    assert readiness["counts"] == {"READY_FOR_FORMALIZATION": 6, "NEEDS_ADDITIONAL_SPECIFICATION": 10, "NOT_IMPLEMENTABLE_AS_DESCRIBED": 4}


def test_conditional_branch_resolution_uses_canonical_branch_record():
    catalog = model.SequenceResearchCatalog(SOURCE)
    seq3 = catalog.detail("SEQ-0003")
    assert seq3["branch_group_id"] == "CBG-0002"
    assert seq3["branch"]["common_antecedent"].startswith("Chiusura oltre")
    branches = catalog.list_branches()
    branch = next(item for item in branches["items"] if item["branch_group_id"] == "CBG-0002")
    assert set(branch["sequence_ids"]) == {"SEQ-0003", "SEQ-0004"}
    assert branches["label"] == "Conditional Branch"


def test_filters_and_provenance_counts_are_source_backed():
    catalog = model.SequenceResearchCatalog(SOURCE)
    high = catalog.list_sequences({"priority": "HIGH_RESEARCH_PRIORITY"})
    assert high["count"] > 0
    repeated = catalog.list_sequences({"failure_memory_relation": "DIRECT_REPEAT_OF_FAILED_IDEA"})
    assert [item["sequence_id"] for item in repeated["items"]] == ["SEQ-0010"]
    detail = catalog.detail("SEQ-0003")
    assert detail["raw_claim_count"] == len(detail["source_claims"])
    assert detail["source_count"] == len({claim["source_id"] for claim in detail["source_claims"]})
    assert sum(detail["evidence_quality_distribution"].values()) == detail["raw_claim_count"]


def test_missing_and_invalid_artifacts_are_isolated(tmp_path):
    for filename in model.FILES.values():
        if filename != model.FILES["clusters"]:
            shutil.copy2(SOURCE / filename, tmp_path / filename)
    (tmp_path / model.FILES["priorities"]).write_text("{invalid", encoding="utf-8")
    catalog = model.SequenceResearchCatalog(tmp_path)
    result = catalog.list_sequences()
    assert result["count"] == 20
    assert all(item["priority"] is None for item in result["items"])
    warning_artifacts = {item.get("artifact") for item in result["warnings"]}
    assert model.FILES["clusters"] in warning_artifacts
    assert model.FILES["priorities"] in warning_artifacts


def test_routes_are_authenticated_and_read_only(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "sequence.db"))
    backend.init_db()
    monkeypatch.setattr(model, "CATALOG", model.SequenceResearchCatalog(SOURCE))
    with TestClient(backend.app) as client:
        assert client.get("/api/research/sequences").status_code == 401
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        response = client.get("/api/research/sequences?mechanism_id=MECH-06", headers=headers)
        assert response.status_code == 200
        assert [item["sequence_id"] for item in response.json()["items"]] == ["SEQ-0003"]
        assert client.get("/api/research/sequences/SEQ-0003", headers=headers).status_code == 200
        assert client.get("/api/research/mechanisms", headers=headers).status_code == 200
        assert client.get("/api/research/branches", headers=headers).status_code == 200
        assert client.get("/api/research/sequence-readiness", headers=headers).json()["ready_for_phase_7_3"] is True
        assert client.get("/api/research/sequences/UNKNOWN", headers=headers).status_code == 404
