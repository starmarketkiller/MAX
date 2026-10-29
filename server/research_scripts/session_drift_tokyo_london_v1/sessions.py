"""Tokyo / London cash-open clocks with DST via IANA zones.

Reuses the same zone policy as behavior_lab_v1/sessions.py: never fixed UTC
hours for session opens.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TOKYO = ZoneInfo("Asia/Tokyo")
LONDON = ZoneInfo("Europe/London")
UTC = timezone.utc


def utc_from_epoch(epoch_seconds):
    return datetime.fromtimestamp(epoch_seconds, tz=UTC)


def local_open_utc(day_utc_date, zone, hour, minute=0):
    """Cash open on the civil date of `day_utc_date` in `zone`, returned as UTC datetime.

    `day_utc_date` is a datetime (any tz); its calendar Y-M-D is interpreted in
    the session zone so a single trading day maps to one open.
    """
    local_date = day_utc_date.astimezone(zone).date() if day_utc_date.tzinfo else day_utc_date.date()
    local = datetime(local_date.year, local_date.month, local_date.day,
                     hour, minute, tzinfo=zone)
    return local.astimezone(UTC)


def tokyo_open_utc(day, hour=9, minute=0):
    return local_open_utc(day, TOKYO, hour, minute)


def london_open_utc(day, hour=8, minute=0):
    return local_open_utc(day, LONDON, hour, minute)


def iter_weekdays(start_utc, end_utc):
    """UTC midnights from start to end (end exclusive) that are Mon–Fri in UTC calendar.

    The session filter still uses Tokyo local weekday at Tokyo open.
    """
    day = datetime(start_utc.year, start_utc.month, start_utc.day, tzinfo=UTC)
    last = datetime(end_utc.year, end_utc.month, end_utc.day, tzinfo=UTC)
    while day < last:
        yield day
        day += timedelta(days=1)


def is_tokyo_weekday(tokyo_open_dt, weekday_only=True):
    if not weekday_only:
        return True
    return tokyo_open_dt.astimezone(TOKYO).weekday() < 5
