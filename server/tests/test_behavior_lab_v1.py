"""Behavior Lab V1 (BL-H4M15-IPC-001): deterministic tests on SYNTHETIC samples.

Every price below is invented for the test and says nothing about XAUUSD.
The real run happens on the research PC with the Phase 7 tick files.
"""
from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research_scripts"
sys.path.insert(0, str(RESEARCH))

from behavior_lab_v1 import prereg as prereg_mod  # noqa: E402
from behavior_lab_v1 import run_experiment  # noqa: E402
from behavior_lab_v1.bars import (H4, M15, build_bars, check_alignment,  # noqa: E402
                                  compare_with_reference_h4, resample)
from behavior_lab_v1.events import (confirm_m15, detect_impulses, detect_pullbacks,  # noqa: E402
                                    run_family, simulate_outcome, wilder_atr)
from behavior_lab_v1.sessions import (dst_transition_check, gap_report, rome_time,  # noqa: E402
                                      session_label)
from behavior_lab_v1.stats import block_bootstrap_mean, detector_health, wilson  # noqa: E402
from behavior_lab_v1.ticks import TickAudit  # noqa: E402

PREREG = RESEARCH / "behavior_lab_v1" / "prereg_BL-H4M15-IPC-001.json"
PARAMS = prereg_mod.load(str(PREREG))["params"]


def ep(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp())


