"""AGENCY_IDENTITY_V1: Unreal Faces, the agency every model belongs to.

The agency is the stable brand; models are launched under it one at a time
(see launch.py).  Handles are proposals only: availability cannot be checked
from NEXUS (Instagram answers identically for taken and free handles without
login), so a human confirms them in the app before any profile is created.
"""
from __future__ import annotations

AGENCY_IDENTITY = {
    "schema_version": "AGENCY_IDENTITY_V1",
    "name": "Unreal Faces",
    "legal_note": "trademark search (EUIPO/UIBM) still to do before paid branding",
    "positioning": "AI model agency, fashion + lifestyle mix: distinct models, one standard",
    "tagline": "Faces that don't exist. Style that does.",
    "proposed_handles": {"instagram": ["unrealfaces.agency", "unrealfaces", "unreal.faces"],
                         "status": "UNVERIFIED_CHECK_IN_APP"},
    "palette": {"ink": "#0B0B0F", "chrome": "#C9CCD3", "violet": "#7B5CFF",
                "signal_pink": "#FF4FA3", "paper": "#F5F3EF"},
    "typography": {"display": "geometric grotesk, all caps, wide tracking",
                   "body": "neutral sans (Inter-like)"},
    "tone_of_voice": ["confident, never arrogant", "playful about being AI",
                      "short sentences, English first", "no fake scarcity, no income claims"],
    "visual_rules": ["every model image signed with a small 'AI' chrome tag",
                     "ink or paper backgrounds for agency posts",
                     "one model per agency post; group shots only for roster reveals"],
    "brand_rules": [
        "every account carries the platform AI label and 'AI creator' in bio",
        "sponsored or affiliate content is always disclosed (#ad / paid partnership)",
        "no real-person likeness, no minors, no explicit content",
        "products only from the store gate (STORE_READY)",
        "credit budget per model approved before each paid step",
    ],
    "roster_policy": {"launch_mode": "ONE_AT_A_TIME",
                      "next_launch_allowed_from_stage": "MONETIZATION",
                      "niche_overlap": "avoid two active models with the same archetype"},
    "brand_contact": "collabs via link in bio (form) - no DM negotiations by the agency",
}


def agency_instagram_kit(identity=AGENCY_IDENTITY, roster=()):
    """The agency's own showcase profile (portfolio + brand contact)."""
    live = [m for m in roster if m.get("status") in {"CHARACTER_SHEET_READY", "ACTIVE"}]
    bio = ("AI model agency ✦ Faces that don't exist, style that does ✦ "
           "All talent is AI-generated ✦ Brands: collab ↓")
    return {
        "schema_version": "AGENCY_PROFILE_KIT_V1",
        "account": "agency", "display_name": "UNREAL FACES — AI Model Agency",
        "handle_candidates": identity["proposed_handles"]["instagram"],
        "handle_status": "UNVERIFIED_CHECK_IN_APP",
        "bio": bio, "bio_length": len(bio),
        "profile_picture_brief": ("wordmark 'UF' in chrome on ink background, no face "
                                  "(the agency is the frame, models are the faces)"),
        "link_in_bio": ["brand collab form", "roster page", "shop (when STORE_READY)"],
        "highlights": ["Roster", "Casting", "For brands", "How it's made (AI)", "Shop"],
        "launch_grid": [
            {"slot": 1, "type": "manifesto", "concept": "Faces that don't exist. Style that does."},
            {"slot": 2, "type": "how_it_works", "concept": "We are an AI agency: every face here is "
                                                          "generated, every product is real."},
            {"slot": 3, "type": "for_brands", "concept": "Why brands work with AI models: speed, "
                                                        "consistency, disclosure."},
            {"slot": 4, "type": "casting_teaser", "concept": "Casting open: silhouette of the first model"},
            {"slot": 5, "type": "casting_teaser", "concept": "Mood board of the first model's world"},
            {"slot": 6, "type": "reveal", "concept": "First model reveal (after IDENTITY gate)"},
            {"slot": 7, "type": "roster_card", "concept": "Model card: name, niche, @handle"},
            {"slot": 8, "type": "behind_the_scenes", "concept": "From brief to video: how a post is made"},
            {"slot": 9, "type": "values", "concept": "Our rules: AI label, #ad, no real-person likeness"},
        ],
        "roster_live": [m["stage_name"] for m in live],
        "first_captions": {
            "manifesto": "Meet Unreal Faces. An AI model agency. The faces aren't real — "
                         "the style, the products and the stories are. #AIcreator",
            "casting_teaser": "Casting is open. Our first face drops soon. "
                              "Guess the style in the comments 👀 #AIcreator",
        },
        "disclosure": "AI-generated profile label ON; 'All talent is AI-generated' in bio",
        "posting_cadence": "3 posts/week until the first model is live, then 1 roster post/week",
    }
