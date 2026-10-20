#!/usr/bin/env python3
"""Phase 7.34 — analyze confirmatory FVG_CONT under frozen FVG-CONT-HABITAT-RM-001."""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))
PHASE723 = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_23")
PREREG_REL = "server/research_scripts/phase7/phase7_33_fvg_cont_habitat/preregistration_v1.json"
RUN_DIR = os.path.join(PHASE_DIR, "runs", "fvg_cont_confirmatory_forward")
DEFAULT_D1 = os.path.join(
    ROOT,
    "server/research_scripts/phase7/phase7_30_liq_sweep_buy_trend/runs/"
    "liq_sweep_confirmatory_forward/nxs_d1_gold_refresh_20261019.csv",
)
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
    """Latest launched confirmatory manifest.

    Filename order is not launch order: the cloud prepare hash sorts after
    the Windows run hash, so the unlaunched manifest would win ``sorted(glob)``.
    """
    launched = []
    prepared = []
    for path in glob.glob(os.path.join(RUN_DIR, "*.manifest.json")):
        try:
            with open(path, encoding="utf-8") as f:
                manifest = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not (
            manifest.get("confirmatory")
            or manifest.get("hypothesis_id") == "FVG-CONT-HABITAT-RM-001"
        ):
            continue
        if manifest.get("start_time_utc"):
            launched.append((manifest["start_time_utc"], path))
        else:
            prepared.append((manifest.get("prepared_at_utc") or "", path))
    if launched:
        launched.sort()
        return launched[-1][1]
    if prepared:
        prepared.sort()
        return prepared[-1][1]
    return None


def _load_rows(path: str) -> List[dict]:
    enc = _detect_text_encoding(path)
    rows = []
    with open(path, encoding=enc, errors="replace") as f:
        for row in csv.reader(f):
            if not row:
                continue
            d = dict(zip(COLS, row))
            if d.get("strategy") == "FVG_CONT":
                rows.append(d)
    return rows


def _episodes(rows: List[dict]) -> List[dict]:
    opens = [r for r in rows if r["action"] == "OPEN"]
    closes = [r for r in rows if r["action"] == "CLOSE"]
    eps = []
    for o, c in zip(opens, closes):
        reason = o["reason"]
        side = "BUY" if "bull" in reason.lower() else (
            "SELL" if "bear" in reason.lower() else "UNK"
        )
        eps.append({
            "open": datetime.strptime(o["time"].lstrip("\ufeff"), "%Y.%m.%d %H:%M:%S"),
            "side": side,
            "setup": reason,
            "exit": c["reason"],
            "R": float(c["r_multiple"] or 0),
        })
    return eps


