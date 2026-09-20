#!/usr/bin/env python3
"""Phase 7.4A Final Statistical Integrity Patch sec.6 - regression
tests. Dati interamente SINTETICI + verifica strutturale degli
artefatti gia' scritti su disco (contratto v2, frozen spec v3, null
calibration results). Nessuna nuova esecuzione su dati reali."""
import json
import os
import sys

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
sys.path.insert(0, PHASE74_DIR)
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))

from matched_pair_permutation_test import compute_matched_pair_differences, block_sign_flip_permutation_p  # noqa: E402
from control_reuse_ledger import ControlReuseLedger  # noqa: E402
from build_seq0015_statistical_test_contract_v2 import CONTRACT_ENTRIES_V2, DIAGNOSTIC_ONLY_OUTCOMES  # noqa: E402
from seq0015_momentum_burst_detector import DETECTOR_VERSION, FROZEN_PARAMETERS  # noqa: E402
import numpy as np  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def test_null_calibration_results_present_and_reasonable():
    path = os.path.join(PHASE74_DIR, "phase7_4_null_calibration_v1.json")
    check("null_calibration_file_exists", os.path.exists(path))
    with open(path, encoding="utf-8") as f:
        cal = json.load(f)
    new_gauss = cal["new_method_block_sign_flip_permutation"]["gaussian_iid"]["empirical_rejection_rate"]
    check("new_method_gaussian_iid_reasonably_calibrated_at_05",
          0.02 <= new_gauss["0.05"] <= 0.09, f"rej@.05={new_gauss['0.05']} (atteso vicino a .05)")
    shared = cal["shared_regime_demo_old_vs_new"]
    old_shared = shared["OLD_pooled_flattened_controls"]["empirical_rejection_rate"]["0.05"]
    new_shared = shared["NEW_matched_pair_per_event"]["empirical_rejection_rate"]["0.05"]
    check("matched_pair_correctly_calibrated_where_pooled_fails_under_shared_regime",
          abs(new_shared - 0.05) < abs(old_shared - 0.05),
          f"OLD rej@.05={old_shared} (atteso molto lontano da .05), NEW rej@.05={new_shared} (atteso vicino a .05)")


def test_matched_pair_construction_excludes_eventless_entries():
    d = compute_matched_pair_differences([1.0, 0.5, 0.2], [[0.1, 0.2], [], [0.3]])
    check("matched_pair_excludes_events_without_valid_controls", len(d) == 2, f"len(d)={len(d)} atteso 2 (evento senza controlli escluso)")


def test_control_reuse_ledger_enforces_cap():
    ledger = ControlReuseLedger(max_control_reuse_per_run=5)
    for _ in range(5):
        ledger.register_controls_used(["C-SHARED"])
    pool = ["C-SHARED", "C-OTHER"]
    filtered = ledger.filter_available_pool(pool)
    check("control_reuse_cap_enforced", filtered == ["C-OTHER"], f"filtered={filtered} (C-SHARED al tetto deve essere escluso)")


def test_binary_and_continuous_share_same_validated_method():
    methods = {e["variable_type"]: e["hypothesis_test"] for e in CONTRACT_ENTRIES_V2}
    check("binary_and_continuous_use_same_method", methods.get("BINARY") == methods.get("CONTINUOUS"),
          f"BINARY={methods.get('BINARY')!r} CONTINUOUS={methods.get('CONTINUOUS')!r}")
    all_invalid_independence = all(e["independent_two_sample_assumption_valid"] is False for e in CONTRACT_ENTRIES_V2 if e["variable_type"] == "BINARY")
    check("independent_two_sample_assumption_declared_invalid_for_binary", all_invalid_independence)


def test_fdr_family_size_recomputed_deterministically():
    n_outcomes = sum(1 for e in CONTRACT_ENTRIES_V2 if e.get("p_value_method"))
    family_size = 3 * n_outcomes
    check("fdr_family_size_recomputed_21", family_size == 21 and n_outcomes == 7, f"n_outcomes={n_outcomes}, family_size={family_size}")
    overlap = {e["outcome_id"] for e in CONTRACT_ENTRIES_V2} & set(DIAGNOSTIC_ONLY_OUTCOMES)
    check("diagnostic_only_still_excluded_from_v2_contract", len(overlap) == 0)


