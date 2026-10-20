#!/usr/bin/env python3
"""Phase 7.34 — confirmatory forward MT5 under frozen FVG-CONT-HABITAT-RM-001.

Window: 2026.07.01 → 2026.10.19 (after Phase 7.32 diagnostic end 2026.06.30).
~3.5 months H4 — longer than the LIQ_SWEEP 3-week confirmatory that yielded n=0.
Expected n still likely <30 → INSUFFICIENT_EVIDENCE is an allowed honest outcome.

Arm B (BUY-only) + regime C applied in analyze_confirmatory_forward.py.
EA runs bidirectional selector=8 so identity matches Phase 7.32.
"""
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

PREREG_REL = "server/research_scripts/phase7/phase7_33_fvg_cont_habitat/preregistration_v1.json"
RUN_DIR = os.path.join(PHASE_DIR, "runs", "fvg_cont_confirmatory_forward")
PERIOD = ("2026.07.01", "2026.10.19")


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
        selector=8,
        symbol="GOLD",
        period=PERIOD,
        chart_period="H4",
        fixed_lot=0.01,
        leverage=100,
    )
    manifest["hypothesis_id"] = prereg["hypothesis_id"]
    manifest["prereg_commit_sha"] = prereg_sha
    manifest["params_sha256"] = prereg["params_sha256"]
    manifest["confirmatory"] = True
    manifest["phase"] = "7.34"
    manifest["arm_B_filter_applied_in"] = "analyze_confirmatory_forward.py"
    manifest["prepared_at_utc"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)

    status_path = os.path.join(PHASE_DIR, "confirmatory_run_status_v1.json")
    can_launch = os.name == "nt" and os.path.exists(TERMINAL_EXE)
    prepare_only = args.prepare_only or (not can_launch and not args.force_launch)

    if prepare_only:
        status = {
            "status": "PREPARED_AWAITING_WINDOWS_MT5",
            "reason": (
                "Cloud/Linux has no MT5. Run launch on PC-MT5 "
                "(see RUNBOOK_CONFIRMATORY_WINDOWS.md)."
            ),
            "run_id": manifest["run_id"],
            "manifest_path": manifest_path,
            "ini_path": ini_path,
            "hypothesis_id": prereg["hypothesis_id"],
            "prereg_commit_sha": prereg_sha,
            "period": list(PERIOD),
            "expected_n_note": (
                "Diagnostic density ~2.5 trades/month ⇒ ~3.5 months ≈ 8–10 closes; "
                "n_B likely still <30 → INSUFFICIENT_EVIDENCE is the expected honest "
                "label, but this is the first confirmatory sample under the frozen prereg."
            ),
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2, ensure_ascii=True)
        print(f"status: {status['status']}")
        print(f"run_id: {manifest['run_id']}")
        print(f"period: {PERIOD[0]} .. {PERIOD[1]}")
        print(f"prereg_sha: {prereg_sha[:12]}")
        return 0

    manifest = launch(manifest, manifest_path)
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({
            "status": "LAUNCHED",
            "run_id": manifest["run_id"],
            "manifest_path": manifest_path,
            "hypothesis_id": prereg["hypothesis_id"],
            "prereg_commit_sha": prereg_sha,
            "next": "Wait Tester → collect_confirmatory_forward_run.py",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2, ensure_ascii=True)
    print("Tester launched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
