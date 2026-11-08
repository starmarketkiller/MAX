#!/usr/bin/env python3
"""Fail if registry freeze / FAILED defaults disagree with the EA inputs.

Deterministic Tier-0 check for the credit-safe edge loop.
Usage: python3 scripts/edge_freeze_check.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "contracts" / "edge-validation-registry.json"
INPUTS = ROOT / "MQL5" / "Include" / "NEXUS_v1" / "NXS_Inputs.mqh"
EDGE_BOOK = ROOT / "MQL5" / "Include" / "NEXUS_v1" / "NXS_EdgeBook.mqh"

# Maps registry strategy_id -> EA input default identifier.
INPUT_ALIASES = {
    "MACD": "InpStrat_MACD",
    "RSI_DIV": "InpStrat_RSI_DIV",
    "BB_SQUEEZE": "InpStrat_BB_SQUEEZE",
    "TSI": "InpStrat_TSI",
    "SH_BMS_RTO": "InpStrat_SH_BMS_RTO",
    "SILVER_BULLET": "InpStrat_SilverBullet",
    "CRT": None,  # profile-disabled / research-only, no dedicated live default check here
}

SHORTLIST = {
    "FVG_CONT",
    "LIQ_SWEEP",
    "ORDER_BLOCK",
    "BREAKOUT_ACC",
    "Z_SCORE_BREAKOUT",
    "EMA_PULLBACK",
}


def _parse_bool_defaults(text: str) -> dict[str, bool]:
    found: dict[str, bool] = {}
    for match in re.finditer(
        r"input\s+bool\s+(Inp\w+)\s*=\s*(true|false)\s*;", text
    ):
        found[match.group(1)] = match.group(2) == "true"
    return found


def main() -> int:
    data = json.loads(REG.read_text(encoding="utf-8"))
    items = data["strategies"] if isinstance(data, dict) else data
    by_id = {s["strategy_id"]: s for s in items}

    offenders = [
        s["strategy_id"]
        for s in items
        if s.get("defect_status") == "DEFECT_BLOCKED" and s.get("default_enabled")
    ]
    if offenders:
        print("FAIL: DEFECT_BLOCKED still default_enabled:", ", ".join(offenders))
        return 1

    failed_on = [
        s["strategy_id"]
        for s in items
        if s.get("standalone_edge_status") == "FAILED" and s.get("default_enabled")
    ]
    if failed_on:
        print("FAIL: FAILED still default_enabled:", ", ".join(failed_on))
        return 1

    fvg = by_id["FVG_CONT"]
    if fvg.get("defect_status") != "REMEDIATED":
        print("FAIL: FVG_CONT defect_status expected REMEDIATED, got", fvg.get("defect_status"))
        return 1

    inputs_text = INPUTS.read_text(encoding="utf-8")
    defaults = _parse_bool_defaults(inputs_text)
    for strategy_id, input_name in INPUT_ALIASES.items():
        if input_name is None:
            continue
        strat = by_id.get(strategy_id)
        if strat is None:
            print("FAIL: registry missing", strategy_id)
            return 1
        if input_name not in defaults:
            print("FAIL: EA input missing", input_name)
            return 1
        want_enabled = bool(strat.get("default_enabled"))
        if defaults[input_name] != want_enabled:
            print(
                f"FAIL: {input_name} default={defaults[input_name]} "
                f"but registry {strategy_id}.default_enabled={want_enabled}"
            )
            return 1

    if "InpBookMode" not in inputs_text or "NXS_BOOK_EDGE_SHORTLIST" not in inputs_text:
        print("FAIL: InpBookMode / NXS_BOOK_EDGE_SHORTLIST missing from NXS_Inputs.mqh")
        return 1

    edge_text = EDGE_BOOK.read_text(encoding="utf-8")
    for name in SHORTLIST:
        if f'"{name}"' not in edge_text:
            print("FAIL: shortlist name missing from NXS_EdgeBook.mqh:", name)
            return 1
    for name in ("MACD", "RSI_DIV", "BB_SQUEEZE", "TSI", "SILVER_BULLET"):
        if f'"{name}"' not in edge_text:
            print("FAIL: hard-deny name missing from NXS_EdgeBook.mqh:", name)
            return 1

    profiles = (ROOT / "MQL5" / "Include" / "NEXUS_v1" / "NXS_StrategyProfiles.mqh").read_text(
        encoding="utf-8"
    )
    if "NXS_EdgeBook_Allows(name)" not in profiles:
        print("FAIL: NXS_Profile_Enabled must call NXS_EdgeBook_Allows")
        return 1

    ea = (ROOT / "MQL5" / "Experts" / "NEXUS_EA_v2.mq5").read_text(encoding="utf-8")
    if 'NXS_EdgeBook_Allows("FVG_CONT")' not in ea:
        print("FAIL: NXS_CollectRaw must gate FVG_CONT through EdgeBook")
        return 1

    if "InpRiskProfile == 4" not in edge_text:
        print("FAIL: EdgeBook preflight must refuse PRESET_MVP_v206")
        return 1

    print(
        "OK: freeze/FAILED defaults aligned; FVG_CONT REMEDIATED; "
        "EDGE_SHORTLIST book present"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
