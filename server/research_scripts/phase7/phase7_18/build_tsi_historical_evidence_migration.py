#!/usr/bin/env python3
"""Phase 7.18 punto 6 - migrazione dell'evidenza storica TSI (SOLO
perche' il fix e' stato causalmente validato in questa fase): crea una
nuova identita' implementativa canonica (post-fix, TF-guarded) e marca
la precedente come historical contaminated implementation. Nessun
artifact cancellato. Nessun risultato MT5 vecchio riusato come
evidenza della nuova implementazione. Riusa la classificazione gia'
fatta in Phase 7.17 (tsi_historical_evidence_map_v1.json).
"""
import os
import sys

PHASE718_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE717_DIR = os.path.abspath(os.path.join(PHASE718_DIR, "..", "phase7_17"))
ROOT = os.path.abspath(os.path.join(PHASE718_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    prior_map = load_json(os.path.join(PHASE717_DIR, "tsi_historical_evidence_map_v1.json"))["payload"]

    payload = {
        "implementations": {
            "TSI_IMPL_V1_CONTAMINATED": {
                "status": "HISTORICAL_CONTAMINATED",
                "description": "NXS_Strat_TSI() SENZA guardia TF - g_tsiState (filtro ricorsivo "
                               "IIR doppio EMA) mutato da ogni passaggio multi-TF (M5/M15/M30/"
                               "H1/H4/D1), non solo D1. Contaminazione UNIVERSALE (100% delle "
                               "barre D1, Phase 7.17) - a differenza di ORDER_BLOCK, mai "
                               "autoriparante (memoria esponenziale del filtro non si azzera mai).",
                "active_from_commit": "presente da prima di Phase 7.10 (data di introduzione non "
                                      "ricostruita - fuori scope, richiederebbe git blame dedicato)",
                "active_until_commit": "8590f63 (Phase 7.17, ultimo commit prima del fix)",
                "defect_confirmed_by": ["phase7_17/tsi_decision_card_v1.json (formalizzazione "
                                       "matematica + dati reali gia' disponibili, "
                                       "DEFECT_CONFIRMED_MATERIAL_IMPACT)",
                                       "phase7_18/tsi_parity_comparison_v1.json (EA reale, trace "
                                       "dinamico pre/post fix)"],
                "artifacts_produced_under_this_implementation_not_deleted": [
                    "knowledge/backtest_database.json, sweep37 S05=TSI (839 trade, PF 0.76)",
                    "results/phase2_baseline_20260705_v2.0.27.csv, riga InpStrat_TSI (15 trade, PF 0.51)",
                    "results/phase_partB_silent_diagnostic_20260706.csv, riga TSI (pattern_fired=3874)",
                    "server/research_scripts/phase7/phase7_18/nxs_tsi_realtrace_diag_prefix.csv "
                    "(baseline pre-fix di QUESTA fase)",
                ],
                "reuse_policy": "NON riutilizzare questi artifact come evidenza della nuova "
                               "implementazione V2 - restano evidenza storica dell'implementazione "
                               "V1 contaminata, preservati per tracciabilita'. Classificazione "
                               "per-artifact gia' fatta in Phase 7.17 (vedi "
                               "phase7_17/tsi_historical_evidence_map_v1.json) riportata invariata "
                               "qui sotto.",
                "prior_classification_from_phase_7_17": [
                    {"artifact": item["artifact"], "classification": item["classification"]}
                    for item in prior_map["items"]
                ],
            },
            "TSI_IMPL_V2_TF_GUARDED": {
                "status": "CANONICAL_CURRENT",
                "description": "NXS_Strat_TSI() CON guardia `if(tf != NXS_Profile_TF(\"TSI\")) "
                               "return s;` subito dopo la risoluzione del TF attivo, prima di "
                               "qualunque lettura/mutazione di g_tsiState.",
                "active_from_commit": "commit di Phase 7.18 (vedi vault report per l'hash finale)",
                "validated_by": "server/research_scripts/phase7/phase7_18/tsi_parity_comparison_v1.json "
                                "(trace EA reale pre/post fix, stessi tick, stessa finestra "
                                "2026.01.01-2026.08.25) + tsi_decision_card_v2.json "
                                "(FIX_CAUSALLY_VALIDATED)",
                "no_prior_evidence_available": "Nessun risultato MT5/Python precedente e' evidenza "
                                               "di QUESTA implementazione (non esisteva prima "
                                               "di questa fase) - qualunque valutazione futura "
                                               "(inclusa profittabilita') deve ripartire da run "
                                               "eseguiti DOPO questo commit. Il warm-up del filtro "
                                               "ricorsivo (g_tsiState) riparte da zero a ogni avvio "
                                               "del Tester/EA - un run futuro dovra' tenerne conto "
                                               "(gate barsSeen<75 sul TF canonico, non piu' inquinato "
                                               "da passaggi non canonici).",
            },
        },
        "python_backtest_engine_status": {
            "identity": "server/research_scripts/phase7/phase7_17/nxs_tsi_replica.py "
                       "(porting fedele riga-per-riga di g_tsiState/tsi_update, single-TF per costruzione)",
            "classification": "PARTIAL_STRUCTURAL_MODEL_NOT_EVENT_LEVEL_PARITY_VALIDATED",
            "note": "Confermato in Phase 7.18: sulla finestra 2026.01.01-2026.08.25, la "
                   "ricostruzione TF-scoped Python (C) concorda al 100% con l'EA reale "
                   "post-fix (B) su tutti gli 8 segnali del periodo maturo comune - le "
                   "5 differenze residue sono interamente spiegate dalla profondita' diversa "
                   "del warm-up (B riparte da barsSeen=0 all'avvio del run breve, C eredita "
                   "un filtro maturo dalla storia locale piena). Questo eleva la fiducia nella "
                   "fedelta' strutturale del motore Python MA non equivale a "
                   "EVENT_LEVEL_PARITY_VALIDATED nel senso stretto (nessun trace EA "
                   "pluriennale raccolto, stesso limite gia' dichiarato in Phase 7.17) - "
                   "Python NON e' ground truth, MT5 post-fix resta la fonte canonica per "
                   "qualunque decisione economica.",
        },
        "no_artifact_deleted": True,
        "no_old_mt5_result_reused_as_evidence_of_new_implementation": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE718_DIR, "tsi_historical_evidence_migration_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
