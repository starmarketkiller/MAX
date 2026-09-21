#!/usr/bin/env python3
"""Phase 7.6C - SEQ-0014B structural preflight SPEC: consistency checks.
Verifica coerenza interna, che gli input riusati (Phase 7.6B/7.5C/7.5B)
non siano stati alterati, che l'episode_gap_rule sia genuinamente
per-famiglia (non un'unica costante copiata), che il matching_spec
imponga il contrasto stesso-famiglia, che l'arm-size policy non inventi
una soglia, e che nessun count reale/outcome sia stato toccato."""
import os
import sys

PHASE76C_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE76C_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE76C_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc_path = os.path.join(PHASE76C_DIR, "seq0014b_structural_preflight_spec_v1.json")
    doc = load_json(doc_path)
    p = doc["payload"]

    check("canonical_hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_matches_expected", p["baseline_commit"] == "fb52168fe2ff27f91abc8671b08992c56e654f4f")

    # ---- input riusati: verificati contro i file reali, non assunti ----
    setup_pop_path = os.path.join(PHASE7_DIR, "phase7_6b", "seq0014b_setup_population_spec_v1.json")
    setup_pop_doc = load_json(setup_pop_path)
    check("setup_population_spec_hash_matches_real_file",
          p["inputs_reused_unchanged"]["setup_population_spec_canonical_sha256"] == setup_pop_doc["canonical_sha256"])
    check("eligible_families_are_exactly_6_and_match_source",
          p["inputs_reused_unchanged"]["eligible_setup_families"] ==
          setup_pop_doc["payload"]["eligible_setup_families"] ==
          ["VOLATILITY_EXPANSION", "DISPLACEMENT", "BREAKOUT", "SWEEP", "COMPRESSION_RELEASE", "PULLBACK"])
    check("regime_contract_reused_verbatim",
          p["inputs_reused_unchanged"]["regime_contract_reused"] == setup_pop_doc["payload"]["regime_contract"])
    check("timestamp_contract_reused_verbatim",
          p["inputs_reused_unchanged"]["timestamp_contract_reused"] == setup_pop_doc["payload"]["timestamp_contract"])
    check("architecture_decision_still_pooled_stratified",
          p["inputs_reused_unchanged"]["architecture_decision_reused"] == "OPTION_B_POOLED_STRATIFIED_BY_SETUP_FAMILY_ID")

    # ---- unita' di analisi: decisione presa, non lasciata aperta, non basata su n ----
    uoa = p["unit_of_analysis_decision"]
    check("unit_of_analysis_decision_is_family_event",
          uoa["decision"] == "OPTION_B_FAMILY_EVENT_UNIT_WITH_MANDATORY_CROSS_FAMILY_DEPENDENCE_CLUSTERING")
    check("option_A_row_first_explicitly_rejected", uoa["option_A_row_first_unit"]["rejected"] is True)
    check("option_B_explicitly_selected", uoa["option_B_family_event_unit"]["selected"] is True)
    check("decision_not_based_on_sample_size_flag", uoa["decision_not_based_on_sample_size"] is True)
    check("decision_basis_cites_mech23_and_stratification",
          "MECH-23" in uoa["decision_basis"] and "stratificazione" in uoa["decision_basis"])

    # ---- geometria within-family: shared horizon/embargo riusati da SEQ-0009, mai ri-derivati ----
    seq0009 = load_json(os.path.join(PHASE7_DIR, "phase7_5b", "seq0009_frozen_structural_spec_v1.json"))["payload"]
    wfg = p["within_family_geometry_rule"]
    shared = wfg["shared_across_all_6_families"]
    check("shared_natural_horizon_matches_seq0009", shared["natural_horizon"] == seq0009["proposed_natural_horizon"] == 40)
    check("shared_embargo_matches_seq0009",
          shared["outcome_overlap_embargo_bars"] == seq0009["proposed_outcome_overlap_embargo_bars"] == 39)
    check("shared_embargo_equals_horizon_minus_1", shared["outcome_overlap_embargo_bars"] == shared["natural_horizon"] - 1)
    check("shared_overlap_policy_matches_seq0009", shared["overlap_policy"] == seq0009["overlap_policy"])

    # ---- episode_gap_rule: genuinamente per-famiglia, non un'unica costante ----
    gap_rules = wfg["family_specific_episode_gap_rule"]
    eligible = p["inputs_reused_unchanged"]["eligible_setup_families"]
    check("gap_rule_declared_for_all_6_eligible_families", set(gap_rules.keys()) == set(eligible))
    check("gap_rule_is_not_a_single_constant_across_families",
          len(set(g["value"] for g in gap_rules.values())) > 1,
          f"valori distinti: {sorted(set(g['value'] for g in gap_rules.values()))}")
    for fam in eligible:
        check(f"{fam}_gap_rule_has_mechanism_rationale",
              isinstance(gap_rules[fam]["value"], int) and len(gap_rules[fam]["detector_mechanism"]) > 20
              and len(gap_rules[fam]["rationale"]) > 20)
    check("sweep_gap_rule_reused_unchanged_from_seq0009", gap_rules["SWEEP"]["value"] == seq0009["episode_gap_rule"] == 2)
    check("volatility_expansion_and_displacement_share_gap_1_instantaneous_class",
          gap_rules["VOLATILITY_EXPANSION"]["value"] == gap_rules["DISPLACEMENT"]["value"] == 1)
    check("breakout_sweep_pullback_share_gap_2_rolling_extreme_class",
          gap_rules["BREAKOUT"]["value"] == gap_rules["SWEEP"]["value"] == gap_rules["PULLBACK"]["value"] == 2)
    check("compression_release_gap_equals_its_own_precondition_window",
          gap_rules["COMPRESSION_RELEASE"]["value"] == 5)

    # ---- cross-family dependence clustering: soglia condivisa, invariant dichiarato, test sintetico richiesto ----
    cfd = p["cross_family_dependence_clustering"]
    check("cross_family_threshold_equals_shared_embargo", cfd["threshold_bars"] == shared["outcome_overlap_embargo_bars"])
    ndc = cfd["no_double_counting_invariant"]
    check("no_double_counting_invariant_statement_present", "pooled_independent_units" in ndc["statement"])
    check("synthetic_regression_required_flag", ndc["synthetic_regression_required"] is True)
    check("synthetic_case_describes_two_families_sharing_rows",
          "A" in ndc["synthetic_case_description"] and "B" in ndc["synthetic_case_description"])

    # ---- matching_spec: contrasto sempre stessa famiglia, dimensione ortogonale, cutpoint riusati ----
    seq0014a = load_json(os.path.join(PHASE7_DIR, "phase7_5c", "seq0014_frozen_structural_spec_v1.json"))["payload"]
    ms = p["matching_spec"]
    check("match_dimensions_is_volatility_state_pre_setup_only", ms["match_dimensions"] == ["volatility_state_pre_setup"])
    check("k_reused_from_seq0014a", ms["k"] == seq0014a["matching_spec"]["k"])
    check("minimum_control_count_reused_from_seq0014a",
          ms["minimum_control_count"] == seq0014a["matching_spec"]["minimum_control_count"])
    check("max_control_reuse_per_run_reused_from_seq0014a",
          ms["max_control_reuse_per_run"] == seq0014a["matching_spec"]["max_control_reuse_per_run"])
    atr_def = seq0014a["matching_spec"]["state_feature_definitions"]["volatility_state_pre_entry"]
    check("tercile_cutpoints_reused_unchanged",
          ms["state_feature_definitions"]["volatility_state_pre_setup"]["tercile_cutpoints_fit_on_discovery_only"] ==
          atr_def["tercile_cutpoints_fit_on_discovery_only"])
    check("control_pool_policy_forbids_cross_family",
          "SAME_SETUP_FAMILY_ID_OPPOSITE_REGIME_ONLY" in ms["control_pool_construction_policy"])
    check("split_boundaries_reused_from_seq0014a", ms["split_boundaries"] == seq0014a["matching_spec"]["split_boundaries"])
    check("no_additional_matching_dimensions_invented", ms["additional_matching_dimensions_forbidden_unless_preexisting"] is True)
    check("contrast_roles_choppy_is_event_trending_is_control",
          "CHOPPY" in ms["contrast_roles"]["event_side"] and "TRENDING" in ms["contrast_roles"]["control_pool_side"])

    # ---- arm-size policy: verificato contro il file reale, nessuna soglia inventata ----
    asp = p["arm_size_policy"]
    min_ev_path = os.path.join(PHASE7_DIR, "policies", "minimum_evidence_gates.json")
    min_ev = load_json(min_ev_path)
    check("arm_size_policy_checked_file_hash_matches_real_file",
          asp["checked_against_file_sha256"] == __import__("canonical_utils").file_sha256(min_ev_path))
    check("no_per_arm_minimum_found_in_real_gates_file",
          all("per arm" not in str(v).lower() and "per braccio" not in str(v).lower()
              for v in min_ev["gates"].values()))
    check("canonical_per_arm_minimum_exists_is_false", asp["canonical_per_arm_minimum_exists_in_project"] is False)
    check("arm_size_flag_is_needs_arm_size_policy", asp["flag"] == "NEEDS_ARM_SIZE_POLICY")
    check("arm_size_not_invented_flag", asp["not_invented"] is True)

    # ---- RECLAIM discrepancy: solo pointer, out of scope, registry non toccato ----
    rr = p["reclaim_discrepancy_reference"]
    check("reclaim_reference_is_pointer_only", rr["pointer_only"] is True)
    check("reclaim_reference_cites_baseline_commit", rr["already_documented_in_commit"] == "fb52168fe2ff27f91abc8671b08992c56e654f4f")
    check("registry_not_touched_in_this_phase", rr["registry_file_touched_in_this_phase"] is False)
    check("no_impact_on_geometry_flag", rr["no_impact_on_this_preflight_geometry"] is True)

    # ---- deferred work correctly scoped out of this commit ----
    check("not_yet_done_list_has_all_deferred_items", len(p["not_yet_done_deferred_to_result_commit"]) >= 6)
    check("no_real_counts_computed_flag", p["no_real_counts_computed_in_this_spec"] is True)
    check("no_outcome_accessed_flag", p["no_nexus_outcome_data_accessed"] is True)
    check("no_edge_discovery_flag", p["no_edge_discovery_performed"] is True)
    check("no_primary_outcome_selected_flag", p["no_primary_outcome_selected"] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non legge mai outcome ----
    builder_path = os.path.join(PHASE76C_DIR, "build_seq0014b_structural_preflight_spec.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_imports_outcome_computation",
          "load_outcomes" not in builder_src and "compute_outcome" not in builder_src)
    check("builder_never_reads_events_p71_csv_yet",
          "events_p71.csv" not in builder_src, "il result commit legge i dati reali, non questo spec")

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== SEQ-0014B structural preflight spec consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