def _load_d1(path: str):
    out = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = datetime.strptime(r["time"], "%Y.%m.%d %H:%M")
            out.append((t, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
    return out


def _sma200_map(d1):
    closes = [c for *_o, c in d1]
    times = [t for t, *_ in d1]
    return {
        t: (None if i < 199 else sum(closes[i - 199 : i + 1]) / 200.0)
        for i, t in enumerate(times)
    }


def _prior_d1_index(d1, open_dt: datetime) -> Optional[int]:
    best = None
    for i, (t, *_rest) in enumerate(d1):
        if t <= open_dt:
            best = i
        else:
            break
    return best


def _atr14(d1, i: int) -> Optional[float]:
    if i < 14:
        return None
    trs = []
    for j in range(i - 13, i + 1):
        _t, o, h, l, c = d1[j]
        prev_c = d1[j - 1][4]
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    return sum(trs) / len(trs)


def _regime_cell(d1, i: int, sma) -> Optional[Tuple[str, int]]:
    t, _o, _h, _l, c = d1[i]
    s = sma.get(t)
    if s is None:
        return None
    atr = _atr14(d1, i)
    if atr is None or atr <= 0:
        return None
    trend = "BULL" if c > s else "BEAR"
    start = max(14, i - 251)
    atrs = [a for j in range(start, i + 1) if (a := _atr14(d1, j)) is not None]
    if len(atrs) < 20:
        return None
    atrs_sorted = sorted(atrs)
    rank = sum(1 for x in atrs_sorted if x <= atr) / len(atrs_sorted)
    terc = 0 if rank < 1 / 3 else (1 if rank < 2 / 3 else 2)
    return (trend, terc)


def _stats(Rs: List[float]) -> dict:
    if not Rs:
        return {"n": 0, "mean_R": None, "sum_R": 0.0, "win_rate": None}
    return {
        "n": len(Rs),
        "mean_R": round(sum(Rs) / len(Rs), 4),
        "sum_R": round(sum(Rs), 4),
        "win_rate": round(sum(1 for x in Rs if x > 0) / len(Rs), 4),
    }


def _decide(prereg, n_b: int, ci_delta) -> str:
    min_n = int(prereg["params"]["min_n_for_decision"])
    if n_b < min_n:
        return "INSUFFICIENT_EVIDENCE"
    if ci_delta is None:
        return "MIXED"
    if ci_delta[0] > 0:
        return "SIGNAL_SUPPORTED_AS_HYPOTHESIS"
    if ci_delta[1] <= 0:
        return "HABITAT_ONLY"
    return "MIXED"


def analyze(d1_path: str) -> dict:
    prereg_sha = assert_frozen_spec_committed_before_run(ROOT, PREREG_REL)
    with open(os.path.join(ROOT, PREREG_REL), encoding="utf-8") as f:
        prereg = json.load(f)["payload"]
    seed = int(prereg["params"]["random_seed"])

    mp = _find_manifest()
    if mp is None:
        return {
            "status": "RUN_NOT_YET_PREPARED",
            "hypothesis_id": prereg["hypothesis_id"],
            "decision": "INSUFFICIENT_EVIDENCE",
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
            "decision": "INSUFFICIENT_EVIDENCE",
            "promotable": False,
            "live_ready": False,
        }

    trades = manifest.get("trades_csv_dest")
    if trades and not os.path.isabs(trades):
        trades = os.path.join(RUN_DIR, os.path.basename(trades))
    eps_all = _episodes(_load_rows(trades)) if trades and os.path.exists(trades) else []
    # InpResetTradesLogOnInit FileMove failed on this PC (tester err=5020), so
    # the CSV still holds the pre-window diagnostic. Confirmatory sample is
    # opens inside the frozen tester window only — same rows the certificate
    # counts as OPENED. Not an SL/TP retune.
    start = datetime.strptime(manifest["period_from"], "%Y.%m.%d")
    end = datetime.strptime(manifest["period_to"], "%Y.%m.%d").replace(
        hour=23, minute=59, second=59
    )
    eps = [e for e in eps_all if start <= e["open"] <= end]
    cert_opened = (manifest.get("reconciliation") or {}).get("n_opened_per_certificate")

    d1 = _load_d1(d1_path)
    d1_last = d1[-1][0] if d1 else None
    window_end = datetime.strptime(manifest["period_to"], "%Y.%m.%d")
    d1_covers = d1_last is not None and d1_last.date() >= window_end.date()
    sma = _sma200_map(d1)

    annotated = []
    for e in eps:
        i = _prior_d1_index(d1, e["open"])
        if i is None:
            annotated.append({**e, "d1_i": None, "regime": None})
            continue
        annotated.append({**e, "d1_i": i, "regime": _regime_cell(d1, i, sma)})

    arm_a = annotated
    arm_b = [e for e in annotated if e["side"] == "BUY"]

    rng = random.Random(seed)
    cells: Dict[Tuple[str, int], List[int]] = defaultdict(list)
    if d1_covers:
        for i in range(200, len(d1) - 11):
            cell = _regime_cell(d1, i, sma)
            if cell and cell[0] == "BULL":
                cells[cell].append(i)

    b_proxy, c_proxy, paired_delta = [], [], []
    for e in arm_b:
        cell, i = e["regime"], e["d1_i"]
        if i is None or not cell or cell not in cells or len(cells[cell]) < 5:
            continue
        atr = _atr14(d1, i)
        if atr is None or atr <= 0 or i + 10 >= len(d1):
            continue
        fwd = (d1[i + 10][4] - d1[i][4]) / atr
        b_proxy.append(fwd)
        choices = [j for j in cells[cell] if abs(j - i) > 5]
        if not choices:
            continue
        j = choices[rng.randrange(len(choices))]
        atr_j = _atr14(d1, j)
        if atr_j is None or atr_j <= 0 or j + 10 >= len(d1):
            continue
        fwd_c = (d1[j + 10][4] - d1[j][4]) / atr_j
        c_proxy.append(fwd_c)
        paired_delta.append(fwd - fwd_c)

    ci_delta = None
    if len(paired_delta) >= 5:
        xs = sorted(paired_delta)
        rng2 = random.Random(seed + 1)
        boots = sorted(
            sum(xs[rng2.randrange(len(xs))] for _ in range(len(xs))) / len(xs)
            for _ in range(5000)
        )
        ci_delta = [round(boots[int(0.025 * (len(boots) - 1))], 4),
                    round(boots[int(0.975 * (len(boots) - 1))], 4)]

    decision = _decide(prereg, len(arm_b), ci_delta)
    status = "ANALYZED" if d1_covers else "ANALYZED_D1_COVERAGE_INCOMPLETE"

    return {
        "status": status,
        "phase": "7.34",
        "hypothesis_id": prereg["hypothesis_id"],
        "prereg_commit_sha": prereg_sha,
        "params_sha256": prereg["params_sha256"],
        "run_mode": "CONFIRMATORY_FORWARD",
        "promotable": False,
        "live_ready": False,
        "run_id": manifest.get("run_id"),
        "window": [manifest.get("period_from"), manifest.get("period_to")],
        "sample_isolation": {
            "raw_episodes_in_csv": len(eps_all),
            "in_window_episodes": len(eps),
            "certificate_opened": cert_opened,
            "window_matches_certificate": cert_opened == len(eps),
            "note": (
                "NEXUS_trades.csv was not archived (Tester: FileMove err=5020). "
                "Pre-window rows are the Phase 7.32 diagnostic and are excluded. "
                "Arms use opens inside the frozen window only."
            ),
        },
        "d1_csv": d1_path,
        "d1_covers_window": d1_covers,
        "arm_A_baseline_recipe_R": _stats([e["R"] for e in arm_a]),
        "arm_B_buy_recipe_R": _stats([e["R"] for e in arm_b]),
        "arm_A_buy_share": (
            round(sum(1 for e in arm_a if e["side"] == "BUY") / len(arm_a), 4)
            if arm_a else None
        ),
        "arm_C_proxy": {
            "outcome": "10d_forward_return_over_ATR14 — NOT recipe R",
            "B_proxy": _stats(b_proxy),
            "C_proxy": _stats(c_proxy),
            "paired_delta_B_minus_C": _stats(paired_delta),
            "paired_delta_iid_bootstrap_ci95": ci_delta,
            "n_paired": len(paired_delta),
        },
        "decision": decision,
        "reconciliation": manifest.get("reconciliation"),
        "power_note": prereg["power_note"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--d1-csv", default=DEFAULT_D1)
    args = ap.parse_args()

    payload = analyze(args.d1_csv)
    doc = wrap_with_provenance(
        payload, "phase7_34_fvg_cont_confirmatory/analyze_confirmatory_forward.py"
    )
    out = os.path.join(PHASE_DIR, "confirmatory_forward_result_v1.json")
    save_json(out, doc)

    status_path = os.path.join(PHASE_DIR, "confirmatory_run_status_v1.json")
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
        "B_n": (payload.get("arm_B_buy_recipe_R") or {}).get("n"),
        "sha": doc["canonical_sha256"][:16],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
