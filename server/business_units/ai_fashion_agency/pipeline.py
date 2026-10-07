"""AI Fashion Agency deterministic workflows (gates and decisions).

Creative/analytical judgement runs as bounded skills through the canonical
Orchestrator (see skills.py).  This module holds only the deterministic
rules that must never be delegated to a model: classification routing, the
PRODUCT -> STORE FIRST gate, compliance, model assignment, the credit
approval gate and cost/revenue attribution.  It never publishes, spends
credits, opens a store or contacts anyone.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

from .policy import require_approval
from .store import COST_CATEGORIES, INPUT_TYPES, REVENUE_STREAMS, new_id

# AGENCY_COST_ALERT when generation credits exceed this with zero revenue.
CREDIT_ALERT_THRESHOLD = 20.0

# ---- input bus -------------------------------------------------------------

PRODUCT_INPUTS = {"PRODUCT", "FASHION_ITEM", "AFFILIATE_OFFER"}
VIRAL_INPUTS = {"TREND_VIDEO", "TREND_AUDIO", "TREND_FORMAT"}
BRIEF_INPUTS = {"CONTENT_IDEA", "SEASON_EVENT"}
HUMAN_REVIEW_INPUTS = {"CAMPAIGN", "BRAND_REQUEST", "SERVICE"}

WORKFLOW_BY_INPUT = {
    **{t: "STORE_GATE" for t in PRODUCT_INPUTS},
    **{t: "VIRAL_ADAPTER" for t in VIRAL_INPUTS},
    **{t: "CONTENT_BRIEF" for t in BRIEF_INPUTS},
    **{t: "CAMPAIGN_MANAGER" for t in HUMAN_REVIEW_INPUTS},
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def receive_input(store, input_type, payload, *, source, idempotency_key):
    """Agency Input Queue entry point for any NEXUS automation."""
    if input_type not in INPUT_TYPES:
        raise ValueError("unsupported agency input type")
    if not source or not idempotency_key:
        raise ValueError("source and idempotency_key required")
    record = {"input_id": new_id("AIN"), "input_type": input_type, "payload": dict(payload),
              "source": source, "state": "CLASSIFIED",
              "workflow": WORKFLOW_BY_INPUT[input_type], "received_at": _now()}
    return store.upsert("inputs", record, idempotency_key=f"input:{idempotency_key}")


# ---- PRODUCT -> STORE FIRST gate -------------------------------------------

PRODUCT_TRANSITIONS = {
    "DISCOVERED": {"EVALUATING", "RETIRED"},
    "EVALUATING": {"STORE_PENDING", "RETIRED"},
    "STORE_PENDING": {"STORE_READY", "RETIRED"},
    "STORE_READY": {"CONTENT_READY", "RETIRED"},
    "CONTENT_READY": {"PUBLISHED", "RETIRED"},
    "PUBLISHED": {"MONETIZING", "RETIRED"},
    "MONETIZING": {"RETIRED"},
    "RETIRED": set(),
}
PROMOTABLE_PRODUCT_STATES = {"STORE_READY", "CONTENT_READY", "PUBLISHED", "MONETIZING"}
LISTING_KINDS = {"OWN_STORE", "AFFILIATE_LINK"}


def product_from_input(store, input_record):
    if input_record["workflow"] != "STORE_GATE":
        raise ValueError("input is not a product")
    p = input_record["payload"]
    if not p.get("title"):
        raise ValueError("product title required")
    record = {"product_id": new_id("PRD"), "title": p["title"], "category": p.get("category"),
              "source_url": p.get("source_url"), "supplier": p.get("supplier"),
              "unit_cost_eur": p.get("unit_cost_eur"), "target_price_eur": p.get("target_price_eur"),
              "trend_evidence": list(p.get("trend_evidence") or []),
              "revenue_stream": "affiliate" if input_record["input_type"] == "AFFILIATE_OFFER"
              else "own_store",
              "input_id": input_record["input_id"], "status": "DISCOVERED",
              "viability": None, "store_listing": None, "history": []}
    return store.upsert("products", record)


def evaluate_viability(product, *, min_margin=0.30):
    """Deterministic commercial viability; the scout skill supplies evidence."""
    reasons = []
    cost, price = product.get("unit_cost_eur"), product.get("target_price_eur")
    if product["revenue_stream"] == "own_store":
        if not isinstance(cost, (int, float)) or not isinstance(price, (int, float)) or price <= 0:
            reasons.append("unit cost and target price required")
            margin = None
        else:
            margin = (price - cost) / price
            if margin < min_margin:
                reasons.append(f"margin {margin:.0%} below {min_margin:.0%}")
    else:
        margin = None
    if not product.get("trend_evidence"):
        reasons.append("no trend evidence")
    if not product.get("supplier") and product["revenue_stream"] == "own_store":
        reasons.append("no supplier")
    return {"viable": not reasons, "gross_margin": margin, "reasons": reasons,
            "evaluated_at": _now()}


def transition_product(store, product_id, target, *, actor, viability=None, listing=None,
                       approved_by=None):
    product = store.get("products", product_id)
    if target not in PRODUCT_TRANSITIONS[product["status"]]:
        raise ValueError(f"invalid product transition {product['status']} -> {target}")
    update = {"product_id": product_id, "status": target}
    if target == "STORE_PENDING":
        if not (viability or product.get("viability") or {}).get("viable"):
            raise ValueError("STORE_PENDING requires a viable commercial evaluation")
        update["viability"] = viability or product["viability"]
    if target == "STORE_READY":
        if not listing or listing.get("kind") not in LISTING_KINDS or not listing.get("url"):
            raise ValueError("STORE_READY requires a live store or affiliate listing reference")
        if not approved_by:
            raise ValueError("STORE_READY requires human approval of the listing")
        update["store_listing"] = {**listing, "approved_by": approved_by, "verified_at": _now()}
    update["history"] = product.get("history", []) + [
        {"from": product["status"], "to": target, "actor": actor, "at": _now()}]
    return store.upsert("products", update)


def store_gate(product):
    """Canonical gate: commercial content only for products we can sell now."""
    if product is None:
        return {"open": True, "reason": "non-commercial content"}
    if product["status"] not in PROMOTABLE_PRODUCT_STATES:
        return {"open": False, "reason": f"product {product['product_id']} is "
                f"{product['status']}; promotion requires STORE_READY"}
    return {"open": True, "reason": "product store-ready"}


# ---- compliance ------------------------------------------------------------

FORBIDDEN_CLAIM_RE = re.compile(
    r"\b(guaranteed|guarantee|get rich|passive income|cure[sd]?|miracle|100% safe|"
    r"risk[- ]free|garantit[oa]|guadagn[ai] sicur)", re.I)
FORBIDDEN_REUSE = {"REPOST_ORIGINAL", "OVERLAY_ON_ORIGINAL", "REUSE_ORIGINAL_FOOTAGE"}


def compliance_check(brief, model=None, product=None):
    issues = []
    if brief.get("production_method") in FORBIDDEN_REUSE:
        issues.append("original third-party footage cannot be reused; recreate the format")
    if brief.get("audio_source") not in {None, "PLATFORM_LIBRARY", "ORIGINAL", "LICENSED"}:
        issues.append("audio must come from the platform library, be original or licensed")
    text = " ".join(str(brief.get(k) or "") for k in ("hook", "script", "caption", "cta"))
    if FORBIDDEN_CLAIM_RE.search(text):
        issues.append("misleading or absolute commercial claim")
    if not brief.get("ai_label"):
        issues.append("AI-generated content label required")
    if brief.get("commercial"):
        if not brief.get("ad_disclosure"):
            issues.append("advertising/affiliate disclosure required (#ad / paid partnership)")
        gate = store_gate(product)
        if not gate["open"]:
            issues.append(gate["reason"])
    if brief.get("depicts_real_person"):
        issues.append("no real-person likeness without documented consent")
    if model is not None:
        if model["age_presentation"] != "ADULT_21_PLUS":
            issues.append("models must present as adults 21+")
        if brief.get("content_category") not in model["content_categories"]:
            issues.append("content category not allowed for this model")
    if brief.get("explicit"):
        issues.append("sexual/explicit content is not allowed")
    return {"passed": not issues, "issues": issues, "checked_at": _now()}


# ---- viral adapter / content brief -----------------------------------------

def viral_reference_from_input(input_record, analysis):
    """Turn a trend input + verified VIRAL_FORMAT_ANALYSIS into a reference.

    `analysis` is the verified output of the VIRAL_FORMAT_ANALYSIS skill (or a
    human-entered equivalent).  Only structure is kept, never the media.
    """
    if input_record["workflow"] != "VIRAL_ADAPTER":
        raise ValueError("input is not a viral reference")
    required = {"format_name", "hook_pattern", "beats", "payoff", "comment_bait",
                "audio_strategy", "duration_seconds"}
    missing = required - set(analysis)
    if missing:
        raise ValueError(f"viral analysis missing {sorted(missing)}")
    return {"reference_id": new_id("VRF"), "input_id": input_record["input_id"],
            "source_url": input_record["payload"].get("source_url"),
            "platform": input_record["payload"].get("platform"),
            "structure": {k: analysis[k] for k in sorted(required)},
            "media_retained": False}


def build_content_brief(store, *, title, content_category, hook, script, caption,
                        viral_reference=None, product_id=None, campaign_id=None,
                        audio_source="PLATFORM_LIBRARY", production_method="ORIGINAL_RECREATION",
                        aspect_ratio="9:16", duration_seconds=15, cta=None,
                        format_name=None, platform="tiktok", objective="awareness"):
    product = store.get("products", product_id) if product_id else None
    gate = store_gate(product)
    brief = {"brief_id": new_id("BRF"), "title": title, "content_category": content_category,
             "hook": hook, "script": script, "caption": caption, "cta": cta,
             "viral_reference": viral_reference, "product_id": product_id,
             "campaign_id": campaign_id, "commercial": product is not None,
             "audio_source": audio_source, "production_method": production_method,
             "aspect_ratio": aspect_ratio, "duration_seconds": duration_seconds,
             "ai_label": True, "ad_disclosure": product is not None,
             "status": "DRAFT", "model_id": None,
             "format": format_name or ((viral_reference or {}).get("structure") or {}).get(
                 "format_name") or "original",
             "platform": platform, "objective": objective,
             "store_gate_status": ("NOT_COMMERCIAL" if product is None else
                                   "OPEN" if gate["open"] else "BLOCKED"),
             "generation_cost_estimate": None, "approval_status": "NOT_REQUESTED"}
    brief["compliance"] = compliance_check(brief, product=product)
    if not brief["compliance"]["passed"]:
        brief["status"] = "REJECTED"
    saved = store.upsert("briefs", brief)
    if product is not None and not gate["open"]:
        store.emit("AGENCY_STORE_BLOCKED", product["product_id"],
                   {"detail": f"brief '{title}' bloccato: prodotto {product['status']}"})
    return saved


# ---- model casting / assignment --------------------------------------------

ASSIGNABLE_MODEL_STATUSES = {"CASTING_DRAFT", "DESIGN_PENDING_APPROVAL",
                             "CHARACTER_SHEET_READY", "ACTIVE"}


def score_models(brief, models, product=None):
    keywords = set(re.findall(r"[a-z]+", " ".join(
        [brief.get("title", ""), brief.get("content_category", ""),
         (product or {}).get("category") or "", (product or {}).get("title") or ""]).lower()))
    ranked = []
    for model in models:
        if model["status"] not in ASSIGNABLE_MODEL_STATUSES:
            continue
        if brief["content_category"] not in model["content_categories"]:
            continue
        fit_words = set(re.findall(r"[a-z]+", " ".join(model["brand_fit"] + [model["style"]]).lower()))
        overlap = len(keywords & fit_words)
        load = len(model.get("assigned_tasks", []))
        status_bonus = {"ACTIVE": 2, "CHARACTER_SHEET_READY": 1}.get(model["status"], 0)
        ranked.append({"model_id": model["model_id"], "score": overlap * 3 + status_bonus - load,
                       "keyword_overlap": sorted(keywords & fit_words), "load": load})
    return sorted(ranked, key=lambda x: (-x["score"], x["model_id"]))


def assign_model(store, brief_id, *, model_id=None, actor):
    brief = store.get("briefs", brief_id)
    if brief["status"] != "DRAFT":
        raise ValueError("only DRAFT briefs can be assigned")
    snapshot = store.snapshot()
    product = store.get("products", brief["product_id"]) if brief["product_id"] else None
    ranking = score_models(brief, snapshot["models"], product)
    if model_id is None:
        if not ranking:
            raise ValueError("no eligible model for this brief")
        model_id = ranking[0]["model_id"]
    model = store.get("models", model_id)
    compliance = compliance_check(brief, model=model, product=product)
    if not compliance["passed"]:
        raise ValueError("assignment blocked by compliance: " + "; ".join(compliance["issues"]))
    assignment = store.upsert("assignments", {
        "assignment_id": new_id("ASG"), "brief_id": brief_id, "model_id": model_id,
        "ranking": ranking, "selected_by": actor, "status": "ASSIGNED"})
    store.upsert("models", {"model_id": model_id, "assigned_tasks":
                            model.get("assigned_tasks", []) + [assignment["assignment_id"]]})
    store.upsert("briefs", {"brief_id": brief_id, "model_id": model_id, "status": "ASSIGNED",
                            "compliance": compliance})
    return assignment


# ---- Higgsfield generation packs + credit approval gate ---------------------

def _quote_is_fresh(quote, today=None):
    if not quote or not isinstance(quote.get("credits"), (int, float)):
        return False
    quoted = date.fromisoformat(quote["quoted_at"][:10])
    return ((today or date.today()) - quoted).days <= int(quote.get("stale_after_days", 7))


def build_generation_pack(store, brief_id, *, video_quote=None, today=None):
    """Plan the paid Higgsfield calls for one brief.  Never executes them.

    A step is approvable only with a fresh, non-spending quote.  Steps without
    one stay WAITING_QUOTE and are excluded from the approvable total.
    """
    brief = store.get("briefs", brief_id)
    if brief["status"] != "ASSIGNED":
        raise ValueError("generation pack requires an assigned brief")
    model = store.get("models", brief["model_id"])
    steps = []
    if model["status"] not in {"CHARACTER_SHEET_READY", "ACTIVE"}:
        sheet = model["visual_identity"]["higgsfield_sheet"]
        quote = model.get("last_quote")
        steps.append({"step_id": "S1_CHARACTER_SHEET", "tool": "higgsfield.ai_influencer_generate",
                      "quote_tool": "higgsfield.ai_influencer_prepare",
                      "params": {k: v for k, v in sheet.items() if k != "tool"},
                      "quote": quote if _quote_is_fresh(quote, today) else None})
    method = ("higgsfield.generate_video:motion_transfer"
              if brief.get("viral_reference") else "higgsfield.generate_video")
    steps.append({"step_id": f"S{len(steps) + 1}_VIDEO", "tool": method,
                  "quote_tool": "higgsfield (quote before submit)",
                  "params": {"model_id": model["model_id"], "aspect_ratio": brief["aspect_ratio"],
                             "duration_seconds": brief["duration_seconds"],
                             "hook": brief["hook"], "script": brief["script"],
                             "character_reference": "S1_CHARACTER_SHEET output"
                             if steps else model["model_id"]},
                  "quote": video_quote if _quote_is_fresh(video_quote, today) else None})
    for step in steps:
        step["state"] = "WAITING_APPROVAL" if step["quote"] else "WAITING_QUOTE"
    approvable = [s for s in steps if s["state"] == "WAITING_APPROVAL"]
    state = "WAITING_APPROVAL" if approvable else "WAITING_QUOTE"
    pack = store.upsert("generation_packs", {
        "pack_id": new_id("GEN"), "brief_id": brief_id, "model_id": model["model_id"],
        "provider": "HIGGSFIELD", "steps": steps, "state": state,
        "quoted_credits": round(sum(s["quote"]["credits"] for s in approvable), 4),
        "unquoted_steps": [s["step_id"] for s in steps if s["state"] == "WAITING_QUOTE"],
        "credits_spent": 0, "approved_by": None, "approval_required": True})
    store.upsert("briefs", {"brief_id": brief_id, "status": "WAITING_APPROVAL",
                            "generation_cost_estimate": {
                                "quoted_credits": pack["quoted_credits"],
                                "unquoted_steps": pack["unquoted_steps"]},
                            "approval_status": state})
    if state == "WAITING_APPROVAL":
        store.emit("AGENCY_APPROVAL_REQUIRED", pack["pack_id"],
                   {"detail": f"generazione {model['stage_name']} "
                              f"({pack['quoted_credits']:g} crediti)",
                    "credits": pack["quoted_credits"]}, requires_human=True)
    if model["status"] not in {"CHARACTER_SHEET_READY", "ACTIVE"}:
        store.emit("AGENCY_CASTING_REQUIRED", model["model_id"],
                   {"detail": f"{model['stage_name']} non ha ancora un character sheet"},
                   requires_human=True)
    return pack


def approve_generation_pack(store, pack_id, *, approved_by, expected_credits):
    """Records explicit human approval of the exact quoted cost.  No spend."""
    pack = store.get("generation_packs", pack_id)
    if pack["state"] != "WAITING_APPROVAL":
        raise ValueError("pack is not waiting for approval")
    if not approved_by:
        raise ValueError("explicit human approval required")
    require_approval("SPEND_CREDITS", approved_by)
    if expected_credits != pack["quoted_credits"]:
        raise ValueError("approved credits differ from the quote; re-quote required")
    steps = [{**s, "state": "APPROVED"} if s["state"] == "WAITING_APPROVAL" else s
             for s in pack["steps"]]
    store.upsert("briefs", {"brief_id": pack["brief_id"], "status": "APPROVED",
                            "approval_status": "APPROVED"})
    return store.upsert("generation_packs", {"pack_id": pack_id, "state": "APPROVED",
                                             "steps": steps, "approved_by": approved_by,
                                             "approved_at": _now()})


def record_generation_result(store, pack_id, step_id, *, credits_spent, job_id, eur_per_credit=None):
    """Record a step that a human-approved session executed on Higgsfield."""
    pack = store.get("generation_packs", pack_id)
    step = next(s for s in pack["steps"] if s["step_id"] == step_id)
    if step["state"] != "APPROVED":
        raise ValueError("only approved steps can be recorded as executed")
    if credits_spent > step["quote"]["credits"]:
        raise ValueError("spend exceeded the approved quote")
    steps = [{**s, "state": "COMPLETED", "job_id": job_id, "credits_spent": credits_spent}
             if s["step_id"] == step_id else s for s in pack["steps"]]
    done = all(s["state"] == "COMPLETED" for s in steps)
    store.upsert("generation_packs", {"pack_id": pack_id, "steps": steps,
                                      "state": "COMPLETED" if done else "APPROVED",
                                      "credits_spent": pack["credits_spent"] + credits_spent})
    record_cost(store, "generation_credits", credits=credits_spent,
                eur=(credits_spent * eur_per_credit) if eur_per_credit else None,
                model_id=pack["model_id"], brief_id=pack["brief_id"], reference=job_id,
                idempotency_key=f"gen:{pack_id}:{step_id}")
    if step_id.endswith("CHARACTER_SHEET"):
        store.upsert("models", {"model_id": pack["model_id"], "status": "CHARACTER_SHEET_READY",
                                "character_sheet_job_id": job_id})
        store.emit("AGENCY_MODEL_READY", pack["model_id"], {"detail": "character sheet pronto"})
    if done:
        store.upsert("briefs", {"brief_id": pack["brief_id"], "status": "GENERATED"})


# ---- cost & revenue accounting ---------------------------------------------

def record_cost(store, category, *, eur=None, credits=None, model_id=None, brief_id=None,
                campaign_id=None, reference=None, idempotency_key):
    if category not in COST_CATEGORIES:
        raise ValueError("unknown cost category")
    if eur is None and credits is None:
        raise ValueError("cost needs eur or credits")
    cost = store.upsert("costs", {"cost_id": new_id("CST"), "category": category, "eur": eur,
                                  "credits": credits, "model_id": model_id, "brief_id": brief_id,
                                  "campaign_id": campaign_id, "reference": reference,
                                  "business_unit_id": "AI_FASHION_AGENCY",
                                  "recorded_at": _now()},
                        idempotency_key=f"cost:{idempotency_key}")
    snapshot = store.snapshot()
    credits_total = sum(float(c.get("credits") or 0) for c in snapshot["costs"])
    revenue_total = sum(float(r.get("gross_revenue_eur") or r.get("amount_eur") or 0)
                        for r in snapshot["revenue_events"])
    if credits_total > CREDIT_ALERT_THRESHOLD and revenue_total == 0:
        store.emit("AGENCY_COST_ALERT", cost["cost_id"],
                   {"detail": f"{credits_total:g} crediti spesi senza ricavi"},
                   requires_human=True)
    return cost


def record_revenue_event(store, *, stream, amount_eur, model_id, campaign_id, product_id,
                         content_id, channel, external_reference, disclosed,
                         revenue_v1_id=None, idempotency_key, costs_eur=0.0,
                         source="manual_observation"):
    """Observed revenue with full attribution.  Never inferred or estimated."""
    if stream not in REVENUE_STREAMS:
        raise ValueError("unknown revenue stream")
    if not external_reference:
        raise ValueError("revenue requires an observed external reference")
    if stream in {"affiliate", "sponsored_product", "brand_campaign", "creator_sponsorship"} \
            and not disclosed:
        raise ValueError("commercial revenue requires disclosed content")
    if product_id:
        product = store.get("products", product_id)
        if product["status"] not in PROMOTABLE_PRODUCT_STATES:
            raise ValueError("revenue attributed to a product that never passed the store gate")
    if float(amount_eur) < 0 or float(costs_eur) < 0:
        raise ValueError("revenue and costs must be non-negative observations")
    before = len(store.snapshot()["revenue_events"])
    gross, costs = float(amount_eur), float(costs_eur)
    timestamp = _now()
    event = store.upsert("revenue_events", {
        "revenue_event_id": new_id("ARV"), "business_unit_id": "AI_FASHION_AGENCY",
        "stream": stream, "amount_eur": gross, "gross_revenue_eur": gross,
        "costs_eur": costs, "net_revenue_eur": round(gross - costs, 2), "source": source,
        "model_id": model_id, "campaign_id": campaign_id, "product_id": product_id,
        "content_id": content_id, "channel": channel,
        "external_reference": external_reference, "revenue_v1_id": revenue_v1_id,
        "timestamp": timestamp, "recorded_at": timestamp},
        idempotency_key=f"rev:{idempotency_key}")
    if len(store.snapshot()["revenue_events"]) > before:
        store.emit("AGENCY_REVENUE_EVENT", event["revenue_event_id"],
                   {"detail": f"€{gross:.2f} lordi da {channel or 'n/d'}"})
    return event

