"""AGENCY_AUTOMATION_POLICY_V1: what the Agency may do alone.

Every irreversible or money/identity-bearing action passes through
`require_approval`, which is fail-closed.  Actions with no live
implementation in NEXUS (publish, sponsor, outreach, payments) are
additionally hard-disabled: approval alone cannot trigger them from code.
"""
from __future__ import annotations

AUTONOMOUS_ACTIONS = frozenset({
    "SCOUT", "DEDUPLICATE", "CLASSIFY", "CREATE_BRIEF", "ASSIGN_MODEL",
    "PREPARE_GENERATION_PACK", "COMPLIANCE_CHECK", "REPORT", "DRAFT_SOCIAL_POST",
    "PROPOSE_LISTING",
})
APPROVAL_REQUIRED_ACTIONS = frozenset({
    "SPEND_CREDITS", "CREATE_PAID_ASSET", "PUT_PRODUCT_ONLINE", "SCHEDULE_POST",
    "PUBLISH", "SPONSOR", "CONTACT_BRAND", "ACCEPT_AGREEMENT", "MAKE_PAYMENT",
    "CREATE_SOCIAL_ACCOUNT",
})
# No code path performs these in V2, approval or not.
HARD_DISABLED_ACTIONS = frozenset({"PUBLISH", "SPONSOR", "CONTACT_BRAND",
                                   "ACCEPT_AGREEMENT", "MAKE_PAYMENT"})


class ApprovalRequired(PermissionError):
    pass


def require_approval(action, approved_by):
    if action in AUTONOMOUS_ACTIONS:
        return {"action": action, "mode": "AUTONOMOUS"}
    if action not in APPROVAL_REQUIRED_ACTIONS:
        raise ApprovalRequired(f"unknown action {action}: fail-closed")
    if action in HARD_DISABLED_ACTIONS:
        raise ApprovalRequired(f"{action} is disabled in Agency V2")
    if not approved_by or not str(approved_by).strip():
        raise ApprovalRequired(f"{action} requires explicit human approval")
    return {"action": action, "mode": "APPROVED", "approved_by": approved_by}


def policy_snapshot():
    return {"schema_version": "AGENCY_AUTOMATION_POLICY_V1",
            "autonomous": sorted(AUTONOMOUS_ACTIONS),
            "approval_required": sorted(APPROVAL_REQUIRED_ACTIONS),
            "hard_disabled": sorted(HARD_DISABLED_ACTIONS)}
