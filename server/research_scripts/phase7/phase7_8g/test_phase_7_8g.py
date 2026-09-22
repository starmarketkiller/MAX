#!/usr/bin/env python3
"""Phase 7.8G - Suite di consistenza per: atomic reseal, immutable run
manifest, e zero-trade root cause analysis."""
import os
import subprocess
import sys

PHASE78G_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE78G_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name}")
    return condition


def main():
    # ---- Atomic reseal ----
    reseal_doc = load_json(os.path.join(PHASE78G_DIR, "volatility_breakout_atomic_prerun_reseal_v1.json"))
    check("reseal_hash_matches_payload", reseal_doc["canonical_sha256"] == canonical_sha256(reseal_doc["payload"]))
    check("reseal_verdict_is_verified", reseal_doc["payload"]["final_verdict"]["value"] == "ATOMIC_RESEAL_VERIFIED")
    check("reseal_drift_classified", reseal_doc["payload"]["data_drift_reevaluation"]["conclusion"]
          in ("IRRELEVANT_POST_WINDOW_CACHE_DRIFT", "RELEVANT_WINDOW_DATA_DRIFT"))
    check("reseal_data_not_modified_flag", reseal_doc["payload"]["no_data_modified_or_resynced_in_this_phase"] is True)

    reseal_verify = subprocess.run(
        [sys.executable, os.path.join(PHASE78G_DIR, "verify_atomic_reseal.py")],
        capture_output=True, text=True)
    check("reseal_independent_verify_passes", reseal_verify.returncode == 0)
    check("reseal_independent_verify_agrees", "ATOMIC_RESEAL_VERIFIED" in reseal_verify.stdout)

    # ---- Immutable run manifest ----
    run_manifest = load_json(os.path.join(PHASE78G_DIR, "immutable_run_manifest_v1.json"))
    check("run_manifest_hash_matches_payload", run_manifest["canonical_sha256"] == canonical_sha256(run_manifest["payload"]))
    check("run_manifest_collected_before_interpretation_flag",
          run_manifest["payload"]["collected_before_any_interpretation"] is True)
    report_entry = run_manifest["payload"]["collected_files"].get("report_htm")
    check("run_manifest_report_present", report_entry is not None)
    if report_entry:
        report_path = os.path.join(ROOT, report_entry["dest_path"])
        check("run_manifest_report_hash_matches_real_file",
              os.path.isfile(report_path) and file_sha256(report_path) == report_entry["sha256"])
    ini_entry = run_manifest["payload"]["collected_files"].get("tester_ini_used")
    check("run_manifest_ini_present", ini_entry is not None)
    if ini_entry:
        with open(os.path.join(ROOT, ini_entry["dest_path"]), encoding="utf-8") as f:
            ini_text = f.read()
        check("run_ini_matches_7_8f_frozen_config", "Expert=NEXUS_EA_v2" in ini_text and "Leverage=500" in ini_text
              and "InpStrat_VolBreakoutConfirmed" not in ini_text)

    # ---- Zero-trade root cause ----
    rc_doc = load_json(os.path.join(PHASE78G_DIR, "volatility_breakout_zero_trade_root_cause_v1.json"))
    check("root_cause_hash_matches_payload", rc_doc["canonical_sha256"] == canonical_sha256(rc_doc["payload"]))
    check("root_cause_total_trades_is_0", rc_doc["payload"]["observed_fact"]["total_trades_in_official_report"] == "0")
    check("root_cause_history_quality_100pct",
          rc_doc["payload"]["observed_fact"]["history_quality"] == "100% ticks reali")
    check("root_cause_flag_default_false",
          "false" in rc_doc["payload"]["root_cause"]["default_value_line"])
    check("root_cause_never_in_frozen_config", rc_doc["payload"]["root_cause"]["never_included_in_any_frozen_config"] is True)
    check("root_cause_no_verdict_computed", rc_doc["payload"]["no_verdict_computed_on_this_run"] is True)
    check("root_cause_proposed_fix_is_single_field",
          "InpStrat_VolBreakoutConfirmed=true" in rc_doc["payload"]["proposed_fix"]["action"])

    rc_verify = subprocess.run(
        [sys.executable, os.path.join(PHASE78G_DIR, "verify_zero_trade_root_cause.py")],
        capture_output=True, text=True)
    check("root_cause_independent_verify_passes", rc_verify.returncode == 0)
    check("root_cause_independent_verify_agrees", "ROOT_CAUSE_CONFIRMED_MISCONFIGURATION" in rc_verify.stdout)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.8G suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
