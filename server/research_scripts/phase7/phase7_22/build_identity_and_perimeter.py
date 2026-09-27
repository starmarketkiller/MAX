#!/usr/bin/env python3
"""Phase 7.22 punto 1 - congela identita', implementazione e perimetro
PRIMA di guardare qualunque risultato economico."""
import os
import sys

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE722_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, file_sha256  # noqa: E402

STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")


def build():
    payload = {
        "canonical_strategy_identity": "ORDER_BLOCK",
        "implementation_identity": "ORDER_BLOCK_IMPL_V2_TF_GUARDED - NXS_Strat_OrderBlock() CON "
            "guardia TF-scoped (`if(tf != NXS_Profile_TF(\"ORDER_BLOCK\")) return s;`), applicata e "
            "validata causalmente in Phase 7.14, chiusa in Phase 7.15, semanticamente mappata in "
            "Phase 7.16 (APPROXIMATION_WITH_KNOWN_GAPS per il motore Python - non usato come fonte "
            "primaria in questa fase).",
        "reference_commit": "17da794 (Phase 7.14, fix causalmente validato) - HEAD al momento di "
            "questa fase: d8f365e (Phase 7.21). Nessuna modifica a MQL5/ dalla Phase 7.18 in poi "
            "(confermato via git log).",
        "current_source_sha256": file_sha256(STRAT_PATH),
        "canonical_tf": "PERIOD_D1", "entry_tf": "PERIOD_M15 (esecuzione, coerente col pattern "
            "gia' usato per BREAKOUT_ACC/ORDER_BLOCK)",
        "selector_profile": {"selector": 15, "InpUseStrategyProfiles": True, "InpProfileMultiTF": True},
        "ob_mit_relationship": "OB_MIT (NXS_Strat_OB_Mitigation_Structural(), selettore 20) e' un "
            "WRAPPER diretto di NXS_Strat_OrderBlock() - nessuno stato proprio, eredita "
            "automaticamente il fix. Il run di questa fase usa SOLO il selettore 15 (ORDER_BLOCK "
            "isolato) - OB_MIT resta DISABILITATO, nessun dato economico OB_MIT prodotto o dedotto "
            "in questa fase (vedi Phase 7.15 ob_mit_perimeter_v1.json per l'analisi statica separata "
            "gia' fatta - non riusata qui come evidenza economica).",
        "historical_artifacts_reusable": [],
        "historical_artifacts_not_reusable_contaminated_or_not_interpretable": [
            {"artifact": "results/phase2_baseline_20260705_v2.0.27.csv (riga InpStrat_ORDER_BLOCK)",
             "why": "Prodotto sotto ORDER_BLOCK_IMPL_V1_CONTAMINATED (pre-fix) - classificato "
                   "HISTORICAL_CONTAMINATED in Phase 7.14."},
            {"artifact": "results/phase_partB_silent_diagnostic_20260706.csv (riga ORDER_BLOCK)",
             "why": "Idem - pre-fix."},
            {"artifact": "server/research_scripts/phase7/phase7_14/nxs_orderblock_realtrace_diag_"
                        "prefix_curated.csv",
             "why": "Baseline PRE-FIX di Phase 7.14 stessa - evidenza storica dell'implementazione "
                   "V1, mai economica (Research Mode, nessun fill)."},
            {"artifact": "server/research_scripts/phase7/phase7_14/nxs_orderblock_realtrace_diag_"
                        "postfix_curated.csv",
             "why": "POST-fix ma diagnostico puro (Research Mode, 8 eventi RETEST_SIGNAL_FIRED, "
                   "ZERO fill reali/P&L) - valido per confermare che il fix funziona a livello di "
                   "segnale, NON utilizzabile come baseline economica (nessun costo/fill/esito "
                   "reale catturato). Riusato in questa fase SOLO per stimare il tasso storico di "
                   "generazione segnali (~2.76/anno su 2.9 anni), non come evidenza di P&L."},
            {"artifact": "server/backtest.py::sig_order_block/_ob_series (motore Python)",
             "why": "APPROXIMATION_WITH_KNOWN_GAPS (Phase 7.16) - non fedelta' evento-per-evento "
                   "provata contro un trace EA live. Non usato come fonte primaria per la "
                   "popolazione economica di questa fase (MT5 = ground truth, per esplicita "
                   "istruzione del task)."},
        ],
        "old_pf_wr_not_used_as_baseline": True,
        "mt5_is_ground_truth_for_real_events": True,
        "no_modification_to_breakout_acc_or_tsi_in_this_phase": True,
        "no_optimization_until_baseline_demonstrated": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE722_DIR, "identity_and_perimeter_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
