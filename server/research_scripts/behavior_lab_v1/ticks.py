"""Tick input and tick-level data checks.

Same file layout and parsing as phase7/phase7_1/build_h4_bars_p71.py: one
gzip CSV per UTC day, header epoch_ms,bid,ask,bid_vol,ask_vol.
"""
from __future__ import annotations

import csv
import gzip
import os
from datetime import datetime, timedelta, timezone


def day_path(root, day):
    return os.path.join(root, f"{day.year:04d}", f"{day.strftime('%Y-%m-%d')}.csv.gz")


def iter_days(start, end):
    """UTC days from start to end inclusive (both dates)."""
    day = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    last = datetime(end.year, end.month, end.day, tzinfo=timezone.utc)
    while day <= last:
        yield day
        day += timedelta(days=1)


def read_day(path):
    """Yield (epoch_ms, bid, ask) in file order. A missing file yields nothing."""
    if not os.path.exists(path):
        return
    with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for row in reader:
            if row:
                yield int(row[0]), float(row[1]), float(row[2])


def iter_ticks(roots, start, end, missing=None):
    """Ticks of [start, end] days, looking up each day in the first root that has it."""
    for day in iter_days(start, end):
        path = next((day_path(r, day) for r in roots if os.path.exists(day_path(r, day))), None)
        if path is None:
            if missing is not None:
                missing.append(day.strftime("%Y-%m-%d"))
            continue
        yield from read_day(path)


class TickAudit:
    """Counts tick-level defects without dropping anything: bars are built from
    every tick, and the audit says whether that is safe."""

    def __init__(self, max_spread):
        self.max_spread = max_spread
        self.n = 0
        self.crossed = 0           # ask < bid
        self.nonpositive = 0       # bid or ask <= 0
        self.non_monotonic = 0     # timestamp going backwards
        self.duplicates = 0        # same timestamp, bid and ask as the previous tick
        self.wide_spread = 0       # ask - bid > max_spread
        self.spread_sum = 0.0
        self.spread_max = 0.0
        self.first_ms = None
        self.last_ms = None
        self._prev = None

    def add(self, ts, bid, ask):
        self.n += 1
        spread = ask - bid
        if ask < bid:
            self.crossed += 1
        if bid <= 0 or ask <= 0:
            self.nonpositive += 1
        if spread > self.max_spread:
            self.wide_spread += 1
        if self._prev is not None:
            if ts < self._prev[0]:
                self.non_monotonic += 1
            elif self._prev == (ts, bid, ask):
                self.duplicates += 1
        self._prev = (ts, bid, ask)
        self.spread_sum += spread
        self.spread_max = max(self.spread_max, spread)
        self.first_ms = ts if self.first_ms is None else min(self.first_ms, ts)
        self.last_ms = ts if self.last_ms is None else max(self.last_ms, ts)

    def report(self):
        hard = self.crossed + self.nonpositive + self.non_monotonic
        return {
            "n_ticks": self.n, "crossed_ask_below_bid": self.crossed,
            "nonpositive_price": self.nonpositive, "non_monotonic_timestamp": self.non_monotonic,
            "exact_duplicates": self.duplicates, "spread_above_max": self.wide_spread,
            "max_spread_threshold": self.max_spread,
            "mean_spread": (self.spread_sum / self.n) if self.n else None,
            "max_spread_seen": self.spread_max if self.n else None,
            "first_tick_ms": self.first_ms, "last_tick_ms": self.last_ms,
            "verdict": "FAIL" if hard else ("PASS_WITH_NOTES" if self.duplicates or self.wide_spread
                                              else "PASS"),
        }
