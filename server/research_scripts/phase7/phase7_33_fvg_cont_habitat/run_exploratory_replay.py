#!/usr/bin/env python3
"""Phase 7.33 — exploratory habitat replay on EXPOSED 7.32 diagnostic trades.

NOT_PROMOTABLE / DISCOVERY_REUSE. No sealed holdouts. No MT5 launch.
"""
from __future__ import annotations

import csv
import json
import os
import random
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))
PREREG_REL = "server/research_scripts/phase7/phase7_33_fvg_cont_habitat/preregistration_v1.json"
TRADES = os.path.join(
    ROOT,
    "server/research_scripts/phase7/phase7_32_fvg_cont_isolation_diagnostic/runs/"
    "fvg_cont_isolation_diagnostic/"
    "FVG_CONT_2023.10.02_2026.06.30_8761b3513079eed9_20261019T214337Z_1b2a7150.trades.csv",
)
D1_CANDIDATES = [
    os.path.join(
        ROOT,
        "server/research_scripts/phase7/phase7_30_liq_sweep_buy_trend/runs/"
        "liq_sweep_confirmatory_forward/nxs_d1_gold_refresh_20261019.csv",
    ),
    os.path.join(ROOT, "server/research_scripts/phase7/phase7_9h/raw_data/nxs_d1_gold_phase79h.csv"),
]
COLS = [
    "time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
    "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf",
]

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7"))
from engine.preregistration_provenance_guard import (  # noqa: E402
    assert_frozen_spec_committed_before_run,
)


def _d1_path() -> str:
    for p in D1_CANDIDATES:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError("No D1 gold CSV found")


def _load_trades(path: str) -> List[dict]:
    text = open(path, encoding="utf-16").read()
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        row = next(csv.reader([line]))
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
    m = {}
    for i, t in enumerate(times):
        m[t] = None if i < 199 else sum(closes[i - 199 : i + 1]) / 200.0
    return m


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
    atrs = []
    for j in range(start, i + 1):
        a = _atr14(d1, j)
        if a is not None:
            atrs.append(a)
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


def _month_block_ci(eps: List[dict], seed: int, n_boot: int = 5000):
    if len(eps) < 5:
        return None
    blocks = defaultdict(list)
    for e in eps:
        blocks[(e["open"].year, e["open"].month)].append(e["R"])
    keys = list(blocks.keys())
    if len(keys) < 3:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        sample = []
        for _k in keys:
            sample.extend(blocks[keys[rng.randrange(len(keys))]])
        if sample:
            means.append(sum(sample) / len(sample))
    means.sort()
    return [round(means[int(0.025 * (len(means) - 1))], 4),
            round(means[int(0.975 * (len(means) - 1))], 4)]


def run() -> dict:
    prereg_sha = assert_frozen_spec_committed_before_run(ROOT, PREREG_REL)
    with open(os.path.join(ROOT, PREREG_REL), encoding="utf-8") as f:
        prereg = json.load(f)["payload"]
    seed = int(prereg["params"]["random_seed"])
    d1_path = _d1_path()
    d1 = _load_d1(d1_path)
    sma = _sma200_map(d1)
    eps = _episodes(_load_trades(TRADES))

    annotated = []
    for e in eps:
        i = _prior_d1_index(d1, e["open"])
        if i is None:
            continue
        cell = _regime_cell(d1, i, sma)
        annotated.append({**e, "d1_i": i, "regime": cell})

    arm_a = annotated
    arm_b = [e for e in annotated if e["side"] == "BUY"]

    rng = random.Random(seed)
    cells: Dict[Tuple[str, int], List[int]] = defaultdict(list)
    for i in range(200, len(d1) - 11):
        cell = _regime_cell(d1, i, sma)
        if cell and cell[0] == "BULL":
            cells[cell].append(i)

    b_proxy, c_proxy, paired_delta = [], [], []
    for e in arm_b:
        cell = e["regime"]
        i = e["d1_i"]
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
        boots = []
        for _ in range(5000):
            s = [xs[rng2.randrange(len(xs))] for _ in range(len(xs))]
            boots.append(sum(s) / len(s))
        boots.sort()
        ci_delta = [round(boots[int(0.025 * (len(boots) - 1))], 4),
                    round(boots[int(0.975 * (len(boots) - 1))], 4)]

    def decide(n_b, ci):
        if n_b < int(prereg["params"]["min_n_for_decision"]):
            return "INSUFFICIENT_EVIDENCE"
        if ci is None:
            return "MIXED"
        if ci[0] > 0:
            return "SIGNAL_SUPPORTED_AS_HYPOTHESIS"
        if ci[1] <= 0:
            return "HABITAT_ONLY"
        return "MIXED"

    decision = decide(len(arm_b), ci_delta)

    return {
        "phase": "7.33",
        "hypothesis_id": prereg["hypothesis_id"],
        "prereg_commit_sha": prereg_sha,
        "params_sha256": prereg["params_sha256"],
        "run_mode": "EXPLORATORY_REPLAY_ON_EXPOSED_DIAGNOSTIC",
        "promotable": False,
        "evidence_grade": "DISCOVERY_REUSE",
        "window": ["2023.10.02", "2026.06.30"],
        "d1_csv": d1_path,
        "arm_A_baseline_recipe_R": _stats([e["R"] for e in arm_a]),
        "arm_B_buy_recipe_R": _stats([e["R"] for e in arm_b]),
        "arm_B_month_block_ci95_recipe_R": _month_block_ci(arm_b, seed),
        "arm_A_buy_share": (
            round(sum(1 for e in arm_a if e["side"] == "BUY") / len(arm_a), 4) if arm_a else None
        ),
        "arm_B_n_filtered_from_A": {"A": len(arm_a), "B": len(arm_b)},
        "arm_C_proxy": {
            "outcome": "10d_forward_return_over_ATR14 — NOT recipe R; exploratory habitat control only",
            "B_proxy": _stats(b_proxy),
            "C_proxy": _stats(c_proxy),
            "paired_delta_B_minus_C": _stats(paired_delta),
            "paired_delta_iid_bootstrap_ci95": ci_delta,
            "n_paired": len(paired_delta),
        },
        "decision_exploratory": decision,
        "decision_meaning": (
            "Frozen labels for bookkeeping only. Data are EXPOSED (looked at in 7.32). "
            "Cannot promote FVG_CONT. Confirmatory needs forward MT5 after 2026-06-30."
        ),
        "power_note": prereg["power_note"],
        "next_confirmatory_step": prereg["data_policy"]["confirmatory_requires"],
    }


def main() -> int:
    sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
    from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

    payload = run()
    doc = wrap_with_provenance(payload, "phase7_33_fvg_cont_habitat/run_exploratory_replay.py")
    out = os.path.join(PHASE_DIR, "exploratory_replay_result_v1.json")
    save_json(out, doc)
    print(json.dumps({
        "promotable": payload["promotable"],
        "decision_exploratory": payload["decision_exploratory"],
        "A_n": payload["arm_A_baseline_recipe_R"]["n"],
        "B_n": payload["arm_B_buy_recipe_R"]["n"],
        "B_mean_R": payload["arm_B_buy_recipe_R"]["mean_R"],
        "delta_ci": payload["arm_C_proxy"]["paired_delta_iid_bootstrap_ci95"],
        "sha": doc["canonical_sha256"][:16],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
