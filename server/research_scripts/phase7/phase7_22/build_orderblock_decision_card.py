#!/usr/bin/env python3
"""Phase 7.22 punto 15 - Gate finale. Stessi 5 criteri e stessa logica
di Phase 7.21 (BREAKOUT_ACC) per confrontabilita' diretta fra le due
strategie."""
import os
import sys

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE722_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

CONCENTRATION_EXTREME_THRESHOLD_PCT = 100.0  # stessa soglia dichiarata di Phase 7.21


def build():
    baseline = load_json(os.path.join(PHASE722_DIR, "orderblock_baseline_economics_v1.json"))["payload"]
    cost = load_json(os.path.join(PHASE722_DIR, "orderblock_cost_stress_v1.json"))["payload"]
    execn = load_json(os.path.join(PHASE722_DIR, "orderblock_execution_realism_v1.json"))["payload"]
    temporal = load_json(os.path.join(PHASE722_DIR, "orderblock_temporal_robustness_v1.json"))["payload"]
    stats = load_json(os.path.join(PHASE722_DIR, "orderblock_statistical_uncertainty_v1.json"))["payload"]
    oos = load_json(os.path.join(PHASE722_DIR, "orderblock_oos_forward_analysis_v1.json"))["payload"]

    if baseline["ALL"]["n_trades"] == 0:
        return {"decision": "INSUFFICIENT_EVIDENCE", "decision_means_live_ready": False,
               "checks": {}, "reason": "Zero eventi nel dataset economico canonico - la strategia "
                   "non ha generato trade nella finestra di discovery.",
               "no_optimization_performed": True}

    checks = {}
    checks["1_net_expectancy_positive_ALL"] = baseline["ALL"]["net_expectancy_per_trade"] > 0
    checks["2_cost_survival_all_3_scenarios"] = all(
        sc["ALL"]["survives_positive"] for sc in cost["scenarios"].values())

    opened = execn.get("funnel_counts", {}).get("OPENED", baseline["ALL"]["n_trades"])
    checks["3_execution_does_not_collapse_signal_to_zero"] = opened is not None and opened > 0

    top5 = temporal.get("concentration_of_profit", {}).get("top_5", {})
    top5_pct = top5.get("pct_of_total_net")
    checks["4_no_extreme_concentration"] = (top5_pct is not None and abs(top5_pct) < CONCENTRATION_EXTREME_THRESHOLD_PCT)
    checks["4_concentration_detail"] = (
        f"i primi 5 trade (su {baseline['ALL']['n_trades']}) spiegano il "
        f"{top5_pct:.1f}% del P&L netto totale" if top5_pct is not None else "non calcolabile")

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
        "checks": checks, "decision": decision, "decision_means_live_ready": False,
        "supporting_evidence_summary": {
            "ALL_net_expectancy_per_trade": baseline["ALL"]["net_expectancy_per_trade"],
            "ALL_profit_factor": baseline["ALL"]["profit_factor"],
            "ALL_bootstrap_ci_95": [ci_all["bootstrap_ci_95_low"], ci_all["bootstrap_ci_95_high"]]
                                  if ci_all else None,
            "ALL_ci_excludes_zero": ci_all["excludes_zero"] if ci_all else None,
            "BUY_net_expectancy_per_trade": baseline["BUY"].get("net_expectancy_per_trade"),
            "BUY_bootstrap_ci_95": [ci_buy["bootstrap_ci_95_low"], ci_buy["bootstrap_ci_95_high"]]
                                  if ci_buy else None,
            "SELL_net_expectancy_per_trade": baseline["SELL"].get("net_expectancy_per_trade"),
            "SELL_bootstrap_ci_95": [ci_sell["bootstrap_ci_95_low"], ci_sell["bootstrap_ci_95_high"]]
                                   if ci_sell else None,
            "top_5_trades_pct_of_total_net": top5_pct, "oos_status": oos_status,
        },
        "next_phase_if_this_passes": "CONDITIONAL_EDGE + EXIT/RISK OPTIMIZATION - non svolta in "
            "questa fase.",
        "no_optimization_performed": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE722_DIR, "orderblock_decision_card_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  DECISIONE: {payload['decision']}")


if __name__ == "__main__":
    main()
