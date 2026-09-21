#!/usr/bin/env python3
"""Phase 7.7B - Strategy Meta-Filter Gate: consistency checks.
Verifica che i due assi (structural eligibility / research readiness)
siano genuinamente indipendenti, che il gate richieda ENTRAMBI, che
nessun dato sorgente di Phase 7.7A sia stato alterato (ne' l'old
artifact ne' il lifecycle registry), e che nessun nuovo backtest/
outcome/MECH-23 sia stato toccato."""
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
    gate_doc = load_json(os.path.join(PHASE77B_DIR, "strategy_meta_filter_gate_v1.json"))
    crossref_doc = load_json(os.path.join(PHASE77B_DIR, "strategy_meta_filter_gate_crossref_v1.json"))
    gp, cp = gate_doc["payload"], crossref_doc["payload"]

    check("gate_hash_matches_payload", gate_doc["canonical_sha256"] == canonical_sha256(gp))
    check("crossref_hash_matches_payload", crossref_doc["canonical_sha256"] == canonical_sha256(cp))
    check("baseline_commit_matches_expected", gp["baseline_commit"] == "6ac26cc0ee8ee088a94e2cee038c12c1d1195316")

    # ---- old artifact (Phase 7.7A) NON modificato - verificato contro il file reale ----
    old_meta_path = os.path.join(PHASE7_DIR, "phase7_7a", "strategy_meta_filter_eligibility_v1.json")
    old_meta_doc = load_json(old_meta_path)
    check("old_meta_filter_artifact_hash_matches_real_file",
          gp["source_old_meta_filter_artifact_untouched"]["canonical_sha256"] == old_meta_doc["canonical_sha256"])
    check("old_meta_filter_artifact_declared_not_modified",
          gp["source_old_meta_filter_artifact_untouched"]["modified_in_this_phase"] is False)
    check("old_meta_filter_known_hash_unchanged",
          old_meta_doc["canonical_sha256"] == "7fe6d96c0a0e1380ba16f3707f84a152d61a6dbd22322ac01e6cb2b71059b493")

    lifecycle_path = os.path.join(PHASE7_DIR, "phase7_7a", "strategy_lifecycle_registry_v1.json")
    lifecycle_doc = load_json(lifecycle_path)
    check("lifecycle_registry_hash_matches_real_file",
          gp["source_lifecycle_registry"]["canonical_sha256"] == lifecycle_doc["canonical_sha256"])
    check("lifecycle_registry_known_hash_unchanged",
          lifecycle_doc["canonical_sha256"] == "270088329416d23cef2d5675b8da21690d6e542d4b3493142c3e0fa15c628bf1")

    # ---- gate definition: richiede ENTRAMBI gli assi, mai automatico da FULL_STRATEGY_SPEC ----
    gd = gp["gate_definition"]
    check("gate_requires_both_axes", "AND" in gd["requirement"] and "ELIGIBLE" in gd["requirement"] and "READY" in gd["requirement"])
    check("gate_explicitly_forbids_automatic_promotion",
          "NON diventa automaticamente" in gd["explicit_non_automatic_promotion"])

    # ---- valori enum esattamente quelli richiesti dal reviewer ----
    check("structural_values_exactly_two", gp["structural_eligibility_values"] == ["ELIGIBLE", "NOT_ELIGIBLE"])
    check("readiness_values_exactly_six",
          set(gp["research_readiness_values"]) == {"READY", "NEEDS_MORE_EVIDENCE", "BORDERLINE_LOW_PRIORITY",
                                                     "REFUTED_INAPPROPRIATE", "EXECUTION_FAILED_INAPPROPRIATE",
                                                     "NOT_READY"})

    # ---- i 6 candidati esplicitamente richiesti dal reviewer sono tutti presenti ----
    results = gp["gate_results_by_candidate"]
    required_candidates = ["VOLATILITY_BREAKOUT_CONFIRMED", "H006_LIQUIDITY_SWEEP_RECLAIM", "WICK_SWEEP_RECLAIM",
                            "ADX_RSI", "BREAKOUT_ACC"]
    check("all_named_candidates_present_except_sar_split_in_two",
          all(c in results for c in required_candidates) and
          ("SAR_LIVE" in results or "H015_SAR_EXTERNAL_VALIDATION" in results))
    check("both_sar_identities_covered", "SAR_LIVE" in results and "H015_SAR_EXTERNAL_VALIDATION" in results)

    # ---- risultati specifici attesi (derivati meccanicamente, verificati esplicitamente) ----
    check("volbrk_structural_eligible_needs_more_evidence",
          results["VOLATILITY_BREAKOUT_CONFIRMED"]["meta_filter_structural_eligibility"] == "ELIGIBLE" and
          results["VOLATILITY_BREAKOUT_CONFIRMED"]["meta_filter_research_readiness"] == "NEEDS_MORE_EVIDENCE")
    check("h006_structural_eligible_borderline_low_priority",
          results["H006_LIQUIDITY_SWEEP_RECLAIM"]["meta_filter_structural_eligibility"] == "ELIGIBLE" and
          results["H006_LIQUIDITY_SWEEP_RECLAIM"]["meta_filter_research_readiness"] == "BORDERLINE_LOW_PRIORITY")
    check("wick_sweep_not_eligible_execution_failed",
          results["WICK_SWEEP_RECLAIM"]["meta_filter_structural_eligibility"] == "NOT_ELIGIBLE" and
          results["WICK_SWEEP_RECLAIM"]["meta_filter_research_readiness"] == "EXECUTION_FAILED_INAPPROPRIATE")
    check("h015_sar_eligible_refuted",
          results["H015_SAR_EXTERNAL_VALIDATION"]["meta_filter_structural_eligibility"] == "ELIGIBLE" and
          results["H015_SAR_EXTERNAL_VALIDATION"]["meta_filter_research_readiness"] == "REFUTED_INAPPROPRIATE")
    check("sar_live_not_eligible_audit_depth_refuted",
          results["SAR_LIVE"]["meta_filter_structural_eligibility"] == "NOT_ELIGIBLE" and
          results["SAR_LIVE"]["meta_filter_research_readiness"] == "REFUTED_INAPPROPRIATE" and
          "audit" in results["SAR_LIVE"]["structural_blocker"].lower())
    check("adx_rsi_not_eligible_audit_depth_refuted",
          results["ADX_RSI"]["meta_filter_structural_eligibility"] == "NOT_ELIGIBLE" and
          results["ADX_RSI"]["meta_filter_research_readiness"] == "REFUTED_INAPPROPRIATE")
    check("breakout_acc_not_eligible_audit_depth_not_ready",
          results["BREAKOUT_ACC"]["meta_filter_structural_eligibility"] == "NOT_ELIGIBLE" and
          results["BREAKOUT_ACC"]["meta_filter_research_readiness"] == "NOT_READY")

    # ---- nessun candidato passa il gate oggi - fatto onesto, non un difetto ----
    check("no_candidate_passes_full_gate_today",
          all(not r["meta_filter_ready_gate_passed"] for r in results.values()))
    check("zero_candidates_have_readiness_ready",
          all(r["meta_filter_research_readiness"] != "READY" for r in results.values()))

    # ---- evidence_verdict e classification citati devono coincidere con quelli REALI di 7.7A (mai alterati) ----
    lp = lifecycle_doc["payload"]["deep_dive_candidates"]
    for cid, r in results.items():
        check(f"{cid}_evidence_verdict_unchanged_from_7_7a",
              r["evidence_verdict_unchanged_from_7_7a"] == lp[cid]["evidence_verdict"])
        check(f"{cid}_classification_unchanged_from_7_7a",
              r["classification_unchanged_from_7_7a"] == lp[cid]["classification"])

    # ---- counts coerenti con i risultati per-candidato ----
    counts = gp["counts"]
    check("counts_total_matches_n_candidates", counts["total_candidates_evaluated"] == len(results))
    check("counts_structural_eligible_matches",
          counts["structural_eligible_count"] == sum(1 for r in results.values() if r["meta_filter_structural_eligibility"] == "ELIGIBLE"))
    check("counts_research_ready_matches",
          counts["research_ready_count"] == sum(1 for r in results.values() if r["meta_filter_research_readiness"] == "READY"))
    check("counts_blocked_matches",
          counts["blocked_count"] == sum(1 for r in results.values() if not r["meta_filter_ready_gate_passed"]))
    check("counts_meta_filter_ready_is_zero", counts["meta_filter_ready_count"] == 0)

    # ---- crossref: ogni candidato ha una entry, il vecchio ELIGIBLE viene esplicitamente corretto ----
    check("crossref_covers_all_candidates", set(cp["crossref_by_candidate"].keys()) == set(results.keys()))
    for cid, x in cp["crossref_by_candidate"].items():
        check(f"{cid}_crossref_new_axes_match_gate_results",
              x["new_structural_eligibility"] == results[cid]["meta_filter_structural_eligibility"] and
              x["new_research_readiness"] == results[cid]["meta_filter_research_readiness"])
        if x["old_single_label_phase_7_7a"] == "META_FILTER_ELIGIBLE":
            check(f"{cid}_semantic_correction_flags_dashboard_risk",
                  "pronto a testare" in x["semantic_correction"])

    # ---- governance inconsistencies: almeno le 4 attese, inclusa la nuova (audit depth gap) ----
    gi_types = {g["type"] for g in gp["governance_inconsistencies"]}
    check("governance_inconsistencies_include_semantic_conflation_corrected",
          "SEMANTIC_CONFLATION_CORRECTED_THIS_PHASE" in gi_types)
    check("governance_inconsistencies_include_active_vs_refuted", "ACTIVE_STATUS_VS_REFUTED_EVIDENCE" in gi_types)
    check("governance_inconsistencies_include_h006_drift", "H006_VOCABULARY_DRIFT" in gi_types)
    check("governance_inconsistencies_include_new_audit_depth_gap", "STRUCTURAL_ELIGIBILITY_AUDIT_DEPTH_GAP" in gi_types)

    # ---- vincoli espliciti della fase ----
    for flag in ("no_new_backtest_executed", "no_mech23_applied", "no_historical_results_modified",
                 "no_edge_discovery_performed", "no_new_outcome_data_accessed"):
        check(f"{flag}_is_true", gp[flag] is True)
    check("seq0015_still_closed", gp["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", gp["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    # ---- verifica statica: il builder non legge mai outcome/prezzi, non riscrive l'old artifact ----
    builder_path = os.path.join(PHASE77B_DIR, "build_strategy_meta_filter_gate.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_reads_events_or_state_or_bars_csv",
          "events_p71.csv" not in builder_src and "market_state_dataset_p71.csv" not in builder_src)
    check("builder_never_writes_to_old_meta_filter_or_lifecycle_paths",
          "strategy_meta_filter_eligibility_v1.json\", \"w" not in builder_src and
          "strategy_lifecycle_registry_v1.json\", \"w" not in builder_src)
    check("builder_never_reruns_backtest_engine",
          "run_backtest" not in builder_src and "sig_volatility_breakout" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== Strategy meta-filter gate consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
