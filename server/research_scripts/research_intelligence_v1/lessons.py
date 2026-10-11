"""What memory already knows about a family, read before the next experiment.

Read-only and deterministic. The briefing is what a person (or a Tier 1-3
agent) attaches to a new preregistration: hypotheses already refuted, failure
modes seen, data already exposed, open proposals, remaining budget and the
per-test alpha. It is also what priority_queue uses to hold a family while a
defect fix is open.
"""
from __future__ import annotations

from .hypotheses import FamilyBudget


def open_defects(memory, family):
    out = []
    for p in memory.of_type("IMPROVEMENT_PROPOSAL"):
        cur = memory.current(p["record_id"])
        if p["family"] == family and cur["record_id"] == p["record_id"] \
                and cur["body"]["proposal_class"] == "DEFECT_FIX" and cur["body"]["status"] in ("PROPOSED", "ACCEPTED"):
            out.append(cur["record_id"])
    return sorted(out)


def briefing(memory, family, *, max_per_family=6, family_alpha=0.05):
    hyps = [memory.current(h["record_id"]) for h in memory.of_type("HYPOTHESIS")
            if h["family"] == family and memory.current(h["record_id"])["record_id"] == h["record_id"]]
    exps = [e for e in memory.of_type("EXPERIMENT") if e["family"] == family]
    open_props = {}
    for p in memory.of_type("IMPROVEMENT_PROPOSAL"):
        cur = memory.current(p["record_id"])
        if p["family"] == family and cur["record_id"] == p["record_id"] and cur["body"]["status"] in ("PROPOSED",
                                                                                                    "ACCEPTED"):
            open_props.setdefault(cur["body"]["proposal_class"], []).append(cur["record_id"])
    return {
        "family": family,
        "refuted_or_negative": sorted([h["record_id"] for h in hyps if h["body"]["lifecycle_state"] == "REJECTED"]
                                      + [e["record_id"] for e in exps if e["body"]["result"] == "NEGATIVE"]),
        "failure_modes_seen": sorted({m for e in exps for m in e["body"].get("failure_modes", [])}),
        "datasets_exposed": sorted({f"{d['dataset_id']}:{d['exposure']}" for e in exps for d in e["body"]["datasets"]
                                    if d["exposure"] != "UNSEEN"}),
        "open_proposals": {k: sorted(v) for k, v in sorted(open_props.items())},
        "open_defects_block_new_runs": open_defects(memory, family),
        "hypotheses": len(hyps), "budget_remaining": FamilyBudget(memory, max_per_family).remaining(family),
        "per_test_alpha": family_alpha / max(len(hyps), 1),
        "proposal_only_hypotheses": sorted(h["record_id"] for h in hyps if h["body"]["is_proposal_only"]),
    }
