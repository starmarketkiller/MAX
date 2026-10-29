#!/usr/bin/env python3
"""Run TG-12M-GATE-001 on the research PC with long daily XAUUSD CSV.

    cd server/research_scripts
    python -m trend_12m_gate_v1.run_experiment --split selection --daily-csv /path/xau.csv
    python -m trend_12m_gate_v1.run_experiment --split combined_confirmations --daily-csv /path/xau.csv

Cloud VMs without daily history cannot produce outcomes; they can still load the
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
from datetime import datetime, timezone

from . import prereg as prereg_mod
from .decision import decide_confirmation, decide_selection
from .series import load_daily_csv
from .signals import build_all_variants, build_variant_rows
from .stats import summarize

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
PREREG_PATH = os.path.join(HERE, "prereg_TG-12M-GATE-001.json")
CODE_FILES = (
    "signals.py", "series.py", "stats.py", "decision.py", "prereg.py", "run_experiment.py",
)
WINNER_PATH = os.path.join(DATA_DIR, "selected_variant.json")


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


def load_winner(path=WINNER_PATH):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_winner(winner_id, selection_decision, path=WINNER_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "hypothesis_id": "TG-12M-GATE-001",
        "selected_variant_id": winner_id,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "selection_decision": selection_decision.get("decision"),
        "survivors": selection_decision.get("survivors"),
        "evidence_ceiling": "EXPLORATORY_ONLY",
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


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
        keys = list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="TG-12M-GATE-001 runner")
    parser.add_argument("--split", required=True, choices=list(prereg_mod.ALLOWED_SPLITS))
    parser.add_argument(
        "--daily-csv",
        required=True,
        help="Long daily XAUUSD CSV with date + close columns",
    )
    parser.add_argument("--prereg", default=PREREG_PATH)
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--winner-id",
        default=None,
        help="Override frozen winner (confirmation splits). Default: data/selected_variant.json",
    )
    args = parser.parse_args(argv)

    prereg = prereg_mod.load(args.prereg)
    prereg_mod.assert_split_avoids_exclusions(prereg, args.split)

    registry_path = os.path.join(DATA_DIR, "hypothesis_registry.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    registry = prereg_mod.check_hypothesis_registry(registry_path, prereg)

    t0 = time.perf_counter()
    bars = load_daily_csv(args.daily_csv, price_column=prereg["params"]["price_column"])

    decision = None
    rows = []
    summary = {}
    extra = {}

    if args.split == "selection":
        by_id = build_all_variants(bars, prereg, "selection")
        decision = decide_selection(by_id, prereg["params"])
        summary = {
            "n_days": max((len(v) for v in by_id.values()), default=0),
            "variants": {vid: summarize(r, prereg["params"],
                                        ci_level=1.0 - prereg["params"]["selection_alpha"] / len(prereg["params"]["variant_ids"]))
                         for vid, r in by_id.items()},
        }
        # Persist winner only when selection finds survivors.
        if decision.get("selected_variant_id"):
            save_winner(decision["selected_variant_id"], decision)
            rows = by_id[decision["selected_variant_id"]]
        else:
            # Still write first variant rows for audit if any.
            first = prereg["params"]["variant_ids"][0]
            rows = by_id.get(first) or []
        extra["variant_details"] = decision.get("variant_details")

    elif args.split == "combined_confirmations":
        winner_rec = load_winner()
        winner_id = args.winner_id or (winner_rec or {}).get("selected_variant_id")
        if not winner_id:
            print(
                "No frozen winner. Run --split selection first (and obtain a survivor), "
                "or pass --winner-id.",
                file=sys.stderr,
            )
            return 2
        rows_a = build_variant_rows(bars, prereg, "confirmation_a", winner_id)
        rows_b = build_variant_rows(bars, prereg, "confirmation_b", winner_id)
        sum_a = summarize(rows_a, prereg["params"])
        sum_b = summarize(rows_b, prereg["params"])
        rows = rows_a + rows_b
        for r in rows:
            r["split_tag"] = "combined_confirmations"
        summary = summarize(rows, prereg["params"])
        summary["confirmation_a"] = sum_a
        summary["confirmation_b"] = sum_b
        decision = decide_confirmation(sum_a, sum_b, summary, rows, prereg["params"], winner_id)
        extra["selected_variant_id"] = winner_id

    else:
        # confirmation_a / confirmation_b / internal_validation — single variant
        winner_rec = load_winner()
        winner_id = args.winner_id or (winner_rec or {}).get("selected_variant_id")
        if not winner_id:
            # Allow running a single confirmation for smoke with explicit --winner-id.
            print(
                "No frozen winner. Run --split selection first, or pass --winner-id.",
                file=sys.stderr,
            )
            return 2
        rows = build_variant_rows(bars, prereg, args.split, winner_id)
        summary = summarize(rows, prereg["params"])
        extra["selected_variant_id"] = winner_id

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.out or os.path.join(DATA_DIR, "runs", f"{args.split}_{stamp}")
    meta = {
        "git_commit": git_commit(),
        "code_sha256": code_fingerprint(),
        "prereg_sha256": sha256_file(args.prereg),
        "elapsed_s": round(time.perf_counter() - t0, 2),
        "daily_csv": os.path.abspath(args.daily_csv),
        "n_bars": len(bars),
        "evidence_ceiling": "EXPLORATORY_ONLY",
        "validated_claim": False,
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
        "n_days": summary.get("n_days"),
        "decision": (decision or {}).get("decision"),
        "selected_variant_id": (decision or {}).get("selected_variant_id") or extra.get("selected_variant_id"),
        "evidence_ceiling": "EXPLORATORY_ONLY",
        "mean_excess_log_return": summary.get("mean_excess_log_return"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
