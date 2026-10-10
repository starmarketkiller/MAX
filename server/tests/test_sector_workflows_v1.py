"""Sector workflows stay on the one queue and do not grow a side effect."""
import json
from pathlib import Path
from fastapi.testclient import TestClient

import app as backend
from core.dispatcher import DurableQueueDispatcher
from jarvis_v1.authenticated_scope import EndpointRateLimiter
from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService
from jarvis_v1.sector_workflows import (
    COUNCIL_ACTION, FINANCE_ACTION, REVENUE_ACTION, SOCIAL_ACTION, TRADING_ACTION,
)


ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_ACTIONS = {
    "nexus_trading_execution", "revenue_convert", "social_publish", "systems_ship",
    "jarvis_deliver", "jarvis_notify", "council_adopt",
}


def _fake_model(payload):
    def _call(prompt, model, json_mode=False, timeout=None):
        _call.n += 1
        return {"success": True, "model": model, "response_text": json.dumps(payload),
                "wall_seconds": 0.0, "error": None}
    _call.n = 0
    return _call


def _service(tmp_path, monkeypatch, payload=None):
    call = _fake_model(payload or {})
    monkeypatch.setattr("core.orchestrator.ollama_worker.call_local_model", call)
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    service = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"))
    return service, call


def _client(monkeypatch, service):
    monkeypatch.setattr(backend, "JARVIS_SERVICE", service)
    monkeypatch.setattr(backend, "JARVIS_GATEWAY", JarvisGateway(service))
    monkeypatch.setattr(backend, "FLOOR_WORKFLOW_LIMITER", EndpointRateLimiter(limit=30))
    client = TestClient(backend.app)
    return client


def _steps(service, task_id):
    return [event["payload"]["station_id"] for event in service.ledger.read_for_task(task_id)
            if event["event_type"] in {"STEP_COMPLETED", "TASK_WAITING_APPROVAL"}]


def test_trading_requires_a_dataset_and_never_executes(tmp_path, monkeypatch):
    service, call = _service(tmp_path, monkeypatch)
    client = _client(monkeypatch, service)
    backend.app.dependency_overrides[backend.require_mutation] = lambda: "42"
    backend.app.dependency_overrides[backend.require_user] = lambda: "42"
    try:
        missing = client.post("/api/jarvis/trading-research", headers={"Idempotency-Key": "trading-no-dataset"},
                              json={"objective": "inspect the series", "context": {"evidence_records": [
                                  {"evidence_id": "E1", "note": "a note", "source": "https://example.com/x"}]}})
        assert missing.status_code == 422
        assert missing.json()["detail"]["code"] == "DATASET_REQUIRED"
        assert service.queue.list_all() == []
        created = client.post("/api/jarvis/trading-research", headers={"Idempotency-Key": "trading-dataset-01"},
                              json={"objective": "inspect the series", "context": {"evidence_records": [
                                  {"evidence_id": "E1", "note": "bars", "source": "dataset:dukascopy-2024"}]}})
        assert created.status_code == 202
        task_id = created.json()["task_id"]
        assert DurableQueueDispatcher(service.orchestrator, poll_seconds=0.05, lease_seconds=30).run_once() is True
        assert service.queue.get(task_id)["state"] == "WAITING_APPROVAL"
        assert call.n == 0
        assert _steps(service, task_id) == ["trading.data", "trading.research", "jarvis.approval"]
        trace = client.get("/api/jarvis/trading-research", params={"task_id": task_id}).json()
        reasons = {item["station_id"]: item["reason"] for item in trace["not_run"]}
        assert reasons["trading.struct"] == "series_absent"
        assert reasons["trading.backtest"] == "no_second_sample"
        assert "trading.exec" not in reasons
        blob = json.dumps(service.ledger.read_for_task(task_id))
        assert "ORDER" not in blob and "DEAL" not in blob and "GO_LIVE" not in blob
        assert FORBIDDEN_ACTIONS.isdisjoint(service.orchestrator.local_handlers)
    finally:
        backend.app.dependency_overrides.clear()


