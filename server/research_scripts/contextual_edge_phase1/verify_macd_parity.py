#!/usr/bin/env python3
"""Generate the bounded MACD/MT5 parity diagnostic artifact."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from macd_features import (
    FAST_PERIOD,
    PARITY_ABS_TOLERANCE,
    PARITY_WARMUP_BARS,
    PRICE_FIELD,
    SIGNAL_PERIOD,
    SLOW_PERIOD,
    parity_metrics,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = (
    ROOT / "results/cost_calibration_67_rerun/mt5_macd_indicators_may_aug.csv",
    ROOT / "results/cost_calibration_67_rerun/mt5_macd_indicators_may_aug_extended.csv",
)
OUT = Path(__file__).resolve().parent / "macd_parity_report_v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_report() -> dict:
    fixtures = []
    for path in FIXTURES:
        metrics = parity_metrics(pd.read_csv(path))
        fixtures.append(
            {
                "source_file": path.relative_to(ROOT).as_posix(),
                "sha256": sha256(path),
                **metrics,
            }
        )
    status = "MACD_PARITY_PASS" if all(f["status"] == "PASS" for f in fixtures) else "MACD_PARITY_FAIL"
    return {
        "schema_version": 1,
        "status": status,
        "feature_definition": {
            "fast": FAST_PERIOD,
            "slow": SLOW_PERIOD,
            "signal": SIGNAL_PERIOD,
            "price_field": PRICE_FIELD,
            "main_line": "EMA(close,12)-EMA(close,26)",
            "signal_line": "SMA(macd_main,9)",
            "observation_point": "closed H4 bar only",
        },
        "parity_policy": {
            "absolute_tolerance": PARITY_ABS_TOLERANCE,
            "warmup_bars_excluded": PARITY_WARMUP_BARS,
            "warmup_reason": "Fixture starts without MT5 pre-window EMA accumulator state; fixed convergence exclusion, never tuned against scientific outcomes.",
        },
        "fixtures": fixtures,
        "scientific_outcomes_read": False,
    }


def main() -> int:
    report = build_report()
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "MACD_PARITY_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
