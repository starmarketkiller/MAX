"""h1a_detector.py - pure, causal implementation of the frozen contract
in STRATEGY_CONTRACT_H1_A.md. Every numeric rule here is a direct
transcription of that document - no rule is invented here that is not
already written and tagged (DESIGN_ASSUMPTION_V1 or otherwise) there.

Causal by construction: classify_sequence() only ever compares bar[t]
against a window built from bars strictly before t (the window is
appended to only AFTER classifying the current bar) - the same
discipline already used by
phase5e_causal_replay_v1.baseline_signal.classify_sequence, mirrored
here for a different, H1-A-specific rule (not imported, because the
rule itself is different - the causal-ordering PATTERN is reused, the
trading rule is not shared).
"""
from __future__ import annotations

from collections import deque
from typing import Any, Iterable

STRATEGY_ID = "H1_A"
STRATEGY_VERSION = "H1_A_V1"

LOOKBACK_N = 20  # reused from market_state_dataset_v1.csv's own frozen lookback

BUY, SELL, WAIT = "BUY", "SELL", "WAIT"

REASON_INSUFFICIENT_WARMUP = "INSUFFICIENT_WARMUP_HISTORY"
REASON_NO_SWEEP = "NO_SWEEP_DETECTED"
REASON_SWEEP_WITHOUT_RECLAIM = "SWEEP_WITHOUT_RECLAIM_NOT_H1A_SETUP"
REASON_AMBIGUOUS_BOTH = "AMBIGUOUS_BOTH_SIDES_SWEPT_AND_RECLAIMED"
REASON_CANDIDATE_LONG = "CANDIDATE_LONG_SWEEP_RECLAIM"
REASON_CANDIDATE_SHORT = "CANDIDATE_SHORT_SWEEP_RECLAIM"


def classify_bar(
    bar: dict[str, Any],
    level_high: float | None,
    level_low: float | None,
    sweep_buffer: float,
) -> tuple[str, str, dict[str, Any] | None]:
    """Pure function: one bar + its strictly-prior levels -> (decision,
    reason_code, candidate_detail or None). ``sweep_buffer`` is an
    explicit parameter (contract SS3: "non hardcoded"), not a
    module-level constant - callers pass bar['avg_spread'] per the
    frozen contract, but a test can pass any value to probe the rule.
    """
    if level_high is None or level_low is None:
        return WAIT, REASON_INSUFFICIENT_WARMUP, None

    sweep_high = bar["high"] > level_high + sweep_buffer
    sweep_low = bar["low"] < level_low - sweep_buffer
    reclaim_high = sweep_high and bar["close"] <= level_high
    reclaim_low = sweep_low and bar["close"] >= level_low

    if reclaim_high and reclaim_low:
        return WAIT, REASON_AMBIGUOUS_BOTH, None
    if reclaim_low:
        detail = {
            "direction": "LONG",
            "level": level_low,
            "sweep_extreme": bar["low"],
            "entry_reference_price": bar["close"],
        }
        return BUY, REASON_CANDIDATE_LONG, detail
    if reclaim_high:
        detail = {
            "direction": "SHORT",
            "level": level_high,
            "sweep_extreme": bar["high"],
            "entry_reference_price": bar["close"],
        }
        return SELL, REASON_CANDIDATE_SHORT, detail
    if sweep_high or sweep_low:
        return WAIT, REASON_SWEEP_WITHOUT_RECLAIM, None
    return WAIT, REASON_NO_SWEEP, None


def classify_sequence(
    bars: Iterable[dict[str, Any]], sweep_buffer_field: str = "avg_spread"
) -> list[tuple[str, str, dict[str, Any] | None]]:
    """Stream bars in ascending time order (caller's responsibility -
    BarStore already guarantees this). Returns one (decision,
    reason_code, detail) per bar, same order.

    Causal by construction: ``highs``/``lows`` contain only strictly
    prior bars at the moment bar i is classified (appended only after).
    Bar i's own high/low/close are never part of the window used to
    judge bar i.
    """
    highs: deque[float] = deque(maxlen=LOOKBACK_N)
    lows: deque[float] = deque(maxlen=LOOKBACK_N)
    out: list[tuple[str, str, dict[str, Any] | None]] = []
    for bar in bars:
        if len(highs) < LOOKBACK_N:
            out.append((WAIT, REASON_INSUFFICIENT_WARMUP, None))
        else:
            level_high = max(highs)
            level_low = min(lows)
            buffer = float(bar.get(sweep_buffer_field) or 0.0)
            out.append(classify_bar(bar, level_high, level_low, buffer))
        highs.append(bar["high"])
        lows.append(bar["low"])
    return out
