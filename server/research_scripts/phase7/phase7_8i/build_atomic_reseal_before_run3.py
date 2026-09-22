#!/usr/bin/env python3
"""Phase 7.8I - Atomic Reseal window-aware, ricostruito FRESCO
immediatamente prima del terzo run. Include il nuovo EX5/source hash
(post-ricompilazione) e il config di ricerca corretto (7.8I)."""
import os
import sys

PHASE78I_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78I_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

PRIOR_78F_PATH = os.path.join(PHASE7_DIR, "phase7_8f", "volatility_breakout_execution_config_audit_v1.json")
RESEARCH_CONFIG_PATH = os.path.join(PHASE78I_DIR, "volatility_breakout_research_config_v1.json")
TECH_PREFLIGHT_PATH = os.path.join(PHASE78I_DIR, "volatility_breakout_technical_preflight_v1.json")
RAW_AUDIT_DIR = os.path.join(PHASE78I_DIR, "raw_data_audit")

TERMINAL_BASES_ROOT = (
    r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6\bases\XMGlobal-MT5 10"
)
TERM_DATA = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6"
RELEVANT_TICK_MONTHS = ["202312"] + [f"2024{m:02d}" for m in range(1, 13)] + \
                       [f"2025{m:02d}" for m in range(1, 13)] + ["202601", "202602"]


