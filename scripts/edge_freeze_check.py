#!/usr/bin/env python3
"""Fail if any DEFECT_BLOCKED strategy is still default_enabled.

Deterministic Tier-0 check for the credit-safe edge loop.
Usage: python3 scripts/edge_freeze_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "contracts" / "edge-validation-registry.json"


def main() -> int:
    data = json.loads(REG.read_text(encoding="utf-8"))
    items = data["strategies"] if isinstance(data, dict) else data
    offenders = [
        s["strategy_id"]
        for s in items
        if s.get("defect_status") == "DEFECT_BLOCKED" and s.get("default_enabled")
    ]
    if offenders:
        print("FAIL: DEFECT_BLOCKED still default_enabled:", ", ".join(offenders))
        return 1
    fvg = next(s for s in items if s["strategy_id"] == "FVG_CONT")
    if fvg.get("defect_status") != "REMEDIATED":
        print("FAIL: FVG_CONT defect_status expected REMEDIATED, got", fvg.get("defect_status"))
        return 1
    print("OK: no DEFECT_BLOCKED enabled; FVG_CONT defect REMEDIATED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
