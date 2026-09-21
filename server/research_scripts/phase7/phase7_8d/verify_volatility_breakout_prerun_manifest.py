#!/usr/bin/env python3
"""Phase 7.8D - Verifica indipendente del PRE-RUN MANIFEST.

Ricontrolla, RI-DERIVANDO dai campi grezzi (non fidandosi del blocco
'seal_verification' gia' scritto dal builder), le condizioni richieste:
  - tutti i campi richiesti popolati
  - hash validi (ricalcolati sui file reali, non copiati)
  - ordinamento date valido
  - FRESH/OBSERVED non sovrapposte
  - T1/T2/T3 partizionano ESATTAMENTE la finestra FRESH
  - gli hash di protocollo corrispondono agli artifact frozen reali
  - nessun campo di outcome presente

Uscita: PRE_RUN_SEAL_VERIFIED_READY_TO_RUN o PRE_RUN_SEAL_BLOCKED,
mai un'esecuzione del Serious validation."""
import datetime
import os
import sys

PHASE78D_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78D_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78D_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json  # noqa: E402

MANIFEST_PATH = os.path.join(PHASE78D_DIR, "volatility_breakout_serious_validation_prerun_manifest_v1.json")
AUTHORIZATION_PATH = os.path.join(PHASE7_DIR, "phase7_8c",
                                    "volatility_breakout_serious_3y_run_authorization_v1.json")
PREREG_PATH = os.path.join(PHASE7_DIR, "phase7_8b", "volatility_breakout_serious_3y_prereg_v1.json")
COST_MODEL_PATH = os.path.join(PHASE7_DIR, "policies", "cost_model_integration.json")
RAW_CSV = os.path.join(PHASE78D_DIR, "raw_coverage_audit", "nxs_volbrk_prerun_coverage.csv")
RAW_SUMMARY = os.path.join(PHASE78D_DIR, "raw_coverage_audit", "nxs_volbrk_prerun_summary.txt")


def iso_parse(s):
    return datetime.datetime.fromisoformat(s)


def verify():
    doc = load_json(MANIFEST_PATH)
    p = doc["payload"]
    checks = {}

    # ---- 1. Campi richiesti popolati ----
    tw = p["temporal_windows"]
    di = p["dataset_identity"]
    pp = p["protocol_identity_pins"]
    required_present = all([
        tw["TOTAL_TEST_WINDOW"]["start"], tw["TOTAL_TEST_WINDOW"]["end"],
        tw["PRIMARY_FRESH_VERDICT_WINDOW"]["start"], tw["PRIMARY_FRESH_VERDICT_WINDOW"]["end"],
        tw["PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW"]["start"], tw["PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW"]["end"],
        di["symbol"], di["timeframe"], di["broker_server"], di["account_login"], di["tester_model"],
        di["broker_timezone_offset_convention"], di["history_synchronization_timestamp_server"],
        pp["strategy_frozen_commit"], pp["prereg_canonical_hash"], pp["authorization_7_8c_canonical_hash"],
        pp["cost_model_hash"],
    ])
    checks["all_required_fields_populated"] = required_present

    # ---- 2. Hash validi - RICALCOLATI, non copiati dal payload ----
    hr = p["dataset_hash_representation"]
    hashes_valid = (
        hr["coverage_csv_sha256"] == file_sha256(RAW_CSV) and
        hr["coverage_summary_sha256"] == file_sha256(RAW_SUMMARY) and
        pp["cost_model_hash"] == file_sha256(COST_MODEL_PATH)
    )
    checks["hashes_valid_recomputed_independently"] = hashes_valid

    # ---- 3. Ordinamento date valido ----
    total_start = iso_parse(tw["TOTAL_TEST_WINDOW"]["start"])
    total_end = iso_parse(tw["TOTAL_TEST_WINDOW"]["end"])
    fresh_start = iso_parse(tw["PRIMARY_FRESH_VERDICT_WINDOW"]["start"])
    fresh_end = iso_parse(tw["PRIMARY_FRESH_VERDICT_WINDOW"]["end"])
    observed_start = iso_parse(tw["PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW"]["start"])
    observed_end = iso_parse(tw["PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW"]["end"])
    tail_start = iso_parse(tw["NEWLY_ELAPSED_TAIL_SEGMENT"]["start"])
    tail_end = iso_parse(tw["NEWLY_ELAPSED_TAIL_SEGMENT"]["end"])
    date_ordering_valid = (
        total_start == fresh_start and fresh_end == observed_start and
        observed_end == tail_start and tail_end == total_end and
        total_start < fresh_end < observed_end < total_end
    )
    checks["date_ordering_valid"] = date_ordering_valid

    # ---- 4. FRESH/OBSERVED non sovrapposte ----
    checks["fresh_observed_non_overlapping"] = fresh_end <= observed_start

    # ---- 5. T1/T2/T3 partizionano ESATTAMENTE la finestra FRESH ----
    t1_start, t1_end = iso_parse(tw["T1"]["start"]), iso_parse(tw["T1"]["end"])
    t2_start, t2_end = iso_parse(tw["T2"]["start"]), iso_parse(tw["T2"]["end"])
    t3_start, t3_end = iso_parse(tw["T3"]["start"]), iso_parse(tw["T3"]["end"])
    t1t2t3_valid = (
        t1_start == fresh_start and t1_end == t2_start and t2_end == t3_start and t3_end == fresh_end
    )
    checks["t1_t2_t3_exact_partition"] = t1t2t3_valid
    durations = [(t1_end - t1_start).days, (t2_end - t2_start).days, (t3_end - t3_start).days]
    checks["t1_t2_t3_durations_approximately_equal"] = max(durations) - min(durations) <= 1

    # ---- 6. Hash di protocollo corrispondono agli artifact frozen REALI ----
    auth_doc = load_json(AUTHORIZATION_PATH)
    prereg_doc = load_json(PREREG_PATH)
    protocol_hashes_correspond = (
        pp["authorization_7_8c_canonical_hash"] == auth_doc["canonical_sha256"] and
        pp["prereg_canonical_hash"] == prereg_doc["canonical_sha256"]
    )
    checks["protocol_hashes_correspond_to_real_frozen_artifacts"] = protocol_hashes_correspond

    # ---- 7. Nessun campo di outcome presente (scansione ricorsiva delle chiavi) ----
    forbidden_keys = {"trade_count", "profit_factor", "pf", "expectancy", "win_rate", "winrate",
                       "drawdown", "max_drawdown", "buy_performance", "sell_performance",
                       "yearly_performance", "net_profit", "sharpe"}

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

    forbidden_found = scan_keys(p)
    checks["no_outcome_fields_present"] = len(forbidden_found) == 0
    checks["forbidden_keys_found"] = sorted(forbidden_found)

    all_passed = all(v for k, v in checks.items() if k != "forbidden_keys_found")
    verdict = "PRE_RUN_SEAL_VERIFIED_READY_TO_RUN" if all_passed else "PRE_RUN_SEAL_BLOCKED"

    return checks, verdict


def main():
    checks, verdict = verify()
    for k, v in checks.items():
        if k == "forbidden_keys_found":
            continue
        print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print(f"\nVERDICT: {verdict}")
    print("SERIOUS_VALIDATION_NOT_EXECUTED (questo script non esegue mai il backtest)")
    return verdict == "PRE_RUN_SEAL_VERIFIED_READY_TO_RUN"


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
