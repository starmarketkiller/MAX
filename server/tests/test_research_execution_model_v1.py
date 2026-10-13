from pathlib import Path
import json
import sys

import pytest

SERVER = Path(__file__).resolve().parents[1]
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))

import backtest
from research_execution_model_v1 import (
    SyntheticBar,
    apply_cost_cap,
    experiment_identity,
    fill_price,
    resolve_bar_exit,
    update_stop_before_exit,
    validate_timeframe,
)


def test_unknown_timeframe_is_rejected_by_scientific_contract():
    with pytest.raises(ValueError, match="unsupported timeframe"):
        validate_timeframe("2h")


def test_signal_close_and_next_open_are_distinct_models():
    signal = SyntheticBar(100, 104, 99, 103)
    following = SyntheticBar(106, 109, 105, 108)
    assert fill_price(signal, following, "SIGNAL_CLOSE_LEGACY") == 103
    assert fill_price(signal, following, "NEXT_OPEN_V1") == 106


def test_same_bar_stop_and_target_is_stop_first_in_legacy_contract():
    bar = SyntheticBar(100, 112, 88, 101)
    assert resolve_bar_exit(
        bar, direction=1, stop=90, target=110, policy="MANAGEMENT_THEN_STOP_FIRST"
    ) == ("SL", 90)


def test_same_bar_ambiguity_can_fail_closed():
    bar = SyntheticBar(100, 112, 88, 101)
    with pytest.raises(ValueError, match="touches stop and target"):
        resolve_bar_exit(
            bar, direction=1, stop=90, target=110, policy="AMBIGUOUS_REJECT"
        )


def test_breakeven_and_trailing_are_characterized_before_intrabar_exit():
    bar = SyntheticBar(open=100, high=112, low=99, close=110)
    updated = update_stop_before_exit(
        bar, direction=1, entry=100, stop=90, risk_distance=10,
        breakeven_r=1.0, trailing_atr=2.0, atr=2.0,
    )
    assert updated == 106
    assert resolve_bar_exit(
        bar, direction=1, stop=updated, target=120,
        policy="MANAGEMENT_THEN_STOP_FIRST",
    ) == ("SL", 106)


def test_complete_cost_application_and_5r_cap_are_auditable():
    uncapped = apply_cost_cap(spread_r=0.5, commission_r=0.25, slippage_r=0.25)
    assert uncapped["applied_cost_r"] == 1.0
    assert uncapped["cap_applied"] is False
    capped = apply_cost_cap(spread_r=4.0, commission_r=2.0, slippage_r=2.0)
    assert capped["raw_cost_r"] == 8.0
    assert capped["applied_cost_r"] == 5.0
    assert capped["cap_applied"] is True
    assert capped["spread_r"] + capped["commission_r"] + capped["slippage_r"] == 5.0


def test_fill_model_changes_experiment_identity():
    base = {
        "experiment_id": "EXP-1",
        "engine_version": "PY_BACKTEST_V1",
        "intrabar_policy": "STOP_FIRST",
    }
    close_id = experiment_identity({**base, "fill_model": "SIGNAL_CLOSE_LEGACY"})
    open_id = experiment_identity({**base, "fill_model": "NEXT_OPEN_V1"})
    assert close_id != open_id


def test_strict_real_source_failure_does_not_fall_back_to_synthetic(monkeypatch):
    monkeypatch.setattr(backtest, "_fetch_dukascopy", lambda *args, **kwargs: None)
    monkeypatch.setitem(sys.modules, "sweep", None)
    with pytest.raises(backtest.DataSourceUnavailableError):
        backtest._fetch_real("NO_SOURCE", "1d", 100, allow_synthetic_fallback=False)


def test_legacy_source_failure_remains_reproducible(monkeypatch):
    monkeypatch.setattr(backtest, "_fetch_dukascopy", lambda *args, **kwargs: None)
    monkeypatch.setitem(sys.modules, "sweep", None)
    candles, source = backtest._fetch_real(
        "LEGACY_SYNTHETIC_FIXTURE", "1d", 100, allow_synthetic_fallback=True
    )
    assert source == "synthetic"
    assert len(candles) == 100


