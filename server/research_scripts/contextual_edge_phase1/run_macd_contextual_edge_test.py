#!/usr/bin/env python3
"""Execute the frozen MACD Phase 1 test without changing selection/spec."""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

from macd_execution_common import (
    HERE,
    ROOT,
    SELECTION_PATH,
    SELECTION_SIDECAR,
    file_sha256,
    load_analysis_frame,
    load_frozen_preregistration,
)


RESULT_PATH = HERE / "macd_contextual_edge_test_result_v1.json"
EVIDENCE_PATH = HERE / "macd_evidence_record_v1.json"
DECISION_PATH = HERE / "macd_decision_card_v1.json"
LIMITATIONS_PATH = HERE / "macd_limitations_v1.json"
REGISTRY_PROPOSAL_PATH = HERE / "macd_component_value_registry_proposal_v1.json"
EXPECTED_SELECTION_SHA256 = "3a70d28a56ff7f3dab2fdbe49630963d453e7bb45f1fdac20720d47ecfd6d23e"
N_BOOT = 2000
SEED = 42
COST_PROFILES = {
    "ZERO_COST": {"spread_price": 0.0, "slippage_price": 0.0, "commission_r": 0.0},
    "BROKER_BASELINE": {"spread_price": 0.55, "slippage_price": 0.10, "commission_r": 0.0},
    "CONSERVATIVE": {"spread_price": 0.70, "slippage_price": 0.15, "commission_r": 0.0},
    "STRESS": {"spread_price": 1.30, "slippage_price": 0.25, "commission_r": 0.0},
}
THRESHOLD_BY_ID = {
    "T0_25_ATR": 0.25,
    "T0_5_ATR": 0.5,
    "T1_0_ATR": 1.0,
    "T1_5_ATR": 1.5,
    "T2_0_ATR": 2.0,
    "T3_0_ATR": 3.0,
}


def _load_engines():
    engine_dir = ROOT / "server/research_scripts/phase7/engine"
    dependence_dir = ROOT / "server/research_scripts/phase6_5"
    sys.path.insert(0, str(engine_dir))
    sys.path.insert(0, str(dependence_dir))
    try:
        from matched_pair_permutation_test import block_sign_flip_permutation_p
        from multiple_testing_v2 import benjamini_hochberg
        from dependence_diagnostics import full_dependence_report
        from block_bootstrap import compare_iid_vs_block
        return block_sign_flip_permutation_p, benjamini_hochberg, full_dependence_report, compare_iid_vs_block
    finally:
        sys.path.pop(0)
        sys.path.pop(0)


def load_frozen_selection() -> dict:
    actual = file_sha256(SELECTION_PATH)
    sidecar = SELECTION_SIDECAR.read_text(encoding="ascii").strip().split()[0]
    if actual != EXPECTED_SELECTION_SHA256 or sidecar != EXPECTED_SELECTION_SHA256:
        raise RuntimeError("selection manifest hash mismatch; fail-closed")
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    if selection.get("status") != "FROZEN_BEFORE_OUTCOME_TEST" or selection.get("outcome_data_read") is not False:
        raise RuntimeError("selection manifest is not an outcome-blind frozen artifact")
    return selection


def threshold_outcome(frame, row: int, direction: str, threshold: float, profile: dict) -> int | None:
    horizon = 40
    future = frame.iloc[row + 1:row + 1 + horizon]
    if len(future) != horizon:
        return None
    entry = float(frame.at[row, "close"])
    atr = float(frame.at[row, "atr"])
    if not np.isfinite(atr) or atr <= 0:
        return None
    if direction == "BUY":
        favorable = (future["high"].to_numpy(dtype=float) - entry) / atr
        adverse = (entry - future["low"].to_numpy(dtype=float)) / atr
    else:
        favorable = (entry - future["low"].to_numpy(dtype=float)) / atr
        adverse = (future["high"].to_numpy(dtype=float) - entry) / atr

    # Existing frozen cost convention: spread once round-trip; slippage on
    # entry and on market exits (stop), but not on a limit target.
    target_cost_atr = (profile["spread_price"] + profile["slippage_price"]) / atr + profile["commission_r"]
    stop_cost_atr = (profile["spread_price"] + 2 * profile["slippage_price"]) / atr + profile["commission_r"]
    target_hits = favorable >= (threshold + target_cost_atr)
    stop_hits = adverse >= max(0.0, 1.0 - stop_cost_atr)
    target_idx = int(np.argmax(target_hits)) if np.any(target_hits) else None
    stop_idx = int(np.argmax(stop_hits)) if np.any(stop_hits) else None
    if target_idx is None and stop_idx is None:
        return None
    if target_idx is not None and (stop_idx is None or target_idx <= stop_idx):
        return 1
    return 0


