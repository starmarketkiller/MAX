#!/usr/bin/env python3
"""NEXUS Local Inference Gateway V1.

The ONLY thing Render is ever allowed to reach over the authenticated tunnel.
Ollama itself stays bound to 127.0.0.1 and is never exposed directly - this
process is the security boundary JARVIS_MINISTRAL_ROUTER_V1's design requires
between Render/Jarvis and the local model:

    Render/Jarvis -> HTTPS authenticated tunnel -> this gateway -> 127.0.0.1:11434

It exposes exactly two routes:
  POST /v1/jarvis/interpret  - the only cognitive-router operation
  GET  /v1/jarvis/health     - liveness probe, no auth required

By construction this module imports NOTHING capable of a mutation: no
TaskQueue, no Orchestrator, no EventLedger, no shell, no filesystem writes
beyond reading the bounded output schema already checked into contracts/.
A request here can, at most, ask Ollama a question and get back a single
JSON object that is schema-validated before it ever leaves this process.
"""
from __future__ import annotations

import hmac
import json
import os
import sys
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
ORCH = SERVER / "orchestrator_v1"
for entry in (SERVER, ORCH):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from orchestrator_v1.core import ollama_worker  # noqa: E402
from orchestrator_v1.nxs_schema_validator import validate  # noqa: E402

OUTPUT_SCHEMA_PATH = ROOT / "contracts" / "jarvis-ministral-router-output.schema.json"
OUTPUT_SCHEMA = json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))

DEFAULT_PORT = int(os.environ.get("NEXUS_LOCAL_INFERENCE_GATEWAY_PORT", "8765"))
MAX_REQUEST_BYTES = int(os.environ.get("NEXUS_LOCAL_INFERENCE_GATEWAY_MAX_BYTES", "32768"))
MAX_TEXT_LENGTH = 4000
RATE_LIMIT_PER_MINUTE = int(os.environ.get("NEXUS_LOCAL_INFERENCE_GATEWAY_RATE_LIMIT", "30"))
DEFAULT_TIMEOUT_SECONDS = int(os.environ.get("NEXUS_LOCAL_INFERENCE_GATEWAY_TIMEOUT_SECONDS", "8"))

SYSTEM_PROMPT = """Sei il motore di interpretazione di Jarvis, un assistente NEXUS via Telegram.
Il tuo UNICO compito e' interpretare il messaggio dell'utente e produrre UN oggetto
JSON secondo lo schema sotto. Non esegui azioni, non scrivi codice, non muti nulla:
produci solo un'interpretazione strutturata che un sistema deterministico validera'
ed eseguira'.

REGOLE INDEROGABILI:
- Rispondi SOLO con JSON valido, nessun testo prima o dopo.
- "referenced_task_id" deve essere uno dei task_id elencati in candidate_task_ids del
  contesto, oppure null. Non inventare MAI un task_id che non e' nella lista.
- Se non sei sicuro dell'intento o del task a cui si riferisce, metti
  needs_clarification=true e scrivi una domanda breve in clarification_question.
- "confidence" riflette quanto sei sicuro, onestamente - non gonfiarla.
- "risk_level" e' solo una tua stima informativa: NON decide se un'azione e' permessa,
  le policy di sicurezza reali sono altrove, fuori dal tuo controllo.

Rispondi con un oggetto JSON con esattamente questi campi: intent, goal, confidence,
referenced_task_id, recommended_action, target_agent, skill, provider_preference,
needs_clarification, clarification_question, risk_level, reason_summary."""


def build_prompt(text: str, context_packet: dict) -> str:
    return (f"{SYSTEM_PROMPT}\n\nCONTESTO (JSON):\n"
            f"{json.dumps(context_packet, ensure_ascii=False)}\n\n"
            f"MESSAGGIO UTENTE: {json.dumps(text, ensure_ascii=False)}")


