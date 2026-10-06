"""Test per trade_episodes.py: ricostruzione posizione da deal, partial
close, deal multipli, aggregazione commission/swap, pairing EA_TRADE_LOG.

Le fixture di deal synthetic seguono esattamente la shape di
csv_formats.parse_native_deal_export() (stessi campi, stessi nomi di
enum) - non un formato inventato."""
import pytest

from mt5_data_v1 import identity, trade_episodes

ACCOUNT_ID = identity.derive_account_id("333444", "TestBroker", "TestServer")
PROV = {"raw_source_path": "x.csv", "raw_source_sha256": "a" * 64,
       "parser_name": "test", "parser_version": "1.0.0", "normalized_at": "2026-01-01T00:00:00+00:00"}


def _deal(**kw):
    base = {"row_index": 0, "deal_ticket": 0, "position_id": 1, "order_ticket": 1,
           "time": "2026-01-01T00:00:00+00:00", "time_msc": None, "symbol": "EURUSD",
           "magic": 100, "type": "DEAL_TYPE_BUY", "entry": "DEAL_ENTRY_IN", "price": 1.1,
           "volume": 0.10, "sl": None, "tp": None, "profit": None, "swap": None,
           "commission": None, "comment": None, "reason": "DEAL_REASON_EXPERT"}
    base.update(kw)
    return base


def test_simple_open_close_full_episode():
    deals = [
        _deal(deal_ticket=1, entry="DEAL_ENTRY_IN", type="DEAL_TYPE_BUY", price=1.1000, volume=0.10,
             time="2026-01-01T10:00:00+00:00"),
        _deal(deal_ticket=2, entry="DEAL_ENTRY_OUT", price=1.1050, volume=0.10, profit=50.0,
             swap=-1.0, commission=-2.0, time="2026-01-01T12:00:00+00:00"),
    ]
    eps = trade_episodes.from_native_deals(deals, ACCOUNT_ID, PROV)
    assert len(eps) == 1
    ep = eps[0]
    assert ep["status"] == "CLOSED"
    assert ep["volume_opened"] == 0.10
    assert ep["volume_closed"] == 0.10
    assert ep["realized_pnl"] == 50.0
    assert ep["swap_total"] == -1.0
    assert ep["commission_total"] == -2.0
    assert ep["deal_ids"] == [1, 2]
    assert ep["side"] == "BUY"


def test_partial_close_leaves_status_partially_closed():
    deals = [
        _deal(deal_ticket=1, entry="DEAL_ENTRY_IN", volume=0.20, price=1.1000,
             time="2026-01-01T10:00:00+00:00"),
        _deal(deal_ticket=2, entry="DEAL_ENTRY_OUT", volume=0.10, price=1.1050, profit=25.0,
             time="2026-01-01T11:00:00+00:00"),
    ]
    eps = trade_episodes.from_native_deals(deals, ACCOUNT_ID, PROV)
    ep = eps[0]
    assert ep["status"] == "PARTIALLY_CLOSED"
    assert ep["volume_opened"] == 0.20
    assert ep["volume_closed"] == 0.10


def test_multiple_in_deals_averaged_open_price():
    deals = [
        _deal(deal_ticket=1, entry="DEAL_ENTRY_IN", volume=0.10, price=1.1000,
             time="2026-01-01T09:00:00+00:00"),
        _deal(deal_ticket=2, entry="DEAL_ENTRY_IN", volume=0.10, price=1.2000,
             time="2026-01-01T09:30:00+00:00"),
        _deal(deal_ticket=3, entry="DEAL_ENTRY_OUT", volume=0.20, price=1.2500, profit=100.0,
             swap=-0.5, commission=-1.0, time="2026-01-01T10:00:00+00:00"),
    ]
    eps = trade_episodes.from_native_deals(deals, ACCOUNT_ID, PROV)
    ep = eps[0]
    assert ep["avg_open_price"] == pytest.approx(1.15)
    assert ep["status"] == "CLOSED"
    assert len(ep["deal_ids"]) == 3


