#!/usr/bin/env python3
"""Phase 7.32 — analyze FVG_CONT isolation diagnostic under frozen prereg."""
from __future__ import annotations

import csv
import glob
import json
import os
import sys
from datetime import datetime, timezone
from typing import List, Optional

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))
PHASE723 = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_23")
PREREG_REL = (
    "server/research_scripts/phase7/phase7_32_fvg_cont_isolation_diagnostic/"
    "preregistration_v1.json"
)
RUN_DIR = os.path.join(PHASE_DIR, "runs", "fvg_cont_isolation_diagnostic")
COLS = [
    "time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
    "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf",
]

sys.path.insert(0, PHASE723)
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402
from engine.preregistration_provenance_guard import (  # noqa: E402
    assert_frozen_spec_committed_before_run,
)
from nxs_research_run_harness import _detect_text_encoding  # noqa: E402


def _find_manifest() -> Optional[str]:
    cands = sorted(glob.glob(os.path.join(RUN_DIR, "*.manifest.json")))
    for p in reversed(cands):
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
        if m.get("hypothesis_id") == "FVG-CONT-MT5-ISOLATION-DIAG-001" or m.get("diagnostic"):
            return p
    return cands[-1] if cands else None


def _load_closes(path: str) -> List[dict]:
    enc = _detect_text_encoding(path)
    out = []
    with open(path, encoding=enc, errors="replace") as f:
        for row in csv.reader(f):
            if not row:
                continue
            d = dict(zip(COLS, row))
            if d.get("strategy") == "FVG_CONT" and d.get("action") == "CLOSE":
                out.append(d)
    return out


def _foreign_strategies(path: str) -> List[str]:
    enc = _detect_text_encoding(path)
    names = set()
    with open(path, encoding=enc, errors="replace") as f:
        for row in csv.reader(f):
            if not row:
                continue
            d = dict(zip(COLS, row))
            if d.get("strategy") and d["strategy"] != "FVG_CONT":
                names.add(d["strategy"])
    return sorted(names)


def analyze() -> dict:
    prereg_sha = assert_frozen_spec_committed_before_run(ROOT, PREREG_REL)
    with open(os.path.join(ROOT, PREREG_REL), encoding="utf-8") as f:
        prereg = json.load(f)["payload"]
    min_n = int(prereg["params"]["min_n_for_sample_ready"])

    mp = _find_manifest()
    if mp is None:
        return {
            "status": "RUN_NOT_YET_PREPARED",
            "hypothesis_id": prereg["hypothesis_id"],
            "decision": "INSUFFICIENT_SAMPLE",
            "promotable": False,
            "live_ready": False,
        }
    with open(mp, encoding="utf-8") as f:
        manifest = json.load(f)
    if manifest.get("status") != "COLLECTED":
        return {
            "status": "RUN_NOT_YET_COLLECTED",
            "manifest_status": manifest.get("status"),
            "run_id": manifest.get("run_id"),
            "hypothesis_id": prereg["hypothesis_id"],
            "prereg_commit_sha": prereg_sha,
            "decision": "INSUFFICIENT_SAMPLE",
            "promotable": False,
            "live_ready": False,
        }

    trades = manifest.get("trades_csv_dest")
    if trades and not os.path.isabs(trades):
        trades = os.path.join(RUN_DIR, os.path.basename(trades))
    closes = _load_closes(trades) if trades and os.path.exists(trades) else []
    foreign = _foreign_strategies(trades) if trades and os.path.exists(trades) else []
    Rs = [float(c["r_multiple"] or 0) for c in closes]
    n = len(closes)
    mean_R = (sum(Rs) / n) if n else None
    win_rate = (sum(1 for x in Rs if x > 0) / n) if n else None

    recon = manifest.get("reconciliation") or {}
    decision = "INSUFFICIENT_SAMPLE"
    if foreign:
        decision = "HARNESS_OR_IDENTITY_PROBLEM"
    elif recon and recon.get("ok") is False:
        decision = "HARNESS_OR_IDENTITY_PROBLEM"
    elif n >= min_n:
        decision = "SAMPLE_READY_FOR_EDGE_PREREG"
    elif n == 0 and not trades:
        # empty CSV / no trades file — still insufficient unless recon screams
        decision = "INSUFFICIENT_SAMPLE"

    return {
        "status": "ANALYZED",
        "phase": "7.32",
        "hypothesis_id": prereg["hypothesis_id"],
        "prereg_commit_sha": prereg_sha,
        "params_sha256": prereg["params_sha256"],
        "run_mode": "MT5_ISOLATION_DIAGNOSTIC",
        "promotable": False,
        "live_ready": False,
        "evidence_grade": "DIAGNOSTIC_FIRST_LOOK",
        "run_id": manifest.get("run_id"),
        "window": [manifest.get("period_from"), manifest.get("period_to")],
        "n_closed_FVG_CONT": n,
        "mean_recipe_R": round(mean_R, 4) if mean_R is not None else None,
        "win_rate": round(win_rate, 4) if win_rate is not None else None,
        "foreign_strategies_in_csv": foreign,
        "reconciliation": recon,
        "decision": decision,
        "decision_rule_source": "preregistration_v1.json decision_rule_frozen",
        "power_note": prereg["power_note"],
        "next": (
            "If SAMPLE_READY_FOR_EDGE_PREREG: write a NEW habitat/regime prereg (7.33+). "
            "If INSUFFICIENT_SAMPLE: extend window or accept low density — do not promote."
        ),
    }


def main() -> int:
    payload = analyze()
    doc = wrap_with_provenance(
        payload, "phase7_32_fvg_cont_isolation_diagnostic/analyze_diagnostic_run.py"
    )
    out = os.path.join(PHASE_DIR, "diagnostic_result_v1.json")
    save_json(out, doc)

    status_path = os.path.join(PHASE_DIR, "diagnostic_run_status_v1.json")
    early = payload.get("status") in ("RUN_NOT_YET_PREPARED", "RUN_NOT_YET_COLLECTED")
    if early and os.path.isfile(status_path):
        with open(status_path, encoding="utf-8") as f:
            prev = json.load(f)
        if prev.get("status") == "PREPARED_AWAITING_WINDOWS_MT5":
            prev["analyze_probe"] = {
                "status": payload.get("status"),
                "decision": payload.get("decision"),
                "result_path": out,
                "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            with open(status_path, "w", encoding="utf-8") as f:
                json.dump(prev, f, indent=2, ensure_ascii=True)
        else:
            early = False
    if not early:
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump({
                "status": payload.get("status"),
                "decision": payload.get("decision"),
                "run_id": payload.get("run_id"),
                "hypothesis_id": payload.get("hypothesis_id"),
                "result_path": out,
                "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            }, f, indent=2, ensure_ascii=True)

    print(json.dumps({
        "status": payload.get("status"),
        "decision": payload.get("decision"),
        "n": payload.get("n_closed_FVG_CONT"),
        "sha": doc["canonical_sha256"][:16],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
