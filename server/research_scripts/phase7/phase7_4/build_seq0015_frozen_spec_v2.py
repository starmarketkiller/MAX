#!/usr/bin/env python3
"""Phase 7.4A Integrity Patch sec.5 - costruisce
phase7_4_seq0015_frozen_spec_v2.json, che DICHIARA supersedes: v1 e
corregge ESCLUSIVAMENTE i 3 problemi della patch (episode/outcome
overlap, contratto statistico per outcome, terminologia ATR_t) + la
correzione terminologica del novelty_note. NON sovrascrive v1 (file
lasciato intatto sul disco), NON modifica detector formula/soglia/
direction (verificato qui stesso, programmaticamente, non solo
dichiarato)."""
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
from build_seq0015_frozen_spec import sha256_file, sha256_canonical_json, validate_against_schema  # noqa: E402


INVARIANT_PATHS = [
    ("detector_formula", "true_range_formula"),
    ("detector_formula", "atr_period"),
    ("detector_formula", "burst_ratio_formula"),
    ("detector_formula", "threshold_method"),
    ("detector_formula", "threshold_percentile"),
    ("detector_formula", "threshold_window_bars"),
    ("detector_formula", "threshold_minimum_warmup_bars"),
    ("direction_policy", "rule"),
    ("direction_policy", "no_event_handling"),
    ("observation_timing", "event_a_index"),
    ("observation_timing", "observation_cutoff_index"),
    ("observation_timing", "transition_complete_index"),
    ("observation_timing", "prediction_start_index"),
    ("observation_timing", "outcome_window_start_index"),
]


def load_v1():
    v1_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v1.json")
    with open(v1_path, encoding="utf-8") as f:
        return json.load(f)


def assert_formula_threshold_direction_unchanged(v1_frozen_parameters, v2_frozen_parameters):
    """Verifica PROGRAMMATICA (non solo dichiarata) che detector formula,
    soglia e direction policy siano identici byte-per-byte fra v1 e v2 -
    solo il testo di giustificazione/commento puo' essere cambiato."""
    diffs = []
    for section, key in INVARIANT_PATHS:
        v1_val = v1_frozen_parameters.get(section, {}).get(key)
        v2_val = v2_frozen_parameters.get(section, {}).get(key)
        if v1_val != v2_val:
            diffs.append({"section": section, "key": key, "v1": v1_val, "v2": v2_val})
    return diffs


