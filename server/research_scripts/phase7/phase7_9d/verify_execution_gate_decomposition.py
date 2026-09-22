#!/usr/bin/env python3
"""Phase 7.9D - verificatore indipendente. Ri-deriva TUTTO dai raw file
(certificato reale + Journal Tester reale + stream 7.9C gia' frozen),
senza fidarsi di alcun numero gia' scritto negli artifact prodotti -
fallisce chiuso su qualunque discrepanza.
"""
import json
import os
import sys

PHASE79D_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79D_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79D_DIR)
import build_execution_events_and_gate_counts as ev_builder  # noqa: E402
import build_execution_parity_decision as decision_builder  # noqa: E402

ALLOWED_VERDICTS = {
    "EXISTING_POSITION_GATE_DOMINANT", "RISK_GATE_DOMINANT", "PREFLIGHT_GATE_DOMINANT",
    "ORDER_EXECUTION_FAILURE_DOMINANT", "ROUTER_GATE_DOMINANT", "MULTI_GATE_EXECUTION_LOSS",
    "EXECUTION_GAP_RESOLVED_OTHER", "EXECUTION_GAP_STILL_UNRESOLVED",
}
ALLOWED_NEXT_DECISIONS = {
    "REBUILD_CANONICAL_BREAKOUT_ACC_DATASET", "FIX_EXECUTION_IMPLEMENTATION_BEFORE_RESEARCH",
    "BLOCKED_EXECUTION_IDENTITY_UNRESOLVED",
}


