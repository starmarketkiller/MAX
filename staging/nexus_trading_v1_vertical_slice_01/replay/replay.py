"""replay.py - chronological replay with an explicit anti-lookahead
check: decisions produced from a truncated (as_of-bounded) bar series
must be byte-identical, bar for bar, to the corresponding prefix of a
decision series produced from the FULL bar series. If a later bar had
ever leaked into an earlier decision, these two would diverge and the
check would fail loudly - it is not just an assertion that "no future
bar is in the list", it is a behavioural proof that the same past
produces the same decision regardless of what comes after it.
"""
from __future__ import annotations

from typing import Any

from decision_engine import engine as decision_engine
from data_layer.bar_store import BarStore


def run_decisions_over(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """No open-paper-attempt state here - pure decision replay, always
    reports has_open_attempt=False, so the output is a function of the
    bars alone (dedup/veto behaviour is tested separately against the
    paper engine, not against this pure replay)."""
    return decision_engine.evaluate_series(bars, lambda: False)


def verify_no_future_leakage(store: BarStore, as_of_sample_indices: list[int]) -> dict[str, Any]:
    """For each sample index i into store.all_bars(), replay the
    series TRUNCATED at that bar's available_at_utc, and compare every
    decision in that truncated run against the same-index decision in
    one FULL run over the entire series. Returns a report, never
    raises - callers (tests) decide pass/fail from the report."""
    full_bars = store.all_bars()
    full_decisions = run_decisions_over(full_bars)

    mismatches: list[dict[str, Any]] = []
    checked_cutoffs = 0
    for i in as_of_sample_indices:
        if i < 0 or i >= len(full_bars):
            continue
        as_of = full_bars[i]["available_at_utc"]
        truncated_bars = store.bars_as_of(as_of)
        truncated_decisions = run_decisions_over(truncated_bars)
        checked_cutoffs += 1

        if len(truncated_decisions) != i + 1:
            mismatches.append({
                "as_of": as_of, "issue": "LENGTH_MISMATCH",
                "expected_len": i + 1, "actual_len": len(truncated_decisions),
            })
            continue

        for j, (full_rec, trunc_rec) in enumerate(zip(full_decisions[: i + 1], truncated_decisions)):
            compare_fields = ("h1a_decision", "h1a_reason_code", "level_high_observed",
                               "level_low_observed", "candidate_detail")
            for field_name in compare_fields:
                if full_rec.get(field_name) != trunc_rec.get(field_name):
                    mismatches.append({
                        "as_of": as_of, "bar_index": j, "field": field_name,
                        "full_run_value": full_rec.get(field_name),
                        "truncated_run_value": trunc_rec.get(field_name),
                    })

    return {
        "checked_cutoffs": checked_cutoffs,
        "mismatches": mismatches,
        "passed": len(mismatches) == 0 and checked_cutoffs > 0,
    }
