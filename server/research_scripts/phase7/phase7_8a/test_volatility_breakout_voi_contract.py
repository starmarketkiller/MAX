#!/usr/bin/env python3
"""Phase 7.8A - Value-of-Information Contract: consistency checks.
Verifica che l'evidenza citata coincida con gli artifact canonici reali
(Phase 7.7A/7.7B, Strategy Foundry Phase 3, Failure Memory), che nessun
punteggio numerico VoI sia stato inventato, che GO_LIVE non sia mai
un'azione diretta, che la decision tree sia congelata prima del test, e
che nessun backtest/outcome/MECH-23 sia stato toccato."""
import os
import sys

PHASE78A_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78A_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78A_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc = load_json(os.path.join(PHASE78A_DIR, "volatility_breakout_voi_contract_v1.json"))
    p = doc["payload"]

    check("hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_matches_expected", p["baseline_commit"] == "fdab6e73def3fa50665e2d111a5cd8e7ccda48ce")
    check("candidate_is_volbrk", p["candidate_id"] == "VOLATILITY_BREAKOUT_CONFIRMED")

    # ---- source artifacts NON modificati - hash verificati contro i file reali ----
    lifecycle_doc = load_json(os.path.join(PHASE7_DIR, "phase7_7a", "strategy_lifecycle_registry_v1.json"))
    gate_doc = load_json(os.path.join(PHASE7_DIR, "phase7_7b", "strategy_meta_filter_gate_v1.json"))
    refinement_doc = load_json(os.path.join(PHASE7_DIR, "phase7_7b", "missing_field_semantics_refinement_v1.json"))
    sa = p["source_artifacts"]
    check("lifecycle_hash_matches_real_file", sa["lifecycle_registry"]["canonical_sha256"] == lifecycle_doc["canonical_sha256"])
    check("gate_hash_matches_real_file", sa["gate"]["canonical_sha256"] == gate_doc["canonical_sha256"])
    check("refinement_hash_matches_real_file", sa["refinement"]["canonical_sha256"] == refinement_doc["canonical_sha256"])
    check("modified_in_this_phase_false", sa["modified_in_this_phase"] is False)

    foundry3_path = os.path.join(ROOT, "vault", "01-Trading",
                                  "NEXUS - Strategy Foundry Phase 3 Volatility Breakout Implementation.md")
    failure_memory_path = os.path.join(
        ROOT, "vault", "01-Trading",
        "NEXUS - Failure Memory (Registro Pattern di Fallimento Metodologico) (12-09).md")
    check("foundry3_hash_matches_real_file", sa["strategy_foundry_phase3_vault_note_sha256"] == file_sha256(foundry3_path))
    check("failure_memory_hash_matches_real_file", sa["failure_memory_vault_note_sha256"] == file_sha256(failure_memory_path))

    # ---- evidence state: valori citati devono coincidere con quelli REALI di 7.7A ----
    candidate = lifecycle_doc["payload"]["deep_dive_candidates"]["VOLATILITY_BREAKOUT_CONFIRMED"]
    ces = p["current_evidence_state"]
    check("discovery_result_matches_real_7_7a", ces["discovery_result"] == candidate["evidence_ladder"]["discovery"])
    check("internal_validation_matches_real_7_7a",
          ces["internal_validation_result"] == candidate["evidence_ladder"]["internal_validation"])
    check("full_backtest_matches_real_7_7a",
          ces["full_backtest_engine_result"] == candidate["evidence_ladder"]["full_backtest_engine"])
    check("fast_structural_matches_real_7_7a",
          ces["fast_structural_result"] == candidate["evidence_ladder"]["fast_structural_real_ticks_6mo"])
    check("signal_parity_matches_real_7_7a",
          ces["signal_parity_python_mql5"] == candidate["evidence_ladder"]["signal_parity_python_vs_mql5"])
    check("cost_evidence_flags_zero_cost_full_backtest",
          "costo zero" in ces["cost_evidence"]["full_backtest_engine"])
    check("external_evidence_flags_absence", "Assente" in ces["external_evidence"]["assessment"])

    # ---- gate status corrente citato coincide col gate reale ----
    gate_result = gate_doc["payload"]["gate_results_by_candidate"]["VOLATILITY_BREAKOUT_CONFIRMED"]
    refined_status = refinement_doc["payload"]["per_candidate_field_classifications"][
        "VOLATILITY_BREAKOUT_CONFIRMED"]["refined_structural_status"]
    cmfgs = ces["current_meta_filter_gate_status"]
    check("current_gate_structural_matches_refinement", cmfgs["structural"] == refined_status)
    check("current_gate_readiness_matches_real_gate", cmfgs["readiness"] == gate_result["meta_filter_research_readiness"])
    check("current_gate_passed_matches_real_gate", cmfgs["gate_passed"] == gate_result["meta_filter_ready_gate_passed"])
    check("current_gate_passed_is_false", cmfgs["gate_passed"] is False)

    # ---- decision to be informed: GO_LIVE mai un'azione diretta ----
    dtbi = p["decision_to_be_informed"]
    check("go_live_not_a_possible_action", "GO_LIVE" not in dtbi["possible_actions"] and
          not any("GO LIVE" in v or "GO_LIVE" in v for v in dtbi["possible_actions"].values() if "MAI" not in v))
    check("explicit_exclusion_of_go_live_present", "GO_LIVE non e' mai" in dtbi["explicit_exclusion"])
    check("current_state_is_hold", dtbi["current_state"].startswith("B_HOLD_NEED_MORE_EVIDENCE"))

    # ---- uncertainty axes: almeno le 7 richieste, sign gia' basso, gli altri HIGH ----
    ua = p["uncertainty_axes_addressed_by_serious_3y"]
    required_axes = {"sign_uncertainty", "magnitude_uncertainty", "temporal_stability", "direction_asymmetry",
                      "cost_robustness", "regime_concentration", "sample_adequacy"}
    check("all_7_required_axes_present", required_axes.issubset(set(ua.keys())))
    check("sign_uncertainty_relatively_low", "LOW" in ua["sign_uncertainty"]["current_level"])
    for axis in ("magnitude_uncertainty", "temporal_stability", "direction_asymmetry", "cost_robustness",
                 "regime_concentration", "sample_adequacy"):
        check(f"{axis}_is_high", ua[axis]["current_level"] == "HIGH")

    # ---- alternative experiments: almeno le 6 richieste, nessun rescue post-hoc silenzioso ----
    alt = p["alternative_experiments"]
    required_alts = {"SERIOUS_3Y_FULL_TEST", "LONGER_CHEAPER_BAR_LEVEL_VALIDATION", "CROSS_FEED_VALIDATION",
                      "ADDITIONAL_RECENT_HOLDOUT", "DIRECTION_SPECIFIC_DIAGNOSTIC", "NO_TEST_WAIT_FOR_MORE_DATA"}
    check("all_6_required_alternatives_present", required_alts.issubset(set(alt.keys())))
    check("direction_specific_diagnostic_warns_against_post_hoc_rescue",
          "rescue post-hoc" in alt["DIRECTION_SPECIFIC_DIAGNOSTIC"]["warning"])

    # ---- cost matrix: solo valori ordinali LOW/MEDIUM/HIGH (o eccezione dichiarata esplicitamente) ----
    cost = p["cost_of_experiment"]
    ordinal_values = {"LOW", "MEDIUM", "HIGH", "LOW_BUT_INDEFINITE_TIME", "INDEFINITE_NOT_ORDINAL",
                      "LOW-MEDIUM"}
    for alt_name, c in cost.items():
        for field in ("compute_cost", "data_cost", "engineering_cost", "contamination_risk",
                      "researcher_degrees_of_freedom_risk"):
            check(f"{alt_name}_{field}_is_ordinal_not_numeric",
                  c[field] in ordinal_values or c[field].replace("-", "").replace("_", "").isalpha())
    check("no_test_wait_elapsed_time_flagged_non_ordinal",
          cost["NO_TEST_WAIT_FOR_MORE_DATA"]["elapsed_time"] == "INDEFINITE_NOT_ORDINAL")

    # ---- decision tree: 4 esiti congelati, action mapping corretto, mai promozione automatica su unstable ----
    dt = p["decision_tree_frozen_before_test"]
    check("decision_tree_has_4_outcomes",
          set(dt.keys()) == {"strong_negative", "null_inconclusive", "positive_but_unstable", "positive_and_robust"})
    check("strong_negative_maps_to_abandon", dt["strong_negative"]["action"] == "A_ABANDON_ARCHIVE")
    check("null_inconclusive_maps_to_hold", dt["null_inconclusive"]["action"] == "B_HOLD_NEED_MORE_EVIDENCE")
    check("positive_but_unstable_maps_to_hold_not_advance",
          dt["positive_but_unstable"]["action"] == "B_HOLD_NEED_MORE_EVIDENCE")
    check("positive_and_robust_maps_to_advance", dt["positive_and_robust"]["action"] == "C_ADVANCE_TO_NEXT_VALIDATION_GATE")
    check("positive_and_robust_note_excludes_go_live", "GO_LIVE" in dt["positive_and_robust"]["note"])

    # ---- formal VoI: nessuna probabilita' inventata, verdetto esplicito ----
    fv = p["formal_voi"]
    check("numeric_voi_not_identified", fv["verdict"] == "NUMERIC_VOI_NOT_IDENTIFIED")
    check("no_invented_pass_probability_flag", fv["no_invented_pass_probability"] is True)
    check("missing_prerequisites_at_least_2", len(fv["missing_prerequisites"]) >= 2)

    # ---- utility matrix: nessun punteggio numerico aggregato, solo ordinale con rationale ----
    um = p["expected_information_utility_matrix"]
    check("no_arbitrary_numeric_score_flag", um["no_arbitrary_numeric_score_computed"] is True)
    required_criteria = {"decision_relevance", "uncertainty_reduction", "independence_of_evidence",
                          "contamination_risk", "cost", "downstream_unlock_value"}
    for alt_name in required_alts:
        entry = um[alt_name]
        check(f"{alt_name}_utility_has_all_6_criteria_and_rationale",
              required_criteria.issubset(set(entry.keys())) and len(entry.get("rationale", "")) > 20)

    # ---- stopping logic: almeno 4 condizioni, include cost_robustness_failure citando WICK_SWEEP_RECLAIM ----
    sl = p["stopping_logic"]["stop_conditions"]
    check("at_least_4_stop_conditions", len(sl) >= 4)
    cost_stop = next((c for c in sl if c["condition"] == "COST_ROBUSTNESS_FAILURE"), None)
    check("cost_robustness_failure_cites_wick_sweep_precedent",
          cost_stop is not None and "WICK_SWEEP_RECLAIM" in cost_stop["description"] and "5.80" in cost_stop["description"])

    # ---- verdetto finale: uno dei 3 valori enumerati, mai basato su probabilita' inventata ----
    v = p["serious_3y_eligibility_verdict"]
    check("verdict_is_one_of_3_valid_enums",
          v["value"] in ("SERIOUS_3Y_IS_NEXT_BEST_EXPERIMENT", "ALTERNATIVE_EXPERIMENT_HAS_HIGHER_INFORMATION_VALUE",
                          "INSUFFICIENT_INFORMATION_TO_PRIORITIZE"))
    check("verdict_not_based_on_invented_probability_flag", v["not_based_on_invented_probability"] is True)
    check("verdict_has_explicit_budget_caveat", "budget" in v["explicit_caveat"].lower())

    # ---- future numeric VoI prerequisites: almeno le 6 richieste ----
    fnvp = p["future_numeric_voi_prerequisites"]
    required_prereqs = {"prior_edge_distribution", "candidate_base_rate", "cost_of_false_promotion",
                        "cost_of_false_rejection", "compute_cost", "capital_opportunity_cost"}
    check("all_6_future_prerequisites_present", required_prereqs.issubset(set(fnvp.keys())))

    # ---- vincoli espliciti della fase ----
    for flag in ("no_serious_3y_executed", "no_new_outcome_data_accessed", "no_parameter_optimization_performed",
                 "no_mech23_applied", "no_edge_discovery_performed", "no_retroactive_modification_of_frozen_artifacts"):
        check(f"{flag}_is_true", p[flag] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non legge mai outcome/prezzi, non esegue backtest, non riscrive artifact frozen ----
    builder_path = os.path.join(PHASE78A_DIR, "build_volatility_breakout_voi_contract.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_reads_events_or_state_or_bars_csv",
          "events_p71.csv" not in builder_src and "market_state_dataset_p71.csv" not in builder_src)
    check("builder_never_calls_run_backtest", "run_backtest(" not in builder_src)
    check("builder_never_writes_to_frozen_artifact_paths",
          "strategy_lifecycle_registry_v1.json\", \"w" not in builder_src and
          "strategy_meta_filter_gate_v1.json\", \"w" not in builder_src and
          "missing_field_semantics_refinement_v1.json\", \"w" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== VOLATILITY_BREAKOUT_CONFIRMED VoI contract consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
