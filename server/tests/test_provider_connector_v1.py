from datetime import datetime, timezone

from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService
from jarvis_v1.telegram_adapter import TelegramAdapter
from orchestrator_v1.core.dispatcher import DurableQueueDispatcher
from orchestrator_v1.core.provider_connector import (
    MockProviderAdapter, OfflineProviderAdapter, ProviderConnectorV1, ProviderResult)


def telegram_update(update_id, text):
    return {"update_id": update_id, "message": {
        "from": {"id": 42}, "chat": {"id": 99}, "text": text}}


def build(tmp_path, adapter):
    service = JarvisService(tmp_path / "queue.json", tmp_path / "ledger.jsonl",
                            tmp_path / "conversation.json")
    gateway = JarvisGateway(service)
    telegram = TelegramAdapter(service, tmp_path / "seen.json", token="token",
                               allowed_users=["42"], gateway=gateway)
    connector = ProviderConnectorV1(service.orchestrator, {"CLAUDE": adapter})
    dispatcher = DurableQueueDispatcher(service.orchestrator, poll_seconds=0.01,
                                        provider_connector=connector)
    return service, gateway, telegram, connector, dispatcher


def test_telegram_research_escalates_provider_verifies_and_jarvis_finalizes(tmp_path):
    provider = MockProviderAdapter(result={
        "summary": "Ricerca completata con limiti dichiarati.",
        "details": {"finding": "source-backed"}, "source_refs": ["artifact:a.json"],
        "limitations": ["mock acceptance only"]})
    service, gateway, telegram, connector, dispatcher = build(tmp_path, provider)
    created = telegram.handle_update(telegram_update(
        1, "Jarvis, crea una task di ricerca scientifica su una ipotesi esistente."))
    task_id = created["task_id"]
    assert dispatcher.run_once() is True
    assert service.queue.get(task_id)["state"] == "ESCALATION_REQUIRED"
    assert service.queue.get(task_id)["escalation"]["target"] == "TIER3_CLAUDE"
    assert dispatcher.run_once() is True
    record = service.queue.get(task_id)
    assert record["state"] == "COMPLETED"
    assert record["provider_execution"]["verified"] is True
    assert record["provider_execution"]["premium_calls"] == 1
    assert record["result_packet"]["decision"] == "COMPLETED"
    assert len(provider.calls) == 1
    assert set(provider.calls[0]["context_packet"]) == {
        "objective", "relevant_findings", "canonical_artifacts", "current_head",
        "allowed_files", "exact_question", "previous_attempts", "failures", "tests",
        "constraints", "forbidden_actions", "output_required"}
    follow = gateway.handle({
        "message_id": "follow", "user_id": "42", "channel": "TELEGRAM",
        "conversation_id": "telegram:99", "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_type": "TEXT", "text": "A che punto è?", "attachments": [],
        "reply_to": None, "request_class": "FOLLOW_UP", "priority": "NORMAL", "metadata": {}})
    assert follow["status"] == "FINALIZED"
    assert follow["details"]["premium_calls"] == 1
    assert follow["generated_by"] == "provider_connector:CLAUDE"


def test_offline_provider_keeps_escalation_and_does_not_count_call(tmp_path):
    service, _, telegram, connector, dispatcher = build(
        tmp_path, OfflineProviderAdapter("CLAUDE", "OFFLINE"))
    task_id = telegram.handle_update(telegram_update(
        2, "Crea una task di ricerca scientifica su una ipotesi."))["task_id"]
    dispatcher.run_once()
    record = connector.process_task(task_id)
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["provider_execution"]["status"] == "OFFLINE"
    assert record["provider_execution"]["premium_calls"] == 0


def test_rate_limit_returns_to_escalation_without_losing_task(tmp_path):
    class RateLimited(MockProviderAdapter):
        def invoke(self, context_packet, *, idempotency_key, timeout_seconds):
            self.calls.append({"idempotency_key": idempotency_key})
            return ProviderResult(status="RATE_LIMITED", error_class="HTTP_429",
                                  retry_after_seconds=60)
    provider = RateLimited()
    service, _, telegram, connector, dispatcher = build(tmp_path, provider)
    task_id = telegram.handle_update(telegram_update(
        3, "Crea una task di ricerca scientifica su una ipotesi."))["task_id"]
    dispatcher.run_once()
    record = connector.process_task(task_id)
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["provider_execution"]["status"] == "RATE_LIMITED"
    assert record["provider_execution"]["retry_after_seconds"] == 60
    assert record["provider_execution"]["premium_calls"] == 1
    assert dispatcher.run_once() is False
    assert len(provider.calls) == 1


def test_manifest_policy_blocks_premium_even_if_adapter_available(tmp_path):
    provider = MockProviderAdapter()
    service, _, telegram, connector, dispatcher = build(tmp_path, provider)
    task_id = telegram.handle_update(telegram_update(
        4, "Crea una task per analizzare una opportunità generica."))["task_id"]
    dispatcher.run_once()
    record = connector.process_task(task_id)
    assert record["state"] == "ESCALATION_REQUIRED"
    assert record["provider_execution"]["status"] in ("UNAVAILABLE", "POLICY_BLOCKED")
    assert provider.calls == []


def test_provider_call_is_idempotent_after_completion(tmp_path):
    provider = MockProviderAdapter()
    service, _, telegram, connector, dispatcher = build(tmp_path, provider)
    task_id = telegram.handle_update(telegram_update(
        5, "Crea una task di ricerca scientifica su una ipotesi."))["task_id"]
    dispatcher.run_once(); connector.process_task(task_id)
    first = service.queue.get(task_id)
    second = connector.process_task(task_id)
    assert second == first
    assert len(provider.calls) == 1


def test_transient_provider_error_retries_once_with_same_idempotency_key(tmp_path):
    class Transient(MockProviderAdapter):
        def invoke(self, context_packet, *, idempotency_key, timeout_seconds):
            self.calls.append({"idempotency_key": idempotency_key})
            if len(self.calls) == 1:
                raise TimeoutError("provider timeout")
            return ProviderResult(status="SUCCESS", output=self.result,
                                  provider_request_id="after_retry")
    provider = Transient()
    service, _, telegram, connector, dispatcher = build(tmp_path, provider)
    task_id = telegram.handle_update(telegram_update(
        6, "Crea una task di ricerca scientifica su una ipotesi."))["task_id"]
    dispatcher.run_once(); connector.process_task(task_id)
    record = service.queue.get(task_id)
    assert record["state"] == "COMPLETED"
    assert record["provider_execution"]["premium_calls"] == 2
    assert provider.calls[0]["idempotency_key"] == provider.calls[1]["idempotency_key"]
    assert any(event["event_type"] == "PROVIDER_RETRY"
               for event in service.ledger.read_for_task(task_id))
