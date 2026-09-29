#!/usr/bin/env python3
"""NEXUS TASK #0008 punto 17 - la confidence finale non e' MAI
auto-dichiarata da un producer/reviewer: deriva solo da segnali esterni
osservabili (verifier, review status, qualita' delle fonti, validita' dello
schema, risultati dei test, limitazioni irrisolte)."""

_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "UNKNOWN": -1}
_BAD_REVIEW_DECISIONS = ("REJECT", "INSUFFICIENT_EVIDENCE")
_OK_REVIEW_DECISIONS = ("APPROVE", "APPROVE_WITH_MINOR_FIXES", None)


def derive_confidence(*, verifier_passed, schema_valid, review_decision=None,
                     source_quality="UNKNOWN", tests_all_passed=True,
                     unresolved_limitations=None):
    unresolved_limitations = unresolved_limitations or []

    if verifier_passed is not True or schema_valid is not True:
        return "LOW"
    if review_decision in _BAD_REVIEW_DECISIONS:
        return "LOW"
    if review_decision == "REVISION_REQUIRED":
        return "LOW"
    if not tests_all_passed:
        return "LOW"

    level = "HIGH"
    if source_quality in ("LOW", "UNKNOWN"):
        level = "MEDIUM"
    if unresolved_limitations:
        level = "MEDIUM"
    if review_decision not in _OK_REVIEW_DECISIONS and review_decision is not None:
        level = "MEDIUM"

    return level
