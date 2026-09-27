#!/usr/bin/env python3
"""Phase 7.19 punto 5 - ANTI_LEAKAGE_SPECIFICATION_V1: separazione
obbligatoria AVAILABLE_AT_DECISION_TIME vs FUTURE_INFORMATION, e
progetto del controllo automatico anti-leakage (specifica, non
implementazione)."""
import os
import sys

PHASE719_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE719_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "specification_name": "ANTI_LEAKAGE_SPECIFICATION_V1",
        "core_rule": "Ogni feature usata nell'analisi deve dichiarare esplicitamente QUANDO "
                    "diventa disponibile, da quale barra/tick deriva, se usa una barra chiusa "
                    "o in formazione, se dipende da dati futuri, e se la causalita' e' stata "
                    "verificata - schema: definitions.feature_value in "
                    "event_audit_packet_v1.schema.json.",
        "mandatory_declaration_fields": [
            "available_at_decision_time (bool)",
            "derived_from_bar (riferimento esplicito)",
            "uses_closed_bar_only (bool)",
            "depends_on_future_data (bool)",
            "causality_verified (bool)",
            "causality_verification_method (stringa - COME e' stato verificato, non solo "
            "affermato)",
        ],
        "automatic_check_design": {
            "principle": "Un controllo automatico non puo' fidarsi della sola dichiarazione "
                        "manuale - deve RI-DERIVARE la disponibilita' temporale dai timestamp "
                        "grezzi, stessa disciplina gia' in uso nel progetto per gli altri "
                        "verificatori indipendenti (fail-closed, non fidarsi del builder).",
            "proposed_algorithm": [
                "1. Per ogni feature con available_at_decision_time=true, verificare che "
                "derived_from_bar.close_time <= timeline.decision_time.value (mai barre "
                "ancora in formazione al decision_time, salvo depends_on_future_data "
                "dichiarato true esplicitamente per un caso di studio, mai per una feature "
                "usata realmente dalla strategia)",
                "2. Se uses_closed_bar_only=true ma la barra referenziata ha "
                "status=FORMING al decision_time, FALLIRE il controllo (bug di causalita' "
                "gia' visto in questo progetto: Phase 7.9J su BREAKOUT_ACC EMA100, Phase "
                "7.9K su ORDER_BLOCK forward path)",
                "3. Confrontare multi_timeframe_context.bars_by_timeframe[tf]."
                "subsequent_bars: DEVE essere vuoto/assente in un packet usato per Stage A "
                "del Visual Audit - la sola PRESENZA di subsequent_bars popolati e' un "
                "leak strutturale, indipendentemente dal fatto che vengano mostrati o meno "
                "al reviewer",
                "4. Verificare che nessun campo in decision_time_features."
                "available_at_decision_time referenzi (direttamente o per derivazione "
                "dichiarata) un campo elencato altrove come future_information_excluded",
            ],
            "not_implemented_this_phase": True,
            "reuse_note": "Il pattern e' lo stesso gia' validato nei verificatori indipendenti "
                         "di Phase 7.9-7.18 (fail-closed, ri-derivazione diretta dal sorgente/"
                         "dai dati grezzi, mai fidarsi della sola dichiarazione) - non un "
                         "concetto nuovo per questo progetto, solo la sua prima "
                         "formalizzazione come specifica generale riusabile.",
        },
        "known_historical_leakage_bugs_in_this_project": [
            "Phase 7.9J: BREAKOUT_ACC EMA100 causale - bug di leakage temporale confermato e "
            "corretto (la barra 'in formazione' veniva inclusa nel calcolo)",
            "Phase 7.9K: ORDER_BLOCK forward path - offset di indicizzazione che poteva "
            "includere estremi precedenti al fill",
        ],
        "future_bars_never_in_stage_a": "Il campo multi_timeframe_context.bars_by_timeframe["
                                       "tf].subsequent_bars esiste nello schema SOLO per "
                                       "Stage B/C del Visual Audit - un tool che genera "
                                       "packet per Stage A deve ometterlo interamente, non "
                                       "limitarsi a non mostrarlo nell'interfaccia.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE719_DIR, "anti_leakage_specification_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
