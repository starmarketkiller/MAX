#!/usr/bin/env python3
"""Run BL-H4M15-IPC-001 on the research PC, where the Phase 7 tick files live.

    python -m behavior_lab_v1.run_experiment --split discovery --smoke-days 10
    python -m behavior_lab_v1.run_experiment --split discovery

(from server/research_scripts). --smoke-days limits the run to the first N
days of the split and writes no statistics: it only proves the data reads,
bars align and the pipeline runs end to end. Run it before the full split.

Refuses locked_validation and final_holdout. internal_validation reads go
through phase7/engine/validation_access_ledger.py, persisted in data/.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from . import prereg as prereg_mod
from .bars import H4, M15, build_bars, check_alignment, compare_with_reference_h4
from .events import run_family
from .sessions import dst_transition_check, gap_report
from .stats import breakdown, detector_health, funnel, stability, summarize
from .ticks import TickAudit, iter_ticks

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(HERE)
PHASE7_DECODED = os.path.join(RESEARCH, "phase7", "data_cache_new_period", "decoded")
PHASE6_DECODED = os.path.join(RESEARCH, "phase6", "data_cache_holdout", "decoded")
PHASE7_MANIFEST = os.path.join(RESEARCH, "phase7", "data_cache_new_period", "manifest.json")
EXPECTED_MANIFEST_SHA256 = "605249c671178c92c7a2a3e91a670f17c12ca4bea10576407292ccd99e64fbde"
DATA_DIR = os.path.join(HERE, "data")
PREREG = os.path.join(HERE, "prereg_BL-H4M15-IPC-001.json")
CODE_FILES = ("ticks.py", "bars.py", "sessions.py", "events.py", "stats.py", "prereg.py",
              "run_experiment.py")

sys.path.insert(0, os.path.join(RESEARCH, "phase7", "engine"))
from validation_access_ledger import ValidationAccessLedger, load_policy  # noqa: E402


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_check(path):
    if not os.path.exists(path):
        return {"present": False, "verdict": "MISSING"}
    actual = sha256_file(path)
    return {"present": True, "sha256": actual, "expected": EXPECTED_MANIFEST_SHA256,
            "verdict": "MATCH" if actual == EXPECTED_MANIFEST_SHA256 else "MISMATCH"}


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def persistent_ledger(path):
    policy = load_policy(os.path.join(RESEARCH, "phase7", "policies", "validation_access_policy_v1.json"))
    ledger = ValidationAccessLedger(policy)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            for record in json.load(handle):
                ledger.log.append(record)
                key = (record["candidate_id"], record["split"])
                ledger._counts[key] = ledger._counts.get(key, 0) + 1
    return ledger


def write_events(path, rows):
    fields = sorted({k for r in rows for k in r if k != "window"})
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: v for k, v in r.items() if k != "window"})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True)
    ap.add_argument("--smoke-days", type=int, default=0)
    ap.add_argument("--phase7-decoded", default=PHASE7_DECODED)
    ap.add_argument("--phase6-decoded", default=PHASE6_DECODED)
    ap.add_argument("--manifest", default=PHASE7_MANIFEST)
    ap.add_argument("--reference-h4", default=os.path.join(
        RESEARCH, "phase7", "phase7_1", "data", "xauusd_h4_bars_p71.csv"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    prereg = prereg_mod.load(PREREG)
    split_start, split_end, warmup_start = prereg_mod.split_window(prereg, args.split)
    smoke = args.smoke_days > 0
    if smoke:
        split_end = min(split_end, split_start + args.smoke_days * 86400)

    manifest = manifest_check(args.manifest)
    if manifest["verdict"] == "MISMATCH":
        raise SystemExit(f"tick manifest hash mismatch: {manifest}")

    os.makedirs(DATA_DIR, exist_ok=True)
    registry_path = os.path.join(DATA_DIR, "hypothesis_registry.json")
    registry = prereg_mod.check_hypothesis_registry(registry_path, prereg)
    run_id = f"{prereg['hypothesis_id']}_{args.split}_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    if smoke:
        run_id += f"_smoke{args.smoke_days}d"

    access = None
    if args.split == "internal_validation" and not smoke:
        ledger_path = os.path.join(DATA_DIR, "validation_access_log.json")
        ledger = persistent_ledger(ledger_path)
        access = ledger.record_access(prereg["hypothesis_id"], args.split, run_id,
                                      manifest.get("sha256") or "UNVERIFIED",
                                      purpose="BL-H4M15-IPC-001 internal validation",
                                      caller="behavior_lab_v1/run_experiment.py")
        with open(ledger_path, "w", encoding="utf-8") as handle:
            json.dump(ledger.export_log(), handle, indent=2)

    missing = []
    audit = TickAudit(prereg["params"]["tick_audit_max_spread"])
    start_dt = datetime.fromtimestamp(warmup_start, tz=timezone.utc)
    end_dt = datetime.fromtimestamp(split_end, tz=timezone.utc) - timedelta(seconds=1)
    ticks = ((ts, b, a) for ts, b, a in iter_ticks([args.phase7_decoded, args.phase6_decoded],
                                                   start_dt, end_dt, missing)
             if ts < split_end * 1000)
    bars = build_bars(ticks, [M15, H4], audit)
    m15, h4 = bars[M15], bars[H4]

    checks = {"tick_audit": audit.report(), "missing_day_files": missing,
              "alignment_mismatches": check_alignment(h4, m15)[:50],
              "m15_gaps": gap_report(m15, M15), "dst_signature": dst_transition_check(m15),
              "manifest": manifest}
    if os.path.exists(args.reference_h4):
        with open(args.reference_h4, newline="", encoding="utf-8") as handle:
            checks["reference_h4_mismatches"] = compare_with_reference_h4(h4, list(csv.DictReader(handle)))[:50]
    else:
        checks["reference_h4_mismatches"] = "REFERENCE_NOT_PRESENT"

    result = run_family(h4, m15, prereg["params"], split_start, split_end)
    out_dir = args.out or os.path.join(DATA_DIR, "runs", run_id)
    os.makedirs(out_dir, exist_ok=True)
    write_events(os.path.join(out_dir, "events.csv"), result["events"])
    summary = {
        "run_id": run_id, "hypothesis_id": prereg["hypothesis_id"], "split": args.split,
        "smoke": smoke, "split_start": split_start, "split_end": split_end,
        "prereg_sha256": sha256_file(PREREG), "params_sha256": prereg["params_sha256"],
        "code_sha256": {f: sha256_file(os.path.join(HERE, f)) for f in CODE_FILES},
        "git_commit": git_commit(), "validation_access": access, "data_checks": checks,
        "n_m15_bars": len(m15), "n_h4_bars": len(h4),
        "detector_health": detector_health(result),
        "funnel_events": funnel(result["events"]), "funnel_controls": funnel(result["controls"]),
    }
    if not smoke:
        events = result["events"]
        summary.update({
            "events": summarize(events), "controls": summarize(result["controls"]),
            "by_direction": breakdown(events, lambda r: "BUY" if r["direction"] == 1 else "SELL"),
            "by_session": breakdown(events, lambda r: r.get("session")),
            "stability": stability(events),
        })
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, default=str)
    registry[prereg["hypothesis_id"]]["runs"].append({"run_id": run_id, "split": args.split,
                                                       "smoke": smoke})
    with open(registry_path, "w", encoding="utf-8") as handle:
        json.dump(registry, handle, indent=2)
    print(json.dumps({"run_id": run_id, "out": out_dir, "tick_audit": checks["tick_audit"]["verdict"],
                      "alignment_mismatches": len(checks["alignment_mismatches"]),
                      "funnel_events": summary["funnel_events"]}, indent=2))
    return summary


if __name__ == "__main__":
    main()
