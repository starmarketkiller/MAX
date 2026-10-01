from datetime import datetime, timezone

import pytest

from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.programming import build_plan, is_programming_request
from jarvis_v1.service import JarvisService, classify
from orchestrator_v1.core.provider_policy import ProviderPolicyRegistryV1


def message(text, conversation="programming-1", metadata=None):
    return {"message_id": f"m-{abs(hash(text))}", "user_id": "42", "channel": "TEST",
            "conversation_id": conversation, "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_type": "TEXT", "text": text, "attachments": [], "reply_to": None,
            "request_class": "UNKNOWN", "priority": "NORMAL", "metadata": metadata or {}}


@pytest.fixture
def service(tmp_path, monkeypatch):
    svc = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"),
                        str(tmp_path / "conversations.json"))
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    return svc


def test_intent_policy_and_least_privilege_defaults():
    assert is_programming_request("sistema il bug nel repo")
    assert classify("sistema il bug e fai i test") == "TASK_REQUEST"
    plan = build_plan("Sistema il bug e fai i test")
    assert plan["intent"] == "PATCH"
    assert {"NO_PUSH", "NO_DEPLOY"} <= set(plan["policy_flags"])
    assert "PATCH_WORKSPACE" in plan["capability_scope"]["allowed_operations"]
    assert "PUSH" in plan["capability_scope"]["denied_operations"]
    assert next(s for s in plan["stages"] if s["name"] == "PUSH")["enabled"] is False


def test_test_only_and_commit_only_are_enforced():
    test_plan = build_plan("Test only: verifica il fix")
    assert {"TEST_ONLY", "NO_PUSH"} <= set(test_plan["policy_flags"])
    assert "PATCH_WORKSPACE" not in test_plan["capability_scope"]["allowed_operations"]
    commit_plan = build_plan("Fai il fix, solo commit e non pushare")
    assert {"COMMIT_ONLY", "NO_PUSH"} <= set(commit_plan["policy_flags"])
    assert "COMMIT" in commit_plan["capability_scope"]["allowed_operations"]
    assert "PUSH" not in commit_plan["capability_scope"]["allowed_operations"]


def test_reference_resolution_and_push_requires_explicit_approval():
    plan = build_plan("Pushalo", last_task_id="TASK_PREVIOUS")
    assert plan["reference"] == {"task_id": "TASK_PREVIOUS",
                                 "resolution": "CONVERSATION_CONTEXT"}
    assert plan["approval_required"] == "EXPLICIT_USER_APPROVAL"
    push = next(s for s in plan["stages"] if s["name"] == "PUSH")
    assert push["enabled"] is True and push["requires_approval"] is True
    deploy = next(s for s in plan["stages"] if s["name"] == "DEPLOY_VIA_SAFE_AUTO_DEPLOY")
    assert deploy["enabled"] is False and deploy["requires_approval"] is True


def test_push_request_stops_at_real_approval_gate(service):
    first = JarvisGateway(service).handle(message("Implementa un fix e fai i test"))
    push = JarvisGateway(service).handle(message("Pushalo"))
    record = service.queue.get(push["task_id"])
    assert record["state"] == "WAITING_APPROVAL"
    assert record["action_params"]["execution_plan"]["reference"]["task_id"] == first["task_id"]
    assert any(event["event_type"] == "APPROVAL_REQUIRED"
               for event in service.ledger.read_for_task(push["task_id"]))


def test_service_submits_plan_to_queue_without_selecting_executor(service):
    response = JarvisGateway(service).handle(message(
        "Implementa il fix nei file server/jarvis_v1 e fai i test",
        metadata={"files_allowed": ["server/jarvis_v1/**", "server/tests/**"]}))
    record = service.queue.get(response["task_id"])
    plan = record["action_params"]["execution_plan"]
    assert record["action"] == "conversational_programming"
    assert record["manifest"]["task_type"] == "CODE"
    assert record["manifest"]["work_type"] == "complex_code"
    assert record["manifest"]["files_allowed"] == ["server/jarvis_v1/**", "server/tests/**"]
    assert record["executor"] is None
    assert plan["capability_scope"]["allowed_paths"] == record["manifest"]["files_allowed"]
    assert any(event["event_type"] == "TASK_CREATED"
               for event in service.ledger.read_for_task(response["task_id"]))


def test_resume_uses_durable_conversation_context(service):
    first = JarvisGateway(service).handle(message("Implementa un fix e fai i test"))
    resumed = JarvisGateway(service).handle(message("Riprendi quello", conversation="programming-1"))
    plan = service.queue.get(resumed["task_id"])["action_params"]["execution_plan"]
    assert plan["intent"] == "RESUME"
    assert plan["reference"]["task_id"] == first["task_id"]


def test_route_preview_is_local_free_premium_order_and_does_not_execute(service):
    response = JarvisGateway(service).handle(message("Implementa un refactor complesso nel codice"))
    manifest = service.queue.get(response["task_id"])["manifest"]
    preview = ProviderPolicyRegistryV1().route_preview(manifest)
    assert preview["dry_run"] is True and preview["provider_calls"] == 0
    assert preview["policy"]["routing_order"] == ["DETERMINISTIC", "LOCAL", "FREE_ONLINE", "PREMIUM"]
    assert all(candidate["eligible_for_execution"] is False
               for candidate in preview["evaluation_candidates"])
    assert any(candidate["provider_id"] == "CODEX_OPENAI"
               for candidate in preview["premium_fallback"])
