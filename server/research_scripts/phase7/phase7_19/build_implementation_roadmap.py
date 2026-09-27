#!/usr/bin/env python3
"""Phase 7.19 punto 22 - roadmap di implementazione futura, divisa per
livello (MQL5 / Python-backend / Product Platform / Jarvis / Research
Engine) con dipendenze esplicite. NESSUNA implementazione eseguita in
questa fase."""
import os
import sys

PHASE719_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE719_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "roadmap_name": "IMPLEMENTATION_ROADMAP_V1",
        "principle": "Ogni livello dipende da cio' che il livello precedente produce - "
                    "l'ordine sotto NON e' arbitrario.",
        "levels": {
            "1_MQL5": {
                "what": [
                    "Emettere RUNTIME_IDENTITY_MANIFEST_V1 all'avvio (OnInit) - richiede "
                    "decidere come calcolare build_fingerprint/ex5_hash (limite tecnico MQL5 "
                    "da verificare)",
                    "Generalizzare l'istrumentazione diagnostica (oggi temporanea e "
                    "una-tantum per ORDER_BLOCK/TSI) in un meccanismo PERMANENTE e "
                    "GENERICO per catturare state_before/state_after di QUALUNQUE strategia "
                    "- richiede uno standard di stato serializzabile per strategia (il "
                    "state_blob generico dello schema e' il punto di partenza)",
                    "Esportare Bid/Ask al momento della decisione, non solo al fill",
                    "Esportare i 6 timestamp distinti della timeline (oggi ne esistono "
                    "tipicamente 1-2 per evento)",
                ],
                "depends_on": "Nessuna dipendenza a monte - e' il livello fondazionale",
                "blocked_by": "Nessuno - puo' iniziare indipendentemente, ma richiede "
                             "un'autorizzazione dedicata a modificare l'EA (fuori scope di "
                             "questa fase)",
            },
            "2_python_backend": {
                "what": [
                    "Builder che assembla un EVENT_AUDIT_PACKET_V1 completo a partire da: "
                    "trade log MT5 + trace diagnostico + dati OHLC multi-TF",
                    "Ricostruzione multi_timeframe_context (gia' dimostrata parzialmente in "
                    "Phase 7.13, va generalizzata)",
                    "Motore anti-leakage check (algoritmo gia' specificato in "
                    "ANTI_LEAKAGE_SPECIFICATION_V1, non ancora implementato)",
                    "Motore di campionamento (SAMPLING_PROTOCOL_V1) per selezionare winners/"
                    "losers/random/matched_non_events/near_miss",
                ],
                "depends_on": "Livello 1 (senza dati EA generalizzati, i packet Python restano "
                             "limitati a Fidelity B/C come negli esempi di questa fase)",
                "blocked_by": "Nessuno strutturale - puo' iniziare gia' oggi usando SOLO dati "
                             "gia' disponibili (Fidelity B/C), migliorando quando il Livello 1 "
                             "sara' pronto",
            },
            "3_product_platform": {
                "what": [
                    "Interfaccia di rendering grafico per il contesto multi-TF",
                    "Implementazione tecnica di VISUAL_AUDIT_PROTOCOL_V1 con enforcement "
                    "reale della sequenza Stage A -> B -> C (oggi solo specifica)",
                    "Storage versionato per VISUAL_AUDIT_RESULT_V1 (conclusions_versioned/"
                    "superseded_by)",
                ],
                "depends_on": "Livello 2 (i packet devono esistere prima di poterli mostrare)",
                "blocked_by": "Livello 2 non ancora implementato",
            },
            "4_jarvis": {
                "what": [
                    "Capacita' di interrogare EVENT_AUDIT_PACKET_V1/MATCHED_NON_EVENT_V1 in "
                    "linguaggio naturale",
                    "Generazione di narrative_interpretation rispettando "
                    "SOURCE_OF_TRUTH_HIERARCHY_V1 (mai sovrascrivere i livelli superiori)",
                ],
                "depends_on": "Livello 2 (dati) + Livello 3 (interfaccia di presentazione, "
                             "utile ma non strettamente bloccante)",
                "blocked_by": "Livello 2 non ancora implementato",
            },
            "5_research_engine": {
                "what": [
                    "Automazione della CONDITIONAL_EDGE_DISCOVERY (PRE_ENTRY_FEATURES -> "
                    "OUTCOME) rispettando train/validation/holdout tag e hypothesis_id",
                    "Automazione del campionamento matched_non_events su larga scala",
                ],
                "depends_on": "Livello 2 (dataset con anti-leakage verificato) - MAI iniziare "
                             "discovery su packet con anti_leakage_check_passed=false/null",
                "blocked_by": "Livello 2 non ancora implementato + ANTI_LEAKAGE_SPECIFICATION_V1 "
                             "non ancora automatizzata",
            },
        },
        "correct_order": ["1_MQL5 (parziale, puo' procedere in parallelo)", "2_python_backend",
                         "3_product_platform", "4_jarvis", "5_research_engine"],
        "explicit_non_goal_this_phase": "Nessuno di questi livelli e' stato implementato in "
                                       "Phase 7.19 - solo specificato.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE719_DIR, "implementation_roadmap_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
