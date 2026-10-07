import json
from pathlib import Path

from jarvis_v1.local_operations import (
    CapabilityResolver, OperationsProjection, SkillRegistry,
    build_execution_plan, is_complex_mistral_request,
)
from jarvis_v1.service import JarvisService
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
    response = service.handle(message(
        "/mistral analizza lo stato del sistema revenue e dimmi quali azioni concrete sono pronte oggi"))
    assert response["response_type"] == "TASK_ACK"
    assert "background" in response["summary"]
    record = service.queue.get(response["task_id"])
    assert record["state"] == "QUEUED"
    assert record["action"] == "repo_inspection_v1"
    assert record["multi_stage_execution"]["steps"]
    artifact_dir = Path(service.conversation_store.path).parent / "task_artifacts" / response["task_id"]
    assert (artifact_dir / "artifacts").is_dir()


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
