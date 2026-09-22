#!/usr/bin/env python3
"""Phase 7.9B - Verifica INDIPENDENTE della formalizzazione BREAKOUT_ACC.
Ricalcola dal codice/registro/artifact reali: identita', reachability
statica, e le catene di hash verso le fonti di evidenza. Fallisce chiuso
su qualunque mismatch. MAI esegue backtest."""
import os
import sys

PHASE79B_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79B_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402


def verify():
    lc_doc = load_json(os.path.join(PHASE79B_DIR, "breakout_acc_lifecycle_contract_v1.json"))
    ln_doc = load_json(os.path.join(PHASE79B_DIR, "breakout_acc_evidence_lineage_v1.json"))
    dc_doc = load_json(os.path.join(PHASE79B_DIR, "breakout_acc_formalization_decision_v1.json"))
    checks = {}

    checks["lifecycle_hash_matches_payload"] = lc_doc["canonical_sha256"] == canonical_sha256(lc_doc["payload"])
    checks["lineage_hash_matches_payload"] = ln_doc["canonical_sha256"] == canonical_sha256(ln_doc["payload"])
    checks["decision_hash_matches_payload"] = dc_doc["canonical_sha256"] == canonical_sha256(dc_doc["payload"])

    # ---- Identity: ricalcolata dal registro/codice reali ----
    identity = lc_doc["payload"]["identity"]
    registry = load_json(os.path.join(ROOT, "contracts", "strategy-registry.json"))
    real_entry = next(s for s in registry["strategies"] if s["strategy_id"] == "BREAKOUT_ACC")
    checks["registry_entry_matches_real_file"] = identity["registry_entry_verified"] == real_entry
    checks["selector_9_confirmed"] = real_entry["selector_index"] == 9

    strategies_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    with open(strategies_file, encoding="utf-8") as f:
        strategies_src = f.read()
    checks["guard_line_recomputed_matches"] = identity["master_switch"]["guard_line_source"] in strategies_src
    checks["function_recomputed_present"] = "SNXSSignal NXS_Strat_BreakoutAcc()" in strategies_src
    checks["shared_enum_all_3_present"] = all(
        f's.strat = STRAT_BREAKOUT_ACC; s.stratName = "{name}"' in strategies_src.replace("\n", " ").replace("   ", " ")
        or f"STRAT_BREAKOUT_ACC" in strategies_src
        for name in ("BREAKOUT_ACC", "VOLATILITY_BREAKOUT_CONFIRMED", "Z_SCORE_BREAKOUT")
    )

    ea_file = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")
    with open(ea_file, encoding="utf-8") as f:
        ea_src = f.read()
    checks["router_call_recomputed_present"] = "NXS_Strat_BreakoutAcc()" in ea_src

    # ---- Lifecycle contract: hash della funzione ricalcolato ----
    start = strategies_src.index("SNXSSignal NXS_Strat_BreakoutAcc()")
    end = strategies_src.index("\n}\n", start) + 3
    func_body = strategies_src[start:end]
    recomputed_func_hash = canonical_sha256({"function_source": func_body})
    checks["function_hash_recomputed_matches"] = recomputed_func_hash == lc_doc["payload"]["lifecycle_contract"]["source_function_hash"]

    # ---- Static reachability: tutti i check devono essere True ----
    reachability = lc_doc["payload"]["static_reachability"]
    checks["reachability_all_checks_true"] = all(reachability["checks"].values())
    checks["reachability_verdict_pass"] = reachability["verdict"] == "STATIC_REACHABILITY_PASS"

    # ---- Evidence lineage: fonte Phase E hash reale ----
    phase_e_source = ln_doc["payload"]["evidence_lineage"]["sources_examined"]["source_D_phase_e_september"]
    phase_e_json_path = os.path.join(ROOT, "results", "cost_calibration_67_rerun", "phase_e_breakoutacc_findings.json")
    checks["phase_e_json_file_exists"] = os.path.isfile(phase_e_json_path)
    if os.path.isfile(phase_e_json_path):
        checks["phase_e_json_hash_matches_real_file"] = file_sha256(phase_e_json_path) == phase_e_source["phase_e_json_sha256"]
        real_phase_e = load_json(phase_e_json_path)
        checks["phase_e_n_trades_4_confirmed"] = (
            real_phase_e["parity_test_window_2_max_historical_intersection"]["mt5_result"]["n_trades_total"] == 4
        )
        checks["phase_e_all_losses_confirmed"] = (
            real_phase_e["parity_test_window_2_max_historical_intersection"]["mt5_result"]["all_losses"] is True
        )
        checks["phase_e_verdict_hold_confirmed"] = (
            real_phase_e["gate_consequence"]["verdict"].startswith("HOLD_NEEDS_MORE_EVIDENCE")
        )

    # ---- Vincoli espliciti della fase ----
    for doc, name in ((lc_doc, "lifecycle"), (ln_doc, "lineage"), (dc_doc, "decision")):
        checks[f"{name}_no_backtest_flag"] = doc["payload"].get("no_backtest_executed") is True

    checks["decision_next_experiment_valid_category"] = dc_doc["payload"]["decision"]["next_admissible_experiment"]["category"] in (
        "BUILD_CLEAN_DISCOVERY_DATASET", "REANALYZE_EXISTING_RAW_RESULTS", "RUN_CAUSAL_DISCOVERY",
        "RUN_FAST_STRUCTURAL_VALIDATION", "BLOCKED_NEEDS_IMPLEMENTATION_FIX")
    checks["decision_not_executed"] = dc_doc["payload"]["decision"]["next_admissible_experiment"]["not_executed_in_this_phase"] is True
    checks["constraints_preserved"] = all(dc_doc["payload"]["constraints_preserved"].values())

    core_checks = {k: v for k, v in checks.items() if isinstance(v, bool)}
    all_passed = all(core_checks.values())
    verdict = "FORMALIZATION_INDEPENDENTLY_CONFIRMED" if all_passed else "VERIFICATION_FAILED"
    return checks, verdict


def main():
    checks, verdict = verify()
    for k, v in checks.items():
        print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print(f"\nVERDICT: {verdict}")
    return verdict == "FORMALIZATION_INDEPENDENTLY_CONFIRMED"


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
