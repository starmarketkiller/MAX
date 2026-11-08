#!/usr/bin/env python3
"""Validate NEXUS_EDGE_SHORTLIST_GOLD.set against Inputs defaults and shortlist."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SET_PATH = ROOT / "MQL5" / "Profiles" / "NEXUS_EDGE_SHORTLIST_GOLD.set"
INPUTS = ROOT / "MQL5" / "Include" / "NEXUS_v1" / "NXS_Inputs.mqh"

SHORTLIST_INPUTS = {
    "InpStrat_FVG_CONT",
    "InpStrat_LIQ_SWEEP",
    "InpStrat_ORDER_BLOCK",
    "InpStrat_BREAKOUT_ACC",
    "InpStrat_ZScoreBreakout",
    "InpStrat_EMA_PULLBACK",
}

HARD_DENY_INPUTS = {
    "InpStrat_MACD",
    "InpStrat_RSI_DIV",
    "InpStrat_TSI",
    "InpStrat_BB_SQUEEZE",
    "InpStrat_SH_BMS_RTO",
    "InpStrat_SH_BMS_RTO_V2",
    "InpStrat_SilverBullet",
}

BOOK_REQUIRED = {
    "InpBookMode": "1",
    "InpUseStrategyProfiles": "true",
    "InpUseInstitutionalCore": "false",
    "InpDataCollectionMode": "false",
    "InpLiveTradingAuthorized": "false",
}


def _parse_set(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        values[key.strip()] = val.strip().lower()
    return values


def _parse_input_bool_defaults(text: str) -> dict[str, bool]:
    found: dict[str, bool] = {}
    for match in re.finditer(
        r"input\s+bool\s+(Inp(?:Strat_|UseStrat_|UseStruct)\w*)\s*=\s*(true|false)\s*;",
        text,
    ):
        found[match.group(1)] = match.group(2) == "true"
    return found


def main() -> int:
    values = _parse_set(SET_PATH.read_text(encoding="utf-8"))
    defaults = _parse_input_bool_defaults(INPUTS.read_text(encoding="utf-8"))

    for key, want in BOOK_REQUIRED.items():
        if values.get(key) != want:
            print(f"FAIL: {key} expected {want}, got {values.get(key)}")
            return 1

    for key in SHORTLIST_INPUTS:
        if values.get(key) != "true":
            print(f"FAIL: shortlist {key} must be true")
            return 1

    for key in HARD_DENY_INPUTS:
        if values.get(key) != "false":
            print(f"FAIL: hard-deny {key} must be false")
            return 1

    missing = []
    for name, default_on in defaults.items():
        if name in SHORTLIST_INPUTS:
            continue
        if default_on and values.get(name) != "false":
            missing.append(name)
    if missing:
        print("FAIL: default-true toggles not forced false in .set:")
        print(" ", ", ".join(sorted(missing)))
        return 1

    print(
        f"OK: EDGE_SHORTLIST .set complete "
        f"({len(SHORTLIST_INPUTS)} shortlist on, "
        f"{sum(1 for v in defaults.values() if v)} default-true forced off)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
