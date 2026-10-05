"""JARVIS_MINISTRAL_ROUTER_V1 - Render-side client (jarvis_v1/ministral_router.py).

Tests build_router_context() (per-message, NOT the project-wide
CONTEXT_PACKET_V2), the gateway HTTP call with an injected opener (no real
network), and resolve_intent_via_router()'s own second validation pass
(schema + referenced_task_id membership) - defense in depth even though the
gateway already validates.
"""
import io
import json
import urllib.error
from datetime import datetime, timezone

import pytest

from jarvis_v1 import ministral_router
from jarvis_v1.service import JarvisService


def message(text, conversation="c1", metadata=None, user_id="42"):
    return {"message_id": f"m-{abs(hash((text, conversation, str(metadata))))}", "user_id": user_id,
            "channel": "TEST", "conversation_id": conversation,
            "timestamp": datetime.now(timezone.utc).isoformat(), "input_type": "TEXT",
            "text": text, "attachments": [], "reply_to": None, "request_class": "UNKNOWN",
            "priority": "NORMAL", "metadata": metadata or {}}


@pytest.fixture
def service(tmp_path, monkeypatch):
    svc = JarvisService(str(tmp_path / "q.json"), str(tmp_path / "l.jsonl"), str(tmp_path / "c.json"))
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    return svc


def _submit(service, task_id, state="WAITING_APPROVAL", conversation_id="c1", created_by="jarvis:42"):
    value = {
        "task_id": task_id, "title": "router test task", "objective": "x", "task_type": "CODE",
        "work_type": "complex_code", "priority": "NORMAL", "risk_level": "A1", "scientific_risk": "NONE",
        "code_risk": "HIGH", "financial_risk": "NONE", "required_capabilities": ["small_python_functions"],
        "deterministic_tools_available": False, "repo_scope": "task-scoped", "files_allowed": ["src/x.py"],
        "files_forbidden": [".env"], "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
        "success_criteria": ["ok"], "verifier": "free_coding_worker_v1", "estimated_complexity": "SMALL",
        "estimated_runtime": "5m", "premium_allowed": False, "preferred_executor": "TIER1_LOCAL_CHEAP",
        "fallback_executors": ["TIER4_CODEX"], "approval_required": "REVIEW_REQUIRED", "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1", "account_scope_id": None,
    }
    service.orchestrator.submit(value, action="conversational_programming",
                                action_params={"conversation_id": conversation_id})
    if state != "QUEUED":
        service.queue.transition(task_id, "RUNNING", executor="TEST")
        if state != "RUNNING":
            service.queue.transition(task_id, state)
    return task_id


# build_router_context --------------------------------------------------
def test_context_is_small_and_user_scoped_not_the_full_project_packet(service):
    task_id = _submit(service, "TASK_CTX_A")
    _submit(service, "TASK_CTX_OTHER_CONV", conversation_id="c2", created_by="jarvis:999")
    context = ministral_router.build_router_context(service, message("ciao"))
    assert context["candidate_task_ids"] == [task_id]
    assert "work_graph" not in context  # not the project-wide CONTEXT_PACKET_V2
    assert "artifact_reservations" not in context


def test_context_includes_conversation_memory(service):
    service.conversation_store.update("c1", last_task_id="TASK_X", last_view="APPROVAL_LIST", user_id="42")
    context = ministral_router.build_router_context(service, message("ciao"))
    assert context["conversation"]["last_task_id"] == "TASK_X"
    assert context["conversation"]["last_view"] == "APPROVAL_LIST"


def test_context_project_summary_absent_when_shared_state_not_wired(service):
    context = ministral_router.build_router_context(service, message("ciao"))
    assert "project_summary" not in context


def test_context_project_summary_present_when_shared_state_wired_and_never_raises(service, tmp_path):
    class _FakeSharedState:
        def snapshot(self):
            return {"current_state": {"current_milestone": "M1", "blockers": ["b1", "b2"],
                                      "roadmap_completion": 0.87}}
    service.set_shared_cognitive_state(_FakeSharedState())
    context = ministral_router.build_router_context(service, message("ciao"))
    assert context["project_summary"]["blockers_count"] == 2
    assert context["project_summary"]["roadmap_completion"] == 0.87


def test_context_project_summary_enrichment_failure_is_swallowed(service):
    class _BrokenSharedState:
        def snapshot(self):
            raise RuntimeError("disk error")
    service.set_shared_cognitive_state(_BrokenSharedState())
    context = ministral_router.build_router_context(service, message("ciao"))  # must not raise
    assert "project_summary" not in context


