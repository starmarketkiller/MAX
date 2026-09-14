import json

import pytest
from fastapi.testclient import TestClient

import app as backend
import knowledge_browser


@pytest.fixture()
def corpus(tmp_path, monkeypatch):
    trading = tmp_path / "vault" / "01-Trading"
    docs = tmp_path / "docs"
    knowledge = tmp_path / "knowledge"
    trading.mkdir(parents=True)
    docs.mkdir()
    knowledge.mkdir()
    (trading / "NEXUS - ADX_RSI Validation (14-09-2026).md").write_text(
        "# ADX_RSI Validation\n\nVerdict: PASS\n\nEvidence from the controlled run.", encoding="utf-8")
    (docs / "Architecture.md").write_text("# Architecture\n\nRead-only system map.", encoding="utf-8")
    (knowledge / "strategy_database.json").write_text(json.dumps({
        "generato": "2026-09-14", "avvertenza": "isolated research run",
        "strategie": [{"nome": "ADX_RSI", "stato": "attiva", "PF": None,
                       "WR_pct": None, "affidabilita_dati": "limited sample"}],
    }), encoding="utf-8")
    monkeypatch.setenv("NEXUS_KNOWLEDGE_ROOT", str(tmp_path))
    knowledge_browser.build_index.cache_clear()
    yield tmp_path
    knowledge_browser.build_index.cache_clear()


@pytest.fixture()
def client(tmp_path, corpus, monkeypatch):
    monkeypatch.setattr(backend, "DB_PATH", str(tmp_path / "knowledge.db"))
    backend.init_db()
    with TestClient(backend.app) as value:
        login = value.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        value.user_headers = {"Authorization": f"Bearer {login.json()['token']}"}
        yield value


def test_knowledge_routes_require_authentication(client):
    client.cookies.clear()
    assert client.get("/api/knowledge").status_code == 401


def test_index_is_metadata_only_and_preserves_missing_metrics(client):
    response = client.get("/api/knowledge", headers=client.user_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 3
    assert payload["provenance"] == "CACHED"
    assert all("content" not in row for row in payload["documents"])
    strategy = next(row for row in payload["documents"] if row["kind"] == "strategy")
    assert strategy["metrics"]["profit_factor"] is None
    assert strategy["metrics"]["win_rate_pct"] is None


def test_markdown_content_is_loaded_by_opaque_id(client):
    listing = client.get("/api/knowledge", headers=client.user_headers).json()
    document = next(row for row in listing["documents"] if row["title"] == "ADX_RSI Validation")
    response = client.get(f"/api/knowledge/{document['id']}", headers=client.user_headers)
    assert response.status_code == 200
    assert response.json()["content"].startswith("# ADX_RSI Validation")
    assert response.json()["verdict"] == "PASS"


@pytest.mark.parametrize("entry_id", ["../app.py", "doc-not-a-digest", "strategy-../../secret"])
def test_arbitrary_paths_and_invalid_ids_are_rejected(client, entry_id):
    response = client.get(f"/api/knowledge/{entry_id}", headers=client.user_headers)
    assert response.status_code == 404


def test_direct_lookup_never_accepts_a_path(corpus):
    assert knowledge_browser.get_entry("../../etc/passwd") is None
