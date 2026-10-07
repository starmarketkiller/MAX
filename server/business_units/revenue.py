"""BUSINESS_UNIT_REVENUE_V1: Revenue-side projection for revenue-bearing units.

Revenue V1 (FirstRevenueStore / REVENUE_V1) stays the authority for paid
Revolut orders and the zero-budget venture registry stays fixed at its four
ventures.  Business units with their own cost base (credits, fees) publish
observed revenue events with business_unit_id and appear here, so Jarvis
/revenue shows them next to the ventures without a second revenue system.
"""
from __future__ import annotations


def _top(events, key):
    totals = {}
    for e in events:
        if e.get(key):
            totals[e[key]] = totals.get(e[key], 0) + float(e.get("gross_revenue_eur",
                                                                  e.get("amount_eur", 0)))
    return max(totals, key=totals.get) if totals else None


def agency_revenue_projection(agency_store):
    s = agency_store.snapshot()
    events = s["revenue_events"]
    gross = round(sum(float(e.get("gross_revenue_eur", e.get("amount_eur", 0))) for e in events), 2)
    event_costs = sum(float(e.get("costs_eur") or 0) for e in events)
    op_costs = sum(float(c.get("eur") or 0) for c in s["costs"])
    costs = round(event_costs + op_costs, 2)
    return {"schema_version": "BUSINESS_UNIT_REVENUE_V1", "business_unit_id": "AI_FASHION_AGENCY",
            "revenue_events": len(events), "gross_revenue_eur": gross, "costs_eur": costs,
            "net_revenue_eur": round(gross - costs, 2),
            "credits_spent": round(sum(float(c.get("credits") or 0) for c in s["costs"]), 4),
            "credits_valued_in_eur": all(c.get("eur") is not None for c in s["costs"]
                                         if c.get("credits")),
            "top_model": _top(events, "model_id"), "top_campaign": _top(events, "campaign_id"),
            "top_product": _top(events, "product_id"),
            "linked_revenue_v1_ids": sorted({e["revenue_v1_id"] for e in events
                                             if e.get("revenue_v1_id")})}


def business_units_revenue(*, agency_store=None):
    return [agency_revenue_projection(agency_store)] if agency_store else []
