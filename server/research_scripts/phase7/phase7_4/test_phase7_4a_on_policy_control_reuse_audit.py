#!/usr/bin/env python3
"""Phase 7.4A On-Policy Matched-Control Simulation Audit - regression
tests. Dati interamente SINTETICI + verifica strutturale degli
artefatti gia' scritti su disco. Nessuna nuova esecuzione su dati reali."""
import json
import os
import sys

import numpy as np

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
sys.path.insert(0, PHASE74_DIR)
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))

from on_policy_matched_control_simulation import (  # noqa: E402
    gen_on_policy_control_reuse, gen_on_policy_overlapping_control_sets, gen_temporal_overlap_cell,
    minimum_feasible_pool_size, InsufficientPoolError,
)
from run_on_policy_matched_control_audit import audit_old_overlapping_control_sets_reuse  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def test_minimum_feasible_pool_size_formula():
    check("min_pool_max_reuse_5_is_30", minimum_feasible_pool_size(30, 5, 5) == 30)
    check("min_pool_max_reuse_1_is_150", minimum_feasible_pool_size(30, 5, 1) == 150)
    check("min_pool_max_reuse_3_is_50", minimum_feasible_pool_size(30, 5, 3) == 50)


def test_old_generator_confirmed_off_policy():
    audit = audit_old_overlapping_control_sets_reuse()
    check("old_generator_exceeds_frozen_cap_of_5", audit["max_reuse_observed_old_generator"] > 5,
          f"max_reuse_observed={audit['max_reuse_observed_old_generator']}")
    check("old_generator_flagged_violates_frozen_policy", audit["violates_frozen_policy"] is True)


def test_ledger_enforcement_never_exceeded_across_all_generators():
    rng = np.random.default_rng(555)
    violations = 0
    for _ in range(50):
        _, report = gen_on_policy_control_reuse(rng, max_reuse=5, pool_size=45)
        if report["max_reuse_observed"] > 5:
            violations += 1
    for _ in range(50):
        _, report = gen_on_policy_overlapping_control_sets(rng, max_reuse=5)
        if report["max_reuse_observed"] > 5:
            violations += 1
    for _ in range(50):
        _, report = gen_temporal_overlap_cell(rng, max_reuse=5, temporal_clustering="high", pool_size=30)
        if report["max_reuse_observed"] > 5:
            violations += 1
    check("ledger_never_exceeded_across_150_on_policy_replicates", violations == 0, f"violazioni={violations}/150")


def test_insufficient_pool_correctly_rejected():
    rng = np.random.default_rng(1)
    try:
        gen_on_policy_control_reuse(rng, max_reuse=5, pool_size=29)  # 1 sotto il minimo
        check("pool_one_below_minimum_rejected", False, "avrebbe dovuto sollevare InsufficientPoolError!")
    except InsufficientPoolError:
        check("pool_one_below_minimum_rejected", True)


def test_least_used_selection_solves_packing_failure():
    """Verifica empirica (poche repliche, solo per regressione) che la
    selezione 'meno-usato-per-primo' non fallisca al pool minimo teorico -
    con selezione uniforme casuale il fallimento era 86% (misurato prima
    della correzione)."""
    rng = np.random.default_rng(2)
    failures = 0
    for _ in range(50):
        try:
            gen_on_policy_control_reuse(rng, max_reuse=5, pool_size=30)
        except InsufficientPoolError:
            failures += 1
    check("least_used_first_selection_no_packing_failures_at_minimum_pool", failures == 0, f"fallimenti={failures}/50 (atteso 0)")


def test_audit_artifact_structure_and_verdict():
    path = os.path.join(PHASE74_DIR, "phase7_4_on_policy_matched_control_audit_v1.json")
    check("audit_artifact_exists", os.path.exists(path))
    with open(path, encoding="utf-8") as f:
        audit = json.load(f)
    check("verdict_is_one_of_two_allowed_strings",
          audit["decision"]["control_reuse_verdict"] in ("ON_POLICY_CONTROL_REUSE_RISK_CONFIRMED", "PRIOR_CONTROL_REUSE_BLOCKER_NOT_REPRODUCED_ON_POLICY"))
    check("overall_verdict_still_not_yet_validated",
          audit["decision"]["overall_verdict_unchanged"] == "PRIMARY INFERENCE METHOD NOT YET VALIDATED")
    check("old_off_policy_status_marked_explicitly", "OFF_POLICY_STRESS" in audit["decision"]["old_off_policy_status"])
    # coerenza interna: il verdetto deve riflettere il massimo fra riuso isolato e caso peggiore della matrice.
    isolated = audit["decision"]["on_policy_isolated_reuse_max_reuse5_type1_at_05"]
    worst = audit["decision"]["on_policy_worst_case_type1_at_05"]
    expected_confirmed = (isolated > 0.10) or (worst > 0.10)
    actual_confirmed = audit["decision"]["control_reuse_verdict"] == "ON_POLICY_CONTROL_REUSE_RISK_CONFIRMED"
    check("verdict_consistent_with_worst_case_and_isolated_values", expected_confirmed == actual_confirmed)


def test_phi07_blocker_still_referenced_and_unchanged():
    sel_path = os.path.join(PHASE74_DIR, "phase7_4_dependence_aware_method_selection_v1.json")
    check("method_selection_artifact_still_present_untouched", os.path.exists(sel_path))
    with open(sel_path, encoding="utf-8") as f:
        sel = json.load(f)
    check("primary_verdict_still_not_yet_validated_in_source_artifact",
          sel["verdict"] == "PRIMARY INFERENCE METHOD NOT YET VALIDATED")


def test_frozen_artifacts_untouched():
    for v in ["v1", "v2", "v3", "v4"]:
        spec_path = os.path.join(PHASE74_DIR, f"phase7_4_seq0015_frozen_spec_{v}.json")
        check(f"frozen_spec_{v}_still_exists", os.path.exists(spec_path))
    check("no_frozen_spec_v5_created", not os.path.exists(os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v5.json")))
    detector_path = os.path.join(PHASE74_DIR, "seq0015_momentum_burst_detector.py")
    with open(detector_path, encoding="utf-8") as f:
        content = f.read()
    check("detector_still_v1_unchanged", 'DETECTOR_VERSION = "seq0015_momentum_burst_detector.py@v1"' in content)


def main():
    test_minimum_feasible_pool_size_formula()
    test_old_generator_confirmed_off_policy()
    test_ledger_enforcement_never_exceeded_across_all_generators()
    test_insufficient_pool_correctly_rejected()
    test_least_used_selection_solves_packing_failure()
    test_audit_artifact_structure_and_verdict()
    test_phi07_blocker_still_referenced_and_unchanged()
    test_frozen_artifacts_untouched()

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.4A On-Policy Control Reuse Audit regression suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
