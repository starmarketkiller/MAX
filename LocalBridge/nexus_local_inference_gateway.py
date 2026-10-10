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

TELEGRAM_MISTRAL_DIRECT_MODE_V1 (2026-10-06) adds a third route:
  POST /v1/jarvis/chat - free-form chat, no forced output schema (unlike
  /interpret, which always forces a structured router decision). Same
  security boundary (auth, rate limit, size limit, localhost-only Ollama),
  same ollama_worker.call_local_model() - just json_mode=False and a
  different, much shorter system prompt. Still never mutates anything: the
  reply text is the only thing returned, nothing is written to disk here.

FLOOR_WORKFLOW_V1 adds:
  POST /v1/jarvis/complete - one JSON completion for an already-built prompt.
  The caller validates the text. This route does not apply the router schema
  and does not write a queue, ledger, or file.
"""
from __future__ import annotations

import hmac
import json
import os
import sys
import threading
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
#: LOCAL_INFERENCE_CONNECTIVITY_V1 (2026-10-06): misurato direttamente su questa
#: macchina - una chiamata a freddo (modello non ancora residente in Ollama,
#: es. dopo l'avvio del gateway o 5+ minuti di inattivita', il default
#: keep_alive di Ollama) ha richiesto ~49s per ministral-3:3b; una chiamata a
#: caldo ~6s. Il default precedente (8s) falliva quasi sempre la prima
#: richiesta reale con MODEL_CALL_FAILED/502 - vedi anche il warmup in run().
DEFAULT_TIMEOUT_SECONDS = int(os.environ.get("NEXUS_LOCAL_INFERENCE_GATEWAY_TIMEOUT_SECONDS", "60"))

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
- "recommended_action" e "skill", se li usi, devono essere una parola o due,
  MAI una frase.

"intent" DEVE essere ESATTAMENTE uno di questi valori (nessun altro e' valido):
QUERY, TASK_REQUEST, APPROVAL, REJECTION, COMMAND, FOLLOW_UP,
NOTIFICATION_PREFERENCE, PROVIDER_PREFERENCE, EXECUTIVE_APPROVAL_REFERENCE,
GOAL_TO_TASK, EXECUTIVE_INTENT, STATE_QUERY, UNKNOWN

"risk_level" DEVE essere ESATTAMENTE uno di: LOW, MEDIUM, HIGH, UNKNOWN

Rispondi con un oggetto JSON con esattamente questi campi: intent, goal, confidence,
referenced_task_id, recommended_action, target_agent, skill, provider_preference,
needs_clarification, clarification_question, risk_level, reason_summary."""


def build_prompt(text: str, context_packet: dict) -> str:
    return (f"{SYSTEM_PROMPT}\n\nCONTESTO (JSON):\n"
            f"{json.dumps(context_packet, ensure_ascii=False)}\n\n"
            f"MESSAGGIO UTENTE: {json.dumps(text, ensure_ascii=False)}")


CHAT_SYSTEM_PROMPT = """Sei Mistral, un assistente locale accessibile direttamente via Telegram (modalita'
diretta, distinta da Jarvis). Rispondi in linguaggio naturale, in italiano salvo richiesta diversa,
in modo conciso e diretto. Non esegui azioni, non hai accesso a file o task reali in questa modalita' -
se l'utente ti chiede di fare qualcosa che richiede accesso a dati/file/task reali, dillo chiaramente
invece di inventare una risposta plausibile."""

CHAT_MAX_HISTORY_TURNS = 12  # difesa in profondita' - il chiamante (Render) e' gia' responsabile
                            # di limitare la finestra inviata, ma questo gateway non si fida
                            # ciecamente di un body arbitrario


def build_chat_prompt(text: str, history: list) -> str:
    bounded = [h for h in (history or []) if isinstance(h, dict)][-CHAT_MAX_HISTORY_TURNS:]
    lines = [CHAT_SYSTEM_PROMPT, ""]
    for turn in bounded:
        role = "Utente" if turn.get("role") == "user" else "Mistral"
        lines.append(f"{role}: {str(turn.get('text') or '')[:MAX_TEXT_LENGTH]}")
    lines.append(f"Utente: {text}")
    lines.append("Mistral:")
    return "\n".join(lines)


def chat(text, history, *, model=None, timeout=None, call_local_model=None):
    """Pure core logic, no HTTP - mirrors interpret() but free-form: no
    forced JSON schema, no candidate_task_ids validation (this mode never
    references a task). Returns {"ok": True, "output": {"reply": "<text>"}}
    or {"ok": False, "error": "<reason>", "status": <http status>} - never
    raises."""
    call_local_model = call_local_model or ollama_worker.call_local_model
    text = (text or "")[:MAX_TEXT_LENGTH]
    if not text.strip():
        return {"ok": False, "error": "EMPTY_TEXT", "status": 400}
    prompt = build_chat_prompt(text, history)
    try:
        call = call_local_model(prompt, model=model or ollama_worker.DEFAULT_MODEL,
                                timeout=timeout or DEFAULT_TIMEOUT_SECONDS,
                                json_mode=False, ensure_single_resident=False)
    except Exception as exc:  # noqa: BLE001 - never leak an unhandled error to the caller
        return {"ok": False, "error": f"MODEL_CALL_FAILED: {type(exc).__name__}", "status": 502}
    if not call.get("success"):
        return {"ok": False, "error": f"MODEL_CALL_FAILED: {call.get('error')}", "status": 502}
    reply = (call.get("response_text") or "").strip()
    if not reply:
        return {"ok": False, "error": "EMPTY_MODEL_RESPONSE", "status": 502}
    return {"ok": True, "output": {"reply": reply}}


