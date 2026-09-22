#!/usr/bin/env python3
"""Phase 7.8I - Verifica INDIPENDENTE dell'atomic reseal prima del terzo
run. Ricalcola dai file reali su disco: i 27 hash tick, lo snapshot H4,
l'identita' ambiente (EA EX5/source nuovo, timezone), e le catene di
provenienza verso 7.8F/config di ricerca/preflight tecnico. Fallisce
chiuso su qualunque mismatch. MAI esegue il Serious validation."""
import os
import sys

PHASE78I_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78I_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

MANIFEST_PATH = os.path.join(PHASE78I_DIR, "volatility_breakout_atomic_reseal_before_run3_v1.json")
PRIOR_78F_PATH = os.path.join(PHASE7_DIR, "phase7_8f", "volatility_breakout_execution_config_audit_v1.json")
RESEARCH_CONFIG_PATH = os.path.join(PHASE78I_DIR, "volatility_breakout_research_config_v1.json")
TECH_PREFLIGHT_PATH = os.path.join(PHASE78I_DIR, "volatility_breakout_technical_preflight_v1.json")
TERMINAL_BASES_ROOT = (
    r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6\bases\XMGlobal-MT5 10"
)
TERM_DATA = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6"


def verify():
    doc = load_json(MANIFEST_PATH)
    p = doc["payload"]
    checks = {}

    prior_78f_doc = load_json(PRIOR_78F_PATH)
    research_config_doc = load_json(RESEARCH_CONFIG_PATH)
    preflight_doc = load_json(TECH_PREFLIGHT_PATH)

    checks["7_8f_hash_matches_real_file"] = p["source_artifacts_untouched"]["7_8f"]["canonical_sha256"] == prior_78f_doc["canonical_sha256"]
    checks["research_config_hash_matches_real_file"] = (
        p["source_artifacts_untouched"]["research_config"]["canonical_sha256"] == research_config_doc["canonical_sha256"]
    )
    checks["preflight_hash_matches_real_file"] = (
        p["source_artifacts_untouched"]["technical_preflight"]["canonical_sha256"] == preflight_doc["canonical_sha256"]
    )
    checks["preflight_verdict_is_pass"] = preflight_doc["payload"]["verdict"] == "TECHNICAL_EXECUTION_PREFLIGHT_PASS"

    waf = p["window_aware_fingerprint"]
    tick_entries = waf["tick_files"]["entries"]
    checks["tick_files_count_is_27"] = len(tick_entries) == 27
    mismatches = []
    for e in tick_entries:
        abs_path = os.path.join(TERMINAL_BASES_ROOT, *e["relative_path"].split("/"))
        if not os.path.isfile(abs_path) or file_sha256(abs_path) != e["sha256"] or os.path.getsize(abs_path) != e["size_bytes"]:
            mismatches.append(e["relative_path"])
    checks["all_tick_files_reverified_on_disk"] = len(mismatches) == 0
    checks["tick_files_mismatches"] = mismatches

    snap = waf["h4_bars_window_aware_snapshot"]
    snap_path = os.path.join(ROOT, snap["file"])
    checks["h4_snapshot_hash_matches_real_file"] = os.path.isfile(snap_path) and file_sha256(snap_path) == snap["sha256"]
    with open(snap_path, encoding="ansi", errors="strict") as f:
        lines = f.read().strip().splitlines()
    checks["h4_snapshot_last_bar_before_todate"] = lines[-1].split(",")[0] < "2026.03.01 00:00:00"
    checks["h4_snapshot_bar_count_matches"] = (len(lines) - 1) == snap["bar_count"]
    recomputed_combined = canonical_sha256({"tick_files": tick_entries, "h4_snapshot": {k: v for k, v in snap.items()}})
    checks["combined_fingerprint_hash_matches_seal"] = recomputed_combined == p["final_seal"]["window_aware_fingerprint_hash"]

    ei = p["environment_identity"]
    tz_path = os.path.join(ROOT, ei["tz_raw_file"])
    checks["tz_raw_hash_matches"] = os.path.isfile(tz_path) and file_sha256(tz_path) == ei["tz_raw_file_sha256"]
    with open(tz_path, encoding="utf-8") as f:
        tz_kv = dict(ln.split("=", 1) for ln in f.read().strip().splitlines() if "=" in ln)
    checks["tz_offset_recomputed_matches"] = (
        int(tz_kv["broker_utc_offset_seconds_TradeServer_minus_GMT"]) == ei["broker_utc_offset_seconds"] == 10800
    )
    ex5_path = os.path.join(TERM_DATA, "MQL5", "Experts", "NEXUS_EA_v2.ex5")
    checks["ea_ex5_hash_recomputed_matches"] = os.path.isfile(ex5_path) and file_sha256(ex5_path) == ei["ea_ex5_sha256"]
    checks["ea_ex5_matches_new_recompiled_hash"] = (
        ei["ea_ex5_sha256"] == research_config_doc["payload"]["recompile_evidence"]["new_ex5_sha256"]
    )
    src_path = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")
    checks["ea_source_hash_recomputed_matches"] = os.path.isfile(src_path) and file_sha256(src_path) == ei["ea_source_sha256"]
    checks["environment_hash_matches_seal"] = canonical_sha256(ei) == p["final_seal"]["environment_identity_hash"]

    tc = research_config_doc["payload"]["tester_execution_config_research"]
    checks["research_config_has_all_5_fields"] = all(
        f in tc["raw_text"] for f in ("InpResearchMode=true", "InpResearchExitMode=0",
                                        "InpResearchFixedLot=0.01", "InpStrat_VolBreakoutConfirmed=true",
                                        "InpProfileMultiTF=true"))
    checks["research_config_hash_matches_seal"] = tc["sha256"] == p["final_seal"]["research_tester_config_hash"]

    checks["seal_verification_all_true"] = all(v for v in p["seal_verification"].values() if isinstance(v, bool))
    checks["not_executed_flag"] = p["serious_validation_not_executed"] is True
    checks["no_data_modified_flag"] = p["no_data_modified_or_resynced_in_this_phase"] is True

    core_checks = {k: v for k, v in checks.items() if isinstance(v, bool)}
    all_passed = all(core_checks.values())
    verdict = "ATOMIC_RESEAL_VERIFIED" if all_passed else "ATOMIC_RESEAL_BLOCKED"
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
    return verdict == "ATOMIC_RESEAL_VERIFIED"


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
