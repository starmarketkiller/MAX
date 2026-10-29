"""Preregistered decision rules for TG-12M-GATE-001.

Ceiling: EXPLORATORY_ONLY. VALIDATED is never emitted.
"""
from __future__ import annotations

from .stats import sign_of, summarize, year_concentration_share, yearly_breakdown

EVIDENCE_CEILING = "EXPLORATORY_ONLY"
FORBIDDEN = "VALIDATED"
VARIANT_ORDER = ("LO_FLAT_UNIT", "LO_FLAT_VOL", "LS_VOL")


def bonferroni_level(params):
    k = len(params["variant_ids"])
    alpha = float(params["selection_alpha"])
    return 1.0 - (alpha / k)


def select_survivors(variant_summaries, params):
    """Return list of variant_ids that pass F1 (CI low > 0 at Bonferroni level)."""
    level = bonferroni_level(params)
    survivors = []
    details = {}
    for vid in params["variant_ids"]:
        summary = variant_summaries.get(vid) or {}
        ci = summary.get("mean_excess_log_return_ci_month_blocks")
        mean_ex = summary.get("mean_excess_log_return")
        ok = False
        reason = "no_ci"
        if ci is not None and ci.get("low") is not None and ci["low"] > 0:
            ok = True
            reason = f"ci_low={ci['low']:.8f} > 0 at level={level}"
        elif mean_ex is not None and ci is None:
            reason = "ci_unavailable"
        else:
            reason = f"ci_low={(ci or {}).get('low')} ≤ 0 or missing"
        details[vid] = {
            "survives": ok,
            "mean_excess_log_return": mean_ex,
            "ci": ci,
            "reason": reason,
            "n_days": summary.get("n_days", 0),
        }
        if ok:
            survivors.append(vid)
    return survivors, details


def pick_winner(survivors, variant_summaries):
    if not survivors:
        return None
    def key(vid):
        mean = (variant_summaries.get(vid) or {}).get("mean_excess_log_return") or float("-inf")
        # Higher mean wins; tie-break declaration order.
        return (-mean, VARIANT_ORDER.index(vid) if vid in VARIANT_ORDER else 99)
    return sorted(survivors, key=key)[0]


def decide_selection(variant_rows_by_id, params):
    """Apply F1 on selection split. Never returns VALIDATED."""
    min_n = int(params["min_n_selection"])
    level = bonferroni_level(params)
    summaries = {}
    for vid, rows in variant_rows_by_id.items():
        summaries[vid] = summarize(rows, params, ci_level=level)

    # n gate: require at least one variant to have enough days (all share calendar).
    n_any = max((s.get("n_days", 0) for s in summaries.values()), default=0)
    if n_any < min_n:
        return {
            "decision": "INSUFFICIENT_EVIDENCE",
            "evidence_ceiling": EVIDENCE_CEILING,
            "power_gate_status": "EXPLORATORY_ONLY",
            "validated_forbidden": True,
            "selected_variant_id": None,
            "survivors": [],
            "reasons": [f"selection n_days={n_any}; need ≥{min_n}"],
            "falsifiers_fired": [],
            "variant_details": {},
            "variant_summaries": summaries,
        }

    survivors, details = select_survivors(summaries, params)
    if not survivors:
        return {
            "decision": "FAIL",
            "evidence_ceiling": EVIDENCE_CEILING,
            "power_gate_status": "EXPLORATORY_ONLY",
            "validated_forbidden": True,
            "selected_variant_id": None,
            "survivors": [],
            "reasons": ["F1: no variant beats matched BH after Bonferroni CI"],
            "falsifiers_fired": ["F1_no_variant_beats_bh_after_mt"],
            "variant_details": details,
            "variant_summaries": summaries,
        }

    winner = pick_winner(survivors, summaries)
    return {
        "decision": "SELECTION_SURVIVOR",
        "evidence_ceiling": EVIDENCE_CEILING,
        "power_gate_status": "EXPLORATORY_ONLY",
        "validated_forbidden": True,
        "selected_variant_id": winner,
        "survivors": survivors,
        "reasons": [f"survivors={survivors}; frozen winner={winner}"],
        "falsifiers_fired": [],
        "variant_details": details,
        "variant_summaries": summaries,
    }


def decide_confirmation(summary_a, summary_b, summary_combined, rows_combined, params, winner_id):
    """Apply F2–F4 on confirmation. Never returns VALIDATED."""
    reasons = []
    falsifiers = []
    min_n = int(params["min_n_per_confirmation"])
    min_combined = int(params["min_n_combined_for_ci"])
    max_share = float(params["year_concentration_max_share"])

    na = summary_a.get("n_days", summary_a.get("n_closed", 0))
    nb = summary_b.get("n_days", summary_b.get("n_closed", 0))
    nc = summary_combined.get("n_days", summary_combined.get("n_closed", 0))

    if na < min_n or nb < min_n:
        return {
            "decision": "INSUFFICIENT_EVIDENCE",
            "evidence_ceiling": EVIDENCE_CEILING,
            "power_gate_status": "EXPLORATORY_ONLY",
            "validated_forbidden": True,
            "selected_variant_id": winner_id,
            "reasons": [
                f"n_days confirmation_a={na}, confirmation_b={nb}; need ≥{min_n} each"
            ],
            "falsifiers_fired": [],
        }

    if nc < min_combined:
        return {
            "decision": "INSUFFICIENT_EVIDENCE",
            "evidence_ceiling": EVIDENCE_CEILING,
            "power_gate_status": "EXPLORATORY_ONLY",
            "validated_forbidden": True,
            "selected_variant_id": winner_id,
            "reasons": [f"combined n_days={nc}; need ≥{min_combined}"],
            "falsifiers_fired": [],
        }

    sa = sign_of(summary_a.get("mean_excess_log_return"))
    sb = sign_of(summary_b.get("mean_excess_log_return"))
    if sa is not None and sb is not None and sa != 0 and sb != 0 and sa != sb:
        falsifiers.append("F4_sign_flip_across_confirmations")
        reasons.append(f"sign confirmation_a={sa} vs confirmation_b={sb}")

    ci = summary_combined.get("mean_excess_log_return_ci95_month_blocks")
    mean_ex = summary_combined.get("mean_excess_log_return")
    if ci is None:
        reasons.append("month-block CI unavailable (<2 month blocks); treat as weak evidence")
        if mean_ex is None or mean_ex <= 0:
            falsifiers.append("F2_winner_ci_includes_zero_on_confirm")
            reasons.append(f"mean_excess_log_return={mean_ex} ≤ 0 without CI")
    else:
        if ci["low"] <= 0:
            falsifiers.append("F2_winner_ci_includes_zero_on_confirm")
            reasons.append(f"CI95 low={ci['low']:.8f} ≤ 0 (high={ci['high']:.8f})")

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
            "No F2–F4 fired; still EXPLORATORY_ONLY — not POWER_READY, not VALIDATED"
        )

    return {
        "decision": decision,
        "evidence_ceiling": EVIDENCE_CEILING,
        "power_gate_status": "EXPLORATORY_ONLY",
        "validated_forbidden": True,
        "forbidden_label": FORBIDDEN,
        "selected_variant_id": winner_id,
        "reasons": reasons,
        "falsifiers_fired": falsifiers,
        "yearly": yearly,
        "year_concentration": conc,
        "sign_confirmation_a": sa,
        "sign_confirmation_b": sb,
    }
