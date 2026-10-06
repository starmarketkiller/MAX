"""Test per analytics.py e reports.py: metriche account/strategy, drawdown
proxy, confronto cross-account normalizzato (mai PnL grezzo - sez.13)."""
from mt5_data_v1 import analytics, identity, reports

ACCOUNT_A = identity.derive_account_id("acct_a", "Broker", "Server")
ACCOUNT_B = identity.derive_account_id("acct_b", "Broker", "Server")


def _closed_episode(pnl, close_time, strategy="STRAT_A", status="CLOSED"):
    return {
        "episode_id": f"e{close_time}", "account_id": ACCOUNT_A, "position_id": 1, "symbol": "EURUSD",
        "strategy_attribution": {"status": "VERIFIED", "strategy_name": strategy} if strategy else {"status": "UNKNOWN"},
        "side": "BUY", "open_time": "2026-01-01T00:00:00+00:00", "close_time": close_time,
        "volume_opened": 0.1, "volume_closed": 0.1, "avg_open_price": 1.1, "avg_close_price": 1.1,
        "realized_pnl": pnl, "swap_total": 0.0, "commission_total": 0.0, "r_multiple": None,
        "status": status, "deal_ids": [1], "provenance": {},
    }


def test_account_metrics_empty_episodes():
    m = analytics.compute_account_metrics([])
    assert m["total_trades"] == 0
    assert m["win_rate"] is None


def test_account_metrics_win_rate_and_profit_factor():
    episodes = [
        _closed_episode(100, "2026-01-01T10:00:00+00:00"),
        _closed_episode(-50, "2026-01-02T10:00:00+00:00"),
        _closed_episode(50, "2026-01-03T10:00:00+00:00"),
    ]
    m = analytics.compute_account_metrics(episodes)
    assert m["total_trades"] == 3
    assert m["win_rate"] == 2 / 3
    assert m["profit_factor"] == 150 / 50
    assert m["total_realized_pnl"] == 100


def test_account_metrics_open_episodes_excluded():
    episodes = [_closed_episode(100, "2026-01-01T10:00:00+00:00"),
               _closed_episode(None, None, status="OPEN")]
    m = analytics.compute_account_metrics(episodes)
    assert m["total_trades"] == 1


def test_max_drawdown_proxy_detects_dip():
    episodes = [
        _closed_episode(100, "2026-01-01T10:00:00+00:00"),
        _closed_episode(-150, "2026-01-02T10:00:00+00:00"),
        _closed_episode(80, "2026-01-03T10:00:00+00:00"),
    ]
    m = analytics.compute_account_metrics(episodes)
    assert m["max_drawdown"] == 150  # picco 100 -> fondo -50 = drawdown di 150
    assert m["max_drawdown_basis"] == "CUMULATIVE_REALIZED_PNL_PROXY_NOT_ACCOUNT_EQUITY"


def test_strategy_metrics_groups_unknown_separately():
    episodes = [
        _closed_episode(100, "2026-01-01T10:00:00+00:00", strategy="STRAT_A"),
        _closed_episode(50, "2026-01-02T10:00:00+00:00", strategy=None),
    ]
    by_strategy = analytics.compute_strategy_metrics(episodes)
    assert "STRAT_A" in by_strategy
    assert "__UNKNOWN__" in by_strategy
    assert by_strategy["STRAT_A"]["total_trades"] == 1
    assert by_strategy["__UNKNOWN__"]["total_trades"] == 1


def test_normalize_for_comparison_not_comparable_without_balance():
    metrics = {"total_realized_pnl": 100.0}
    result = analytics.normalize_for_comparison(metrics, None, "USD")
    assert result["comparable"] is False


def test_normalize_for_comparison_pnl_pct():
    metrics = {"total_realized_pnl": 100.0}
    result = analytics.normalize_for_comparison(metrics, 1000.0, "USD")
    assert result["comparable"] is True
    assert result["pnl_pct"] == 0.1


def test_compare_accounts_flags_mixed_currency():
    entries = [
        {"account_id": ACCOUNT_A, "metrics": {"total_realized_pnl": 100.0}, "starting_balance": 1000.0, "currency": "USD"},
        {"account_id": ACCOUNT_B, "metrics": {"total_realized_pnl": 50.0}, "starting_balance": 500.0, "currency": "EUR"},
    ]
    comparison = analytics.compare_accounts(entries)
    assert comparison["mixed_currency_warning"] is True
    assert set(comparison["currencies_seen"]) == {"USD", "EUR"}


def test_compare_accounts_never_exposes_raw_pnl_only_pct():
    entries = [{"account_id": ACCOUNT_A, "metrics": {"total_realized_pnl": 100.0},
               "starting_balance": 1000.0, "currency": "USD"}]
    comparison = analytics.compare_accounts(entries)
    assert "total_realized_pnl" not in comparison["accounts"][0]
    assert comparison["accounts"][0]["pnl_pct"] == 0.1


def test_account_performance_summary_schema():
    episodes = [_closed_episode(100, "2026-01-01T10:00:00+00:00")]
    summary = reports.build_account_performance_summary(ACCOUNT_A, episodes)
    assert summary["schema"] == "ACCOUNT_PERFORMANCE_SUMMARY_V1"
    assert summary["account_metrics"]["total_trades"] == 1
    assert "STRAT_A" in summary["strategy_metrics"]


def test_multi_account_executive_summary_flags_failed_quality():
    s1 = reports.build_account_performance_summary(
        ACCOUNT_A, [_closed_episode(100, "2026-01-01T10:00:00+00:00")],
        data_quality={"status": "FAILED"})
    exec_summary = reports.build_multi_account_executive_summary([s1])
    assert exec_summary["accounts_with_failed_data_quality"] == [ACCOUNT_A]
    assert exec_summary["cross_account_comparison_available"] is False
