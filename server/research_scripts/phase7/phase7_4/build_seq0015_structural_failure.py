#!/usr/bin/env python3
"""Phase 7.4A Structural Closure sec.4, CORRETTO dalla Structural Verdict
Semantics Patch (2026-09-20) - formalizza il verdetto strutturale per
SEQ-0015 (distinto da REFUTED_EDGE/INSUFFICIENT_SAMPLE/NO_EDGE - nessun
outcome e' mai stato letto). Usa REALMENTE candidate_lifecycle.Candidate
(nessun lifecycle parallelo) transitando GENERATED -> STRUCTURALLY_NON_VIABLE.

CORREZIONE: la versione precedente descriveva questo esito come
un'impossibilita' universale del design ("indipendentemente dalla
quantita' di dati disponibili"). L'evidenza disponibile dimostra SOLO
che il test pre-registrato non e' eseguibile SULLA partition
development_discovery gia' congelata - non che il meccanismo sia
impossibile in astratto. Una serie futura con gap fra cluster di eventi
piu' ampi dell'embargo (39 barre) potrebbe produrre piu' di
un'osservazione indipendente; questo pero' costituirebbe un NUOVO
esperimento pre-registrato (nuova partition, nuova provenance), mai
un'estensione della stessa run."""
import json
import os
import sys

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
from candidate_lifecycle import Candidate, InvalidTransitionError  # noqa: E402

SEQ0015_STATUS = "FROZEN_EXPERIMENT_NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY_PARTITION"


def main():
    with open(os.path.join(PHASE74_DIR, "phase7_4_baseline_matching_topology_audit_v1.json"), encoding="utf-8") as f:
        topology = json.load(f)
    finding = topology["major_structural_finding_independent_view_collapse"]
    funnel = topology["detection_funnel"]

    candidate = Candidate("SEQFAM-SEQ0015_MOMENTUM_BURST_CONTINUATION_V1")
    candidate.transition("STRUCTURALLY_NON_VIABLE",
                         reason=f"INDEPENDENT_VIEW={finding['n_independent_view_eligible']} sulla partition "
                                f"development_discovery preregistrata (nessuna affermazione oltre questa "
                                f"partition) - vedi failure_memory_registry_v1.json:FAIL-009")
    assert candidate.is_terminal()

    payload = {
        "sequence_family_id": "SEQFAM-SEQ0015_MOMENTUM_BURST_CONTINUATION_V1",
        "SEQ0015_STATUS": SEQ0015_STATUS,
        "SEQ0015_STATUS_precise_definition": (
            "Il detector/episode/embargo congelati (P90/252, episode_gap=3, natural_horizon=40, embargo=39) "
            "non soddisfano il gate di campione minimo indipendente (n_nominal_minimum=30) SULLA SPECIFICA "
            "partition development_discovery gia' preregistrata e congelata. NESSUNA affermazione e' fatta "
            "oltre questa partition - vedi 'not_a_universal_impossibility_claim' sotto."
        ),
        "lifecycle_state": "STRUCTURALLY_NON_VIABLE (candidate_lifecycle.py - stato invariato, vedi nota terminologica)",
        "lifecycle_transition": {"history": candidate.history, "is_terminal": candidate.is_terminal()},
        "not_a_universal_impossibility_claim": (
            "CORREZIONE ESPLICITA (Phase 7.4A Structural Verdict Semantics Patch): questo verdetto NON dimostra "
            "che il design non possa MAI produrre un numero sufficiente di osservazioni indipendenti "
            "indipendentemente dalla quantita' di dati. Un periodo di osservazione diverso o piu' lungo "
            "potrebbe contenere intervalli senza eventi piu' ampi dell'embargo (es. 60 barre) e interrompere "
            "il clustering transitivo, producendo piu' di un'osservazione indipendente. La conclusione qui "
            "dimostrata riguarda ESCLUSIVAMENTE la partition development_discovery gia' fissata e "
            "preregistrata - non il meccanismo detector/episode/embargo in astratto."
        ),
        "distinction_from_other_categories": {
            "NOT_REFUTED_EDGE": "REFUTED implica che un effetto e' stato misurato e trovato nullo/contrario - QUI nessun outcome e' mai stato letto o calcolato.",
            "NOT_ORDINARY_INSUFFICIENT_SAMPLE": "INSUFFICIENT_SAMPLE ordinario implica che il processo sperimentale e' valido e il campione osservato in QUESTA run e' semplicemente sotto soglia (es. n=25 invece di 30) - potenzialmente risolvibile con piu' dati SENZA toccare il design.",
            "NOT_NO_EDGE": "NO_EDGE (o NO_SUPPORTED_CANDIDATE, Phase 7.1) implica che l'inferenza e' stata eseguita e non ha superato i gate - QUI l'inferenza non ha mai potuto iniziare.",
            "IS_FROZEN_DESIGN_PARTITION_INCOMPATIBILITY": "Il meccanismo di event clustering del design congelato comprime 210 episodi in 1 sola osservazione indipendente SULLA partition preregistrata attuale - il test COSI' COM'E' PRE-REGISTRATO non e' eseguibile su QUESTI dati, senza che cio' implichi un giudizio sul meccanismo in generale.",
        },
        "evidence": {
            "n_event_view": funnel["n_event_view"], "n_episode_view": funnel["n_episode_view"],
            "n_independent_view": funnel["n_independent_view_eligible"],
            "median_episode_gap_bars": finding["median_episode_gap_bars"],
            "episode_gap_rule_bars": 3, "natural_horizon_bars": 40, "outcome_overlap_embargo_bars": 39,
            "minimum_sample_gate_n_nominal_minimum": 30,
            "shortfall": f"n_independent_view={funnel['n_independent_view_eligible']} << minimum_sample_gate.n_nominal_minimum=30 (sulla partition development_discovery preregistrata)",
        },
        "no_rescue_applied": (
            "NON sono stati modificati P90/252/natural_horizon=40/embargo=39 per rendere SEQ-0015 testabile - "
            "questo sarebbe un redesign post-preregistration informato dalla firing topology, esplicitamente "
            "vietato. Se in futuro si vorra' studiare il meccanismo su una finestra dati diversa/piu' lunga, "
            "dovra' diventare un NUOVO esperimento pre-registrato (nuova partition, nuova provenance, nuova "
            "sequence spec/hypothesis) - MAI un'estensione silenziosa di questa stessa run."
        ),
        "direction_semantics_note": (
            "SequenceBaselineAdapter assegna a OGNI controllo la stessa direzione dell'evento (direction-"
            "conditioned counterfactual baseline, baseline_contract_v4.json:direction_aware - 'valutati come "
            "ipotetico BUY/SELL') - NON la direzione osservata indipendentemente della barra di controllo. "
            "Verificato coerente con il contratto v4 in questa patch (Phase 7.4A Structural Verdict Semantics "
            "Patch) - nessuna modifica al codice, solo terminologia."
        ),
        "failure_memory_pattern_ref": "FAIL-009 (failure_memory_registry_v1.json) - INDEPENDENT_VIEW_COLLAPSE_ON_PREREGISTERED_PARTITION",
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
