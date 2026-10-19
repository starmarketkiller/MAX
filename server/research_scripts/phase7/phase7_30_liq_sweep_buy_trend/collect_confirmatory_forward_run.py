#!/usr/bin/env python3
"""Phase 7.30 — collect confirmatory forward run after Tester finishes.

Run on the Windows research PC (paths from nxs_research_run_harness.py).
Verify Tester is idle (tasklist / log) before calling this.
"""
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

RUN_DIR = os.path.join(PHASE_DIR, "runs", "liq_sweep_confirmatory_forward")
STATUS_PATH = os.path.join(PHASE_DIR, "confirmatory_run_status_v1.json")


def main() -> int:
    candidates = sorted(glob.glob(os.path.join(RUN_DIR, "*.manifest.json")))
    if not candidates:
        print("No confirmatory manifest found. Run launch_confirmatory_forward_run.py first.")
        return 1
    manifest_path = candidates[-1]
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    if not manifest.get("confirmatory"):
        print(f"WARNING: latest manifest lacks confirmatory=true: {manifest_path}")

    manifest = collect_after_run(manifest, manifest_path)
    status = {
        "status": "COLLECTED" if manifest.get("status") == "COLLECTED" else manifest.get("status"),
        "run_id": manifest.get("run_id"),
        "manifest_path": manifest_path,
        "trades_csv_dest": manifest.get("trades_csv_dest"),
        "certificate_dest": manifest.get("certificate_dest"),
        "reconciliation": manifest.get("reconciliation"),
        "warnings": manifest.get("warnings"),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "next": "python analyze_confirmatory_forward.py  (refresh D1 CSV if needed)",
    }
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=True)

    print(f"status: {manifest.get('status')}")
    print(f"trades_csv_dest: {manifest.get('trades_csv_dest')}")
    print(f"certificate_dest: {manifest.get('certificate_dest')}")
    print(f"reconciliation: {manifest.get('reconciliation')}")
    print(f"warnings: {manifest.get('warnings')}")
    print(f"wrote {STATUS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
