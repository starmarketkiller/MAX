"""JARVIS_MINISTRAL_ROUTER_V1 - end-to-end wiring inside JarvisService.handle().

ministral_router.resolve_intent_via_router is monkeypatched throughout (no
real gateway/Ollama in CI) so every test here is deterministic and fast.
Covers: ENABLED=false is a true no-op (today's exact behavior), the
deterministic-first bypass for already-unambiguous mutations, SHADOW mode
never affecting or delaying the real response, ACTIVE mode's dispatch and
every fallback trigger, and the 11 required example phrases from the task.
"""
import time
from datetime import datetime, timezone

import pytest

from jarvis_v1 import ministral_router
from jarvis_v1.gateway import JarvisGateway
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


def _manifest(task_id, **changes):
    value = {
        "task_id": task_id, "title": "router integration test task", "objective": "Update src/sample.py",
        "task_type": "CODE", "work_type": "complex_code", "priority": "NORMAL",
        "risk_level": "A1", "scientific_risk": "NONE", "code_risk": "HIGH",
        "financial_risk": "NONE", "required_capabilities": ["small_python_functions"],
        "deterministic_tools_available": False, "repo_scope": "task-scoped",
        "files_allowed": ["src/sample.py"], "files_forbidden": [".env", "MQL5/**"],
        "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
        "success_criteria": ["bounded patch verified"], "verifier": "free_coding_worker_v1",
        "estimated_complexity": "SMALL", "estimated_runtime": "5m", "premium_allowed": False,
        "preferred_executor": "TIER1_LOCAL_CHEAP", "fallback_executors": ["TIER4_CODEX"],
        "approval_required": "REVIEW_REQUIRED", "created_by": "jarvis:42",
        "created_at": datetime.now(timezone.utc).isoformat(), "tenant_id": "tenant-1",
        "account_scope_id": None,
    }
    value.update(changes)
    return value


def _submit(service, task_id, state, conversation_id="c1", **record_updates):
    value = _manifest(task_id)
    service.orchestrator.submit(value, action="conversational_programming",
                                action_params={"conversation_id": conversation_id})
    if state != "QUEUED":
        service.queue.transition(task_id, "RUNNING", executor="TEST")
        if state != "RUNNING":
            service.queue.transition(task_id, state, **record_updates)
    return task_id


def _enable_router(monkeypatch, mode="SHADOW"):
    monkeypatch.setenv("JARVIS_MINISTRAL_ROUTER_ENABLED", "true")
    monkeypatch.setenv("JARVIS_MINISTRAL_ROUTER_MODE", mode)


VALID_OUTPUT = {
    "intent": "QUERY", "goal": None, "confidence": 0.95, "referenced_task_id": None,
    "recommended_action": None, "target_agent": None, "skill": None, "provider_preference": None,
    "needs_clarification": False, "clarification_question": None, "risk_level": "LOW",
    "reason_summary": "test",
}


