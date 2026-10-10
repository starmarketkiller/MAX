"""The one offer that can take money first: manual lead research at 25 EUR.

This opens the catalog, accepts a prospect only with a public https source,
and books revenue only from an observed Revolut payment. It does not browse,
send mail, or move money.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

OPPORTUNITY_ID = "OPP_LEAD_RESEARCH_SERVICE"
OFFER_ID = "OFFER_LEAD_RESEARCH_25"
PRICE_EUR = 25


def _provenance(source_url):
    return {"source": source_url, "confidence": "VERIFIED", "reference": source_url}


def _slug(value):
    token = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    return (token or "PROSPECT")[:24]


def ensure_catalog(store):
    state = store.snapshot()
    if not any(item["opportunity_id"] == OPPORTUNITY_ID for item in state["opportunities"]):
        store.register_opportunity({
            "opportunity_id": OPPORTUNITY_ID,
            "source": "vault/02-Business/Opportunity-Funding/NEXUS TASK 0011",
            "evidence": ["Public offer: 15-20 qualified leads for 25 EUR, manual delivery"],
            "target_customer_type": "small Italian web agency",
            "problem": "the agency needs qualified local leads and does not have them",
            "possible_solution": "deliver 15-20 sourced leads after a yes",
            "estimated_value": {"amount": PRICE_EUR, "currency": "EUR", "status": "ESTIMATE"},
            "confidence": "LOW",
            "next_action": "wait for a reply, then deliver only sourced leads",
            "provenance": {"source": "vault", "confidence": "DECLARED", "reference": "TASK_0011"},
        }, idempotency_key="lead-research-opportunity")
    state = store.snapshot()
    if not any(item["offer_id"] == OFFER_ID for item in state["offers"]):
        store.create_offer({
            "offer_id": OFFER_ID,
            "opportunity_id": OPPORTUNITY_ID,
            "problem": "qualified leads are missing",
            "deliverable": "15 to 20 sourced leads, not contacted by NEXUS",
            "price": {"amount": PRICE_EUR, "currency": "EUR", "reviewed": True},
            "delivery_time": "after the prospect says yes",
            "included": ["sourced lead list"],
            "excluded": ["autonomous outreach", "payment initiation", "invented contacts"],
            "status": "REVIEWED",
            "provenance": {"source": "vault", "confidence": "DECLARED", "reference": "TASK_0011"},
        }, idempotency_key="lead-research-offer")
    return store.snapshot()


def open_prospect(store, *, display_name, company, source_url):
    ensure_catalog(store)
    name = str(display_name or "").strip()
    firm = str(company or "").strip()
    source = str(source_url or "").strip()
    if not name or not firm or not source.startswith("https://"):
        raise ValueError("prospect requires a name, a company and an https source")
    existing = next((item for item in store.snapshot()["leads"]
                     if item.get("website") == source and item["offer_id"] == OFFER_ID), None)
    if existing:
        return {"lead_id": existing["lead_id"], "status": existing["status"],
                "offer_id": OFFER_ID, "price_eur": PRICE_EUR, "sends_mail": False, "created": False}
    prospect_id = f"PROSPECT_{_slug(firm)}_{uuid.uuid4().hex[:6].upper()}"
    lead_id = f"LEAD_{_slug(firm)}_{uuid.uuid4().hex[:6].upper()}"
    observed = datetime.now(timezone.utc).isoformat()
    store.register_prospect({
        "prospect_id": prospect_id, "dedup_key": source, "display_name": name,
        "source": source, "source_reference": source, "evidence": [source],
        "observed_at": observed, "company": firm, "provenance": _provenance(source),
    }, idempotency_key=f"prospect:{source}")
    store.create_lead({
        "lead_id": lead_id, "opportunity_id": OPPORTUNITY_ID, "offer_id": OFFER_ID,
        "display_name": name, "customer_type": "small Italian web agency",
        "company": firm, "website": source, "source": source,
        "service_interest": "lead research", "fit_score": None,
        "next_action": "human sends the message; NEXUS does not",
        "provenance": _provenance(source),
    }, idempotency_key=f"lead:{source}")
    store.transition_lead(lead_id, "QUALIFIED", idempotency_key=f"qualify:{lead_id}")
    store.transition_lead(lead_id, "CONTACT_READY", idempotency_key=f"ready:{lead_id}")
    return {"lead_id": lead_id, "prospect_id": prospect_id, "status": "CONTACT_READY",
            "offer_id": OFFER_ID, "price_eur": PRICE_EUR, "sends_mail": False, "created": True}


def attach_delivery(store, lead_id, items):
    store.attach_sourced_delivery(lead_id, items, idempotency_key=f"delivery:{lead_id}")
    pack = next(item for item in store.snapshot()["deliveries"] if item["lead_id"] == lead_id)
    return {"delivery_id": pack["delivery_id"], "count": pack["count"], "sent": False}


def book_observed_payment(store, *, lead_id, external_reference, cost=0):
    reference = str(external_reference or "").strip()
    if len(reference) < 4:
        raise ValueError("PAID requires an observed Revolut reference")
    state = store.snapshot()
    lead = next((item for item in state["leads"] if item["lead_id"] == lead_id), None)
    if not lead or lead["status"] != "INTERESTED":
        raise ValueError("payment requires a lead that already replied interested")
    if not any(item["lead_id"] == lead_id for item in state["deliveries"]):
        raise ValueError("payment requires the sourced delivery pack")
    payment_id = f"PAY_{uuid.uuid4().hex[:12].upper()}"
    store.record_payment({
        "payment_id": payment_id, "offer_id": OFFER_ID, "lead_id": lead_id,
        "amount": PRICE_EUR, "currency": "EUR", "method": "REVOLUT", "status": "PAID",
        "external_reference": reference, "money_movement_capability": False,
        "provenance": {"source": "revolut", "confidence": "VERIFIED", "reference": reference},
    }, idempotency_key=f"pay:{reference}")
    store.transition_lead(lead_id, "WON", idempotency_key=f"won:{reference}")
    return store.record_revenue(
        payment_id=payment_id, cost=cost, time_spent="observed",
        acquisition_source="manual outreach",
        provenance={"source": "revolut", "confidence": "VERIFIED", "reference": reference},
        idempotency_key=f"rev:{reference}")


def public_status(store):
    ensure_catalog(store)
    state = store.snapshot()
    return {
        "offer_id": OFFER_ID,
        "price_eur": PRICE_EUR,
        "sends_mail": False,
        "moves_money": False,
        "leads": [{"lead_id": item["lead_id"], "display_name": item["display_name"],
                   "status": item["status"], "company": item.get("company"),
                   "website": item.get("website")} for item in state["leads"]
                  if item["offer_id"] == OFFER_ID],
        "deliveries": [{"delivery_id": item["delivery_id"], "lead_id": item["lead_id"],
                        "count": item["count"], "sent": item["sent"]}
                       for item in state["deliveries"]],
        "revenue_count": len(state["revenues"]),
    }
