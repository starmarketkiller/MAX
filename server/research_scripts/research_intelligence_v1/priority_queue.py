"""Experiment priority queue with anti-contamination controls.

Criteria are the eight of phase7_26/research_priority_queue_v1.json (simple
unweighted 1-5 sum, PF never a criterion) plus four declared here:
contamination_risk, compute_cost, data_availability, ecosystem_relevance.
All are computed from memory records and a caller-supplied availability map:
no network, no data read, no model call.

Exclusions come before ranking and are recorded with their reason:
data not available, a protected split needed, lifecycle already past testing.
The family budget fixes how many tests may run and the per-test alpha
(Bonferroni over the family), so adding candidates never loosens the bar.
"""
from __future__ import annotations

from . import gates
from .memory import canonical, sha256_text

RULES_VERSION = "RI_QUEUE_RULES_V1"
P726_CRITERIA = ["expected_information_gain", "evidence_quality", "sample_availability", "integrity_confidence",
                 "novelty", "cost_time_to_test", "availability_of_untouched_data", "mechanism_distinctiveness"]
EXTRA_CRITERIA = ["contamination_risk", "compute_cost", "data_availability", "ecosystem_relevance"]
LEVEL = {"LOW": 2, "MEDIUM": 3, "HIGH": 5, "UNKNOWN": 1}
RISK = {"LOW": 5, "MEDIUM": 3, "HIGH": 1, "UNKNOWN": 2}
QUEUEABLE = {"OBSERVATION", "HYPOTHESIS"}


def _clip(x):
    return max(1, min(5, int(x)))


def score(memory, hyp, availability):
    b = hyp["body"]
    family = hyp["family"]
    siblings = [r for r in memory.of_type("HYPOTHESIS") if r["family"] == family]
    tested = [r for r in memory.of_type("EXPERIMENT") if r["family"] == family]
    null_like = "NULL" in b["hypothesis_id"].upper()
    datasets = b["data_needed"]
    exposures = [d.get("exposure") for e in tested for d in e["body"]["datasets"]]
    return {
        "expected_information_gain": LEVEL[b["expected_information_value"]],
        "evidence_quality": 2 if b["is_proposal_only"] else 3,
        "sample_availability": 4 if all(availability.get(d) for d in datasets) else 1,
        "integrity_confidence": 4 if not any(f["body"]["status"] == "PROPOSED" and f["body"]["proposal_class"]
                                            == "DEFECT_FIX" and f["family"] == family
                                            for f in memory.of_type("IMPROVEMENT_PROPOSAL")) else 2,
        "novelty": _clip(6 - len(siblings) // 2),
        "cost_time_to_test": 4 if all(availability.get(d) for d in datasets) else 1,
        "availability_of_untouched_data": 1 if any(x not in ("UNSEEN", None) for x in exposures) else 4,
        "mechanism_distinctiveness": 4 if null_like or "not declared" not in b["mechanism"] else 1,
        "contamination_risk": RISK[b["overfitting_risk"]],
        "compute_cost": 3,
        "data_availability": 5 if all(availability.get(d) for d in datasets) else 1,
        "ecosystem_relevance": _clip(1 + len(tested) + (1 if len(siblings) > 1 else 0)),
    }


def build_queue(memory, availability, *, family_budget=6, family_alpha=0.05, author="research-director-rules",
                write=True, created_at=None):
    """Rank queueable hypotheses. Returns the PRIORITIZATION body (and writes it once per input state)."""
    protected = gates.protected_splits()
    ranked, excluded = [], []
    families = {}
    for hyp in memory.of_type("HYPOTHESIS"):
        b = hyp["body"]
        families.setdefault(hyp["family"], 0)
        families[hyp["family"]] += 1
        if b["lifecycle_state"] not in QUEUEABLE:
            excluded.append({"record_id": hyp["record_id"], "reason": f"lifecycle {b['lifecycle_state']}: "
                             "already preregistered, tested or decided"})
            continue
        missing = [d for d in b["data_needed"] if not availability.get(d)]
        if missing:
            excluded.append({"record_id": hyp["record_id"], "reason": f"data not available: {missing}"})
            continue
        needs_protected = [d for d in b["data_needed"] if any(p in d.lower() for p in protected)]
        if needs_protected:
            excluded.append({"record_id": hyp["record_id"],
                             "reason": f"needs a one-shot split {needs_protected}: never queued automatically"})
            continue
        s = score(memory, hyp, availability)
        ranked.append({"record_id": hyp["record_id"], "family": hyp["family"], "scores": s,
                       "total": sum(s.values()), "evidence_level": b["evidence_level"]})
    ranked.sort(key=lambda r: (-r["total"], r["record_id"]))
    budget = {"per_family_max_hypotheses": family_budget, "family_alpha": family_alpha,
              "per_test_alpha_bonferroni": {f: family_alpha / max(n, 1) for f, n in sorted(families.items())},
              "criteria": P726_CRITERIA + EXTRA_CRITERIA, "pf_is_a_criterion": False,
              "max_runs_without_approval": 0}
    body = {"rules_version": RULES_VERSION, "budget": budget, "ranked": ranked, "excluded": excluded}
    if write:
        # Keyed on the evidence state, not on earlier queues: same evidence + same availability = same queue.
        state = next((r["record_hash"] for r in reversed(memory.records) if r["record_type"] != "PRIORITIZATION"),
                     "0" * 64)
        pid = f"PRIO-{sha256_text(RULES_VERSION + state + canonical(availability))[:12].upper()}"
        if not memory.get(pid):
            memory.append("PRIORITIZATION", pid, body, author=author, origin="RULE_ENGINE",
                          project="NEXUS_TRADING_RESEARCH", family="CROSS_FAMILY",
                          provenance=[{"kind": "RECORD", "ref": "evidence-state", "sha256": state}],
                          created_at=created_at)
    return body
