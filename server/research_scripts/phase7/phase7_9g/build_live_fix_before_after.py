#!/usr/bin/env python3
"""Phase 7.9G - punto 1 + 4: freeze pre-fix (before) e post-fix (after)
dell'identita' del codice sorgente/binario per NXS_Strategies.mqh e
NEXUS_EA_v2.mq5 - eseguito due volte (prima e dopo l'applicazione del
fix minimale) per costruire un before/after immutabile.
"""
import json
import os
import sys

PHASE79G_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79G_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "8d2cde76f4233aa0da3ffa83778eee421a60093c"

EA_PATH = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")
STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
BACKTEST_PATH = os.path.join(ROOT, "server", "backtest.py")

TERM_DATA = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6"
DEPLOYED_EA_EX5 = os.path.join(TERM_DATA, "MQL5", "Experts", "NEXUS_EA_v2.ex5")


def snapshot(label):
    ex5_info = None
    if os.path.exists(DEPLOYED_EA_EX5):
        ex5_info = {
            "sha256": file_sha256(DEPLOYED_EA_EX5),
            "mtime_utc": None,  # popolato dal chiamante dopo la compilazione, se richiesto
            "size_bytes": os.path.getsize(DEPLOYED_EA_EX5),
        }
    return {
        "label": label,
        "NEXUS_EA_v2.mq5_sha256": file_sha256(EA_PATH),
        "NXS_Strategies.mqh_sha256": file_sha256(STRAT_PATH),
        "backtest.py_sha256": file_sha256(BACKTEST_PATH),
        "deployed_ex5": ex5_info,
    }


IDENTIFIED_DEFECT = {
    "defect_mechanism": "g_breakoutAccState (NXS_Strategies.mqh, struct globale unico "
        "lastBarTime+lastFireTime[2]) viene letto/scritto da NXS_Strat_BreakoutAcc() ad OGNI "
        "pass multi-TF del router (M5/M15/M30/H1/H4/D1), non solo durante il pass D1 - il "
        "gate della funzione (NXS_SelectorAllows(9)) non dipende dal timeframe attivo "
        "(NXS_EffTF()/g_activeTF).",
    "affected_state_variables": ["g_breakoutAccState.lastBarTime", "g_breakoutAccState.lastFireTime[0] (BUY)",
                                 "g_breakoutAccState.lastFireTime[1] (SELL)"],
    "affected_code_path": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh: NXS_Strat_BreakoutAcc() "
        "(righe ~1534-1564), chiamata da NXS_CollectRaw() dentro il loop multi-TF di "
        "NXS_CollectAllSignals() (NEXUS_EA_v2.mq5:683-713)",
    "verdict_reference": "Phase 7.9F: IMPLEMENTATION_DEFECT_CONFIRMED - vedi "
        "server/research_scripts/phase7/phase7_9f/breakout_acc_identity_adjudication_v1.json",
    "BREAKOUT_ACC_IMPLEMENTED_V1": "semantica live pre-fix: cooldown condiviso cross-TF - "
        "risultato empirico riproducibile: 4 trade in 7,5 anni (Phase 7.9D/E)",
    "BREAKOUT_ACC_INTENDED_D1_V1": "semantica documentata da 6 fonti indipendenti (Phase "
        "7.9F): cooldown isolato a D1 - mai eseguita come Serious backtest, solo come "
        "esperimento diagnostico (95 post-cooldown / 75 post-HTF, Phase 7.9E Esperimento A)",
}


def main():
    stage = sys.argv[1] if len(sys.argv) > 1 else "before"
    snap = snapshot(stage)
    payload = {
        "phase": "7.9G", "candidate": "BREAKOUT_ACC", "baseline_commit": BASELINE_COMMIT,
        "stage": stage,
        "source_hashes": snap,
        "identified_defect": IDENTIFIED_DEFECT,
        "authorization": "Modifica dell'EA live esplicitamente autorizzata dall'utente per "
            "questo obiettivo specifico (Phase 7.9G), con vincoli: fix minimale, nessuna "
            "optimization, nessun parameter tuning, nessun cambio design performance-driven.",
    }
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE79G_DIR, f"breakout_acc_live_fix_before_after_v1_{stage}.json")
    save_json(out_path, doc)
    print(f"stage={stage}")
    print(f"NEXUS_EA_v2.mq5={snap['NEXUS_EA_v2.mq5_sha256']}")
    print(f"NXS_Strategies.mqh={snap['NXS_Strategies.mqh_sha256']}")
    return doc


if __name__ == "__main__":
    main()
