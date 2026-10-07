"""Read-only projections of the Agency for Jarvis and the executive layer.

AI_FASHION_AGENCY_STATE_V1 (V2 fields added additively) is what Jarvis
reads; business_unit_state() is the same facts in the shared
BUSINESS_UNIT_STATE_V1 shape so NEXUS_EXECUTIVE_STATE_V1 can embed it as
`ai_fashion_agency`.  agency_answer() is a deterministic answer selector over
this projection, used by the existing Jarvis command path - not a second
conversational engine.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from business_units import build_business_unit_state
from business_units.revenue import agency_revenue_projection

from .kpis import agency_kpis, campaign_kpis, model_kpis

ACTIVE_MODEL_STATUSES = {"ACTIVE", "CHARACTER_SHEET_READY"}
QUEUE_BRIEF_STATES = {"DRAFT", "ASSIGNED", "PACK_READY", "WAITING_APPROVAL", "APPROVED",
                      "GENERATED", "IN_REVIEW"}
BLOCKED_PRODUCT_STATES = {"DISCOVERED", "EVALUATING", "STORE_PENDING"}
TREND_INPUTS = {"TREND_VIDEO", "TREND_AUDIO", "TREND_FORMAT"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _approvals(s):
    items = []
    for pack in s["generation_packs"]:
        if pack["state"] == "WAITING_APPROVAL":
            model = next(m for m in s["models"] if m["model_id"] == pack["model_id"])
            items.append({"kind": "GENERATION_PACK", "id": pack["pack_id"],
                          "what": f"generazione Higgsfield per {model['stage_name']}",
                          "credits": pack["quoted_credits"]})
    for product in s["products"]:
        candidate = product.get("listing_candidate") or {}
        if candidate.get("approval_status") == "WAITING_APPROVAL":
            items.append({"kind": "STORE_LISTING", "id": product["product_id"],
                          "what": f"listing di '{product['title']}'", "credits": 0})
    for post in s["social_posts"]:
        if post["state"] == "READY_FOR_REVIEW":
            items.append({"kind": "SOCIAL_POST", "id": post["post_id"],
                          "what": f"post {post['platform']}", "credits": 0})
    return items


def agency_state(store, *, queue=None):
    s = store.snapshot()
    models, briefs, packs = s["models"], s["briefs"], s["generation_packs"]
    products, posts = s["products"], s["social_posts"]
    revenue = agency_revenue_projection(store)
    kpis = agency_kpis(s)
    approvals = _approvals(s)
    waiting_packs = [p for p in packs if p["state"] == "WAITING_APPROVAL"]
    store_ready = [p for p in products if p["status"] == "STORE_READY"]
    store_pending = [p for p in products if p["status"] == "STORE_PENDING"]
    blocked = [p for p in products if p["status"] in BLOCKED_PRODUCT_STATES]
    ready_campaigns = [b for b in briefs if b["status"] in {"WAITING_APPROVAL", "APPROVED"}]
    working = sorted({b["model_id"] for b in briefs
                      if b.get("model_id") and b["status"] in QUEUE_BRIEF_STATES})
    names = {m["model_id"]: m["stage_name"] for m in models}
    accounts = [a for m in models for a in m["social_accounts"]]

    alerts, next_actions = [], []
    for item in approvals:
        next_actions.append({"action": "APPROVE_OR_REJECT", **item,
                             "requires": "EXPLICIT_USER_APPROVAL"})
    for product in blocked:
        next_actions.append({"action": "ADVANCE_STORE_GATE", "product_id": product["product_id"],
                             "status": product["status"]})
    for pack in packs:
        if pack["unquoted_steps"] and pack["state"] in {"WAITING_QUOTE", "WAITING_APPROVAL"}:
            alerts.append(f"{pack['pack_id']}: {len(pack['unquoted_steps'])} step senza preventivo")
    rejected = [b for b in briefs if b["status"] == "REJECTED"]
    if rejected:
        alerts.append(f"{len(rejected)} brief bloccati dalla compliance")
    if not any(a["status"] == "ACTIVE" for a in accounts):
        alerts.append("nessun account social attivo (tutti NOT_CREATED)")
    if not any(m["status"] in ACTIVE_MODEL_STATUSES for m in models):
        next_actions.append({"action": "APPROVE_FIRST_CHARACTER_SHEET",
                             "requires": "EXPLICIT_USER_APPROVAL"})

    health = ("NOT_STARTED" if not (briefs or products or s["revenue_events"]) else
              "AMBER" if waiting_packs or blocked or rejected else "GREEN")
    tasks = [t for t in (queue.list_all() if queue else [])
             if t.get("action") == "agency_bounded_task"]
    return {
        "schema_version": "AI_FASHION_AGENCY_STATE_V1", "health": health,
        "models_total": len(models),
        "models_active": sum(m["status"] in ACTIVE_MODEL_STATUSES for m in models),
        "models_casting": sum(m["status"] in {"CASTING_DRAFT", "DESIGN_PENDING_APPROVAL"}
                              for m in models),
        "models_working": [names[m] for m in working],
        "campaigns_active": len(ready_campaigns),
        "content_queue": sum(b["status"] in QUEUE_BRIEF_STATES for b in briefs),
        "trend_inputs": sum(i["input_type"] in TREND_INPUTS for i in s["inputs"]),
        "products_found": len(products), "store_pending": len(store_pending),
        "store_ready": len(store_ready), "store_blocked": len(blocked),
        "blocked_products": [{"product_id": p["product_id"], "title": p["title"],
                              "status": p["status"],
                              "reasons": p.get("blocked_reasons") or []} for p in blocked],
        "content_ready": sum(p["state"] == "READY" for p in s["content_packages"]),
        "awaiting_approval": len(approvals), "approvals": approvals,
        "credits_pending_approval": round(sum(p["quoted_credits"] for p in waiting_packs), 4),
        "credits_spent": kpis["credits_spent"],
        "scheduled": sum(p["state"] == "SCHEDULED" for p in posts),
        "published": sum(p["state"] == "PUBLISHED" for p in posts),
        "views": kpis["views"], "engagement": kpis["engagement"],
        "followers": (sum(a["followers"] for a in accounts if isinstance(a.get("followers"), int))
                      if any(isinstance(a.get("followers"), int) for a in accounts)
                      else "UNAVAILABLE"),
        "accounts": {"total": len(accounts),
                     "active": sum(a["status"] == "ACTIVE" for a in accounts),
                     "not_created": sum(a["status"] == "NOT_CREATED" for a in accounts)},
        "revenue_eur": revenue["gross_revenue_eur"], "costs_eur": revenue["costs_eur"],
        "profit_eur": revenue["net_revenue_eur"],
        "top_model": revenue["top_model"], "top_campaign": revenue["top_campaign"],
        "top_product": revenue["top_product"], "kpis": kpis,
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
    if state["credits_pending_approval"]:
        text += (f"; generazione Higgsfield in attesa di approvazione "
                 f"({state['credits_pending_approval']:g} crediti)")
    text += f". Ricavi €{state['revenue_eur']:.2f}, costi €{state['costs_eur']:.2f}, " \
            f"crediti spesi {state['credits_spent']:g}."
    return text


def _eur(value):
    return f"€{value:.2f}"


def agency_answer(question, store, *, queue=None):
    """Deterministic answer for the executive questions in the V2 brief."""
    st = agency_state(store, queue=queue)
    s = store.snapshot()
    q = (question or "").lower()
    if re.search(r"approv", q):
        if not st["approvals"]:
            return "Agenzia: niente da approvare in questo momento.", st
        items = "; ".join(f"{a['what']}" + (f" ({a['credits']:g} crediti)" if a["credits"] else "")
                          for a in st["approvals"])
        return f"Agenzia — da approvare: {items}.", st
    if re.search(r"guadagn|ricav|profit|soldi|incass", q):
        return (f"Agenzia: ricavi {_eur(st['revenue_eur'])}, costi {_eur(st['costs_eur'])}, "
                f"profitto {_eur(st['profit_eur'])}, crediti spesi {st['credits_spent']:g}. "
                + ("Nessun ricavo osservato finora." if not s["revenue_events"] else "")).strip(), st
    if re.search(r"prodott", q):
        blocked = ", ".join(f"{p['title']} ({p['status']})" for p in st["blocked_products"]) or "nessuno"
        return (f"Agenzia: {st['products_found']} prodotti trovati, {st['store_ready']} store-ready, "
                f"{st['store_pending']} in attesa di listing. Bloccati: {blocked}."), st
    if re.search(r"account", q):
        rows = {}
        for m in s["models"]:
            active = [a["platform"] for a in m["social_accounts"] if a["status"] == "ACTIVE"]
            rows[m["stage_name"]] = active
        with_acc = [n for n, a in rows.items() if a]
        return (f"Agenzia: account attivi {st['accounts']['active']}/{st['accounts']['total']}. "
                f"Modelle con account: {', '.join(with_acc) or 'nessuna'}. "
                f"Da creare: {st['accounts']['not_created']} slot (handle non ancora assegnati)."), st
    if re.search(r"cresc|crescendo", q):
        if st["followers"] == "UNAVAILABLE":
            return ("Agenzia: crescita non misurabile — nessun account attivo né dati di "
                    "analytics (UNAVAILABLE)."), st
        growth = {v["stage_name"]: v["followers_growth"] for v in model_kpis(s).values()
                  if isinstance(v["followers_growth"], (int, float))}
        if growth:
            best = max(growth, key=growth.get)
            return f"Agenzia: cresce di più {best} (+{growth[best]:g} follower).", st
    if re.search(r"campagn", q):
        rows = campaign_kpis(s)
        if not rows:
            return "Agenzia: nessuna campagna commerciale ancora (serve un prodotto store-ready).", st
        best = max(rows.items(), key=lambda kv: (kv[1]["revenue"], kv[1]["status"] != "REJECTED"))
        return (f"Agenzia: campagna più promettente '{best[1]['title']}' "
                f"(stato {best[1]['status']}, store gate {best[1]['store_gate_status']}, "
                f"ricavi {_eur(best[1]['revenue'])})."), st
    if re.search(r"modell|lavorando", q):
        mk = model_kpis(s)
        working = ", ".join(st["models_working"]) or "nessuna"
        statuses = ", ".join(f"{v['stage_name']} {v['status']}" for v in mk.values())
        return f"Agenzia: modelle al lavoro: {working}. Roster: {statuses}.", st
    return jarvis_summary(st), st


def business_unit_state(store, *, queue=None):
    st = agency_state(store, queue=queue)
    decision = ({"status": "HUMAN_APPROVAL_REQUIRED", "items": st["next_actions"]}
                if any(a.get("requires") == "EXPLICIT_USER_APPROVAL" for a in st["next_actions"])
                else {"status": "NONE", "items": []})
    return build_business_unit_state(
        unit_id="AI_FASHION_AGENCY", name="AI Fashion Agency",
        mission="Coordinate a roster of disclosed AI fashion/lifestyle creators that turn "
                "NEXUS trend and product opportunities into original content and revenue.",
        state="FOUNDATION" if st["health"] == "NOT_STARTED" else "OPERATING_DRY_RUN",
        health=st["health"],
        inputs=["TREND_VIDEO", "TREND_AUDIO", "TREND_FORMAT", "PRODUCT", "FASHION_ITEM",
                "SERVICE", "CAMPAIGN", "AFFILIATE_OFFER", "BRAND_REQUEST", "CONTENT_IDEA",
                "SEASON_EVENT"],
        workers=["canonical Orchestrator (agency_bounded_task)", "local Ministral",
                 "Higgsfield via approved Claude session", "Postiz (dry-run adapter)"],
        capabilities=["scouting", "viral_format_analysis", "store_gate", "model_casting",
                      "content_brief", "compliance_check", "generation_pack", "social_drafts",
                      "revenue_attribution", "kpis"],
        kpis={k: st["kpis"][k] for k in ("content_created", "content_published", "views",
                                         "engagement", "sales", "ROI", "credits_spent")},
        costs_eur=st["costs_eur"], revenue_eur=st["revenue_eur"],
        risks=["platform AI-label enforcement", "advertising disclosure (AGCOM)",
               "copyright on trend references", "credit spend without ROI"],
        tasks=st["agency_tasks"], evidence=["AI_FASHION_AGENCY_STATE_V1",
                                            "BUSINESS_UNIT_REVENUE_V1"],
        next_gate="FIRST_CHARACTER_SHEET_APPROVAL" if st["models_active"] == 0
        else "FIRST_PUBLISHED_CONTENT",
        decision=decision)
