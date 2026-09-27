#!/usr/bin/env python3
"""Phase 7.20 punto 4 - evidenza storica riutilizzabile vs non
riutilizzabile, per le strategie di Tier A (le uniche con evidenza
quantitativa reale nel corpus). Riusa le migrazioni gia' fatte in
Phase 7.14/7.17/7.18 per ORDER_BLOCK/TSI - non le riscrive."""
import os
import sys

PHASE720_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE720_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402


def build():
    payload = {
        "principle": "Un artifact storico non viene mai cancellato - viene classificato REUSABLE o "
                    "NOT_REUSABLE rispetto all'identita' implementativa CANONICA attuale (non a quella "
                    "storica che lo ha prodotto).",
        "reusable": [
            {"artifact": "server/research_scripts/phase7/phase7_9k/breakout_acc_intended_d1_v2_dataset."
                        "json", "strategy": "BREAKOUT_ACC", "why": "Prodotto DOPO il fix del cooldown "
                        "(Phase 7.9G) e DOPO la correzione dell'offset (Phase 7.9K) - rappresenta "
                        "l'implementazione canonica attuale, fill reali."},
        ],
        "not_reusable_as_evidence_of_current_canonical_implementation": [
            {"artifact": "knowledge/backtest_database.json, sweep37 S02 ORDER_BLOCK (se esistesse) / "
                        "results/phase2_baseline_20260705, results/phase_partB_silent_diagnostic",
             "strategy": "ORDER_BLOCK", "why": "Prodotti PRIMA del fix Phase 7.14 - classificati "
                        "HISTORICAL_CONTAMINATED (phase7_14/historical_evidence_migration_v1.json). Zero "
                        "evidenza economica esiste per l'implementazione V2 attuale."},
            {"artifact": "knowledge/backtest_database.json, sweep37 S05 TSI; results/phase2_baseline_"
                        "20260705 (riga TSI); results/phase_partB_silent_diagnostic (riga TSI)",
             "strategy": "TSI", "why": "Prodotti PRIMA del fix Phase 7.18 - tutti classificati "
                        "POSSIBLY_CONTAMINATED (phase7_17/tsi_historical_evidence_map_v1.json, riportato "
                        "invariato in phase7_18/tsi_historical_evidence_migration_v1.json)."},
            {"artifact": "knowledge/backtest_database.json, sweep37 S01/S02/S03/S06 (ADX_RSI/BOLLINGER/"
                        "MACD/BJORGUM), S07/S08 (LIQ_SWEEP/FVG_CONT)",
             "strategy": "ADX_RSI, BOLLINGER, MACD, BJORGUM, LIQ_SWEEP, FVG_CONT",
             "why": "L'identita' implementativa eseguita in quel run (guardia TF presente o assente) "
                    "NON E' ACCERTATA per nessuna di queste 6 strategie (nessun audit di integrita' "
                    "dedicato mai svolto) - il PF riportato resta un dato grezzo, non evidenza di una "
                    "identita' implementativa specifica. Riusabile SOLO come indizio per priorizzare un "
                    "audit dedicato, MAI come evidenza economica diretta."},
        ],
        "breakout_acc_v1_dataset_status": "server/research_scripts/phase7/phase7_9h/"
            "breakout_acc_intended_d1_v1_dataset.json e' SUPERSEDED dal v2 (Phase 7.9K) - non cancellato, "
            "ma non usare per un test economico (offset non corretto).",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE720_DIR, "evidence_reusability_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
