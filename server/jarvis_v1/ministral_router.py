"""JARVIS_MINISTRAL_ROUTER_V1 - Render-side client of the Local Inference Gateway.

Render never talks to Ollama directly (it has no network path to it - see
design discussion). It talks ONLY to the gateway
(LocalBridge/nexus_local_inference_gateway.py), which is the actual security
boundary in front of the local model, reachable through an authenticated
tunnel the operator configures outside this code.

This module builds the small, per-message context packet Ministral needs
(NOT the project-wide CONTEXT_PACKET_V2 - too large/irrelevant for routing a
single message), calls the gateway, and validates its answer a SECOND time
(schema + candidate_task_ids membership) even though the gateway already
validated it - defense in depth, cheap, never trust a network boundary once.
Every failure mode (unreachable, timeout, malformed, invented task_id,
low confidence) returns a uniform {"ok": False, ...} - this module never
raises and never mutates anything; JarvisService decides what to do with
the result.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from orchestrator_v1.nxs_schema_validator import validate
from path_resolver import resolve_contracts_dir

CONTRACTS = resolve_contracts_dir(__file__)
OUTPUT_SCHEMA = json.loads((CONTRACTS / "jarvis-ministral-router-output.schema.json").read_text(encoding="utf-8"))

DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("JARVIS_MINISTRAL_ROUTER_TIMEOUT_SECONDS", "4"))
DEFAULT_CONFIDENCE_THRESHOLD = float(os.environ.get("JARVIS_MINISTRAL_ROUTER_CONFIDENCE_THRESHOLD", "0.75"))
MAX_CANDIDATE_TASKS = 20


def build_router_context(service, message):
    """Small, per-message context - conversation memory this user/
    conversation actually has, plus the real universe of task_ids Ministral
    is allowed to reference. A compact Shared Cognitive State summary is
    included ONLY when that module is importable and has data - optional,
    never required, never the full CONTEXT_PACKET_V2."""
    conversation_id = message["conversation_id"]
    stored = service.conversation_store.get(conversation_id)
    candidates = service._user_scoped_tasks(message)[:MAX_CANDIDATE_TASKS]
    context = {
        "conversation": {
            "last_task_id": stored.get("last_task_id"),
            "last_view": stored.get("last_view"),
            "preferred_provider": stored.get("preferred_provider"),
            "notification_mode": stored.get("notification_mode"),
            "premium_allowed": stored.get("premium_allowed"),
        },
        "candidate_task_ids": [c["task_id"] for c in candidates],
        "candidate_tasks": [{"task_id": c["task_id"], "state": c["state"],
                             "title": (c.get("manifest") or {}).get("title")} for c in candidates],
    }
    shared_state = getattr(service, "shared_cognitive_state", None)
    if shared_state is not None:
        try:
            current = shared_state.snapshot().get("current_state", {})
            context["project_summary"] = {
                "current_milestone": current.get("current_milestone"),
                "blockers_count": len(current.get("blockers") or []),
                "roadmap_completion": current.get("roadmap_completion"),
            }
        except Exception:  # noqa: BLE001 - this enrichment is optional, never required
            pass
    return context


def _call_gateway(text, context_packet, *, timeout, opener=urllib.request.urlopen):
    gateway_url = os.environ.get("JARVIS_MINISTRAL_GATEWAY_URL", "")
    token = os.environ.get("JARVIS_MINISTRAL_GATEWAY_TOKEN", "")
    if not gateway_url or not token:
        return {"ok": False, "error": "GATEWAY_NOT_CONFIGURED"}
    body = json.dumps({"text": text, "context_packet": context_packet}).encode("utf-8")
    req = urllib.request.Request(
        gateway_url.rstrip("/") + "/v1/jarvis/interpret", data=body,
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
    return {"ok": True, "output": payload.get("output")}


def resolve_intent_via_router(service, message, *, timeout=None, opener=urllib.request.urlopen):
    """Builds context, calls the gateway, validates the answer again
    Render-side. Returns {"ok": True, "output": {...}, "latency_ms": float}
    or {"ok": False, "error": "<reason>", "latency_ms": float} - uniform,
    never raises. Latency is always reported so shadow comparisons and
    fallback decisions both have it, regardless of outcome."""
    started = time.monotonic()
    context_packet = build_router_context(service, message)
    text = message.get("text") or ""
    result = _call_gateway(text, context_packet, timeout=timeout or DEFAULT_TIMEOUT_SECONDS, opener=opener)
    latency_ms = round((time.monotonic() - started) * 1000, 2)
    if not result["ok"]:
        return {"ok": False, "error": result["error"], "latency_ms": latency_ms}
    output = result["output"]
    errors = validate(output, OUTPUT_SCHEMA)
    if errors:
        return {"ok": False, "error": f"RENDER_SIDE_SCHEMA_INVALID: {errors[:3]}", "latency_ms": latency_ms}
    referenced = output.get("referenced_task_id")
    if referenced is not None and referenced not in context_packet["candidate_task_ids"]:
        return {"ok": False, "error": "RENDER_SIDE_REFERENCED_TASK_ID_NOT_IN_CANDIDATES",
                "latency_ms": latency_ms}
    return {"ok": True, "output": output, "latency_ms": latency_ms}


def is_confident_enough(output, threshold=None):
    threshold = DEFAULT_CONFIDENCE_THRESHOLD if threshold is None else threshold
    return bool(output.get("confidence", 0) >= threshold and not output.get("needs_clarification"))
