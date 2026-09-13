"""PR6 — test del Canonical Strategy Registry (backend + contratto)."""
import json
import os
import re
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as backend
import strategy_registry as sr
import backtest

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


def test_counts_are_52_live_plus_30_research():
    # Storico dei conteggi precedenti (37 live/4 research/59 totali) nella
    # cronologia git di questo file. Il registry e' cresciuto in modo
    # tracciabile fra 11/08 e dd22384 (WICK_SWEEP_RECLAIM e altre strategie
    # aggiunte a knowledge/strategy_database.json e ai backtest research-only
    # in server/backtest.py). Non e' drift: `test_registry_validates_and_reconciles`
    # sopra continua a passare (nessun errore, nessun drift) e
    # `python3 contracts/generate_registry.py` e' idempotente su questi dati
    # (nessuna differenza col file committato). I conteggi qui sotto sono
    # solo l'ultima istantanea verificata; se il registry cresce ancora,
    # vanno riaggiornati qui con la stessa evidenza (generator idempotente +
    # validator pulito), non ipotizzati.
    assert sr.count_live() == 52
    assert len(sr.research_only_ids()) == 30
    assert len(sr.all_records()) == 82


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
    with pytest.raises(sr.UnknownStrategyError):
        backtest.run_backtest(strategy="DOES_NOT_EXIST", bars=20)


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
    # il backend non usa piu' i 36 hardcoded; il conteggio segue il registry
    # (vedi test_counts_are_52_live_plus_30_research per la provenienza).
    assert backend.STRAT_LIST == sr.live_ids()
    assert len(backend.STRAT_LIST) == 52
    assert "ELLIOTT" in backend.STRAT_LIST
    assert "CISD" not in backend.STRAT_LIST   # alias, non id canonico


# ------------------------------------------------------------- endpoint -----
def test_backtest_strategies_endpoint_uses_registry(client):
    h = _auth(client)
    r = client.get("/api/backtest/strategies", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_ea"] == 52
    assert len(body["research_only"]) == 30


def test_registry_endpoint_exposes_artifact(client):
    h = _auth(client)
    r = client.get("/api/strategies/registry", headers=h)
    assert r.status_code == 200
    assert r.json()["counts"]["total"] == 82


def test_resolve_endpoint_404_on_unknown(client):
    h = _auth(client)
    assert client.get("/api/strategies/resolve/CISD", headers=h).status_code == 200
    assert client.get("/api/strategies/resolve/NOPE", headers=h).status_code == 404


def test_generated_frontend_adapter_matches_registry():
    path = os.path.join(ROOT, "frontend", "src", "contracts", "strategyRegistry.js")
    adapter = open(path, encoding="utf-8").read()
    # [A-Z] iniziale escludeva id come "3COMMAS_BOT" (aggiunto dopo la
    # scrittura di questo test): l'adapter era gia' corretto, era la regex a
    # non estrarlo. Verificato rigenerando con
    # `python3 contracts/generate_registry.py` (idempotente, nessun diff).
    ids = re.findall(r'^  \["([A-Z0-9][A-Z0-9_]*)",', adapter, re.M)
    assert ids == [record["strategy_id"] for record in sr.all_records()]


def test_generated_mql_adapter_matches_live_registry():
    path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_StrategyRegistry.mqh")
    adapter = open(path, encoding="utf-8").read().split("bool NXS_StrategyKnown", 1)[1]
    # stesso bug di regex del test sopra ("3COMMAS_BOT" iniziava con cifra).
    ids = re.findall(r'id=="([A-Z0-9][A-Z0-9_]*)"', adapter)
    assert ids == sr.live_ids()
