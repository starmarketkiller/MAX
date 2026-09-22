#!/usr/bin/env python3
"""Phase 7.9B - Suite di consistenza: identita', lifecycle contract,
reachability statica, evidence lineage, formalization decision."""
import os
import subprocess
import sys

PHASE79B_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79B_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name}")
    return condition


def main():
    lc = load_json(os.path.join(PHASE79B_DIR, "breakout_acc_lifecycle_contract_v1.json"))
    ln = load_json(os.path.join(PHASE79B_DIR, "breakout_acc_evidence_lineage_v1.json"))
    dc = load_json(os.path.join(PHASE79B_DIR, "breakout_acc_formalization_decision_v1.json"))

    for doc, name in ((lc, "lifecycle"), (ln, "lineage"), (dc, "decision")):
        check(f"{name}_hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(doc["payload"]))
        check(f"{name}_baseline_commit_correct", doc["payload"]["baseline_commit"] == "ea0013e090ae2776fe61565392d19991c6dbecc4")

    identity = lc["payload"]["identity"]
    check("selector_index_is_9", identity["selector_index_confirmed"] is True)
    check("shared_enum_disambiguation_present", "shared_enum_disambiguation" in identity)
    check("not_confused_with_3_entries", len(identity["shared_enum_disambiguation"]["not_confused_with"]) == 3)

    lifecycle = lc["payload"]["lifecycle_contract"]
    required_fields = ("SETUP", "TRIGGER", "ENTRY", "DIRECTION", "INVALIDATION_STOP", "TARGET",
                        "TIMEOUT", "MANAGEMENT", "POSITION_SIZING", "COST_ASSUMPTIONS",
                        "TIMEFRAME", "INSTRUMENT")
    check("all_12_lifecycle_fields_present", all(f in lifecycle["fields"] for f in required_fields))
    valid_status = {"VERIFIED_VALUE", "VERIFIED_ABSENCE", "NOT_EXTRACTED"}
    check("all_fields_have_valid_status", all(lifecycle["fields"][f]["status"] in valid_status for f in required_fields))
    valid_requirement = {"REQUIRED", "NOT_REQUIRED_BY_DESIGN", "SATISFIED_BY_EQUIVALENT_MECHANISM"}
    check("all_fields_have_valid_requirement_semantics", all(
        lifecycle["fields"][f].get("requirement") in valid_requirement for f in required_fields))
    check("timeout_verified_absence_not_required", lifecycle["fields"]["TIMEOUT"]["status"] == "VERIFIED_ABSENCE"
          and lifecycle["fields"]["TIMEOUT"]["requirement"] == "NOT_REQUIRED_BY_DESIGN")

    reachability = lc["payload"]["static_reachability"]
    check("reachability_pass", reachability["verdict"] == "STATIC_REACHABILITY_PASS")
    check("reachability_no_blockers", len(reachability["blockers"]) == 0)

    lineage = ln["payload"]["evidence_lineage"]
    check("4_sources_examined", len(lineage["sources_examined"]) == 4)
    check("critical_contradiction_documented", "critical_contradiction_found" in lineage)
    check("governance_gap_documented", "governance_gap_found" in lineage)
    check("source_A_retrograded_unverified",
          lineage["sources_examined"]["source_A_breakout_acc_md_july"]["status"].startswith("EVIDENCE_IDENTITY_UNVERIFIED"))
    check("source_D_confirmed",
          lineage["sources_examined"]["source_D_phase_e_september"]["status"].startswith("EVIDENCE_IDENTITY_CONFIRMED"))
    check("source_D_4_trades_all_losses",
          "SOLO 4 TRADE MT5 REALI" in lineage["sources_examined"]["source_D_phase_e_september"]["claim"])

    quality = ln["payload"]["evidence_quality_audit"]
    valid_scale = {"LOW", "MEDIUM", "HIGH", "UNKNOWN"}
    quality_fields = ("strategy_formalization_completeness", "signal_identity_confidence",
                       "execution_identity_confidence", "sample_quality", "cost_realism",
                       "independence", "discovery_validation_separation", "statistical_rigor")
    check("all_8_quality_fields_present", all(f in quality for f in quality_fields))
    check("all_quality_values_qualitative", all(quality[f] in valid_scale for f in quality_fields))
    check("formalization_high_but_evidence_low",
          quality["strategy_formalization_completeness"] == "HIGH"
          and quality["statistical_rigor"] == "LOW")

    decision = dc["payload"]["decision"]
    check("formalization_verdict_full_spec", decision["formalization_verdict"] == "FULL_STRATEGY_SPEC_VERIFIED")
    check("next_experiment_reanalyze", decision["next_admissible_experiment"]["category"] == "REANALYZE_EXISTING_RAW_RESULTS")
    check("not_a_promotion_flag_present", "not_a_promotion" in decision)
    check("readiness_still_hold", "HOLD_NEEDS_MORE_EVIDENCE" in decision["updated_research_readiness"])

    constraints = dc["payload"]["constraints_preserved"]
    check("volbrk_not_reopened", constraints["volatility_breakout_confirmed_not_reopened"] is True)
    check("h006_not_reopened", constraints["h006_not_reopened"] is True)
    check("hvcw_backlog_only", constraints["historical_volume_contract_walls_remains_backlog_only"] is True)

    verify_result = subprocess.run(
        [sys.executable, os.path.join(PHASE79B_DIR, "verify_breakout_acc_lifecycle_formalization.py")],
        capture_output=True, text=True)
    check("independent_verify_passes", verify_result.returncode == 0)
    check("independent_verify_agrees", "FORMALIZATION_INDEPENDENTLY_CONFIRMED" in verify_result.stdout)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.9B suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