def build_frozen_spec_v2(v1_spec):
    detector_path = os.path.join(PHASE74_DIR, "seq0015_momentum_burst_detector.py")
    detector_source_hash_v2 = sha256_file(detector_path)
    frozen_parameters_hash_v2 = sha256_canonical_json(FROZEN_PARAMETERS)

    diffs = assert_formula_threshold_direction_unchanged(v1_spec["frozen_parameters"], FROZEN_PARAMETERS)

    frozen_parameters = dict(FROZEN_PARAMETERS)

    # sec.1 - event_cluster_rule vs outcome_overlap_rule, policy congelata (scelta D).
    frozen_parameters["episode_rule"] = dict(frozen_parameters["episode_rule"])
    frozen_parameters["episode_rule"]["event_cluster_rule_bars"] = frozen_parameters["episode_rule"].pop("episode_gap_rule_bars")
    frozen_parameters["episode_rule"]["outcome_overlap_rule"] = {
        "concept_distinction": (
            "event_cluster_rule (3 barre) risponde 'e' la stessa espansione fisica locale?' - usato per "
            "EPISODE_VIEW. outcome_overlap_rule risponde 'le finestre di misura dell'outcome si "
            "sovrappongono, anche se le espansioni fisiche sono diverse?' - due episodi a gap>3 ma con "
            "outcome window sovrapposte NON sono osservazioni indipendenti solo perche' superano gap=3."
        ),
        "outcome_overlap_embargo_bars": 39,
        "embargo_derivation": "natural_horizon-1 = 40-1 = 39: due eventi a distanza d hanno outcome window sovrapposte se e solo se d<natural_horizon (finestra [t+1,t+natural_horizon]), quindi l'ultimo d che sovrappone e' natural_horizon-1.",
        "method_chosen": "D - combinazione predefinita: (1) declustering per embargo (embargo=39) sui rappresentanti di EPISODE_VIEW per ottenere INDEPENDENT_VIEW (sequence_episode_engine.build_outcome_independent_view), usata come n per Wilson/two-proportion/bootstrap su TUTTI i 7 outcome; (2) moving block bootstrap come diagnostica di dipendenza residua quando il candidato risulta DEPENDENCE_SENSITIVE anche dopo l'embargo.",
        "alternatives_considered": {
            "A_episode_clustering_overlap_aware": "Scartata come UNICA soluzione: ridefinire event_cluster_rule stesso in funzione dell'overlap dell'outcome confonderebbe due concetti distinti (espansione fisica locale vs indipendenza statistica dell'outcome) nello stesso parametro, perdendo la possibilita' di diagnosticare separatamente 'quante espansioni fisiche' vs 'quante osservazioni indipendenti'.",
            "B_embargo_only": "Insufficiente da sola: un embargo a larghezza fissa=natural_horizon-1 elimina la pseudo-indipendenza pairwise ma non cattura dipendenza seriale residua su catene piu' lunghe (es. una sequenza di burst ciascuno a 38 barre dall'altro, che coprirebbe centinaia di barre pur essendo ogni singola coppia sotto l'embargo).",
            "C_bootstrap_only": "Insufficiente da sola: senza prima correggere l'n nominale con l'embargo, il bootstrap a blocchi verrebbe applicato a un campione gia' contaminato da pseudo-indipendenza pairwise ovvia (esattamente il caso t=100/t=105 dell'esempio) - il bootstrap correggerebbe la STIMA di incertezza ma non l'inflazione grossolana del conteggio n stesso.",
            "D_chosen": "Scelta: l'embargo risolve la pseudo-indipendenza pairwise ESATTA e ovvia (il problema descritto esplicitamente dall'utente), il bootstrap resta come rete di sicurezza per dipendenza residua piu' sottile - nessuna delle due soluzioni da sola e' sufficiente, la combinazione si allinea anche alla 'future_direction' gia' dichiarata in policies/minimum_evidence_gates.json (stimare direttamente l'incertezza con block bootstrap quando DEPENDENCE_SENSITIVE).",
        },
        "synthetic_tests_ref": "server/research_scripts/phase7/phase7_3/engine/sequence_episode_engine.py (Caso 4/5/6/7 nel __main__) + server/research_scripts/phase7/phase7_4/test_phase7_4a_integrity_patch.py",
    }

    # sec.2 - contratto statistico per outcome (documento separato, referenziato qui).
    frozen_parameters["statistical_test_contract_ref"] = "server/research_scripts/phase7/phase7_4/seq0015_statistical_test_contract_v1.json"
    frozen_parameters["statistical_test_contract_summary"] = {
        "binary_outcomes": ["P_PLUS_1ATR_BEFORE_MINUS_1ATR", "P_PLUS_0_5ATR_BEFORE_MINUS_1ATR", "P_PLUS_1_5ATR_BEFORE_MINUS_1ATR"],
        "binary_method": "WILSON_CI95 + two_proportion_z_test (invariato, gia' coerente - sec.2)",
        "continuous_outcomes": ["MFE", "MAE", "TIME_TO_MFE", "PATH_EFFICIENCY"],
        "continuous_method": "two_sample_block_bootstrap_percentile_p (nuovo, estensione esplicita di statistical_methods_policy.json sec.2 - Wilson NON applicabile a variabili continue)",
        "n_inferential_outcomes_with_frozen_pvalue_method": 7,
        "n_outcomes_moved_to_diagnostic": 0,
        "note": "Tutti i 6 secondary avevano gia' un test inferenziale definibile con metodi ammessi dal progetto - nessuna demotion a DIAGNOSTIC_ONLY necessaria (verificato programmaticamente da build_seq0015_statistical_test_contract.py, non assunto).",
    }

    # sec.3 - conferma eseguibilita' della famiglia BH-FDR.
    frozen_parameters["multiple_testing_full_family"] = dict(frozen_parameters["multiple_testing_full_family"])
    frozen_parameters["multiple_testing_full_family"]["p_values_defined_for_all_21_members"] = True
    frozen_parameters["multiple_testing_full_family"]["verification_method"] = "build_seq0015_statistical_test_contract.py - ogni entry del contratto ha hypothesis_test/p_value_method non nulli, verificato programmaticamente (non solo dichiarato) prima di congelare questo spec."

    # sec.4 - correzione terminologica (propagata anche qui, non solo nel detector).
    frozen_parameters["failure_memory_terminology_correction_note"] = (
        "Corretto (sec.4): H008_EVENT_VOLATILITY_EXPANSION usava ATR_t, che e' causale al momento della "
        "decisione (disponibile a close(t), nessun dato futuro) ma self-normalized/endogeno rispetto alla "
        "propria anomalia (TR_t contribuisce ad ATR_t e ne attenua meccanicamente burst_ratio) - MAI "
        "descritto come 'non causale' in questo documento o nei successivi."
    )

    frozen_parameters["provenance"] = {
        "detector_source_hash": detector_source_hash_v2,
        "detector_source_file": "server/research_scripts/phase7/phase7_4/seq0015_momentum_burst_detector.py",
        "frozen_parameters_hash": frozen_parameters_hash_v2,
        "supersedes": "phase7_4_seq0015_frozen_spec_v1.json",
        "v1_detector_source_hash": v1_spec["frozen_parameters"]["provenance"]["detector_source_hash"],
        "v1_frozen_parameters_hash": v1_spec["frozen_parameters"]["provenance"]["frozen_parameters_hash"],
        "detector_source_hash_changed_from_v1": detector_source_hash_v2 != v1_spec["frozen_parameters"]["provenance"]["detector_source_hash"],
        "detector_source_hash_change_reason": "SOLO commenti/docstring (correzione terminologica sec.4 + nota Integrity Patch) - formula/soglia/direction verificati invariati programmaticamente, vedi 'formula_threshold_direction_diffs_vs_v1' (deve essere lista vuota).",
        "formula_threshold_direction_diffs_vs_v1": diffs,
        "supersession_reason": "Phase 7.4A Integrity Patch (2026-09-20): (1) event_cluster_rule vs outcome_overlap_rule non distinti in v1 - rischio di pseudo-indipendenza per episodi separati da >event_cluster_rule ma <natural_horizon; (2) uncertainty_method=WILSON_CI95 dichiarato genericamente in v1 non e' applicabile ai 4 outcome continui; (3) terminologia 'non causale' applicata impropriamente ad ATR_t nel novelty_note di v1.",
    }

    spec = dict(v1_spec)  # stessa struttura schema-conforme di v1, solo i campi sopra sono corretti/estesi
    spec["frozen_parameters"] = frozen_parameters
    spec["uncertainty_method"] = "WILSON_CI95"  # invariato - descrive il PRIMARY outcome (binario); dettaglio completo nel contratto per-outcome referenziato

    # Correzione terminologica nel novelty_note (sec.4).
    old_phrase = "USANDO ATR SAME-BAR (non causale rispetto alla propria anomalia, verificato leggendo wilder_atr())."
    new_phrase = ("USANDO ATR SAME-BAR (ATR_t - causale al momento della decisione, disponibile a close(t), ma "
                  "self-normalized/endogeno rispetto alla propria anomalia: TR_t contribuisce ad ATR_t e ne "
                  "attenua meccanicamente il rapporto di anomalia, verificato leggendo wilder_atr()).")
    assert old_phrase in spec["failure_memory_links"]["novelty_note"], "frase da correggere non trovata in v1 - controllare il testo sorgente"
    spec["failure_memory_links"] = dict(spec["failure_memory_links"])
    spec["failure_memory_links"]["novelty_note"] = spec["failure_memory_links"]["novelty_note"].replace(old_phrase, new_phrase)

    return spec, diffs


def main():
    v1_spec = load_v1()
    spec, diffs = build_frozen_spec_v2(v1_spec)

    if diffs:
        print("ERRORE: formula/soglia/direction sono cambiate rispetto a v1 - vietato da sec.5!")
        print(json.dumps(diffs, indent=2, ensure_ascii=False))
        raise SystemExit(1)
    print("Verifica programmatica: formula/soglia/direction IDENTICHE a v1 (0 diff su 14 campi invarianti controllati).")

    result = validate_against_schema(spec)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["PASS"]:
        raise SystemExit("Frozen spec v2 NON conforme allo schema - non scritto su disco.")

    out_path = os.path.join(PHASE74_DIR, "phase7_4_seq0015_frozen_spec_v2.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    print(f"\nScritto: {out_path}")
    print(f"detector_source_hash (v2) = {spec['frozen_parameters']['provenance']['detector_source_hash']}")
    print(f"frozen_parameters_hash (v2) = {spec['frozen_parameters']['provenance']['frozen_parameters_hash']}")
    print(f"detector_source_hash_changed_from_v1 = {spec['frozen_parameters']['provenance']['detector_source_hash_changed_from_v1']} (atteso: True, solo commenti/doc)")
    return True


if __name__ == "__main__":
    main()
