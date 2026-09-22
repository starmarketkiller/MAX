#!/usr/bin/env python3
"""Phase 7.9A - Suite di consistenza: postmortem, reconciliation,
lifecycle archive, checklist riusabile, reprioritization."""
import os
import subprocess
import sys

PHASE79A_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79A_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name}")
    return condition


def main():
    doc = load_json(os.path.join(PHASE79A_DIR, "phase7_9a_postmortem_and_reprioritization_v1.json"))
    p = doc["payload"]

    check("hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_correct", p["baseline_commit"] == "f9550050f853c7dd4fefa3ef5c4315aa8ac3fcd7")
    check("no_backtest_no_modify_no_rescue",
          p["no_new_backtest_executed"] and p["no_strategy_modified"] and p["no_rescue_performed"])

    check("section_1_present", "section_1_canonical_result_reconciliation" in p)
    check("section_1_root_cause_documented",
          "root_cause" in p["section_1_canonical_result_reconciliation"]["narrative_discrepancy_found"])

    sec2 = p["section_2_archive_lifecycle"]
    check("section_2_all_5_fields_present", all(
        f in sec2["new_state_as_of_7_9a"] for f in
        ("research_readiness", "serious_validation", "execution_candidate", "meta_filter_ready", "deployable")))
    check("section_2_serious_validation_fail", sec2["new_state_as_of_7_9a"]["serious_validation"] == "FAIL")
    check("section_2_preserves_provenance", sec2["preserve_all_provenance"] is True)
    check("section_2_modifies_no_prior_artifact", sec2["this_artifact_modifies_no_prior_frozen_artifact"] is True)

    sec4 = p["section_4_failure_postmortem"]
    check("section_4_three_categories_separated", all(
        k in sec4 for k in ("strategy_failure", "execution_pipeline_failures_discovered_during_validation",
                            "tooling_logging_failures_discovered")))
    check("section_4_pipeline_has_8_lessons", len(sec4["execution_pipeline_failures_discovered_during_validation"]) == 8)
    check("section_4_tooling_has_3_lessons", len(sec4["tooling_logging_failures_discovered"]) == 3)

    checklist_doc = load_json(os.path.join(PHASE79A_DIR, "serious_validation_preflight_checklist_v1.json"))
    check("checklist_hash_matches_payload", checklist_doc["canonical_sha256"] == canonical_sha256(checklist_doc["payload"]))
    check("checklist_12_items_ids_sequential",
          [item["id"] for item in checklist_doc["payload"]["checklist"]] == list(range(1, 13)))

    sec7 = p["section_7_reprioritization"]
    valid_scale = {"LOW", "MEDIUM", "HIGH", "UNKNOWN", "FAR", "FAR_BUT_FIRST_STEP_IS_CHEAP"}
    for cid in ("H006_LIQUIDITY_SWEEP_RECLAIM", "BREAKOUT_ACC"):
        for field in ("evidence_strength", "uncertainty_remaining", "independence",
                       "expected_information_gain", "engineering_cost", "compute_cost",
                       "contamination_risk"):
            check(f"{cid}_{field}_is_qualitative", sec7[cid][field] in valid_scale)

    sec8 = p["section_8_next_research_decision"]
    check("section_8_target_is_open_candidate",
          sec8["target"] in p["section_6_remaining_candidate_inventory"]["remaining_open_candidates"])

    sec9 = p["section_9_new_backlog_item"]
    check("section_9_id_correct", sec9["id"] == "HISTORICAL_VOLUME_CONTRACT_WALLS")
    check("section_9_not_prioritized", sec9["backlog_status"] == "NON_PRIORITIZED")
    check("section_9_treated_as_market_event_not_strategy", sec9["initial_treatment"] == "MARKET_EVENT / STATE_RESEARCH")
    check("section_9_caveat_present", "NON assumere" in sec9["explicit_caveat"])

    verify_result = subprocess.run(
        [sys.executable, os.path.join(PHASE79A_DIR, "verify_postmortem_and_reprioritization.py")],
        capture_output=True, text=True)
    check("independent_verify_passes", verify_result.returncode == 0)
    check("independent_verify_agrees", "POSTMORTEM_INDEPENDENTLY_CONFIRMED" in verify_result.stdout)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.9A suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
