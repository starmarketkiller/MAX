#!/usr/bin/env python3
"""Phase 7.5A sec.9,11,13 - applica il Sequence Structural Feasibility
Gate alle 5 sequence family eligible rimaste dopo la chiusura di
SEQ-0015 (Phase 7.4A): SEQ-0001, SEQ-0009, SEQ-0014, SEQ-0016, SEQ-0020
(fonte: phase7_3/phase7_3_eligible_sequence_families_v1.json).

REGOLA DURA (sec.9): se una family non ha ancora un detector
sufficientemente formalizzato (formula/soglia congelata, episode_gap_rule,
natural_horizon proposto, outcome_overlap_embargo proposto), questo
script NON inventa quei parametri per far girare il gate - passa lo
spec incompleto COSI' COM'E' al gate reale
(engine/sequence_structural_feasibility_gate.py), che lo classifica
meccanicamente NEEDS_DETECTOR_FORMALIZATION con l'elenco esatto dei
campi mancanti. Nessun numero e' scelto qui per nessuna delle 5 family.

NESSUN dato NEXUS letto, NESSUN outcome, NESSUNA edge discovery.
SEQ-0015 e' CHIUSA e non compare in questo script come candidato."""
import os
import sys

PHASE75_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE75_DIR, "..", "..", "..", ".."))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE75_DIR, ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "engine"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))

from sequence_structural_feasibility_gate import (  # noqa: E402
    evaluate_family_structural_feasibility, REQUIRED_SPEC_FIELDS, ENGINE_VERSION, GATE_POLICY_VERSION,
)
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

# development_discovery e' la partition preregistrata gia' usata da tutta
# la Phase 7 (stesso n_bars gia' congelato/pubblicato per SEQ-0015,
# Phase 7.4A) - costante di progetto, non una scelta ad-hoc per questo
# script. Riportata qui SOLO come descrizione della partition dichiarata
# nello spec - il gate non la usa per calcolare nulla quando
# event_row_indices e' assente (nessun accesso dati).
DEVELOPMENT_DISCOVERY_PARTITION = {"partition_id": "development_discovery", "n_bars": 2393}

MINIMUM_EVIDENCE_GATES_REF = load_json(os.path.join(PHASE7_DIR, "policies", "minimum_evidence_gates.json"))
MINIMUM_EVIDENCE_GATES = {
    "n_nominal_minimum": MINIMUM_EVIDENCE_GATES_REF["gates"]["n_nominal_minimum"]["value"],
}

