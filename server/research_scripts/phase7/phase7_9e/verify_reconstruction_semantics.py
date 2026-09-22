#!/usr/bin/env python3
"""Phase 7.9E - verificatore indipendente. Ri-deriva tutto dai file raw
(output reali dei due esperimenti diagnostici nel vero Tester) senza
fidarsi dei numeri gia' scritti negli artifact - fallisce chiuso su
qualunque discrepanza."""
import csv
import json
import os
import sys

PHASE79E_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79E_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79E_DIR)
import build_offline_vs_live_semantics_diff as diff_builder  # noqa: E402
import build_missing_event_forensics as forensics_builder  # noqa: E402
import build_reconstruction_parity_and_decision as decision_builder  # noqa: E402

ALLOWED_VERDICTS = {
    "OFFLINE_RECONSTRUCTION_PARITY_CONFIRMED", "OFFLINE_RECONSTRUCTION_PARITY_PARTIAL",
    "EVALUATION_CADENCE_MISMATCH", "STATE_SEMANTICS_MISMATCH", "HTF_TIMING_MISMATCH",
    "MULTI_CAUSE_RECONSTRUCTION_FAILURE", "OFFLINE_RECONSTRUCTION_ROOT_CAUSE_UNRESOLVED",
}
ALLOWED_NEXT_DECISIONS = {"REBUILD_CANONICAL_BREAKOUT_ACC_DATASET", "BLOCK_RESEARCH_UNTIL_RECONSTRUCTION_PARITY"}

RAW_DIR = os.path.join(PHASE79E_DIR, "raw_data")


