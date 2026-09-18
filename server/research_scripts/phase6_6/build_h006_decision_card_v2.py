#!/usr/bin/env python3
"""Phase 6.6 sec.5 - Decision Card v2 per H006: JSON strutturato, leggibile
da una UI senza dover interpretare Markdown. Nessun campo qui viene
ricalcolato - riflette esclusivamente decisioni gia' prese in Phase 6
(verdetto) e Phase 6.5 (motivi metodologici aggiuntivi)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical_utils import ROOT, load_json, save_json, wrap_with_provenance, rel_path  # noqa: E402

PHASE6_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6")
PHASE65_DIR = os.path.join(ROOT, "server", "research_scripts", "phase6_5")
PHASE66_DIR = os.path.dirname(os.path.abspath(__file__))


def build():
    p6 = load_json(os.path.join(PHASE6_DIR, "h006_primary_result.json"))["primary_result"]
    dep = load_json(os.path.join(PHASE65_DIR, "h006_dependence_audit.json"))
    gate = load_json(os.path.join(PHASE65_DIR, "dependence_audit_gate_result_H006.json"))

    card = {
        "hypothesis_id": "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT",
        "current_grade": "E2",
        "decision": "RETAIN_E2",
        "promotion_allowed": False,
        "next_stage_allowed": False,
        "next_stages_explicitly_not_authorized": ["E3", "E4", "E5"],
        "primary_reason": (
            f"DeltaP osservato nel true holdout ({p6['delta_p']:.4f}) e' sotto la soglia minima di "
            f"materialita' pre-registrata (0.15), con CI95 Wilson sovrapposte fra evento e baseline "
            f"(ci95_non_overlapping={p6['ci95_non_overlapping']}). Verdetto pre-registrato: {p6['VERDICT']}."
        ),
        "secondary_reasons": [
            "Consistenza di direzione BUY/SELL fallita nel test primario (Phase 6): l'intero effetto aggregato era concentrato sul lato SELL.",
            f"Audit di dipendenza (Phase 6.5): dependence_flag={dep['dependence_flag']}, overlap_rate={dep['overlap_rate']:.3f} - il campione nominale di {dep['n_nominal']} eventi osserva un numero di movimenti di mercato indipendenti stimato fra {dep['n_effective']['cluster_count_approximation']} e {dep['n_nominal']} a seconda del metodo.",
            "Anche correggendo il baseline per direzione (Phase 6.5, Directional Baseline v3), nessuno dei due lati (BUY o SELL) supera da solo la soglia di non-sovrapposizione CI95.",
        ],
        "failed_gates": [
            {"gate": "H006_PASS_CRITERIA", "phase": "Phase6", "result": "NOT_MET", "detail": p6["verdict_reason"]},
        ],
        "passed_gates": [
            {"gate": "LEAKAGE_GUARD_PASS", "phase": "Phase6", "result": "PASS"},
            {"gate": "DEPENDENCE_AUDIT_PASS", "phase": "Phase6.5", "result": gate["verdict"]},
        ],
        "unresolved_questions": [
            "L'asimmetria SELL_SWEEP_RECLAIM_ASYMMETRY e' un artefatto di regime (periodo 2022-2023) o una proprieta' strutturale del fenomeno? Non determinabile senza un nuovo holdout indipendente dedicato.",
            "I tre metodi di n_effective (46/91/115) divergono sostanzialmente - quale (se uno solo) e' piu' rappresentativo per QUESTO tipo di evento resta una domanda aperta di metodologia, non solo di questo caso.",
            "Un vero CROSS_FEED_VALIDATION (E4, fonte dati diversa da Dukascopy) non e' stato tentato - non e' chiaro se varrebbe la pena investirci prima di risolvere l'asimmetria direzionale.",
        ],
        "evidence_record_reference": "server/research_scripts/phase6_6/h006_evidence_v2.json",
        "post_hoc_observations_reference": "server/research_scripts/phase6_6/post_hoc_observations_v1.json",
    }
    sources = [
        os.path.join(PHASE6_DIR, "h006_primary_result.json"),
        os.path.join(PHASE65_DIR, "h006_dependence_audit.json"),
        os.path.join(PHASE65_DIR, "dependence_audit_gate_result_H006.json"),
    ]
    return card, sources


if __name__ == "__main__":
    card, sources = build()
    wrapped = wrap_with_provenance(card, script="server/research_scripts/phase6_6/build_h006_decision_card_v2.py")
    out_path = os.path.join(PHASE66_DIR, "h006_decision_card_v2.json")
    save_json(out_path, wrapped)
    print(f"canonical_sha256: {wrapped['canonical_sha256']}")
    print(f"written: {out_path}")
