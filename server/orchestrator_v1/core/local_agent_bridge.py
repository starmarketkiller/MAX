"""Outbound-only Local Agent Bridge coordination for approved local tasks.

The backend never reaches into a workstation.  A separately authenticated
client polls this store, leases one Router-approved job, executes only the
bounded local handler, and returns a verifier receipt.  This module does not
route tasks and exposes no generic command or shell primitive.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


class LocalAgentBridgeV1:
    CAPABILITY = "complex_code_change"
    MAX_ATTEMPTS = 2  # initial execution plus one bounded retry

    # LOCAL_BRIDGE_REWORK_REDISPATCH_FIX_V1: the complete set of values ever
    # assigned to a job's "status" in this module is QUEUED (dispatch(), and
    # report_failure()'s retry reset), LEASED (claim()), FAILED (claim()'s own
    # lost-task-record cleanup and report_failure()'s exhausted-attempts
    # terminal state) and COMPLETED (submit_result()) - audited by grepping
    # every `job["status"] = ...` / `job.update({"status": ...})` site below.
    # "EXPIRED" is accepted as a synonym for "not active" (kept for forward
    # compatibility with a future lease-sweep) but nothing assigns it today.
    #
    # Only QUEUED/LEASED mean "this job is still pending or being worked on
    # right now" - dispatch()'s idempotency guard must short-circuit on those
    # ONLY. Treating COMPLETED as "not FAILED/EXPIRED, so still active" (the
    # pre-fix guard) silently blocked every legitimate rework re-dispatch of
    # an already-completed task_id: the Dynamic Specialist Review hands the
    # SAME task_id back to QUEUED after a human reject + reviewer rework, and
    # dispatch() must be able to queue a fresh job for it.
    ACTIVE_JOB_STATES = {"QUEUED", "LEASED"}

    def __init__(self, orchestrator, *, state_path, secret="", heartbeat_ttl=45,
                 lease_seconds=300, max_requests_per_minute=60, clock=time.time):
        self.orchestrator = orchestrator
        self.queue = orchestrator.queue
        self.ledger = orchestrator.ledger
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.secret = secret
        self.heartbeat_ttl = max(10, int(heartbeat_ttl))
        self.lease_seconds = max(30, int(lease_seconds))
        self.max_requests_per_minute = max(5, int(max_requests_per_minute))
        self.clock = clock
        self._lock = threading.RLock()
        self._nonces = {}
        self._requests = {}
        if not self.state_path.exists():
            self._save({"schema_version": 1, "bridges": {}, "jobs": {}})

    @property
    def configured(self):
        return len(self.secret) >= 32

    def job_status(self, task_id):
        """Read-only: this task's bridge job status, or None if it has no
        job. SAFE_ORPHANED_TASK_RESUME_V1 uses this to refuse resuming a task
        whose bridge job is still genuinely active (ACTIVE_JOB_STATES) -
        without exposing the private _load()/_save() write API."""
        with self._lock:
            data = self._load()
        job = data["jobs"].get(task_id)
        return job["status"] if job else None

    def _load(self):
        with self.state_path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def _save(self, data):
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, self.state_path)

    def verify_request(self, *, bridge_id, method, path, timestamp, nonce, body, signature):
        """Verify HMAC, freshness, replay and a conservative per-bridge rate limit."""
        if not self.configured:
            raise PermissionError("bridge authentication is not configured")
        try:
            numeric_timestamp = int(timestamp)
        except (TypeError, ValueError):
            raise PermissionError("invalid bridge timestamp")
        now = int(self.clock())
        if abs(now - numeric_timestamp) > 60:
            raise PermissionError("stale bridge request")
        if not bridge_id or not nonce or not signature:
            raise PermissionError("incomplete bridge authentication")
        with self._lock:
            self._nonces = {key: value for key, value in self._nonces.items()
                            if now - value <= 120}
            nonce_key = f"{bridge_id}:{nonce}"
            if nonce_key in self._nonces:
                raise PermissionError("replayed bridge request")
            window = [value for value in self._requests.get(bridge_id, []) if now - value < 60]
            if len(window) >= self.max_requests_per_minute:
                raise RuntimeError("bridge rate limit exceeded")
            body_hash = hashlib.sha256(body).hexdigest()
            canonical = "\n".join([method.upper(), path, str(timestamp), nonce, body_hash])
            expected = hmac.new(self.secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise PermissionError("invalid bridge signature")
            self._nonces[nonce_key] = now
            window.append(now)
            self._requests[bridge_id] = window

    def heartbeat(self, bridge_id, capabilities, status="ONLINE"):
        allowed = sorted(set(capabilities or []) & {self.CAPABILITY})
        with self._lock:
            data = self._load()
            data["bridges"][bridge_id] = {
                "bridge_id": bridge_id, "status": status if status in ("ONLINE", "DEGRADED") else "DEGRADED",
                "capabilities": allowed, "last_heartbeat": _iso(), "last_heartbeat_epoch": self.clock(),
            }
            self._save(data)
        self.ledger.append("TOOL_USED", None,
                           {"tool": "local_agent_bridge_heartbeat", "bridge_id": bridge_id, "status": status,
                            "capabilities": allowed}, actor="local_agent_bridge_v1")
        return self.status(bridge_id)

    def status(self, bridge_id=None):
        with self._lock:
            data = self._load()
        items = []
        now = self.clock()
        for item in data["bridges"].values():
            current = dict(item)
            age = max(0, now - float(current.get("last_heartbeat_epoch") or 0))
            current["heartbeat_age_seconds"] = round(age, 1)
            if age > self.heartbeat_ttl:
                current["status"] = "OFFLINE"
            items.append(current)
        if bridge_id:
            return next((item for item in items if item["bridge_id"] == bridge_id),
                        {"bridge_id": bridge_id, "status": "OFFLINE", "capabilities": []})
        return {"configured": self.configured, "count": len(items), "items": items}

    def _eligible_bridge_exists(self):
        return any(item["status"] in ("ONLINE", "DEGRADED") and
                   self.CAPABILITY in item["capabilities"]
                   for item in self.status()["items"])

    def dispatch(self, task_record, decision, handler):
        """Queue an already-routed local job; return False when no bridge can execute it."""
        if not self.configured or not self._eligible_bridge_exists():
            return False
        if task_record.get("action") != "conversational_programming":
            return False
        prompt = handler.build_prompt(task_record)
        client_record = {key: task_record.get(key) for key in
                         ("task_id", "manifest", "action", "action_params")}
        with self._lock:
            data = self._load()
            existing = data["jobs"].get(task_record["task_id"])
            if existing and existing["status"] in self.ACTIVE_JOB_STATES:
                return True
            data["jobs"][task_record["task_id"]] = {
                "job_id": f"lab_{uuid.uuid4().hex[:16]}", "task_id": task_record["task_id"],
                "status": "QUEUED", "capability": self.CAPABILITY,
                "executor": decision.executor, "model": decision.agent["model_or_runtime"].split(" ")[0],
                "prompt": prompt, "task_record": client_record, "attempts": 0,
                "lease": None, "created_at": _iso(), "updated_at": _iso(),
                "result_id": None, "result_digest": None,
            }
            self._save(data)
        self.queue.transition(task_record["task_id"], "WAITING_PROVIDER",
                              local_bridge={"status": "QUEUED", "capability": self.CAPABILITY})
        self.ledger.append("TASK_QUEUED", task_record["task_id"],
                           {"queue": "local_agent_bridge_v1", "capability": self.CAPABILITY,
                            "executor": decision.executor},
                           actor="local_agent_bridge_v1")
        return True

    def claim(self, bridge_id, capabilities):
        offered = set(capabilities or []) & {self.CAPABILITY}
        if self.CAPABILITY not in offered:
            return None
        if self.status(bridge_id)["status"] == "OFFLINE":
            return None
        with self._lock:
            data = self._load()
            now = datetime.now(timezone.utc)
            for job in sorted(data["jobs"].values(), key=lambda item: item["created_at"]):
                if job["status"] == "LEASED" and job.get("lease"):
                    if datetime.fromisoformat(job["lease"]["expires_at"]) <= now:
                        job["status"], job["lease"] = "QUEUED", None
                if job["status"] != "QUEUED" or job["attempts"] >= self.MAX_ATTEMPTS:
                    continue
                try:
                    task = self.queue.get(job["task_id"])
                except KeyError:
                    job["status"] = "FAILED"
                    continue
                if task["state"] != "WAITING_PROVIDER" or job["capability"] not in offered:
                    continue
                token = secrets.token_urlsafe(32)
                job["status"] = "LEASED"
                job["attempts"] += 1
                job["lease"] = {"bridge_id": bridge_id, "token": token,
                                "expires_at": _iso(now + timedelta(seconds=self.lease_seconds))}
                job["updated_at"] = _iso(now)
                self._save(data)
                self.ledger.append("TASK_CLAIMED", job["task_id"],
                                   {"transport": "local_agent_bridge_v1", "bridge_id": bridge_id,
                                    "attempt": job["attempts"]},
                                   actor="local_agent_bridge_v1")
                self.ledger.append("TASK_EXECUTION_STARTED", job["task_id"],
                                   {"transport": "local_agent_bridge_v1", "bridge_id": bridge_id,
                                    "attempt": job["attempts"]},
                                   actor="local_agent_bridge_v1")
                return {key: job[key] for key in ("job_id", "task_id", "capability", "executor",
                                                   "model", "prompt", "task_record", "lease")}
            self._save(data)
        return None

    def _leased_job(self, data, task_id, bridge_id, lease_token):
        job = data["jobs"].get(task_id)
        if not job:
            raise KeyError("bridge job not found")
        lease = job.get("lease") or {}
        if job["status"] != "LEASED" or lease.get("bridge_id") != bridge_id or not hmac.compare_digest(
                str(lease.get("token") or ""), str(lease_token or "")):
            raise PermissionError("invalid bridge lease")
        if datetime.fromisoformat(lease["expires_at"]) <= datetime.now(timezone.utc):
            raise PermissionError("expired bridge lease")
        return job

    def renew(self, task_id, bridge_id, lease_token):
        with self._lock:
            data = self._load()
            job = self._leased_job(data, task_id, bridge_id, lease_token)
            job["lease"]["expires_at"] = _iso(datetime.now(timezone.utc) +
                                                 timedelta(seconds=self.lease_seconds))
            job["updated_at"] = _iso()
            self._save(data)
        self.ledger.append("TOOL_USED", task_id,
                           {"tool": "local_agent_bridge_lease_renew", "bridge_id": bridge_id},
                           actor="local_agent_bridge_v1")
        return {"task_id": task_id, "lease_expires_at": job["lease"]["expires_at"]}

    def submit_result(self, task_id, bridge_id, lease_token, result_id, response_text, verification):
        if not isinstance(result_id, str) or not result_id.strip():
            raise ValueError("result_id required")
        digest = hashlib.sha256(json.dumps({"response_text": response_text,
                                            "verification": verification}, sort_keys=True).encode()).hexdigest()
        with self._lock:
            data = self._load()
            job = data["jobs"].get(task_id)
            if job and job.get("result_id") == result_id:
                if job.get("result_digest") != digest:
                    raise PermissionError("result id replayed with different payload")
                return self.queue.get(task_id)
            job = self._leased_job(data, task_id, bridge_id, lease_token)
        record = self.orchestrator.accept_local_bridge_result(
            task_id, executor=job["executor"], response_text=response_text,
            verification=verification, bridge_id=bridge_id)
        with self._lock:
            data = self._load()
            job = data["jobs"][task_id]
            job.update({"status": "COMPLETED", "lease": None, "result_id": result_id,
                        "result_digest": digest, "updated_at": _iso()})
            self._save(data)
        self.ledger.append("RESULT_DELIVERED", task_id,
                           {"transport": "local_agent_bridge_v1", "bridge_id": bridge_id,
                            "result_id": result_id},
                           actor="local_agent_bridge_v1")
        return record

    def report_failure(self, task_id, bridge_id, lease_token, failure_class):
        safe_failure = str(failure_class or "LOCAL_BRIDGE_FAILURE")[:120]
        with self._lock:
            data = self._load()
            job = self._leased_job(data, task_id, bridge_id, lease_token)
            retry = job["attempts"] < self.MAX_ATTEMPTS
            job.update({"status": "QUEUED" if retry else "FAILED", "lease": None,
                        "last_error": safe_failure, "updated_at": _iso()})
            self._save(data)
        self.ledger.append("TASK_FAILED", task_id,
                           {"transport": "local_agent_bridge_v1", "bridge_id": bridge_id,
                            "failure_class": safe_failure,
                            "retry_scheduled": retry, "attempt": job["attempts"]},
                           actor="local_agent_bridge_v1")
        if not retry:
            self.orchestrator.fail_local_bridge_task(task_id, safe_failure)
        return {"task_id": task_id, "retry_scheduled": retry, "attempt": job["attempts"]}
