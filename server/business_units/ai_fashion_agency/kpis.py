"""Agency / model / campaign KPIs.  Missing data is "UNAVAILABLE", never 0.

Counts NEXUS owns (content created, revenue events, costs) are always real.
Audience metrics (views, engagement, followers, CTR) only exist once a social
analytics source reports them; until then they are UNAVAILABLE.
"""
from __future__ import annotations

UNAVAILABLE = "UNAVAILABLE"


def _metric(values):
    present = [v for v in values if isinstance(v, (int, float))]
    return sum(present) if present else UNAVAILABLE


def _ratio(num, den):
    if num == UNAVAILABLE or den == UNAVAILABLE or not den:
        return UNAVAILABLE
    return round(num / den, 4)


def _money(events, key):
    return round(sum(float(e.get(key, e.get("amount_eur", 0)) or 0) for e in events), 2)


def agency_kpis(snapshot):
    posts = snapshot["social_posts"]
    published = [p for p in posts if p["state"] == "PUBLISHED"]
    revenue = snapshot["revenue_events"]
    accounts = [a for m in snapshot["models"] for a in m["social_accounts"]]
    gross = _money(revenue, "gross_revenue_eur")
    costs_eur = round(sum(float(c.get("eur") or 0) for c in snapshot["costs"]) +
                      sum(float(r.get("costs_eur") or 0) for r in revenue), 2)
    views = _metric([p.get("views") for p in published])
    clicks = _metric([p.get("clicks") for p in published])
    return {
        "content_created": len(snapshot["content_packages"]),
        "content_published": len(published),
        "views": views, "engagement": _metric([p.get("engagement") for p in published]),
        "followers_growth": _metric([a.get("followers_growth") for a in accounts]),
        "CTR": _ratio(clicks, views), "sales": len(revenue),
        "gross_revenue": gross, "costs": costs_eur, "net_revenue": round(gross - costs_eur, 2),
        "ROI": round((gross - costs_eur) / costs_eur, 4) if costs_eur else UNAVAILABLE,
        "credits_spent": round(sum(float(c.get("credits") or 0) for c in snapshot["costs"]), 4),
    }


def model_kpis(snapshot):
    rows = {}
    for model in snapshot["models"]:
        mid = model["model_id"]
        posts = [p for p in snapshot["social_posts"] if p["model_id"] == mid and
                 p["state"] == "PUBLISHED"]
        packages = [p for p in snapshot["content_packages"] if p["model_id"] == mid]
        revenue = [r for r in snapshot["revenue_events"] if r.get("model_id") == mid]
        gross = _money(revenue, "gross_revenue_eur")
        views = _metric([p.get("views") for p in posts])
        rows[mid] = {
            "stage_name": model["stage_name"], "status": model["status"],
            "views": views, "engagement": _metric([p.get("engagement") for p in posts]),
            "followers_growth": _metric([a.get("followers_growth")
                                         for a in model["social_accounts"]]),
            "conversion": _ratio(len(revenue) if revenue else UNAVAILABLE, views),
            "revenue": gross,
            "revenue_per_content": round(gross / len(posts), 2) if posts else UNAVAILABLE,
            "content_success_rate": (round(sum(p["review"].get("verdict") == "APPROVE"
                                               for p in packages) / len(packages), 4)
                                     if packages else UNAVAILABLE),
            "accounts_active": sum(a["status"] == "ACTIVE" for a in model["social_accounts"]),
        }
    return rows


def campaign_kpis(snapshot):
    rows = {}
    campaigns = {b.get("campaign_id") or b["brief_id"]: b for b in snapshot["briefs"]
                 if b.get("commercial")}
    for cid, brief in campaigns.items():
        posts = [p for p in snapshot["social_posts"] if p["brief_id"] == brief["brief_id"]
                 and p["state"] == "PUBLISHED"]
        revenue = [r for r in snapshot["revenue_events"]
                   if r.get("campaign_id") == cid or r.get("content_id") == brief["brief_id"]]
        cost = round(sum(float(c.get("eur") or 0) for c in snapshot["costs"]
                         if c.get("campaign_id") == cid or c.get("brief_id") == brief["brief_id"]), 2)
        gross = _money(revenue, "gross_revenue_eur")
        views = _metric([p.get("views") for p in posts])
        rows[cid] = {"title": brief["title"], "status": brief["status"],
                     "store_gate_status": brief.get("store_gate_status"), "views": views,
                     "engagement": _metric([p.get("engagement") for p in posts]),
                     "CTR": _ratio(_metric([p.get("clicks") for p in posts]), views),
                     "sales": len(revenue), "revenue": gross, "cost": cost,
                     "profit": round(gross - cost, 2),
                     "ROI": round((gross - cost) / cost, 4) if cost else UNAVAILABLE}
    return rows
