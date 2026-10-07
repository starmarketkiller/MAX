"""Read-only projections of the Agency for Jarvis and the executive layer.

AI_FASHION_AGENCY_STATE_V1 is what Jarvis reads; business_unit_state() is the
same facts in the shared BUSINESS_UNIT_STATE_V1 shape so the future
NEXUS_EXECUTIVE_STATE_V1 can embed it as `ai_fashion_agency` without a
parallel executive state.
"""
from __future__ import annotations

from datetime import datetime, timezone

from business_units import build_business_unit_state

ACTIVE_MODEL_STATUSES = {"ACTIVE", "CHARACTER_SHEET_READY"}
QUEUE_BRIEF_STATES = {"DRAFT", "ASSIGNED", "PACK_READY", "WAITING_APPROVAL", "APPROVED",
                      "GENERATED", "IN_REVIEW"}
BLOCKED_PRODUCT_STATES = {"DISCOVERED", "EVALUATING", "STORE_PENDING"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _sum(items, key):
    return round(sum(float(x.get(key) or 0) for x in items), 4)


def agency_state(store, *, queue=None):
    s = store.snapshot()
    models, briefs, packs = s["models"], s["briefs"], s["generation_packs"]
    products, revenue, costs = s["products"], s["revenue_events"], s["costs"]
    waiting_packs = [p for p in packs if p["state"] == "WAITING_APPROVAL"]
    revenue_eur, costs_eur = _sum(revenue, "amount_eur"), _sum(costs, "eur")
    credits_spent = _sum(costs, "credits")
    store_ready = [p for p in products if p["status"] == "STORE_READY"]
    store_blocked = [p for p in products if p["status"] in BLOCKED_PRODUCT_STATES]

    by_model = {}
    for event in revenue:
        by_model[event["model_id"]] = by_model.get(event["model_id"], 0) + event["amount_eur"]
    views_by_model = {m["model_id"]: m["performance_metrics"]["views"] for m in models}
    top_model = (max(by_model, key=by_model.get) if by_model else
                 (max(views_by_model, key=views_by_model.get)
                  if any(views_by_model.values()) else None))
    by_campaign = {}
    for event in revenue:
        if event.get("campaign_id"):
            by_campaign[event["campaign_id"]] = by_campaign.get(event["campaign_id"], 0) + \
                event["amount_eur"]
    ready_campaigns = [b for b in briefs if b["status"] in {"WAITING_APPROVAL", "APPROVED"}]

    alerts, next_actions = [], []
    for pack in waiting_packs:
        next_actions.append({"action": "APPROVE_OR_REJECT_GENERATION_PACK",
                             "pack_id": pack["pack_id"], "credits": pack["quoted_credits"],
                             "requires": "EXPLICIT_USER_APPROVAL"})
    for product in store_blocked:
        next_actions.append({"action": "ADVANCE_STORE_GATE", "product_id": product["product_id"],
                             "status": product["status"]})
    for pack in packs:
        if pack["unquoted_steps"] and pack["state"] in {"WAITING_QUOTE", "WAITING_APPROVAL"}:
            alerts.append(f"{pack['pack_id']}: {len(pack['unquoted_steps'])} step senza preventivo")
    rejected = [b for b in briefs if b["status"] == "REJECTED"]
    if rejected:
        alerts.append(f"{len(rejected)} brief bloccati dalla compliance")
    if not any(m["social_accounts"] for m in models):
        alerts.append("nessun account social collegato")
    if not any(m["status"] in ACTIVE_MODEL_STATUSES for m in models):
        next_actions.append({"action": "APPROVE_FIRST_CHARACTER_SHEET",
                             "requires": "EXPLICIT_USER_APPROVAL"})

    health = ("NOT_STARTED" if not (briefs or products or revenue) else
              "AMBER" if waiting_packs or store_blocked or rejected else "GREEN")
    tasks = [t for t in (queue.list_all() if queue else [])
             if t.get("action") == "agency_bounded_task"]
    published = [b for b in briefs if b["status"] == "PUBLISHED"]
    metrics = [m["performance_metrics"] for m in models]
    return {
        "schema_version": "AI_FASHION_AGENCY_STATE_V1", "health": health,
        "models_total": len(models),
        "models_active": sum(m["status"] in ACTIVE_MODEL_STATUSES for m in models),
        "models_casting": sum(m["status"] in {"CASTING_DRAFT", "DESIGN_PENDING_APPROVAL"}
                              for m in models),
        "campaigns_active": len(ready_campaigns),
        "content_queue": sum(b["status"] in QUEUE_BRIEF_STATES for b in briefs),
        "store_ready": len(store_ready), "store_blocked": len(store_blocked),
        "awaiting_approval": len(waiting_packs),
        "credits_pending_approval": round(sum(p["quoted_credits"] for p in waiting_packs), 4),
        "credits_spent": credits_spent, "published": len(published),
        "views": sum(m["views"] for m in metrics),
        "engagement": sum(m["engagement"] for m in metrics),
        "followers": sum(m["followers"] for m in metrics),
        "revenue_eur": revenue_eur, "costs_eur": costs_eur,
        "profit_eur": round(revenue_eur - costs_eur, 2),
        "top_model": top_model,
        "top_campaign": max(by_campaign, key=by_campaign.get) if by_campaign else None,
        "agency_tasks": {"total": len(tasks),
                         "open": sum(t["state"] not in {"COMPLETED", "FAILED", "CANCELLED"}
                                     for t in tasks)},
        "alerts": alerts, "next_actions": next_actions,
        "commercial_actions_enabled": False, "publishing_enabled": False,
        "generated_at": _now(),
    }


def jarvis_summary(state):
    """One Italian sentence Jarvis can say as-is."""
    parts = [f"{state['campaigns_active']} campagna pronta" if state["campaigns_active"] == 1
             else f"{state['campaigns_active']} campagne pronte",
             f"{state['store_ready']} prodotto store-ready" if state["store_ready"] == 1
             else f"{state['store_ready']} prodotti store-ready",
             f"{state['models_total']} modelle in roster ({state['models_active']} attive)"]
    text = "AI Fashion Agency: " + ", ".join(parts)
    if state["awaiting_approval"]:
        text += (f"; generazione Higgsfield in attesa di approvazione "
                 f"({state['credits_pending_approval']:g} crediti)")
    text += f". Ricavi €{state['revenue_eur']:.2f}, costi €{state['costs_eur']:.2f}, " \
            f"crediti spesi {state['credits_spent']:g}."
    return text


def business_unit_state(store, *, queue=None):
    st = agency_state(store, queue=queue)
    decision = ({"status": "HUMAN_APPROVAL_REQUIRED", "items": st["next_actions"]}
                if any(a.get("requires") == "EXPLICIT_USER_APPROVAL" for a in st["next_actions"])
                else {"status": "NONE", "items": []})
    return build_business_unit_state(
        unit_id="AI_FASHION_AGENCY", name="AI Fashion Agency",
        mission="Coordinate a roster of disclosed AI fashion/lifestyle creators that turn "
                "NEXUS trend and product opportunities into original content and revenue.",
        state="FOUNDATION" if st["health"] == "NOT_STARTED" else "OPERATING",
        health=st["health"],
        inputs=["TREND_VIDEO", "TREND_AUDIO", "TREND_FORMAT", "PRODUCT", "FASHION_ITEM",
                "SERVICE", "CAMPAIGN", "AFFILIATE_OFFER", "BRAND_REQUEST", "CONTENT_IDEA",
                "SEASON_EVENT"],
        workers=["canonical Orchestrator (agency_bounded_task)", "local Ministral",
                 "Higgsfield via approved Claude session"],
        capabilities=["viral_format_analysis", "product_opportunity_scout", "store_gate",
                      "model_casting", "content_brief", "compliance_check",
                      "generation_pack", "revenue_attribution"],
        kpis={k: st[k] for k in ("models_active", "content_queue", "published", "views",
                                 "engagement", "followers", "credits_spent")},
        costs_eur=st["costs_eur"], revenue_eur=st["revenue_eur"],
        risks=["platform AI-label enforcement", "advertising disclosure (AGCOM)",
               "copyright on trend references", "credit spend without ROI"],
        tasks=st["agency_tasks"], evidence=["AI_FASHION_AGENCY_STATE_V1"],
        next_gate="FIRST_CHARACTER_SHEET_APPROVAL" if st["models_active"] == 0
        else "FIRST_PUBLISHED_CONTENT",
        decision=decision)
