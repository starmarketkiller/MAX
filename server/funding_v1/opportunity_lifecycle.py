#!/usr/bin/env python3
"""NEXUS TASK #0006 - Opportunity Lifecycle V1: state machine FAIL-CLOSED,
stesso principio gia' stabilito in server/orchestrator_v1/core/task_queue.py
(ALLOWED_TRANSITIONS) - applicato qui al dominio business. Nessuna
opportunity puo' saltare da IDEA a MARKET_TEST."""

STATES = ["IDEA", "RESEARCH_REQUIRED", "RESEARCHING", "PROVISIONAL", "VALIDATION_READY",
         "VALIDATING", "MVP_READY", "MARKET_TEST", "FIRST_REVENUE", "REPEATABLE", "SCALABLE",
         "PAUSED", "REJECTED"]

# PAUSED e' raggiungibile da OGNI stato non terminale (pausa generica) - REJECTED e' sempre
# raggiungibile da ogni stato non terminale (decisione di abbandono, mai automatica - vedi
# approval boundary). SCALABLE e REJECTED sono terminali (nessuna uscita).
_RESUMABLE_FROM_PAUSED = ["IDEA", "RESEARCH_REQUIRED", "RESEARCHING", "PROVISIONAL",
                         "VALIDATION_READY", "VALIDATING", "MVP_READY", "MARKET_TEST",
                         "FIRST_REVENUE", "REPEATABLE"]

ALLOWED_TRANSITIONS = {
    "IDEA": ["RESEARCH_REQUIRED", "PAUSED", "REJECTED"],
    "RESEARCH_REQUIRED": ["RESEARCHING", "PAUSED", "REJECTED"],
    "RESEARCHING": ["PROVISIONAL", "RESEARCH_REQUIRED", "PAUSED", "REJECTED"],
    "PROVISIONAL": ["VALIDATION_READY", "RESEARCH_REQUIRED", "PAUSED", "REJECTED"],
    "VALIDATION_READY": ["VALIDATING", "PAUSED", "REJECTED"],
    "VALIDATING": ["MVP_READY", "PROVISIONAL", "PAUSED", "REJECTED"],
    "MVP_READY": ["MARKET_TEST", "PAUSED", "REJECTED"],
    "MARKET_TEST": ["FIRST_REVENUE", "MVP_READY", "PAUSED", "REJECTED"],
    "FIRST_REVENUE": ["REPEATABLE", "PAUSED", "REJECTED"],
    "REPEATABLE": ["SCALABLE", "PAUSED", "REJECTED"],
    "SCALABLE": [],
    "PAUSED": list(_RESUMABLE_FROM_PAUSED) + ["REJECTED"],
    "REJECTED": [],
}


def validate_transition(current_state, new_state):
    """Ritorna (bool, str) - mai applica una transizione non elencata."""
    if current_state not in ALLOWED_TRANSITIONS:
        return False, f"stato corrente sconosciuto: {current_state}"
    if new_state not in ALLOWED_TRANSITIONS[current_state]:
        return False, (f"transizione non permessa: {current_state} -> {new_state} "
                      f"(permesse: {ALLOWED_TRANSITIONS[current_state]})")
    return True, "OK"


def build_lifecycle_definition():
    return {"schema_version": 1, "states": STATES, "allowed_transitions": ALLOWED_TRANSITIONS}
