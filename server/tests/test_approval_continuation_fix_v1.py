"""Closure proofs for the four review findings. Original asserts stay in the first suite."""
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from jarvis_v1.free_coding_worker import (
    BINDING_SCHEMA, NEWLINE_POLICY, FreeCodingWorkerHandler, baseline_digest, binding_digest,
    file_digest, proposal_digest)
from jarvis_v1.service import JarvisService
from orchestrator_v1.core.orchestrator import Orchestrator
from jarvis_v1.gateway import JarvisGateway
from test_approval_continuation_v1 import (
    FIXED, FIXTURE, SOURCE, _approve, _events, _manifest, _message, _packet, _patch, _plant, _service)

CHILD = Path(__file__).with_name("approval_continuation_crash_child.py")
SERVER = Path(__file__).resolve().parents[1]


def _plant_allowed(service, task_id, patch, allowed):
    manifest = _manifest(task_id)
    manifest["files_allowed"] = allowed
    service.orchestrator.submit(
        manifest, action="conversational_programming",
        action_params={"test_commands": [["PYTHON", "-m", "pytest",
                                          "server/tests/test_sample_counter.py", "-q"]]})
    service.queue.transition(
        task_id, "WAITING_APPROVAL", result_packet=_packet(task_id),
        proposed_patch=patch, approval_effect="REQUEUE")


def _bound_patch(changes, baselines):
    return {
        "changes": changes,
        "test_results": [{"argv": ["PYTHON", "-m", "pytest", "server/tests/test_sample_counter.py", "-q"],
                          "returncode": 0, "stdout": "2 passed", "stderr": ""}],
        "baselines": baselines,
        "attempt": 0,
        "newline_policy": NEWLINE_POLICY,
        "proposal_sha256": proposal_digest(changes),
        "baseline_sha256": baseline_digest(baselines),
        "binding_schema": BINDING_SCHEMA,
        "binding_sha256": binding_digest(changes),
    }


def _reopen(tmp_path, project, monkeypatch):
    def _forbidden(*_args, **_kwargs):
        raise AssertionError("model call is not part of continuation")

    monkeypatch.setattr("core.orchestrator.ollama_worker.call_local_model", _forbidden)
    monkeypatch.setattr("jarvis_v1.service.is_ollama_reachable", lambda timeout=1: False)
    service = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"),
                            str(tmp_path / "conversation.json"))
    handler = FreeCodingWorkerHandler(project_root=project, workspace_root=tmp_path / "workspaces")
    service.orchestrator.register_local_handler("conversational_programming", handler)
    return service, handler


def test_same_process_lock_does_not_claim_cross_process_exclusion(tmp_path):
    orch = Orchestrator(queue_path=str(tmp_path / "q.json"), ledger_path=str(tmp_path / "l.jsonl"))
    assert type(orch._apply_guard) is type(threading.Lock())


