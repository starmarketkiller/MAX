"""Build one observation per Tokyo→London session from M15 bid/ask bars."""
from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

from .sessions import is_tokyo_weekday, iter_weekdays, london_open_utc, tokyo_open_utc, utc_from_epoch

TOKYO = ZoneInfo("Asia/Tokyo")


def _bar_index_by_start(bars):
    return {int(b["start"]): b for b in bars}


def _nearest_bar(index, target_epoch, tolerance_seconds):
    """Exact start match, else nearest start within tolerance (prefer at/after target)."""
    if target_epoch in index:
        return index[target_epoch]
    best = None
    best_key = None
    for start, bar in index.items():
        dist = abs(start - target_epoch)
        if dist > tolerance_seconds:
            continue
        key = (dist, 0 if start >= target_epoch else 1)
        if best is None or key < best_key:
            best = bar
            best_key = key
    return best


def _side_price(bar, side):
    side = side.upper()
    if side == "ASK":
        return float(bar["ask_open"])
    if side == "BID":
        return float(bar["open"])  # bid open
    raise ValueError(f"unknown side {side}")


def _next_tokyo_open(t_open, hour, minute):
    t_local = t_open.astimezone(TOKYO)
    nxt = t_local + timedelta(days=1)
    return nxt.replace(hour=hour, minute=minute, second=0, microsecond=0).astimezone(t_open.tzinfo)


def build_session_rows(bars, params, start_ts, end_ts):
    """One row per weekday session with both opens inside [start_ts, end_ts).

    bars: M15 list with start/end/open/ask_open (behavior_lab bar schema).
    Missing opens are skipped when skip_if_missing_entry_or_exit is true.
    """
    index = _bar_index_by_start(bars)
    tol = int(params["open_match_tolerance_minutes"]) * 60
    commission = float(params["commission_usd_per_oz"])
    rows = []
    start_dt = utc_from_epoch(start_ts)
    end_dt = utc_from_epoch(end_ts)

    for day in iter_weekdays(start_dt, end_dt):
        t_open = tokyo_open_utc(
            day,
            params["tokyo_open_local_hour"],
            params["tokyo_open_local_minute"],
        )
        if not is_tokyo_weekday(t_open, params.get("weekday_only", True)):
            continue
        tokyo_local = t_open.astimezone(TOKYO)
        l_open = london_open_utc(
            tokyo_local,
            params["london_open_local_hour"],
            params["london_open_local_minute"],
        )
        if l_open <= t_open:
            continue
        t_epoch = int(t_open.timestamp())
        l_epoch = int(l_open.timestamp())
        if t_epoch < start_ts or l_epoch >= end_ts:
            continue

        entry_bar = _nearest_bar(index, t_epoch, tol)
        exit_bar = _nearest_bar(index, l_epoch, tol)
        if entry_bar is None or exit_bar is None:
            continue

        entry_ask = _side_price(entry_bar, params["entry_side"])
        exit_bid = _side_price(exit_bar, params["exit_side"])
        entry_mid = (float(entry_bar["open"]) + float(entry_bar["ask_open"])) / 2.0
        exit_mid = (float(exit_bar["open"]) + float(exit_bar["ask_open"])) / 2.0
        net = exit_bid - entry_ask - commission
        mid_ret = exit_mid - entry_mid
        hold_seconds = l_epoch - t_epoch

        next_tokyo = _next_tokyo_open(
            t_open, params["tokyo_open_local_hour"], params["tokyo_open_local_minute"]
        )
        next_bar = _nearest_bar(index, int(next_tokyo.timestamp()), tol)
        if next_bar is None:
            day_net = scaled = delta = None
        else:
            next_bid = _side_price(next_bar, params["exit_side"])
            day_net = next_bid - entry_ask - commission
            dur_day = int(next_tokyo.timestamp()) - t_epoch
            scale = (hold_seconds / dur_day) if dur_day > 0 else 0.0
            scaled = day_net * scale
            delta = net - scaled

        rows.append({
            "status": "CLOSED",
            "entry_time": t_epoch,
            "exit_time": l_epoch,
            "tokyo_open_utc": t_open.isoformat(),
            "london_open_utc": l_open.isoformat(),
            "entry_ask": entry_ask,
            "exit_bid": exit_bid,
            "net_return_usd": net,
            "mid_return_usd": mid_ret,
            "day_net_return_usd": day_net,
            "scaled_generic_gold_usd": scaled,
            "delta_vs_generic_gold_usd": delta,
            "hold_seconds": hold_seconds,
            "year": t_open.strftime("%Y"),
            "month": t_open.strftime("%Y-%m"),
            "split_tag": None,
        })
    return rows


def tag_split(rows, tag):
    for row in rows:
        row["split_tag"] = tag
    return rows
