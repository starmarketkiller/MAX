#!/usr/bin/env python3
"""Phase 7.19 punti 11-13 - protocollo di campionamento: matched
non-events, near-miss, default 20/20/20/20/20 adattivo alla
numerosita' disponibile."""
import os
import sys

PHASE719_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE719_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "protocol_name": "SAMPLING_PROTOCOL_V1",
        "categories": {
            "winners": "trade chiusi in profitto",
            "losers": "trade chiusi in perdita",
            "random": "campione casuale indipendente dall'esito, per evitare selection bias",
            "blocked_or_near_miss": "segnali bloccati da un gate o quasi-triggerati (vedi "
                                    "NEAR_MISS_EVENT)",
            "matched_non_events": "periodi con condizioni simili ma nessun segnale generato "
                                  "(vedi MATCHED_NON_EVENT)",
        },
        "default_sample_size_per_category": 20,
        "default_is_not_mandatory": True,
        "adaptive_rule": "Se il dataset ha MENO eventi disponibili del default per una "
                        "categoria, usare TUTTI gli eventi di quella categoria (mai "
                        "sovracampionare, mai inventare eventi). Se il dataset e' molto "
                        "piccolo (es. i 60 raw trigger D1 di TSI su 2.9 anni, Phase 7.17), il "
                        "campione = l'intera popolazione disponibile per quella categoria.",
        "matched_non_event_protocol": {
            "matching_criteria_allowed": ["volatility", "regime", "direction", "timeframe",
                                          "session", "level_proximity", "trend", "year_period"],
            "matching_must_be_causal": "I criteri di matching devono essere calcolabili con "
                                       "informazione disponibile ALLA STESSA data del "
                                       "non-evento, mai con conoscenza retrospettiva del "
                                       "periodo (es. 'questo periodo era in trend' va "
                                       "determinato causalmente, non guardando il grafico "
                                       "completo a posteriori)",
            "outcome_never_used_in_selection": "Il campionamento dei controlli NON deve MAI "
                                              "usare l'esito futuro per decidere quali periodi "
                                              "includere - MATCHED_NON_EVENT_V1.outcome_used_"
                                              "in_selection e' vincolato a false nello schema.",
            "purpose": "Capire cosa distingue davvero un segnale da un mercato apparentemente "
                      "simile senza segnale - non per stimare un edge, solo per "
                      "caratterizzare la selettivita' del meccanismo.",
        },
        "near_miss_protocol": {
            "definition": "Un evento in cui mancava una sola condizione, il trigger era quasi "
                         "raggiunto, un gate ha bloccato, era attivo un cooldown, o c'era "
                         "disaccordo HTF.",
            "purpose": "Supporto per una futura conditional edge discovery - QUI solo "
                      "raccolta/classificazione, nessuna discovery eseguita.",
            "schema": "matched_non_event_v1.schema.json (record_kind=NEAR_MISS_EVENT)",
        },
        "selection_disclosure_rule": "Qualunque selezione di 'casi interessanti' che usi il "
                                    "PnL o l'outcome per decidere quali eventi mostrare in un "
                                    "Visual Audit deve essere DICHIARATA ESPLICITAMENTE come "
                                    "tale (mai presentata come campione neutro) - vedi "
                                    "ANTI_BIAS_RULES_V1.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE719_DIR, "sampling_protocol_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
