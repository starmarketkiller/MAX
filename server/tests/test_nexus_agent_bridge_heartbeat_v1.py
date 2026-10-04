"""BRIDGE_HEARTBEAT_DURING_EXECUTION_V1.

LocalBridge/nexus_agent_bridge.py is a standalone script (not a package),
loaded here via importlib - same pattern scripts/tests/*.py already uses
for scripts/classify_deploy_risk.py etc. This is the first dedicated test
file for this script; the only prior coverage was a source-text regression
guard in test_local_agent_bridge_v1.py (no subprocess/shell/git-push/deploy
in the file), which stays unaffected and untouched by this change.

BridgeClient.execute() used to send exactly one heartbeat per run_once()
cycle, BEFORE claiming/executing a job - a job that blocks inside
ollama_worker.call_local_model() for longer than the server's
HEARTBEAT_TTL (default 45s) made the server classify this bridge OFFLINE
even though it was genuinely still working. These tests drive a second,
independent background thread (_heartbeat_loop) that keeps sending
heartbeats on its own short interval for the entire duration of execute(),
sharing the same shutdown Event as the pre-existing lease-renewal thread
(_renew_loop, completely unmodified) without altering claim/lease/
idempotency semantics at all.
"""
import importlib.util
import json
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bridge_module = load("nexus_agent_bridge", "LocalBridge/nexus_agent_bridge.py")
BridgeClient = bridge_module.BridgeClient


class FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self):
        return self._body


class RecordingOpener:
    """Fake urllib opener - records every call by endpoint path, thread-safe
    since heartbeat/renew run on their own background threads concurrently
    with whatever the test's main thread is doing."""

    def __init__(self, *, heartbeat_raises=False):
        self.calls = []
        self._lock = threading.Lock()
        self.heartbeat_raises = heartbeat_raises

    def __call__(self, request, timeout=None):
        url = request.full_url
        with self._lock:
            self.calls.append(url)
        if "/heartbeat" in url:
            if self.heartbeat_raises:
                raise TimeoutError("simulated heartbeat network failure")
            return FakeResponse({"bridge_id": "test-bridge", "status": "ONLINE"})
        if "/claim" in url:
            return FakeResponse({"job": None})
        if "/renew" in url:
            return FakeResponse({"task_id": "x", "lease_expires_at": "2099-01-01T00:00:00+00:00"})
        if "/result" in url or "/failure" in url:
            return FakeResponse({"state": "WAITING_APPROVAL"})
        return FakeResponse({})

    def count(self, substring):
        with self._lock:
            return sum(1 for url in self.calls if substring in url)


def _client(opener, **overrides):
    kwargs = dict(base_url="https://nexus.example", bridge_id="pc-1", secret="s" * 48,
                  opener=opener, heartbeat_interval_seconds=0.05)
    kwargs.update(overrides)
    return BridgeClient(**kwargs)


def _job(task_id="TASK_X"):
    return {"task_id": task_id, "capability": "complex_code_change", "executor": "LOCAL_STRONG_MINISTRAL3B",
           "model": "ministral3b", "prompt": "fix it", "task_record": {}, "lease": {"token": "tok-1"}}


def test_long_job_keeps_heartbeating_past_a_short_interval(monkeypatch):
    opener = RecordingOpener()
    client = _client(opener)

    def slow_call(prompt, model):
        time.sleep(0.3)  # several multiples of the 0.05s heartbeat interval
        return {"success": True, "model": model, "response_text": "x", "error": None}

    monkeypatch.setattr(bridge_module.ollama_worker, "call_local_model", slow_call)
    monkeypatch.setattr(client.handler, "verify",
                        lambda record, text: type("V", (), {"passed": True,
                                                            "parsed_output": {"test_results": []}})())

    client.execute(_job())
    # At minimum the job duration (0.3s) divided by the interval (0.05s),
    # minus slack for scheduling jitter - comfortably more than the single
    # heartbeat run_once() used to send before this fix.
    assert opener.count("/heartbeat") >= 3


def test_heartbeat_thread_terminates_when_job_finishes(monkeypatch):
    opener = RecordingOpener()
    client = _client(opener)

    def quick_call(prompt, model):
        return {"success": True, "model": model, "response_text": "x", "error": None}

    monkeypatch.setattr(bridge_module.ollama_worker, "call_local_model", quick_call)
    monkeypatch.setattr(client.handler, "verify",
                        lambda record, text: type("V", (), {"passed": True,
                                                            "parsed_output": {"test_results": []}})())

    before = {t.ident for t in threading.enumerate()}
    client.execute(_job())
    time.sleep(0.2)  # generous margin past join(timeout=1) having already run
    after = {t.ident for t in threading.enumerate()}
    assert after - before == set()  # no heartbeat/renew thread left behind


