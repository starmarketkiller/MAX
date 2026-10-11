"""Improvement proposal registry: decisions are new records, made by a human.

A proposal is written once as PROPOSED (review.py). Accepting, rejecting,
marking implemented or reverting appends a new IMPROVEMENT_PROPOSAL record
that SUPERSEDES the previous state; the earlier state stays readable, so the
history of every improvement can be replayed and undone.
"""
from __future__ import annotations

import copy

from . import gates

TRANSITIONS = {"PROPOSED": {"ACCEPTED", "REJECTED"}, "ACCEPTED": {"IMPLEMENTED", "REJECTED"},
               "IMPLEMENTED": {"REVERTED"}, "REJECTED": set(), "REVERTED": set()}


def open_proposals(memory, family=None):
    out = []
    for p in memory.of_type("IMPROVEMENT_PROPOSAL"):
        cur = memory.current(p["record_id"])
        if cur["record_id"] == p["record_id"] and cur["body"]["status"] in ("PROPOSED", "ACCEPTED") \
                and (family is None or p["family"] == family):
            out.append(cur)
    return out


def decide(memory, proposal_id, new_status, *, decided_by, note, created_at=None):
    gates.assert_decision_by_human(decided_by)
    cur = memory.current(proposal_id)
    if cur is None or cur["record_type"] != "IMPROVEMENT_PROPOSAL":
        raise ValueError(f"{proposal_id} is not a proposal")
    old = cur["body"]["status"]
    if new_status not in TRANSITIONS[old]:
        raise gates.GateViolation(f"{old} -> {new_status} is not an allowed transition")
    body = copy.deepcopy(cur["body"])
    body.update(status=new_status, decided_by=decided_by)
    body["rationale"] = f"{body['rationale']} | {new_status} by {decided_by}: {note}"
    n = sum(1 for r in memory.records if r["record_id"].startswith(proposal_id + ".D"))
    return memory.append("IMPROVEMENT_PROPOSAL", f"{proposal_id}.D{n + 1}", body, author=decided_by,
                         origin="HUMAN", project=cur["project"], family=cur["family"],
                         provenance=[{"kind": "RECORD", "ref": cur["record_id"], "sha256": cur["record_hash"]}],
                         relations=[{"type": "SUPERSEDES", "target": cur["record_id"]}], created_at=created_at)
