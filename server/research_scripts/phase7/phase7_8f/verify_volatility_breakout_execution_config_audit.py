#!/usr/bin/env python3
"""Phase 7.8F - Verifica INDIPENDENTE dell'Execution Config Audit.

Ricalcola da zero (mai fidandosi del blocco 'seal_verification' scritto dal
builder):
  - la regola FromDate/ToDate, ri-leggendo i due file probe grezzi
  - l'hash del tester config finale
  - i confronti con l'artifact 7.8E reale (non modificato)
  - il selector index contro il registro reale
  - lo stato letterale del bug Expert= nel log grezzo del terminale

Fallisce chiuso (BLOCKED) su qualunque mismatch. MAI esegue il Serious
validation."""
import os
import sys

PHASE78F_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78F_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78F_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

MANIFEST_PATH = os.path.join(PHASE78F_DIR, "volatility_breakout_execution_config_audit_v1.json")
PRIOR_78E_PATH = os.path.join(PHASE7_DIR, "phase7_8e", "volatility_breakout_final_data_freeze_v1.json")
RAW_PROBES_DIR = os.path.join(PHASE78F_DIR, "raw_probes")


def verify():
    doc = load_json(MANIFEST_PATH)
    p = doc["payload"]
    checks = {}

    # ---- 1. Leverage: il valore corretto e' davvero 500, con provenienza reale ----
    la = p["leverage_audit"]
    checks["leverage_corrected_value_is_500"] = la["corrected_value"] == 500
    checks["leverage_at_least_one_source_authoritative"] = any(
        s.get("authoritative") for s in la["sources_examined"])

    # ---- 2. Expert path bug: il log grezzo REALE contiene davvero l'errore riportato ----
    epb = p["expert_path_bug_discovery"]
    log_path = os.path.join(ROOT, epb["log_evidence_file"])
    checks["expert_path_bug_log_file_exists"] = os.path.isfile(log_path)
    checks["expert_path_bug_log_hash_matches"] = (
        os.path.isfile(log_path) and file_sha256(log_path) == epb["log_evidence_sha256"]
    )
    with open(log_path, encoding="utf-8") as f:
        log_text = f.read()
    checks["expert_path_bug_log_contains_real_error"] = (
        "Experts\\Experts\\NXS_VolBrkTesterWindowProbe.ex5 not found" in log_text
        and "tester didn't start" in log_text
    )
    checks["expert_path_bug_corrected_value_no_prefix"] = (
        epb["corrected_value"] == "Expert=NEXUS_EA_v2" and "Experts\\" not in epb["corrected_value"]
    )

    # ---- 3. Timestamp semantics: ricalcolate dai file probe grezzi REALI, non copiate ----
    ts = p["timestamp_semantics"]
    probe_a_path = os.path.join(ROOT, ts["probe_A_fromdate_boundary"]["raw_output_file"])
    probe_b_path = os.path.join(ROOT, ts["probe_B_todate_boundary"]["raw_output_file"])
    checks["probe_A_file_exists"] = os.path.isfile(probe_a_path)
    checks["probe_B_file_exists"] = os.path.isfile(probe_b_path)
    checks["probe_A_hash_matches"] = (
        os.path.isfile(probe_a_path)
        and file_sha256(probe_a_path) == ts["probe_A_fromdate_boundary"]["raw_output_sha256"]
    )
    checks["probe_B_hash_matches"] = (
        os.path.isfile(probe_b_path)
        and file_sha256(probe_b_path) == ts["probe_B_todate_boundary"]["raw_output_sha256"]
    )
    with open(probe_a_path, encoding="utf-16") as f:
        pa = dict(ln.split("=", 1) for ln in f.read().strip().splitlines() if "=" in ln)
    with open(probe_b_path, encoding="utf-16") as f:
        pb = dict(ln.split("=", 1) for ln in f.read().strip().splitlines() if "=" in ln)
    checks["probe_A_recomputed_fromdate_inclusive"] = (
        pa["first_bar_time"] == "2023.12.20 00:00:00" == ts["probe_A_fromdate_boundary"]["first_bar_time"]
    )
    checks["probe_B_recomputed_todate_exclusive"] = (
        pb["last_bar_time"] == "2024.01.09 20:00:00" == ts["probe_B_todate_boundary"]["last_bar_time"]
        and pb["last_tick_time"] < "2024.01.10 00:00:00"
    )

    # ---- 4. Applicazione ai confini reali di 7.8D/7.8E (non modificati) ----
    prior_78e_doc = load_json(PRIOR_78E_PATH)
    real_tw = prior_78e_doc["payload"]["temporal_identity_recheck"]["PRIMARY_FRESH_VERDICT_WINDOW"]
    ab = ts["applied_to_frozen_boundaries"]
    checks["end_boundary_matches_real_7_8e"] = ab["end_boundary"]["frozen_value"] == real_tw["end"]
    checks["start_boundary_matches_real_7_8e"] = ab["start_boundary"]["frozen_value"] == real_tw["start"]
    checks["end_boundary_correctly_marked_exact"] = ab["end_boundary"]["coincides_exactly"] is True
    checks["start_boundary_correctly_marked_superset"] = ab["start_boundary"]["coincides_exactly"] is False
    checks["filter_rule_frozen_before_run"] = "12:06:50" in ab["start_boundary"]["filter_rule_frozen_now_before_seeing_results"]

    # ---- 5. Dipendenza temporale nascosta: verificata nel codice reale, non copiata ----
    htd = p["hidden_time_dependency_check"]
    strategies_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    with open(strategies_file, encoding="utf-8") as f:
        strategies_src = f.read()
    sig_start = strategies_src.index("SNXSSignal NXS_Strat_VolatilityBreakoutConfirmed()")
    sig_body = strategies_src[sig_start:strategies_src.index("\n}\n", sig_start) + 3]
    checks["signal_reverified_no_time_tokens"] = not any(
        tok in sig_body for tok in ("TimeCurrent", "TimeGMT", "InpServerGMTOffset", "InpUseSessions"))
    checks["signal_conclusion_matches"] = htd["signal_code_check"]["has_time_or_session_dependency"] is False

    ea_file = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")
    with open(ea_file, encoding="utf-8") as f:
        ea_src = f.read()
    profile_path_start = ea_src.index("if(InpUseStrategyProfiles){")
    profile_path_end = ea_src.index("return;   // percorso profili", profile_path_start) + 60
    profile_path_body = ea_src[profile_path_start:profile_path_end]
    checks["execution_path_reverified_calls_open_trade_directly"] = "NXS_OpenTrade(s," in profile_path_body
    checks["execution_path_reverified_skips_session_gate"] = "NXS_ResolvedEntryThreshold" not in profile_path_body
    checks["final_conclusion_is_no_dependency"] = htd["conclusion"] == "NO_TIMEZONE_DEPENDENT_SIGNAL_LOGIC"

    # ---- 6. Selector index contro il registro reale ----
    reg = load_json(os.path.join(ROOT, "contracts", "strategy-registry.json"))
    reg_entry = next(s for s in reg["strategies"] if s["strategy_id"] == "VOLATILITY_BREAKOUT_CONFIRMED")
    tc = p["tester_execution_config_final"]
    checks["selector_matches_real_registry"] = (
        f"InpStrategySelector={reg_entry['selector_index']}" in tc["raw_text"] and reg_entry["selector_index"] == 56
    )
    checks["tester_config_has_no_double_experts_prefix"] = "Experts\\Experts" not in tc["raw_text"]
    checks["tester_config_leverage_is_500"] = "Leverage=500" in tc["raw_text"]
    checks["tester_config_hash_recomputed_matches"] = (
        canonical_sha256({"tester_config_text": tc["raw_text"]}) == tc["sha256"]
        == p["final_seal"]["tester_config_sha256"]
    )
    checks["tester_config_not_launched"] = tc["not_launched"] is True

    # ---- 7. Provenienza verso 7.8E reale ----
    checks["previous_manifest_hash_matches_real_7_8e_file"] = (
        p["final_seal"]["previous_manifest_hash_7_8e"] == prior_78e_doc["canonical_sha256"]
    )
    checks["prereg_hash_matches_real_7_8e_chain"] = (
        p["final_seal"]["prereg_hash"] == prior_78e_doc["payload"]["final_seal"]["prereg_hash"]
    )
    checks["data_reverification_requirement_carried_forward"] = (
        p["final_seal"]["data_reverification_required_before_run"]["required"] is True
    )

    # ---- 8. Nessun campo di outcome ----
    forbidden_keys = {"trade_count", "profit_factor", "pf", "expectancy", "win_rate", "winrate",
                      "drawdown", "max_drawdown", "net_profit", "sharpe"}

    def scan_keys(obj):
        found = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.lower() in forbidden_keys:
                    found.add(k)
                found |= scan_keys(v)
        elif isinstance(obj, list):
            for item in obj:
                found |= scan_keys(item)
        return found
    checks["no_outcome_fields_present"] = len(scan_keys(p)) == 0

    core_checks = {k: v for k, v in checks.items() if isinstance(v, bool)}
    all_passed = all(core_checks.values())
    verdict = "EXECUTION_CONFIG_VERIFIED_READY_FOR_RUN" if all_passed else "EXECUTION_CONFIG_BLOCKED"
    return checks, verdict


def main():
    checks, verdict = verify()
    for k, v in checks.items():
        print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print(f"\nVERDICT: {verdict}")
    print("SERIOUS_VALIDATION_NOT_EXECUTED (questo script non esegue mai il backtest)")
    return verdict == "EXECUTION_CONFIG_VERIFIED_READY_FOR_RUN"


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
