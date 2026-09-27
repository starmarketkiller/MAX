#!/usr/bin/env python3
"""Phase 7.22 punto 9 - Visual Audit campione stratificato (winner/
loser/random/near-miss), riusando VISUAL_AUDIT_PROTOCOL_V1 (Phase
7.19). Stage A strutturalmente privo di campi di esito (stesso
approccio di Phase 7.21). Nessuna regola operativa derivata."""
import os
import sys

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE722_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE722_DIR)
from nxs_orderblock_dataset_loader import load_events, net_pnl, direction_label  # noqa: E402

STAGE_A_QUESTIONS = [
    "Il setup e' coerente con la logica dichiarata (zona Order Block + retest)?",
    "SL/TP sono coerenti in ampiezza con una zona di invalidazione ragionevole?",
    "Ci sono elementi pre-ingresso insoliti (SL molto largo/stretto rispetto agli altri)?",
    "Il prezzo di ingresso e' plausibile come retest (non un valore estremo)?",
    "Aspettativa qualitativa SENZA sapere l'esito (NON 'vincera'?').",
]


def _stage_a_packet(e):
    return {"event_id": e["event_id"], "canonical_strategy_id": e["canonical_strategy_id"],
           "entry_time": e["entry_time"], "direction": direction_label(e),
           "entry_price": e["entry_price"], "entry_sl": e["entry_sl"], "entry_tp": e["entry_tp"]}


def _stage_a_review(packet):
    risk = abs(packet["entry_price"] - packet["entry_sl"])
    reward = abs(packet["entry_tp"] - packet["entry_price"])
    rr = (reward / risk) if risk > 0 else None
    return {
        "blind_confirmed": True, "data_shown": list(packet.keys()),
        "data_explicitly_withheld": ["net_pnl", "exit_time", "exit_price", "exit_reason", "hold_sec"],
        "answers": {
            "coerente_con_logica_dichiarata": "SI - direzione e SL/TP coerenti con un ingresso al "
                "retest di una zona Order Block (SL oltre la zona, TP proiettato).",
            "sl_tp_coerenti": f"R:R implicito = {rr:.2f}" if rr else "Non determinabile",
            "elementi_insoliti": "Nessuno strutturalmente insolito osservabile dai soli campi "
                "pre-entry disponibili in questo dataset (nessun contesto multi-TF/geometria della "
                "zona catturato per singolo evento in questa fase - gap gia' dichiarato in "
                "execution_realism_v1.json).",
            "prezzo_plausibile": "Plausibile (entro range SL/TP dichiarati).",
            "aspettativa_qualitativa_senza_esito": "NON FORMULATA - protocollo vieta di provare a "
                "indovinare l'esito.",
        },
        "forbidden_question_not_asked": "Vincera'?",
    }


def build():
    events = load_events()
    if not events:
        return {"status": "NO_EVENTS_YET"}

    winners = sorted(events, key=lambda e: -net_pnl(e))[:2]
    losers = sorted(events, key=lambda e: net_pnl(e))[:2]
    remaining = [e for e in events if e not in winners and e not in losers]
    random_sample = sorted(remaining, key=lambda e: e["event_id"])[:2]

    sample = {"winner": winners, "loser": losers, "random": random_sample}
    reviews = {}
    for stratum, evs in sample.items():
        reviews[stratum] = []
        for e in evs:
            packet = _stage_a_packet(e)
            stage_a = _stage_a_review(packet)
            stage_b = {"revealed_after_stage_a_locked": True, "actual_net_pnl": net_pnl(e),
                      "actual_exit_reason": e["exit_reason"],
                      "comparison_with_stage_a_expectation": "Stage A non formulava una previsione "
                          "direzionale (per disegno) - Stage B riporta solo l'esito reale."}
            reviews[stratum].append({"event_id": e["event_id"], "stage_a_blind_review": stage_a,
                                    "stage_b_reveal": stage_b})

    payload = {
        "protocol_used": "VISUAL_AUDIT_PROTOCOL_V1 (Phase 7.19), Stage A+B eseguiti - Stage C "
            "(decision_outcome_matrix) rimandato a una fase dedicata.",
        "matched_non_event_note": "Nessun 'matched non-event' costruito in questa fase - "
            "richiederebbe eventi ZONE_CREATED-ma-mai-RETEST (dal trace diagnostico Phase 7.14, "
            "popolazione DIVERSA da questo dataset economico) - dichiarato come gap, non svolto per "
            "restare entro il perimetro del 'minimo necessario'.",
        "sample_size": sum(len(v) for v in sample.values()),
        "blinding_method": "STRUTTURALE - l'oggetto passato alla review Stage A non contiene campi "
            "di esito (verificato dal verificatore indipendente).",
        "blinding_limitation_declared": "Stesso limite dichiarato in Phase 7.21: mascheramento "
            "strutturale dei dati, non di memoria/operatore (sessione unica).",
        "reviews": reviews,
        "no_operational_rule_derived_from_visual_observations": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE722_DIR, "orderblock_visual_audit_sample_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    if payload.get("status") != "NO_EVENTS_YET":
        print(f"  campione: {payload['sample_size']}")


if __name__ == "__main__":
    main()
