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
    "logo": {"mark": "UF", "style": "silver/chrome calligraphic script monogram",
             "background": "soft pink", "use": "profile picture, casting banner, backdrop, judges' table cards",
             "file": "assets/uf_logo_pink.png"},
    "palette": {"uf_pink": "#F4B6CB", "chrome": "#C9CCD3", "ink": "#0B0B0F",
                "paper": "#F5F3EF", "hot_pink": "#FF4FA3"},
    "typography": {"display": "geometric grotesk, all caps, wide tracking",
                   "body": "neutral sans (Inter-like)"},
    "tone_of_voice": ["confident, never arrogant", "playful about being AI",
                      "short sentences, English first", "no fake scarcity, no income claims"],
    "visual_rules": ["every model image signed with a small 'AI' chrome tag",
                     "agency posts live in the pink casting room: UF logo on banner and backdrop",
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


# Casting-room scene shared by every agency post (format reference: "casting
# reality" pages; we recreate the format, never another agency's branding).
CASTING_SET = ("bright fashion casting studio, soft pink seamless backdrop with a large silver "
               "chrome calligraphic 'UF' monogram, pink banner reading 'UNREAL FACES CASTING', "
               "white judges' table with clipboards, polaroids and small pink 'UF' name cards, "
               "softbox lighting, phone-shot vertical framing, realistic, candid")

CASTING_GRID = (
    {"slot": 1, "format": "reel", "type": "casting_open", "model_number": "001",
     "scene": "first model walks in holding number card 001, judges look up from clipboards",
     "caption": "Day one at Unreal Faces. Who walks in first? 💄"},
    {"slot": 2, "format": "reel", "type": "casting_1on1", "model_number": "007",
     "scene": "1on1: model 007 walks to the mark, holds the finishing pose, judge nods",
     "caption": "Casting 1on1 — the finishing pose 💄"},
    {"slot": 3, "format": "reel", "type": "judges_reaction", "model_number": "012",
     "scene": "model 012 stops posing and just laughs; judges lean in, one writes 'YES'",
     "caption": "She stopped trying. That's when it worked 💄"},
    {"slot": 4, "format": "reel", "type": "overdo_it", "model_number": "015",
     "scene": "model 015 overdoes the walk with dramatic spins, judges exchange looks",
     "caption": "When the walk is a little too much 💄"},
    {"slot": 5, "format": "carousel", "type": "backstage", "model_number": None,
     "scene": "backstage: rack of outfits, mirror lights, number tags pinned, makeup brush close-up",
     "caption": "Things you only see backstage 💄"},
    {"slot": 6, "format": "photo", "type": "lineup", "model_number": "001-021",
     "scene": "five models in a row against the UF backdrop, each holding a number card",
     "caption": "Five numbers. One contract. Who gets it? 👇"},
    {"slot": 7, "format": "reel", "type": "polaroid_wall", "model_number": None,
     "scene": "judge pins polaroids on a pink board under the UF logo, two get a chrome star",
     "caption": "The polaroid wall never lies 💄"},
    {"slot": 8, "format": "reel", "type": "callback", "model_number": "021",
     "scene": "judge reads 'number 021' twice; model 021 turns back in disbelief",
     "caption": "When they call your number twice 💄"},
    {"slot": 9, "format": "reel", "type": "signed", "model_number": "021",
     "scene": "model 021 signs at the judges' table, UF logo behind, confetti in pink and silver",
     "caption": "Number 021 is officially Unreal. Meet our first face soon 💄"},
)

POST_TAGS = "#unrealfaces #casting #AIgenerated #AImodel"


def casting_post_prompt(post):
    """Image/video prompt for one grid slot; the uploaded UF logo is the reference."""
    return (f"{CASTING_SET}. {post['scene']}. Original AI-generated models (no real-person "
            "likeness), adults, tasteful fashion styling. Use the reference image for the "
            "exact UF logo.")


def agency_instagram_kit(identity=AGENCY_IDENTITY, roster=()):
    """The agency's own showcase profile: a casting-room series under the UF logo."""
    live = [m for m in roster if m.get("status") in {"CHARACTER_SHEET_READY", "ACTIVE"}]
    bio = ("AI model agency ✦ Faces that don't exist, style that does ✦ "
           "All talent is AI-generated ✦ Brands: collab ↓")
    grid = [{**post, "caption": f"{post['caption']} {POST_TAGS}",
             "prompt": casting_post_prompt(post)} for post in CASTING_GRID]
    return {
        "schema_version": "AGENCY_PROFILE_KIT_V1",
        "account": "agency", "display_name": "UNREAL FACES — AI Model Agency",
        "handle_candidates": identity["proposed_handles"]["instagram"],
        "handle_status": "UNVERIFIED_CHECK_IN_APP",
        "bio": bio, "bio_length": len(bio),
        "profile_picture_brief": "the UF logo: silver chrome script monogram on soft pink, centered",
        "logo_reference": "upload the UF logo to Higgsfield once and pass it as reference to every post",
        "link_in_bio": ["brand collab form", "roster page", "shop (when STORE_READY)"],
        "highlights": ["Casting", "Roster", "Backstage", "For brands", "How it's made (AI)"],
        "series": "UNREAL FACES CASTING",
        "launch_grid": grid,
        "roster_live": [m["stage_name"] for m in live],
        "disclosure": "AI-generated profile label ON; 'All talent is AI-generated' in bio",
        "posting_cadence": "1 casting post/day for the first 9, then 3/week; slot 9 opens the first model's launch",
    }
