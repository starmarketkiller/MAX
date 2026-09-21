#!/usr/bin/env python3
"""Phase 7.8D - PRE-RUN Manifest: consistency checks.
Verifica che ogni valore nel manifest sia REALMENTE tracciabile ai file
grezzi prodotti dal run MT5 read-only (raw_coverage_audit/), che nessun
valore sia stato fabbricato, che la correzione della fase precedente
(PRE_RUN_SEAL_BLOCKED_NO_DATA_ACCESS) sia annotata senza modificare
l'artifact originale, che il verify script indipendente concordi col
builder, e che nessun outcome/backtest sia stato toccato."""
import datetime
import os
import sys

PHASE78D_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78D_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78D_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc = load_json(os.path.join(PHASE78D_DIR, "volatility_breakout_serious_validation_prerun_manifest_v1.json"))
    p = doc["payload"]

    check("hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("candidate_is_volbrk", p["candidate_id"] == "VOLATILITY_BREAKOUT_CONFIRMED")

    # ---- baseline commit must be a real commit that exists in this repo's history ----
    import subprocess
    log = subprocess.run(["git", "cat-file", "-t", p["baseline_commit"]], cwd=ROOT,
                          capture_output=True, text=True)
    check("baseline_commit_is_a_real_existing_git_object", log.stdout.strip() == "commit")

    # ---- correzione della fase precedente: annotata, non modificata ----
    prior_path = os.path.join(PHASE78D_DIR, "volatility_breakout_prerun_seal_status_v1.json")
    prior_doc = load_json(prior_path)
    corr = p["correction_of_prior_blocked_status"]
    check("prior_status_hash_matches_real_file", corr["target_artifact_canonical_sha256_unchanged"] == prior_doc["canonical_sha256"])
    check("prior_status_known_hash_unchanged",
          prior_doc["canonical_sha256"] == "9f68eea0ef20999a8e6d3025ea9237831cac6f1c3fff68e43ea6efe4381c1702")
    check("prior_status_modified_flag_false", corr["modified_in_this_phase"] is False)

    # ---- raw coverage audit files exist and hashes match exactly ----
    raw_csv = os.path.join(PHASE78D_DIR, "raw_coverage_audit", "nxs_volbrk_prerun_coverage.csv")
    raw_summary = os.path.join(PHASE78D_DIR, "raw_coverage_audit", "nxs_volbrk_prerun_summary.txt")
    raw_done = os.path.join(PHASE78D_DIR, "raw_coverage_audit", "nxs_volbrk_prerun_done.txt")
    check("raw_csv_exists", os.path.isfile(raw_csv))
    check("raw_summary_exists", os.path.isfile(raw_summary))
    check("raw_done_marker_exists", os.path.isfile(raw_done))
    hr = p["dataset_hash_representation"]
    check("coverage_csv_hash_matches_real_file", hr["coverage_csv_sha256"] == file_sha256(raw_csv))
    check("coverage_summary_hash_matches_real_file", hr["coverage_summary_sha256"] == file_sha256(raw_summary))
    check("coverage_done_hash_matches_real_file", hr["coverage_done_marker_sha256"] == file_sha256(raw_done))

    # ---- audit script source exists, hash matches, and is genuinely read-only (no trading calls) ----
    script_path = os.path.join(ROOT, "server", "research_scripts", "NXS_VolBrkPrerunCoverageAudit.mq5")
    check("audit_script_exists_and_hash_matches", os.path.isfile(script_path) and
          hr["audit_script_source_sha256"] == file_sha256(script_path))
    with open(script_path, encoding="utf-8") as f:
        script_src = f.read()
    check("audit_script_never_places_orders",
          "OrderSend" not in script_src and "trade.Buy" not in script_src and "trade.Sell" not in script_src)
    check("audit_script_touches_no_nexus_v1_includes", "NEXUS_v1" not in script_src)

    # ---- real tick coverage finding: values traceable to the real summary file ----
    with open(raw_summary, encoding="utf-8") as f:
        summary_text = f.read()
    di = p["dataset_identity"]
    check("first_tick_matches_real_summary_file", di["first_available_timestamp_ticks"] in summary_text)
    check("last_tick_matches_real_summary_file", di["last_available_timestamp_ticks"] in summary_text)
    check("first_h4_bar_matches_real_summary_file", di["first_available_timestamp_h4_bars"] in summary_text)
    check("account_login_matches_real_summary_file", di["account_login"] in summary_text)
    check("broker_server_matches_real_summary_file", di["broker_server"] in summary_text)
    check("trade_mode_is_demo_matches_real_file", di["account_trade_mode"] == "DEMO" and "trade_mode=DEMO" in summary_text)

    # ---- monthly probe rows: n and classification match the real CSV exactly ----
    with open(raw_csv, encoding="utf-8") as f:
        csv_lines = [ln.strip() for ln in f if ln.strip()]
    gold_rows = [ln for ln in csv_lines if ln.startswith("XMGlobal-MT5 10,345277936,DEMO,GOLD,")]
    tcs = p["real_tick_coverage_by_subperiod"]
    check("n_monthly_probes_matches_real_csv_row_count", len(tcs) == len(gold_rows) == 37)
    real_n_resolvable = sum(1 for ln in gold_rows if int(ln.split(",")[6]) > 0)
    check("n_real_tick_resolvable_matches_real_csv",
          p["real_tick_coverage_summary"]["n_real_tick_resolvable"] == real_n_resolvable == 33)

    # ---- temporal windows: internally consistent (re-verified independently, not trusting payload's own claim) ----
    tw = p["temporal_windows"]
    total_start = datetime.datetime.fromisoformat(tw["TOTAL_TEST_WINDOW"]["start"])
    total_end = datetime.datetime.fromisoformat(tw["TOTAL_TEST_WINDOW"]["end"])
    fresh_start = datetime.datetime.fromisoformat(tw["PRIMARY_FRESH_VERDICT_WINDOW"]["start"])
    fresh_end = datetime.datetime.fromisoformat(tw["PRIMARY_FRESH_VERDICT_WINDOW"]["end"])
    obs_start = datetime.datetime.fromisoformat(tw["PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW"]["start"])
    obs_end = datetime.datetime.fromisoformat(tw["PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW"]["end"])
    tail_start = datetime.datetime.fromisoformat(tw["NEWLY_ELAPSED_TAIL_SEGMENT"]["start"])
    tail_end = datetime.datetime.fromisoformat(tw["NEWLY_ELAPSED_TAIL_SEGMENT"]["end"])
    check("total_window_equals_fresh_start_to_tail_end", total_start == fresh_start and total_end == tail_end)
    check("fresh_end_equals_observed_start", fresh_end == obs_start)
    check("observed_end_equals_tail_start", obs_end == tail_start)
    check("previously_observed_window_matches_strategy_foundry_phase3_dates",
          obs_start == datetime.datetime(2026, 3, 1) and obs_end == datetime.datetime(2026, 9, 1))
    check("fresh_start_equals_first_real_tick", fresh_start.strftime("%Y.%m.%d %H:%M:%S") ==
          di["first_available_timestamp_ticks"])
    check("total_end_equals_last_real_tick", total_end.strftime("%Y.%m.%d %H:%M:%S") ==
          di["last_available_timestamp_ticks"])
    check("newly_elapsed_tail_excluded_from_primary_flag",
          tw["NEWLY_ELAPSED_TAIL_SEGMENT"]["excluded_from_primary_verdict"] is True)

    # ---- T1/T2/T3 partition ----
    t1s, t1e = (datetime.datetime.fromisoformat(tw["T1"]["start"]), datetime.datetime.fromisoformat(tw["T1"]["end"]))
    t2s, t2e = (datetime.datetime.fromisoformat(tw["T2"]["start"]), datetime.datetime.fromisoformat(tw["T2"]["end"]))
    t3s, t3e = (datetime.datetime.fromisoformat(tw["T3"]["start"]), datetime.datetime.fromisoformat(tw["T3"]["end"]))
    check("t1_starts_at_fresh_start", t1s == fresh_start)
    check("t3_ends_at_fresh_end", t3e == fresh_end)
    check("t1_t2_t3_contiguous_no_gaps_no_overlap", t1e == t2s and t2e == t3s)
    durations = [(t1e - t1s).days, (t2e - t2s).days, (t3e - t3s).days]
    check("t1_t2_t3_durations_approximately_equal", max(durations) - min(durations) <= 1, str(durations))
    check("t1_t2_t3_never_called_year_1_2_3_in_this_payload",
          "\"Year 1\"" not in str(p) and "'Year 1'" not in str(p))

    # ---- tick model correction: annotates 7.8B without modifying it ----
    prereg_doc = load_json(os.path.join(PHASE7_DIR, "phase7_8b", "volatility_breakout_serious_3y_prereg_v1.json"))
    tmc = p["tick_model_correction"]
    check("tick_model_target_hash_matches_real_7_8b_file", tmc["target_artifact_7_8b_canonical_sha256_unchanged"] == prereg_doc["canonical_sha256"])
    check("tick_model_correction_is_model_4", "Model=4" in tmc["actual_established_project_convention"])

    # ---- protocol identity pins match real frozen artifacts ----
    auth_doc = load_json(os.path.join(PHASE7_DIR, "phase7_8c", "volatility_breakout_serious_3y_run_authorization_v1.json"))
    pp = p["protocol_identity_pins"]
    check("pin_prereg_hash_matches_real_file", pp["prereg_canonical_hash"] == prereg_doc["canonical_sha256"])
    check("pin_authorization_hash_matches_real_file", pp["authorization_7_8c_canonical_hash"] == auth_doc["canonical_sha256"])
    cost_model_path = os.path.join(PHASE7_DIR, "policies", "cost_model_integration.json")
    check("pin_cost_model_hash_matches_real_file", pp["cost_model_hash"] == file_sha256(cost_model_path))
    check("pin_strategy_commit_is_f035d30", pp["strategy_frozen_commit"] == "f035d30")

    # ---- seal_verification block: all true, and cross-checked against the independent verify script ----
    sv = p["seal_verification"]
    check("seal_all_checks_passed_flag", sv["all_checks_passed"] is True)
    for k in ("all_required_fields_populated", "date_ordering_valid", "fresh_and_observed_non_overlapping",
              "t1_t2_t3_exactly_partition_fresh_window", "protocol_hashes_correspond_to_frozen_artifacts",
              "no_outcome_fields_present"):
        check(f"seal_{k}_is_true", sv[k] is True)

    # ---- run the independent verify script and confirm it agrees ----
    import subprocess
    verify_result = subprocess.run(
        [sys.executable, os.path.join(PHASE78D_DIR, "verify_volatility_breakout_prerun_manifest.py")],
        capture_output=True, text=True,
    )
    check("independent_verify_script_exits_0", verify_result.returncode == 0)
    check("independent_verify_script_agrees_on_verdict",
          "PRE_RUN_SEAL_VERIFIED_READY_TO_RUN" in verify_result.stdout)
    check("independent_verify_script_confirms_no_execution",
          "SERIOUS_VALIDATION_NOT_EXECUTED" in verify_result.stdout)

    # ---- manifest purity: no outcome fields anywhere ----
    mp = p["manifest_purity_check"]
    check("manifest_purity_all_false", all(v is False for v in mp.values()))

    # ---- final status ----
    fs = p["final_status"]
    check("final_status_is_verified_ready_to_run", fs["value"] == "PRE_RUN_SEAL_VERIFIED_READY_TO_RUN")
    check("final_status_still_flags_serious_validation_not_executed", fs["serious_validation_still_not_executed"] is True)

    # ---- vincoli espliciti della fase ----
    for flag in ("serious_validation_not_executed", "no_strategy_outcome_accessed", "no_trade_results_generated",
                 "no_pf_expectancy_or_winrate_computed", "no_edge_discovery_performed",
                 "no_retroactive_modification_of_frozen_artifacts"):
        check(f"{flag}_is_true", p[flag] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non esegue mai backtest, non riscrive artifact frozen ----
    builder_path = os.path.join(PHASE78D_DIR, "build_volatility_breakout_prerun_manifest.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_imports_or_invokes_backtest_engine",
          "import backtest" not in builder_src and "from backtest" not in builder_src)
    check("builder_never_writes_to_frozen_artifact_paths",
          "volatility_breakout_serious_3y_prereg_v1.json\", \"w" not in builder_src and
          "volatility_breakout_serious_3y_run_authorization_v1.json\", \"w" not in builder_src and
          "volatility_breakout_prerun_seal_status_v1.json\", \"w" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== VOLATILITY_BREAKOUT PRE-RUN manifest consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
