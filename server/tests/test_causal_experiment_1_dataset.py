"""Integrity gate on the frozen Causal Experiment 1 dataset (Track C).

No MT5 re-run: validates the committed CSV under results/causal_experiment_1/.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "results" / "causal_experiment_1" / "wick_sweep_1r_dataset.csv"

REQUIRED = {
    "event_id", "level_id", "timestamp", "side", "direction", "level_price",
    "entry_ref", "created_time", "level_age_seconds", "touch_count_before_sweep",
    "penetration_pips", "sweep_depth_pips", "session_bucket", "hour",
    "day_of_week", "source_tf", "window_id", "outcome", "time_to_outcome_seconds",
}
OUTCOMES = {"PLUS_1R_FIRST", "MINUS_1R_FIRST", "CENSORED", "AMBIGUOUS_SAME_BAR"}
SESSIONS = {"ASIA", "LONDON", "NY", "LATE"}


def _parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(s)


@pytest.fixture(scope="module")
def rows():
    assert CSV_PATH.is_file(), f"missing frozen dataset: {CSV_PATH}"
    with CSV_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_dataset_has_required_schema(rows):
    assert rows, "dataset vuoto"
    assert REQUIRED <= set(rows[0].keys())


def test_dataset_meets_minimum_sample(rows):
    # Phase E design: >= 150 resolved preferred; frozen file has 195 total.
    assert len(rows) >= 150


def test_outcomes_and_sessions_are_canonical(rows):
    for r in rows:
        assert r["outcome"] in OUTCOMES
        assert r["session_bucket"] in SESSIONS
        assert r["side"] in {"HIGH", "LOW"}
        assert r["window_id"] in {"W1", "W2", "W3"}


def test_no_lookahead_created_before_sweep(rows):
    bad = []
    for r in rows:
        created = _parse_dt(r["created_time"])
        sweep = _parse_dt(r["timestamp"])
        if created > sweep:
            bad.append(r["event_id"])
    assert bad == []


def test_event_ids_unique(rows):
    ids = [r["event_id"] for r in rows]
    assert len(ids) == len(set(ids))


def test_level_age_non_negative(rows):
    for r in rows:
        assert float(r["level_age_seconds"]) >= 0.0
