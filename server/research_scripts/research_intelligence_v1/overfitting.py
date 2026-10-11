"""Learning-without-overfitting checks for a planned experiment.

Each check returns {check, status PASS|WARN|BLOCK, detail}. A BLOCK makes the
statistical review reject the plan; nothing here reads market data.

- PERIOD_REUSE: how many experiments and plans already used this dataset/period.
- MULTIPLE_TESTING: alpha split over every test of the correlated family,
  past and planned (Bonferroni, conservative by design).
- CORRELATED_LEAKAGE: hypotheses linked by ALTERNATIVE_TO / DERIVED_FROM share
  one alpha family and must not be tested on data that selected them.
- PROTECTED_SPLIT: one-shot splits are never planned.
- POST_HOC: a hypothesis derived from a result cannot be tested on the data that
  produced the result.
- EVIDENCE_CLASS: the evidence a plan can reach is capped by its split and by
  the origin of the hypothesis (a generated hypothesis starts exploratory).
"""
from __future__ import annotations

from . import gates
from . import hypotheses as _h  # noqa: F401  (puts phase7/engine on sys.path)
from post_hoc_quarantine import (PostHocPromotionBlocked, attempt_promotion,  # noqa: E402
                                 register_post_hoc_observation)

MAX_PERIOD_REUSE = 3
SPLIT_CAP = {"discovery": "DISCOVERY_ONLY", "internal_validation": "INTERNAL_VALIDATION",
             "forward": "INDEPENDENT_FORWARD", "outside_splits": "EXPLORATORY", "unknown": "EXPLORATORY"}


def _c(check, status, detail):
    return {"check": check, "status": status, "detail": detail}


def correlated_family(memory, hyp_record_id):
    """Connected component of hypotheses over ALTERNATIVE_TO / DERIVED_FROM / REFINES / SUPERSEDES."""
    links = {}
    hyps = {r["record_id"] for r in memory.of_type("HYPOTHESIS")}
    for r in memory.of_type("HYPOTHESIS"):
        for rel in r["relations"]:
            if rel["type"] in ("ALTERNATIVE_TO", "DERIVED_FROM", "REFINES", "SUPERSEDES") and rel["target"] in hyps:
                links.setdefault(r["record_id"], set()).add(rel["target"])
                links.setdefault(rel["target"], set()).add(r["record_id"])
    seen, todo = set(), [hyp_record_id]
    while todo:
        cur = todo.pop()
        if cur not in seen:
            seen.add(cur)
            todo += list(links.get(cur, ()))
    return sorted(seen)


def tests_in_family(memory, family_ids):
    ids = {memory.get(h)["body"]["hypothesis_id"] for h in family_ids}
    run = [e for e in memory.of_type("EXPERIMENT") if e["body"]["hypothesis_id"] in ids
           and e["body"]["status"] in ("COMPLETED", "PARTIAL")]
    planned = [p for p in memory.of_type("EXPERIMENT_PLAN") if p["body"]["hypothesis_record"] in family_ids
               and p["body"]["status"] == "DRAFT_PREREGISTRATION"]
    return run, planned


def source_datasets(memory, hyp_record_id):
    """Datasets of the records a hypothesis was derived from (its selection data)."""
    out, todo, seen = set(), [hyp_record_id], set()
    while todo:
        rid = todo.pop()
        if rid in seen or memory.get(rid) is None:
            continue
        seen.add(rid)
        r = memory.get(rid)
        body = r["body"]
        if r["record_type"] == "OBSERVATION":
            out.add(body["dataset"]["dataset_id"])
        if r["record_type"] == "EXPERIMENT":
            out |= {d["dataset_id"] for d in body["datasets"]}
        for rel in r["relations"]:
            if rel["type"] in ("DERIVED_FROM", "ALTERNATIVE_TO") or (
                    r["record_type"] in ("REVIEW",) and rel["type"] == "REVIEWS"):
                todo.append(rel["target"])
        for src in r["provenance"]:
            if src["kind"] == "RECORD":
                todo.append(src["ref"])
    return out


def check_plan(memory, hyp_record_id, dataset, *, family_alpha=0.05, adding=1):
    hyp = memory.get(hyp_record_id)
    checks = []
    if dataset["split"] in gates.protected_splits():
        checks.append(_c("PROTECTED_SPLIT", "BLOCK", f"{dataset['split']} is one-shot"))
    else:
        checks.append(_c("PROTECTED_SPLIT", "PASS", dataset["split"]))

    reuse = sum(1 for e in memory.of_type("EXPERIMENT") for d in e["body"]["datasets"]
                if d["dataset_id"] == dataset["dataset_id"] and d.get("period") == dataset.get("period")) + \
        sum(1 for p in memory.of_type("EXPERIMENT_PLAN") if p["body"]["dataset"]["dataset_id"] == dataset["dataset_id"]
            and p["body"]["dataset"].get("period") == dataset.get("period")
            and p["body"]["status"] == "DRAFT_PREREGISTRATION")
    status = "PASS" if reuse < MAX_PERIOD_REUSE else ("WARN" if reuse == MAX_PERIOD_REUSE else "BLOCK")
    checks.append(_c("PERIOD_REUSE", status, f"{reuse} earlier experiments/plans on this dataset and period "
                                             f"(limit {MAX_PERIOD_REUSE})"))

    fam = correlated_family(memory, hyp_record_id)
    run, planned = tests_in_family(memory, fam)
    # Conservative: every hypothesis of the correlated family counts as a test that will be
    # run, so planning one now cannot borrow alpha from siblings planned later.
    n_tests = max(len(fam), len(run) + len(planned) + adding)
    alpha = family_alpha / n_tests
    checks.append(_c("MULTIPLE_TESTING", "PASS", f"{len(run)} run + {len(planned)} planned tests, correlated "
                                                 f"family of {len(fam)} hypotheses: per-test alpha {alpha:.5f}"))
    checks.append(_c("CORRELATED_LEAKAGE", "PASS" if len(fam) == 1 else "WARN",
                     f"correlated with {[h for h in fam if h != hyp_record_id]}: one alpha family, "
                     "results of one must not select parameters of another"))

    selected_on = source_datasets(memory, hyp_record_id)
    if dataset["dataset_id"] in selected_on:
        # Reuse the Phase 7 sec.15 gate: an idea found in some data is a post-hoc
        # observation for that data and cannot be promoted by testing it there.
        obs = register_post_hoc_observation(hyp_record_id, dataset["dataset_id"], "residual_analysis",
                                            dataset["dataset_id"])
        try:
            attempt_promotion(obs, "PRE_REGISTERED_CANDIDATE", same_run=True)
            checks.append(_c("POST_HOC", "PASS", "gate did not object"))
        except PostHocPromotionBlocked as exc:
            checks.append(_c("POST_HOC", "BLOCK", str(exc)))
    else:
        checks.append(_c("POST_HOC", "PASS", f"selection data {sorted(selected_on) or 'none'} differ from the test data"))

    cap = SPLIT_CAP.get(dataset["split"], "EXPLORATORY")
    if hyp["body"]["is_proposal_only"] and cap not in ("EXPLORATORY", "DISCOVERY_ONLY"):
        checks.append(_c("EVIDENCE_CLASS", "BLOCK", "a generated hypothesis is first tested on discovery"))
    else:
        checks.append(_c("EVIDENCE_CLASS", "PASS", f"at most {cap}; an AI or rule proposal is not evidence"))
    return checks, alpha, cap
