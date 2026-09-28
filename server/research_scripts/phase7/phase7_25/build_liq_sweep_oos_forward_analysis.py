#!/usr/bin/env python3
"""Phase 7.25 punto 10 - OOS/forward. Finestra 2026.07.01-2026.09.27,
genuinamente untouched (vedi data_exposure_map_v1.json), eseguita con
l'harness di isolamento di Phase 7.23 (launch_oos_forward_run.py /
collect_oos_forward_run.py), un SOLO run, guardato SOLO DOPO aver
congelato baseline/concentrazione/costi/execution/temporale/
statistica/path anatomy/visual audit. Se il campione e' troppo
piccolo: INSUFFICIENT_OOS_SAMPLE, non FAILED."""
import glob
import json
import os
import sys

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
PHASE723_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_23")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE723_DIR)
from nxs_research_run_harness import _detect_text_encoding  # noqa: E402

RUN_DIR = os.path.join(PHASE725_DIR, "runs", "liq_sweep_oos_forward")
MIN_SAMPLE_FOR_MEANINGFUL_OOS = 5  # dichiarato PRIMA di guardare il risultato - stessa soglia 7.21/7.22
STRATEGY_NAME = "LIQ_SWEEP"


def _find_manifest():
    candidates = sorted(glob.glob(os.path.join(RUN_DIR, "*.manifest.json")))
    return candidates[-1] if candidates else None


def _load_closes(trades_path):
    if not trades_path or not os.path.exists(trades_path):
        return None
    encoding = _detect_text_encoding(trades_path)
    cols = ["time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
           "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf"]
    import csv
    with open(trades_path, encoding=encoding, errors="replace") as f:
        reader = csv.reader(f)
        rows = [dict(zip(cols, row)) for row in reader if row]
    return [r for r in rows if r.get("strategy") == STRATEGY_NAME and r.get("action") == "CLOSE"]


def build():
    manifest_path = _find_manifest()
    if manifest_path is None:
        return {"status": "RUN_NOT_YET_LAUNCHED"}
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    if manifest.get("status") != "COLLECTED":
        return {"status": "RUN_NOT_YET_COLLECTED", "manifest_status": manifest.get("status"),
               "run_id": manifest.get("run_id")}

    trades_path = manifest.get("trades_csv_dest")
    if trades_path and not os.path.isabs(trades_path):
        trades_path = os.path.join(PHASE725_DIR, "runs", "liq_sweep_oos_forward",
                                   os.path.basename(trades_path))
    closes = _load_closes(trades_path)
    if closes is None:
        closes = []

    n = len(closes)
    nets = [float(r["score_or_pnl"]) for r in closes]
    decision = "INSUFFICIENT_OOS_SAMPLE" if n < MIN_SAMPLE_FOR_MEANINGFUL_OOS else \
              "SAMPLE_SUFFICIENT_FOR_A_FIRST_READ"

    payload = {
        "window": ["2026.07.01", "2026.09.27"], "window_genuinely_untouched": True,
        "run_id": manifest["run_id"],
        "run_config": "harness di isolamento Phase 7.23 (selettore 7 isolato, stessa identita' "
            "canonica del run diagnostico, InpResearchMode=true, lotto fisso 0.01).",
        "n_closed_trades_liq_sweep": n,
        "closed_trades_net_pnl": [round(x, 2) for x in nets],
        "net_pnl_total": sum(nets) if nets else 0.0,
        "net_pnl_per_trade": (sum(nets) / n) if n else None,
        "win_rate": (sum(1 for x in nets if x > 0) / n) if n else None,
        "min_sample_threshold_declared_before_result": MIN_SAMPLE_FOR_MEANINGFUL_OOS,
        "decision": decision,
        "decision_meaning": {
            "INSUFFICIENT_OOS_SAMPLE": "Campione troppo piccolo per QUALUNQUE conclusione - "
                "fallimento del CAMPIONE, non della strategia.",
            "SAMPLE_SUFFICIENT_FOR_A_FIRST_READ": "Campione minimo ma non banale - direzione "
                "dell'effetto osservabile, magnitudo non ancora affidabile.",
        }[decision],
        "single_validation_run_only": True,
        "looked_at_only_after_everything_else_frozen": True,
        "reconciliation": manifest.get("reconciliation"),
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE725_DIR, "oos_forward_analysis_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    if payload.get("status") not in ("RUN_NOT_YET_LAUNCHED", "RUN_NOT_YET_COLLECTED"):
        print(f"  n_trades: {payload['n_closed_trades_liq_sweep']} decisione: {payload['decision']}")


if __name__ == "__main__":
    main()
