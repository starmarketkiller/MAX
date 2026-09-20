#!/usr/bin/env python3
"""Phase 7.4A Baseline Matching Topology Audit - regression tests.
Verifica strutturale degli artefatti gia' scritti su disco + self-test
del guard anti-leakage. NON ri-esegue l'audit su dati reali (costoso) -
legge gli artefatti gia' prodotti e ne verifica la coerenza interna."""
import json
import os
import sys

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
sys.path.insert(0, PHASE74_DIR)

from structural_audit_outcome_guard import assert_no_outcome_columns, StructuralAuditOutcomeLeakage  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def load(name):
    with open(os.path.join(PHASE74_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def test_outcome_guard_blocks_forbidden_columns():
    try:
        assert_no_outcome_columns(["mfe_ATR", "event_id"])
        check("guard_blocks_forbidden_column_in_mixed_list", False, "avrebbe dovuto sollevare!")
    except StructuralAuditOutcomeLeakage:
        check("guard_blocks_forbidden_column_in_mixed_list", True)
    check("guard_allows_pure_structural_columns",
          assert_no_outcome_columns(["event_id", "event_index", "control_id", "match_distance", "reuse_count", "direction", "split"]) is True)
    check("guard_does_not_false_positive_on_return_direction",
          assert_no_outcome_columns(["return_direction", "roc"]) is True)


def test_topology_audit_artifact_structure():
    audit = load("phase7_4_baseline_matching_topology_audit_v1.json")
    check("topology_audit_has_major_structural_finding_section", "major_structural_finding_independent_view_collapse" in audit)
    finding = audit["major_structural_finding_independent_view_collapse"]
    check("independent_view_collapse_documented", finding["n_independent_view_eligible"] <= 1,
          f"n_independent_view_eligible={finding['n_independent_view_eligible']}")

    funnel = audit["detection_funnel"]
    check("detection_funnel_monotonic_decreasing",
          funnel["n_event_view"] >= funnel["n_episode_view"] >= funnel["n_independent_view_eligible"],
          f"EVENT_VIEW={funnel['n_event_view']} EPISODE_VIEW={funnel['n_episode_view']} INDEPENDENT_VIEW={funnel['n_independent_view_eligible']}")

    reuse = audit["control_reuse_topology"]
    check("real_engine_max_reuse_exceeds_frozen_cap_5", reuse["max_reuse_exceeds_frozen_cap_5"] is True,
          f"max_reuse={reuse['max_reuse']}")
    check("reuse_histogram_sums_to_unique_controls",
          sum(reuse["reuse_histogram"].values()) == reuse["n_unique_controls"])
    check("control_assignments_equals_events_matched_times_k",
          reuse["n_control_assignments"] == funnel["n_events_matched"] * 5,
          f"assignments={reuse['n_control_assignments']} events_matched*5={funnel['n_events_matched']*5}")

    overlap = audit["outcome_window_overlap_proxy"]
    check("overlap_fraction_between_0_and_1", 0.0 <= overlap["fraction_event_pairs_sharing_overlapping_control"] <= 1.0)

    graph = audit["bipartite_graph_diagnostics"]
    check("graph_event_nodes_equals_events_matched", graph["n_event_nodes"] == funnel["n_events_matched"])
    check("graph_control_nodes_equals_unique_controls", graph["n_control_nodes"] == reuse["n_unique_controls"])
    check("component_sizes_sum_le_total_nodes",
          sum(graph["component_sizes"]) <= graph["n_event_nodes"] + graph["n_control_nodes"])


def test_no_outcome_leakage_in_raw_match_records():
    audit = load("phase7_4_baseline_matching_topology_audit_v1.json")
    sample = audit.get("raw_match_records_sample", [])
    check("raw_match_records_sample_present_or_empty", isinstance(sample, list))
    if sample:
        keys = set()
        for rec in sample:
            keys.update(rec.keys())
        check("raw_match_records_keys_pass_outcome_guard", assert_no_outcome_columns(keys, context="raw_match_records_sample") is True)


def test_counterfactual_selection_comparison():
    comparison = load("phase7_4_topology_vs_synthetic_comparison_v1.json")
    sec11 = comparison["section11_selection_algorithm_audit"]
    real_max = sec11["real_vs_counterfactual_same_real_data"]["real_engine_max_reuse"]
    cf_max = sec11["real_vs_counterfactual_same_real_data"]["counterfactual_least_used_max_reuse"]
    check("counterfactual_least_used_reduces_reuse_dramatically", cf_max < real_max,
          f"real_engine_max_reuse={real_max}, counterfactual_max_reuse={cf_max}")
    check("counterfactual_confirms_pool_not_scarce", cf_max <= 2,
          f"counterfactual_max_reuse={cf_max} (atteso ~1, confermando che la scarsita' non e' la causa)")


def test_classification_verdict_matches_declared_criteria():
    comparison = load("phase7_4_topology_vs_synthetic_comparison_v1.json")
    sec10 = comparison["section10_synthetic_vs_real_comparison"]
    expected = "MATERIAL_MATCH_TO_HIGH_RISK_SYNTHETIC_GEOMETRY" if (sec10["real_max_reuse_condition_met"] and sec10["real_overlap_condition_met"]) \
        else ("PARTIAL_MATCH" if (sec10["real_max_reuse_condition_met"] or sec10["real_overlap_condition_met"]) else "LOW_MATCH")
    check("classification_recomputation_matches_stored_verdict", expected == sec10["classification"])
    check("classification_is_one_of_three_allowed",
          sec10["classification"] in ("MATERIAL_MATCH_TO_HIGH_RISK_SYNTHETIC_GEOMETRY", "PARTIAL_MATCH", "LOW_MATCH"))


def test_frozen_artifacts_untouched():
    for v in ["v1", "v2", "v3", "v4"]:
        check(f"frozen_spec_{v}_still_exists", os.path.exists(os.path.join(PHASE74_DIR, f"phase7_4_seq0015_frozen_spec_{v}.json")))
    check("no_frozen_spec_v5_created", not os.path.exists(os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v5.json")))
    detector_path = os.path.join(PHASE74_DIR, "seq0015_momentum_burst_detector.py")
    with open(detector_path, encoding="utf-8") as f:
        content = f.read()
    check("detector_still_v1_unchanged", 'DETECTOR_VERSION = "seq0015_momentum_burst_detector.py@v1"' in content)


def test_overall_verdict_unchanged_reference():
    sel = load("phase7_4_dependence_aware_method_selection_v1.json")
    check("primary_verdict_still_not_yet_validated", sel["verdict"] == "PRIMARY INFERENCE METHOD NOT YET VALIDATED")


def main():
    test_outcome_guard_blocks_forbidden_columns()
    test_topology_audit_artifact_structure()
    test_no_outcome_leakage_in_raw_match_records()
    test_counterfactual_selection_comparison()
    test_classification_verdict_matches_declared_criteria()
    test_frozen_artifacts_untouched()
    test_overall_verdict_unchanged_reference()

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Phase 7.4A Baseline Matching Topology Audit regression suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
