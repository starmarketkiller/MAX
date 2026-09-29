#!/usr/bin/env python3
"""NEXUS TASK #0008 punto 1 - WORK_PRODUCT_V1 lifecycle: state machine
FAIL-CLOSED, stesso principio di core/task_queue.py e di
server/funding_v1/opportunity_lifecycle.py. Nessuna FINAL DELIVERY finche'
la review richiesta (quando REVIEW_MATRIX_V1 lo impone) non e' passata."""

STATES = ["DRAFT", "VERIFYING", "VERIFIED", "REVIEW_REQUIRED", "UNDER_REVIEW",
         "REVISION_REQUIRED", "REVISED", "FINALIZING", "FINALIZED", "DELIVERED", "BLOCKED"]

MAX_REVIEW_LOOPS = 2

ALLOWED_TRANSITIONS = {
    "DRAFT": ["VERIFYING", "BLOCKED"],
    "VERIFYING": ["VERIFIED", "REVISION_REQUIRED", "BLOCKED"],
    "VERIFIED": ["REVIEW_REQUIRED", "FINALIZING", "BLOCKED"],
    "REVIEW_REQUIRED": ["UNDER_REVIEW", "BLOCKED"],
    "UNDER_REVIEW": ["FINALIZING", "REVISION_REQUIRED", "BLOCKED"],
    "REVISION_REQUIRED": ["REVISED", "BLOCKED"],
    "REVISED": ["VERIFYING", "BLOCKED"],
    "FINALIZING": ["FINALIZED", "BLOCKED"],
    "FINALIZED": ["DELIVERED"],
    "DELIVERED": [],
    # Restart esplicito (mai automatico) da un blocco - stessa idea di PAUSED
    # in opportunity_lifecycle.py, ma qui il blocco richiede sempre un
    # intervento deliberato prima di ripartire, non una semplice ripresa.
    "BLOCKED": ["DRAFT"],
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
    return {"schema_version": 1, "states": STATES, "allowed_transitions": ALLOWED_TRANSITIONS,
           "max_review_loops": MAX_REVIEW_LOOPS}
