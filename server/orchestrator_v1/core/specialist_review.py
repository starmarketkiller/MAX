#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - Dynamic Specialist Review.

    WAITING_APPROVAL -> (human REJECT) -> ESCALATION_REQUIRED, candidates=[...]
        -> a candidate is AVAILABLE/LOW_QUOTA -> review call (ProviderConnectorV1,
           reused as-is) -> REWORK_INSTRUCTIONS -> back to the local worker
        -> no candidate usable right now -> WAITING_REVIEW_PROVIDER (distinct
           from ESCALATION_REQUIRED on purpose - see task_queue.py) -> resumes
           on its own the moment one becomes available, no human action needed

This module owns only the two small, genuinely new pieces: WHICH reviewers
are candidates for a work_type (capability > availability > cost > preference
- an ORDERED LIST, never a single hardcoded provider name), and WHAT shape a
reviewer's response must have. Availability checking, the policy/budget gate,
the actual provider call, idempotency and the context packet contract are
ProviderConnectorV1/ProviderPolicyRegistryV1/context_packet.py, reused
unchanged - this is deliberately not a parallel routing system.
"""
from __future__ import annotations

HUMAN_REJECTED_REWORK_REQUESTED = "HUMAN_REJECTED_REWORK_REQUESTED"

# Ordered by preference within each work_type - capability (can this role
# review this kind of change at all) already filters the key set; a caller
# still checks each candidate's live state() in order and stops at the first
# AVAILABLE/LOW_QUOTA one (availability), still gated by the existing
# premium budget policy (cost). Adding a third reviewer for a work_type - a
# free/local one, say - is one entry in one of these lists, never a change
# to the workflow itself.
REVIEWER_CANDIDATES_FOR_WORK_TYPE = {
    # GROQ first: a FREE_ONLINE reviewer costs nothing and is tried before
    # either premium fallback - CODEX/CLAUDE are only ever reached if GROQ is
    # OFFLINE/RATE_LIMITED/EXHAUSTED or not yet wired (see
    # GroqReviewAdapter.configured). This is the "capability > availability >
    # cost > preference" principle applied literally: same capability tier
    # (review this patch), GROQ wins purely on cost when it's available.
    "complex_code": ["GROQ", "CODEX", "CLAUDE"],
    "scientific_research": ["CLAUDE"],
}
_DEFAULT_CANDIDATES = ["CLAUDE"]

# Shared, single source of truth for the review contract's wording - every
# reviewer adapter (Claude, Groq, ...) uses this exact prompt so "what a
# reviewer is allowed to do" is defined once, not re-typed per provider.
REVIEWER_SYSTEM_PROMPT = (
    "Sei un senior code reviewer per NEXUS. Non scrivi mai codice, non esegui mai "
    "comandi, non fai mai push o deploy: il tuo unico output e' un pacchetto di "
    "istruzioni correttive per un worker locale che ritentera' la patch. Rispondi SOLO "
    "con un oggetto JSON con esattamente queste chiavi: problems_found (array di "
    "stringhe), rework_instructions (stringa), allowed_paths (array di stringhe), "
    "required_tests (array di stringhe), risks (array di stringhe). Nessun altro testo, "
    "nessun markdown fuori dal JSON.")


def select_reviewer_candidates(work_type):
    """Pure, deterministic: no state is read here. Returns a NEW list every
    call so a caller can safely store/mutate its own copy on a task record."""
    return list(REVIEWER_CANDIDATES_FOR_WORK_TYPE.get(work_type, _DEFAULT_CANDIDATES))


def validate_rework_response(output):
    """A specialist reviewer never writes or executes a patch - it returns a
    bounded instruction packet for the local worker's next attempt. Fail
    closed on any missing/malformed field rather than guessing a default,
    same discipline as ProviderConnectorV1._verify_output for a normal
    escalation response."""
    if not isinstance(output, dict):
        return False, ["reviewer output is not an object"]
    errors = []
    problems = output.get("problems_found")
    if not isinstance(problems, list) or not all(isinstance(item, str) for item in problems):
        errors.append("problems_found must be an array of strings")
    instructions = output.get("rework_instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        errors.append("rework_instructions must be a non-empty string")
    allowed_paths = output.get("allowed_paths")
    if not isinstance(allowed_paths, list) or not all(isinstance(p, str) for p in allowed_paths):
        errors.append("allowed_paths must be an array of strings")
    required_tests = output.get("required_tests")
    if not isinstance(required_tests, list) or not all(isinstance(t, str) for t in required_tests):
        errors.append("required_tests must be an array of strings")
    risks = output.get("risks")
    if not isinstance(risks, list) or not all(isinstance(r, str) for r in risks):
        errors.append("risks must be an array of strings")
    return (not errors), errors
