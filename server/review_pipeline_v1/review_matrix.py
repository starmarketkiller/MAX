#!/usr/bin/env python3
"""NEXUS TASK #0008 punto 3 - REVIEW_MATRIX_V1: dati, non prompt. Ogni riga
e' un giudizio di design dichiarato esplicitamente (stessa disciplina di
FUNDING_DIMENSION_WEIGHTS in opportunity_scoring.py) - il Review Engine la
LEGGE, non la reinterpreta. Modificabile editando questo dizionario (o, in
futuro, l'artifact canonico generato da build_review_matrix.py) senza
toccare nessun prompt."""

REVIEW_MATRIX = {
    "routine_summary": {
        "producer_default": "LOCAL_GENERALIST", "reviewer_default": None,
        "review_required": False, "distinct_producer_reviewer_required": False,
        "premium_budget_level": "FREE_ONLY",
    },
    "registry_backfill": {
        "producer_default": "DETERMINISTIC", "reviewer_default": "DETERMINISTIC",
        "review_required": False, "distinct_producer_reviewer_required": False,
        "premium_budget_level": "FREE_ONLY",
    },
    "business_analysis": {
        "producer_default": "LOCAL_GENERALIST", "reviewer_default": "STRATEGIC_GENERALIST",
        "review_required": True, "distinct_producer_reviewer_required": True,
        "premium_budget_level": "PREMIUM_IF_NEEDED",
    },
    "scientific_research": {
        "producer_default": "LOCAL_GENERALIST", "reviewer_default": "SCIENTIFIC_RESEARCHER",
        "review_required": True, "distinct_producer_reviewer_required": True,
        "premium_budget_level": "PREMIUM_IF_NEEDED",
    },
    "complex_code": {
        "producer_default": "CODE_SPECIALIST", "reviewer_default": None,
        "review_required": False, "distinct_producer_reviewer_required": False,
        "premium_budget_level": "LOW_COST",
        # "review_required=False" perche' il verifier (test) e' sufficiente in V1 -
        # una seconda review resta disponibile via needs_second_review su
        # REVIEW_RESULT_V1 o CRITICAL_REVIEW quando il chiamante lo richiede
        # esplicitamente, non e' imposta di default (§3 tabella utente:
        # "tests + optional second review").
    },
    "architecture_design": {
        "producer_default": "SCIENTIFIC_RESEARCHER", "reviewer_default": "SECOND_OPINION",
        "review_required": True, "distinct_producer_reviewer_required": True,
        "premium_budget_level": "CRITICAL_REVIEW",
    },
    "deployment": {
        "producer_default": "DEPLOYMENT_SPECIALIST", "reviewer_default": "DETERMINISTIC",
        "review_required": True, "distinct_producer_reviewer_required": True,
        "premium_budget_level": "PREMIUM_ALLOWED",
    },
    "trading_critical": {
        "producer_default": "DETERMINISTIC", "reviewer_default": "SCIENTIFIC_RESEARCHER",
        "review_required": True, "distinct_producer_reviewer_required": True,
        "premium_budget_level": "CRITICAL_REVIEW",
    },
}


def get_matrix_entry(work_type):
    """Fail-closed: un work_type non censito NON eredita un default
    permissivo - richiede review e il budget premium piu' cauto, cosi' un
    tipo di lavoro nuovo non scivola silenziosamente a FREE_ONLY."""
    if work_type in REVIEW_MATRIX:
        return dict(REVIEW_MATRIX[work_type])
    return {
        "producer_default": "LOCAL_GENERALIST", "reviewer_default": "SECOND_OPINION",
        "review_required": True, "distinct_producer_reviewer_required": True,
        "premium_budget_level": "PREMIUM_IF_NEEDED", "unrecognized_work_type": True,
    }


def build_review_matrix():
    entries = [{"work_type": wt, **cfg} for wt, cfg in REVIEW_MATRIX.items()]
    return {"schema_version": 1, "entries": entries}
