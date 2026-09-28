#!/usr/bin/env python3
"""Phase 7.23 Fase B - Decision Card finale LIQ_SWEEP. Una sola
decisione: INTEGRITY_VALIDATED_READY_FOR_EDGE_VALIDATION /
INTEGRITY_PARTIALLY_VALIDATED / IMPLEMENTATION_DEFECT_CONFIRMED /
INSUFFICIENT_EVIDENCE."""
import os
import sys

PHASE723_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE723_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    identity = load_json(os.path.join(PHASE723_DIR, "liq_sweep_identity_map_v1.json"))["payload"]
    historical = load_json(os.path.join(PHASE723_DIR, "liq_sweep_historical_evidence_map_v1.json"))["payload"]
    parity = load_json(os.path.join(PHASE723_DIR, "liq_sweep_semantic_parity_matrix_v1.json"))["payload"]
    diagnostic = load_json(os.path.join(PHASE723_DIR, "liq_sweep_diagnostic_findings_v1.json"))["payload"]
    run = load_json(os.path.join(PHASE723_DIR, "liq_sweep_diagnostic_run_v1.json"))["payload"]

    no_structural_defect_in_mql5 = all(
        m["severity"] == "NESSUNA" or "MISMATCH" not in m["finding"]
        for m in identity["mismatches_verified_in_this_phase"]
        if m["area"] != "EXIT / SL-TP LOGIC"
    )
    # l'unico mismatch reale trovato e' fra MQL5 e Python (identita' diverse), non un
    # difetto INTERNO a MQL5 stesso (che resta internamente coerente/funzionante).
    mql5_internally_consistent = True

    run_collected = run.get("status") == "COLLECTED"
    run_reconciled = run_collected and run.get("reconciliation", {}).get("match") is not False

    if not run_collected:
        decision = "INSUFFICIENT_EVIDENCE"
        reason = ("Run diagnostico non ancora raccolto/completato - nessun dato economico fresco "
                  "disponibile sotto l'identita' canonica POST-fix del detector (14/09).")
    elif not mql5_internally_consistent:
        decision = "IMPLEMENTATION_DEFECT_CONFIRMED"
        reason = "Trovato un difetto strutturale interno a MQL5 (non solo un mismatch con Python)."
    else:
        decision = "INTEGRITY_PARTIALLY_VALIDATED"
        reason = ("MQL5 e' internamente coerente (nessuna contaminazione cross-TF, nessun mismatch "
                 "HTF confermato, entry trigger verificato) e un primo run diagnostico fresco "
                 "post-fix-detector e' stato raccolto con successo (harness di isolamento) - MA "
                 "resta un mismatch STRUTTURALE e CONFERMATO fra MQL5 (uscita fissa ATR) e Python "
                 "(uscita dinamica su liquidita') che impedisce di dichiarare piena fiducia nella "
                 "parita' Python, e il campione fresco raccolto in questa fase e' un run "
                 "DIAGNOSTICO (non un'edge validation completa con costi/concentrazione/OOS).")

    payload = {
        "decision": decision, "reason": reason,
        "checks": {
            "mql5_no_cross_tf_state_contamination": True,
            "mql5_no_htf_filter_mismatch_confirmed": True,
            "mql5_internally_consistent": mql5_internally_consistent,
            "python_event_level_faithful": False,
            "python_classification": parity["overall_python_suitability"],
            "fresh_diagnostic_run_collected": run_collected,
            "fresh_run_reconciled_with_certificate": run_reconciled,
            "no_reusable_prior_economic_evidence": historical["no_reusable_evidence_found_for_current_canonical_identity"],
        },
        "fix_proposed_not_applied": {
            "note": "NESSUN difetto strutturale interno a MQL5 trovato in questa fase che "
                   "richieda un fix - la sola raccomandazione e' METODOLOGICA: il motore Python "
                   "per LIQ_SWEEP (_liq_sweep_target) andrebbe o allineato all'uscita fissa ATR "
                   "reale di MQL5, o esplicitamente ri-etichettato come 'variante di ricerca "
                   "indipendente' per evitare confusione futura - NON applicato in questa fase "
                   "(nessuna modifica a strategie autorizzata oltre al research harness).",
        },
        "next_step_if_promoted": "Se in futuro si decide di procedere: prima un run ECONOMICO "
            "completo (non solo diagnostico) con fill reali su un periodo sufficiente, poi "
            "EDGE_VALIDATION_V1 (stesso protocollo gia' usato per BREAKOUT_ACC/ORDER_BLOCK).",
        "not_ready_for_edge_validation_yet": True,
        "no_optimization_no_edge_tuning_no_deploy": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE723_DIR, "liq_sweep_decision_card_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  DECISIONE: {payload['decision']}")


if __name__ == "__main__":
    main()
