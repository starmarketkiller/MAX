"""Hypothesis registration with deterministic deduplication.

The signature is phase7/engine/candidate_signature.canonical_signature (no
semantic or AI matching, by design): same event family, direction, state
conditions and outcome definition = same hypothesis, whatever the wording,
casing, order or number format.

A hypothesis written by a rule or a model is a PROPOSAL: evidence level
NONE_PROPOSAL and lifecycle HYPOTHESIS, until a pre-registered experiment
says otherwise.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase7", "engine"))
from candidate_signature import canonical_signature, signature_hash  # noqa: E402

REQUIRED_DECLARATIONS = ("mechanism", "falsification", "data_needed", "overfitting_risk",
                         "expected_information_value")


class DuplicateHypothesis(Exception):
    def __init__(self, existing_id):
        super().__init__(f"same signature as {existing_id}")
        self.existing_id = existing_id


def signature_of(spec):
    sig = canonical_signature(spec["event_family"], spec["direction"], spec["state_conditions"],
                              spec["outcome_definition"])
    return sig, signature_hash(sig)


def register(memory, hypothesis_id, spec, *, statement, origin, author, project, family,
             lifecycle_state="HYPOTHESIS", evidence_level=None, provenance=(), relations=(),
             created_at=None, budget=None):
    """Append a HYPOTHESIS record, or raise DuplicateHypothesis without writing.

    `budget`, when given, is a FamilyBudget: proposals beyond the family's
    allowance are refused before they can inflate the multiple-testing family."""
    missing = [k for k in REQUIRED_DECLARATIONS if not spec.get(k)]
    if missing:
        raise ValueError(f"hypothesis {hypothesis_id} must declare {missing}")
    sig, sig_hash = signature_of(spec)
    existing = memory.hypothesis_signatures().get(sig_hash)
    if existing:
        raise DuplicateHypothesis(existing)
    proposal = origin in ("RULE_ENGINE", "AI_PROPOSAL")
    if proposal and lifecycle_state not in ("OBSERVATION", "HYPOTHESIS"):
        raise ValueError("a generated hypothesis cannot start beyond HYPOTHESIS")
    if budget is not None:
        budget.consume(family, hypothesis_id)
    body = {"hypothesis_id": hypothesis_id, "statement": statement, "version": spec.get("version", "1"),
            "lifecycle_state": lifecycle_state, "signature": sig, "signature_sha256": sig_hash,
            "mechanism": spec["mechanism"], "falsification": spec["falsification"],
            "data_needed": list(spec["data_needed"]), "overfitting_risk": spec["overfitting_risk"],
            "expected_information_value": spec["expected_information_value"],
            "evidence_level": "NONE_PROPOSAL" if proposal else (evidence_level or "NONE_PROPOSAL"),
            "is_proposal_only": proposal}
    return memory.append("HYPOTHESIS", f"HYP-{hypothesis_id}", body, author=author, origin=origin,
                         project=project, family=family, provenance=provenance, relations=relations,
                         created_at=created_at)


class FamilyBudget:
    """Attempts, variants and comparisons per family, so generation cannot grow
    the multiple-testing family without limit. Counts what is already in memory."""

    def __init__(self, memory, max_hypotheses_per_family=6):
        self.max = max_hypotheses_per_family
        self.used = {}
        for r in memory.of_type("HYPOTHESIS"):
            self.used.setdefault(r["family"], set()).add(r["body"]["hypothesis_id"])

    def remaining(self, family):
        return self.max - len(self.used.get(family, set()))

    def consume(self, family, hypothesis_id):
        if self.remaining(family) <= 0:
            raise BudgetExhausted(f"family {family}: {self.max} hypotheses already registered; "
                                  "a new one needs an explicit budget decision")
        self.used.setdefault(family, set()).add(hypothesis_id)


class BudgetExhausted(Exception):
    pass
