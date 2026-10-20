#!/usr/bin/env python3
"""Phase 7.34 — collect confirmatory FVG_CONT run after Tester (Windows)."""
from __future__ import annotations

import glob
import json
import os
import sys
from datetime import datetime, timezone

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))
PHASE723 = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_23")
sys.path.insert(0, PHASE723)
from nxs_research_run_harness import collect_after_run  # noqa: E402

RUN_DIR = os.path.join(PHASE_DIR, "runs", "fvg_cont_confirmatory_forward")
STATUS_PATH = os.path.join(PHASE_DIR, "confirmatory_run_status_v1.json")


def _latest_manifest(run_dir: str) -> str | None:
    """Pick the run that was actually launched, not the lexicographic filename.

    Cloud prepare writes a manifest whose config hash sorts after the Windows
    run hash. ``sorted(glob)[-1]`` therefore collected the unlaunched prepare
    file (run_dir ``/workspace/...``) and failed to copy trades on this PC.
    """
    launched = []
    prepared = []
    for path in glob.glob(os.path.join(run_dir, "*.manifest.json")):
        try:
            with open(path, encoding="utf-8") as f:
                manifest = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not (
            manifest.get("confirmatory")
            or manifest.get("hypothesis_id") == "FVG-CONT-HABITAT-RM-001"
        ):
            continue
        if manifest.get("start_time_utc"):
            launched.append((manifest["start_time_utc"], path))
        else:
            prepared.append((manifest.get("prepared_at_utc") or "", path))
    if launched:
        launched.sort()
        return launched[-1][1]
    if prepared:
        prepared.sort()
        return prepared[-1][1]
    return None


def main() -> int:
    chosen = _latest_manifest(RUN_DIR)
    if not chosen:
        print("No confirmatory manifest. Run launch_confirmatory_forward_run.py first.")
        return 1
    with open(chosen, encoding="utf-8") as f:
        manifest = json.load(f)
    manifest = collect_after_run(manifest, chosen)
    status = {
        "status": manifest.get("status"),
        "run_id": manifest.get("run_id"),
        "manifest_path": chosen,
        "trades_csv_dest": manifest.get("trades_csv_dest"),
        "certificate_dest": manifest.get("certificate_dest"),
        "reconciliation": manifest.get("reconciliation"),
        "warnings": manifest.get("warnings"),
        "next": "python analyze_confirmatory_forward.py --d1-csv <refreshed D1>",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=True)
    print(json.dumps({
        "status": status["status"],
        "run_id": status["run_id"],
        "trades_csv_dest": status["trades_csv_dest"],
        "reconciliation": status["reconciliation"],
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
