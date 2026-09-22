#!/usr/bin/env python3
"""Phase 7.9A - Verifica INDIPENDENTE del postmortem/reprioritization.
Ricalcola dai file reali: i numeri canonici BUY/SELL (contro l'artifact
7.8I reale, mai modificato), le catene di hash verso 7.7A/7.7B/7.8I, la
coerenza del checklist standalone, e i vincoli espliciti della fase (no
nuovo backtest, no rescue, no modifica di artifact precedenti)."""
import os
import sys

PHASE79A_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE79A_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE79A_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

MANIFEST_PATH = os.path.join(PHASE79A_DIR, "phase7_9a_postmortem_and_reprioritization_v1.json")
CHECKLIST_PATH = os.path.join(PHASE79A_DIR, "serious_validation_preflight_checklist_v1.json")
RESULT_78I_PATH = os.path.join(PHASE7_DIR, "phase7_8i", "volatility_breakout_serious_3y_result_v1.json")
STRUCT_78B_PATH = os.path.join(PHASE7_DIR, "phase7_7b", "structural_eligibility_semantics_correction_v1.json")
LIFECYCLE_77A_PATH = os.path.join(PHASE7_DIR, "phase7_7a", "strategy_lifecycle_registry_v1.json")


def verify():
    doc = load_json(MANIFEST_PATH)
    p = doc["payload"]
    checks = {}

    result_doc = load_json(RESULT_78I_PATH)
    struct_doc = load_json(STRUCT_78B_PATH)
    lifecycle_doc = load_json(LIFECYCLE_77A_PATH)

    # ---- Sezione 1: numeri BUY/SELL ricalcolati dall'artifact 7.8I reale ----
    da = result_doc["payload"]["direction_asymmetry"]["per_direction"]
    reported = p["section_1_canonical_result_reconciliation"]["narrative_discrepancy_found"]["correct_values_canonical"]
    checks["buy_n_matches_real_7_8i"] = reported["BUY"]["n"] == da["BUY"]["n"] == 56
    checks["buy_expectancy_matches_real_7_8i"] = abs(reported["BUY"]["expectancy_R"] - da["BUY"]["expectancy_R"]) < 1e-9
    checks["buy_pf_matches_real_7_8i"] = abs(reported["BUY"]["pf"] - da["BUY"]["pf"]) < 1e-9
    checks["sell_n_matches_real_7_8i"] = reported["SELL"]["n"] == da["SELL"]["n"] == 127
    checks["sell_expectancy_matches_real_7_8i"] = abs(reported["SELL"]["expectancy_R"] - da["SELL"]["expectancy_R"]) < 1e-9
    checks["sell_pf_matches_real_7_8i"] = abs(reported["SELL"]["pf"] - da["SELL"]["pf"]) < 1e-9
    checks["7_8i_artifact_hash_referenced_matches_real_file"] = (
        p["section_1_canonical_result_reconciliation"]["canonical_source"]["canonical_sha256"] == result_doc["canonical_sha256"]
    )
    checks["aggregate_verdict_still_fail"] = (
        p["section_1_canonical_result_reconciliation"]["aggregate_verdict_unchanged"]["final_classification"]
        == result_doc["payload"]["final_classification"] == "FAIL"
    )

    # ---- Vault report corretto sul filesystem reale ----
    vault_path = os.path.join(ROOT, "vault", "01-Trading",
                               "NEXUS - Phase 7.8I Recompile + Research Mode - Primo Risultato Scientifico (FAIL).md")
    checks["vault_7_8i_file_exists"] = os.path.isfile(vault_path)
    if os.path.isfile(vault_path):
        with open(vault_path, encoding="utf-8") as f:
            vault_text = f.read()
        checks["vault_7_8i_now_shows_correct_buy_numbers"] = "n=56" in vault_text and "-0,726" in vault_text
        checks["vault_7_8i_now_shows_correct_sell_numbers"] = "n=127" in vault_text and "+0,223" in vault_text
        checks["vault_7_8i_no_longer_shows_wrong_numbers"] = "n=63" not in vault_text and "n=120" not in vault_text

    # ---- Sezione 2: hash reali verso 7.7A/7.7B/7.8I ----
    sec2 = p["section_2_archive_lifecycle"]
    checks["lifecycle_7_7a_hash_matches_real_file"] = (
        sec2["source_artifacts_untouched"]["lifecycle_registry_7_7a"]["canonical_sha256"] == lifecycle_doc["canonical_sha256"]
    )
    checks["structural_7_7b_hash_matches_real_file"] = (
        sec2["source_artifacts_untouched"]["structural_eligibility_7_7b"]["canonical_sha256"] == struct_doc["canonical_sha256"]
    )
    checks["7_8i_result_hash_in_chain_matches_real_file"] = (
        sec2["full_evidence_chain_hashes"]["7_8i_result"] == result_doc["canonical_sha256"]
    )
    checks["new_state_is_archived"] = sec2["new_state_as_of_7_9a"]["research_readiness"] == "REFUTED_ARCHIVED"
    checks["new_state_not_deployable"] = sec2["new_state_as_of_7_9a"]["deployable"] is False
    checks["new_state_not_execution_candidate"] = sec2["new_state_as_of_7_9a"]["execution_candidate"] is False

    # ---- Sezione 3: nessun rescue ----
    sec3 = p["section_3_directional_observation"]
    checks["directional_observation_not_rescue"] = sec3["explicitly_not"] == "RESCUED_STRATEGY"
    checks["no_sell_only_variant_created"] = sec3["no_automatic_sell_only_variant_created"] is True

    # ---- Sezione 6: candidati esclusi/rimasti coerenti con 7.7B reale ----
    sec6 = p["section_6_remaining_candidate_inventory"]
    real_readiness = struct_doc["payload"]["research_readiness_by_candidate_unchanged"]
    checks["h006_readiness_matches_real_7_7b"] = (
        sec6["remaining_open_candidates"]["H006_LIQUIDITY_SWEEP_RECLAIM"]["research_readiness"]
        == real_readiness["H006_LIQUIDITY_SWEEP_RECLAIM"]["meta_filter_research_readiness"]
    )
    checks["breakout_acc_readiness_matches_real_7_7b"] = (
        sec6["remaining_open_candidates"]["BREAKOUT_ACC"]["research_readiness"]
        == real_readiness["BREAKOUT_ACC"]["meta_filter_research_readiness"]
    )
    checks["no_refuted_candidate_in_remaining_list"] = not any(
        cid in sec6["remaining_open_candidates"] for cid in sec6["excluded_as_already_refuted"]
    )

    # ---- Sezione 8: decisione con solo 3 categorie ammesse ----
    checks["decision_class_is_valid"] = p["section_8_next_research_decision"]["decision_class"] in (
        "FORMALIZE_EXISTING_CANDIDATE", "VALIDATE_EXISTING_CANDIDATE", "RETURN_TO_EVENT_DISCOVERY")
    checks["decision_did_not_execute_test"] = "Nessun test lanciato" in p["section_8_next_research_decision"]["explicitly_not_executed"]

    # ---- Checklist standalone: esiste ed e' referenziato correttamente ----
    checks["checklist_standalone_file_exists"] = os.path.isfile(CHECKLIST_PATH)
    if os.path.isfile(CHECKLIST_PATH):
        checklist_doc = load_json(CHECKLIST_PATH)
        checks["checklist_standalone_hash_matches_payload"] = checklist_doc["canonical_sha256"] == canonical_sha256(checklist_doc["payload"])
        checks["checklist_has_12_items"] = len(checklist_doc["payload"]["checklist"]) == 12
        checks["checklist_cross_ref_matches"] = (
            p["section_5_permanent_preflight_checklist"]["standalone_file_canonical_sha256"] == checklist_doc["canonical_sha256"]
        )

    # ---- Vincoli espliciti della fase ----
    checks["no_new_backtest_flag"] = p["no_new_backtest_executed"] is True
    checks["no_strategy_modified_flag"] = p["no_strategy_modified"] is True
    checks["no_rescue_flag"] = p["no_rescue_performed"] is True

    core_checks = {k: v for k, v in checks.items() if isinstance(v, bool)}
    all_passed = all(core_checks.values())
    verdict = "POSTMORTEM_INDEPENDENTLY_CONFIRMED" if all_passed else "VERIFICATION_FAILED"
    return checks, verdict


def main():
    checks, verdict = verify()
    for k, v in checks.items():
        print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print(f"\nVERDICT: {verdict}")
    return verdict == "POSTMORTEM_INDEPENDENTLY_CONFIRMED"


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
