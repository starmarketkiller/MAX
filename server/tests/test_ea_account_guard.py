"""NEXUS-ACCT-001: the EA opens on DEMO by default and never on LIVE unless armed.

The MQL5 side cannot run here, so the source is checked statically: the gate
must sit inside the single exposure invariant, before any other entry gate
that could let an order through, and LIVE must default to off.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as backend
import ea_account_mode
import nexus_security as sec

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "MQL5" / "Include" / "NEXUS_v1"


def _src(name):
    return (INC / name).read_text(encoding="utf-8")


def _function_body(text, signature):
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


def test_live_authorization_defaults_off():
    inputs = _src("NXS_Inputs.mqh")
    assert re.search(r"input\s+bool\s+InpLiveTradingAuthorized\s*=\s*false\s*;", inputs)
    assert re.search(r"input\s+long\s+InpLiveAccountLogin\s*=\s*0\s*;", inputs)


def test_gate_is_inside_the_single_exposure_invariant_and_runs_first():
    body = _function_body(_src("NXS_Execution.mqh"), "bool NXS_CommonExposurePreflight(")
    gate = body.index("NXS_AccountGuard_EntryAllowed(")
    assert gate < body.index('"RUIN_FREEZE"')
    assert gate < body.index('"PROTECTIONS"')
    assert gate < body.index('"HARD_STOP"')
    assert "gateOut = GATE_ACCOUNT_MODE; return false;" in body
    assert "#include <NEXUS_v1\\NXS_AccountGuard.mqh>" in _src("NXS_Execution.mqh")


def test_guard_allows_only_tester_demo_or_a_pinned_live_login():
    body = _function_body(_src("NXS_AccountGuard.mqh"), "bool NXS_AccountGuard_EntryAllowed(")
    assert 'if(mode == "TESTER" || mode == "DEMO") return true;' in body
    assert body.index("!InpLiveTradingAuthorized") < body.index("InpLiveAccountLogin")
    assert "login != InpLiveAccountLogin" in body
    assert body.count("return true;") == 2
    # nothing else in the guard sends or modifies orders
    assert "OrderSend" not in _src("NXS_AccountGuard.mqh")


def test_close_paths_do_not_call_the_account_gate():
    globals_src = _src("NXS_Globals.mqh")
    for name in ("NXS_DoClose", "NXS_DoClosePartial", "NXS_DoModify"):
        match = re.search(r"bool\s+" + name + r"\s*\(", globals_src)
        assert match, name
        assert "NXS_AccountGuard" not in _function_body(globals_src, match.group(0))


def test_trace_maps_the_new_gate_without_renumbering():
    trace = _src("NXS_Trace.mqh")
    enum = _function_body(trace, "enum ENUM_NXS_GATE_REASON")
    assert enum.rstrip("}; \n").endswith("GATE_ACCOUNT_MODE")
    assert 'case GATE_ACCOUNT_MODE:      return "ACCOUNT_MODE";' in trace
    assert 'StringFind(r, "account_mode")' in trace


def test_push_declares_the_account():
    push = _src("NXS_WebBridge.mqh")
    for field in ("accountLogin", "accountServer", "accountTradeMode",
                  "liveTradingArmed", "accountEntriesAllowed"):
        assert f'\\"{field}\\"' in push


@pytest.mark.parametrize("payload,verdict", [
    ({}, "UNREPORTED"),
    ({"accountTradeMode": "DEMO", "accountLogin": 77, "accountEntriesAllowed": True}, "DEMO_REPORTED"),
    ({"accountTradeMode": "TESTER"}, "TESTER_REPORTED"),
    ({"accountTradeMode": "LIVE", "accountEntriesAllowed": False}, "LIVE_BLOCKED"),
    ({"accountTradeMode": "LIVE", "liveTradingArmed": True, "accountEntriesAllowed": False}, "LIVE_BLOCKED"),
    ({"accountTradeMode": "CONTEST", "liveTradingArmed": True, "accountEntriesAllowed": True}, "LIVE_ARMED"),
    ({"accountTradeMode": "SOMETHING"}, "UNKNOWN"),
])
def test_classify(payload, verdict):
    assert ea_account_mode.classify(payload)["verdict"] == verdict


def test_unreported_account_is_never_assumed_demo():
    view = ea_account_mode.classify({"balance": 1000})
    assert view["trade_mode"] is None and view["entries_allowed"] is None


@pytest.fixture()
def logged_in():
    with TestClient(backend.app) as client:
        resp = client.post("/api/auth/login", json={"email": backend.ADMIN_USER,
                                                    "password": backend.ADMIN_PASSWORD})
        assert resp.status_code == 200, resp.text
        yield client, {sec.CSRF_HEADER: resp.json()["csrf_token"]}


def test_status_exposes_the_account_the_ea_reported(logged_in):
    client, _ = logged_in
    resp = client.post("/api/ea/push", headers={"X-Nexus-Token": backend.BRIDGE_TOKEN}, json={
        "magic": 990001, "symbol": "ACCTGUARD", "online": True, "equity": 1000, "balance": 1000,
        "accountLogin": 5551234, "accountServer": "Broker-Demo", "accountTradeMode": "DEMO",
        "liveTradingArmed": False, "accountEntriesAllowed": True})
    assert resp.status_code == 200
    status = client.get("/api/ea/status").json()
    row = next(e for e in status["eas"] if e.get("symbol") == "ACCTGUARD")
    assert row["accountTradeMode"] == "DEMO"
    assert "account" in status
    assert ea_account_mode.classify(row)["verdict"] == "DEMO_REPORTED"
    with backend._conn() as c:
        stored = c.execute("SELECT account_id FROM ea_status_history WHERE symbol=? "
                           "ORDER BY id DESC LIMIT 1", ("ACCTGUARD",)).fetchone()
    assert str(stored["account_id"]) == "5551234"
