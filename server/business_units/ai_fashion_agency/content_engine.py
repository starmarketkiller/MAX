"""Content engine glue: generated brief + verified review -> content package.

trend input -> viral analysis -> brief -> model -> generation pack ->
approval -> generation (human-approved session) -> review -> package READY
-> social draft (social.py).
"""
from __future__ import annotations

from .store import new_id


def brief_card(store, brief_id):
    """The per-brief fields the operator and Jarvis need in one place."""
    b = store.get("briefs", brief_id)
    product = store.get("products", b["product_id"]) if b.get("product_id") else None
    model = store.get("models", b["model_id"]) if b.get("model_id") else None
    return {"brief_id": brief_id, "hook": b["hook"], "format": b.get("format"),
            "model": model["stage_name"] if model else None,
            "product_or_service": product["title"] if product else None,
            "platform": b.get("platform"), "objective": b.get("objective"), "cta": b.get("cta"),
            "risk_compliance": b["compliance"], "store_gate_status": b.get("store_gate_status"),
            "generation_cost_estimate": b.get("generation_cost_estimate"),
            "approval_status": b.get("approval_status"), "status": b["status"]}


def create_content_package(store, brief_id, *, media_refs, review):
    """`review` is a verified CONTENT_REVIEW output (skills.py)."""
    brief = store.get("briefs", brief_id)
    if brief["status"] != "GENERATED":
        raise ValueError("content packages need generated media (brief GENERATED)")
    if not media_refs:
        raise ValueError("media_refs required")
    if review.get("verdict") != "APPROVE":
        store.upsert("briefs", {"brief_id": brief_id, "status": "IN_REVIEW",
                                "review": review})
        return None
    package = store.upsert("content_packages", {
        "package_id": new_id("PKG"), "brief_id": brief_id, "model_id": brief["model_id"],
        "product_id": brief.get("product_id"), "media_refs": list(media_refs),
        "review": review, "state": "READY", "social_ready": True})
    store.upsert("briefs", {"brief_id": brief_id, "status": "IN_REVIEW", "package_id":
                            package["package_id"]})
    store.emit("AGENCY_CONTENT_READY", package["package_id"], {"detail": brief["title"]})
    if brief.get("commercial"):
        store.emit("AGENCY_CAMPAIGN_READY", package["package_id"],
                   {"detail": brief["title"]}, requires_human=True)
    return package
