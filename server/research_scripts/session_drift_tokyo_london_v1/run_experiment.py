#!/usr/bin/env python3
"""Run SD-TOKYO-LONDON-001 on the research PC (Phase 7 ticks) or from M15 CSV.

    cd server/research_scripts
    python -m session_drift_tokyo_london_v1.run_experiment --split discovery_a --smoke-days 10
    python -m session_drift_tokyo_london_v1.run_experiment --split discovery_a
    python -m session_drift_tokyo_london_v1.run_experiment --split combined_discoveries

Cloud VMs without tick cache cannot produce outcomes; they can still load the
preregistration and run the synthetic unit tests.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

from . import prereg as prereg_mod
from .decision import decide
from .events import build_session_rows, tag_split
from .stats import summarize

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(HERE)
PHASE7_DECODED = os.path.join(RESEARCH, "phase7", "data_cache_new_period", "decoded")
PHASE6_DECODED = os.path.join(RESEARCH, "phase6", "data_cache_holdout", "decoded")
DATA_DIR = os.path.join(HERE, "data")
PREREG_PATH = os.path.join(HERE, "prereg_SD-TOKYO-LONDON-001.json")
CODE_FILES = (
    "events.py", "sessions.py", "stats.py", "decision.py", "prereg.py", "run_experiment.py",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit():
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def code_fingerprint():
    h = hashlib.sha256()
    for name in CODE_FILES:
        path = os.path.join(HERE, name)
        h.update(name.encode())
        h.update(sha256_file(path).encode())
    return h.hexdigest()


def load_bars_csv(path):
    """M15 CSV with at least: start, open, ask_open (epoch seconds or ISO)."""
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            start = raw.get("start") or raw.get("time_utc")
            if start is None:
                continue
            if start.isdigit() or (start.startswith("-") and start[1:].isdigit()):
                start_ts = int(start)
            else:
                start_ts = int(datetime.fromisoformat(start.replace("Z", "+00:00")).timestamp())
            minutes = int(float(raw.get("bar_minutes") or raw.get("minutes") or 15))
            bid_o = float(raw["open"])
            ask_o = float(raw.get("ask_open") or raw.get("ask") or bid_o)
            rows.append({
                "start": start_ts,
                "end": start_ts + minutes * 60,
                "open": bid_o,
                "high": float(raw.get("high", bid_o)),
                "low": float(raw.get("low", bid_o)),
                "close": float(raw.get("close", bid_o)),
                "ask_open": ask_o,
                "ask_high": float(raw.get("ask_high", ask_o)),
                "ask_low": float(raw.get("ask_low", ask_o)),
                "ask_close": float(raw.get("ask_close", ask_o)),
                "n_ticks": int(float(raw.get("n_ticks") or 1)),
            })
    rows.sort(key=lambda b: b["start"])
    return rows


def build_bars_from_ticks(start_ts, end_ts, max_spread, smoke_days=None):
    """Reuse behavior_lab tick→M15 builder. Requires Phase 7 decoded cache on disk."""
    sys.path.insert(0, RESEARCH)
    from behavior_lab_v1.bars import M15, build_bars  # noqa: WPS433
    from behavior_lab_v1.ticks import TickAudit, iter_ticks  # noqa: WPS433

    start = datetime.fromtimestamp(start_ts, tz=timezone.utc)
    end = datetime.fromtimestamp(end_ts, tz=timezone.utc) - timedelta(seconds=1)
    if smoke_days is not None:
        end = min(end, start + timedelta(days=smoke_days) - timedelta(seconds=1))
    audit = TickAudit(max_spread)
    missing = []
    roots = [PHASE7_DECODED, PHASE6_DECODED]
    if not any(os.path.isdir(r) for r in roots):
        raise FileNotFoundError(
            "Phase 7/6 decoded tick dirs missing. Run on the research PC or pass --bars-csv. "
            f"Expected under {PHASE7_DECODED}"
        )
    ticks = iter_ticks(roots, start, end, missing=missing)
    series = build_bars(ticks, [M15], audit=audit)
    return series[M15], audit.report(), missing


def run_split(prereg, split, bars, smoke=False):
    params = prereg["params"]
    prereg_mod.assert_split_avoids_exclusions(prereg, split)
    start_ts, end_ts = prereg_mod.split_window(prereg, split)
    rows = tag_split(build_session_rows(bars, params, start_ts, end_ts), split)
    summary = summarize(rows, params) if not smoke else {
        "n_closed": sum(1 for r in rows if r["status"] == "CLOSED"),
        "smoke": True,
    }
    return rows, summary, start_ts, end_ts


def write_outputs(run_dir, prereg, split, rows, summary, meta, decision=None):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump({
            "hypothesis_id": prereg["hypothesis_id"],
            "params_sha256": prereg["params_sha256"],
            "split": split,
            "evidence_ceiling": prereg["evidence_ceiling"],
            "summary": summary,
            "decision": decision,
            "meta": meta,
        }, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    if rows:
        path = os.path.join(run_dir, "events.csv")
        keys = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="SD-TOKYO-LONDON-001 runner")
    parser.add_argument(
        "--split",
        required=True,
        choices=list(prereg_mod.ALLOWED_SPLITS),
    )
    parser.add_argument("--smoke-days", type=int, default=None)
    parser.add_argument("--bars-csv", default=None, help="Prebuilt M15 bid/ask CSV")
    parser.add_argument("--prereg", default=PREREG_PATH)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    prereg = prereg_mod.load(args.prereg)
    prereg_mod.assert_split_avoids_exclusions(prereg, args.split)

    registry_path = os.path.join(DATA_DIR, "hypothesis_registry.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    registry = prereg_mod.check_hypothesis_registry(registry_path, prereg)

    t0 = time.perf_counter()
    audit = None
    missing = []
    if args.bars_csv:
        bars = load_bars_csv(args.bars_csv)
    else:
        # Load enough bars for the split (and +1 day for Tokyo→Tokyo comparator).
        start_ts, end_ts = prereg_mod.split_window(prereg, args.split)
        load_end = end_ts + 2 * 86400
        bars, audit, missing = build_bars_from_ticks(
            start_ts,
            load_end,
            prereg["params"]["tick_audit_max_spread"],
            smoke_days=args.smoke_days,
        )

    smoke = args.smoke_days is not None
    decision = None
    if args.split == "combined_discoveries" and not smoke:
        # Build A and B separately for sign falsifier, then combined stats.
        rows_a, sum_a, _, _ = run_split(prereg, "discovery_a", bars, smoke=False)
        rows_b, sum_b, _, _ = run_split(prereg, "discovery_b", bars, smoke=False)
        rows = tag_split(rows_a + rows_b, "combined_discoveries")
        summary = summarize(rows, prereg["params"])
        decision = decide(sum_a, sum_b, summary, rows, prereg["params"])
        summary["discovery_a"] = sum_a
        summary["discovery_b"] = sum_b
    else:
        rows, summary, _, _ = run_split(prereg, args.split, bars, smoke=smoke)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.out or os.path.join(DATA_DIR, "runs", f"{args.split}_{stamp}")
    meta = {
        "git_commit": git_commit(),
        "code_sha256": code_fingerprint(),
        "prereg_sha256": sha256_file(args.prereg),
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "bars_source": args.bars_csv or "phase7_ticks",
        "n_bars": len(bars),
        "missing_tick_days": missing[:20],
        "n_missing_tick_days": len(missing),
        "tick_audit": audit,
        "smoke_days": args.smoke_days,
        "evidence_ceiling": "EXPLORATORY_ONLY",
        "validated_claim": False,
    }
    write_outputs(run_dir, prereg, args.split, rows, summary, meta, decision=decision)

    registry[prereg["hypothesis_id"]]["runs"].append({
        "split": args.split,
        "at": stamp,
        "run_dir": run_dir,
        "params_sha256": prereg["params_sha256"],
        "smoke": smoke,
    })
    with open(registry_path, "w", encoding="utf-8") as handle:
        json.dump(registry, handle, indent=2)
        handle.write("\n")

    print(json.dumps({
        "run_dir": run_dir,
        "split": args.split,
        "n_closed": summary.get("n_closed"),
        "decision": (decision or {}).get("decision"),
        "evidence_ceiling": "EXPLORATORY_ONLY",
        "mean_net_return_usd": summary.get("mean_net_return_usd"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
