#!/usr/bin/env python3
"""Phase 7.28 — same-feed A/B for BB_SQUEEZE squeezeBars contamination.

Stream A: shared squeezeBars/consumed mutated on D1+H4+H1 passes
Stream B: TF-scoped — only D1 mutates

Signals counted on D1 pass only.
"""
from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))
D1_CSV = os.path.join(
    ROOT, "server", "research_scripts", "phase7", "phase7_9h", "raw_data", "nxs_d1_gold_phase79h.csv"
)

PASS_ORDER = ("D1", "H4", "H1")
PROFILE_TF = "D1"
LOOKBACK = 150
PERCENTILE_MAX = 20.0
MIN_SQUEEZE = 5
BB_PERIOD = 20
BB_DEV = 2.0
TF_MINUTES = {"D1": 1440, "H4": 240, "H1": 60}


def _parse_t(s: str) -> datetime:
    # D1 file uses "2019.01.02 00:00"
    return datetime.strptime(s.strip(), "%Y.%m.%d %H:%M").replace(tzinfo=timezone.utc)


def load_d1(path: str) -> List[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "t": _parse_t(r["time"]),
                "o": float(r["open"]),
                "h": float(r["high"]),
                "l": float(r["low"]),
                "c": float(r["close"]),
            })
    return rows


def resample_from_d1(d1: List[dict], minutes: int) -> List[dict]:
    """Synthetic intra-day bars from D1 OHLC (same calendar day).
    Not broker-faithful — only for contamination mechanism stress.
    For H4: 6 bars/day; H1: 24 bars/day using D1 OHLC envelope.
    """
    out = []
    n_slots = 1440 // minutes
    for b in d1:
        base = b["t"]
        for s in range(n_slots):
            # distribute OHLC crudely inside the day
            t = datetime.fromtimestamp(base.timestamp() + s * minutes * 60, tz=timezone.utc)
            # linear blend open→close with high/low retained
            frac = (s + 1) / n_slots
            c = b["o"] + (b["c"] - b["o"]) * frac
            o = b["o"] + (b["c"] - b["o"]) * (s / n_slots)
            out.append({"t": t, "o": o, "h": max(b["h"], o, c), "l": min(b["l"], o, c), "c": c})
    return out


def bollinger_bw(closes: np.ndarray, i: int) -> Optional[float]:
    if i < BB_PERIOD - 1:
        return None
    window = closes[i - BB_PERIOD + 1 : i + 1]
    mid = float(window.mean())
    if mid <= 0:
        return None
    std = float(window.std(ddof=0))
    up = mid + BB_DEV * std
    lo = mid - BB_DEV * std
    return (up - lo) / mid


def bands_at(closes: np.ndarray, i: int) -> Optional[Tuple[float, float, float]]:
    if i < BB_PERIOD - 1:
        return None
    window = closes[i - BB_PERIOD + 1 : i + 1]
    mid = float(window.mean())
    std = float(window.std(ddof=0))
    return mid + BB_DEV * std, mid - BB_DEV * std, mid


class BBState:
    __slots__ = ("last_bar_time", "squeeze_bars", "consumed")

    def __init__(self):
        self.last_bar_time = None
        self.squeeze_bars = 0
        self.consumed = False


def evaluate(state: BBState, bars: List[dict], closes: np.ndarray, i: int) -> Optional[str]:
    if i + 1 >= len(bars) or i < LOOKBACK + 2:
        return None
    cur_bar0 = bars[i + 1]["t"]
    if state.last_bar_time == cur_bar0:
        return None
    state.last_bar_time = cur_bar0

    bw1 = bollinger_bw(closes, i)
    bw2 = bollinger_bw(closes, i - 1)
    if bw1 is None or bw1 <= 0 or bw2 is None:
        return None

    below = 0
    for j in range(i - LOOKBACK, i - 1):
        if j < BB_PERIOD:
            continue
        bwi = bollinger_bw(closes, j)
        if bwi is not None and bwi < bw1:
            below += 1
    percentile = 100.0 * below / LOOKBACK
    is_squeeze = percentile <= PERCENTILE_MAX

    if is_squeeze:
        state.squeeze_bars += 1
    else:
        state.squeeze_bars = 0
        state.consumed = False
        return None

    if state.squeeze_bars < MIN_SQUEEZE or state.consumed:
        return None

    bands = bands_at(closes, i)
    if bands is None:
        return None
    up, lo, _mid = bands
    c1 = bars[i]["c"]
    expanding = bw1 > bw2
    if not expanding:
        return None
    if c1 > up:
        state.consumed = True
        return "BUY"
    if c1 < lo:
        state.consumed = True
        return "SELL"
    return None


