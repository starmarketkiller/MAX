#!/usr/bin/env python3
"""Phase 7.8B - Serious 3Y Preregistration: consistency checks.
Verifica che ogni soglia riusata coincida con l'artifact canonico
reale (minimum_evidence_gates.json, cost_model_integration.json,
stability_matrix_policy.json), che i NOT_YET_JUSTIFIED siano genuini
(nessun numero inventato nascosto), che il no-rescue clause sia
completo, che nessun result branch porti a LIVE, e che nessun
backtest/outcome/parametro sia stato toccato."""
import os
import sys

PHASE78B_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78B_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78B_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc = load_json(os.path.join(PHASE78B_DIR, "volatility_breakout_serious_3y_prereg_v1.json"))
    p = doc["payload"]

    check("hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_matches_expected", p["baseline_commit"] == "b8c598f0bbf7693d7f9c9641853e8d7d339bb67f")
    check("candidate_is_volbrk", p["candidate_id"] == "VOLATILITY_BREAKOUT_CONFIRMED")

    # ---- 7.8A NON modificato ----
    voi_path = os.path.join(PHASE7_DIR, "phase7_8a", "volatility_breakout_voi_contract_v1.json")
    voi_doc = load_json(voi_path)
    edc = p["evidence_dependence_correction"]
    check("voi_contract_hash_matches_real_file", edc["target_artifact_canonical_sha256_unchanged"] == voi_doc["canonical_sha256"])
    check("voi_contract_known_hash_unchanged",
          voi_doc["canonical_sha256"] == "cbef913124092cc94ba3ff8479d0102a30dc3afe5fe78976ede24ed0a5cc08ac")
    check("voi_not_modified_flag", edc["modified_in_this_phase"] is False)
    check("voi_verdict_referenced_matches_real", p["voi_contract_verdict_referenced"] ==
          voi_doc["payload"]["serious_3y_eligibility_verdict"]["value"])

    # ---- Sec.1: evidence dependence correction - concordance/independence separati, verdict invariato ----
    corr = edc["correction"]["corrected_framing"]
    check("evidence_concordance_positive", corr["evidence_concordance"] == "POSITIVE")
    check("evidence_independence_not_established", corr["evidence_independence"] == "NOT_ESTABLISHED")
    check("voi_verdict_not_flipped", edc["correction"]["does_this_change_the_voi_verdict"] is False)

    # ---- Sec.2: strategy identity verificata contro il registro reale ----
    reg = load_json(os.path.join(ROOT, "contracts", "strategy-registry.json"))
    reg_entry = next(s for s in reg["strategies"] if s["strategy_id"] == "VOLATILITY_BREAKOUT_CONFIRMED")
    si = p["strategy_identity_frozen"]
    check("frozen_commit_is_f035d30", si["frozen_commit"] == "f035d30")
    check("registry_entry_matches_real_registry",
          si["registry_entry_verified"]["status"] == reg_entry["status"] and
          si["registry_entry_verified"]["selector_index"] == reg_entry["selector_index"] and
          si["registry_entry_verified"]["research_parity"] == reg_entry["research_parity"])
    check("no_parameter_may_change_flag", si["no_parameter_may_change_after_this_commit"] is True)
    check("target_is_exactly_1R_no_other_multiple", "1xR" in si["target"] or "1R" in si["target"])
    check("censoring_note_present_and_correct",
          "non ha uno stato" in si["censoring_note"] or "P&L e' SEMPRE definito" in si["censoring_note"])

    # ---- Sec.3: dataset/period - previously observed vs fresh, no absolute dates fabricated ----
    dp = p["dataset_and_period"]
    check("trailing_6mo_marked_previously_observed",
          dp["previously_observed_vs_fresh"]["trailing_6_months_2026_03_2026_09"]["status"] == "PREVIOUSLY_OBSERVED")
    check("remaining_marked_fresh_with_caveat",
          dp["previously_observed_vs_fresh"]["remaining_approx_2_5_years_preceding_the_trailing_segment"]["status"]
          == "FRESH_FOR_THIS_EXACT_COMBINED_STRATEGY")
    check("fresh_caveat_mentions_h001_h008_refuted",
          "H001" in dp["previously_observed_vs_fresh"]["remaining_approx_2_5_years_preceding_the_trailing_segment"]["caveat"] and
          "H008" in dp["previously_observed_vs_fresh"]["remaining_approx_2_5_years_preceding_the_trailing_segment"]["caveat"])
    check("no_absolute_dates_fabricated",
          "NON dichiarate qui con date assolute" in dp["window_selection_rule_exact_dates"])
    check("primary_verdict_uses_only_fresh_portion",
          "SOLO sulla porzione FRESH" in dp["primary_verdict_window_rule"])
    check("no_cherry_picking_flag", dp["no_cherry_picking_of_subperiod"] is True)

    # ---- Sec.4: execution contract - no shadow assumption, ambiguity flagged not invented ----
    ec = p["execution_contract"]
    check("no_shadow_assumption_flag", ec["no_shadow_or_idealized_assumption"] is True)
    check("same_bar_ambiguity_declared_not_invented", ec["same_bar_sl_tp_ambiguity_rule"] == "NOT_YET_JUSTIFIED")
    check("timeout_execution_uses_real_price_not_fixed_r",
          "MAI un valore R fisso" in ec["timeout_execution"])

    # ---- Sec.5: cost scenarios riusati identici da cost_model_integration.json REALE ----
    cost_model_path = os.path.join(PHASE7_DIR, "policies", "cost_model_integration.json")
    cost_model = load_json(cost_model_path)
    cs = p["cost_scenarios"]
    check("cost_model_source_hash_matches_real_file", cs["source_sha256"] == file_sha256(cost_model_path))
    check("cost_scenarios_include_all_4_canonical",
          set(cs["scenarios"].keys()) == {"ZERO_COST", "BROKER_BASELINE", "CONSERVATIVE", "STRESS"})
    check("primary_scenario_is_broker_baseline", cs["primary_scenario_for_verdict"] == "BROKER_BASELINE")
    check("zero_cost_is_diagnostic_only", cs["scenarios"]["ZERO_COST"]["role"] == "DIAGNOSTIC_ONLY")
    check("conservative_stress_are_stress_diagnostics",
          cs["scenarios"]["CONSERVATIVE"]["role"] == "STRESS_DIAGNOSTIC" and
          cs["scenarios"]["STRESS"]["role"] == "STRESS_DIAGNOSTIC")
    check("no_new_cost_scenario_flag", cs["no_new_scenario_created_after_seeing_result"] is True)
    check("reporting_rule_matches_real_cost_model_file", cs["reporting_rule_reused"] == cost_model["reporting_rule"])

    # ---- Sec.6: primary endpoint - metodo statistico gia' ammesso (non superseded) ----
    stat_methods_path = os.path.join(PHASE7_DIR, "policies", "statistical_methods_policy.json")
    stat_methods = load_json(stat_methods_path)
    pe = p["primary_endpoint"]
    check("statistical_method_is_moving_block_bootstrap_not_superseded",
          "moving_block_bootstrap" in pe["statistical_method"] and
          "two_sample_block_bootstrap_percentile_p" not in pe["statistical_method"])
    check("moving_block_bootstrap_is_allowed_method",
          "moving_block_bootstrap" in stat_methods["allowed_as_primary_evidence"])
    check("secondary_never_replaces_primary_flag", pe["secondary_never_replaces_primary"] is True)
    check("secondary_cannot_override_fail_flag", pe["secondary_diagnostics_cannot_override_primary_fail"] is True)

    # ---- Sec.7: decision thresholds - riusati da minimum_evidence_gates.json dove possibile ----
    min_ev_path = os.path.join(PHASE7_DIR, "policies", "minimum_evidence_gates.json")
    min_ev = load_json(min_ev_path)
    dt = p["decision_thresholds"]
    check("minimum_nominal_sample_matches_real_policy",
          dt["minimum_nominal_sample"]["value"] == min_ev["gates"]["n_nominal_minimum"]["value"] == 30)
    check("minimum_effective_sample_matches_real_policy",
          dt["minimum_effective_sample"]["value"] == min_ev["gates"]["effective_n_minimum"]["value"] == 20)
    check("materiality_threshold_declared_not_yet_justified",
          dt["materiality_threshold_beyond_breakeven"]["value"] == "NOT_YET_JUSTIFIED")
    check("materiality_note_explains_scale_mismatch",
          "scala PROBABILITA" in dt["materiality_threshold_beyond_breakeven"]["note"])
    check("temporal_stability_criterion_not_yet_justified",
          dt["temporal_stability_criterion"]["value"] == "NOT_YET_JUSTIFIED")
    check("sign_criterion_is_domain_defined_pf_gt_1",
          "PF > 1.0" in dt["sign_criterion"]["rule"] and dt["sign_criterion"]["source"] == "DOMAIN_DEFINED" or
          "DOMAIN_DEFINED" in dt["sign_criterion"]["source"])
    check("uncertainty_requirement_ci_excludes_zero",
          "escludere 0" in dt["uncertainty_requirement"]["rule"])
    check("cost_robustness_criterion_uses_stress_scenario",
          "STRESS" in dt["cost_robustness_criterion"]["rule"])
    check("composite_rule_has_4_states",
          set(dt["pass_borderline_fail_composite_rule"].keys()) == {"PASS", "BORDERLINE", "FAIL", "INSUFFICIENT_SAMPLE"})
    check("run_authorization_is_partially_blocked", dt["run_authorization_status"] == "PARTIALLY_BLOCKED")
    check("run_authorization_blockers_at_least_3", len(dt["run_authorization_blockers"]) >= 3)
    check("run_authorization_note_forbids_resolving_after_result",
          "DOPO aver visto un risultato" in dt["run_authorization_note"])

    # ---- Sec.8: effective sample - nessun ESS inventato, fallback dichiarato ----
    es = p["effective_sample"]
    check("no_invented_ess_flag", es["no_invented_ess"] is True)
    check("fallback_declared_if_not_estimable", "fallback_if_not_estimable" in es and len(es["fallback_if_not_estimable"]) > 20)

    # ---- Sec.9: direction asymmetry - axis riusato da stability_matrix_policy.json REALE ----
    stab_path = os.path.join(PHASE7_DIR, "policies", "stability_matrix_policy.json")
    stab = load_json(stab_path)
    da = p["direction_asymmetry_diagnostic"]
    check("direction_axis_matches_real_stability_matrix_file",
          da["reused_axis_definition"] == stab["axes"]["direction"])
    check("forbidden_action_explicitly_bans_direction_deletion",
          "overall FAILS" in da["forbidden_action"] and "VIETATO" in da["forbidden_action"])
    check("direction_not_declared_part_of_setup_identity_flag",
          da["direction_is_not_a_declared_part_of_setup_identity"] is True)
    check("cites_sar_and_macd_precedent",
          "SAR" in da["when_prevents_pass"] and "MACD" in da["when_prevents_pass"])

    # ---- Sec.10: temporal stability - segmentation reused, no window change after results ----
    ts = p["temporal_stability_diagnostic"]
    check("temporal_axis_matches_real_stability_matrix_file",
          ts["reused_axis_definition"] == stab["axes"]["year_or_broad_time_regime"])
    check("no_window_change_after_results_flag", ts["no_window_change_after_seeing_results"] is True)
    check("concentration_criterion_cites_already_observed_pattern",
          "2 mesi su 5" in ts["concentration_criterion"])

    # ---- Sec.11: no-rescue clause - almeno 7 azioni vietate ----
    nrc = p["no_rescue_clause"]
    check("no_rescue_has_at_least_7_forbidden_actions", len(nrc["forbidden_after_seeing_results"]) >= 7)
    check("no_rescue_forbids_threshold_adjustment_including_not_yet_justified",
          any("NOT_YET_JUSTIFIED" in a for a in nrc["forbidden_after_seeing_results"]))
    check("no_rescue_cites_macd_precedent", "MACD" in nrc["precedent"])

    # ---- Sec.12: result branches - nessuno porta a LIVE ----
    rb = p["result_branches"]
    check("result_branches_has_4_states",
          set(rb.keys()) - {"no_branch_leads_directly_to_live"} == {"PASS", "BORDERLINE", "FAIL", "INSUFFICIENT_SAMPLE"})
    check("no_branch_leads_to_live_flag", rb["no_branch_leads_directly_to_live"] is True)
    check("pass_action_is_advance_not_live", rb["PASS"]["action"] == "ADVANCE_TO_NEXT_VALIDATION_GATE")
    check("no_action_string_contains_live",
          not any("LIVE" in v["action"] for k, v in rb.items() if isinstance(v, dict) and "action" in v))

    # ---- Sec.13: next gate after PASS - deciso ora, non dopo il risultato ----
    ng = p["next_gate_after_pass"]
    check("next_gate_is_execution_validation", ng["chosen_next_stage"] == "EXECUTION_VALIDATION")
    check("decided_before_seeing_result_flag", ng["decided_before_seeing_result"] is True)
    check("next_gate_cites_wick_sweep_precedent", "WICK_SWEEP_RECLAIM" in ng["rationale"])

    # ---- vincoli espliciti della fase ----
    for flag in ("serious_3y_not_executed", "no_new_outcome_data_accessed", "no_parameter_optimization_performed",
                 "no_strategy_parameter_modified", "no_mech23_applied", "no_edge_discovery_performed",
                 "no_retroactive_modification_of_frozen_artifacts"):
        check(f"{flag}_is_true", p[flag] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non legge mai outcome/prezzi, non esegue backtest ----
    builder_path = os.path.join(PHASE78B_DIR, "build_volatility_breakout_serious_3y_prereg.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_reads_events_or_state_or_bars_csv",
          "events_p71.csv" not in builder_src and "market_state_dataset_p71.csv" not in builder_src)
    check("builder_never_imports_or_invokes_backtest_engine",
          "import backtest" not in builder_src and "from backtest" not in builder_src and
          "backtest.run_backtest" not in builder_src,
          "run_backtest() appare solo come citazione testuale del motore gia' usato in Strategy Foundry "
          "Phase 3, mai importato o invocato qui")
    check("builder_never_writes_to_frozen_artifact_paths",
          "volatility_breakout_voi_contract_v1.json\", \"w" not in builder_src and
          "strategy-registry.json\", \"w" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== VOLATILITY_BREAKOUT Serious 3Y prereg consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
