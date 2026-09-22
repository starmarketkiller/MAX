#!/usr/bin/env python3
"""Phase 7.8G - Verifica INDIPENDENTE della root-cause analysis dello zero-
trade. Ri-estrae i fatti dal report reale, ri-legge il codice sorgente
reale, e ri-verifica che il flag mancante non compaia in NESSUN tester
config congelato precedente. Fallisce chiuso su qualunque mismatch."""
import os
import re
import sys

PHASE78G_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE78G_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json  # noqa: E402

MANIFEST_PATH = os.path.join(PHASE78G_DIR, "volatility_breakout_zero_trade_root_cause_v1.json")
RUN_MANIFEST_PATH = os.path.join(PHASE78G_DIR, "immutable_run_manifest_v1.json")


def verify():
    doc = load_json(MANIFEST_PATH)
    p = doc["payload"]
    checks = {}

    run_manifest = load_json(RUN_MANIFEST_PATH)
    checks["run_manifest_hash_matches_real_file"] = (
        p["immutable_run_manifest_reference"]["canonical_sha256"] == run_manifest["canonical_sha256"]
    )

    report_path = os.path.join(ROOT, run_manifest["payload"]["collected_files"]["report_htm"]["dest_path"])
    checks["report_file_exists"] = os.path.isfile(report_path)
    checks["report_hash_matches_manifest"] = (
        file_sha256(report_path) == run_manifest["payload"]["collected_files"]["report_htm"]["sha256"]
    )
    with open(report_path, encoding="utf-16", errors="ignore") as f:
        report_text = f.read()

    def extract_after(label_substr, text):
        idx = text.find(label_substr)
        if idx < 0:
            return None
        m = re.search(r"<b>(.*?)</b>", text[idx: idx + 300])
        return m.group(1).strip() if m else None

    recomputed_total_trades = extract_after("Operazioni di Trading Totali", report_text)
    recomputed_quality = extract_after("dello Storico", report_text)
    checks["total_trades_recomputed_matches"] = recomputed_total_trades == p["observed_fact"]["total_trades_in_official_report"]
    checks["total_trades_is_zero"] = recomputed_total_trades == "0"
    checks["history_quality_recomputed_matches"] = recomputed_quality == p["observed_fact"]["history_quality"]
    checks["history_quality_is_100pct"] = recomputed_quality == "100% ticks reali"

    inputs_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Inputs.mqh")
    with open(inputs_file, encoding="utf-8") as f:
        inputs_src = f.read()
    checks["flag_default_is_false_in_real_code"] = (
        "input bool     InpStrat_VolBreakoutConfirmed = false;" in inputs_src
    )

    strategies_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    with open(strategies_file, encoding="utf-8") as f:
        strategies_src = f.read()
    checks["guard_condition_present_in_real_code"] = (
        "if(!InpStrat_VolBreakoutConfirmed || !NXS_SelectorAllows(56)) return s;" in strategies_src
    )

    # Ri-verifica che il flag non compaia in NESSUno dei tester config congelati precedenti
    prior_configs = [
        os.path.join(PHASE78G_DIR, "..", "phase7_8e", "volatility_breakout_final_data_freeze_v1.json"),
        os.path.join(PHASE78G_DIR, "..", "phase7_8f", "volatility_breakout_execution_config_audit_v1.json"),
    ]
    all_missing = True
    for cfg_path in prior_configs:
        cfg_doc = load_json(cfg_path)
        raw = str(cfg_doc)
        if "InpStrat_VolBreakoutConfirmed" in raw:
            all_missing = False
    checks["flag_absent_from_all_prior_frozen_configs"] = all_missing

    checks["no_verdict_computed_flag"] = p["no_verdict_computed_on_this_run"] is True
    checks["no_result_produced_flag"] = p["no_serious_validation_result_produced"] is True

    core_checks = {k: v for k, v in checks.items() if isinstance(v, bool)}
    all_passed = all(core_checks.values())
    verdict = "ROOT_CAUSE_CONFIRMED_MISCONFIGURATION" if all_passed else "ROOT_CAUSE_VERIFICATION_FAILED"
    return checks, verdict


def main():
    checks, verdict = verify()
    for k, v in checks.items():
        print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print(f"\nVERDICT: {verdict}")
    return verdict == "ROOT_CAUSE_CONFIRMED_MISCONFIGURATION"


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