def test_intent_is_stored_before_the_first_write(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_INTENT", patch)
    seen = {}
    original = Path.write_bytes

    def _write(self, data):
        if self.name == "sample_counter.py" and data == FIXED.encode("utf-8"):
            record = service.queue.get("TASK_INTENT")
            seen["intent"] = record.get("application_intent")
            seen["phase"] = record.get("application_phase")
        return original(self, data)

    monkeypatch.setattr(Path, "write_bytes", _write)
    response = _approve(service, "TASK_INTENT", patch)
    intent = seen["intent"]
    assert response["status"] == "COMPLETED"
    assert seen["phase"] == "INTENT_PERSISTED"
    assert intent["task_id"] == "TASK_INTENT"
    assert intent["binding_schema"] == BINDING_SCHEMA
    assert intent["binding_sha256"] == patch["binding_sha256"]
    assert intent["proposal_sha256"] == patch["proposal_sha256"]
    assert intent["baseline_sha256"] == patch["baseline_sha256"]
    assert intent["files"][0]["path"] == SOURCE
    assert intent["files"][0]["baseline_sha256"] == file_digest(before)
    assert intent["files"][0]["proposal_content_sha256"] == file_digest(FIXED.encode("utf-8"))


def test_duplicate_paths_and_old_digest_do_not_write(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_OLD", patch)
    missing = _message("TASK_OLD", patch)
    missing["metadata"].pop("binding_sha256")
    missing["metadata"].pop("binding_schema")
    reused = _approve(service, "TASK_OLD", patch, binding_sha256=patch["proposal_sha256"])
    refused = JarvisGateway(service).handle(missing)
    assert service.queue.get("TASK_OLD")["state"] == "WAITING_APPROVAL"
    assert (project / SOURCE).read_bytes() == before
    assert refused["status"] != "COMPLETED"
    assert reused["status"] != "COMPLETED"
    assert _events(service, "TASK_OLD", "FILE_CHANGED") == []

    duplicated = _patch(FIXED, before)
    duplicated["changes"] = [
        {"path": SOURCE, "content": FIXED},
        {"path": SOURCE, "content": "def next_value(current):\n    return current\n"},
    ]
    duplicated["proposal_sha256"] = proposal_digest(duplicated["changes"])
    duplicated["binding_sha256"] = "ab" * 32
    _plant(service, "TASK_DUP", duplicated)
    response = _approve(service, "TASK_DUP", duplicated)
    assert response["status"] != "COMPLETED"
    assert service.queue.get("TASK_DUP")["state"] == "WAITING_APPROVAL"
    assert (project / SOURCE).read_bytes() == before


def test_colliding_content_digest_requires_the_path_binding(tmp_path, monkeypatch):
    service, handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    (project / "a.py").write_bytes(b"BASE")
    (project / "b.py").write_bytes(b"BASE")
    shared = {
        SOURCE: file_digest(before),
        "a.py": file_digest(b"BASE"),
        "b.py": file_digest(b"BASE"),
    }
    left = _bound_patch([
        {"path": "a.py", "content": "AAA\0BBB"},
        {"path": "b.py", "content": "CCC"},
        {"path": SOURCE, "content": FIXED},
    ], shared)
    right = _bound_patch([
        {"path": "a.py", "content": "AAA"},
        {"path": "b.py", "content": "BBB\0CCC"},
        {"path": SOURCE, "content": FIXED},
    ], shared)
    assert left["proposal_sha256"] == right["proposal_sha256"]
    assert left["binding_sha256"] != right["binding_sha256"]
    allowed = [SOURCE, "a.py", "b.py"]
    _plant_allowed(service, "TASK_BIND2", right, allowed)
    denied = _approve(service, "TASK_BIND2", right, binding_sha256=left["binding_sha256"])
    assert denied["status"] != "COMPLETED"
    assert (project / "a.py").read_bytes() == b"BASE"
    assert (project / "b.py").read_bytes() == b"BASE"
    calls = []
    original = handler.command_runner

    def _runner(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    handler.command_runner = _runner
    applied = _approve(service, "TASK_BIND2", right)
    record = service.queue.get("TASK_BIND2")
    assert applied["status"] == "COMPLETED"
    assert calls == [1]
    assert (project / "a.py").read_bytes() == b"AAA"
    assert (project / "b.py").read_bytes() == b"BBB\0CCC"
    assert (project / SOURCE).read_bytes() == FIXED.encode("utf-8")
    assert record["application_receipt"]["binding_schema"] == BINDING_SCHEMA
    assert record["application_receipt"]["binding_sha256"] == right["binding_sha256"]
    assert record["application_receipt"]["proposal_sha256"] == right["proposal_sha256"]


def test_legacy_patch_accepts_only_a_new_v2_approval(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    stored = dict(patch)
    stored.pop("binding_schema")
    stored.pop("binding_sha256")
    _plant(service, "TASK_V2", stored)
    old = _message("TASK_V2", patch)
    old["metadata"].pop("binding_sha256")
    old["metadata"].pop("binding_schema")
    refused = JarvisGateway(service).handle(old)
    assert refused["status"] != "COMPLETED"
    assert (project / SOURCE).read_bytes() == before
    response = _approve(service, "TASK_V2", patch)
    record = service.queue.get("TASK_V2")
    assert response["status"] == "COMPLETED"
    assert record["proposed_patch"]["binding_schema"] == BINDING_SCHEMA
    assert record["proposed_patch"]["binding_sha256"] == patch["binding_sha256"]
    assert (project / SOURCE).read_bytes() == FIXED.encode("utf-8")


def test_two_approvals_cannot_roll_back_the_completed_file(tmp_path, monkeypatch):
    service, handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_RACE", patch)
    calls = []
    original = handler.command_runner

    def _runner(*args, **kwargs):
        calls.append(args[0])
        if len(calls) > 1:
            return subprocess.CompletedProcess(args[0], 1, "", "second approval")
        return original(*args, **kwargs)

    handler.command_runner = _runner
    results = []

    def _run():
        try:
            results.append(_approve(service, "TASK_RACE", patch))
        except Exception as exc:
            results.append(exc)

    first = threading.Thread(target=_run)
    second = threading.Thread(target=_run)
    first.start()
    second.start()
    first.join(90)
    second.join(90)
    record = service.queue.get("TASK_RACE")
    assert not first.is_alive() and not second.is_alive()
    assert [item["status"] for item in results] == ["COMPLETED", "COMPLETED"]
    assert calls and len(calls) == 1
    assert record["state"] == "COMPLETED"
    assert (project / SOURCE).read_bytes() == FIXED.encode("utf-8")
    assert _events(service, "TASK_RACE", "TASK_FAILED") == []


def _recover(tmp_path, project, monkeypatch, patch, task_id):
    reopened, _handler = _reopen(tmp_path, project, monkeypatch)
    parked = reopened.queue.get(task_id)
    assert parked["state"] == "WAITING_APPROVAL"
    assert parked["application_phase"] == "WRITTEN_UNFINALIZED"
    assert "application_receipt" not in parked
    assert (project / SOURCE).read_bytes() == FIXED.encode("utf-8")
    response = _approve(reopened, task_id, patch)
    record = reopened.queue.get(task_id)
    assert response["status"] == "COMPLETED"
    assert record["state"] == "COMPLETED"
    assert record["application_receipt"]["applied_sha256"] == file_digest(FIXED.encode("utf-8"))
    assert record["application_receipt"]["binding_sha256"] == patch["binding_sha256"]
    assert (project / SOURCE).read_bytes() == FIXED.encode("utf-8")


def test_ledger_error_after_write_recovers_on_reopen(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_LEDGER", patch)
    original = service.ledger.append

    def _append(event_type, task_id, payload, actor="orchestrator_v1_core"):
        if event_type == "FILE_CHANGED":
            raise OSError("injected ledger failure")
        return original(event_type, task_id, payload, actor=actor)

    service.ledger.append = _append
    response = _approve(service, "TASK_LEDGER", patch)
    assert response["status"] == "WAITING_APPROVAL"
    assert "application_receipt" not in service.queue.get("TASK_LEDGER")
    _recover(tmp_path, project, monkeypatch, patch, "TASK_LEDGER")


def test_transition_error_after_write_recovers_on_reopen(tmp_path, monkeypatch):
    service, _handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_TRANSITION", patch)
    original = service.queue.transition

    def _transition(task_id, new_state, **updates):
        if new_state == "COMPLETED":
            raise OSError("injected transition failure")
        return original(task_id, new_state, **updates)

    service.queue.transition = _transition
    response = _approve(service, "TASK_TRANSITION", patch)
    record = service.queue.get("TASK_TRANSITION")
    assert response["status"] == "WAITING_APPROVAL"
    assert record["state"] == "WAITING_APPROVAL"
    assert _events(service, "TASK_TRANSITION", "TASK_COMPLETED")
    _recover(tmp_path, project, monkeypatch, patch, "TASK_TRANSITION")


def test_failed_rollback_records_the_residual_and_blocks_retry(tmp_path, monkeypatch):
    service, handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_ROLLBACK", patch)
    handler.command_runner = lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, "", "red")
    original_write = Path.write_bytes
    original_read = Path.read_bytes
    phase = {"restore": False}

    def _write(self, data):
        if data == before:
            phase["restore"] = True
            raise OSError("injected rollback failure")
        return original_write(self, data)

    def _read(self):
        if phase["restore"] and self.name == "sample_counter.py":
            raise OSError("residual unreadable")
        return original_read(self)

    monkeypatch.setattr(Path, "write_bytes", _write)
    monkeypatch.setattr(Path, "read_bytes", _read)
    response = _approve(service, "TASK_ROLLBACK", patch)
    record = service.queue.get("TASK_ROLLBACK")
    residual = record["application_residuals"][0]
    assert response["status"] == "FAILED"
    assert record["state"] == "FAILED"
    assert record["result_packet"]["decision"] == "FAILED"
    assert record["rollback_verified"] is False
    assert record["application_recovery"] == "BLOCKED"
    assert residual["path"] == SOURCE
    assert residual["residual"] == "UNKNOWN"
    assert residual["observed_sha256"] is None
    assert residual["restored"] is False
    assert "application_receipt" not in record
    phase["restore"] = False
    monkeypatch.undo()
    again = _approve(service, "TASK_ROLLBACK", patch)
    assert again["status"] != "COMPLETED"
    assert service.queue.get("TASK_ROLLBACK")["state"] == "FAILED"


def test_observable_rollback_failure_keeps_the_read_hash(tmp_path, monkeypatch):
    service, handler, project = _service(tmp_path, monkeypatch)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    _plant(service, "TASK_OBSERVED", patch)
    handler.command_runner = lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, "", "red")
    original_write = Path.write_bytes

    def _write(self, data):
        if data == before:
            raise OSError("injected rollback failure")
        return original_write(self, data)

    monkeypatch.setattr(Path, "write_bytes", _write)
    response = _approve(service, "TASK_OBSERVED", patch)
    record = service.queue.get("TASK_OBSERVED")
    residual = record["application_residuals"][0]
    assert response["status"] == "FAILED"
    assert record["rollback_verified"] is False
    assert residual["residual"] == "OTHER"
    assert residual["observed_sha256"] == file_digest(FIXED.encode("utf-8"))
    assert (project / SOURCE).read_bytes() == FIXED.encode("utf-8")
    assert "application_receipt" not in record


def test_killed_child_is_recovered_after_reopen(tmp_path, monkeypatch):
    project = tmp_path / "project"
    shutil.copytree(FIXTURE, project)
    before = (project / SOURCE).read_bytes()
    patch = _patch(FIXED, before)
    ready = tmp_path / "ready"
    log_path = tmp_path / "child.log"
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [sys.executable, str(CHILD), str(tmp_path), str(project), str(ready)],
            cwd=str(SERVER),
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            stdout=log, stderr=subprocess.STDOUT)
    deadline = time.time() + 90
    while time.time() < deadline:
        if ready.is_file() and ready.read_text(encoding="utf-8") == "ready":
            break
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    assert ready.is_file() and ready.read_text(encoding="utf-8") == "ready", log_path.read_text(encoding="utf-8")
    proc.kill()
    proc.wait(timeout=20)
    assert proc.returncode not in (0, None)
    parked = JarvisService(str(tmp_path / "queue.json"), str(tmp_path / "ledger.jsonl"),
                           str(tmp_path / "conversation.json")).queue.get("TASK_CRASH")
    assert parked["state"] == "WAITING_APPROVAL"
    assert parked["application_phase"] == "WRITTEN_UNFINALIZED"
    assert parked["application_intent"]["binding_sha256"] == patch["binding_sha256"]
    assert "application_receipt" not in parked
    assert (project / SOURCE).read_bytes() == FIXED.encode("utf-8")
    reopened, _handler = _reopen(tmp_path, project, monkeypatch)
    response = _approve(reopened, "TASK_CRASH", patch)
    record = reopened.queue.get("TASK_CRASH")
    assert response["status"] == "COMPLETED"
    assert record["application_receipt"]["applied_binding_sha256"] == patch["binding_sha256"]
    assert (project / SOURCE).read_bytes() == FIXED.encode("utf-8")
    assert _events(reopened, "TASK_CRASH", "TASK_COMPLETED")
