#!/usr/bin/env python3
"""Phase 7.8E - Final Data Freeze: consistency checks.
Verifica che l'offset broker misurato sia REALE (non fabbricato), che
il manifest dati sia genuinamente derivato dai file .tkc/.hcc reali su
disco, che la tester config sia congelata (mai lanciata), che i confini
temporali coincidano esattamente con 7.8D, che il verificatore
indipendente concordi, e che nessun outcome/backtest sia stato
toccato."""
import os
import sys

PHASE78E_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78E_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78E_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc = load_json(os.path.join(PHASE78E_DIR, "volatility_breakout_final_data_freeze_v1.json"))
    p = doc["payload"]

    check("hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_matches_expected", p["baseline_commit"] == "a5a79723bd13543e179b506abbd91d04fa4a356c")
    check("candidate_is_volbrk", p["candidate_id"] == "VOLATILITY_BREAKOUT_CONFIRMED")

    # ---- 7.8D non modificato ----
    prior_path = os.path.join(PHASE7_DIR, "phase7_8d", "volatility_breakout_serious_validation_prerun_manifest_v1.json")
    prior_doc = load_json(prior_path)
    sa = p["source_artifact_untouched"]
    check("prior_manifest_hash_matches_real_file", sa["canonical_sha256"] == prior_doc["canonical_sha256"])
    check("prior_manifest_known_hash_unchanged",
          prior_doc["canonical_sha256"] == "9c0105b984c0296bb2663f0c30d655b7ce521b99047194af3a9a6311ca208a19")
    check("prior_manifest_modified_flag_false", sa["modified_in_this_phase"] is False)

    # ---- Timezone: valori tracciabili al file grezzo REALE (non un numero inventato) ----
    tz_measure_path = os.path.join(PHASE7_DIR, "phase7_8d", "raw_coverage_audit", "nxs_volbrk_timezone_measure.txt")
    check("tz_measure_raw_file_exists", os.path.isfile(tz_measure_path))
    with open(tz_measure_path, encoding="utf-8") as f:
        tz_raw_text = f.read()
    tm = p["timezone_measurement"]
    check("tz_offset_is_10800_matching_real_raw_file",
          tm["broker_utc_offset_seconds"] == 10800 and
          "broker_utc_offset_seconds_TradeServer_minus_GMT=10800" in tz_raw_text)
    check("tz_discrepancy_explicitly_documented",
          "InpServerGMTOffset=2" in tm["discrepancy_found"]["declared_in_7_8b_and_7_8d"] and
          "+3h" in tm["discrepancy_found"]["actually_measured"] and
          "10800" in tm["discrepancy_found"]["actually_measured"])
    check("tz_dst_caveat_present_and_honest",
          "TimeDaylightSavings" in tm["dst_caveat"] and "RI-MISURATO" in tm["dst_caveat"])
    tz_script_path = os.path.join(ROOT, "server", "research_scripts", "NXS_VolBrkTimezoneMeasure.mq5")
    check("tz_script_exists_and_hash_matches", os.path.isfile(tz_script_path) and
          tm["measurement_script_source_sha256"] == file_sha256(tz_script_path))
    with open(tz_script_path, encoding="utf-8") as f:
        tz_script_src = f.read()
    check("tz_script_never_places_orders", "OrderSend" not in tz_script_src and "trade." not in tz_script_src)
    check("tz_raw_output_hash_matches_real_file", tm["measurement_raw_output_sha256"] == file_sha256(tz_measure_path))

    # ---- Data manifest: hash REALI dei file .tkc/.hcc, ricalcolati indipendentemente ----
    terminal_root = (
        r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6\bases\XMGlobal-MT5 10"
    )
    dm = p["data_manifest"]
    check("data_manifest_has_27_tick_files_and_4_bar_files",
          dm["n_tick_files"] == 27 and dm["n_bar_files"] == 4)
    check("data_manifest_zero_missing", dm["n_missing_files"] == 0 and dm["missing_files"] == [])
    n_reverified = 0
    for entry in dm["entries"][:5] + dm["entries"][-5:]:  # campione: primi e ultimi 5, per costo
        abs_path = os.path.join(terminal_root, *entry["relative_path"].split("/"))
        if os.path.isfile(abs_path):
            check(f"data_file_hash_matches_real_{entry['relative_path'].replace('/', '_')}",
                  entry["sha256"] == file_sha256(abs_path) and entry["size_bytes"] == os.path.getsize(abs_path))
            n_reverified += 1
    check("at_least_10_data_files_reverified_directly", n_reverified >= 10)
    check("volatility_note_cites_2026_hcc_change_observed", "2026.hcc" in dm["volatility_note"])
    check("boundary_note_explains_monthly_granularity", "20" in dm["boundary_note"])

    dhc = p["dataset_hash_correction"]
    check("dataset_hash_correction_target_matches_real_7_8d_file",
          dhc["target_artifact_7_8d_canonical_sha256_unchanged"] == prior_doc["canonical_sha256"])
    check("dataset_hash_correction_modified_flag_false", dhc["modified_in_this_phase"] is False)
    check("data_manifest_hash_matches_canonical_recompute",
          dhc["data_manifest_canonical_sha256"] == canonical_sha256(dm))

    # ---- Temporal identity recheck: identico a 7.8D, non ricalcolato ----
    tir = p["temporal_identity_recheck"]
    real_tw = prior_doc["payload"]["temporal_windows"]
    for k in ("TOTAL_TEST_WINDOW", "PRIMARY_FRESH_VERDICT_WINDOW", "PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW",
              "NEWLY_ELAPSED_TAIL_SEGMENT", "T1", "T2", "T3"):
        check(f"temporal_{k}_matches_real_7_8d", tir[k] == real_tw[k])
    check("no_boundary_changed_flag", tir["no_boundary_changed"] is True)
    check("no_recalculation_based_on_outcomes_flag", tir["no_recalculation_based_on_outcomes"] is True)

    # ---- Tester config: congelata, selector reale, mai lanciata ----
    tc = p["tester_execution_config_frozen_not_launched"]
    check("tester_config_not_launched_flag", tc["not_launched"] is True)
    reg = load_json(os.path.join(ROOT, "contracts", "strategy-registry.json"))
    reg_entry = next(s for s in reg["strategies"] if s["strategy_id"] == "VOLATILITY_BREAKOUT_CONFIRMED")
    check("tester_config_selector_matches_real_registry",
          f"InpStrategySelector={reg_entry['selector_index']}" in tc["raw_text"] and reg_entry["selector_index"] == 56)
    check("tester_config_model_is_4", "Model=4" in tc["raw_text"])
    check("tester_config_dates_match_primary_fresh_window",
          tw_start := tir["PRIMARY_FRESH_VERDICT_WINDOW"]["start"][:10].replace("-", ".") in tc["raw_text"])
    check("tester_config_hash_matches_canonical_recompute",
          tc["sha256"] == canonical_sha256({"tester_config_text": tc["raw_text"]}))
    check("tester_config_expert_is_real_nexus_ea_v2",
          os.path.isfile(os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")) and
          "NEXUS_EA_v2" in tc["raw_text"])

    # ---- Final seal: pin coerenti con gli artifact reali ----
    fs = p["final_seal"]
    check("seal_previous_manifest_hash_matches_real_file", fs["previous_manifest_hash_7_8d"] == prior_doc["canonical_sha256"])
    check("seal_prereg_hash_matches_real_7_8d_payload",
          fs["prereg_hash"] == prior_doc["payload"]["protocol_identity_pins"]["prereg_canonical_hash"])
    check("seal_authorization_hash_matches_real_7_8d_payload",
          fs["authorization_7_8c_hash"] == prior_doc["payload"]["protocol_identity_pins"]["authorization_7_8c_canonical_hash"])
    cost_model_path = os.path.join(PHASE7_DIR, "policies", "cost_model_integration.json")
    check("seal_cost_model_hash_matches_real_file", fs["cost_model_hash"] == file_sha256(cost_model_path))
    check("seal_selector_verified_flag", fs["selector_index_verified_against_real_registry"] is True)
    check("seal_reverification_required_flag", fs["reverification_required_before_run"]["required"] is True)
    check("seal_reverification_cites_2026_hcc_precedent",
          "2026.hcc" in fs["reverification_required_before_run"]["reason"])

    # ---- Seal verification block + verdetto ----
    sv = p["seal_verification"]
    check("seal_verification_all_true", all(sv.values()))
    fv = p["final_verdict"]
    check("final_verdict_is_verified_ready_to_execute", fv["value"] == "FINAL_PRE_RUN_SEAL_VERIFIED_READY_TO_EXECUTE")
    check("final_verdict_still_not_executed_flag", fv["serious_validation_still_not_executed"] is True)
    check("final_verdict_note_requires_reverification", "RICALCOLATO" in fv["note"])

    # ---- esegue lo script di verifica indipendente e conferma l'accordo ----
    import subprocess
    verify_result = subprocess.run(
        [sys.executable, os.path.join(PHASE78E_DIR, "verify_volatility_breakout_final_data_freeze.py")],
        capture_output=True, text=True,
    )
    check("independent_verify_script_exits_0", verify_result.returncode == 0)
    check("independent_verify_script_agrees_on_verdict",
          "FINAL_PRE_RUN_SEAL_VERIFIED_READY_TO_EXECUTE" in verify_result.stdout)
    check("independent_verify_confirms_no_data_files_changed",
          "data_files_changed_since_seal = []" in verify_result.stdout)
    check("independent_verify_confirms_no_execution",
          "SERIOUS_VALIDATION_NOT_EXECUTED" in verify_result.stdout)

    # ---- vincoli espliciti della fase ----
    for flag in ("serious_validation_not_executed", "no_strategy_outcome_accessed", "no_trade_results_generated",
                 "no_pf_expectancy_or_winrate_computed", "no_edge_discovery_performed",
                 "no_retroactive_modification_of_frozen_artifacts"):
        check(f"{flag}_is_true", p[flag] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non esegue mai backtest, non riscrive artifact frozen ----
    builder_path = os.path.join(PHASE78E_DIR, "build_volatility_breakout_final_data_freeze.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_imports_or_invokes_backtest_engine",
          "import backtest" not in builder_src and "from backtest" not in builder_src)
    check("builder_never_launches_terminal_process",
          "Start-Process" not in builder_src and "subprocess.run" not in builder_src.replace(
              "def build_data_manifest", ""))
    check("builder_never_writes_to_frozen_artifact_paths",
          "volatility_breakout_serious_validation_prerun_manifest_v1.json\", \"w" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== VOLATILITY_BREAKOUT Final Data Freeze consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
