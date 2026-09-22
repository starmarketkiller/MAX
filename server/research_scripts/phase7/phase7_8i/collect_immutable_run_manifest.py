#!/usr/bin/env python3
"""Phase 7.8I - Raccoglie e hasha gli output RAW del terzo Serious
validation SUBITO dopo la fine del Tester, PRIMA di qualunque
interpretazione. I run 1 (7.8G) e 2 (7.8H) restano archiviati
separatamente e immutati - non toccati qui."""
import glob
import os
import shutil
import sys

PHASE78I_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78I_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

TERM_DATA = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6"
COMMON_FILES = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\Common\Files"
OUT_DIR = os.path.join(PHASE78I_DIR, "immutable_run_output")


def find_report():
    return glob.glob(os.path.join(TERM_DATA, "**", "volbrk_serious_3y_run3*"), recursive=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    collected = {}

    reports = find_report()
    for r in sorted(set(reports)):
        if os.path.isfile(r) and r.lower().endswith((".htm", ".html")):
            dest = os.path.join(OUT_DIR, os.path.basename(r))
            shutil.copy2(r, dest)
            collected["report_htm"] = {
                "dest_path": os.path.relpath(dest, ROOT).replace("\\", "/"),
                "sha256": file_sha256(dest), "size_bytes": os.path.getsize(dest),
            }
            break

    trades_csv = os.path.join(COMMON_FILES, "NEXUS_trades.csv")
    if os.path.isfile(trades_csv):
        dest = os.path.join(OUT_DIR, "NEXUS_trades_serious_3y_run3.csv")
        shutil.copy2(trades_csv, dest)
        collected["trade_log_csv"] = {
            "dest_path": os.path.relpath(dest, ROOT).replace("\\", "/"),
            "sha256": file_sha256(dest), "size_bytes": os.path.getsize(dest),
        }

    tester_logs_dir = os.path.join(TERM_DATA, "Tester", "logs")
    if os.path.isdir(tester_logs_dir):
        for fn in os.listdir(tester_logs_dir):
            src = os.path.join(tester_logs_dir, fn)
            if os.path.isfile(src):
                dest = os.path.join(OUT_DIR, f"tester_journal_{fn}")
                shutil.copy2(src, dest)
                collected.setdefault("tester_journal_logs", []).append({
                    "dest_path": os.path.relpath(dest, ROOT).replace("\\", "/"),
                    "sha256": file_sha256(dest), "size_bytes": os.path.getsize(dest),
                })

    ini_src = r"C:\Users\User\.claude\jobs\703d44b4\tmp\volbrk_serious_3y_run3.ini"
    if os.path.isfile(ini_src):
        dest = os.path.join(OUT_DIR, "volbrk_serious_3y_run3.ini")
        shutil.copy2(ini_src, dest)
        collected["tester_ini_used"] = {
            "dest_path": os.path.relpath(dest, ROOT).replace("\\", "/"), "sha256": file_sha256(dest),
        }

    ex5_path = os.path.join(TERM_DATA, "MQL5", "Experts", "NEXUS_EA_v2.ex5")
    src_path = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")
    ea_identity = {}
    if os.path.isfile(ex5_path):
        ea_identity["ex5_sha256"] = file_sha256(ex5_path)
        ea_identity["ex5_mtime"] = os.path.getmtime(ex5_path)
    if os.path.isfile(src_path):
        ea_identity["source_sha256"] = file_sha256(src_path)
    collected["ea_build_identity"] = ea_identity

    reseal_doc = load_json(os.path.join(PHASE78I_DIR, "volatility_breakout_atomic_reseal_before_run3_v1.json"))
    collected["atomic_reseal_before_run3_hash"] = reseal_doc["canonical_sha256"]

    prior_run1 = load_json(os.path.join(PHASE7_DIR, "phase7_8g", "immutable_run_manifest_v1.json"))
    prior_run2 = load_json(os.path.join(PHASE7_DIR, "phase7_8h", "immutable_run_manifest_run2_v1.json"))

    payload = {
        "phase": "7.8I", "artifact_role": "IMMUTABLE_RUN_MANIFEST_RUN3", "candidate_id": "VOLATILITY_BREAKOUT_CONFIRMED",
        "collected_before_any_interpretation": True,
        "collected_files": collected,
        "prior_runs_archived_reference": {
            "run1_7_8g": {"canonical_sha256": prior_run1["canonical_sha256"],
                          "classification": "TECHNICALLY_INVALID_ZERO_TRADE_RUN", "archived_and_unmodified": True},
            "run2_7_8h": {"canonical_sha256": prior_run2["canonical_sha256"],
                          "classification": "TECHNICAL_EXECUTION_FAILURE_STRATEGY_NEVER_INITIALIZED",
                          "archived_and_unmodified": True},
        },
        "no_verdict_computed_here": True,
    }
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE78I_DIR, "immutable_run_manifest_run3_v1.json")
    save_json(out_path, doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    for k, v in collected.items():
        print(f"  collected[{k}] = {'present' if v else 'MISSING'}")
    return doc


if __name__ == "__main__":
    main()
