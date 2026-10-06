#!/usr/bin/env python3
"""Build and freeze the outcome-blind MACD Phase 1 selection manifest."""
from __future__ import annotations

import json

from macd_execution_common import (
    SELECTION_PATH,
    file_sha256,
    load_analysis_frame,
    load_frozen_preregistration,
    prepare_observations,
    run_outcome_blind_matching,
)


def build_manifest() -> dict:
    prereg = load_frozen_preregistration()
    frame = load_analysis_frame(prereg)
    events, control_rows, missing = prepare_observations(prereg, frame)
    matches, reuse = run_outcome_blind_matching(prereg, frame, events, control_rows)
    event_by_id = {event["event_id"]: event for event in events}
    match_by_id = {match["event_id"]: match for match in matches}

    cells = []
    for cell_id in prereg["test_family"]["cells"]:
        _, regime, direction, threshold_id = cell_id.split("__")
        cell_events = [e for e in events if e["regime_v1"] == regime and e["direction"] == direction]
        evaluable = [e for e in cell_events if e["complete_horizon"]]
        matched = [e for e in evaluable if match_by_id[e["event_id"]]["status"] in ("MATCHED", "MATCHED_K_SHORTFALL")]
        reason_codes = []
        if len(evaluable) < prereg["selection"]["minimum_raw_sample_per_cell"]:
            reason_codes.append("INSUFFICIENT_RAW_SAMPLE")
        if len(matched) < prereg["selection"]["minimum_matched_events_per_cell"]:
            reason_codes.append("INSUFFICIENT_CONTROLS")
        cells.append({
            "cell_id": cell_id,
            "regime": regime,
            "direction": direction,
            "threshold_id": threshold_id,
            "raw_crossover_count": len(cell_events),
            "complete_horizon_count": len(evaluable),
            "matched_event_count": len(matched),
            "selection_eligible": not reason_codes,
            "reason_codes": reason_codes,
        })

    return {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_OUTCOME_TEST",
        "outcome_data_read": False,
        "allowed_inputs_used": ["raw crossover counts", "current-bar missingness", "horizon availability", "control-pool availability"],
        "forbidden_inputs_used": [],
        "preregistration_sha256": file_sha256(SELECTION_PATH.parent / "macd_preregistration_v1.json"),
        "dataset_rows": len(frame),
        "event_summary": {
            "total_crossovers": len(events),
            "BUY": sum(e["direction"] == "BUY" for e in events),
            "SELL": sum(e["direction"] == "SELL" for e in events),
            "missingness": missing,
        },
        "control_summary": {
            "eligible_physical_control_rows": len(control_rows),
            "directional_control_records": len(control_rows) * 2,
            "reuse": reuse,
        },
        "cells": cells,
        "events": events,
        "matching": matches,
        "guardrail": "No future price path, outcome, effect, p-value, confidence interval, outcome-derived ESS, or cost performance was read to build this artifact."
    }


def main() -> int:
    manifest = build_manifest()
    SELECTION_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "outcome_data_read": manifest["outcome_data_read"],
        "event_summary": manifest["event_summary"],
        "control_summary": manifest["control_summary"],
        "eligible_cells": sum(c["selection_eligible"] for c in manifest["cells"]),
        "ineligible_cells": sum(not c["selection_eligible"] for c in manifest["cells"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
