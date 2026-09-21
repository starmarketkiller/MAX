#!/usr/bin/env python3
"""Phase 7.7B-REFINEMENT - Missing-Field Semantics Refinement:
consistency checks. Verifica che H006's invalidation_stop sia
classificato VERIFIED_ABSENCE+SATISFIED_BY_EQUIVALENT_MECHANISM contro
il file reale H006_frozen_spec.json (non assunto), che nessun candidato
diventi INELIGIBLE senza una VERIFIED_ABSENCE+REQUIRED reale, che nessun
NOT_EXTRACTED colli a ELIGIBLE, che readiness/gate/altri artifact restino
invariati."""
import os
import sys

PHASE77B_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE77B_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE77B_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc = load_json(os.path.join(PHASE77B_DIR, "missing_field_semantics_refinement_v1.json"))
    p = doc["payload"]

    check("hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_matches_expected", p["baseline_commit"] == "4743ce0a29310a411afb5bd656179ee43ed76e5f")

    # ---- Sorgenti NON modificate - verificate contro gli hash reali dei file ----
    su = p["sources_untouched"]
    lifecycle_doc = load_json(os.path.join(PHASE7_DIR, "phase7_7a", "strategy_lifecycle_registry_v1.json"))
    gate_doc = load_json(os.path.join(PHASE7_DIR, "phase7_7b", "strategy_meta_filter_gate_v1.json"))
    prior_doc = load_json(os.path.join(PHASE7_DIR, "phase7_7b", "structural_eligibility_semantics_correction_v1.json"))
    check("lifecycle_registry_hash_matches_real_file", su["lifecycle_registry"]["canonical_sha256"] == lifecycle_doc["canonical_sha256"])
    check("gate_hash_matches_real_file", su["gate"]["canonical_sha256"] == gate_doc["canonical_sha256"])
    check("prior_correction_hash_matches_real_file", su["prior_correction"]["canonical_sha256"] == prior_doc["canonical_sha256"])
    check("lifecycle_known_hash_unchanged",
          lifecycle_doc["canonical_sha256"] == "270088329416d23cef2d5675b8da21690d6e542d4b3493142c3e0fa15c628bf1")
    check("gate_known_hash_unchanged",
          gate_doc["canonical_sha256"] == "c3be76cb15c2bf479ccd4caa3e6c7193a0b1103feb5de49e6553574c39f9cb60")
    check("prior_correction_known_hash_unchanged",
          prior_doc["canonical_sha256"] == "5e2c93f4a9d8faca5284dd3341234c7c8b22682504c9a58ed8b948fc24c63822")
    check("modified_in_this_phase_flag_false", su["modified_in_this_phase"] is False)

    # ---- Vocabolario: esattamente i valori richiesti dal reviewer ----
    check("field_knowledge_values_exact",
          p["field_knowledge_values"] == ["VERIFIED_VALUE", "VERIFIED_ABSENCE", "NOT_EXTRACTED"])
    check("requirement_role_values_exact",
          p["requirement_role_values"] == ["REQUIRED", "NOT_REQUIRED_BY_DESIGN", "SATISFIED_BY_EQUIVALENT_MECHANISM"])
    check("rule_maps_verified_absence_plus_required_to_ineligible",
          "STRUCTURALLY_INELIGIBLE" in p["rule"]["VERIFIED_ABSENCE_plus_REQUIRED"])
    check("rule_not_extracted_always_unverified",
          p["rule"]["NOT_EXTRACTED_any_role"] == "STRUCTURAL_STATUS_UNVERIFIED (non possiamo giudicare il ruolo di un campo non letto)")

    # ---- H006 test-case: il cuore della richiesta - verificato contro il file H006_frozen_spec.json reale ----
    h006_spec_path = os.path.join(ROOT, "server", "research_scripts", "phase6", "H006_frozen_spec.json")
    h006_spec = load_json(h006_spec_path)
    tc = p["h006_test_case"]
    check("h006_test_case_field_is_invalidation_stop", tc["field"] == "invalidation_stop")
    check("h006_test_case_candidate_is_h006", tc["candidate"] == "H006_LIQUIDITY_SWEEP_RECLAIM")
    check("h006_test_case_field_knowledge_is_verified_absence", tc["field_knowledge"] == "VERIFIED_ABSENCE")
    check("h006_test_case_requirement_role_is_satisfied_by_equivalent",
          tc["requirement_role"] == "SATISFIED_BY_EQUIVALENT_MECHANISM")
    check("h006_test_case_does_not_imply_ineligibility", tc["does_this_imply_ineligibility"] is False)
    check("h006_test_case_source_hash_matches_real_file",
          tc["verified_against_real_source_file_sha256"] == file_sha256(h006_spec_path))
    check("h006_spec_genuinely_has_no_invalidation_or_stop_key",
          not any("invalid" in k.lower() or "stop" in k.lower() for k in h006_spec.keys()))
    check("h006_spec_primary_outcome_declares_no_dynamic_management",
          "nessuna gestione dinamica" in h006_spec["primary_outcome"]["definition"])

    # ---- Nessun candidato diventa INELIGIBLE senza una vera VERIFIED_ABSENCE+REQUIRED ----
    check("zero_ineligible_cases_found", p["ineligible_cases_count"] == 0)
    check("ineligible_cases_dict_empty", p["ineligible_cases_found"] == {})

    # ---- Nessun cambiamento di stato rispetto alla correzione precedente (4743ce0) ----
    check("zero_status_changes", p["status_changes_count"] == 0)
    pcfc = p["per_candidate_field_classifications"]
    check("all_7_candidates_present", len(pcfc) == 7)
    for cid, c in pcfc.items():
        check(f"{cid}_status_matches_prior_correction",
              c["refined_structural_status"] == c["prior_correction_structural_status"])

    # ---- Verifica specifica: nessun NOT_EXTRACTED risulta ELIGIBLE (mai colato attraverso) ----
    for cid, c in pcfc.items():
        has_not_extracted_required = any(
            fc["field_knowledge"] == "NOT_EXTRACTED" and fc["requirement_role"] == "REQUIRED"
            for fc in c["field_classifications"].values()
        )
        if has_not_extracted_required:
            check(f"{cid}_with_not_extracted_required_field_is_unverified_not_eligible",
                  c["refined_structural_status"] == "STRUCTURAL_STATUS_UNVERIFIED")

    # ---- I 3 candidati pienamente estratti restano ELIGIBLE con tutti i campi core VERIFIED_VALUE
    # (tranne H006.invalidation_stop, il test-case) ----
    for cid in ("VOLATILITY_BREAKOUT_CONFIRMED", "H015_SAR_EXTERNAL_VALIDATION"):
        check(f"{cid}_all_core_fields_verified_value",
              all(fc["field_knowledge"] == "VERIFIED_VALUE" for fc in pcfc[cid]["field_classifications"].values()))
    h006_fc = pcfc["H006_LIQUIDITY_SWEEP_RECLAIM"]["field_classifications"]
    check("h006_entry_direction_target_verified_value_invalidation_verified_absence",
          h006_fc["entry"]["field_knowledge"] == "VERIFIED_VALUE" and
          h006_fc["direction"]["field_knowledge"] == "VERIFIED_VALUE" and
          h006_fc["target_exit"]["field_knowledge"] == "VERIFIED_VALUE" and
          h006_fc["invalidation_stop"]["field_knowledge"] == "VERIFIED_ABSENCE")

    # ---- Research readiness invariata, gate invariato ----
    check("readiness_unchanged_confirmed_flag", p["research_readiness_unchanged_confirmed"] is True)
    old_gate_results = gate_doc["payload"]["gate_results_by_candidate"]
    for cid, g in p["refined_gate_results_by_candidate"].items():
        check(f"{cid}_readiness_matches_7_7b_exactly",
              g["research_readiness_unchanged"] == old_gate_results[cid]["meta_filter_research_readiness"])
    check("gate_count_unchanged_flag", p["gate_counts"]["gate_count_unchanged"] is True)
    check("gate_count_zero_before_and_after",
          p["gate_counts"]["meta_filter_ready_count_before_this_refinement"] == 0 and
          p["gate_counts"]["meta_filter_ready_count_after_this_refinement"] == 0)

    # ---- vincoli espliciti della fase ----
    for flag in ("no_new_backtest_executed", "no_new_research_performed", "no_mech23_applied",
                 "no_retroactive_modification_of_frozen_artifacts", "no_edge_discovery_performed"):
        check(f"{flag}_is_true", p[flag] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non legge mai outcome/prezzi, non riscrive artifact frozen ----
    builder_path = os.path.join(PHASE77B_DIR, "build_missing_field_semantics_refinement.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_reads_events_or_state_or_bars_csv",
          "events_p71.csv" not in builder_src and "market_state_dataset_p71.csv" not in builder_src)
    check("builder_never_writes_to_frozen_artifact_paths",
          "strategy_lifecycle_registry_v1.json\", \"w" not in builder_src and
          "strategy_meta_filter_gate_v1.json\", \"w" not in builder_src and
          "structural_eligibility_semantics_correction_v1.json\", \"w" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Missing-field semantics refinement consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
