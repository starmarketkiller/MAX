"""AGENCY_* executive events.

Events are appended to the canonical EventLedger (NEXUS_EVENT_V1, enum
extended additively) and forwarded to the existing Jarvis notification path
by the sink wired in app.py.  Only attention events push to Telegram.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

AGENCY_EVENT_TYPES = (
    "AGENCY_MODEL_READY", "AGENCY_CASTING_REQUIRED", "AGENCY_TREND_FOUND",
    "AGENCY_PRODUCT_FOUND", "AGENCY_STORE_BLOCKED", "AGENCY_STORE_READY",
    "AGENCY_CONTENT_READY", "AGENCY_APPROVAL_REQUIRED", "AGENCY_CAMPAIGN_READY",
    "AGENCY_SOCIAL_SCHEDULED", "AGENCY_CONTENT_PUBLISHED", "AGENCY_REVENUE_EVENT",
    "AGENCY_COST_ALERT",
)
# Events that deserve a proactive Jarvis push; the rest are ledger-only.
ATTENTION_EVENTS = {"AGENCY_APPROVAL_REQUIRED", "AGENCY_CASTING_REQUIRED",
                    "AGENCY_STORE_BLOCKED", "AGENCY_COST_ALERT", "AGENCY_CAMPAIGN_READY",
                    "AGENCY_REVENUE_EVENT"}

SUMMARIES_IT = {
    "AGENCY_MODEL_READY": "Agenzia: modella pronta",
    "AGENCY_CASTING_REQUIRED": "Agenzia: serve un casting/approvazione character sheet",
    "AGENCY_TREND_FOUND": "Agenzia: nuovo trend registrato",
    "AGENCY_PRODUCT_FOUND": "Agenzia: nuovo prodotto candidato",
    "AGENCY_STORE_BLOCKED": "Agenzia: prodotto bloccato dallo store gate",
    "AGENCY_STORE_READY": "Agenzia: prodotto store-ready",
    "AGENCY_CONTENT_READY": "Agenzia: contenuto pronto per la revisione",
    "AGENCY_APPROVAL_REQUIRED": "Agenzia: serve la tua approvazione",
    "AGENCY_CAMPAIGN_READY": "Agenzia: campagna pronta",
    "AGENCY_SOCIAL_SCHEDULED": "Agenzia: post programmato",
    "AGENCY_CONTENT_PUBLISHED": "Agenzia: contenuto pubblicato",
    "AGENCY_REVENUE_EVENT": "Agenzia: nuovo ricavo registrato",
    "AGENCY_COST_ALERT": "Agenzia: allarme costi",
}


def build_event(event_type, entity_id, payload, *, requires_human=False):
    if event_type not in AGENCY_EVENT_TYPES:
        raise ValueError("unsupported agency event")
    detail = payload.get("detail")
    return {"event_id": f"AEV_{uuid.uuid4().hex[:12].upper()}", "event_type": event_type,
            "business_unit_id": "AI_FASHION_AGENCY", "entity_id": entity_id,
            "payload": dict(payload), "requires_human_action": bool(requires_human),
            "attention": event_type in ATTENTION_EVENTS,
            "summary": SUMMARIES_IT[event_type] + (f": {detail}" if detail else "") + ".",
            "created_at": datetime.now(timezone.utc).isoformat()}


def ledger_sink(ledger, notify=None):
    """Sink factory for app.py: ledger-first, then Jarvis push for attention events."""
    def sink(event):
        ledger.append(event["event_type"], None,
                      {"entity_id": event["entity_id"], "business_unit_id": "AI_FASHION_AGENCY",
                       "requires_human_action": event["requires_human_action"],
                       "summary": event["summary"]},
                      actor="ai_fashion_agency_v2")
        if notify and event["attention"]:
            notify(event)
    return sink
