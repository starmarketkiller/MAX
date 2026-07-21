"""PR6 — test del Canonical Strategy Registry (backend + contratto)."""
import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as backend
import strategy_registry as sr

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOKEN = {"X-Nexus-Token": "test-token"}


@pytest.fixture()
def client():
    with TestClient(backend.app) as c:
        yield c


def _auth(client):
    # login dashboard per gli endpoint require_user
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"} if "token" in r.json() else {}


# ------------------------------------------------------------- contratto ----
def test_registry_validates_and_reconciles():
    """Il validatore ufficiale non deve trovare errori né drift."""
    sys.path.insert(0, os.path.join(ROOT, "contracts"))
    import validate_registry as v
    reg = v.load_registry()
    assert v.validate(reg) == []
    _, drift = v.reconcile(reg)
    assert drift == []


def test_counts_are_37_live_plus_4_research():
    assert sr.count_live() == 37
    assert len(sr.research_only_ids()) == 4
    assert len(sr.all_records()) == 41


def test_cisd_is_alias_of_three_bar():
    assert sr.canonical_id("CISD") == "THREE_BAR_DELIVERY_BREAK"
    assert sr.canonical_id("THREE_BAR_DELIVERY_BREAK") == "THREE_BAR_DELIVERY_BREAK"


def test_elliott_is_live_without_research():
    r = sr.resolve("ELLIOTT")
    assert r["live_implementation"] is True
    assert r["research_implementation"] is False
    assert r["research_parity"] == "NOT_IMPLEMENTED"


def test_unknown_strategy_raises_never_falls_back():
    with pytest.raises(sr.UnknownStrategyError):
        sr.resolve("DOES_NOT_EXIST")


def test_scalp_are_research_only_not_live():
    for sid in sr.research_only_ids():
        r = sr.resolve(sid)
        assert r["status"] == "RESEARCH_ONLY"
        assert r["live_implementation"] is False
        assert r["default_enabled"] is False


def test_selector_index_unique_among_live():
    seen = {}
    for r in sr.all_records():
        si = r.get("selector_index")
        if r["live_implementation"] and si is not None:
            assert si not in seen, f"selector {si} duplicato"
            seen[si] = r["strategy_id"]


def test_strat_list_derives_from_registry_not_hardcoded():
    # il backend non usa piu' i 36 hardcoded
    assert backend.STRAT_LIST == sr.live_ids()
    assert len(backend.STRAT_LIST) == 37
    assert "ELLIOTT" in backend.STRAT_LIST
    assert "CISD" not in backend.STRAT_LIST   # alias, non id canonico


# ------------------------------------------------------------- endpoint -----
def test_backtest_strategies_endpoint_uses_registry(client):
    h = _auth(client)
    r = client.get("/api/backtest/strategies", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_ea"] == 37
    assert len(body["research_only"]) == 4


def test_registry_endpoint_exposes_artifact(client):
    h = _auth(client)
    r = client.get("/api/strategies/registry", headers=h)
    assert r.status_code == 200
    assert r.json()["counts"]["total"] == 41


def test_resolve_endpoint_404_on_unknown(client):
    h = _auth(client)
    assert client.get("/api/strategies/resolve/CISD", headers=h).status_code == 200
    assert client.get("/api/strategies/resolve/NOPE", headers=h).status_code == 404
