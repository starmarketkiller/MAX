"""Independent probes for PR #78. Does not modify product source."""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

REVIEW = Path(r"C:\Users\User\ClaudeWork\MAX_approval_review_b0a55c6")
sys.path.insert(0, str(REVIEW / "server"))

import jarvis_v1.service as service_module
import core.orchestrator as orchestrator_module
from jarvis_v1.free_coding_worker import (
    NEWLINE_POLICY, FreeCodingWorkerHandler, baseline_digest, file_digest, proposal_digest)
from jarvis_v1.gateway import JarvisGateway
from jarvis_v1.service import JarvisService
from orchestrator_v1.core.ledger import EventLedger
from orchestrator_v1.core.result_packet import build_result_packet
from orchestrator_v1.core.task_queue import TaskQueue

FIXTURE = REVIEW / "server" / "tests" / "fixtures" / "approval_continuation_a2"
SOURCE = "protocol_a_fixture/sample_counter.py"
TEST = "server/tests/test_sample_counter.py"
FIXED = (
    "def next_value(current):\n"
    "    \"\"\"Return the integer that follows current.\"\"\"\n"
    "    return current + 1"
)
MODEL_CALLS = {"n": 0}
RESULTS = []


def _forbid_model(*_args, **_kwargs):
    MODEL_CALLS["n"] += 1
    raise AssertionError("model call")


orchestrator_module.ollama_worker.call_local_model = _forbid_model
service_module.is_ollama_reachable = lambda timeout=1: False


def _record(name, expected, observed, passed, refs):
    RESULTS.append({
        "name": name, "expected": expected, "observed": observed,
        "passed": passed, "refs": refs,
    })


def _manifest(task_id, allowed):
    return {
        "task_id": task_id, "title": "review probe", "objective": "binding",
        "task_type": "CODE", "priority": "NORMAL", "risk_level": "A0",
        "scientific_risk": "NONE", "code_risk": "NONE", "financial_risk": "NONE",
        "required_capabilities": ["small_python_functions"],
        "deterministic_tools_available": False, "repo_scope": "isolated",
        "files_allowed": allowed, "files_forbidden": ["MQL5/**"],
        "dependencies": [], "blockers": [], "expected_artifacts": ["RESULT_PACKET_V1"],
        "success_criteria": ["applied bytes"], "verifier": "free_coding_worker_v1",
        "estimated_complexity": "TRIVIAL", "estimated_runtime": "1m",
        "premium_allowed": False, "preferred_executor": "TIER1_LOCAL_CHEAP",
        "fallback_executors": [], "approval_required": "REVIEW_REQUIRED",
        "created_by": "jarvis:42", "created_at": "2026-11-08T17:00:00Z",
        "tenant_id": "tenant-1", "account_scope_id": None,
    }


def _packet(task_id):
    now = datetime.now(timezone.utc).isoformat()
    return build_result_packet(
        task_id=task_id, executor="LOCAL_STRONG_MINISTRAL3B", start_time=now, end_time=now,
        files_read=[], files_changed=[], tools_or_commands=["review-probe"],
        artifacts_created=[], tests_ran=True, tests_passed=1, tests_failed=0,
        verifier_ran=True, verifier_passed=True, verifier_errors=[], commit=None,
        push_status="NOT_APPLICABLE", decision="PATCH_READY_AWAITING_APPROVAL",
        confidence="MEDIUM", limitations=["sandbox only"], unresolved_issues=[],
        suggested_next_tasks=[], escalation_needed=False)


def _service(root, project, runner=None):
    service = JarvisService(str(root / "queue.json"), str(root / "ledger.jsonl"),
                            str(root / "conversation.json"))
    handler = FreeCodingWorkerHandler(
        project_root=project, workspace_root=root / "workspaces", command_runner=runner)
    service.orchestrator.register_local_handler("conversational_programming", handler)
    return service, handler


def _plant(service, task_id, patch, allowed):
    service.orchestrator.submit(
        _manifest(task_id, allowed), action="conversational_programming",
        action_params={"test_commands": [["PYTHON", "-m", "pytest", TEST, "-q"]]})
    service.queue.transition(
        task_id, "WAITING_APPROVAL", result_packet=_packet(task_id),
        proposed_patch=patch, approval_effect="REQUEUE")


