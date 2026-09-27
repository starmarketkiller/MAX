#!/usr/bin/env python3
"""Phase 7.21 punto 9/10 - OOS/forward. Il periodo 2026.08.15-2026.09.27
e' l'UNICO genuinamente untouched (vedi data_exposure_map_v1.json) - mai
attraversato da nessuna versione dell'EA prima di questa fase. Eseguito
UN SOLO run MT5 (nxs_breakoutacc_forward_oos.ini, stessa identita'
canonica/selettore 9 di r002/r003), UNA SOLA volta, DOPO aver congelato
tutto il resto (baseline/costi/execution/temporale/statistica) - non
guardato prima.

Se il campione forward e' troppo piccolo: INSUFFICIENT_OOS_SAMPLE, non
FAILED - esito esplicitamente ammesso dalla task."""
import csv
import os
import sys

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

TRADES_CSV_PATH = os.path.join(PHASE721_DIR, "nexus_trades_forward_oos.csv")
MIN_SAMPLE_FOR_MEANINGFUL_OOS = 5  # dichiarato PRIMA di guardare il risultato


def _load_breakoutacc_closes():
    if not os.path.exists(TRADES_CSV_PATH):
        return None
    with open(TRADES_CSV_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    closes = [r for r in rows if r["strategy"] == "BREAKOUT_ACC" and r["action"] == "CLOSE"]
    return closes


def build():
    closes = _load_breakoutacc_closes()

    if closes is None:
        return {
            "status": "RUN_NOT_YET_CAPTURED",
            "note": "nexus_trades_forward_oos.csv non presente - copiare NEXUS_trades.csv dal "
                   "terminale dopo il completamento del run nxs_breakoutacc_forward_oos.ini prima "
                   "di ri-eseguire questo builder.",
        }

    n = len(closes)
    nets = [float(r["score_or_pnl"]) for r in closes]
    directions_from_reason = [r.get("reason", "") for r in closes]

    if n == 0:
        decision = "INSUFFICIENT_OOS_SAMPLE"
    elif n < MIN_SAMPLE_FOR_MEANINGFUL_OOS:
        decision = "INSUFFICIENT_OOS_SAMPLE"
    else:
        decision = "SAMPLE_SUFFICIENT_FOR_A_FIRST_READ"

    payload = {
        "window": ["2026.08.15", "2026.09.27"],
        "window_genuinely_untouched": True,
        "run_config": "nxs_breakoutacc_forward_oos.ini (selettore 9 isolato, stessa identita' "
            "canonica del run r002/r003, InpResearchMode=true, InpResearchExitMode=0/RAW, lotto "
            "fisso 0.01, leva 1:100)",
        "n_closed_trades_breakout_acc": n,
        "closed_trades_net_pnl": [round(x, 2) for x in nets],
        "net_pnl_total": sum(nets) if nets else 0.0,
        "net_pnl_per_trade": (sum(nets) / n) if n else None,
        "win_rate": (sum(1 for x in nets if x > 0) / n) if n else None,
        "profit_factor": ((sum(x for x in nets if x > 0) / abs(sum(x for x in nets if x <= 0)))
                          if n and any(x <= 0 for x in nets) and sum(x for x in nets if x <= 0) != 0
                          else None),
        "min_sample_threshold_declared_before_result": MIN_SAMPLE_FOR_MEANINGFUL_OOS,
        "decision": decision,
        "decision_meaning": {
            "INSUFFICIENT_OOS_SAMPLE": "Campione troppo piccolo per QUALUNQUE conclusione - non e' "
                "un fallimento della strategia, e' un fallimento del CAMPIONE (finestra troppo "
                "corta per la cadenza di segnali D1 di questa strategia, ~9-16/anno storicamente).",
            "SAMPLE_SUFFICIENT_FOR_A_FIRST_READ": "Campione minimo ma non banale - direzione "
                "dell'effetto osservabile, magnitudo non ancora affidabile.",
        }[decision],
        "single_validation_run_only": True,
        "looked_at_only_after_everything_else_frozen": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE721_DIR, "oos_forward_analysis_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    if payload.get("status") == "RUN_NOT_YET_CAPTURED":
        print("  STATO: run non ancora catturato")
    else:
        print(f"  n_trades: {payload['n_closed_trades_breakout_acc']} decisione: {payload['decision']}")


if __name__ == "__main__":
    main()
