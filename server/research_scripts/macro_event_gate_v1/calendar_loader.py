"""Stub calendar loader for MEG-NFP-CPI-FOMC-001.

Real NFP/CPI/FOMC schedules with *pre-release* timestamps must be obtained on
the research PC (see macro_calendar_v1/SOURCES.md and this package README).
This module only validates schema, enriches UTC via macro_calendar_v1, and
loads CSV fixtures. It never invents release times or consensus values.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(HERE)
if RESEARCH not in sys.path:
    sys.path.insert(0, RESEARCH)

from macro_calendar_v1.release_time import (  # noqa: E402
    REQUIRED_COLUMNS,
    enrich,
    read_csv,
    validate_rows,
)

ALLOWED_EVENTS = ("NFP", "CPI", "FOMC_STATEMENT")
FIXTURE_MARKER = "SYNTHETIC_FIXTURE"


class CalendarError(Exception):
    pass


def default_fixture_path():
    return os.path.join(HERE, "fixtures", "sample_events_synthetic.csv")


def load_events_csv(path, *, allow_synthetic=False, event_types=None):
    """Load and validate a calendar CSV; return enriched rows sorted by release_utc.

    Parameters
    ----------
    path : str
        CSV with REQUIRED_COLUMNS from macro_calendar_v1.release_time.
    allow_synthetic : bool
        If False, refuse rows whose source_url or revision_note marks a fixture.
        CI tests pass True; PC runs on real calendars must leave this False.
    event_types : iterable or None
        Subset of ALLOWED_EVENTS; default = all three.
    """
    if not path or not os.path.exists(path):
        raise CalendarError(
            f"calendar CSV not found: {path!r}. Obtain NFP/CPI/FOMC schedule with "
            "pre-release timestamps (macro_calendar_v1/SOURCES.md) and pass --calendar-csv."
        )
    rows = read_csv(path)
    if not rows:
        raise CalendarError(f"calendar CSV is empty: {path}")

    problems = validate_rows(rows)
    if problems:
        raise CalendarError("calendar validation failed:\n  " + "\n  ".join(problems))

    allowed = set(event_types) if event_types is not None else set(ALLOWED_EVENTS)
    unknown = {r["event"] for r in rows if r.get("event") not in ALLOWED_EVENTS}
    if unknown:
        raise CalendarError(f"unsupported event types: {sorted(unknown)}; allowed={ALLOWED_EVENTS}")

    filtered = [r for r in rows if r.get("event") in allowed]
    if not filtered:
        raise CalendarError(f"no rows for event types {sorted(allowed)} in {path}")

    if not allow_synthetic:
        for n, row in enumerate(filtered, start=2):
            note = (row.get("revision_note") or "") + " " + (row.get("source_url") or "")
            if FIXTURE_MARKER in note or "example.invalid" in (row.get("source_url") or ""):
                raise CalendarError(
                    f"line {n}: synthetic/fixture calendar refused "
                    f"(allow_synthetic=False). Use a real sourced calendar on the PC."
                )

    enriched = enrich(filtered)
    for row in enriched:
        # Epoch for windowing; fail hard if enrichment somehow skipped.
        row["release_ts"] = int(
            datetime.fromisoformat(row["release_utc"]).astimezone(timezone.utc).timestamp()
        )
    enriched.sort(key=lambda r: r["release_ts"])
    return enriched


def event_days_utc_dates(events):
    """Set of YYYY-MM-DD (UTC calendar date of release) for control exclusion."""
    out = set()
    for row in events:
        out.add(datetime.fromtimestamp(row["release_ts"], tz=timezone.utc).strftime("%Y-%m-%d"))
    return out
