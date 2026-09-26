#!/usr/bin/env python3
"""Phase 7.9K - verificatore indipendente. Ri-deriva ogni artifact,
verifica il contratto temporale direttamente sul codice sorgente, con
serie sintetiche calcolabili a mano, e verifica che Phase 7.9H/7.9I/
7.9J restino invariate."""
import json
import os
import subprocess
import sys
from datetime import datetime

PHASE79K_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "phase7_9i"))
ROOT = os.path.abspath(os.path.join(PHASE79K_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
sys.path.insert(0, PHASE79K_DIR)
import build_dataset_v2 as dataset_v2_builder  # noqa: E402
import build_decision_card_v2 as decision_builder  # noqa: E402
import build_edge_decomposition_v2 as edge_v2_builder  # noqa: E402
import build_failure_map_v2 as fmap_v2_builder  # noqa: E402
import build_gate_diagnostic_v2 as gate_v2_builder  # noqa: E402
import build_natural_horizon_v2 as horizon_v2_builder  # noqa: E402
import build_path_anatomy_v2 as path_v2_builder  # noqa: E402
import build_sensitivity_v2 as sens_v2_builder  # noqa: E402
import build_temporal_contract as contract_builder  # noqa: E402
import nxs_forward_path_v2 as fp  # noqa: E402

ARTIFACTS = [
    ("breakout_acc_temporal_contract_v1.json", contract_builder.build),
    ("breakout_acc_intended_d1_v2_dataset.json", dataset_v2_builder.build),
    ("breakout_acc_path_anatomy_v2.json", path_v2_builder.build),
    ("breakout_acc_natural_horizon_v2.json", horizon_v2_builder.build),
    ("breakout_acc_edge_decomposition_v2.json", edge_v2_builder.build),
    ("breakout_acc_gate_diagnostic_v2.json", gate_v2_builder.build),
    ("breakout_acc_sensitivity_v2.json", sens_v2_builder.build),
    ("breakout_acc_failure_map_v2.json", fmap_v2_builder.build),
    ("breakout_acc_decision_card_v2.json", decision_builder.build),
]

ALLOWED_DECISIONS = ["MECHANISM_SUPPORTED", "MECHANISM_PARTIALLY_SUPPORTED",
                    "MECHANISM_NOT_SUPPORTED", "INSUFFICIENT_EVIDENCE"]
FORBIDDEN_WORDS = ["PROMOTE", "DEPLOY", "PROFITABLE"]


def _mk(t, o, h, l, c):
    return {"time": t, "open": o, "high": h, "low": l, "close": c}


SYNTH_BARS = [
    _mk(datetime(2024, 1, 1), 100, 200, 10, 102),
    _mk(datetime(2024, 1, 2), 102, 108, 101, 106),
    _mk(datetime(2024, 1, 3), 106, 107, 99, 100),
    _mk(datetime(2024, 1, 4), 100, 120, 100, 115),
    _mk(datetime(2024, 1, 5), 115, 116, 110, 112),
    _mk(datetime(2024, 1, 8), 112, 118, 111, 117),
]


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        saved = load_json(os.path.join(PHASE79K_DIR, fname))
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- 1) test a mano ri-eseguito qui (indipendentemente dal test runner). ---
    entry_time = datetime(2024, 1, 1, 14, 0, 0)
    result = fp.path_anatomy_v2(SYNTH_BARS, entry_time, 101, 1, horizons=[1, 3, 5], max_h=5)
    expected = {"mfe": 19, "mae": 2, "fwd1": 5, "fwd3": 14, "fwd5": 16}
    if result["mfe_price_units"] != expected["mfe"]:
        errors.append(f"test a mano fallito: mfe atteso {expected['mfe']}, trovato "
                      f"{result['mfe_price_units']}")
    if result["mae_price_units"] != expected["mae"]:
        errors.append(f"test a mano fallito: mae atteso {expected['mae']}, trovato "
                      f"{result['mae_price_units']}")
    if result["horizons"]["fwd_return_1d1_price_units"] != expected["fwd1"]:
        errors.append("test a mano fallito: fwd_return_1d1")
    if result["horizons"]["fwd_return_5d1_price_units"] != expected["fwd5"]:
        errors.append("test a mano fallito: fwd_return_5d1")

    # --- 2) nessun estremo precedente al fill (barra d'ingresso H=200/L=10 mai usata). ---
    if result["mfe_price_units"] == 99:
        errors.append("REGRESSIONE: MFE include l'estremo della barra d'ingresso "
                      "(H=200) - il difetto NON e' corretto")

    # --- 3) censura esplicita, mai FAILURE per orizzonti insufficienti. ---
    censored = fp.path_anatomy_v2(SYNTH_BARS, entry_time, 101, 1, horizons=[10], max_h=10)
    if censored["status"] != "CENSORED_INSUFFICIENT_BARS":
        errors.append("orizzonte con barre insufficienti non censurato correttamente")
    if fp.classify_continuation_failure_v2(censored, 10) == "FAILURE":
        errors.append("REGRESSIONE: un orizzonte censurato e' stato classificato FAILURE")

    # --- 4) contratto: bar 1 = prima barra COMPLETA, verificato sul codice sorgente
    # (non solo sul comportamento). ---
    src = open(os.path.join(PHASE79K_DIR, "nxs_forward_path_v2.py"), encoding="utf-8").read()
    fn_start = src.find("def build_forward_curve_v2(")
    fn_body = src[fn_start:src.find("\n\n\n", fn_start)]
    if "window[1:]" in fn_body:
        errors.append("build_forward_curve_v2 sembra ancora scartare la prima barra "
                      "(window[1:]) - il difetto di offset potrebbe non essere corretto")
    if "enumerate(window, start=1)" not in fn_body:
        errors.append("build_forward_curve_v2 non enumera da window[0] come bar 1 - "
                      "verificare la correzione")

    # --- 5) dataset V2: event_id conservati, funnel invariato, identita' preservata. ---
    v1 = load_json(os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9h",
                                "breakout_acc_intended_d1_v1_dataset.json"))
    v2_payload = dataset_v2_builder.build()
    v1_ids = {e["event_id"] for e in v1["payload"]["events"]}
    v2_ids = {e["event_id"] for e in v2_payload["events"]}
    if v1_ids != v2_ids:
        errors.append("event_id non conservati identicamente fra V1 e V2")
    if v2_payload["dataset_name"] != "BREAKOUT_ACC_INTENDED_D1_V1":
        errors.append("dataset_name cambiato - l'identita' di strategia non deve cambiare")
    v1_by_id = {e["event_id"]: e for e in v1["payload"]["events"]}
    for e in v2_payload["events"]:
        v1e = v1_by_id[e["event_id"]]
        if e["funnel_terminal_stage"] != v1e["funnel_terminal_stage"]:
            errors.append(f"funnel_terminal_stage cambiato per {e['event_id']} - non atteso")
        if e.get("entry_fill_price") != v1e.get("entry_fill_price"):
            errors.append(f"entry_fill_price cambiato per {e['event_id']} - non atteso")

    # --- 6) Phase 7.9H/7.9I/7.9J invariate (git diff pulito). ---
    for rel in ("server/research_scripts/phase7/phase7_9h",
               "server/research_scripts/phase7/phase7_9i",
               "server/research_scripts/phase7/phase7_9j"):
        result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=ROOT)
        if result.returncode != 0:
            errors.append(f"{rel} risulta modificato rispetto a HEAD - non atteso in "
                          "questa fase")

    # --- 7) nessun file MQL5/Python modificato. ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "server/backtest.py"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.stdout.strip():
        errors.append(f"file MQL5/Python risultano modificati: {result.stdout.strip()}")

    # --- 8) decisione finale e vocabolario. ---
    decision_doc = load_json(os.path.join(PHASE79K_DIR, "breakout_acc_decision_card_v2.json"))
    if decision_doc["payload"]["final_decision"] not in ALLOWED_DECISIONS:
        errors.append("final_decision fuori dal vocabolario consentito")
    full_text = json.dumps(decision_doc["payload"], ensure_ascii=False).upper()
    for w in FORBIDDEN_WORDS:
        if w in full_text:
            errors.append(f"parola vietata '{w}' trovata nella decision card V2")

    # --- 9) EMA100: 72 valutabili, 3 non valutabili, tutti fra i B-only. ---
    prec = decision_doc["payload"]["ema100_precision"]
    if (prec["n_evaluable_for_ema100"], prec["n_not_evaluable_insufficient_warmup"]) != (72, 3):
        errors.append(f"attesi 72/3 per EMA100, trovato "
                      f"{prec['n_evaluable_for_ema100']}/{prec['n_not_evaluable_insufficient_warmup']}")

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
