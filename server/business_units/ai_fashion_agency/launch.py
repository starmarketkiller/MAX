"""MODEL_LAUNCH_V1: the repeatable pipeline Unreal Faces runs for every model.

CASTING -> IDENTITY -> PROFILE_KIT -> CONTENT_PLAN -> PRODUCTION -> PUBLISHING
-> MONETIZATION -> REVIEW -> CLOSED (then the next casting).

Every stage has an explicit exit gate. Human decisions (casting choice, paid
character sheet, account creation, publishing, final review) are recorded
with `approved_by`; nothing here spends credits, creates accounts or posts.
One model at a time: a new casting opens only once every open launch has
reached MONETIZATION (AGENCY_IDENTITY roster_policy).
"""
from __future__ import annotations

from datetime import datetime, timezone

from .identity import AGENCY_IDENTITY
from .policy import require_approval
from .store import new_id

STAGES = ("CASTING", "IDENTITY", "PROFILE_KIT", "CONTENT_PLAN", "PRODUCTION",
          "PUBLISHING", "MONETIZATION", "REVIEW", "CLOSED")
REVIEW_DECISIONS = ("SCALE", "ITERATE", "RETIRE")
MIN_PACKAGES_FOR_PUBLISHING = 3
MIN_PUBLISHED_FOR_MONETIZATION = 9
MIN_FOLLOWERS_FOR_MONETIZATION = 1000
OPEN_STAGES_BLOCKING_NEW_CASTING = set(STAGES[:STAGES.index("MONETIZATION")])

