#!/usr/bin/env python3
"""Phase 7.6C - Outcome-Horizon Ordering Audit: consistency checks.
Verifica che l'audit sia fondato sui fatti reali (nessuna asserzione
inventata), che gli artifact frozen (spec/result 7.6C) NON siano stati
toccati, che nessun orizzonte alternativo sia stato ispezionato/
calcolato sui dati, e che lo scope del verdetto NOT_TESTABLE sia
correttamente delimitato a DESIGN_V1."""
import os
import sys

PHASE76C_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE76C_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE76C_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc_path = os.path.join(PHASE76C_DIR, "seq0014b_outcome_horizon_ordering_audit_v1.json")
    doc = load_json(doc_path)
    p = doc["payload"]

    check("canonical_hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_matches_expected", p["baseline_commit"] == "80e7cbc124e40c61a9f0d28a31dd3c6d2e1a5fc3")
    check("audited_spec_commit_matches_expected", p["audited_spec_commit"] == "6c0d3f64d74a8d0495c4b634bee0c9d7d2ea8a93")
    check("audited_result_commit_matches_expected", p["audited_result_commit"] == "80e7cbc124e40c61a9f0d28a31dd3c6d2e1a5fc3")

    # ---- gli artifact frozen NON sono stati toccati - verificato contro gli hash REALI dei file ----
    spec_path = os.path.join(PHASE76C_DIR, "seq0014b_structural_preflight_spec_v1.json")
    result_path = os.path.join(PHASE76C_DIR, "seq0014b_structural_preflight_result_v1.json")
    spec_doc = load_json(spec_path)
    result_doc = load_json(result_path)
    fau = p["frozen_artifacts_untouched"]
    check("spec_commit_hash_matches_real_file", fau["spec_commit_canonical_sha256_unchanged"] == spec_doc["canonical_sha256"])
    check("result_commit_hash_matches_real_file", fau["result_commit_canonical_sha256_unchanged"] == result_doc["canonical_sha256"])
    check("spec_file_sha256_matches_real_file", fau["spec_file_sha256"] == file_sha256(spec_path))
    check("result_file_sha256_matches_real_file", fau["result_file_sha256"] == file_sha256(result_path))
    check("no_modification_flag_true", fau["no_modification_made_to_frozen_spec_or_result"] is True)
    # verifica indipendente: lo spec/result gia' noti dal commit precedente non sono cambiati di numero
    check("spec_natural_horizon_still_40", spec_doc["payload"]["within_family_geometry_rule"]
          ["shared_across_all_6_families"]["natural_horizon"] == 40)
    check("spec_embargo_still_39", spec_doc["payload"]["within_family_geometry_rule"]
          ["shared_across_all_6_families"]["outcome_overlap_embargo_bars"] == 39)
    check("result_pooled_independent_units_still_11",
          result_doc["payload"]["cross_family_pooled_geometry"]["pooled_independent_units"] == 11)
    check("result_status_still_not_testable",
          result_doc["payload"]["seq0014b_status"] == "NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION")

    # ---- outcome non scelto: verificato contro il file reale di 7.6B, non assunto ----
    setup_pop_path = os.path.join(PHASE7_DIR, "phase7_6b", "seq0014b_setup_population_spec_v1.json")
    setup_pop = load_json(setup_pop_path)["payload"]
    once = p["outcome_not_chosen_evidence"]
    check("setup_population_has_no_primary_outcome_key",
          "primary_outcome" not in setup_pop["candidate_failure_noise_outcomes"])
    check("outcome_not_chosen_conclusion_present", "non puo' essere stato" in once["conclusion"] or
          "non esisteva ancora" in once["conclusion"])
    check("candidate_outcomes_list_nonempty", len(once["candidate_outcomes_listed_without_selection"]) >= 4)

    # ---- vocabolario outcome: hash verificato contro il file reale ----
    ove = p["outcome_vocabulary_evidence"]
    outcome_surface_path = os.path.join(PHASE7_DIR, "phase7_3", "outcome_surface_v3.py")
    check("outcome_vocabulary_file_hash_matches_real_file", ove["file_sha256"] == file_sha256(outcome_surface_path))
    check("outcome_vocabulary_has_no_intrinsic_horizon", ove["no_intrinsic_horizon_parameter_in_vocabulary"] is True)

    # ---- evidenza cross-experiment: SEQ-0014A (20) vs SEQ-0009 (40) - verificato contro i file reali ----
    seq0014a = load_json(os.path.join(PHASE7_DIR, "phase7_5c", "seq0014_frozen_structural_spec_v1.json"))["payload"]
    seq0009 = load_json(os.path.join(PHASE7_DIR, "phase7_5b", "seq0009_frozen_structural_spec_v1.json"))["payload"]
    cehe = p["cross_experiment_horizon_evidence"]
    check("seq0014a_horizon_matches_real_file", cehe["SEQ-0014A_state_entry_natural_horizon"] == seq0014a["proposed_natural_horizon"])
    check("seq0009_horizon_matches_real_file", cehe["SEQ-0009_sweep_reversal_natural_horizon"] == seq0009["proposed_natural_horizon"])
    check("horizons_genuinely_differ_within_project", cehe["horizons_differ_within_the_same_project"] is True)
    check("seq0014a_horizon_is_20", seq0014a["proposed_natural_horizon"] == 20)
    check("seq0009_horizon_is_40", seq0009["proposed_natural_horizon"] == 40)

    # ---- classificazione: PROJECT_CONVENTION, non A ne' B, coerente su tutte e 6 le famiglie tranne SWEEP ----
    hc = p["horizon_classification"]
    check("classification_is_project_convention", hc["classification"] == "PROJECT_CONVENTION")
    check("option_A_mechanism_derived_rejected", hc["classification_options_considered"]["A_MECHANISM_DERIVED"]["verdict"] is False)
    check("option_B_outcome_derived_rejected", hc["classification_options_considered"]["B_OUTCOME_DERIVED"]["verdict"] is False)
    check("option_C_project_convention_accepted", hc["classification_options_considered"]["C_PROJECT_CONVENTION"]["verdict"] is True)
    check("no_family_has_derivation_for_this_specific_experiment", hc["any_mechanism_derived_for_this_specific_experiment"] is False)
    pfhd = hc["per_family_horizon_derivation"]
    families = list(pfhd.keys())
    check("all_6_families_covered", set(families) == set(setup_pop["eligible_setup_families"]))
    check("sweep_has_a_derivation_but_not_for_this_experiment",
          pfhd["SWEEP"]["has_independent_mechanistic_horizon_derivation"] is True and
          pfhd["SWEEP"]["derivation_was_for_this_experiment"] is False)
    for fam in families:
        if fam == "SWEEP":
            continue
        check(f"{fam}_has_no_independent_horizon_derivation",
              pfhd[fam]["has_independent_mechanistic_horizon_derivation"] is False)

    # ---- scope correction: DESIGN_V1 identity ben definita, mai generalizzato a MECH-23 impossibile ----
    dv1 = p["design_v1_identity_and_scope_correction"]
    check("design_v1_name_present", dv1["name"] == "SEQ-0014B_DESIGN_V1")
    check("design_v1_components_include_horizon_and_embargo",
          dv1["components"]["natural_horizon_bars"] == 40 and dv1["components"]["outcome_overlap_embargo_bars"] == 39)
    check("design_v1_verdict_scoped_correctly",
          dv1["verdict_scoped_to_this_identity"] == "NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION")
    check("design_v1_explicitly_excludes_universal_mech23_claim",
          "MECH-23" in dv1["verdict_NOT_scoped_to"] and "impossibile" in dv1["verdict_NOT_scoped_to"])

    # ---- future requirements: outcome ex-ante, nuova identita', no horizon shopping ----
    fer = p["future_experiment_requirements"]
    check("future_requirements_at_least_4", len(fer) >= 4)
    check("future_requirements_mention_ex_ante_outcome", any("EX-ANTE" in r or "ex-ante" in r for r in fer))
    check("future_requirements_mention_new_identity", any("NUOVA identita'" in r or "nuova identita'" in r for r in fer))
    check("future_requirements_forbid_horizon_shopping", any("salvare" in r.lower() or "10/20/30" in r for r in fer))

    # ---- framework rule proposta: label nuovo, nessuna nuova infrastruttura costruita ----
    frp = p["framework_rule_proposed"]
    check("new_label_is_horizon_conditional", frp["new_result_classification_label"] == "HORIZON_CONDITIONAL_STRUCTURAL_RESULT")
    check("retroactive_application_does_not_modify_original_artifact",
          "SENZA modificare" in frp["retroactive_application_to_7_6c"])
    check("no_new_infrastructure_built_flag", "nessuna nuova" in frp["scope_of_this_proposal"].lower())

    # ---- vincoli espliciti dell'audit: nessuna esplorazione, nessun rescue, nessun outcome ----
    check("no_alternate_horizon_inspected_flag", p["no_alternate_horizon_inspected"] is True)
    check("no_preflight_rerun_flag", p["no_preflight_rereun"] is True)
    check("no_rescue_attempted_flag", p["no_rescue_attempted"] is True)
    check("no_frozen_modified_flag", p["no_frozen_spec_or_result_modified"] is True)
    check("no_outcome_accessed_flag", p["no_nexus_outcome_data_accessed"] is True)
    check("no_edge_discovery_flag", p["no_edge_discovery_performed"] is True)
    check("no_primary_outcome_selected_flag", p["no_primary_outcome_selected"] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non legge mai outcome ne' ricalcola geometria sui dati reali ----
    builder_path = os.path.join(PHASE76C_DIR, "build_seq0014b_outcome_horizon_ordering_audit.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_imports_outcome_computation",
          "load_outcomes" not in builder_src and "compute_outcome" not in builder_src)
    check("builder_never_reads_events_or_state_csv",
          "events_p71.csv" not in builder_src and "market_state_dataset_p71.csv" not in builder_src)
    check("builder_never_calls_compute_detection_funnel",
          "compute_detection_funnel" not in builder_src, "nessuna geometria ricalcolata, solo audit dei parametri gia' congelati")
    check("builder_never_writes_to_spec_or_result_paths",
          "seq0014b_structural_preflight_spec_v1.json\", \"w" not in builder_src and
          "seq0014b_structural_preflight_result_v1.json\", \"w" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== SEQ-0014B outcome-horizon ordering audit consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
