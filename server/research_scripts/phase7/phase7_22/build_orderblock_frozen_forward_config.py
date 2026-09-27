#!/usr/bin/env python3
"""Phase 7.22 punto 11 (continuazione) - se la decisione finale richiede
forward validation, congela una configurazione forward. NON eseguita -
solo specificata."""
import os
import sys

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE722_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, file_sha256  # noqa: E402

STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")


def build():
    payload = {
        "trigger": "orderblock_decision_card_v1.json: decisione richiede forward validation",
        "frozen_as_of_commit": "d8f365e (Phase 7.21, HEAD al momento di questa fase)",
        "frozen_source_sha256": file_sha256(STRAT_PATH),
        "canonical_implementation": "NXS_Strat_OrderBlock() (guardia TF-scoped, Phase 7.14) - "
            "IDENTICA a quella usata per il run di discovery e forward gia' eseguiti in questa fase.",
        "config_frozen": {"selector": 15, "canonical_tf": "PERIOD_D1", "entry_tf": "PERIOD_M15",
            "lot_mode": "FIXED_LOT", "fixed_lot": 0.01,
            "direction_scope": "ENTRAMBE (BUY e SELL) - nessun lato eliminato post-hoc.",
            "ob_mit_scope": "DISABILITATO (selettore isolato 15) - nessuna promozione OB_MIT "
                          "basata su questi risultati."},
        "rules_from_this_point_forward": [
            "NESSUNA modifica alla strategia (geometria zona, gate, SL/TP, selettore) mentre il "
            "forward e' in corso.",
            "NESSUN tuning osservando i risultati del forward mano a mano che arrivano.",
            "OGNI evento va registrato con un Audit Packet (schema EVENT_AUDIT_PACKET_V1).",
            "Nessuna promozione a capitale reale finche' il forward non produce un campione "
            "sufficiente (>=5 trade chiusi) per una nuova lettura del gate finale.",
            "BREAKOUT_ACC resta congelata nella sua configurazione forward separata (Phase 7.21) - "
            "non toccata da questa fase.",
        ],
        "minimum_sample_before_next_gate_reevaluation": 5,
        "not_executed_only_frozen": True, "no_live_deploy": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE722_DIR, "orderblock_frozen_forward_config_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