def verify():
    errors = []

    # --- 1) Funnel map: struttura statica coerente, nessun P&L, nessuna nuova
    # strumentazione dichiarata come "nuova" (deve dichiararsi PREESISTENTE).
    funnel_path = os.path.join(PHASE79D_DIR, "breakout_acc_execution_funnel_v1.json")
    funnel_doc = load_json(funnel_path)
    funnel_payload = funnel_doc["payload"]
    if canonical_sha256(funnel_payload) != funnel_doc["canonical_sha256"]:
        errors.append("funnel map: canonical_sha256 non corrisponde al payload")
    if "PREESISTENTI" not in funnel_payload["instrumentation_source"] and \
       "PREESISTENTI".lower() not in funnel_payload["instrumentation_source"].lower():
        errors.append("funnel map: non dichiara esplicitamente che la strumentazione e' preesistente")
    if len(funnel_payload["funnel_steps"]) < 20:
        errors.append("funnel map: numero di step sospettosamente basso (mappa incompleta?)")

    # --- 2) Eventi + gate counts: ricostruzione INDIPENDENTE dai file raw. ---
    events_path = os.path.join(PHASE79D_DIR, "breakout_acc_execution_events_v1.json")
    counts_path = os.path.join(PHASE79D_DIR, "breakout_acc_execution_gate_counts_v1.json")
    events_doc = load_json(events_path)
    counts_doc = load_json(counts_path)

    fresh_records, fresh_accounting, fresh_cross_check, fresh_cert = ev_builder.build()
    stored_records = events_doc["payload"]["events"]
    if canonical_sha256(fresh_records) != canonical_sha256(stored_records):
        errors.append("events: ricostruzione indipendente dal Journal differisce da quella salvata")
    if canonical_sha256(fresh_accounting) != canonical_sha256(counts_doc["payload"]["accounting"]):
        errors.append("gate_counts: accounting ricalcolato differisce da quello salvato")

    # --- 3) Invariante di funnel accounting (punto 5 dell'istruzione). ---
    acc = counts_doc["payload"]["accounting"]
    if acc["total_generated"] != acc["opened"] + acc["blocked"] + acc["broker_reject"]:
        errors.append("EXECUTION_FUNNEL_ACCOUNTING_FAIL: generated != opened+blocked+broker_reject")
    if not acc["invariant_holds"]:
        errors.append("accounting.invariant_holds e' False - il funnel non e' riconciliato")

    # --- 4) Certificato reale: hash del file sorgente citato coincide col reale. ---
    cross_check = counts_doc["payload"]["certificate_cross_check"]
    cert_full_path = os.path.join(ROOT, cross_check["certificate_path"])
    if not os.path.exists(cert_full_path):
        errors.append(f"certificato citato non trovato su disco: {cert_full_path}")
    else:
        real_cert = load_json(cert_full_path)
        if real_cert.get("funnel", {}).get("generated") != acc["total_generated"]:
            errors.append("il certificato reale su disco non coincide piu' con quello letto (modificato?)")
        if real_cert.get("strategy") != "BREAKOUT_ACC" or real_cert.get("selector") != 9:
            errors.append(f"certificato non e' per BREAKOUT_ACC/selector=9: strategy={real_cert.get('strategy')} selector={real_cert.get('selector')}")
        if real_cert.get("research_mode") is not True:
            errors.append("certificato: research_mode non e' true - trace potrebbe non essere stato attivo")

    # --- 5) Decisione finale: ricostruzione indipendente, verdetto/decisione
    # entro i set ammessi, coerenza interna. ---
    decision_path = os.path.join(PHASE79D_DIR, "breakout_acc_execution_parity_decision_v1.json")
    decision_doc = load_json(decision_path)
    fresh_decision_payload = decision_builder.build()
    if canonical_sha256(fresh_decision_payload) != canonical_sha256(decision_doc["payload"]):
        errors.append("decision: ricostruzione indipendente differisce da quella salvata")

    payload = decision_doc["payload"]
    if payload["final_verdict"] not in ALLOWED_VERDICTS:
        errors.append(f"final_verdict '{payload['final_verdict']}' fuori dal set ammesso")
    if payload["next_decision"] not in ALLOWED_NEXT_DECISIONS:
        errors.append(f"next_decision '{payload['next_decision']}' fuori dal set ammesso")
    if payload.get("next_step_not_executed") is not True:
        errors.append("next_step_not_executed non e' True - la fase potrebbe aver ecceduto lo scope")

    # --- 6) Riproducibilita' vs Phase E: i 4 trade devono combaciare esattamente. ---
    repro = payload["reproducibility_check_vs_phase_e"]
    if not repro["count_matches_phase_e"]:
        errors.append("il conteggio dei trade reali non coincide con Phase E (4 attesi)")
    if not repro["timestamps_match_phase_e_exactly"]:
        errors.append("i timestamp dei trade reali non coincidono esattamente con Phase E")

    # --- 7) Pairing con 7.9C: aritmetica interna coerente. ---
    pairing = payload["signal_reconstruction_vs_real_ea_pairing"]
    if pairing["matched"] + pairing["missing_in_diagnostic_run"] != pairing["expected_signal_fire_from_7_9c_readonly_reconstruction"]:
        errors.append("pairing: matched + missing != totale atteso dalla 7.9C")
    if pairing["matched"] + pairing["extra_in_diagnostic_run"] != pairing["observed_generated_by_actual_ea_in_diagnostic_run"]:
        errors.append("pairing: matched + extra != totale osservato nel run diagnostico")

    # --- 8) Nessun P&L usato per la diagnosi (stesso vincolo della 7.9C). ---
    full_text = json.dumps(payload).lower()
    for term in ("expectancy", "\"pf\":", "profit_factor", "win_rate"):
        if term in full_text:
            errors.append(f"trovato termine P&L vietato nell'artifact di diagnosi: {term}")

    # --- 9) Vincoli di scope preservati. ---
    for flag in ("volbrk_not_reopened", "h006_not_reopened", "hvcw_backlog_only"):
        if payload.get(flag) is not True:
            errors.append(f"flag di scope '{flag}' non True")

    # --- 10) Deliverable presenti e non vuoti. ---
    for fname in ("breakout_acc_execution_funnel_v1.json", "breakout_acc_execution_events_v1.csv",
                  "breakout_acc_execution_events_v1.json", "breakout_acc_execution_gate_counts_v1.json",
                  "breakout_acc_execution_parity_decision_v1.json"):
        p = os.path.join(PHASE79D_DIR, fname)
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            errors.append(f"deliverable mancante o vuoto: {fname}")

    return errors


def main():
    errors = verify()
    if errors:
        print(f"VERIFY FAILED: {len(errors)} problemi")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("VERIFY OK: tutti i controlli indipendenti passati (0 problemi)")
    sys.exit(0)


if __name__ == "__main__":
    main()
