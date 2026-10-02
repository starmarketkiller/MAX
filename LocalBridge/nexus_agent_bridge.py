#!/usr/bin/env python3
"""Outbound-only NEXUS Local Agent Bridge V1 client.

This process exposes no listening socket and has no generic shell endpoint. It
polls for Router-authorized ``complex_code_change`` jobs, calls local Ollama,
then runs the existing bounded FreeCodingWorker verifier in a task workspace.
"""
from __future__ import annotations

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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
ORCH = SERVER / "orchestrator_v1"
for entry in (SERVER, ORCH):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from jarvis_v1.free_coding_worker import FreeCodingWorkerHandler  # noqa: E402
from orchestrator_v1.core import ollama_worker  # noqa: E402


class BridgeClient:
    def __init__(self, *, base_url, bridge_id, secret, project_root=ROOT,
                 poll_seconds=3, timeout=30, opener=urllib.request.urlopen):
        if len(secret or "") < 32:
            raise ValueError("NEXUS_LOCAL_AGENT_BRIDGE_SECRET must contain at least 32 characters")
        self.base_url = base_url.rstrip("/")
        if not self.base_url.startswith("https://") and "localhost" not in self.base_url:
            raise ValueError("bridge requires HTTPS except for localhost development")
        self.bridge_id, self.secret = bridge_id, secret
        self.poll_seconds, self.timeout, self.opener = float(poll_seconds), int(timeout), opener
        self.handler = FreeCodingWorkerHandler(
            project_root=project_root,
            workspace_root=Path(os.environ.get("NEXUS_LOCAL_AGENT_WORKSPACE",
                                               str(Path(project_root) / ".nexus" /
                                                   "bridge_workspaces"))))
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
            "status": status, "capabilities": ["complex_code_change"]})

    def claim(self):
        return self._request("/api/jarvis/local-bridge/claim", {
            "capabilities": ["complex_code_change"]}).get("job")

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

    def execute(self, job):
        task_id, lease = job["task_id"], job["lease"]
        stopped = threading.Event()
        renewer = threading.Thread(target=self._renew_loop,
                                   args=(task_id, lease["token"], stopped), daemon=True)
        renewer.start()
        try:
            call = ollama_worker.call_local_model(job["prompt"], model=job["model"])
            if not call["success"]:
                return self._request("/api/jarvis/local-bridge/failure", {
                    "task_id": task_id, "lease_token": lease["token"],
                    "failure_class": "LOCAL_MODEL_UNAVAILABLE"})
            verified = self.handler.verify(job["task_record"], call["response_text"])
            if not verified.passed:
                return self._request("/api/jarvis/local-bridge/failure", {
                    "task_id": task_id, "lease_token": lease["token"],
                    "failure_class": "LOCAL_VERIFIER_REJECTED"})
            parsed = verified.parsed_output
            # Only bounded evidence is returned. Workspace absolute paths and model
            # prompts are never logged or included in the public RESULT_PACKET.
            verification = {"passed": True, "model": call["model"],
                            "test_results": parsed.get("test_results") or []}
            return self._request("/api/jarvis/local-bridge/result", {
                "task_id": task_id, "lease_token": lease["token"],
                "result_id": f"result:{task_id}:{lease['token'][:12]}",
                "response_text": call["response_text"], "verification": verification})
        finally:
            stopped.set()
            renewer.join(timeout=1)

    def run_once(self):
        self.heartbeat()
        job = self.claim()
        if not job:
            return False
        self.execute(job)
        return True

    def run_forever(self):
        backoff = self.poll_seconds
        while self.running:
            try:
                self.run_once()
                backoff = self.poll_seconds
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                # No payload/token is printed. Reconnect conservatively.
                backoff = min(max(self.poll_seconds, backoff * 2), 60)
            time.sleep(backoff)

    def stop(self, *_):
        self.running = False
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
        poll_seconds=float(os.environ.get("NEXUS_LOCAL_AGENT_POLL_SECONDS", "3")))


if __name__ == "__main__":
    client = from_environment()
    signal.signal(signal.SIGINT, client.stop)
    signal.signal(signal.SIGTERM, client.stop)
    client.run_forever()
