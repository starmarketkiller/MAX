"""Initial casting roster: five deliberately different archetypes.

All models start as CASTING_DRAFT: designed, not generated.  The Higgsfield
AI Influencer `selection` blocks use option ids observed from
ai_influencer_get_options on 2026-10-07; a fresh ai_influencer_prepare quote
is still mandatory before any paid generation.
"""
from __future__ import annotations

# Hard rules applied to every model regardless of archetype.
GLOBAL_RESTRICTED = [
    "any minor or youthful-looking age presentation", "nudity or sexual acts",
    "resemblance to a specific real person without consent",
    "unlabeled AI content", "undisclosed ads or affiliate links",
    "false product, health, income or trading-return claims",
    "reposting third-party footage",
]

_BASE_SHEET = {"tool": "higgsfield.ai_influencer_prepare", "tier": "normal",
               "randomize": False, "batch_size": 2}


def _model(model_id, stage_name, archetype, style, tone, personality, categories,
           allowed, brand_fit, signature, selection, brief, quote=None):
    return {
        "model_id": model_id, "stage_name": stage_name,
        "visual_identity": {"signature_elements": signature,
                            "higgsfield_sheet": {**_BASE_SHEET, "selection": selection,
                                                 "brief": brief}},
        "age_presentation": "ADULT_21_PLUS", "style": style, "archetype": archetype,
        "tone": tone, "personality": personality, "content_categories": categories,
        "allowed_content": allowed, "restricted_content": list(GLOBAL_RESTRICTED),
        "social_accounts": [], "brand_fit": brand_fit,
        "visual_consistency_rules": [
            "same face/character sheet reference on every generation",
            "signature elements visible in the first frame",
            "phone-camera realism, natural skin texture",
        ],
        "prompt_seed": None, "voice_profile_future": None,
        "ai_disclosure": {"profile_label": "AI-generated profile", "bio_tag": "AI creator",
                          "content_label_required": True},
        "status": "CASTING_DRAFT", "last_quote": quote,
        "performance_metrics": {"followers": 0, "views": 0, "engagement": 0, "comments": 0,
                                "content_published": 0, "sales": 0, "revenue_eur": 0.0},
        "campaigns": [], "assigned_tasks": [],
    }


