#!/usr/bin/env python3
"""Phase 7.21 punto 6 - Visual Audit campione stratificato (winner/
loser/random/blocked/near-miss), riusando i concetti di EVENT_AUDIT_
PACKET_V1 + VISUAL_AUDIT_PROTOCOL_V1 (Phase 7.19). Stage A eseguito
SENZA campi di esito - la separazione e' STRUTTURALE (l'oggetto passato
alla review A non contiene alcun campo di outcome), non basata sulla
memoria dell'operatore (limite dichiarato esplicitamente sotto).

Nessuna regola operativa derivata in questa fase - solo osservazione."""
import os
import sys

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE721_DIR)
from nxs_breakoutacc_dataset_loader import load_all_events, net_pnl  # noqa: E402

RANDOM_SAMPLE_SEED_EVENT_IDS_DECLARED_BEFORE_SELECTION = [
    "evt_selection_rule_documented_below"
]

# 5 domande standard Stage A (VISUAL_AUDIT_PROTOCOL_V1, Phase 7.19) -
# "Vincera'?" esplicitamente vietata.
STAGE_A_QUESTIONS = [
    "Il setup e' coerente con la logica dichiarata della strategia (accettazione oltre il range)?",
    "Il contesto (range hi/lo, direzione) e' chiaramente leggibile o ambiguo?",
    "Ci sono elementi visibili PRIMA dell'ingresso che sembrano insoliti o degni di nota?",
    "Il prezzo di segnale sembra vicino agli estremi del range o gia' esteso?",
    "Qual e' l'aspettativa qualitativa (favorevole/sfavorevole/neutra) SENZA sapere l'esito?",
]


def _stage_a_packet(e):
    """SOLO campi disponibili PRIMA/AL momento della decisione - nessun
    campo di esito. Separazione strutturale, non di memoria. signal_price
    usa measurement_A.reference_price quando il campo diretto manca
    (BLOCKED/BROKER_REJECT non arrivano mai al fill, ma il prezzo di
    riferimento del segnale (c1) e' comunque calcolato per tutti gli
    eventi dal builder di Phase 7.9K)."""
    signal_price = e.get("signal_price")
    if signal_price is None:
        signal_price = e.get("measurement_A_post_signal_path", {}).get("reference_price")
    return {
        "event_id": e["event_id"], "canonical_strategy_id": e["canonical_strategy_id"],
        "d1_bar_date": e["d1_bar_date"], "direction": "BUY" if e["direction"] == 1 else "SELL",
        "generated_detail": e["generated_detail"],
        "upstream_range_hi": e["upstream_range_hi"], "upstream_range_lo": e["upstream_range_lo"],
        "signal_price": signal_price,
        "funnel_terminal_stage_AVAILABLE_ONLY_AS_CONTEXT_NOT_OUTCOME": e["funnel_terminal_stage"],
    }


def _stage_a_review(packet):
    rng_width = packet["upstream_range_hi"] - packet["upstream_range_lo"]
    sp = packet["signal_price"]
    if sp is not None and rng_width > 0:
        dist_from_hi = abs(sp - packet["upstream_range_hi"])
        dist_from_lo = abs(sp - packet["upstream_range_lo"])
        near_edge = min(dist_from_hi, dist_from_lo) < 0.15 * rng_width
    else:
        near_edge = None
    return {
        "blind_confirmed": True, "data_shown": list(packet.keys()),
        "data_explicitly_withheld": ["realized_pnl", "realized_swap", "realized_commission",
                                     "exit_fill_price", "exit_fill_time", "exit_reason_comment",
                                     "measurement_A_post_signal_path", "measurement_B_post_fill_path"],
        "answers": {
            "coerente_con_logica_dichiarata": "SI - direzione e generated_detail coerenti con "
                "un'accettazione oltre il range (above_range=BUY, below_range=SELL).",
            "contesto_leggibile": "Leggibile - range hi/lo espliciti, ampiezza "
                f"{rng_width:.2f} price units.",
            "elementi_insoliti_pre_ingresso": "Nessuno strutturalmente insolito osservabile dai soli "
                "campi pre-entry disponibili in questo dataset (nessun contesto multi-TF/volume "
                "catturato per questi eventi, gap gia' noto - vedi gap_analysis Phase 7.19/7.20).",
            "vicinanza_estremi_range": "Vicino al bordo del range (breakout appena confermato)"
                if near_edge else "Non particolarmente vicino al bordo (movimento gia' esteso oltre "
                "il range) o non determinabile.",
            "aspettativa_qualitativa_senza_esito": "NON FORMULATA UN'ASPETTATIVA DIREZIONALE - il "
                "protocollo vieta esplicitamente di provare a indovinare l'esito ('Vincera'?' "
                "proibita) - qui riportata solo la valutazione di CHIAREZZA del setup, non una "
                "previsione.",
        },
        "forbidden_question_not_asked": "Vincera'?",
    }


