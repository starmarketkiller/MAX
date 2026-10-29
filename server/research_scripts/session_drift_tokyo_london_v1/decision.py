"""Preregistered decision rules for SD-TOKYO-LONDON-001.

Ceiling: EXPLORATORY_ONLY. VALIDATED is never emitted.
"""
from __future__ import annotations

from .stats import sign_of, year_concentration_share, yearly_breakdown

EVIDENCE_CEILING = "EXPLORATORY_ONLY"
FORBIDDEN = "VALIDATED"


def decide(summary_a, summary_b, summary_combined, rows_combined, params):
    """Apply F1–F4 and n gates. Never returns VALIDATED."""
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

    # F4 sign flip
    sa = sign_of(summary_a.get("mean_net_return_usd"))
    sb = sign_of(summary_b.get("mean_net_return_usd"))
    if sa is not None and sb is not None and sa != 0 and sb != 0 and sa != sb:
        falsifiers.append("F4_sign_flip_across_discoveries")
        reasons.append(f"sign discovery_a={sa} vs discovery_b={sb}")

    # F1 CI includes zero / non-positive
    ci = summary_combined.get("mean_net_return_usd_ci95_month_blocks")
    mean_net = summary_combined.get("mean_net_return_usd")
    if ci is None:
        reasons.append("month-block CI unavailable (<2 month blocks); treat as weak evidence")
        if mean_net is None or mean_net <= 0:
            falsifiers.append("F1_ci_includes_zero")
            reasons.append(f"mean_net_return_usd={mean_net} ≤ 0 without CI")
    else:
        if ci["low"] <= 0:
            falsifiers.append("F1_ci_includes_zero")
            reasons.append(f"CI95 low={ci['low']:.6f} ≤ 0 (high={ci['high']:.6f})")

    # F2 generic gold
    delta = summary_combined.get("mean_delta_vs_generic_gold_usd")
    if delta is None or delta <= 0:
        falsifiers.append("F2_does_not_beat_generic_gold")
        reasons.append(f"mean_delta_vs_generic_gold_usd={delta}")

    # F3 year concentration
    yearly = yearly_breakdown(rows_combined)
    conc = year_concentration_share(yearly, min_n=20)
    if conc["share"] is not None and conc["share"] > max_share:
        falsifiers.append("F3_year_concentration")
        reasons.append(
            f"year {conc['dominant_year']} share={conc['share']:.3f} > {max_share}"
        )

    if falsifiers:
        decision = "FAIL"
    else:
        decision = "EXPLORATORY_PROMISING"
        reasons.append(
            "No F1–F4 fired; still EXPLORATORY_ONLY — not POWER_READY, not VALIDATED"
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
        "sign_discovery_a": sa,
        "sign_discovery_b": sb,
    }
