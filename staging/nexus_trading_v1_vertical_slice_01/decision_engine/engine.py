"""engine.py - ties BarStore + h1a_detector together into one Decision
record per bar, plus an attached, REUSED phase5d_shadow_engine_v1
audit event for authorization-status transparency.

Important distinction, stated once here and in EVENT_DECISION_SCHEMA.md:
the field that actually drives Paper Execution is ``h1a_decision``
(this module's own detector output). The attached
``shadow_audit_event`` (phase5d_shadow_engine_v1.contract.DecisionEvent)
is a SEPARATE, REUSED authorization-audit record - its own
``hypothetical_decision`` is, by construction, always WAIT/NO_TRADE for
H1_A (registry_status="RESEARCH_ONLY", never ACTIVE, so the arbiter can
never reach AUTHORIZED_EXECUTABLE - see arbiter.REASON_OBSERVATION_ONLY).
That is the CORRECT, intended behaviour: it proves, independently of
this module's own logic, that H1_A can never be mistaken for a live-
authorized decision even if this journal were ever read by the real
registry-gated path. It is not a second trading signal and is never
used to gate the paper engine.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in (str(_REPO_ROOT / "server"), str(_REPO_ROOT / "server" / "research_scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from phase5d_shadow_engine_v1 import contract as _contract  # noqa: E402

from . import h1a_detector  # noqa: E402

LOCAL_REGISTRY_STATUS = {"H1_A": "RESEARCH_ONLY"}  # never read from/written to the canonical file

MISSING_RULES_DECLARED = [
    "HTF_CONTEXT_NOT_IMPLEMENTED",
    "SESSION_FILTER_NOT_IMPLEMENTED",
    "SWEEP_CONFIRMATION_THRESHOLD_BEYOND_ZERO_BUFFER_NOT_IMPLEMENTED",
]


def _build_shadow_fixture(bar: dict[str, Any], decision: str, detail: dict[str, Any] | None) -> dict[str, Any]:
    candidate_actions: list[dict[str, Any]] = []
    if decision in (h1a_detector.BUY, h1a_detector.SELL) and detail is not None:
        candidate_actions.append({
            "strategy_id": h1a_detector.STRATEGY_ID,
            "proposed_side": decision,
            "available_evidence": [f"xauusd_h4_bars.csv#bar_epoch={bar['bar_epoch']}"],
        })
    return {
        "causal_timestamp": bar["available_at_utc"],
        "symbol": "XAUUSD",
        "timeframe": "H4",
        "market_state": {"close": bar.get("close"), "atr": bar.get("atr")},
        "observed_conditions": [],
        "alternative_scenarios": [],
        "invalidations": [],
        "available_evidence": [a["available_evidence"][0] for a in candidate_actions],
        "calibration_status": "UNKNOWN",
        "data_quality": "VALID" if bar.get("close") is not None else "INVALID",
        "candidate_actions": candidate_actions,
    }


def evaluate_bar(bar: dict[str, Any], level_high: float | None, level_low: float | None,
                  sweep_buffer: float, has_open_attempt: bool) -> dict[str, Any]:
    """Pure (given has_open_attempt as an external, caller-supplied
    fact - this module never queries paper-engine state itself, so the
    dedup/veto rule stays visible and testable at the call site)."""
    raw_decision, reason_code, detail = h1a_detector.classify_bar(bar, level_high, level_low, sweep_buffer)

    vetoed = False
    final_decision, final_reason = raw_decision, reason_code
    if raw_decision in (h1a_detector.BUY, h1a_detector.SELL) and has_open_attempt:
        vetoed = True
        final_decision = h1a_detector.WAIT
        final_reason = "DUPLICATE_SUPPRESSED_OPEN_ATTEMPT_EXISTS"

    shadow_fixture = _build_shadow_fixture(bar, final_decision, None if vetoed else detail)
    shadow_event = _contract.build_event(shadow_fixture, LOCAL_REGISTRY_STATUS)

    return {
        "event_id": shadow_event.event_id,
        "strategy_id": h1a_detector.STRATEGY_ID,
        "strategy_version": h1a_detector.STRATEGY_VERSION,
        "detector_version": h1a_detector.STRATEGY_VERSION,
        "bar_epoch": bar["bar_epoch"],
        "causal_timestamp": bar["available_at_utc"],
        "symbol": "XAUUSD",
        "timeframe": "H4",
        "level_high_observed": level_high,
        "level_low_observed": level_low,
        "sweep_buffer_used": sweep_buffer,
        "bar_high": bar["high"],
        "bar_low": bar["low"],
        "bar_close": bar["close"],
        "h1a_decision": final_decision,
        "h1a_reason_code": final_reason,
        "h1a_decision_pre_veto": raw_decision,
        "h1a_reason_code_pre_veto": reason_code,
        "is_veto": vetoed,
        "veto_reason": "DUPLICATE_SUPPRESSED_OPEN_ATTEMPT_EXISTS" if vetoed else None,
        "missing_rules_declared": MISSING_RULES_DECLARED,
        "candidate_detail": None if vetoed else detail,
        "shadow_audit_event": shadow_event.to_dict(),
    }


def evaluate_series(bars: list[dict[str, Any]], is_open_fn) -> list[dict[str, Any]]:
    """``is_open_fn() -> bool`` is called fresh before each bar - lets
    the caller (paper engine driver) report real position state without
    this module importing the paper engine (keeps the dependency
    direction one-way: paper engine depends on decision engine, never
    the reverse)."""
    from collections import deque

    highs: deque[float] = deque(maxlen=h1a_detector.LOOKBACK_N)
    lows: deque[float] = deque(maxlen=h1a_detector.LOOKBACK_N)
    out = []
    for bar in bars:
        if len(highs) < h1a_detector.LOOKBACK_N:
            level_high = level_low = None
        else:
            level_high, level_low = max(highs), min(lows)
        buffer = float(bar.get("avg_spread") or 0.0)
        record = evaluate_bar(bar, level_high, level_low, buffer, is_open_fn())
        out.append(record)
        highs.append(bar["high"])
        lows.append(bar["low"])
    return out
