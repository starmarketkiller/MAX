#!/usr/bin/env python3
"""Phase 7.32 — launch/prepare FVG_CONT selector=8 isolation diagnostic."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))
PHASE723 = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_23")
sys.path.insert(0, PHASE723)
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7"))
from engine.preregistration_provenance_guard import (  # noqa: E402
    assert_frozen_spec_committed_before_run,
)
from nxs_research_run_harness import TERMINAL_EXE, build_ini, launch  # noqa: E402

PREREG_REL = (
    "server/research_scripts/phase7/phase7_32_fvg_cont_isolation_diagnostic/"
    "preregistration_v1.json"
)
RUN_DIR = os.path.join(PHASE_DIR, "runs", "fvg_cont_isolation_diagnostic")
PERIOD = ("2023.10.02", "2026.06.30")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--force-launch", action="store_true")
    args = ap.parse_args()

    prereg_sha = assert_frozen_spec_committed_before_run(ROOT, PREREG_REL)
    with open(os.path.join(ROOT, PREREG_REL), encoding="utf-8") as f:
        prereg = json.load(f)["payload"]

    os.makedirs(RUN_DIR, exist_ok=True)
    manifest, manifest_path, ini_path = build_ini(
        run_dir=RUN_DIR,
        strategy_identity="FVG_CONT",
        selector=int(prereg["params"]["selector"]),
        symbol=prereg["params"]["symbol"],
        period=PERIOD,
        chart_period=prereg["params"]["chart_period"],
        fixed_lot=float(prereg["params"]["fixed_lot"]),
        leverage=int(prereg["params"]["leverage"]),
    )
    manifest["hypothesis_id"] = prereg["hypothesis_id"]
    manifest["prereg_commit_sha"] = prereg_sha
    manifest["params_sha256"] = prereg["params_sha256"]
    manifest["diagnostic"] = True
    manifest["promotable"] = False
    manifest["prepared_at_utc"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)

    status_path = os.path.join(PHASE_DIR, "diagnostic_run_status_v1.json")
    can_launch = os.name == "nt" and os.path.exists(TERMINAL_EXE)
    prepare_only = args.prepare_only or (not can_launch and not args.force_launch)

    if prepare_only:
        status = {
            "status": "PREPARED_AWAITING_WINDOWS_MT5",
            "run_id": manifest["run_id"],
            "manifest_path": manifest_path,
            "ini_path": ini_path,
            "hypothesis_id": prereg["hypothesis_id"],
            "prereg_commit_sha": prereg_sha,
            "period": list(PERIOD),
            "selector": 8,
            "next": "On PC-MT5: python launch_diagnostic_run.py  then collect → analyze",
            "runbook": "RUNBOOK_DIAGNOSTIC_WINDOWS.md",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2, ensure_ascii=True)
        print(f"status: {status['status']}")
        print(f"run_id: {manifest['run_id']}")
        print(f"prereg_sha: {prereg_sha[:12]}")
        return 0

    manifest = launch(manifest, manifest_path)
    status = {
        "status": "LAUNCHED",
        "run_id": manifest["run_id"],
        "manifest_path": manifest_path,
        "hypothesis_id": prereg["hypothesis_id"],
        "prereg_commit_sha": prereg_sha,
        "next": "Wait Tester finish → python collect_diagnostic_run.py",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=True)
    print("Tester launched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
