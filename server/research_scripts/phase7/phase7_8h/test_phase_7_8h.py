#!/usr/bin/env python3
"""Phase 7.8H - Suite di consistenza: config corretto, atomic reseal
prima del run2, immutable run manifest, sanity gate, root cause piu'
profonda (EX5 non aggiornato)."""
import os
import subprocess
import sys

PHASE78H_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE78H_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name}")
    return condition


def main():
    cc = load_json(os.path.join(PHASE78H_DIR, "volatility_breakout_corrected_config_v1.json"))
    check("corrected_config_hash_matches_payload", cc["canonical_sha256"] == canonical_sha256(cc["payload"]))
    check("corrected_config_single_field_diff",
          cc["payload"]["correction_classification"]["single_field_diff"]["is_exactly_one_field"] is True)
    check("corrected_config_is_technical_enablement",
          cc["payload"]["correction_classification"]["correction_type"] == "TECHNICAL_ENABLEMENT_FIX")

    reseal = load_json(os.path.join(PHASE78H_DIR, "volatility_breakout_atomic_reseal_before_run2_v1.json"))
    check("reseal_hash_matches_payload", reseal["canonical_sha256"] == canonical_sha256(reseal["payload"]))
    check("reseal_verdict_verified", reseal["payload"]["final_verdict"]["value"] == "ATOMIC_RESEAL_VERIFIED")
    reseal_verify = subprocess.run(
        [sys.executable, os.path.join(PHASE78H_DIR, "verify_atomic_reseal_before_run2.py")],
        capture_output=True, text=True)
    check("reseal_independent_verify_passes", reseal_verify.returncode == 0)

    run2_manifest = load_json(os.path.join(PHASE78H_DIR, "immutable_run_manifest_run2_v1.json"))
    check("run2_manifest_hash_matches_payload", run2_manifest["canonical_sha256"] == canonical_sha256(run2_manifest["payload"]))
    check("run2_collected_before_interpretation", run2_manifest["payload"]["collected_before_any_interpretation"] is True)
    check("run1_reference_archived_unmodified",
          run2_manifest["payload"]["prior_run1_archived_reference"]["archived_and_unmodified"] is True)

    result = load_json(os.path.join(PHASE78H_DIR, "volatility_breakout_serious_3y_result_v1.json"))
    check("result_hash_matches_payload", result["canonical_sha256"] == canonical_sha256(result["payload"]))
    check("result_n_nominal_is_0", result["payload"]["sample"]["n_nominal_fresh"] == 0)
    check("result_sanity_gate_present", "gate_status" in result["payload"]["sanity_gate"])
    check("result_classification_is_technical_failure",
          result["payload"]["final_classification"] == "TECHNICAL_EXECUTION_FAILURE_STRATEGY_NEVER_INITIALIZED")
    check("result_no_statistical_verdict", result["payload"]["no_statistical_verdict_computed"] is True)

    rc = load_json(os.path.join(PHASE78H_DIR, "volatility_breakout_run2_deeper_root_cause_v1.json"))
    check("root_cause_hash_matches_payload", rc["canonical_sha256"] == canonical_sha256(rc["payload"]))
    check("root_cause_ex5_predates_commit",
          rc["payload"]["deeper_root_cause"]["ex5_mtime_iso_utc"][:10] < "2026-09-17")
    check("root_cause_evidence_flag_missing",
          rc["payload"]["deeper_root_cause"]["empirical_evidence_from_mt5_native_input_dump"]
          ["InpStrat_VolBreakoutConfirmed_missing_between_the_two_adjacent_flags"] is True)
    check("root_cause_both_runs_flagged", "both_runs_affected" in rc["payload"]["deeper_root_cause"])
    check("root_cause_recommends_stop", "attendere conferma esplicita" in rc["payload"]["recommendation"])

    rc_verify = subprocess.run(
        [sys.executable, os.path.join(PHASE78H_DIR, "verify_run2_deeper_root_cause.py")],
        capture_output=True, text=True)
    check("root_cause_independent_verify_passes", rc_verify.returncode == 0)
    check("root_cause_independent_verify_agrees", "DEEPER_ROOT_CAUSE_CONFIRMED_STALE_EX5" in rc_verify.stdout)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.8H suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