def resolved_pairs(frame, selection: dict, cell: dict, profile: dict) -> list[dict]:
    event_lookup = {event["event_id"]: event for event in selection["events"]}
    pairs = []
    for match in selection["matching"]:
        event = event_lookup[match["event_id"]]
        if event["regime_v1"] != cell["regime"] or event["direction"] != cell["direction"]:
            continue
        if match["status"] not in ("MATCHED", "MATCHED_K_SHORTFALL") or len(match["matches"]) != 5:
            continue
        threshold = THRESHOLD_BY_ID[cell["threshold_id"]]
        event_value = threshold_outcome(frame, event["row"], event["direction"], threshold, profile)
        controls = [
            threshold_outcome(frame, int(item["control_id"].split(":")[0][1:]), event["direction"], threshold, profile)
            for item in match["matches"]
        ]
        if event_value is None or any(value is None for value in controls):
            continue
        pairs.append({
            "event_id": event["event_id"], "row": event["row"],
            "event_value": event_value, "control_values": controls,
            "paired_difference": float(event_value - np.mean(controls)),
        })
    return sorted(pairs, key=lambda item: item["row"])


def dependence_report(pairs, label, full_dependence_report, compare_iid_vs_block):
    rows = [pair["row"] for pair in pairs]
    outcomes = {pair["row"]: pair["event_value"] for pair in pairs}
    directions = {pair["row"]: "FROZEN_CELL_DIRECTION" for pair in pairs}
    report = full_dependence_report(rows, directions, outcomes, label=label)
    block = compare_iid_vs_block([pair["event_value"] for pair in pairs], n_boot=N_BOOT, seed=SEED)
    return {
        "cluster_count_ess": report["n_effective"]["cluster_count_approximation"],
        "autocorrelation_ess": report["n_effective"]["autocorrelation_based"],
        "block_bootstrap_variance_ess": block["ess_from_block_bootstrap_variance"],
        "overlap_rate": report["overlap_rate"],
        "dependence_flag": report["dependence_flag"],
        "method_details": {
            "cluster_gap_threshold_bars": report["cluster_gap_threshold_bars"],
            "autocorrelation": report["outcome_autocorrelation"],
            "block_bootstrap": block["block_bootstrap"],
        },
    }


