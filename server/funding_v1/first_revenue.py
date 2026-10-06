"""FIRST_REVENUE_EXECUTION_V1 domain store.

Read/write bookkeeping only.  It cannot send outreach, create contracts, or
move money.  CONTACTED requires an explicit approval record and Revenue can
only be materialized from an observed PAID Revolut record.
"""
from __future__ import annotations

import copy
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


LEAD_TRANSITIONS = {
    "DISCOVERED": {"QUALIFIED", "LOST"},
    "QUALIFIED": {"CONTACT_READY", "LOST"},
    "CONTACT_READY": {"CONTACTED", "LOST"},
    "CONTACTED": {"REPLIED", "LOST"},
    "REPLIED": {"INTERESTED", "LOST"},
    "INTERESTED": {"WON", "LOST"},
    "WON": set(), "LOST": set(),
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _empty():
    return {"schema_version": "FIRST_REVENUE_EXECUTION_V1", "revision": 0,
            "opportunities": [], "offers": [], "prospects": [], "leads": [], "payments": [], "revenues": [],
            "attention_events": [],
            "idempotency_keys": []}


class FirstRevenueStore:
    def __init__(self, path, *, ledger=None):
        self.path = Path(path)
        self.ledger = ledger
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save(_empty())

    def _load(self):
        with self.path.open(encoding="utf-8") as handle:
            value = json.load(handle)
        if value.get("schema_version") != "FIRST_REVENUE_EXECUTION_V1":
            raise RuntimeError("unsupported first revenue store")
        value.setdefault("attention_events", [])
        value.setdefault("prospects", [])
        return value

    def _save(self, value):
        temp = self.path.with_name(f"{self.path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temp, self.path)

    def _tx(self, key, mutator):
        with self._lock:
            state = self._load()
            if key and key in state["idempotency_keys"]:
                return copy.deepcopy(state)
            mutator(state)
            state["revision"] += 1
            if key:
                state["idempotency_keys"] = (state["idempotency_keys"] + [key])[-500:]
            self._save(state)
            return copy.deepcopy(state)

    def snapshot(self):
        with self._lock:
            return copy.deepcopy(self._load())

    def _event(self, record_type, record_id, action):
        if self.ledger:
            self.ledger.append("FIRST_REVENUE_RECORD_UPDATED", None,
                               {"record_type": record_type, "record_id": record_id,
                                "action": action}, actor="first_revenue_execution_v1")

    @staticmethod
    def _upsert(items, id_field, record):
        if any(item[id_field] == record[id_field] for item in items):
            raise ValueError(f"duplicate {id_field}: {record[id_field]}")
        items.append(record)

    def register_opportunity(self, record, *, idempotency_key=None):
        required = {"opportunity_id", "source", "evidence", "target_customer_type", "problem",
                    "possible_solution", "estimated_value", "confidence", "next_action", "provenance"}
        if not required.issubset(record):
            raise ValueError(f"opportunity fields missing: {sorted(required-set(record))}")
        if record["provenance"].get("confidence") not in {"VERIFIED", "DECLARED"}:
            raise ValueError("unverified opportunity cannot become canonical")
        result = self._tx(idempotency_key, lambda state: self._upsert(
            state["opportunities"], "opportunity_id", {**record, "created_at": _now()}))
        self._event("OPPORTUNITY", record["opportunity_id"], "REGISTERED")
        return result

    def create_offer(self, record, *, idempotency_key=None):
        if not record.get("price", {}).get("reviewed"):
            record = {**record, "status": "DRAFT"}
        now = _now()
        def apply(state):
            if not any(item["opportunity_id"] == record.get("opportunity_id")
                       for item in state["opportunities"]):
                raise ValueError("unknown opportunity_id")
            self._upsert(state["offers"], "offer_id",
                         {**record, "created_at": now, "updated_at": now})
        result = self._tx(idempotency_key, apply)
        self._event("OFFER", record["offer_id"], "CREATED")
        return result

    def register_prospect(self, record, *, idempotency_key=None):
        required = {"prospect_id", "dedup_key", "display_name", "source",
                    "source_reference", "evidence", "observed_at", "provenance"}
        if not required.issubset(record):
            raise ValueError(f"prospect fields missing: {sorted(required-set(record))}")
        if record["provenance"].get("confidence") not in {"VERIFIED", "DECLARED"}:
            raise ValueError("unverified prospect cannot become canonical")
        def apply(state):
            existing = next((item for item in state["prospects"]
                             if item["dedup_key"] == record["dedup_key"]), None)
            if existing:
                existing["duplicate_observations"] = existing.get("duplicate_observations", 0) + 1
                existing["last_observed_at"] = record["observed_at"]
                return
            self._upsert(state["prospects"], "prospect_id", {
                **record, "status": "DISCOVERED", "created_at": _now(),
                "last_observed_at": record["observed_at"], "duplicate_observations": 0,
            })
        result = self._tx(idempotency_key, apply)
        self._event("PROSPECT", record["prospect_id"], "INGESTED")
        return result

    def create_lead(self, record, *, idempotency_key=None):
        now = _now()
        value = {**record, "status": "DISCOVERED", "delivery_task_id": None,
                 "outreach_approval": {
            "status": "REQUIRED", "approved_by": None, "approved_at": None,
            "message_fingerprint": None}, "created_at": now, "updated_at": now}
        def apply(state):
            if not any(item["offer_id"] == record.get("offer_id") for item in state["offers"]):
                raise ValueError("unknown offer_id")
            self._upsert(state["leads"], "lead_id", value)
        result = self._tx(idempotency_key, apply)
        self._event("LEAD", record["lead_id"], "DISCOVERED")
        return result

    def transition_lead(self, lead_id, new_status, *, approval=None, idempotency_key=None):
        def apply(state):
            lead = next((item for item in state["leads"] if item["lead_id"] == lead_id), None)
            if not lead:
                raise KeyError(lead_id)
            if new_status not in LEAD_TRANSITIONS[lead["status"]]:
                raise ValueError(f"invalid lead transition {lead['status']} -> {new_status}")
            if new_status == "CONTACTED":
                if not approval or approval.get("status") != "APPROVED" or not approval.get("approved_by"):
                    raise PermissionError("outreach requires explicit human approval")
                lead["outreach_approval"] = {**approval, "approved_at": approval.get("approved_at") or _now()}
            lead["status"] = new_status; lead["updated_at"] = _now()
        result = self._tx(idempotency_key, apply)
        self._event("LEAD", lead_id, new_status)
        return result

    def record_manual_send(self, lead_id, *, approved_fingerprint, draft_fingerprint,
                           approved_by, receipt_reference, idempotency_key=None):
        """Record an observed manual Gmail send; never sends a message itself."""
        if not all(isinstance(value, str) and value.strip() for value in
                   (approved_fingerprint, draft_fingerprint, approved_by, receipt_reference)):
            raise ValueError("manual send requires approval, matching fingerprint and receipt")
        if approved_fingerprint != draft_fingerprint:
            raise PermissionError("stale approval or message fingerprint mismatch")
        def apply(state):
            lead = next(item for item in state["leads"] if item["lead_id"] == lead_id)
            if lead["status"] != "CONTACT_READY":
                raise ValueError(f"invalid lead transition {lead['status']} -> CONTACTED")
            lead["outreach_approval"] = {
                "status": "APPROVED", "approved_by": approved_by,
                "approved_at": _now(), "message_fingerprint": approved_fingerprint,
            }
            lead["outreach_receipt"] = {
                "mode": "MANUAL_SEND_WITH_RECORDED_APPROVAL",
                "reference": receipt_reference,
                "message_fingerprint": draft_fingerprint,
                "recorded_at": _now(),
            }
            lead["status"] = "CONTACTED"
            lead["updated_at"] = _now()
        result = self._tx(idempotency_key, apply)
        self._event("LEAD", lead_id, "CONTACTED")
        self._event("LEAD", lead_id, "MANUAL_SEND_RECORDED")
        return result

    def record_attention(self, record, *, idempotency_key=None):
        required = {"experiment_id", "intervention_type", "active_decision_seconds",
                    "approval_latency_seconds", "recorded_at", "provenance"}
        if not required.issubset(record):
            raise ValueError(f"attention fields missing: {sorted(required-set(record))}")
        if record["active_decision_seconds"] < 0 or record["approval_latency_seconds"] < 0:
            raise ValueError("attention durations cannot be negative")
        value = {**record, "attention_id": record.get("attention_id") or
                 f"ATTN_{uuid.uuid4().hex[:12].upper()}"}
        result = self._tx(idempotency_key, lambda state: self._upsert(
            state["attention_events"], "attention_id", value))
        self._event("ATTENTION", value["attention_id"], "RECORDED")
        return result

    def link_delivery_task(self, lead_id, task_id, *, idempotency_key=None):
        """Reference normal Queue delivery work without duplicating execution."""
        if not isinstance(task_id, str) or not task_id.startswith("TASK_"):
            raise ValueError("delivery requires a canonical TASK_ id")
        def apply(state):
            lead = next((item for item in state["leads"] if item["lead_id"] == lead_id), None)
            if not lead:
                raise KeyError(lead_id)
            if lead["status"] not in {"INTERESTED", "WON"}:
                raise ValueError("delivery task may only be linked after demonstrated interest")
            lead["delivery_task_id"] = task_id
            lead["updated_at"] = _now()
        result = self._tx(idempotency_key, apply)
        self._event("LEAD", lead_id, "DELIVERY_TASK_LINKED")
        return result

    def record_payment(self, record, *, idempotency_key=None):
        if record.get("method") != "REVOLUT" or record.get("money_movement_capability") is not False:
            raise ValueError("V1 only records observed Revolut status and cannot move money")
        if record.get("status") == "PAID" and not record.get("external_reference"):
            raise ValueError("PAID requires an observed external reference")
        def apply(state):
            lead = next((item for item in state["leads"] if item["lead_id"] == record.get("lead_id")), None)
            if not lead or lead["offer_id"] != record.get("offer_id"):
                raise ValueError("payment lead/offer lineage invalid")
            self._upsert(state["payments"], "payment_id",
                         {**record, "observed_at": record.get("observed_at") or _now()})
        result = self._tx(idempotency_key, apply)
        self._event("PAYMENT", record["payment_id"], record["status"])
        return result

    def record_revenue(self, *, payment_id, cost, time_spent, acquisition_source,
                       provenance, idempotency_key=None):
        created = {}
        def apply(state):
            payment = next((item for item in state["payments"] if item["payment_id"] == payment_id), None)
            if not payment or payment["status"] != "PAID":
                raise ValueError("revenue requires an observed PAID payment")
            amount = Decimal(str(payment["amount"])); actual_cost = Decimal(str(cost))
            record = {"revenue_id": f"REV_{uuid.uuid4().hex[:12].upper()}",
                      "payment_id": payment_id, "amount": float(amount),
                      "currency": payment["currency"], "cost": float(actual_cost),
                      "gross_margin": float(amount-actual_cost), "offer_id": payment["offer_id"],
                      "lead_id": payment["lead_id"], "payment_method": "REVOLUT",
                      "payment_status": "PAID", "time_spent": time_spent,
                      "acquisition_source": acquisition_source, "recorded_at": _now(),
                      "provenance": provenance}
            self._upsert(state["revenues"], "revenue_id", record); created.update(record)
        self._tx(idempotency_key, apply)
        self._event("REVENUE", created["revenue_id"], "RECORDED")
        return created
