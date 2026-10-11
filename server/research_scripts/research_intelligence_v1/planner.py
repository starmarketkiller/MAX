"""Autonomous planning: ranked hypotheses -> falsifiable, preregistration-ready plans.

Reads the PRIORITIZATION produced by priority_queue (never re-ranks on its own),
then for each candidate within the cycle budget:
1. skips what was already executed or planned (exact equivalence key) and what is
   substantially equivalent to something already tested or planned (same event,
   direction and features, every threshold within NEAR_REL_TOL);
2. runs the overfitting checks and the Statistical Reviewer;
3. writes an EXPERIMENT_PLAN (draft preregistration) whose actions the loop will
   pass through authorization.

The success of a cycle is never the number of plans or backtests: see evaluation.py.
"""
from __future__ import annotations

import re

from . import overfitting
from .memory import canonical, sha256_text
from .review import MIN_CLOSED_FOR_FIRST_READ

NEAR_REL_TOL = 0.05
DEFAULT_CYCLE_BUDGET = {"max_plans": 2, "max_plans_per_family": 1}


def equivalence_key(hyp, dataset):
    return sha256_text(canonical({"signature": hyp["body"]["signature_sha256"], "dataset": dataset["dataset_id"],
                                  "split": dataset["split"], "period": dataset.get("period")}))


def _parse(signature):
    head, conds = {}, {}
    for line in signature.splitlines():
        if line.startswith("STATE."):
            m = re.match(r"STATE\.(.+?)(==|!=|>=|<=|>|<)(.+)", line)
            conds[m.group(1)] = (m.group(2), m.group(3))
        else:
            k, _, v = line.partition("=")
            head[k] = v
    return head, conds


def near_equivalent(sig_a, sig_b, tol=NEAR_REL_TOL):
    """Same event, direction, outcome and feature/operator set; numeric thresholds within tol."""
    (ha, ca), (hb, cb) = _parse(sig_a), _parse(sig_b)
    if ha != hb or set(ca) != set(cb):
        return False
    for f, (op, va) in ca.items():
        opb, vb = cb[f]
        if op != opb:
            return False
        try:
            a, b = float(va), float(vb)
        except ValueError:
            if va != vb:
                return False
            continue
        if abs(a - b) > tol * max(abs(a), abs(b), 1e-12):
            return False
    return True


def statistical_review(hyp, checks, alpha, cap, expected_events):
    """The Statistical Reviewer: deterministic, verifiable, and the only way a plan becomes a draft."""
    issues = [f"{c['check']}: {c['detail']}" for c in checks if c["status"] == "BLOCK"]
    b = hyp["body"]
    if "not declared" in b["falsification"] or not b["falsification"].strip():
        issues.append("no falsification criterion")
    if "not declared" in b["mechanism"]:
        issues.append("no economic mechanism")
    if expected_events is not None and expected_events < MIN_CLOSED_FOR_FIRST_READ:
        issues.append(f"expected {expected_events} events < {MIN_CLOSED_FOR_FIRST_READ}: underpowered by design")
    return {"reviewer": "statistical-reviewer-rules", "verdict": "REJECT" if issues else "PASS",
            "issues": issues, "alpha": alpha, "evidence_cap": cap,
            "warnings": [f"{c['check']}: {c['detail']}" for c in checks if c["status"] == "WARN"]}


def learned_underpowered(memory, dataset_id, expected_events):
    """Earlier cycles already found this dataset underpowered at this sample size."""
    for a in memory.of_type("ACTION"):
        if a["body"]["kind"] == "SYNTHETIC_DRY_RUN" and a["body"]["status"] == "EXECUTED":
            res = a["body"].get("result") or {}
            plan = memory.get(a["body"].get("plan_record", "")) if a["body"].get("plan_record") else None
            if plan and plan["body"]["dataset"]["dataset_id"] == dataset_id and res.get("verdict") == "UNDERPOWERED" \
                    and res.get("expected_events") == expected_events:
                return a["record_id"], res
    return None, None


