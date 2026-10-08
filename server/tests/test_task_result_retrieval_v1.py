import json

from jarvis_v1.service import JarvisService, classify
from jarvis_v1.multi_stage_executor import MultiStageExecutor
from jarvis_v1.telegram_adapter import TelegramAdapter


def message(text, message_id="m1"):
    return {"message_id": message_id, "user_id": "u1", "channel": "TELEGRAM",
            "conversation_id": "telegram:c1", "timestamp": "2026-10-08T00:00:00+00:00",
            "input_type": "TEXT", "text": text, "attachments": [], "reply_to": None,
            "request_class": "UNKNOWN", "priority": "NORMAL", "metadata": {}}


def _completed_multi_stage(monkeypatch, tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    notifications = []
    executor = MultiStageExecutor(service.orchestrator, notification_sink=notifications.append)
    service.set_multi_stage_executor(executor)
    calls = iter([("Sintesi sistema.", ["Subsystem A degradato."]),
                  ("Estrazione artifact.", ["Subsystem B richiede review."])])

    def local_call(*_args, **_kwargs):
        summary, findings = next(calls)
        return {"success": True, "response_text": json.dumps(
            {"summary": summary, "findings": findings, "risks": []}),
            "error": None, "model": "ministral-3:3b", "wall_seconds": .1}

    monkeypatch.setattr("core.ollama_worker.call_local_model", local_call)
    response = service.handle(message(
        "/mistral analizza lo stato operativo di Nexus e identifica due subsystem che richiedono attenzione"))
    parent_id = response["task_id"]
    child_ids = []
    for _ in range(2):
        executor.run_once()
        parent = service.queue.get(parent_id)
        step = next(item for item in parent["multi_stage_execution"]["steps"]
                    if item["state"] == "RUNNING")
        child_ids.append(step["child_task_id"])
        service.orchestrator.process_task(step["child_task_id"])
        service.queue.annotate(step["child_task_id"], local_bridge={
            "status": "COMPLETED", "capability": "bounded_read_only_analysis",
            "bridge_id": "test-bridge"})
        executor.run_once()
    return service, notifications, parent_id, child_ids


def test_result_intent_routes_to_read_only_retrieval():
    phrases = ["mostrami il risultato della task TASK_ABC123",
               "cosa ha prodotto la task TASK_ABC123?",
               "quali step ha verificato TASK_ABC123?",
               "mostrami gli artifact di TASK_ABC123",
               "perché è stata completata TASK_ABC123?",
               "apri il report della task TASK_ABC123"]
    assert {classify(value) for value in phrases} == {"TASK_RESULT"}


def test_parent_result_retrieves_children_capabilities_and_evidence(monkeypatch, tmp_path):
    service, notifications, parent_id, child_ids = _completed_multi_stage(monkeypatch, tmp_path)
    before = len(service.queue.list_all())
    response = service.handle(message(f"mostrami il risultato completo della task {parent_id}", "m2"))
    assert len(service.queue.list_all()) == before
    assert response["details"]["view"] == "TASK_RESULT"
    assert response["details"]["result_status"] == "AVAILABLE"
    assert {item["task_id"] for item in response["details"]["children"]} == set(child_ids)
    assert {item["required_capability"] for item in response["details"]["children"]} == {
        "summaries", "artifact_field_extraction"}
    assert {item["transport_capability"] for item in response["details"]["children"]} == {
        "bounded_read_only_analysis"}
    assert all(item["verifier"]["passed"] is True for item in response["details"]["children"])
    assert {item["text"] for item in response["details"]["evidence"]} == {
        "Subsystem A degradato.", "Subsystem B richiede review."}
    completed = [item for item in notifications if item["event_type"] == "TASK_COMPLETED"]
    assert len(completed) == 1
    assert "Sintesi sistema" in completed[0]["summary"]
    assert completed[0]["details"]["view"] == "TASK_RESULT"


def test_missing_result_is_explicit_and_does_not_create_work(tmp_path):
    service = JarvisService(queue_path=tmp_path / "queue.json", ledger_path=tmp_path / "ledger.jsonl",
                            conversation_path=tmp_path / "conversations.json")
    task_id = service.create_task(message("crea una task per riepilogare lo stato", "create"))["task_id"]
    before = len(service.queue.list_all())
    response = service.handle(message(f"mostrami il risultato della task {task_id}", "result"))
    assert len(service.queue.list_all()) == before
    assert response["status"] == "RESULT_UNAVAILABLE"
    assert response["details"]["unavailable_reason"] == "RESULT_PACKET_MISSING"


def test_telegram_renders_result_and_result_button(monkeypatch, tmp_path):
    service, _notifications, parent_id, _children = _completed_multi_stage(monkeypatch, tmp_path)
    response = service.handle(message(f"apri il report della task {parent_id}", "m3"))
    rendered = TelegramAdapter.render_response(response)
    assert "Capability logica: summaries" in rendered
    assert "Capability logica: artifact_field_extraction" in rendered
    assert "Capability bridge: bounded_read_only_analysis" in rendered
    keyboard = TelegramAdapter.build_keyboard(response)
    assert keyboard[0][0]["callback_data"] == f"J1|TR|{parent_id}|C"


def test_telegram_result_callback_is_read_only(monkeypatch, tmp_path):
    service, _notifications, parent_id, _children = _completed_multi_stage(monkeypatch, tmp_path)
    adapter = TelegramAdapter(service, state_path=tmp_path / "updates.json", token="t",
                              allowed_users={"7"})
    parsed = adapter.parse_update({"update_id": 9, "callback_query": {
        "from": {"id": 7}, "data": f"J1|TR|{parent_id}|C",
        "message": {"chat": {"id": 7}}}})
    before = len(service.queue.list_all())
    response = service.handle(parsed)
    assert response["details"]["view"] == "TASK_RESULT"
    assert len(service.queue.list_all()) == before