def test_open_position_with_no_close_deal():
    deals = [_deal(deal_ticket=1, entry="DEAL_ENTRY_IN", volume=0.10, price=1.1,
                   time="2026-01-01T10:00:00+00:00")]
    eps = trade_episodes.from_native_deals(deals, ACCOUNT_ID, PROV)
    ep = eps[0]
    assert ep["status"] == "OPEN"
    assert ep["close_time"] is None
    assert ep["realized_pnl"] is None


def test_balance_deal_without_position_produces_no_episode():
    deals = [_deal(deal_ticket=1, position_id=0, entry=None, type="DEAL_TYPE_BALANCE",
                   symbol=None, volume=0.0)]
    eps = trade_episodes.from_native_deals(deals, ACCOUNT_ID, PROV)
    assert eps == []


def test_ea_trade_log_simple_pairing_not_flagged_ambiguous():
    events = [
        {"row_index": 1, "time": "2026-01-01T10:00:00+00:00", "action": "OPEN", "ticket": 0,
         "strategy": "STRAT_A", "price": 1.1, "lots": 0.1, "sl": 1.0, "tp": 1.2,
         "score_or_pnl": 65.0, "reason": "entry", "hold_sec": 0, "r_multiple": 0.0, "resolved_tf": ""},
        {"row_index": 2, "time": "2026-01-01T12:00:00+00:00", "action": "CLOSE", "ticket": 99,
         "strategy": "STRAT_A", "price": 1.15, "lots": 0.1, "sl": 1.0, "tp": 1.2,
         "score_or_pnl": 50.0, "reason": "tp", "hold_sec": 7200, "r_multiple": 1.0, "resolved_tf": "H1"},
    ]
    eps = trade_episodes.from_ea_trade_log(events, ACCOUNT_ID, "EURUSD", PROV)
    assert len(eps) == 1
    ep = eps[0]
    assert ep["provenance"]["pairing_method"] == "SEQUENTIAL_HEURISTIC_PER_STRATEGY"
    assert ep["strategy_attribution"] == {"status": "VERIFIED", "strategy_name": "STRAT_A"}
    assert ep["realized_pnl"] == 50.0
    assert ep["position_id"] == 99


def test_ea_trade_log_pyramided_same_strategy_flagged_ambiguous():
    events = [
        {"row_index": 1, "time": "2026-01-01T10:00:00+00:00", "action": "OPEN", "ticket": 0,
         "strategy": "STRAT_A", "price": 1.1, "lots": 0.1, "sl": 1.0, "tp": 1.2,
         "score_or_pnl": 65.0, "reason": "entry", "hold_sec": 0, "r_multiple": 0.0, "resolved_tf": ""},
        {"row_index": 2, "time": "2026-01-01T10:30:00+00:00", "action": "OPEN", "ticket": 0,
         "strategy": "STRAT_A", "price": 1.12, "lots": 0.1, "sl": 1.0, "tp": 1.2,
         "score_or_pnl": 65.0, "reason": "entry", "hold_sec": 0, "r_multiple": 0.0, "resolved_tf": ""},
        {"row_index": 3, "time": "2026-01-01T12:00:00+00:00", "action": "CLOSE", "ticket": 99,
         "strategy": "STRAT_A", "price": 1.15, "lots": 0.1, "sl": 1.0, "tp": 1.2,
         "score_or_pnl": 50.0, "reason": "tp", "hold_sec": 7200, "r_multiple": 1.0, "resolved_tf": "H1"},
    ]
    eps = trade_episodes.from_ea_trade_log(events, ACCOUNT_ID, "EURUSD", PROV)
    closed = [e for e in eps if e["status"] == "CLOSED"]
    assert closed[0]["provenance"]["pairing_method"] == "AMBIGUOUS_FIFO_MULTIPLE_OPEN_PENDING"
    # la seconda OPEN resta aperta (nessuna seconda CLOSE nella finestra)
    assert any(e["status"] == "OPEN" for e in eps)