def synthetic_ticks(start, minutes, step=60, base=2000.0, spread=0.3):
    """Deterministic saw-tooth price, one tick per `step` seconds."""
    out = []
    for n in range(minutes * 60 // step):
        ts = (start + n * step) * 1000 + (n % 7) * 13
        bid = round(base + ((n * 37) % 101) / 10.0 - 5.0 + n * 0.001, 3)
        out.append((ts, bid, round(bid + spread, 3)))
    return out


def bar(start, o, h, l, c, minutes=240, spread=0.2):  # noqa: E741
    return {"start": start, "end": start + minutes * 60, "open": o, "high": h, "low": l, "close": c,
            "ask_open": o + spread, "ask_high": h + spread, "ask_low": l + spread,
            "ask_close": c + spread, "avg_spread": spread, "max_spread": spread, "n_ticks": 10,
            "first_tick_ms": start * 1000, "last_tick_ms": (start + minutes * 60 - 1) * 1000}


# ------------------------------------------------------------------ bars --
def test_m15_and_h4_from_the_same_ticks_are_aligned():
    ticks = synthetic_ticks(ep("2023-02-06T00:00:00"), 3 * 24 * 60)
    bars = build_bars(ticks, [M15, H4])
    assert len(bars[M15]) == 3 * 96 and len(bars[H4]) == 3 * 6
    assert check_alignment(bars[H4], bars[M15]) == []
    rebuilt = resample(bars[M15], H4)
    assert [b["close"] for b in rebuilt] == [b["close"] for b in bars[H4]]
    assert all(b["end"] - b["start"] == 900 for b in bars[M15])


def test_alignment_check_catches_a_shifted_bucket():
    ticks = synthetic_ticks(ep("2023-02-06T00:00:00"), 8 * 60)
    bars = build_bars(ticks, [M15, H4])
    broken = [dict(b) for b in bars[H4]]
    broken[0]["close"] += 0.5
    assert {m["field"] for m in check_alignment(broken, bars[M15])} == {"close"}


def test_ties_and_out_of_order_rows_follow_the_reference_rule():
    t0 = ep("2023-02-06T00:00:00") * 1000
    ticks = [(t0 + 5000, 10.0, 10.2), (t0 + 1000, 9.0, 9.2), (t0 + 9000, 11.0, 11.2),
             (t0 + 9000, 12.0, 12.2)]
    b = build_bars(ticks, [M15])[M15][0]
    assert b["open"] == 9.0 and b["close"] == 12.0      # earliest open, later row wins the tie
    assert b["high"] == 12.0 and b["low"] == 9.0 and b["ask_close"] == 12.2


def _load_p71():
    path = RESEARCH / "phase7" / "phase7_1" / "build_h4_bars_p71.py"
    spec = importlib.util.spec_from_file_location("build_h4_bars_p71_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_h4_bars_match_the_existing_phase7_builder(tmp_path):
    """Run build_h4_bars_p71.main() itself on the same synthetic tick files."""
    p71 = _load_p71()
    decoded = tmp_path / "decoded"
    ticks = synthetic_ticks(ep("2023-02-06T00:00:00"), 2 * 24 * 60, step=37)
    by_day = {}
    for t in ticks:
        day = datetime.fromtimestamp(t[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        by_day.setdefault(day, []).append(t)
    for day, rows in by_day.items():
        folder = decoded / day[:4]
        folder.mkdir(parents=True, exist_ok=True)
        with gzip.open(folder / f"{day}.csv.gz", "wt", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["epoch_ms", "bid", "ask", "bid_vol", "ask_vol"])
            for ts, bid, ask in rows:
                writer.writerow([ts, bid, ask, 1.0, 1.0])
    p71.PHASE6_DECODED_DIR = p71.PHASE7_DECODED_DIR = str(decoded)
    p71.OUT_DIR = str(tmp_path)
    p71.BUFFER_START = p71.PERIOD_START = datetime(2023, 2, 6, tzinfo=timezone.utc)
    p71.PERIOD_END = datetime(2023, 2, 7, tzinfo=timezone.utc)
    p71.main()
    with open(tmp_path / "xauusd_h4_bars_p71.csv", newline="", encoding="utf-8") as handle:
        reference = list(csv.DictReader(handle))
    ours = build_bars(ticks, [H4])[H4]
    assert len(reference) == len(ours) == 12
    assert compare_with_reference_h4(ours, reference) == []


def test_tick_audit_flags_each_defect():
    audit = TickAudit(max_spread=1.0)
    for row in [(1000, 10.0, 10.1), (1000, 10.0, 10.1), (900, 10.0, 10.1), (2000, 10.2, 10.1),
                (3000, 0.0, 10.0), (4000, 10.0, 12.5)]:
        audit.add(*row)
    r = audit.report()
    assert (r["exact_duplicates"], r["non_monotonic_timestamp"], r["crossed_ask_below_bid"],
            r["nonpositive_price"]) == (1, 1, 1, 1)
    assert r["spread_above_max"] == 2 and r["verdict"] == "FAIL"


# ------------------------------------------------------- sessions and DST --
def test_sessions_follow_each_city_dst():
    # 2024-03-20: New York already on summer time (since 10 March), London not yet (31 March).
    assert session_label(ep("2024-03-20T12:30:00")) == "LONDON_NY_OVERLAP"
    # Same UTC clock in January: New York opens at 13:00 UTC, so 12:30 is London only.
    assert session_label(ep("2024-01-10T12:30:00")) == "LONDON"
    assert session_label(ep("2024-01-13T12:30:00")) == "OFF"        # Saturday
    assert session_label(ep("2024-01-10T01:00:00")) == "TOKYO"


def test_europe_rome_conversion_across_dst():
    assert rome_time(ep("2024-03-30T12:00:00")).hour == 13       # CET
    assert rome_time(ep("2024-04-01T12:00:00")).hour == 14       # CEST
    assert rome_time(ep("2024-10-28T12:00:00")).hour == 13       # back to CET


def test_gaps_are_classified_weekend_daily_break_other():
    fri = ep("2023-02-10T21:45:00")
    bars = [bar(fri, 1, 1, 1, 1, M15), bar(ep("2023-02-12T23:00:00"), 1, 1, 1, 1, M15),
            bar(ep("2023-02-13T21:45:00"), 1, 1, 1, 1, M15), bar(ep("2023-02-13T23:00:00"), 1, 1, 1, 1, M15),
            bar(ep("2023-02-14T10:00:00"), 1, 1, 1, 1, M15)]
    report = gap_report(bars, M15)
    assert report["weekend_gaps"] == 1 and report["daily_break_gaps"] == 1
    # Sunday 23:15 -> Monday 21:45 and Monday 23:15 -> Tuesday 10:00 are real holes
    assert [g["after_utc"][:16] for g in report["other_gaps"]] == ["2023-02-12T23:15", "2023-02-13T23:15"]


def test_dst_signature_moves_the_quiet_hour_by_one():
    bars = []
    for day, quiet in (("2023-07-11", 21), ("2023-01-10", 22)):
        for h in range(24):
            b = bar(ep(f"{day}T{h:02d}:00:00"), 1, 1, 1, 1, M15)
            b["n_ticks"] = 1 if h == quiet else 100
            bars.append(b)
    sig = dst_transition_check(bars)
    assert sig["US_DST"] == 21 and sig["US_STANDARD"] == 22 and sig["shift_hours"] == 1


# ------------------------------------------------------------- detectors --
def h4_series():
    """20 quiet bars, a bullish impulse, then a pullback that reaches 50% on bar 23."""
    t0 = ep("2023-03-06T00:00:00")
    bars = [bar(t0 + n * 14400, 100.0, 100.6, 99.6, 100.1) for n in range(20)]
    bars.append(bar(t0 + 20 * 14400, 100.0, 103.2, 99.9, 103.0))      # impulse, body 3.0
    bars.append(bar(t0 + 21 * 14400, 103.0, 103.5, 102.8, 103.3))     # leg extreme 103.5
    bars.append(bar(t0 + 22 * 14400, 103.3, 103.4, 102.6, 102.7))     # 25% retrace
    bars.append(bar(t0 + 23 * 14400, 102.7, 102.8, 101.6, 101.8))     # 52% retrace -> event
    bars.extend(bar(t0 + n * 14400, 101.8, 102.2, 101.5, 102.0) for n in range(24, 30))
    return bars


def test_impulse_uses_previous_bar_atr_and_fires_once():
    h4 = h4_series()
    atr = wilder_atr(h4, PARAMS["atr_period"])
    impulses = detect_impulses(h4, atr, PARAMS)
    assert [i["i"] for i in impulses] == [20] and impulses[0]["direction"] == 1
    assert impulses[0]["atr_prev"] == pytest.approx(atr[19])


def test_pullback_event_is_known_at_the_close_of_its_bar():
    h4 = h4_series()
    events = detect_pullbacks(h4, detect_impulses(h4, wilder_atr(h4, 14), PARAMS), PARAMS)
    assert len(events) == 1
    ev = events[0]
    assert ev["pullback_j"] == 23 and ev["known_at"] == h4[23]["end"]
    assert ev["anchor"] == 99.9 and ev["leg_extreme"] == 103.5
    assert ev["retrace"] == pytest.approx((103.5 - 101.6) / (103.5 - 99.9))
    assert ev["pullback_extreme"] == 101.6


def test_pullback_through_the_anchor_cancels():
    h4 = h4_series()
    h4[22] = dict(h4[22], low=99.8)
    events = detect_pullbacks(h4, detect_impulses(h4, wilder_atr(h4, 14), PARAMS), PARAMS)
    assert events == []


def test_future_bars_cannot_change_a_past_event():
    h4 = h4_series()
    base = detect_pullbacks(h4, detect_impulses(h4, wilder_atr(h4, 14), PARAMS), PARAMS)
    future = [dict(b, high=b["high"] + 50, low=b["low"] - 50) if n > 23 else b
              for n, b in enumerate(h4)]
    again = detect_pullbacks(future, detect_impulses(future, wilder_atr(future, 14), PARAMS), PARAMS)
    assert again[0] == base[0]


def test_detector_health_is_not_pathological_on_quiet_data():
    h4 = h4_series()
    result = {"n_h4_bars_in_split": len(h4),
              "impulses_in_split": detect_impulses(h4, wilder_atr(h4, 14), PARAMS)}
    result["pullbacks_in_split"] = detect_pullbacks(h4, result["impulses_in_split"], PARAMS)
    health = detector_health(result)
    assert health["IMPULSE"]["allowed_for_discovery"] is True
    assert health["PULLBACK"]["status"] != "PATHOLOGICAL"


# ----------------------------------------------- M15 confirmation and outcome --
def m15_after(t, closes, highs=None, lows=None, spread=0.2):
    out = []
    for n, c in enumerate(closes):
        h = highs[n] if highs else c + 0.1
        lo = lows[n] if lows else c - 0.1
        out.append(bar(t + n * 900, c, h, lo, c, M15, spread))
    return out


def test_confirmation_only_reads_bars_after_the_h4_close():
    t = ep("2023-03-10T08:00:00")
    before = [bar(t - 900, 0, 999, -999, 0, M15)]          # wild bar before T must be ignored
    m15 = before + m15_after(t, [101.8, 101.9, 102.2, 102.3], highs=[101.9, 102.0, 102.3, 102.4])
    conf = confirm_m15(m15, t, 1, 99.9, PARAMS)
    assert conf["status"] == "CONFIRMED" and conf["index"] == 3     # first close above prior highs
    assert all(b["start"] >= t for b in conf["window"])


def test_confirmation_cancelled_when_anchor_breaks_and_unconfirmed_after_window():
    t = ep("2023-03-10T08:00:00")
    broken = m15_after(t, [101.0, 100.0, 99.5], lows=[100.9, 99.95, 99.8])
    assert confirm_m15(broken, t, 1, 99.9, PARAMS)["status"] == "CANCELLED_ANCHOR_BROKEN"
    flat = m15_after(t, [101.0] * 20, highs=[101.5] * 20)
    assert confirm_m15(flat, t, 1, 99.9, PARAMS)["status"] == "UNCONFIRMED"


def test_long_outcome_target_stop_same_bar_timeout_and_censoring():
    t = ep("2023-03-10T08:00:00")
    end = t + 10 * 86400
    # entry at ask_open of bar 0 = 102.2; stop 101.2 -> risk 1.0; target 104.2 on BID
    win = m15_after(t, [102.0, 103.0, 104.3], highs=[102.1, 103.1, 104.3], lows=[101.9, 102.9, 104.0])
    r = simulate_outcome(win, 0, 1, 101.2, PARAMS, end)
    assert r["exit_reason"] == "TARGET" and r["realized_r"] == pytest.approx(2.0)
    assert r["spread_cost_r"] == pytest.approx(0.2)
    loss = m15_after(t, [102.0, 101.0], lows=[101.9, 101.1])
    assert simulate_outcome(loss, 0, 1, 101.2, PARAMS, end)["realized_r"] == pytest.approx(-1.0)
    both = m15_after(t, [102.0], highs=[105.0], lows=[101.0])
    assert simulate_outcome(both, 0, 1, 101.2, PARAMS, end)["exit_reason"] == "STOP"
    flat = m15_after(t, [102.5] * PARAMS["horizon_m15_bars"])
    timeout = simulate_outcome(flat, 0, 1, 101.2, PARAMS, end)
    # entry on ASK 102.7, risk 1.5, exit on BID close 102.5
    assert timeout["exit_reason"] == "TIMEOUT" and timeout["realized_r"] == pytest.approx(-0.2 / 1.5)
    short_split = simulate_outcome(flat, 0, 1, 101.2, PARAMS, t + 3600)
    assert short_split["status"] == "CENSORED"


def test_short_fills_on_bid_and_exits_on_ask():
    t = ep("2023-03-10T08:00:00")
    # short entry at BID open 100.0, stop 101.0 -> risk 1.0, target 98.0 must be hit by the ASK
    path = m15_after(t, [100.0, 98.1], highs=[100.1, 98.3], lows=[99.9, 97.95])
    r = simulate_outcome(path, 0, -1, 101.0, PARAMS, t + 86400)
    assert r["status"] == "CENSORED"           # ask low 98.15 never reaches 98.0, path ends early
    deeper = m15_after(t, [100.0, 97.5], highs=[100.1, 97.9], lows=[99.9, 97.5])
    r2 = simulate_outcome(deeper + m15_after(t + 1800, [97.5] * 2), 0, -1, 101.0, PARAMS, t + 86400)
    assert r2["exit_reason"] == "TARGET" and r2["realized_r"] == pytest.approx(2.0)


def test_run_family_end_to_end_on_a_synthetic_setup():
    h4 = h4_series()
    t = h4[23]["end"]
    m15 = m15_after(t, [101.8, 101.9, 102.2, 102.3, 102.6, 103.0, 103.6, 104.4, 105.0],
                    highs=[101.9, 102.0, 102.3, 102.4, 102.7, 103.1, 103.7, 104.5, 105.1])
    result = run_family(h4, m15, PARAMS, h4[0]["start"], h4[-1]["end"] + 86400, controls=False)
    [row] = result["events"]
    assert row["confirmation"] == "CONFIRMED" and row["entry_time"] == m15[3]["start"]
    assert row["status"] == "CLOSED" and row["exit_reason"] == "TARGET"
    assert row["entry_time"] > row["known_at"]


# ------------------------------------------------------------ statistics --
def test_wilson_and_month_block_bootstrap_are_deterministic():
    w = wilson(30, 100)
    assert w["low"] == pytest.approx(0.2189, abs=1e-3) and w["high"] == pytest.approx(0.3958, abs=1e-3)
    rows = [{"entry_time": ep(f"2023-{m:02d}-15T00:00:00"), "v": (m % 3) - 1.0} for m in range(1, 13)]
    a = block_bootstrap_mean(rows, lambda r: r["v"], n_boot=500)
    b = block_bootstrap_mean(rows, lambda r: r["v"], n_boot=500)
    assert a == b and a["n_blocks"] == 12


# ---------------------------------------------------- pre-registration --
def test_prereg_is_frozen_and_tampering_is_refused(tmp_path):
    data = json.loads(PREREG.read_text(encoding="utf-8"))
    assert data["params_sha256"] == prereg_mod.canonical_sha256(data["params"])
    data["params"]["target_r"] = 3.0
    tampered = tmp_path / "p.json"
    tampered.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(prereg_mod.PreregViolation):
        prereg_mod.load(str(tampered))


def test_same_hypothesis_cannot_rerun_with_other_params(tmp_path):
    prereg = prereg_mod.load(str(PREREG))
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({prereg["hypothesis_id"]: {"params_sha256": "other", "runs": []}}))
    with pytest.raises(prereg_mod.PreregViolation):
        prereg_mod.check_hypothesis_registry(str(registry), prereg)


@pytest.mark.parametrize("split", ["locked_validation", "final_holdout", "anything"])
def test_runner_refuses_protected_splits(split):
    with pytest.raises(prereg_mod.PreregViolation):
        prereg_mod.split_window(prereg_mod.load(str(PREREG)), split)


def test_discovery_and_validation_windows_match_the_phase7_partitions():
    manifest = json.loads((RESEARCH / "phase7" / "partition_manifest_v1.json").read_text())
    segments = {s["name"]: s for s in manifest["payload"]["segments"]}
    prereg = prereg_mod.load(str(PREREG))
    assert prereg["splits"]["discovery"]["start_utc"][:10] == segments["development_discovery"]["declared_start"]
    assert prereg["splits"]["internal_validation"]["start_utc"][:10] == \
        segments["development_internal_validation"]["declared_start"]


# --------------------------------------------------------------- runner --
def test_smoke_run_on_synthetic_tick_files(tmp_path, monkeypatch):
    decoded = tmp_path / "decoded"
    for day in ("2023-02-06", "2023-02-07"):
        folder = decoded / day[:4]
        folder.mkdir(parents=True, exist_ok=True)
        with gzip.open(folder / f"{day}.csv.gz", "wt", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["epoch_ms", "bid", "ask", "bid_vol", "ask_vol"])
            for ts, bid, ask in synthetic_ticks(ep(f"{day}T00:00:00"), 24 * 60, step=120):
                writer.writerow([ts, bid, ask, 1.0, 1.0])
    monkeypatch.setattr(run_experiment, "DATA_DIR", str(tmp_path / "data"))
    summary = run_experiment.main(["--split", "discovery", "--smoke-days", "4",
                                   "--phase7-decoded", str(decoded), "--phase6-decoded", str(decoded),
                                   "--manifest", str(tmp_path / "absent.json"),
                                   "--reference-h4", str(tmp_path / "absent.csv"),
                                   "--out", str(tmp_path / "out")])
    assert summary["smoke"] is True and "events" not in summary          # no statistics in smoke mode
    assert summary["data_checks"]["alignment_mismatches"] == []
    assert summary["data_checks"]["tick_audit"]["verdict"] == "PASS"
    assert summary["data_checks"]["manifest"]["verdict"] == "MISSING"
    missing = summary["data_checks"]["missing_day_files"]
    assert "2023-02-05" in missing and "2023-02-06" not in missing and "2023-02-08" not in missing
    assert summary["n_m15_bars"] == 2 * 96
    assert (tmp_path / "out" / "summary.json").exists()


def test_python_side_never_trades():
    text = "\n".join(p.read_text(encoding="utf-8")
                     for p in (RESEARCH / "behavior_lab_v1").glob("*.py"))
    for banned in ("order_send", "OrderSend", "MetaTrader5", "requests.", "urllib", "WebRequest"):
        assert banned not in text


# --------------------------------------------------- BL-01 analysis, decision, report --
from behavior_lab_v1 import bl01  # noqa: E402
from behavior_lab_v1.analysis import (cost_sensitivity, profit_factor,  # noqa: E402
                                      stratified_vs_control)
from behavior_lab_v1.decision import decide  # noqa: E402
from behavior_lab_v1.report import render  # noqa: E402


def trade(r, direction=1, session="LONDON", atr=10.0, month=1, spread_r=0.05):
    return {"status": "CLOSED", "exit_reason": "TARGET" if r > 0 else "STOP", "realized_r_net": r,
            "realized_r": r, "spread_cost_r": spread_r, "direction": direction, "session": session,
            "atr_h4": atr, "entry_time": ep(f"2023-{month:02d}-10T09:00:00")}


def test_profit_factor_and_breakeven():
    rows = [trade(2.0), trade(-1.0), trade(-1.0)]
    assert profit_factor(rows) == pytest.approx(1.0)
    costs = cost_sensitivity(rows, 2.0)
    assert costs["breakeven_win_rate_gross"] == pytest.approx(1 / 3)
    assert costs["extra_0.10R"] == pytest.approx(-0.1) and costs["double_spread"] == pytest.approx(-0.05)


def test_stratified_comparison_only_compares_like_with_like():
    # events all in LONDON high-vol; controls good in LONDON, bad in TOKYO: a raw comparison
    # would flatter the events, the stratified one must not
    controls = [trade(2.0 if n % 2 else -1.0, session="LONDON", atr=30.0) for n in range(40)] + \
               [trade(-1.0, session="TOKYO", atr=30.0) for _ in range(40)] + \
               [trade(-1.0, session="TOKYO", atr=a) for a in (1.0, 2.0) for _ in range(20)]
    events = [trade(2.0 if n % 2 else -1.0, session="LONDON", atr=30.0) for n in range(20)]
    res = stratified_vs_control(events, controls)
    assert res["adjusted_delta_expectancy_r"] == pytest.approx(0.0)
    assert res["cells_used"] == 1 and res["events_without_comparable_control"] == 0


def base_summary(**over):
    s = {"smoke": False,
         "data_checks": {"tick_audit": {"verdict": "PASS"}, "alignment_mismatches": [],
                         "reference_h4_mismatches": [], "manifest": {"verdict": "MATCH"}},
         "detector_health": {"IMPULSE": {"status": "NORMAL"}, "PULLBACK": {"status": "NORMAL"}},
         "events": {"n_closed": 80, "expectancy_r_net": 0.2,
                    "expectancy_r_net_ci95_month_blocks": {"low": 0.05, "high": 0.4}},
         "vs_control_stratified": {"adjusted_delta_expectancy_r": 0.1, "cells_used": 5, "cells_event_better": 4},
         "stability": {"quarters_with_n_ge_5": 5, "quarters_positive": 4},
         "cost_sensitivity": {"extra_0.10R": 0.1},
         "by_direction": {"BUY": {"n_closed": 40, "expectancy_r_net": 0.2},
                          "SELL": {"n_closed": 40, "expectancy_r_net": 0.0}},
         "hour_profile": {"max_hour_share": 0.2}}
    s.update(over)
    return s


def test_decision_rules_go_investigate_stop():
    assert decide(base_summary())["decision"] == "GO"
    weak = base_summary(events={"n_closed": 80, "expectancy_r_net": 0.05,
                                "expectancy_r_net_ci95_month_blocks": {"low": -0.1, "high": 0.2}})
    inv = decide(weak)
    assert inv["decision"] == "INVESTIGATE" and "month-block CI95 low > 0" in inv["reasons"]
    small = base_summary(events={"n_closed": 12, "expectancy_r_net": 0.9})
    assert decide(small)["kind"] == "SAMPLE"
    negative = base_summary(events={"n_closed": 80, "expectancy_r_net": -0.3,
                                    "expectancy_r_net_ci95_month_blocks": {"low": -0.5, "high": -0.1}})
    assert decide(negative)["kind"] == "NEGATIVE"
    broken = base_summary(data_checks={"tick_audit": {"verdict": "FAIL"}, "alignment_mismatches": [],
                                       "reference_h4_mismatches": [], "manifest": {"verdict": "MATCH"}})
    assert decide(broken)["kind"] == "DATA_OR_DETECTOR"
    clock = base_summary(hour_profile={"max_hour_share": 0.6})
    assert decide(clock)["decision"] == "INVESTIGATE"


def _write_ticks(decoded, days):
    for day in days:
        folder = decoded / day[:4]
        folder.mkdir(parents=True, exist_ok=True)
        with gzip.open(folder / f"{day}.csv.gz", "wt", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["epoch_ms", "bid", "ask", "bid_vol", "ask_vol"])
            for ts, bid, ask in synthetic_ticks(ep(f"{day}T00:00:00"), 24 * 60, step=120):
                writer.writerow([ts, bid, ask, 1.0, 1.0])


def test_full_run_report_has_every_section(tmp_path, monkeypatch):
    decoded = tmp_path / "decoded"
    _write_ticks(decoded, ["2023-02-06", "2023-02-07", "2023-02-08"])
    monkeypatch.setattr(run_experiment, "DATA_DIR", str(tmp_path / "data"))
    full = run_experiment.main(["--split", "discovery", "--phase7-decoded", str(decoded),
                                "--phase6-decoded", str(decoded), "--manifest", str(tmp_path / "x.json"),
                                "--reference-h4", str(tmp_path / "x.csv"), "--out", str(tmp_path / "out")])
    assert full["status"] == "EXPLORATORY_DISCOVERY"
    assert full["decision"]["decision"] == "STOP"          # manifest missing on a full run
    assert full["peak_rss_mb"] is None or full["peak_rss_mb"] > 0
    outputs = json.loads((tmp_path / "out" / "outputs.sha256.json").read_text())
    assert set(outputs) == {"summary.json", "events.csv", "controls.csv", "run.log"}
    pre = bl01.preflight(str(decoded), str(decoded), str(tmp_path / "x.json"))
    text = render(pre, None, full, [])
    for n in range(1, 8):
        assert f"## {n}." in text


def test_bl01_stops_before_running_when_preflight_fails(tmp_path, monkeypatch):
    decoded = tmp_path / "decoded"
    _write_ticks(decoded, ["2023-02-06"])
    monkeypatch.setattr(bl01, "RUNS", str(tmp_path / "runs"))
    monkeypatch.setattr(run_experiment, "DATA_DIR", str(tmp_path / "data"))
    code = bl01.main(["--phase7-decoded", str(decoded), "--phase6-decoded", str(decoded),
                      "--manifest", str(tmp_path / "absent.json")])
    assert code == 1
    [report] = list((tmp_path / "runs").glob("*/report.md"))
    text = report.read_text(encoding="utf-8")
    assert "STOP obbligatorio" in text and "tick manifest MISSING" in text
    assert not list((tmp_path / "runs").glob("*/smoke"))        # nothing ran after the blocker


def test_manifest_check_uses_the_registry_content_hash(tmp_path, monkeypatch):
    """The registry records a canonical-JSON hash of the manifest; raw bytes differ with formatting."""
    import hashlib
    sys.path.insert(0, str(RESEARCH / "phase6_6"))
    from canonical_utils import canonical_sha256
    content = {"days": {"2023-02-04": {"ticks": 10, "sha256": "ab"}}, "symbol": "XAUUSD"}
    pretty, compact = tmp_path / "pretty.json", tmp_path / "compact.json"
    pretty.write_text(json.dumps(content, indent=4))
    compact.write_text(json.dumps(content, separators=(",", ":")))
    assert hashlib.sha256(pretty.read_bytes()).hexdigest() != hashlib.sha256(compact.read_bytes()).hexdigest()
    monkeypatch.setattr(run_experiment, "EXPECTED_MANIFEST_CONTENT_HASH", canonical_sha256(content))
    for path in (pretty, compact):
        check = run_experiment.manifest_check(str(path))
        assert check["verdict"] == "MATCH" and check["file_sha256"] != check["sha256"]
    changed = tmp_path / "changed.json"
    changed.write_text(json.dumps(dict(content, symbol="XAGUSD")))
    assert run_experiment.manifest_check(str(changed))["verdict"] == "MISMATCH"


def test_expected_manifest_hash_matches_the_dataset_registry():
    reg = json.loads((RESEARCH / "phase7" / "dataset_version_registry_v2.json").read_text())
    text = json.dumps(reg)
    assert run_experiment.EXPECTED_MANIFEST_CONTENT_HASH in text


def test_detector_health_ignores_warmup_detections():
    """Real smoke run (2026-10-12): 17 impulses found over warmup + split were divided by the
    39 split bars only, giving a false PATHOLOGICAL. Warmup detections must not count."""
    h4 = h4_series()
    impulses = detect_impulses(h4, wilder_atr(h4, 14), PARAMS)
    assert impulses, "the synthetic series must contain at least one impulse"
    last_event_end = max(h4[e["i"]]["end"] for e in impulses)
    split_start = last_event_end + 1
    split_end = h4[-1]["end"]
    result = run_family(h4, [], PARAMS, split_start, split_end, controls=False)
    assert result["impulses"] and result["impulses_in_split"] == []
    health = detector_health(result)
    assert health["IMPULSE"]["n_events"] == 0
    assert health["IMPULSE"]["status"] != "PATHOLOGICAL"
    inside = run_family(h4, [], PARAMS, h4[0]["end"], split_end, controls=False)
    assert len(inside["impulses_in_split"]) == len(impulses)
