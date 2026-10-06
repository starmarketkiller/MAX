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
import os
import time
import urllib.error
import urllib.request

DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("JARVIS_MINISTRAL_CHAT_TIMEOUT_SECONDS", "20"))
MAX_HISTORY_TURNS = int(os.environ.get("JARVIS_MINISTRAL_CHAT_HISTORY_TURNS", "6"))


def _call_gateway(text, history, *, timeout, opener=urllib.request.urlopen):
    gateway_url = os.environ.get("JARVIS_MINISTRAL_GATEWAY_URL", "")
    token = os.environ.get("JARVIS_MINISTRAL_GATEWAY_TOKEN", "")
    if not gateway_url or not token:
        return {"ok": False, "error": "GATEWAY_NOT_CONFIGURED"}
    body = json.dumps({"text": text, "history": history}).encode("utf-8")
    req = urllib.request.Request(
        gateway_url.rstrip("/") + "/v1/jarvis/chat", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    try:
        with opener(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read())
        except Exception:  # noqa: BLE001
            detail = {}
        return {"ok": False, "error": f"GATEWAY_HTTP_{exc.code}: {detail.get('error')}"}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"ok": False, "error": f"GATEWAY_UNREACHABLE: {type(exc).__name__}"}
    if not payload.get("ok"):
        return {"ok": False, "error": f"GATEWAY_REJECTED: {payload.get('error')}"}
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
    result = _call_gateway(text, bounded_history(history), timeout=timeout or DEFAULT_TIMEOUT_SECONDS,
                           opener=opener)
    latency_ms = round((time.monotonic() - started) * 1000, 2)
    return {**result, "latency_ms": latency_ms}