def execute():
    prereg = load_frozen_preregistration()
    selection = load_frozen_selection()
    frame = load_analysis_frame(prereg)
    permutation, bh_fn, dependence_fn, block_fn = _load_engines()

    cells = []
    raw_p_values = []
    zero_profile = COST_PROFILES["ZERO_COST"]
    for selected in selection["cells"]:
        pairs = resolved_pairs(frame, selection, selected, zero_profile) if selected["selection_eligible"] else []
        reasons = list(selected["reason_codes"])
        if selected["selection_eligible"] and len(pairs) < prereg["selection"]["minimum_raw_sample_per_cell"]:
            reasons.append("INSUFFICIENT_RESOLVED_PAIRS")
        if reasons:
            p_value = 1.0
            permutation_result = {"n": len(pairs), "p_value": 1.0, "method": "NOT_TESTED_FIXED_P_ONE"}
        else:
            permutation_result = permutation(
                [pair["paired_difference"] for pair in pairs], n_boot=N_BOOT, seed=SEED
            )
            p_value = permutation_result["p_value"]
        effect = float(np.mean([pair["paired_difference"] for pair in pairs])) if pairs else None
        event_rate = float(np.mean([pair["event_value"] for pair in pairs])) if pairs else None
        control_rate = float(np.mean([np.mean(pair["control_values"]) for pair in pairs])) if pairs else None
        dependence = dependence_report(pairs, selected["cell_id"], dependence_fn, block_fn) if pairs else None
        cell = {
            **selected,
            "resolved_pair_count": len(pairs),
            "censored_pair_count": max(0, selected["matched_event_count"] - len(pairs)),
            "event_target_first_rate": event_rate,
            "matched_control_target_first_rate": control_rate,
            "paired_effect": effect,
            "raw_p_value": p_value,
            "test_reason_codes": reasons,
            "permutation": permutation_result,
            "dependence": dependence,
        }
        cells.append(cell)
        raw_p_values.append((selected["cell_id"], p_value))

    bh = bh_fn(raw_p_values, q=prereg["test_family"]["bh_fdr_q"])
    primary_cells = []
    for cell in cells:
        adjustment = bh[cell["cell_id"]]
        cell["bh"] = adjustment
        cell["primary_statistical_criterion_met"] = bool(
            cell["selection_eligible"]
            and cell["resolved_pair_count"] >= 30
            and cell["paired_effect"] is not None and cell["paired_effect"] > 0
            and adjustment["adjusted_p_bh"] <= 0.10
        )
        ess_values = [] if cell["dependence"] is None else [
            cell["dependence"]["cluster_count_ess"],
            cell["dependence"]["autocorrelation_ess"],
            cell["dependence"]["block_bootstrap_variance_ess"],
        ]
        cell["low_ess_interpretation"] = bool(
            ess_values and any(value is None or value < 30 for value in ess_values)
        )
        if cell["primary_statistical_criterion_met"]:
            primary_cells.append(cell)

    economic = []
    for cell in primary_cells:
        profile_results = {}
        for profile_name, profile in COST_PROFILES.items():
            pairs = resolved_pairs(frame, selection, cell, profile)
            effect = float(np.mean([pair["paired_difference"] for pair in pairs])) if pairs else None
            profile_results[profile_name] = {
                "resolved_pair_count": len(pairs),
                "paired_effect": effect,
                "effect_positive": effect is not None and effect > 0,
            }
        economic.append({
            "cell_id": cell["cell_id"],
            "admission_reason": "PRIMARY_STATISTICAL_CRITERION_MET",
            "profiles": profile_results,
            "survives_all_nonzero_profiles": all(
                profile_results[name]["effect_positive"]
                for name in ("BROKER_BASELINE", "CONSERVATIVE", "STRESS")
            ),
        })

    interpretable_positive = [c for c in primary_cells if not c["low_ess_interpretation"]]
    if interpretable_positive:
        verdict, grade = "PROMISING", "E2"
        rationale = "At least one frozen cell met the BH-adjusted primary criterion with all three ESS estimates >=30; DISCOVERY_REUSE caps the result below SUPPORTED."
    elif primary_cells:
        verdict, grade = "WEAK", "E1"
        rationale = "A primary statistical result exists, but preregistered dependence diagnostics force INSUFFICIENT_EVIDENCE interpretation."
    else:
        verdict, grade = "WEAK", "E1"
        rationale = "No frozen cell met the preregistered positive paired-effect plus BH q<=0.10 criterion."

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result = {
        "schema_version": 1,
        "status": "EXECUTED_NOT_COMMITTED",
        "component_id": prereg["component_id"],
        "preregistration_sha256": file_sha256(HERE / "macd_preregistration_v1.json"),
        "selection_manifest_sha256": file_sha256(SELECTION_PATH),
        "execution_commit": head,
        "dataset_id": prereg["dataset"]["dataset_id"],
        "validation_integrity": "DISCOVERY_REUSE",
        "family_size": len(cells),
        "bh_q": prereg["test_family"]["bh_fdr_q"],
        "permutation_defaults": {"n_boot": N_BOOT, "seed": SEED, "source": "matched_pair_permutation_test.py canonical defaults"},
        "cells": cells,
        "economic_stage": economic,
        "summary": {
            "crossovers": selection["event_summary"],
            "selection_eligible_cells": sum(c["selection_eligible"] for c in cells),
            "selection_ineligible_cells": sum(not c["selection_eligible"] for c in cells),
            "cells_with_positive_effect": sum(c["paired_effect"] is not None and c["paired_effect"] > 0 for c in cells),
            "cells_meeting_primary_criterion": len(primary_cells),
            "cells_entering_economic_stage": len(economic),
            "cells_with_low_ess": sum(c["low_ess_interpretation"] for c in cells),
            "verdict": verdict,
            "evidence_grade": grade,
            "supported": False,
            "rationale": rationale,
        },
        "guardrails": {
            "preregistration_modified": False,
            "selection_recomputed_after_outcome": False,
            "dependence_modified_p_or_bh": False,
            "supported_impossible_on_discovery_reuse": True,
            "registry_mutated": False,
        },
    }
    return result