# Per ogni family: SOLO cio' che e' gia' dichiarato altrove nel repo
# (market_sequence_registry_v1.json, phase7_3_eligible_sequence_families_v1.json,
# feature_registry_v2.json, phase5/build_events.py per i detector gia'
# esistenti) - MAI un valore inventato per completare lo spec.
FAMILY_KNOWN_STATE = {
    "SEQ-0001": {
        "mechanism_id": "MECH-01",
        "event_direction_policy": "BOTH",
        "observation_timing": {
            "observation_cutoff": "event_a bar close (t=0)",
            "prediction_start": "t=0",
            "outcome_window_start": "t=1",
        },
        "detector_source_ref": None,
        "detector_parameters": None,
        "known_feature_dependencies": ["directional_efficiency"],
        "features_already_in_registry": ["directional_efficiency"],
        "narrative_definition": "MECH-01: movimento direzionale sostenuto su finestra multi-mese/annuale, "
                                 "nessuna inversione di trend confermata nel breve periodo successivo "
                                 "(market_sequence_registry_v1.json).",
        "missing_degrees_of_freedom_note": (
            "'movimento direzionale sostenuto' non ha ancora una soglia numerica congelata su "
            "directional_efficiency (quale valore/percentile conta come 'sostenuto'?), ne' una finestra "
            "di osservazione in barre H4 dichiarata (oggi descritta solo come 'mesi'). episode_gap_rule, "
            "natural_horizon e outcome_overlap_embargo non hanno alcuna proposta, nemmeno preliminare."
        ),
    },
    "SEQ-0009": {
        "mechanism_id": "MECH-18",
        "event_direction_policy": "BOTH",
        "observation_timing": {
            "observation_cutoff": "event_a bar close (t=0)",
            "prediction_start": "t=0",
            "outcome_window_start": "t=1",
        },
        "detector_source_ref": "server/research_scripts/phase5/build_events.py:SWEEP (sweep_v1_range20)",
        "detector_parameters": {"sweep_lookback_n": 20, "formula": "wick oltre max(high[i-20:i])/min(low[i-20:i]), "
                                 "escluso close oltre il livello (altrimenti e' RECLAIM, sequence diversa)"},
        "known_feature_dependencies": ["atr", "dist_from_rolling_high_atr", "dist_from_rolling_low_atr",
                                        "dist_from_prev_day_high_atr", "dist_from_prev_day_low_atr",
                                        "dist_from_prev_week_high_atr", "dist_from_prev_week_low_atr"],
        "features_already_in_registry": ["atr"],
        "narrative_definition": "MECH-18: prezzo eccede brevemente un livello di riferimento (swing/prev day/week "
                                 "high/low) senza chiudere oltre, poi richiude all'interno - detector SWEEP gia' "
                                 "esistente e usato in Phase 5 (solo come prerequisito di RECLAIM, mai testato da "
                                 "solo - RELATED_TO_PREVIOUS_FAILURE, non DIRECT_REPEAT).",
        "missing_degrees_of_freedom_note": (
            "Il detector grezzo (SWEEP) esiste gia' in codice con parametri fissi (sweep_lookback_n=20) - PIU' "
            "avanti delle altre 4 family per questo motivo - ma non e' MAI stato incorniciato come sequence "
            "standalone: mancano episode_gap_rule/natural_horizon/outcome_overlap_embargo proposti per SEQ-0009 "
            "come tale (i valori usati per SEQ-0015 non sono automaticamente validi qui - meccanismo diverso, "
            "livello di riferimento diverso), e le dimensioni di stato pre-evento per il baseline matching "
            "(quali terzili/feature categoriche?) non sono ancora dichiarate."
        ),
    },
    "SEQ-0014": {
        "mechanism_id": "MECH-23",
        "event_direction_policy": "NON_DIRECTIONAL",
        "observation_timing": {
            "observation_cutoff": "event_a bar close (t=0)",
            "prediction_start": "t=0",
            "outcome_window_start": "t=1",
        },
        "detector_source_ref": None,
        "detector_parameters": None,
        "known_feature_dependencies": ["directional_efficiency", "atr_percentile o variance_ratio_proxy"],
        "features_already_in_registry": ["directional_efficiency", "atr_percentile", "variance_ratio_proxy"],
        "narrative_definition": "MECH-23: classificazione dello stato corrente come 'choppy/laterale a bassa "
                                 "informazione' - famiglia LOW_INFORMATION_STATE/HIGH_CHOP_RISK, non un candidato "
                                 "direzionale (market_sequence_registry_v1.json).",
        "missing_degrees_of_freedom_note": (
            "Nessuna soglia congelata su directional_efficiency/atr_percentile/variance_ratio_proxy per "
            "definire 'choppy' (quale percentile? quale finestra?). Trattandosi di uno STATO (non un evento "
            "puntuale), 'event_a_index' stesso deve ancora essere definito operativamente (prima barra in cui lo "
            "stato viene rilevato? richiede N barre consecutive?) prima che episode_gap_rule/natural_horizon/"
            "embargo abbiano senso."
        ),
    },
    "SEQ-0016": {
        "mechanism_id": "MECH-26",
        "event_direction_policy": "CONTEXT_DEPENDENT",
        "observation_timing": {
            "observation_cutoff": "event_a bar close (t=0)",
            "prediction_start": "t=0",
            "outcome_window_start": "t=1",
        },
        "detector_source_ref": None,
        "detector_parameters": None,
        "known_feature_dependencies": ["atr (banda di volatilita' - proxy da definire)", "trend_state derivato"],
        "features_already_in_registry": ["atr"],
        "narrative_definition": "MECH-26: prezzo estende oltre una banda di volatilita' (es. Bollinger esterna) "
                                 "dopo un movimento rapido, poi reversione verso la media o continuazione "
                                 "(market_sequence_registry_v1.json).",
        "missing_degrees_of_freedom_note": (
            "'banda di volatilita'' non ha una formula congelata (Bollinger a quale moltiplicatore/finestra? o "
            "un proxy ATR-based, come gia' notato in feature_dependencies come 'proxy da definire'?). "
            "trend_state derivato non esiste come feature nominata in feature_registry_v2.json (da costruire, "
            "come gia' fatto ad-hoc per SEQ-0015 con trend_state_pre_burst, ma non riusabile automaticamente "
            "senza ridichiarare i propri terzili su questa family). direction e' CONTEXT_DEPENDENT (non ancora "
            "un policy operativo BUY/SELL/NO_EVENT come richiesto dal gate)."
        ),
    },
    "SEQ-0020": {
        "mechanism_id": "MECH-33",
        "event_direction_policy": "BOTH",
        "observation_timing": {
            "observation_cutoff": "event_a bar close (t=0)",
            "prediction_start": "t=0",
            "outcome_window_start": "t=1",
        },
        "detector_source_ref": None,
        "detector_parameters": None,
        "known_feature_dependencies": ["ema_slope_raw o feature equivalenti a media mobile corta/lunga sul midpoint"],
        "features_already_in_registry": ["ema_slope_raw", "ema_slope_atr_norm"],
        "narrative_definition": "MECH-33: incrocio o divergenza fra media mobile corta e lunga del midpoint di "
                                 "barra - possibile ridondanza con ema_slope_atr_norm gia' esistente, da "
                                 "verificare prima di trattarlo come nuovo (market_sequence_registry_v1.json).",
        "missing_degrees_of_freedom_note": (
            "Nessuna coppia di finestre (corta/lunga) congelata per l'incrocio, ne' una soglia di 'divergenza' "
            "minima per contare come evento (altrimenti il detector spara quasi su ogni barra - stesso rischio "
            "gia' descritto per FAIL-004, da verificare ESPLICITAMENTE con questo stesso gate una volta che le "
            "finestre siano proposte, non assunto ora). La nota di possibile ridondanza con ema_slope_atr_norm "
            "andrebbe risolta PRIMA di scrivere un nuovo detector (potrebbe non essere una sequence distinta)."
        ),
    },
}


