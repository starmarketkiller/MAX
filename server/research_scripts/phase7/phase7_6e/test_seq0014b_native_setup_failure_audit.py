#!/usr/bin/env python3
"""Phase 7.6E - Native Setup Failure Audit: consistency checks.
Verifica che le definizioni usate siano REALMENTE quelle gia' congelate
in fb52168/build_events_p71.py (non inventate), che la classificazione
sia internamente coerente, che nessuna barrier/horizon/DESIGN_V2 sia
stata creata, e che i frozen artifact precedenti restino invariati."""
import os
import sys

PHASE76E_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE76E_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE76E_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc_path = os.path.join(PHASE76E_DIR, "seq0014b_native_setup_failure_audit_v1.json")
    doc = load_json(doc_path)
    p = doc["payload"]

    check("canonical_hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_matches_expected", p["baseline_commit"] == "67282deb8d6808d9d1977a810463fe07393496b1")

    # ---- lifecycle audit: formule/direzioni citate devono coincidere con fb52168 REALE ----
    setup_pop = load_json(os.path.join(PHASE7_DIR, "phase7_6b", "seq0014b_setup_population_spec_v1.json"))["payload"]
    inv = setup_pop["detector_inventory"]
    fla = p["family_lifecycle_audit"]
    for fam in ["VOLATILITY_EXPANSION", "DISPLACEMENT", "BREAKOUT", "SWEEP", "COMPRESSION_RELEASE", "PULLBACK"]:
        check(f"{fam}_formula_matches_fb52168", fla[fam]["detector_formula"] == inv[fam]["formula"])
        check(f"{fam}_direction_matches_fb52168", fla[fam]["direction"] == inv[fam]["direction_defined"])
    check("build_events_hash_matches_real_file",
          fla["build_events_source_sha256"] == file_sha256(os.path.join(PHASE7_DIR, "phase7_1", "build_events_p71.py")))

    # ---- BREAKOUT/SWEEP invalidation cita il role GIA' congelato in fb52168, non inventato ----
    check("breakout_invalidation_cites_real_failed_breakout_role",
          repr(inv["FAILED_BREAKOUT"]["role"]) in fla["BREAKOUT"]["native_invalidation"])
    check("sweep_invalidation_cites_real_reclaim_role",
          repr(inv["RECLAIM"]["role"]) in fla["SWEEP"]["native_invalidation"])
    check("breakout_retest_diagnostic_cites_real_retest_role",
          repr(inv["RETEST"]["role"]) in fla["BREAKOUT"]["native_confirmation_diagnostic"])

    # ---- le 4 famiglie senza role in fb52168 devono avere native_invalidation=None qui ----
    for fam in ["VOLATILITY_EXPANSION", "DISPLACEMENT", "COMPRESSION_RELEASE", "PULLBACK"]:
        check(f"{fam}_has_no_role_field_in_fb52168_and_no_native_invalidation_here",
              "role" not in inv[fam] and fla[fam]["native_invalidation"] is None)

    # ---- classificazione: coerente con l'audit, nessuna famiglia FULL_NATIVE_SETUP ----
    fc = p["family_classification"]
    check("no_family_is_full_native_setup",
          all(fc[fam]["classification"] != "FULL_NATIVE_SETUP" for fam in
              ["VOLATILITY_EXPANSION", "DISPLACEMENT", "BREAKOUT", "SWEEP", "COMPRESSION_RELEASE", "PULLBACK"]))
    check("breakout_and_sweep_are_partial_setup",
          fc["BREAKOUT"]["classification"] == "PARTIAL_SETUP" and fc["SWEEP"]["classification"] == "PARTIAL_SETUP")
    check("other_4_are_directional_event_only",
          all(fc[fam]["classification"] == "DIRECTIONAL_EVENT_ONLY" for fam in
              ["VOLATILITY_EXPANSION", "DISPLACEMENT", "COMPRESSION_RELEASE", "PULLBACK"]))
    check("summary_counts_match_individual_classifications",
          fc["summary"]["FULL_NATIVE_SETUP_count"] == 0 and fc["summary"]["PARTIAL_SETUP_count"] == 2 and
          fc["summary"]["DIRECTIONAL_EVENT_ONLY_count"] == 4)

    # ---- double barrier semantic status: BREAKOUT/SWEEP misaligned (native invalidation exists and is bypassed) ----
    dbs = p["double_barrier_semantic_status"]
    check("breakout_double_barrier_is_semantically_misaligned", dbs["BREAKOUT"]["status"] == "SEMANTICALLY_MISALIGNED")
    check("sweep_double_barrier_is_semantically_misaligned", dbs["SWEEP"]["status"] == "SEMANTICALLY_MISALIGNED")
    check("other_4_are_compatible_but_synthetic",
          all(dbs[fam]["status"] == "COMPATIBLE_BUT_SYNTHETIC" for fam in
              ["VOLATILITY_EXPANSION", "DISPLACEMENT", "COMPRESSION_RELEASE", "PULLBACK"]))
    check("none_classified_native_flag", dbs["none_classified_as_native"] is True)

    # ---- referenced contract: verificato contro il file reale di 7.6D, non toccato ----
    contract_doc = load_json(os.path.join(PHASE7_DIR, "phase7_6d", "seq0014b_outcome_horizon_contract_v1.json"))
    check("phase_7_6d_contract_untouched_hash_matches",
          contract_doc["canonical_sha256"] == "9a36ce4648ff8e5d9b3fcad0864aa226b3998f164aced35c1dbb08ae50c5f1e6")

    # ---- false equivalence guard: entrambe le assunzioni esplicitamente respinte ----
    feg = p["false_equivalence_guard"]
    check("assumption_1_rejected", "RESPINTA" in feg["rejected_assumption_1"])
    check("assumption_2_rejected", "RESPINTA" in feg["rejected_assumption_2"])

    # ---- censoring correction: corregge 7.6D senza modificarlo ----
    cc = p["censoring_correction"]
    check("censoring_correction_references_three_state_partition",
          "P(SUCCESS)" in cc["correction"] and "P(FAILURE)" in cc["correction"] and
          "UNRESOLVED" in cc["correction"])
    check("censoring_correction_does_not_modify_frozen_artifact", cc["modification_to_frozen_artifact"] is False)

    # ---- claim identity: B e' quella operazionalizzata, non A silenziosamente ----
    ci = p["claim_identity"]
    check("currently_operationalized_is_B", ci["which_is_currently_operationalized"] == "B")
    check("explicit_non_silent_conversion_present", len(ci["explicit_non_silent_conversion"]) > 30)

    # ---- pooled compatibility: non implementato, conclusione onesta ----
    poc = p["pooled_outcome_compatibility"]
    check("pooled_native_failure_not_implemented", poc["not_implemented_here"] is True)

    # ---- decisione: verdetto e' uno dei 3 enumerati, coerente con la classificazione ----
    dec = p["decision"]
    check("verdict_is_one_of_three_valid_enums",
          dec["verdict"] in ("NATIVE_FAILURE_CONTRACT_AVAILABLE", "PARTIALLY_AVAILABLE_REQUIRES_SETUP_FORMALIZATION",
                              "MECH23_NOT_OPERATIONALIZABLE_ON_RAW_EVENT_FAMILIES"))
    check("verdict_matches_partial_availability_given_2_partial_families",
          dec["verdict"] == "PARTIALLY_AVAILABLE_REQUIRES_SETUP_FORMALIZATION")
    check("not_full_native_flag", dec["not_full_native_for_any_family"] is True)

    # ---- next requirement: nessuno stop/target inventato, pipeline reorg proposta non implementata ----
    nr = p["next_requirement"]
    check("no_stop_or_target_invented_flag", nr["no_stop_or_target_invented"] is True)
    check("pipeline_reorg_has_4_stages", len(nr["proposed_pipeline_reorg"]["stages"]) == 4)
    check("pipeline_reorg_not_implemented_flag", nr["proposed_pipeline_reorg"]["not_implemented_here"] is True)
    check("mech23_as_meta_filter_note_present", "STESSO" not in nr["mech23_as_meta_filter"] and
          len(nr["mech23_as_meta_filter"]) > 30)

    # ---- vincoli espliciti dell'audit ----
    for flag in ("no_stop_target_invalidation_invented", "no_barrier_magnitude_chosen", "no_horizon_chosen",
                 "no_geometry_or_preflight_executed", "no_design_v2_created", "no_frozen_prior_artifacts_modified",
                 "no_nexus_outcome_data_accessed", "no_structural_preflight_executed", "no_edge_discovery_performed",
                 "no_primary_outcome_selected"):
        check(f"{flag}_is_true", p[flag] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- frozen artifacts precedenti invariati (verifica diretta contro gli hash noti) ----
    spec_doc = load_json(os.path.join(PHASE7_DIR, "phase7_6c", "seq0014b_structural_preflight_spec_v1.json"))
    result_doc = load_json(os.path.join(PHASE7_DIR, "phase7_6c", "seq0014b_structural_preflight_result_v1.json"))
    horizon_audit_doc = load_json(os.path.join(PHASE7_DIR, "phase7_6c", "seq0014b_outcome_horizon_ordering_audit_v1.json"))
    check("design_v1_spec_hash_unchanged", spec_doc["canonical_sha256"] == "15136d2aed317ac484822e4b8cdeb31a411c4ecfa93aecb47d7c4b435adc4347")
    check("design_v1_result_status_unchanged", result_doc["payload"]["seq0014b_status"] == "NOT_TESTABLE_WITH_FROZEN_SETUP_POPULATION")
    check("horizon_ordering_audit_classification_unchanged",
          horizon_audit_doc["payload"]["horizon_classification"]["classification"] == "PROJECT_CONVENTION")

    # ---- verifica statica: il builder non legge/calcola mai outcome, prezzi, o geometria ----
    builder_path = os.path.join(PHASE76E_DIR, "build_seq0014b_native_setup_failure_audit.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_reads_events_or_state_or_bars_csv",
          "events_p71.csv" not in builder_src and "market_state_dataset_p71.csv" not in builder_src and
          "xauusd_h4_bars_p71.csv" not in builder_src)
    check("builder_never_imports_geometry_engine_modules",
          "from sequence_structural_feasibility_gate import" not in builder_src and
          "from dependence_diagnostics import" not in builder_src and
          "from baseline_engine_v4 import" not in builder_src)
    check("builder_never_writes_to_any_prior_frozen_artifact_path",
          "seq0014b_structural_preflight_spec_v1.json\", \"w" not in builder_src and
          "seq0014b_structural_preflight_result_v1.json\", \"w" not in builder_src and
          "seq0014b_outcome_horizon_contract_v1.json\", \"w" not in builder_src and
          "seq0014b_setup_population_spec_v1.json\", \"w" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== SEQ-0014B native setup failure audit consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
