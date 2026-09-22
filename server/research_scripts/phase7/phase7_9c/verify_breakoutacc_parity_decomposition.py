#!/usr/bin/env python3
"""Phase 7.9C - verificatore indipendente della parity decomposition.

Ri-deriva TUTTO dai raw file (stream MT5 gia' collezionato dal broker
reale + stream Python rigenerato da zero tramite le funzioni originali
di backtest.py), senza fidarsi di alcun numero gia' scritto negli
artifact prodotti da build_breakoutacc_parity_decomposition.py -
fallisce chiuso su qualunque discrepanza.
"""
import json
import os
import sys

PHASE79C_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79C_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json  # noqa: E402

sys.path.insert(0, PHASE79C_DIR)
import build_breakoutacc_parity_decomposition as builder  # noqa: E402


def verify():
    errors = []

    matrix_path = os.path.join(PHASE79C_DIR, "breakout_acc_event_parity_matrix_v1.json")
    decision_path = os.path.join(PHASE79C_DIR, "breakout_acc_parity_decision_v1.json")
    matrix_envelope = load_json(matrix_path)
    decision_envelope = load_json(decision_path)
    matrix_doc = matrix_envelope["payload"]
    decision_doc = decision_envelope["payload"]

    # 1) Ricostruzione indipendente dell'intera pipeline dai raw file.
    fresh_payload = builder.build()

    if canonical_sha256(fresh_payload) != canonical_sha256(matrix_doc):
        errors.append("RECOMPUTED payload != STORED payload nel parity matrix (mismatch non atteso)")

    # 2) Hash interno coerente.
    recomputed_hash = canonical_sha256(matrix_doc)
    if recomputed_hash != matrix_envelope["canonical_sha256"]:
        errors.append(f"canonical_sha256 dichiarato ({matrix_envelope['canonical_sha256']}) != ricalcolato ({recomputed_hash})")

    # 3) Conteggi MT5 nel matrix == quelli letti a mano dai raw file.
    mt5_rows, mt5_summary = builder.load_mt5_stream()
    n_fire_raw = sum(1 for r in mt5_rows if r["final_reason"] == "SIGNAL_FIRE")
    n_blocked_cd_raw = sum(1 for r in mt5_rows if r["final_reason"] == "BLOCKED_COOLDOWN")
    n_blocked_htf_raw = sum(1 for r in mt5_rows if r["final_reason"] == "BLOCKED_HTF")
    recon = matrix_doc["reconstruction"]["mt5_stream"]
    if recon["n_signal_fire"] != n_fire_raw:
        errors.append(f"MT5 n_signal_fire dichiarato {recon['n_signal_fire']} != raw {n_fire_raw}")
    if recon["n_blocked_cooldown"] != n_blocked_cd_raw:
        errors.append(f"MT5 n_blocked_cooldown dichiarato {recon['n_blocked_cooldown']} != raw {n_blocked_cd_raw}")
    if recon["n_blocked_htf"] != n_blocked_htf_raw:
        errors.append(f"MT5 n_blocked_htf dichiarato {recon['n_blocked_htf']} != raw {n_blocked_htf_raw}")
    if int(mt5_summary["n_final_fire"]) != n_fire_raw:
        errors.append("MT5 summary.txt n_final_fire non coerente col CSV riga-per-riga")

    # 4) Conteggi Python nel matrix == quelli del file full stream.
    py_events, py_summary = builder.load_py_stream()
    n_py_fire_raw = sum(1 for e in py_events if e["event"] == "SIGNAL_FIRE")
    n_py_bcd_raw = sum(1 for e in py_events if e["event"] == "BLOCKED_COOLDOWN")
    n_py_bhtf_raw = sum(1 for e in py_events if e["event"] == "BLOCKED_HTF")
    py_recon = matrix_doc["reconstruction"]["python_stream"]
    if int(py_recon["n_signal_fire"]) != n_py_fire_raw:
        errors.append(f"Python n_signal_fire dichiarato {py_recon['n_signal_fire']} != raw {n_py_fire_raw}")
    if int(py_recon["n_blocked_cooldown"]) != n_py_bcd_raw:
        errors.append(f"Python n_blocked_cooldown dichiarato {py_recon['n_blocked_cooldown']} != raw {n_py_bcd_raw}")
    if int(py_recon["n_blocked_htf"]) != n_py_bhtf_raw:
        errors.append(f"Python n_blocked_htf dichiarato {py_recon['n_blocked_htf']} != raw {n_py_bhtf_raw}")

    # 5) Pairing: matched+mt5_only+python_only devono ricostruire i totali.
    pairing = matrix_doc["pairing"]
    if pairing["matched"] + pairing["mt5_only"] != pairing["mt5_signal_fire_total"]:
        errors.append("pairing: matched + mt5_only != mt5_signal_fire_total")
    if pairing["matched"] + pairing["python_only"] != pairing["python_signal_total"]:
        errors.append("pairing: matched + python_only != python_signal_total")
    if pairing["mt5_signal_fire_total"] != n_fire_raw:
        errors.append("pairing.mt5_signal_fire_total non coerente col conteggio raw MT5 SIGNAL_FIRE")
    if pairing["python_signal_total"] != n_py_fire_raw:
        errors.append("pairing.python_signal_total non coerente col conteggio raw Python SIGNAL_FIRE")

    # 6) Nessun P&L presente in nessuna parte dell'artifact (vincolo esplicito).
    matrix_str = json.dumps(matrix_doc).lower()
    forbidden_pnl_terms = ["expectancy", "\"pf\":", "profit_factor", "\"r_multiple", "win_rate"]
    for term in forbidden_pnl_terms:
        if term in matrix_str:
            errors.append(f"trovato termine P&L vietato nell'artifact di diagnosi segnale: {term}")

    # 7) Verdetto/decisione entro i set ammessi dall'istruzione.
    allowed_verdicts = {"SIGNAL_PARITY_CONFIRMED", "SIGNAL_PARITY_PARTIAL", "SIGNAL_PARITY_FAILED",
                         "EXECUTION_GAP_DOMINANT", "DATA_FEED_GAP_DOMINANT", "MULTI_CAUSE_PARITY_GAP"}
    allowed_decisions = {"REANALYZE_EXISTING_RAW_RESULTS", "FIX_PARITY_BEFORE_STATISTICS", "DATA_SOURCE_SENSITIVITY_STUDY"}
    if matrix_doc["final_verdict"] not in allowed_verdicts:
        errors.append(f"final_verdict '{matrix_doc['final_verdict']}' fuori dal set ammesso")
    if matrix_doc["next_decision"]["decision"] not in allowed_decisions:
        errors.append(f"next_decision '{matrix_doc['next_decision']['decision']}' fuori dal set ammesso")

    # 8) Il decision artifact deve essere coerente col matrix (stesso verdetto/decisione/hash).
    if decision_doc["final_verdict"] != matrix_doc["final_verdict"]:
        errors.append("decision.final_verdict != matrix.final_verdict")
    if decision_doc["next_decision"] != matrix_doc["next_decision"]["decision"]:
        errors.append("decision.next_decision != matrix.next_decision.decision")
    if decision_doc["parity_matrix_canonical_sha256"] != matrix_envelope["canonical_sha256"]:
        errors.append("decision.parity_matrix_canonical_sha256 non punta all'hash reale del matrix")

    # 9) Fonti non toccate: gli hash citati devono combaciare coi file reali oggi.
    phase_e_path = os.path.join(ROOT, "results", "cost_calibration_67_rerun", "phase_e_breakoutacc_findings.json")
    real_hash = file_sha256(phase_e_path)
    declared_hash = matrix_doc["source_artifacts_untouched"]["phase_e_findings"]["sha256"]
    if real_hash != declared_hash:
        errors.append(f"phase_e_breakoutacc_findings.json e' stato modificato: hash dichiarato {declared_hash} != reale {real_hash}")

    # 10) Deliverable CSV/JSON degli stream esistono e non sono vuoti.
    for fname in ("breakout_acc_python_event_stream_v1.csv", "breakout_acc_python_event_stream_v1.json",
                  "breakout_acc_mt5_event_stream_v1.csv", "breakout_acc_mt5_event_stream_v1.json"):
        p = os.path.join(PHASE79C_DIR, fname)
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            errors.append(f"deliverable mancante o vuoto: {fname}")

    # 11) Vincoli espliciti di scope rispettati.
    for flag in ("no_new_serious_backtest", "no_optimization", "no_strategy_modification",
                 "no_pnl_used_for_diagnosis", "volbrk_not_reopened", "h006_not_reopened", "hvcw_backlog_only"):
        if matrix_doc.get(flag) is not True:
            errors.append(f"flag di scope '{flag}' non True")

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
