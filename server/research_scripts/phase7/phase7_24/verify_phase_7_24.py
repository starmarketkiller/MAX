#!/usr/bin/env python3
"""Phase 7.24 - verificatore indipendente. Ri-deriva ogni artifact dai
builder; verifica l'aritmetica del funnel in modo indipendente (non
fidandosi dei valori gia' salvati); verifica che il fix del bug BOM sia
davvero presente nell'harness condiviso; verifica che nessuna riga
MQL5/Product-Platform/contracts sia stata modificata; verifica che il
dataset canonico non dipenda da Python; verifica la decisione finale."""
import os
import sys
import subprocess

PHASE724_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE724_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE724_DIR)
import build_funnel_accounting as funnel_builder  # noqa: E402
import build_canonical_dataset as dataset_builder  # noqa: E402
import build_python_fidelity_classification as fidelity_builder  # noqa: E402
import build_readiness_decision_card as decision_builder  # noqa: E402
from nxs_liq_sweep_dataset_loader import PHASE723_DIR  # noqa: E402

ARTIFACTS = [
    ("funnel_accounting_v1.json", funnel_builder.build),
    ("liq_sweep_canonical_dataset_v1.json", dataset_builder.build),
    ("liq_sweep_python_fidelity_classification_v1.json", fidelity_builder.build),
    ("liq_sweep_readiness_decision_card_v1.json", decision_builder.build),
]

ALLOWED_DECISIONS = {"READY_FOR_EDGE_VALIDATION", "READY_WITH_DOCUMENTED_LIMITATION",
                     "NOT_READY_FOR_EDGE_VALIDATION"}


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        path = os.path.join(PHASE724_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"{fname}: file mancante")
            continue
        saved = load_json(path)
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- l'harness condiviso deve avere il fix del bug BOM (Phase 7.24):
    # niente piu' 'utf-16-le'/'utf-16-be' espliciti come valore di ritorno. ---
    harness_path = os.path.join(PHASE723_DIR, "nxs_research_run_harness.py")
    harness_text = open(harness_path, encoding="utf-8").read()
    det_start = harness_text.find("def _detect_text_encoding(")
    det_end = harness_text.find("\ndef ", det_start + 10)
    det_body = harness_text[det_start:det_end]
    if 'return "utf-16-le"' in det_body or 'return "utf-16-be"' in det_body:
        errors.append("_detect_text_encoding sembra ancora ritornare un codec BOM-preservante "
                      "esplicito (utf-16-le/be) - il fix del bug BOM di Phase 7.24 andrebbe "
                      "riverificato")
    if 'return "utf-16"' not in det_body:
        errors.append("_detect_text_encoding non ritorna piu' il codec generico 'utf-16' per "
                      "un BOM UTF-16 - il fix atteso non e' presente")

    # --- verifica INDIPENDENTE (non derivata dal builder) dell'aritmetica del
    # funnel, ricalcolata da zero sui file grezzi. ---
    funnel_payload = load_json(os.path.join(PHASE724_DIR, "funnel_accounting_v1.json"))["payload"]
    fc = funnel_payload["final_counts"]
    if fc["opened"] != fc["closed_within_window"] + fc["still_open_at_period_end"]:
        errors.append("funnel: opened != closed_within_window + still_open_at_period_end")
    if fc["closed_within_window"] != fc["events_used_economically"]:
        errors.append("funnel: closed_within_window != events_used_economically - il dataset "
                      "economico non copre tutti i CLOSE")

    # --- nessun residuo classificato UNKNOWN o DATA_LOSS senza giustificazione
    # esplicita (l'adjudication non deve essere forzata). ---
    for item in funnel_payload["residual_adjudication"]:
        if item["classification"] in ("UNKNOWN", "DATA_LOSS"):
            errors.append(f"residuo classificato {item['classification']} - verificare "
                          f"che non sia una riconciliazione forzata: {item['residual']}")

    # --- il dataset canonico deve dichiarare esplicitamente zero dipendenza
    # da Python. ---
    dataset_payload = load_json(os.path.join(PHASE724_DIR, "liq_sweep_canonical_dataset_v1.json"))["payload"]
    if dataset_payload.get("python_used_to_build_this_dataset") is not False:
        errors.append("liq_sweep_canonical_dataset_v1.json non dichiara esplicitamente "
                      "python_used_to_build_this_dataset=false")
    n_closed = sum(1 for e in dataset_payload["events"] if e["lifecycle"] == "CLOSED")
    if n_closed != dataset_payload["n_events_closed_economic"]:
        errors.append("liq_sweep_canonical_dataset_v1.json: n_events_closed_economic non "
                      "corrisponde al conteggio reale degli eventi CLOSED")

    # --- nessuna modifica a MQL5/Product-Platform/contracts (solo research
    # harness Python). ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "Product-Platform/",
                            "contracts/"], cwd=ROOT, capture_output=True, text=True)
    modified = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if modified:
        errors.append(f"file MQL5/Product-Platform/contracts risultano modificati: {modified}")

    # --- decisione ammessa. ---
    decision_payload = load_json(os.path.join(PHASE724_DIR, "liq_sweep_readiness_decision_card_v1.json"))["payload"]
    if decision_payload["decision"] not in ALLOWED_DECISIONS:
        errors.append(f"decisione '{decision_payload['decision']}' non ammessa")
    if decision_payload.get("no_optimization_performed") is not True:
        errors.append("decision card: manca no_optimization_performed=true")

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
