"""The first floor workflow stops at ACCEPT_ONLY and exposes only its own steps."""
import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

import app as backend
from core.dispatcher import DurableQueueDispatcher
from jarvis_v1.floor_workflow import NOT_RUN, WORKFLOW_ID, project_trace
from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService


def _context():
    return {"evidence_records": [{"evidence_id": "E1", "note": "caller supplied"}]}


def _model_payload():
    return {
        "VIRAL_FORMAT_ANALYSIS": {
            "format_name": "hook-cut", "hook_pattern": "question", "beats": ["open", "turn"],
            "payoff": "held", "comment_bait": "which", "audio_strategy": "PLATFORM_LIBRARY",
            "duration_seconds": 15, "evidence": ["E1"], "limitations": [],
        },
        "PRODUCT_OPPORTUNITY_SCOUT": {
            "title": "linen jacket", "category": "outerwear", "trend_evidence": ["E1"],
            "target_audience": "notes only", "risks": [], "missing_info": [],
        },
        "CONTENT_BRIEF_DRAFT": {
            "title": "linen jacket", "content_category": "fashion", "hook": "described piece only",
            "script": "use the supplied note", "caption": "no added claim", "cta": "review internally",
            "evidence": ["E1"],
        },
    }


def _service(tmp_path, monkeypatch):
    calls = {"n": 0}

    def _fake(prompt, model, json_mode=False):
        calls["n"] += 1
        return {"success": True, "model": model, "response_text": json.dumps(_model_payload()),
                "wall_seconds": 0.0, "error": None}

    monkeypatch.setattr("core.orchestrator.ollama_worker.call_local_model", _fake)
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    service = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"))
    return service, calls


def _message(task_id, action):
    return {"message_id": f"m-{action}-{task_id}", "user_id": "42", "channel": "TEST",
            "conversation_id": "c-floor", "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_type": "TEXT", "text": action, "attachments": [], "reply_to": None,
            "request_class": "APPROVAL", "priority": "HIGH",
            "metadata": {"task_id": task_id, "approval_action": action}}


def test_dispatcher_runs_the_handoff_and_approval_does_not_rerun(tmp_path, monkeypatch):
    service, calls = _service(tmp_path, monkeypatch)
    task_id = service.floor_workflow.submit(objective="internal handoff", context=_context())
    dispatcher = DurableQueueDispatcher(service.orchestrator, poll_seconds=0.05, lease_seconds=30)
    assert dispatcher.run_once() is True
    record = service.queue.get(task_id)
    assert record["state"] == "WAITING_APPROVAL"
    assert record["approval_effect"] == "ACCEPT_ONLY"
    assert record["result_packet"]["decision"] == "PROPOSAL_AWAITING_APPROVAL"
    assert record["result_packet"]["artifacts_created"]
    assert calls["n"] == 1
    events = service.ledger.read_for_task(task_id)
    stations = [event["payload"]["station_id"] for event in events
                if event["event_type"] in {"STEP_COMPLETED", "TASK_WAITING_APPROVAL"}
                and event["payload"].get("workflow_id") == WORKFLOW_ID]
    assert stations == [
        "jarvis.intake", "jarvis.intent", "jarvis.plan", "jarvis.orch",
        "fashion.trend", "fashion.discover", "fashion.verify", "fashion.plan",
        "fashion.handoff", "jarvis.approval",
    ]
    assert not any(event["event_type"] in {"TASK_COMPLETED", "AGENCY_CONTENT_PUBLISHED", "PUSH_COMPLETED",
                                           "DEPLOY_READY"} for event in events)
    approved = JarvisGateway(service).handle(_message(task_id, "APPROVE"))
    assert approved["status"] == "PROPOSAL_ACCEPTED"
    assert dispatcher.run_once() is False
    assert calls["n"] == 1
    assert service.queue.claim_next("later") is None
    trace = project_trace(service.queue, service.ledger)
    assert trace["task_id"] == task_id
    assert trace["artifact_count"] >= 1
    assert trace["delivery"] == "not_sent"
    assert "manifest" not in trace
    assert all(station not in {step["station_id"] for step in trace["steps"]} for station in NOT_RUN)
    blob = json.dumps(trace)
    assert "caller supplied" not in blob
    assert "linen jacket" not in blob


def test_trace_drops_fields_outside_the_step_contract(tmp_path, monkeypatch):
    service, _calls = _service(tmp_path, monkeypatch)
    task_id = service.floor_workflow.submit(objective="internal handoff", context=_context())
    DurableQueueDispatcher(service.orchestrator, poll_seconds=0.05, lease_seconds=30).run_once()
    service.ledger.append("STEP_COMPLETED", task_id, {
        "step_id": "trend", "station_id": "fashion.trend", "state": "RECORDED",
        "output_ref": "skill:VIRAL_FORMAT_ANALYSIS", "provenance": "AGENCY_SKILL",
        "workflow_id": WORKFLOW_ID, "side_effects": "none",
        "manifest": {"token": "secret-token"}, "context": "caller supplied",
    }, actor="floor_workflow_v1")
    trace = project_trace(service.queue, service.ledger, task_id)
    blob = json.dumps(trace)
    assert "secret-token" not in blob
    assert "caller supplied" not in blob
    assert all("manifest" not in step for step in trace["steps"])


def test_floor_workflow_read_requires_a_session():
    client = TestClient(backend.app)
    assert client.get("/api/jarvis/floor-workflow").status_code == 401


def test_service_registers_the_workflow_handler(tmp_path, monkeypatch):
    service, _calls = _service(tmp_path, monkeypatch)
    assert service.orchestrator.local_handlers["nexus_fashion_handoff_workflow"] is service.floor_workflow.handler
