#!/usr/bin/env python3
"""Durable, single-concurrency queue dispatcher for Orchestrator V1.

The dispatcher only claims QUEUED records and calls Orchestrator.process_task.
Routing, approvals, local/premium policy and result construction remain owned by
the existing Orchestrator. Ambiguous RUNNING work after a crash is blocked,
never replayed automatically.
"""
from __future__ import annotations

import os
import re
import threading
import time
import uuid


def _sanitized_error(exc):
    """Useful diagnostic without filesystem paths, bearer values or long payloads."""
    message = str(exc).replace("\r", " ").replace("\n", " ")[:300]
    message = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", message)
    message = re.sub(r"(?i)(token|secret|password)=([^\s,;]+)", r"\1=[REDACTED]", message)
    message = re.sub(r"[A-Za-z]:\\[^\s]+", "[PATH]", message)
    message = re.sub(r"(?<!:)\/(?:[^\s\/]+\/)+[^\s]+", "[PATH]", message)
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


class DurableQueueDispatcher:
    def __init__(self, orchestrator, *, poll_seconds=2.0, lease_seconds=900,
                 max_backoff_seconds=60, shutdown_timeout_seconds=25,
                 provider_connector=None):
        self.orchestrator = orchestrator
        self.queue = orchestrator.queue
        self.ledger = orchestrator.ledger
        self.poll_seconds = max(0.05, float(poll_seconds))
        self.lease_seconds = max(30, int(lease_seconds))
        self.max_backoff_seconds = max(1, int(max_backoff_seconds))
        self.shutdown_timeout_seconds = max(1, int(shutdown_timeout_seconds))
        self.provider_connector = provider_connector
        self.owner_id = f"dispatcher:{os.getpid()}:{uuid.uuid4().hex[:12]}"
        self._stop = threading.Event()
        self._thread = None

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())

    def start(self):
        if self.running:
            return False
        self._stop.clear()
        orphaned = self.queue.recover_orphaned_running(self.owner_id)
        for task_id in orphaned:
            self.ledger.append("TASK_ORPHANED", task_id,
                {"classification": "ORPHANED_RUNNING_AFTER_RESTART",
                 "action": "BLOCKED_FAIL_CLOSED"}, actor="durable_queue_dispatcher_v1")
            self.ledger.append("TASK_BLOCKED", task_id,
                {"reason": "orphaned RUNNING task after process restart; manual review required"},
                actor="durable_queue_dispatcher_v1")
        self.ledger.append("DISPATCHER_STARTED", None,
            {"owner_id": self.owner_id, "max_concurrency": 1,
             "orphaned_running_count": len(orphaned)}, actor="durable_queue_dispatcher_v1")
        self._thread = threading.Thread(target=self._run_loop,
                                        name="nexus-durable-dispatcher", daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()  # stop accepting new work before draining current task
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=self.shutdown_timeout_seconds)
        drained = not self.running
        self.ledger.append("DISPATCHER_STOPPED", None,
            {"owner_id": self.owner_id, "drained": drained}, actor="durable_queue_dispatcher_v1")
        return drained

    def _run_loop(self):
        backoff = self.poll_seconds
        while not self._stop.is_set():
            try:
                worked = self.run_once()
                backoff = self.poll_seconds
                if not worked:
                    self._stop.wait(self.poll_seconds)
            except Exception as exc:  # loop infrastructure failure, no secret/payload logging
                self.ledger.append("TASK_DISPATCH_RETRY", None,
                    {"failure_class": type(exc).__name__, "backoff_seconds": round(backoff, 2)},
                    actor="durable_queue_dispatcher_v1")
                self._stop.wait(backoff)
                backoff = min(self.max_backoff_seconds, max(1, backoff * 2))

    def run_once(self):
        record = self.queue.claim_next(self.owner_id, lease_seconds=self.lease_seconds)
        if record is None:
            return self.provider_connector.run_once() if self.provider_connector else False
        task_id = record["task_id"]
        token = record["dispatch_claim"]["token"]
        self.ledger.append("TASK_CLAIMED", task_id,
            {"owner_id": self.owner_id, "attempt": record.get("dispatch_attempts", 1)},
            actor="durable_queue_dispatcher_v1")
        try:
            self.ledger.append("TASK_EXECUTION_STARTED", task_id,
                {"owner_id": self.owner_id}, actor="durable_queue_dispatcher_v1")
            self.orchestrator.process_task(task_id, claim_token=token)
        except Exception as exc:
            current = self.queue.get(task_id)
            if current["state"] == "RUNNING":
                safe_error = _sanitized_error(exc)
                self.queue.transition(task_id, "BLOCKED",
                    dispatch_last_error=safe_error,
                    recovery={"classification": "DISPATCH_EXECUTION_AMBIGUOUS",
                              "action": "BLOCKED_FAIL_CLOSED",
                              "failure_class": type(exc).__name__})
                self.ledger.append("TASK_BLOCKED", task_id,
                    {"reason": "dispatcher exception after RUNNING; automatic replay prohibited",
                     "failure_class": type(exc).__name__}, actor="durable_queue_dispatcher_v1")
                return True
            elif current["state"] == "QUEUED":
                attempt = int(current.get("dispatch_attempts") or 1)
                delay = min(self.max_backoff_seconds, 2 ** min(attempt, 10))
                self.queue.release_claim(task_id, token, retry_after_seconds=delay,
                                         error=type(exc).__name__)
                self.ledger.append("TASK_DISPATCH_RETRY", task_id,
                    {"failure_class": type(exc).__name__, "backoff_seconds": delay,
                     "attempt": attempt}, actor="durable_queue_dispatcher_v1")
                return True
            raise
        finally:
            released = self.queue.release_claim(task_id, token)
            self.ledger.append("TASK_CLAIM_RELEASED", task_id,
                {"owner_id": self.owner_id, "released": released,
                 "final_state": self.queue.get(task_id)["state"]},
                actor="durable_queue_dispatcher_v1")
        return True
