"""EA telemetry -> TradingSupervisor wiring. Read-only: no order is ever sent.

Closes the gap found while auditing feature/trading-execution-v1: the
supervisor (Grok's fix, c9e3455) was correct and tested in isolation, but
nothing fed it the EA's real /api/ea/push payload, so `/api/trading/execution`
always returned the empty default regardless of what the EA was doing.
"""
import os

import pytest
from fastapi.testclient import TestClient

from trading_v1.ea_bridge import ingest_positions
from trading_v1.supervisor import TradingSupervisor

TOKEN = {"X-Nexus-Token": "test-token"}


def test_ingest_positions_records_each_ticket_as_confirmed(tmp_path):
    book = TradingSupervisor(tmp_path / "state.json")
    payload = {"positions": [
        {"ticket": 501, "strategy": "MACD", "side": "BUY", "pnl": 3.5},
        {"ticket": 502, "strategy": "ORDER_BLOCK", "side": "SELL", "pnl": -1.2},
    ]}
    recorded = ingest_positions(book, payload)
    assert len(recorded) == 2
    projection = book.projection()
    assert projection["accepts_orders"] is False
    tickets = {r["ticket"] for r in projection["records"]}
    assert tickets == {501, 502}
    for record in projection["records"]:
        assert record["state"] == "CONFIRMED"


def test_ingest_positions_is_a_noop_without_positions(tmp_path):
    book = TradingSupervisor(tmp_path / "state.json")
    assert ingest_positions(book, {}) == []
    assert ingest_positions(book, {"positions": "not-a-list"}) == []
    assert book.projection()["records"] == []


def test_ingest_positions_skips_a_position_without_a_ticket(tmp_path):
    book = TradingSupervisor(tmp_path / "state.json")
    recorded = ingest_positions(book, {"positions": [{"strategy": "MACD"}]})
    assert recorded == []


def test_repeated_push_of_the_same_ticket_does_not_duplicate_records(tmp_path):
    book = TradingSupervisor(tmp_path / "state.json")
    payload = {"positions": [{"ticket": 9, "strategy": "SAR"}]}
    ingest_positions(book, payload)
    ingest_positions(book, payload)
    assert len(book.projection()["records"]) == 1


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_TRADING_STATE", str(tmp_path / "trading_state.json"))
    import app as backend
    with TestClient(backend.app) as c:
        yield c


def test_real_ea_push_reaches_the_trading_execution_route(client):
    import app as backend
    push = client.post("/api/ea/push", headers=TOKEN, json={
        "magic": 990011, "symbol": "XAUUSD", "balance": 1000, "equity": 1003.5,
        "positions": [{"ticket": 7001, "symbol": "XAUUSD", "side": "BUY",
                       "lots": 0.10, "pnl": 3.5, "strategy": "MACD", "magic": 990011}],
    })
    assert push.status_code == 200 and push.json()["ok"] is True

    login = client.post("/api/auth/login",
                        json={"email": backend.ADMIN_USER, "password": backend.ADMIN_PASSWORD})
    assert login.status_code == 200
    view = client.get("/api/trading/execution")
    assert view.status_code == 200
    body = view.json()
    assert body["sends_orders"] is False
    assert body["order_owner"] == "MQL5_EA"
    assert {"client_id": "ticket:7001", "ticket": 7001} in [
        {"client_id": r.get("client_id"), "ticket": r.get("ticket")} for r in body["records"]
    ]


def test_push_without_positions_key_still_acks_and_does_not_crash(client):
    push = client.post("/api/ea/push", headers=TOKEN,
                       json={"magic": 1, "symbol": "XAUUSD", "balance": 1000})
    assert push.status_code == 200 and push.json()["ok"] is True
