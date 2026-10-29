"""SD-TOKYO-LONDON-001: synthetic-only tests. No XAUUSD outcomes."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research_scripts"
sys.path.insert(0, str(RESEARCH))

from session_drift_tokyo_london_v1 import prereg as prereg_mod  # noqa: E402
from session_drift_tokyo_london_v1.decision import decide  # noqa: E402
from session_drift_tokyo_london_v1.events import build_session_rows  # noqa: E402
from session_drift_tokyo_london_v1.sessions import (  # noqa: E402
    london_open_utc,
    tokyo_open_utc,
)
from session_drift_tokyo_london_v1.stats import (  # noqa: E402
    sign_of,
    summarize,
    year_concentration_share,
)

PREREG = RESEARCH / "session_drift_tokyo_london_v1" / "prereg_SD-TOKYO-LONDON-001.json"
TOKYO = ZoneInfo("Asia/Tokyo")
UTC = timezone.utc


def ep(text):
    return int(datetime.fromisoformat(text).timestamp())


def m15_bar(start, bid_open, spread=0.3):
    return {
        "start": start,
        "end": start + 900,
        "open": bid_open,
        "high": bid_open + 1,
        "low": bid_open - 1,
        "close": bid_open + 0.1,
        "ask_open": bid_open + spread,
        "ask_high": bid_open + 1 + spread,
        "ask_low": bid_open - 1 + spread,
        "ask_close": bid_open + 0.1 + spread,
        "n_ticks": 10,
    }


def test_prereg_params_hash_matches():
    prereg = prereg_mod.load(str(PREREG))
    assert prereg["hypothesis_id"] == "SD-TOKYO-LONDON-001"
    assert prereg["evidence_ceiling"] == "EXPLORATORY_ONLY"
    assert "VALIDATED" not in prereg["decision_vocabulary"] or (
        prereg["decision_vocabulary"]["VALIDATED"].startswith("FORBIDDEN")
    )


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
    with pytest.raises(prereg_mod.PreregViolation):
        prereg_mod.assert_split_avoids_exclusions(prereg, "final_holdout")


def test_tokyo_london_opens_respect_dst():
    # Winter: Tokyo 09:00 = 00:00 UTC; London 08:00 GMT = 08:00 UTC
    winter = datetime(2024, 1, 10, tzinfo=UTC)
    t = tokyo_open_utc(winter, 9, 0)
    l = london_open_utc(winter.astimezone(TOKYO), 8, 0)
    assert t.astimezone(UTC).hour == 0
    assert l.astimezone(UTC).hour == 8
    # Summer: London BST → 08:00 local = 07:00 UTC
    summer = datetime(2024, 7, 10, tzinfo=UTC)
    l2 = london_open_utc(summer.astimezone(TOKYO), 8, 0)
    assert l2.astimezone(UTC).hour == 7


def test_session_rows_long_ask_to_bid_on_synthetic_bars():
    prereg = prereg_mod.load(str(PREREG))
    params = prereg["params"]
    # Build a few weekdays in Jan 2024 with rising gold across Tokyo→London.
    bars = []
    day = datetime(2024, 1, 8, tzinfo=UTC)  # Monday
    for i in range(10):
        d = day + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        t_open = tokyo_open_utc(d, 9, 0)
        l_open = london_open_utc(t_open.astimezone(TOKYO), 8, 0)
        t_ep = int(t_open.timestamp())
        l_ep = int(l_open.timestamp())
        base = 2000.0 + i
        bars.append(m15_bar(t_ep, base, spread=0.4))
        bars.append(m15_bar(l_ep, base + 2.0, spread=0.4))  # +2 bid vs entry
        # next Tokyo for comparator
        nxt = tokyo_open_utc(t_open + timedelta(hours=30), 9, 0)
        # force next calendar day open
        from session_drift_tokyo_london_v1.events import _next_tokyo_open
        nxt = _next_tokyo_open(t_open, 9, 0)
        bars.append(m15_bar(int(nxt.timestamp()), base + 3.0, spread=0.4))

    start = ep("2024-01-08T00:00:00+00:00")
    end = ep("2024-01-20T00:00:00+00:00")
    rows = build_session_rows(bars, params, start, end)
    assert len(rows) >= 5
    # net = exit_bid - entry_ask = (base+2) - (base+0.4) = 1.6
    assert rows[0]["net_return_usd"] == pytest.approx(1.6)
    assert all(r["status"] == "CLOSED" for r in rows)


def test_decision_fail_on_ci_including_zero_and_never_validated():
    params = prereg_mod.load(str(PREREG))["params"]
    # Build flat rows spanning two months so bootstrap CI exists and includes 0.
    rows = []
    t0 = ep("2024-01-02T00:00:00+00:00")
    for i in range(80):
        rows.append({
            "status": "CLOSED",
            "entry_time": t0 + i * 86400,
            "net_return_usd": 0.01 if i % 2 == 0 else -0.01,
            "mid_return_usd": 0.0,
            "delta_vs_generic_gold_usd": -0.05,
            "year": "2024" if i < 40 else "2025",
            "month": "2024-01" if i < 40 else "2024-02",
        })
    # Force two discovery summaries with opposite signs → F4 also
    sum_a = {"n_closed": 40, "mean_net_return_usd": 0.5}
    sum_b = {"n_closed": 40, "mean_net_return_usd": -0.5}
    combined = summarize(rows, params)
    result = decide(sum_a, sum_b, combined, rows, params)
    assert result["decision"] == "FAIL"
    assert "F4_sign_flip_across_discoveries" in result["falsifiers_fired"]
    assert result["evidence_ceiling"] == "EXPLORATORY_ONLY"
    assert result["validated_forbidden"] is True
    assert result.get("decision") != "VALIDATED"


def test_decision_insufficient_n():
    params = prereg_mod.load(str(PREREG))["params"]
    result = decide(
        {"n_closed": 5, "mean_net_return_usd": 1.0},
        {"n_closed": 5, "mean_net_return_usd": 1.0},
        {"n_closed": 10},
        [],
        params,
    )
    assert result["decision"] == "INSUFFICIENT_EVIDENCE"


def test_year_concentration_share():
    yearly = {
        "2023": {"n": 100, "mean_net_return_usd": 1.0},
        "2024": {"n": 100, "mean_net_return_usd": 0.1},
        "2025": {"n": 100, "mean_net_return_usd": -0.5},
    }
    conc = year_concentration_share(yearly, min_n=20)
    assert conc["dominant_year"] == "2023"
    assert conc["share"] == pytest.approx(1.0 / 1.1)


def test_sign_helper():
    assert sign_of(1.2) == 1
    assert sign_of(-0.1) == -1
    assert sign_of(0.0) == 0
    assert sign_of(None) is None


def test_combined_split_window_unions_discoveries():
    prereg = prereg_mod.load(str(PREREG))
    start, end = prereg_mod.split_window(prereg, "combined_discoveries")
    a0, a1 = prereg_mod.split_window(prereg, "discovery_a")
    b0, b1 = prereg_mod.split_window(prereg, "discovery_b")
    assert start == a0 and end == b1
    assert a1 == b0