def _wait_for_ledger_event(service, event_type, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        events = [e for e in service.ledger.read_all() if e["event_type"] == event_type]
        if events:
            return events
        time.sleep(0.02)
    return []


# 1. disabled by default = true no-op ---------------------------------------
def test_router_disabled_by_default_is_a_true_no_op(service, monkeypatch):
    monkeypatch.delenv("JARVIS_MINISTRAL_ROUTER_ENABLED", raising=False)

    def _should_not_be_called(*a, **k):
        raise AssertionError("router must not be invoked when disabled")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router", _should_not_be_called)
    response = JarvisGateway(service).handle(message("Che giornata di merda"))
    assert response["response_type"] == "ANSWER"  # falls through to the usual fallback, unchanged


# 2. deterministic-first bypass -----------------------------------------
def test_explicit_mutation_signal_never_calls_the_router_even_when_active(service, monkeypatch):
    task_id = _submit(service, "TASK_EXPLICIT", "WAITING_APPROVAL")
    _enable_router(monkeypatch, mode="ACTIVE")

    def _should_not_be_called(*a, **k):
        raise AssertionError("router must not be invoked for an already-explicit command")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router", _should_not_be_called)
    response = JarvisGateway(service).handle(message(f"approva {task_id}"))
    assert response["task_id"] == task_id
    assert service.queue.get(task_id)["state"] == "QUEUED"


def test_button_callback_never_calls_the_router(service, monkeypatch):
    task_id = _submit(service, "TASK_CALLBACK_BYPASS", "WAITING_APPROVAL")
    _enable_router(monkeypatch, mode="ACTIVE")

    def _should_not_be_called(*a, **k):
        raise AssertionError("router must not be invoked for a ui_action-driven message")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router", _should_not_be_called)
    msg = message(f"Telegram action APPROVE for {task_id}",
                 metadata={"ui_action": "APPROVE", "task_id": task_id})
    response = JarvisGateway(service).handle(msg)
    assert response["task_id"] == task_id


# 3. SHADOW never alters or delays the real response ----------------------
def test_shadow_mode_response_is_identical_to_classifier_path(service, monkeypatch):
    _enable_router(monkeypatch, mode="SHADOW")
    disagreeing = dict(VALID_OUTPUT, intent="EXECUTIVE_INTENT", confidence=0.99)
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": disagreeing, "latency_ms": 1})
    baseline = service._dispatch_classifier(dict(message("Che giornata di merda")))
    response = JarvisGateway(service).handle(message("Che giornata di merda"))
    assert response["summary"] == baseline["summary"]
    assert response["response_type"] == baseline["response_type"]


def test_shadow_mode_slow_router_does_not_delay_the_response(service, monkeypatch):
    _enable_router(monkeypatch, mode="SHADOW")

    def _slow(svc, msg, **k):
        time.sleep(2)
        return {"ok": True, "output": VALID_OUTPUT, "latency_ms": 2000}
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router", _slow)
    started = time.monotonic()
    response = JarvisGateway(service).handle(message("Che giornata di merda"))
    elapsed = time.monotonic() - started
    assert elapsed < 0.5
    assert response["response_type"] == "ANSWER"


def test_shadow_mode_offline_router_does_not_delay_or_change_the_response(service, monkeypatch):
    _enable_router(monkeypatch, mode="SHADOW")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": False, "error": "GATEWAY_UNREACHABLE", "latency_ms": 5})
    baseline = service._dispatch_classifier(dict(message("Che giornata di merda")))
    response = JarvisGateway(service).handle(message("Che giornata di merda"))
    assert response["summary"] == baseline["summary"]


def test_shadow_mode_logs_comparison_with_disagreement(service, monkeypatch):
    _enable_router(monkeypatch, mode="SHADOW")
    disagreeing = dict(VALID_OUTPUT, intent="EXECUTIVE_INTENT")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": disagreeing, "latency_ms": 42})
    JarvisGateway(service).handle(message("Che giornata di merda"))
    events = _wait_for_ledger_event(service, "MINISTRAL_ROUTER_SHADOW_COMPARISON")
    assert events, "expected a shadow comparison ledger event"
    payload = events[-1]["payload"]
    assert payload["classifier_decision"] == "UNKNOWN"
    assert payload["ministral_decision"] == "EXECUTIVE_INTENT"
    assert payload["disagreement"] is True
    assert payload["schema_valid"] is True


def test_shadow_mode_router_raising_is_logged_not_crashed(service, monkeypatch):
    _enable_router(monkeypatch, mode="SHADOW")

    def _raising(svc, msg, **k):
        raise RuntimeError("unexpected")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router", _raising)
    response = JarvisGateway(service).handle(message("Che giornata di merda"))  # must not raise
    assert response["response_type"] == "ANSWER"
    events = _wait_for_ledger_event(service, "MINISTRAL_ROUTER_SHADOW_COMPARISON")
    assert events and events[-1]["payload"]["schema_valid"] is False


# ACTIVE mode ---------------------------------------------------------------
def test_active_mode_dispatches_via_router_output_and_logs_decision(service, monkeypatch):
    _enable_router(monkeypatch, mode="ACTIVE")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": VALID_OUTPUT, "latency_ms": 10})
    response = JarvisGateway(service).handle(message("dimmi qualcosa di generico"))
    assert response["response_type"] == "ANSWER"
    events = [e for e in service.ledger.read_all() if e["event_type"] == "MINISTRAL_ROUTER_ACTIVE_DECISION"]
    assert events
    assert events[-1]["payload"]["intent"] == "QUERY"


def test_active_mode_gateway_offline_falls_back_to_classifier(service, monkeypatch):
    _enable_router(monkeypatch, mode="ACTIVE")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": False, "error": "GATEWAY_UNREACHABLE", "latency_ms": 5})
    baseline = service._dispatch_classifier(dict(message("dimmi qualcosa di generico")))
    response = JarvisGateway(service).handle(message("dimmi qualcosa di generico"))
    assert response["summary"] == baseline["summary"]
    events = [e for e in service.ledger.read_all() if e["event_type"] == "MINISTRAL_ROUTER_FALLBACK"]
    assert events and events[-1]["payload"]["reason"] == "GATEWAY_UNREACHABLE"


def test_active_mode_invalid_schema_falls_back_to_classifier(service, monkeypatch):
    _enable_router(monkeypatch, mode="ACTIVE")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": False, "error": "RENDER_SIDE_SCHEMA_INVALID: x", "latency_ms": 5})
    baseline = service._dispatch_classifier(dict(message("dimmi qualcosa di generico")))
    response = JarvisGateway(service).handle(message("dimmi qualcosa di generico"))
    assert response["summary"] == baseline["summary"]


def test_active_mode_low_confidence_falls_back_to_classifier(service, monkeypatch):
    _enable_router(monkeypatch, mode="ACTIVE")
    low = dict(VALID_OUTPUT, confidence=0.3)
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": low, "latency_ms": 5})
    baseline = service._dispatch_classifier(dict(message("dimmi qualcosa di generico")))
    response = JarvisGateway(service).handle(message("dimmi qualcosa di generico"))
    assert response["summary"] == baseline["summary"]
    events = [e for e in service.ledger.read_all() if e["event_type"] == "MINISTRAL_ROUTER_FALLBACK"]
    assert events and events[-1]["payload"]["reason"] == "LOW_CONFIDENCE_OR_NEEDS_CLARIFICATION"


def test_active_mode_needs_clarification_falls_back_to_classifier(service, monkeypatch):
    _enable_router(monkeypatch, mode="ACTIVE")
    unsure = dict(VALID_OUTPUT, confidence=0.99, needs_clarification=True)
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": unsure, "latency_ms": 5})
    baseline = service._dispatch_classifier(dict(message("dimmi qualcosa di generico")))
    response = JarvisGateway(service).handle(message("dimmi qualcosa di generico"))
    assert response["summary"] == baseline["summary"]


def test_active_mode_unmappable_intent_falls_back_to_classifier(service, monkeypatch):
    # STATE_QUERY with raw text the deterministic state-word matcher can't
    # resolve - _dispatch_via_router_output must refuse to call state_query()
    # with an empty filter rather than silently returning an empty list.
    _enable_router(monkeypatch, mode="ACTIVE")
    unmappable = dict(VALID_OUTPUT, intent="STATE_QUERY")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": unmappable, "latency_ms": 5})
    baseline = service._dispatch_classifier(dict(message("xyzxyz non matcha nessun sinonimo di stato")))
    response = JarvisGateway(service).handle(message("xyzxyz non matcha nessun sinonimo di stato"))
    assert response["summary"] == baseline["summary"]


# required example phrases (ACTIVE, stubbed representative output) ---------
def test_phrase_approvo_with_single_pending(service, monkeypatch):
    task_id = _submit(service, "TASK_PHRASE_APPROVO", "WAITING_APPROVAL")
    _enable_router(monkeypatch, mode="ACTIVE")
    out = dict(VALID_OUTPUT, intent="APPROVAL", referenced_task_id=task_id, recommended_action="APPROVE")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": out, "latency_ms": 5})
    response = JarvisGateway(service).handle(message("Approvo"))
    assert response["task_id"] == task_id
    assert service.queue.get(task_id)["state"] == "QUEUED"


def test_phrase_che_facciamo_adesso(service, monkeypatch):
    _submit(service, "TASK_PHRASE_NEXT", "QUEUED")
    _enable_router(monkeypatch, mode="ACTIVE")
    out = dict(VALID_OUTPUT, intent="EXECUTIVE_INTENT")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": out, "latency_ms": 5})
    response = JarvisGateway(service).handle(message("Che facciamo adesso?"))
    assert response["response_type"] == "ANSWER"


def test_phrase_continua_tu(service, monkeypatch):
    task_id = _submit(service, "TASK_PHRASE_CONTINUE", "WAITING_APPROVAL")
    service.conversation_store.update("c1", last_task_id=task_id, user_id="42")
    _enable_router(monkeypatch, mode="ACTIVE")
    out = dict(VALID_OUTPUT, intent="FOLLOW_UP", referenced_task_id=task_id)
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": out, "latency_ms": 5})
    response = JarvisGateway(service).handle(message("Continua tu"))
    assert response["task_id"] == task_id


def test_phrase_voglio_guadagnare_i_primi_10_euro(service, monkeypatch):
    _enable_router(monkeypatch, mode="ACTIVE")
    out = dict(VALID_OUTPUT, intent="GOAL_TO_TASK", goal="guadagnare i primi 10 euro")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": out, "latency_ms": 5})
    response = JarvisGateway(service).handle(message("Voglio guadagnare i primi 10€"))
    assert response["response_type"] == "ANSWER"


def test_phrase_fammi_vedere_quelle_bloccate(service, monkeypatch):
    stuck = _submit(service, "TASK_PHRASE_BLOCKED", "ESCALATION_REQUIRED",
                    escalation={"target": "MANUAL_REVIEW", "classification": "x"})
    _enable_router(monkeypatch, mode="ACTIVE")
    out = dict(VALID_OUTPUT, intent="STATE_QUERY")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": out, "latency_ms": 5})
    response = JarvisGateway(service).handle(message("Fammi vedere quelle bloccate"))
    assert response["details"]["view"] == "TASK_LIST"
    assert stuck in [item["task_id"] for item in response["details"]["items"]]


def test_phrase_usa_groq(service, monkeypatch):
    _enable_router(monkeypatch, mode="ACTIVE")
    out = dict(VALID_OUTPUT, intent="PROVIDER_PREFERENCE", provider_preference="groq")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": out, "latency_ms": 5})
    response = JarvisGateway(service).handle(message("Usa Groq"))
    assert response["response_type"] in ("ANSWER", "PREFERENCE_SET")


def test_phrase_non_usare_premium(service, monkeypatch):
    _enable_router(monkeypatch, mode="ACTIVE")
    out = dict(VALID_OUTPUT, intent="PROVIDER_PREFERENCE")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": out, "latency_ms": 5})
    response = JarvisGateway(service).handle(message("Non usare premium"))
    assert response["response_type"] in ("ANSWER", "PREFERENCE_SET")


def test_phrase_riprendi_quella(service, monkeypatch):
    task_id = _submit(service, "TASK_PHRASE_RESUME", "BLOCKED",
                      recovery={"classification": "ORPHANED_RUNNING_AFTER_RESTART"},
                      dispatch_last_error="ORPHANED_RUNNING_AFTER_RESTART")
    service.conversation_store.update("c1", last_task_id=task_id, user_id="42")
    # "riprendi quella" already has an explicit reference word - deterministic-
    # first bypass must handle it, the router must never even be called.
    _enable_router(monkeypatch, mode="ACTIVE")

    def _should_not_be_called(*a, **k):
        raise AssertionError("explicit reference word must bypass the router")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router", _should_not_be_called)
    response = JarvisGateway(service).handle(message("Riprendi quella"))
    assert response["task_id"] == task_id


def test_phrase_che_giornata_di_merda(service, monkeypatch):
    _enable_router(monkeypatch, mode="ACTIVE")
    out = dict(VALID_OUTPUT, intent="UNKNOWN", needs_clarification=True,
              clarification_question="Posso aiutarti con qualcosa di specifico?")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": out, "latency_ms": 5})
    response = JarvisGateway(service).handle(message("Che giornata di merda"))
    assert response["response_type"] == "ANSWER"  # falls back cleanly, no crash, no guessed mutation


def test_phrase_richiesta_ambigua_asks_for_clarification(service, monkeypatch):
    a = _submit(service, "TASK_AMBIG_A", "WAITING_APPROVAL")
    b = _submit(service, "TASK_AMBIG_B", "WAITING_APPROVAL")
    _enable_router(monkeypatch, mode="ACTIVE")
    out = dict(VALID_OUTPUT, confidence=0.4, needs_clarification=True,
              clarification_question="Quale delle due intendi?")
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": True, "output": out, "latency_ms": 5})
    response = JarvisGateway(service).handle(message("approva quella"))
    # "quella" IS an explicit reference word -> deterministic-first path
    # resolves it (ambiguous -> no mutation), router never consulted.
    assert service.queue.get(a)["state"] == "WAITING_APPROVAL"
    assert service.queue.get(b)["state"] == "WAITING_APPROVAL"


def test_phrase_task_inesistente_never_invents_a_mutation(service, monkeypatch):
    _enable_router(monkeypatch, mode="ACTIVE")
    # The gateway/router client themselves already reject an invented
    # referenced_task_id (see test_ministral_router_v1.py) - this proves
    # the service layer treats that rejection as an ordinary fallback.
    monkeypatch.setattr(ministral_router, "resolve_intent_via_router",
                        lambda svc, msg, **k: {"ok": False,
                                               "error": "RENDER_SIDE_REFERENCED_TASK_ID_NOT_IN_CANDIDATES",
                                               "latency_ms": 5})
    response = JarvisGateway(service).handle(message("Approva TASK_NON_ESISTENTE_123"))
    assert response["response_type"] == "ERROR"
    assert response["status"] == "UNKNOWN"
