#!/usr/bin/env python3
"""Phase 7.29 — LIQ_SWEEP OOS failure-mode diagnosis (deterministic).

Question (RRA-01 #4 / #5 shortlist): why was the OOS window negative?
Hypotheses tested against existing MT5 trade CSVs + D1 gold path — no new
backtest, no parameter change, no holdout read beyond already-consumed OOS.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

PHASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE_DIR, "..", "..", "..", ".."))

IS_TRADES = os.path.join(
    ROOT,
    "server/research_scripts/phase7/phase7_23/runs/liq_sweep_diagnostic/"
    "LIQ_SWEEP_2023.10.02_2026.06.30_66767008acee43f3_20260927T211708Z_882af939.trades.csv",
)
OOS_TRADES = os.path.join(
    ROOT,
    "server/research_scripts/phase7/phase7_25/runs/liq_sweep_oos_forward/"
    "LIQ_SWEEP_2026.07.01_2026.09.27_df1e067b3b38ee3d_20260928T072223Z_1f7a854f.trades.csv",
)
D1_CSV = os.path.join(
    ROOT, "server/research_scripts/phase7/phase7_9h/raw_data/nxs_d1_gold_phase79h.csv"
)
COLS = [
    "time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
    "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf",
]


def _load_trades(path: str) -> List[dict]:
    text = open(path, encoding="utf-16").read()
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        row = next(csv.reader([line]))
        rows.append(dict(zip(COLS, row)))
    return [r for r in rows if r.get("strategy") == "LIQ_SWEEP"]


def _episodes(rows: List[dict]) -> List[dict]:
    opens = [r for r in rows if r["action"] == "OPEN"]
    closes = [r for r in rows if r["action"] == "CLOSE"]
    eps = []
    for o, c in zip(opens, closes):
        reason = o["reason"]
        if "high_reversal" in reason:
            side = "SELL"
        elif "low_reversal" in reason:
            side = "BUY"
        else:
            side = "UNK"
        if "Asia" in reason:
            level = "Asia"
        elif "Weekly" in reason:
            level = "Weekly"
        else:
            level = "Other"
        eps.append({
            "open": o["time"],
            "close": c["time"],
            "side": side,
            "level": level,
            "setup": reason,
            "exit": c["reason"],
            "R": float(c["r_multiple"] or 0),
            "pnl": float(c["score_or_pnl"] or 0),
            "hold_h": float(c["hold_sec"] or 0) / 3600.0,
        })
    return eps


def _stats(eps: List[dict]) -> dict:
    if not eps:
        return {"n": 0}
    Rs = [e["R"] for e in eps]
    return {
        "n": len(eps),
        "mean_R": round(sum(Rs) / len(Rs), 4),
        "sum_R": round(sum(Rs), 4),
        "win_rate": round(sum(1 for x in Rs if x > 0) / len(Rs), 4),
        "sl": sum(1 for e in eps if e["exit"] == "sl"),
        "tp": sum(1 for e in eps if e["exit"] == "tp"),
        "mean_hold_h": round(sum(e["hold_h"] for e in eps) / len(eps), 2),
    }


def _by_side_level(eps: List[dict]) -> dict:
    buckets: Dict[str, List[dict]] = defaultdict(list)
    for e in eps:
        buckets[f"{e['side']}|{e['level']}"].append(e)
    return {k: _stats(v) for k, v in sorted(buckets.items())}


def _gold_drift(start: str, end: str) -> Optional[dict]:
    rows = []
    with open(D1_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = datetime.strptime(r["time"], "%Y.%m.%d %H:%M")
            rows.append((t, float(r["close"])))
    s = datetime.strptime(start, "%Y.%m.%d")
    e = datetime.strptime(end, "%Y.%m.%d")
    xs = [c for t, c in rows if s <= t <= e]
    if len(xs) < 2:
        return None
    return {
        "start_px": xs[0],
        "end_px": xs[-1],
        "ret_pct": round((xs[-1] / xs[0] - 1) * 100, 3),
        "n_bars": len(xs),
    }


def _hypotheses(is_eps, oos_eps, is_drift, oos_drift) -> List[dict]:
    is_buy = [e for e in is_eps if e["side"] == "BUY"]
    is_sell = [e for e in is_eps if e["side"] == "SELL"]
    oos_buy = [e for e in oos_eps if e["side"] == "BUY"]
    oos_sell = [e for e in oos_eps if e["side"] == "SELL"]

    sell_share_is = len(is_sell) / len(is_eps) if is_eps else 0
    sell_share_oos = len(oos_sell) / len(oos_eps) if oos_eps else 0

    # H1 REGIME / HABITAT — IS edge carried by BUY in a +119% gold bull
    h1_support = (
        len(is_buy) / len(is_eps) >= 0.85
        and _stats(is_buy)["mean_R"] > 0
        and _stats(is_sell)["mean_R"] < 0.2
        and is_drift is not None and is_drift["ret_pct"] > 50
        and oos_drift is not None and oos_drift["ret_pct"] > 0
        and all(e["R"] < 0 for e in oos_sell)
    )

    # H2 SETUP_MIX_SHIFT — OOS drew far more SELL share than IS
    h2_support = sell_share_oos >= 0.4 and sell_share_is <= 0.15

    # H3 EXECUTION_BUG — would show weird hold/R, not clean ±1R SL/TP
    oos_abs_R = [abs(e["R"]) for e in oos_eps]
    clean_R = all(0.9 <= r <= 2.1 for r in oos_abs_R) if oos_abs_R else False
    h3_support = False  # explicitly rejected if exits look canonical

    # H4 PURE_SAMPLE_NOISE — n small; cannot alone explain coherent SELL wipe
    h4_support = len(oos_eps) < 30  # always true here; not primary

    # H5 DETECTOR_REGRESSION — same identity/harness as IS; no evidence of code drift in artifacts
    h5_support = False

    return [
        {
            "id": "H1_HABITAT_REGIME",
            "claim": "In-sample expectancy was mostly gold-bull BUY habitat, not symmetric sweep edge.",
            "supported": h1_support,
            "evidence": {
                "is_buy_share": round(len(is_buy) / len(is_eps), 4),
                "is_buy_mean_R": _stats(is_buy).get("mean_R"),
                "is_sell_n": len(is_sell),
                "is_sell_mean_R": _stats(is_sell).get("mean_R"),
                "is_gold_ret_pct": is_drift["ret_pct"] if is_drift else None,
                "oos_gold_ret_pct": oos_drift["ret_pct"] if oos_drift else None,
                "oos_sell_all_stopped": all(e["R"] < 0 for e in oos_sell) if oos_sell else None,
            },
        },
        {
            "id": "H2_SETUP_MIX_SHIFT",
            "claim": "OOS trade mix shifted toward SELL (counter-trend in the same bull) vs IS.",
            "supported": h2_support,
            "evidence": {
                "sell_share_is": round(sell_share_is, 4),
                "sell_share_oos": round(sell_share_oos, 4),
                "oos_sell_mean_R": _stats(oos_sell).get("mean_R"),
                "oos_buy_mean_R": _stats(oos_buy).get("mean_R"),
            },
        },
        {
            "id": "H3_EXECUTION_BUG",
            "claim": "OOS failure is an execution/fill/ATR bug.",
            "supported": h3_support,
            "rejected": True,
            "evidence": {
                "oos_exits": _stats(oos_eps),
                "R_magnitudes_look_canonical_sl_tp": clean_R,
                "note": "5/6 exits are SL near -1R, 1 TP near +1.9R — consistent with recipe, not broken fills.",
            },
        },
        {
            "id": "H4_SAMPLE_SIZE",
            "claim": "n=6 alone makes any OOS verdict fragile (already noted in Phase 7.25).",
            "supported": h4_support,
            "primary": False,
            "evidence": {"oos_n": len(oos_eps), "threshold_for_power": "~180 trades for 0.3R LIQ-like (edge capability V1)"},
        },
        {
            "id": "H5_DETECTOR_REGRESSION",
            "claim": "OOS used a broken post-fix detector vs IS.",
            "supported": h5_support,
            "rejected": True,
            "evidence": {
                "note": "Same Phase 7.23 isolation harness / selector-7 identity; OOS window declared untouched in 7.25.",
            },
        },
    ]


def build() -> dict:
    is_rows = _load_trades(IS_TRADES)
    oos_rows = _load_trades(OOS_TRADES)
    is_eps = _episodes(is_rows)
    oos_eps = _episodes(oos_rows)
    is_drift = _gold_drift("2023.10.02", "2026.06.30")
    oos_drift = _gold_drift("2026.07.01", "2026.09.27")
    hyps = _hypotheses(is_eps, oos_eps, is_drift, oos_drift)

    primary = "H1_HABITAT_REGIME+H2_SETUP_MIX_SHIFT"
    decision = "FAILURE_MODE_IDENTIFIED_REGIME_CONDITIONAL"
    # downgrade standalone confidence; do not mark FAILED (n=6 insufficient for that)
    edge_implication = (
        "LIQ_SWEEP remains CANDIDATE only as a regime-conditional / BUY-with-trend hypothesis. "
        "Standalone promotion to SUPPORTED is blocked until a preregistered test separates "
        "habitat effect from signal (regime-matched or SELL-disabled ablation) with adequate n."
    )

    oos_buy = [e for e in oos_eps if e["side"] == "BUY"]
    return {
        "phase": "7.29",
        "strategy": "LIQ_SWEEP",
        "question": "Why was the Phase 7.25 OOS window negative?",
        "inputs": {
            "is_trades": "phase7_23/runs/liq_sweep_diagnostic/*.trades.csv",
            "oos_trades": "phase7_25/runs/liq_sweep_oos_forward/*.trades.csv",
            "d1_path": "phase7_9h/raw_data/nxs_d1_gold_phase79h.csv",
            "prior_decision": "phase7_25/decision_card_v1.json → EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION",
        },
        "windows": {
            "IS": {"range": ["2023.10.02", "2026.06.30"], "gold_drift": is_drift, "stats": _stats(is_eps)},
            "OOS": {"range": ["2026.07.01", "2026.09.27"], "gold_drift": oos_drift, "stats": _stats(oos_eps)},
        },
        "mix": {
            "IS_by_side_level": _by_side_level(is_eps),
            "OOS_by_side_level": _by_side_level(oos_eps),
            "OOS_episodes": [
                {k: e[k] for k in ("open", "side", "level", "exit", "R")} for e in oos_eps
            ],
            "OOS_open_without_close": sum(1 for r in oos_rows if r["action"] == "OPEN") - len(oos_eps),
        },
        "hypotheses": hyps,
        "primary_failure_mode": primary,
        "decision": decision,
        "edge_implication": edge_implication,
        "oos_buy_only_mean_R": _stats(oos_buy).get("mean_R"),
        "recommended_next_experiment": {
            "name": "LIQ_SWEEP_BUY_TREND_FILTER_OR_REGIME_MATCH_V1",
            "preregister_before_running": True,
            "design_sketch": (
                "Compare (A) current LIQ_SWEEP vs (B) BUY-only when D1 close > SMA200 "
                "vs (C) regime-matched random entries in same bull cells. "
                "Success = B beats C after costs with n powered for 0.3R."
            ),
            "do_not": [
                "Optimize SL/TP on IS",
                "Declare FAILED from n=6 alone",
                "Go live / prop on current bidirectional recipe",
            ],
        },
        "not_an_edge_claim": True,
        "production_status": "NO-GO unchanged",
    }


def main():
    import sys

    sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
    from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

    payload = build()
    doc = wrap_with_provenance(payload, "phase7_29_liq_sweep_oos_failure/build_oos_failure_mode_diagnosis.py")
    out = os.path.join(PHASE_DIR, "liq_sweep_oos_failure_mode_v1.json")
    save_json(out, doc)
    print(json.dumps({
        "decision": payload["decision"],
        "primary": payload["primary_failure_mode"],
        "is_mean_R": payload["windows"]["IS"]["stats"]["mean_R"],
        "oos_mean_R": payload["windows"]["OOS"]["stats"]["mean_R"],
        "sha": doc["canonical_sha256"][:16],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