def test_revenue_without_a_url_is_rejected_and_approval_does_not_send(tmp_path, monkeypatch):
    payload = {"fit": "INSUFFICIENT_EVIDENCE", "matched_problem": "perimeter only",
               "evidence": ["SRC_1"], "conflicts": []}
    service, call = _service(tmp_path, monkeypatch, payload)
    client = _client(monkeypatch, service)
    backend.app.dependency_overrides[backend.require_mutation] = lambda: "42"
    try:
        rejected = client.post("/api/jarvis/revenue-proposal", headers={"Idempotency-Key": "revenue-no-url"},
                               json={"objective": "draft an offer", "context": {"evidence_records": [
                                   {"evidence_id": "SRC_1", "note": "seen", "source": "dataset:note"}]}})
        assert rejected.status_code == 422
        assert rejected.json()["detail"]["code"] == "URL_REQUIRED"
        assert service.queue.list_all() == []
        created = client.post("/api/jarvis/revenue-proposal", headers={"Idempotency-Key": "revenue-with-url"},
                              json={"objective": "draft an offer", "context": {"evidence_records": [
                                  {"evidence_id": "SRC_1", "note": "seen", "source": "https://example.com/brief"}]}})
        assert created.status_code == 202
        task_id = created.json()["task_id"]
        DurableQueueDispatcher(service.orchestrator, poll_seconds=0.05, lease_seconds=30).run_once()
        assert service.queue.get(task_id)["state"] == "WAITING_APPROVAL"
        assert service.queue.get(task_id)["approval_effect"] == "ACCEPT_ONLY"
        assert call.n == 1
        approved = client.post(f"/api/jarvis/approvals/{task_id}", json={"action": "APPROVE"})
        assert approved.status_code == 200
        assert service.queue.get(task_id)["state"] == "PROPOSAL_ACCEPTED"
        names = [event["event_type"] for event in service.ledger.read_all()]
        assert "NOTIFICATION_SENT" not in names
        assert REVENUE_ACTION in service.orchestrator.local_handlers
        assert "revenue_convert" not in service.orchestrator.local_handlers
    finally:
        backend.app.dependency_overrides.clear()


def test_social_draft_requires_an_accepted_handoff_and_cannot_publish(tmp_path, monkeypatch):
    from jarvis_v1.floor_workflow import WORKFLOW_ID
    review = {"verdict": "REVISE", "issues": [], "evidence": ["E1"]}
    service, call = _service(tmp_path, monkeypatch, {
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
    })
    client = _client(monkeypatch, service)
    backend.app.dependency_overrides[backend.require_mutation] = lambda: "42"
    try:
        launched = client.post("/api/jarvis/floor-workflow", headers={"Idempotency-Key": "social-source-01"},
                               json={"objective": "internal handoff", "context": {"evidence_records": [
                                   {"evidence_id": "E1", "note": "caller supplied", "source": "fixture:caller"}]}})
        assert launched.status_code == 202
        source_id = launched.json()["task_id"]
        DurableQueueDispatcher(service.orchestrator, poll_seconds=0.05, lease_seconds=30).run_once()
        early = client.post("/api/jarvis/social-draft", headers={"Idempotency-Key": "social-too-early"},
                            json={"source_task_id": source_id})
        assert early.status_code == 409
        assert early.json()["detail"]["code"] == "SOURCE_NOT_ACCEPTED"
        client.post(f"/api/jarvis/approvals/{source_id}", json={"action": "APPROVE"})
        monkeypatch.setattr("core.orchestrator.ollama_worker.call_local_model", _fake_model(review))
        drafted = client.post("/api/jarvis/social-draft", headers={"Idempotency-Key": "social-draft-01"},
                              json={"source_task_id": source_id, "objective": "free prompt"})
        assert drafted.status_code == 422
        drafted = client.post("/api/jarvis/social-draft", headers={"Idempotency-Key": "social-draft-01"},
                              json={"source_task_id": source_id})
        assert drafted.status_code == 202
        task_id = drafted.json()["task_id"]
        DurableQueueDispatcher(service.orchestrator, poll_seconds=0.05, lease_seconds=30).run_once()
        assert service.queue.get(task_id)["state"] == "WAITING_APPROVAL"
        assert _steps(service, task_id) == ["social.edit", "social.script", "social.create", "social.qc", "social.ok"]
        assert "social_publish" not in service.orchestrator.local_handlers
        assert SOCIAL_ACTION in service.orchestrator.local_handlers
        assert WORKFLOW_ID != "jarvis.social.draft.v1"
    finally:
        backend.app.dependency_overrides.clear()


