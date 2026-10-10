"""Cross-user/cross-tenant approval decisions fail closed for every task type."""
from datetime import datetime, timezone

from jarvis_v1.authenticated_scope import AuthenticatedScope
from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService
from jarvis_v1.task_authorization import authorize_task_decision


def _manifest(task_id, *, created_by="jarvis:42", tenant_id="tenant-1"):
    return {
        "task_id": task_id, "title": "authorization", "objective": "verify owner",
        "task_type": "RESEARCH", "priority": "NORMAL", "risk_level": "A0",
        "scientific_risk": "NONE", "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": ["text_generation"], "deterministic_tools_available": False,
        "repo_scope": "", "files_allowed": [], "files_forbidden": [], "dependencies": [],
        "blockers": [], "expected_artifacts": [], "success_criteria": ["authorized"],
        "verifier": "manual", "estimated_complexity": "TRIVIAL", "estimated_runtime": "1m",
        "premium_allowed": False, "preferred_executor": "TIER1_LOCAL_CHEAP",
        "fallback_executors": [], "approval_required": "REVIEW_REQUIRED",
        "created_by": created_by, "created_at": "2026-10-10T00:00:00Z",
        "tenant_id": tenant_id, "account_scope_id": None,
    }


def _message(task_id, *, user="42", action="APPROVE", channel="WEB"):
    return {
        "message_id": f"auth-{user}-{task_id}-{action}", "user_id": user,
        "channel": channel, "conversation_id": f"decision:{user}",
        "timestamp": datetime.now(timezone.utc).isoformat(), "input_type": "TEXT",
        "text": action, "attachments": [], "reply_to": None,
        "request_class": "APPROVAL", "priority": "HIGH",
        "metadata": {"task_id": task_id, "approval_action": action},
    }


def _waiting(service, task_id, *, created_by="jarvis:42", tenant_id="tenant-1"):
    service.orchestrator.submit(_manifest(task_id, created_by=created_by, tenant_id=tenant_id),
                                action="authorization_test")
    service.queue.transition(task_id, "RUNNING")
    service.queue.transition(task_id, "WAITING_APPROVAL")
    return service.queue.get(task_id)


def test_owner_allowed_other_owner_and_tenant_denied(tmp_path):
    service = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"))
    gateway = JarvisGateway(service)
    _waiting(service, "TASK_OWNER")
    denied = gateway.handle(_message("TASK_OWNER", user="7"))
    assert denied["status"] == "FORBIDDEN"
    assert service.queue.get("TASK_OWNER")["state"] == "WAITING_APPROVAL"
    allowed = gateway.handle(_message("TASK_OWNER"))
    assert allowed["status"] == "QUEUED"

    _waiting(service, "TASK_TENANT", tenant_id="tenant-9")
    denied_tenant = gateway.handle(_message("TASK_TENANT"))
    assert denied_tenant["status"] == "FORBIDDEN"
    assert service.queue.get("TASK_TENANT")["state"] == "WAITING_APPROVAL"


def test_internal_and_ambiguous_legacy_tasks_have_no_implicit_admin(tmp_path):
    service = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"))
    gateway = JarvisGateway(service)
    for task_id, creator in (("TASK_INTERNAL", "revenue_agent"),
                             ("TASK_LEGACY", "test"), ("TASK_AMBIGUOUS", "unknown_creator")):
        _waiting(service, task_id, created_by=creator)
        response = gateway.handle(_message(task_id, user="admin"))
        assert response["status"] == "FORBIDDEN"
        assert service.queue.get(task_id)["state"] == "WAITING_APPROVAL"


def test_multistage_child_inherits_verified_parent_owner(tmp_path):
    service = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"))
    _waiting(service, "TASK_PARENT")
    child = _waiting(service, "TASK_CHILD", created_by="multi_stage:TASK_PARENT")
    owner = AuthenticatedScope("42", "jarvis:42", "tenant-1")
    stranger = AuthenticatedScope("7", "jarvis:7", "tenant-1")
    assert authorize_task_decision(service.queue, child, owner).code == "TASK_PARENT_OWNER_MATCH"
    assert authorize_task_decision(service.queue, child, stranger).allowed is False
    approved = JarvisGateway(service).handle(_message("TASK_CHILD", channel="TELEGRAM"))
    assert approved["status"] == "QUEUED"


def test_fake_or_missing_parent_delegation_is_rejected(tmp_path):
    service = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"))
    gateway = JarvisGateway(service)
    _waiting(service, "TASK_FAKE_CHILD", created_by="multi_stage:TASK_MISSING")
    assert gateway.handle(_message("TASK_FAKE_CHILD"))["status"] == "FORBIDDEN"
    assert service.queue.get("TASK_FAKE_CHILD")["state"] == "WAITING_APPROVAL"