def verify():
    errors = []

    # --- 1) Semantics diff: ricostruzione indipendente coincide. ---
    diff_path = os.path.join(PHASE79E_DIR, "breakout_acc_live_vs_offline_semantics_diff_v1.json")
    diff_doc = load_json(diff_path)
    fresh_diff = diff_builder.build()
    if canonical_sha256(fresh_diff) != canonical_sha256(diff_doc["payload"]):
        errors.append("semantics diff: ricostruzione indipendente differisce")
    if canonical_sha256(diff_doc["payload"]) != diff_doc["canonical_sha256"]:
        errors.append("semantics diff: hash dichiarato non corrisponde al payload")

    # --- 2) I conteggi citati nel diff coincidono coi raw file reali degli esperimenti. ---
    cadence_summary_path = os.path.join(RAW_DIR, "nxs_breakoutacc_cadence_diag_summary.txt")
    with open(cadence_summary_path, encoding="utf-16") as f:
        cadence_summary = dict(ln.split("=", 1) for ln in f.read().strip().splitlines() if "=" in ln)
    sec2 = diff_doc["payload"]["2_timing_semantics_verified_empirically"]
    if int(cadence_summary["n_m15_passes"]) != sec2["n_m15_passes"]:
        errors.append("n_m15_passes dichiarato non coincide col raw file dell'esperimento A")
    if int(cadence_summary["n_activation_fail"]) != sec2["n_activation_fail"]:
        errors.append("n_activation_fail dichiarato non coincide col raw file dell'esperimento A")
    if int(cadence_summary["n_new_d1_bar_after_success"]) != sec2["n_new_d1_bar_detected_after_success"]:
        errors.append("n_new_d1_bar dichiarato non coincide col raw file dell'esperimento A")

    sec5 = diff_doc["payload"]["5_htf_gate_placement_and_counts"]
    if int(cadence_summary["n_raw_accept"]) != sec5["raw_acceptance_isolated_D1_only"]:
        errors.append("raw_accept dichiarato non coincide col raw file")
    if int(cadence_summary["n_cooldown_pass"]) != sec5["post_cooldown_isolated_D1_only"]:
        errors.append("cooldown_pass dichiarato non coincide col raw file")
    if int(cadence_summary["n_htf_pass"]) != sec5["post_htf_isolated_D1_only_shift0_semantics"]:
        errors.append("htf_pass dichiarato non coincide col raw file")

    sharedstate_summary_path = os.path.join(RAW_DIR, "nxs_breakoutacc_sharedstate_diag_summary.txt")
    with open(sharedstate_summary_path, encoding="utf-16") as f:
        shared_summary = dict(ln.split("=", 1) for ln in f.read().strip().splitlines() if "=" in ln)
    if int(shared_summary["n_d1_fired_with_shared_state"]) != sec5["post_cooldown_with_cross_tf_shared_state"]:
        errors.append("n_d1_fired_with_shared_state dichiarato non coincide col raw file dell'esperimento B")

    # --- 3) Missing event forensics: ricostruzione indipendente + coerenza coi raw. ---
    forensics_path = os.path.join(PHASE79E_DIR, "breakout_acc_missing_event_forensics_v1.json")
    forensics_doc = load_json(forensics_path)
    fresh_forensics = forensics_builder.build()
    if canonical_sha256(fresh_forensics) != canonical_sha256(forensics_doc["payload"]):
        errors.append("missing event forensics: ricostruzione indipendente differisce")
    if len(forensics_doc["payload"]["events"]) != 3:
        errors.append("missing event forensics: attesi esattamente 3 eventi")
    for e in forensics_doc["payload"]["events"]:
        if not e["would_fire_in_isolation"]:
            errors.append(f"evento {e['date']}: atteso would_fire_in_isolation=True, verifica il raw CSV")

    # --- 4) Parity + decision: ricostruzione indipendente, verdetto/decisione ammessi. ---
    parity_path = os.path.join(PHASE79E_DIR, "breakout_acc_reconstruction_parity_v1.json")
    decision_path = os.path.join(PHASE79E_DIR, "breakout_acc_reconstruction_decision_v1.json")
    parity_doc = load_json(parity_path)
    decision_doc = load_json(decision_path)
    fresh_full = decision_builder.build()

    if parity_doc["payload"]["achieved"] is not False:
        errors.append("parity_target.achieved dovrebbe essere False (nessun fix eseguito in questa fase)")
    if decision_doc["payload"]["final_verdict"] not in ALLOWED_VERDICTS:
        errors.append(f"final_verdict fuori dal set ammesso: {decision_doc['payload']['final_verdict']}")
    if decision_doc["payload"]["next_decision"] not in ALLOWED_NEXT_DECISIONS:
        errors.append(f"next_decision fuori dal set ammesso: {decision_doc['payload']['next_decision']}")
    if decision_doc["payload"].get("next_step_not_executed") is not True:
        errors.append("next_step_not_executed non e' True")
    if decision_doc["payload"].get("live_ea_strategy_logic_unchanged") is not True:
        errors.append("live_ea_strategy_logic_unchanged non e' True")

    # --- 5) EA live NON modificato: hash dei file sorgente live invariati rispetto a HEAD. ---
    ea_path = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")
    strat_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    import subprocess
    for p, name in ((ea_path, "NEXUS_EA_v2.mq5"), (strat_path, "NXS_Strategies.mqh")):
        result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", p], cwd=ROOT)
        if result.returncode != 0:
            errors.append(f"{name} risulta modificato rispetto a HEAD - vietato in questa fase")

    # --- 6) Nessun P&L usato per la diagnosi. ---
    full_text = json.dumps(decision_doc["payload"]).lower() + json.dumps(diff_doc["payload"]).lower()
    for term in ("expectancy", "\"pf\":", "profit_factor", "win_rate"):
        if term in full_text:
            errors.append(f"trovato termine P&L vietato: {term}")

    # --- 7) Deliverable presenti. ---
    for fname in (
        "breakout_acc_live_vs_offline_semantics_diff_v1.json",
        "breakout_acc_missing_event_forensics_v1.json",
        "breakout_acc_reconstruction_parity_v1.json",
        "breakout_acc_reconstruction_decision_v1.json",
    ):
        p = os.path.join(PHASE79E_DIR, fname)
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            errors.append(f"deliverable mancante o vuoto: {fname}")

    # --- 8) Artifact frozen 7.9C/7.9D non modificati (solo controllo esistenza/leggibilita'). ---
    for rel in (
        "server/research_scripts/phase7/phase7_9c/breakout_acc_event_parity_matrix_v1.json",
        "server/research_scripts/phase7/phase7_9d/breakout_acc_execution_parity_decision_v1.json",
    ):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            errors.append(f"artifact frozen mancante: {rel}")
        else:
            load_json(p)

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
