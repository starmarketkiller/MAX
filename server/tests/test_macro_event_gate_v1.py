"""MEG-NFP-CPI-FOMC-001: synthetic-only tests. No XAUUSD outcomes."""
from __future__ import annotations

import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research_scripts"
sys.path.insert(0, str(RESEARCH))

from macro_event_gate_v1 import prereg as prereg_mod  # noqa: E402
from macro_event_gate_v1.calendar_loader import (  # noqa: E402
    CalendarError,
    default_fixture_path,
    load_events_csv,
)
from macro_event_gate_v1.decision import decide  # noqa: E402
from macro_event_gate_v1.stats import metric_elevated, summarize  # noqa: E402
from macro_event_gate_v1.windows import (  # noqa: E402
    build_event_rows,
    event_window_bounds,
    same_clock_window_on_day,
    window_metrics,
)

PREREG = RESEARCH / "macro_event_gate_v1" / "prereg_MEG-NFP-CPI-FOMC-001.json"
FIXTURE = RESEARCH / "macro_event_gate_v1" / "fixtures" / "sample_events_synthetic.csv"
NY = ZoneInfo("America/New_York")
UTC = timezone.utc


def ep(text):
    return int(datetime.fromisoformat(text).timestamp())


def m15_bar(start, bid_open, spread=0.3, mid_path=0.0):
    bid = bid_open + mid_path
    return {
        "start": start,
        "end": start + 900,
        "open": bid,
        "high": bid + 1,
        "low": bid - 1,
        "close": bid + 0.05,
        "ask_open": bid + spread,
        "ask_high": bid + 1 + spread,
        "ask_low": bid - 1 + spread,
        "ask_close": bid + 0.05 + spread,
        "n_ticks": 10,
    }


def test_prereg_params_hash_matches():
    prereg = prereg_mod.load(str(PREREG))
    assert prereg["hypothesis_id"] == "MEG-NFP-CPI-FOMC-001"
    assert prereg["evidence_ceiling"] == "EXPLORATORY_ONLY"
    assert prereg["decision_vocabulary"]["VALIDATED"].startswith("FORBIDDEN")
    assert prereg["params"]["pre_minutes"] == 5
    assert prereg["params"]["post_minutes"] == 30
    assert prereg["params"]["event_types"] == ["NFP", "CPI", "FOMC_STATEMENT"]
    assert prereg["phase"].startswith("1_non_directional")


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
    prereg_mod.assert_split_avoids_exclusions(prereg, "discovery_a")
    prereg_mod.assert_split_avoids_exclusions(prereg, "discovery_b")
    prereg_mod.assert_split_avoids_exclusions(prereg, "internal_validation")
    prereg_mod.assert_split_avoids_exclusions(prereg, "combined_discoveries")
    with pytest.raises(prereg_mod.PreregViolation):
        prereg_mod.assert_split_avoids_exclusions(prereg, "final_holdout")


def test_fixture_calendar_loads_only_when_allowed():
    assert Path(default_fixture_path()) == FIXTURE
    with pytest.raises(CalendarError):
        load_events_csv(str(FIXTURE), allow_synthetic=False)
    rows = load_events_csv(str(FIXTURE), allow_synthetic=True)
    assert len(rows) >= 6
    assert all("release_ts" in r for r in rows)
    assert {r["event"] for r in rows} <= {"NFP", "CPI", "FOMC_STATEMENT"}


def test_same_clock_respects_ny_dst():
    # 2024-02-02 08:30 NY = 13:30 UTC (EST)
    winter_release = ep("2024-02-02T13:30:00+00:00")
    c0, c1 = same_clock_window_on_day(winter_release, "2024-01-26", 5, 30)
    # Control day 2024-01-26 also EST → 13:30 UTC − 5min
    assert c0 == ep("2024-01-26T13:25:00+00:00")
    assert c1 == ep("2024-01-26T14:00:00+00:00")

    # 2024-07-05 08:30 NY = 12:30 UTC (EDT)
    summer_release = int(
        datetime(2024, 7, 5, 8, 30, tzinfo=NY).astimezone(UTC).timestamp()
    )
    s0, s1 = event_window_bounds(summer_release, 5, 30)
    assert s1 - s0 == 35 * 60
    # Map to another EDT Friday
    d0, d1 = same_clock_window_on_day(summer_release, "2024-06-28", 5, 30)
    control_local = datetime.fromtimestamp(d0 + 5 * 60, tz=UTC).astimezone(NY)
    assert control_local.hour == 8 and control_local.minute == 30


