"""Versioned, deterministic execution semantics for research fixtures.

This module does not replace ``backtest.py``.  It makes ambiguous bar-level
assumptions explicit so that new experiments can declare them and parity work
can compare the same contract across Python, MT5, and TradingView.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal


SUPPORTED_TIMEFRAMES = frozenset({"5m", "15m", "30m", "1h", "4h", "1d", "1wk"})
FillModel = Literal["SIGNAL_CLOSE_LEGACY", "NEXT_OPEN_V1"]
IntrabarPolicy = Literal[
    "MANAGEMENT_THEN_STOP_FIRST", "STOP_FIRST", "TARGET_FIRST", "AMBIGUOUS_REJECT"
]


@dataclass(frozen=True)
class SyntheticBar:
    open: float
    high: float
    low: float
    close: float


def validate_timeframe(timeframe: str) -> str:
    value = str(timeframe).lower()
    if value not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    return value


def fill_price(signal_bar: SyntheticBar, next_bar: SyntheticBar, model: FillModel) -> float:
    if model == "SIGNAL_CLOSE_LEGACY":
        return signal_bar.close
    if model == "NEXT_OPEN_V1":
        return next_bar.open
    raise ValueError(f"unsupported fill model: {model}")


def resolve_bar_exit(
    bar: SyntheticBar,
    *,
    direction: int,
    stop: float,
    target: float,
    policy: IntrabarPolicy,
) -> tuple[str, float] | None:
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or 1")
    stop_hit = bar.low <= stop if direction == 1 else bar.high >= stop
    target_hit = bar.high >= target if direction == 1 else bar.low <= target
    if stop_hit and target_hit:
        if policy in ("MANAGEMENT_THEN_STOP_FIRST", "STOP_FIRST"):
            return "SL", stop
        if policy == "TARGET_FIRST":
            return "TP", target
        if policy == "AMBIGUOUS_REJECT":
            raise ValueError("bar touches stop and target under AMBIGUOUS_REJECT")
    if stop_hit:
        return "SL", stop
    if target_hit:
        return "TP", target
    return None


def update_stop_before_exit(
    bar: SyntheticBar,
    *,
    direction: int,
    entry: float,
    stop: float,
    risk_distance: float,
    breakeven_r: float = 0.0,
    trailing_atr: float = 0.0,
    atr: float = 0.0,
) -> float:
    """Characterize the legacy order: BE/trailing update before hit testing."""
    if direction not in (-1, 1) or risk_distance <= 0:
        raise ValueError("invalid direction or risk distance")
    updated = stop
    favorable = bar.high - entry if direction == 1 else entry - bar.low
    if breakeven_r > 0 and favorable >= breakeven_r * risk_distance:
        updated = max(updated, entry) if direction == 1 else min(updated, entry)
    if trailing_atr > 0 and atr > 0:
        candidate = bar.close - trailing_atr * atr if direction == 1 else bar.close + trailing_atr * atr
        updated = max(updated, candidate) if direction == 1 else min(updated, candidate)
    return updated


def apply_cost_cap(
    *, spread_r: float, commission_r: float, slippage_r: float, cap_r: float = 5.0
) -> dict:
    values = (spread_r, commission_r, slippage_r, cap_r)
    if any(v < 0 for v in values) or cap_r == 0:
        raise ValueError("cost components must be non-negative and cap_r positive")
    raw = spread_r + commission_r + slippage_r
    applied = min(raw, cap_r)
    scale = applied / raw if raw else 1.0
    return {
        "raw_cost_r": raw,
        "applied_cost_r": applied,
        "cap_applied": raw > cap_r,
        "spread_r": spread_r * scale,
        "commission_r": commission_r * scale,
        "slippage_r": slippage_r * scale,
    }


def experiment_identity(contract: dict) -> str:
    """Stable identity includes execution semantics, preventing fill-model reuse."""
    required = ("experiment_id", "fill_model", "intrabar_policy", "engine_version")
    missing = [key for key in required if not contract.get(key)]
    if missing:
        raise ValueError(f"missing execution identity fields: {', '.join(missing)}")
    canonical = json.dumps(
        {key: contract[key] for key in required}, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
