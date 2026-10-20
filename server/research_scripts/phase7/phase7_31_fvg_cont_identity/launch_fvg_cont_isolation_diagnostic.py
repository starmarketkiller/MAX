#!/usr/bin/env python3
"""Phase 7.31 — PREPARE-ONLY package for next-step FVG_CONT MT5 isolation.

Does NOT claim this launch is under a frozen MT5 economic prereg yet.
Identity audit decision ISOLATION_READY gates *feasibility*; a separate
hypothesis_id must be preregistered before treating trades as confirmatory.

Default: --prepare-only on non-Windows. Period left long enough to matter
(2023.10.02–2026.06.30 mirrors LIQ_SWEEP diagnostic density window) — human
must still commit a diagnostic prereg before launch-for-evidence.
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
from nxs_research_run_harness import TERMINAL_EXE, build_ini  # noqa: E402

RUN_DIR = os.path.join(PHASE_DIR, "runs", "fvg_cont_isolation_diagnostic")
# Dense historical window for *diagnostic* density (not the thin 7.30 confirmatory)
PERIOD = ("2023.10.02", "2026.06.30")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare-only", action="store_true")
    args = ap.parse_args()

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
    manifest["phase"] = "7.31"
    manifest["note"] = (
        "PREPARE_ONLY_PACKAGE — do not treat as confirmatory until a dedicated "
        "MT5 diagnostic prereg is committed (identity audit only approved isolation)."
    )
    manifest["identity_hypothesis_id"] = "FVG-CONT-IDENTITY-ISOLATION-001"
    manifest["economic_prereg_required_before_launch_for_evidence"] = True
    manifest["prepared_at_utc"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)

    status = {
        "status": "PREPARED_PACKAGE_AWAITING_MT5_DIAGNOSTIC_PREREG",
        "run_id": manifest["run_id"],
        "ini_path": ini_path,
        "manifest_path": manifest_path,
        "selector": 8,
        "period": list(PERIOD),
        "warning": (
            "Launching Tester now without a new economic/diagnostic prereg commit "
            "is allowed for smoke only; results must be labeled NON_PROMOTABLE / "
            "UNPREREGISTERED until that prereg exists."
        ),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    status_path = os.path.join(PHASE_DIR, "isolation_prepare_status_v1.json")
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=True)

    print(f"run_id: {manifest['run_id']}")
    print(f"status: {status['status']}")
    print(f"ini: {ini_path}")
    if args.prepare_only or os.name != "nt" or not os.path.exists(TERMINAL_EXE):
        return 0
    print("Refusing auto-launch without economic prereg. Use --prepare-only path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