def test_window_metrics_spread_and_range():
    t0 = ep("2024-02-02T13:25:00+00:00")
    bars = [
        m15_bar(t0, 2000.0, spread=0.5, mid_path=0.0),
        m15_bar(t0 + 900, 2000.0, spread=0.7, mid_path=2.0),
    ]
    m = window_metrics(bars)
    assert m["n_bars"] == 2
    assert m["mean_spread"] == pytest.approx(0.6)
    # mid = bid + spread/2 → (2000.25 vs 2002.35) → range 2.1
    assert m["mid_range"] == pytest.approx(2.1)


def _bars_around_release(release_ts, base=2000.0, event_spread=1.2, quiet_spread=0.3, event_range=5.0):
    """Dense M15 grid spanning ±10 weeks around release for event + controls."""
    bars = []
    # Cover ±70 days every 15 minutes during NY daytime hours only would be huge;
    # instead place bars only in the 35-minute windows we care about for event
    # day and same-weekday controls within 8 weeks.
    release_dt = datetime.fromtimestamp(release_ts, tz=UTC)
    for week in range(0, 9):
        for sign in ((0,) if week == 0 else (-1, 1)):
            day = (release_dt + timedelta(days=sign * 7 * week)).date()
            # Rebuild NY local clock of original release on that civil date.
            local = release_dt.astimezone(NY)
            control_local = datetime(
                day.year, day.month, day.day,
                local.hour, local.minute, 0, tzinfo=NY,
            )
            rts = int(control_local.astimezone(UTC).timestamp())
            w0, w1 = event_window_bounds(rts, 5, 30)
            is_event = week == 0
            spread = event_spread if is_event else quiet_spread
            # Two bars: start of window and +15m with mid path for range
            bars.append(m15_bar(w0, base, spread=spread, mid_path=0.0))
            mid_bump = event_range if is_event else 0.4
            bars.append(m15_bar(w0 + 900, base, spread=spread, mid_path=mid_bump))
            # trailing bar still inside post window if needed
            if w0 + 1800 < w1:
                bars.append(m15_bar(w0 + 1800, base, spread=spread, mid_path=mid_bump * 0.5))
    bars.sort(key=lambda b: b["start"])
    return bars


def test_build_event_rows_elevated_on_synthetic():
    prereg = prereg_mod.load(str(PREREG))
    params = prereg["params"]
    # One NFP inside discovery_a with elevated spread/range vs quiet controls.
    release_ts = int(datetime(2024, 2, 2, 8, 30, tzinfo=NY).astimezone(UTC).timestamp())
    events = [{
        "event": "NFP",
        "release_utc": datetime.fromtimestamp(release_ts, tz=UTC).isoformat(),
        "release_ts": release_ts,
        "reference_period": "2024-01",
        "source_url": "https://example.invalid/macro_event_gate_v1/fixture",
    }]
    # Add sibling events so event_day_set is non-empty but controls avoid them.
    bars = _bars_around_release(release_ts, event_spread=1.5, quiet_spread=0.25, event_range=6.0)
    rows = build_event_rows(bars, events, prereg, "discovery_a", params)
    closed = [r for r in rows if r["status"] == "CLOSED"]
    assert len(closed) == 1
    assert closed[0]["spread_delta"] > 0
    assert closed[0]["range_delta"] > 0
    assert closed[0]["n_controls"] >= params["min_controls_per_event"]


