#!/usr/bin/env python3
"""NEXUS TASK #0008 punto 5 - PREMIUM_BUDGET_POLICY_V1: regole
deterministiche, mai un router che decide 'a sensazione' se un premium
provider puo' essere usato."""

LEVELS = ["FREE_ONLY", "LOW_COST", "PREMIUM_IF_NEEDED", "PREMIUM_ALLOWED", "CRITICAL_REVIEW"]

RULES = {
    "FREE_ONLY": {
        "premium_allowed_condition": "mai - nessun premium provider ammesso per costruzione",
        "requires_user_approval": False,
    },
    "LOW_COST": {
        "premium_allowed_condition": "premium solo dopo almeno 1 fallimento locale gia' "
                                    "verificato dal verifier (mai al primo tentativo)",
        "requires_user_approval": False,
    },
    "PREMIUM_IF_NEEDED": {
        "premium_allowed_condition": "premium se la confidence del risultato locale e' "
                                    "sotto soglia o se la Review Matrix impone "
                                    "review_required=True con un reviewer premium",
        "requires_user_approval": False,
    },
    "PREMIUM_ALLOWED": {
        "premium_allowed_condition": "il Router puo' scegliere direttamente un premium "
                                    "provider, senza dover prima fallire in locale",
        "requires_user_approval": False,
    },
    "CRITICAL_REVIEW": {
        "premium_allowed_condition": "review premium sempre obbligatoria",
        "requires_user_approval": True,
    },
}


def allow_premium(level, *, local_attempt_failed=False, local_confidence="UNKNOWN",
                 review_matrix_requires_review=False):
    """Ritorna (allowed: bool, requires_user_approval: bool, reason: str) -
    fail-closed: un livello non riconosciuto non concede mai premium."""
    if level not in RULES:
        return False, True, f"livello sconosciuto '{level}' - fail-closed, nessun premium"
    rule = RULES[level]
    if level == "FREE_ONLY":
        return False, False, rule["premium_allowed_condition"]
    if level == "LOW_COST":
        allowed = bool(local_attempt_failed)
        return allowed, False, rule["premium_allowed_condition"]
    if level == "PREMIUM_IF_NEEDED":
        allowed = bool(review_matrix_requires_review) or local_confidence in ("LOW", "UNKNOWN")
        return allowed, False, rule["premium_allowed_condition"]
    if level == "PREMIUM_ALLOWED":
        return True, False, rule["premium_allowed_condition"]
    if level == "CRITICAL_REVIEW":
        return True, True, rule["premium_allowed_condition"]
    return False, True, "ramo fail-closed non atteso"


def build_premium_budget_policy():
    return {"schema_version": 1, "levels": LEVELS,
           "rules": [{"level": lvl, **cfg} for lvl, cfg in RULES.items()]}
