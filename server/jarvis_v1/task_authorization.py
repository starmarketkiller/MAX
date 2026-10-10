"""Fail-closed authorization for user decisions on Jarvis tasks.

Ownership is server-derived.  Client metadata, conversation ids and action
parameters are never treated as authority.  A multi-stage child inherits the
verified owner of its parent; all other service/internal and ambiguous legacy
identities require an explicit future delegation contract.
"""
from __future__ import annotations

from dataclasses import dataclass

from .authenticated_scope import AuthenticatedScope


@dataclass(frozen=True)
class DecisionAuthorization:
    allowed: bool
    code: str
    owner_task_id: str | None = None


def authorize_task_decision(queue, record: dict, scope: AuthenticatedScope,
                            *, _visited: frozenset[str] = frozenset()) -> DecisionAuthorization:
    """Authorize an authenticated user to approve/reject ``record``.

    The only supported delegation in V1 is the structural multi-stage parent
    relationship written by the canonical executor.  It is deliberately
    encoded in ``created_by`` and checked against an existing parent record;
    arbitrary client-provided parent ids do not grant authority.
    """
    task_id = str(record.get("task_id") or "")
    if not task_id or task_id in _visited:
        return DecisionAuthorization(False, "TASK_OWNERSHIP_CYCLE")
    manifest = record.get("manifest") or {}
    if manifest.get("tenant_id") != scope.tenant_id:
        return DecisionAuthorization(False, "TASK_TENANT_MISMATCH")
    created_by = str(manifest.get("created_by") or "")
    if created_by == scope.owner:
        return DecisionAuthorization(True, "TASK_OWNER_MATCH", task_id)
    prefix = "multi_stage:"
    if not created_by.startswith(prefix):
        return DecisionAuthorization(False, "TASK_OWNER_UNVERIFIED")
    parent_id = created_by[len(prefix):]
    if not parent_id or parent_id == task_id:
        return DecisionAuthorization(False, "TASK_PARENT_INVALID")
    try:
        parent = queue.get(parent_id)
    except KeyError:
        return DecisionAuthorization(False, "TASK_PARENT_NOT_FOUND")
    parent_auth = authorize_task_decision(
        queue, parent, scope, _visited=_visited | {task_id})
    if not parent_auth.allowed:
        return parent_auth
    return DecisionAuthorization(True, "TASK_PARENT_OWNER_MATCH",
                                 parent_auth.owner_task_id or parent_id)


def authorized_decision_records(queue, records: list[dict], scope: AuthenticatedScope) -> list[dict]:
    """Return only tasks on which ``scope`` may make a decision."""
    return [record for record in records
            if authorize_task_decision(queue, record, scope).allowed]
