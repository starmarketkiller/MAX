#!/usr/bin/env python3
"""Confirmatory density gate (Phase 7.35) — calendar sample-size check.

NOT the full NEXUS Power Gate V1 (often NOT_ASSESSABLE). This is a cheap,
deterministic preflight: refuse confirmatory windows whose expected n is
below min_n given an observed trades/month rate from a prior diagnostic.

Usage:
  python3 scripts/confirmatory_density_gate.py \\
    --trades-per-month 2.5 --months 3.5 --min-n 30 --buy-share 0.4

Exit 0 + verdict ALLOW only when expected_n_B >= min_n.
Exit 2 + verdict REFUSE otherwise (still prints JSON).
"""
from __future__ import annotations

import argparse
import json
import sys


def assess(*, trades_per_month: float, months: float, min_n: int, buy_share: float) -> dict:
    if trades_per_month < 0 or months <= 0 or min_n < 1 or not (0 < buy_share <= 1):
        return {
            "verdict": "INVALID_INPUT",
            "allow": False,
            "reason": "trades_per_month>=0, months>0, min_n>=1, 0<buy_share<=1 required",
        }
    expected_n = trades_per_month * months
    expected_n_B = expected_n * buy_share
    months_needed = (min_n / (trades_per_month * buy_share)) if (trades_per_month * buy_share) > 0 else None
    allow = expected_n_B >= min_n
    return {
        "verdict": "ALLOW" if allow else "REFUSE",
        "allow": allow,
        "inputs": {
            "trades_per_month": trades_per_month,
            "months": months,
            "min_n": min_n,
            "buy_share": buy_share,
        },
        "expected_n_all": round(expected_n, 2),
        "expected_n_B": round(expected_n_B, 2),
        "months_needed_for_min_n_B": round(months_needed, 1) if months_needed is not None else None,
        "note": (
            "Deterministic density preflight only. Does not replace Power Gate V1 / "
            "prereg / isolation. REFUSE means do not spend a confirmatory MT5 run yet."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades-per-month", type=float, required=True)
    ap.add_argument("--months", type=float, required=True)
    ap.add_argument("--min-n", type=int, default=30)
    ap.add_argument("--buy-share", type=float, default=1.0,
                    help="Fraction of trades kept after side filter (default 1.0)")
    args = ap.parse_args()
    card = assess(
        trades_per_month=args.trades_per_month,
        months=args.months,
        min_n=args.min_n,
        buy_share=args.buy_share,
    )
    print(json.dumps(card, indent=2, ensure_ascii=True))
    if card["verdict"] == "INVALID_INPUT":
        return 1
    return 0 if card["allow"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
