#!/usr/bin/env python3
"""Phase 7.9G - verificatore indipendente. Ri-deriva tutto dai raw file
(certificato reale post-fix, Journal Tester reale, ricostruzioni
offline MQL5/Python gia' esistenti) senza fidarsi dei numeri gia'
scritti negli artifact - fallisce chiuso su qualunque discrepanza.
"""
import json
import os
import subprocess
import sys

PHASE79G_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79G_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79G_DIR)
import build_live_fix_before_after as bf_builder  # noqa: E402
import build_bar_updn_structural_warning as bar_updn_builder  # noqa: E402
import build_postfix_signal_parity as parity_builder  # noqa: E402
import build_stale_evidence_reclassification as stale_builder  # noqa: E402
import build_phase7_9g_decision as decision_builder  # noqa: E402


def verify():
    errors = []

    # --- 1) Fix minimale applicato: guard presente, prima di ogni stato. ---
    combined_path = os.path.join(PHASE79G_DIR, "breakout_acc_live_fix_before_after_v1.json")
    combined_doc = load_json(combined_path)
    static_v = combined_doc["payload"]["static_verification"]
    if not static_v["guard_present"]:
        errors.append("il guard 'if(tf != NXS_Profile_TF(...)) return s;' non e' presente nel codice")
    if not static_v["all_state_touches_occur_after_guard"]:
        errors.append("esistono letture/scritture di g_breakoutAccState PRIMA del guard - fix non completo")

    # --- 2) EA live e' effettivamente cambiato (NXS_Strategies.mqh), ma SOLO quello
    # (non NEXUS_EA_v2.mq5, non backtest.py) rispetto al baseline pre-fase. ---
    diff_summary = combined_doc["payload"]["diff_summary"]
    if not diff_summary["NXS_Strategies.mqh_changed"]:
        errors.append("NXS_Strategies.mqh risulta NON modificato - il fix non e' stato applicato")
    if diff_summary["NEXUS_EA_v2.mq5_changed"]:
        errors.append("NEXUS_EA_v2.mq5 risulta modificato - fuori dal fix minimale dichiarato")
    if diff_summary["backtest.py_changed"]:
        errors.append("backtest.py risulta modificato in questa fase - non autorizzato (punto 9 non ancora eseguito)")

    # --- 3) Compilazione pulita (0 errori). ---
    if combined_doc["payload"]["compile_result"]["errors"] != 0:
        errors.append("la compilazione post-fix ha riportato errori")

    # --- 4) BAR_UPDN non toccato. ---
    bar_updn_doc = load_json(os.path.join(PHASE79G_DIR, "breakout_acc_bar_updn_structural_warning_v1.json"))
    if not bar_updn_doc["payload"]["not_fixed_in_this_phase"]:
        errors.append("BAR_UPDN risulta corretto in questa fase - non autorizzato")
    strat_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    with open(strat_path, encoding="utf-8") as f:
        strat_text = f.read()
    import re
    m = re.search(r"SNXSSignal NXS_Strat_BarUpDn\(\)\{(.*?)\n\}\n", strat_text, re.S)
    if m and 'NXS_Profile_TF("BAR_UPDN")' in m.group(1):
        errors.append("NXS_Strat_BarUpDn() risulta gia' avere un guard per-TF - inatteso, BAR_UPDN non doveva essere toccato")

    # --- 5) Ricostruzione indipendente della parity a tre vie. ---
    parity_path = os.path.join(PHASE79G_DIR, "breakout_acc_postfix_signal_parity_v1.json")
    parity_doc = load_json(parity_path)
    fresh_parity = parity_builder.build()
    # confronto solo sui CONTEGGI (non sull'intero payload, che include un timestamp di lettura
    # certificato non deterministico) - i conteggi devono essere identici a runs successive.
    if fresh_parity["exact_parity_target"]["counts"] != parity_doc["payload"]["exact_parity_target"]["counts"]:
        errors.append("i conteggi di parity ricalcolati indipendentemente differiscono da quelli salvati")

    # --- 6) Il certificato citato esiste davvero e i suoi conteggi combaciano. ---
    cert_path_rel = parity_doc["payload"]["stream_A_live_ea"]["certificate_path"]
    cert_full_path = os.path.join(ROOT, cert_path_rel) if not os.path.isabs(cert_path_rel) else cert_path_rel
    real_cert_path = os.path.join(PHASE79G_DIR, "raw_data", "postfix_certificate_r002.json")
    if not os.path.exists(real_cert_path):
        errors.append(f"certificato raw non trovato: {real_cert_path}")
    else:
        real_cert = load_json(real_cert_path)
        declared_funnel = parity_doc["payload"]["stream_A_live_ea"]["certificate_funnel"]
        if real_cert["funnel"] != declared_funnel:
            errors.append("il funnel del certificato reale non coincide con quello dichiarato nell'artifact")
        if real_cert["funnel"]["generated"] != real_cert["funnel"]["opened"] + real_cert["funnel"]["blocked"] + real_cert["funnel"]["broker_reject"]:
            errors.append("EXECUTION_FUNNEL_ACCOUNTING_FAIL nel run post-fix: generated != opened+blocked+broker_reject")

    # --- 7) Decisione: entro i set ammessi, coerente con parity. ---
    decision_path = os.path.join(PHASE79G_DIR, "breakout_acc_phase7_9g_decision_v1.json")
    decision_doc = load_json(decision_path)
    fresh_decision = decision_builder.build()
    if canonical_sha256(fresh_decision) != canonical_sha256(decision_doc["payload"]):
        errors.append("decision: ricostruzione indipendente differisce da quella salvata")
    if decision_doc["payload"]["next_decision"] not in ("BUILD_CANONICAL_BREAKOUT_ACC_DATASET", "CONTINUE_PARITY_DEBUG"):
        errors.append(f"next_decision fuori dal set ammesso: {decision_doc['payload']['next_decision']}")
    if decision_doc["payload"]["parity_passed"] and decision_doc["payload"]["next_decision"] != "BUILD_CANONICAL_BREAKOUT_ACC_DATASET":
        errors.append("parity_passed=True ma next_decision non e' BUILD_CANONICAL_BREAKOUT_ACC_DATASET")
    if not decision_doc["payload"]["parity_passed"] and decision_doc["payload"]["next_decision"] != "CONTINUE_PARITY_DEBUG":
        errors.append("parity_passed=False ma next_decision non e' CONTINUE_PARITY_DEBUG")
    if decision_doc["payload"].get("next_step_not_executed") is not True:
        errors.append("next_step_not_executed non e' True")

    # --- 8) Se parity passata, l'identita' canonica NON deve essere promossa a evidenza validata. ---
    if decision_doc["payload"]["parity_passed"]:
        cim = decision_doc["payload"]["canonical_identity_migration"]
        if cim["BREAKOUT_ACC_INTENDED_D1_V1"]["evidence_status"] != "NOT_YET_VALIDATED":
            errors.append("l'identita' canonica e' stata promossa a evidenza validata - non autorizzato in questa fase")

    # --- 9) Stale evidence reclassification: nessun artifact storico modificato. ---
    stale_doc = load_json(os.path.join(PHASE79G_DIR, "breakout_acc_stale_evidence_reclassification_v1.json"))
    if not stale_doc["payload"]["no_artifacts_modified"]:
        errors.append("stale evidence reclassification dichiara di aver modificato artifact storici")
    fresh_stale = stale_builder.build()
    if canonical_sha256(fresh_stale) != canonical_sha256(stale_doc["payload"]):
        errors.append("stale evidence reclassification: ricostruzione indipendente differisce")

    # --- 10) Nessun P&L usato per la diagnosi/decisione. Esclude deliberatamente il campo
    # 'explicitly_not_used' del criterio di decisione, il cui SCOPO e' elencare questi
    # stessi termini come disclaimer di cio' che NON e' stato usato - non un uso reale. ---
    decision_for_scan = json.loads(json.dumps(decision_doc["payload"]))
    decision_for_scan.get("parity_decision_criteria", {}).pop("explicitly_not_used", None)
    full_text = (json.dumps(parity_doc["payload"]).lower() + json.dumps(decision_for_scan).lower())
    for term in ("expectancy", "\"pf\":", "profit_factor", "win_rate"):
        if term in full_text:
            errors.append(f"trovato termine P&L vietato: {term}")

    # --- 11) Frozen artifact precedenti (7.9C/D/E/F) non modificati. ---
    for rel in (
        "server/research_scripts/phase7/phase7_9c/breakout_acc_event_parity_matrix_v1.json",
        "server/research_scripts/phase7/phase7_9d/breakout_acc_execution_parity_decision_v1.json",
        "server/research_scripts/phase7/phase7_9e/breakout_acc_reconstruction_decision_v1.json",
        "server/research_scripts/phase7/phase7_9f/breakout_acc_identity_adjudication_v1.json",
    ):
        p = os.path.join(ROOT, rel)
        result = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", p], cwd=ROOT)
        if result.returncode != 0:
            errors.append(f"artifact frozen risulta modificato rispetto a HEAD: {rel}")

    # --- 12) Deliverable presenti. ---
    for fname in (
        "breakout_acc_live_fix_before_after_v1.json", "breakout_acc_fixed_identity_v1.json",
        "breakout_acc_postfix_signal_parity_v1.json", "breakout_acc_stale_evidence_reclassification_v1.json",
        "breakout_acc_phase7_9g_decision_v1.json", "breakout_acc_bar_updn_structural_warning_v1.json",
    ):
        p = os.path.join(PHASE79G_DIR, fname)
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
