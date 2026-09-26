#!/usr/bin/env python3
"""Phase 7.9H - validazione del dataset canonico + i 10 deliverable
richiesti + decisione finale (SOLO fra CANONICAL_DATASET_READY_FOR_
MECHANISM_RESEARCH e CANONICAL_DATASET_NOT_READY - mai un verdetto di
profittabilita').
"""
import os
import sys

PHASE79H_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79G_DIR = os.path.abspath(os.path.join(PHASE79H_DIR, "..", "phase7_9g"))
ROOT = os.path.abspath(os.path.join(PHASE79H_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

FORBIDDEN_OPTIMIZATION_ACTIONS = [
    "Nessun parameter tuning su SL/TP/cooldown/soglie di BREAKOUT_ACC.",
    "Nessuna selezione di orizzonti di path anatomy DOPO aver visto i risultati "
    "(i 7 orizzonti [1,3,5,10,20,40,60] barre D1 sono preregistrati nel builder, "
    "non derivati dai risultati).",
    "Nessun filtro/esclusione di eventi basato sul loro P&L realizzato.",
    "Nessuna nuova modifica al codice EA in questa fase (verificato: nessun file "
    "MQL5/Strategie modificato rispetto a HEAD).",
    "Nessuna promozione del dataset a verdetto di profittabilita' - la decisione "
    "finale e' ristretta a READY/NOT_READY per la ricerca sul meccanismo.",
    "Nessuna eliminazione degli 8 eventi B-only residui - ritenuti con "
    "classificazione causale esplicita.",
]


def validate(dataset_payload, b_only_payload):
    checks = []
    events = dataset_payload["events"]

    ids = [e["event_id"] for e in events]
    checks.append({"check": "event_id_uniqueness", "pass": len(ids) == len(set(ids)),
                   "detail": f"{len(ids)} eventi, {len(set(ids))} id unici"})

    from build_canonical_event_dataset import event_id
    stability_ok = all(
        e["event_id"] == event_id("BREAKOUT_ACC", e["direction"], e["d1_bar_date"])
        for e in events)
    checks.append({"check": "event_id_stability_deterministic_rebuild", "pass": stability_ok,
                   "detail": "ogni event_id ricalcolato dalla stessa formula (strategia, "
                             "direzione, data) coincide con quello salvato"})

    n_opened = sum(1 for e in events if e["funnel_terminal_stage"] == "OPENED")
    n_blocked = sum(1 for e in events if e["funnel_terminal_stage"] == "BLOCKED")
    n_reject = sum(1 for e in events if e["funnel_terminal_stage"] == "BROKER_REJECT")
    n_neverobs = sum(1 for e in events if e["funnel_terminal_stage"] == "NEVER_OBSERVED_IN_LIVE_TRACE")
    checks.append({"check": "funnel_matches_frozen_certificate",
                   "pass": (n_opened, n_blocked, n_reject) == (47, 11, 9),
                   "detail": f"opened={n_opened} blocked={n_blocked} broker_reject={n_reject} "
                             "(atteso 47/11/9 dal certificato Phase 7.9G/7.9H)"})
    checks.append({"check": "b_only_residual_retained_not_eliminated", "pass": n_neverobs == 8,
                   "detail": f"{n_neverobs} eventi NEVER_OBSERVED_IN_LIVE_TRACE presenti "
                             "(atteso 8)"})

    no_fabricated_fill = all(
        e["fill_stage"] in ("NOT_APPLICABLE", "NOT_APPLICABLE_NEVER_GENERATED", "UNKNOWN_NO_DEAL_MATCH")
        for e in events if e["funnel_terminal_stage"] != "OPENED")
    checks.append({"check": "no_fabricated_fill_data_for_non_opened_events",
                   "pass": no_fabricated_fill,
                   "detail": "nessun evento BLOCKED/BROKER_REJECT/NEVER_OBSERVED ha campi di "
                             "fill inventati"})

    opened_events = [e for e in events if e["funnel_terminal_stage"] == "OPENED"]
    all_filled = all(e.get("fill_stage") == "FILLED" for e in opened_events)
    checks.append({"check": "all_opened_events_have_verified_fill", "pass": all_filled,
                   "detail": f"{sum(1 for e in opened_events if e.get('fill_stage')=='FILLED')}/"
                             f"{len(opened_events)} eventi OPENED con fill reale verificato"})

    has_signal_and_fill_distinct_fields = all(
        "signal_price" in e and "entry_fill_price" in e and "signal_to_fill_slippage_price_units" in e
        for e in opened_events)
    checks.append({"check": "signal_price_and_fill_price_kept_as_distinct_fields",
                   "pass": has_signal_and_fill_distinct_fields,
                   "detail": "ogni evento OPENED ha signal_price, entry_fill_price e "
                             "signal_to_fill_slippage_price_units come campi separati "
                             "(mai fusi in uno solo)"})

    has_path = all("post_entry_path_anatomy" in e for e in opened_events)
    checks.append({"check": "post_entry_path_anatomy_present_for_all_opened",
                   "pass": has_path, "detail": f"{len(opened_events)} eventi con path anatomy"})

    no_pnl_in_horizons = all(
        set(e["post_entry_path_anatomy"].get("horizons", {}).keys())
        == {f"fwd_return_{h}d1_price_units" for h in dataset_payload["preregistered_horizons_d1_bars"]}
        for e in opened_events if e["post_entry_path_anatomy"].get("status") == "OK")
    checks.append({"check": "path_anatomy_uses_preregistered_horizons_not_tp_sl",
                   "pass": no_pnl_in_horizons,
                   "detail": "gli orizzonti di forward return sono esattamente quelli "
                             "preregistrati, non derivati da TP/SL della strategia"})

    b_only_all_classified = all(
        e.get("causal_status") == "PARTIALLY_EXPLAINED_NOT_ENOUGH_EVIDENCE_FOR_EXACT_MECHANISM"
        for e in b_only_payload["events"])
    checks.append({"check": "b_only_events_causally_classified_not_asserted_with_false_certainty",
                   "pass": b_only_all_classified,
                   "detail": "tutti gli 8 eventi B-only hanno una classificazione causale "
                             "onesta (non certezza fabbricata)"})

    return checks


def build():
    dataset_doc = load_json(os.path.join(PHASE79H_DIR, "breakout_acc_intended_d1_v1_dataset.json"))
    b_only_doc = load_json(os.path.join(PHASE79H_DIR, "b_only_residual_classification_v1.json"))
    parity_doc = load_json(os.path.join(PHASE79G_DIR, "breakout_acc_postfix_signal_parity_v1.json"))

    checks = validate(dataset_doc["payload"], b_only_doc["payload"])
    all_pass = all(c["pass"] for c in checks)

    exact_target = parity_doc["payload"]["exact_parity_target"]
    python_third_impl = {
        "principle": "Python (server/backtest.py:sig_breakout_acc) e' trattato come terza "
            "implementazione indipendente, MAI come ground truth - le tre parity restano "
            "separate.",
        "same_feed_parity_A_vs_B": {
            "description": exact_target["same_feed_parity_A_vs_B"]["description"],
            "matched": exact_target["same_feed_parity_A_vs_B"]["pairing"]["matched"],
            "only_a_live_ea_not_explained": exact_target["same_feed_parity_A_vs_B"]["pairing"]["only_a"],
            "only_b_offline_residual": exact_target["same_feed_parity_A_vs_B"]["pairing"]["only_b"],
        },
        "cross_feed_parity_A_vs_C_live_vs_python": {
            "description": exact_target["cross_feed_parity_A_vs_C"]["description"],
            "pairing": exact_target["cross_feed_parity_A_vs_C"]["pairing"],
        },
        "cross_feed_parity_B_vs_C_offline_vs_python": {
            "description": exact_target["cross_feed_parity_B_vs_C"]["description"],
            "pairing": exact_target["cross_feed_parity_B_vs_C"]["pairing"],
        },
        "note": "Il dataset event-level (fill/path anatomy) e' costruito SOLO dal trace/deal "
            "reale MQL5 (stream A) - Python resta un confronto di parity a livello di segnale, "
            "non fuso nei campi per-evento del dataset canonico (feed diverso, nessun fill "
            "reale disponibile lato Python).",
    }

    deliverables = {
        "1_canonical_event_level_dataset": "breakout_acc_intended_d1_v1_dataset.json "
            f"({len(dataset_doc['payload']['events'])} eventi)",
        "2_event_id_uniqueness_and_stability_tests": "vedi validation_checks e "
            "test_phase_7_9h.py (TestEventId*)",
        "3_provenance_completeness_per_event": "ogni evento ha *_source/provenance "
            "esplicito; UNKNOWN dove non ricostruibile, mai inventato",
        "4_signal_vs_fill_price_distinction": "campi signal_price/entry_fill_price/"
            "signal_to_fill_slippage_price_units distinti per tutti i 47 eventi OPENED "
            "(slippage osservato: 0.0 su tutti - fill Research Mode a mercato, nessun "
            "modello di slippage broker applicato in questo run diagnostico)",
        "5_post_entry_path_anatomy": f"MFE/MAE/tempo-a-MFE-MAE/forward returns a "
            f"{dataset_doc['payload']['preregistered_horizons_d1_bars']} barre D1 "
            "preregistrate, per tutti i 47 eventi OPENED",
        "6_b_only_residual_causal_classification": "b_only_residual_classification_v1.json "
            "(8 eventi, ritenuti non eliminati, meccanismo CROSS_TF_CONTAMINATION escluso "
            "per costruzione, 2 candidati non confermati proposti)",
        "7_python_third_implementation_parity": python_third_impl,
        "8_dataset_validation_checks": checks,
        "9_forbidden_optimization_actions_respected": FORBIDDEN_OPTIMIZATION_ACTIONS,
        "10_final_decision": None,  # riempito sotto
    }

    final_decision = ("CANONICAL_DATASET_READY_FOR_MECHANISM_RESEARCH" if all_pass else
                      "CANONICAL_DATASET_NOT_READY")
    deliverables["10_final_decision"] = final_decision

    return {
        "phase": "7.9H", "dataset_name": "BREAKOUT_ACC_INTENDED_D1_V1",
        "no_optimization_no_edge_search": True,
        "no_profitability_verdict": True,
        "validation_checks": checks,
        "all_checks_passed": all_pass,
        "deliverables": deliverables,
        "final_decision": final_decision,
        "final_decision_allowed_values": [
            "CANONICAL_DATASET_READY_FOR_MECHANISM_RESEARCH", "CANONICAL_DATASET_NOT_READY"],
        "next_step_not_executed": ("Edge Decomposition -> Path Anatomy aggregata -> Natural "
            "Horizon -> Mechanism Discovery - NON iniziato in questa fase, richiede una nuova "
            "istruzione dedicata."),
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79H_DIR, "phase_7_9h_validation_and_decision_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"all_checks_passed={payload['all_checks_passed']}")
    print(f"final_decision={payload['final_decision']}")
    for c in payload["validation_checks"]:
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['check']}")
    return doc


if __name__ == "__main__":
    main()