def test_finance_empty_report_creates_no_task_and_an_orphan_figure_blocks(tmp_path, monkeypatch):
    service, call = _service(tmp_path, monkeypatch)
    client = _client(monkeypatch, service)
    backend.app.dependency_overrides[backend.require_user] = lambda: "42"
    backend.app.dependency_overrides[backend.require_mutation] = lambda: "42"
    try:
        empty = client.get("/api/jarvis/finance-report")
        assert empty.status_code == 200
        assert empty.json()["state"] is None
        assert len(empty.json()["not_run"]) == 13
        assert service.queue.list_all() == []
        quiet = client.post("/api/jarvis/finance-report", headers={"Idempotency-Key": "finance-quiet-01"},
                            json={"claim": "no document", "context": {"evidence_records": [
                                {"evidence_id": "C1", "note": "none", "source": "ledger:empty"}]}})
        assert quiet.status_code == 200
        assert quiet.json()["task_id"] is None
        assert service.queue.list_all() == []
        orphan = client.post("/api/jarvis/finance-report", headers={"Idempotency-Key": "finance-orphan-1"},
                             json={"claim": "cost 12", "context": {"evidence_records": [
                                 {"evidence_id": "C1", "note": "none", "source": "ledger:empty"}]}})
        assert orphan.status_code == 202
        task_id = orphan.json()["task_id"]
        DurableQueueDispatcher(service.orchestrator, poll_seconds=0.05, lease_seconds=30).run_once()
        assert service.queue.get(task_id)["state"] == "BLOCKED"
        assert not any(event["event_type"] == "STEP_COMPLETED" for event in service.ledger.read_for_task(task_id))
        assert call.n == 0
        assert FINANCE_ACTION in service.orchestrator.local_handlers
    finally:
        backend.app.dependency_overrides.clear()


def test_council_without_failures_does_not_invent_a_hypothesis(tmp_path, monkeypatch):
    service, _call = _service(tmp_path, monkeypatch)
    client = _client(monkeypatch, service)
    backend.app.dependency_overrides[backend.require_mutation] = lambda: "42"
    try:
        empty = client.post("/api/jarvis/council-hypothesis", headers={"Idempotency-Key": "council-empty-1"},
                            json={})
        assert empty.status_code == 200
        assert empty.json()["state"] is None
        assert service.queue.list_all() == []
        service.ledger.append("TASK_FAILED", "TASK_OLD", {"reason": "verify failed"})
        created = client.post("/api/jarvis/council-hypothesis", headers={"Idempotency-Key": "council-once-01"},
                              json={})
        assert created.status_code == 202
        task_id = created.json()["task_id"]
        DurableQueueDispatcher(service.orchestrator, poll_seconds=0.05, lease_seconds=30).run_once()
        assert service.queue.get(task_id)["state"] == "WAITING_APPROVAL"
        assert "council.hypo" in _steps(service, task_id)
        assert "council.adopt" not in _steps(service, task_id)
        assert COUNCIL_ACTION in service.orchestrator.local_handlers
        assert "council_adopt" not in service.orchestrator.local_handlers
    finally:
        backend.app.dependency_overrides.clear()


def test_systems_floor_has_no_deploy_path():
    text = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "autoDeployTrigger: off" in text
    frontend = ROOT / "frontend" / "src" / "command"
    blob = "\n".join(path.read_text(encoding="utf-8") for path in frontend.glob("*.js*"))
    assert "onrender.com" not in blob
    assert "safe-deploy" not in blob.lower()


def test_revenue_automation_does_not_reference_the_floor_action():
    text = (ROOT / "server" / "funding_v1" / "revenue_automation.py").read_text(encoding="utf-8")
    assert REVENUE_ACTION not in text


def test_live_revenue_without_gateway_does_not_queue(tmp_path, monkeypatch):
    service, _call = _service(tmp_path, monkeypatch)
    client = _client(monkeypatch, service)
    monkeypatch.setenv("NEXUS_ENV", "LIVE")
    monkeypatch.delenv("JARVIS_MINISTRAL_GATEWAY_URL", raising=False)
    monkeypatch.delenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", raising=False)
    backend.app.dependency_overrides[backend.require_mutation] = lambda: "42"
    try:
        response = client.post("/api/jarvis/revenue-proposal", headers={"Idempotency-Key": "revenue-live-off"},
                               json={"objective": "draft an offer", "context": {"evidence_records": [
                                   {"evidence_id": "SRC_1", "note": "seen", "source": "https://example.com/brief"}]}})
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "MODEL_UNAVAILABLE"
        assert service.queue.list_all() == []
    finally:
        backend.app.dependency_overrides.clear()
