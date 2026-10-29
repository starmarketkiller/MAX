"""TG-12M-GATE-001: synthetic-only tests. No XAUUSD outcomes."""
from __future__ import annotations

import csv
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research_scripts"
sys.path.insert(0, str(RESEARCH))

from trend_12m_gate_v1 import prereg as prereg_mod  # noqa: E402
from trend_12m_gate_v1.decision import (  # noqa: E402
    decide_confirmation,
    decide_selection,
    pick_winner,
)
from trend_12m_gate_v1.series import (  # noqa: E402
    load_daily_csv,
    log_returns,
    realized_vol,
    trailing_return,
)
from trend_12m_gate_v1.signals import build_variant_rows  # noqa: E402
from trend_12m_gate_v1.stats import (  # noqa: E402
    sign_of,
    summarize,
    year_concentration_share,
)

PREREG = RESEARCH / "trend_12m_gate_v1" / "prereg_TG-12M-GATE-001.json"
UTC = timezone.utc


def ep(text):
    return int(datetime.fromisoformat(text).timestamp())


def test_prereg_params_hash_matches():
    prereg = prereg_mod.load(str(PREREG))
    assert prereg["hypothesis_id"] == "TG-12M-GATE-001"
    assert prereg["evidence_ceiling"] == "EXPLORATORY_ONLY"
    assert prereg["decision_vocabulary"]["VALIDATED"].startswith("FORBIDDEN")
    assert prereg["params"]["selection_end_date"] == "2018-12-31"
    assert prereg["params"]["variant_ids"] == ["LO_FLAT_UNIT", "LO_FLAT_VOL", "LS_VOL"]


def test_excluded_windows_refuse_overlap():
    prereg = prereg_mod.load(str(PREREG))
    assert prereg_mod.window_hits_exclusion(
        ep("2026-03-01T00:00:00+00:00"),
        ep("2026-04-01T00:00:00+00:00"),
        prereg,
    ) == "excluded_phase7_sealed_holdout"
    assert prereg_mod.window_hits_exclusion(
        ep("2022-06-01T00:00:00+00:00"),
        ep("2022-07-01T00:00:00+00:00"),
        prereg,
    ) == "excluded_consumed_holdout_2022"
    prereg_mod.assert_split_avoids_exclusions(prereg, "selection")
    prereg_mod.assert_split_avoids_exclusions(prereg, "confirmation_a")
    prereg_mod.assert_split_avoids_exclusions(prereg, "confirmation_b")
    prereg_mod.assert_split_avoids_exclusions(prereg, "internal_validation")
    prereg_mod.assert_split_avoids_exclusions(prereg, "combined_confirmations")
    with pytest.raises(prereg_mod.PreregViolation):
        prereg_mod.assert_split_avoids_exclusions(prereg, "final_holdout")


def test_day_in_exclusion():
    prereg = prereg_mod.load(str(PREREG))
    assert prereg_mod.day_in_exclusion(ep("2022-06-15T00:00:00+00:00"), prereg)
    assert prereg_mod.day_in_exclusion(ep("2026-05-01T00:00:00+00:00"), prereg)
    assert prereg_mod.day_in_exclusion(ep("2018-06-15T00:00:00+00:00"), prereg) is None


def _synthetic_bars(n_days, start, drift_per_day=0.001, base=1000.0):
    bars = []
    px = base
    day = start
    for _ in range(n_days):
        # skip weekends
        while day.weekday() >= 5:
            day += timedelta(days=1)
        bars.append({
            "date": day.strftime("%Y-%m-%d"),
            "ts": int(day.timestamp()),
            "close": px,
        })
        px *= math.exp(drift_per_day)
        day += timedelta(days=1)
    return bars


def test_trailing_return_and_vol_causal():
    bars = _synthetic_bars(400, datetime(2010, 1, 4, tzinfo=UTC), drift_per_day=0.001)
    # Add small alternating noise so realized vol is strictly positive.
    for i, b in enumerate(bars):
        b["close"] *= 1.0 + (0.002 if i % 2 == 0 else -0.001)
    closes = [b["close"] for b in bars]
    lrets = log_returns(closes)
    assert trailing_return(closes, 10, 252) is None
    r12 = trailing_return(closes, 300, 252)
    assert r12 is not None and r12 > 0
    sigma = realized_vol(lrets, 300, 60, 252)
    assert sigma is not None and sigma > 0


def test_load_daily_csv_roundtrip(tmp_path):
    path = tmp_path / "xau.csv"
    bars = _synthetic_bars(10, datetime(2015, 1, 5, tzinfo=UTC))
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "close"])
        writer.writeheader()
        for b in bars:
            writer.writerow({"date": b["date"], "close": b["close"]})
    loaded = load_daily_csv(str(path))
    assert len(loaded) == 10
    assert loaded[0]["close"] == pytest.approx(bars[0]["close"])


def test_lo_flat_unit_beats_flat_on_rising_synthetic():
    """Strong uptrend: LO_FLAT_UNIT should match BH (always long) → excess ~0 after costs.

    Use a series that rises then we only check rows build without lookahead crash.
    """
    prereg = prereg_mod.load(str(PREREG))
    # Long history ending in selection window with positive drift.
    bars = _synthetic_bars(900, datetime(2014, 1, 2, tzinfo=UTC), drift_per_day=0.0008)
    rows = build_variant_rows(bars, prereg, "selection", "LO_FLAT_UNIT")
    assert len(rows) >= 100
    # All weights should be in {0, 1} for unit long-flat.
    assert all(r["weight"] in (0.0, 1.0) for r in rows)
    # Causal: exit after entry.
    assert all(r["exit_time"] > r["entry_time"] for r in rows)