GATES = {
    "CASTING": "your approval of the proposed model",
    "IDENTITY": "character sheet generated (paid, quoted, approved) and variant chosen",
    "PROFILE_KIT": "you create the Instagram account and confirm the real handle",
    "CONTENT_PLAN": "30-day plan generated (automatic)",
    "PRODUCTION": f"at least {MIN_PACKAGES_FOR_PUBLISHING} reviewed content packages",
    "PUBLISHING": (f"at least {MIN_PUBLISHED_FOR_MONETIZATION} posts published by you and "
                   f"{MIN_FOLLOWERS_FOR_MONETIZATION}+ followers"),
    "MONETIZATION": "a STORE_READY product and the first attributed revenue event",
    "REVIEW": "your decision: SCALE, ITERATE or RETIRE",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


# ---- casting -----------------------------------------------------------------

def casting_scores(snapshot):
    """Rank roster candidates for the next launch (deterministic, explainable)."""
    launched = {l["model_id"] for l in snapshot.get("launches", [])}
    active_archetypes = {m["archetype"] for m in snapshot["models"]
                         if m["model_id"] in launched and m["status"] != "RETIRED"}
    ranked = []
    for model in snapshot["models"]:
        if model["model_id"] in launched or model["status"] == "RETIRED":
            continue
        cats = set(model["content_categories"])
        viral = 2 * len(cats & {"viral_formats", "humor"})
        products = min(len(model["brand_fit"]), 5)
        seed = 2 if model.get("seed_pack") else 0
        quote = 1 if (model.get("last_quote") or {}).get("credits") else 0
        overlap = -5 if model["archetype"] in active_archetypes else 0
        ranked.append({"model_id": model["model_id"], "stage_name": model["stage_name"],
                       "archetype": model["archetype"],
                       "score": viral + products + seed + quote + overlap,
                       "why": {"viral_fit": viral, "product_breadth": products,
                               "seed_pack": seed, "quoted": quote, "niche_overlap": overlap}})
    return sorted(ranked, key=lambda r: (-r["score"], r["model_id"]))


def open_casting(store):
    """Propose the next model. Refuses while another launch is still early."""
    require_approval("SCOUT", None)  # autonomous: proposing is not deciding
    snap = store.snapshot()
    blocking = [l for l in snap.get("launches", []) if l["stage"] in OPEN_STAGES_BLOCKING_NEW_CASTING]
    if blocking:
        raise ValueError(f"one model at a time: {blocking[0]['stage_name']} is still in "
                         f"{blocking[0]['stage']}")
    ranking = casting_scores(snap)
    if not ranking:
        raise ValueError("no casting candidates left in the roster")
    top = ranking[0]
    launch = store.upsert("launches", {
        "launch_id": new_id("LCH"), "agency": AGENCY_IDENTITY["name"],
        "model_id": top["model_id"], "stage_name": top["stage_name"], "stage": "CASTING",
        "ranking": ranking[:5], "decisions": [], "artifacts": {}, "history": [],
        "opened_at": _now()})
    store.emit("AGENCY_CASTING_REQUIRED", launch["launch_id"],
               {"detail": f"proposta {top['stage_name']} ({top['archetype']})"},
               requires_human=True)
    return launch


# ---- kits --------------------------------------------------------------------

def model_profile_kit(model, identity=AGENCY_IDENTITY):
    name = model["stage_name"]
    slug = name.lower()
    seed = model.get("seed_pack") or {}
    archetypes = seed.get("content_archetypes") or model["allowed_content"][:3]
    adaptations = seed.get("viral_adaptations") or model["allowed_content"][:3]
    bio = (f"{name} ✦ {model['style']} ✦ AI creator @{identity['proposed_handles']['instagram'][0]} "
           f"✦ all content AI-generated")
    grid = []
    for i in range(9):
        source = (archetypes if i % 3 == 0 else adaptations if i % 3 == 1 else ["outfit / mood still"])
        grid.append({"slot": i + 1, "type": ("series", "viral_remake", "still")[i % 3],
                     "concept": source[(i // 3) % len(source)]})
    return {"schema_version": "MODEL_PROFILE_KIT_V1", "model_id": model["model_id"],
            "display_name": f"{name} | AI creator",
            "handle_candidates": [f"{slug}.unrealfaces", f"{slug}_uf", f"its.{slug}.ai"],
            "handle_status": "UNVERIFIED_CHECK_IN_APP",
            "bio": bio, "bio_length": len(bio),
            "profile_picture_brief": ("head-and-shoulders from the approved character sheet, "
                                      "signature elements visible: "
                                      + ", ".join(model["visual_identity"]["signature_elements"])),
            "highlights": ["About me", "Outfits", "Behind the AI", "Favourites (later: Shop)"],
            "launch_grid": grid,
            "disclosure": ["platform AI label ON", "'AI creator' in bio",
                           "#ad on any sponsored post"],
            "signature": model["visual_identity"]["signature_elements"]}


def content_plan(model, days=30):
    """30-day plan: 1 post/day, viral remakes + series + stills; no sponsorship
    before the MONETIZATION gate."""
    seed = model.get("seed_pack") or {}
    adaptations = seed.get("viral_adaptations") or model["allowed_content"]
    archetypes = seed.get("content_archetypes") or model["content_categories"]
    plan = []
    for day in range(1, days + 1):
        kind = ("viral_remake", "series", "viral_remake", "still", "series", "viral_remake",
                "community")[(day - 1) % 7]
        concept = {"viral_remake": adaptations[(day - 1) % len(adaptations)],
                   "series": archetypes[(day - 1) % len(archetypes)],
                   "still": "outfit / mood still from the latest shoot",
                   "community": "comment-reply video or 'A or B?' poll"}[kind]
        plan.append({"day": day, "kind": kind, "concept": concept,
                     "format": "9:16 video" if kind != "still" else "4:5 image",
                     "sponsored": False,
                     "source": "trend scouting fills the exact trend the week before"})
    return {"schema_version": "MODEL_CONTENT_PLAN_V1", "model_id": model["model_id"],
            "days": plan, "cadence": "1 post/day",
            "sponsorship": "blocked until MONETIZATION gate (followers + STORE_READY product)"}


# ---- stage transitions ----------------------------------------------------------

def _gate_errors(store, launch, evidence):
    model = store.get("models", launch["model_id"])
    snap = store.snapshot()
    stage = launch["stage"]
    if stage == "IDENTITY":
        if model["status"] not in {"CHARACTER_SHEET_READY", "ACTIVE"}:
            return ["character sheet not generated yet (needs the approved paid step)"]
    if stage == "PROFILE_KIT":
        ig = next(a for a in model["social_accounts"] if a["platform"] == "instagram")
        if ig["status"] != "ACTIVE":
            return ["Instagram account not confirmed: record_account_created() first"]
    if stage == "PRODUCTION":
        ready = [p for p in snap["content_packages"]
                 if p["model_id"] == model["model_id"] and p["state"] == "READY"]
        if len(ready) < MIN_PACKAGES_FOR_PUBLISHING:
            return [f"{len(ready)}/{MIN_PACKAGES_FOR_PUBLISHING} content packages ready"]
    if stage == "PUBLISHING":
        published = [p for p in snap["social_posts"]
                     if p["model_id"] == model["model_id"] and p["state"] == "PUBLISHED"]
        ig = next(a for a in model["social_accounts"] if a["platform"] == "instagram")
        errors = []
        if len(published) < MIN_PUBLISHED_FOR_MONETIZATION:
            errors.append(f"{len(published)}/{MIN_PUBLISHED_FOR_MONETIZATION} posts published")
        if not isinstance(ig.get("followers"), int) or ig["followers"] < MIN_FOLLOWERS_FOR_MONETIZATION:
            errors.append(f"followers {ig.get('followers') or 'n/d'}/{MIN_FOLLOWERS_FOR_MONETIZATION}")
        return errors
    if stage == "MONETIZATION":
        errors = []
        if not any(p["status"] in {"STORE_READY", "CONTENT_READY", "PUBLISHED", "MONETIZING"}
                   for p in snap["products"]):
            errors.append("no STORE_READY product")
        if not any(r.get("model_id") == model["model_id"] for r in snap["revenue_events"]):
            errors.append("no attributed revenue yet")
        return errors
    return []


def advance(store, launch_id, *, approved_by=None, decision=None):
    """Move a launch to its next stage if the current gate is satisfied."""
    launch = store.get("launches", launch_id)
    stage = launch["stage"]
    if stage == "CLOSED":
        raise ValueError("launch already closed")
    if stage == "CASTING":
        require_approval("APPROVE_CASTING", approved_by)
    if stage == "REVIEW":
        require_approval("APPROVE_CASTING", approved_by)
        if decision not in REVIEW_DECISIONS:
            raise ValueError(f"review decision must be one of {REVIEW_DECISIONS}")
    errors = _gate_errors(store, launch, None)
    if errors:
        raise ValueError(f"{stage} gate not met: " + "; ".join(errors))
    nxt = STAGES[STAGES.index(stage) + 1]
    model = store.get("models", launch["model_id"])
    artifacts = dict(launch["artifacts"])
    if nxt == "PROFILE_KIT":
        artifacts["profile_kit"] = model_profile_kit(model)
    if nxt == "CONTENT_PLAN":
        artifacts["content_plan"] = content_plan(model)
    if stage == "REVIEW" and decision == "RETIRE":
        store.upsert("models", {"model_id": model["model_id"], "status": "RETIRED"})
    update = {"launch_id": launch_id, "stage": nxt, "artifacts": artifacts,
              "history": launch["history"] + [{"from": stage, "to": nxt, "at": _now(),
                                               "approved_by": approved_by, "decision": decision}]}
    if decision:
        update["decisions"] = launch["decisions"] + [{"stage": stage, "decision": decision,
                                                      "by": approved_by}]
    saved = store.upsert("launches", update)
    if nxt == "IDENTITY":
        store.emit("AGENCY_APPROVAL_REQUIRED", launch_id,
                   {"detail": f"character sheet di {launch['stage_name']} (a pagamento)"},
                   requires_human=True)
    if nxt == "PROFILE_KIT":
        store.emit("AGENCY_MODEL_READY", launch["model_id"],
                   {"detail": f"{launch['stage_name']}: kit profilo Instagram pronto"})
    return saved


def advance_content_plan(store, launch_id):
    """CONTENT_PLAN is automatic once the plan exists."""
    launch = store.get("launches", launch_id)
    if launch["stage"] != "CONTENT_PLAN" or not launch["artifacts"].get("content_plan"):
        raise ValueError("no content plan to accept")
    return advance(store, launch_id)


def record_account_created(store, model_id, *, platform, handle, approved_by):
    """A human created the account in the app: record the real handle."""
    require_approval("CREATE_SOCIAL_ACCOUNT", approved_by)
    if not handle or " " in handle:
        raise ValueError("real handle required")
    model = store.get("models", model_id)
    accounts = [{**a, "status": "ACTIVE", "handle": handle.lstrip("@"),
                 "ai_label_enabled": True, "followers": a.get("followers") or 0}
                if a["platform"] == platform else a for a in model["social_accounts"]]
    if accounts == model["social_accounts"]:
        raise ValueError("unknown platform for this model")
    return store.upsert("models", {"model_id": model_id, "social_accounts": accounts})


def current_launch(snapshot):
    open_ = [l for l in snapshot.get("launches", []) if l["stage"] != "CLOSED"]
    return max(open_, key=lambda l: l["opened_at"]) if open_ else None


def launch_summary(snapshot):
    launch = current_launch(snapshot)
    closed = [l for l in snapshot.get("launches", []) if l["stage"] == "CLOSED"]
    if not launch:
        return {"agency": AGENCY_IDENTITY["name"], "open": None, "launched": len(closed),
                "next_step": "open_casting: propose the next model"}
    return {"agency": AGENCY_IDENTITY["name"], "launched": len(closed),
            "open": {"launch_id": launch["launch_id"], "model": launch["stage_name"],
                     "stage": launch["stage"], "gate": GATES.get(launch["stage"])},
            "next_step": GATES.get(launch["stage"])}
