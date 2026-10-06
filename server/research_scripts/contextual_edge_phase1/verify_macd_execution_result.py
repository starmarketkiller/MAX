#!/usr/bin/env python3
"""Consistency verifier for the uncommitted MACD Phase 1 result packet."""
from __future__ import annotations

import json

from macd_execution_common import (
    HERE,
    SELECTION_PATH,
    file_sha256,
    load_frozen_preregistration,
)
from run_macd_contextual_edge_test import (
    DECISION_PATH,
    EVIDENCE_PATH,
    EXPECTED_SELECTION_SHA256,
    LIMITATIONS_PATH,
    REGISTRY_PROPOSAL_PATH,
    RESULT_PATH,
    load_frozen_selection,
)


def verify() -> dict:
    errors = []
    prereg = load_frozen_preregistration()
    selection = load_frozen_selection()
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    limitations = json.loads(LIMITATIONS_PATH.read_text(encoding="utf-8"))
    proposal = json.loads(REGISTRY_PROPOSAL_PATH.read_text(encoding="utf-8"))

    if file_sha256(SELECTION_PATH) != EXPECTED_SELECTION_SHA256:
        errors.append("selection hash drift")
    if selection.get("outcome_data_read") is not False:
        errors.append("selection was not outcome-blind")
    if len(selection.get("cells", [])) != 60 or len(result.get("cells", [])) != 60:
        errors.append("family is not 60 cells")
    if [c["cell_id"] for c in result["cells"]] != prereg["test_family"]["cells"]:
        errors.append("result cell identity/order differs from preregistration")
    if any(cell["bh"].get("m_family") != 60 for cell in result["cells"]):
        errors.append("BH family size differs from 60")
    for cell in result["cells"]:
        if (not cell["selection_eligible"] or cell["test_reason_codes"]) and cell["raw_p_value"] != 1.0:
            errors.append(f"non-testable cell does not have p=1: {cell['cell_id']}")
    primary_ids = {c["cell_id"] for c in result["cells"] if c["primary_statistical_criterion_met"]}
    economic_ids = {c["cell_id"] for c in result["economic_stage"]}
    if primary_ids != economic_ids:
        errors.append("economic-stage admission differs from primary criterion")
    if result["summary"].get("supported") is not False or evidence.get("is_validated_edge") is not False:
        errors.append("DISCOVERY_REUSE result was promoted to supported/validated")
    if evidence.get("source_result_sha256") != file_sha256(RESULT_PATH):
        errors.append("evidence result hash mismatch")
    if decision.get("automatic_registry_mutation") is not False:
        errors.append("decision permits automatic registry mutation")
    if decision.get("closure_status") != "CLOSED_WEAK":
        errors.append("decision is not canonically closed as WEAK")
    observation = decision.get("post_hoc_observation", {})
    if observation.get("cell_id") != "MACD__LOW_VOL__SELL__T1_0_ATR":
        errors.append("post-hoc observation identity drift")
    if observation.get("classification") != "POST_HOC_OBSERVATION_NOT_CONFIRMED":
        errors.append("nominal cell was not classified as unconfirmed post-hoc")
    if observation.get("bh_q_value") != 1.0:
        errors.append("post-hoc observation BH q drift")
    if proposal.get("automatic_mutation") is not False:
        errors.append("registry proposal permits automatic mutation")
    if proposal.get("proposed_value") != "WEAK":
        errors.append("registry proposal does not preserve WEAK verdict")
    if proposal.get("scope", {}).get("representation") != "CAUSAL_CROSSOVER":
        errors.append("registry proposal scope is not representation-specific")
    if proposal.get("evidence", {}).get("result_sha256") != file_sha256(RESULT_PATH):
        errors.append("registry proposal result provenance mismatch")
    if limitations.get("provenance", {}).get("result") != file_sha256(RESULT_PATH):
        errors.append("limitations result provenance mismatch")
    return {
        "status": "PASS" if not errors else "FAIL",
        "preregistration_sha256": result.get("preregistration_sha256"),
        "selection_manifest_sha256": result.get("selection_manifest_sha256"),
        "result_sha256": file_sha256(RESULT_PATH),
        "family_size": len(result.get("cells", [])),
        "primary_cells": len(primary_ids),
        "economic_cells": len(economic_ids),
        "verdict": result.get("summary", {}).get("verdict"),
        "errors": errors,
    }


def main() -> int:
    report = verify()
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
