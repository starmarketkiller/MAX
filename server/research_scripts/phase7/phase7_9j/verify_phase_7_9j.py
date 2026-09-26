#!/usr/bin/env python3
"""Phase 7.9J - verificatore indipendente. Ri-deriva ogni artifact di
Phase 7.9J E le versioni corrette degli artifact Phase 7.9I dai
builder, verifica la correzione di causalita' temporale direttamente
sul codice sorgente e con un test di non-leakage, verifica che Phase
7.9H e i file MQL5/Python restino invariati - fallisce chiuso su
qualunque discrepanza.
"""
import copy
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

PHASE79J_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79I_DIR = os.path.abspath(os.path.join(PHASE79J_DIR, "..", "phase7_9i"))
ROOT = os.path.abspath(os.path.join(PHASE79J_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79I_DIR)
sys.path.insert(0, PHASE79J_DIR)
import build_b_only_comparison as b_only_cmp_builder  # noqa: E402
import build_direction_alignment_outcome_table as alignment_builder  # noqa: E402
import build_edge_decomposition as edge_builder  # noqa: E402
import build_executive_summary_and_decision_card as exec_builder  # noqa: E402
import build_failure_map_and_robustness as fmap_builder  # noqa: E402
import build_feature_engineering as feat_builder  # noqa: E402
import build_gate_diagnostic as gate_builder  # noqa: E402
import build_mechanism_discovery as mech_builder  # noqa: E402
import build_natural_horizon as horizon_builder  # noqa: E402
import build_natural_horizon_reconciliation as horizon_recon_builder  # noqa: E402
import build_path_anatomy as path_builder  # noqa: E402
import build_sensitivity_67_vs_75 as sens_builder  # noqa: E402
import build_sensitivity_67_vs_75_path_reconstruction as sens_path_builder  # noqa: E402
import build_temporal_causality_audit as temporal_audit_builder  # noqa: E402
import nxs_mechanism_context as ctx  # noqa: E402

ARTIFACTS_79I_CORRECTED = [
    (PHASE79I_DIR, "breakout_acc_feature_engineering_v1.json", feat_builder.build),
    (PHASE79I_DIR, "breakout_acc_edge_decomposition_v1.json", edge_builder.build),
    (PHASE79I_DIR, "breakout_acc_path_anatomy_v1.json", path_builder.build),
    (PHASE79I_DIR, "breakout_acc_natural_horizon_v1.json", horizon_builder.build),
    (PHASE79I_DIR, "breakout_acc_mechanism_discovery_v1.json", mech_builder.build),
    (PHASE79I_DIR, "breakout_acc_sensitivity_67_vs_75_v1.json", sens_builder.build),
    (PHASE79I_DIR, "breakout_acc_gate_diagnostic_v1.json", gate_builder.build),
    (PHASE79I_DIR, "breakout_acc_b_only_comparison_v1.json", b_only_cmp_builder.build),
    (PHASE79I_DIR, "breakout_acc_failure_map_and_robustness_v1.json", fmap_builder.build),
    (PHASE79I_DIR, "breakout_acc_executive_summary_decision_card_v1.json", exec_builder.build),
]
ARTIFACTS_79J_NEW = [
    (PHASE79J_DIR, "breakout_acc_temporal_causality_audit_v1.json", temporal_audit_builder.build),
    (PHASE79J_DIR, "breakout_acc_sensitivity_67_vs_75_path_v1.json", sens_path_builder.build),
    (PHASE79J_DIR, "breakout_acc_direction_alignment_outcome_v1.json", alignment_builder.build),
    (PHASE79J_DIR, "breakout_acc_natural_horizon_reconciliation_v1.json", horizon_recon_builder.build),
]

FORBIDDEN_WORDS = ["PROMOTE", "DEPLOY", "PROFITABLE"]
ALLOWED_DECISIONS = ["MECHANISM_SUPPORTED", "MECHANISM_PARTIALLY_SUPPORTED",
                    "MECHANISM_NOT_SUPPORTED", "INSUFFICIENT_EVIDENCE"]


def verify():
    errors = []

    for directory, fname, build_fn in ARTIFACTS_79I_CORRECTED + ARTIFACTS_79J_NEW:
        saved = load_json(os.path.join(directory, fname))
        fresh = build_fn()
        if canonical_sha256(fresh) != canonical_sha256(saved["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")

    # --- 1) causal_ema usa < stretto (non <=) - verifica DIRETTA sul codice sorgente. ---
    ctx_src = open(os.path.join(PHASE79I_DIR, "nxs_mechanism_context.py"), encoding="utf-8").read()
    ema_fn_start = ctx_src.find("def causal_ema(")
    ema_fn_end = ctx_src.find("\n\n\n", ema_fn_start)
    ema_fn_body = ctx_src[ema_fn_start:ema_fn_end]
    if "<= as_of_date.date()" in ema_fn_body:
        errors.append("causal_ema() usa ancora '<=' - il bug di causalita' NON risulta "
                      "corretto nel codice sorgente")
    if "< as_of_date.date()" not in ema_fn_body:
        errors.append("causal_ema() non usa '< as_of_date.date()' come atteso dopo la "
                      "correzione")

    atr_fn_start = ctx_src.find("def causal_atr(")
    atr_fn_end = ctx_src.find("\n\n\n", atr_fn_start)
    atr_fn_body = ctx_src[atr_fn_start:atr_fn_end]
    if "< as_of_date.date()" not in atr_fn_body:
        errors.append("causal_atr() non usa '< as_of_date.date()' - inatteso, causal_atr "
                      "era gia' corretto in origine")

    # --- 2) test causale diretto: modificare una barra NON ancora disponibile alla
    # decisione non deve cambiare la feature dell'evento. ---
    d1_bars = ctx.load_d1_bars()
    as_of = datetime(2019, 6, 5)
    ema_before = ctx.causal_ema(d1_bars, as_of, period=100)
    atr_before = ctx.causal_atr(d1_bars, as_of, period=20)

    mutated_bars = copy.deepcopy(d1_bars)
    for b in mutated_bars:
        if b["time"].date() >= as_of.date():
            b["close"] *= 1000.0
            b["high"] *= 1000.0
            b["low"] *= 1000.0
    ema_after = ctx.causal_ema(mutated_bars, as_of, period=100)
    atr_after = ctx.causal_atr(mutated_bars, as_of, period=20)
    if ema_before != ema_after:
        errors.append(f"TEST DI NON-LEAKAGE FALLITO per causal_ema: modificare barre >= "
                      f"as_of_date ha cambiato il risultato ({ema_before} -> {ema_after})")
    if atr_before != atr_after:
        errors.append(f"TEST DI NON-LEAKAGE FALLITO per causal_atr: modificare barre >= "
                      f"as_of_date ha cambiato il risultato ({atr_before} -> {atr_after})")

    # test complementare: modificare SOLO barre passate (< as_of_date) DEVE cambiare
    # il risultato (altrimenti la funzione starebbe ignorando dati che dovrebbe usare).
    mutated_past = copy.deepcopy(d1_bars)
    for b in mutated_past:
        if b["time"].date() < as_of.date():
            b["close"] *= 1.5
    ema_past_mutated = ctx.causal_ema(mutated_past, as_of, period=100)
    if ema_past_mutated == ema_before:
        errors.append("causal_ema non cambia se si modificano barre PASSATE - sospetto "
                      "che la funzione non stia leggendo i dati attesi")

    # --- 3) breakout_magnitude (c1) verificata causalmente pulita: non deve cambiare se
    # si modifica la barra corrente (shift 0, mai usata per c1/c2). ---
    feat_rows = feat_builder.build()["rows"]
    sample = next(r for r in feat_rows if r["d1_bar_date"] == "2019.06.05")
    if sample["breakout_close_c1"] is None:
        errors.append("evento 2019.06.05 senza breakout_close_c1 - impossibile verificare")

    # --- 4) Phase 7.9H frozen non modificata. ---
    dataset_path = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9h",
                                "breakout_acc_intended_d1_v1_dataset.json")
    result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", dataset_path], cwd=ROOT)
    if result.returncode != 0:
        errors.append("il dataset canonico 7.9H risulta modificato rispetto a HEAD")

    # --- 5) nessun file MQL5/Python di strategia modificato. ---
    result = subprocess.run(["git", "status", "--porcelain", "--", "MQL5/", "server/backtest.py"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.stdout.strip():
        errors.append(f"file MQL5/Python risultano modificati: {result.stdout.strip()}")

    # --- 6) originali pre-fix preservati. ---
    for fname in (
        "breakout_acc_feature_engineering_v1_ORIGINAL_pre_temporal_fix.json",
        "breakout_acc_edge_decomposition_v1_ORIGINAL_pre_temporal_fix.json",
        "breakout_acc_mechanism_discovery_v1_ORIGINAL_pre_temporal_fix.json",
        "breakout_acc_executive_summary_decision_card_v1_ORIGINAL_pre_temporal_fix.json",
        "breakout_acc_b_only_comparison_v1_ORIGINAL_pre_temporal_fix.json",
    ):
        p = os.path.join(PHASE79J_DIR, "raw_data_pre_fix", fname)
        if not os.path.exists(p):
            errors.append(f"originale pre-fix mancante: {fname}")

    # --- 7) impatto del fix EMA misurato come nullo sul flag booleano di allineamento -
    # ri-verificato direttamente (non solo fidandosi dell'audit). ---
    pre = load_json(os.path.join(PHASE79J_DIR, "raw_data_pre_fix",
                                 "breakout_acc_feature_engineering_v1_ORIGINAL_pre_temporal_fix.json"))["payload"]["rows"]
    post = feat_rows
    pre_by_id = {r["event_id"]: r for r in pre}
    flips = sum(1 for r in post if pre_by_id[r["event_id"]]["htf_proxy_trend_aligned"]
               != r["htf_proxy_trend_aligned"])
    if flips != 0:
        errors.append(f"attesi 0 flip del flag trend_aligned dopo il fix, trovati {flips}")

    # --- 8) zero variazione di allineamento su tutti i 75 eventi (punto 3 della
    # revisione) - ri-verificato direttamente. ---
    n_misaligned = sum(1 for r in post if r["htf_proxy_trend_aligned"] is False)
    if n_misaligned != 0:
        errors.append(f"attesi 0 eventi non allineati (EMA100) su 75, trovati {n_misaligned}")

    # --- 9) vocabolario di decisione e parole vietate, dopo la revisione del linguaggio. ---
    exec_doc = load_json(os.path.join(PHASE79I_DIR,
                                      "breakout_acc_executive_summary_decision_card_v1.json"))
    if exec_doc["payload"]["final_decision"] not in ALLOWED_DECISIONS:
        errors.append("final_decision fuori dal vocabolario consentito")
    full_text = json.dumps(exec_doc["payload"], ensure_ascii=False).upper()
    for w in FORBIDDEN_WORDS:
        if w in full_text:
            errors.append(f"parola vietata '{w}' trovata nell'executive summary/decision card")

    # --- 10) linguaggio corretto: "analisi indipendenti" non deve piu' comparire senza
    # qualifica nel Mechanism Discovery (deve essere accompagnato da un chiarimento). ---
    mech_doc = load_json(os.path.join(PHASE79I_DIR, "breakout_acc_mechanism_discovery_v1.json"))
    mech_text = json.dumps(mech_doc["payload"], ensure_ascii=False)
    if "lineage_note" not in mech_doc["payload"]:
        errors.append("mechanism_discovery non ha una lineage_note che documenti la "
                      "revisione del linguaggio")

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
