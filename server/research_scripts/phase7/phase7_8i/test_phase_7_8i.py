#!/usr/bin/env python3
"""Phase 7.8I - Suite di consistenza completa: ricompilazione, config di
ricerca, preflight tecnico, atomic reseal, immutable run manifest,
risultato scientifico finale (FAIL, verificato indipendentemente)."""
import os
import subprocess
import sys

PHASE78I_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE78I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name}")
    return condition


def main():
    rc_config = load_json(os.path.join(PHASE78I_DIR, "volatility_breakout_research_config_v1.json"))
    check("research_config_hash_matches_payload", rc_config["canonical_sha256"] == canonical_sha256(rc_config["payload"]))
    check("recompile_new_ex5_differs_from_old",
          rc_config["payload"]["recompile_evidence"]["new_ex5_differs_from_old"] is True)
    check("recompile_zero_errors", rc_config["payload"]["recompile_evidence"]["compile_errors_count"] == 0)
    check("research_config_all_5_fields",
          all(f in rc_config["payload"]["tester_execution_config_research"]["raw_text"] for f in
              ("InpResearchMode=true", "InpResearchExitMode=0", "InpResearchFixedLot=0.01",
               "InpStrat_VolBreakoutConfirmed=true", "InpProfileMultiTF=true")))
    check("correction_type_is_research_enablement",
          rc_config["payload"]["correction_classification"]["correction_type"] == "RESEARCH_EXECUTION_ENABLEMENT_FIX")

    preflight = load_json(os.path.join(PHASE78I_DIR, "volatility_breakout_technical_preflight_v1.json"))
    check("preflight_hash_matches_payload", preflight["canonical_sha256"] == canonical_sha256(preflight["payload"]))
    check("preflight_verdict_pass", preflight["payload"]["verdict"] == "TECHNICAL_EXECUTION_PREFLIGHT_PASS")
    check("preflight_not_used_as_evidence", preflight["payload"]["not_used_as_scientific_evidence"] is True)

    reseal = load_json(os.path.join(PHASE78I_DIR, "volatility_breakout_atomic_reseal_before_run3_v1.json"))
    check("reseal_hash_matches_payload", reseal["canonical_sha256"] == canonical_sha256(reseal["payload"]))
    check("reseal_verdict_verified", reseal["payload"]["final_verdict"]["value"] == "ATOMIC_RESEAL_VERIFIED")
    reseal_verify = subprocess.run(
        [sys.executable, os.path.join(PHASE78I_DIR, "verify_atomic_reseal_before_run3.py")],
        capture_output=True, text=True)
    check("reseal_independent_verify_passes", reseal_verify.returncode == 0)

    run3_manifest = load_json(os.path.join(PHASE78I_DIR, "immutable_run_manifest_run3_v1.json"))
    check("run3_manifest_hash_matches_payload", run3_manifest["canonical_sha256"] == canonical_sha256(run3_manifest["payload"]))
    check("run3_collected_before_interpretation", run3_manifest["payload"]["collected_before_any_interpretation"] is True)
    check("run1_run2_archived_unmodified",
          run3_manifest["payload"]["prior_runs_archived_reference"]["run1_7_8g"]["archived_and_unmodified"] is True
          and run3_manifest["payload"]["prior_runs_archived_reference"]["run2_7_8h"]["archived_and_unmodified"] is True)

    result = load_json(os.path.join(PHASE78I_DIR, "volatility_breakout_serious_3y_result_v1.json"))
    check("result_hash_matches_payload", result["canonical_sha256"] == canonical_sha256(result["payload"]))
    check("result_n_nominal_183", result["payload"]["sample"]["n_nominal_fresh"] == 183)
    check("result_sign_criterion_false", result["payload"]["gates"]["sign_criterion"] is False)
    check("result_final_classification_fail", result["payload"]["final_classification"] == "FAIL")
    check("result_matching_ambiguity_did_not_change_verdict",
          result["payload"]["trade_matching_ambiguity_bracket"]["matching_ambiguity_changes_verdict"] is False)
    check("result_no_rescue", result["payload"]["no_rescue_applied"] is True)
    check("result_next_state_archive", result["payload"]["next_lifecycle_state"] == "ARCHIVE_CURRENT_DESIGN")

    result_verify = subprocess.run(
        [sys.executable, os.path.join(PHASE78I_DIR, "verify_serious_validation_result.py")],
        capture_output=True, text=True)
    check("result_independent_verify_passes", result_verify.returncode == 0)
    check("result_independent_verify_agrees", "RESULT_INDEPENDENTLY_CONFIRMED" in result_verify.stdout)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.8I suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
