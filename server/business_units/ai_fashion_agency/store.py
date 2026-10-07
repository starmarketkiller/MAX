"""AI_FASHION_AGENCY_REGISTRY_V1: persistent domain state of the Agency.

Same persistence idiom as RevenueVentureRegistry (atomic JSON replace,
revision counter, idempotency keys).  It is domain state only: work items
live in the canonical TaskQueue, events in the EventLedger.  Nothing here
publishes, spends credits, opens a store or contacts anyone.
"""
from __future__ import annotations

import copy
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "AI_FASHION_AGENCY_REGISTRY_V1"

MODEL_STATUSES = ("CASTING_DRAFT", "DESIGN_PENDING_APPROVAL", "CHARACTER_SHEET_READY",
                  "ACTIVE", "PAUSED", "RETIRED")
INPUT_TYPES = ("TREND_VIDEO", "TREND_AUDIO", "TREND_FORMAT", "PRODUCT", "FASHION_ITEM",
               "SERVICE", "CAMPAIGN", "AFFILIATE_OFFER", "BRAND_REQUEST", "CONTENT_IDEA",
               "SEASON_EVENT")
INPUT_STATES = ("RECEIVED", "CLASSIFIED", "ROUTED", "REJECTED")
BRIEF_STATES = ("DRAFT", "ASSIGNED", "PACK_READY", "WAITING_APPROVAL", "APPROVED",
                "GENERATED", "IN_REVIEW", "PUBLISHED", "REJECTED")
PACK_STATES = ("WAITING_QUOTE", "WAITING_APPROVAL", "APPROVED", "SUBMITTED", "COMPLETED",
               "REJECTED", "CANCELLED")
COST_CATEGORIES = ("generation_credits", "higgsfield", "api", "ads", "store_fees", "social",
                   "tools", "human_time")
REVENUE_STREAMS = ("affiliate", "own_store", "sponsored_product", "ugc_service",
                   "brand_campaign", "creator_sponsorship", "fashion_promotion",
                   "digital_product", "agency_service", "model_licensing", "social_monetization")


def _now():
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:10].upper()}"


def _seed():
    from .roster import initial_roster
    return {"schema_version": SCHEMA, "revision": 0, "models": initial_roster(),
            "inputs": [], "products": [], "briefs": [], "assignments": [],
            "generation_packs": [], "campaigns": [], "costs": [], "revenue_events": [],
            "idempotency_index": {}}


class AgencyStore:
    COLLECTIONS = ("models", "inputs", "products", "briefs", "assignments",
                   "generation_packs", "campaigns", "costs", "revenue_events")
    KEYS = {"models": "model_id", "inputs": "input_id", "products": "product_id",
            "briefs": "brief_id", "assignments": "assignment_id",
            "generation_packs": "pack_id", "campaigns": "campaign_id", "costs": "cost_id",
            "revenue_events": "revenue_event_id"}

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save(_seed())

    def _load(self):
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if value.get("schema_version") != SCHEMA:
            raise RuntimeError("unsupported agency registry")
        return value

    def _save(self, value):
        temp = self.path.with_name(self.path.name + f".{os.getpid()}.tmp")
        temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, self.path)

    def snapshot(self):
        with self._lock:
            return copy.deepcopy(self._load())

    def get(self, collection, item_id):
        key = self.KEYS[collection]
        found = next((x for x in self.snapshot()[collection] if x[key] == item_id), None)
        if found is None:
            raise KeyError(f"{collection}:{item_id}")
        return found

    def upsert(self, collection, record, *, idempotency_key=None):
        """Insert or replace one record.  Domain rules live in pipeline.py."""
        if collection not in self.COLLECTIONS:
            raise ValueError("unknown agency collection")
        key = self.KEYS[collection]
        if not record.get(key):
            raise ValueError(f"{key} required")
        with self._lock:
            state = self._load()
            index_entry = state["idempotency_index"].get(idempotency_key) if idempotency_key else None
            if index_entry:
                stored_collection, stored_id = index_entry
                return copy.deepcopy(next(x for x in state[stored_collection]
                                          if x[self.KEYS[stored_collection]] == stored_id))
            items = state[collection]
            record = {**record, "updated_at": _now()}
            index = next((i for i, x in enumerate(items) if x[key] == record[key]), None)
            if index is None:
                record.setdefault("created_at", record["updated_at"])
                items.append(record)
            else:
                items[index] = {**items[index], **record}
                record = items[index]
            state["revision"] += 1
            if idempotency_key:
                state["idempotency_index"][idempotency_key] = [collection, record[key]]
            self._save(state)
            return copy.deepcopy(record)
