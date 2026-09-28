#!/usr/bin/env python3
"""Phase 7.25 punto 13 - Gate finale. Stessi criteri di Phase 7.21/7.22
per confrontabilita' diretta fra le tre strategie. Per
EDGE_VALIDATED_PRELIMINARY servono TUTTI: expectancy netta positiva,
cost survival, execution survival, concentrazione non estrema,
uncertainty compatibile con edge, almeno una componente di evidenza
indipendente."""
import os
import sys

PHASE725_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE725_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

CONCENTRATION_EXTREME_THRESHOLD_PCT = 100.0  # stessa soglia dichiarata di Phase 7.21/7.22


def build():
    baseline = load_json(os.path.join(PHASE725_DIR, "baseline_economics_v1.json"))["payload"]
    concentration = load_json(os.path.join(PHASE725_DIR, "concentration_analysis_v1.json"))["payload"]
    cost = load_json(os.path.join(PHASE725_DIR, "cost_stress_v1.json"))["payload"]
    execn = load_json(os.path.join(PHASE725_DIR, "execution_realism_v1.json"))["payload"]
    stats = load_json(os.path.join(PHASE725_DIR, "statistical_uncertainty_v1.json"))["payload"]
    oos = load_json(os.path.join(PHASE725_DIR, "oos_forward_analysis_v1.json"))["payload"]

    if baseline["ALL"]["n_trades"] == 0:
        return {"decision": "INSUFFICIENT_EVIDENCE", "decision_means_live_ready": False,
               "checks": {}, "reason": "Zero eventi CLOSED nel dataset canonico.",
               "no_optimization_performed": True, "not_ready_for_deploy": True}

    checks = {}
    checks["1_net_expectancy_positive_ALL"] = baseline["ALL"]["net_expectancy_per_trade"] > 0
    checks["2_cost_survival_all_3_scenarios"] = all(
        sc["ALL"]["survives_positive"] for sc in cost["scenarios"].values())
    checks["3_execution_does_not_collapse_signal_to_zero"] = execn["execution_does_not_collapse_to_zero"]

    top5_pct = concentration["concentration"]["top_5"]["pct_of_total_net"]
    checks["4_no_extreme_concentration"] = (top5_pct is not None and abs(top5_pct) < CONCENTRATION_EXTREME_THRESHOLD_PCT)
    checks["4_concentration_detail"] = (
        f"i primi 5 trade (su {baseline['ALL']['n_trades']}) spiegano il {top5_pct:.1f}% del "
        f"P&L netto totale - edge_survives_without_top_5={concentration['edge_survives_without_top_5']}"
        if top5_pct is not None else "non calcolabile")

    ci_all_iid = stats["results"]["ALL"]["net_expectancy_bootstrap_ci_iid"]
    ci_all_block = stats["results"]["ALL"]["net_expectancy_block_bootstrap_ci"]
    checks["5_uncertainty_compatible_with_edge"] = bool(
        ci_all_iid and ci_all_iid["excludes_zero"] and ci_all_block and ci_all_block["excludes_zero"])

    oos_status = oos.get("status") or oos.get("decision")
    checks["6_independent_evidence_available_and_supportive"] = (
        oos.get("decision") == "SAMPLE_SUFFICIENT_FOR_A_FIRST_READ" and
        oos.get("net_pnl_per_trade") is not None and oos.get("net_pnl_per_trade") > 0)

    all_pass = all([checks["1_net_expectancy_positive_ALL"], checks["2_cost_survival_all_3_scenarios"],
                    checks["3_execution_does_not_collapse_signal_to_zero"],
                    checks["4_no_extreme_concentration"],
                    checks["5_uncertainty_compatible_with_edge"],
                    checks["6_independent_evidence_available_and_supportive"]])

    if all_pass:
        decision = "EDGE_VALIDATED_PRELIMINARY"
    elif oos_status in ("RUN_NOT_YET_LAUNCHED", "RUN_NOT_YET_COLLECTED"):
        decision = "INSUFFICIENT_EVIDENCE"
    elif oos.get("decision") == "INSUFFICIENT_OOS_SAMPLE":
        decision = "EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION"
    elif not checks["1_net_expectancy_positive_ALL"] or not checks["2_cost_survival_all_3_scenarios"]:
        decision = "EDGE_NOT_SUPPORTED"
    elif (oos.get("decision") == "SAMPLE_SUFFICIENT_FOR_A_FIRST_READ" and
          not checks["6_independent_evidence_available_and_supportive"]):
        # campione OOS sufficiente per una prima lettura MA non supporta l'edge storico
        # (negativo/non chiaramente positivo) - stesso significato sostanziale di un campione
        # insufficiente (l'evidenza indipendente non conferma), non equiparato a "OOS mai tentato".
        decision = "EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION"
    else:
        decision = "EDGE_CANDIDATE_REQUIRES_OOS"

    payload = {
        "checks": checks, "decision": decision, "decision_means_live_ready": False,
        "supporting_evidence_summary": {
            "ALL_net_expectancy_per_trade": baseline["ALL"]["net_expectancy_per_trade"],
            "ALL_profit_factor": baseline["ALL"]["profit_factor"],
            "ALL_bootstrap_ci_95_iid": [ci_all_iid["bootstrap_ci_95_low"], ci_all_iid["bootstrap_ci_95_high"]]
                                      if ci_all_iid else None,
            "ALL_ci_excludes_zero_iid": ci_all_iid["excludes_zero"] if ci_all_iid else None,
            "ALL_bootstrap_ci_95_block": [ci_all_block["bootstrap_ci_95_low"], ci_all_block["bootstrap_ci_95_high"]]
                                        if ci_all_block else None,
            "ALL_ci_excludes_zero_block": ci_all_block["excludes_zero"] if ci_all_block else None,
            "BUY_net_expectancy_per_trade": baseline["BUY"].get("net_expectancy_per_trade"),
            "SELL_net_expectancy_per_trade": baseline["SELL"].get("net_expectancy_per_trade"),
            "top_5_trades_pct_of_total_net": top5_pct, "oos_status": oos_status,
            "oos_net_pnl_per_trade": oos.get("net_pnl_per_trade"),
            "oos_n_trades": oos.get("n_closed_trades_liq_sweep"),
        },
        "next_phase_if_this_passes": "CONDITIONAL_EDGE + EXIT/RISK OPTIMIZATION - non svolta in "
            "questa fase.",
        "no_optimization_performed": True, "not_ready_for_deploy": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE725_DIR, "decision_card_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  DECISIONE: {payload['decision']}")


if __name__ == "__main__":
    main()
