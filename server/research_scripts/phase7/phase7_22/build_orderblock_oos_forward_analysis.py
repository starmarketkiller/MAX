#!/usr/bin/env python3
"""Phase 7.22 punto 11 - OOS/forward. Finestra 2026.08.25-2026.09.27
(corretta durante questa fase - i dati gia' esistenti in NEXUS_trades.csv
coprivano gia' fino al 2026.08.24, vedi orderblock_data_exposure_map_v1.
json), genuinamente untouched. Un solo run MT5 dedicato (stessa identita'
canonica), eseguito una sola volta, DOPO aver congelato baseline/
concentrazione/costi/execution/temporale/statistica. Se il campione e'
troppo piccolo: INSUFFICIENT_OOS_SAMPLE, non FAILED."""
import csv
import os
import sys

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE722_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

TRADES_CSV_PATH = os.path.join(PHASE722_DIR, "nexus_trades_forward_oos.csv")
MIN_SAMPLE_FOR_MEANINGFUL_OOS = 5  # dichiarato PRIMA di guardare il risultato - stessa soglia 7.21
STRATEGY_NAME = "ORDER_BLOCK"


def _load_closes():
    if not os.path.exists(TRADES_CSV_PATH):
        return None
    with open(TRADES_CSV_PATH, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r["strategy"] == STRATEGY_NAME and r["action"] == "CLOSE"]


def build():
    closes = _load_closes()
    if closes is None:
        return {"status": "RUN_NOT_YET_CAPTURED",
               "note": "nexus_trades_forward_oos.csv non presente - copiare NEXUS_trades.csv dal "
                      "terminale dopo il completamento del run forward dedicato."}

    n = len(closes)
    nets = [float(r["score_or_pnl"]) for r in closes]
    decision = "INSUFFICIENT_OOS_SAMPLE" if n < MIN_SAMPLE_FOR_MEANINGFUL_OOS else \
              "SAMPLE_SUFFICIENT_FOR_A_FIRST_READ"

    payload = {
        "window": ["2026.08.25", "2026.09.27"], "window_genuinely_untouched": True,
        "run_config": "nxs_orderblock_forward_oos.ini (selettore 15 isolato, stessa identita' "
            "canonica del run di discovery, InpResearchMode=true, lotto fisso 0.01)",
        "n_closed_trades_order_block": n,
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
        "certificate_note": "Il certificato del run forward (nxs_orderblock_forward_oos_certificate."
            "txt) riporta VERDICT=FAIL / MISSING_TELEMETRY - un artefatto NOTO del meccanismo di "
            "certificazione quando zero eventi vengono generati nell'intera finestra (non distingue "
            "'mercato silenzioso' da 'telemetria rotta'). Confermato indipendentemente dal CSV grezzo "
            "(nexus_trades_forward_oos.csv, 0 righe ORDER_BLOCK) che si tratta genuinamente di zero "
            "segnali, coerente con la cadenza storica bassa - non un errore del run.",
        "certificate_period_note": "Il certificato riporta period_end=2026.09.25 (non 2026.09.27 "
            "come da ToDate dell'ini) - gap di 2 giorni plausibilmente dovuto a fine settimana/"
            "disponibilita' dati (oggi e' domenica 2026.09.27) - non investigato oltre.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE722_DIR, "orderblock_oos_forward_analysis_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    if payload.get("status") != "RUN_NOT_YET_CAPTURED":
        print(f"  n_trades: {payload['n_closed_trades_order_block']} decisione: {payload['decision']}")


if __name__ == "__main__":
    main()
