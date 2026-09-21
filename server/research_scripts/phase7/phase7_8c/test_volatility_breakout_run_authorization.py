#!/usr/bin/env python3
"""Phase 7.8C - Run Authorization: consistency checks.
Verifica che nessun numero sia stato inventato per i 3 blocker, che le
regole adottate siano genuinamente scale-free/strutturali o
riconducibili a policy esistenti (citate correttamente), che il verdetto
non sia mai READY_TO_RUN, che 7.8A/7.8B restino invariati, e che nessun
backtest/outcome/optimization sia stato toccato."""
import os
import sys

PHASE78C_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78C_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78C_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc = load_json(os.path.join(PHASE78C_DIR, "volatility_breakout_serious_3y_run_authorization_v1.json"))
    p = doc["payload"]

    check("hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_matches_expected", p["baseline_commit"] == "26be3863413682a9e5baef45cb59a0f6f7f5d2d9")
    check("candidate_is_volbrk", p["candidate_id"] == "VOLATILITY_BREAKOUT_CONFIRMED")

    # ---- 7.8A/7.8B NON modificati ----
    prereg_path = os.path.join(PHASE7_DIR, "phase7_8b", "volatility_breakout_serious_3y_prereg_v1.json")
    voi_path = os.path.join(PHASE7_DIR, "phase7_8a", "volatility_breakout_voi_contract_v1.json")
    prereg_doc = load_json(prereg_path)
    voi_doc = load_json(voi_path)
    sa = p["source_artifacts_untouched"]
    check("prereg_hash_matches_real_file", sa["prereg"]["canonical_sha256"] == prereg_doc["canonical_sha256"])
    check("voi_hash_matches_real_file", sa["voi_contract"]["canonical_sha256"] == voi_doc["canonical_sha256"])
    check("prereg_known_hash_unchanged",
          prereg_doc["canonical_sha256"] == "4eadc5fd9c529e1bb8722add4dcb5784ae85327e991c6c1c6712c163f4d827e8")
    check("modified_in_this_phase_false", sa["modified_in_this_phase"] is False)

    # ---- Sec.1: naming correction - 7.8B non modificato, vocabolario corretto ----
    nc = p["naming_correction"]
    check("naming_target_hash_matches_real_prereg", nc["target_artifact_canonical_sha256_unchanged"] == prereg_doc["canonical_sha256"])
    check("naming_modified_flag_false", nc["modified_in_this_phase"] is False)
    check("corrected_vocab_has_3_windows",
          set(nc["corrected_vocabulary"].keys()) == {"TOTAL_TEST_WINDOW", "PRIMARY_FRESH_VERDICT_WINDOW",
                                                        "PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW"})
    check("forbidden_labels_include_3y_oos", any("3Y OOS" in lbl for lbl in nc["forbidden_labels"]))

    # ---- Sec.2: materiality - nessun numero R inventato, citazione reale di cost_model_integration.json ----
    cost_model_path = os.path.join(PHASE7_DIR, "policies", "cost_model_integration.json")
    cost_model = load_json(cost_model_path)
    mr = p["materiality_blocker_resolution"]
    check("materiality_status_resolved", mr["status"] == "RESOLVED")
    check("materiality_no_numeric_threshold_invented",
          mr["adopted_resolution"]["numeric_materiality_threshold"] == "NOT_REQUIRED_AT_THIS_STAGE")
    gate_text = mr["adopted_resolution"]["executable_edge_gate"]
    check("materiality_gate_uses_ci_and_stress_not_a_magnitude",
          "CI95" in gate_text and "STRESS" in gate_text and
          "0.05" not in gate_text and "0.10" not in gate_text and "0.1" not in gate_text)
    check("materiality_cites_real_cost_model_structural_edge_states",
          "STRUCTURAL_EDGE" in mr["supporting_policy_evidence"]["cost_model_integration_two_state_framework"] and
          "EXECUTABLE_EDGE_AFTER_COST" in mr["supporting_policy_evidence"]["cost_model_integration_two_state_framework"] and
          "STRUCTURAL_EDGE" in cost_model["states"] and "EXECUTABLE_EDGE_AFTER_COST" in cost_model["states"])
    check("materiality_supportability_is_partial_not_full",
          mr["resolution_supportability"] == "PARTIALLY_SUPPORTED_BY_EXISTING_POLICY_STRUCTURE_ADAPTED")
    check("materiality_magnitude_still_always_reported_flag", mr["adopted_resolution"]["magnitude_still_always_reported"] is True)

    # ---- Sec.3: temporal stability - regola scale-free, nessun valore R assoluto ----
    tsr = p["temporal_stability_blocker_resolution"]
    check("temporal_status_resolved", tsr["status"] == "RESOLVED")
    check("temporal_rejected_fixed_r_threshold_explicitly",
          "0.05R" in tsr["rejected_approach"] or "fissa" in tsr["rejected_approach"])
    check("temporal_criterion_1_is_sign_based_2_of_3",
          "2 dei 3" in tsr["adopted_rule"]["criterion_1"] and ">= 0" in tsr["adopted_rule"]["criterion_1"])
    check("temporal_criterion_2_is_ratio_based_100pct",
          "100%" in tsr["adopted_rule"]["criterion_2"])
    check("temporal_explicitly_scale_free",
          "valore assoluto" in tsr["adopted_rule"]["why_scale_free"] and
          "calibrazione specifica della scala" in tsr["adopted_rule"]["why_scale_free"])
    check("temporal_cites_sar_macd_precedent_in_outcome_mapping",
          "SAR" in tsr["outcome_mapping"]["criterion_1_or_2_violated_moderately"] and
          "MACD" in tsr["outcome_mapping"]["both_criteria_violated"])

    # ---- Sec.4: same-bar SL/TP - sintesi bracket, mai un tie-break sintetico, cita Failure Memory ----
    sbr = p["same_bar_sl_tp_blocker_resolution"]
    check("same_bar_status_resolved", sbr["status"] == "RESOLVED")
    check("same_bar_principle_is_real_tick_required",
          sbr["adopted_principle"].startswith("REAL_TICK_REQUIRED_FOR_PRIMARY_VERDICT"))
    check("same_bar_never_assumes_tp_or_sl_first",
          "MAI assunto silenziosamente" in sbr["resolution_logic"]["if_ordering_not_resolvable"])
    check("same_bar_cites_data_coverage_gap_pattern",
          "DATA_COVERAGE_GAP" in sbr["resolution_logic"]["if_ordering_not_resolvable"])
    check("same_bar_is_synthesis_not_pure_a_or_b",
          "SINTESI" in sbr["chosen_option_between_A_and_B"])
    check("same_bar_bracket_uses_worst_and_best_case",
          "worst_case" in sbr["adopted_synthesis"]["mandatory_sensitivity_bracket"] and
          "best_case" in sbr["adopted_synthesis"]["mandatory_sensitivity_bracket"])
    check("same_bar_decision_rule_has_new_explicit_state",
          "EXECUTION_ORDER_UNRESOLVED_BLOCKS_VERDICT" in sbr["adopted_synthesis"]["decision_rule"])

    # ---- Failure Memory: verificato che il pattern citato esiste davvero nel file reale ----
    failure_memory_path = os.path.join(
        ROOT, "vault", "01-Trading",
        "NEXUS - Failure Memory (Registro Pattern di Fallimento Metodologico) (12-09).md")
    with open(failure_memory_path, encoding="utf-8") as f:
        failure_memory_text = f.read()
    check("data_coverage_gap_pattern_really_exists_in_failure_memory", "DATA_COVERAGE_GAP" in failure_memory_text)
    check("shadow_execution_assumption_pattern_really_exists", "SHADOW_EXECUTION_ASSUMPTION" in failure_memory_text)

    # ---- Sec.5: PRE-RUN MANIFEST schema - NON creato con dati reali, solo schema/procedura ----
    pms = p["prerun_manifest_schema"]
    check("manifest_not_created_flag", pms["artifact_not_created_in_this_phase"] is True)
    required_fields_expected = {"exact_start_timestamp", "exact_end_timestamp", "fresh_window_start",
                                 "fresh_window_end", "previously_observed_window_start",
                                 "previously_observed_window_end", "broker_timezone_offset", "symbol",
                                 "timeframe", "tester_model", "tick_coverage_pct_by_subperiod",
                                 "dataset_history_hash", "strategy_commit_or_hash", "cost_model_hash",
                                 "prereg_hash", "code_commit_sha"}
    check("manifest_required_fields_complete", set(pms["required_fields"]) == required_fields_expected)
    check("manifest_procedural_rule_after_sync_before_results",
          "AFTER data synchronization" in pms["procedural_rule"]["step_1"] and
          "BEFORE backtest execution" in pms["procedural_rule"]["step_2"])
    check("manifest_invariant_no_results", "Nessun risultato" in pms["procedural_rule"]["invariant"])
    check("manifest_hash_refs_prereg_hash_matches_real_file",
          pms["hash_references_this_manifest_must_pin"]["prereg_hash"] == prereg_doc["canonical_sha256"])
    check("manifest_hash_refs_cost_model_hash_matches_real_file",
          pms["hash_references_this_manifest_must_pin"]["cost_model_hash"] == file_sha256(cost_model_path))
    check("manifest_strategy_commit_matches_prereg",
          pms["hash_references_this_manifest_must_pin"]["strategy_frozen_commit"] ==
          prereg_doc["payload"]["strategy_identity_frozen"]["frozen_commit"])

    # ---- Sec.6: run authorization - mai READY_TO_RUN, tutti i blocker RESOLVED ----
    ra = p["run_authorization"]
    check("all_3_blockers_resolved",
          all(v == "RESOLVED" for v in ra["blockers_from_7_8b_status"].values()) and
          len(ra["blockers_from_7_8b_status"]) == 3)
    check("verdict_is_ready_for_prerun_seal", ra["verdict"] == "READY_FOR_PRE_RUN_SEAL")
    check("verdict_never_ready_to_run", "READY_TO_RUN" not in ra["verdict"])
    check("explicitly_not_ready_to_run_flag", ra["explicitly_not_ready_to_run"] is True)
    check("verdict_options_are_exactly_the_2_allowed",
          set(ra["verdict_options_considered"]) == {"READY_FOR_PRE_RUN_SEAL", "STILL_BLOCKED"})

    # ---- Sec.7: final gate chain - 5 stadi, nessuna nuova infrastruttura ----
    fgc = p["final_gate_chain"]
    check("gate_chain_has_5_stages", len(fgc["stages"]) == 5)
    check("gate_chain_ends_with_immutable_result", "IMMUTABLE_RESULT_ARTIFACT" in fgc["stages"][-1])
    check("gate_chain_not_new_infrastructure_flag", fgc["not_implemented_as_new_infrastructure"] is True)

    # ---- vincoli espliciti della fase ----
    for flag in ("serious_3y_not_executed", "no_new_outcome_data_accessed", "no_parameter_optimization_performed",
                 "no_edge_discovery_performed", "no_retroactive_modification_of_frozen_artifacts"):
        check(f"{flag}_is_true", p[flag] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non legge mai outcome/prezzi, non esegue backtest, non riscrive frozen ----
    builder_path = os.path.join(PHASE78C_DIR, "build_volatility_breakout_run_authorization.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_reads_events_or_state_or_bars_csv",
          "events_p71.csv" not in builder_src and "market_state_dataset_p71.csv" not in builder_src)
    check("builder_never_imports_or_invokes_backtest_engine",
          "import backtest" not in builder_src and "from backtest" not in builder_src)
    check("builder_never_writes_to_frozen_artifact_paths",
          "volatility_breakout_serious_3y_prereg_v1.json\", \"w" not in builder_src and
          "volatility_breakout_voi_contract_v1.json\", \"w" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== VOLATILITY_BREAKOUT run authorization consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
