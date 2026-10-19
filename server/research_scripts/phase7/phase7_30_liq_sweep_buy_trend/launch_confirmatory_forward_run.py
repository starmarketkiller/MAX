#!/usr/bin/env python3
"""Phase 7.30 — prepare/launch confirmatory forward MT5 isolation run.

Window: 2026.09.28 → 2026.10.19 (after Phase 7.25 OOS end; before any new
parameter look). Same harness identity as Phase 7.23/7.25 (selector 7,
GOLD, H4, fixed lot 0.01, ResearchMode).

Arm B (BUY + SMA200) is applied in analyze_confirmatory_forward.py — the
EA still runs the bidirectional recipe so identity matches prior runs.

Requires Windows + MT5 paths from nxs_research_run_harness.py.
On Linux/cloud: --prepare-only writes ini+manifest and exits without launch.
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

PREREG_REL = "server/research_scripts/phase7/phase7_30_liq_sweep_buy_trend/preregistration_v1.json"
RUN_DIR = os.path.join(PHASE_DIR, "runs", "liq_sweep_confirmatory_forward")
PERIOD = ("2026.09.28", "2026.10.19")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare-only", action="store_true",
                    help="Write ini+manifest only (no Tester launch). Default on non-Windows.")
    ap.add_argument("--force-launch", action="store_true",
                    help="Attempt Tester launch even if terminal exe missing (will fail).")
    args = ap.parse_args()

    prereg_sha = assert_frozen_spec_committed_before_run(ROOT, PREREG_REL)
    with open(os.path.join(ROOT, PREREG_REL), encoding="utf-8") as f:
        prereg = json.load(f)["payload"]

    os.makedirs(RUN_DIR, exist_ok=True)
    manifest, manifest_path, ini_path = build_ini(
        run_dir=RUN_DIR,
        strategy_identity="LIQ_SWEEP",
        selector=7,
        symbol="GOLD",
        period=PERIOD,
        chart_period="H4",
        fixed_lot=0.01,
        leverage=100,
        extra_inputs={
            # provenance tag for this hypothesis (EA ignores unknown? only known inputs)
            # Keep only known Inp* keys — harness already sets BuildGitCommit.
        },
    )
    manifest["hypothesis_id"] = prereg["hypothesis_id"]
    manifest["prereg_commit_sha"] = prereg_sha
    manifest["params_sha256"] = prereg["params_sha256"]
    manifest["confirmatory"] = True
    manifest["arm_B_filter_applied_in"] = "analyze_confirmatory_forward.py"
    manifest["prepared_at_utc"] = datetime.now(timezone.utc).isoformat()
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=True)

    print(f"run_id: {manifest['run_id']}")
    print(f"ini: {ini_path}")
    print(f"manifest: {manifest_path}")
    print(f"prereg_sha: {prereg_sha[:12]}")
    print(f"period: {PERIOD[0]} .. {PERIOD[1]}")

    is_windows = os.name == "nt"
    can_launch = is_windows and os.path.exists(TERMINAL_EXE)
    prepare_only = args.prepare_only or (not can_launch and not args.force_launch)

    status_path = os.path.join(PHASE_DIR, "confirmatory_run_status_v1.json")
    if prepare_only:
        status = {
            "status": "PREPARED_AWAITING_WINDOWS_MT5",
            "reason": (
                "Cloud/Linux agent has no MetaTrader 5 terminal. "
                "INI+manifest are ready; run launch on the research Windows PC "
                "(see RUNBOOK_CONFIRMATORY_WINDOWS.md)."
            ),
            "run_id": manifest["run_id"],
            "manifest_path": manifest_path,
            "ini_path": ini_path,
            "hypothesis_id": prereg["hypothesis_id"],
            "prereg_commit_sha": prereg_sha,
            "period": list(PERIOD),
            "expected_n_note": (
                "OOS rate ~2 trades/month ⇒ ~3-week window likely yields 0–2 closes; "
                "decision will almost certainly be INSUFFICIENT_EVIDENCE (min_n=30). "
                "Still required as first confirmatory sample under the frozen prereg."
            ),
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2, ensure_ascii=True)
        print(f"status: {status['status']}")
        print(f"wrote {status_path}")
        return 0

    manifest = launch(manifest, manifest_path)
    status = {
        "status": "LAUNCHED",
        "run_id": manifest["run_id"],
        "manifest_path": manifest_path,
        "dest_ini": manifest.get("dest_ini"),
        "hypothesis_id": prereg["hypothesis_id"],
        "prereg_commit_sha": prereg_sha,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "next": "Wait for Tester finish, then: python collect_confirmatory_forward_run.py",
    }
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, ensure_ascii=True)
    print("Tester launched. After completion run collect_confirmatory_forward_run.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