def initial_roster():
    return [
        _model("MDL_STREET_NOVA", "Nova", "STREETWEAR_URBAN", "streetwear", "playful, confident",
               "relatable big-sister energy, self-ironic, reacts big",
               ["viral_formats", "humor", "lifestyle", "fashion", "product_content"],
               ["trend remakes", "outfit checks", "try-on", "product reactions", "pet humor"],
               ["streetwear", "sneakers", "accessories", "tech gadgets", "beauty basics"],
               ["white over-ear headphones around the neck", "small silver hoops",
                "oversized streetwear"],
               {"gender": ["female"], "age": ["adult"], "ethnicity_origin_base": ["european"],
                "skin_tone": ["st_olive"], "hair": ["hair_long"], "hair_colour": ["hc_darkbrown"],
                "eye_color": ["eye_hazel"], "eye_shape": ["es_almond"],
                "freak_face": ["fn_freckles", "fn_dimples"], "distinctive": ["df_ears"],
                "accessory": ["acc_headphones"], "aesthetic": ["streetstyle"],
                "body_type": ["body_athletic"], "height": ["h_average"]},
               "Realistic, relatable lifestyle & entertainment creator. Warm expressive face for "
               "close-up selfie video, natural skin, playful confident vibe. Signature: oversized "
               "streetwear, small silver hoops, white headphones around the neck. Phone-camera "
               "creator, not a glossy model.",
               quote={"credits": 2.25, "batch_size": 2, "quoted_at": "2026-10-07",
                      "source": "higgsfield.ai_influencer_prepare", "stale_after_days": 7}),
        _model("MDL_LUXE_ELENA", "Elena", "ELEGANT_LUXURY", "elegant / quiet luxury",
               "calm, polished, slightly ironic", "old-money taste, honest reviews",
               ["fashion", "shoots", "special_occasions", "product_content", "runway_casting"],
               ["lookbooks", "styling tips", "unboxing", "event looks"],
               ["dresses", "bags", "jewelry", "fragrance", "home decor"],
               ["slicked low bun", "gold jewelry", "neutral palette"],
               {"gender": ["female"], "age": ["adult"], "ethnicity_origin_base": ["european"],
                "skin_tone": ["st_fair"], "hair": ["hair_long"], "hair_colour": ["hc_blonde"],
                "eye_color": ["eye_blue"], "freak_face": ["fn_cheekbones"],
                "accessory": ["acc_jewelry"], "aesthetic": ["suits"], "body_type": ["body_slim"],
                "height": ["h_tall"]},
               "Elegant quiet-luxury fashion creator, adult, calm confident presence, editorial "
               "but believable. Signature: low bun, gold jewelry, neutral tones.",
               quote={"credits": 2.25, "batch_size": 2, "quoted_at": "2026-10-07",
                      "source": "higgsfield.ai_influencer_prepare", "stale_after_days": 7}),
        _model("MDL_ACTIVE_MAYA", "Maya", "SPORT_ACTIVE", "athleisure", "energetic, motivating",
               "gym humor, before-the-workout honesty",
               ["lifestyle", "viral_formats", "humor", "product_content"],
               ["workout fails", "gym outfits", "routine POV", "healthy-snack tests"],
               ["activewear", "sneakers", "fitness gadgets", "bottles", "bags"],
               ["high ponytail", "bright sports set", "sweatband"],
               {"gender": ["female"], "age": ["adult"], "ethnicity_origin_base": ["latin_american"],
                "skin_tone": ["st_tan"], "hair": ["hair_long"], "hair_colour": ["hc_chestnut"],
                "eye_color": ["eye_brown"], "aesthetic": ["sporty"],
                "body_type": ["body_athletic"], "height": ["h_average"]},
               "Sporty adult lifestyle creator, high energy, funny about gym life. Signature: high "
               "ponytail, bright sports set, sweatband."),
        _model("MDL_CUTE_KAI", "Kai", "CUTE_RELATABLE", "casual / cozy", "awkward, wholesome",
               "chaotic-good, pet owner, everyday fails",
               ["humor", "viral_formats", "lifestyle", "product_content"],
               ["relatable POVs", "pet content", "cozy hauls", "cheap-vs-expensive tests"],
               ["home gadgets", "pet products", "cozy fashion", "stationery", "snacks"],
               ["round glasses", "oversized hoodie", "a cat in many videos"],
               {"gender": ["male"], "age": ["adult"], "ethnicity_origin_base": ["east_asian"],
                "skin_tone": ["st_light"], "hair": ["hair_short"], "hair_colour": ["hc_black"],
                "eye_color": ["eye_brown"], "accessory": ["acc_glasses"],
                "aesthetic": ["casual"], "body_type": ["body_slim"], "height": ["h_average"]},
               "Wholesome, awkward-funny adult male creator, cozy home vibe, pet owner. "
               "Signature: round glasses, oversized hoodie."),
        _model("MDL_BOLD_SIENNA", "Sienna", "BOLD_GLAM", "bold / glam (platform-safe)",
               "confident, teasing, witty", "main-character energy, fashion-forward",
               ["fashion", "shoots", "special_occasions", "viral_formats"],
               ["night-out looks", "transition edits", "glam GRWM", "swimwear in context"],
               ["evening wear", "heels", "makeup", "swimwear", "fragrance"],
               ["red hair", "bold lip", "statement earrings"],
               {"gender": ["female"], "age": ["adult"], "ethnicity_origin_base": ["european"],
                "skin_tone": ["st_light"], "hair": ["hair_long"], "hair_colour": ["hc_red"],
                "eye_color": ["eye_green"], "freak_face": ["fn_fulllips"],
                "accessory": ["acc_jewelry"], "aesthetic": ["theatrical"],
                "body_type": ["body_curvy"], "height": ["h_tall"]},
               "Bold glamorous adult fashion creator, confident and witty, platform-safe "
               "sensuality only (no nudity). Signature: red hair, bold lip, statement earrings."),
    ]
