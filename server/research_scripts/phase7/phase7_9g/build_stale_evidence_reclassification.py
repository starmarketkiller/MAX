#!/usr/bin/env python3
"""Phase 7.9G - punto 12: marca esplicitamente come evidenza storica
dell'implementazione contaminata (NON evidenza per la canonical D1)
ogni risultato generato prima del fix - senza cancellare nulla."""
import os
import sys

PHASE79G_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79G_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "8d2cde76f4233aa0da3ffa83778eee421a60093c"


def build():
    entries = [
        {
            "artifact": "results/cost_calibration_67_rerun/phase_e_breakoutacc_findings.json",
            "claim": "4 trade MT5 reali in 7,5 anni, tutti in perdita",
            "reclassification": "HISTORICAL_IMPLEMENTATION_EVIDENCE",
            "applies_to_canonical_d1": "NOT_EVIDENCE_FOR_CANONICAL_D1",
            "reason": "Generato con l'EA pre-fix (state cross-TF condiviso, "
                "IMPLEMENTATION_DEFECT_CONFIRMED - Phase 7.9F) - il numero di trade riflette "
                "il comportamento contaminato, non la strategia D1 intesa.",
            "modified_in_this_phase": False,
        },
        {
            "artifact": "server/research_scripts/phase7/phase7_9d/breakout_acc_execution_parity_decision_v1.json",
            "claim": "funnel di esecuzione pulito, 4/4 trade riprodotti identici a Phase E",
            "reclassification": "HISTORICAL_IMPLEMENTATION_EVIDENCE",
            "applies_to_canonical_d1": "NOT_EVIDENCE_FOR_CANONICAL_D1",
            "reason": "La riproducibilita' del funnel e' un fatto tecnico valido "
                "(dimostra che l'EA pre-fix era deterministico) ma il conteggio di 4 trade "
                "stesso e' il prodotto del difetto ora corretto - il verdetto tecnico "
                "(EXECUTION_GAP_RESOLVED_OTHER) resta valido, il NUMERO 4 non e' piu' "
                "rappresentativo della strategia D1 intesa.",
            "modified_in_this_phase": False,
        },
        {
            "artifact": "server/research_scripts/phase7/phase7_9c/breakout_acc_event_parity_matrix_v1.json",
            "claim": "80 SIGNAL_FIRE stimati offline (read-only), execution gap ipotizzato",
            "reclassification": "HISTORICAL_IMPLEMENTATION_EVIDENCE",
            "applies_to_canonical_d1": "PARTIALLY_APPLICABLE",
            "reason": "Lo stream MT5 di 7.9C era GIA' una ricostruzione read-only isolata a "
                "D1 (nessuna contaminazione cross-TF, essendo uno script standalone che legge "
                "solo barre D1) - quindi il suo conteggio (80) e' concettualmente PIU' vicino "
                "alla semantica D1 intesa che ai 4 trade dell'EA pre-fix. Non e' pero' "
                "dichiarato 'evidenza valida' senza una nuova verifica di parity col fix "
                "reale (vedi breakout_acc_postfix_signal_parity_v1.json).",
            "modified_in_this_phase": False,
        },
        {
            "artifact": "server/research_scripts/phase7/phase7_9e/*",
            "claim": "scoperta del meccanismo di contaminazione cross-TF",
            "reclassification": "METHODOLOGICAL_FINDING_NOT_STRATEGY_EVIDENCE",
            "applies_to_canonical_d1": "N/A - non e' evidenza sulla strategia, e' evidenza "
                "sul MOTORE - resta interamente valida e non riclassificata.",
            "reason": "Questo artifact non fa affermazioni sulla strategia stessa, solo sul "
                "meccanismo del bug - non richiede riclassificazione.",
            "modified_in_this_phase": False,
        },
        {
            "artifact": "server/research_scripts/phase7/phase7_9f/*",
            "claim": "adjudication IMPLEMENTATION_DEFECT_CONFIRMED",
            "reclassification": "GOVERNANCE_DECISION_STILL_AUTHORITATIVE",
            "applies_to_canonical_d1": "N/A - questo e' il documento che AUTORIZZA la "
                "riclassificazione stessa, non un dato da riclassificare.",
            "reason": "Verdetto di governance, non dato empirico sulla strategia - resta "
                "l'autorita' di riferimento per questa fase.",
            "modified_in_this_phase": False,
        },
    ]

    for e in entries:
        if e["artifact"].startswith("results/") or (e["artifact"].startswith("server/") and "*" not in e["artifact"]):
            p = os.path.join(ROOT, e["artifact"])
            if os.path.exists(p):
                e["sha256_at_reclassification_time"] = file_sha256(p)

    return {
        "phase": "7.9G", "candidate": "BREAKOUT_ACC", "baseline_commit": BASELINE_COMMIT,
        "principle": "Nessun artifact storico viene cancellato o modificato retroattivamente. "
            "Ogni risultato generato con l'implementazione pre-fix (cross-TF contaminata) e' "
            "marcato esplicitamente come HISTORICAL_IMPLEMENTATION_EVIDENCE / "
            "NOT_EVIDENCE_FOR_CANONICAL_D1 - una nota di governance, non una cancellazione.",
        "reclassified_entries": entries,
        "no_artifacts_modified": True,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79G_DIR, "breakout_acc_stale_evidence_reclassification_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    return doc


if __name__ == "__main__":
    main()