def plan_cycle(memory, prioritization, cycle_id, dataset_catalog, *, budget=None, author="research-director-rules",
               created_at=None):
    """dataset_catalog: data_needed id -> {dataset_id, split, period, real_data, estimated_seconds,
    expected_events, requires_authorization}. Declared by the caller; nothing is fetched."""
    budget = dict(DEFAULT_CYCLE_BUDGET, **(budget or {}))
    out = {"planned": [], "rejected_by_review": [], "skipped": [], "budget": budget}
    per_family = {}
    tested = [(e["body"]["hypothesis_id"], d["dataset_id"], d["split"]) for e in memory.of_type("EXPERIMENT")
              for d in e["body"]["datasets"] if e["body"]["status"] != "NOT_RUN"]
    for entry in prioritization["ranked"]:
        if len(out["planned"]) >= budget["max_plans"]:
            out["skipped"].append({"record_id": entry["record_id"], "reason": "cycle budget reached"})
            continue
        hyp = memory.current(entry["record_id"])
        fam = hyp["family"]
        if per_family.get(fam, 0) >= budget["max_plans_per_family"]:
            out["skipped"].append({"record_id": hyp["record_id"], "reason": f"family {fam} cycle budget reached"})
            continue
        needed = [dataset_catalog[d] for d in hyp["body"]["data_needed"] if d in dataset_catalog]
        if not needed:
            out["skipped"].append({"record_id": hyp["record_id"], "reason": "no dataset declared in the catalog"})
            continue
        ds_info = needed[0]
        dataset = {"dataset_id": ds_info["dataset_id"], "split": ds_info["split"],
                   "period": ds_info.get("period", "unknown"), "exposure": ds_info.get("exposure", "UNSEEN")}
        key = equivalence_key(hyp, dataset)
        pid = f"PLAN-{key[:16].upper()}"
        if memory.get(pid):
            out["skipped"].append({"record_id": hyp["record_id"],
                                   "reason": f"already planned as {pid} ({memory.get(pid)['body']['status']})"})
            continue
        if (hyp["body"]["hypothesis_id"], dataset["dataset_id"], dataset["split"]) in tested:
            out["skipped"].append({"record_id": hyp["record_id"], "reason": "already executed on this dataset/split"})
            continue
        twin = next((p["body"]["hypothesis_record"] for p in memory.of_type("EXPERIMENT_PLAN")
                     if p["body"]["dataset"]["dataset_id"] == dataset["dataset_id"]
                     and near_equivalent(memory.get(p["body"]["hypothesis_record"])["body"]["signature"],
                                         hyp["body"]["signature"])), None)
        if twin:
            out["skipped"].append({"record_id": hyp["record_id"], "reason": f"substantially equivalent to {twin}"})
            continue

        learned, res = learned_underpowered(memory, dataset["dataset_id"], ds_info.get("expected_events"))
        if learned:
            out["skipped"].append({"record_id": hyp["record_id"],
                                   "reason": f"learned from {learned}: {dataset['dataset_id']} gives "
                                             f"{res['expected_events']} events, {res['n_needed_for_80pct_power']} "
                                             "needed; extend the period or revise the expected effect first"})
            continue
        checks, alpha, cap = overfitting.check_plan(memory, hyp["record_id"], dataset)
        review = statistical_review(hyp, checks, alpha, cap, ds_info.get("expected_events"))
        params = {"hypothesis_signature_sha256": hyp["body"]["signature_sha256"], "dataset": dataset}
        actions = [
            {"kind": "DEDUP_CHECK", "params": {"equivalence_key": key}},
            {"kind": "SYNTHETIC_DRY_RUN", "params": {"alpha": alpha, "expected_events": ds_info.get("expected_events"),
                                                     "rows": 20_000, "estimated_seconds": 2, "seed": key[:8]}},
            {"kind": "RUN_EXPERIMENT_REAL_DATA",
             "params": dict(params, real_data=bool(ds_info.get("real_data", True)),
                            estimated_seconds=ds_info.get("estimated_seconds", 0),
                            requires_authorization=bool(ds_info.get("requires_authorization")),
                            description=f"run {hyp['body']['hypothesis_id']} on {dataset['dataset_id']}")},
        ]
        body = {"cycle_id": cycle_id, "hypothesis_record": hyp["record_id"], "equivalence_key": key,
                "dataset": dataset, "evidence_target": cap,
                "decision_rule": f"reject H0 only if the preregistered primary outcome beats its control at "
                                 f"alpha {alpha:.5f} with at least {MIN_CLOSED_FOR_FIRST_READ} closed events; "
                                 f"otherwise INCONCLUSIVE or NEGATIVE, never re-tuned on the same data",
                "falsification": hyp["body"]["falsification"], "alpha": alpha,
                "min_sample": MIN_CLOSED_FOR_FIRST_READ,
                "compute_estimate": {"seconds": ds_info.get("estimated_seconds"),
                                     "expected_events": ds_info.get("expected_events")},
                "overfitting_checks": checks, "statistical_review": review,
                "status": "DRAFT_PREREGISTRATION" if review["verdict"] == "PASS" else "REJECTED_BY_REVIEW",
                "actions": actions if review["verdict"] == "PASS" else []}
        memory.append("EXPERIMENT_PLAN", pid, body, author=author, origin="RULE_ENGINE",
                      project=hyp["project"], family=fam, created_at=created_at,
                      provenance=[{"kind": "RECORD", "ref": hyp["record_id"], "sha256": hyp["record_hash"]}],
                      relations=[{"type": "TESTS", "target": hyp["record_id"]}])
        if review["verdict"] == "PASS":
            out["planned"].append(pid)
            per_family[fam] = per_family.get(fam, 0) + 1
        else:
            out["rejected_by_review"].append({"plan": pid, "issues": review["issues"]})
    return out
