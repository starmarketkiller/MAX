#!/usr/bin/env python3
"""Phase 7.6D - MECH-23 Outcome-Horizon Contract: consistency checks.
Verifica coerenza interna, che il claim sia citato verbatim, che il
blocker sulla magnitudo di barriera sia genuino (non un rescue
travestito), che nessuna geometria/outcome/preflight sia stato toccato,
e che i frozen DESIGN_V1 artifact (6c0d3f6/80e7cbc) restino invariati."""
import os
import sys

PHASE76D_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE76D_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE76D_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc_path = os.path.join(PHASE76D_DIR, "seq0014b_outcome_horizon_contract_v1.json")
    doc = load_json(doc_path)
    p = doc["payload"]

    check("canonical_hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_matches_expected", p["baseline_commit"] == "f6b085984db1ce96dc120d0740aa23f42d1cd124")

    # ---- claim citato verbatim, non riparafrasato ----
    estimand_audit = load_json(os.path.join(PHASE7_DIR, "phase7_6a", "seq0014_estimand_identity_audit_v1.json"))["payload"]
    check("claim_cited_verbatim_matches_source",
          p["claim_formalization"]["claim_verbatim"] ==
          estimand_audit["canonical_source"]["falsification_definition_verbatim"])
    cf = p["claim_formalization"]
    check("unit_exposure_comparator_outcome_censoring_timescale_all_present",
          all(k in cf for k in ("UNIT", "EXPOSURE", "COMPARATOR", "OUTCOME", "CENSORING", "TIME_SCALE")))
    check("outcome_and_censoring_and_timescale_explicitly_not_yet_defined",
          "NON ANCORA" in cf["OUTCOME"] and "NON ANCORA" in cf["CENSORING"] and "NON ANCORA" in cf["TIME_SCALE"])

    # ---- estimand: singolo, stessa famiglia, filter-utility non profitability generica ----
    pe = p["primary_estimand"]
    check("single_estimand_enforced_flag", pe["single_estimand_enforced"] is True)
    check("estimand_answers_filter_utility", pe["answers_filter_utility_not_generic_profitability"] is True)
    check("estimand_mentions_same_family_contrast", "stessa famiglia" in pe["candidate_estimand"] or
          "same" in pe["candidate_estimand"].lower() or "stessa" in pe["candidate_estimand"])

    # ---- candidate outcome audit: tutti e 5 valutati, nessun dato usato ----
    coa = p["candidate_outcome_audit"]
    expected_candidates = {"P_PLUS_1ATR_BEFORE_MINUS_1ATR", "MAE", "REVERSAL_PROBABILITY", "TIME_TO_TARGET", "PATH_EFFICIENCY"}
    check("all_5_candidates_present", expected_candidates.issubset(set(coa.keys())))
    for cand in expected_candidates:
        check(f"{cand}_has_required_semantic_fields",
              all(k in coa[cand] for k in ("what_it_measures", "represents", "needs_horizon")))
    check("mae_flagged_as_horizon_value_dependent_not_just_censoring",
          "monoton" in coa["MAE"]["barrier_note"])
    check("path_efficiency_flags_domain_contamination_risk_with_seq0014a",
          "SEQ-0014A" in coa["PATH_EFFICIENCY"]["suitability_as_primary"])
    check("time_to_target_flagged_unsuitable_as_primary",
          "NON ADATTO" in coa["TIME_TO_TARGET"]["suitability_as_primary"])
    outcome_surface_path = os.path.join(PHASE7_DIR, "phase7_3", "outcome_surface_v3.py")
    check("outcome_surface_hash_matches_real_file",
          coa["outcome_surface_source_sha256"] == file_sha256(outcome_surface_path))

    # ---- primary outcome: classe identificata, magnitudo esatta bloccata (non un rescue) ----
    pod = p["primary_outcome_decision"]
    check("primary_outcome_class_is_double_barrier", "DOUBLE_BARRIER" in pod["primary_outcome_class"])
    check("class_is_mechanically_defensible_flag", pod["class_is_mechanically_defensible_from_claim"] is True)
    check("exact_id_status_is_not_yet_justified", "NON ANCORA GIUSTIFICATO" in pod["exact_vocabulary_id_status"])
    check("verdict_is_class_identified_parameterization_blocked",
          pod["verdict"] == "PRIMARY_OUTCOME_CLASS_IDENTIFIED_EXACT_PARAMETERIZATION_NOT_YET_JUSTIFIED")
    check("blocker_text_present_and_substantive", len(pod["blocker"]) > 50)
    check("symmetric_1atr_shortcut_explicitly_rejected",
          "naturale-per-simmetria" in pod["why_not_just_pick_the_symmetric_1atr_variant"] or
          "convenzione" in pod["why_not_just_pick_the_symmetric_1atr_variant"].lower())

    # ---- horizon derivation: forbidden sources explicitly listed and match user's exact constraints ----
    hdp = p["horizon_derivation_process"]
    forbidden = hdp["explicitly_forbidden_derivation_sources"]
    check("forbidden_sources_include_sample_size_and_matching_and_design_v1_result",
          any("sample size" in f for f in forbidden) and any("matching" in f for f in forbidden) and
          any("80e7cbc" in f or "DESIGN_V1" in f for f in forbidden))
    check("horizon_not_resolved_pending_barrier_magnitude",
          "PARAMETERIZATION_NOT_YET" in hdp["why_not_yet_resolvable_here"] or
          "APERTA" in hdp["why_not_yet_resolvable_here"])

    # ---- barrier vs censoring: 3 opzioni, nessuna scelta congelata ----
    bvc = p["barrier_vs_censoring"]
    check("three_censoring_options_present",
          set(bvc["censoring_treatment_options_not_yet_chosen"].keys()) ==
          {"TREAT_AS_FAILURE", "TREAT_AS_NEUTRAL_EXCLUDED", "THIRD_CATEGORY_REPORTED_SEPARATELY"})
    check("censoring_decision_not_frozen", "NON SCELTO" in bvc["decision"])
    check("neutral_excluded_flagged_as_riskiest", "selection bias" in bvc["rejected_note"])

    # ---- common horizon: evidenza cross-experiment riusata da f6b0859, decisione non presa ----
    horizon_audit = load_json(os.path.join(PHASE7_DIR, "phase7_6c", "seq0014b_outcome_horizon_ordering_audit_v1.json"))["payload"]
    chr_ = p["common_horizon_requirement"]
    check("cites_seq0014a_20_vs_seq0009_40_from_prior_audit",
          str(horizon_audit["cross_experiment_horizon_evidence"]["SEQ-0014A_state_entry_natural_horizon"]) in chr_["evidence_from_project_history"] and
          str(horizon_audit["cross_experiment_horizon_evidence"]["SEQ-0009_sweep_reversal_natural_horizon"]) in chr_["evidence_from_project_history"])
    check("common_horizon_decision_not_made", "NON DECISO" in chr_["decision"])
    check("common_horizon_never_justified_by_declustering_convenience",
          "declustering" in chr_["decision"])

    # ---- filter utility: link a NO_TRADE reale ----
    fdu = p["filter_decision_utility"]
    check("filter_utility_links_to_no_trade_decision", "NO_TRADE" in fdu["answer_for_the_chosen_class"])

    # ---- materiality: floor di progetto riusato, verificato contro il file reale ----
    min_ev_gates = load_json(os.path.join(PHASE7_DIR, "policies", "minimum_evidence_gates.json"))
    me = p["material_effect"]
    check("materiality_floor_matches_real_policy_file",
          me["existing_project_default_floor"]["value"] ==
          min_ev_gates["gates"]["minimum_material_delta_p_default"]["value"])
    check("materiality_not_chosen_from_data", "NON scelto guardando i dati" in me["existing_project_default_floor"]["source"])

    # ---- design_v2 eligibility: verdetto e' uno dei due enumerati dall'utente ----
    dve = p["design_v2_eligibility"]
    check("design_v2_verdict_is_valid_enum",
          dve["verdict"] in ("DESIGN_V2_READY_FOR_STRUCTURAL_SPEC", "DESIGN_V2_BLOCKED_ON_OUTCOME_HORIZON_CONTRACT"))
    check("design_v2_verdict_is_blocked_given_open_parameterization",
          dve["verdict"] == "DESIGN_V2_BLOCKED_ON_OUTCOME_HORIZON_CONTRACT")
    check("blocking_items_include_primary_outcome_and_horizon_and_censoring",
          any("primary_outcome" in b for b in dve["blocking_items"]) and
          any("horizon" in b for b in dve["blocking_items"]) and
          any("censoring" in b for b in dve["blocking_items"]))
    check("non_blocking_items_include_estimand_and_direction_and_materiality",
          "primary_estimand" in dve["non_blocking_items_already_resolvable"] and
          "direction_of_expected_effect" in dve["non_blocking_items_already_resolvable"])

    # ---- no geometry / no outcome / no preflight - tutti i flag ----
    ngc = p["no_geometry_confirmation"]
    check("all_no_geometry_flags_true", all(ngc[k] is True for k in
          ("no_event_counts_computed", "no_independent_counts_computed", "no_matching_counts_computed",
           "no_cross_family_collapse_computed", "no_structural_preflight_executed",
           "no_alternate_horizon_inspected_on_data")))

    # ---- framework rule: raffina la regola precedente, non ne inventa una scollegata ----
    fr = p["framework_rule"]
    check("framework_chain_has_8_links",
          fr["chain"] == ["CLAIM", "ESTIMAND", "OUTCOME DEFINITION", "RESOLUTION WINDOW / CENSORING",
                           "NATURAL HORIZON", "EMBARGO", "STRUCTURAL FEASIBILITY", "INFERENCE"])
    check("framework_explicitly_supersedes_prior_partial_rule", "f6b0859" in fr["supersedes_prior_partial_rule"])
    check("no_new_infrastructure_flag", fr["no_new_infrastructure_built"] is True)

    # ---- DESIGN_V1 frozen artifacts (spec/result) invariati - verifica hash contro i file reali ----
    spec_doc = load_json(os.path.join(PHASE7_DIR, "phase7_6c", "seq0014b_structural_preflight_spec_v1.json"))
    result_doc = load_json(os.path.join(PHASE7_DIR, "phase7_6c", "seq0014b_structural_preflight_result_v1.json"))
    check("design_v1_spec_hash_still_matches_known_value", spec_doc["canonical_sha256"] ==
          "15136d2aed317ac484822e4b8cdeb31a411c4ecfa93aecb47d7c4b435adc4347")
    check("design_v1_result_status_still_not_testable",
          result_doc["payload"]["seq0014b_status"] == "NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION")
    check("no_frozen_design_v1_artifacts_modified_flag", p["no_frozen_design_v1_artifacts_modified"] is True)

    # ---- flag finali obbligatori ----
    check("no_outcome_accessed_flag", p["no_nexus_outcome_data_accessed"] is True)
    check("no_structural_preflight_executed_flag", p["no_structural_preflight_executed"] is True)
    check("no_edge_discovery_flag", p["no_edge_discovery_performed"] is True)
    check("no_primary_outcome_selected_flag", p["no_primary_outcome_selected"] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non legge/calcola mai outcome, prezzi, o geometria ----
    builder_path = os.path.join(PHASE76D_DIR, "build_seq0014b_outcome_horizon_contract.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_imports_outcome_computation",
          "load_outcomes" not in builder_src and "compute_outcome" not in builder_src)
    check("builder_never_reads_events_or_state_or_bars_csv",
          "events_p71.csv" not in builder_src and "market_state_dataset_p71.csv" not in builder_src and
          "xauusd_h4_bars_p71.csv" not in builder_src)
    check("builder_never_imports_geometry_engine_modules",
          "from sequence_structural_feasibility_gate import" not in builder_src and
          "from dependence_diagnostics import" not in builder_src and
          "from sequence_episode_engine import" not in builder_src and
          "from baseline_engine_v4 import" not in builder_src,
          "i nomi delle funzioni di geometria compaiono solo in prosa descrittiva (cosa NON e' stato fatto), "
          "mai in un import reale")
    check("builder_never_writes_to_design_v1_spec_or_result_paths",
          "seq0014b_structural_preflight_spec_v1.json\", \"w" not in builder_src and
          "seq0014b_structural_preflight_result_v1.json\", \"w" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== SEQ-0014B outcome-horizon contract consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
