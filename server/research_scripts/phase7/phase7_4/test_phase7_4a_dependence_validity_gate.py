#!/usr/bin/env python3
"""Phase 7.4A Dependence Validity Gate - regression tests. Dati
interamente SINTETICI + verifica strutturale degli artefatti gia'
scritti su disco. Nessuna nuova esecuzione su dati reali."""
import json
import os
import sys

import numpy as np

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
sys.path.insert(0, PHASE74_DIR)
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))

from dependence_validity_gate import (  # noqa: E402
    compute_dependence_diagnostics, classify_dependence_validity, p_value_for_bh,
    INFERENCE_VALID, DEPENDENCE_SENSITIVE, INFERENCE_INVALID_DEPENDENCE, THRESHOLDS_FROZEN,
)
from dependence_gated_bh_family import build_gated_bh_family  # noqa: E402
from matched_pair_permutation_test import block_sign_flip_permutation_p  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def gen_ar1(rng, phi, n=30, mean_shift=0.0):
    eps = rng.normal(0.0, 1.0, n)
    x = np.empty(n)
    x[0] = eps[0] + mean_shift
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t] * np.sqrt(1 - phi ** 2) + mean_shift * (1 - phi)
    return x


def test_calibration_curve_monotonic_and_present():
    path = os.path.join(PHASE74_DIR, "phase7_4_dependence_gate_calibration_v1.json")
    check("calibration_curve_file_exists", os.path.exists(path))
    with open(path, encoding="utf-8") as f:
        cal = json.load(f)
    rows = cal["calibration_curve"]
    check("calibration_curve_has_6_phi_points", len(rows) == 6, f"n={len(rows)}")
    type1_at_05 = [r["empirical_type1_error"]["0.05"] for r in rows]
    check("type1_error_increases_with_phi",
          all(type1_at_05[i] <= type1_at_05[i + 1] + 0.02 for i in range(len(type1_at_05) - 1)),
          f"type1@.05 per phi crescente: {type1_at_05}")
    check("gate_severity_increases_with_phi_low_end_valid_high_end_invalid",
          rows[0]["gate_majority_verdict"] == "INFERENCE_VALID" and rows[-1]["gate_majority_verdict"] == "INFERENCE_INVALID_DEPENDENCE",
          f"phi=0.0 -> {rows[0]['gate_majority_verdict']}, phi=0.7 -> {rows[-1]['gate_majority_verdict']}")


def test_gate_classifies_iid_as_valid_and_strong_ar1_as_not_valid():
    rng = np.random.default_rng(123)
    white = rng.normal(0, 1, 60)
    diag_white = compute_dependence_diagnostics(white)
    cls_white = classify_dependence_validity(diag_white)
    check("iid_white_noise_classified_valid", cls_white["state"] == INFERENCE_VALID, f"state={cls_white['state']}")

    strong = gen_ar1(rng, 0.8, n=60)
    diag_strong = compute_dependence_diagnostics(strong)
    cls_strong = classify_dependence_validity(diag_strong)
    check("strong_ar1_not_classified_valid", cls_strong["state"] != INFERENCE_VALID, f"state={cls_strong['state']}")


def test_dependence_sensitive_and_invalid_get_p_equals_1():
    check("dependence_sensitive_p_forced_to_1", p_value_for_bh(0.001, DEPENDENCE_SENSITIVE) == 1.0)
    check("inference_invalid_p_forced_to_1", p_value_for_bh(0.001, INFERENCE_INVALID_DEPENDENCE) == 1.0)
    check("inference_valid_p_passthrough", p_value_for_bh(0.001, INFERENCE_VALID) == 0.001)


