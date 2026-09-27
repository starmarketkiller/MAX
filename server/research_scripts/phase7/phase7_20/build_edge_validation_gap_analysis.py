#!/usr/bin/env python3
"""Phase 7.20 punto 5 - gap mancanti prima dell'edge validation vera e
propria, per le strategie shortlisted e per le PROMISING_BUT_NEEDS_
INTEGRITY_WORK piu' vicine a entrarci."""
import os
import sys

PHASE720_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE720_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "BREAKOUT_ACC": [
            "Benchmark esplicito (random entry / buy-and-hold) mai calcolato - necessario per lo Stadio 1 "
            "di EDGE_VALIDATION_V1.",
            "Nessun vero holdout temporale (OOS) - richiede raccogliere un periodo successivo "
            "indipendente, non uno split retroattivo.",
            "SL/TP reali non riesaminati nell'ottica capital-a-rischio (serve prima di qualunque stima di "
            "minimum viable capital).",
        ],
        "ORDER_BLOCK": [
            "Zero evidenza economica per l'implementazione V2 - serve un nuovo run MT5 reale (non "
            "Research Mode) preregistrato prima di essere lanciato.",
            "Fill reali, spread, slippage, commissioni: nessuno di questi dati esiste oggi per V2.",
            "Periodo del nuovo run non ancora deciso - deve attraversare piu' di un regime per essere "
            "utile, ma non cosi' lungo da rischiare l'overfitting gia' documentato altrove nel progetto.",
        ],
        "LIQ_SWEEP_and_FVG_CONT_before_they_can_join_the_shortlist": [
            "Audit di integrita' dedicato (stesso schema gia' usato 3 volte per BREAKOUT_ACC/ORDER_BLOCK/"
            "TSI) - oggi nessuna delle due e' mai stata controllata per il difetto CROSS_TIMEFRAME_STATE_"
            "CONTAMINATION.",
            "Per FVG_CONT specificamente: mappare la condivisione di STRAT_FVG_CONT con IFVG/FVG_MIT/"
            "FVG_MIT_WINDOW (stesso lavoro gia' fatto per OB_MIT/ORDER_BLOCK in Phase 7.14/7.15) prima di "
            "qualunque conclusione.",
            "Conteggio trade reale per il PF sweep37 di entrambe - l'artifact riassuntivo riporta solo il "
            "PF, non il campione.",
        ],
        "cross_cutting_gap_entire_corpus": "Nessuna strategia del corpus (comprese le 2 shortlisted) ha "
            "oggi un vero holdout out-of-sample gia' pronto - e' il gap PIU' RICORRENTE trovato in questa "
            "fase, coerente con il gap 'runtime_fingerprint assente in tutti gli esempi' trovato in Phase "
            "7.19 per un motivo diverso ma della stessa natura (infrastruttura di misurazione ancora "
            "incompleta rispetto alla ricchezza della logica di trading).",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE720_DIR, "edge_validation_gap_analysis_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
