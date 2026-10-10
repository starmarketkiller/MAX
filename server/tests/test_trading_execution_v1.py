"""Sandbox execution cycle. The broker double is not a demo account and sends nothing to MT5."""
import pytest

from trading_v1.broker import DONE, INVALID_STOPS, REJECTED, RETRYABLE, ScriptedBroker, UnconnectedMt5Port
from trading_v1.engine import ExecutionEngine, Intent, jarvis_proposal
from trading_v1.floor import project
from trading_v1.risk import AccountView, RiskLimits
from trading_v1.signals import macd_intent


def account():
    return AccountView("DEMO", True, 1000, 1000, 0, 800, 0, 0)


def intent(**kw):
    base = dict(client_id="ord-1", strategy_id="MACD", side="BUY", symbol="XAUUSD",
                volume=0.1, price=100, stop=99, quote_age_seconds=0, spread_points=10)
    base.update(kw)
    return Intent(**base)


def engine(tmp_path, broker, **kw):
    book = ExecutionEngine(tmp_path / "exec.json", broker, account=account(), **kw)
    book.enable_strategy("MACD", approved_by="owner")
    return book


def test_demo_cycle_confirms_once_and_does_not_duplicate(tmp_path):
    broker = ScriptedBroker([{"retcode": DONE, "ticket": 501, "position_id": 501,
                              "unrealized_pnl": 3.5}])
    book = engine(tmp_path, broker)
    first = book.submit(intent())
    assert first["state"] == "FILLED" and first["ticket"] == 501
    assert broker.sends == 1 and len(broker.positions) == 1
    second = book.submit(intent())
    assert second["ticket"] == 501 and broker.sends == 1
    report = book.reconcile()
    assert report["authoritative"] == "broker" and report["diverged"] is False
    view = project(book.projection(), stages={"MACD": "DEMO"}, reconcile=report)
    assert view["orders_confirmed"] == [{"client_id": "ord-1", "ticket": 501}]
    assert view["unrealized_pnl"] == 3.5
    assert view["stations"]["trading.exec"] == "confirmed"
    assert view["realized_pnl"] is None


def test_retryable_reject_does_not_open_two_positions(tmp_path):
    broker = ScriptedBroker([{"retcode": 10004}, {"retcode": DONE, "ticket": 7, "position_id": 7}])
    book = engine(tmp_path, broker)
    result = book.submit(intent())
    assert result["state"] == "FILLED" and result["ticket"] == 7
    assert broker.sends == 2 and len(broker.positions) == 1
    assert 10004 in RETRYABLE


def test_crash_after_broker_accept_recovers_without_a_second_order(tmp_path):
    broker = ScriptedBroker([{"retcode": DONE, "ticket": 9, "position_id": 9}])
    book = engine(tmp_path, broker)
    book.submit(intent())
    state = book._load()
    state["orders"]["ord-1"]["state"] = "SENDING"
    book._save(state)
    restarted = ExecutionEngine(tmp_path / "exec.json", broker, account=account())
    again = restarted.submit(intent())
    assert again["state"] == "FILLED" and again["ticket"] == 9
    assert broker.sends == 1


def test_crash_before_send_retries_once(tmp_path):
    broker = ScriptedBroker([{"retcode": DONE, "ticket": 11, "position_id": 11}])
    book = engine(tmp_path, broker)
    state = book._load()
    state["orders"]["ord-1"] = {"client_id": "ord-1", "strategy_id": "MACD", "state": "SENDING",
                                "ticket": None}
    book._save(state)
    result = book.submit(intent())
    assert result["ticket"] == 11 and broker.sends == 1


def test_disconnect_rejection_invalid_stop_and_kill_switch(tmp_path):
    broker = ScriptedBroker([{"retcode": REJECTED}])
    broker.connected = False
    book = engine(tmp_path, broker)
    blocked = book.submit(intent(client_id="down"))
    assert blocked["retcode"] == "DISCONNECTED" and broker.positions == {}

    broker.connected = True
    rejected = book.submit(intent(client_id="no"))
    assert rejected["state"] == "REJECTED" and broker.positions == {}

    broker.script.append({"retcode": INVALID_STOPS})
    invalid = book.submit(intent(client_id="stop"))
    assert invalid["state"] == "REJECTED" and invalid["retcode"] == INVALID_STOPS
    assert broker.positions == {}

    book.set_kill_switch(True)
    killed = book.submit(intent(client_id="kill"))
    assert killed["reasons"] == ["KILL_SWITCH"]
    assert broker.sends == 2


