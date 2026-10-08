import json
from pathlib import Path

from jarvis_v1.local_operations import (
    CapabilityResolver, OperationsProjection, SkillRegistry,
    build_execution_plan, is_complex_mistral_request,
)
from jarvis_v1.service import JarvisService
from jarvis_v1.multi_stage_executor import MultiStageExecutor
from orchestrator_v1.core.local_agent_bridge import LocalAgentBridgeV1
from nxs_schema_validator import validate


class Store:
    def snapshot(self):
        return {"prospects": [{"prospect_id": "PROSPECT_1", "display_name": "Gabriele"}],
                "leads": [{"lead_id": "LEAD_1", "display_name": "Gabriele", "status": "QUALIFIED",
                           "source": "DECLARED", "updated_at": "2026-10-07T00:00:00+00:00"}]}


class Runner:
    running = False
    class Delivery:
        path = Path("does-not-exist")
    delivery = Delivery()


class Scheduler:
    def __init__(self, path):
        self.path = path
        path.write_text(json.dumps({"scheduled_keys": {
            "followup:LEAD_1:2026-10-08T00:00:00+00:00": {"task_id": "TASK_FOLLOW"}}}),
            encoding="utf-8")


class Portfolio:
    def snapshot(self):
        return {"ventures": [{"venture_id": "LEAD_RESEARCH_SERVICE", "name": "Lead Research",
                               "status": "READY_TO_TEST", "leads": 0, "sales": 0,
                               "revenue_eur": 0, "updated_at": "2026-10-07T00:00:00+00:00"}]}


def message(text):
    return {"message_id": "m1", "user_id": "u1", "channel": "TELEGRAM",
            "conversation_id": "c1", "timestamp": "2026-10-07T00:00:00+00:00",
            "input_type": "TEXT", "text": text, "attachments": [], "reply_to": None,
            "request_class": "UNKNOWN", "priority": "NORMAL", "metadata": {}}


def test_skill_registry_is_allowlisted_and_skill_is_not_permission(tmp_path):
    skill = tmp_path / ".claude/skills/mql5-engineering"
    skill.mkdir(parents=True)
    registry = SkillRegistry(tmp_path)
    agents = {"agents": [{"agent_id": "LOCAL", "availability": "ONLINE",
                           "capabilities": ["mql5_static_analysis"]}]}
    resolver = CapabilityResolver(agents, registry)
    denied = resolver.resolve("mql5_static_analysis", context="EA_MQL5_AUDIT_SERVICE",
                              authorized_capabilities=[])
    assert denied["authorization_result"] == "DENIED"
    assert denied["selected_skill"] is None
    allowed = resolver.resolve("mql5_static_analysis", context="EA_MQL5_AUDIT_SERVICE",
                               authorized_capabilities=["mql5_static_analysis"])
    assert allowed["selected_skill"] == "mql5-engineering"
    assert allowed["selected_agent"] == "LOCAL"


def test_complex_mistral_request_builds_bounded_async_plan():
    text = "analizza lo stato del sistema revenue e dimmi quali azioni concrete sono pronte oggi"
    assert is_complex_mistral_request(text)
    plan = build_execution_plan(text, authorized_capabilities=["summaries"])
    assert plan["schema_version"] == "MULTI_STAGE_EXECUTION_PLAN_V1"
    assert plan["steps"][0]["authorization_result"] == "AUTHORIZED"
    assert plan["steps"][1]["authorization_result"] == "DENIED"
    assert plan["task_total_budget_seconds"] > plan["sync_chat_budget_seconds"]
    schema = json.loads((Path(__file__).parents[2] / "contracts/multi-stage-execution-plan-v1.schema.json")
                        .read_text(encoding="utf-8"))
    assert validate(plan, schema) == []