def _message(task_id, patch, suffix="a"):
    return {
        "message_id": f"m-{task_id}-{suffix}", "user_id": "42", "channel": "TEST",
        "conversation_id": "c-review", "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_type": "TEXT", "text": "APPROVE", "attachments": [], "reply_to": None,
        "request_class": "APPROVAL", "priority": "HIGH",
        "metadata": {
            "task_id": task_id, "approval_action": "APPROVE",
            "attempt": patch["attempt"], "proposal_sha256": patch["proposal_sha256"],
            "baseline_sha256": patch["baseline_sha256"],
        },
    }


def _approve(service, task_id, patch, suffix="a"):
    return JarvisGateway(service).handle(_message(task_id, patch, suffix))


def _make_patch(changes, baselines, attempt=0, digest=None):
    return {
        "changes": changes,
        "test_results": [{"argv": ["PYTHON", "-m", "pytest", TEST, "-q"], "returncode": 0,
                          "stdout": "2 passed", "stderr": ""}],
        "baselines": baselines,
        "attempt": attempt,
        "newline_policy": NEWLINE_POLICY,
        "proposal_sha256": digest if digest is not None else proposal_digest(changes),
        "baseline_sha256": baseline_digest(baselines),
    }


def _ok_runner(*_args, **_kwargs):
    return SimpleNamespace(returncode=0, stdout="stub-pass", stderr="")


def _copy_project(root):
    project = root / "project"
    shutil.copytree(FIXTURE, project)
    return project


def _sha(path):
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def probe_fixture_hashes():
    source_sha, source_n = _sha(FIXTURE / "protocol_a_fixture" / "sample_counter.py")
    test_sha, test_n = _sha(FIXTURE / "server" / "tests" / "test_sample_counter.py")
    proposal = FIXED.encode("utf-8")
    observed = {
        "source": [source_sha, source_n],
        "test": [test_sha, test_n],
        "proposal": [hashlib.sha256(proposal).hexdigest(), len(proposal), proposal.count(b"\r")],
    }
    expected = {
        "source": ["264700c5d857c1edddb95cba17e081e5ab7ada7f1a23a3e41031e3cc7b9f56b4", 98],
        "test": ["e98023b76671c81832034ab8dce684ce60f5aadc6766d3b06191e6baa21cb36f", 600],
        "proposal": ["feecd4e53946235ac4c35706bd9f28f13419a2425d75fbf057accfcb349a1806", 98, 0],
    }
    _record("fixture hashes match the evidence file", expected, observed, observed == expected,
            ["server/tests/approval_continuation_evidence_v1.json"])


