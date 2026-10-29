"""Load daily XAUUSD CSV and build causal return rows (no invented prices)."""
from __future__ import annotations

import csv
import math
from datetime import datetime, timezone

from . import prereg as prereg_mod


def _parse_date(text):
    text = text.strip().replace("Z", "+00:00")
    if "T" in text:
        dt = datetime.fromisoformat(text)
    else:
        dt = datetime.strptime(text[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_daily_csv(path, price_column="close"):
    """Return list of {date, ts, close} sorted ascending. Raises on empty/bad file."""
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"empty CSV: {path}")
        fields = {f.lower(): f for f in reader.fieldnames}
        date_key = fields.get("date") or fields.get("time") or fields.get("time_utc")
        close_key = fields.get(price_column.lower()) or fields.get("close") or fields.get("mid")
        if date_key is None or close_key is None:
            raise ValueError(
                f"CSV must have date + {price_column} columns; got {reader.fieldnames}"
            )
        for raw in reader:
            if not raw.get(date_key):
                continue
            dt = _parse_date(raw[date_key])
            close = float(raw[close_key])
            if not math.isfinite(close) or close <= 0:
                continue
            rows.append({
                "date": dt.strftime("%Y-%m-%d"),
                "ts": int(dt.timestamp()),
                "close": close,
            })
    rows.sort(key=lambda r: r["ts"])
    if len(rows) < 2:
        raise ValueError(f"need ≥2 daily rows in {path}")
    return rows


def log_returns(closes):
    out = [None]
    for i in range(1, len(closes)):
        out.append(math.log(closes[i] / closes[i - 1]))
    return out


def trailing_return(closes, i, lookback):
    """Price return close[i]/close[i-lookback]-1; None if insufficient history."""
    j = i - lookback
    if j < 0:
        return None
    return closes[i] / closes[j] - 1.0


def realized_vol(log_rets, i, lookback, trading_days_per_year):
    """Annualized std of log returns over (i-lookback+1)..i inclusive; needs lookback points."""
    start = i - lookback + 1
    if start < 1:  # log_rets[0] is None
        return None
    window = log_rets[start : i + 1]
    if any(v is None for v in window) or len(window) < lookback:
        return None
    mean = sum(window) / len(window)
    var = sum((x - mean) ** 2 for x in window) / (len(window) - 1)
    return math.sqrt(var * trading_days_per_year)


def vol_weight(sigma, target_vol, leverage_cap):
    if sigma is None or sigma <= 0:
        return None
    return min(float(leverage_cap), float(target_vol) / float(sigma))


def filter_eval_indices(bars, prereg, split, warm_up):
    """Indices i where weight from bar i is applied to return i→i+1 inside the split.

    Excludes holdout days (signal day and return day). Combined confirmations
    drop the consumed 2022 holdout gap.
    """
    start_ts, end_ts = prereg_mod.split_window(prereg, split)
    out = []
    n = len(bars)
    for i in range(warm_up, n - 1):
        ts = bars[i]["ts"]
        ts_next = bars[i + 1]["ts"]
        if ts < start_ts or ts_next >= end_ts:
            continue
        if prereg_mod.day_in_exclusion(ts, prereg):
            continue
        if prereg_mod.day_in_exclusion(ts_next, prereg):
            continue
        # For combined_confirmations, also require membership in A or B windows.
        if split == "combined_confirmations":
            in_a = (
                prereg_mod.split_window(prereg, "confirmation_a")[0]
                <= ts
                < prereg_mod.split_window(prereg, "confirmation_a")[1]
            )
            in_b = (
                prereg_mod.split_window(prereg, "confirmation_b")[0]
                <= ts
                < prereg_mod.split_window(prereg, "confirmation_b")[1]
            )
            if not (in_a or in_b):
                continue
        out.append(i)
    return out
