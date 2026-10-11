"""Scientific safety gates. Each raises GateViolation; nothing here applies changes.

Reuses phase7/policies/validation_access_policy_v1.json for protected splits and
the phase7_26 lifecycle vocabulary for promotion.
"""
from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
POLICY = os.path.join(HERE, "..", "phase7", "policies", "validation_access_policy_v1.json")
EVIDENCE_ORDER = ["NONE_PROPOSAL", "EXPLORATORY", "DISCOVERY_ONLY", "MECHANICAL_VERIFICATION",
                  "INTERNAL_VALIDATION", "LOCKED_VALIDATION", "INDEPENDENT_FORWARD"]
LIVE_MARKERS = re.compile(r"(MQL5/|NEXUS_EA|\.mq5|\.mqh|live|LIVE|risk_percent|RiskPercent|lot size|"
                          r"InpLive|order_send|OrderSend|deploy)")
MAX_PROPOSALS_PER_REVIEW = 10


class GateViolation(Exception):
    pass


def protected_splits():
    with open(POLICY, encoding="utf-8") as handle:
        policy = json.load(handle)
    return {name for name, rule in policy["splits"].items() if rule["access_mode"] == "ONE_SHOT"}


def assert_no_automatic_protected_access(split):
    if split in protected_splits():
        raise GateViolation(f"'{split}' is a one-shot split: never read automatically, only by an explicit, "
                            "ledgered human decision")


def assert_params_frozen(declared_sha256, proposed_params_sha256):
    if declared_sha256 != proposed_params_sha256:
        raise GateViolation("frozen parameters differ: a parameter change is a NEW_HYPOTHESIS with a new id")


def assert_promotion_allowed(target_state, evidence_level):
    if target_state != "SUPPORTED":
        return
    # MECHANICAL_VERIFICATION supports claims about code or data (exact counts, source reading),
    # never a market edge: phase7_26 marks those with mechanical_verification_exception.
    if evidence_level != "MECHANICAL_VERIFICATION" and \
            EVIDENCE_ORDER.index(evidence_level) < EVIDENCE_ORDER.index("INTERNAL_VALIDATION"):
        raise GateViolation(f"SUPPORTED needs at least INTERNAL_VALIDATION evidence, not {evidence_level}: "
                            "no promotion on discovery alone")


def check_proposal(body):
    """Every proposal must be reversible, bounded and never self-applied to live or frozen assets."""
    if not body["reversible"] or not body["revert_plan"].strip():
        raise GateViolation("a proposal without a revert plan cannot be registered")
    text = " ".join([body["title"], body["rationale"], *body["steps"]])
    if LIVE_MARKERS.search(text) and not body["touches_frozen_or_live"]:
        raise GateViolation("proposal mentions live/EA/risk assets but is not flagged touches_frozen_or_live")
    if body["touches_frozen_or_live"] and "HUMAN_APPROVAL" not in body["requires"]:
        raise GateViolation("live or frozen assets need HUMAN_APPROVAL")
    if body["proposal_class"] == "NEW_HYPOTHESIS" and "NEW_PREREGISTRATION" not in body["requires"]:
        raise GateViolation("NEW_HYPOTHESIS requires NEW_PREREGISTRATION")
    if body["proposal_class"] == "DEFECT_FIX" and not {"DETERMINISTIC_REPRODUCTION", "REGRESSION_TEST",
                                                       "IMPACT_ANALYSIS"} <= set(body["requires"]):
        raise GateViolation("DEFECT_FIX requires reproduction, regression test and impact analysis")
    if body["proposal_class"] == "PROCESS_IMPROVEMENT" and "method" in body["title"].lower() \
            and "DEDICATED_METHOD_TEST" not in body["requires"]:
        raise GateViolation("a methodology change must be validated on a dedicated test, not on protected results")
    if body["status"] not in ("PROPOSED",):
        raise GateViolation("proposals are registered as PROPOSED; decisions are new records by a human")


def assert_decision_by_human(decided_by):
    if not decided_by or decided_by.lower().startswith(("rule", "ai", "jarvis", "auto")):
        raise GateViolation("accepting, rejecting or implementing a proposal is a human decision")


def negative_evidence_preserved(before_records, after_records):
    """No NEGATIVE/REJECTED record may disappear or change between two snapshots."""
    def negatives(records):
        return {r["record_id"]: r["record_hash"] for r in records
                if r["body"].get("result") == "NEGATIVE" or r["body"].get("lifecycle_state") == "REJECTED"}
    before, after = negatives(before_records), negatives(after_records)
    lost = [rid for rid, h in before.items() if after.get(rid) != h]
    if lost:
        raise GateViolation(f"negative evidence removed or altered: {lost}")
    return True


GENERATED = ("RULE_ENGINE", "AI_PROPOSAL")
DECIDED = ("ACCEPTED", "REJECTED", "IMPLEMENTED", "REVERTED")


def _supersedes(record):
    return [r["target"] for r in record["relations"] if r["type"] == "SUPERSEDES"]


