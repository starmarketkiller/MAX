#!/usr/bin/env python3
"""Phase 7.8F - Final Execution Config Audit: consistency checks."""
import os
import subprocess
import sys

PHASE78F_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78F_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78F_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc = load_json(os.path.join(PHASE78F_DIR, "volatility_breakout_execution_config_audit_v1.json"))
    p = doc["payload"]

    check("hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_matches_expected", p["baseline_commit"] == "9b75ceeee1e49ef1e3efd2e5127bdc5bc50e7f1a")
    check("candidate_is_volbrk", p["candidate_id"] == "VOLATILITY_BREAKOUT_CONFIRMED")

    # ---- 7.8E non modificato ----
    prior_path = os.path.join(PHASE7_DIR, "phase7_8e", "volatility_breakout_final_data_freeze_v1.json")
    prior_doc = load_json(prior_path)
    sa = p["source_artifact_untouched"]
    check("prior_7_8e_hash_matches_real_file", sa["canonical_sha256"] == prior_doc["canonical_sha256"])
    check("prior_7_8e_modified_flag_false", sa["modified_in_this_phase"] is False)

    # ---- Leverage audit ----
    la = p["leverage_audit"]
    check("leverage_frozen_was_100", la["frozen_value_in_7_8e"] == 100)
    check("leverage_corrected_to_500", la["corrected_value"] == 500)
    check("leverage_sources_include_10_09_authoritative",
          any("10-09" in s.get("date", "") and s.get("authoritative") for s in la["sources_examined"]))
    check("leverage_sources_include_sar_precedent_non_authoritative",
          any("sar_dukascopy" in s["source"] and not s.get("authoritative", True) for s in la["sources_examined"]))
    research_mode_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_ResearchMode.mqh")
    check("leverage_code_verification_file_exists", os.path.isfile(research_mode_file))
    with open(research_mode_file, encoding="utf-8") as f:
        rm_src = f.read()
    check("leverage_fixed_lot_claim_verifiable_in_real_code",
          "lots = InpResearchFixedLot;" in rm_src and la["code_verification"]["fixed_lot_confirmed_in_source"] is True)

    # ---- Expert path bug ----
    epb = p["expert_path_bug_discovery"]
    log_path = os.path.join(ROOT, epb["log_evidence_file"])
    check("expert_bug_log_file_exists", os.path.isfile(log_path))
    check("expert_bug_log_hash_matches_real_file", file_sha256(log_path) == epb["log_evidence_sha256"])
    check("expert_bug_frozen_value_matches_7_8e_real_config",
          epb["frozen_config_7_8e_value"].replace("\\\\", "\\") in
          prior_doc["payload"]["tester_execution_config_frozen_not_launched"]["raw_text"])
    check("expert_bug_corrected_no_double_prefix", "Experts\\Experts" not in epb["corrected_value"])

    # ---- Timestamp semantics ----
    ts = p["timestamp_semantics"]
    probe_a_path = os.path.join(ROOT, ts["probe_A_fromdate_boundary"]["raw_output_file"])
    probe_b_path = os.path.join(ROOT, ts["probe_B_todate_boundary"]["raw_output_file"])
    check("probe_A_exists_and_hash_matches",
          os.path.isfile(probe_a_path) and file_sha256(probe_a_path) == ts["probe_A_fromdate_boundary"]["raw_output_sha256"])
    check("probe_B_exists_and_hash_matches",
          os.path.isfile(probe_b_path) and file_sha256(probe_b_path) == ts["probe_B_todate_boundary"]["raw_output_sha256"])
    check("probe_B_used_pure_weekday_range_no_weekend",
          "2024.01.08" in ts["probe_B_todate_boundary"]["ini_config"]
          and "2024.01.10" in ts["probe_B_todate_boundary"]["ini_config"])
    check("rule_fromdate_inclusive", ts["rule_determined"]["from_date_inclusive_from_00_00_00"] is True)
    check("rule_todate_exclusive", ts["rule_determined"]["to_date_exclusive_at_00_00_00"] is True)
    check("rule_measured_not_assumed", ts["rule_determined"]["measured_not_assumed"] is True)

    ab = ts["applied_to_frozen_boundaries"]
    real_tw = prior_doc["payload"]["temporal_identity_recheck"]["PRIMARY_FRESH_VERDICT_WINDOW"]
    check("end_boundary_frozen_value_matches_real_7_8e", ab["end_boundary"]["frozen_value"] == real_tw["end"])
    check("start_boundary_frozen_value_matches_real_7_8e", ab["start_boundary"]["frozen_value"] == real_tw["start"])
    check("end_boundary_rule_is_exact_tester_window", ab["end_boundary"]["handling_rule"] == "EXACT_TESTER_WINDOW")
    check("start_boundary_rule_is_superset_filter",
          ab["start_boundary"]["handling_rule"] == "RUN_SUPERSET_AND_FILTER_EXACT_WINDOW")
    check("start_boundary_filter_cites_exact_frozen_timestamp",
          real_tw["start"][11:] in ab["start_boundary"]["filter_rule_frozen_now_before_seeing_results"]
          or "12:06:50" in ab["start_boundary"]["filter_rule_frozen_now_before_seeing_results"])
    check("no_boundary_value_changed_vs_7_8e",
          ab["start_boundary"]["frozen_value"] == real_tw["start"]
          and ab["end_boundary"]["frozen_value"] == real_tw["end"])
    check("data_drift_observation_does_not_change_boundary",
          ts["data_drift_side_observation"]["not_a_boundary_change"] is True)

    # ---- Hidden time dependency ----
    htd = p["hidden_time_dependency_check"]
    check("signal_check_no_time_dependency", htd["signal_code_check"]["has_time_or_session_dependency"] is False)
    check("execution_path_calls_open_trade_directly",
          htd["execution_gate_check"]["real_execution_path_used"]["profile_path_calls_open_trade_directly"] is True)
    check("execution_path_skips_session_gate",
          htd["execution_gate_check"]["real_execution_path_used"]["profile_path_skips_session_gate"] is True)
    check("conclusion_no_timezone_dependent_signal_logic",
          htd["conclusion"] == "NO_TIMEZONE_DEPENDENT_SIGNAL_LOGIC")

    # ---- Tester config finale ----
    tc = p["tester_execution_config_final"]
    check("tester_config_not_launched", tc["not_launched"] is True)
    check("tester_config_expert_no_prefix", "Expert=NEXUS_EA_v2" in tc["raw_text"])
    check("tester_config_leverage_500", "Leverage=500" in tc["raw_text"])
    check("tester_config_use_strategy_profiles_explicit", "InpUseStrategyProfiles=true" in tc["raw_text"])
    reg = load_json(os.path.join(ROOT, "contracts", "strategy-registry.json"))
    reg_entry = next(s for s in reg["strategies"] if s["strategy_id"] == "VOLATILITY_BREAKOUT_CONFIRMED")
    check("tester_config_selector_matches_registry",
          f"InpStrategySelector={reg_entry['selector_index']}" in tc["raw_text"])
    check("tester_config_hash_matches_recompute",
          tc["sha256"] == canonical_sha256({"tester_config_text": tc["raw_text"]}))
    check("tester_config_hash_matches_seal", tc["sha256"] == p["final_seal"]["tester_config_sha256"])
    check("tester_config_dates_unchanged_vs_7_8e",
          tc["raw_text"].count(real_tw["start"][:10].replace("-", ".")) >= 1
          and tc["raw_text"].count(real_tw["end"][:10].replace("-", ".")) >= 1)

    # ---- Final seal / verdict ----
    fs = p["final_seal"]
    check("seal_previous_manifest_matches_real_7_8e", fs["previous_manifest_hash_7_8e"] == prior_doc["canonical_sha256"])
    check("seal_prereg_hash_matches_7_8e_chain", fs["prereg_hash"] == prior_doc["payload"]["final_seal"]["prereg_hash"])
    check("seal_reverification_requirement_carried_forward",
          fs["data_reverification_required_before_run"]["required"] is True)
    sv = p["seal_verification"]
    check("seal_verification_all_true", all(sv.values()))
    fv = p["final_verdict"]
    check("final_verdict_ready_for_run", fv["value"] == "EXECUTION_CONFIG_VERIFIED_READY_FOR_RUN")
    check("final_verdict_still_not_executed", fv["serious_validation_still_not_executed"] is True)

    # ---- esegue il verificatore indipendente ----
    verify_result = subprocess.run(
        [sys.executable, os.path.join(PHASE78F_DIR, "verify_volatility_breakout_execution_config_audit.py")],
        capture_output=True, text=True,
    )
    check("independent_verify_exits_0", verify_result.returncode == 0)
    check("independent_verify_agrees_on_verdict",
          "EXECUTION_CONFIG_VERIFIED_READY_FOR_RUN" in verify_result.stdout)
    check("independent_verify_confirms_no_execution",
          "SERIOUS_VALIDATION_NOT_EXECUTED" in verify_result.stdout)

    # ---- vincoli espliciti della fase ----
    for flag in ("serious_validation_not_executed", "no_strategy_outcome_accessed", "no_trade_results_generated",
                 "no_pf_expectancy_or_winrate_computed", "no_edge_discovery_performed",
                 "no_retroactive_modification_of_frozen_artifacts"):
        check(f"{flag}_is_true", p[flag] is True)

    # ---- verifica statica: il builder non esegue mai backtest, non lancia il terminale, non riscrive 7.8E ----
    builder_path = os.path.join(PHASE78F_DIR, "build_volatility_breakout_execution_config_audit.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_imports_backtest_engine", "import backtest" not in builder_src)
    check("builder_never_launches_terminal", "Start-Process" not in builder_src and "terminal64" not in builder_src)
    check("builder_never_writes_to_7_8e_frozen_path",
          "volatility_breakout_final_data_freeze_v1.json\", \"w" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== VOLATILITY_BREAKOUT Execution Config Audit consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
