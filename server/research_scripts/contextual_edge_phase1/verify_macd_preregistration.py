#!/usr/bin/env python3
"""Fail-closed verifier for the frozen MACD Phase 1 preregistration."""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PREREG = HERE / "macd_preregistration_v1.json"
SIDECAR = HERE / "macd_preregistration_v1.sha256"
DIAGNOSTICS = (
    HERE / "macd_parity_report_v1.json",
    HERE / "regime_compatibility_diagnostic_v1.json",
)
REGIMES = ["HIGH_VOL", "LOW_VOL", "TRANSITION", "TRENDING", "RANGING"]
DIRECTIONS = ["BUY", "SELL"]
THRESHOLDS = ["T0_25_ATR", "T0_5_ATR", "T1_0_ATR", "T1_5_ATR", "T2_0_ATR", "T3_0_ATR"]


def expected_cells() -> list[str]:
    return [f"MACD__{regime}__{direction}__{threshold}"
            for regime, direction, threshold in itertools.product(REGIMES, DIRECTIONS, THRESHOLDS)]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify() -> dict:
    errors = []
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    sidecar = SIDECAR.read_text(encoding="ascii").strip().split()[0] if SIDECAR.exists() else None
    actual_hash = file_sha256(PREREG)

    if prereg.get("status") != "FROZEN_NOT_EXECUTED":
        errors.append("status is not FROZEN_NOT_EXECUTED")
    if sidecar != actual_hash:
        errors.append("preregistration SHA-256 sidecar mismatch")
    if prereg["regime"].get("states_in_frozen_order") != REGIMES:
        errors.append("frozen regime IDs/order changed")
    if prereg["test_family"].get("cells") != expected_cells():
        errors.append("frozen 60-cell family changed")
    if prereg["test_family"].get("frozen_cell_count") != 60:
        errors.append("frozen_cell_count is not 60")
    if prereg["test_family"].get("bh_fdr_q") != 0.10:
        errors.append("BH q changed")
    if prereg["test_family"].get("horizon_H4_bars") != 40:
        errors.append("horizon changed")

    baseline = prereg.get("baseline", {})
    expected_baseline = {
        "match_dimensions": ["regime_v1", "period_bucket"],
        "controls_per_event_k": 5,
        "minimum_control_pool_after_filters": 20,
        "max_control_reuse_per_run": 3,
        "within_split_only": True,
    }
    for field, expected in expected_baseline.items():
        if baseline.get(field) != expected:
            errors.append(f"baseline {field} changed")

    if prereg["dependence_diagnostics"].get("diagnostic_may_gate_p_value_or_bh") is not False:
        errors.append("dependence diagnostic may gate p-value/BH")
    if prereg["execution_state"].get("selection_executed") is not False:
        errors.append("selection already marked executed")
    if prereg["execution_state"].get("scientific_test_executed") is not False:
        errors.append("scientific test already marked executed")

    diagnostic_status = {}
    for path in DIAGNOSTICS:
        artifact = json.loads(path.read_text(encoding="utf-8"))
        outcome_blind = artifact.get("scientific_outcomes_read") is False
        diagnostic_status[path.name] = {"scientific_outcomes_read": artifact.get("scientific_outcomes_read")}
        if not outcome_blind:
            errors.append(f"{path.name} is not outcome-blind")

    return {
        "status": "PASS" if not errors else "FAIL",
        "preregistration_sha256": actual_hash,
        "sidecar_sha256": sidecar,
        "cell_count": len(prereg["test_family"].get("cells", [])),
        "diagnostics": diagnostic_status,
        "errors": errors,
    }


def main() -> int:
    result = verify()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
