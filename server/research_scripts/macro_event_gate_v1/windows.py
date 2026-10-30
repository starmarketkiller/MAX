"""Event vs same-clock non-event windows for MEG-NFP-CPI-FOMC-001.

Non-directional phase 1: compare mean bid-ask spread and mid-range inside
[release − pre_minutes, release + post_minutes] against the same local
America/New_York clock on non-event weekdays.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .calendar_loader import event_days_utc_dates
from .prereg import day_in_exclusion

NEW_YORK = ZoneInfo("America/New_York")
UTC = timezone.utc


def _mean(values):
    return sum(values) / len(values) if values else None


def bar_spread(bar):
    """USD spread from ask_open − open (bid), falling back to ask_close − close."""
    if bar.get("ask_open") is not None and bar.get("open") is not None:
        return float(bar["ask_open"]) - float(bar["open"])
    if bar.get("ask_close") is not None and bar.get("close") is not None:
        return float(bar["ask_close"]) - float(bar["close"])
    return None


def bar_mid(bar):
    bid = bar.get("close")
    ask = bar.get("ask_close")
    if bid is None:
        bid = bar.get("open")
    if ask is None and bid is not None:
        spread = bar_spread(bar)
        ask = bid + spread if spread is not None else None
    if bid is None or ask is None:
        return None
    return 0.5 * (float(bid) + float(ask))


def bars_in_window(bars, start_ts, end_ts):
    """Bars whose start is inside [start_ts, end_ts)."""
    return [b for b in bars if start_ts <= int(b["start"]) < end_ts]


def window_metrics(bars_slice):
    """Return mean_spread and mid_range over bars in the slice, or None fields."""
    spreads = []
    mids = []
    for bar in bars_slice:
        sp = bar_spread(bar)
        if sp is not None:
            spreads.append(sp)
        mid = bar_mid(bar)
        if mid is not None:
            mids.append(mid)
    mean_spread = _mean(spreads)
    mid_range = (max(mids) - min(mids)) if len(mids) >= 2 else None
    return {
        "n_bars": len(bars_slice),
        "mean_spread": mean_spread,
        "mid_range": mid_range,
    }


def event_window_bounds(release_ts, pre_minutes, post_minutes):
    pre_s = int(pre_minutes) * 60
    post_s = int(post_minutes) * 60
    return release_ts - pre_s, release_ts + post_s


def same_clock_window_on_day(release_ts, day_utc_date, pre_minutes, post_minutes):
    """Map an event's NY local clock onto another UTC calendar date.

    Uses America/New_York local time-of-day of the original release so DST is
    respected for the control day (same local clock, possibly different UTC).
    """
    release_dt = datetime.fromtimestamp(release_ts, tz=UTC).astimezone(NEW_YORK)
    local_t = release_dt.timetz().replace(tzinfo=None)
    y, m, d = (int(x) for x in day_utc_date.split("-"))
    # Anchor the control calendar day in NY local civil date ≈ UTC date for
    # US daytime releases (08:30 / 14:00) — use NY date matching the UTC date
    # string passed in (caller supplies NY-local or UTC date consistently).
    control_local = datetime(y, m, d, local_t.hour, local_t.minute, local_t.second, tzinfo=NEW_YORK)
    control_release_ts = int(control_local.astimezone(UTC).timestamp())
    return event_window_bounds(control_release_ts, pre_minutes, post_minutes)


def _weekday_utc(day_str):
    y, m, d = (int(x) for x in day_str.split("-"))
    return datetime(y, m, d, tzinfo=UTC).weekday()


def candidate_control_days(event_ts, event_day_set, split_start, split_end, params, prereg):
    """Same weekday, non-event, inside split, outside exclusions, within lookback weeks."""
    lookback_weeks = int(params["control_lookback_weeks"])
    max_controls = int(params["max_controls_per_event"])
    event_day = datetime.fromtimestamp(event_ts, tz=UTC).strftime("%Y-%m-%d")
    target_wd = _weekday_utc(event_day)
    event_date = datetime.fromtimestamp(event_ts, tz=UTC).date()
    out = []
    # Walk ±lookback_weeks by calendar day, prefer past then future.
    for week in range(1, lookback_weeks + 1):
        for sign in (-1, 1):
            day = event_date + timedelta(days=sign * 7 * week)
            day_str = day.strftime("%Y-%m-%d")
            day_ts = int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp())
            if day_ts < split_start or day_ts >= split_end:
                continue
            if day_in_exclusion(day_ts, prereg):
                continue
            if day_str in event_day_set:
                continue
            if _weekday_utc(day_str) != target_wd:
                continue
            if day.weekday() >= 5:
                continue
            out.append(day_str)
            if len(out) >= max_controls:
                return out
    return out


def build_event_rows(bars, events, prereg, split, params):
    """Build one CLOSED row per event with usable event + control metrics."""
    from .prereg import split_window

    start, end = split_window(prereg, split)
    # Filter events to split; refuse if any event window overlaps exclusion.
    event_day_set = event_days_utc_dates(events)
    min_bars = int(params["min_bars_per_window"])
    min_controls = int(params["min_controls_per_event"])
    pre = int(params["pre_minutes"])
    post = int(params["post_minutes"])

    rows = []
    for ev in events:
        rts = int(ev["release_ts"])
        if rts < start or rts >= end:
            continue
        w0, w1 = event_window_bounds(rts, pre, post)
        if day_in_exclusion(rts, prereg) or day_in_exclusion(w0, prereg) or day_in_exclusion(w1 - 1, prereg):
            continue

        event_slice = bars_in_window(bars, w0, w1)
        event_m = window_metrics(event_slice)
        if event_m["n_bars"] < min_bars or event_m["mean_spread"] is None or event_m["mid_range"] is None:
            rows.append({
                "status": "SKIP_SPARSE_EVENT",
                "event": ev["event"],
                "release_ts": rts,
                "release_utc": ev["release_utc"],
                "entry_time": rts,
                "year": datetime.fromtimestamp(rts, tz=UTC).strftime("%Y"),
                "month": datetime.fromtimestamp(rts, tz=UTC).strftime("%Y-%m"),
                "n_bars_event": event_m["n_bars"],
            })
            continue

        controls = candidate_control_days(rts, event_day_set, start, end, params, prereg)
        control_spreads = []
        control_ranges = []
        used_days = []
        for day_str in controls:
            c0, c1 = same_clock_window_on_day(rts, day_str, pre, post)
            cm = window_metrics(bars_in_window(bars, c0, c1))
            if cm["n_bars"] < min_bars or cm["mean_spread"] is None or cm["mid_range"] is None:
                continue
            control_spreads.append(cm["mean_spread"])
            control_ranges.append(cm["mid_range"])
            used_days.append(day_str)

        if len(used_days) < min_controls:
            rows.append({
                "status": "SKIP_SPARSE_CONTROL",
                "event": ev["event"],
                "release_ts": rts,
                "release_utc": ev["release_utc"],
                "entry_time": rts,
                "year": datetime.fromtimestamp(rts, tz=UTC).strftime("%Y"),
                "month": datetime.fromtimestamp(rts, tz=UTC).strftime("%Y-%m"),
                "n_controls": len(used_days),
            })
            continue

        ctrl_spread = _mean(control_spreads)
        ctrl_range = _mean(control_ranges)
        spread_delta = event_m["mean_spread"] - ctrl_spread
        range_delta = event_m["mid_range"] - ctrl_range
        rows.append({
            "status": "CLOSED",
            "event": ev["event"],
            "release_ts": rts,
            "release_utc": ev["release_utc"],
            "entry_time": rts,
            "window_start": w0,
            "window_end": w1,
            "n_bars_event": event_m["n_bars"],
            "mean_spread_event": event_m["mean_spread"],
            "mid_range_event": event_m["mid_range"],
            "mean_spread_control": ctrl_spread,
            "mid_range_control": ctrl_range,
            "spread_delta": spread_delta,
            "range_delta": range_delta,
            "n_controls": len(used_days),
            "control_days": ",".join(used_days),
            "year": datetime.fromtimestamp(rts, tz=UTC).strftime("%Y"),
            "month": datetime.fromtimestamp(rts, tz=UTC).strftime("%Y-%m"),
            "reference_period": ev.get("reference_period") or "",
            "source_url": ev.get("source_url") or "",
        })
    return rows
