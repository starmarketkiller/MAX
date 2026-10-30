#!/usr/bin/env python3
"""Run MEG-NFP-CPI-FOMC-001 on the research PC.

Requires:
  1. Calendar CSV with pre-release timestamps (not the synthetic fixture).
  2. M15 bid/ask bars covering the split (tick-derived or --bars-csv).

    cd server/research_scripts
    python -m macro_event_gate_v1.run_experiment \\
        --split discovery_a \\
        --calendar-csv /path/to/nfp_cpi_fomc.csv \\
        --bars-csv /path/to/xauusd_m15_bidask.csv

Cloud VMs without calendar + ticks cannot produce outcomes; they can load the
preregistration and run synthetic unit tests.
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
from datetime import datetime, timezone

from . import prereg as prereg_mod
from .calendar_loader import load_events_csv
from .decision import decide
from .stats import summarize
from .windows import build_event_rows

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
PREREG_PATH = os.path.join(HERE, "prereg_MEG-NFP-CPI-FOMC-001.json")
CODE_FILES = (
    "windows.py", "stats.py", "decision.py", "prereg.py",
    "calendar_loader.py", "run_experiment.py",
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
    """M15 CSV: start (epoch or ISO), open, high, low, close, ask_open, ask_close, …"""
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            start = raw.get("start") or raw.get("time") or raw.get("timestamp")
            if start is None:
                raise ValueError("bars CSV needs a start/time column")
            try:
                start_ts = int(float(start))
            except ValueError:
                start_ts = int(datetime.fromisoformat(start.replace("Z", "+00:00")).timestamp())
            bar = {
                "start": start_ts,
                "end": start_ts + 900,
                "open": float(raw["open"]),
                "high": float(raw.get("high") or raw["open"]),
                "low": float(raw.get("low") or raw["open"]),
                "close": float(raw["close"]),
            }
            if raw.get("ask_open") not in (None, ""):
                bar["ask_open"] = float(raw["ask_open"])
            if raw.get("ask_close") not in (None, ""):
                bar["ask_close"] = float(raw["ask_close"])
            elif "ask_open" in bar:
                bar["ask_close"] = bar["ask_open"] + (bar["close"] - bar["open"])
            rows.append(bar)
    rows.sort(key=lambda b: b["start"])
    return rows


def write_outputs(run_dir, prereg, split, rows, summary, meta, decision=None, extra=None):
    os.makedirs(run_dir, exist_ok=True)
    payload = {
        "hypothesis_id": prereg["hypothesis_id"],
        "params_sha256": prereg["params_sha256"],
        "split": split,
        "evidence_ceiling": prereg["evidence_ceiling"],
        "summary": summary,
        "decision": decision,
        "meta": meta,
    }
    if extra:
        payload["extra"] = extra
    with open(os.path.join(run_dir, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    if rows:
        path = os.path.join(run_dir, "events.csv")
        keys = sorted({k for r in rows for k in r.keys()})
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="MEG-NFP-CPI-FOMC-001 runner")
    parser.add_argument("--split", required=True, choices=list(prereg_mod.ALLOWED_SPLITS))
    parser.add_argument(
        "--calendar-csv",
        required=True,
        help="NFP/CPI/FOMC calendar CSV with pre-release timestamps (macro_calendar_v1 schema)",
    )
    parser.add_argument(
        "--bars-csv",
        required=True,
        help="M15 bid/ask CSV (start, open, close, ask_open, ask_close, …)",
    )
    parser.add_argument("--prereg", default=PREREG_PATH)
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--allow-synthetic-calendar",
        action="store_true",
        help="Permit fixture/example.invalid calendars (CI/smoke only; not for real decisions)",
    )
    args = parser.parse_args(argv)

    prereg = prereg_mod.load(args.prereg)
    prereg_mod.assert_split_avoids_exclusions(prereg, args.split)

    registry_path = os.path.join(DATA_DIR, "hypothesis_registry.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    registry = prereg_mod.check_hypothesis_registry(registry_path, prereg)

    t0 = time.perf_counter()
    events = load_events_csv(
        args.calendar_csv,
        allow_synthetic=args.allow_synthetic_calendar,
        event_types=prereg["params"]["event_types"],
    )
    bars = load_bars_csv(args.bars_csv)

    decision = None
    extra = {}

    if args.split == "combined_discoveries":
        rows_a = build_event_rows(bars, events, prereg, "discovery_a", prereg["params"])
        rows_b = build_event_rows(bars, events, prereg, "discovery_b", prereg["params"])
        sum_a = summarize(rows_a, prereg["params"])
        sum_b = summarize(rows_b, prereg["params"])
        rows = rows_a + rows_b
        for r in rows:
            r["split_tag"] = "combined_discoveries"
        summary = summarize(rows, prereg["params"])
        summary["discovery_a"] = sum_a
        summary["discovery_b"] = sum_b
        decision = decide(sum_a, sum_b, summary, rows, prereg["params"])
    else:
        rows = build_event_rows(bars, events, prereg, args.split, prereg["params"])
        summary = summarize(rows, prereg["params"])

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.out or os.path.join(DATA_DIR, "runs", f"{args.split}_{stamp}")
    meta = {
        "git_commit": git_commit(),
        "code_sha256": code_fingerprint(),
        "prereg_sha256": sha256_file(args.prereg),
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "calendar_csv": os.path.abspath(args.calendar_csv),
        "bars_csv": os.path.abspath(args.bars_csv),
        "n_calendar_events": len(events),
        "n_bars": len(bars),
        "allow_synthetic_calendar": bool(args.allow_synthetic_calendar),
        "evidence_ceiling": "EXPLORATORY_ONLY",
        "validated_claim": False,
        "phase": "non_directional_microstructure_v1",
    }
    write_outputs(run_dir, prereg, args.split, rows, summary, meta, decision=decision, extra=extra)

    registry[prereg["hypothesis_id"]]["runs"].append({
        "split": args.split,
        "at": stamp,
        "run_dir": run_dir,
        "params_sha256": prereg["params_sha256"],
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
        "mean_spread_delta": summary.get("mean_spread_delta"),
        "mean_range_delta": summary.get("mean_range_delta"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
