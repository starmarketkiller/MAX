#!/usr/bin/env python3
"""Phase 7.14 punto 7 - migrazione dell'evidenza storica (SOLO se il fix
e' causalmente validato): crea una nuova identita' implementativa
canonica (post-fix, TF-guarded) e marca la precedente come historical
contaminated implementation. Nessun artifact cancellato. Nessun
risultato MT5 vecchio riusato come evidenza della nuova implementazione.
Python resta separato - UNAFFECTED_BY_THIS_BUG non e' semantic parity
provata.
"""
import os
import sys

PHASE714_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE714_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, file_sha256  # noqa: E402

STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")


def build():
    payload = {
        "implementations": {
            "ORDER_BLOCK_IMPL_V1_CONTAMINATED": {
                "status": "HISTORICAL_CONTAMINATED",
                "description": "NXS_Strat_OrderBlock() SENZA guardia TF - g_obBuy/g_obSell mutati "
                               "da ogni passaggio multi-TF (M5/M15/M30/H1/H4/D1), non solo D1.",
                "active_from_commit": "presente da prima di Phase 7.9H (data di introduzione non "
                                      "ricostruita - fuori scope, richiederebbe git blame dedicato)",
                "active_until_commit": "7b823b9 (Phase 7.13, ultimo commit prima del fix)",
                "defect_confirmed_by": ["phase7_13/decision_card_order_block_v1.json (Python, "
                                       "DEFECT_CONFIRMED_MATERIAL_IMPACT)",
                                       "phase7_14/baseline_pre_fix_v1.json (EA reale, trace dinamico)"],
                "artifacts_produced_under_this_implementation_not_deleted": [
                    "results/phase2_baseline_20260705_v2.0.27.csv (riga InpStrat_ORDER_BLOCK)",
                    "results/phase_partB_silent_diagnostic_20260706.csv (riga ORDER_BLOCK)",
                    "server/research_scripts/phase7/phase7_14/nxs_orderblock_realtrace_diag_prefix.csv (baseline pre-fix di QUESTA fase)",
                ],
                "reuse_policy": "NON riutilizzare questi artifact come evidenza della nuova "
                               "implementazione V2 - restano evidenza storica dell'implementazione "
                               "V1 contaminata, preservati per tracciabilita'.",
            },
            "ORDER_BLOCK_IMPL_V2_TF_GUARDED": {
                "status": "CANONICAL_CURRENT",
                "description": "NXS_Strat_OrderBlock() CON guardia `if(tf != NXS_Profile_TF("
                               "'ORDER_BLOCK')) return s;` subito dopo la risoluzione del TF attivo, "
                               "prima di ogni lettura/scrittura di g_obBuy/g_obSell.",
                "active_from_commit": "commit di Phase 7.14 (vedi vault report per l'hash finale)",
                "validated_by": "server/research_scripts/phase7/phase7_14/parity_comparison_v1.json "
                                "(trace EA reale pre/post fix, stessi tick, stesso periodo)",
                "no_prior_evidence_available": "Nessun risultato MT5/Python precedente e' evidenza "
                                               "di QUESTA implementazione (non esisteva prima "
                                               "di questa fase) - qualunque valutazione futura "
                                               "(inclusa profittabilita') deve ripartire da run "
                                               "eseguiti DOPO questo commit.",
            },
        },
        "python_backtest_engine_status": {
            "identity": "server/backtest.py::sig_order_block/_ob_series",
            "classification": "UNAFFECTED_BY_THIS_BUG_NOT_SEMANTIC_PARITY_PROVEN",
            "note": "Il motore Python e' single-TF per costruzione (Phase 7.13, "
                   "historical_evidence_impact_map_v1.json) - non era mai stato affetto dal "
                   "difetto multi-TF. QUESTO NON DIMOSTRA che sia semanticamente identico a "
                   "ORDER_BLOCK_IMPL_V2_TF_GUARDED (stessa geometria zona, stesse soglie, "
                   "stesso ATR, ecc.) - una verifica di parita' Python-vs-MQL5-V2 dedicata "
                   "resta un lavoro separato, non svolto in questa fase.",
        },
        "no_artifact_deleted": True,
        "no_old_mt5_result_reused_as_evidence_of_new_implementation": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE714_DIR, "historical_evidence_migration_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
