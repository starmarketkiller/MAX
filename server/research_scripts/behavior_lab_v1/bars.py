"""Bars from ticks, UTC-aligned, and the H4/M15 alignment check.

Aggregation rule is the one of phase7/phase7_1/build_h4_bars_p71.py, widened
to any bar length: OHLC on BID, open = earliest tick, close = latest tick (a
tie on the timestamp keeps the later row), buckets aligned on UTC midnight.
On top of that each bar keeps the ASK OHLC, so entries and exits can be priced
on the side that would actually fill, and spread statistics.

A bar is labelled by its start time. It becomes known only at its end time
(start + length): nothing downstream may read a bar before that.
"""
from __future__ import annotations

from datetime import datetime, timezone

M15 = 15
H4 = 240


def bucket_start(ts_ms, minutes):
    size = minutes * 60
    return (ts_ms // 1000) // size * size


class BarBuilder:
    def __init__(self, minutes):
        self.minutes = minutes
        self._bars = {}

    def add(self, ts, bid, ask):
        key = bucket_start(ts, self.minutes)
        rec = self._bars.get(key)
        if rec is None:
            self._bars[key] = {"open": bid, "high": bid, "low": bid, "close": bid,
                               "ask_open": ask, "ask_high": ask, "ask_low": ask, "ask_close": ask,
                               "open_ms": ts, "close_ms": ts, "spread_sum": ask - bid,
                               "spread_max": ask - bid, "n_ticks": 1}
            return
        if ts < rec["open_ms"]:
            rec["open"], rec["ask_open"], rec["open_ms"] = bid, ask, ts
        if ts >= rec["close_ms"]:
            rec["close"], rec["ask_close"], rec["close_ms"] = bid, ask, ts
        rec["high"] = max(rec["high"], bid)
        rec["low"] = min(rec["low"], bid)
        rec["ask_high"] = max(rec["ask_high"], ask)
        rec["ask_low"] = min(rec["ask_low"], ask)
        rec["spread_sum"] += ask - bid
        rec["spread_max"] = max(rec["spread_max"], ask - bid)
        rec["n_ticks"] += 1

    def bars(self):
        out = []
        size = self.minutes * 60
        for key in sorted(self._bars):
            rec = self._bars[key]
            out.append({
                "start": key, "end": key + size,
                "time_utc": datetime.fromtimestamp(key, tz=timezone.utc).isoformat(),
                "open": rec["open"], "high": rec["high"], "low": rec["low"], "close": rec["close"],
                "ask_open": rec["ask_open"], "ask_high": rec["ask_high"],
                "ask_low": rec["ask_low"], "ask_close": rec["ask_close"],
                "avg_spread": rec["spread_sum"] / rec["n_ticks"], "max_spread": rec["spread_max"],
                "n_ticks": rec["n_ticks"], "first_tick_ms": rec["open_ms"],
                "last_tick_ms": rec["close_ms"],
            })
        return out


def build_bars(ticks, minutes_list, audit=None):
    """One pass over the ticks, one bar series per requested length."""
    builders = {m: BarBuilder(m) for m in minutes_list}
    for ts, bid, ask in ticks:
        if audit is not None:
            audit.add(ts, bid, ask)
        for builder in builders.values():
            builder.add(ts, bid, ask)
    return {m: b.bars() for m, b in builders.items()}


def resample(bars, minutes):
    """Aggregate finer bars into `minutes` bars with the same rule as ticks."""
    size = minutes * 60
    out = {}
    for bar in bars:
        key = bar["start"] // size * size
        rec = out.get(key)
        if rec is None:
            out[key] = dict(bar, start=key, end=key + size,
                            time_utc=datetime.fromtimestamp(key, tz=timezone.utc).isoformat(),
                            spread_sum=bar["avg_spread"] * bar["n_ticks"])
            continue
        if bar["first_tick_ms"] < rec["first_tick_ms"]:
            rec.update(open=bar["open"], ask_open=bar["ask_open"], first_tick_ms=bar["first_tick_ms"])
        if bar["last_tick_ms"] >= rec["last_tick_ms"]:
            rec.update(close=bar["close"], ask_close=bar["ask_close"], last_tick_ms=bar["last_tick_ms"])
        for field, fn in (("high", max), ("low", min), ("ask_high", max), ("ask_low", min),
                          ("max_spread", max)):
            rec[field] = fn(rec[field], bar[field])
        rec["spread_sum"] += bar["avg_spread"] * bar["n_ticks"]
        rec["n_ticks"] += bar["n_ticks"]
    result = []
    for key in sorted(out):
        rec = out[key]
        rec["avg_spread"] = rec.pop("spread_sum") / rec["n_ticks"]
        result.append(rec)
    return result


PRICE_FIELDS = ("open", "high", "low", "close", "ask_open", "ask_high", "ask_low", "ask_close")


def check_alignment(h4_bars, m15_bars, tolerance=1e-9):
    """Every H4 bar must equal the aggregation of the M15 bars inside it.

    Same ticks, two bar lengths: any difference means a bucketing or tie-break
    bug, not a market effect. Returns mismatches; empty means aligned."""
    rebuilt = {b["start"]: b for b in resample(m15_bars, H4)}
    mismatches = []
    for bar in h4_bars:
        other = rebuilt.get(bar["start"])
        if other is None:
            mismatches.append({"start": bar["start"], "field": "missing_m15"})
            continue
        for field in PRICE_FIELDS:
            if abs(bar[field] - other[field]) > tolerance:
                mismatches.append({"start": bar["start"], "field": field,
                                   "h4": bar[field], "m15": other[field]})
        if bar["n_ticks"] != other["n_ticks"]:
            mismatches.append({"start": bar["start"], "field": "n_ticks",
                               "h4": bar["n_ticks"], "m15": other["n_ticks"]})
    extra = set(rebuilt) - {b["start"] for b in h4_bars}
    for start in sorted(extra):
        mismatches.append({"start": start, "field": "missing_h4"})
    return mismatches


def compare_with_reference_h4(h4_bars, reference_rows, tolerance=1e-6):
    """Parity with phase7_1 xauusd_h4_bars_p71.csv (bar_epoch, open, high, low, close, n_ticks)."""
    ours = {b["start"]: b for b in h4_bars}
    mismatches = []
    for row in reference_rows:
        epoch = int(row["bar_epoch"])
        bar = ours.get(epoch)
        if bar is None:
            continue
        for field in ("open", "high", "low", "close"):
            if abs(float(row[field]) - bar[field]) > tolerance:
                mismatches.append({"start": epoch, "field": field, "ref": float(row[field]),
                                   "ours": bar[field]})
        if int(row["n_ticks"]) != bar["n_ticks"]:
            mismatches.append({"start": epoch, "field": "n_ticks", "ref": int(row["n_ticks"]),
                               "ours": bar["n_ticks"]})
    return mismatches
