"""US macro release times: local (America/New_York) -> UTC -> Europe/Rome.

This module converts and validates. It holds no historical data and never
fills a missing value: an event without an official source stays absent.

Why it matters: the US and the EU change clocks on different Sundays (US:
second Sunday of March and first Sunday of November; EU: last Sunday of March
and last Sunday of October). In those weeks an 08:30 New York release is at
13:30 in Rome instead of the usual 14:30, and a price study keyed on a fixed
UTC or Rome hour would read the wrong bar.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
ROME = ZoneInfo("Europe/Rome")

# Release clock conventions, as published by each agency. `verified` says where
# this repository has checked it; anything else must be confirmed per event.
RELEASE_CONVENTIONS = {
    "CPI": {"agency": "BLS", "local_time": "08:30", "verified": "not from this container: bls.gov schedule pages answer 403"},
    "NFP": {"agency": "BLS (Employment Situation)", "local_time": "08:30", "verified": "not from this container: bls.gov schedule pages answer 403"},
    "PCE": {"agency": "BEA (Personal Income and Outlays)", "local_time": "08:30", "verified": "bea.gov/news/schedule, read 2026-10-11"},
    "FOMC_STATEMENT": {"agency": "Federal Reserve", "local_time": "14:00", "verified": "federalreserve.gov press releases 2025-01-29 and 2025-09-17, 'For release at 2:00 p.m.'"},
}

REQUIRED_COLUMNS = ("event", "reference_period", "release_date_local", "release_time_local",
                    "local_timezone", "source_url", "retrieved_at_utc")
OPTIONAL_VALUE_COLUMNS = ("actual", "forecast", "previous", "forecast_source", "revision_note")


def to_utc_and_rome(release_date, release_time="08:30", zone=NEW_YORK):
    """Return (utc_datetime, rome_datetime) for a local release clock."""
    if isinstance(release_date, str):
        release_date = date.fromisoformat(release_date)
    hh, mm = (int(x) for x in release_time.split(":"))
    local = datetime.combine(release_date, time(hh, mm), tzinfo=zone)
    as_utc = local.astimezone(timezone.utc)
    return as_utc, as_utc.astimezone(ROME)


def dst_mismatch(release_date):
    """True when New York and Rome are not at their usual 6-hour distance."""
    as_utc, rome = to_utc_and_rome(release_date, "12:00")
    ny = as_utc.astimezone(NEW_YORK)
    gap = (rome.utcoffset() - ny.utcoffset()).total_seconds() / 3600
    return gap != 6


def validate_rows(rows):
    """Schema checks for an events file. Returns problems; empty means usable.

    `actual`, `forecast`, `previous` may be empty, never invented: an empty
    forecast stays empty, and a forecast needs its own forecast_source."""
    problems = []
    for n, row in enumerate(rows, start=2):
        for col in REQUIRED_COLUMNS:
            if not (row.get(col) or "").strip():
                problems.append(f"line {n}: missing {col}")
        if row.get("forecast") and not row.get("forecast_source"):
            problems.append(f"line {n}: forecast without forecast_source")
        if (row.get("source_url") or "").startswith("http") is False and row.get("source_url"):
            problems.append(f"line {n}: source_url is not a URL")
        try:
            to_utc_and_rome(row.get("release_date_local", ""), row.get("release_time_local", "") or "x",
                            ZoneInfo(row.get("local_timezone") or "UTC"))
        except (ValueError, KeyError) as exc:
            problems.append(f"line {n}: bad date/time/zone ({exc})")
    return problems


def enrich(rows):
    """Add release_utc, release_rome and dst_mismatch to validated rows."""
    out = []
    for row in rows:
        as_utc, rome = to_utc_and_rome(row["release_date_local"], row["release_time_local"],
                                       ZoneInfo(row["local_timezone"]))
        out.append(dict(row, release_utc=as_utc.isoformat(), release_rome=rome.isoformat(),
                        dst_mismatch=dst_mismatch(row["release_date_local"])))
    return out


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