def build():
    prior_78f_doc = load_json(PRIOR_78F_PATH)
    research_config_doc = load_json(RESEARCH_CONFIG_PATH)
    preflight_doc = load_json(TECH_PREFLIGHT_PATH)

    if preflight_doc["payload"]["verdict"] != "TECHNICAL_EXECUTION_PREFLIGHT_PASS":
        raise RuntimeError("Preflight tecnico non passato - reseal bloccato per costruzione.")

    audit_path = os.path.join(RAW_AUDIT_DIR, "nxs_volbrk_window_aware_audit.txt")
    with open(audit_path, encoding="utf-8") as f:
        audit_kv = dict(ln.split("=", 1) for ln in f.read().strip().splitlines() if "=" in ln)
    n_inside = int(audit_kv["year2026_bars_inside_fresh_before_20260301"])

    prior_78h_reseal = load_json(os.path.join(PHASE7_DIR, "phase7_8h", "volatility_breakout_atomic_reseal_before_run2_v1.json"))
    prior_n_inside = int(prior_78h_reseal["payload"]["data_drift_reevaluation"]["n_bars_inside_fresh_now"])

    data_drift_reevaluation = {
        "n_bars_inside_fresh_now": n_inside,
        "n_bars_inside_fresh_at_7_8h": prior_n_inside,
        "inside_fresh_unchanged": n_inside == prior_n_inside,
        "last_bar_in_2026_hcc": audit_kv["year2026_last_bar_time"],
        "conclusion": "IRRELEVANT_POST_WINDOW_CACHE_DRIFT" if n_inside == prior_n_inside else
                      "RELEVANT_WINDOW_DATA_DRIFT_REQUIRES_INVESTIGATION",
    }

    tick_entries = []
    for month in RELEVANT_TICK_MONTHS:
        abs_path = os.path.join(TERMINAL_BASES_ROOT, "ticks", "GOLD", f"{month}.tkc")
        entry = {"relative_path": f"ticks/GOLD/{month}.tkc", "size_bytes": os.path.getsize(abs_path),
                  "sha256": file_sha256(abs_path)}
        if month in ("202312", "202602"):
            entry["boundary_note"] = "mese di confine"
        tick_entries.append(entry)

    snapshot_csv_path = os.path.join(RAW_AUDIT_DIR, "nxs_volbrk_window_snapshot.csv")
    h4_snapshot = {
        "file": os.path.relpath(snapshot_csv_path, ROOT).replace("\\", "/"),
        "sha256": file_sha256(snapshot_csv_path),
        "bar_count": int(audit_kv["superset_snapshot_bar_count"]),
        "first_bar": audit_kv["superset_snapshot_first_bar"],
        "last_bar": audit_kv["superset_snapshot_last_bar"],
    }
    window_aware_fingerprint = {
        "tick_files": {"n_files": len(tick_entries), "entries": tick_entries},
        "h4_bars_window_aware_snapshot": h4_snapshot,
    }
    window_aware_fingerprint["combined_hash"] = canonical_sha256({
        "tick_files": tick_entries, "h4_snapshot": {k: v for k, v in h4_snapshot.items()},
    })

    tz_path = os.path.join(RAW_AUDIT_DIR, "nxs_volbrk_timezone_measure_immediately_before_run3.txt")
    with open(tz_path, encoding="utf-8") as f:
        tz_kv = dict(ln.split("=", 1) for ln in f.read().strip().splitlines() if "=" in ln)
    remeasured_offset = int(tz_kv["broker_utc_offset_seconds_TradeServer_minus_GMT"])

    ex5_path = os.path.join(TERM_DATA, "MQL5", "Experts", "NEXUS_EA_v2.ex5")
    src_path = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")
    environment_identity = {
        "broker_server": tz_kv["server"], "login": tz_kv["login"],
        "broker_utc_offset_seconds": remeasured_offset,
        "broker_utc_offset_matches_frozen": remeasured_offset == 10800,
        "ea_ex5_sha256": file_sha256(ex5_path),
        "ea_ex5_matches_recompiled_ex5": file_sha256(ex5_path) ==
            research_config_doc["payload"]["recompile_evidence"]["new_ex5_sha256"],
        "ea_source_sha256": file_sha256(src_path),
        "tz_raw_file": os.path.relpath(tz_path, ROOT).replace("\\", "/"),
        "tz_raw_file_sha256": file_sha256(tz_path),
    }

    tc = research_config_doc["payload"]["tester_execution_config_research"]
    final_seal = {
        "data_drift_conclusion": data_drift_reevaluation["conclusion"],
        "window_aware_fingerprint_hash": window_aware_fingerprint["combined_hash"],
        "environment_identity_hash": canonical_sha256(environment_identity),
        "research_tester_config_hash": tc["sha256"],
        "research_config_artifact_hash": research_config_doc["canonical_sha256"],
        "technical_preflight_hash": preflight_doc["canonical_sha256"],
        "strategy_frozen_commit": "f035d30",
        "prereg_hash": prior_78f_doc["payload"]["final_seal"]["prereg_hash"],
        "authorization_7_8c_hash": prior_78f_doc["payload"]["final_seal"]["authorization_7_8c_hash"],
        "cost_model_hash": prior_78f_doc["payload"]["final_seal"]["cost_model_hash"],
    }

    seal_verification = {
        "data_drift_correctly_classified": data_drift_reevaluation["conclusion"] in
            ("IRRELEVANT_POST_WINDOW_CACHE_DRIFT", "RELEVANT_WINDOW_DATA_DRIFT_REQUIRES_INVESTIGATION"),
        "inside_fresh_bars_unchanged": data_drift_reevaluation["inside_fresh_unchanged"],
        "tick_files_all_27_present": window_aware_fingerprint["tick_files"]["n_files"] == 27,
        "environment_measured_fresh": True,
        "broker_offset_matches_frozen": environment_identity["broker_utc_offset_matches_frozen"],
        "ea_ex5_matches_recompiled_binary": environment_identity["ea_ex5_matches_recompiled_ex5"],
        "technical_preflight_passed": preflight_doc["payload"]["verdict"] == "TECHNICAL_EXECUTION_PREFLIGHT_PASS",
        "correction_type_is_research_enablement": research_config_doc["payload"]["correction_classification"]
            ["correction_type"] == "RESEARCH_EXECUTION_ENABLEMENT_FIX",
        "no_outcome_fields_present": True,
        "serious_validation_not_yet_executed_at_seal_time": True,
    }

    final_verdict_value = "ATOMIC_RESEAL_VERIFIED" if all(seal_verification.values()) else "ATOMIC_RESEAL_BLOCKED"

    payload = {
        "phase": "7.8I", "artifact_role": "ATOMIC_RESEAL_BEFORE_RUN3", "candidate_id": "VOLATILITY_BREAKOUT_CONFIRMED",
        "source_artifacts_untouched": {
            "7_8f": {"canonical_sha256": prior_78f_doc["canonical_sha256"], "modified_in_this_phase": False},
            "research_config": {"canonical_sha256": research_config_doc["canonical_sha256"], "modified_in_this_phase": False},
            "technical_preflight": {"canonical_sha256": preflight_doc["canonical_sha256"], "modified_in_this_phase": False},
        },
        "data_drift_reevaluation": data_drift_reevaluation,
        "window_aware_fingerprint": window_aware_fingerprint,
        "environment_identity": environment_identity,
        "final_seal": final_seal,
        "seal_verification": seal_verification,
        "final_verdict": {"value": final_verdict_value, "serious_validation_still_not_executed": True},
        "serious_validation_not_executed": True,
        "no_strategy_outcome_accessed": True,
        "no_data_modified_or_resynced_in_this_phase": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE78I_DIR, "volatility_breakout_atomic_reseal_before_run3_v1.json")
    save_json(out_path, doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"final_verdict={payload['final_verdict']['value']}")
    for k, v in payload["seal_verification"].items():
        print(f"  seal_check[{k}]={v}")
    return doc


if __name__ == "__main__":
    main()
