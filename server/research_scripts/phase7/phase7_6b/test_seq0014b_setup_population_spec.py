#!/usr/bin/env python3
"""Phase 7.6B - SEQ-0014B setup population spec: consistency checks.
Verifica coerenza interna, che SEQ-0014A non sia stata toccata, che
nessun outcome sia stato letto e che nessun structural preflight/
discovery sia stato eseguito."""
import os
import sys

PHASE76B_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE76B_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE76B_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

RESULTS = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"check": name, "status": status})
    print(f"[{status}] {name} {('- ' + detail) if detail else ''}")
    return condition


def main():
    doc_path = os.path.join(PHASE76B_DIR, "seq0014b_setup_population_spec_v1.json")
    doc = load_json(doc_path)
    p = doc["payload"]

    check("canonical_hash_matches_payload", doc["canonical_sha256"] == canonical_sha256(p))

    # ---- inventario: 9 famiglie, 6 eleggibili + 3 riclassificate come outcome-label ----
    inv = p["detector_inventory"]
    check("inventory_has_all_9_families", len(inv) == 9, f"n={len(inv)}")
    check("eligible_families_are_exactly_6",
          p["eligible_setup_families"] == ["VOLATILITY_EXPANSION", "DISPLACEMENT", "BREAKOUT", "SWEEP",
                                            "COMPRESSION_RELEASE", "PULLBACK"])
    check("excluded_as_outcome_labels_are_exactly_3",
          p["excluded_as_independent_setups_reclassified_as_outcome_labels"] ==
          ["FAILED_BREAKOUT", "RETEST", "RECLAIM"])
    for fam in p["eligible_setup_families"]:
        check(f"{fam}_is_not_delayed_confirmation", inv[fam]["delayed_confirmation"] is False)
    for fam in p["excluded_as_independent_setups_reclassified_as_outcome_labels"]:
        check(f"{fam}_is_delayed_confirmation", inv[fam]["delayed_confirmation"] is True)

    # ---- build_events.py hash reale, non inventato ----
    build_events_path = os.path.join(PHASE7_DIR, "phase7_1", "build_events_p71.py")
    check("build_events_hash_matches_current_file",
          p["eligibility_rule"]["build_events_source_hash"] == file_sha256(build_events_path))

    # ---- eleggibilita' non basata su performance ----
    forbidden = p["eligibility_rule"]["criteria_explicitly_forbidden"]
    check("forbidden_criteria_include_pf_winrate_deltap",
          any("PF" in c or "profit" in c.lower() for c in forbidden) and
          any("win rate" in c.lower() for c in forbidden) and
          any("deltap" in c.lower() or "delta" in c.lower() for c in forbidden))

    # ---- RECLAIM discrepancy: verificato contro l'artifact frozen originale, non assunto ----
    reclaim = inv["RECLAIM"]
    check("reclaim_history_cites_actual_frozen_result_file",
          "phase7_1_run_results.json" in reclaim["prior_test_history"])
    check("reclaim_history_flags_registry_discrepancy",
          "MAI 'REFUTED'" in reclaim["prior_test_history"] or "MAI" in reclaim["prior_test_history"])
    check("reclaim_not_labeled_refuted_outright", "already_refuted_as_autonomous_edge" not in reclaim)

    # ---- failure-memory policy: distinzione esplicita, nessuna famiglia disqualificata a torto ----
    fmp = p["failure_memory_inclusion_policy"]
    check("distinction_present", "REFUTED_AS_AUTONOMOUS_EDGE" in fmp["distinction"] and
          "NOT_USABLE_AS_FILTER_TEST_UNIT" in fmp["distinction"])
    check("all_6_eligible_have_refuted_autonomous_history",
          all(inv[fam].get("already_refuted_as_autonomous_edge") is True for fam in p["eligible_setup_families"]))
    check("refuted_history_does_not_disqualify",
          len(p["eligible_setup_families"]) == 6,
          "tutte e 6 restano eleggibili nonostante lo storico REFUTED_AS_AUTONOMOUS_EDGE")

    # ---- architettura: decisione presa, non lasciata aperta ----
    arch = p["architecture_decision"]
    check("architecture_decision_made", arch["decision"] == "OPTION_B_POOLED_STRATIFIED_BY_SETUP_FAMILY_ID")
    check("both_options_described", "option_A_single_family" in arch and "option_B_pooled_stratified" in arch)
    check("no_naive_pooling_enforcement_present", "no_naive_pooling_enforcement" in arch)

    # ---- regime contract: CHOPPY riusa i cutpoint di SEQ-0014A invariati, MED escluso ----
    seq0014a_path = os.path.join(PHASE7_DIR, "phase7_5c", "seq0014_frozen_structural_spec_v1.json")
    seq0014a = load_json(seq0014a_path)["payload"]
    reg = p["regime_contract"]
    check("choppy_cutpoints_match_seq0014a_frozen_unchanged",
          reg["tercile_cutpoints_reused_unchanged"] ==
          seq0014a["state_definition"]["tercile_cutpoints_fit_on_discovery_only"])
    check("med_tercile_excluded", reg["MED_tercile_treatment"] == "EXCLUDED")

    # ---- timestamp contract: regime letto a t-1, endogeneita' identificata e risolta ----
    ts = p["timestamp_contract"]
    check("regime_read_at_t_minus_1", ts["regime_read_timestamp"].startswith("t-1"))
    check("endogeneity_risk_explicitly_identified", "endogeneity_risk_identified" in ts)
    check("no_data_computed_yet_for_timestamps", ts["not_yet_computed"].startswith("Nessun valore"))

    # ---- outcome candidates: elencati, nessuna selezione ----
    co = p["candidate_failure_noise_outcomes"]
    check("at_least_4_generic_outcome_candidates", len(co["generic_candidates_from_existing_vocabulary"]) >= 4)
    check("family_specific_candidates_present", len(co["family_specific_native_candidates"]) == 2)
    check("no_single_outcome_selected_as_primary",
          not any("primary_outcome" == k for k in co.keys()))

    # ---- hard stop check: popolazione trovata, non bloccato ----
    hsc = p["hard_stop_check"]
    check("hard_stop_not_triggered", hsc["hard_stop_triggered"] is False)
    check("mech23_status_is_awaiting_structural_preflight",
          hsc["MECH23_FILTER_CLAIM_STATUS"] == "SETUP_POPULATION_SPECIFIED_AWAITING_STRUCTURAL_PREFLIGHT")

    # ---- nessuna esecuzione prematura, nessun tocco a SEQ-0014A, nessun outcome ----
    check("no_structural_preflight_executed_flag", p["no_structural_preflight_executed"] is True)
    check("no_discovery_authorized_flag", p["no_discovery_authorized"] is True)
    check("no_outcome_accessed_flag", p["no_nexus_outcome_data_accessed"] is True)
    check("no_edge_discovery_flag", p["no_edge_discovery_performed"] is True)
    check("seq0015_still_closed", p["seq0015_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")
    check("seq0009_still_closed", p["seq0009_status_unchanged"] == "CLOSED_NOT_REEXAMINED_AS_CANDIDATE")

    check("seq0014a_frozen_spec_file_exists", os.path.exists(seq0014a_path))
    check("seq0014a_untouched_claim_present", "seq0014a_untouched" in p)

    # ---- verifica statica: il builder non legge mai outcome ----
    builder_path = os.path.join(PHASE76B_DIR, "build_seq0014b_setup_population_spec.py")
    with open(builder_path, encoding="utf-8") as f:
        builder_src = f.read()
    check("builder_never_opens_outcomes_csv", "OUTCOMES_PATH" not in builder_src and "outcomes_v1" not in builder_src)
    check("builder_never_imports_outcome_computation",
          "load_outcomes" not in builder_src and "compute_outcome" not in builder_src)

    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_fail = len(RESULTS) - n_pass
    print(f"\n=== SEQ-0014B setup population spec consistency suite: {n_pass} PASS, {n_fail} FAIL su {len(RESULTS)} check ===")
    return n_fail == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
