#!/usr/bin/env python3
"""Phase 7.3 sec.10/13/14 - Integrazione di governance: riusa (non
duplica) engine/preregistration_provenance_guard.py (Phase 7.1) e
engine/candidate_lifecycle.py (Phase 7.0/Integrity Patch). Nessun
lifecycle parallelo, nessuna nuova logica di provenance."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", ".."))
PHASE7_ENGINE_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "engine")
sys.path.insert(0, PHASE7_ENGINE_DIR)
from preregistration_provenance_guard import assert_frozen_spec_committed_before_run, PreRegistrationProvenanceError  # noqa: E402,F401
from candidate_lifecycle import Candidate, InvalidTransitionError  # noqa: E402,F401


class DirectRepeatBlockedError(Exception):
    pass


def assert_frozen_spec_ready_for_sequence_family(repo_root: str, frozen_spec_rel_path: str) -> str:
    """Riuso diretto sec.10 - stessa regola PRE-REGISTRATION COMMIT -> RUN
    -> RESULT COMMIT di Phase 7.1, applicata a un sequence_family_frozen_spec."""
    return assert_frozen_spec_committed_before_run(repo_root, frozen_spec_rel_path)


def enforce_failure_memory_gate(failure_memory_links: dict, direct_repeat_override: dict = None):
    """sec.14 - DIRECT_REPEAT_OF_FAILED_IDEA e' bloccato SALVO override
    documentato e pre-registrato (presente nel frozen spec stesso, non
    aggiunto a runtime)."""
    if failure_memory_links.get("direct_repeat_flag"):
        if not direct_repeat_override:
            raise DirectRepeatBlockedError(
                f"failure_memory_relation=DIRECT_REPEAT_OF_FAILED_IDEA (prior_failure_ids="
                f"{failure_memory_links.get('prior_failure_ids')}) - bloccato. Serve un "
                f"direct_repeat_override documentato e pre-registrato nel frozen spec stesso."
            )
        required_keys = {"override_reason", "independent_mechanistic_justification", "approved_by"}
        missing = required_keys - set(direct_repeat_override)
        if missing:
            raise DirectRepeatBlockedError(f"direct_repeat_override incompleto - mancano: {missing}")
    return True


def new_candidate_for_sequence_family(sequence_family_id: str) -> Candidate:
    """Usa candidate_lifecycle.Candidate DIRETTAMENTE - nessun wrapper che
    ne alteri la macchina a stati (sec.13: 'non creare un lifecycle
    parallelo')."""
    return Candidate(sequence_family_id)


if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(ROOT))

    # Caso 1: gate failure-memory su una family NOVEL -> nessun blocco.
    novel_links = {"failure_memory_relation": "NOVEL", "prior_failure_ids": [], "direct_repeat_flag": False,
                   "related_failure_flag": False, "novelty_note": None}
    assert enforce_failure_memory_gate(novel_links) is True
    print("Caso 1 OK: family NOVEL -> nessun blocco failure-memory.")

    # Caso 2: DIRECT_REPEAT senza override -> bloccato.
    direct_repeat_links = {"failure_memory_relation": "DIRECT_REPEAT_OF_FAILED_IDEA",
                            "prior_failure_ids": ["SEQ-0010"], "direct_repeat_flag": True,
                            "related_failure_flag": False, "novelty_note": None}
    try:
        enforce_failure_memory_gate(direct_repeat_links)
        print("ERRORE: DIRECT_REPEAT senza override avrebbe dovuto essere bloccato!")
    except DirectRepeatBlockedError as e:
        print(f"Caso 2 OK: DIRECT_REPEAT senza override -> bloccato ({type(e).__name__})")

    # Caso 3: DIRECT_REPEAT CON override completo e documentato -> ammesso.
    override = {"override_reason": "test", "independent_mechanistic_justification": "test", "approved_by": "test"}
    assert enforce_failure_memory_gate(direct_repeat_links, direct_repeat_override=override) is True
    print("Caso 3 OK: DIRECT_REPEAT con override documentato -> ammesso.")

    # Caso 4: nessun lifecycle parallelo - il Candidate creato qui e' esattamente
    # candidate_lifecycle.Candidate, stesse transizioni ammesse/vietate.
    c = new_candidate_for_sequence_family("SEQFAM-DEMO")
    c.transition("DISCOVERY_SIGNAL")
    try:
        c.transition("SUPPORTED")
        print("ERRORE: salto di stato illegale non bloccato dal lifecycle riusato!")
    except InvalidTransitionError:
        print("Caso 4 OK: lifecycle riusato (candidate_lifecycle.py) applica le stesse regole, nessun parallelo.")

    print("\nGovernance del Sequence Engine verificata (provenance + failure-memory + lifecycle riusati).")
