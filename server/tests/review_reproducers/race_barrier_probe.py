"""Force both approvals past the baseline check before either writes."""
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

REVIEW = Path(r"C:\Users\User\ClaudeWork\MAX_approval_review_b0a55c6")
sys.path.insert(0, str(REVIEW / "server"))

import pathlib
import jarvis_v1.service as service_module
import core.orchestrator as orchestrator_module
from jarvis_v1.free_coding_worker import file_digest
from independent_review_probe import (
    FIXED, SOURCE, _approve, _copy_project, _make_patch, _plant, _service, _snapshot)

orchestrator_module.ollama_worker.call_local_model = lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("model"))
service_module.is_ollama_reachable = lambda timeout=1: False

root = Path(tempfile.mkdtemp())
project = _copy_project(root)
source = (project / SOURCE).read_bytes()
patch = _make_patch([{"path": SOURCE, "content": FIXED}], {SOURCE: file_digest(source)})
reads = {"n": 0}
lock = threading.Lock()
barrier = threading.Barrier(2)
original_read = pathlib.Path.read_bytes
calls = {"n": 0}
call_lock = threading.Lock()


def read_bytes(self):
    data = original_read(self)
    if self.name == "sample_counter.py" and project in self.parents and data == source:
        with lock:
            reads["n"] += 1
            mine = reads["n"]
        if mine <= 2:
            barrier.wait(8)
    return data


def runner(*_args, **_kwargs):
    with call_lock:
        calls["n"] += 1
        mine = calls["n"]
    if mine == 1:
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")
    deadline = datetime.now(timezone.utc).timestamp() + 8
    while datetime.now(timezone.utc).timestamp() < deadline:
        if service.queue.get("TASK_FORCE")["state"] == "COMPLETED":
            break
        threading.Event().wait(0.02)
    return SimpleNamespace(returncode=1, stdout="", stderr="injected")


pathlib.Path.read_bytes = read_bytes
try:
    service, _handler = _service(root, project, runner=runner)
    _plant(service, "TASK_FORCE", patch, [SOURCE])
    outcomes = []

    def run(suffix):
        try:
            outcomes.append((suffix, _approve(service, "TASK_FORCE", patch, suffix)["status"], None))
        except Exception as exc:
            outcomes.append((suffix, None, f"{type(exc).__name__}: {exc}"))

    threads = [threading.Thread(target=run, args=(suffix,)) for suffix in ("one", "two")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(20)
    snap = _snapshot(service, "TASK_FORCE", project)
    print({
        "outcomes": outcomes,
        "reads": reads["n"],
        "runner_calls": calls["n"],
        "state": snap["state"],
        "decision": snap["decision"],
        "error": snap["dispatch_last_error"],
        "receipt": snap["receipt"] is not None,
        "events": snap["events"],
        "file_sha256": snap["file_sha256"],
        "proposal_sha256": file_digest(FIXED.encode()),
        "baseline_sha256": file_digest(source),
        "receipt_applied": None if snap["receipt"] is None else snap["receipt"].get("applied_sha256"),
        "file_is_proposal": snap["file_sha256"] == file_digest(FIXED.encode()),
        "file_is_baseline": snap["file_sha256"] == file_digest(source),
    })
finally:
    pathlib.Path.read_bytes = original_read
