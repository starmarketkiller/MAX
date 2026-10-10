"""The EA remains the only order sender. These tests never open a trade."""
import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from nexus_policy import EA_ACTIONS
from trading_v1.floor import project
from trading_v1.supervisor import TradingSupervisor
import importlib.util


def _bridge():
    path = Path(__file__).resolve().parents[2] / "LocalBridge" / "nexus_mt5_readonly_bridge.py"
    spec = importlib.util.spec_from_file_location("nexus_mt5_readonly_bridge", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_python_package_has_no_order_sender():
    root = Path(__file__).resolve().parents[1] / "trading_v1"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    for banned in ("order_send", "def send", "sig_macd", "ExecutionEngine", "OrderSend("):
        assert banned not in text
    assert "close_position" in EA_ACTIONS
    assert "open_order" not in EA_ACTIONS


def test_signal_is_stored_and_does_not_create_an_order(tmp_path):
    book = TradingSupervisor(tmp_path / "state.json")
    record = book.ingest({"kind": "SIGNAL", "client_id": "ea-1", "strategy_id": "MACD"})
    assert record["state"] == "SIGNAL_ONLY" and record["retry_allowed"] is False
    assert book.projection()["accepts_orders"] is False


def test_timeout_with_a_deal_is_confirmed_and_not_retried(tmp_path):
    book = TradingSupervisor(tmp_path / "state.json")
    record = book.resolve_timeout("ea-1", {"orders": [], "deals": [
        {"client_id": "ea-1", "ticket": 501, "position_id": 501}], "positions": []})
    assert record["state"] == "CONFIRMED" and record["ticket"] == 501
    assert record["retry_allowed"] is False and record["confirmed_by"] == "deals"


def test_timeout_without_a_broker_trace_stays_ambiguous(tmp_path):
    book = TradingSupervisor(tmp_path / "state.json")
    record = book.resolve_timeout("ea-1", {"orders": [], "deals": [], "positions": []})
    assert record["state"] == "AMBIGUOUS" and record["retry_allowed"] is False
    again = book.resolve_timeout("ea-1", {"orders": [{"client_id": "ea-1", "ticket": 9}],
                                          "deals": [], "positions": []})
    assert again["state"] == "IN_FLIGHT" and again["retry_allowed"] is False


def test_pending_order_after_timeout_is_not_a_second_send(tmp_path):
    book = TradingSupervisor(tmp_path / "state.json")
    record = book.resolve_timeout("ea-1", {"orders": [{"client_id": "ea-1", "ticket": 4}],
                                           "deals": [], "positions": []})
    assert record["state"] == "IN_FLIGHT" and record["retry_allowed"] is False
    assert project(book.projection())["stations"]["trading.exec"] == "in_flight"


def test_demo_stays_off_until_the_account_is_connected_and_verified(tmp_path):
    book = TradingSupervisor(tmp_path / "state.json")
    missing = book.review_demo({"connected": False}, {"account_login": "1", "verified_by": "owner"})
    assert missing["demo_account_verified"] is False
    assert "TERMINAL_NOT_CONNECTED" in missing["reasons"]
    live_account = book.review_demo(
        {"connected": True, "trade_mode": "LIVE", "login": 1},
        {"account_login": "1", "verified_by": "owner"})
    assert "NOT_A_DEMO_ACCOUNT" in live_account["reasons"]
    jarvis = book.review_demo(
        {"connected": True, "trade_mode": "DEMO", "login": 77},
        {"account_login": "77", "verified_by": "jarvis:42"})
    assert jarvis["demo_account_verified"] is False
    ready = book.review_demo(
        {"connected": True, "trade_mode": "DEMO", "login": 77, "server": "Broker-Demo"},
        {"account_login": "77", "verified_by": "owner"})
    assert ready["demo_account_verified"] is True
    assert ready["trading_started"] is False and ready["orders_sent"] == 0
    assert ready["live_enabled"] is False


def test_enable_live_phrase_is_not_enough_and_live_stays_off(tmp_path):
    book = TradingSupervisor(tmp_path / "state.json")
    phrase = book.review_live(
        {"connected": True, "trade_mode": "LIVE", "login": 9},
        {"phrase": "ENABLE_LIVE", "actor": "owner", "account_login": "9"},
        {"risk_percent": 1}, {"fingerprint": "abc"})
    assert "PHRASE_IS_NOT_AUTHORIZATION" in phrase["reasons"]
    assert phrase["live_enabled"] is False
    complete = book.review_live(
        {"connected": True, "trade_mode": "LIVE", "login": 9},
        {"phrase": "ENABLE_LIVE", "approval_id": "APR-1", "actor": "owner",
         "account_login": "9"},
        {"risk_percent": 1, "max_lot": 0.1}, {"fingerprint": "abc"})
    assert complete["live_eligible"] is True
    assert complete["live_enabled"] is False and complete["trading_started"] is False


def test_readonly_bridge_rejects_orders_and_a_public_bind():
    bridge = _bridge()
    token = "local-test-token-24chars"
    server = bridge.ThreadingHTTPServer(
        ("127.0.0.1", 0), bridge.make_handler(token, lambda: {"connected": True, "login": 77,
                                                              "trade_mode": "DEMO"}))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        request = Request(f"http://127.0.0.1:{port}/v1/mt5/account",
                          headers={"X-Nexus-Token": token})
        with urlopen(request, timeout=2) as response:
            body = json.loads(response.read().decode())
        assert body["login"] == 77 and body["accepts_orders"] is False
        posted = Request(f"http://127.0.0.1:{port}/v1/mt5/account", data=b"{}", method="POST",
                         headers={"X-Nexus-Token": token})
        with pytest.raises(Exception) as error:
            urlopen(posted, timeout=2)
        assert error.value.code == 405
    finally:
        server.shutdown()
    with pytest.raises(RuntimeError):
        bridge.serve("0.0.0.0", 9, token, reader=lambda: {})