def write_artifacts(result):
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summary = result["summary"]
    nominal_cell = next(
        cell for cell in result["cells"]
        if cell["cell_id"] == "MACD__LOW_VOL__SELL__T1_0_ATR"
    )
    post_hoc_observation = {
        "classification": "POST_HOC_OBSERVATION_NOT_CONFIRMED",
        "cell_id": "MACD__LOW_VOL__SELL__T1_0_ATR",
        "regime": "LOW_VOL",
        "direction": "SELL",
        "threshold_atr": 1.0,
        "paired_effect": nominal_cell["paired_effect"],
        "raw_p_value": nominal_cell["raw_p_value"],
        "bh_q_value": nominal_cell["bh"]["adjusted_p_bh"],
        "interpretation": "Nominal observation only; it did not survive the frozen 60-cell BH family.",
        "restrictions": [
            "Do not promote this cell.",
            "Do not narrow the frozen family to rescue it.",
            "Do not immediately retest it on the same dataset.",
            "A future test requires a new preregistration and independent data."
        ],
    }
    evidence = {
        "schema_version": 1,
        "evidence_id": "EVD-MACD-CONTEXTUAL-PHASE1-001",
        "component_id": result["component_id"],
        "evidence_grade": summary["evidence_grade"],
        "verdict": summary["verdict"],
        "validation_integrity": result["validation_integrity"],
        "source_result": RESULT_PATH.name,
        "source_result_sha256": file_sha256(RESULT_PATH),
        "preregistration_sha256": result["preregistration_sha256"],
        "selection_manifest_sha256": result["selection_manifest_sha256"],
        "facts": summary,
        "post_hoc_observations": [post_hoc_observation],
        "is_validated_edge": False,
        "is_deployable": False,
    }
    EVIDENCE_PATH.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    decision = {
        "schema_version": 1,
        "decision_card_id": "DC-MACD-CONTEXTUAL-PHASE1-001",
        "decision": summary["verdict"],
        "evidence_grade": summary["evidence_grade"],
        "supported": False,
        "rationale": summary["rationale"],
        "automatic_registry_mutation": False,
        "closure_status": "CLOSED_WEAK",
        "post_hoc_observation": post_hoc_observation,
        "next_step": "No immediate MACD retest. Any future test of the nominal observation requires a new preregistration and independent data.",
        "source_evidence": EVIDENCE_PATH.name,
    }
    DECISION_PATH.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    limitations = {
        "schema_version": 1,
        "limitations": [
            "Dataset is DISCOVERY_REUSE, not TRUE_HOLDOUT.",
            "Phase 5.5 and Phase 7.27 regime classifiers have PARTIAL semantic compatibility only.",
            "Crossover observations and 40-bar windows overlap; three ESS diagnostics are reported separately.",
            "Intrabar ordering is unavailable; target wins same-bar ties consistently with the reused Phase 5 outcome primitive.",
            "Cost-stage path adjustment reuses the frozen repository convention: spread once, slippage at entry and market stop exit, no slippage at limit target.",
            "No result may be interpreted as profitability, deployment eligibility, or a standalone MACD strategy validation.",
            "The LOW_VOL / SELL / 1.0 ATR cell is post-hoc and unconfirmed because raw p=0.02249 did not survive the frozen 60-cell BH family (q=1.0)."
        ],
        "provenance": {
            "preregistration": result["preregistration_sha256"],
            "selection": result["selection_manifest_sha256"],
            "result": file_sha256(RESULT_PATH),
        },
    }
    LIMITATIONS_PATH.write_text(json.dumps(limitations, indent=2) + "\n", encoding="utf-8")
    proposal = {
        "schema_version": 1,
        "proposal_id": "PROP-MACD-COMPONENT-VALUE-PHASE1-001",
        "strategy_id": "MACD",
        "field": "component_value_status",
        "current_value": "NOT_EVALUATED",
        "proposed_value": "WEAK",
        "automatic_mutation": False,
        "requires_joint_review": True,
        "scope": {
            "timeframe": "H4",
            "parameters": {"fast": 12, "slow": 26, "signal": 9, "price": "PRICE_CLOSE"},
            "representation": "CAUSAL_CROSSOVER",
            "regime_source": "PHASE5_5_H4_REGIME_V1",
            "pilot": "CONTEXTUAL_EDGE_PHASE1_MACD_V1",
        },
        "does_not_apply_to": [
            "continuous MACD value",
            "histogram slope",
            "zero-line distance",
            "acceleration",
            "divergence",
            "other MACD parameters, timeframes, regimes, or combinations"
        ],
        "evidence": {
            "record": EVIDENCE_PATH.name,
            "result": RESULT_PATH.name,
            "result_sha256": file_sha256(RESULT_PATH),
            "verdict": "WEAK",
            "evidence_grade": "E1",
            "validation_integrity": "DISCOVERY_REUSE",
        },
        "runtime_change": False,
    }
    REGISTRY_PROPOSAL_PATH.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    result = execute()
    write_artifacts(result)
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
