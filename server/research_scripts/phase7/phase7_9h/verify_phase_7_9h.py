#!/usr/bin/env python3
"""Phase 7.9H - verificatore indipendente. Ri-deriva ogni artifact dai
builder e ri-verifica sul codice/dati grezzi le affermazioni chiave -
fallisce chiuso su qualunque discrepanza."""
import json
import os
import subprocess
import sys

PHASE79H_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79H_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79H_DIR)
import build_b_only_residual_classification as b_only_builder  # noqa: E402
import build_canonical_event_dataset as dataset_builder  # noqa: E402
import build_dataset_validation_and_deliverables as validation_builder  # noqa: E402


def verify():
    errors = []

    b_only_saved = load_json(os.path.join(PHASE79H_DIR, "b_only_residual_classification_v1.json"))
    dataset_saved = load_json(os.path.join(PHASE79H_DIR, "breakout_acc_intended_d1_v1_dataset.json"))
    validation_saved = load_json(os.path.join(PHASE79H_DIR, "phase_7_9h_validation_and_decision_v1.json"))

    fresh_b_only = b_only_builder.build()
    if canonical_sha256(fresh_b_only) != canonical_sha256(b_only_saved["payload"]):
        errors.append("b_only_residual_classification: ricostruzione differisce dal file salvato")

    fresh_dataset = dataset_builder.build()
    if canonical_sha256(fresh_dataset) != canonical_sha256(dataset_saved["payload"]):
        errors.append("dataset: ricostruzione differisce dal file salvato")

    fresh_validation = validation_builder.build()
    if canonical_sha256(fresh_validation) != canonical_sha256(validation_saved["payload"]):
        errors.append("validation: ricostruzione differisce dal file salvato")

    events = dataset_saved["payload"]["events"]

    # --- 1) 75 eventi totali, id unici. ---
    if len(events) != 75:
        errors.append(f"attesi 75 eventi, trovati {len(events)}")
    ids = [e["event_id"] for e in events]
    if len(ids) != len(set(ids)):
        errors.append("event_id duplicati")

    # --- 2) funnel = 47/11/9/8, verificato anche DIRETTAMENTE dal certificato reale. ---
    cert_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9g",
                             "raw_data", "postfix_certificate_r002.json")
    cert = json.loads(open(cert_path, encoding="utf-8-sig").read())
    funnel = cert["funnel"]
    if (funnel["opened"], funnel["blocked"], funnel["broker_reject"]) != (47, 11, 9):
        errors.append(f"certificato reale non concorda con 47/11/9: {funnel}")
    counts = dataset_saved["payload"]["counts_by_terminal_stage"]
    if (counts["OPENED"], counts["BLOCKED"], counts["BROKER_REJECT"], counts["NEVER_OBSERVED_IN_LIVE_TRACE"]) \
            != (47, 11, 9, 8):
        errors.append(f"conteggi funnel nel dataset non corrispondono: {counts}")

    # --- 3) nessun evento OPENED senza fill reale verificato. ---
    for e in events:
        if e["funnel_terminal_stage"] == "OPENED" and e.get("fill_stage") != "FILLED":
            errors.append(f"evento OPENED {e['event_id']} senza fill FILLED")
        if e["funnel_terminal_stage"] != "OPENED" and "entry_fill_price" in e:
            errors.append(f"evento non-OPENED {e['event_id']} ha un entry_fill_price "
                          "fabbricato")

    # --- 4) ri-verifica diretta della somma dei deal reali esportati (95 = 1 balance + 94
    # deal di trading = 47 posizioni x 2). ---
    deals_path = os.path.join(PHASE79H_DIR, "raw_data", "nxs_diag_deals_export_r003.csv")
    import csv
    with open(deals_path, encoding="utf-8") as f:
        deal_rows = list(csv.DictReader(f))
    gold_deals = [r for r in deal_rows if r["symbol"] == "GOLD"]
    if len(gold_deals) != 94:
        errors.append(f"attesi 94 deal GOLD reali, trovati {len(gold_deals)}")
    positions = set(r["position_id"] for r in gold_deals)
    if len(positions) != 47:
        errors.append(f"attese 47 posizioni distinte, trovate {len(positions)}")

    # --- 5) nessun file MQL5/Python modificato in questa fase (nessuna nuova modifica
    # all'EA live oltre a quanto gia' autorizzato in 7.9G). ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "server/backtest.py"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.stdout.strip():
        errors.append(f"file MQL5/Python risultano modificati: {result.stdout.strip()}")

    # --- 6) i diagnostici EA aggiunti in questa fase sono realmente sola-lettura (nessuna
    # chiamata OrderSend/PositionOpen/trade). ---
    diag_path = os.path.join(PHASE79H_DIR, "NXS_BreakoutAccDealExportDiagnostic.mq5")
    diag_text = open(diag_path, encoding="utf-8").read()
    if "NXS_DIAG_ExportDeals" not in diag_text:
        errors.append("funzione di export diagnostico non trovata nel file atteso")
    # la funzione diagnostica stessa non deve contenere invii di ordine
    export_fn_start = diag_text.find("void NXS_DIAG_ExportDeals()")
    export_fn_end = diag_text.find("\ndouble OnTester()")
    export_fn_body = diag_text[export_fn_start:export_fn_end]
    for forbidden in ("OrderSend", "PositionOpen", "NXS_SafeBuy", "NXS_SafeSell"):
        if forbidden in export_fn_body:
            errors.append(f"la funzione diagnostica contiene '{forbidden}' - non e' sola "
                          "lettura come dichiarato")

    # --- 7) flag di scope. ---
    if dataset_saved["payload"].get("no_optimization_no_edge_search") is not True:
        errors.append("dataset: flag no_optimization_no_edge_search non True")
    if validation_saved["payload"].get("no_profitability_verdict") is not True:
        errors.append("validation: flag no_profitability_verdict non True")
    if validation_saved["payload"]["final_decision"] not in (
            "CANONICAL_DATASET_READY_FOR_MECHANISM_RESEARCH", "CANONICAL_DATASET_NOT_READY"):
        errors.append("final_decision fuori dal vocabolario consentito")

    # --- 8) gli 8 eventi B-only non hanno un P&L usato per la loro classificazione causale
    # (nessun campo di pnl nel loro record). ---
    b_only_events = [e for e in events if e["population_source"] == "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY"]
    if len(b_only_events) != 8:
        errors.append(f"attesi 8 eventi B-only, trovati {len(b_only_events)}")
    for e in b_only_events:
        if "realized_pnl" in e:
            errors.append(f"evento B-only {e['event_id']} ha un P&L (non dovrebbe, mai "
                          "osservato/eseguito)")

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
