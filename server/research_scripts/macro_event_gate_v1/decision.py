"""Preregistered decision rules for MEG-NFP-CPI-FOMC-001.

Ceiling: EXPLORATORY_ONLY. VALIDATED is never emitted.

F1 (phase-1 core): on combined discoveries, FAIL if *neither* spread_delta nor
range_delta shows event > same-clock control with month-block CI low > 0.
"""
from __future__ import annotations

from .stats import metric_elevated, sign_of, year_concentration_share, yearly_breakdown

EVIDENCE_CEILING = "EXPLORATORY_ONLY"
FORBIDDEN = "VALIDATED"


def decide(summary_a, summary_b, summary_combined, rows_combined, params):
    """Apply F1–F3 and n gates. Never returns VALIDATED."""
    reasons = []
    falsifiers = []
    min_n = int(params["min_n_per_discovery"])
    min_combined = int(params["min_n_combined_for_ci"])
    max_share = float(params["year_concentration_max_share"])

    na = summary_a.get("n_closed", 0)
    nb = summary_b.get("n_closed", 0)
    nc = summary_combined.get("n_closed", 0)

    if na < min_n or nb < min_n:
        return {
            "decision": "INSUFFICIENT_EVIDENCE",
            "evidence_ceiling": EVIDENCE_CEILING,
            "power_gate_status": "EXPLORATORY_ONLY",
            "validated_forbidden": True,
            "reasons": [
                f"n_closed discovery_a={na}, discovery_b={nb}; need ≥{min_n} each"
            ],
            "falsifiers_fired": [],
        }

    if nc < min_combined:
        return {
            "decision": "INSUFFICIENT_EVIDENCE",
            "evidence_ceiling": EVIDENCE_CEILING,
            "power_gate_status": "EXPLORATORY_ONLY",
            "validated_forbidden": True,
            "reasons": [f"combined n_closed={nc}; need ≥{min_combined}"],
            "falsifiers_fired": [],
        }

    spread_ok, spread_ci, spread_mean = metric_elevated(summary_combined, "spread_delta")
    range_ok, range_ci, range_mean = metric_elevated(summary_combined, "range_delta")

    if not spread_ok and not range_ok:
        falsifiers.append("F1_spread_and_vol_not_elevated_vs_same_clock")
        reasons.append(
            f"spread_delta mean={spread_mean} ci={spread_ci}; "
            f"range_delta mean={range_mean} ci={range_ci}; "
            "neither CI low > 0"
        )
    else:
        reasons.append(
            f"elevation: spread_ok={spread_ok} (mean={spread_mean}), "
            f"range_ok={range_ok} (mean={range_mean})"
        )

    # F2 year concentration on spread_delta (primary microstructure cost proxy)
    yearly = yearly_breakdown(rows_combined, metric="spread_delta")
    conc = year_concentration_share(yearly, metric_key="mean_spread_delta", min_n=8)
    if conc["share"] is not None and conc["share"] > max_share:
        falsifiers.append("F2_year_concentration")
        reasons.append(
            f"year {conc['dominant_year']} share={conc['share']:.3f} > {max_share}"
        )

    # F3 sign flip: require same sign on at least one elevated metric across A/B
    # Prefer spread if both elevated on combined; else the one that elevated.
    metric_for_sign = "mean_spread_delta"
    if spread_ok and not range_ok:
        metric_for_sign = "mean_spread_delta"
    elif range_ok and not spread_ok:
        metric_for_sign = "mean_range_delta"
    elif spread_ok and range_ok:
        metric_for_sign = "mean_spread_delta"

    sa = sign_of(summary_a.get(metric_for_sign))
    sb = sign_of(summary_b.get(metric_for_sign))
    if sa is not None and sb is not None and sa != 0 and sb != 0 and sa != sb:
        falsifiers.append("F3_sign_flip_across_discoveries")
        reasons.append(f"sign {metric_for_sign} discovery_a={sa} vs discovery_b={sb}")

    if falsifiers:
        decision = "FAIL"
    else:
        decision = "EXPLORATORY_PROMISING"
        reasons.append(
            "No F1–F3 fired; still EXPLORATORY_ONLY — not POWER_READY, not VALIDATED. "
            "Phase-1 only justifies a non-directional gate study; no directional claim."
        )

    return {
        "decision": decision,
        "evidence_ceiling": EVIDENCE_CEILING,
        "power_gate_status": "EXPLORATORY_ONLY",
        "validated_forbidden": True,
        "forbidden_label": FORBIDDEN,
        "reasons": reasons,
        "falsifiers_fired": falsifiers,
        "yearly": yearly,
        "year_concentration": conc,
        "spread_elevated": spread_ok,
        "range_elevated": range_ok,
        "sign_metric": metric_for_sign,
        "sign_discovery_a": sa,
        "sign_discovery_b": sb,
    }
