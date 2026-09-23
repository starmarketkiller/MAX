#!/usr/bin/env python3
"""Phase 7.10 - verificatore indipendente. Ri-deriva ogni artifact dai
builder senza fidarsi dei file gia' scritti - fallisce chiuso su
qualunque discrepanza. Verifica anche che nessun artifact storico
(7.9C-7.9F frozen) sia stato modificato e che il fix di 7.9G non sia
stato toccato oltre la correzione di etichetta autorizzata.
"""
import json
import os
import subprocess
import sys

PHASE710_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE710_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE710_DIR)
import build_7_9g_label_correction_audit as label_builder  # noqa: E402
import build_cross_tf_contamination_failure_memory as memory_builder  # noqa: E402
import build_stateful_strategy_static_audit as audit_builder  # noqa: E402
import build_retroactive_integrity_audit_schema as schema_builder  # noqa: E402
import build_final_synthesis_report as report_builder  # noqa: E402


def verify():
    errors = []

    # --- 1) Ricostruzione indipendente di tutti gli artifact. ---
    def schema_combined():
        return {"phase": "7.10", "task": 4, "baseline_commit": schema_builder.BASELINE_COMMIT,
                "schema": schema_builder.schema(),
                "breakout_acc_case_study": schema_builder.breakout_acc_case_study()}

    checks = [
        ("breakout_acc_7_9g_label_correction_v1.json", label_builder.build),
        ("cross_timeframe_state_contamination_failure_memory_v1.json", memory_builder.build),
        ("stateful_strategy_static_audit_v1.json", audit_builder.build),
        ("retroactive_strategy_integrity_audit_schema_v1.json", schema_combined),
        ("phase_7_10_final_synthesis_report_v1.json", report_builder.build),
    ]
    for fname, builder_fn in checks:
        p = os.path.join(PHASE710_DIR, fname)
        if not os.path.exists(p):
            errors.append(f"deliverable mancante: {fname}")
            continue
        doc = load_json(p)
        fresh = builder_fn()
        if canonical_sha256(fresh) != canonical_sha256(doc["payload"]):
            errors.append(f"{fname}: ricostruzione indipendente differisce dal file salvato")
        if canonical_sha256(doc["payload"]) != doc["canonical_sha256"]:
            errors.append(f"{fname}: hash dichiarato non corrisponde al payload")

    # --- 2) La correzione di etichetta 7.9G: verifica diretta sul codice sorgente
    # (non fidarsi della narrazione) che l'inversione sia stata REALMENTE corretta. ---
    parity_script = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9g",
                                  "build_postfix_signal_parity.py")
    with open(parity_script, encoding="utf-8") as f:
        parity_text = f.read()
    if 'pair_dates(stream_B["final_events"], stream_A["events"])' in parity_text:
        errors.append("build_postfix_signal_parity.py: la chiamata invertita originale e' "
                      "ancora presente - il fix non e' stato applicato")
    if 'pair_dates(stream_A["events"], stream_B["final_events"])' not in parity_text:
        errors.append("build_postfix_signal_parity.py: la chiamata corretta attesa non e' presente")

    # --- 3) I conteggi sostanziali del 7.9G NON devono essere cambiati dalla correzione. ---
    corrected_parity = load_json(os.path.join(
        ROOT, "server", "research_scripts", "phase7", "phase7_9g", "breakout_acc_postfix_signal_parity_v1.json"))["payload"]
    original_parity = load_json(os.path.join(
        PHASE710_DIR, "raw_data", "breakout_acc_postfix_signal_parity_v1_ORIGINAL_pre_label_fix.json"))["payload"]
    if corrected_parity["exact_parity_target"]["counts"] != original_parity["exact_parity_target"]["counts"]:
        errors.append("i conteggi A/B/C sono cambiati fra la versione originale e quella corretta - "
                      "il fix di etichetta non doveva alterare la sostanza")
    corrected_pairing = corrected_parity["exact_parity_target"]["same_feed_parity_A_vs_B"]["pairing"]
    if {corrected_pairing["only_a"], corrected_pairing["only_b"]} != {0, 8}:
        errors.append(f"i residui corretti non sono {{0,8}} come atteso: {corrected_pairing}")
    if corrected_pairing["only_a"] != 0:
        errors.append(f"dopo la correzione, only_a (residuo di A/live) dovrebbe essere 0, trovato {corrected_pairing['only_a']}")

    # --- 4) Nessun artifact storico frozen modificato (7.9C-7.9F + 7.9G stesso, tranne
    # i 2 file esplicitamente corretti). ---
    frozen_paths = [
        "server/research_scripts/phase7/phase7_9c/breakout_acc_event_parity_matrix_v1.json",
        "server/research_scripts/phase7/phase7_9d/breakout_acc_execution_parity_decision_v1.json",
        "server/research_scripts/phase7/phase7_9e/breakout_acc_reconstruction_decision_v1.json",
        "server/research_scripts/phase7/phase7_9f/breakout_acc_identity_adjudication_v1.json",
        "server/research_scripts/phase7/phase7_9g/breakout_acc_live_fix_before_after_v1.json",
        "server/research_scripts/phase7/phase7_9g/breakout_acc_bar_updn_structural_warning_v1.json",
        "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
        "MQL5/Experts/NEXUS_EA_v2.mq5",
        "server/backtest.py",
    ]
    for rel in frozen_paths:
        p = os.path.join(ROOT, rel)
        result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", p], cwd=ROOT)
        if result.returncode != 0:
            errors.append(f"artifact/codice che doveva restare invariato risulta modificato: {rel}")

    # --- 5) I 2 file effettivamente corretti in 7.9G DEVONO differire dall'originale
    # preservato (altrimenti la correzione non e' stata applicata). ---
    original_decision = load_json(os.path.join(
        PHASE710_DIR, "raw_data", "breakout_acc_phase7_9g_decision_v1_ORIGINAL_pre_label_fix.json"))["payload"]
    corrected_decision = load_json(os.path.join(
        ROOT, "server", "research_scripts", "phase7", "phase7_9g", "breakout_acc_phase7_9g_decision_v1.json"))["payload"]
    if canonical_sha256(original_decision) == canonical_sha256(corrected_decision):
        errors.append("il decision artifact 7.9G risulta identico a prima della correzione - "
                      "atteso diverso (etichette corrette)")
    if original_decision["parity_passed"] != corrected_decision["parity_passed"]:
        errors.append("parity_passed e' cambiato fra originale e corretto - non autorizzato")
    if original_decision["next_decision"] != corrected_decision["next_decision"]:
        errors.append("next_decision e' cambiato fra originale e corretto - non autorizzato")

    # --- 6) Nessun difetto trovato in questa fase risulta corretto (solo BREAKOUT_ACC, gia'
    # fixato in 7.9G, puo' avere status FIXED). ---
    static_audit = load_json(os.path.join(PHASE710_DIR, "stateful_strategy_static_audit_v1.json"))["payload"]
    for c in static_audit["candidates"]:
        if c["strategy"] != "BREAKOUT_ACC" and c["status"] not in (
            "NOT_FIXED_CONFIRMED_STRUCTURALLY", "NOT_FIXED_LOW_PRACTICAL_RISK",
            "SAFE_BY_DESIGN_VERIFIED", "SAFE_BY_DESIGN_DOCUMENTED",
            "SAFE_BY_DESIGN_VERIFIED_FOR_THIS_PATTERN",
        ):
            errors.append(f"{c['strategy']}: status inatteso '{c['status']}' - possibile correzione "
                          "non autorizzata applicata in questa fase")
    bar_updn = next(c for c in static_audit["candidates"] if c["strategy"] == "BAR_UPDN")
    if bar_updn["classification"] != "DEFECT_CONFIRMED":
        errors.append("BAR_UPDN dovrebbe essere classificato DEFECT_CONFIRMED")
    strat_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    with open(strat_path, encoding="utf-8") as f:
        strat_text = f.read()
    import re
    m = re.search(r"SNXSSignal NXS_Strat_BarUpDn\(\)\{(.*?)\n\}\n", strat_text, re.S)
    if m and 'NXS_Profile_TF(' in m.group(1):
        errors.append("NXS_Strat_BarUpDn() contiene un riferimento a NXS_Profile_TF - "
                      "sembra corretto, non autorizzato in questa fase")

    # --- 7) Nessuna analisi di P&L usata per le classificazioni. Esclude deliberatamente la
    # definizione dello stage OUTCOME_EVIDENCE nello schema, il cui SCOPO e' descrivere in
    # astratto quali metriche quello stage documenta in generale - non un uso reale di P&L
    # per derivare una classificazione in QUESTA fase. ---
    full_text = ""
    for fname, _ in checks:
        p = os.path.join(PHASE710_DIR, fname)
        if not os.path.exists(p):
            continue
        payload = json.loads(json.dumps(load_json(p)["payload"]))
        if fname == "retroactive_strategy_integrity_audit_schema_v1.json":
            payload.get("schema", {}).get("stage_definitions", {}).pop("OUTCOME_EVIDENCE", None)
        full_text += json.dumps(payload).lower()
    for term in ("expectancy", "\"pf\":", "profit_factor", "win_rate"):
        if term in full_text:
            errors.append(f"trovato termine P&L vietato: {term}")

    # --- 8) Coerenza fra static_audit e final_synthesis_report (stesse liste). ---
    report = load_json(os.path.join(PHASE710_DIR, "phase_7_10_final_synthesis_report_v1.json"))["payload"]
    defect_from_audit = sorted(c["strategy"] for c in static_audit["candidates"] if c["classification"] == "DEFECT_CONFIRMED")
    defect_from_report = sorted(report["q3_other_exposed_strategies"]["defect_confirmed"])
    if defect_from_audit != defect_from_report:
        errors.append("la lista DEFECT_CONFIRMED nel report finale non coincide con l'audit statico")

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
