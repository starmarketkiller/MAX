"""Did research get better? Cycle metrics and improvement trials.

Cycle metrics (EVALUATION record) count information, not activity: findings and
errors found, hypotheses eliminated or strengthened, duplicates avoided,
resources used, quality of new proposals, reliability of conclusions. The number
of backtests is reported only as a cost.

Improvement trials (IMPROVEMENT_TRIAL records) measure each proposal against a
baseline fixed before the change:
- metric: rate of reviewed experiments of the family that show the proposal's
  finding (e.g. DATASET_HASH_MISSING) under the same review rules version;
- BASELINE: written when a person ACCEPTS the proposal, over the reviews known then;
- RESULT: written once at least MIN_INDEPENDENT experiments of the family are
  reviewed after the IMPLEMENTED decision (records that were not in the baseline);
- verdict IMPROVED / NOT_IMPROVED / INSUFFICIENT_EVIDENCE. Failed improvements
  stay in memory like every other negative result.
"""
from __future__ import annotations

from .lessons import open_defects  # noqa: F401  (re-exported for callers)
from .memory import sha256_text
from .review import RULES_VERSION

METRICS_VERSION = "RI_EVAL_METRICS_V1"
MIN_INDEPENDENT = 3
REQUIRED_DROP = 0.5


def _reviews(memory, family, records=None):
    pool = records if records is not None else memory.records
    out = []
    for r in pool:
        if r["record_type"] == "REVIEW" and r["family"] == family and r["body"]["rules_version"] == RULES_VERSION:
            out.append(r)
    return out


def finding_rate(reviews, check):
    if not reviews:
        return {"rate": None, "n": 0, "with_finding": 0}
    hit = sum(1 for r in reviews if any(f["check"] == check for f in r["body"]["findings"]))
    return {"rate": hit / len(reviews), "n": len(reviews), "with_finding": hit}


def baseline_for(memory, family, check, upto_index=None):
    pool = memory.records[:upto_index] if upto_index is not None else memory.records
    return finding_rate(_reviews(memory, family, pool), check)


def success_criterion(baseline):
    if baseline["rate"] is None:
        return f"on >= {MIN_INDEPENDENT} later experiments the finding rate is below 0.5"
    target = baseline["rate"] * (1 - REQUIRED_DROP)
    return (f"on >= {MIN_INDEPENDENT} experiments reviewed after implementation the finding rate is "
            f"<= {target:.3f} (baseline {baseline['rate']:.3f} on {baseline['n']} reviews)")


def _check_of(proposal):
    return proposal["record_id"].split("-", 1)[1].rsplit("-", 1)[0].split(".")[0]


def _index(memory, record_id):
    return next(i for i, r in enumerate(memory.records) if r["record_id"] == record_id)


def update_trials(memory, *, author="improvement-evaluator-rules", created_at=None):
    """Write missing BASELINE / RESULT trials. Idempotent (deterministic ids)."""
    written = []
    for prop in memory.of_type("IMPROVEMENT_PROPOSAL"):
        if prop["body"]["status"] != "PROPOSED" or "." in prop["record_id"]:
            continue
        chain, cur = [], prop["record_id"]
        while True:
            nxt = [r for r in memory.records if r["record_type"] == "IMPROVEMENT_PROPOSAL"
                   and any(x["type"] == "SUPERSEDES" and x["target"] == cur for x in r["relations"])]
            if not nxt:
                break
            cur = nxt[-1]["record_id"]
            chain.append(nxt[-1])
        accepted = next((r for r in chain if r["body"]["status"] == "ACCEPTED"), None)
        implemented = next((r for r in chain if r["body"]["status"] == "IMPLEMENTED"), None)
        if not accepted:
            continue
        check, family = _check_of(prop), prop["family"]
        base_id = f"TRIAL-{sha256_text(prop['record_id'] + '|BASELINE')[:16].upper()}"
        if not memory.get(base_id):
            base = baseline_for(memory, family, check, upto_index=_index(memory, accepted["record_id"]))
            memory.append("IMPROVEMENT_TRIAL", base_id,
                          {"proposal_record": prop["record_id"], "phase": "BASELINE", "metric": f"finding_rate:{check}",
                           "baseline": base, "success_criterion": success_criterion(base)},
                          author=author, origin="RULE_ENGINE", project=prop["project"], family=family,
                          created_at=created_at, relations=[{"type": "REVIEWS", "target": accepted["record_id"]}])
            written.append(base_id)
        res_id = f"TRIAL-{sha256_text(prop['record_id'] + '|RESULT')[:16].upper()}"
        if not implemented or memory.get(res_id):
            continue
        base = memory.get(base_id)["body"]
        later = _reviews(memory, family, memory.records[_index(memory, implemented["record_id"]):])
        if len(later) < MIN_INDEPENDENT:
            continue
        after = finding_rate(later, check)
        if base["baseline"]["rate"] is None:
            verdict = "INSUFFICIENT_EVIDENCE"
        elif after["rate"] <= base["baseline"]["rate"] * (1 - REQUIRED_DROP):
            verdict = "IMPROVED"
        else:
            verdict = "NOT_IMPROVED"
        memory.append("IMPROVEMENT_TRIAL", res_id,
                      {"proposal_record": prop["record_id"], "phase": "RESULT", "metric": base["metric"],
                       "baseline": base["baseline"], "success_criterion": base["success_criterion"],
                       "after": after, "verdict": verdict,
                       "independent_records": [r["body"]["reviewed_record"] for r in later]},
                      author=author, origin="RULE_ENGINE", project=prop["project"], family=family,
                      created_at=created_at,
                      relations=[{"type": "REVIEWS", "target": implemented["record_id"]},
                                 {"type": "DERIVED_FROM", "target": base_id}])
        written.append(res_id)
    return written


