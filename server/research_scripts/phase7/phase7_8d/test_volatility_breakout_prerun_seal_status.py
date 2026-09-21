#!/usr/bin/env python3
"""Phase 7.8D - PRE-RUN Seal Status: consistency checks.
Verifica che la correzione T1/T2/T3 sia genuinamente scale-free e non
modifichi 7.8C, che la verifica di accesso ai dati sia fondata su
controlli REALI e riproducibili (non affermazioni), che nessuna
data/hash/tick-coverage sia stata fabbricata, che il final_status sia
uno dei 2 valori ammessi, e che nessun outcome/backtest sia stato
toccato."""
import os
import re
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
    doc = load_json(os.path.join(PHASE78D_DIR, "volatility_breakout_prerun_seal_status_v1.json"))
    p = doc["payload"]

    check("hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))
    check("baseline_commit_matches_expected", p["baseline_commit"] == "a0fe99eb88ff8b21d26bacbaae69003c49eeec32")
    check("candidate_is_volbrk", p["candidate_id"] == "VOLATILITY_BREAKOUT_CONFIRMED")

    # ---- 7.8C NON modificato ----
    auth_path = os.path.join(PHASE7_DIR, "phase7_8c", "volatility_breakout_serious_3y_run_authorization_v1.json")
    auth_doc = load_json(auth_path)
    sa = p["source_artifact_untouched"]
    check("authorization_hash_matches_real_file", sa["canonical_sha256"] == auth_doc["canonical_sha256"])
    check("authorization_known_hash_unchanged",
          auth_doc["canonical_sha256"] == "239ad329967ac0668965f89e3fe217f8b4dec7826b23593a510eba118f6eda78")
    check("modified_in_this_phase_false", sa["modified_in_this_phase"] is False)

    # ---- Sec.1: T1/T2/T3 correction - scale-free, contiguous, no gaps/overlap, no outcome ----
    tsc = p["temporal_segmentation_correction"]
    check("tsc_target_hash_matches_real_authorization", tsc["target_artifact_canonical_sha256_unchanged"] == auth_doc["canonical_sha256"])
    check("tsc_modified_flag_false", tsc["modified_in_this_phase"] is False)
    check("tsc_never_uses_year_1_2_3_going_forward",
          "NON 'Year 1/2/3'" in tsc["correction_rule"]["definition"] or
          "NON anni solari" in tsc["correction_rule"]["definition"])
    check("tsc_constraints_include_no_overlap_no_gaps_equal_duration",
          any("overlap" in c for c in tsc["correction_rule"]["constraints"]) and
          any("gap" in c for c in tsc["correction_rule"]["constraints"]) and
          any("uguali" in c for c in tsc["correction_rule"]["constraints"]))
    check("tsc_boundaries_frozen_before_outcomes_flag", tsc["correction_rule"]["boundaries_frozen_before_outcomes"] is True)
    check("tsc_no_outcome_read_flag", tsc["correction_rule"]["no_outcome_read_to_construct_segments"] is True)
    check("tsc_criteria_unchanged_in_substance_still_2_of_3_and_100pct",
          "2 dei 3" in tsc["criteria_unchanged_in_substance"]["criterion_1"] and
          "100%" in tsc["criteria_unchanged_in_substance"]["criterion_2"])
    check("tsc_status_resolved", tsc["status"] == "RESOLVED")

    # ---- Sec.2: data access verification - controlli REALI, riproducibili ----
    dav = p["data_access_verification"]
    check("mt5_process_check_method_is_get_process",
          "Get-Process" in dav["mt5_process_check"]["method"])
    check("mt5_process_check_found_none_running",
          "NESSUN processo" in dav["mt5_process_check"]["result"])

    # ---- LocalBridge whitelist: verificato DAVVERO contro il file sorgente reale ----
    local_bridge_path = os.path.join(ROOT, "LocalBridge", "nexus_local_worker.py")
    check("local_bridge_file_exists_and_hash_matches_real_file",
          os.path.isfile(local_bridge_path) and
          dav["local_bridge_capability_check"]["file_sha256"] == file_sha256(local_bridge_path))
    with open(local_bridge_path, encoding="utf-8") as f:
        lb_src = f.read()
    real_handlers = sorted(set(re.findall(r"def handle_(\w+)\(", lb_src)))
    check("local_bridge_handlers_list_matches_real_source",
          dav["local_bridge_capability_check"]["handlers_found_in_source"] == real_handlers)
    check("local_bridge_genuinely_has_no_sync_or_backtest_action",
          not any(kw in lb_src.lower() for kw in
                  ("sync_history", "run_backtest", "run_tester", "start_tester", "history_sync",
                   "download_history")) and
          dav["local_bridge_capability_check"]["has_history_sync_or_backtest_action"] is False)

    # ---- Cache GOLD: percorsi/dimensioni/mtime riportati devono corrispondere ai file REALI su disco ----
    for entry in dav["existing_gold_history_cache_found"]:
        d = entry["directory"]
        check(f"gold_cache_dir_exists_{entry['latest_file']}_{len(entry['directory'])}",
              os.path.isdir(d), d)
        if os.path.isdir(d):
            real_files = sorted(e for e in os.listdir(d) if e.endswith(".hcc"))
            check("gold_cache_n_year_files_matches_real_dir_listing_" + d[-20:],
                  len(real_files) == entry["n_year_files"])
            check("gold_cache_latest_file_matches_real_dir_listing_" + d[-20:],
                  (real_files[-1] if real_files else None) == entry["latest_file"])

    check("existing_cache_flagged_stale_not_used_as_sync",
          "STALE" in dav["existing_cache_does_not_satisfy_requirement"]["reason"])
    check("no_dates_hashes_tick_coverage_fabricated_flag", dav["no_dates_hashes_or_tick_coverage_fabricated"] is True)

    # ---- Sec.3-8: blocked sections dichiarate, nessun valore fabbricato dentro di esse ----
    bs = p["blocked_sections_pending_real_data_access"]
    check("blocked_sections_cover_exact_windows_dataset_identity_tick_coverage",
          "exact_windows" in bs and "dataset_identity" in bs and "real_tick_coverage" in bs)
    for k, v in bs.items():
        if k == "protocol_identity_pins":
            continue
        check(f"blocked_section_{k}_does_not_contain_a_date_pattern",
              not re.search(r"\d{4}-\d{2}-\d{2}", v))

    # ---- Protocol hashes pinnabili: verificati contro i file reali ----
    pph = p["pinnable_protocol_hashes"]
    check("pinnable_strategy_commit_is_f035d30", pph["strategy_frozen_commit"] == "f035d30")
    prereg_doc = load_json(os.path.join(PHASE7_DIR, "phase7_8b", "volatility_breakout_serious_3y_prereg_v1.json"))
    check("pinnable_prereg_hash_matches_real_file", pph["prereg_canonical_hash"] == prereg_doc["canonical_sha256"])
    check("pinnable_authorization_hash_matches_real_file", pph["authorization_7_8c_canonical_hash"] == auth_doc["canonical_sha256"])
    cost_model_path = os.path.join(PHASE7_DIR, "policies", "cost_model_integration.json")
    check("pinnable_cost_model_hash_matches_real_file", pph["cost_model_hash"] == file_sha256(cost_model_path))

    # ---- Sec.9: final status - uno dei 2 valori ammessi, mai READY_TO_RUN ----
    fs = p["final_status"]
    check("final_status_is_blocked_or_verified",
          fs["value"] in ("PRE_RUN_SEAL_VERIFIED_READY_TO_RUN", "PRE_RUN_SEAL_BLOCKED"))
    check("final_status_is_blocked_given_no_data_access", fs["value"] == "PRE_RUN_SEAL_BLOCKED")
    check("final_status_reason_cites_no_data_access", "NO_DATA_ACCESS" in fs["reason"] or "no_data_access" in fs["reason"].lower())
    check("final_status_distinguishes_access_blocker_from_conceptual",
          "non metodologico" in fs["not_a_conceptual_blocker"] or "ACCESSO/AMBIENTE" in fs["not_a_conceptual_blocker"])

    # ---- vincoli espliciti della fase ----
    for flag in ("serious_validation_not_executed", "no_strategy_outcome_accessed", "no_trade_results_generated",
                 "no_pf_expectancy_or_winrate_computed", "no_edge_discovery_performed",
                 "no_retroactive_modification_of_frozen_artifacts"):
        check(f"{flag}_is_true", p[flag] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non legge mai outcome/prezzi, non esegue backtest ----
    builder_path = os.path.join(PHASE78D_DIR, "build_volatility_breakout_prerun_seal_status.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_reads_events_or_state_or_bars_csv",
          "events_p71.csv" not in builder_src and "market_state_dataset_p71.csv" not in builder_src)
    check("builder_never_imports_or_invokes_backtest_engine",
          "import backtest" not in builder_src and "from backtest" not in builder_src)
    check("builder_never_writes_to_frozen_artifact_paths",
          "volatility_breakout_serious_3y_run_authorization_v1.json\", \"w" not in builder_src and
          "volatility_breakout_serious_3y_prereg_v1.json\", \"w" not in builder_src)
    check("builder_never_parses_hcc_binary_content", "struct.unpack" not in builder_src and "rate_record" not in builder_src.lower())

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== VOLATILITY_BREAKOUT PRE-RUN seal status consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