def complete(prompt, *, model=None, timeout=None, call_local_model=None):
    """JSON completion for a prompt the caller already built.

    Unlike interpret(), the text is not checked against the router schema.
    Unlike chat(), json_mode is on. Nothing is written here.
    """
    call_local_model = call_local_model or ollama_worker.call_local_model
    prompt = str(prompt or "")
    if not prompt.strip():
        return {"ok": False, "error": "EMPTY_PROMPT", "status": 400}
    if len(prompt) > 48000:
        return {"ok": False, "error": "PROMPT_TOO_LARGE", "status": 413}
    try:
        bounded = DEFAULT_TIMEOUT_SECONDS if timeout is None else max(1, min(int(timeout), 60))
    except (TypeError, ValueError):
        return {"ok": False, "error": "INVALID_TIMEOUT", "status": 400}
    try:
        call = call_local_model(prompt, model=model or ollama_worker.DEFAULT_MODEL,
                                timeout=bounded, json_mode=True, ensure_single_resident=False)
    except Exception as exc:  # noqa: BLE001 - never leak an unhandled error to the caller
        return {"ok": False, "error": f"MODEL_CALL_FAILED: {type(exc).__name__}", "status": 502}
    if not call.get("success"):
        return {"ok": False, "error": f"MODEL_CALL_FAILED: {call.get('error')}", "status": 502}
    text = (call.get("response_text") or "").strip()
    if not text:
        return {"ok": False, "error": "EMPTY_MODEL_RESPONSE", "status": 502}
    return {"ok": True, "output": {"text": text}}


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
        if self.path not in ("/v1/jarvis/interpret", "/v1/jarvis/chat", "/v1/jarvis/complete"):
            self._json(404, {"ok": False, "error": "NOT_FOUND"})
            return
        if not _check_auth(self.headers.get("Authorization"), self.auth_token):
            self._json(401, {"ok": False, "error": "UNAUTHORIZED"})
            return
        if not _rate_limiter.allow():
            self._json(429, {"ok": False, "error": "RATE_LIMITED"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        limit = 65536 if self.path == "/v1/jarvis/complete" else MAX_REQUEST_BYTES
        if length <= 0 or length > limit:
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
        if self.path == "/v1/jarvis/chat":
            result = chat(body.get("text"), body.get("history"))
        elif self.path == "/v1/jarvis/complete":
            result = complete(body.get("prompt"), timeout=body.get("timeout"))
        else:
            result = interpret(body.get("text"), body.get("context_packet"))
        if result["ok"]:
            self._json(200, {"ok": True, "output": result["output"]})
        else:
            self._json(result.get("status", 502), {"ok": False, "error": result["error"]})


def _warmup_model():
    """LOCAL_INFERENCE_CONNECTIVITY_V1: a cold call to Ollama (model not yet
    resident) measured ~49s on this machine vs ~6s warm - without this, the
    first real /interpret or /chat request after the gateway starts (or
    after Ollama's keep_alive window expires) was the one most likely to
    time out. Best-effort, non-fatal, never blocks the server from accepting
    connections (runs in a background thread) - a failed/slow warmup just
    means the first real request pays the cold-start cost instead."""
    try:
        result = ollama_worker.call_local_model(
            "ciao", model=ollama_worker.DEFAULT_MODEL, timeout=90, json_mode=False,
            ensure_single_resident=False)
        print(f"[gateway] warmup {'ok' if result.get('success') else 'failed'} "
             f"({result.get('wall_seconds')}s)", flush=True)
    except Exception as exc:  # noqa: BLE001 - warmup is best-effort, never fatal
        print(f"[gateway] warmup raised {type(exc).__name__} (non-fatal)", flush=True)


def run(port=None):
    token = os.environ.get("NEXUS_LOCAL_INFERENCE_GATEWAY_TOKEN", "")
    if len(token) < 32:
        raise ValueError("NEXUS_LOCAL_INFERENCE_GATEWAY_TOKEN must contain at least 32 characters")
    GatewayHandler.auth_token = token
    server = ThreadingHTTPServer(("127.0.0.1", port or DEFAULT_PORT), GatewayHandler)
    print(f"[gateway] listening on 127.0.0.1:{port or DEFAULT_PORT} "
          f"(expose only via an authenticated tunnel, never directly)", flush=True)
    threading.Thread(target=_warmup_model, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    run()
