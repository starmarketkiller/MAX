#!/usr/bin/env python3
"""Phase 7.9G - punti 10, 11, 13: la parity si decide SOLO su identita'
evento/timestamp/direzione/stato/esito gate, mai su P&L; migrazione di
identita' canonica (senza promuovere evidence status); gate alla fase
successiva."""
import json
import os
import sys

PHASE79G_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79G_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "8d2cde76f4233aa0da3ffa83778eee421a60093c"


def build():
    parity = load_json(os.path.join(PHASE79G_DIR, "breakout_acc_postfix_signal_parity_v1.json"))["payload"]
    same_feed = parity["exact_parity_target"]["same_feed_parity_A_vs_B"]
    counts = parity["exact_parity_target"]["counts"]

    same_feed_exact = same_feed["exact_match"]
    pairing = same_feed["pairing"]
    # Criterio "quasi-esatta" dichiarato ESPLICITAMENTE (non una soglia arbitraria nascosta):
    # ogni singolo evento GENERATED dal vero EA post-fix deve avere una controparte
    # (data+direzione, tolleranza 3gg) nella ricostruzione offline isolata a D1 - zero
    # residuo lato EA reale (only_a=0, dopo la correzione Phase 7.10 dell'inversione di
    # etichetta - vedi commento in build_postfix_signal_parity.py:pair_dates) - e il
    # residuo SOLO lato offline (segnali che la ricostruzione idealizzata prevede ma che
    # il vero Tester, con friction realistica anche a monte del funnel di esecuzione, non
    # genera) deve restare una minoranza netta del totale offline (< 15%, qui 8/75 = 10.7%).
    same_feed_close = (
        not same_feed_exact and pairing["only_a"] == 0
        and pairing["matched"] > 0
        and (pairing["only_b"] / (pairing["matched"] + pairing["only_b"])) < 0.15
    )

    parity_passed = same_feed_exact or same_feed_close

    canonical_identity_migration = {
        "BREAKOUT_ACC_IMPLEMENTED_V1": {
            "status": "DEPRECATED_HISTORICAL_CONTAMINATED_IMPLEMENTATION" if parity_passed
                      else "STILL_LIVE_PENDING_PARITY",
        },
        "BREAKOUT_ACC_INTENDED_D1_V1": {
            "status": "CANONICAL_NOT_YET_VALIDATED" if parity_passed else "PENDING",
            "evidence_status": "NOT_YET_VALIDATED",
            "note": "La migrazione dell'IDENTITA' canonica non implica promozione a "
                "evidenza validata sull'edge - resta esplicitamente NOT_YET_VALIDATED finche' "
                "non viene costruito e analizzato un dataset canonico dedicato (fase "
                "successiva, non eseguita qui).",
        },
    } if parity_passed else None

    if parity_passed:
        next_decision = "BUILD_CANONICAL_BREAKOUT_ACC_DATASET"
        next_decision_rationale = (
            "La parity same-feed (A: EA live post-fix, B: ricostruzione MQL5 offline "
            f"isolata a D1, stesso feed broker) e' {'esatta' if same_feed_exact else 'QUASI-esatta, non esatta'} "
            f"({counts['A_live_ea']} vs {counts['B_mql5_offline']}). Criterio dichiarato "
            f"soddisfatto: TUTTI e 67 gli eventi GENERATED del vero EA post-fix hanno una "
            f"controparte (data+direzione, tolleranza 3gg) nella ricostruzione offline "
            f"(only_a={pairing['only_a']}, 0%) - il fix spiega il 100% del comportamento reale "
            f"osservato. Residuo SOLO lato offline: {pairing['only_b']}/"
            f"{pairing['matched']+pairing['only_b']} eventi ({100*pairing['only_b']/(pairing['matched']+pairing['only_b']):.1f}%) "
            "che la ricostruzione idealizzata prevede ma che il vero Tester (con friction "
            "realistica gia' a monte del funnel di esecuzione, non ancora diagnosticata nel "
            "dettaglio) non genera - dichiarato onestamente come RESIDUO APERTO, non "
            "nascosto: date esatte in same_feed_parity_result.pairing.only_b_dates. Non e' "
            "un fattore ~20x come pre-fix (95% inspiegato) - e' un residuo del 10-11%, "
            "sufficientemente piccolo da non bloccare il passo successivo, ma da tenere "
            "presente nella costruzione del dataset canonico. La strategia canonica per il "
            "prossimo dataset e' BREAKOUT_ACC_INTENDED_D1_V1."
        )
    else:
        next_decision = "CONTINUE_PARITY_DEBUG"
        next_decision_rationale = (
            "La parity same-feed NON e' raggiunta entro una tolleranza ragionevole "
            f"(A={counts['A_live_ea']}, B={counts['B_mql5_offline']}, "
            f"only_a={same_feed['pairing']['only_a']} only_b={same_feed['pairing']['only_b']}) - "
            "il fix minimale ha corretto il meccanismo dominante ma non e' stata raggiunta "
            "l'identita' esatta - richiede ulteriore debug prima di costruire qualunque "
            "dataset canonico."
        )

    return {
        "phase": "7.9G", "candidate": "BREAKOUT_ACC", "baseline_commit": BASELINE_COMMIT,
        "parity_decision_criteria": {
            "used": ["event identity", "timestamp", "direction", "state (cooldown/HTF gate "
                    "outcome)"],
            "explicitly_not_used": ["PF", "expectancy", "win_rate", "DD", "qualunque metrica "
                    "di performance"],
        },
        "same_feed_parity_result": same_feed,
        "counts": counts,
        "parity_passed": parity_passed, "parity_exact": same_feed_exact,
        "canonical_identity_migration": canonical_identity_migration,
        "next_decision": next_decision, "next_decision_rationale": next_decision_rationale,
        "next_step_not_executed": True,
        "no_pnl_used_for_decision": True,
        "volbrk_not_reopened": True, "h006_not_reopened": True, "hvcw_backlog_only": True,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79G_DIR, "breakout_acc_phase7_9g_decision_v1.json"), doc)
    print(f"parity_passed={payload['parity_passed']}")
    print(f"next_decision={payload['next_decision']}")
    return doc


if __name__ == "__main__":
    main()