def test_exception_in_job_still_stops_both_threads(monkeypatch):
    opener = RecordingOpener()
    client = _client(opener)

    def raising_call(prompt, model):
        raise RuntimeError("local model crashed")

    monkeypatch.setattr(bridge_module.ollama_worker, "call_local_model", raising_call)

    before = {t.ident for t in threading.enumerate()}
    with pytest.raises(RuntimeError):
        client.execute(_job())
    time.sleep(0.2)
    after = {t.ident for t in threading.enumerate()}
    assert after - before == set()  # finally still joined both threads


def test_heartbeat_failure_does_not_abort_or_duplicate_the_job(monkeypatch):
    opener = RecordingOpener(heartbeat_raises=True)
    client = _client(opener)

    def slow_call(prompt, model):
        time.sleep(0.2)
        return {"success": True, "model": model, "response_text": "x", "error": None}

    monkeypatch.setattr(bridge_module.ollama_worker, "call_local_model", slow_call)
    monkeypatch.setattr(client.handler, "verify",
                        lambda record, text: type("V", (), {"passed": True,
                                                            "parsed_output": {"test_results": []}})())

    client.execute(_job())  # must not raise despite every heartbeat() call failing
    assert opener.count("/result") == 1  # exactly one submission, never doubled
    assert opener.count("/failure") == 0


def test_lease_renewal_cadence_is_independent_of_heartbeat_interval(monkeypatch):
    """_renew_loop is completely unmodified (still a fixed 60s wait) - a
    short job on a fast 0.05s heartbeat interval must produce heartbeat
    calls but never trigger a renew() call (60s away), proving the two
    background loops are genuinely independent, not accidentally merged."""
    opener = RecordingOpener()
    client = _client(opener)

    def quick_call(prompt, model):
        time.sleep(0.15)
        return {"success": True, "model": model, "response_text": "x", "error": None}

    monkeypatch.setattr(bridge_module.ollama_worker, "call_local_model", quick_call)
    monkeypatch.setattr(client.handler, "verify",
                        lambda record, text: type("V", (), {"passed": True,
                                                            "parsed_output": {"test_results": []}})())

    client.execute(_job())
    assert opener.count("/heartbeat") >= 2
    assert opener.count("/renew") == 0


def test_short_job_behaves_exactly_as_before_the_fix(monkeypatch):
    """A job that finishes before the first heartbeat interval elapses sends
    zero EXTRA heartbeats from the new loop - unchanged behaviour for the
    common case."""
    opener = RecordingOpener()
    client = _client(opener, heartbeat_interval_seconds=5)  # job finishes well before this

    def quick_call(prompt, model):
        return {"success": True, "model": model, "response_text": "x", "error": None}

    monkeypatch.setattr(bridge_module.ollama_worker, "call_local_model", quick_call)
    monkeypatch.setattr(client.handler, "verify",
                        lambda record, text: type("V", (), {"passed": True,
                                                            "parsed_output": {"test_results": []}})())

    client.execute(_job())
    assert opener.count("/heartbeat") == 0  # none from the loop; run_once() sends its own separately
    assert opener.count("/result") == 1


def test_run_once_full_cycle_still_claims_and_executes_normally(monkeypatch):
    """Regression: the ordinary run_once() cycle (heartbeat -> claim ->
    execute) is untouched end to end."""
    opener = RecordingOpener()
    client = _client(opener)
    job = _job()

    calls = {"n": 0}
    def claim_once():
        calls["n"] += 1
        return job if calls["n"] == 1 else None
    monkeypatch.setattr(client, "claim", claim_once)

    def quick_call(prompt, model):
        return {"success": True, "model": model, "response_text": "x", "error": None}
    monkeypatch.setattr(bridge_module.ollama_worker, "call_local_model", quick_call)
    monkeypatch.setattr(client.handler, "verify",
                        lambda record, text: type("V", (), {"passed": True,
                                                            "parsed_output": {"test_results": []}})())

    worked = client.run_once()
    assert worked is True
    assert opener.count("/result") == 1

    idle = client.run_once()
    assert idle is False
