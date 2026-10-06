"""NEXUS_LOCAL_TASK_LEDGER_V1 - /task and /handoff short-circuit in
JarvisService.handle(), before classify()-based routing (same discipline as
/mistral - see test_jarvis_mistral_direct_mode_v1.py)."""
from datetime import datetime, timezone

import pytest

from jarvis_v1.service import JarvisService


def message(text, conversation="c1", user_id="42"):
    return {"message_id": f"m-{abs(hash((text, conversation)))}", "user_id": user_id,
            "channel": "TEST", "conversation_id": conversation,
            "timestamp": datetime.now(timezone.utc).isoformat(), "input_type": "TEXT",
            "text": text, "attachments": [], "reply_to": None, "request_class": "UNKNOWN",
            "priority": "NORMAL", "metadata": {}}


@pytest.fixture
def service(tmp_path, monkeypatch):
    svc = JarvisService(str(tmp_path / "q.json"), str(tmp_path / "l.jsonl"), str(tmp_path / "c.json"))
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    return svc


def test_task_without_objective_prompts_usage(service):
    response = service.handle(message("/task"))
    assert "Usa /task seguito dall'obiettivo" in response["summary"]


def test_task_creates_a_real_canonical_task(service):
    response = service.handle(message("/task analizza gli ultimi CSV MT5 e trova anomalie"))
    assert response["task_id"] is not None
    record = service.queue.get(response["task_id"])
    assert record["manifest"]["objective"] == "analizza gli ultimi CSV MT5 e trova anomalie"
    assert record["state"] == "QUEUED"


def test_task_objective_text_is_never_misrouted_by_other_classifiers(service):
    # Testo che altrimenti potrebbe matchare APPROVAL/mutation verbs - il
    # prefisso /task deve comunque vincere e creare una task, non approvare nulla.
    response = service.handle(message("/task approva tutte le modifiche pendenti nel repo"))
    assert response["task_id"] is not None
    record = service.queue.get(response["task_id"])
    assert record["manifest"]["objective"] == "approva tutte le modifiche pendenti nel repo"


def test_handoff_without_task_id_prompts_usage(service):
    response = service.handle(message("/handoff"))
    assert "Usa /handoff <task_id>" in response["summary"]


def test_handoff_unknown_task_id_is_reported_cleanly(service):
    response = service.handle(message("/handoff TASK_DOES_NOT_EXIST"))
    assert response["status"] == "PARTIAL"
    assert "Nessuna task trovata" in response["summary"]


def test_handoff_known_task_writes_and_reports_artifact_paths(service):
    create_response = service.handle(message("/task analizza i log del tester"))
    task_id = create_response["task_id"]
    response = service.handle(message(f"/handoff {task_id}"))
    assert response["details"]["view"] == "TASK_HANDOFF"
    assert response["details"]["task_id"] == task_id
    assert "handoff.md" in response["details"]["artifact_paths"]
    import pathlib
    assert pathlib.Path(response["details"]["artifact_paths"]["handoff.md"]).exists()


def test_follow_up_on_completed_task_lazily_writes_handoff_artifacts(service):
    create_response = service.handle(message("/task analizza i log del tester"))
    task_id = create_response["task_id"]
    service.queue.transition(task_id, "RUNNING", executor="TEST")
    service.queue.transition(task_id, "COMPLETED", result_packet={
        "task_id": task_id, "executor": "TIER1_LOCAL_CHEAP",
        "start_time": "2026-10-06T10:00:00+00:00", "end_time": "2026-10-06T10:05:00+00:00",
        "files_read": [], "files_changed": [], "tools_or_commands": [], "artifacts_created": [],
        "tests": {"ran": False, "passed": 0, "failed": 0},
        "verifier": {"ran": False, "passed": False, "errors": []},
        "commit": None, "push_status": "NOT_APPLICABLE", "decision": "fatto",
        "confidence": "HIGH", "limitations": [], "unresolved_issues": [], "suggested_next_tasks": [],
        "escalation_needed": {"needed": False, "reason": None, "target_tier": None},
    })
    from jarvis_v1 import task_handoff
    artifacts_dir = task_handoff.task_artifacts_dir(service, task_id)
    assert not artifacts_dir.exists()
    service.handle(message(f"dettagli tecnici {task_id}"))
    assert (artifacts_dir / "handoff.md").exists()
