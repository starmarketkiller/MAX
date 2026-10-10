"""Social layer V2: content package -> post draft -> review -> approval ->
SCHEDULED (internal) ... PUBLISHED / FAILED.

Decision (reuse-first, documented in README): Postiz is the target adapter
(open-source, self-hostable multi-platform scheduler with analytics, already
exposed as an agent skill in this workspace).  Activepieces is not used: it is
a general automation runner and would duplicate the Orchestrator.  Native
platform APIs are deferred (per-app review, one integration per platform).

V2 never calls a publisher.  Even "SCHEDULED" is an internal plan: handing a
post to Postiz would make it go live at the scheduled time, which is a
PUBLISH action and is hard-disabled by policy.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from .pipeline import compliance_check
from .policy import require_approval
from .store import new_id

POST_STATES = ("DRAFT", "READY_FOR_REVIEW", "APPROVED", "SCHEDULED", "PUBLISHED", "FAILED")
POST_TRANSITIONS = {"DRAFT": {"READY_FOR_REVIEW", "FAILED"},
                    "READY_FOR_REVIEW": {"APPROVED", "DRAFT", "FAILED"},
                    "APPROVED": {"SCHEDULED", "FAILED"},
                    "SCHEDULED": {"PUBLISHED", "FAILED"},
                    "PUBLISHED": set(), "FAILED": {"DRAFT"}}


def _now():
    return datetime.now(timezone.utc).isoformat()


class SocialAdapter:
    name = None

    def status(self):
        raise NotImplementedError

    def build_payload(self, post, account):
        raise NotImplementedError

    def publish(self, payload):  # pragma: no cover - guarded by policy
        require_approval("PUBLISH", None)


class PostizAdapter(SocialAdapter):
    """Payload builder only.  No HTTP client ships in V2."""
    name = "POSTIZ"

    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url if base_url is not None else os.environ.get("NEXUS_POSTIZ_URL")
        self.api_key = api_key if api_key is not None else os.environ.get("NEXUS_POSTIZ_API_KEY")

    def status(self):
        return "CONFIGURED_DRY_RUN" if self.base_url and self.api_key else "NOT_CONFIGURED"

    def build_payload(self, post, account):
        return {"adapter": self.name, "platform": account["platform"],
                "account_ref": account["social_account_id"], "text": post["caption"],
                "media_refs": post["media_refs"], "planned_at": post.get("planned_at"),
                "ai_generated_label": True, "dry_run": True}


class ManualExportAdapter(SocialAdapter):
    """Human posts by hand from an exported package (always available)."""
    name = "MANUAL_EXPORT"

    def status(self):
        return "AVAILABLE"

    def build_payload(self, post, account):
        return {"adapter": self.name, "platform": account["platform"], "caption": post["caption"],
                "media_refs": post["media_refs"],
                "checklist": ["enable the platform AI-generated label",
                              "keep #ad / paid-partnership tag when commercial"]}


ADAPTERS = {"POSTIZ": PostizAdapter, "MANUAL_EXPORT": ManualExportAdapter}


def _account(store, model_id, platform):
    model = store.get("models", model_id)
    return next((a for a in model["social_accounts"] if a["platform"] == platform), None)


def create_post_draft(store, package_id, *, platform=None, adapter="POSTIZ"):
    """Autonomous: draft a post for a reviewed content package."""
    require_approval("DRAFT_SOCIAL_POST", None)
    package = store.get("content_packages", package_id)
    if package["state"] != "READY":
        raise ValueError("only READY content packages can become social drafts")
    brief = store.get("briefs", package["brief_id"])
    platform = platform or brief["platform"]
    account = _account(store, package["model_id"], platform)
    if account is None:
        raise ValueError("model has no slot for this platform")
    post = store.upsert("social_posts", {
        "post_id": new_id("PST"), "package_id": package_id, "brief_id": brief["brief_id"],
        "model_id": package["model_id"], "platform": platform,
        "social_account_id": account["social_account_id"], "adapter": adapter,
        "caption": brief["caption"], "media_refs": package["media_refs"],
        "commercial": brief["commercial"], "state": "DRAFT", "planned_at": None,
        "blockers": ([] if account["status"] == "ACTIVE"
                     else [f"account {account['social_account_id']} is {account['status']}"]),
        "history": []})
    return post


def transition_post(store, post_id, target, *, actor, approved_by=None, planned_at=None):
    post = store.get("social_posts", post_id)
    if target not in POST_TRANSITIONS[post["state"]]:
        raise ValueError(f"invalid post transition {post['state']} -> {target}")
    update = {"post_id": post_id, "state": target}
    if target == "READY_FOR_REVIEW":
        brief = store.get("briefs", post["brief_id"])
        review = compliance_check({**brief, "caption": post["caption"]})
        if not review["passed"]:
            raise ValueError("post blocked by compliance: " + "; ".join(review["issues"]))
        update["compliance"] = review
    if target == "APPROVED":
        require_approval("SCHEDULE_POST", approved_by)
        update["approved_by"] = approved_by
    if target == "SCHEDULED":
        if post["blockers"]:
            raise ValueError("cannot schedule: " + "; ".join(post["blockers"]))
        if not planned_at:
            raise ValueError("planned_at required")
        update["planned_at"] = planned_at
        account = _account(store, post["model_id"], post["platform"])
        update["adapter_payload"] = ADAPTERS[post["adapter"]]().build_payload(
            {**post, "planned_at": planned_at}, account)
    if target == "PUBLISHED":
        require_approval("PUBLISH", approved_by)  # hard-disabled in V2
    update["history"] = post["history"] + [{"from": post["state"], "to": target,
                                            "actor": actor, "at": _now()}]
    saved = store.upsert("social_posts", update)
    if target == "SCHEDULED":
        store.emit("AGENCY_SOCIAL_SCHEDULED", post_id, {"detail": f"{post['platform']} {planned_at}"})
    return saved


def record_external_publication(store, post_id, *, url, published_by):
    """The human published the approved post in the app; NEXUS only records it.

    Publishing from NEXUS stays hard-disabled; this is bookkeeping of a
    human action, so it needs the post to be APPROVED/SCHEDULED and a real URL.
    """
    require_approval("RECORD_EXTERNAL_PUBLICATION", published_by)
    post = store.get("social_posts", post_id)
    if post["state"] not in {"APPROVED", "SCHEDULED"}:
        raise ValueError("only approved posts can be recorded as published")
    if not str(url).startswith("https://"):
        raise ValueError("published post URL required")
    saved = store.upsert("social_posts", {
        "post_id": post_id, "state": "PUBLISHED", "published_url": url,
        "published_by": published_by, "published_at": _now(),
        "history": post["history"] + [{"from": post["state"], "to": "PUBLISHED",
                                       "actor": published_by, "at": _now(),
                                       "mode": "EXTERNAL_HUMAN"}]})
    store.emit("AGENCY_CONTENT_PUBLISHED", post_id, {"detail": url})
    return saved


def record_account_metrics(store, model_id, *, platform, followers, source, observed_at=None):
    """Observed account metrics (insights screen, analytics export). Never estimated."""
    if not isinstance(followers, int) or followers < 0 or not source:
        raise ValueError("observed follower count and source required")
    model = store.get("models", model_id)
    accounts = []
    for account in model["social_accounts"]:
        if account["platform"] == platform:
            previous = account.get("followers") if isinstance(account.get("followers"), int) else None
            account = {**account, "followers": followers,
                       "followers_growth": (followers - previous) if previous is not None else None,
                       "metrics_source": source, "metrics_observed_at": observed_at or _now()}
        accounts.append(account)
    return store.upsert("models", {"model_id": model_id, "social_accounts": accounts})


def account_overview(store):
    rows = []
    for model in store.snapshot()["models"]:
        for account in model["social_accounts"]:
            rows.append({"model_id": model["model_id"], "stage_name": model["stage_name"],
                         **account})
    return rows