# _call_gateway / resolve_intent_via_router ------------------------------
VALID_OUTPUT = {
    "intent": "QUERY", "goal": None, "confidence": 0.9, "referenced_task_id": None,
    "recommended_action": None, "target_agent": None, "skill": None, "provider_preference": None,
    "needs_clarification": False, "clarification_question": None, "risk_level": "LOW",
    "reason_summary": "test",
}


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._body = json.dumps(payload).encode()
        self.status = status

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener_returning(payload):
    def _opener(req, timeout=None):
        return _FakeResponse(payload)
    return _opener


def test_resolve_not_configured_without_env(service, monkeypatch):
    monkeypatch.delenv("JARVIS_MINISTRAL_GATEWAY_URL", raising=False)
    monkeypatch.delenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", raising=False)
    result = ministral_router.resolve_intent_via_router(service, message("ciao"))
    assert result["ok"] is False
    assert "NOT_CONFIGURED" in result["error"]
    assert "latency_ms" in result


def test_resolve_success_with_injected_opener(service, monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    result = ministral_router.resolve_intent_via_router(
        service, message("ciao"), opener=_opener_returning({"ok": True, "output": VALID_OUTPUT}))
    assert result["ok"] is True
    assert result["output"]["intent"] == "QUERY"
    assert result["latency_ms"] >= 0


def test_resolve_rejects_a_referenced_task_id_not_among_live_candidates(service, monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    bad = dict(VALID_OUTPUT, intent="APPROVAL", referenced_task_id="TASK_NEVER_SUBMITTED")
    result = ministral_router.resolve_intent_via_router(
        service, message("approvo"), opener=_opener_returning({"ok": True, "output": bad}))
    assert result["ok"] is False
    assert "NOT_IN_CANDIDATES" in result["error"]


def test_resolve_accepts_a_referenced_task_id_that_is_a_live_candidate(service, monkeypatch):
    task_id = _submit(service, "TASK_RESOLVE_OK")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    good = dict(VALID_OUTPUT, intent="APPROVAL", referenced_task_id=task_id)
    result = ministral_router.resolve_intent_via_router(
        service, message("approvo"), opener=_opener_returning({"ok": True, "output": good}))
    assert result["ok"] is True


def test_resolve_rejects_schema_invalid_gateway_output(service, monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    bad = dict(VALID_OUTPUT); bad["intent"] = "NOT_A_VALID_INTENT"
    result = ministral_router.resolve_intent_via_router(
        service, message("ciao"), opener=_opener_returning({"ok": True, "output": bad}))
    assert result["ok"] is False
    assert "SCHEMA_INVALID" in result["error"]


def test_resolve_handles_gateway_http_error(service, monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")

    def _opener(req, timeout=None):
        raise urllib.error.HTTPError("url", 401, "unauthorized", {}, io.BytesIO(b'{"error":"UNAUTHORIZED"}'))

    result = ministral_router.resolve_intent_via_router(service, message("ciao"), opener=_opener)
    assert result["ok"] is False
    assert "GATEWAY_HTTP_401" in result["error"]


def test_resolve_handles_gateway_unreachable(service, monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")

    def _opener(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    result = ministral_router.resolve_intent_via_router(service, message("ciao"), opener=_opener)
    assert result["ok"] is False
    assert "GATEWAY_UNREACHABLE" in result["error"]


def test_resolve_handles_gateway_level_rejection(service, monkeypatch):
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_URL", "https://gateway.example/")
    monkeypatch.setenv("JARVIS_MINISTRAL_GATEWAY_TOKEN", "secret")
    result = ministral_router.resolve_intent_via_router(
        service, message("ciao"), opener=_opener_returning({"ok": False, "error": "SCHEMA_INVALID: x"}))
    assert result["ok"] is False
    assert "GATEWAY_REJECTED" in result["error"]


# is_confident_enough -----------------------------------------------------
def test_is_confident_enough_true_above_threshold():
    assert ministral_router.is_confident_enough(dict(VALID_OUTPUT, confidence=0.9), threshold=0.75)


def test_is_confident_enough_false_below_threshold():
    assert not ministral_router.is_confident_enough(dict(VALID_OUTPUT, confidence=0.5), threshold=0.75)


def test_is_confident_enough_false_when_needs_clarification():
    assert not ministral_router.is_confident_enough(
        dict(VALID_OUTPUT, confidence=0.99, needs_clarification=True), threshold=0.75)
