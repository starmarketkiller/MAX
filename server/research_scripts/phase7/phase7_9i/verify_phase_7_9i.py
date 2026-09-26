#!/usr/bin/env python3
"""Phase 7.9I - verificatore indipendente. Ri-deriva ogni artifact dai
builder e ri-verifica sul dataset frozen le affermazioni chiave -
fallisce chiuso su qualunque discrepanza."""
import json
import os
import subprocess
import sys

PHASE79I_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
import build_b_only_comparison as b_only_cmp_builder  # noqa: E402
import build_edge_decomposition as edge_builder  # noqa: E402
import build_executive_summary_and_decision_card as exec_builder  # noqa: E402
import build_failure_map_and_robustness as fmap_builder  # noqa: E402
import build_feature_engineering as feat_builder  # noqa: E402
import build_gate_diagnostic as gate_builder  # noqa: E402
import build_mechanism_discovery as mech_builder  # noqa: E402
import build_natural_horizon as horizon_builder  # noqa: E402
import build_path_anatomy as path_builder  # noqa: E402
import build_sensitivity_67_vs_75 as sens_builder  # noqa: E402

ARTIFACTS = [
    ("breakout_acc_feature_engineering_v1.json", feat_builder.build),
    ("breakout_acc_edge_decomposition_v1.json", edge_builder.build),
    ("breakout_acc_path_anatomy_v1.json", path_builder.build),
    ("breakout_acc_natural_horizon_v1.json", horizon_builder.build),
    ("breakout_acc_mechanism_discovery_v1.json", mech_builder.build),
    ("breakout_acc_sensitivity_67_vs_75_v1.json", sens_builder.build),
    ("breakout_acc_gate_diagnostic_v1.json", gate_builder.build),
    ("breakout_acc_b_only_comparison_v1.json", b_only_cmp_builder.build),
    ("breakout_acc_failure_map_and_robustness_v1.json", fmap_builder.build),
    ("breakout_acc_executive_summary_decision_card_v1.json", exec_builder.build),
]

FORBIDDEN_WORDS = ["PROMOTE", "DEPLOY", "PROFITABLE"]
ALLOWED_DECISIONS = ["MECHANISM_SUPPORTED", "MECHANISM_PARTIALLY_SUPPORTED",
                    "MECHANISM_NOT_SUPPORTED", "INSUFFICIENT_EVIDENCE"]


def verify():
    errors = []

    for fname, build_fn in ARTIFACTS:
        saved = load_json(os.path.join(PHASE79I_DIR, fname))
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- 1) il dataset frozen 7.9H non e' stato modificato in questa fase. ---
    dataset_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9h",
                                "breakout_acc_intended_d1_v1_dataset.json")
    result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", dataset_path], cwd=ROOT)
    if result.returncode != 0:
        errors.append("il dataset canonico 7.9H risulta modificato rispetto a HEAD")

    # --- 2) nessun file MQL5/Python di strategia modificato. ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "server/backtest.py"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.stdout.strip():
        errors.append(f"file MQL5/Python risultano modificati: {result.stdout.strip()}")

    # --- 3) Population B (47 OPENED) e' un sottoinsieme di Population A (67
    # live-observed) - nessun evento OPENED ha population_source diverso. ---
    feat = feat_builder.build()
    rows = feat["rows"]
    opened = [r for r in rows if r["funnel_terminal_stage"] == "OPENED"]
    if len(opened) != 47:
        errors.append(f"attesi 47 eventi OPENED, trovati {len(opened)}")
    if not all(r["population_source"] == "LIVE_TRACE_GENERATED" for r in opened):
        errors.append("esiste un evento OPENED con population_source diverso da "
                      "LIVE_TRACE_GENERATED - Population B non e' un sottoinsieme di A")

    # --- 4) gli 8 B-only non si sovrappongono a Population B. ---
    b_only = [r for r in rows if r["population_source"] == "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY"]
    if len(b_only) != 8:
        errors.append(f"attesi 8 eventi B-only, trovati {len(b_only)}")
    if any(r["funnel_terminal_stage"] == "OPENED" for r in b_only):
        errors.append("un evento B-only risulta OPENED - sovrapposizione con Population B "
                      "non attesa")

    # --- 5) ri-verifica diretta BUY/SELL split (36/11) sui 47 OPENED. ---
    n_buy = sum(1 for r in opened if r["direction_label"] == "BUY")
    n_sell = sum(1 for r in opened if r["direction_label"] == "SELL")
    if (n_buy, n_sell) != (36, 11):
        errors.append(f"split BUY/SELL atteso 36/11, trovato {n_buy}/{n_sell}")

    # --- 6) nessuna optimization: verifica che nessun builder contenga ricerche di
    # soglia/grid search (controllo statico sui file sorgente). ---
    forbidden_patterns = ["for tp in", "for sl in", "grid_search", "best_threshold",
                          "optimal_threshold"]
    for fname in os.listdir(PHASE79I_DIR):
        if fname.startswith("build_") and fname.endswith(".py"):
            text = open(os.path.join(PHASE79I_DIR, fname), encoding="utf-8").read().lower()
            for pat in forbidden_patterns:
                if pat in text:
                    errors.append(f"{fname}: pattern potenzialmente di optimization "
                                  f"trovato: '{pat}'")

    # --- 7) decisione finale nel vocabolario consentito, nessuna parola vietata. ---
    exec_doc = load_json(os.path.join(PHASE79I_DIR,
                                      "breakout_acc_executive_summary_decision_card_v1.json"))
    if exec_doc["payload"]["final_decision"] not in ALLOWED_DECISIONS:
        errors.append("final_decision fuori dal vocabolario consentito")
    full_text = json.dumps(exec_doc["payload"], ensure_ascii=False).upper()
    for w in FORBIDDEN_WORDS:
        if w in full_text:
            errors.append(f"parola vietata '{w}' trovata nell'executive summary/decision card")
    if len(exec_doc["payload"]["executive_summary_max_10_lines"]) > 10:
        errors.append("executive summary supera le 10 righe")

    # --- 8) se emerge una nuova ipotesi, deve essere dichiarata esplicitamente NON
    # implementata. ---
    next_hyp = exec_doc["payload"].get("next_hypothesis_not_implemented")
    if next_hyp is not None and next_hyp.get("explicitly_not_implemented") is not True:
        errors.append("la nuova ipotesi proposta non e' esplicitamente marcata come NON "
                      "implementata")

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
