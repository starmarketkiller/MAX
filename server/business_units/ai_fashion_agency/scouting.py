"""Provenance-safe scouting: SCOUT_RESULT_V1 -> dedupe -> Agency Input Bus.

Census (2026-10-07): NEXUS has no web search/crawl capability of its own; the
Market Scout explicitly runs with network disabled on supplied evidence.  V2
therefore keeps that contract: a scout result is evidence *captured* by an
approved collector and handed in with full provenance.  Collectors:

- SUPPLIED_SESSION_TOOL: an approved Claude/Codex session's web search/fetch
  (used by the V2 dry run).  ACTIVE.
- MANUAL: a human pastes a link + quote.  ACTIVE.
- SEARXNG / CRAWL4AI / PLAYWRIGHT_MCP: candidates in capability_scout.py,
  NOT_INSTALLED until vetted.

No collector in NEXUS fetches pages by itself, so there is no scraping to
throttle; future collectors must honour robots.txt/ToS and rate limits.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime

from . import pipeline
from .store import new_id

SCOUT_KINDS = {
    "TREND_SCOUT": "TREND_FORMAT",
    "VIRAL_FORMAT_SCOUT": "TREND_VIDEO",
    "PRODUCT_SCOUT": "PRODUCT",
    "FASHION_ITEM_SCOUT": "FASHION_ITEM",
}
COLLECTORS = {"SUPPLIED_SESSION_TOOL": "ACTIVE", "MANUAL": "ACTIVE",
              "SEARXNG": "NOT_INSTALLED", "CRAWL4AI": "NOT_INSTALLED",
              "PLAYWRIGHT_MCP": "NOT_INSTALLED"}


def dedup_key(kind, title):
    norm = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    return f"{kind}:" + hashlib.sha256(norm.encode()).hexdigest()[:16]


def validate_scout_result(result):
    errors = []
    if result.get("kind") not in SCOUT_KINDS:
        errors.append("unknown scout kind")
    if COLLECTORS.get(result.get("collector")) != "ACTIVE":
        errors.append("collector not active")
    if not str(result.get("url") or "").startswith(("https://", "http://")):
        errors.append("url/reference must be an http(s) URL")
    if not result.get("source"):
        errors.append("source required")
    try:
        datetime.fromisoformat(str(result.get("observed_at")))
    except ValueError:
        errors.append("observed_at must be ISO-8601")
    evidence = result.get("evidence")
    if not isinstance(evidence, list) or not evidence or not all(
            isinstance(e, dict) and e.get("quote") and e.get("evidence_id") for e in evidence):
        errors.append("evidence must be non-empty quotes with evidence_id")
    if not isinstance(result.get("confidence"), (int, float)) or not 0 <= result["confidence"] <= 1:
        errors.append("confidence must be 0..1")
    if not result.get("title"):
        errors.append("title required")
    return errors


def ingest_scout_result(store, result):
    """Validate, dedupe and route one result.  Returns (record, created)."""
    errors = validate_scout_result(result)
    if errors:
        raise ValueError("; ".join(errors))
    key = result.get("dedup_key") or dedup_key(result["kind"], result["title"])
    existing = next((r for r in store.snapshot()["scout_results"] if r["dedup_key"] == key), None)
    if existing:
        sightings = existing.get("sightings", []) + [
            {"url": result["url"], "observed_at": result["observed_at"]}]
        return store.upsert("scout_results", {"scout_result_id": existing["scout_result_id"],
                                              "sightings": sightings[-20:]}), False
    input_type = SCOUT_KINDS[result["kind"]]
    payload = {"title": result["title"], "source_url": result["url"],
               "source": result["source"], "platform": result.get("platform"),
               "category": result.get("category"),
               "trend_evidence": [f"{e['evidence_id']}: {e['quote']}" for e in result["evidence"]],
               **{k: result[k] for k in ("supplier", "unit_cost_eur", "target_price_eur")
                  if k in result}}
    item = pipeline.receive_input(store, input_type, payload, source=f"scout:{result['kind']}",
                                  idempotency_key=key)
    record = store.upsert("scout_results", {
        "scout_result_id": new_id("SCR"), "kind": result["kind"], "title": result["title"],
        "source": result["source"], "url": result["url"], "observed_at": result["observed_at"],
        "evidence": result["evidence"], "confidence": float(result["confidence"]),
        "collector": result["collector"], "dedup_key": key, "input_id": item["input_id"],
        "sightings": [{"url": result["url"], "observed_at": result["observed_at"]}],
        "product_id": None})
    if item["workflow"] == "STORE_GATE":
        product = pipeline.product_from_input(store, item)
        record = store.upsert("scout_results", {"scout_result_id": record["scout_result_id"],
                                                "product_id": product["product_id"]})
        store.emit("AGENCY_PRODUCT_FOUND", product["product_id"], {"detail": result["title"]})
    else:
        store.emit("AGENCY_TREND_FOUND", item["input_id"], {"detail": result["title"]})
    return record, True