def test_future_bar_truncation_does_not_change_causal_macd_prefix():
    closes = [100 + i * 0.2 + (i % 7) * 0.03 for i in range(120)]
    full12, full26 = backtest.ema_series(closes, 12), backtest.ema_series(closes, 26)
    full_line, full_signal = backtest._macd_signal_series(full12, full26)
    prefix = closes[:90]
    p12, p26 = backtest.ema_series(prefix, 12), backtest.ema_series(prefix, 26)
    prefix_line, prefix_signal = backtest._macd_signal_series(p12, p26)
    assert prefix_line == full_line[:90]
    assert prefix_signal == full_signal[:90]


def test_zero_cost_warning_and_execution_metadata_are_opt_in(monkeypatch):
    candles = [
        {"time": f"2026-01-{1 + i // 24:02d} {i % 24:02d}:00", "open": 100 + i, "high": 101 + i,
         "low": 99 + i, "close": 100 + i}
        for i in range(260)
    ]
    monkeypatch.setattr(backtest, "_fetch_real", lambda *args, **kwargs: (candles, "fixture"))
    result = backtest.run_backtest(
        timeframe="1d", strategy="MACD", bars=260, strict_execution_contract=True,
        experiment_id="MACD-FIXTURE-V1", dataset_fingerprint="a" * 64,
        indicator_implementation_version="MACD_PY_V1",
    )
    contract = result["execution_contract"]
    assert "ZERO_COST_SIMULATION" in contract["warnings"]
    assert contract["fill_model"] == "SIGNAL_CLOSE_LEGACY"
    assert contract["cost_cap_occurrences"] >= 0


def test_strict_contract_accepts_canonical_mql5_timeframe_aliases(monkeypatch):
    candles = [
        {"time": f"2026-02-{1 + i // 24:02d} {i % 24:02d}:00", "open": 100 + i,
         "high": 101 + i, "low": 99 + i, "close": 100 + i}
        for i in range(260)
    ]
    seen = {}

    def fixture_fetch(symbol, timeframe, bars, **kwargs):
        seen["timeframe"] = timeframe
        return candles, "fixture"

    monkeypatch.setattr(backtest, "_fetch_real", fixture_fetch)
    result = backtest.run_backtest(
        timeframe="D1", strategy="MACD", bars=260, strict_execution_contract=True,
        experiment_id="MACD-D1-FIXTURE-V1", dataset_fingerprint="b" * 64,
        indicator_implementation_version="MACD_PY_V1",
    )
    assert seen["timeframe"] == "1d"
    assert result["execution_contract"]["timeframe_contract"] == "1d"


def test_execution_model_schema_accepts_complete_versioned_contract():
    schema_path = SERVER.parent / "contracts" / "research-execution-model-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = {
        "schema_version": "RESEARCH_EXECUTION_MODEL_V1",
        "experiment_id": "EXP-MACD-CLOSE-V1",
        "engine_version": "PY_BACKTEST_LEGACY_V1",
        "dataset_fingerprint": "a" * 64,
        "data_source": "SYNTHETIC_FIXTURE_V1",
        "timeframe_contract": "4h",
        "fill_model": "SIGNAL_CLOSE_LEGACY",
        "intrabar_policy": "MANAGEMENT_THEN_STOP_FIRST",
        "cost_model": {
            "spread_price": 2.5,
            "commission_r": 0.0,
            "slippage_price": 0.5,
            "max_cost_r_per_trade": 5.0,
        },
        "cost_cap_occurrences": 0,
        "execution_fidelity_class": "PYTHON_BAR_APPROXIMATION",
        "indicator_implementation_version": "MACD_PY_V1",
        "legacy_compatibility": True,
        "warnings": [],
    }
    assert schema["$schema"].endswith("2020-12/schema")
    assert set(schema["required"]).issubset(payload)
    assert payload["schema_version"] == schema["properties"]["schema_version"]["const"]
    assert payload["timeframe_contract"] in schema["properties"]["timeframe_contract"]["enum"]
    assert payload["fill_model"] in schema["properties"]["fill_model"]["enum"]
    assert set(payload) <= set(schema["properties"])


def test_effective_risk_cap_contract_has_no_approved_numeric_policy():
    schema_path = SERVER.parent / "contracts" / "nxs-effective-risk-cap-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "NXS_EFFECTIVE_RISK_CAP_V1"
    rendered = json.dumps(schema)
    assert "0.5" not in rendered
    assert "1.0" not in rendered
    assert "POLICY_NOT_APPROVED" in schema["properties"]["result"]["properties"]["decision"]["enum"]
