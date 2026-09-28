#!/usr/bin/env python3
"""Phase 7.23 Fase B - riepilogo del run diagnostico LIQ_SWEEP, eseguito
con il nuovo harness di isolamento (Fase A di questa stessa fase).
Periodo minimo scelto (non pluriennale automatico): 2023.10.02-
2026.06.30 (~2.9 anni, stessa finestra gia' nota nel progetto per il
diagnostico ORDER_BLOCK/TSI - dati tick presumibilmente gia' cachati,
nessun difetto strutturale trovato in fase statica che richiedesse un
confronto pre/post-fix piu' lungo)."""
import csv
import glob
import json
import os
import re
import sys

PHASE723_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE723_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE723_DIR)
from nxs_research_run_harness import _detect_text_encoding  # noqa: E402

RUN_DIR_GLOB = os.path.join(PHASE723_DIR, "runs", "liq_sweep_diagnostic", "*.manifest.json")
TRADES_COLS = ["time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
              "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf"]


def _find_manifest():
    candidates = sorted(glob.glob(RUN_DIR_GLOB))
    return candidates[-1] if candidates else None


def _load_trades(path, strategy):
    if not path or not os.path.exists(path):
        return None
    encoding = _detect_text_encoding(path)
    with open(path, encoding=encoding, errors="replace") as f:
        reader = csv.reader(f)
        rows = [dict(zip(TRADES_COLS, row)) for row in reader if row]
    return [r for r in rows if r.get("strategy") == strategy]


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
        trades_path = os.path.join(PHASE723_DIR, trades_path)
    rows = _load_trades(trades_path, "LIQ_SWEEP")
    opens = [r for r in rows if r["action"] == "OPEN"] if rows is not None else []
    closes = [r for r in rows if r["action"] == "CLOSE"] if rows is not None else []

    events = []
    oi = 0
    for c in sorted(closes, key=lambda r: r["time"]):
        opens_sorted = sorted(opens, key=lambda r: r["time"])
        if oi < len(opens_sorted) and opens_sorted[oi]["time"] <= c["time"]:
            o = opens_sorted[oi]
            oi += 1
            sl, tp, price = float(o["sl"]), float(o["tp"]), float(o["price"])
            direction = 1 if sl < price < tp else (-1 if sl > price > tp else 0)
            events.append({"entry_time": o["time"], "entry_price": price, "entry_sl": sl,
                          "entry_tp": tp, "exit_time": c["time"], "exit_price": float(c["price"]),
                          "exit_reason": c["reason"], "direction": direction,
                          "net_pnl": float(c["score_or_pnl"])})

    payload = {
        "status": "COLLECTED",
        "run_id": manifest["run_id"], "run_isolation_manifest": manifest_path,
        "code_git_sha": manifest["code_git_sha"], "config_hash": manifest["config_hash"],
        "period_from": manifest["period_from"], "period_to": manifest["period_to"],
        "reconciliation": manifest.get("reconciliation"),
        "warnings": manifest.get("warnings", []),
        "n_open_rows": len(opens), "n_close_rows": len(closes), "n_events_paired": len(events),
        "events": events,
        "net_pnl_total": sum(e["net_pnl"] for e in events) if events else 0.0,
        "no_edge_validation_performed": "Questo e' un run DIAGNOSTICO per l'audit di integrita' - "
            "NON una edge validation (nessun cost stress/concentration/OOS/bootstrap qui, quello "
            "sarebbe il contenuto di una futura Phase EDGE_VALIDATION_V1 dedicata, come per "
            "BREAKOUT_ACC/ORDER_BLOCK).",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE723_DIR, "liq_sweep_diagnostic_run_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  status: {payload.get('status')}")
    if payload.get("status") == "COLLECTED":
        print(f"  eventi: {payload['n_events_paired']} net_pnl_total: {payload['net_pnl_total']:.2f}")


if __name__ == "__main__":
    main()
