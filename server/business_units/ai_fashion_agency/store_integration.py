"""PRODUCT_FOUND -> viability -> availability -> listing candidate ->
WAITING_APPROVAL -> STORE_READY -> campaign eligible.

There is no live NEXUS store yet, so listings are references to an external
shop page or an affiliate link behind a small adapter interface.  Opening a
store or putting a product online is never done here: STORE_READY only
records that a human approved an already-existing listing.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from . import pipeline
from .policy import require_approval


class StoreAdapter:
    kind = None

    def validate(self, listing):
        url = urlparse(str(listing.get("url") or ""))
        errors = [] if url.scheme == "https" and url.netloc else ["listing needs an https URL"]
        return errors

    def check_availability(self, listing, fetcher=None):
        """`fetcher(url) -> {"status": int}` is injected; NEXUS ships none in V2."""
        if fetcher is None:
            return {"available": None, "status": "UNVERIFIED_NEEDS_HUMAN_CHECK"}
        response = fetcher(listing["url"])
        ok = 200 <= int(response.get("status", 0)) < 400
        return {"available": ok, "status": "REACHABLE" if ok else "UNREACHABLE"}


class ExternalStoreLinkAdapter(StoreAdapter):
    kind = "EXTERNAL_STORE_LINK"


class AffiliateLinkAdapter(StoreAdapter):
    kind = "AFFILIATE_LINK"

    def validate(self, listing):
        errors = super().validate(listing)
        if not listing.get("program"):
            errors.append("affiliate listing needs the affiliate program name")
        return errors


class ShopifyProductAdapter(StoreAdapter):
    """Own Shopify store product page: https://<shop>/products/<handle>.

    Availability uses Shopify's public product JSON (<url>.js), which needs no
    credentials; listing or editing products still goes through the Shopify
    connector and human approval, never from here.
    """
    kind = "SHOPIFY_PRODUCT"

    def validate(self, listing):
        errors = super().validate(listing)
        path = urlparse(str(listing.get("url") or "")).path.rstrip("/").split("/")
        if len(path) < 3 or path[-2] != "products" or not path[-1]:
            errors.append("Shopify listing must be a /products/<handle> URL")
        return errors

    def check_availability(self, listing, fetcher=None):
        if fetcher is None:
            return {"available": None, "status": "UNVERIFIED_NEEDS_HUMAN_CHECK"}
        response = fetcher(listing["url"].rstrip("/") + ".js")
        if not 200 <= int(response.get("status", 0)) < 300:
            return {"available": False, "status": "UNREACHABLE"}
        product = response.get("json") or {}
        available = bool(product.get("available"))
        return {"available": available,
                "status": "IN_STOCK" if available else "OUT_OF_STOCK",
                "price_cents": product.get("price")}


ADAPTERS = {a.kind: a() for a in (ExternalStoreLinkAdapter, AffiliateLinkAdapter,
                                   ShopifyProductAdapter)}
# pipeline.LISTING_KINDS is the V1 vocabulary; map the V2 adapter kinds onto it.
_PIPELINE_KIND = {"EXTERNAL_STORE_LINK": "OWN_STORE", "AFFILIATE_LINK": "AFFILIATE_LINK",
                  "SHOPIFY_PRODUCT": "OWN_STORE"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def evaluate_product(store, product_id):
    """DISCOVERED -> EVALUATING -> STORE_PENDING, or stays EVALUATING + blocked."""
    product = store.get("products", product_id)
    if product["status"] == "DISCOVERED":
        product = pipeline.transition_product(store, product_id, "EVALUATING", actor="store_gate")
    viability = pipeline.evaluate_viability(product)
    if not viability["viable"]:
        store.upsert("products", {"product_id": product_id, "viability": viability,
                                  "blocked_reasons": viability["reasons"]})
        store.emit("AGENCY_STORE_BLOCKED", product_id,
                   {"detail": "; ".join(viability["reasons"])})
        return store.get("products", product_id)
    return pipeline.transition_product(store, product_id, "STORE_PENDING", actor="store_gate",
                                       viability=viability)


def propose_listing(store, product_id, listing, *, fetcher=None):
    """Autonomous: attach a listing candidate and ask for approval."""
    require_approval("PROPOSE_LISTING", None)
    product = store.get("products", product_id)
    if product["status"] != "STORE_PENDING":
        raise ValueError("listing candidates need a STORE_PENDING product")
    adapter = ADAPTERS.get(listing.get("kind"))
    if adapter is None:
        raise ValueError("unsupported listing kind")
    errors = adapter.validate(listing)
    if errors:
        raise ValueError("; ".join(errors))
    candidate = {**listing, "availability": adapter.check_availability(listing, fetcher),
                 "approval_status": "WAITING_APPROVAL", "proposed_at": _now()}
    store.upsert("products", {"product_id": product_id, "listing_candidate": candidate})
    store.emit("AGENCY_APPROVAL_REQUIRED", product_id,
               {"detail": f"listing per '{product['title']}'"}, requires_human=True)
    return candidate


def approve_listing(store, product_id, *, approved_by):
    require_approval("PUT_PRODUCT_ONLINE", approved_by)
    product = store.get("products", product_id)
    candidate = product.get("listing_candidate")
    if not candidate or candidate["approval_status"] != "WAITING_APPROVAL":
        raise ValueError("no listing candidate waiting for approval")
    if candidate["availability"]["available"] is False:
        raise ValueError("listing unreachable; re-propose a working link")
    listing = {"kind": _PIPELINE_KIND[candidate["kind"]], "url": candidate["url"],
               "adapter": candidate["kind"], "program": candidate.get("program")}
    updated = pipeline.transition_product(store, product_id, "STORE_READY", actor="store_gate",
                                          listing=listing, approved_by=approved_by)
    store.upsert("products", {"product_id": product_id, "listing_candidate":
                              {**candidate, "approval_status": "APPROVED"}})
    store.emit("AGENCY_STORE_READY", product_id, {"detail": product["title"]})
    return updated


def campaign_eligible(product):
    return pipeline.store_gate(product)["open"]