def probe_two_file_binding():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        project = _copy_project(root)
        source = (project / SOURCE).read_bytes()
        (project / "protocol_a_fixture" / "a.py").write_bytes(source)
        (project / "protocol_a_fixture" / "b.py").write_bytes(source)
        paths = ["protocol_a_fixture/a.py", "protocol_a_fixture/b.py", SOURCE]
        baselines = {path: file_digest((project / path).read_bytes()) for path in paths}
        same_baseline = baselines["protocol_a_fixture/a.py"] == baselines["protocol_a_fixture/b.py"]
        first = [
            {"path": "protocol_a_fixture/a.py", "content": "ONE\n"},
            {"path": "protocol_a_fixture/b.py", "content": "TWO\n"},
            {"path": SOURCE, "content": FIXED},
        ]
        swapped = [
            {"path": "protocol_a_fixture/a.py", "content": "TWO\n"},
            {"path": "protocol_a_fixture/b.py", "content": "ONE\n"},
            {"path": SOURCE, "content": FIXED},
        ]
        digest_differs = proposal_digest(first) != proposal_digest(swapped)
        service, _handler = _service(root, project)
        patch = _make_patch(swapped, baselines, digest=proposal_digest(first))
        _plant(service, "TASK_SWAP", patch, paths)
        before = {path: (project / path).read_bytes() for path in paths}
        response = _approve(service, "TASK_SWAP", patch)
        after = {path: (project / path).read_bytes() for path in paths}
        observed = {
            "identical_baselines": same_baseline,
            "digest_differs": digest_differs,
            "status": response["status"],
            "state": service.queue.get("TASK_SWAP")["state"],
            "bytes_unchanged": after == before,
        }
        _record(
            "swapped path/content association with the original proposal hash",
            "identical baselines, different digest, refusal before any write",
            observed,
            same_baseline and digest_differs and response["status"] != "COMPLETED"
            and service.queue.get("TASK_SWAP")["state"] == "WAITING_APPROVAL" and after == before,
            ["server/jarvis_v1/free_coding_worker.py:58",
             "server/jarvis_v1/free_coding_worker.py:290",
             "server/jarvis_v1/service.py:1968"])

        collision_a = [
            {"path": "protocol_a_fixture/a.py", "content": "AAA\0BBB"},
            {"path": "protocol_a_fixture/b.py", "content": "CCC"},
            {"path": SOURCE, "content": FIXED},
        ]
        collision_b = [
            {"path": "protocol_a_fixture/a.py", "content": "AAA"},
            {"path": "protocol_a_fixture/b.py", "content": "BBB\0CCC"},
            {"path": SOURCE, "content": FIXED},
        ]
        shared = proposal_digest(collision_a)
        observed_digest = {
            "equal": shared == proposal_digest(collision_b),
            "associations_differ": collision_a != collision_b,
            "digest": shared,
        }
        _record(
            "proposal digest distinguishes path/content associations",
            "different path/content maps have different proposal hashes",
            observed_digest,
            observed_digest["equal"] is False,
            ["server/jarvis_v1/free_coding_worker.py:58"])

        service2, _handler2 = _service(root, project, runner=_ok_runner)
        planted = _make_patch(collision_b, baselines, digest=shared)
        _plant(service2, "TASK_NUL", planted, paths)
        response2 = _approve(service2, "TASK_NUL", planted)
        record = service2.queue.get("TASK_NUL")
        written = {
            "a": (project / "protocol_a_fixture" / "a.py").read_bytes(),
            "b": (project / "protocol_a_fixture" / "b.py").read_bytes(),
        }
        observed_apply = {
            "status": response2["status"],
            "state": record["state"],
            "written_a": written["a"],
            "written_b": written["b"],
            "receipt_hashes_equal": (
                (record.get("application_receipt") or {}).get("proposal_sha256")
                == (record.get("application_receipt") or {}).get("applied_sha256")),
        }
        accepted_other_association = (
            response2["status"] == "COMPLETED"
            and written["a"] == b"AAA" and written["b"] == b"BBB\0CCC")
        _record(
            "NUL-joined digest applied to the other association",
            "approval of the shared hash does not write a different path/content map",
            observed_apply,
            not accepted_other_association,
            ["server/jarvis_v1/free_coding_worker.py:58",
             "server/jarvis_v1/free_coding_worker.py:353"])


def probe_real_two_file_pytest():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        project = _copy_project(root)
        source = (project / SOURCE).read_bytes()
        (project / "protocol_a_fixture" / "a.py").write_bytes(source)
        (project / "protocol_a_fixture" / "b.py").write_bytes(source)
        paths = ["protocol_a_fixture/a.py", "protocol_a_fixture/b.py", SOURCE]
        baselines = {path: file_digest((project / path).read_bytes()) for path in paths}
        changes = [
            {"path": "protocol_a_fixture/a.py", "content": "alpha = 1\n"},
            {"path": "protocol_a_fixture/b.py", "content": "beta = 2\n"},
            {"path": SOURCE, "content": FIXED},
        ]
        service, _handler = _service(root, project)
        patch = _make_patch(changes, baselines)
        _plant(service, "TASK_TWO", patch, paths)
        response = _approve(service, "TASK_TWO", patch)
        observed = {
            "status": response["status"],
            "state": service.queue.get("TASK_TWO")["state"],
            "a": (project / "protocol_a_fixture" / "a.py").read_bytes().decode(),
            "b": (project / "protocol_a_fixture" / "b.py").read_bytes().decode(),
            "source_cr": b"\r" in (project / SOURCE).read_bytes(),
            "model_calls": MODEL_CALLS["n"],
        }
        _record(
            "two files with identical baselines apply through canonical pytest",
            "both files changed, source has no CR, state COMPLETED, no model call",
            observed,
            response["status"] == "COMPLETED" and observed["a"] == "alpha = 1\n"
            and observed["b"] == "beta = 2\n" and observed["source_cr"] is False
            and MODEL_CALLS["n"] == 0,
            ["server/jarvis_v1/free_coding_worker.py:323"])


