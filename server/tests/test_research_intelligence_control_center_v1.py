import json
import os
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient

import app as backend
from orchestrator_v1.nxs_schema_validator import validate
from research_intelligence_read_model import ResearchIntelligenceReadModel


ROOT = Path(__file__).resolve().parents[2]
MEMORY = ROOT / "server" / "research_scripts" / "research_intelligence_v1" / "memory" / "research_memory_v1.jsonl"
SCHEMA = json.loads((ROOT / "contracts" / "research-control-center-v1.schema.json").read_text(encoding="utf-8"))


def assert_contract(payload):
    assert validate(payload, SCHEMA) == []


def test_projection_is_verified_and_never_invents_loop_or_queue():
    model = ResearchIntelligenceReadModel(MEMORY).build()
    assert model["status"] == "HEALTHY"
    assert model["provenance"]["verified"] is True
    assert model["provenance"]["records"] > 0
    # committed memory holds two closed RI-02 cycles (BL-01 discovery ingest and its analysis)
    assert model["research_loop"]["status"] == "CYCLE_CLOSED"
    assert model["research_loop"]["current_cycle"] is None and model["research_loop"]["last_cycle"] == "C0002"
    assert model["research_loop"]["next_actions"] == []
    # PRIORITIZE ran but every candidate was excluded (family budget): an empty queue, nothing invented
    assert model["hypothesis_queue"]["status"] == "AVAILABLE"
    assert model["hypothesis_queue"]["items"] == []
    assert model["experiment_registry"]["count"] == 10
    assert all(item["provenance"] for item in model["experiment_registry"]["items"])
    bl01 = [i for i in model["experiment_registry"]["items"] if i["hypothesis_id"] == "BL-H4M15-IPC-001"]
    assert [(i["status"], i["result"], i["decision"]) for i in bl01] == [("COMPLETED", "INCONCLUSIVE", "INVESTIGATE")]
    assert_contract(model)


def test_memory_without_loop_runs_is_idle(tmp_path):
    from research_intelligence_v1 import pilot
    from research_intelligence_v1.memory import ResearchMemory
    pilot.seed(ResearchMemory(str(tmp_path / "memory.jsonl")))
    model = ResearchIntelligenceReadModel(tmp_path / "memory.jsonl").build()
    assert model["research_loop"]["status"] == "IDLE_NOT_RUN"
    assert model["research_loop"]["next_actions"] == ["Start a cycle explicitly"]
    assert model["hypothesis_queue"]["status"] == "NOT_MATERIALIZED" and model["hypothesis_queue"]["items"] == []
    assert_contract(model)


def test_missing_memory_is_explicitly_unavailable(tmp_path):
    model = ResearchIntelligenceReadModel(tmp_path / "missing.jsonl").build()
    assert model["status"] == "UNAVAILABLE"
    assert model["provenance"]["verified"] is False
    assert model["warnings"][0]["code"] == "RESEARCH_MEMORY_NOT_FOUND"
    assert model["experiment_registry"]["items"] == []
    assert_contract(model)


def test_corrupt_memory_fails_closed(tmp_path):
    path = tmp_path / "memory.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    model = ResearchIntelligenceReadModel(path).build()
    assert model["status"] == "UNAVAILABLE"
    assert model["warnings"][0]["code"] == "RESEARCH_MEMORY_READ_FAILED"


def test_endpoint_requires_authentication_and_is_read_only(monkeypatch):
    client = TestClient(backend.app)
    assert client.get("/api/research/intelligence/control-center").status_code == 401
    backend.app.dependency_overrides[backend.require_user] = lambda: "research-owner"
    try:
        response = client.get("/api/research/intelligence/control-center")
        assert response.status_code == 200
        payload = response.json()
        assert payload["approval_center"]["actions_enabled"] is False
        assert client.post("/api/research/intelligence/control-center", json={}).status_code == 405
    finally:
        backend.app.dependency_overrides.pop(backend.require_user, None)


def test_projection_does_not_modify_memory():
    before = MEMORY.read_bytes()
    ResearchIntelligenceReadModel(MEMORY).build()
    assert MEMORY.read_bytes() == before


def test_memory_import_honors_packaged_contracts_directory(tmp_path):
    contracts = tmp_path / "contracts"
    contracts.mkdir()
    source = ROOT / "contracts" / "research-memory-v1.schema.json"
    (contracts / source.name).write_bytes(source.read_bytes())
    env = dict(os.environ, NEXUS_CONTRACTS_DIR=str(contracts))
    script = (
        "import sys; "
        f"sys.path.insert(0, {str(ROOT / 'server' / 'research_scripts')!r}); "
        "import research_intelligence_v1.memory as m; print(m.SCHEMA_PATH)"
    )
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == str(contracts / "research-memory-v1.schema.json")
