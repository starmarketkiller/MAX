#!/usr/bin/env python3
"""NEXUS TASK #0008 punto 7 - riusa la classificazione fallimenti gia'
esistente (core/retry_escalation.py, estesa in modo additivo con
STRATEGIC_AMBIGUITY) e la mappa su uno specialist_role per questa pipeline,
invece di duplicare la logica di classificazione."""
import os
import sys

REVIEW_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR = os.path.join(os.path.dirname(REVIEW_DIR), "orchestrator_v1")
sys.path.insert(0, ORCH_DIR)
from core.retry_escalation import (RETRY_MAX_ATTEMPTS, CLASSIFICATIONS,  # noqa: E402
                                   classify_failure, decide_escalation_target)

CLASSIFICATION_TO_SPECIALIST_ROLE = {
    "SCIENTIFIC_AMBIGUITY": "SCIENTIFIC_RESEARCHER",
    "COMPLEX_CODE_CHANGE": "CODE_SPECIALIST",
    "STRATEGIC_AMBIGUITY": "STRATEGIC_GENERALIST",
    "LOCAL_MODEL_CAPABILITY": "LOCAL_GENERALIST",
    "ENVIRONMENT": "DETERMINISTIC",
    "TOOLING": "DETERMINISTIC",
    "PERMISSION": None,   # -> APPROVAL_REQUIRED, non uno specialist
    "UNKNOWN": None,      # -> MANUAL_REVIEW
}


def specialist_role_for_classification(classification):
    return CLASSIFICATION_TO_SPECIALIST_ROLE.get(classification)