def probe_cross_task_and_partial():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        project = _copy_project(root)
        source = (project / SOURCE).read_bytes()
        baselines = {SOURCE: file_digest(source)}
        changes = [{"path": SOURCE, "content": FIXED}]
        service, _handler = _service(root, project, runner=_ok_runner)
        patch_a = _make_patch(changes, baselines)
        patch_b = _make_patch([{"path": SOURCE, "content": FIXED + "\n"}], baselines)
        _plant(service, "TASK_A", patch_a, [SOURCE])
        _plant(service, "TASK_B", patch_b, [SOURCE])
        crossed = dict(patch_a)
        crossed["proposal_sha256"] = patch_b["proposal_sha256"]
        response = _approve(service, "TASK_A", crossed, "cross")
        partial = {"changes": changes, "test_results": [], "proposal_sha256": patch_a["proposal_sha256"]}
        _plant(service, "TASK_PARTIAL", partial, [SOURCE])
        partial_response = JarvisGateway(service).handle({
            "message_id": "m-partial", "user_id": "42", "channel": "TEST",
            "conversation_id": "c-review", "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_type": "TEXT", "text": "APPROVE", "attachments": [], "reply_to": None,
            "request_class": "APPROVAL", "priority": "HIGH",
            "metadata": {"task_id": "TASK_PARTIAL", "approval_action": "APPROVE",
                         "attempt": 0, "proposal_sha256": patch_a["proposal_sha256"],
                         "baseline_sha256": patch_a["baseline_sha256"]},
        })
        observed = {
            "cross_status": response["status"],
            "cross_state": service.queue.get("TASK_A")["state"],
            "file": (project / SOURCE).read_bytes() == source,
            "partial_status": partial_response["status"],
            "partial_state": service.queue.get("TASK_PARTIAL")["state"],
        }
        _record(
            "cross-task hash and partial binding",
            "both stay WAITING_APPROVAL and the file stays at the baseline",
            observed,
            response["status"] != "COMPLETED" and observed["cross_state"] == "WAITING_APPROVAL"
            and observed["file"] and partial_response["status"] != "COMPLETED"
            and observed["partial_state"] == "WAITING_APPROVAL",
            ["server/jarvis_v1/service.py:1968", "server/jarvis_v1/service.py:2058"])


def _snapshot(service, task_id, project, relative=SOURCE):
    fresh_queue = TaskQueue(service.queue.path)
    fresh_ledger = EventLedger(service.ledger.path)
    record = fresh_queue.get(task_id)
    events = [event["event_type"] for event in fresh_ledger.read_for_task(task_id)]
    return {
        "state": record["state"],
        "decision": (record.get("result_packet") or {}).get("decision"),
        "receipt": record.get("application_receipt"),
        "dispatch_last_error": record.get("dispatch_last_error"),
        "events": events,
        "file_sha256": file_digest((project / relative).read_bytes()),
    }