def build_partial_spec(sequence_id: str, known: dict) -> dict:
    """Costruisce lo spec SOLO con i campi gia' noti - i campi mancanti
    sono semplicemente ASSENTI (non None inventato per placeholder, il
    gate stesso li rileva come assenti via `field not in spec`)."""
    spec = {
        "sequence_family_id": f"SEQFAM-{sequence_id}-CANDIDATE-V1",
        "event_direction_policy": known["event_direction_policy"],
        "observation_timing": known["observation_timing"],
        "discovery_partition": DEVELOPMENT_DISCOVERY_PARTITION,
        "minimum_evidence_gates": MINIMUM_EVIDENCE_GATES,
    }
    if known["detector_source_ref"] is not None:
        spec["detector_source_ref"] = known["detector_source_ref"]
        spec["detector_parameters"] = known["detector_parameters"]
        # Il detector grezzo esistere in codice NON equivale a "frozen" per
        # QUESTA sequence (episode/horizon/embargo/stato di matching non
        # dichiarati) - detector_frozen resta assente di proposito.
    return spec


def main():
    elig_path = os.path.join(PHASE7_DIR, "phase7_3", "phase7_3_eligible_sequence_families_v1.json")
    eligible = load_json(elig_path)["payload"]["eligible_sequence_ids"]
    remaining = [s for s in eligible if s != "SEQ-0015"]
    assert remaining == ["SEQ-0001", "SEQ-0009", "SEQ-0014", "SEQ-0016", "SEQ-0020"], (
        f"inventario inatteso: {remaining} - questo script copre SOLO le 5 family rimaste dopo SEQ-0015"
    )

    per_family_results = []
    for sequence_id in remaining:
        known = FAMILY_KNOWN_STATE[sequence_id]
        spec = build_partial_spec(sequence_id, known)
        gate_result = evaluate_family_structural_feasibility(spec)
        assert gate_result["verdict"] == "NEEDS_DETECTOR_FORMALIZATION", (
            f"{sequence_id}: atteso NEEDS_DETECTOR_FORMALIZATION (nessun detector formalizzato ancora nel "
            f"repo per questa sequence) - ottenuto {gate_result['verdict']}. Se questo assert fallisce, "
            f"un detector e' stato formalizzato altrove e questo script va aggiornato con i suoi parametri "
            f"REALI, non con placeholder."
        )
        per_family_results.append({
            "sequence_id": sequence_id,
            "mechanism_id": known["mechanism_id"],
            "narrative_definition": known["narrative_definition"],
            "detector_source_ref": known["detector_source_ref"],
            "detector_status": "EXISTING_RAW_EVENT_DETECTOR_NOT_YET_FRAMED_AS_SEQUENCE" if known["detector_source_ref"]
                                else "NO_DETECTOR_CODE_YET",
            "known_feature_dependencies": known["known_feature_dependencies"],
            "features_already_in_registry": known["features_already_in_registry"],
            "gate_verdict": gate_result["verdict"],
            "missing_degrees_of_freedom": gate_result["missing_degrees_of_freedom"],
            "missing_degrees_of_freedom_note": known["missing_degrees_of_freedom_note"],
        })

    payload = {
        "gate_engine_version": ENGINE_VERSION,
        "gate_policy_version": GATE_POLICY_VERSION,
        "baseline_commit_ref": "7b9d64b (Phase 7.4A Structural Verdict Semantics Patch - SEQ-0015 CLOSED)",
        "seq0015_status": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE - vedi failure_memory_registry_v1.json FAIL-009",
        "no_nexus_outcome_data_accessed": True,
        "no_edge_discovery_performed": True,
        "required_spec_fields_reference": list(REQUIRED_SPEC_FIELDS),
        "families_evaluated": per_family_results,
        "summary": {
            "n_families_evaluated": len(per_family_results),
            "n_ready_for_preregistration": sum(1 for r in per_family_results if r["gate_verdict"] == "FEASIBLE"),
            "n_needs_detector_formalization": sum(1 for r in per_family_results
                                                   if r["gate_verdict"] == "NEEDS_DETECTOR_FORMALIZATION"),
            "n_structurally_blocked": sum(1 for r in per_family_results
                                           if r["gate_verdict"] == "NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY"),
            "note": "Tutte e 5 le family rimaste sono NEEDS_DETECTOR_FORMALIZATION in questa run - nessuna "
                    "di esse ha ancora un detector abbastanza formalizzato (formula/soglia congelata, "
                    "episode_gap_rule, natural_horizon proposto, outcome_overlap_embargo proposto) perche' il "
                    "gate possa calcolare una geometria reale. Questo e' il risultato ATTESO e CORRETTO di "
                    "eseguire il preflight PRIMA della formalizzazione (sec.15 della richiesta Phase 7.5A) - "
                    "non un fallimento del gate.",
        },
    }
    out_path = os.path.join(PHASE75_DIR, "phase7_5_structural_feasibility_results_v1.json")
    save_json(out_path, wrap_with_provenance(payload, "phase7/phase7_5/build_phase7_5_structural_feasibility_results.py"))
    print(f"Scritto {out_path}")

    # ---- Candidate queue (sec.11) - ranking ESCLUSIVAMENTE strutturale ----
    def structural_completeness_rank(r):
        # Meno campi mancanti + detector grezzo gia' esistente = piu' vicino
        # a READY_FOR_PREREGISTRATION. MAI un punteggio di edge/probabilita'.
        has_existing_detector = 0 if r["detector_source_ref"] else 1
        return (has_existing_detector, len(r["missing_degrees_of_freedom"]), r["sequence_id"])

    ranked = sorted(per_family_results, key=structural_completeness_rank)
    queue_payload = {
        "ranking_policy": "ESCLUSIVAMENTE strutturale (testabilita', completezza detector, chiarezza "
                          "implementativa) - MAI probabilita' di edge/expected profitability/likelihood of "
                          "success (sec.10 della richiesta Phase 7.5A).",
        "READY_FOR_PREREGISTRATION": [r["sequence_id"] for r in per_family_results if r["gate_verdict"] == "FEASIBLE"],
        "STRUCTURALLY_BLOCKED_ON_CURRENT_PARTITION": [r["sequence_id"] for r in per_family_results
                                                       if r["gate_verdict"] == "NOT_TESTABLE_ON_PREREGISTERED_DISCOVERY"],
        "NEEDS_DETECTOR_FORMALIZATION_ORDERED_BY_STRUCTURAL_COMPLETENESS": [
            {
                "sequence_id": r["sequence_id"],
                "detector_status": r["detector_status"],
                "n_missing_degrees_of_freedom": len(r["missing_degrees_of_freedom"]),
                "missing_degrees_of_freedom": r["missing_degrees_of_freedom"],
            }
            for r in ranked
        ],
        "seq0015_status": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "no_edge_score_field": True,
    }
    queue_path = os.path.join(PHASE75_DIR, "phase7_5_candidate_queue_v1.json")
    save_json(queue_path, wrap_with_provenance(queue_payload, "phase7/phase7_5/build_phase7_5_structural_feasibility_results.py"))
    print(f"Scritto {queue_path}")


if __name__ == "__main__":
    main()