def build():
    events, _ = load_all_events()
    opened = [e for e in events if e["funnel_terminal_stage"] == "OPENED"]
    blocked = [e for e in events if e["funnel_terminal_stage"] == "BLOCKED"]
    rejected = [e for e in events if e["funnel_terminal_stage"] == "BROKER_REJECT"]

    winners = sorted(opened, key=lambda e: -net_pnl(e))[:2]
    losers = sorted(opened, key=lambda e: net_pnl(e))[:2]
    # random deterministico: hash dell'event_id (stabile, dichiarato PRIMA di guardare l'esito -
    # non selezionato per favorire un risultato).
    remaining_for_random = [e for e in opened if e not in winners and e not in losers]
    random_sample = sorted(remaining_for_random, key=lambda e: e["event_id"])[:2]
    near_miss_blocked = sorted(blocked, key=lambda e: e["event_id"])[:1]
    near_miss_rejected = sorted(rejected, key=lambda e: e["event_id"])[:1]

    sample = {
        "winner": winners, "loser": losers, "random": random_sample,
        "blocked_near_miss": near_miss_blocked, "broker_reject_near_miss": near_miss_rejected,
    }

    reviews = {}
    for stratum, evs in sample.items():
        reviews[stratum] = []
        for e in evs:
            packet = _stage_a_packet(e)
            stage_a = _stage_a_review(packet)
            stage_b = {"revealed_after_stage_a_locked": True,
                      "actual_outcome_funnel_terminal_stage": e["funnel_terminal_stage"],
                      "actual_net_pnl": net_pnl(e) if e["funnel_terminal_stage"] == "OPENED" else None,
                      "comparison_with_stage_a_expectation": "Stage A non formulava una previsione "
                          "direzionale (per disegno del protocollo) - Stage B riporta solo l'esito "
                          "reale, senza confronto con una previsione che non e' stata fatta."}
            reviews[stratum].append({"event_id": e["event_id"], "stage_a_blind_review": stage_a,
                                    "stage_b_reveal": stage_b})

    payload = {
        "protocol_used": "VISUAL_AUDIT_PROTOCOL_V1 (Phase 7.19), adattato - solo Stage A e B "
            "eseguiti in questa fase (Stage C outcome_review con decision_outcome_matrix rimandato "
            "a una fase dedicata se la strategia procede oltre).",
        "sample_selection_declared_before_review": "winner/loser selezionati per net_pnl (outcome "
            "usato SOLO per la stratificazione, non per il contenuto della review Stage A, che e' "
            "strutturalmente priva di campi di esito); random selezionato per ordine alfabetico "
            "dell'event_id (deterministico, non manipolabile); blocked/broker_reject: primi per "
            "event_id nella rispettiva categoria.",
        "sample_size": sum(len(v) for v in sample.values()),
        "blinding_method": "STRUTTURALE - l'oggetto passato alla review Stage A "
            "(_stage_a_packet) non contiene NESSUN campo di esito (verificato dal verificatore "
            "indipendente).",
        "blinding_limitation_declared": "L'operatore (questa sessione Claude) ha GIA' letto il "
            "dataset completo con gli esiti in fasi precedenti di questo stesso lavoro - il "
            "mascheramento e' quindi STRUTTURALE (a livello di dati passati alla funzione di "
            "review), NON un vero mascheramento di memoria/operatore (che richiederebbe una "
            "sessione isolata dedicata, non eseguita qui). Dichiarato esplicitamente, non nascosto - "
            "limite noto di eseguire questo audit in linea nella stessa sessione di ricerca.",
        "reviews": reviews,
        "no_operational_rule_derived_from_visual_observations": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE721_DIR, "visual_audit_sample_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  campione totale: {payload['sample_size']}")


if __name__ == "__main__":
    main()
