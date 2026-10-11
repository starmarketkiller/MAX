"""Hypothesis generation from results and observations, by declared templates.

Rule-based (Tier 0): a trigger reads an OBSERVATION or EXPERIMENT record and
returns candidate specs. Every candidate declares mechanism, falsification,
data needed, overfitting risk and expected information value, and is written
as a proposal (evidence NONE_PROPOSAL, lifecycle HYPOTHESIS). Candidates go
through deterministic dedup and the family budget; refused ones are reported,
never silently dropped. A model (Tier 1-3) may propose specs through the same
`register_candidates` path with origin AI_PROPOSAL: same gates, same dedup.

The base hypothesis is never modified: alternatives are new ids.
"""
from __future__ import annotations

import copy

from .hypotheses import BudgetExhausted, DuplicateHypothesis, register

LOW_SELECTIVITY_CONVERSION = 0.8


def _with(spec, conditions=None, drop=(), **changes):
    out = copy.deepcopy(spec)
    out["state_conditions"] = [c for c in out["state_conditions"] if c["feature_id"] not in drop]
    for c in conditions or []:
        out["state_conditions"] = [x for x in out["state_conditions"] if x["feature_id"] != c["feature_id"]] + [c]
    out.update(changes)
    return out


def selectivity_alternatives(base_id, base_spec, observation):
    """Trigger LOW_SELECTIVITY: when almost every impulse becomes a pullback, the
    pullback filter carries little information. Alternatives make it bite, or
    remove it to measure what it adds."""
    conv = (observation["body"]["values"] or {}).get("conversion_impulse_to_pullback")
    if conv is None or conv < LOW_SELECTIVITY_CONVERSION:
        return []
    common = {"overfitting_risk": "MEDIUM", "data_needed": list(base_spec["data_needed"])}
    return [
        (f"{base_id}-ALT-DEEP-PB", _with(base_spec, [{"feature_id": "pullback_retrace_min", "operator": ">=",
                                                       "threshold": 0.5}], **common,
            mechanism="a retrace of half the leg exhausts short-term counter-flow; shallower pullbacks are "
                      "continuation noise that dilutes the signal",
            falsification="on discovery, conversion impulse->pullback stays above 0.8 or p_target_first is not "
                          "above the shallow-pullback events of the same split",
            expected_information_value="HIGH"),
         f"pullback conversion {conv:.3f}: test whether a deeper retrace adds selectivity"),
        (f"{base_id}-ALT-ATR-PB", _with(base_spec, [{"feature_id": "pullback_retrace_atr_min", "operator": ">=",
                                                      "threshold": 0.75}], drop=("pullback_retrace_min",), **common,
            mechanism="a pullback measured in volatility units is comparable across regimes; a leg fraction "
                      "is not when legs differ in size",
            falsification="selectivity and outcome do not differ from the leg-fraction rule on the same split",
            expected_information_value="MEDIUM"),
         "volatility-scaled pullback instead of leg fraction"),
        (f"{base_id}-ALT-2BAR-IMPULSE", _with(base_spec, [{"feature_id": "impulse_consecutive_h4_bars",
                                                           "operator": ">=", "threshold": 2}], **common,
            mechanism="two consecutive impulse bars mark sustained order flow rather than a single print",
            falsification="impulse count falls but conversion and p_target_first do not change",
            expected_information_value="MEDIUM"),
         "stricter impulse definition to raise selectivity upstream"),
        (f"{base_id}-NULL-NO-PB", _with(base_spec, drop=("pullback_retrace_min", "pullback_max_h4_bars"),
                                        **dict(common, overfitting_risk="LOW"),
            mechanism="null model: if the pullback adds nothing, the M15 confirmation after any impulse "
                      "should perform the same",
            falsification="base hypothesis beats this null by more than the month-block CI on discovery",
            expected_information_value="HIGH"),
         "null model isolating the contribution of the pullback filter"),
        (f"{base_id}-ALT-MACRO-WINDOW", _with(base_spec, [{"feature_id": "macro_release_within_h",
                                                           "operator": "<=", "threshold": 2}],
                                              overfitting_risk="HIGH",
                                              data_needed=list(base_spec["data_needed"]) + ["MACRO_CALENDAR_HISTORY"],
            mechanism="impulses born from scheduled releases (CPI, NFP, FOMC) are information shocks and may "
                      "retrace differently from flow-driven impulses",
            falsification="release-born and other impulses show the same conversion and outcome",
            expected_information_value="MEDIUM"),
         "macro-release impulses vs flow impulses (needs a historical calendar not yet in the repo)"),
        (f"{base_id}-ALT-SESSION-OVERLAP", _with(base_spec, [{"feature_id": "impulse_session", "operator": "==",
                                                              "threshold": "LONDON_NY_OVERLAP"}], **common,
            mechanism="impulses in the London/New York overlap carry the deepest liquidity and may retrace less",
            falsification="session split of the base run shows no difference",
            expected_information_value="LOW"),
         "session-conditioned impulse"),
    ]


def register_candidates(memory, candidates, *, base_record, source_record, family, budget, author,
                        origin="RULE_ENGINE", project="NEXUS_TRADING_RESEARCH", created_at=None):
    """Register each (id, spec, why) or report why it was refused."""
    report = {"registered": [], "duplicates": [], "over_budget": []}
    for hyp_id, spec, why in candidates:
        relations = [{"type": "ALTERNATIVE_TO", "target": base_record}]
        if source_record != base_record:
            relations.append({"type": "DERIVED_FROM", "target": source_record})
        try:
            rec = register(memory, hyp_id, spec, statement=why, origin=origin, author=author, project=project,
                           family=family, provenance=[{"kind": "RECORD", "ref": source_record}],
                           relations=relations, created_at=created_at, budget=budget)
            report["registered"].append(rec["record_id"])
        except DuplicateHypothesis as dup:
            report["duplicates"].append({"candidate": hyp_id, "existing": dup.existing_id})
        except BudgetExhausted as exc:
            report["over_budget"].append({"candidate": hyp_id, "reason": str(exc)})
    return report
