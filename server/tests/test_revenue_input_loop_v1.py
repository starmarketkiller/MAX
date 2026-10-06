import inspect

from fastapi.testclient import TestClient

import app as backend
from funding_v1 import revenue_automation


class _PreflightPass:
    warnings = []

    @staticmethod
    def raise_for_status():
        return None


class _Runner:
    def __init__(self):
        self.running = False
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1
        self.running = True
        return True

    def stop(self):
        self.stopped += 1
        self.running = False
        return True

    def status(self):
        return {"running": self.running, "last_tick_at": None,
                "last_error_class": None, "interval_seconds": 60}


def test_production_startup_and_shutdown_wiring_is_feature_gated(monkeypatch):
    runner = _Runner()
    monkeypatch.setattr(backend, "REVENUE_AUTOMATION_RUNNER", runner)
    monkeypatch.setattr(backend, "REVENUE_AUTOMATION_ENABLED", True)
    monkeypatch.setattr(backend, "QUEUE_DISPATCHER_ENABLED", False)
    monkeypatch.setattr(backend, "SEED_ON_START", False)
    monkeypatch.setattr(backend, "DUKASCOPY_AUTOFETCH", False)
    monkeypatch.setattr(backend, "security_preflight", lambda: _PreflightPass())
    monkeypatch.setattr(backend, "init_db", lambda: None)
    monkeypatch.setattr(backend.JOB_STORE, "reap_orphans", lambda: 0)
    backend._startup()
    assert runner.started == 1 and runner.running is True
    backend._shutdown()
    assert runner.stopped == 1 and runner.running is False


def test_production_runner_start_failure_is_isolated(monkeypatch):
    class Broken(_Runner):
        def start(self):
            raise RuntimeError("secret=not-logged")
    monkeypatch.setattr(backend, "REVENUE_AUTOMATION_RUNNER", Broken())
    monkeypatch.setattr(backend, "REVENUE_AUTOMATION_ENABLED", True)
    monkeypatch.setattr(backend, "QUEUE_DISPATCHER_ENABLED", False)
    monkeypatch.setattr(backend, "SEED_ON_START", False)
    monkeypatch.setattr(backend, "DUKASCOPY_AUTOFETCH", False)
    monkeypatch.setattr(backend, "security_preflight", lambda: _PreflightPass())
    monkeypatch.setattr(backend, "init_db", lambda: None)
    monkeypatch.setattr(backend.JOB_STORE, "reap_orphans", lambda: 0)
    backend._startup()  # no exception: revenue loop is non-critical


def test_authenticated_api_intake_stays_at_prospect_layer(monkeypatch):
    observed = {}
    class Acquisition:
        def ingest(self, records, **kwargs):
            observed.update({"records": records, **kwargs})
            return {"accepted": ["PROSPECT_1"], "duplicates": [], "rejected": []}
    monkeypatch.setattr(backend, "REVENUE_ACQUISITION", Acquisition())
    backend.app.dependency_overrides[backend.require_mutation] = lambda: "tester"
    try:
        response = TestClient(backend.app).post("/api/revenue/prospects/intake", json={
            "source": "AUTHORIZED_API", "source_reference": "batch:1",
            "prospects": [{"display_name": "Example", "evidence": ["Observed"]}]})
    finally:
        backend.app.dependency_overrides.pop(backend.require_mutation, None)
    assert response.status_code == 200
    assert response.json()["accepted"] == ["PROSPECT_1"]
    assert observed["source"] == "AUTHORIZED_API"
    assert "lead" not in response.text.casefold()


def test_runtime_has_no_email_payment_or_lifecycle_execution_path():
    source = inspect.getsource(revenue_automation)
    assert "smtplib" not in source
    assert "record_payment(" not in source
    assert "record_revenue(" not in source
    assert "transition_lead(" not in source
    assert "send_message(" not in source


def test_jarvis_sink_emits_canonical_attention_event_and_safe_error_summary(monkeypatch):
    ledger_events, pushes = [], []
    monkeypatch.setattr(backend.JARVIS_SERVICE.ledger, "append",
                        lambda event_type, task_id, payload, actor=None:
                        ledger_events.append((event_type, task_id, payload)))
    monkeypatch.setattr(backend.JARVIS_TELEGRAM, "allowed_users", {"42"})
    monkeypatch.setattr(backend, "_jarvis_proactive_notify",
                        lambda chat_id, response: pushes.append((chat_id, response)))
    backend._revenue_jarvis_sink({
        "type": "REVENUE_AUTOMATION_DEGRADED",
        "event_type": "REVENUE_RUNNER_ERROR", "failure_class": "RuntimeError"})
    assert ledger_events[0][0] == "REVENUE_RUNNER_ERROR"
    assert pushes[0][0] == "42"
    assert "degradato" in pushes[0][1]["summary"]
    assert "secret" not in str(pushes[0][1]).casefold()
