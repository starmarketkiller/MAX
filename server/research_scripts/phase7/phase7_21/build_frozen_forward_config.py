#!/usr/bin/env python3
"""Phase 7.21 punto 10 - poiche' la decisione finale e'
EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION (nessun vero holdout storico
disponibile, campione forward insufficiente - 1 solo trade), congela
una configurazione demo forward. NON eseguita in questa fase - solo
specificata/congelata."""
import os
import sys

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, file_sha256  # noqa: E402

STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")


def build():
    payload = {
        "trigger": "decision_card_v1.json: EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION",
        "frozen_as_of_commit": "7e2c764 (Phase 7.20, HEAD al momento di questa fase)",
        "frozen_source_sha256": file_sha256(STRAT_PATH),
        "canonical_implementation": "NXS_Strat_BreakoutAcc() (guardia di cooldown per-direzione, "
            "Phase 7.9G) - IDENTICA a quella usata per il run forward gia' eseguito in questa fase.",
        "config_frozen": {
            "selector": 9, "canonical_tf": "PERIOD_D1", "entry_tf": "PERIOD_M15",
            "lot_mode": "FIXED_LOT", "fixed_lot": 0.01,
            "direction_scope": "ENTRAMBE (BUY e SELL) - H2 (BUY piu' robusto) resta un'ipotesi, non "
                "un filtro applicato all'esecuzione. Escludere SELL ora sarebbe esattamente "
                "l'operazione vietata dal punto 12 della task ('eliminare SELL perche' hanno "
                "performato peggio').",
        },
        "rules_from_this_point_forward": [
            "NESSUNA modifica alla strategia (formula, gate, SL/TP, selettore) mentre il forward e' "
            "in corso.",
            "NESSUN tuning osservando i risultati del forward mano a mano che arrivano.",
            "OGNI evento (aperto, bloccato, rifiutato) va registrato con un Audit Packet (schema "
            "EVENT_AUDIT_PACKET_V1, Phase 7.19) - non solo i trade aperti.",
            "Nessuna promozione a capitale reale finche' il forward non produce un campione "
            "sufficiente (stessa soglia dichiarata qui: >=5 trade chiusi) per una nuova lettura del "
            "gate finale.",
        ],
        "minimum_sample_before_next_gate_reevaluation": 5,
        "current_forward_sample_available": 1,
        "additional_forward_trades_needed": 4,
        "estimated_wait_given_historical_cadence": "La cadenza storica e' 9-16 segnali generati/anno "
            "(non tutti aperti) - un campione di 5 trade CHIUSI potrebbe richiedere diversi mesi, "
            "non settimane. Nessuna scorciatoia proposta (es. multi-simbolo/multi-broker per "
            "accelerare) in questa fase.",
        "not_executed_only_frozen": True,
        "no_live_deploy": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE721_DIR, "frozen_forward_config_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
