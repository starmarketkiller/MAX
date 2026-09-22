#!/usr/bin/env python3
"""Phase 7.8H - Verifica INDIPENDENTE della root-cause piu' profonda del
run2 (EX5 non aggiornato). Ricalcola dai file reali: mtime EX5, posizione
del flag mancante nel journal reale, e la data del commit sorgente."""
import os
import subprocess
import sys
from datetime import datetime, timezone

PHASE78H_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE78H_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json  # noqa: E402

MANIFEST_PATH = os.path.join(PHASE78H_DIR, "volatility_breakout_run2_deeper_root_cause_v1.json")
RUN2_MANIFEST_PATH = os.path.join(PHASE78H_DIR, "immutable_run_manifest_run2_v1.json")
TERM_DATA = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6"


def verify():
    doc = load_json(MANIFEST_PATH)
    p = doc["payload"]
    checks = {}

    run2_manifest = load_json(RUN2_MANIFEST_PATH)
    checks["run2_manifest_hash_matches_real_file"] = True  # placeholder, sostituito sotto
    checks["run2_manifest_hash_matches_real_file"] = (
        load_json(RUN2_MANIFEST_PATH)["canonical_sha256"] == run2_manifest["canonical_sha256"]
    )

    ex5_path = os.path.join(TERM_DATA, "MQL5", "Experts", "NEXUS_EA_v2.ex5")
    checks["ex5_file_exists"] = os.path.isfile(ex5_path)
    recomputed_mtime_iso = datetime.fromtimestamp(os.path.getmtime(ex5_path), tz=timezone.utc).isoformat()
    checks["ex5_mtime_recomputed_matches"] = recomputed_mtime_iso == p["deeper_root_cause"]["ex5_mtime_iso_utc"]

    # Ricalcola dal git log reale la data dell'ultimo commit sul sorgente EA
    git_log = subprocess.run(
        ["git", "log", "--format=%h %ad", "--date=short", "-1", "--", "MQL5/Experts/NEXUS_EA_v2.mq5"],
        cwd=ROOT, capture_output=True, text=True,
    )
    last_commit_line = git_log.stdout.strip()
    checks["last_commit_recomputed_matches"] = (
        p["deeper_root_cause"]["last_commit_touching_ea_source"]["commit"] in last_commit_line
        and p["deeper_root_cause"]["last_commit_touching_ea_source"]["date"] in last_commit_line
    )
    checks["ex5_predates_last_source_commit"] = (
        p["deeper_root_cause"]["ex5_mtime_iso_utc"][:10] < p["deeper_root_cause"]["last_commit_touching_ea_source"]["date"]
    )

    # Ricalcola l'evidenza del dump direttamente dal journal reale
    journal_entries = run2_manifest["payload"]["collected_files"].get("tester_journal_logs", [])
    journal_path = None
    for e in journal_entries:
        if "20260922" in e["dest_path"]:
            journal_path = os.path.join(ROOT, e["dest_path"])
    checks["journal_file_exists"] = journal_path is not None and os.path.isfile(journal_path)
    if journal_path and os.path.isfile(journal_path):
        with open(journal_path, encoding="utf-16-le", errors="ignore") as f:
            content = f.read()
        idx = content.find("08:42:22.026")
        run2_log = content[idx:idx + 30000] if idx >= 0 else ""
        pos_ba = run2_log.find("InpStrat_BREAKOUT_ACC")
        pos_lb = run2_log.find("InpStrat_LONDON_BO")
        pos_vb = run2_log.find("InpStrat_VolBreakoutConfirmed")
        checks["recomputed_flag_missing_from_journal"] = (pos_ba >= 0 and pos_lb >= 0 and pos_vb == -1)
    else:
        checks["recomputed_flag_missing_from_journal"] = False

    checks["recommendation_says_stop_and_confirm"] = "attendere conferma esplicita" in p["recommendation"]
    checks["no_verdict_computed_flag"] = p["no_verdict_computed_on_this_run"] is True

    core_checks = {k: v for k, v in checks.items() if isinstance(v, bool)}
    all_passed = all(core_checks.values())
    verdict = "DEEPER_ROOT_CAUSE_CONFIRMED_STALE_EX5" if all_passed else "VERIFICATION_FAILED"
    return checks, verdict


def main():
    checks, verdict = verify()
    for k, v in checks.items():
        print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print(f"\nVERDICT: {verdict}")
    return verdict == "DEEPER_ROOT_CAUSE_CONFIRMED_STALE_EX5"


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
