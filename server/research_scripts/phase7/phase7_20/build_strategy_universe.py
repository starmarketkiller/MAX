#!/usr/bin/env python3
"""Phase 7.20 punto 1 - universo completo delle strategie: unisce il
census (Phase 7.11, 83 righe), l'audit statico di integrita' cross-TF
(Phase 7.10, 20 candidate controllate), la priority queue dello stesso
difetto (Phase 7.12) e l'evidenza quantitativa reale disponibile
(knowledge/backtest_database.json, sweep37 - l'unico dataset multi-
strategia a tick reali del progetto) in UN solo record per strategia.
Nessun nuovo dato generato - solo unione di artifact gia' esistenti."""
import json
import os
import re
import sys

PHASE720_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE710_DIR = os.path.abspath(os.path.join(PHASE720_DIR, "..", "phase7_10"))
PHASE711_DIR = os.path.abspath(os.path.join(PHASE720_DIR, "..", "phase7_11"))
PHASE712_DIR = os.path.abspath(os.path.join(PHASE720_DIR, "..", "phase7_12"))
ROOT = os.path.abspath(os.path.join(PHASE720_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

# sweep37 "ROUND CORRENTE (baseline)" - l'UNICO run multi-strategia a tick
# reali del progetto (30% tick reali, XM Global, 2019.07.11-2025.07.11,
# lotto fisso, isolato per strategia). PF riportato testualmente nel
# risultato della campagna in knowledge/backtest_database.json - estratto
# qui una sola volta, non ricalcolato.
SWEEP37_PF = {
    "ADX_RSI": 0.82, "BOLLINGER": 0.79, "MACD": 0.79, "TSI": 0.76,
    "BJORGUM": 0.68, "LIQ_SWEEP": 1.04, "FVG_CONT": 0.96,
}
SWEEP37_NOTE = ("sweep37 ROUND CORRENTE (baseline), commit e6ce816, XM Global GOLD, "
               "2019.07.11-2025.07.11, 'Every tick, 30% tick reali', isolato per "
               "strategia/lotto fisso - PRIMO DATASET PULITO del progetto ma qualita' "
               "dati piu' bassa dei diagnostici dedicati (100% tick reali) di Phase "
               "7.14/7.17/7.18. Numero di trade non riportato in questo artifact "
               "riassuntivo (solo PF) - NON usare da solo per classificare.")


def _load_defect_audit():
    d = load_json(os.path.join(PHASE710_DIR, "stateful_strategy_static_audit_v1.json"))["payload"]
    out = {}
    for c in d["candidates"]:
        out[c["strategy"]] = {"classification": c["classification"], "state_nature": c.get("state_nature", ""),
                              "status": c.get("status")}
    return out


def build():
    census = load_json(os.path.join(PHASE711_DIR, "complete_strategy_census_v1.json"))["payload"]
    rows = census["census_rows"]
    defect_audit = _load_defect_audit()
    priority = load_json(os.path.join(PHASE712_DIR, "strategy_priority_queue_v1.json"))["payload"]
    priority_ids = set()
    for pid in priority["ordered_candidate_ids"]:
        for part in re.split(r"\s*/\s*", pid):
            priority_ids.add(part.strip())

    universe = []
    for r in rows:
        sid = r["canonical_strategy_id"]
        entry = {
            "canonical_strategy_id": sid,
            "current_status": r["current_status"],
            "live_mql5": r["live_mql5"],
            "python_implementation": r["python_implementation"],
            "profile_tf": r["profile_presence"],
            "stateful": r["stateful"],
            "census_known_implementation_defects": r["known_implementation_defects"],
            "census_evidence_status": r["evidence_status"],
            "census_historical_tests": r["historical_tests"],
            "phase_7_10_static_audit": defect_audit.get(sid),
            "flagged_in_7_12_contamination_priority_queue": sid in priority_ids,
            "sweep37_real_tick_pf": SWEEP37_PF.get(sid),
            "sweep37_note": SWEEP37_NOTE if sid in SWEEP37_PF else None,
        }
        universe.append(entry)

    payload = {
        "n_strategies_total": len(universe),
        "sources_merged": [
            "phase7_11/complete_strategy_census_v1.json (83 righe, identita'/stato/registry)",
            "phase7_10/stateful_strategy_static_audit_v1.json (20 candidate controllate per il "
            "difetto CROSS_TIMEFRAME_STATE_CONTAMINATION)",
            "phase7_12/strategy_priority_queue_v1.json (priorita' di diagnosi per lo stesso difetto)",
            "knowledge/backtest_database.json, campagna sweep37 ROUND CORRENTE (unico run "
            "multi-strategia a tick reali disponibile, 7 strategie con PF riportato)",
        ],
        "no_new_data_generated_in_this_phase": True,
        "universe": universe,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE720_DIR, "strategy_universe_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  n_strategie: {payload['n_strategies_total']}")


if __name__ == "__main__":
    main()
