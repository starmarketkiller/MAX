#!/usr/bin/env python3
"""Phase 7.4A sec.18 - Costruisce phase7_4_seq0015_frozen_spec_v1.json,
conforme a sequence_family_frozen_spec_v1.schema.json (Phase 7.3).
NON esegue alcun detect_sequence su dati NEXUS, NON calcola alcun
outcome - assembla solo il documento di pre-registrazione + calcola
gli hash di provenance (sec.16)."""
import hashlib
import json
import os
import sys

PHASE74_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE74_DIR, "..", "..", "..", ".."))
SCHEMA_PATH = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_3", "schemas",
                            "sequence_family_frozen_spec_v1.schema.json")
sys.path.insert(0, PHASE74_DIR)
from seq0015_momentum_burst_detector import DETECTOR_VERSION, FROZEN_PARAMETERS  # noqa: E402


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def sha256_canonical_json(obj):
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_frozen_spec():
    detector_path = os.path.join(PHASE74_DIR, "seq0015_momentum_burst_detector.py")
    detector_source_hash = sha256_file(detector_path)
    frozen_parameters_hash = sha256_canonical_json(FROZEN_PARAMETERS)

    frozen_parameters = dict(FROZEN_PARAMETERS)
    frozen_parameters["provenance"] = {
        "detector_source_hash": detector_source_hash,
        "detector_source_file": "server/research_scripts/phase7/phase7_4/seq0015_momentum_burst_detector.py",
        "frozen_parameters_hash": frozen_parameters_hash,
        "note": "frozen_parameters_hash e' calcolato su questo stesso dict PRIMA dell'aggiunta di questa chiave 'provenance' (vedi build_frozen_spec() - hash preso su FROZEN_PARAMETERS originale importato dal detector, non su questa copia arricchita).",
    }

    spec = {
        "sequence_family_id": "SEQFAM-SEQ0015_MOMENTUM_BURST_CONTINUATION_V1",
        "sequence_ids": ["SEQ-0015"],
        "detector_version": DETECTOR_VERSION,
        "frozen_parameters": frozen_parameters,
        "state_prerequisites": [
            "volatility_state_pre_burst (terzile di atr_percentile a t-1, terzili fitted SOLO su development_discovery)",
            "trend_state_pre_burst (terzile di ema_slope_atr_norm a t-1, terzili fitted SOLO su development_discovery)",
            "direction (BUY/SELL da close_t vs open_t, NO_EVENT se doji)",
        ],
        "observation_cutoff_definition": "close(t) - nessun prezzo con indice > t puo' entrare nella feature di stato o nella soglia di rilevazione (burst_ratio_t e la sua soglia usano solo dati fino a t-1 per il denominatore/soglia, e fino a t per TR_t stesso).",
        "prediction_start_definition": "close(t), coincide con transition_complete_index per costruzione (MOMENTUM_BURST non ha una fase di transizione separata) - verificato >= transition_complete_index da sequence_causality_guard.enforce_temporal_causality.",
        "episode_gap_rule": 3,
        "natural_horizon": 40,
        "overlap_policy": "COLLAPSE_TO_FIRST",
        "baseline_match_dimensions": ["direction", "volatility_state_pre_burst", "trend_state_pre_burst"],
        "baseline_k": 5,
        "primary_outcome": "P_PLUS_1ATR_BEFORE_MINUS_1ATR",
        "secondary_outcomes": [
            "MFE", "MAE", "TIME_TO_MFE", "PATH_EFFICIENCY",
            "P_PLUS_0_5ATR_BEFORE_MINUS_1ATR", "P_PLUS_1_5ATR_BEFORE_MINUS_1ATR",
        ],
        "diagnostic_outcomes": [
            "P_PLUS_0_25ATR_BEFORE_MINUS_1ATR", "P_PLUS_2ATR_BEFORE_MINUS_1ATR", "TIME_TO_TARGET",
            "CONTINUATION_PROBABILITY", "REVERSAL_PROBABILITY", "REALIZED_VOLATILITY_AFTER_SETUP",
        ],
        "minimum_sample_gate": {
            "n_nominal_minimum": 30, "cluster_count_minimum": 20, "effective_n_minimum": 20,
            "minimum_controls_per_match": 20,
            "reference": "server/research_scripts/phase7/policies/minimum_evidence_gates.json - riusati senza override (nessuna continuita' diretta con RECLAIM/H006 che giustifichi un valore diverso per questa sequence, meccanismo indipendente).",
        },
        "effect_size_gate": {
            "minimum_material_delta_p": 0.10,
            "status": "POLICY_THRESHOLD (default di minimum_evidence_gates.json, NON l'override 0.15 usato in Phase 7.1)",
            "rationale": "L'override 0.15 di Phase 7.1 era motivato dalla continuita' diretta con la famiglia RECLAIM/H006 gia' testata storicamente. Questa motivazione non si applica a MOMENTUM_BURST_CONTINUATION (meccanismo indipendente, mai testato prima con questa esatta formalizzazione causale, seppur RELATED_TO_PREVIOUS_FAILURE - vedi failure_memory_links). Si usa quindi il floor di default 0.10, deciso ORA prima di vedere qualunque risultato.",
        },
        "uncertainty_method": "WILSON_CI95",
        "multiple_testing_family": {
            "family_id": "SEQFAM-SEQ0015_MOMENTUM_BURST-FULL-COMPARISON-FAMILY-V1",
            "family_size": 21,
            "members_description": "3 candidati (BOTH/BUY/SELL) x 7 outcome (1 primary + 6 secondary, OutcomeSurfaceV3.inferential_family_size()=7) = 21 - i 6 outcome DIAGNOSTIC_ONLY sono esclusi per costruzione.",
            "method": "Benjamini-Hochberg FDR, q=0.10 (multiple_testing_v2.benjamini_hochberg, riusato senza modifiche).",
        },
        "failure_memory_links": {
            "failure_memory_relation": "RELATED_TO_PREVIOUS_FAILURE",
            "prior_failure_ids": ["H008_EVENT_VOLATILITY_EXPANSION", "H010_INTERACTION_BREAKOUT_x_VOLATILITY_EXPANSION"],
            "direct_repeat_flag": False,
            "related_failure_flag": True,
            "novelty_note": (
                "H008_EVENT_VOLATILITY_EXPANSION (Phase 5, REFUTED, NO_EDGE) testava lo stesso concetto "
                "di base - barra con true range anomalo rispetto ad ATR - con soglia tr>1.0xATR_t "
                "(server/research_scripts/phase5/build_events.py riga 99), USANDO ATR SAME-BAR (non "
                "causale rispetto alla propria anomalia, verificato leggendo wilder_atr()). SEQ-0015 "
                "MOMENTUM_BURST_CONTINUATION NON e' un rename: (1) usa ATR_{t-1} come denominatore della "
                "soglia, non ATR_t (differenza metodologica verificata e motivata esplicitamente in "
                "frozen_parameters.detector_formula); (2) la soglia e' una regola distribuzionale causale "
                "(P90 rolling 252 barre) invece di un moltiplicatore fisso 1.0x mai giustificato "
                "esternamente; (3) il baseline matcha su stato PRE-BURST (t-1) con dimensioni dichiarate "
                "ORA (direction/volatility_state_pre_burst/trend_state_pre_burst), non sui terzili "
                "generici di H008; (4) usa l'architettura Episode-first (Phase 7.3) per non contare burst "
                "consecutivi della stessa espansione come osservazioni indipendenti, cosa che H008 non "
                "faceva affatto. Detto questo, il CONCETTO DI FONDO (barra a range anomalo -> "
                "continuazione) e' lo stesso gia' REFUTED in H008/H010 - dichiarato qui con piena "
                "trasparenza (RELATED_TO_PREVIOUS_FAILURE, non NOVEL) perche' 'NOVEL non deve significare "
                "nome diverso'. SEQ-0015 e' stata scelta come engine qualification family per motivi "
                "tecnici (poche dimensioni, H4 nativo, nessun gap dati), non perche' attesa piu' "
                "profittevole - un secondo REFUTED su questo meccanismo con l'engine v2 sarebbe comunque "
                "un risultato valido e atteso, non un fallimento della fase."
            ),
        },
        "no_rescue_clause": (
            "Nessuna soglia, gate, dimensione di matching, orizzonte o outcome primario/secondario "
            "dichiarati in questo documento sara' modificato dopo aver visto un risultato di QUALUNQUE "
            "fase (discovery, internal_validation, locked_validation, final_holdout) di una futura Phase "
            "7.4B - stesso principio di H006/Phase7.1. Un fallimento del candidato BOTH non autorizza una "
            "nuova ispezione isolata di BUY o SELL al di fuori della famiglia di confronto gia' congelata "
            "qui (candidate_family in frozen_parameters, sec.13)."
        ),
        "direct_repeat_override": None,
    }
    return spec


