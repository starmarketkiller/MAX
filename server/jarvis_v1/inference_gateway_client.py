"""Render-side client for the existing local inference gateway.

The Floor workflow needs one JSON completion. Chat and interpret stay as they
are. This module does not choose a provider, write a queue, or call a paid API.
"""
from __future__ import annotations

import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request


def gateway_configured() -> bool:
    url = os.environ.get("JARVIS_MINISTRAL_GATEWAY_URL", "").strip()
    token = os.environ.get("JARVIS_MINISTRAL_GATEWAY_TOKEN", "")
    return bool(url and token)


def complete_json(prompt, *, timeout=20, opener=urllib.request.urlopen):
    """Return the same shape as ollama_worker.call_local_model, without raising."""
    started = time.monotonic()
    url = os.environ.get("JARVIS_MINISTRAL_GATEWAY_URL", "").strip()
    token = os.environ.get("JARVIS_MINISTRAL_GATEWAY_TOKEN", "")
    if not url or not token:
        return _failure("GATEWAY_NOT_CONFIGURED", started)
    body = json.dumps({"prompt": prompt, "timeout": int(timeout)}).encode("utf-8")
    request = urllib.request.Request(
        url.rstrip("/") + "/v1/jarvis/complete", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    try:
        with opener(request, timeout=timeout) as response:
            payload = json.loads(response.read())
    except Exception as exc:  # noqa: BLE001 - transport failures are task results
        return _failure(_network_error(exc), started)
    if not isinstance(payload, dict) or not payload.get("ok"):
        return _failure(str((payload or {}).get("error") or "GATEWAY_REJECTED")[:300], started)
    text = ((payload.get("output") or {}).get("text") if isinstance(payload.get("output"), dict) else None)
    if not isinstance(text, str) or not text.strip():
        return _failure("GATEWAY_EMPTY_REPLY", started)
    return {"success": True, "response_text": text, "error": None, "model": "gateway",
            "wall_seconds": round(time.monotonic() - started, 2)}


def _failure(error, started):
    return {"success": False, "response_text": None, "error": error, "model": "gateway",
            "wall_seconds": round(time.monotonic() - started, 2)}


def _network_error(exc):
    reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    if isinstance(reason, (socket.timeout, TimeoutError)):
        return "GATEWAY_TIMEOUT"
    if isinstance(reason, ssl.SSLError):
        return "GATEWAY_TLS_ERROR"
    return "GATEWAY_CONNECT_ERROR"
