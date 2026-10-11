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
    if EVIDENCE_ORDER.index(evidence_level) < EVIDENCE_ORDER.index("INTERNAL_VALIDATION"):
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