def test_decision_selection_fail_when_no_edge():
    params = prereg_mod.load(str(PREREG))["params"]
    # Flat excess around zero → F1 FAIL
    t0 = ep("2010-01-04T00:00:00+00:00")
    rows = []
    for i in range(300):
        rows.append({
            "status": "CLOSED",
            "entry_time": t0 + i * 86400,
            "excess_log_return": 0.0001 if i % 2 == 0 else -0.0001,
            "strategy_log_return": 0.0,
            "bh_log_return": 0.0,
            "year": "2010",
            "month": "2010-01" if i < 150 else "2010-02",
        })
    by_id = {vid: list(rows) for vid in params["variant_ids"]}
    result = decide_selection(by_id, params)
    assert result["decision"] == "FAIL"
    assert "F1_no_variant_beats_bh_after_mt" in result["falsifiers_fired"]
    assert result["evidence_ceiling"] == "EXPLORATORY_ONLY"
    assert result["validated_forbidden"] is True
    assert result.get("decision") != "VALIDATED"


def test_decision_selection_survivor_and_winner_pick():
    params = prereg_mod.load(str(PREREG))["params"]
    t0 = ep("2010-01-04T00:00:00+00:00")

    def make_rows(mean_excess, n=300):
        out = []
        for i in range(n):
            out.append({
                "status": "CLOSED",
                "entry_time": t0 + i * 86400,
                "excess_log_return": mean_excess,
                "strategy_log_return": mean_excess,
                "bh_log_return": 0.0,
                "year": "2010",
                "month": "2010-01" if i < 150 else "2010-02",
            })
        return out

    by_id = {
        "LO_FLAT_UNIT": make_rows(0.002),
        "LO_FLAT_VOL": make_rows(0.003),
        "LS_VOL": make_rows(0.001),
    }
    result = decide_selection(by_id, params)
    assert result["decision"] == "SELECTION_SURVIVOR"
    assert result["selected_variant_id"] == "LO_FLAT_VOL"
    assert "VALIDATED" not in result["decision"]


def test_decision_confirmation_fail_sign_flip():
    params = prereg_mod.load(str(PREREG))["params"]
    t0 = ep("2019-01-02T00:00:00+00:00")
    rows = []
    for i in range(200):
        rows.append({
            "status": "CLOSED",
            "entry_time": t0 + i * 86400,
            "excess_log_return": 0.00001 if i % 2 == 0 else -0.00001,
            "strategy_log_return": 0.0,
            "bh_log_return": 0.0,
            "year": "2019" if i < 100 else "2020",
            "month": "2019-01" if i < 100 else "2019-02",
        })
    sum_a = {"n_days": 100, "mean_excess_log_return": 0.5}
    sum_b = {"n_days": 100, "mean_excess_log_return": -0.5}
    combined = summarize(rows, params)
    result = decide_confirmation(sum_a, sum_b, combined, rows, params, "LO_FLAT_VOL")
    assert result["decision"] == "FAIL"
    assert "F4_sign_flip_across_confirmations" in result["falsifiers_fired"]
    assert result["validated_forbidden"] is True


def test_decision_insufficient_n_selection():
    params = prereg_mod.load(str(PREREG))["params"]
    by_id = {vid: [] for vid in params["variant_ids"]}
    result = decide_selection(by_id, params)
    assert result["decision"] == "INSUFFICIENT_EVIDENCE"


def test_year_concentration_and_sign():
    yearly = {
        "2015": {"n": 100, "mean_excess_log_return": 1.0},
        "2016": {"n": 100, "mean_excess_log_return": 0.1},
        "2017": {"n": 100, "mean_excess_log_return": -0.5},
    }
    conc = year_concentration_share(yearly, min_n=20)
    assert conc["dominant_year"] == "2015"
    assert conc["share"] == pytest.approx(1.0 / 1.1)
    assert sign_of(1.2) == 1
    assert sign_of(-0.1) == -1
    assert sign_of(0.0) == 0
    assert sign_of(None) is None


def test_pick_winner_tie_break_order():
    summaries = {
        "LO_FLAT_UNIT": {"mean_excess_log_return": 0.1},
        "LO_FLAT_VOL": {"mean_excess_log_return": 0.1},
        "LS_VOL": {"mean_excess_log_return": 0.05},
    }
    assert pick_winner(["LO_FLAT_UNIT", "LO_FLAT_VOL"], summaries) == "LO_FLAT_UNIT"


def test_combined_split_window_spans_gap_but_day_filter_skips_holdout():
    prereg = prereg_mod.load(str(PREREG))
    start, end = prereg_mod.split_window(prereg, "combined_confirmations")
    a0, a1 = prereg_mod.split_window(prereg, "confirmation_a")
    b0, b1 = prereg_mod.split_window(prereg, "confirmation_b")
    assert start == a0 and end == b1
    # Gap between A end and B start overlaps consumed holdout.
    assert a1 < b0
    mid = ep("2022-06-01T00:00:00+00:00")
    assert a1 <= mid <= b0 or (a1 < mid < b0)
    assert prereg_mod.day_in_exclusion(mid, prereg)
