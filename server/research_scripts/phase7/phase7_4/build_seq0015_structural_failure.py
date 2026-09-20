#!/usr/bin/env python3
"""Phase 7.4A Structural Closure sec.4 - formalizza il verdetto
strutturale per SEQ-0015 (distinto da REFUTED_EDGE/INSUFFICIENT_SAMPLE/
NO_EDGE - nessun outcome e' mai stato letto). Usa REALMENTE
candidate_lifecycle.Candidate (nessun lifecycle parallelo) transitando
GENERATED -> STRUCTURALLY_NON_VIABLE."""
import json
import os
import sys

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
from candidate_lifecycle import Candidate, InvalidTransitionError  # noqa: E402


def main():
    with open(os.path.join(PHASE74_DIR, "phase7_4_baseline_matching_topology_audit_v1.json"), encoding="utf-8") as f:
        topology = json.load(f)
    finding = topology["major_structural_finding_independent_view_collapse"]
    funnel = topology["detection_funnel"]

    candidate = Candidate("SEQFAM-SEQ0015_MOMENTUM_BURST_CONTINUATION_V1")
    candidate.transition("STRUCTURALLY_NON_VIABLE",
                         reason=f"INDEPENDENT_VIEW={finding['n_independent_view_eligible']} sotto la frozen spec v4 - "
                                f"vedi failure_memory_registry_v1.json:FAIL-009")
    assert candidate.is_terminal()

    payload = {
        "sequence_family_id": "SEQFAM-SEQ0015_MOMENTUM_BURST_CONTINUATION_V1",
        "SEQ0015_STATUS": "STRUCTURALLY_NON_VIABLE_UNDER_FROZEN_SPEC",
        "lifecycle_transition": {"history": candidate.history, "is_terminal": candidate.is_terminal()},
        "distinction_from_other_categories": {
            "NOT_REFUTED_EDGE": "REFUTED implica che un effetto e' stato misurato e trovato nullo/contrario - QUI nessun outcome e' mai stato letto o calcolato.",
            "NOT_INSUFFICIENT_SAMPLE": "INSUFFICIENT_SAMPLE implica che il campione di QUESTA run e' troppo piccolo, potenzialmente risolvibile con piu' dati o un periodo piu' lungo di discovery.",
            "NOT_NO_EDGE": "NO_EDGE (o NO_SUPPORTED_CANDIDATE, Phase 7.1) implica che l'inferenza e' stata eseguita e non ha superato i gate - QUI l'inferenza non ha mai potuto iniziare.",
            "IS_STRUCTURALLY_NON_VIABLE": "Il DESIGN stesso (detector P90/252 + episode_gap=3 + natural_horizon=40 + embargo=39) applicato a development_discovery reale produce un numero di osservazioni indipendenti insufficiente per QUALUNQUE metodo statistico, indipendentemente dalla quantita' di dati disponibili nella finestra data.",
        },
        "evidence": {
            "n_event_view": funnel["n_event_view"], "n_episode_view": funnel["n_episode_view"],
            "n_independent_view": funnel["n_independent_view_eligible"],
            "median_episode_gap_bars": finding["median_episode_gap_bars"],
            "episode_gap_rule_bars": 3, "natural_horizon_bars": 40, "outcome_overlap_embargo_bars": 39,
            "minimum_sample_gate_n_nominal_minimum": 30,
            "shortfall": f"n_independent_view={funnel['n_independent_view_eligible']} << minimum_sample_gate.n_nominal_minimum=30",
        },
        "no_rescue_applied": (
            "NON sono stati modificati P90/252/natural_horizon=40/embargo=39 per rendere SEQ-0015 testabile - "
            "questo sarebbe un redesign post-preregistration informato dalla firing topology, esplicitamente "
            "vietato. Se in futuro si vorra' studiare una variante con parametri diversi, dovra' diventare una "
            "NUOVA sequence spec/hypothesis con nuova identita' e nuova preregistrazione - MAI una modifica "
            "silenziosa di SEQ-0015."
        ),
        "failure_memory_pattern_ref": "FAIL-009 (failure_memory_registry_v1.json) - INDEPENDENT_VIEW_COLLAPSE_UNDER_FROZEN_DESIGN",
        "no_outcome_data_accessed": True, "no_edge_discovery_performed": True,
    }

    # Verifica negativa: da REFUTED non deve essere possibile raggiungere STRUCTURALLY_NON_VIABLE (non e' un giudizio sull'effetto).
    other = Candidate("DEMO-CHECK")
    other.transition("DISCOVERY_SIGNAL")
    other.transition("REFUTED")
    try:
        other.transition("STRUCTURALLY_NON_VIABLE")
        raise AssertionError("REFUTED -> STRUCTURALLY_NON_VIABLE avrebbe dovuto essere vietato!")
    except InvalidTransitionError:
        payload["negative_check_refuted_cannot_reach_structurally_non_viable"] = True

    out_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_structural_failure_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nScritto: {out_path}")
    return payload


if __name__ == "__main__":
    main()
