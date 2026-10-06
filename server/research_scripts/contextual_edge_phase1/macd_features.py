#!/usr/bin/env python3
"""Causal MT5-compatible MACD feature extraction for closed H4 bars.

MetaTrader's iMACD uses EMA(fast)-EMA(slow) for the main line and an SMA
over that main line for the signal buffer.  This module deliberately exposes
features only; it does not create trades, outcomes, candidates, or verdicts.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9
PRICE_FIELD = "close"
PARITY_WARMUP_BARS = 200
PARITY_ABS_TOLERANCE = 2e-5


@dataclass(frozen=True)
class MacdDefinition:
    fast: int = FAST_PERIOD
    slow: int = SLOW_PERIOD
    signal: int = SIGNAL_PERIOD
    price_field: str = PRICE_FIELD
    observation_point: str = "closed_bar"


def extract_macd_features(
    bars: pd.DataFrame,
    definition: MacdDefinition = MacdDefinition(),
) -> pd.DataFrame:
    """Return MACD features in input row order using current/past closes only."""
    if definition != MacdDefinition():
        raise ValueError("Phase 1 MACD parameters are frozen at 12/26/9 PRICE_CLOSE")
    if PRICE_FIELD not in bars.columns:
        raise ValueError("bars must contain a close column")

    close = pd.to_numeric(bars[PRICE_FIELD], errors="coerce")
    if close.isna().any():
        raise ValueError("close contains missing or non-numeric values")

    fast_ema = close.ewm(span=FAST_PERIOD, adjust=False, min_periods=1).mean()
    slow_ema = close.ewm(span=SLOW_PERIOD, adjust=False, min_periods=1).mean()
    main = fast_ema - slow_ema
    signal = main.rolling(SIGNAL_PERIOD, min_periods=SIGNAL_PERIOD).mean()
    histogram = main - signal
    slope = histogram.diff()

    previous = histogram.shift(1)
    crossover = np.select(
        [
            (previous <= 0) & (histogram > 0),
            (previous >= 0) & (histogram < 0),
        ],
        ["BULLISH_CROSS", "BEARISH_CROSS"],
        default="NONE",
    )
    crossover = pd.Series(crossover, index=bars.index, dtype="string")
    crossover[previous.isna() | histogram.isna()] = "UNAVAILABLE"

    return pd.DataFrame(
        {
            "macd_main": main,
            "macd_signal": signal,
            "histogram": histogram,
            "histogram_slope": slope,
            "crossover": crossover,
        },
        index=bars.index,
    )


def parity_metrics(
    fixture: pd.DataFrame,
    warmup_bars: int = PARITY_WARMUP_BARS,
    abs_tolerance: float = PARITY_ABS_TOLERANCE,
) -> dict:
    """Compare an MT5 fixture after a declared convergence warmup.

    The fixture starts inside a longer MT5 history and therefore does not
    expose the EMA accumulator state preceding its first row.  A fixed 200-bar
    convergence window is excluded for parity only; it is not used by the
    scientific dataset extractor.
    """
    required = {"close", "macd_main", "macd_signal"}
    missing = sorted(required - set(fixture.columns))
    if missing:
        raise ValueError(f"fixture missing columns: {missing}")
    if len(fixture) <= warmup_bars:
        raise ValueError("fixture is too short for the frozen parity warmup")

    calculated = extract_macd_features(fixture)
    comparison = fixture.iloc[warmup_bars:]
    calculated = calculated.iloc[warmup_bars:]
    main_error = np.abs(
        calculated["macd_main"].to_numpy()
        - pd.to_numeric(comparison["macd_main"]).to_numpy()
    )
    signal_error = np.abs(
        calculated["macd_signal"].to_numpy()
        - pd.to_numeric(comparison["macd_signal"]).to_numpy()
    )
    max_main = float(np.max(main_error))
    max_signal = float(np.max(signal_error))
    return {
        "rows_total": int(len(fixture)),
        "rows_compared": int(len(comparison)),
        "warmup_bars_excluded": warmup_bars,
        "absolute_tolerance": abs_tolerance,
        "max_abs_error_macd_main": max_main,
        "max_abs_error_macd_signal": max_signal,
        "mean_abs_error_macd_main": float(np.mean(main_error)),
        "mean_abs_error_macd_signal": float(np.mean(signal_error)),
        "status": "PASS" if max(max_main, max_signal) <= abs_tolerance else "FAIL",
    }
