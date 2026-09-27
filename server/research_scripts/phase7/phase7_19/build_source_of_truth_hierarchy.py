#!/usr/bin/env python3
"""Phase 7.19 punto 18 - SOURCE_OF_TRUTH_HIERARCHY_V1, incorporando
esplicitamente la lezione di Phase 7.16: MT5 e' ground truth per
strategie stateful/tick-sensitive salvo parity dimostrata."""
import os
import sys

PHASE719_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE719_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "hierarchy_name": "SOURCE_OF_TRUTH_HIERARCHY_V1",
        "levels": [
            {
                "level": "execution",
                "authority": "MT5 runtime trace / broker history",
                "scope": "CIO' CHE E' REALMENTE ACCADUTO (fill, prezzo, timing reale) - "
                        "nessun'altra fonte puo' sovrascriverla",
            },
            {
                "level": "event_identity",
                "authority": "MT5 canonical implementation (NXS_Strat_*() reale)",
                "scope": "QUALE meccanismo ha generato l'evento - definito dal codice "
                        "effettivamente eseguito, non dalla sua descrizione o dal suo intento",
            },
            {
                "level": "statistical_analysis",
                "authority": "Python",
                "scope": "Aggregazione, mechanism research, feature engineering SU eventi gia' "
                        "identificati - MAI la fonte primaria di 'questo evento e' successo "
                        "cosi''",
            },
            {
                "level": "reconstructed_visual_context",
                "authority": "market data + EVENT_AUDIT_PACKET_V1",
                "scope": "Il contesto grafico/multi-TF ricostruito per la revisione umana/"
                        "modello - fedele quanto dichiarato dal proprio FIDELITY_FRAMEWORK_V1 "
                        "tier, mai oltre",
            },
            {
                "level": "narrative_interpretation",
                "authority": "Claude/Jarvis/analista umano",
                "scope": "Interpretazione e giudizio SUL packet gia' costruito - non puo' MAI "
                        "modificare i livelli sottostanti, solo commentarli",
            },
        ],
        "python_event_level_authority_rule": {
            "default": "Python NON e' event-level authoritative per default",
            "exception": "Python DIVENTA event-level authoritative per una specifica coppia "
                        "(strategia, versione) SOLO dopo una parity dimostrata esplicitamente "
                        "(es. EVENT_LEVEL_PARITY_VALIDATED nella classificazione di fedelta' "
                        "Phase 7.16) - MAI per default, MAI per estensione automatica da "
                        "un'altra strategia anche se strutturalmente simile",
            "current_status_in_this_project": {
                "BREAKOUT_ACC": "Python e' un clone fedele al 100% per la logica bar-driven "
                               "post-fix (nessun elemento tick-sensibile residuo)",
                "ORDER_BLOCK": "APPROXIMATION_WITH_KNOWN_GAPS (Phase 7.16) - Python NON e' "
                              "event-level authoritative",
                "TSI": "PARTIAL_STRUCTURAL_MODEL (Phase 7.17) - Python NON e' event-level "
                      "authoritative, non validato contro un trace EA live reale",
            },
        },
        "rule_of_thumb": "Per strategie STATEFUL o con dipendenza da prezzo LIVE/tick (non "
                        "solo chiusure di barra), MT5 resta la fonte canonica degli eventi "
                        "reali salvo parity esplicitamente dimostrata - lezione formalizzata "
                        "in Phase 7.16 (ORDER_BLOCK) e riapplicata in Phase 7.17-7.18 (TSI).",
        "conflict_resolution": "Se due livelli sono in disaccordo, vince SEMPRE il livello "
                              "superiore nella lista (execution > event_identity > "
                              "statistical_analysis > reconstructed_visual_context > "
                              "narrative_interpretation) - un'interpretazione narrativa non "
                              "puo' mai 'correggere' un fatto di esecuzione.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE719_DIR, "source_of_truth_hierarchy_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