def check_record(prior_records, by_id, record):
    """Invariants enforced on every append and replayed by verify(), so no write path
    (register, review, decide, or a raw append) can bypass the gates."""
    rtype, origin, body = record["record_type"], record["origin"], record["body"]
    if rtype == "HYPOTHESIS":
        if origin in GENERATED and (body["lifecycle_state"] not in ("OBSERVATION", "HYPOTHESIS")
                                    or body["evidence_level"] != "NONE_PROPOSAL" or not body["is_proposal_only"]):
            raise GateViolation("a generated hypothesis is a proposal: lifecycle HYPOTHESIS, evidence NONE_PROPOSAL")
        if body["lifecycle_state"] == "SUPPORTED":
            assert_promotion_allowed("SUPPORTED", body["evidence_level"])
        olds = [by_id[t] for t in _supersedes(record) if by_id[t]["record_type"] == "HYPOTHESIS"]
        for old in olds:
            if old["body"]["signature_sha256"] != body["signature_sha256"]:
                raise GateViolation("a hypothesis with different conditions is a new hypothesis id, not a revision")
            if old["body"]["lifecycle_state"] != body["lifecycle_state"] and origin != "HUMAN":
                raise GateViolation("lifecycle changes are human decisions")
        if not olds and any(r["record_type"] == "HYPOTHESIS" and r["body"]["signature_sha256"] ==
                            body["signature_sha256"] for r in prior_records):
            raise GateViolation("duplicate hypothesis signature")
    elif rtype == "IMPROVEMENT_PROPOSAL":
        if body["status"] == "PROPOSED":
            check_proposal(body)
        else:
            if origin != "HUMAN":
                raise GateViolation("only a person decides a proposal")
            assert_decision_by_human(body.get("decided_by", ""))
            if not any(by_id[t]["record_type"] == "IMPROVEMENT_PROPOSAL" for t in _supersedes(record)):
                raise GateViolation("a decision must supersede the proposal it decides")
    elif rtype in ("ACTION", "EXPERIMENT_PLAN", "IMPROVEMENT_TRIAL"):
        check_loop_record(prior_records, by_id, record)
    elif rtype == "EXPERIMENT":
        if origin != "HUMAN":
            for ds in body["datasets"]:
                if ds["split"] in protected_splits():
                    raise GateViolation(f"'{ds['split']}' can only be recorded by a human, ledgered decision")
        m = body["method"]
        if m["preregistered"] and m["params_sha256"] not in ("UNKNOWN", ""):
            for r in prior_records:
                pm = r["body"].get("method") if r["record_type"] == "EXPERIMENT" else None
                if pm and pm["preregistered"] and r["body"]["hypothesis_id"] == body["hypothesis_id"] \
                        and pm["params_sha256"] not in ("UNKNOWN", "") and pm["params_sha256"] != m["params_sha256"]:
                    raise GateViolation(f"frozen parameters of {body['hypothesis_id']} differ from {r['record_id']}: "
                                        "a parameter change needs a new hypothesis id")


def check_loop_record(prior_records, by_id, record):
    """Invariants for RI-02 loop records (called from check_record)."""
    rtype, body = record["record_type"], record["body"]
    if rtype == "ACTION":
        from . import authorization  # local import: authorization imports gates
        from .memory import canonical, sha256_text
        if sha256_text(canonical(body["params"])) != body["params_sha256"]:
            raise GateViolation("action params do not match params_sha256")
        mode, _ = authorization.classify(body["kind"], body["params"])
        if mode != body["mode"]:
            raise GateViolation(f"action {body['kind']} recorded as {body['mode']} but classifies as {mode}")
        allowed = {"EXECUTED": {"AUTO_SAFE"}, "FAILED": {"AUTO_SAFE"},
                   "AWAITING_APPROVAL": {"APPROVAL_REQUIRED"},
                   "REFUSED": {"PROHIBITED", "APPROVAL_REQUIRED", "AUTO_SAFE"}}[body["status"]]
        if mode not in allowed:
            raise GateViolation(f"a {mode} action cannot be {body['status']}")
        if body["status"] == "AWAITING_APPROVAL" and not body.get("orchestrator_task_id"):
            raise GateViolation("an approval request must name its orchestrator task")
    elif rtype == "EXPERIMENT_PLAN":
        if body["dataset"]["split"] in protected_splits():
            raise GateViolation("a plan never targets a one-shot split")
        if body["status"] == "DRAFT_PREREGISTRATION":
            if body["statistical_review"].get("verdict") != "PASS" or \
                    any(c["status"] == "BLOCK" for c in body["overfitting_checks"]):
                raise GateViolation("a draft preregistration needs a passing statistical review")
        if EVIDENCE_ORDER.index(body["evidence_target"]) > EVIDENCE_ORDER.index("INDEPENDENT_FORWARD") or \
                (body["dataset"]["split"] == "discovery" and body["evidence_target"] != "DISCOVERY_ONLY"):
            raise GateViolation("evidence target above what the split allows")
    elif rtype == "IMPROVEMENT_TRIAL" and body["phase"] == "RESULT":
        if not any(r["type"] == "DERIVED_FROM" and by_id.get(r["target"], {}).get("record_type") ==
                   "IMPROVEMENT_TRIAL" for r in record["relations"]):
            raise GateViolation("a trial result must point at its baseline")
