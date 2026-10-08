#!/usr/bin/env python3
"""Outbound-only NEXUS Local Agent Bridge V1 client.

This process exposes no listening socket and has no generic shell endpoint. It
polls only for explicitly allowlisted coding or read-only analysis jobs, calls
local Ollama, then runs the matching bounded verifier in a task workspace.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import signal
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
ORCH = SERVER / "orchestrator_v1"
for entry in (SERVER, ORCH):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from jarvis_v1.free_coding_worker import FreeCodingWorkerHandler  # noqa: E402
from jarvis_v1.local_bounded_task_handler import BoundedLocalTaskHandler  # noqa: E402
from orchestrator_v1.core import ollama_worker  # noqa: E402


def _log(message):
    """Readable, timestamped, single-line status output. Never passed a secret,
    prompt, model response or absolute workspace path - only event names,
    task/job ids and safe counters."""
    print(f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {message}", flush=True)


class BridgeClient:
    # BRIDGE_HEARTBEAT_DURING_EXECUTION_V1: comfortably under the server's
    # default HEARTBEAT_TTL (45s, NEXUS_LOCAL_AGENT_BRIDGE_HEARTBEAT_TTL) so a
    # job that runs long never makes the server classify this bridge OFFLINE
    # while it is genuinely still working.
    DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 15

    def __init__(self, *, base_url, bridge_id, secret, project_root=ROOT,
                 poll_seconds=3, timeout=30, opener=urllib.request.urlopen,
                 heartbeat_interval_seconds=None):
        if len(secret or "") < 32:
            raise ValueError("NEXUS_LOCAL_AGENT_BRIDGE_SECRET must contain at least 32 characters")
        self.base_url = base_url.rstrip("/")
        if not self.base_url.startswith("https://") and "localhost" not in self.base_url:
            raise ValueError("bridge requires HTTPS except for localhost development")
        self.bridge_id, self.secret = bridge_id, secret
        self.poll_seconds, self.timeout, self.opener = float(poll_seconds), int(timeout), opener
        self.heartbeat_interval_seconds = float(
            heartbeat_interval_seconds if heartbeat_interval_seconds is not None
            else self.DEFAULT_HEARTBEAT_INTERVAL_SECONDS)
        workspace_root = Path(os.environ.get(
            "NEXUS_LOCAL_AGENT_WORKSPACE",
            str(Path(project_root) / ".nexus" / "bridge_workspaces")))
        # `handler` remains the canonical coding handler attribute for
        # backwards-compatible tests/diagnostics; `handlers` adds only an
        # allowlisted action resolver, never a generic execution surface.
        self.handler = FreeCodingWorkerHandler(
            project_root=project_root, workspace_root=workspace_root)
        self.handlers = {
            "conversational_programming": self.handler,
            "repo_inspection_v1": BoundedLocalTaskHandler(project_root=project_root),
        }
        self.running = True

    def _request(self, path, payload):
        body = json.dumps(payload or {}, separators=(",", ":")).encode()
        timestamp, nonce = str(int(time.time())), uuid.uuid4().hex
        canonical = "\n".join(["POST", path, timestamp, nonce,
                                hashlib.sha256(body).hexdigest()])
        signature = hmac.new(self.secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
        request = urllib.request.Request(self.base_url + path, data=body, method="POST", headers={
            "Content-Type": "application/json", "X-Nexus-Bridge-Id": self.bridge_id,
            "X-Nexus-Bridge-Timestamp": timestamp, "X-Nexus-Bridge-Nonce": nonce,
            "X-Nexus-Bridge-Signature": signature,
        })
        with self.opener(request, timeout=self.timeout) as response:
            return json.loads(response.read() or b"{}")

    def heartbeat(self, status="ONLINE"):
        return self._request("/api/jarvis/local-bridge/heartbeat", {
            "status": status,
            "capabilities": ["complex_code_change", "bounded_read_only_analysis"]})

    def claim(self):
        return self._request("/api/jarvis/local-bridge/claim", {
            "capabilities": ["complex_code_change", "bounded_read_only_analysis"]}).get("job")

    def renew(self, task_id, lease_token):
        return self._request("/api/jarvis/local-bridge/renew", {
            "task_id": task_id, "lease_token": lease_token})

    def _renew_loop(self, task_id, lease_token, stopped):
        while not stopped.wait(60):
            try:
                self.renew(task_id, lease_token)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                # Execution may finish before expiry; result submission remains
                # authoritative and will fail closed if the lease did expire.
                continue

    def _heartbeat_loop(self, stopped):
        """BRIDGE_HEARTBEAT_DURING_EXECUTION_V1: keeps the bridge's ONLINE
        status alive on the server while execute() is blocked inside a long
        local model call - completely independent of lease renewal (claim/
        lease/idempotency semantics are untouched; this never claims or
        executes a job, only reports liveness). Same resilience pattern as
        _renew_loop: a transient heartbeat failure never aborts the job
        currently executing - result/failure submission stays authoritative."""
        while not stopped.wait(self.heartbeat_interval_seconds):
            try:
                self.heartbeat()
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                continue

    def execute(self, job):
        task_id, lease = job["task_id"], job["lease"]
        stopped = threading.Event()
        renewer = threading.Thread(target=self._renew_loop,
                                   args=(task_id, lease["token"], stopped), daemon=True)
        heartbeater = threading.Thread(target=self._heartbeat_loop,
                                       args=(stopped,), daemon=True)
        renewer.start()
        heartbeater.start()
        try:
            call = ollama_worker.call_local_model(job["prompt"], model=job["model"])
            if not call["success"]:
                return self._request("/api/jarvis/local-bridge/failure", {
                    "task_id": task_id, "lease_token": lease["token"],
                    "failure_class": "LOCAL_MODEL_UNAVAILABLE"})
            action = job["task_record"].get("action")
            if not action and job.get("capability") == "complex_code_change":
                action = "conversational_programming"
            handler = self.handlers.get(action)
            if handler is None:
                return self._request("/api/jarvis/local-bridge/failure", {
                    "task_id": task_id, "lease_token": lease["token"],
                    "failure_class": "UNAUTHORIZED_BRIDGE_ACTION"})
            verified = handler.verify(job["task_record"], call["response_text"])
            if not verified.passed:
                return self._request("/api/jarvis/local-bridge/failure", {
                    "task_id": task_id, "lease_token": lease["token"],
                    "failure_class": "LOCAL_VERIFIER_REJECTED"})
            parsed = verified.parsed_output
            # Only bounded evidence is returned. Workspace absolute paths and model
            # prompts are never logged or included in the public RESULT_PACKET.
            verification = {"passed": True, "model": call["model"],
                            "test_results": parsed.get("test_results") or [],
                            "handler": action}
            return self._request("/api/jarvis/local-bridge/result", {
                "task_id": task_id, "lease_token": lease["token"],
                "result_id": f"result:{task_id}:{lease['token'][:12]}",
                "response_text": call["response_text"], "verification": verification})
        finally:
            stopped.set()
            renewer.join(timeout=1)
            heartbeater.join(timeout=1)

    def run_once(self):
        self.heartbeat()
        job = self.claim()
        if not job:
            return False
        _log(f"claimed job task_id={job['task_id']} capability={job['capability']}")
        self.execute(job)
        _log(f"job finished task_id={job['task_id']}")
        return True

    def run_forever(self):
        _log(f"bridge starting bridge_id={self.bridge_id} base_url={self.base_url} "
            f"poll_seconds={self.poll_seconds}")
        backoff = self.poll_seconds
        while self.running:
            try:
                if not self.run_once():
                    pass  # heartbeat sent, nothing to claim - normal idle tick, not logged
                backoff = self.poll_seconds
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                # No payload/token/secret is ever included in this message.
                backoff = min(max(self.poll_seconds, backoff * 2), 60)
                _log(f"connection error ({type(exc).__name__}), retrying in {backoff:.0f}s")
            time.sleep(backoff)
        _log("bridge stopped")

    def stop(self, *_):
        self.running = False
        _log("stop requested, sending final DEGRADED heartbeat")
        try:
            self.heartbeat("DEGRADED")
        except Exception:
            pass


def from_environment():
    return BridgeClient(
        base_url=os.environ.get("NEXUS_URL", "").strip(),
        bridge_id=os.environ.get("NEXUS_LOCAL_AGENT_BRIDGE_ID", "workstation-1").strip(),
        secret=os.environ.get("NEXUS_LOCAL_AGENT_BRIDGE_SECRET", ""),
        project_root=Path(os.environ.get("NEXUS_REPO_ROOT", str(ROOT))).resolve(),
        poll_seconds=float(os.environ.get("NEXUS_LOCAL_AGENT_POLL_SECONDS", "3")),
        heartbeat_interval_seconds=float(os.environ.get(
            "NEXUS_LOCAL_AGENT_HEARTBEAT_INTERVAL_SECONDS",
            str(BridgeClient.DEFAULT_HEARTBEAT_INTERVAL_SECONDS))))


def diagnose():
    """Read-only startup check. Prints only pass/fail per step - never a
    secret, token or signature. Returns True iff every step passed."""
    ok = True

    def step(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        mark = "OK" if passed else "FAIL"
        _log(f"[diagnose] {label}: {mark}{(' - ' + detail) if detail else ''}")

    base_url = os.environ.get("NEXUS_URL", "").strip()
    step("NEXUS_URL set", bool(base_url), base_url or "missing")
    secret = os.environ.get("NEXUS_LOCAL_AGENT_BRIDGE_SECRET", "")
    step("NEXUS_LOCAL_AGENT_BRIDGE_SECRET length >= 32", len(secret) >= 32,
        f"{len(secret)} chars" if secret else "missing")
    repo_root = Path(os.environ.get("NEXUS_REPO_ROOT", str(ROOT))).resolve()
    step("NEXUS_REPO_ROOT looks like the MAX checkout", (repo_root / "server").is_dir(),
        str(repo_root))
    reachable = ollama_worker.is_ollama_reachable(timeout=3)
    step("Ollama reachable", reachable, "run 'ollama serve' if this fails" if not reachable else "")
    if base_url:
        try:
            with urllib.request.urlopen(base_url.rstrip("/") + "/api/health", timeout=5) as resp:
                step("NEXUS backend reachable (/api/health)", resp.status == 200,
                    f"http {resp.status}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            step("NEXUS backend reachable (/api/health)", False, type(exc).__name__)
    else:
        step("NEXUS backend reachable (/api/health)", False, "skipped, NEXUS_URL missing")
    if base_url and len(secret) >= 32:
        try:
            status = from_environment().heartbeat()
            step("Bridge heartbeat accepted by backend", bool(status.get("bridge_id")),
                f"status={status.get('status')}")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            step("Bridge heartbeat accepted by backend", False, type(exc).__name__)
    else:
        step("Bridge heartbeat accepted by backend", False, "skipped, prior step(s) failed")
    _log(f"[diagnose] overall: {'READY' if ok else 'NOT READY'}")
    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NEXUS Local Agent Bridge V1 client")
    parser.add_argument("--diagnose", action="store_true",
                       help="run read-only startup checks and exit, without claiming any job")
    args = parser.parse_args()
    if args.diagnose:
        sys.exit(0 if diagnose() else 1)
    client = from_environment()
    signal.signal(signal.SIGINT, client.stop)
    signal.signal(signal.SIGTERM, client.stop)
    client.run_forever()
