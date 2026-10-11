"""BL-01 power verification and BL-02 sizing. Synthetic computation only: no tick read.

Inputs that come from data are the structural counts measured on MARKET_STATE_V1
H4 bars (2019-02-03..2022-02-03) with the Behavior Lab detectors of PR #39
(commit 613a9a8, frozen BL-H4M15-IPC-001 params): they describe how often the
H4 setup forms, never how trades end.

Run from server/research_scripts:
    python -m bl_power_study_v1.run_study            # writes bl01_power_report_v1.json
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from research_intelligence_v1 import power as P  # noqa: E402

STRUCTURAL = {
    "source": "MARKET_STATE_V1_436265d450475aaa xauusd_h4_bars.csv sha256 4f4a248d...ebcb",
    "detectors": "behavior_lab_v1.events detect_impulses/detect_pullbacks @ 613a9a8, params sha 7c66d51c...",
    "h4_bars": 4809, "years": 3.001, "impulses": 183, "pullbacks": 167, "conversion_impulse_to_pullback": 0.913,
    "pullbacks_per_year": 55.65, "pullbacks_by_year": {"2019": 60, "2020": 58, "2021": 45, "2022 (Jan only)": 4},
    "monthly_dispersion_index": 0.98, "spread_over_atr_at_pullbacks": {"median": 0.0461, "p90": 0.0761},
}
DISCOVERY_YEARS = 1.498           # 2023-02-04 .. 2024-08-04
PULLBACKS_EXPECTED = round(STRUCTURAL["pullbacks_per_year"] * DISCOVERY_YEARS, 1)
ASSUMPTIONS = {
    "target_r": 2.0, "null_p_target_first": "1/3 (driftless barrier probability for +2R/-1R)",
    "timeout_share": 0.15, "timeout_r": "Normal(0, 0.7) clipped to [-1, 2]",
    "cost_r": "0.05 R round trip (median spread/ATR 0.046 at risk about 1 ATR); stress +0.10 R as in the rule",
    "pullback_to_trade_conversion": "unknown: 0.4 / 0.6 / 0.8 (needs M15 confirmation, risk filter, entry gap; "
                                    "measured by BL-01 itself, a structural not an outcome quantity)",
    "dependence": "month-level shift of p with SD 0.05 (also 0.10); month-clustered SE approximates the "
                  "month-block bootstrap (checked: width ratio 0.98, CI-low 0.017 R lower on average)",
    "decision_rule": "BL01_DECISION_RULES_V1, direction/hour/cell checks not modelled (GO is an upper bound)",
}


def poisson_tail_ge(lam, k):
    term, cdf = math.exp(-lam), 0.0
    for i in range(k):
        cdf += term
        term *= lam / (i + 1)
    return 1 - cdf


def bl01():
    out = {"loop_v1_replication": P.replicate_loop_v1(), "expected_pullbacks": PULLBACKS_EXPECTED,
           "expected_pullbacks_90pct": [round(PULLBACKS_EXPECTED - 1.645 * math.sqrt(PULLBACKS_EXPECTED), 1),
                                        round(PULLBACKS_EXPECTED + 1.645 * math.sqrt(PULLBACKS_EXPECTED), 1)]}
    out["p_trades_ge_60"] = {str(c): round(poisson_tail_ge(PULLBACKS_EXPECTED * c, 60), 3) for c in (0.4, 0.6, 0.7, 0.8)}
    out["p_trades_ge_30"] = {str(c): round(poisson_tail_ge(PULLBACKS_EXPECTED * c, 30), 3) for c in (0.4, 0.6, 0.7, 0.8)}
    table = []
    for dp in (0.0, 0.04, 0.08, 0.12, 0.16):
        mu, sd = P.moments(1 / 3 + dp, timeout_share=0.15, cost_r=0.05)
        row = {"delta_p": dp, "net_mean_r": round(mu, 3), "sd_r": round(sd, 3),
               "ci_low_power_n50": round(P.power_ci_low_positive(mu, sd, 50), 3),
               "ci_low_power_n83": round(P.power_ci_low_positive(mu, sd, 83), 3),
               "n_for_80pct_ci_low": P.n_required(mu, sd, deff=1.05)}
        for conv in (0.4, 0.6, 0.8):
            for msd in (0.05, 0.10):
                sim = P.simulate_bl01_rule(delta_p=dp, pullbacks_expected=PULLBACKS_EXPECTED, conversion=conv,
                                           month_sd=msd, reps=2000)
                row[f"rule_conv{conv}_msd{msd}"] = {k: round(v, 3) for k, v in sim["decision_rates"].items()}
                row[f"trades_median_conv{conv}"] = sim["trades_median"]
        table.append(row)
    out["scenarios"] = table
    out["mde_net_r_80pct"] = {f"n{n}": round(P.mde(n, 1.40, deff=1.05), 3) for n in (33, 50, 67, 83)}
    return out


def bl02():
    rows = []
    for mde in (0.10, 0.15, 0.20, 0.25, 0.30):
        n = P.n_required(mde, 1.40, deff=1.10)
        rows.append({"mde_net_r": mde, "trades_needed_80pct": n,
                     "years_xauusd_h4": {str(c): round(n / (STRUCTURAL["pullbacks_per_year"] * c), 1)
                                         for c in (0.4, 0.6, 0.8)}})
    window_years = 11.0  # 2008-01-01 .. 2018-12-31
    reach = {str(c): round(P.mde(STRUCTURAL["pullbacks_per_year"] * c * window_years, 1.40, deff=1.10), 3)
             for c in (0.4, 0.6, 0.8)}
    return {"sample_size": rows, "candidate_window": "2008-01-01..2018-12-31 (11 years, NOT_USED by every registered family)",
            "mde_reachable_in_window_net_r": reach, "assumed_sd_r": 1.40, "assumed_deff": 1.10,
            "alpha": "0.05 two-sided (single preregistered primary hypothesis)", "power": 0.8}


def main():
    report = {"study": "BL01_POWER_AND_BL02_SIZING_V1", "inputs_structural": STRUCTURAL, "assumptions": ASSUMPTIONS,
              "bl01": bl01(), "bl02": bl02()}
    path = os.path.join(HERE, "bl01_power_report_v1.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return report


if __name__ == "__main__":
    r = main()
    print(json.dumps({"p_trades_ge_60": r["bl01"]["p_trades_ge_60"], "mde": r["bl01"]["mde_net_r_80pct"],
                      "bl02": r["bl02"]["mde_reachable_in_window_net_r"]}, indent=1))