def latest_closed(bars: List[dict], asof: datetime) -> Optional[int]:
    times = [b["t"] for b in bars]
    lo, hi = 0, len(times) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if times[mid] <= asof:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    if best is None or best < 1:
        return None
    while best >= 1 and best + 1 < len(bars) and bars[best + 1]["t"] > asof:
        best -= 1
    if best + 1 >= len(bars) or best < LOOKBACK + 2:
        return None
    return best


def run_stream(series: Dict[str, List[dict]], closes: Dict[str, np.ndarray], scoped: bool):
    state = BBState()
    signals = []
    d1 = series["D1"]
    for i in range(LOOKBACK + 3, len(d1) - 1):
        asof = d1[i + 1]["t"]
        for tf in PASS_ORDER:
            if scoped and tf != PROFILE_TF:
                continue
            bars = series[tf]
            j = latest_closed(bars, asof)
            if j is None:
                continue
            sig = evaluate(state, bars, closes[tf], j)
            if sig and tf == PROFILE_TF:
                signals.append((d1[i]["t"], sig))
    return signals


def classify(n_a: int, n_b: int) -> str:
    if n_b == 0 and n_a == 0:
        return "INSUFFICIENT_EVIDENCE"
    if n_b == 0:
        return "DEFECT_CONFIRMED_MATERIAL_IMPACT"
    ratio = n_a / n_b
    if ratio <= 0.25 or abs(n_b - n_a) >= max(5, 0.4 * n_b):
        return "DEFECT_CONFIRMED_MATERIAL_IMPACT"
    if abs(n_b - n_a) <= 2 and ratio >= 0.9:
        return "DEFECT_CONFIRMED_LOW_IMPACT"
    if ratio < 0.9:
        return "DEFECT_CONFIRMED_MATERIAL_IMPACT"
    return "DEFECT_CONFIRMED_LOW_IMPACT"


def build() -> dict:
    d1 = load_d1(D1_CSV)
    # For H4/H1 contamination stress use synthetic denser series from D1.
    # Flag clearly — this measures mechanism sensitivity, not broker parity.
    series = {
        "D1": d1,
        "H4": resample_from_d1(d1, 240),
        "H1": resample_from_d1(d1, 60),
    }
    closes = {tf: np.array([b["c"] for b in bars], dtype=float) for tf, bars in series.items()}
    sig_a = run_stream(series, closes, scoped=False)
    sig_b = run_stream(series, closes, scoped=True)
    set_a = {(t.isoformat(), d) for t, d in sig_a}
    set_b = {(t.isoformat(), d) for t, d in sig_b}
    return {
        "phase": "7.28",
        "strategy": "BB_SQUEEZE",
        "defect_class": "ACCUMULATOR_STATE_CONTAMINATION",
        "profile_tf": PROFILE_TF,
        "data": {
            "source": "server/research_scripts/phase7/phase7_9h/raw_data/nxs_d1_gold_phase79h.csv",
            "n_d1_bars": len(d1),
            "range": [d1[0]["t"].isoformat(), d1[-1]["t"].isoformat()],
            "higher_tf_note": "H1/H4 synthetically densified from D1 OHLC for mechanism stress only",
        },
        "stream_A_contaminated_signals_on_profile_pass": len(sig_a),
        "stream_B_tf_scoped_signals": len(sig_b),
        "overlap_events": len(set_a & set_b),
        "only_A": len(set_a - set_b),
        "only_B": len(set_b - set_a),
        "suppression_vs_scoped": None if not sig_b else round(1.0 - len(sig_a) / len(sig_b), 4),
        "decision": classify(len(sig_a), len(sig_b)),
        "method_note": (
            "Python replica of squeezeBars/consumed + BB percentile gate. "
            "H1/H4 legs are synthetic densifications — sufficient to show whether "
            "foreign-TF mutations corrupt the D1 accumulator; not MT5 parity."
        ),
    }


def main():
    import json
    import sys

    sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
    from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

    payload = build()
    doc = wrap_with_provenance(payload, "phase7_28_defect_impact_batch/sim_bb_squeeze_abc.py")
    out = os.path.join(PHASE_DIR, "bb_squeeze_abc_impact_v1.json")
    save_json(out, doc)
    print(json.dumps({
        "decision": payload["decision"],
        "A": payload["stream_A_contaminated_signals_on_profile_pass"],
        "B": payload["stream_B_tf_scoped_signals"],
        "sha": doc["canonical_sha256"][:16],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
