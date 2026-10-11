"""Release-time conversion New York -> UTC -> Europe/Rome, incl. US/EU DST mismatch weeks."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research_scripts"))

from macro_calendar_v1.release_time import (RELEASE_CONVENTIONS, dst_mismatch, enrich,  # noqa: E402
                                            to_utc_and_rome, validate_rows)


@pytest.mark.parametrize("day,clock,utc_hm,rome_hm,mismatch", [
    ("2024-01-11", "08:30", "13:30", "14:30", False),   # both on winter time
    ("2024-03-12", "08:30", "12:30", "13:30", True),    # US summer time, EU not yet
    ("2024-04-10", "08:30", "12:30", "14:30", False),   # both on summer time
    ("2024-10-31", "08:30", "12:30", "13:30", True),    # EU back to winter, US not yet
    ("2024-11-07", "14:00", "19:00", "20:00", False),   # FOMC statement, both winter
    ("2025-03-19", "14:00", "18:00", "19:00", True),    # FOMC in the March gap
])
def test_conversion_follows_each_side_dst(day, clock, utc_hm, rome_hm, mismatch):
    as_utc, rome = to_utc_and_rome(day, clock)
    assert as_utc.strftime("%H:%M") == utc_hm
    assert rome.strftime("%H:%M") == rome_hm
    assert dst_mismatch(day) is mismatch


def test_conventions_declare_where_they_were_checked():
    assert RELEASE_CONVENTIONS["FOMC_STATEMENT"]["local_time"] == "14:00"
    assert "403" in RELEASE_CONVENTIONS["CPI"]["verified"]


def test_validation_refuses_invented_or_unsourced_values():
    good = {"event": "CPI", "reference_period": "2024-02", "release_date_local": "2024-03-12",
            "release_time_local": "08:30", "local_timezone": "America/New_York",
            "source_url": "https://www.bls.gov/", "retrieved_at_utc": "2026-10-11T08:00:00Z",
            "actual": "", "forecast": "", "previous": ""}
    assert validate_rows([good]) == []
    unsourced_forecast = dict(good, forecast="0.4")
    assert validate_rows([unsourced_forecast]) == ["line 2: forecast without forecast_source"]
    missing_source = dict(good, source_url="")
    assert "line 2: missing source_url" in validate_rows([missing_source])
    [row] = enrich([good])
    assert row["release_utc"].startswith("2024-03-12T12:30") and row["dst_mismatch"] is True
