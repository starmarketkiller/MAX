"""Sessions, Europe/Rome time and data gaps, with DST handled by tz rules.

The tick data is UTC and has no DST shift of its own. What moves with DST is
the market: London and New York open one hour earlier in UTC during their
summer time, on different dates (the US switches 2-3 weeks before Europe in
March and 1 week after in Oct/Nov). Session labels are therefore computed in
each city's local time, never as fixed UTC hours.

zoneinfo needs the IANA database: on Windows it comes only from the `tzdata`
package (declared in server/requirements-dev.txt).
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
LONDON = ZoneInfo("Europe/London")
NEW_YORK = ZoneInfo("America/New_York")
TOKYO = ZoneInfo("Asia/Tokyo")

# Local cash-session hours [open, close) per city. Policy values, not market facts.
SESSION_HOURS = {"TOKYO": (TOKYO, 9, 15), "LONDON": (LONDON, 8, 17), "NEW_YORK": (NEW_YORK, 8, 17)}


def utc(epoch_seconds):
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)


def rome_time(epoch_seconds):
    return utc(epoch_seconds).astimezone(ROME)


def utc_offset_hours(epoch_seconds, zone):
    return utc(epoch_seconds).astimezone(zone).utcoffset().total_seconds() / 3600


def session_label(epoch_seconds):
    """LONDON_NY_OVERLAP, LONDON, NEW_YORK, TOKYO or OFF, from local clocks."""
    open_now = []
    for name, (zone, start, end) in SESSION_HOURS.items():
        local = utc(epoch_seconds).astimezone(zone)
        if local.weekday() < 5 and start <= local.hour < end:
            open_now.append(name)
    if "LONDON" in open_now and "NEW_YORK" in open_now:
        return "LONDON_NY_OVERLAP"
    for name in ("NEW_YORK", "LONDON", "TOKYO"):
        if name in open_now:
            return name
    return "OFF"


def is_weekend_gap(prev_end, next_start):
    """True when a gap spans the FX/metals weekend close (Friday evening NY to Sunday evening NY)."""
    a = utc(prev_end).astimezone(NEW_YORK)
    b = utc(next_start).astimezone(NEW_YORK)
    return (b - a).days >= 1 and (a.weekday() == 4 or a.weekday() == 5) and b.weekday() in (6, 0)


def gap_report(bars, minutes, allowed_daily_break_minutes=90):
    """Missing bars between consecutive bars, classified.

    WEEKEND: Friday close to Sunday reopen. DAILY_BREAK: the short pause around
    17:00 New York (21:00 or 22:00 UTC depending on US DST). OTHER: anything
    else, to be reviewed before trusting the period."""
    size = minutes * 60
    gaps = {"WEEKEND": 0, "DAILY_BREAK": 0, "OTHER": []}
    for prev, nxt in zip(bars, bars[1:]):
        missing = (nxt["start"] - prev["end"]) // size
        if missing <= 0:
            continue
        if is_weekend_gap(prev["end"], nxt["start"]):
            gaps["WEEKEND"] += 1
            continue
        ny = utc(prev["end"]).astimezone(NEW_YORK)
        minutes_missing = missing * minutes
        if 16 <= ny.hour <= 18 and minutes_missing <= allowed_daily_break_minutes:
            gaps["DAILY_BREAK"] += 1
            continue
        gaps["OTHER"].append({"after_utc": utc(prev["end"]).isoformat(),
                              "before_utc": utc(nxt["start"]).isoformat(),
                              "missing_bars": int(missing)})
    return {"weekend_gaps": gaps["WEEKEND"], "daily_break_gaps": gaps["DAILY_BREAK"],
            "other_gaps": gaps["OTHER"], "n_other_gaps": len(gaps["OTHER"])}


def dst_transition_check(bars):
    """Where the daily break sits in UTC, per US DST state.

    If the data is truly UTC, the quietest hour should move by one hour between
    US summer and winter time. Returns the hour (UTC) with the fewest ticks for
    each state; a summer/winter difference of 1 hour is the expected signature."""
    ticks_by_state = {"US_DST": {}, "US_STANDARD": {}}
    for bar in bars:
        state = "US_DST" if utc_offset_hours(bar["start"], NEW_YORK) == -4 else "US_STANDARD"
        if utc(bar["start"]).astimezone(NEW_YORK).weekday() >= 5:
            continue
        hour = utc(bar["start"]).hour
        ticks_by_state[state][hour] = ticks_by_state[state].get(hour, 0) + bar["n_ticks"]
    result = {}
    for state, hours in ticks_by_state.items():
        result[state] = min(hours, key=hours.get) if hours else None
    if result["US_DST"] is not None and result["US_STANDARD"] is not None:
        result["shift_hours"] = (result["US_STANDARD"] - result["US_DST"]) % 24
    else:
        result["shift_hours"] = None
    return result