def interpret(text, context_packet, *, model=None, timeout=None, call_local_model=None):
    """Pure core logic, no HTTP - directly unit-testable. Returns
    {"ok": True, "output": {...}} on a validated, in-bounds interpretation,
    or {"ok": False, "error": "<reason>", "status": <http status to use>}
    for every failure mode (timeout, unreachable, malformed, invented
    task_id, schema violation) - never raises.

    call_local_model resolves to ollama_worker.call_local_model LOOKED UP AT
    CALL TIME (not bound as a default-argument value) so a test that
    monkeypatches ollama_worker.call_local_model also affects the real
    do_POST path, which never passes an explicit override."""
    call_local_model = call_local_model or ollama_worker.call_local_model
    text = (text or "")[:MAX_TEXT_LENGTH]
    context_packet = context_packet if isinstance(context_packet, dict) else {}
    candidate_ids = set(context_packet.get("candidate_task_ids") or [])
    prompt = build_prompt(text, context_packet)
    try:
        call = call_local_model(prompt, model=model or ollama_worker.DEFAULT_MODEL,
                                timeout=timeout or DEFAULT_TIMEOUT_SECONDS,
                                json_mode=True, ensure_single_resident=False)
    except Exception as exc:  # noqa: BLE001 - never leak an unhandled error to the caller
        return {"ok": False, "error": f"MODEL_CALL_FAILED: {type(exc).__name__}", "status": 502}
    if not call.get("success"):
        return {"ok": False, "error": f"MODEL_CALL_FAILED: {call.get('error')}", "status": 502}
    parsed = ollama_worker.try_parse_json(call.get("response_text") or "")
    if not isinstance(parsed, dict):
        return {"ok": False, "error": "OUTPUT_NOT_JSON_OBJECT", "status": 422}
    errors = validate(parsed, OUTPUT_SCHEMA)
    if errors:
        return {"ok": False, "error": f"SCHEMA_INVALID: {errors[:3]}", "status": 422}
    referenced = parsed.get("referenced_task_id")
    if referenced is not None and referenced not in candidate_ids:
        return {"ok": False, "error": "REFERENCED_TASK_ID_NOT_IN_CANDIDATES", "status": 422}
    return {"ok": True, "output": parsed}


class _RateLimiter:
    def __init__(self, per_minute):
        self.per_minute = per_minute
        self._hits: deque = deque()

    def allow(self):
        now = time.time()
        while self._hits and now - self._hits[0] > 60:
            self._hits.popleft()
        if len(self._hits) >= self.per_minute:
            return False
        self._hits.append(now)
        return True


_rate_limiter = _RateLimiter(RATE_LIMIT_PER_MINUTE)


def _check_auth(auth_header, expected_token):
    if not expected_token:
        return False
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    return hmac.compare_digest(auth_header[len("Bearer "):], expected_token)


class GatewayHandler(BaseHTTPRequestHandler):
    server_version = "NexusLocalInferenceGateway/1"
    protocol_version = "HTTP/1.1"
    auth_token = None  # set by run()

    def log_message(self, fmt, *args):  # noqa: A003 - stdlib signature
        # Never log headers/body (carries the auth token and user text) -
        # only method/path/status, same discipline as the bridge's _log().
        sys.stderr.write(f"[gateway] {self.address_string()} {fmt % args}\n")

    def _json(self, status, payload):
        # Always close after responding: several early-return paths below
        # (unknown path, bad auth, rate limit, oversized) deliberately never
        # read the request body, which would otherwise leave unread bytes on
        # a persistent HTTP/1.1 connection for the next handle_one_request()
        # loop to misparse as a new request line. Low request volume, no
        # real cost to closing every time.
        self.close_connection = True
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - stdlib handler naming
        if self.path != "/v1/jarvis/health":
            self._json(404, {"ok": False, "error": "NOT_FOUND"})
            return
        self._json(200, {"ok": True, "ollama_reachable": ollama_worker.is_ollama_reachable(timeout=2)})

    def do_POST(self):  # noqa: N802 - stdlib handler naming
        if self.path != "/v1/jarvis/interpret":
            self._json(404, {"ok": False, "error": "NOT_FOUND"})
            return
        if not _check_auth(self.headers.get("Authorization"), self.auth_token):
            self._json(401, {"ok": False, "error": "UNAUTHORIZED"})
            return
        if not _rate_limiter.allow():
            self._json(429, {"ok": False, "error": "RATE_LIMITED"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_REQUEST_BYTES:
            self._json(413, {"ok": False, "error": "PAYLOAD_TOO_LARGE"})
            return
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "INVALID_JSON"})
            return
        if not isinstance(body, dict):
            self._json(400, {"ok": False, "error": "INVALID_BODY"})
            return
        result = interpret(body.get("text"), body.get("context_packet"))
        if result["ok"]:
            self._json(200, {"ok": True, "output": result["output"]})
        else:
            self._json(result.get("status", 502), {"ok": False, "error": result["error"]})


def run(port=None):
    token = os.environ.get("NEXUS_LOCAL_INFERENCE_GATEWAY_TOKEN", "")
    if len(token) < 32:
        raise ValueError("NEXUS_LOCAL_INFERENCE_GATEWAY_TOKEN must contain at least 32 characters")
    GatewayHandler.auth_token = token
    server = ThreadingHTTPServer(("127.0.0.1", port or DEFAULT_PORT), GatewayHandler)
    print(f"[gateway] listening on 127.0.0.1:{port or DEFAULT_PORT} "
          f"(expose only via an authenticated tunnel, never directly)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    run()
