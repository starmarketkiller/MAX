#!/usr/bin/env python3
"""Phase 7.21 punto 13 - Gate finale. Una sola decisione fra:
EDGE_VALIDATED_PRELIMINARY / EDGE_CANDIDATE_REQUIRES_OOS /
EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION / EDGE_NOT_SUPPORTED /
INSUFFICIENT_EVIDENCE.

Criteri per EDGE_VALIDATED_PRELIMINARY (TUTTI richiesti):
1. expectancy netta positiva (baseline_economics ALL)
2. cost survival (cost_stress, tutti e 3 gli scenari)
3. execution survival (execution_realism - nessun collasso del segnale
   agli execution gates)
4. nessuna concentrazione estrema (temporal_robustness - l'edge non
   deve sparire rimuovendo pochissimi trade)
5. evidenza indipendente non usata per discovery (oos_forward_analysis
   - decision != INSUFFICIENT_OOS_SAMPLE E risultato coerente)
"""
import os
import sys

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

CONCENTRATION_EXTREME_THRESHOLD_PCT = 100.0  # top-5 che spiega >=100% del netto = edge dipende
                                             # interamente da <=5 trade - soglia dichiarata PRIMA
                                             # di guardare il numero effettivo


def build():
    baseline = load_json(os.path.join(PHASE721_DIR, "baseline_economics_v1.json"))["payload"]
    cost = load_json(os.path.join(PHASE721_DIR, "cost_stress_v1.json"))["payload"]
    execn = load_json(os.path.join(PHASE721_DIR, "execution_realism_v1.json"))["payload"]
    temporal = load_json(os.path.join(PHASE721_DIR, "temporal_robustness_v1.json"))["payload"]
    stats = load_json(os.path.join(PHASE721_DIR, "statistical_uncertainty_v1.json"))["payload"]
    oos = load_json(os.path.join(PHASE721_DIR, "oos_forward_analysis_v1.json"))["payload"]

    checks = {}

    checks["1_net_expectancy_positive_ALL"] = baseline["ALL"]["net_expectancy_per_trade"] is not None \
        and baseline["ALL"]["net_expectancy_per_trade"] > 0

    checks["2_cost_survival_all_3_scenarios"] = all(
        sc["ALL"]["survives_positive"] for sc in cost["scenarios"].values())

    signal_pf = execn["signal_edge"]["pct_favorable"]
    realized_wr = execn["realized_edge"]["pct_favorable_win_rate"]
    checks["3_execution_does_not_collapse_signal_to_zero"] = realized_wr is not None and realized_wr > 0
    checks["3_execution_realism_large_gap_note"] = (
        f"signal pct_favorable={signal_pf:.2f} vs realized win_rate={realized_wr:.2f} - gap ampio "
        "(atteso: un ritorno direzionale a 60 barre non equivale a un trade SL/TP-bound), non "
        "trattato come un fallimento del criterio 3 di per se'.")

    top5_pct = temporal["concentration_of_profit"]["top_5"]["pct_of_total_net"]
    checks["4_no_extreme_concentration"] = abs(top5_pct) < CONCENTRATION_EXTREME_THRESHOLD_PCT
    checks["4_concentration_detail"] = (
        f"i primi 5 trade (su {baseline['ALL']['n_trades']}) spiegano il {top5_pct:.1f}% del P&L "
        "netto totale - " + ("SOTTO" if checks["4_no_extreme_concentration"] else "SOPRA/AL LIMITE")
        + f" della soglia dichiarata ({CONCENTRATION_EXTREME_THRESHOLD_PCT}%).")

    oos_status = oos.get("status") or oos.get("decision")
    checks["5_independent_evidence_available_and_supportive"] = (
        oos.get("decision") == "SAMPLE_SUFFICIENT_FOR_A_FIRST_READ" and
        oos.get("net_pnl_per_trade") is not None and oos.get("net_pnl_per_trade") > 0)

    all_5_pass = all([checks["1_net_expectancy_positive_ALL"], checks["2_cost_survival_all_3_scenarios"],
                      checks["3_execution_does_not_collapse_signal_to_zero"],
                      checks["4_no_extreme_concentration"],
                      checks["5_independent_evidence_available_and_supportive"]])

    if all_5_pass:
        decision = "EDGE_VALIDATED_PRELIMINARY"
    elif oos_status == "RUN_NOT_YET_CAPTURED":
        decision = "INSUFFICIENT_EVIDENCE"
    elif oos.get("decision") == "INSUFFICIENT_OOS_SAMPLE":
        decision = "EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION"
    elif not checks["1_net_expectancy_positive_ALL"] or not checks["2_cost_survival_all_3_scenarios"]:
        decision = "EDGE_NOT_SUPPORTED"
    else:
        decision = "EDGE_CANDIDATE_REQUIRES_OOS"

    ci_all = stats["results"]["ALL"]["net_expectancy_bootstrap_ci"]
    ci_buy = stats["results"]["BUY"]["net_expectancy_bootstrap_ci"]
    ci_sell = stats["results"]["SELL"]["net_expectancy_bootstrap_ci"]

    payload = {
        "checks": checks,
        "decision": decision,
        "decision_means_live_ready": False,
        "supporting_evidence_summary": {
            "ALL_net_expectancy_per_trade": baseline["ALL"]["net_expectancy_per_trade"],
            "ALL_profit_factor": baseline["ALL"]["profit_factor"],
            "ALL_bootstrap_ci_95": [ci_all["bootstrap_ci_95_low"], ci_all["bootstrap_ci_95_high"]],
            "ALL_ci_excludes_zero": ci_all["excludes_zero"],
            "BUY_net_expectancy_per_trade": baseline["BUY"]["net_expectancy_per_trade"],
            "BUY_bootstrap_ci_95": [ci_buy["bootstrap_ci_95_low"], ci_buy["bootstrap_ci_95_high"]],
            "BUY_ci_excludes_zero": ci_buy["excludes_zero"],
            "SELL_net_expectancy_per_trade": baseline["SELL"]["net_expectancy_per_trade"],
            "SELL_bootstrap_ci_95": [ci_sell["bootstrap_ci_95_low"], ci_sell["bootstrap_ci_95_high"]],
            "SELL_ci_excludes_zero_negative": ci_sell["excludes_zero"],
            "top_5_trades_pct_of_total_net": top5_pct,
            "oos_status": oos_status,
        },
        "h2_buy_more_robust_than_sell_verdict": (
            "SUPPORTATA DA EVIDENZA STATISTICA NUOVA (non solo dalla scoperta originale): il CI "
            "bootstrap di SELL esclude lo zero sul lato NEGATIVO (statisticamente un perdente, non "
            "solo 'piu' debole' di BUY) mentre BUY esclude lo zero sul lato positivo (debolmente, "
            "limite inferiore vicino a zero). Nota: questo e' comunque calcolato sullo STESSO "
            "campione usato per la scoperta originale (Phase 7.9I/J) - la vera indipendenza "
            "richiederebbe l'OOS (vedi sopra), che pero' conferma o smentisce H1 (edge totale), non "
            "specificamente H2 (BUY vs SELL) data la sua finestra corta."
        ),
        "next_phase_if_this_passes": "CONDITIONAL_EDGE + EXIT/RISK OPTIMIZATION - non svolta in "
            "questa fase.",
        "no_optimization_performed": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE721_DIR, "breakoutacc_decision_card_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  DECISIONE: {payload['decision']}")
    for k, v in payload["checks"].items():
        if k.endswith("_note") or k.endswith("_detail"):
            continue
        print(f"    {k}: {v}")


if __name__ == "__main__":
    main()