def cycle_metrics(memory, start_index, step_outputs, resources):
    """Metrics over the records written since the cycle opened."""
    new = memory.records[start_index:]
    of = lambda t: [r for r in new if r["record_type"] == t]  # noqa: E731
    findings = [f for r in of("REVIEW") for f in r["body"]["findings"]]
    hyps = of("HYPOTHESIS")
    exps = [r for r in of("EXPERIMENT") if r["body"]["status"] != "NOT_RUN"]
    plans = of("EXPERIMENT_PLAN")
    actions = of("ACTION")
    hypo = step_outputs.get("HYPOTHESIZE", {})
    review_out = step_outputs.get("REVIEW", {})
    plan_out = step_outputs.get("PLAN", {})
    declared = [h for h in hyps if "not declared" not in h["body"]["mechanism"]
                and "not declared" not in h["body"]["falsification"]]
    confirmatory = [e for e in exps if e["body"]["evidence_level"] in
                    ("INTERNAL_VALIDATION", "LOCKED_VALIDATION", "INDEPENDENT_FORWARD")]
    return {
        "new_information": {"findings": len(findings),
                            "findings_by_area": {a: sum(1 for f in findings if f["area"] == a)
                                                 for a in sorted({f["area"] for f in findings})},
                            "experiments_ingested": len(exps), "observations": len(of("OBSERVATION"))},
        "hypotheses": {"eliminated": sum(1 for e in exps if e["body"]["result"] == "NEGATIVE"),
                       "strengthened": sum(1 for e in exps if e["body"]["result"] == "POSITIVE"),
                       "inconclusive": sum(1 for e in exps if e["body"]["result"] == "INCONCLUSIVE"),
                       "new_proposals": len(hyps)},
        "errors_identified": sum(1 for f in findings if f["proposal_class"] == "DEFECT_FIX" or f["severity"] == "BLOCKER"),
        "duplicates_avoided": {"hypotheses": len(hypo.get("duplicates", [])),
                               "over_budget": len(hypo.get("over_budget", [])),
                               "proposals_linked": len(review_out.get("linked", [])),
                               "plans_equivalent_or_done": sum(1 for s in plan_out.get("skipped", [])
                                                               if "equivalent" in s["reason"] or "already" in s["reason"])},
        "learning_reused": {"plans_skipped_from_earlier_findings": sum(
            1 for s in plan_out.get("skipped", []) if s["reason"].startswith("learned from"))},
        "resources": resources,
        "proposal_quality": {"hypotheses_with_mechanism_and_falsification":
                             (len(declared) / len(hyps)) if hyps else None,
                             "plans_passing_statistical_review": (sum(1 for p in plans if p["body"]["status"] ==
                                                                      "DRAFT_PREREGISTRATION") / len(plans)) if plans else None},
        "conclusion_reliability": {"experiments": len(exps), "confirmatory_share":
                                   (len(confirmatory) / len(exps)) if exps else None,
                                   "ai_or_rule_results_counted_as_evidence": 0},
        "actions": {m: sum(1 for a in actions if a["body"]["mode"] == m)
                    for m in ("AUTO_SAFE", "APPROVAL_REQUIRED", "PROHIBITED")},
        "cost_only_not_success": {"backtests_or_real_runs_executed": 0},
    }