def probe_same_task_concurrency():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        project = _copy_project(root)
        source = (project / SOURCE).read_bytes()
        baselines = {SOURCE: file_digest(source)}
        patch = _make_patch([{"path": SOURCE, "content": FIXED}], baselines)
        calls = {"n": 0}
        lock = threading.Lock()

        def runner(*_args, **_kwargs):
            with lock:
                calls["n"] += 1
                mine = calls["n"]
            if mine == 1:
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")
            deadline = datetime.now(timezone.utc).timestamp() + 8
            while datetime.now(timezone.utc).timestamp() < deadline:
                if service.queue.get("TASK_RACE")["state"] == "COMPLETED":
                    break
                threading.Event().wait(0.02)
            return SimpleNamespace(returncode=1, stdout="", stderr="injected")

        service, _handler = _service(root, project, runner=runner)
        _plant(service, "TASK_RACE", patch, [SOURCE])
        outcomes = []

        def run(suffix):
            try:
                outcomes.append((suffix, _approve(service, "TASK_RACE", patch, suffix), None))
            except Exception as exc:
                outcomes.append((suffix, None, f"{type(exc).__name__}: {exc}"))

        threads = [threading.Thread(target=run, args=(suffix,)) for suffix in ("one", "two")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(15)
        snap = _snapshot(service, "TASK_RACE", project)
        final_is_proposal = snap["file_sha256"] == file_digest(FIXED.encode())
        final_is_baseline = snap["file_sha256"] == file_digest(source)
        observed = {
            "outcomes": [(name, None if response is None else response.get("status"), error)
                         for name, response, error in outcomes],
            "snapshot": snap,
            "final_is_proposal": final_is_proposal,
            "final_is_baseline": final_is_baseline,
            "runner_calls": calls["n"],
        }
        erased = snap["state"] == "COMPLETED" and final_is_baseline
        single_clean = (
            snap["state"] == "COMPLETED" and final_is_proposal
            and snap["receipt"] is not None
            and all(error is None and status == "COMPLETED" for _name, status, error in observed["outcomes"]))
        _record(
            "two concurrent approvals of the same task",
            "one COMPLETED application remains and a failing sibling does not roll it back",
            observed,
            single_clean and not erased,
            ["server/jarvis_v1/service.py:1981",
             "server/jarvis_v1/free_coding_worker.py:345",
             "server/orchestrator_v1/core/orchestrator.py:487"])


def probe_two_task_rollback_isolation():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        project = _copy_project(root)
        source = (project / SOURCE).read_bytes()
        (project / "protocol_a_fixture" / "other.py").write_bytes(b"other = 0\n")
        base_source = {SOURCE: file_digest(source)}
        base_other = {"protocol_a_fixture/other.py": file_digest(b"other = 0\n")}
        good = _make_patch([{"path": SOURCE, "content": FIXED}], base_source)
        bad = _make_patch([{"path": "protocol_a_fixture/other.py", "content": "other = 1\n"}], base_other)

        def runner(*_args, **_kwargs):
            if (project / "protocol_a_fixture" / "other.py").read_bytes() == b"other = 1\n":
                return SimpleNamespace(returncode=1, stdout="", stderr="red")
            return SimpleNamespace(returncode=0, stdout="ok", stderr="")

        service, _handler = _service(root, project, runner=runner)
        _plant(service, "TASK_GOOD", good, [SOURCE])
        _plant(service, "TASK_BAD", bad, ["protocol_a_fixture/other.py"])
        gate = threading.Barrier(2)

        def run(task_id, patch):
            gate.wait(5)
            return _approve(service, task_id, patch, task_id)

        results = {}

        def wrap(task_id, patch):
            try:
                results[task_id] = run(task_id, patch)["status"]
            except Exception as exc:
                results[task_id] = f"{type(exc).__name__}: {exc}"

        threads = [
            threading.Thread(target=wrap, args=("TASK_GOOD", good)),
            threading.Thread(target=wrap, args=("TASK_BAD", bad)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(20)
        observed = {
            "results": results,
            "good_state": service.queue.get("TASK_GOOD")["state"],
            "bad_state": service.queue.get("TASK_BAD")["state"],
            "source_is_proposal": (project / SOURCE).read_bytes() == FIXED.encode(),
            "other_is_baseline": (project / "protocol_a_fixture" / "other.py").read_bytes() == b"other = 0\n",
        }
        _record(
            "concurrent approvals of two tasks",
            "the passing task stays applied and the failing task rolls back only its own file",
            observed,
            observed["good_state"] == "COMPLETED" and observed["source_is_proposal"]
            and observed["bad_state"] == "FAILED" and observed["other_is_baseline"],
            ["server/jarvis_v1/free_coding_worker.py:364"])


def probe_post_write_persistence():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        project = _copy_project(root)
        source = (project / SOURCE).read_bytes()
        patch = _make_patch([{"path": SOURCE, "content": FIXED}], {SOURCE: file_digest(source)})
        service, _handler = _service(root, project, runner=_ok_runner)
        _plant(service, "TASK_LEDGER", patch, [SOURCE])
        original = service.ledger.append

        def break_completed(event_type, task_id, payload, actor="orchestrator_v1_core"):
            if event_type == "TASK_COMPLETED":
                raise OSError("injected after FILE_CHANGED")
            return original(event_type, task_id, payload, actor=actor)

        service.ledger.append = break_completed
        error = None
        try:
            _approve(service, "TASK_LEDGER", patch)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        snap = _snapshot(service, "TASK_LEDGER", project)
        retry_error = None
        try:
            retry = _approve(service, "TASK_LEDGER", patch, "retry")
            retry_status = retry["status"]
        except Exception as exc:
            retry_status = None
            retry_error = f"{type(exc).__name__}: {exc}"
        snap_after_retry = _snapshot(service, "TASK_LEDGER", project)
        observed = {
            "error": error, "snapshot": snap, "retry_status": retry_status,
            "retry_error": retry_error, "after_retry": snap_after_retry,
            "file_is_proposal": snap["file_sha256"] == file_digest(FIXED.encode()),
            "model_calls": MODEL_CALLS["n"],
        }
        reconcilable = (
            snap_after_retry["state"] == "COMPLETED"
            and snap_after_retry["receipt"] is not None
            and snap_after_retry["file_sha256"] == file_digest(FIXED.encode()))
        _record(
            "ledger failure after the file write",
            "reopening the store shows file, task and audit reconciled without a model call",
            observed,
            reconcilable and MODEL_CALLS["n"] == 0,
            ["server/orchestrator_v1/core/orchestrator.py:521"])

        root2 = Path(tempfile.mkdtemp())
        try:
            project2 = _copy_project(root2)
            source2 = (project2 / SOURCE).read_bytes()
            patch2 = _make_patch([{"path": SOURCE, "content": FIXED}], {SOURCE: file_digest(source2)})
            service2, _handler2 = _service(root2, project2, runner=_ok_runner)
            _plant(service2, "TASK_TRANSITION", patch2, [SOURCE])
            original_transition = service2.queue.transition

            def break_transition(task_id, new_state, **updates):
                if new_state == "COMPLETED":
                    raise OSError("injected transition")
                return original_transition(task_id, new_state, **updates)

            service2.queue.transition = break_transition
            error2 = None
            try:
                _approve(service2, "TASK_TRANSITION", patch2)
            except Exception as exc:
                error2 = f"{type(exc).__name__}: {exc}"
            snap2 = _snapshot(service2, "TASK_TRANSITION", project2)
            _record(
                "queue transition failure after TASK_COMPLETED is appended",
                "file, WAITING task and TASK_COMPLETED audit are not left contradictory",
                {"error": error2, "snapshot": snap2,
                 "file_is_proposal": snap2["file_sha256"] == file_digest(FIXED.encode())},
                not (snap2["file_sha256"] == file_digest(FIXED.encode())
                     and snap2["state"] != "COMPLETED"
                     and "TASK_COMPLETED" in snap2["events"]
                     and snap2["receipt"] is None),
                ["server/orchestrator_v1/core/orchestrator.py:521"])
        finally:
            shutil.rmtree(root2, ignore_errors=True)


def probe_write_and_rollback_failures():
    import pathlib
    original_write = pathlib.Path.write_bytes
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        project = _copy_project(root)
        source = (project / SOURCE).read_bytes()
        (project / "protocol_a_fixture" / "a.py").write_bytes(b"a = 0\n")
        paths = ["protocol_a_fixture/a.py", SOURCE]
        baselines = {path: file_digest((project / path).read_bytes()) for path in paths}
        changes = [
            {"path": "protocol_a_fixture/a.py", "content": "a = 1\n"},
            {"path": SOURCE, "content": FIXED},
        ]
        patch = _make_patch(changes, baselines)
        service, _handler = _service(root, project, runner=_ok_runner)
        _plant(service, "TASK_WRITE", patch, paths)
        seen = {"n": 0}

        def fail_second(self, data):
            if project in self.parents:
                seen["n"] += 1
                if seen["n"] == 2:
                    raise OSError("injected write failure")
            return original_write(self, data)

        pathlib.Path.write_bytes = fail_second
        try:
            response = _approve(service, "TASK_WRITE", patch)
            error = None
        except Exception as exc:
            response = None
            error = f"{type(exc).__name__}: {exc}"
        finally:
            pathlib.Path.write_bytes = original_write
        record = service.queue.get("TASK_WRITE")
        observed = {
            "status": None if response is None else response.get("status"),
            "error": error,
            "state": record["state"],
            "decision": (record.get("result_packet") or {}).get("decision"),
            "receipt": record.get("application_receipt"),
            "error_field": record.get("dispatch_last_error"),
            "a": (project / "protocol_a_fixture" / "a.py").read_bytes(),
            "source": (project / SOURCE).read_bytes(),
        }
        _record(
            "failure during the second file write",
            "FAILED, no receipt, both files back at their baseline, residual named in the record",
            observed,
            record["state"] == "FAILED" and record.get("application_receipt") is None
            and (record.get("result_packet") or {}).get("decision") != "COMPLETED"
            and observed["a"] == b"a = 0\n" and observed["source"] == source
            and bool(record.get("dispatch_last_error")),
            ["server/jarvis_v1/free_coding_worker.py:345",
             "server/orchestrator_v1/core/orchestrator.py:492"])

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        project = _copy_project(root)
        source = (project / SOURCE).read_bytes()
        patch = _make_patch([{"path": SOURCE, "content": FIXED}], {SOURCE: file_digest(source)})

        def fail_runner(*_args, **_kwargs):
            return SimpleNamespace(returncode=1, stdout="", stderr="red")

        service, _handler = _service(root, project, runner=fail_runner)
        _plant(service, "TASK_ROLLBACK", patch, [SOURCE])

        def fail_restore(self, data):
            if self.name == "sample_counter.py" and data == source:
                raise OSError("injected rollback failure")
            return original_write(self, data)

        pathlib.Path.write_bytes = fail_restore
        try:
            try:
                response = _approve(service, "TASK_ROLLBACK", patch)
                error = None
            except Exception as exc:
                response = None
                error = f"{type(exc).__name__}: {exc}"
        finally:
            pathlib.Path.write_bytes = original_write
        snap = _snapshot(service, "TASK_ROLLBACK", project)
        observed = {
            "status": None if response is None else response.get("status"),
            "error": error,
            "snapshot": snap,
            "file_is_proposal": snap["file_sha256"] == file_digest(FIXED.encode()),
            "file_is_baseline": snap["file_sha256"] == file_digest(source),
        }
        reported = snap["state"] == "FAILED" and snap["dispatch_last_error"] and snap["receipt"] is None
        no_false_completed = snap["state"] != "COMPLETED" and snap["decision"] != "COMPLETED"
        residual_explicit = (not observed["file_is_proposal"]) or bool(snap["dispatch_last_error"])
        _record(
            "failure during rollback",
            "no COMPLETED, and any leftover proposal bytes are named on the reopened record",
            observed,
            no_false_completed and reported and residual_explicit and not observed["file_is_proposal"],
            ["server/jarvis_v1/free_coding_worker.py:364",
             "server/orchestrator_v1/core/orchestrator.py:487"])


def main():
    probe_fixture_hashes()
    probe_two_file_binding()
    probe_real_two_file_pytest()
    probe_cross_task_and_partial()
    probe_same_task_concurrency()
    probe_two_task_rollback_isolation()
    probe_post_write_persistence()
    probe_write_and_rollback_failures()
    destination = Path(r"C:\Users\User\ClaudeWork\MAX_approval_review_probes\probe_results.json")
    destination.write_text(json.dumps({
        "model_calls": MODEL_CALLS["n"],
        "results": RESULTS,
    }, indent=2, default=str), encoding="utf-8")
    failed = [item["name"] for item in RESULTS if not item["passed"]]
    print(json.dumps({"model_calls": MODEL_CALLS["n"], "failed": failed,
                      "count": len(RESULTS)}, indent=2))


if __name__ == "__main__":
    main()