def test_family_size_never_reduced():
    rng = np.random.default_rng(42)
    cells = []
    for i in range(21):
        # mix di celle pulite e dipendenti, deliberatamente eterogenee.
        d = gen_ar1(rng, 0.8 if i % 5 == 0 else 0.0, n=30, mean_shift=0.3)
        cells.append({"cell_id": f"CELL-{i}", "candidate_id": f"CAND-{i % 3}", "outcome_id": f"OUT-{i % 7}",
                     "d_values": list(d), "raw_p_value": block_sign_flip_permutation_p(d, seed=i)["p_value"]})
    result = build_gated_bh_family(cells, q=0.10)
    check("family_size_fixed_at_21_regardless_of_gate_outcomes", result["declared_family_size"] == 21)
    n_not_valid = result["n_by_dependence_state"][DEPENDENCE_SENSITIVE] + result["n_by_dependence_state"][INFERENCE_INVALID_DEPENDENCE]
    check("at_least_some_cells_flagged_not_valid_in_heterogeneous_mix", n_not_valid > 0, f"n_by_state={result['n_by_dependence_state']}")
    not_valid_cells = [c for c in result["cells"] if c["dependence_state"] != INFERENCE_VALID]
    check("all_not_valid_cells_have_bh_input_p_equal_1",
          all(c["bh_input_p_value"] == 1.0 for c in not_valid_cells))
    check("no_not_valid_cell_ever_eligible_for_discovery",
          all(c["eligible_for_discovery_verdict"] is False for c in not_valid_cells))


def test_v1_v2_v3_never_overwritten():
    for version, expected_key in [("v1", "provenance"), ("v2", "provenance"), ("v3", "provenance")]:
        path = os.path.join(PHASE74_DIR, f"phase7_4_seq0015_frozen_spec_{version}.json")
        with open(path, encoding="utf-8") as f:
            spec = json.load(f)
        check(f"{version}_frozen_spec_has_no_dependence_validity_gate_key",
              "dependence_validity_gate" not in spec["frozen_parameters"],
              f"{version} deve restare come era prima di questa patch")


def test_v4_supersedes_v3_and_invariants_hold():
    v3_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v3.json")
    v4_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v4.json")
    with open(v3_path, encoding="utf-8") as f:
        v3 = json.load(f)
    with open(v4_path, encoding="utf-8") as f:
        v4 = json.load(f)
    check("v4_declares_supersedes_v3", v4["frozen_parameters"]["provenance"]["supersedes"] == "phase7_4_seq0015_frozen_spec_v3.json")
    check("v4_detector_hash_identical_to_v3",
          v3["frozen_parameters"]["provenance"]["detector_source_hash"] == v4["frozen_parameters"]["provenance"]["detector_source_hash"])
    check("v4_formula_diffs_empty", v4["frozen_parameters"]["provenance"]["formula_threshold_direction_diffs_vs_v3"] == [])
    check("v4_episode_rule_diffs_empty", v4["frozen_parameters"]["provenance"]["episode_rule_diffs_vs_v3"] == [])
    check("v4_control_policy_diffs_empty", v4["frozen_parameters"]["provenance"]["control_policy_and_outcome_contract_diffs_vs_v3"] == [])
    check("v4_has_dependence_validity_gate", "dependence_validity_gate" in v4["frozen_parameters"])
    check("v4_has_sign_flip_assumption_documented",
          "sign_flip_assumption" in v4["frozen_parameters"]["dependence_validity_gate"])
    check("v4_has_shared_regime_correction",
          "shared_regime_interpretation_correction" in v4["frozen_parameters"]["dependence_validity_gate"])


def test_shared_regime_interpretation_corrected():
    path = os.path.join(PHASE74_DIR, "phase7_4_null_calibration_v1.json")
    with open(path, encoding="utf-8") as f:
        cal = json.load(f)
    interp = cal["shared_regime_demo_old_vs_new"]["interpretation"]
    check("shared_regime_interpretation_no_longer_claims_anticonservative_for_zero_rejection",
          "CONSERVATIVO" in interp.upper() and "POWERLESS" in interp.upper())
    old_rej = cal["shared_regime_demo_old_vs_new"]["OLD_pooled_flattened_controls"]["empirical_rejection_rate"]["0.05"]
    check("shared_regime_old_still_shows_zero_rejection_empirically", old_rej == 0.0, f"rej@.05={old_rej}")


def main():
    test_calibration_curve_monotonic_and_present()
    test_gate_classifies_iid_as_valid_and_strong_ar1_as_not_valid()
    test_dependence_sensitive_and_invalid_get_p_equals_1()
    test_family_size_never_reduced()
    test_v1_v2_v3_never_overwritten()
    test_v4_supersedes_v3_and_invariants_hold()
    test_shared_regime_interpretation_corrected()

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.4A Dependence Validity Gate regression suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
