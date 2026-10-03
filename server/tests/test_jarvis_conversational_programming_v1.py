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


def test_negated_push_phrasings_do_not_trigger_premature_approval():
    # NEXUS bugfix 2026-10-02: "non fare push" (and natural variants) were
    # classified intent="PUSH" by the bare \bpush\b check, which also meant
    # _flags() never added NO_PUSH (its fallback only fires when intent !=
    # "PUSH") - a LOW_RISK, test-only, no-push task was sent straight to
    # WAITING_APPROVAL (EXPLICIT_USER_APPROVAL) before Router/Dispatcher/
    # local worker ever ran. Reproduced against the real E2E message.
    for phrase in ("non fare push", "niente push", "no push", "senza fare push",
                  "non pushare", "senza push"):
        plan = build_plan(f"Modifica il file server/tests/test_x.py, {phrase}, non fare deploy")
        assert plan["intent"] != "PUSH", phrase
        assert "NO_PUSH" in plan["policy_flags"], phrase
        assert plan["approval_required"] == "REVIEW_REQUIRED", phrase

    real_message = (
        "Avvia una task di programmazione locale.\n"
        "Modifica solo un file di test innocuo scelto da te, fai una modifica minima e "
        "reversibile, esegui solo i test consentiti, non usare provider premium, non fare "
        "push, non fare deploy e fermati a WAITING_APPROVAL.\n"
        "Usa il Local Agent Bridge e il worker locale.\n"
        "Se qualcosa non e' disponibile, fermati e spiegami il blocker senza usare premium.")
    plan = build_plan(real_message)
    assert plan["intent"] == "PATCH"
    assert "NO_PUSH" in plan["policy_flags"]
    assert plan["approval_required"] == "REVIEW_REQUIRED"


def test_genuine_push_requests_still_require_explicit_approval():
    # The fix must not weaken the real push/high-risk gate.
    for phrase in ("Pushalo", "fai il push", "Implementa il fix e poi pushalo su main"):
        plan = build_plan(phrase, last_task_id="TASK_PREVIOUS" if phrase == "Pushalo" else None)
        assert plan["intent"] == "PUSH", phrase
        assert "NO_PUSH" not in plan["policy_flags"], phrase
        assert plan["approval_required"] == "EXPLICIT_USER_APPROVAL", phrase


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


def test_reject_on_coding_task_hands_off_to_specialist_review_when_wired(service):
    # Wiring test only - the routing/availability/rework logic itself is
    # covered end-to-end in test_dynamic_specialist_review_v1.py. This
    # confirms approval()'s REJECT branch actually calls the Core component
    # instead of the plain pre-existing queue.transition(task_id, "FAILED").
    created = JarvisGateway(service).handle(message("Implementa un fix e fai i test"))
    task_id = created["task_id"]
    assert service.queue.get(task_id)["action"] == "conversational_programming"
    service.queue.transition(task_id, "RUNNING")
    service.queue.transition(task_id, "WAITING_APPROVAL")

    calls = []
    class StubConnector:
        def request_review(self, task_id, reject_reason):
            calls.append((task_id, reject_reason))
    service.set_provider_connector(StubConnector())

    response = JarvisGateway(service).handle(message("REJECT", "approval", metadata={
        "task_id": task_id, "approval_action": "REJECT"}))
    assert calls == [(task_id, "human rejected the proposed patch")]
    # The stub never calls queue.transition itself - state is untouched here
    # (ProviderConnectorV1.request_review owns that in the real flow).
    assert service.queue.get(task_id)["state"] == "WAITING_APPROVAL"


def test_reject_without_wired_connector_keeps_old_failed_behavior(service):
    created = JarvisGateway(service).handle(message("Implementa un fix e fai i test"))
    task_id = created["task_id"]
    service.queue.transition(task_id, "RUNNING")
    service.queue.transition(task_id, "WAITING_APPROVAL")
    assert service.provider_connector is None  # default, matches every pre-existing test
    rejected = JarvisGateway(service).handle(message("REJECT", "approval", metadata={
        "task_id": task_id, "approval_action": "REJECT"}))
    assert rejected["status"] == "FAILED"


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