def test_stale_quote_and_risk_limit_block_before_send(tmp_path):
    broker = ScriptedBroker([{"retcode": DONE}])
    book = engine(tmp_path, broker, limits=RiskLimits(max_risk_per_trade=0.05))
    stale = book.submit(intent(client_id="old", quote_age_seconds=30))
    assert "STALE_QUOTE" in stale["reasons"]
    risk = book.submit(intent(client_id="big"))
    assert "MAX_RISK_PER_TRADE" in risk["reasons"]
    assert broker.sends == 0


def test_restart_sees_broker_position_the_ledger_does_not_know(tmp_path):
    broker = ScriptedBroker([])
    broker.positions[4] = {"position_id": 4, "client_id": "ord-x", "ticket": 4,
                           "unrealized_pnl": -1}
    book = engine(tmp_path, broker)
    report = book.reconcile()
    assert report["broker_unknown_to_ledger"] == [4]
    assert report["diverged"] is True
    assert report["positions"][0]["position_id"] == 4


def test_ledger_fill_missing_on_broker_is_a_divergence(tmp_path):
    broker = ScriptedBroker([{"retcode": DONE, "ticket": 3, "position_id": 3}])
    book = engine(tmp_path, broker)
    book.submit(intent())
    broker.positions.clear()
    report = book.reconcile()
    assert report["ledger_missing_on_broker"] == ["ord-1"]
    assert report["diverged"] is True


def test_live_stays_off_and_jarvis_cannot_arm_it(tmp_path):
    broker = ScriptedBroker([{"retcode": DONE}], environment="DEMO")
    book = engine(tmp_path, broker)
    with pytest.raises(PermissionError):
        book.arm_live(phrase="ENABLE_LIVE", account_environment="DEMO", account_verified=True)
    with pytest.raises(PermissionError):
        book.arm_live(phrase="yes", account_environment="LIVE", account_verified=True)
    assert book.projection()["live_armed"] is False
    assert jarvis_proposal("ENABLE_LIVE")["applied"] is False
    assert jarvis_proposal("RAISE_RISK_LIMIT")["effect"] == "PROPOSAL_ONLY"
    with pytest.raises(PermissionError):
        book.enable_strategy("SAR", approved_by="jarvis:42")


def test_unconnected_terminal_sends_nothing(tmp_path):
    book = engine(tmp_path, UnconnectedMt5Port())
    result = book.submit(intent())
    assert result["state"] == "BLOCKED" and result["retcode"] == "DISCONNECTED"


def test_existing_macd_signal_is_the_backtest_function(tmp_path):
    candles = [{"close": 110}]
    indicators = {"macd_line": [1.0], "macd_signal": [0.2], "ema200": [100.0], "close": [110]}
    assert macd_intent(client_id="s", candles=candles, indicators=indicators, index=0,
                       volume=0.1, stop=100, quote_age_seconds=0, spread_points=1,
                       enabled=set()) is None
    signal = macd_intent(client_id="s", candles=candles, indicators=indicators, index=0,
                         volume=0.1, stop=100, quote_age_seconds=0, spread_points=1,
                         enabled={"MACD"})
    assert signal.side == "BUY" and signal.strategy_id == "MACD"
    broker = ScriptedBroker([{"retcode": DONE, "ticket": 15, "position_id": 15}])
    book = engine(tmp_path, broker)
    assert book.submit(signal)["ticket"] == 15


def test_demo_engine_refuses_a_live_account(tmp_path):
    broker = ScriptedBroker([{"retcode": DONE}], environment="LIVE")
    book = engine(tmp_path, broker)
    blocked = book.submit(intent())
    assert blocked["reasons"] == ["ACCOUNT_MODE_MISMATCH"]
    assert broker.sends == 0
