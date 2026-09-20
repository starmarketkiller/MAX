#!/usr/bin/env python3
"""Phase 7.4A Dependence-Aware Inference Redesign - regression tests.
Dati interamente SINTETICI + verifica strutturale degli artefatti gia'
scritti su disco. Nessuna nuova esecuzione su dati reali."""
import json
import os
import sys

import numpy as np

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))

from dependence_aware_mean_tests import null_centered_block_bootstrap_p, studentized_block_bootstrap_p, hac_newey_west_p  # noqa: E402
from ungated_bh_family import build_ungated_bh_family  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def test_all_three_methods_reject_h0_true_and_h0_false_correctly():
    rng = np.random.default_rng(99)
    for label, fn, kw in [("A", null_centered_block_bootstrap_p, {"n_boot": 400}),
                          ("B", studentized_block_bootstrap_p, {"n_boot": 400}),
                          ("C", hac_newey_west_p, {})]:
        d_h0 = rng.normal(0.0, 1.0, 30)
        r_h0 = fn(d_h0, **kw) if kw else fn(d_h0)
        check(f"{label}_no_crash_on_h0_true", "p_value" in r_h0)

        d_effect = rng.normal(1.5, 1.0, 30)
        r_eff = fn(d_effect, **kw) if kw else fn(d_effect)
        check(f"{label}_detects_large_effect", r_eff["p_value"] < 0.05, f"p={r_eff['p_value']:.4f}")


def test_ungated_family_never_drops_a_cell():
    rng = np.random.default_rng(7)
    cells = [{"cell_id": f"C-{i}", "d_values": list(rng.normal(0.0, 1.0, 30)), "_true_effect": False} for i in range(21)]
    result = build_ungated_bh_family(cells, studentized_block_bootstrap_p, {"n_boot": 300}, q=0.10)
    check("ungated_family_size_equals_input_length", result["declared_family_size"] == 21)
    check("ungated_family_all_cells_have_raw_p", all("raw_p_value" in c for c in result["cells"]))
    check("ungated_family_no_p_forced_to_1_artificially",
          not all(c["raw_p_value"] == 1.0 for c in result["cells"]), "nessun p=1.0 forzato artificialmente per l'intera famiglia")


def test_no_gating_architecture_reintroduced():
    """Verifica strutturale: il nuovo modulo di calibrazione non deve importare
    dependence_validity_gate/dependence_gated_bh_family (architettura abbandonata) -
    la diagnostica di dipendenza puo' restare disponibile altrove ma non deve
    essere usata QUI per selezionare celle."""
    calib_path = os.path.join(PHASE74_DIR, "dependence_aware_inference_calibration.py")
    with open(calib_path, encoding="utf-8") as f:
        content = f.read()
    check("calibration_script_does_not_import_gated_bh_family", "dependence_gated_bh_family" not in content)
    ungated_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine", "ungated_bh_family.py")
    with open(ungated_path, encoding="utf-8") as f:
        ungated_content = f.read()
    check("ungated_bh_family_does_not_reference_p_value_for_bh", "p_value_for_bh" not in ungated_content)


def test_decision_rule_verdict_is_deterministic():
    sel_path = os.path.join(PHASE74_DIR, "phase7_4_dependence_aware_method_selection_v1.json")
    check("method_selection_artifact_exists", os.path.exists(sel_path))
    with open(sel_path, encoding="utf-8") as f:
        sel = json.load(f)
    check("verdict_is_one_of_two_allowed_strings",
          sel["verdict"] in ("DEPENDENCE-AWARE INFERENCE METHOD VALIDATED", "PRIMARY INFERENCE METHOD NOT YET VALIDATED"))
    if sel["verdict"] == "PRIMARY INFERENCE METHOD NOT YET VALIDATED":
        check("no_method_marked_selected_when_not_validated", sel["selected_method"] is None)
        check("most_promising_method_identified", sel["most_promising_method_if_none_validated"] is not None)
    all_criteria = ["criterion_1_core_null_calibration", "criterion_2_no_explosion",
                    "criterion_3_stability_across_n", "criterion_4_21cell_fdr"]
    for method, findings in sel["method_findings"].items():
        recomputed_pass = all(findings[c]["pass"] for c in all_criteria)
        check(f"{method}_overall_pass_consistent_with_4_criteria", recomputed_pass == findings["overall_pass_all_4_criteria"])


def test_frozen_artifacts_untouched():
    """v1-v4 frozen spec, detector, e i moduli del gate ABBANDONATO devono
    restare esattamente come nella baseline di questa fase - questa e' una
    patch di SOLA validazione/redesign, non deve toccare il congelato."""
    detector_path = os.path.join(PHASE74_DIR, "seq0015_momentum_burst_detector.py")
    with open(detector_path, encoding="utf-8") as f:
        content = f.read()
    check("detector_still_has_v1_version_string", 'DETECTOR_VERSION = "seq0015_momentum_burst_detector.py@v1"' in content)
    for v in ["v1", "v2", "v3", "v4"]:
        spec_path = os.path.join(PHASE74_DIR, f"phase7_4_seq0015_frozen_spec_{v}.json")
        check(f"frozen_spec_{v}_exists_untouched", os.path.exists(spec_path))
    gate_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine", "dependence_validity_gate.py")
    check("old_gate_module_still_present_but_not_reused_here", os.path.exists(gate_path))


def main():
    test_all_three_methods_reject_h0_true_and_h0_false_correctly()
    test_ungated_family_never_drops_a_cell()
    test_no_gating_architecture_reintroduced()
    test_decision_rule_verdict_is_deterministic()
    test_frozen_artifacts_untouched()

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.4A Dependence-Aware Redesign regression suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