def test_revenue_projection_is_read_only_and_exposes_real_state(tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    scheduler = Scheduler(tmp_path / "scheduler.json")
    projection = OperationsProjection(revenue_store=Store(), revenue_runner=Runner(),
                                      revenue_scheduler=scheduler, portfolio_registry=Portfolio(),
                                      queue=service.queue, ledger=service.ledger)
    status = projection.revenue(automation_enabled=False)
    assert status["revenue_runner_enabled"] is False
    assert status["leads_count"] == 1
    assert status["followups_due"] == 1
    assert status["ventures_ready_to_test"] == 1
    assert status["commercial_actions_enabled"] is False
    assert projection.find_contact("gabriele")[0]["display_name"] == "Gabriele"


def test_jarvis_revenue_commands_reuse_projection(tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    projection = OperationsProjection(revenue_store=Store(), revenue_runner=Runner(),
                                      revenue_scheduler=Scheduler(tmp_path / "scheduler.json"),
                                      portfolio_registry=Portfolio(), queue=service.queue,
                                      ledger=service.ledger)
    service.set_operations_projection(projection)
    revenue = service.handle(message("/revenue"))
    assert revenue["details"]["commercial_actions_enabled"] is False
    assert service.handle(message("/leads"))["details"]["count"] == 1
    assert service.handle(message("/lead Gabriele"))["details"]["items"][0]["display_name"] == "Gabriele"
    assert service.handle(message("/drafts"))["details"]["count"] == 0
    assert service.handle(message("/followups"))["details"]["count"] == 1
    venture = service.handle(message("/ventures"))["details"]["items"][0]
    assert venture["real_market_test_started"] is False


def test_long_mistral_request_is_async_and_persists_plan(tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    executor = MultiStageExecutor(service.orchestrator)
    service.set_multi_stage_executor(executor)
    response = service.handle(message(
        "/mistral analizza lo stato del sistema revenue e dimmi quali azioni concrete sono pronte oggi"))
    assert response["response_type"] == "TASK_ACK"
    assert "background" in response["summary"]
    record = service.queue.get(response["task_id"])
    assert record["state"] == "WAITING_PROVIDER"
    assert record["action"] == "multi_stage_operations_v1"
    assert record["multi_stage_execution"]["steps"]
    artifact_dir = Path(service.conversation_store.path).parent / "task_artifacts" / response["task_id"]
    assert (artifact_dir / "artifacts").is_dir()


def test_two_distinct_verified_steps_complete_sequentially(monkeypatch, tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    notifications = []
    executor = MultiStageExecutor(service.orchestrator, notification_sink=notifications.append)
    service.set_multi_stage_executor(executor)
    monkeypatch.setattr("core.ollama_worker.call_local_model", lambda *a, **k: {
        "success": True, "response_text": json.dumps({
            "summary": "Stato verificato.", "findings": ["Nessuna azione esterna."], "risks": []}),
        "error": None, "model": "ministral-3:3b", "wall_seconds": .1})
    response = service.handle(message(
        "/mistral analizza lo stato del sistema revenue e dimmi quali azioni concrete sono pronte oggi"))
    parent_id = response["task_id"]
    for _ in range(2):
        executor.run_once()
        parent = service.queue.get(parent_id)
        step = next(s for s in parent["multi_stage_execution"]["steps"]
                    if s["state"] == "RUNNING")
        service.orchestrator.process_task(step["child_task_id"])
        executor.run_once()
    parent = service.queue.get(parent_id)
    assert parent["state"] == "COMPLETED"
    assert [s["state"] for s in parent["multi_stage_execution"]["steps"]] == ["VERIFIED", "VERIFIED"]
    assert len({s["required_capability"] for s in parent["multi_stage_execution"]["steps"]}) == 2
    assert parent["result_packet"]["verifier"]["passed"] is True
    assert any(n["event_type"] == "TASK_COMPLETED" for n in notifications)


def test_unauthorized_step_blocks_without_execution(tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    executor = MultiStageExecutor(service.orchestrator)
    task_id = executor.submit(objective="analizza questo EA MQL5 in dettaglio usando skill autorizzate",
                              created_by="test", conversation_id="c", relevant_paths=[])
    executor.run_once()
    assert service.queue.get(task_id)["state"] == "BLOCKED"
    assert service.queue.get(task_id)["dispatch_last_error"] == "CAPABILITY_NOT_AUTHORIZED"


def test_parent_progress_survives_executor_restart(monkeypatch, tmp_path):
    queue_path, ledger_path = tmp_path / "queue.json", tmp_path / "ledger.jsonl"
    service = JarvisService(queue_path=queue_path, ledger_path=ledger_path,
                            conversation_path=tmp_path / "conversations.json")
    first = MultiStageExecutor(service.orchestrator)
    task_id = first.submit(objective="analizza revenue e prepara un riepilogo operativo completo",
                           created_by="test", conversation_id="c")
    first.run_once()
    before = service.queue.get(task_id)
    child_id = next(s["child_task_id"] for s in before["multi_stage_execution"]["steps"]
                    if s["state"] == "RUNNING")
    monkeypatch.setattr("core.ollama_worker.call_local_model", lambda *a, **k: {
        "success": True, "response_text": json.dumps({"summary": "ok", "findings": [], "risks": []}),
        "error": None, "model": "ministral-3:3b", "wall_seconds": .1})
    service.orchestrator.process_task(child_id)
    restarted = MultiStageExecutor(service.orchestrator)
    restarted.run_once()
    after = service.queue.get(task_id)
    assert after["multi_stage_execution"]["steps"][0]["state"] == "VERIFIED"
    assert after["multi_stage_execution"]["steps"][1]["child_task_id"].startswith("TASK_")


def test_child_waiting_approval_is_visible_on_parent(tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    executor = MultiStageExecutor(service.orchestrator)
    task_id = executor.submit(objective="analizza revenue e prepara un riepilogo operativo completo",
                              created_by="test", conversation_id="c")
    executor.run_once()
    parent = service.queue.get(task_id)
    child_id = next(s["child_task_id"] for s in parent["multi_stage_execution"]["steps"]
                    if s["state"] == "RUNNING")
    service.queue.transition(child_id, "RUNNING")
    service.queue.transition(child_id, "WAITING_APPROVAL")
    executor.run_once()
    parent = service.queue.get(task_id)
    assert parent["multi_stage_execution"]["steps"][0]["state"] == "WAITING_APPROVAL"
    assert parent["state"] == "WAITING_PROVIDER"


def _escalate_first_child(service, executor, parent_id, *, classification="LOCAL_BRIDGE_OFFLINE",
                          target="TIER3_CLAUDE"):
    executor.run_once()
    parent = service.queue.get(parent_id)
    child_id = next(s["child_task_id"] for s in parent["multi_stage_execution"]["steps"]
                    if s["state"] == "RUNNING")
    service.queue.transition(child_id, "RUNNING")
    service.queue.transition(child_id, "ESCALATION_REQUIRED",
                             escalation={"classification": classification, "target": target})
    return child_id


def test_wait_state_notification_is_persistent_and_poll_idempotent(tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    notifications = []
    executor = MultiStageExecutor(service.orchestrator, notification_sink=notifications.append)
    parent_id = executor.submit(objective="analizza revenue e produci due verifiche indipendenti",
                                created_by="test", conversation_id="c", premium_allowed=True)
    _escalate_first_child(service, executor, parent_id)
    for _ in range(100):
        executor.run_once()
    escalations = [item for item in notifications if item["event_type"] == "TASK_ESCALATED"]
    assert len(escalations) == 1
    assert escalations[0]["status"] == "WAITING_FOR_PREMIUM"
    ledger_events = [event for event in service.ledger.read_all()
                     if event["event_type"] == "TASK_ESCALATED" and event["task_id"] == parent_id]
    assert len(ledger_events) == 1

    restarted_notifications = []
    restarted = MultiStageExecutor(service.orchestrator,
                                   notification_sink=restarted_notifications.append)
    for _ in range(10):
        restarted.run_once()
    assert restarted_notifications == []


def test_local_resource_failure_is_waiting_context_without_false_premium(tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    notifications = []
    executor = MultiStageExecutor(service.orchestrator, notification_sink=notifications.append)
    parent_id = executor.submit(objective="analizza revenue e produci due verifiche indipendenti",
                                created_by="test", conversation_id="c", premium_allowed=False)
    _escalate_first_child(service, executor, parent_id)
    executor.run_once()
    parent = service.queue.get(parent_id)
    step = parent["multi_stage_execution"]["steps"][0]
    assert step["state"] == "WAITING_CONTEXT"
    assert step["wait_reason"]["classification"] == "LOCAL_BRIDGE_OFFLINE"
    assert step["wait_reason"]["premium_allowed"] is False
    assert notifications[-1]["status"] == "WAITING_CONTEXT"
    assert "Nessuna chiamata premium" in notifications[-1]["summary"]


def test_distinct_wait_transitions_each_notify_once(tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    notifications = []
    executor = MultiStageExecutor(service.orchestrator, notification_sink=notifications.append)
    parent_id = executor.submit(objective="analizza revenue e produci due verifiche indipendenti",
                                created_by="test", conversation_id="c", premium_allowed=True)
    child_id = _escalate_first_child(service, executor, parent_id)
    executor.run_once()
    service.queue.transition(child_id, "ESCALATION_REQUIRED",
                             escalation={"classification": "RATE_LIMITED", "target": "CODEX"})
    executor.run_once()
    escalations = [item for item in notifications if item["event_type"] == "TASK_ESCALATED"]
    assert len(escalations) == 2
    assert {item["details"]["reason"]["classification"] for item in escalations} == {
        "LOCAL_BRIDGE_OFFLINE", "RATE_LIMITED"}


def test_authorized_resume_continues_same_child_and_final_delivery_is_once(monkeypatch, tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    notifications = []
    executor = MultiStageExecutor(service.orchestrator, notification_sink=notifications.append)
    parent_id = executor.submit(objective="analizza revenue e produci due verifiche indipendenti",
                                created_by="test", conversation_id="c", premium_allowed=False)
    child_id = _escalate_first_child(service, executor, parent_id)
    executor.run_once()
    assert service.queue.get(parent_id)["multi_stage_execution"]["steps"][0]["state"] == \
        "WAITING_CONTEXT"

    monkeypatch.setattr("core.ollama_worker.call_local_model", lambda *a, **k: {
        "success": True, "response_text": json.dumps({
            "summary": "Stato verificato.", "findings": ["Nessuna azione esterna."], "risks": []}),
        "error": None, "model": "ministral-3:3b", "wall_seconds": .1})
    service.queue.transition(child_id, "QUEUED")
    service.orchestrator.process_task(child_id)
    executor.run_once()
    parent = service.queue.get(parent_id)
    assert parent["multi_stage_execution"]["steps"][0]["state"] == "VERIFIED"
    second_child = parent["multi_stage_execution"]["steps"][1]["child_task_id"]
    assert second_child != child_id
    service.orchestrator.process_task(second_child)
    executor.run_once()
    for _ in range(20):
        executor.run_once()
    assert service.queue.get(parent_id)["state"] == "COMPLETED"
    completed = [item for item in notifications if item["event_type"] == "TASK_COMPLETED"]
    assert len(completed) == 1
    assert "2 step verificati" in completed[0]["summary"]


def test_online_bridge_resumes_waiting_context_same_child(tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    bridge = LocalAgentBridgeV1(service.orchestrator, state_path=tmp_path / "bridge.json",
                                secret="s" * 48)
    service.orchestrator.set_local_bridge(bridge)
    executor = MultiStageExecutor(service.orchestrator)
    parent_id = executor.submit(objective="analizza revenue e produci due verifiche indipendenti",
                                created_by="test", conversation_id="c", premium_allowed=False)
    executor.run_once()
    parent = service.queue.get(parent_id)
    child_id = parent["multi_stage_execution"]["steps"][0]["child_task_id"]
    service.orchestrator.process_task(child_id)
    executor.run_once()
    assert service.queue.get(parent_id)["multi_stage_execution"]["steps"][0]["state"] == \
        "WAITING_CONTEXT"

    bridge.heartbeat("pc-1", ["bounded_read_only_analysis"])
    executor.run_once()
    resumed = service.queue.get(parent_id)
    assert resumed["multi_stage_execution"]["steps"][0]["child_task_id"] == child_id
    assert resumed["multi_stage_execution"]["steps"][0]["state"] == "RUNNING"
    assert service.queue.get(child_id)["state"] == "QUEUED"
    assert any(event["event_type"] == "TASK_RESUMED"
               for event in service.ledger.read_for_task(parent_id))


def test_simple_mistral_stays_sync(monkeypatch, tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=2: True)
    monkeypatch.setattr("jarvis_v1.service.call_local_model", lambda *a, **k: {
        "success": True, "response_text": "Ciao!", "error": None})
    response = service.handle(message("/mistral ciao"))
    assert response["response_type"] == "ANSWER"
    assert response["summary"] == "Ciao!"
    assert service.queue.list_all() == []