def test_decision_f1_fail_when_neither_elevated():
    params = prereg_mod.load(str(PREREG))["params"]
    t0 = ep("2024-01-02T00:00:00+00:00")
    rows = []
    for i in range(40):
        rows.append({
            "status": "CLOSED",
            "entry_time": t0 + i * 86400 * 7,
            "spread_delta": 0.01 if i % 2 == 0 else -0.01,
            "range_delta": 0.02 if i % 2 == 0 else -0.02,
            "year": "2024" if i < 20 else "2025",
            "month": "2024-01" if i < 20 else "2024-02",
        })
    sum_a = {"n_closed": 20, "mean_spread_delta": 0.0, "mean_range_delta": 0.0}
    sum_b = {"n_closed": 20, "mean_spread_delta": 0.0, "mean_range_delta": 0.0}
    combined = summarize(rows, params)
    result = decide(sum_a, sum_b, combined, rows, params)
    assert result["decision"] == "FAIL"
    assert "F1_spread_and_vol_not_elevated_vs_same_clock" in result["falsifiers_fired"]
    assert result["evidence_ceiling"] == "EXPLORATORY_ONLY"
    assert result["validated_forbidden"] is True
    assert result.get("decision") != "VALIDATED"


def test_decision_exploratory_promising_when_elevated_no_flip():
    params = prereg_mod.load(str(PREREG))["params"]
    t0 = ep("2024-01-02T13:30:00+00:00")
    rows = []
    for i in range(40):
        rows.append({
            "status": "CLOSED",
            "entry_time": t0 + i * 86400 * 10,
            "spread_delta": 0.5,
            "range_delta": 1.0,
            "year": "2024" if i < 20 else "2025",
            "month": f"2024-{(i % 12) + 1:02d}",
        })
    combined = summarize(rows, params)
    # Force elevation flags via large positive CI (many month blocks).
    spread_ok, _, _ = metric_elevated(combined, "spread_delta")
    range_ok, _, _ = metric_elevated(combined, "range_delta")
    assert spread_ok or range_ok
    sum_a = {"n_closed": 20, "mean_spread_delta": 0.5, "mean_range_delta": 1.0}
    sum_b = {"n_closed": 20, "mean_spread_delta": 0.4, "mean_range_delta": 0.9}
    result = decide(sum_a, sum_b, combined, rows, params)
    assert result["decision"] == "EXPLORATORY_PROMISING"
    assert result["evidence_ceiling"] == "EXPLORATORY_ONLY"
    assert "VALIDATED" not in result["decision"]
    assert result["validated_forbidden"] is True


def test_decision_insufficient_n():
    params = prereg_mod.load(str(PREREG))["params"]
    result = decide(
        {"n_closed": 3, "mean_spread_delta": 1.0},
        {"n_closed": 3, "mean_spread_delta": 1.0},
        {"n_closed": 6},
        [],
        params,
    )
    assert result["decision"] == "INSUFFICIENT_EVIDENCE"
    assert result["validated_forbidden"] is True


def test_decision_sign_flip_f3():
    params = prereg_mod.load(str(PREREG))["params"]
    t0 = ep("2024-01-02T13:30:00+00:00")
    rows = []
    for i in range(40):
        rows.append({
            "status": "CLOSED",
            "entry_time": t0 + i * 86400 * 10,
            "spread_delta": 0.5,
            "range_delta": 1.0,
            "year": "2024" if i < 20 else "2025",
            "month": f"2024-{(i % 12) + 1:02d}",
        })
    combined = summarize(rows, params)
    sum_a = {"n_closed": 20, "mean_spread_delta": 0.5, "mean_range_delta": 1.0}
    sum_b = {"n_closed": 20, "mean_spread_delta": -0.4, "mean_range_delta": -0.9}
    result = decide(sum_a, sum_b, combined, rows, params)
    assert result["decision"] == "FAIL"
    assert "F3_sign_flip_across_discoveries" in result["falsifiers_fired"]


def test_fixture_csv_roundtrip_schema():
    with open(FIXTURE, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert "event" in rows[0]
    assert all(r["revision_note"].startswith("SYNTHETIC_FIXTURE") or "SYNTHETIC" in r["revision_note"]
               for r in rows)
