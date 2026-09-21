#!/usr/bin/env python3
"""Phase 7.8E - Verifica INDIPENDENTE del Final Data Freeze.

Ricalcola da zero (mai fidandosi del blocco 'seal_verification' gia'
scritto dal builder):
  - l'offset broker misurato (ri-letto dal file grezzo, ricalcolato)
  - l'hash del manifest dati (ri-costruito dai file .tkc/.hcc REALI su
    disco, non copiato dal payload)
  - l'hash della tester config
  - gli hash di protocollo (confrontati con gli artifact frozen reali)
  - i confini temporali (confrontati con 7.8D)

Fallisce chiuso (BLOCKED) se un solo file dati e' cambiato/mancante
rispetto al manifest, o se un solo hash non coincide. MAI esegue il
Serious validation."""
import os
import sys

PHASE78E_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78E_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78E_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

MANIFEST_PATH = os.path.join(PHASE78E_DIR, "volatility_breakout_final_data_freeze_v1.json")
PRIOR_MANIFEST_PATH = os.path.join(PHASE7_DIR, "phase7_8d",
                                     "volatility_breakout_serious_validation_prerun_manifest_v1.json")
TZ_MEASURE_PATH = os.path.join(PHASE7_DIR, "phase7_8d", "raw_coverage_audit", "nxs_volbrk_timezone_measure.txt")

TERMINAL_BASES_ROOT = (
    r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6\bases\XMGlobal-MT5 10"
)


def verify():
    doc = load_json(MANIFEST_PATH)
    p = doc["payload"]
    checks = {}

    # ---- 1. Timezone: ri-letto e ricalcolato dal file grezzo ----
    with open(TZ_MEASURE_PATH, encoding="utf-8") as f:
        tz_lines = [ln.strip() for ln in f if ln.strip()]
    tz_kv = dict(ln.split("=", 1) for ln in tz_lines if "=" in ln)
    recomputed_offset = int(tz_kv["broker_utc_offset_seconds_TradeServer_minus_GMT"])
    checks["timezone_offset_recomputed_matches_manifest"] = (
        recomputed_offset == p["timezone_measurement"]["broker_utc_offset_seconds"] == 10800
    )

    # ---- 2. Data manifest: ri-costruito dai file REALI su disco (fail-closed se mancano/cambiati) ----
    dm = p["data_manifest"]
    mismatches, missing_now = [], []
    for entry in dm["entries"]:
        abs_path = os.path.join(TERMINAL_BASES_ROOT, *entry["relative_path"].split("/"))
        if not os.path.isfile(abs_path):
            missing_now.append(entry["relative_path"])
            continue
        real_hash = file_sha256(abs_path)
        real_size = os.path.getsize(abs_path)
        if real_hash != entry["sha256"] or real_size != entry["size_bytes"]:
            mismatches.append({"file": entry["relative_path"], "manifest_sha256": entry["sha256"],
                                "current_sha256": real_hash, "manifest_size": entry["size_bytes"],
                                "current_size": real_size})
    checks["all_31_data_files_present_now"] = len(missing_now) == 0
    checks["all_data_files_unchanged_since_seal"] = len(mismatches) == 0
    checks["data_files_missing_now"] = missing_now
    checks["data_files_changed_since_seal"] = mismatches

    # ---- 3. Hash del manifest: ricalcolato dalla struttura reale, non copiato ----
    checks["data_manifest_hash_matches_seal"] = (
        canonical_sha256(dm) == p["dataset_hash_correction"]["data_manifest_canonical_sha256"]
    )

    # ---- 4. Tester config hash: ricalcolato ----
    tc = p["tester_execution_config_frozen_not_launched"]
    recomputed_tc_hash = canonical_sha256({"tester_config_text": tc["raw_text"]})
    checks["tester_config_hash_recomputed_matches"] = recomputed_tc_hash == tc["sha256"] == p["final_seal"]["tester_config_sha256"]
    checks["tester_config_not_launched"] = tc["not_launched"] is True

    # ---- 5. Hash di protocollo: confrontati con gli artifact frozen REALI ----
    prior_doc = load_json(PRIOR_MANIFEST_PATH)
    checks["previous_manifest_hash_matches_real_7_8d_file"] = (
        p["final_seal"]["previous_manifest_hash_7_8d"] == prior_doc["canonical_sha256"]
    )
    checks["prereg_hash_matches_seal"] = (
        p["final_seal"]["prereg_hash"] == prior_doc["payload"]["protocol_identity_pins"]["prereg_canonical_hash"]
    )
    checks["authorization_hash_matches_seal"] = (
        p["final_seal"]["authorization_7_8c_hash"] ==
        prior_doc["payload"]["protocol_identity_pins"]["authorization_7_8c_canonical_hash"]
    )

    # ---- 6. Confini temporali: confrontati con 7.8D reale ----
    tir = p["temporal_identity_recheck"]
    real_tw = prior_doc["payload"]["temporal_windows"]
    checks["temporal_windows_match_real_7_8d"] = all(
        tir[k] == real_tw[k] for k in ("TOTAL_TEST_WINDOW", "PRIMARY_FRESH_VERDICT_WINDOW",
                                         "PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW",
                                         "NEWLY_ELAPSED_TAIL_SEGMENT", "T1", "T2", "T3")
    )

    # ---- 7. Selector index: verificato contro il registro reale ----
    reg = load_json(os.path.join(ROOT, "contracts", "strategy-registry.json"))
    reg_entry = next(s for s in reg["strategies"] if s["strategy_id"] == "VOLATILITY_BREAKOUT_CONFIRMED")
    checks["selector_index_matches_real_registry"] = (
        f"InpStrategySelector={reg_entry['selector_index']}" in tc["raw_text"]
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
    verdict = "FINAL_PRE_RUN_SEAL_VERIFIED_READY_TO_EXECUTE" if all_passed else "FINAL_PRE_RUN_SEAL_BLOCKED"
    return checks, verdict


def main():
    checks, verdict = verify()
    for k, v in checks.items():
        if isinstance(v, bool):
            print(f"[{'PASS' if v else 'FAIL'}] {k}")
        else:
            print(f"[INFO] {k} = {v}")
    print(f"\nVERDICT: {verdict}")
    print("SERIOUS_VALIDATION_NOT_EXECUTED (questo script non esegue mai il backtest)")
    return verdict == "FINAL_PRE_RUN_SEAL_VERIFIED_READY_TO_EXECUTE"


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