def validate_against_schema(spec):
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    required = schema["required"]
    allowed = set(schema["properties"].keys())
    missing = [k for k in required if k not in spec]
    extra = [k for k in spec if k not in allowed]
    fml_required = schema["properties"]["failure_memory_links"]["required"]
    fml_missing = [k for k in fml_required if k not in spec["failure_memory_links"]]
    direct_repeat_ok = (spec["failure_memory_links"]["direct_repeat_flag"] is False) or (spec.get("direct_repeat_override") is not None)
    return {
        "missing_required_top_level": missing,
        "extra_undeclared_top_level": extra,
        "missing_required_failure_memory_links": fml_missing,
        "direct_repeat_override_consistent": direct_repeat_ok,
        "PASS": not missing and not extra and not fml_missing and direct_repeat_ok,
    }


def main():
    spec = build_frozen_spec()
    result = validate_against_schema(spec)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["PASS"]:
        raise SystemExit("Frozen spec NON conforme allo schema - non scritto su disco.")

    out_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    print(f"\nScritto: {out_path}")
    print(f"detector_source_hash = {spec['frozen_parameters']['provenance']['detector_source_hash']}")
    print(f"frozen_parameters_hash = {spec['frozen_parameters']['provenance']['frozen_parameters_hash']}")
    return True


if __name__ == "__main__":
    main()
