#!/usr/bin/env python3
"""Phase 7.28 — same-feed A/B impact for BAR_UPDN cooldown contamination.

Stream A: shared state mutated on every multi-TF pass (D1→H4→H1→M30→M15)
Stream B: TF-scoped — only M15 (profile) may mutate state

Both count signals produced on the M15 pass only (collector keeps Profile_TF).
Deterministic. No MT5. No holdout. Stdlib + numpy only.
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))
M15_CSV = os.path.join(ROOT, "server", "research_scripts", "nxs_m15_gold_29-08.csv")

PASS_ORDER = ("D1", "H4", "H1", "M30", "M15")
PROFILE_TF = "M15"
COOLDOWN_BARS = 8
TF_MINUTES = {"M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}


def _parse_t(s: str) -> datetime:
    return datetime.strptime(s, "%Y.%m.%d %H:%M").replace(tzinfo=timezone.utc)


def load_m15(path: str) -> List[dict]:
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


def resample(m15: List[dict], minutes: int) -> List[dict]:
    buckets: Dict[datetime, dict] = {}
    order: List[datetime] = []
    for b in m15:
        epoch = int(b["t"].timestamp())
        bucket_epoch = epoch - (epoch % (minutes * 60))
        key = datetime.fromtimestamp(bucket_epoch, tz=timezone.utc)
        if key not in buckets:
            buckets[key] = {"t": key, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"]}
            order.append(key)
        else:
            x = buckets[key]
            x["h"] = max(x["h"], b["h"])
            x["l"] = min(x["l"], b["l"])
            x["c"] = b["c"]
    return [buckets[k] for k in order]


class BarUpDnState:
    __slots__ = ("last_bar_time", "last_fire_buy", "last_fire_sell")

    def __init__(self):
        self.last_bar_time = None
        self.last_fire_buy = None
        self.last_fire_sell = None


def evaluate(state: BarUpDnState, bars: List[dict], i: int, tf: str) -> Optional[str]:
    """Replica NXS_Strat_BarUpDn on closed bar i (shift1 = i, shift2 = i-1).
    curBar0 is bars[i+1].t when available (open of forming bar), else bars[i].t + tf.
    """
    if i < 1 or i + 1 >= len(bars):
        return None
    cur_bar0 = bars[i + 1]["t"]
    if state.last_bar_time == cur_bar0:
        return None
    state.last_bar_time = cur_bar0

    o1, c1, c2 = bars[i]["o"], bars[i]["c"], bars[i - 1]["c"]
    bull = c1 > o1 and o1 > c2
    bear = c1 < o1 and o1 < c2
    period_sec = TF_MINUTES[tf] * 60
    cooldown_sec = COOLDOWN_BARS * period_sec
    t0 = cur_bar0.timestamp()

    buy_ok = state.last_fire_buy is None or (t0 - state.last_fire_buy.timestamp()) >= cooldown_sec
    sell_ok = state.last_fire_sell is None or (t0 - state.last_fire_sell.timestamp()) >= cooldown_sec

    if bull and buy_ok:
        state.last_fire_buy = cur_bar0
        return "BUY"
    if bear and sell_ok:
        state.last_fire_sell = cur_bar0
        return "SELL"
    return None


def build_index(series: Dict[str, List[dict]]) -> Dict[str, Dict[datetime, int]]:
    out = {}
    for tf, bars in series.items():
        out[tf] = {b["t"]: i for i, b in enumerate(bars)}
    return out


def latest_closed_index(bars: List[dict], idx: Dict[datetime, int], asof: datetime) -> Optional[int]:
    """Largest bar open time <= asof whose next bar exists (so shift1 is closed)."""
    # binary search on times
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
    if best is None:
        return None
    # need bars[best] as shift1 ⇒ need best+1 as curBar0 forming
    if best + 1 >= len(bars):
        return None
    # prefer the bar that is the latest fully closed at asof:
    # closed bar index i where bars[i+1].t <= asof
    while best >= 0 and bars[best + 1]["t"] > asof:
        best -= 1
        if best + 1 >= len(bars):
            return None
    return best if best >= 1 else None


def run_stream(series: Dict[str, List[dict]], scoped: bool) -> List[Tuple[datetime, str]]:
    state = BarUpDnState()
    signals = []
    m15 = series["M15"]
    for i in range(2, len(m15) - 1):
        asof = m15[i + 1]["t"]  # evaluation at open of next M15 bar
        for tf in PASS_ORDER:
            if scoped and tf != PROFILE_TF:
                continue
            bars = series[tf]
            j = latest_closed_index(bars, {}, asof)
            if j is None:
                continue
            sig = evaluate(state, bars, j, tf)
            if sig and tf == PROFILE_TF:
                signals.append((m15[i]["t"], sig))
    return signals


def classify(n_a: int, n_b: int) -> str:
    if n_b == 0 and n_a == 0:
        return "INSUFFICIENT_EVIDENCE"
    if n_b == 0:
        return "DEFECT_CONFIRMED_MATERIAL_IMPACT"
    ratio = n_a / n_b
    # BREAKOUT_ACC reference: ~0 overlap / collapse → material
    if ratio <= 0.25 or abs(n_b - n_a) >= max(10, 0.5 * n_b):
        return "DEFECT_CONFIRMED_MATERIAL_IMPACT"
    if abs(n_b - n_a) <= 2 and ratio >= 0.9:
        return "DEFECT_CONFIRMED_LOW_IMPACT"
    if ratio < 0.9:
        return "DEFECT_CONFIRMED_MATERIAL_IMPACT"
    return "DEFECT_CONFIRMED_LOW_IMPACT"


def build() -> dict:
    m15 = load_m15(M15_CSV)
    series = {
        "M15": m15,
        "M30": resample(m15, 30),
        "H1": resample(m15, 60),
        "H4": resample(m15, 240),
        "D1": resample(m15, 1440),
    }
    sig_a = run_stream(series, scoped=False)
    sig_b = run_stream(series, scoped=True)
    set_a = {(t.isoformat(), d) for t, d in sig_a}
    set_b = {(t.isoformat(), d) for t, d in sig_b}
    overlap = len(set_a & set_b)
    only_a = len(set_a - set_b)
    only_b = len(set_b - set_a)
    decision = classify(len(sig_a), len(sig_b))
    return {
        "phase": "7.28",
        "strategy": "BAR_UPDN",
        "defect_class": "COOLDOWN_STATE_CONTAMINATION",
        "profile_tf": PROFILE_TF,
        "data": {
            "source": "server/research_scripts/nxs_m15_gold_29-08.csv",
            "n_m15_bars": len(m15),
            "range": [m15[0]["t"].isoformat(), m15[-1]["t"].isoformat()],
            "higher_tf": "resampled from same M15 feed (same-feed A/B)",
        },
        "stream_A_contaminated_signals_on_profile_pass": len(sig_a),
        "stream_B_tf_scoped_signals": len(sig_b),
        "overlap_events": overlap,
        "only_A": only_a,
        "only_B": only_b,
        "suppression_vs_scoped": None if not sig_b else round(1.0 - len(sig_a) / len(sig_b), 4),
        "decision": decision,
        "method_note": (
            "Python replica of NXS_Strat_BarUpDn cooldown+pattern. "
            "Pass order D1→H4→H1→M30→M15 mirrors EA multi-TF collector. "
            "Not MT5 event-level parity; mechanism impact measure."
        ),
    }


def main():
    import json
    import sys

    sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
    from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

    payload = build()
    doc = wrap_with_provenance(payload, "phase7_28_defect_impact_batch/sim_bar_updn_abc.py")
    out = os.path.join(PHASE_DIR, "bar_updn_abc_impact_v1.json")
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
