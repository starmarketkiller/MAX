#!/usr/bin/env python3
"""Phase 7.7B-CORRECTION - Structural Eligibility Semantics Correction:
consistency checks. Verifica che la riclassificazione sia genuinamente
fondata sul testo REALE di Phase 7.7A (non assunta), che WICK_SWEEP_
RECLAIM/SAR_LIVE/ADX_RSI/BREAKOUT_ACC siano tutti UNVERIFIED (mai
INELIGIBLE), che la research readiness sia identica a 7.7B, che il gate
count non cambi, e che 7.7A/7.7B restino byte-identici (non modificati)."""
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
    doc = load_json(os.path.join(PHASE77B_DIR, "structural_eligibility_semantics_correction_v1.json"))
    p = doc["payload"]

    check("hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_matches_expected", p["baseline_commit"] == "72bcbf299dc2bab52fb435f0b0d3320a52ff99a2")

    # ---- 7.7A e 7.7B NON modificati - verificato contro gli hash reali dei file ----
    lifecycle_path = os.path.join(PHASE7_DIR, "phase7_7a", "strategy_lifecycle_registry_v1.json")
    gate_path = os.path.join(PHASE7_DIR, "phase7_7b", "strategy_meta_filter_gate_v1.json")
    lifecycle_doc = load_json(lifecycle_path)
    gate_doc = load_json(gate_path)
    check("lifecycle_registry_hash_matches_real_file",
          p["source_lifecycle_registry_untouched"]["canonical_sha256"] == lifecycle_doc["canonical_sha256"])
    check("lifecycle_registry_known_hash_unchanged",
          lifecycle_doc["canonical_sha256"] == "270088329416d23cef2d5675b8da21690d6e542d4b3493142c3e0fa15c628bf1")
    check("gate_hash_matches_real_file",
          p["source_gate_untouched"]["canonical_sha256"] == gate_doc["canonical_sha256"])
    check("gate_known_hash_unchanged",
          gate_doc["canonical_sha256"] == "c3be76cb15c2bf479ccd4caa3e6c7193a0b1103feb5de49e6553574c39f9cb60")
    check("no_retroactive_modification_flag", p["no_retroactive_modification_of_7_7a_or_7_7b"] is True)

    # ---- Tassonomia: esattamente 3 valori, ognuno con definizione sostanziale ----
    check("three_structural_values_exactly",
          p["structural_eligibility_values"] == ["STRUCTURALLY_ELIGIBLE", "STRUCTURALLY_INELIGIBLE",
                                                   "STRUCTURAL_STATUS_UNVERIFIED"])
    check("missing_field_taxonomy_has_3_classes",
          set(p["missing_field_taxonomy"].keys()) == {"source-null", "audit-not-extracted", "explicitly-absent"})
    check("general_rule_states_missing_neq_absence",
          "MISSING_FIELD != VERIFIED_ABSENCE" in p["general_rule"])

    # ---- Il caso centrale del reviewer: WICK_SWEEP_RECLAIM deve diventare UNVERIFIED, mai INELIGIBLE ----
    corrected = p["corrected_structural_status_by_candidate"]
    check("wick_sweep_corrected_to_unverified",
          corrected["WICK_SWEEP_RECLAIM"]["corrected_structural_status"] == "STRUCTURAL_STATUS_UNVERIFIED")
    check("wick_sweep_old_status_was_not_eligible",
          corrected["WICK_SWEEP_RECLAIM"]["old_7_7b_structural_status"] == "NOT_ELIGIBLE")
    check("wick_sweep_correction_applied_flag", corrected["WICK_SWEEP_RECLAIM"]["correction_applied"] is True)
    check("wick_sweep_taxonomy_is_audit_not_extracted",
          corrected["WICK_SWEEP_RECLAIM"]["missing_field_taxonomy_class"] == "audit-not-extracted")

    # ---- Verifica che la citazione sia REALMENTE presente nel testo di 7.7A (non inventata) ----
    real_wick_rationale = lifecycle_doc["payload"]["deep_dive_candidates"]["WICK_SWEEP_RECLAIM"]["classification_rationale"]
    check("wick_sweep_evidence_quote_matches_real_7_7a_text",
          corrected["WICK_SWEEP_RECLAIM"]["evidence_quote_from_7_7a_rationale"] == real_wick_rationale)
    check("wick_sweep_real_rationale_confirms_audit_depth_not_absence",
          "non per assenza di formalizzazione" in real_wick_rationale and "non ha approfondito" in real_wick_rationale)

    # ---- Gli altri 3 candidati gia' riconosciuti come audit-depth devono restare UNVERIFIED, non INELIGIBLE ----
    for cid in ("SAR_LIVE", "ADX_RSI", "BREAKOUT_ACC"):
        check(f"{cid}_corrected_to_unverified",
              corrected[cid]["corrected_structural_status"] == "STRUCTURAL_STATUS_UNVERIFIED")
        check(f"{cid}_taxonomy_is_audit_not_extracted",
              corrected[cid]["missing_field_taxonomy_class"] == "audit-not-extracted")
        real_rationale = lifecycle_doc["payload"]["deep_dive_candidates"][cid]["classification_rationale"]
        check(f"{cid}_evidence_quote_matches_real_7_7a_text",
              corrected[cid]["evidence_quote_from_7_7a_rationale"] == real_rationale)

    # ---- I 3 candidati gia' pienamente estratti restano ELIGIBLE (rinominati, non riclassificati nella sostanza) ----
    for cid in ("VOLATILITY_BREAKOUT_CONFIRMED", "H006_LIQUIDITY_SWEEP_RECLAIM", "H015_SAR_EXTERNAL_VALIDATION"):
        check(f"{cid}_remains_eligible_renamed",
              corrected[cid]["corrected_structural_status"] == "STRUCTURALLY_ELIGIBLE" and
              corrected[cid]["old_7_7b_structural_status"] == "ELIGIBLE" and
              corrected[cid]["correction_applied"] is False)

    # ---- Nessun caso di assenza strutturale POSITIVAMENTE verificata in questo registro (dichiarato, non assunto) ----
    check("zero_verified_positive_absence_cases", p["verified_positive_absence_count"] == 0)
    check("verified_positive_absence_cases_dict_is_empty", p["verified_positive_absence_cases"] == {})

    # ---- Research readiness: IDENTICA a 7.7B, mai ricalcolata ----
    old_gate_results = gate_doc["payload"]["gate_results_by_candidate"]
    readiness = p["research_readiness_by_candidate_unchanged"]
    check("readiness_unchanged_confirmed_flag", p["research_readiness_unchanged_confirmed"] is True)
    for cid, r in readiness.items():
        check(f"{cid}_readiness_matches_7_7b_exactly",
              r["meta_filter_research_readiness"] == old_gate_results[cid]["meta_filter_research_readiness"])
        check(f"{cid}_next_evidence_matches_7_7b_exactly",
              r["next_required_evidence"] == old_gate_results[cid]["next_required_evidence"])

    # ---- Coexistence senza contraddizione: structural=UNVERIFIED + readiness=REFUTED_INAPPROPRIATE e' valido ----
    check("sar_live_unverified_plus_refuted_readiness_coexist",
          corrected["SAR_LIVE"]["corrected_structural_status"] == "STRUCTURAL_STATUS_UNVERIFIED" and
          readiness["SAR_LIVE"]["meta_filter_research_readiness"] == "REFUTED_INAPPROPRIATE")

    # ---- Gate: UNVERIFIED deve fallire chiuso, nessun candidato promosso dalla correzione ----
    corrected_gate = p["corrected_gate_results_by_candidate"]
    check("unverified_candidates_all_fail_gate",
          all(not corrected_gate[cid]["meta_filter_ready_gate_passed"] for cid in corrected
              if corrected[cid]["corrected_structural_status"] == "STRUCTURAL_STATUS_UNVERIFIED"))
    check("no_candidate_promoted_flag", p["no_candidate_promoted_by_this_correction"] is True)
    check("gate_count_unchanged_flag", p["gate_counts"]["gate_count_unchanged"] is True)
    check("gate_count_zero_before_and_after",
          p["gate_counts"]["meta_filter_ready_count_before_correction"] == 0 and
          p["gate_counts"]["meta_filter_ready_count_after_correction"] == 0)

    # ---- Conteggi strutturali coerenti ----
    sca = p["structural_counts_after_correction"]
    check("structural_counts_sum_to_7",
          sca["structurally_eligible"] + sca["structurally_ineligible"] + sca["unverified"] == 7)
    check("structural_counts_eligible_is_3", sca["structurally_eligible"] == 3)
    check("structural_counts_ineligible_is_0", sca["structurally_ineligible"] == 0)
    check("structural_counts_unverified_is_4", sca["unverified"] == 4)

    # ---- Future axis proposal: solo concettuale, nessuna nuova infrastruttura ----
    fap = p["future_axis_proposal"]
    check("future_axis_is_execution_readiness", fap["proposed_axis"] == "META_FILTER_EXECUTION_READINESS")
    check("future_axis_cites_wick_sweep_shadow_vs_real",
          "5.80" in fap["rationale"] and "0.78" in fap["rationale"])
    check("future_axis_not_implemented_flag", fap["not_implemented_here"] is True)
    check("future_axis_no_new_infrastructure_flag", fap["no_new_infrastructure_built"] is True)

    # ---- vincoli espliciti della fase ----
    for flag in ("no_new_backtest_executed", "no_mech23_applied", "no_new_outcome_data_accessed",
                 "no_edge_discovery_performed", "no_retroactive_modification_of_7_7a_or_7_7b"):
        check(f"{flag}_is_true", p[flag] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non legge mai outcome/prezzi, non riscrive 7.7A/7.7B, non fa deep-dive codice ----
    builder_path = os.path.join(PHASE77B_DIR, "build_structural_eligibility_semantics_correction.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_reads_events_or_state_or_bars_csv",
          "events_p71.csv" not in builder_src and "market_state_dataset_p71.csv" not in builder_src)
    check("builder_never_reads_mql5_source_files",
          ".mqh" not in builder_src and "NXS_Strategies" not in builder_src)
    check("builder_never_writes_to_7_7a_or_7_7b_paths",
          "strategy_lifecycle_registry_v1.json\", \"w" not in builder_src and
          "strategy_meta_filter_gate_v1.json\", \"w" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Structural eligibility semantics correction consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
