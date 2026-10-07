"""TELEGRAM_MISTRAL_DIRECT_MODE_V1 - Render-side client of the Local
Inference Gateway's free-form chat route.

Mirrors ministral_router.py's _call_gateway() exactly (same gateway, same
env vars, same "Render never talks to Ollama directly" boundary) but calls
/v1/jarvis/chat instead of /v1/jarvis/interpret, and carries a bounded
conversation history instead of a task-routing context packet. This module
never raises and never mutates anything - every failure (unreachable,
timeout, malformed, empty) returns a uniform {"ok": False, "error": ...}
and lets the caller (JarvisService.command()) decide what to show the user.
"""
from __future__ import annotations

import json
import logging
import os
import socket
import ssl
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

# LOCAL_INFERENCE_CONNECTIVITY_V1 (2026-10-06): measured ~49s for a cold
# ministral-3:3b call on the operator's machine (model not yet resident in
# Ollama) vs ~6s warm - 20s failed the first real request after the gateway
# started or after Ollama's keep_alive window expired. The gateway itself
# now warms the model on startup (see nexus_local_inference_gateway.py's
# _warmup_model()), but this client-side timeout still needs real margin
# for whenever that warmup hasn't happened yet or has expired.
DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("JARVIS_MINISTRAL_CHAT_TIMEOUT_SECONDS", "60"))
MAX_HISTORY_TURNS = int(os.environ.get("JARVIS_MINISTRAL_CHAT_HISTORY_TURNS", "6"))
LOGGER = logging.getLogger(__name__)
_STATUS_LOCK = threading.RLock()
_LAST_STATUS = {"last_status": "NEVER_CALLED", "last_error": None, "last_latency_ms": None,
                "last_http_status": None, "last_exception_class": None}


def _configuration():
    url = os.environ.get("JARVIS_MINISTRAL_GATEWAY_URL", "").strip()
    token = os.environ.get("JARVIS_MINISTRAL_GATEWAY_TOKEN", "")
    timeout = float(os.environ.get("JARVIS_MINISTRAL_CHAT_TIMEOUT_SECONDS",
                                   str(DEFAULT_TIMEOUT_SECONDS)))
    return url, token, timeout


def gateway_status():
    """Safe diagnostic projection: never returns URLs, credentials or headers."""
    url, token, timeout = _configuration()
    with _STATUS_LOCK:
        last = dict(_LAST_STATUS)
    return {"gateway_configured": bool(url and token),
            "gateway_host": urlparse(url).hostname if url else None,
            "url_configured": bool(url), "token_present": bool(token),
            "token_length": len(token), "timeout_seconds": timeout, **last}


def _record(result, latency_ms):
    with _STATUS_LOCK:
        _LAST_STATUS.update({"last_status": "OK" if result.get("ok") else "ERROR",
                             "last_error": result.get("error"),
                             "last_latency_ms": latency_ms,
                             "last_http_status": result.get("http_status"),
                             "last_exception_class": result.get("exception_class")})
    if not result.get("ok"):
        status = gateway_status()
        LOGGER.warning("Mistral gateway failure code=%s host=%s token_present=%s "
                       "token_length=%s latency_ms=%s http_status=%s exception_class=%s",
                       result.get("error"), status["gateway_host"], status["token_present"],
                       status["token_length"], latency_ms, result.get("http_status"),
                       result.get("exception_class"))


def _network_error(exc):
    reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    if isinstance(reason, (socket.timeout, TimeoutError)):
        return "GATEWAY_TIMEOUT"
    if isinstance(reason, socket.gaierror):
        return "GATEWAY_DNS_ERROR"
    if isinstance(reason, ssl.SSLError):
        return "GATEWAY_TLS_ERROR"
    if isinstance(reason, (ConnectionError, ConnectionRefusedError)):
        return "GATEWAY_CONNECT_ERROR"
    text = str(reason).lower()
    if "timed out" in text or "timeout" in text:
        return "GATEWAY_TIMEOUT"
    if "name or service" in text or "getaddrinfo" in text or "nodename" in text:
        return "GATEWAY_DNS_ERROR"
    if "certificate" in text or "ssl" in text or "tls" in text:
        return "GATEWAY_TLS_ERROR"
    return "GATEWAY_CONNECT_ERROR"


def _call_gateway(text, history, *, timeout, opener=urllib.request.urlopen):
    gateway_url, token, _ = _configuration()
    if not gateway_url or not token:
        return {"ok": False, "error": "GATEWAY_NOT_CONFIGURED"}
    body = json.dumps({"text": text, "history": history}).encode("utf-8")
    req = urllib.request.Request(
        gateway_url.rstrip("/") + "/v1/jarvis/chat", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    try:
        with opener(req, timeout=timeout) as resp:
            raw = resp.read()
            try:
                payload = json.loads(raw)
            except (TypeError, ValueError):
                return {"ok": False, "error": "GATEWAY_INVALID_RESPONSE",
                        "http_status": getattr(resp, "status", None)}
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read())
        except Exception:  # noqa: BLE001
            detail = {}
        code = "GATEWAY_HTTP_401" if exc.code == 401 else (
            "GATEWAY_HTTP_403" if exc.code == 403 else (
            "GATEWAY_HTTP_4XX" if 400 <= exc.code < 500 else "GATEWAY_HTTP_5XX"))
        return {"ok": False, "error": code, "http_status": exc.code,
                "exception_class": type(exc).__name__}
    except (urllib.error.URLError, TimeoutError, OSError, ssl.SSLError) as exc:
        return {"ok": False, "error": _network_error(exc),
                "exception_class": type(exc).__name__}
    if not payload.get("ok"):
        upstream = str(payload.get("error") or "")
        code = "MODEL_CALL_FAILED" if "MODEL_CALL_FAILED" in upstream else "GATEWAY_REJECTED"
        return {"ok": False, "error": code,
                "http_status": getattr(resp, "status", None)}
    output = payload.get("output") or {}
    reply = output.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        return {"ok": False, "error": "GATEWAY_EMPTY_REPLY"}
    return {"ok": True, "reply": reply}


def bounded_history(turns):
    """Keeps only the most recent MAX_HISTORY_TURNS entries - this module's
    own last line of defense even though the gateway bounds it again
    (defense in depth, same discipline as the gateway's own
    CHAT_MAX_HISTORY_TURNS)."""
    return [t for t in (turns or []) if isinstance(t, dict)][-MAX_HISTORY_TURNS:]


def ask_mistral_direct(text, history, *, timeout=None, opener=urllib.request.urlopen):
    """Returns {"ok": True, "reply": str, "latency_ms": float} or
    {"ok": False, "error": str, "latency_ms": float} - uniform, never raises."""
    started = time.monotonic()
    _, _, configured_timeout = _configuration()
    result = _call_gateway(text, bounded_history(history), timeout=timeout or configured_timeout,
                           opener=opener)
    latency_ms = round((time.monotonic() - started) * 1000, 2)
    _record(result, latency_ms)
    return {**result, "latency_ms": latency_ms}
