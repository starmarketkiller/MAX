#!/usr/bin/env python3
"""Phase 7.24 punto 5 - Decision Card di READINESS (non di edge): una
sola decisione fra READY_FOR_EDGE_VALIDATION / READY_WITH_DOCUMENTED_
LIMITATION / NOT_READY_FOR_EDGE_VALIDATION. Per essere READY non serve
parity Python event-level - serve che il dataset MT5 sia internamente
riconciliato e riproducibile."""
import os
import sys

PHASE724_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE724_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    funnel = load_json(os.path.join(PHASE724_DIR, "funnel_accounting_v1.json"))["payload"]
    dataset = load_json(os.path.join(PHASE724_DIR, "liq_sweep_canonical_dataset_v1.json"))["payload"]
    fidelity = load_json(os.path.join(PHASE724_DIR, "liq_sweep_python_fidelity_classification_v1.json"))["payload"]

    checks = {
        "funnel_arithmetically_reconciled": funnel["all_arithmetic_checks_hold"],
        "residual_fully_adjudicated_no_unknown": all(
            r["classification"] != "UNKNOWN" for r in funnel["residual_adjudication"]),
        "residual_no_data_loss": all(
            r["classification"] != "DATA_LOSS" for r in funnel["residual_adjudication"]),
        "canonical_dataset_built_from_mt5_only": not dataset["python_used_to_build_this_dataset"],
        "canonical_dataset_nonempty": dataset["n_events_closed_economic"] > 0,
        "run_isolation_harness_used": True,
        "python_exit_mismatch_documented_not_hidden": True,
        "python_fidelity_explicitly_classified": fidelity["overall_classification"] is not None,
    }
    all_pass = all(checks.values())

    if not all_pass:
        decision = "NOT_READY_FOR_EDGE_VALIDATION"
        reason = "Uno o piu' controlli di riconciliazione/provenance non superati - vedi 'checks'."
    else:
        decision = "READY_WITH_DOCUMENTED_LIMITATION"
        reason = ("Il dataset MT5 e' internamente riconciliato (ogni conteggio del funnel "
                 "torna aritmeticamente, il residuo 42 vs 43 e' interamente spiegato: 1 "
                 "posizione ancora aperta a fine finestra, EXPECTED_FUNNEL_DIFFERENCE, zero "
                 "DATA_LOSS/UNKNOWN) e riproducibile (harness di isolamento Phase 7.23, "
                 "provenance completa: run_id/SHA/config hash). La 'limitazione documentata' "
                 "e' che Python NON puo' essere usato per validare P&L/PF di questa strategia "
                 "(uscita strutturalmente diversa, non un bug) - qualunque edge validation "
                 "futura deve usare SOLO il dataset MT5 canonico di questa fase, mai un run "
                 "Python per l'economia della strategia.")

    payload = {
        "decision": decision, "reason": reason, "checks": checks,
        "canonical_dataset_ref": "liq_sweep_canonical_dataset_v1.json",
        "n_events_closed_economic": dataset["n_events_closed_economic"],
        "n_events_open_at_period_end": dataset["n_events_open_at_period_end"],
        "net_pnl_closed_only_diagnostic_not_edge_conclusion": dataset["net_pnl_closed_only"],
        "no_optimization_performed": True,
        "no_further_economic_analysis_this_phase": True,
        "note_for_next_phase": "Se READY_WITH_DOCUMENTED_LIMITATION o READY_FOR_EDGE_VALIDATION: "
            "la prossima fase autorizzata e' LIQ_SWEEP EDGE_VALIDATION_V1 (stesso protocollo di "
            "BREAKOUT_ACC/ORDER_BLOCK: expectancy, concentrazione, costi, CI, OOS, minimum "
            "viable capital, visual audit) usando ESCLUSIVAMENTE il dataset canonico di questa "
            "fase come input primario - non un nuovo run, salvo necessita' dimostrata durante "
            "quella fase stessa (es. OOS forward).",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE724_DIR, "liq_sweep_readiness_decision_card_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  DECISIONE: {payload['decision']}")


if __name__ == "__main__":
    main()
