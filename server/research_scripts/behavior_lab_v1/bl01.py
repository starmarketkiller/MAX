#!/usr/bin/env python3
"""Phase BL-01: real-data validation of BL-H4M15-IPC-001, in one command.

    cd server/research_scripts
    python -m behavior_lab_v1.bl01

1. preflight: commit and working tree of the lab code, dependencies, tick
   manifest hash, discovery day files, Phase 6 warmup files;
2. smoke run on the first 10 discovery days; mandatory STOP if the tick audit
   fails, any H4/M15 or reference-H4 mismatch appears, or the pipeline raises
   (a causality assertion included);
3. full discovery run, frozen parameters;
4. report.md next to the run outputs, with the pre-declared decision.

Never reads locked_validation or final_holdout and never runs
internal_validation: that is a separate, explicit command after a GO.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timedelta, timezone

from . import run_experiment
from .prereg import load as load_prereg
from .report import render
from .ticks import day_path, iter_days

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "data", "bl01")
BRANCH = "claude/xau-behavior-lab-h4m15"


def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"ERROR: {exc}"


def preflight(phase7_decoded, phase6_decoded, manifest, expect_commit=None):
    prereg = load_prereg(run_experiment.PREREG)
    disc = prereg["splits"]["discovery"]
    start = datetime.fromisoformat(disc["start_utc"])
    end = datetime.fromisoformat(disc["end_utc"]) - timedelta(days=1)
    warm = datetime.fromisoformat(disc["warmup_start_utc"])

    def count(root, a, b):
        days = list(iter_days(a, b))
        present = [d for d in days if os.path.exists(day_path(root, d))]
        weekday_missing = [d.strftime("%Y-%m-%d") for d in days
                           if d.weekday() < 5 and not os.path.exists(day_path(root, d))]
        return {"days": len(days), "present": len(present), "weekday_missing": weekday_missing[:30],
                "n_weekday_missing": len(weekday_missing)}

    head = _git("rev-parse", "HEAD")
    deps = {}
    for mod in ("numpy", "pandas", "scipy", "tzdata"):
        try:
            deps[mod] = getattr(__import__(mod), "__version__", "present")
        except ImportError:
            deps[mod] = None
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo("America/New_York")
        deps["zoneinfo_new_york"] = True
    except Exception:  # noqa: BLE001 - any failure means DST handling is unusable
        deps["zoneinfo_new_york"] = False
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": head, "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "remote_branch_head": _git("rev-parse", f"origin/{BRANCH}"),
        "expected_commit": expect_commit,
        "lab_code_uncommitted_changes": _git("status", "--porcelain", "--", HERE),
        "dependencies": deps,
        "manifest": run_experiment.manifest_check(manifest),
        "discovery_files": count(phase7_decoded, start, end),
        "warmup_files_phase6": count(phase6_decoded, warm, start - timedelta(days=1)),
        "params_sha256": prereg["params_sha256"],
    }
    blockers = []
    if result["lab_code_uncommitted_changes"]:
        blockers.append("behavior_lab_v1 has uncommitted changes: the code run would not be the PR code")
    if expect_commit and not head.startswith(expect_commit):
        blockers.append(f"HEAD {head} is not the expected commit {expect_commit}")
    if result["manifest"]["verdict"] != "MATCH":
        blockers.append(f"tick manifest {result['manifest']['verdict']}")
    if result["discovery_files"]["present"] == 0:
        blockers.append("no discovery tick files found")
    if not deps["zoneinfo_new_york"]:
        blockers.append("zoneinfo cannot load America/New_York (install tzdata)")
    result["blockers"] = blockers
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase7-decoded", default=run_experiment.PHASE7_DECODED)
    ap.add_argument("--phase6-decoded", default=run_experiment.PHASE6_DECODED)
    ap.add_argument("--manifest", default=run_experiment.PHASE7_MANIFEST)
    ap.add_argument("--expect-commit", default=None)
    ap.add_argument("--smoke-days", type=int, default=10)
    ap.add_argument("--skip-full", action="store_true")
    args = ap.parse_args(argv)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = os.path.join(RUNS, stamp)
    os.makedirs(out_root, exist_ok=True)
    common = ["--phase7-decoded", args.phase7_decoded, "--phase6-decoded", args.phase6_decoded,
              "--manifest", args.manifest]

    pre = preflight(args.phase7_decoded, args.phase6_decoded, args.manifest, args.expect_commit)
    smoke = full = None
    stop = list(pre["blockers"])
    if not stop:
        try:
            smoke = run_experiment.main(["--split", "discovery", "--smoke-days", str(args.smoke_days),
                                         "--out", os.path.join(out_root, "smoke"), *common])
        except Exception:  # noqa: BLE001 - recorded and reported, never swallowed
            stop.append("smoke run raised:\n" + traceback.format_exc())
        if smoke is not None and smoke["decision"]["decision"] != "SMOKE_PASSED":
            stop.extend(smoke["decision"]["reasons"])
    if not stop and not args.skip_full:
        try:
            full = run_experiment.main(["--split", "discovery", "--out", os.path.join(out_root, "discovery"),
                                        *common])
        except Exception:  # noqa: BLE001
            stop.append("discovery run raised:\n" + traceback.format_exc())

    with open(os.path.join(out_root, "preflight.json"), "w", encoding="utf-8") as handle:
        json.dump(pre, handle, indent=2)
    report = render(pre, smoke, full, stop)
    path = os.path.join(out_root, "report.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(report)
    print(f"\nBL-01 report: {path}")
    return 1 if stop else 0


if __name__ == "__main__":
    sys.exit(main())