def test_detector_formula_threshold_unchanged_v2_to_v3():
    v2_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v2.json")
    v3_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v3.json")
    with open(v2_path, encoding="utf-8") as f:
        v2 = json.load(f)
    with open(v3_path, encoding="utf-8") as f:
        v3 = json.load(f)
    check("detector_source_hash_identical_v2_v3",
          v2["frozen_parameters"]["provenance"]["detector_source_hash"] == v3["frozen_parameters"]["provenance"]["detector_source_hash"])
    check("frozen_parameters_hash_identical_v2_v3",
          v2["frozen_parameters"]["provenance"]["frozen_parameters_hash"] == v3["frozen_parameters"]["provenance"]["frozen_parameters_hash"])
    check("v3_declares_supersedes_v2", v3["frozen_parameters"]["provenance"]["supersedes"] == "phase7_4_seq0015_frozen_spec_v2.json")
    check("v3_formula_diffs_empty", v3["frozen_parameters"]["provenance"]["formula_threshold_direction_diffs_vs_v2"] == [])
    check("v3_episode_rule_diffs_empty", v3["frozen_parameters"]["provenance"]["episode_rule_diffs_vs_v2"] == [])


def test_v1_v2_never_overwritten():
    """v1/v2 devono restare esattamente come committati - nessuna riscrittura silenziosa."""
    v1_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v1.json")
    with open(v1_path, encoding="utf-8") as f:
        v1 = json.load(f)
    check("v1_still_has_original_wilson_uncertainty_method", v1["uncertainty_method"] == "WILSON_CI95")
    v2_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v2.json")
    with open(v2_path, encoding="utf-8") as f:
        v2 = json.load(f)
    check("v2_still_references_v1_statistical_contract",
          v2["frozen_parameters"]["statistical_test_contract_ref"] == "server/research_scripts/phase7/phase7_4/seq0015_statistical_test_contract_v1.json")


def test_assign_clusters_transitive_correction_documented():
    v3_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v3.json")
    with open(v3_path, encoding="utf-8") as f:
        v3 = json.load(f)
    b_text = v3["frozen_parameters"]["episode_rule"]["outcome_overlap_rule"]["alternatives_considered"]["B_embargo_only"]
    check("sec8_correction_present_and_explains_transitive_clustering",
          "CORREZIONE" in b_text and "transitivo" in b_text and "138" in b_text)


def test_block_sign_flip_permutation_uses_correct_block_length_formula():
    d = list(np.random.default_rng(1).normal(0, 1, 30))
    r = block_sign_flip_permutation_p(d, n_boot=200, seed=1)
    check("block_length_matches_project_convention_ceil_n_cube_root", r["block_length"] == 4, f"block_length={r['block_length']} atteso 4 per n=30 (ceil(30**(1/3)))")


def test_detector_unchanged_this_patch():
    check("detector_version_string_unchanged", DETECTOR_VERSION == "seq0015_momentum_burst_detector.py@v1")
    check("frozen_threshold_unchanged", FROZEN_PARAMETERS["detector_formula"]["threshold_percentile"] == 90 and
          FROZEN_PARAMETERS["detector_formula"]["threshold_window_bars"] == 252)


def main():
    test_null_calibration_results_present_and_reasonable()
    test_matched_pair_construction_excludes_eventless_entries()
    test_control_reuse_ledger_enforces_cap()
    test_binary_and_continuous_share_same_validated_method()
    test_fdr_family_size_recomputed_deterministically()
    test_detector_formula_threshold_unchanged_v2_to_v3()
    test_v1_v2_never_overwritten()
    test_assign_clusters_transitive_correction_documented()
    test_block_sign_flip_permutation_uses_correct_block_length_formula()
    test_detector_unchanged_this_patch()

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.4A Final Statistical Integrity Patch regression suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
