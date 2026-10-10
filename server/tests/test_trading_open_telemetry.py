"""NEXUS-OTEL-001: opening telemetry, EA -> backend -> projection.

Deterministic. No order is sent: the EA side is checked statically, the
backend with synthetic events shaped like NXS_OpenTelemetry.mqh produces.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as backend
import nexus_security as sec
import trading_open_telemetry as otel

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "MQL5" / "Include" / "NEXUS_v1"
EA = ROOT / "MQL5" / "Experts" / "NEXUS_EA_v2.mq5"
LOGIN = 5550001


def _src(path):
    return Path(path).read_text(encoding="utf-8")


def _body(text, signature):
    start = text.index(signature)
    depth, i = 0, text.index("{", start)
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    raise AssertionError("unbalanced body")


# ------------------------------------------------------------- EA (static) --
def test_every_open_attempt_is_recorded_after_order_send_and_on_local_block():
    globals_src = _src(INC / "NXS_Globals.mqh")
    for name in ("NXS_DoBuy", "NXS_DoSell"):
        body = _body(globals_src, f"bool {name}(")
        send = body.index("OrderSend(")
        blocked = body.index('_NXS_RecordOpenRequest(req, res, false, acctWhy);')
        sent = body.index('_NXS_RecordOpenRequest(req, res, ok, "");')
        assert blocked < send < sent
        assert body.index("NXS_AccountGuard_EntryAllowed(") < send
        # a partial fill opens a real position: it must not look like a failure
        assert "res.retcode == TRADE_RETCODE_DONE_PARTIAL" in body
    # Globals stays free of later includes: the diagnostic EA copy still compiles
    assert "NXS_OTel" not in globals_src and "NXS_Outbox" not in globals_src


def test_telemetry_module_queues_only_and_never_trades():
    text = _src(INC / "NXS_OpenTelemetry.mqh")
    code = re.sub(r"//[^\n]*", "", text)
    for banned in ("OrderSend(", "OrderSendAsync(", "WebRequest(", "NXS_DoBuy(", "NXS_DoSell(",
                   "NXS_SafeBuy(", "NXS_SafeSell(", "NXS_DoClose("):
        assert banned not in code
    assert "NXS_Outbox_Push(" in code
    enabled = _body(text, "bool _nxs_otel_enabled(")
    assert "MQL_TESTER" in enabled and "InpEnableWebSync" in enabled
    deal = _body(text, "void NXS_OTel_OnDealIn(")
    assert "PositionSelectByTicket(posId)" in deal       # open only if MT5 sees it
    assert "DEAL_ENTRY_IN" in deal and "IsNexusMagic" in deal


def test_ea_hooks_flush_deal_and_boot_resync():
    ea = _src(EA)
    assert "#include <NEXUS_v1\\NXS_OpenTelemetry.mqh>" in ea
    assert ea.index("#include <NEXUS_v1\\NXS_TradeLedger.mqh>") < ea.index(
        "#include <NEXUS_v1\\NXS_OpenTelemetry.mqh>")
    tx = _body(ea, "void OnTradeTransaction(")
    assert tx.index("NXS_OTel_Flush();") < tx.index("NXS_Ledger_OnDeal(")
    assert tx.index("NXS_Ledger_OnDeal(") < tx.index("NXS_OTel_OnDealIn(trans.deal, ev);")
    assert tx.index("NXS_OTel_OnDealIn(") < tx.index("if(ev == NXS_LEDGER_EV_NONE) return;")
    init = _body(ea, "int OnInit(")
    assert init.index("NXS_Ledger_Boot(") < init.index('NXS_OTel_ResyncOpenPositions("boot")')
    timer = _body(ea, "void OnTimer(")
    assert timer.index("NXS_OTel_Flush();") < timer.index("NXS_Outbox_Drain();")


def test_python_has_no_order_sender():
    text = _src(Path(otel.__file__))
    for banned in ("order_send", "OrderSend", "def send", "def retry", "MetaTrader5", "requests.post"):
        assert banned not in text


# --------------------------------------------------------------- fixtures --
def _order(order=1001, retcode=10009, volume=0.10, sent=True, key=None, **extra):
    event = {"kind": "order_result", "event_key": key or f"ord:{order}", "account_login": LOGIN,
             "sent": sent, "symbol": "XAUUSD", "side": "BUY", "magic": 77001, "strategy": "SAR",
             "requested_volume": volume, "requested_price": 2400.5, "sl": 2390.0, "tp": 2420.0,
             "retcode": retcode, "order": order, "deal": 0, "filled_volume": volume,
             "fill_price": 2400.6, "sent_at": "2026-10-11T08:00:00Z"}
    event.update(extra)
    return event


def _deal(deal=9001, order=1001, position=7001, volume=0.10, alive=True, msc=1):
    return {"kind": "deal_in", "event_key": f"deal:{deal}", "account_login": LOGIN,
            "ledger_event": "open", "deal": deal, "order": order, "position_id": position,
            "symbol": "XAUUSD", "side": "BUY", "magic": 77001, "strategy": "SAR",
            "deal_volume": volume, "deal_price": 2400.6, "deal_time_msc": msc,
            "position_alive": alive, "position_volume": volume if alive else 0.0,
            "position_price": 2400.6 if alive else 0.0, "sl": 2390.0 if alive else 0.0,
            "tp": 2420.0 if alive else 0.0}


def _snap(position=7001, volume=0.10):
    return {"kind": "position_snapshot", "event_key": f"snap:{position}:{int(volume * 100)}",
            "account_login": LOGIN, "source": "boot", "position_id": position,
            "symbol": "XAUUSD", "side": "BUY", "magic": 77001, "strategy": "SAR",
            "position_alive": True, "position_volume": volume, "position_price": 2400.6,
            "sl": 2390.0, "tp": 2420.0}


def _project(events, now=1000.0, received=1000.0, **kw):
    rows = []
    for event in events:
        clean = otel.validate(event)
        clean["_received_at"] = received
        rows.append(clean)
    return otel.project(rows, now, **kw)


# ------------------------------------------------------------- projection --
def test_full_cycle_request_accept_deal_position():
    view = _project([_order(), _deal()])
    attempt = view["attempts"][0]
    assert attempt["stage"] == "POSITION_OPEN" and attempt["request_sent"] is True
    assert attempt["deals"] == [9001] and attempt["position_id"] == 7001
    assert attempt["retry_allowed"] is False and view["sends_orders"] is False
    position = view["positions"][0]
    assert position["confirmed_by"] == "deal+terminal" and position["sl"] == 2390.0
    assert view["open_positions"] == 1


def test_accepted_without_deal_is_not_an_opening_and_becomes_ambiguous():
    fresh = _project([_order(retcode=10008)], now=1050.0)
    assert fresh["attempts"][0]["stage"] == "ORDER_ACCEPTED"
    assert fresh["open_positions"] == 0
    late = _project([_order(retcode=10008)], now=1000.0 + otel.DEFAULT_AMBIGUOUS_AFTER_SEC + 1)
    assert late["attempts"][0]["stage"] == "ACCEPTED_NO_FILL"
    assert late["ambiguous"] == ["ord:1001"] and late["attempts"][0]["retry_allowed"] is False


def test_deal_without_terminal_position_is_executed_not_open():
    view = _project([_order(), _deal(alive=False)])
    assert view["attempts"][0]["stage"] == "DEAL_EXECUTED"
    assert view["open_positions"] == 0


def test_partial_fill_then_completion():
    partial = _project([_order(retcode=10010, volume=0.10), _deal(volume=0.04)])
    assert partial["attempts"][0]["stage"] == "PARTIALLY_FILLED"
    assert partial["attempts"][0]["filled_volume"] == pytest.approx(0.04)
    done = _project([_order(volume=0.10), _deal(volume=0.04, msc=1),
                     _deal(deal=9002, volume=0.06, msc=2)])
    assert done["attempts"][0]["stage"] == "POSITION_OPEN"
    assert done["attempts"][0]["deals"] == [9001, 9002]
    assert done["positions"][0]["filled_volume"] == pytest.approx(0.10)


def test_rejected_retries_stay_separate_from_the_accepted_attempt():
    view = _project([
        _order(order=0, retcode=10004, key="req:1700000000:11"),
        _order(order=0, retcode=10020, key="req:1700000001:12"),
        _order(order=1001, retcode=10009), _deal()])
    stages = [a["stage"] for a in view["attempts"]]
    assert stages == ["REQUEST_REJECTED", "REQUEST_REJECTED", "POSITION_OPEN"]
    assert view["attempts"][0]["retcode_name"] == "REQUOTE"
    assert view["open_positions"] == 1


def test_local_block_is_reported_without_a_send():
    view = _project([_order(order=0, retcode=0, sent=False, key="req:1700000002:13",
                            blocked_reason="account_mode_live_not_authorized")])
    attempt = view["attempts"][0]
    assert attempt["stage"] == "REQUEST_BLOCKED" and attempt["request_sent"] is False
    assert attempt["reason"] == "account_mode_live_not_authorized"


def test_crash_recovery_from_boot_snapshot():
    """Order and deal events lost in a crash: the boot snapshot still proves the position."""
    view = _project([_snap()])
    position = view["positions"][0]
    assert position["state"] == "POSITION_OPEN" and position["confirmed_by"] == "boot_snapshot"
    assert view["unreported_orders"] == [7001]
    assert view["attempts"] == []


def test_closed_position_is_reconciled_with_the_trade_ledger():
    view = _project([_order(), _deal()], closed_positions={(LOGIN, 7001)})
    assert view["attempts"][0]["stage"] == "CLOSED"
    assert view["open_positions"] == 0


def test_hedging_two_positions_same_symbol_stay_separate():
    view = _project([_order(order=1001), _deal(deal=9001, order=1001, position=7001),
                     _order(order=1002), _deal(deal=9002, order=1002, position=7002)])
    assert [p["position_id"] for p in view["positions"]] == [7001, 7002]
    assert view["open_positions"] == 2


@pytest.mark.parametrize("event", [
    {"kind": "open_order", "event_key": "ord:1", "account_login": LOGIN},
    {"kind": "order_result", "event_key": "deal:1", "account_login": LOGIN, "order": 1},
    {"kind": "order_result", "event_key": "ord:2", "account_login": LOGIN, "order": 1},
    {"kind": "deal_in", "event_key": "deal:5", "account_login": LOGIN, "deal": 6, "order": 1,
     "position_id": 1},
    {"kind": "deal_in", "event_key": "deal:5", "account_login": LOGIN, "deal": 5},
    {"kind": "order_result", "event_key": "ord:1", "account_login": 0, "order": 1},
    {"kind": "order_result", "event_key": "ord:1 OR 1=1", "account_login": LOGIN, "order": 1},
    {"kind": "order_result", "event_key": "ord:1", "account_login": LOGIN, "order": 1, "sent": "yes"},
    {"kind": "position_snapshot", "event_key": "snap:1:10", "account_login": LOGIN},
    "not an object",
])
def test_validate_rejects_malformed_events(event):
    with pytest.raises(otel.InvalidEvent):
        otel.validate(event)


def test_idempotency_survives_a_restart(tmp_path):
    path = tmp_path / "otel.db"
    with sqlite3.connect(path) as conn:
        conn.executescript(otel.DDL)
        assert otel.store(conn, otel.validate(_deal()), 1.0) is True
        assert otel.store(conn, otel.validate(_deal()), 2.0) is False
    with sqlite3.connect(path) as conn:          # a new process, same file
        assert otel.store(conn, otel.validate(_deal()), 3.0) is False
        assert conn.execute("SELECT COUNT(*) FROM ea_execution_events").fetchone()[0] == 1
        other_account = dict(_deal(), account_login=LOGIN + 1)
        assert otel.store(conn, otel.validate(other_account), 4.0) is True


# ------------------------------------------------------------------- API --
@pytest.fixture()
def client():
    with TestClient(backend.app) as c:
        yield c


def _login(client):
    client.cookies.clear()
    resp = client.post("/api/auth/login", json={"email": backend.ADMIN_USER,
                                                "password": backend.ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.text
    return {sec.CSRF_HEADER: resp.json()["csrf_token"]}


def test_ingest_requires_the_ea_token_and_read_requires_a_session(client):
    client.cookies.clear()
    assert client.post("/api/ea/execution_event", json=_deal()).status_code == 401
    assert client.post("/api/ea/execution_event", json=_deal(),
                       headers={"X-Nexus-Token": "wrong"}).status_code == 401
    assert client.get("/api/trading/open-telemetry").status_code == 401


def test_ingest_is_idempotent_and_feeds_the_projection(client):
    token = {"X-Nexus-Token": backend.BRIDGE_TOKEN}
    login = 880000 + (int(backend.now()) % 100000)
    order = dict(_order(order=4401), account_login=login)
    deal = dict(_deal(deal=5501, order=4401, position=6601), account_login=login)
    first = client.post("/api/ea/execution_event", json=order, headers=token).json()
    assert first == {"ok": True, "stored": True, "duplicate": False, "event_key": "ord:4401"}
    again = client.post("/api/ea/execution_event", json=order, headers=token)
    assert again.status_code == 200 and again.json()["duplicate"] is True   # outbox drops it
    assert client.post("/api/ea/execution_event", json=deal, headers=token).status_code == 200
    bad = client.post("/api/ea/execution_event", json={"kind": "open_order"}, headers=token)
    assert bad.status_code == 422                                             # permanent, no retry
    _login(client)
    view = client.get("/api/trading/open-telemetry", params={"account_login": login}).json()
    assert [a["stage"] for a in view["attempts"]] == ["POSITION_OPEN"]
    assert view["sends_orders"] is False and view["retry_allowed"] is False
    assert view["positions"][0]["position_id"] == 6601


def test_migration_is_recorded(client):
    body = client.get("/api/ready").json()
    assert "017_execution_events" in body["checks"]["migrations"]["applied"]
